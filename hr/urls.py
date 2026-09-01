from django.urls import path
from . import views

urlpatterns = [
    path('', views.hr_list, name='hr-list'),
    path('employees/', views.employee_list_view, name='hr-employees'),
    path('employees/new/', views.employee_create_view, name='employee-create'),
    path('employees/<int:pk>/', views.employee_detail_view, name='hr-employee-detail'),
    path('employees/<int:pk>/edit/', views.employee_edit_view, name='employee-edit'),
    path('leave/', views.leave_list_view, name='hr-leave'),
    path('leave/new/', views.leave_request_create_view, name='leave-request-create'),
    path('leave/<int:pk>/approve/', views.leave_approve_view, name='leave-approve'),
    path('leave/<int:pk>/reject/', views.leave_reject_view, name='leave-reject'),
    path('recruitment/', views.recruitment_view, name='hr-recruitment'),
    path('recruitment/openings/new/', views.job_opening_create_view, name='job-opening-create'),
    path('recruitment/candidates/new/', views.candidate_create_view, name='candidate-create'),
    path('recruitment/applications/new/', views.application_create_view, name='application-create'),
    path('recruitment/applications/<int:pk>/advance/',
         views.application_advance_view, name='application-advance'),
    path('recruitment/applications/<int:pk>/reject/',
         views.application_reject_view, name='application-reject'),
    path('recruitment/applications/<int:pk>/set-stage/', views.application_set_stage_view,
         name='application-set-stage'),
    path('employees/<int:pk>/set-status/', views.employee_set_status_view,
         name='employee-set-status'),
]
