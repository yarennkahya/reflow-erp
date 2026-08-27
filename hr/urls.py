from django.urls import path
from . import views

urlpatterns = [
    path('', views.hr_list, name='hr-list'),
    path('employees/', views.employee_list_view, name='hr-employees'),
    path('employees/<int:pk>/', views.employee_detail_view, name='hr-employee-detail'),
    path('leave/', views.leave_list_view, name='hr-leave'),
    path('recruitment/', views.recruitment_view, name='hr-recruitment'),
]
