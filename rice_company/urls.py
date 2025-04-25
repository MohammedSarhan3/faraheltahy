from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

def redirect_to_dashboard(request):
    return redirect('inventory:dashboard')

urlpatterns = [
    path('', login_required(redirect_to_dashboard), name='root'),
    path('inventory/', include(('inventory.urls', 'inventory'), namespace='inventory')),
    path('admin/', admin.site.urls),
    path('invoices/', include('invoices.urls', namespace='invoices')),
    path('accounts/', include('accounts.urls', namespace='accounts')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Add media files serving in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
