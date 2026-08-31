from django.urls import path
from . import views

urlpatterns = [
    path('', views.order_list, name='sales-list'),
    path('returns/', views.return_list_view, name='return-list'),
    path('returns/<int:pk>/approve/', views.return_approve_view, name='return-approve'),
    path('returns/<int:pk>/reject/', views.return_reject_view, name='return-reject'),
    path('order-items/<int:item_pk>/return/', views.return_request_create_view, name='return-request-create'),
    path('orders/new/', views.order_create_view, name='order-create'),
    path('orders/<int:pk>/', views.order_detail_view, name='order-detail'),
    path('customers/', views.customer_list_view, name='customer-list'),
    path('customers/<int:pk>/', views.customer_detail_view, name='customer-detail'),
    path('forecast/', views.forecast_view, name='sales-forecast'),
]
