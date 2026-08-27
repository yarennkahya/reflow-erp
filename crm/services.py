from .models import Opportunity

STAGE_ORDER = [
    Opportunity.Stage.NEW,
    Opportunity.Stage.IN_DISCUSSION,
    Opportunity.Stage.PROPOSAL_SENT,
    Opportunity.Stage.NEGOTIATION,
    Opportunity.Stage.WON,
]


def advance_stage(opportunity):
    """Aktif bir satış kaydını bir sonraki satış aşamasına taşır."""
    if opportunity.status != Opportunity.Status.ACTIVE:
        raise ValueError('Yalnızca aktif satışlar ilerletilebilir.')
    if opportunity.stage not in STAGE_ORDER:
        raise ValueError('Bu satış kaydı zaten kapanmış, ilerletilemez.')
    current_index = STAGE_ORDER.index(opportunity.stage)
    if current_index == len(STAGE_ORDER) - 1:
        raise ValueError('Bu satış kaydı zaten kazanıldı.')
    opportunity.stage = STAGE_ORDER[current_index + 1]
    if opportunity.stage == Opportunity.Stage.WON:
        opportunity.status = Opportunity.Status.WON
    opportunity.save(update_fields=['stage', 'status', 'updated_at'])
    return opportunity


def mark_as_lost(opportunity):
    """Açık bir satış kaydını kaybedildi olarak kapatır."""
    if not opportunity.is_open:
        raise ValueError('Bu satış kaydı zaten kapanmış.')
    opportunity.stage = Opportunity.Stage.LOST
    opportunity.status = Opportunity.Status.LOST
    opportunity.save(update_fields=['stage', 'status', 'updated_at'])
    return opportunity


def set_sale_activity(opportunity, status):
    """Açık satış kaydını aktif veya pasif duruma alır."""
    allowed_statuses = (Opportunity.Status.ACTIVE, Opportunity.Status.PASSIVE)
    if status not in allowed_statuses:
        raise ValueError('Geçersiz satış durumu.')
    if not opportunity.is_open:
        raise ValueError('Kapanmış bir satış kaydının durumu değiştirilemez.')
    opportunity.status = status
    opportunity.save(update_fields=['status', 'updated_at'])
    return opportunity
