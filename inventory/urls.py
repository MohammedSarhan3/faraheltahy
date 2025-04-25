from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('supply-orders/manage/', views.supply_orders_management, name='supply_orders_management'),
    path('supply-orders/manage/<int:supply_order_id>/', views.supply_orders_management, name='supply_orders_management'),
    path('safebox/', views.safebox_management, name='safebox_management'),
    path('inventory/', views.inventory_status, name='inventory_status'),
]
