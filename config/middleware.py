from django.contrib import messages
from django.shortcuts import redirect

from inventory.rbac import module_for_path, user_can_access_module


class ModuleAccessMiddleware:
    """Rolün atanmadığı modüllere doğrudan URL erişimini engeller."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        module = module_for_path(request.path_info)
        if (
            module
            and request.user.is_authenticated
            and not user_can_access_module(request.user, module)
        ):
            messages.error(request, 'Bu modüle erişim izniniz yok.')
            return redirect('dashboard-home')
        return self.get_response(request)
