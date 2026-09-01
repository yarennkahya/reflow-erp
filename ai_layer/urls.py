from django.urls import path

from . import views

urlpatterns = [
    path('chat/', views.chat_view, name='ai-chat'),
    path('upload/', views.file_upload_view, name='ai-upload'),
]