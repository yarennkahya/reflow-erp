from django.urls import path
from . import views

urlpatterns = [
    path('', views.hr_list, name='hr-list'),
    path('employees/', views.employee_list_view, name='hr-employees'),
    path('employees/<int:pk>/', views.employee_detail_view, name='hr-employee-detail'),
    path('leave/', views.leave_list_view, name='hr-leave'),
    path('leave/new/', views.leave_request_create_view, name='leave-request-create'),
    path('leave/<int:pk>/approve/', views.leave_approve_view, name='leave-approve'),
    path('leave/<int:pk>/reject/', views.leave_reject_view, name='leave-reject'),
    path('recruitment/', views.recruitment_view, name='hr-recruitment'),
    path('recruitment/candidates/new/', views.candidate_create_view, name='candidate-create'),
    path('recruitment/applications/new/', views.application_create_view, name='application-create'),
]
