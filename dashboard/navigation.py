"""
Uygulama / menü kayıt defteri.

base.html'deki 29 adet boş `{% block nav_* %}` slotunun yerini alır. Her rota
(url_name) tek bir menü öğesine bağlanır; böylece detay ve form sayfaları da
bağlı oldukları ana menüyü aktif gösterir.

Erişim kontrolü burada DEĞİL, inventory/rbac.py'de yaşar. Bu modül oradan
okur, tersi asla olmaz (döngüsel import olmasın diye).
"""
from dataclasses import dataclass, field
from functools import lru_cache

from django.utils.translation import gettext_lazy as _


@dataclass(frozen=True)
class MenuItem:
    """App bar'daki tek bir menü sekmesi."""

    key: str
    label: str
    url_name: str
    routes: tuple = ()   # bu sekmeyi aktif gösterecek TÜM url_name'ler
    section: str = ''    # menü içi gruplama başlığı (opsiyonel)


@dataclass(frozen=True)
class AppDef:
    """Apps overlay'deki tek bir uygulama."""

    key: str
    app_label: str       # izin app_label'ı; boş string => herkese açık
    label: str
    icon: str            # bootstrap-icons sınıfı
    color: str           # tile rengi için CSS değişkeni adı
    root_url_name: str
    menus: tuple = ()


APPS = (
    AppDef(
        'dashboard', '', _('Kontrol Paneli'), 'bi-grid-1x2-fill',
        '--o-primary', 'dashboard-home',
        menus=(
            MenuItem('dashboard.home', _('Genel Bakış'), 'dashboard-home',
                     ('dashboard-home',)),
            MenuItem('dashboard.notifications', _('Bildirimler'), 'notification-list',
                     ('notification-list',)),
            MenuItem('dashboard.profile', _('Hesap Ayarları'), 'account-settings',
                     ('account-settings',)),
        ),
    ),
    AppDef(
        'inventory', 'inventory', _('Stok'), 'bi-boxes',
        '--o-accent', 'inventory-list',
        menus=(
            MenuItem('inventory.lots', _('Stoklar'), 'inventory-list',
                     ('inventory-list', 'lot-detail')),
            MenuItem('inventory.warehouses', _('Depolar'), 'warehouse-list',
                     ('warehouse-list', 'warehouse-create', 'warehouse-detail',
                      'warehouse-edit', 'warehouse-activity', 'warehouse-delete')),
        ),
    ),
    AppDef(
        'purchasing', 'purchasing', _('Satın Alma'), 'bi-basket3',
        '--o-warning', 'purchasing-list',
        menus=(
            MenuItem('purchasing.orders', _('Siparişler'), 'purchasing-list',
                     ('purchasing-list', 'purchase-order-create', 'purchase-order-detail',
                      'purchase-order-edit', 'purchase-order-advance',
                      'purchase-order-cancel', 'purchase-order-delete',
                      'purchase-order-item-create', 'purchase-order-item-edit',
                      'purchase-order-item-delete', 'purchase-order-item-receive',
                      'purchase-order-set-status')),
            MenuItem('purchasing.suppliers', _('Tedarikçiler'), 'supplier-list',
                     ('supplier-list', 'supplier-create', 'supplier-detail',
                      'supplier-edit', 'supplier-activity', 'supplier-delete',
                      'supplier-product-create', 'supplier-product-edit',
                      'supplier-product-delete')),
        ),
    ),
    AppDef(
        # bi-fire tamamen dolu bir gliftir; ince çizgili diğer ikonların yanında
        # tek başına ağır durur. bi-gear "Hesap Ayarları"nda, bi-cup-hot ise
        # parti detayında "Çıktı ürünü" alanında kullanılıyor — ikisi de
        # çakışırdı. Termometre kavurmanın tanımlayıcı değişkenini anlatır.
        'production', 'production', _('Üretim'), 'bi-thermometer-high',
        '--o-danger', 'production-list',
        menus=(
            MenuItem('production.batches', _('Üretim Emirleri'), 'production-list',
                     ('production-list', 'production-batch-create',
                      'production-batch-detail')),
            MenuItem('production.recipes', _('Reçeteler'), 'production-recipes',
                     ('production-recipes', 'production-recipe-create')),
        ),
    ),
    AppDef(
        'sales', 'sales', _('Satış'), 'bi-cart3',
        '--o-success', 'sales-list',
        menus=(
            MenuItem('sales.orders', _('Siparişler'), 'sales-list',
                     ('sales-list', 'order-create', 'order-detail',
                      'order-set-status')),
            MenuItem('sales.customers', _('Müşteriler'), 'customer-list',
                     ('customer-list', 'customer-create',
                      'customer-detail', 'customer-edit')),
            MenuItem('sales.returns', _('İadeler'), 'return-list',
                     ('return-list', 'return-approve', 'return-reject',
                      'return-request-create')),
            MenuItem('sales.forecast', _('Talep Tahmini'), 'sales-forecast',
                     ('sales-forecast',), section=_('Raporlama')),
        ),
    ),
    AppDef(
        'crm', 'crm', _('CRM'), 'bi-building',
        '--o-info', 'crm-sale-list',
        menus=(
            MenuItem('crm.pipeline', _('Satış Takibi'), 'crm-sale-list',
                     ('crm-sale-list', 'crm-sale-create', 'crm-sale-edit',
                      'crm-sale-delete', 'opportunity-create', 'opportunity-advance',
                      'opportunity-lose', 'crm-sale-activity',
                      'opportunity-set-stage')),
            MenuItem('crm.customers', _('Müşteriler'), 'crm-list',
                     ('crm-list', 'crm-customer-create', 'crm-customer-detail',
                      'crm-customer-edit', 'crm-customer-activity',
                      'crm-customer-delete')),
        ),
    ),
    AppDef(
        'finance', 'finance', _('Finans'), 'bi-graph-up-arrow',
        '--o-success', 'finance-report',
        menus=(
            MenuItem('finance.invoices', _('Faturalar'), 'invoice-list',
                     ('invoice-list', 'invoice-detail', 'invoice-create',
                      'invoice-preview', 'invoice-pdf', 'invoice-send')),
            MenuItem('finance.report', _('Kârlılık Raporu'), 'finance-report',
                     ('finance-report',), section=_('Raporlama')),
        ),
    ),
    AppDef(
        'hr', 'hr', _('İnsan Kaynakları'), 'bi-people',
        '--o-accent', 'hr-employees',
        menus=(
            MenuItem('hr.overview', _('Genel Bakış'), 'hr-list', ('hr-list',)),
            MenuItem('hr.employees', _('Çalışanlar'), 'hr-employees',
                     ('hr-employees', 'hr-employee-detail', 'employee-set-status',
                      'employee-create', 'employee-edit')),
            MenuItem('hr.leave', _('İzinler'), 'hr-leave',
                     ('hr-leave', 'leave-request-create', 'leave-approve',
                      'leave-reject')),
            MenuItem('hr.recruitment', _('İşe Alım'), 'hr-recruitment',
                     ('hr-recruitment', 'job-opening-create', 'candidate-create',
                      'hr-candidates', 'hr-candidate-detail', 'candidate-doc-upload',
                      'application-create', 'application-advance',
                      'application-reject', 'application-set-stage')),
        ),
    ),
    AppDef(
        # bi-calendar3'ün nokta matrisi ve bi-robot'un dolu vizörü, diğer ince
        # çizgili ikonların yanında görsel olarak çok ağır duruyordu.
        'meetings', 'meetings', _('Takvim'), 'bi-calendar-event',
        '--o-info', 'meeting-calendar',
        menus=(
            MenuItem('meetings.calendar', _('Takvim'), 'meeting-calendar',
                     ('meeting-calendar', 'meeting-create', 'meeting-detail',
                      'meeting-edit', 'meeting-cancel', 'meeting-check-conflicts')),
        ),
    ),
    AppDef(
        'ai_layer', 'ai_layer', _('AI Asistan'), 'bi-chat-square-dots',
        '--o-primary', 'chat-page',
        menus=(
            MenuItem('ai.chat', _('Sohbet'), 'chat-page',
                     ('chat-page', 'chat-page-conversation', 'ai-chat')),
        ),
    ),
    AppDef(
        'audit', 'audit', _('Denetim Kaydı'), 'bi-clock-history',
        '--o-text-muted', 'audit-list',
        menus=(
            MenuItem('audit.log', _('Kayıtlar'), 'audit-list', ('audit-list',)),
        ),
    ),
)


@lru_cache(maxsize=1)
def _route_index():
    """url_name -> (app_key, menu_key). Süreç başına bir kez kurulur."""
    return {
        route: (app.key, menu.key)
        for app in APPS
        for menu in app.menus
        for route in menu.routes
    }


def resolve(url_name):
    """Bir url_name'i (app_key, menu_key) çiftine çözer; bulunamazsa (None, None)."""
    if not url_name:
        return (None, None)
    return _route_index().get(url_name, (None, None))


def app_by_key(key):
    return next((app for app in APPS if app.key == key), None)
