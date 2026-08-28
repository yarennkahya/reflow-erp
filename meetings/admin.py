from django.contrib import admin

from .models import Meeting


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_time', 'organizer', 'status', 'customer')
    list_filter = ('status', 'organizer')
