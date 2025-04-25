from django.contrib import admin
from .models import Invoice, Payment, Customer

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 1

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'date_added')
    search_fields = ('name', 'phone')
    ordering = ('-date_added',)

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'customer', 'date', 'pallets', 
                   'total_kilos', 'total_amount', 'paid_amount', 'remaining_amount')
    list_filter = ('date', 'customer')
    search_fields = ('invoice_number', 'customer__name')
    inlines = [PaymentInline]

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'date', 'amount')
    list_filter = ('date', 'invoice__customer')
    search_fields = ('invoice__invoice_number', 'invoice__customer__name')
