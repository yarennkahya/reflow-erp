from django.urls import path

from . import views


urlpatterns = [
    path('', views.audit_list_view, name='audit-list'),
]
