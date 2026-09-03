from django.urls import path
from . import views

urlpatterns = [
    path('', views.order_list, name='purchasing-list'),
    path('orders/new/', views.order_create, name='purchase-order-create'),
    path('orders/<int:pk>/', views.order_detail_view, name='purchase-order-detail'),
    path('orders/<int:pk>/edit/', views.order_edit, name='purchase-order-edit'),
    path('orders/<int:pk>/advance/', views.order_advance, name='purchase-order-advance'),
    path('orders/<int:pk>/cancel/', views.order_cancel, name='purchase-order-cancel'),
    path('orders/<int:pk>/delete/', views.order_delete, name='purchase-order-delete'),
    path('orders/<int:pk>/items/new/', views.order_item_create, name='purchase-order-item-create'),
    path('orders/<int:pk>/items/<int:item_pk>/edit/', views.order_item_edit, name='purchase-order-item-edit'),
    path('orders/<int:pk>/items/<int:item_pk>/delete/', views.order_item_delete, name='purchase-order-item-delete'),
    path('orders/<int:pk>/items/<int:item_pk>/receive/', views.order_item_receive, name='purchase-order-item-receive'),
    path('suppliers/', views.supplier_list_view, name='supplier-list'),
    path('suppliers/new/', views.supplier_create, name='supplier-create'),
    path('suppliers/<int:pk>/', views.supplier_detail, name='supplier-detail'),
    path('suppliers/<int:pk>/edit/', views.supplier_edit, name='supplier-edit'),
    path('suppliers/<int:pk>/activity/', views.supplier_activity, name='supplier-activity'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier-delete'),
    path('suppliers/<int:pk>/products/new/', views.supplier_product_create, name='supplier-product-create'),
    path('suppliers/<int:pk>/products/<int:product_pk>/edit/', views.supplier_product_edit, name='supplier-product-edit'),
    path('suppliers/<int:pk>/products/<int:product_pk>/delete/', views.supplier_product_delete, name='supplier-product-delete'),
    path('orders/<int:pk>/set-status/', views.purchase_order_set_status_view,
         name='purchase-order-set-status'),
]
