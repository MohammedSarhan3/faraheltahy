from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SupplyOrder, InventoryTransaction
from invoices.models import Invoice

@receiver(post_save, sender=SupplyOrder)
def create_supply_transaction(sender, instance, created, **kwargs):
    if created:
        InventoryTransaction.objects.create(
            supply_order=instance,
            date=instance.date,
        )

@receiver(post_save, sender=Invoice)
def create_invoice_transaction(sender, instance, created, **kwargs):
    if created:
        InventoryTransaction.objects.create(
            invoice=instance,
            date=instance.date,
        )
    else:
        # Update existing transaction when invoice is modified
        transaction = InventoryTransaction.objects.filter(invoice=instance).first()
        if transaction:
            transaction.date = instance.date
            transaction.original_quantity = instance.pallets
            transaction.tons = float(instance.total_kilos) / 1000
            transaction.save()
