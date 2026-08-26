from django.db import transaction

from .models import LeaveRequest


def _resolve_leave_request(leave_request, new_status, approved_by):
    if leave_request.status != LeaveRequest.Status.PENDING:
        raise ValueError(
            f'Leave request is not pending (current status: {leave_request.status}).'
        )
    with transaction.atomic():
        leave_request.status = new_status
        leave_request.approved_by = approved_by
        leave_request.save(update_fields=['status', 'approved_by'])
    return leave_request


def approve_leave_request(leave_request, approved_by):
    """Bekleyen bir izin talebini onaylar."""
    return _resolve_leave_request(leave_request, LeaveRequest.Status.APPROVED, approved_by)


def reject_leave_request(leave_request, approved_by):
    """Bekleyen bir izin talebini reddeder."""
    return _resolve_leave_request(leave_request, LeaveRequest.Status.REJECTED, approved_by)