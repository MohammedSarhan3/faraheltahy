from django import forms
from .models import Supplier, SupplyOrder

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
        }

class SupplyOrderForm(forms.ModelForm):
    class Meta:
        model = SupplyOrder
        fields = ['supplier', 'date', 'tons', 'price_per_ton', 'paid_amount']
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tons': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'price_per_ton': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'paid_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
