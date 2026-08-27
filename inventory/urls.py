from django.urls import path
from . import views

urlpatterns = [
    path('', views.lot_list, name='inventory-list'),
    path('lots/<int:pk>/', views.lot_detail, name='lot-detail'),
    path('warehouses/', views.warehouse_list, name='warehouse-list'),
    path('warehouses/new/', views.warehouse_create, name='warehouse-create'),
    path('warehouses/<int:pk>/', views.warehouse_detail, name='warehouse-detail'),
    path('warehouses/<int:pk>/edit/', views.warehouse_edit, name='warehouse-edit'),
    path('warehouses/<int:pk>/activity/', views.warehouse_activity, name='warehouse-activity'),
    path('warehouses/<int:pk>/delete/', views.warehouse_delete, name='warehouse-delete'),
]
