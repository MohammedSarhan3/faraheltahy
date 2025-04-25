from django.urls import path
from . import views

app_name = 'invoices'

urlpatterns = [
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('customers/add/', views.add_customer, name='add_customer'),
    path('customers/<int:pk>/delete/', views.delete_customer, name='delete_customer'),
    path('customers/<int:pk>/invoices/<int:invoice_id>/', views.CustomerDetailView.as_view(), name='edit_invoice'),
]
