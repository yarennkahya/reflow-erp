from django.urls import path
from . import views

urlpatterns = [
    path('', views.batch_list, name='production-list'),
    path('recipes/', views.recipe_list_view, name='production-recipes'),
    path('batches/<int:pk>/', views.batch_detail_view, name='production-batch-detail'),
]
