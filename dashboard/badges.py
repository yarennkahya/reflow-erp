"""
Durum rozetlerinin TEK kaynağı.

Önceden rozet CSS sınıfı 4 ayrı view modülünde ~18 çağrı noktasında elle
hesaplanıyordu (purchasing.STATUS_CLASSES, sales._STATUS, hr._EMP_STATUS /
_LEAVE_STATUS / _APP_STAGE, inventory.FRESHNESS) ve iki farklı biçim üretiyordu.
Hepsi buraya indi.

Anahtar biçimi: '<app_label>.<Model>.<field>'
Değerler `.o-badge--<variant>` CSS sınıfına dönüşür.
"""
from django.utils.translation import gettext_lazy as _

SUCCESS = 'success'
WARNING = 'warning'
DANGER = 'danger'
INFO = 'info'
MUTED = 'muted'
PRIMARY = 'primary'

DEFAULT_VARIANT = MUTED

VARIANTS = {
    'purchasing.PurchaseOrder.status': {
        'draft': MUTED,
        'sent': INFO,
        'confirmed': PRIMARY,
        'partially_received': WARNING,
        'received': SUCCESS,
        'cancelled': DANGER,
    },
    'sales.Order.status': {
        'pending': WARNING,
        'fulfilled': SUCCESS,
        'cancelled': DANGER,
    },
    'sales.ReturnRequest.status': {
        'requested': WARNING,
        'completed': SUCCESS,
        'rejected': DANGER,
    },
    'sales.ReturnRequest.reason': {
        'customer_changed_mind': MUTED,
        'defective': DANGER,
    },
    'sales.Customer.customer_type': {
        'wholesale': PRIMARY,
        'retail': INFO,
    },
    'crm.Opportunity.stage': {
        'new': MUTED,
        'in_discussion': INFO,
        'proposal_sent': PRIMARY,
        'negotiation': WARNING,
        'won': SUCCESS,
        'lost': DANGER,
    },
    'crm.Opportunity.status': {
        'active': SUCCESS,
        'passive': MUTED,
        'won': SUCCESS,
        'lost': DANGER,
    },
    'hr.Employee.employment_status': {
        'active': SUCCESS,
        'on_leave': WARNING,
        'terminated': MUTED,
    },
    'hr.LeaveRequest.status': {
        'pending': WARNING,
        'approved': SUCCESS,
        'rejected': DANGER,
    },
    'hr.JobOpening.status': {
        'open': SUCCESS,
        'closed': MUTED,
        'filled': PRIMARY,
    },
    'hr.Application.stage': {
        'applied': MUTED,
        'screening': INFO,
        'interview': PRIMARY,
        'offer': WARNING,
        'hired': SUCCESS,
        'rejected': DANGER,
    },
    'finance.Invoice.status': {
        'unpaid': DANGER,
        'partially_paid': WARNING,
        'paid': SUCCESS,
    },
    'finance.Payment.method': {
        'cash': MUTED,
        'bank_transfer': INFO,
        'credit_card': PRIMARY,
    },
    'meetings.Meeting.status': {
        'scheduled': INFO,
        'completed': SUCCESS,
        'cancelled': DANGER,
    },
    'production.QualityCheck.result': {
        'pass': SUCCESS,
        'fail': DANGER,
    },
    'inventory.Business.business_type': {
        'supplier': PRIMARY,
        'wholesale_customer': INFO,
        'internal': MUTED,
    },
    # Hesaplanan sözde-alanlar (model choice'ı yok)
    'inventory.Lot.freshness': {
        'NORMAL': SUCCESS,
        'PRIORITY_SALE': WARNING,
        'WASTE': DANGER,
    },
    'common.is_active': {
        True: SUCCESS,
        False: MUTED,
    },
}

# Yalnızca model choice'ı olmayan sözde-alanlar için etiket sağlar.
LABELS = {
    'inventory.Lot.freshness': {
        'NORMAL': _('Normal'),
        'PRIORITY_SALE': _('Öncelikli kullanım'),
        'WASTE': _('SKT geçti'),
    },
    'common.is_active': {
        True: _('Aktif'),
        False: _('Pasif'),
    },
}


def key_for(obj, field_name):
    """Bir model örneği + alan adından noktalı anahtarı üretir."""
    meta = obj._meta
    return f'{meta.app_label}.{meta.object_name}.{field_name}'


def variant(key, value):
    """Anahtar + değer -> varyant adı. Bilinmeyen her şey DEFAULT_VARIANT."""
    return VARIANTS.get(key, {}).get(value, DEFAULT_VARIANT)


def label(key, value, fallback=None):
    """
    Sözde-alanlar için etiket. Gerçek model alanlarında çağıran taraf
    get_FIELD_display() kullanır; burası yalnızca LABELS'a bakar.
    """
    mapped = LABELS.get(key, {}).get(value)
    if mapped is not None:
        return mapped
    return fallback if fallback is not None else value
