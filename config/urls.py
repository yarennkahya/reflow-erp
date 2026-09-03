"""URL configuration for config project."""
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
    path('api/ai/', include('ai_layer.urls')),
    path('inventory/', include('inventory.urls')),
    path('purchasing/', include('purchasing.urls')),
    path('production/', include('production.urls')),
    path('sales/', include('sales.urls')),
    path('crm/', include('crm.urls')),
    path('hr/', include('hr.urls')),
    path('finance/', include('finance.urls')),
    path('audit/', include('audit.urls')),
    path('notifications/', include('notifications.urls')),
    path('meetings/', include('meetings.urls')),
    path('', include('dashboard.urls')),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
