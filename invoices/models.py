from django.db import models
from django.utils import timezone
from django.urls import reverse

class Customer(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True, null=True)
    date_added = models.DateField(default=timezone.now)
    
    def get_absolute_url(self):
        return reverse('invoices:customer_detail', kwargs={'pk': self.pk})
    
    def total_invoices_amount(self):
        return self.invoices.aggregate(total=models.Sum('total_amount'))['total'] or 0
    
    def total_paid_amount(self):
        return Payment.objects.filter(invoice__customer=self).aggregate(total=models.Sum('amount'))['total'] or 0
    
    def total_remaining_amount(self):
        return self.total_invoices_amount() - self.total_paid_amount()
    
    def __str__(self):
        return f"{self.name} - {self.phone}"

def get_default_customer():
    from django.db import models
    Customer = models.get_model('invoices', 'Customer')
    return Customer.objects.get_or_create(name='عميل سابق')[0].id

class PalletType(models.Model):
    PALLET_TYPES = [
        ('رفيع', 'رفيع'),
        ('عريض', 'عريض'),
    ]
    name = models.CharField(max_length=50)  # e.g. "رفيع 9", "رفيع 18", "عريض 10", "عريض 20"
    type = models.CharField(max_length=10, choices=PALLET_TYPES, default='رفيع')
    weight = models.DecimalField(max_digits=5, decimal_places=2)  # Weight in kg

    def __str__(self):
        return f"{self.weight} {self.type}"

    class Meta:
        ordering = ['type', 'weight']
        verbose_name = "نوع طبلية"
        verbose_name_plural = "أنواع طبليات"

class Invoice(models.Model):
    invoice_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='invoices', null=True)
    date = models.DateField(default=timezone.now)
    pallet_type = models.ForeignKey(PalletType, on_delete=models.CASCADE, related_name='invoices', null=True)  # Making it nullable for migration
    pallets = models.IntegerField()  # Number of pallets
    price_per_pallet = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    @property
    def paid_amount(self):
        return self.payments.aggregate(total=models.Sum('amount'))['total'] or 0
    
    @property
    def remaining_amount(self):
        return self.total_amount - self.paid_amount
    
    @property
    def total_kilos(self):
        return float(self.pallets * self.pallet_type.weight)
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            last_invoice = Invoice.objects.order_by('-id').first()
            if last_invoice:
                last_number = int(last_invoice.invoice_number)
                self.invoice_number = str(last_number + 1).zfill(4)
            else:
                self.invoice_number = '0001'
        
        # Convert to proper numeric types before multiplication
        from decimal import Decimal
        pallets = int(self.pallets) if isinstance(self.pallets, str) else self.pallets
        price = Decimal(str(self.price_per_pallet))
        self.total_amount = pallets * price
        
        from django.db import transaction
        with transaction.atomic():
            super().save(*args, **kwargs)
            
            # Check if an InventoryTransaction already exists for this invoice
            from inventory.models import InventoryTransaction
            if not self.transactions.exists():
                # Create inventory transaction for the sale only if it doesn't exist
                InventoryTransaction.objects.create(
                    transaction_type='OUT',
                    invoice=self,
                    original_quantity=self.pallets,  # Store original pallets count
                    tons=Decimal(str(self.total_kilos)) / 1000  # Convert kilos to tons
                )

    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.customer.name}"

class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    def __str__(self):
        return f"Payment for Invoice #{self.invoice.invoice_number} - {self.amount}"
