from django.urls import path
from . import views

urlpatterns = [
    path('', views.hr_list, name='hr-list'),
]
