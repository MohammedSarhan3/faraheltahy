from django.contrib import admin
from .models import SupplyOrder, InventoryTransaction, Payment, Expense, BalanceEntry, SafeTransaction

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 1

class ExpenseInline(admin.TabularInline):
    model = Expense
    extra = 1

class SupplyOrderAdmin(admin.ModelAdmin):
    list_display = ('supplier_name', 'date', 'tons', 'total_amount', 'paid_amount', 'remaining_amount', 'total_expenses')
    inlines = [PaymentInline, ExpenseInline]
    search_fields = ('supplier_name',)
    list_filter = ('date',)

admin.site.register(SupplyOrder, SupplyOrderAdmin)

@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'transaction_type', 'tons')
    list_filter = ('transaction_type', 'date')
    search_fields = ('transaction_type',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('supply_order', 'date', 'amount')
    list_filter = ('date', 'supply_order__supplier_name')
    search_fields = ('supply_order__supplier_name',)
    ordering = ('-date',)

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('supply_order', 'date', 'amount', 'reason')
    list_filter = ('date', 'supply_order__supplier_name')
    search_fields = ('reason', 'supply_order__supplier_name')

class SafeTransactionInline(admin.TabularInline):
    model = SafeTransaction
    extra = 1

@admin.register(BalanceEntry)
class BalanceEntryAdmin(admin.ModelAdmin):
    list_display = ('number', 'amount', 'remaining', 'date_added')
    readonly_fields = ('number', 'remaining')
    inlines = [SafeTransactionInline]
    ordering = ('-number',)

@admin.register(SafeTransaction)
class SafeTransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'balance_entry', 'amount', 'reason', 'get_balance_after')
    list_filter = ('date', 'balance_entry')
    search_fields = ('reason', 'balance_entry__number')
    ordering = ('-date', '-id')
