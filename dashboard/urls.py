from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard-home'),
    path('chat/', views.chat_page_view, name='chat-page'),
]