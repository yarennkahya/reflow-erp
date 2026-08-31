from django.contrib.auth.decorators import login_required
from django.urls import path

from . import views

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('dashboard/', login_required(views.dashboard_view), name='dashboard-home'),
    path('chat/', login_required(views.chat_page_view), name='chat-page'),
    path('profile/', views.account_settings_view, name='account-settings'),
]
