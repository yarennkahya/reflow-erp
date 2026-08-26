from django.contrib import admin

from .models import Department, Employee, Position
from .models import Department, Employee, LeaveRequest, LeaveType, Position

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