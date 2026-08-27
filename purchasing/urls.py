from django.urls import path
from . import views

urlpatterns = [
   path('', views.order_list, name='purchasing-list'),
   path('orders/<int:pk>/', views.order_detail_view, name='purchase-order-detail'),
   path('suppliers/', views.supplier_list_view, name='supplier-list'),
]

