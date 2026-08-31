"""Modül düzeyindeki rol erişimi için ortak yardımcılar."""

MODULE_PATHS = {
    'audit': 'audit',
    'crm': 'crm',
    'finance': 'finance',
    'hr': 'hr',
    'inventory': 'inventory',
    'meetings': 'meetings',
    'production': 'production',
    'purchasing': 'purchasing',
    'sales': 'sales',
}

SIDEBAR_MODULES = (
    'inventory',
    'purchasing',
    'production',
    'sales',
    'finance',
    'crm',
    'hr',
    'ai_layer',
    'meetings',
    'audit',
)

COMMON_MODULES = {'ai_layer'}


def user_can_access_module(user, app_label):
    """Ortak modüllere, süper kullanıcıya veya ilgili role erişim verir."""
    return bool(
        user.is_authenticated
        and (
            app_label in COMMON_MODULES
            or user.is_superuser
            or user.has_module_perms(app_label)
        )
    )


def module_for_path(path):
    """İstek yolunun bağlı olduğu uygulama etiketini döndürür."""
    normalized_path = path.lstrip('/')
    if normalized_path.startswith('api/ai/') or normalized_path.startswith('chat/'):
        return 'ai_layer'
    return MODULE_PATHS.get(normalized_path.split('/', 1)[0])
