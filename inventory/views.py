from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Sum, F, Count
from django.db import transaction
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from .models import SupplyOrder, InventoryTransaction, Payment, BalanceEntry, SafeTransaction, Expense
from decimal import Decimal
import decimal

@login_required
def safebox_management(request):
    try:
        # Get all balance entries
        balances = BalanceEntry.objects.all().order_by('-number')
        
        # Handle transaction filtering
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        balance_number = request.GET.get('balance_number')
        
        # Base queryset for transactions
        transactions = SafeTransaction.objects.all()
        
        # Apply filters if provided
        if start_date:
            transactions = transactions.filter(date__gte=start_date)
        if end_date:
            transactions = transactions.filter(date__lte=end_date)
        if balance_number:
            transactions = transactions.filter(balance_entry__number=balance_number)
        
        if request.method == 'POST':
            action = request.POST.get('action')
            try:
                # For actions that require amount
                if action in ['add_balance', 'withdraw', 'edit_balance', 'edit_transaction']:
                    amount_str = request.POST.get('amount', '0').replace(',', '')
                    amount = Decimal(amount_str)
                    
                    if amount <= 0:
                        raise ValueError('المبلغ يجب أن يكون أكبر من صفر')
                
                if action == 'add_balance':
                    # Create new balance entry
                    balance = BalanceEntry.objects.create(amount=amount)
                    messages.success(request, f'تم إضافة رصيد جديد رقم {balance.number} بمبلغ {amount} جنيه')
                    return redirect('inventory:safebox_management')
                
                elif action == 'edit_balance':
                    balance_number = request.POST.get('balance_number')
                    date_added = request.POST.get('date_added') or timezone.now().date()
                    
                    if not balance_number:
                        raise ValueError('معرف الرصيد مطلوب')
                    
                    balance = BalanceEntry.objects.filter(number=balance_number).first()
                    if not balance:
                        raise BalanceEntry.DoesNotExist(f'الرصيد رقم {balance_number} غير موجود')
                    
                    # Calculate total withdrawals for this balance entry
                    total_withdrawals = SafeTransaction.objects.filter(
                        balance_entry=balance
                    ).aggregate(total=Sum('amount'))['total'] or 0
                    
                    # Update the balance amount
                    balance.amount = amount
                    balance.date_added = date_added
                    
                    # Recalculate the remaining balance
                    balance.remaining = amount - total_withdrawals
                    
                    balance.save()
                    
                    messages.success(request, f'تم تعديل الرصيد رقم {balance_number} بنجاح')
                    return redirect('inventory:safebox_management')
                
                elif action == 'delete_balance':
                    balance_number = request.POST.get('balance_number')
                    
                    if not balance_number:
                        raise ValueError('معرف الرصيد مطلوب')
                    
                    balance = BalanceEntry.objects.filter(number=balance_number).first()
                    if not balance:
                        raise BalanceEntry.DoesNotExist(f'الرصيد رقم {balance_number} غير موجود')
                        
                    balance.delete()
                    
                    messages.success(request, f'تم حذف الرصيد رقم {balance_number} بنجاح')
                    return redirect('inventory:safebox_management')
                
                elif action == 'withdraw':
                    balance_number = request.POST.get('balance_number')
                    reason = request.POST.get('reason')
                    date = request.POST.get('date') or timezone.now().date()
                    
                    if not balance_number:
                        raise ValueError('برجاء اختيار رقم الرصيد')
                    if not reason:
                        raise ValueError('برجاء إدخال السبب')
                    
                    balance = BalanceEntry.objects.filter(number=balance_number).first()
                    if not balance:
                        raise BalanceEntry.DoesNotExist(f'الرصيد رقم {balance_number} غير موجود')
                    
                    try:
                        SafeTransaction.objects.create(
                            balance_entry=balance,
                            amount=amount,
                            reason=reason,
                            date=date
                        )
                        messages.success(request, f'تم سحب {amount} جنيه من رصيد رقم {balance_number} بنجاح')
                        return redirect('inventory:safebox_management')
                    except ValueError as e:
                        messages.error(request, str(e))
                
                elif action == 'edit_transaction':
                    transaction_id = request.POST.get('transaction_id')
                    reason = request.POST.get('reason')
                    date = request.POST.get('date') or timezone.now().date()
                    
                    if not transaction_id:
                        raise ValueError('معرف المعاملة مطلوب')
                    if not reason:
                        raise ValueError('برجاء إدخال السبب')
                    
                    with transaction.atomic():
                        # Get the transaction and its balance entry
                        safe_transaction = SafeTransaction.objects.select_for_update().get(id=transaction_id)
                        
                        # Update transaction details (only reason and date, not amount)
                        # Keep the original amount - the amount cannot be edited
                        safe_transaction.reason = reason
                        safe_transaction.date = date
                        safe_transaction.save(update_fields=['reason', 'date'])
                    
                    messages.success(request, f'تم تعديل المعاملة بنجاح')
                    return redirect('inventory:safebox_management')
                
                elif action == 'delete_transaction':
                    transaction_id = request.POST.get('transaction_id')
                    
                    if not transaction_id:
                        raise ValueError('معرف المعاملة مطلوب')
                    
                    with transaction.atomic():
                        safe_transaction = SafeTransaction.objects.select_for_update().get(id=transaction_id)
                        balance = safe_transaction.balance_entry
                        
                        # Add the transaction amount back to the remaining balance before deleting
                        balance.remaining += safe_transaction.amount
                        balance.save()
                        
                        balance_number = balance.number
                        safe_transaction.delete()
                    
                    messages.success(request, f'تم حذف المعاملة من الرصيد رقم {balance_number} بنجاح')
                    return redirect('inventory:safebox_management')
                    
            except ValueError as e:
                messages.error(request, str(e))
            except decimal.InvalidOperation:
                messages.error(request, 'برجاء إدخال مبلغ صحيح')
            except BalanceEntry.DoesNotExist:
                messages.error(request, 'رقم الرصيد غير موجود')
            except Exception as e:
                messages.error(request, f'حدث خطأ غير متوقع: {str(e)}')
        
        # Get the last 50 transactions
        transactions = transactions.order_by('-date', '-id')[:50]
        
        context = {
            'balances': balances,
            'transactions': transactions,
            'filters': {
                'start_date': start_date,
                'end_date': end_date,
                'balance_number': balance_number
            }
        }
        
        return render(request, 'inventory/safebox_management.html', context)
    except Exception as e:
        messages.error(request, f'حدث خطأ: {str(e)}')
        return redirect('inventory:dashboard')
   

@login_required
def dashboard(request):
    # Calculate total IN transactions (from supply orders) - using .all() to ensure fresh data
    in_transactions = InventoryTransaction.objects.filter(transaction_type='IN').all()
    in_total = in_transactions.aggregate(total=Sum('tons'))['total'] or 0
    
    # Calculate financial totals for safe
    from invoices.models import Invoice, Payment as InvoicePayment
    from .models import Payment as SupplyPayment
    
    # Total collected from customers (invoice payments)
    total_collected_invoices = InvoicePayment.objects.aggregate(total=Sum('amount'))['total'] or 0
    
    # Total due from customers
    total_invoices = Invoice.objects.aggregate(total=Sum(F('pallets') * F('price_per_pallet')))['total'] or 0
    total_customer_due = total_invoices - total_collected_invoices
    
    # Total supplier payments and dues
    total_supply_amount = SupplyOrder.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    total_supply_paid = SupplyPayment.objects.aggregate(total=Sum('amount'))['total'] or 0
    total_supplier_due = (total_supply_amount or 0) - (total_supply_paid or 0)
    
    # Calculate total OUT transactions (from invoices)
    out_transactions = InventoryTransaction.objects.filter(transaction_type='OUT').all()
    out_total = out_transactions.aggregate(total=Sum('tons'))['total'] or 0
    
    # Get formatted inventory display with fresh data
    inventory_display = InventoryTransaction.get_current_inventory_display()
    
    # Get recent supply orders
    recent_supplies = SupplyOrder.objects.all().order_by('-date')[:5]
    
    # Get inventory transactions with fresh data
    transactions = InventoryTransaction.objects.all().order_by('-date')[:10]  # Get last 10 transactions
    
    context = {
        'total_in': in_total,
        'total_out': out_total,
        'inventory_display': inventory_display,
        'recent_supplies': recent_supplies,
        'transactions': transactions,
        # Safe financial data
        'total_collected': total_collected_invoices,
        'total_customer_due': total_customer_due,
        'total_supplier_due': total_supplier_due,
    }
    return render(request, 'inventory/dashboard.html', context)
@login_required
def supply_orders_management(request, supply_order_id=None):
    # Get the base queryset
    supply_orders = SupplyOrder.objects.all()
    
    # Apply year and month filters if present
    filter_year = request.GET.get('filter_year')
    filter_month = request.GET.get('filter_month')
    
    if filter_year:
        try:
            year = int(filter_year)
            supply_orders = supply_orders.filter(date__year=year)
        except (ValueError, TypeError):
            messages.error(request, 'تنسيق السنة غير صحيح')
    
    if filter_month:
        try:
            month = int(filter_month)
            supply_orders = supply_orders.filter(date__month=month)
        except (ValueError, TypeError):
            messages.error(request, 'تنسيق الشهر غير صحيح')
    
    # Order by date
    supply_orders = supply_orders.order_by('-date')
    
    current_supply_order = None
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if supply_order_id:
        current_supply_order = get_object_or_404(SupplyOrder, id=supply_order_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        response_data = {'success': False, 'message': ''}
        
        try:
            if action == 'add_supply':
                supplier_name = request.POST.get('supplier_name')
                date = request.POST.get('date')
                tons = request.POST.get('tons')
                price_per_ton = request.POST.get('price_per_ton')
                initial_payment = request.POST.get('initial_payment', '')
                initial_payment_image = request.FILES.get('initial_payment_image')
                
                with transaction.atomic():
                    supply_order = SupplyOrder.objects.create(
                        supplier_name=supplier_name,
                        date=date,
                        tons=tons,
                        price_per_ton=price_per_ton
                    )
                    
                    if initial_payment and float(initial_payment) > 0:
                        Payment.objects.create(
                            supply_order=supply_order,
                            amount=initial_payment,
                            date=date,
                            image=initial_payment_image
                        )
                    
                    response_data['success'] = True
                    response_data['message'] = 'تم إضافة التوريدة بنجاح'
                
            elif action == 'edit_supply':
                supply_order_id = request.POST.get('supply_order_id')
                supply_order = get_object_or_404(SupplyOrder, id=supply_order_id)
                supplier_name = request.POST.get('supplier_name')
                date = request.POST.get('date')
                tons = request.POST.get('tons')
                price_per_ton = request.POST.get('price_per_ton')
                new_image = request.FILES.get('supply_image')
                
                with transaction.atomic():
                    # Update the SupplyOrder
                    supply_order.supplier_name = supplier_name
                    supply_order.date = date
                    supply_order.price_per_ton = price_per_ton
                    
                    # Handle image update
                    if new_image:
                        # Delete old image if it exists
                        if supply_order.image:
                            supply_order.image.delete(save=False)
                        supply_order.image = new_image
                    
                    # Update the associated InventoryTransaction if tons have changed
                    if float(supply_order.tons) != float(tons):
                        inv_transaction = InventoryTransaction.objects.filter(
                            supply_order=supply_order, 
                            transaction_type='IN'
                        ).first()
                        
                        if inv_transaction:
                            inv_transaction.tons = tons
                            inv_transaction.save()
                    
                    # Update the tons after updating inventory transaction
                    supply_order.tons = tons
                    supply_order.save()
                    
                    response_data['success'] = True
                    response_data['message'] = 'تم تعديل التوريدة بنجاح'
                
            elif action == 'delete_supply':
                supply_order_id = request.POST.get('supply_order_id')
                supply_order = get_object_or_404(SupplyOrder, id=supply_order_id)
                
                # Store supplier name to use in success message
                supplier_name = supply_order.supplier_name
                
                with transaction.atomic():
                    # Delete related inventory transaction first
                    InventoryTransaction.objects.filter(supply_order=supply_order).delete()
                    # Delete the supply order (will cascade delete payments and expenses)
                    supply_order.delete()
                
                response_data['success'] = True
                response_data['message'] = 'تم حذف توريدة {} بنجاح'.format(supplier_name)
                
            elif action == 'add_payment':
                try:
                    supply_order = get_object_or_404(SupplyOrder, id=request.POST.get('supply_order_id'))
                    amount = request.POST.get('payment_amount')
                    date = request.POST.get('payment_date')
                    payment_image = request.FILES.get('payment_image')
                    
                    if not amount:
                        raise ValueError('برجاء إدخال المبلغ')
                    if not date:
                        raise ValueError('برجاء إدخال التاريخ')
                    
                    Payment.objects.create(
                        supply_order=supply_order,
                        amount=amount,
                        date=date,
                        image=payment_image
                    )
                    
                    if is_ajax:
                        return JsonResponse({
                            'success': True,
                            'message': 'تم إضافة الدفعة بنجاح'
                        })
                    messages.success(request, 'تم إضافة الدفعة بنجاح')
                    return redirect('inventory:supply_orders_management', supply_order_id=supply_order.id)
                except ValueError as e:
                    if is_ajax:
                        return JsonResponse({
                            'success': False,
                            'message': str(e)
                        })
                    messages.error(request, str(e))
                    return redirect('inventory:supply_orders_management', supply_order_id=supply_order.id)
                
                Payment.objects.create(
                    supply_order=supply_order,
                    amount=amount,
                    date=date,
                    image=payment_image
                )
                
                response_data['success'] = True
                response_data['message'] = 'تم إضافة الدفعة بنجاح'
                
            elif action == 'edit_payment':
                payment_id = request.POST.get('payment_id')
                payment = get_object_or_404(Payment, id=payment_id)
                amount = request.POST.get('payment_amount')
                date = request.POST.get('payment_date')
                new_image = request.FILES.get('payment_image')
                
                payment.amount = amount
                payment.date = date
                
                # Handle image update
                if new_image:
                    # Delete old image if it exists
                    if payment.image:
                        payment.image.delete(save=False)
                    payment.image = new_image
                    
                payment.save()
                
                response_data['success'] = True
                response_data['message'] = 'تم تعديل الدفعة بنجاح'
                
            elif action == 'delete_payment':
                payment_id = request.POST.get('payment_id')
                payment = get_object_or_404(Payment, id=payment_id)
                supply_order_id = payment.supply_order.id
                
                payment.delete()
                
                response_data['success'] = True
                response_data['message'] = 'تم حذف الدفعة بنجاح'
                
            elif action == 'add_expense':
                supply_order = get_object_or_404(SupplyOrder, id=request.POST.get('supply_order_id'))
                amount = request.POST.get('expense_amount')
                reason = request.POST.get('expense_reason')
                date = request.POST.get('expense_date')
                
                Expense.objects.create(
                    supply_order=supply_order,
                    amount=amount,
                    reason=reason,
                    date=date
                )
                
                response_data['success'] = True
                response_data['message'] = 'تم إضافة النثريات بنجاح'
                
            elif action == 'edit_expense':
                expense_id = request.POST.get('expense_id')
                expense = get_object_or_404(Expense, id=expense_id)
                amount = request.POST.get('expense_amount')
                reason = request.POST.get('expense_reason')
                date = request.POST.get('expense_date')
                
                expense.amount = amount
                expense.reason = reason
                expense.date = date
                expense.save()
                
                response_data['success'] = True
                response_data['message'] = 'تم تعديل النثريات بنجاح'
                
            elif action == 'delete_expense':
                expense_id = request.POST.get('expense_id')
                expense = get_object_or_404(Expense, id=expense_id)
                supply_order_id = expense.supply_order.id
                
                expense.delete()
                
                response_data['success'] = True
                response_data['message'] = 'تم حذف النثريات بنجاح'
            
            if is_ajax:
                return JsonResponse(response_data)
            else:
                if response_data['success']:
                    messages.success(request, response_data['message'])
                return redirect('inventory:supply_orders_management')
                
        except Exception as e:
            response_data['message'] = str(e)
            if is_ajax:
                return JsonResponse(response_data)
            messages.error(request, str(e))
            return redirect('inventory:supply_orders_management')
    
    # Generate years list for the filter (from 2023 to current year + 1)
    current_date = timezone.now()
    current_year = current_date.year
    current_month = current_date.month
    available_years = list(range(2023, current_year + 2))  # +2 to include next year
    
    # Set default filter values if none are selected
    if not filter_year and not filter_month:
        filter_year = str(current_year)
        filter_month = f"{current_month:02d}"
    
    context = {
        'supply_orders': supply_orders,
        'current_supply_order': current_supply_order,
        'available_years': available_years,
        'current_year': current_year,
        'current_month': f"{current_month:02d}"
    }
    
    return render(request, 'inventory/supply_orders_management.html', context)
@login_required
def inventory_status(request):
    # Calculate total IN transactions (from supply orders)
    in_total = InventoryTransaction.objects.filter(transaction_type='IN').aggregate(total=Sum('tons'))['total'] or 0
    
    # Calculate total OUT transactions (from invoices)
    out_total = InventoryTransaction.objects.filter(transaction_type='OUT').aggregate(total=Sum('tons'))['total'] or 0
    
    # Calculate current inventory
    current_inventory = in_total - out_total
    
    # Get all inventory transactions ordered by date
    transactions = InventoryTransaction.objects.order_by('-date')
    
    context = {
        'transactions': transactions,
        'current_inventory': current_inventory,
    }
    return render(request, 'inventory/inventory_status.html', context)


