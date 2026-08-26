from django.urls import path
from . import views

urlpatterns = [
    path('', views.batch_list, name='production-list'),
]
