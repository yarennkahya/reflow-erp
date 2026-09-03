from django.urls import path
from . import views

urlpatterns = [
    path('', views.report_view, name='finance-report'),
    path('invoices/', views.invoice_list_view, name='invoice-list'),
    path('invoices/create/<int:order_pk>/', views.invoice_create_view, name='invoice-create'),
    path('invoices/<int:pk>/', views.invoice_detail_view, name='invoice-detail'),
    path('invoices/<int:pk>/preview/', views.invoice_preview_view,
         name='invoice-preview'),
    path('invoices/<int:pk>/pdf/', views.invoice_pdf_view,
         name='invoice-pdf'),
    path('invoices/<int:pk>/send/', views.invoice_send_view,
         name='invoice-send'),
]
