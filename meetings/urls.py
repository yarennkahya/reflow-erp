from django.urls import path

from . import views


urlpatterns = [
    path('', views.calendar_view, name='meeting-calendar'),
    path('new/', views.meeting_create_view, name='meeting-create'),
    path('<int:pk>/edit/', views.meeting_edit_view, name='meeting-edit'),
    path('<int:pk>/cancel/', views.meeting_cancel_view, name='meeting-cancel'),
    path('<int:pk>/', views.meeting_detail_view, name='meeting-detail'),
]
