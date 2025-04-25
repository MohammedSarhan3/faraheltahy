from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Invoice, Payment, Customer

class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'invoices/customer_list.html'
    context_object_name = 'customers'
    ordering = ['-date_added']

    def get_queryset(self):
        queryset = super().get_queryset()
        customer_search = self.request.GET.get('customer_search')
        if customer_search:
            queryset = queryset.filter(name__icontains=customer_search)
        return queryset.order_by('-date_added')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Calculate totals for displayed customers
        for customer in context['customers']:
            customer.total_amount = customer.total_invoices_amount()
            customer.remaining = customer.total_remaining_amount()
        
        # Add all customer names for the dropdown
        context['all_customer_names'] = Customer.objects.values_list('name', flat=True).order_by('name').distinct()
        return context

class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = Customer
    template_name = 'invoices/customer_detail.html'
    context_object_name = 'customer'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['invoices'] = self.object.invoices.all().order_by('-date')
        context['total_amount'] = self.object.total_invoices_amount()
        context['total_paid'] = self.object.total_paid_amount()
        context['total_remaining'] = self.object.total_remaining_amount()
        # Add pallet types to context
        from .models import PalletType
        context['pallet_types'] = PalletType.objects.all()
        return context
        
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get('action')
        
        if action == 'add_invoice':
            date = request.POST.get('date')
            pallets = request.POST.get('pallets')
            price_per_pallet = request.POST.get('price_per_pallet')
            initial_payment = request.POST.get('initial_payment', 0)
            
            pallet_type_id = request.POST.get('pallet_type')
            from .models import PalletType
            pallet_type = get_object_or_404(PalletType, id=pallet_type_id)
            
            with transaction.atomic():
                invoice = Invoice.objects.create(
                    customer=self.object,
                    date=date,
                    pallet_type=pallet_type,
                    pallets=pallets,
                    price_per_pallet=price_per_pallet
                )
                
                initial_payment = float(initial_payment) if initial_payment.strip() else 0
                if initial_payment > 0:
                    Payment.objects.create(
                        invoice=invoice,
                        amount=initial_payment,
                        date=date
                    )
                
                messages.success(request, 'تم إضافة الفاتورة بنجاح')

        elif action == 'edit_invoice':
            invoice_id = request.POST.get('invoice_id')
            invoice = get_object_or_404(Invoice, id=invoice_id, customer=self.object)
            
            date = request.POST.get('date')
            pallets = request.POST.get('pallets')
            price_per_pallet = request.POST.get('price_per_pallet')
            pallet_type_id = request.POST.get('pallet_type')
            
            from .models import PalletType
            pallet_type = get_object_or_404(PalletType, id=pallet_type_id)
            
            with transaction.atomic():
                invoice.date = date
                invoice.pallet_type = pallet_type
                invoice.pallets = pallets
                invoice.price_per_pallet = price_per_pallet
                invoice.save()
                
                messages.success(request, 'تم تعديل الفاتورة بنجاح')

        elif action == 'add_payment':
            invoice_id = request.POST.get('invoice_id')
            invoice = get_object_or_404(Invoice, id=invoice_id, customer=self.object)
            
            payment_date = request.POST.get('payment_date')
            payment_amount = request.POST.get('payment_amount')
            
            if payment_amount and float(payment_amount) > 0:
                Payment.objects.create(
                    invoice=invoice,
                    date=payment_date,
                    amount=payment_amount
                )
                messages.success(request, 'تم إضافة الدفعة بنجاح')
            else:
                messages.error(request, 'يجب إدخال مبلغ أكبر من صفر')

        elif action == 'delete_invoice':
            invoice_id = request.POST.get('invoice_id')
            invoice = get_object_or_404(Invoice, id=invoice_id, customer=self.object)
            
            with transaction.atomic():
                # Delete the invoice and its related transactions
                invoice.delete()
                messages.success(request, 'تم حذف الفاتورة بنجاح')

        elif action == 'edit_payment':
            payment_id = request.POST.get('payment_id')
            payment = get_object_or_404(Payment, id=payment_id, invoice__customer=self.object)
            
            payment_date = request.POST.get('payment_date')
            payment_amount = request.POST.get('payment_amount')
            
            if payment_amount and float(payment_amount) > 0:
                payment.date = payment_date
                payment.amount = payment_amount
                payment.save()
                messages.success(request, 'تم تعديل الدفعة بنجاح')
            else:
                messages.error(request, 'يجب إدخال مبلغ أكبر من صفر')

        elif action == 'delete_payment':
            payment_id = request.POST.get('payment_id')
            payment = get_object_or_404(Payment, id=payment_id, invoice__customer=self.object)
            payment.delete()
            messages.success(request, 'تم حذف الدفعة بنجاح')
            
        elif action == 'edit_customer':
            name = request.POST.get('name')
            phone = request.POST.get('phone')
            
            if not name:
                messages.error(request, 'يجب إدخال اسم العميل')
            else:
                self.object.name = name
                self.object.phone = phone
                self.object.save()
                messages.success(request, 'تم تعديل معلومات العميل بنجاح')
        
        return redirect('invoices:customer_detail', pk=self.object.pk)

@login_required
def add_customer(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        
        if not name:
            messages.error(request, 'يجب إدخال اسم العميل')
            return redirect('invoices:customer_list')
        
        customer = Customer.objects.create(
            name=name,
            phone=phone
        )
        messages.success(request, f'تم إضافة العميل {name} بنجاح')
        return redirect('invoices:customer_detail', pk=customer.pk)
    
    return redirect('invoices:customer_list')

@login_required
def delete_customer(request, pk):
    if request.method == 'POST':
        customer = get_object_or_404(Customer, pk=pk)
        customer_name = customer.name
        
        with transaction.atomic():
            # This will automatically delete all related invoices and payments due to CASCADE
            customer.delete()
            messages.success(request, f'تم حذف العميل {customer_name} وجميع فواتيره بنجاح')
        
    return redirect('invoices:customer_list')

