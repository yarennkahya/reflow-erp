from django.urls import path

from . import views

urlpatterns = [
    path('', views.customer_list, name='crm-list'),
    path('customers/new/', views.customer_create, name='crm-customer-create'),
    path('customers/<int:pk>/', views.customer_detail, name='crm-customer-detail'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='crm-customer-edit'),
    path('customers/<int:pk>/activity/', views.customer_activity, name='crm-customer-activity'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='crm-customer-delete'),
    path('sales/', views.sale_list, name='crm-sale-list'),
    path('sales/new/', views.sale_create, name='crm-sale-create'),
    path('sales/<int:pk>/edit/', views.sale_edit, name='crm-sale-edit'),
    path('sales/<int:pk>/delete/', views.sale_delete, name='crm-sale-delete'),
    path('sales/<int:pk>/advance/', views.opportunity_advance_view, name='opportunity-advance'),
    path('sales/<int:pk>/lose/', views.opportunity_lose_view, name='opportunity-lose'),
    path('sales/<int:pk>/activity/', views.sale_activity, name='crm-sale-activity'),
]
