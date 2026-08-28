from django.urls import path

from . import views


urlpatterns = [
    path('', views.notification_list_view, name='notification-list'),
    path('feed/', views.notification_feed_view, name='notification-feed'),
    path('<int:pk>/read/', views.notification_read_view, name='notification-read'),
]
