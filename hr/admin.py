from django.contrib import admin

from .models import (
    Application,
    Candidate,
    Department,
    Employee,
    JobOpening,
    LeaveRequest,
    LeaveType,
    Position,
)
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('title', 'department')
    list_filter = ('department',)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'position', 'manager', 'employment_status', 'hire_date')
    list_filter = ('employment_status', 'department')
    search_fields = ('name', 'email')


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'annual_allowance_days')


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('employee', 'leave_type', 'start_date', 'end_date', 'status', 'approved_by')
    list_filter = ('status', 'leave_type')
    ordering = ('-requested_at',)



@admin.register(JobOpening)
class JobOpeningAdmin(admin.ModelAdmin):
    list_display = ('title', 'department', 'position', 'status', 'opened_at')
    list_filter = ('status', 'department')


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone')
    search_fields = ('name', 'email')


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'job_opening', 'stage', 'applied_at', 'updated_at')
    list_filter = ('stage', 'job_opening')
    ordering = ('-updated_at',)