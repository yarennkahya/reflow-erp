from django.urls import path
from . import views

urlpatterns = [
    path('', views.batch_list, name='production-list'),
    path('recipes/', views.recipe_list_view, name='production-recipes'),
    path('recipes/create/', views.recipe_create_view, name='production-recipe-create'),
    path('batches/<int:pk>/', views.batch_detail_view, name='production-batch-detail'),
    path('batches/create/', views.batch_create_view, name='production-batch-create'),
]
