from django.urls import path
from . import views

urlpatterns = [
    path('', views.report_view, name='finance-report'),
    path('invoices/', views.invoice_list_view, name='invoice-list'),
    path('invoices/create/<int:order_pk>/', views.invoice_create_view, name='invoice-create'),
    path('invoices/<int:pk>/', views.invoice_detail_view, name='invoice-detail'),
]
