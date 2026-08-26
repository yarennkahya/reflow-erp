from django.urls import path
from . import views

urlpatterns = [
    path('', views.lot_list, name='inventory-list'),
]
