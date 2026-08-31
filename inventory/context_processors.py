from .rbac import SIDEBAR_MODULES, user_can_access_module


def module_access_processor(request):
    """Sidebar'ın modülleri role göre aktif veya kilitli göstermesini sağlar."""
    user = request.user
    return {
        'module_access': {
            app_label: user_can_access_module(user, app_label)
            for app_label in SIDEBAR_MODULES
        }
    }
