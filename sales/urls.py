from django.urls import path
from . import views

urlpatterns = [
    path('', views.order_list, name='sales-list'),
    path('orders/<int:pk>/', views.order_detail_view, name='order-detail'),
    path('customers/', views.customer_list_view, name='customer-list'),
    path('customers/<int:pk>/', views.customer_detail_view, name='customer-detail'),
]
