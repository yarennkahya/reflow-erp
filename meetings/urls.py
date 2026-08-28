from django.urls import path

from . import views


urlpatterns = [
    path('', views.calendar_view, name='meeting-calendar'),
    path('new/', views.meeting_create_view, name='meeting-create'),
    path('<int:pk>/', views.meeting_detail_view, name='meeting-detail'),
]
