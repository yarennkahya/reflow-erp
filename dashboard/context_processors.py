"""
App bar, apps overlay ve breadcrumb'ı besleyen tek context processor.

inventory.context_processors.module_access_processor'ın yerini alır; geçiş
boyunca dönüştürülmemiş şablonlar çalışmaya devam etsin diye `module_access`
anahtarını da yaymaya devam eder.
"""
from django.conf import settings
from django.urls import NoReverseMatch, reverse

from inventory.rbac import user_can_access_module

from .navigation import APPS, app_by_key, resolve


def _live_asset_version():
    if not settings.DEBUG:
        return settings.ASSET_VERSION
    from config.settings import asset_version
    return asset_version()


def _url(url_name):
    """
    reverse() ama patlamayan hali.

    Registry'deki tek bir yazım hatası aksi halde uygulamanın HER sayfasını
    500'e düşürürdü, çünkü bu processor her render'da çalışıyor.
    """
    try:
        return reverse(url_name)
    except NoReverseMatch:
        return '#'


def _allowed(user, app):
    """Boş app_label => herkese açık (ör. Kontrol Paneli)."""
    return not app.app_label or user_can_access_module(user, app.app_label)


def navigation(request):
    user = getattr(request, 'user', None)
    match = getattr(request, 'resolver_match', None)  # 404/500'de None olur
    app_key, menu_key = resolve(match.url_name if match else None)

    apps = [
        {
            'key': app.key,
            'label': app.label,
            'icon': app.icon,
            'color': app.color,
            'url': _url(app.root_url_name),
            'allowed': _allowed(user, app),
            'is_current': app.key == app_key,
        }
        for app in APPS
    ]

    current = app_by_key(app_key)
    menus = []
    if current and _allowed(user, current):
        menus = [
            {
                'key': menu.key,
                'label': menu.label,
                'section': menu.section,
                'url': _url(menu.url_name),
                'is_current': menu.key == menu_key,
            }
            for menu in current.menus
        ]

    return {
        'site_brand': settings.SITE_BRAND,
        'site_brand_short': settings.SITE_BRAND_SHORT,
        'site_brand_mark': settings.SITE_BRAND_MARK,
        'site_version': settings.SITE_VERSION,
        # DEBUG'ta taze hesapla: CSS düzenleyince yeniden başlatmadan görün.
        # django.conf.settings yalnızca BÜYÜK HARFLİ adları açar, bu yüzden
        # fonksiyonu doğrudan ayar modülünden alıyoruz.
        'asset_version': _live_asset_version(),
        'nav_apps': apps,
        'nav_current_app': (
            {'key': current.key, 'label': current.label, 'icon': current.icon}
            if current else None
        ),
        'nav_menus': menus,
        'nav_current_menu': next((m for m in menus if m['is_current']), None),
        # Geriye dönük uyumluluk: eski şablonlar hâlâ module_access.<app> okuyor.
        'module_access': {
            app.app_label: _allowed(user, app) for app in APPS if app.app_label
        },
    }
