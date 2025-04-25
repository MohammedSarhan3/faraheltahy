from django.db import models
from django.db.models import Sum
from django.utils import timezone

class SupplyOrder(models.Model):
    id = models.AutoField(primary_key=True)  # Keep the existing id
    number = models.PositiveIntegerField(unique=True, null=True)  # Add as a separate field
    supplier_name = models.CharField(max_length=255, default='')
    date = models.DateField(default=timezone.now)
    tons = models.DecimalField(max_digits=10, decimal_places=3, default=0)  # Changed to 3 decimal places for more precision
    price_per_ton = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    def save(self, *args, **kwargs):
        if not self.number:
            last_order = SupplyOrder.objects.order_by('-number').first()
            self.number = (last_order.number + 1) if last_order else 1
        # Convert to Decimal if needed and calculate total
        from decimal import Decimal
        tons = Decimal(str(self.tons))
        price = Decimal(str(self.price_per_ton))
        self.total_amount = tons * price
        
        # Save the supply order first
        super().save(*args, **kwargs)
        
        # Create inventory transaction if it doesn't exist
        from django.db import transaction
        with transaction.atomic():
            if not self.transactions.exists():
                InventoryTransaction.objects.create(
                    transaction_type='IN',
                    supply_order=self,
                    tons=self.tons,
                    original_quantity=self.tons
                )

    @property
    def paid_amount(self):
        return self.payments.aggregate(total=Sum('amount'))['total'] or 0
    
    @property
    def remaining_amount(self):
        return self.total_amount - self.paid_amount
    
    @property
    def total_expenses(self):
        return self.expenses.aggregate(total=Sum('amount'))['total'] or 0
    
    def __str__(self):
        return f"{self.supplier_name} - {self.date} - {self.tons} tons"

class InventoryTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('IN', 'Supply In'),
        ('OUT', 'Sale Out'),
    ]
    
    SOURCE_TYPES = [
        ('SUPPLY', 'Supply Order'),
        ('INVOICE', 'Invoice'),
    ]
    
    date = models.DateField(default=timezone.now)
    transaction_type = models.CharField(max_length=3, choices=TRANSACTION_TYPES)
    supply_order = models.ForeignKey('SupplyOrder', on_delete=models.CASCADE, null=True, blank=True, related_name='transactions')
    invoice = models.ForeignKey('invoices.Invoice', on_delete=models.CASCADE, null=True, blank=True, related_name='transactions')
    
    # For supply orders: stored directly in tons
    # For invoices: stored in tons (converted from pallets * 9kg)
    tons = models.DecimalField(max_digits=10, decimal_places=3)  # 3 decimals for precise kg conversion
    
    # Original quantity (pallets for invoices, tons for supply orders)
    original_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def save(self, *args, **kwargs):
        from decimal import Decimal
        
        if self.invoice:
            # If this is an invoice transaction, convert pallets to tons using pallet type weight
            self.transaction_type = 'OUT'
            self.original_quantity = self.invoice.pallets
            # Calculate tons based on pallet type weight
            pallet_weight_kg = self.invoice.pallet_type.weight
            self.tons = (Decimal(str(self.invoice.pallets)) * Decimal(str(pallet_weight_kg))) / Decimal('1000')
        elif self.supply_order:
            # If this is a supply order transaction, use tons directly
            self.transaction_type = 'IN'
            self.original_quantity = self.supply_order.tons
            self.tons = self.supply_order.tons
            
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.invoice:
            return f"{self.get_transaction_type_display()} - {self.date} - {self.original_quantity} pallets ({self.tons} tons)"
        return f"{self.get_transaction_type_display()} - {self.date} - {self.tons} tons"
    
    @staticmethod
    def format_tons_and_kilos(decimal_tons):
        """Convert decimal tons to tons and kilos format"""
        from decimal import Decimal
        # Convert to total kilos and ensure positive values
        total_kilos = abs(int(Decimal(str(decimal_tons)) * 1000))
        # Split into tons and remaining kilos
        tons = total_kilos // 1000
        kilos = total_kilos % 1000
        return (tons, kilos)
    
    @classmethod
    def get_current_inventory_display(cls):
        """Get current inventory in tons and kilos format"""
        from django.db.models import Sum
        from decimal import Decimal
        
        # Check if there are any transactions
        if not cls.objects.exists():
            return (0, 0)  # Return zero if no transactions exist
        
        # Get total IN transactions (supply orders)
        total_in = cls.objects.filter(transaction_type='IN').aggregate(total=Sum('tons'))['total'] or Decimal('0')
        
        # Get total OUT transactions (invoices)
        total_out = cls.objects.filter(transaction_type='OUT').aggregate(total=Sum('tons'))['total'] or Decimal('0')
        
        # Calculate current inventory
        current_inventory = total_in - total_out
        
        # Ensure we don't return negative values
        if current_inventory < 0:
            current_inventory = Decimal('0')
            
        return cls.format_tons_and_kilos(current_inventory)

class Payment(models.Model):
    supply_order = models.ForeignKey(SupplyOrder, on_delete=models.CASCADE, related_name='payments')
    date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    image = models.ImageField(upload_to='payment_receipts/', null=True, blank=True, verbose_name='صورة الشيك/التحويل')

    def __str__(self):
        return f"Payment for {self.supply_order.supplier_name} - {self.date} - {self.amount}"

class Expense(models.Model):
    supply_order = models.ForeignKey(SupplyOrder, on_delete=models.CASCADE, related_name='expenses')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=200)
    date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"نثريات {self.supply_order.supplier_name} - {self.date} - {self.amount}"

    class Meta:
        ordering = ['-date']

class BalanceEntry(models.Model):
    """Individual balance entry that can be withdrawn from"""
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date_added = models.DateField(default=timezone.now)
    number = models.PositiveIntegerField(default=1)  # The balance number (1, 2, etc.)
    remaining = models.DecimalField(max_digits=12, decimal_places=2)
    
    class Meta:
        ordering = ['-number']
    
    def __str__(self):
        return f"رصيد رقم {self.number} - {self.remaining}"
    
    def save(self, *args, **kwargs):
        if not self.id:  # If this is a new entry
            # Get the highest number and add 1, or start at 1
            highest = BalanceEntry.objects.all().order_by('-number').first()
            self.number = (highest.number + 1) if highest else 1
            self.remaining = self.amount
        super().save(*args, **kwargs)

class SafeTransaction(models.Model):
    balance_entry = models.ForeignKey(
        BalanceEntry,
        on_delete=models.CASCADE,  # Changed from PROTECT to CASCADE to automatically delete related transactions
        related_name='transactions',
        null=True
    )
    date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=200)
    
    class Meta:
        ordering = ['-date', '-id']
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.balance_entry:
            raise ValidationError('يجب تحديد رقم الرصيد')
            
        # Check if this is a new transaction or an edit
        if self.id:
            # This is an edit - get the original transaction amount
            try:
                original = SafeTransaction.objects.get(id=self.id)
                original_amount = original.amount
                
                # Calculate the effective remaining balance for validation
                # (Add back original amount to get the balance before this transaction)
                effective_remaining = self.balance_entry.remaining + original_amount
                
                # Now check if the new amount would overdraw
                if self.amount > effective_remaining:
                    raise ValidationError(f'الرصيد غير كافي في رصيد رقم {self.balance_entry.number}. المتبقي المتاح: {effective_remaining}')
            except SafeTransaction.DoesNotExist:
                pass
        elif self.amount > self.balance_entry.remaining:  # New transaction
            raise ValidationError(f'الرصيد غير كافي في رصيد رقم {self.balance_entry.number}. المتبقي: {self.balance_entry.remaining}')
    
    def __str__(self):
        return f"سحب من رصيد {self.balance_entry.number} - {self.amount} - {self.date}"
    
    def save(self, *args, **kwargs):
        self.clean()  # Run validation before saving
        
        # Store original amount if this is an update (not a new transaction)
        if self.id:
            try:
                # Get the original transaction before changes
                original = SafeTransaction.objects.get(id=self.id)
                original_amount = original.amount
                
                # Restore the original amount to the balance
                self.balance_entry.remaining += original_amount
                # Subtract the new amount
                self.balance_entry.remaining -= self.amount
                self.balance_entry.save()
            except SafeTransaction.DoesNotExist:
                pass
        else:  # This is a new transaction
            self.balance_entry.remaining -= self.amount
            self.balance_entry.save()
            
        super().save(*args, **kwargs)

    @property
    def get_balance_after(self):
        """Get remaining balance after this transaction"""
        # We need to calculate the balance that would be shown after this particular transaction
        # considering the order of all transactions
        
        from django.db.models import Sum
        
        # Get all transactions for this balance entry that occurred
        # on or before this transaction's date, and with <= this transaction's ID
        # This gives us all transactions including this one in correct chronological order
        transactions_up_to_this_one = SafeTransaction.objects.filter(
            balance_entry=self.balance_entry
        ).filter(
            models.Q(date__lt=self.date) | 
            (models.Q(date=self.date) & models.Q(id__lte=self.id))
        ).order_by('date', 'id')
        
        # Sum up all those transactions
        total_withdrawn = transactions_up_to_this_one.aggregate(total=Sum('amount'))['total'] or 0
        
        # Return original balance minus all withdrawals up to and including this one
        return self.balance_entry.amount - total_withdrawn
