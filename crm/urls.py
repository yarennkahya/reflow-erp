from django.urls import path
from . import views

urlpatterns = [
    path('', views.opportunity_list, name='crm-list'),
]
