"""
Odoo tarzı arayüz bileşen kütüphanesi.

settings.py'de TEMPLATES['OPTIONS']['builtins'] olarak kayıtlı; bu yüzden
hiçbir şablonda {% load ui %} gerekmez.

DİKKAT: burası her şablon render'ında yüklenir. Modül seviyesinde ağır import
veya veritabanı erişimi YAPMA.
"""
from decimal import Decimal, InvalidOperation

from django import forms, template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from dashboard import badges

register = template.Library()


# ─────────────────────────────────────────────────────────────
#  Biçimlendirme filtreleri
# ─────────────────────────────────────────────────────────────

@register.filter
def money(value, symbol='₺'):
    """1234.5 -> ₺1.234,50 (Türkçe binlik/ondalık ayracı)."""
    if value in (None, ''):
        return '—'
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return value
    sign = '-' if amount < 0 else ''
    whole, _sep, frac = f'{abs(amount):.2f}'.partition('.')
    grouped = f'{int(whole):,}'.replace(',', '.')
    return f'{sign}{symbol}{grouped},{frac}'


@register.filter
def qty(value, unit=''):
    """Gereksiz sıfırları atar: 12.500 -> 12,5 · 3.000 -> 3"""
    if value in (None, ''):
        return '—'
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return value
    normalized = amount.normalize()
    if normalized == normalized.to_integral_value():
        text = str(normalized.quantize(Decimal(1)))
    else:
        text = format(normalized, 'f').rstrip('0').rstrip('.')
    text = text.replace('.', ',')
    return f'{text} {unit}'.strip()


# ─────────────────────────────────────────────────────────────
#  Form alanları
# ─────────────────────────────────────────────────────────────

_WIDGET_CLASS = (
    (forms.CheckboxInput, 'o-check'),
    (forms.RadioSelect, 'o-radio'),
    (forms.SelectMultiple, 'o-select o-select--multi'),
    (forms.Select, 'o-select'),
    (forms.Textarea, 'o-textarea'),
    (forms.FileInput, 'o-file'),
)


def _control_class(widget):
    for widget_type, css in _WIDGET_CLASS:
        if isinstance(widget, widget_type):
            return css
    return 'o-input'


@register.inclusion_tag('ui/_field.html')
def ui_field(field, label=None, help=None, placeholder=None,
             required=None, cols=6, readonly=False):
    """
    Etiket + kontrol + hata üçlüsü. Projedeki ~60 elle yazılmış tekrarın yerine.

    class'ı MERGE etmez, DEĞİŞTİRİR — bu yüzden forms.py'lerdeki
    setdefault('class', 'form-control') döngüleri ölü koda dönüşür.
    """
    if field is None:
        return {'field': None}

    widget = field.field.widget
    css = _control_class(widget)
    if field.errors:
        css += ' o-invalid'

    attrs = {'class': css}
    if placeholder:
        attrs['placeholder'] = placeholder
    if readonly:
        attrs['readonly'] = 'readonly'

    return {
        'field': field,
        'control': field.as_widget(attrs=attrs),
        'label': label if label is not None else field.label,
        'help': help if help is not None else field.help_text,
        'required': field.field.required if required is None else required,
        'cols': cols,
        'is_check': isinstance(widget, forms.CheckboxInput),
    }


@register.inclusion_tag('ui/_field_value.html')
def ui_field_value(label, value, url=None, mono=False, icon=None, cols=6):
    """Form sheet'te salt okunur alan satırı."""
    return {'label': label, 'value': value, 'url': url,
            'mono': mono, 'icon': icon, 'cols': cols}


# ─────────────────────────────────────────────────────────────
#  Durum rozetleri
# ─────────────────────────────────────────────────────────────

@register.inclusion_tag('ui/_badge.html')
def ui_badge(obj, field_name, size=''):
    """
    {% ui_badge order "status" %}

    Anahtarı obj._meta'dan, etiketi get_FIELD_display()'den türetir.
    Uygulamadaki her durum rozetinin tek çağrı noktası.
    """
    if obj is None:
        return {'label': None}
    value = getattr(obj, field_name, None)
    key = badges.key_for(obj, field_name)

    display = getattr(obj, f'get_{field_name}_display', None)
    if callable(display):
        label = display()
    else:
        # is_active gibi choice'ı olmayan alanlar ortak haritaya düşer
        key = 'common.is_active' if field_name == 'is_active' else key
        label = badges.label(key, value, fallback=value)

    return {'label': label, 'variant': badges.variant(key, value), 'size': size}


@register.inclusion_tag('ui/_badge.html')
def ui_badge_raw(key, value, label=None, size=''):
    """Hesaplanan sözde-alanlar için: {% ui_badge_raw "inventory.Lot.freshness" row.freshness %}"""
    return {
        'label': badges.label(key, value, fallback=label if label is not None else value),
        'variant': badges.variant(key, value),
        'size': size,
    }


@register.inclusion_tag('ui/_avatar.html')
def ui_avatar(name, size='md', url=None):
    """
    Baş harf avatarı. Renk addan deterministik olarak türetilir ve palet içinde
    kalır (eski AVATAR_PALETTE'in neon renkleri yerine).
    """
    text = (name or '?').strip()
    initial = text[0].upper() if text else '?'
    hue = sum(ord(c) for c in text) % 360
    return {'initial': initial, 'hue': hue, 'size': size,
            'title': text, 'url': url}


# ─────────────────────────────────────────────────────────────
#  Boş durum / istatistik / onay
# ─────────────────────────────────────────────────────────────

@register.inclusion_tag('ui/_empty.html')
def ui_empty(icon='bi-inbox', title=None, text=None,
             action_url=None, action_label=None, colspan=None):
    return {'icon': icon, 'title': title or _('Gösterilecek kayıt yok'),
            'text': text, 'action_url': action_url,
            'action_label': action_label, 'colspan': colspan}


@register.inclusion_tag('ui/_stat_button.html')
def ui_stat(value, label, icon=None, url=None, variant=''):
    """Odoo form görünümündeki 'button box' kutucuğu."""
    return {'value': value, 'label': label, 'icon': icon,
            'url': url, 'variant': variant}


@register.inclusion_tag('ui/_confirm_button.html', takes_context=True)
def ui_confirm(context, url, label, message, icon=None,
               variant='danger', name=None, value=None):
    """
    Yıkıcı aksiyon. Gerçek bir POST formu basar — AJAX DEĞİL.

    Silme view'larının bir kısmı ProtectedError yakalayıp messages.error
    basıyor; AJAX çağrısı o mesajı yutardı.
    """
    return {'url': url, 'label': label, 'message': message, 'icon': icon,
            'variant': variant, 'name': name, 'value': value,
            'csrf_token': context.get('csrf_token')}


# ─────────────────────────────────────────────────────────────
#  Control panel parçaları
# ─────────────────────────────────────────────────────────────

@register.inclusion_tag('ui/_breadcrumb.html', takes_context=True)
def ui_breadcrumb(context, record=None, parent=None, parent_url=None):
    """Odoo kırıntısı: Modül / Menü / Kayıt — registry'den türer."""
    return {
        'app': context.get('nav_current_app'),
        'menu': context.get('nav_current_menu'),
        'parent': parent, 'parent_url': parent_url,
        'record': record,
    }


@register.inclusion_tag('ui/_pager.html', takes_context=True)
def ui_pager(context, page_obj=None):
    """page_obj yoksa hiçbir şey basmaz — sayfalanmamış listeler bozulmasın."""
    page_obj = page_obj if page_obj is not None else context.get('page_obj')
    if page_obj is None:
        return {'page_obj': None}
    request = context.get('request')
    base_qs = ''
    if request is not None:
        params = request.GET.copy()
        params.pop('page', None)
        base_qs = params.urlencode()
    return {'page_obj': page_obj, 'base_qs': base_qs}


@register.inclusion_tag('ui/_view_switcher.html', takes_context=True)
def ui_view_switcher(context, views, current='list'):
    """{% ui_view_switcher "list,kanban,graph" current=view %}"""
    known = {
        'list':     ('bi-list-ul',     _('Liste')),
        'kanban':   ('bi-kanban',      _('Kanban')),
        'calendar': ('bi-calendar3',   _('Takvim')),
        'graph':    ('bi-bar-chart',   _('Grafik')),
    }
    request = context.get('request')
    params = request.GET.copy() if request else None
    if params is not None:
        params.pop('view', None)
        params.pop('page', None)
    base = params.urlencode() if params else ''

    items = []
    for name in [v.strip() for v in views.split(',') if v.strip()]:
        icon, title = known.get(name, ('bi-square', name))
        query = f'{base}&view={name}' if base else f'view={name}'
        items.append({'name': name, 'icon': icon, 'title': title,
                      'url': f'?{query}', 'is_current': name == current})
    return {'items': items}


@register.inclusion_tag('ui/_searchbar.html', takes_context=True)
def ui_search(context, target=None, placeholder=None, param='q',
              filters=None, filter_param='status', selected='all',
              groupby=None, groupby_param='groupby', groupby_selected=''):
    """
    Odoo arama çubuğu: facet'ler + Filtreler/Grupla/Favoriler panelleri.

    Paneldeki radio'lar mevcut data-ajax-autosubmit change handler'ına takılır,
    yani SIFIR yeni AJAX kodu gerekir.
    """
    request = context.get('request')
    query = request.GET.get(param, '') if request else ''

    facets = []
    if query:
        facets.append({'label': _('Ara'), 'value': query, 'param': param})

    filter_choices = list(filters or [])
    if filter_choices and selected not in ('all', '', None):
        match = dict(filter_choices).get(selected)
        if match is not None:
            facets.append({'label': _('Filtre'), 'value': match,
                           'param': filter_param})

    groupby_choices = list(groupby or [])
    if groupby_choices and groupby_selected:
        match = dict(groupby_choices).get(groupby_selected)
        if match is not None:
            facets.append({'label': _('Grupla'), 'value': match,
                           'param': groupby_param})

    # Aktif diğer parametreler formda korunmalı, yoksa filtrelerken kaybolurlar.
    keep = {param, filter_param, groupby_param, 'view', 'page'}
    hidden = []
    if request is not None:
        for key, value in request.GET.items():
            if key not in keep:
                hidden.append({'name': key, 'value': value})

    return {
        'target': target, 'placeholder': placeholder or _('Ara…'),
        'param': param, 'query': query, 'facets': facets,
        'filters': filter_choices, 'filter_param': filter_param,
        'selected': selected,
        'groupby': groupby_choices, 'groupby_param': groupby_param,
        'groupby_selected': groupby_selected,
        'hidden': hidden,
    }


@register.simple_tag
def ui_kanban_url(url_name):
    """
    Kanban sürükle-bırak hedefi için `__pk__` yer tutuculu URL üretir.

    JS kartı bırakırken __pk__ yerine kaydın id'sini koyar. Sentinel olarak
    gerçekçi olmayan bir pk kullanıp geri değiştiriyoruz; böylece URL deseni
    JS'te elle kurulmuyor, Django'nun reverse'ünden geliyor.
    """
    from django.urls import NoReverseMatch, reverse
    sentinel = 987654321
    try:
        return reverse(url_name, args=[sentinel]).replace(str(sentinel), '__pk__')
    except NoReverseMatch:
        return ''


@register.inclusion_tag('ui/_statusbar.html')
def ui_statusbar(obj, field_name, hide='', choices=None):
    """
    Odoo statusbar: aşamalar soldan sağa, geçilenler soluk, mevcut vurgulu.

    `hide` ile verilen değerler (ör. 'cancelled') yalnızca AKTİF durumken
    görünür — Odoo'nun davranışı budur.
    """
    if obj is None:
        return {'steps': []}
    value = getattr(obj, field_name, None)
    if choices is None:
        field = obj._meta.get_field(field_name)
        choices = list(field.choices or [])
    else:
        choices = list(choices)

    hidden = {h.strip() for h in str(hide).split(',') if h.strip()}
    visible = [(v, l) for v, l in choices if v not in hidden or v == value]

    order = [v for v, _l in visible]
    current_index = order.index(value) if value in order else -1

    steps = []
    for index, (step_value, step_label) in enumerate(visible):
        steps.append({
            'value': step_value,
            'label': step_label,
            'is_current': step_value == value,
            'is_done': current_index >= 0 and index < current_index,
        })
    return {'steps': steps, 'key': badges.key_for(obj, field_name),
            'value': value}


@register.inclusion_tag('ui/_graph.html')
def ui_graph(chart_id, data, type='bar', height=280, title=None):
    """
    <canvas> + JSON veri adacığı basar. Chart.js'i o-charts.js kurar ve
    renkleri CSS token'larından okur, böylece tema değişince yeniden çizer.
    """
    import json as _json
    return {'chart_id': chart_id, 'type': type, 'height': height,
            'title': title, 'payload': mark_safe(_json.dumps(data))}


# ─────────────────────────────────────────────────────────────
#  Chatter (salt okunur aktivite akışı)
# ─────────────────────────────────────────────────────────────

@register.simple_tag
def ui_chatter(obj, related=None, limit=30):
    """
    AuditLog'dan beslenen salt okunur kayıt geçmişi.

    DİKKAT: log'lar çoğu zaman ALT kayda bağlı (satın alma siparişinde
    GoodsReceipt'e, faturada Payment'a). Bu yüzden `related` ile ilişkili
    nesneler de sorguya katılır, aksi halde panel boş görünür.
    """
    from django.contrib.contenttypes.models import ContentType
    from django.db.models import Q

    from audit.models import AuditLog

    targets = [obj] + [o for o in (related or []) if o is not None]
    query = Q()
    for target in targets:
        query |= Q(content_type=ContentType.objects.get_for_model(target),
                   object_id=target.pk)

    logs = (AuditLog.objects.filter(query)
            .select_related('user', 'content_type')
            .order_by('-created_at')[:limit])
    return render_to_string('ui/_chatter.html', {'logs': logs, 'object': obj})


# ─────────────────────────────────────────────────────────────
#  Blok etiketleri
# ─────────────────────────────────────────────────────────────

class _BlockNode(template.Node):
    def __init__(self, nodelist, template_name, kwargs):
        self.nodelist = nodelist
        self.template_name = template_name
        self.kwargs = kwargs

    def render(self, context):
        resolved = {k: v.resolve(context) for k, v in self.kwargs.items()}
        resolved['content'] = mark_safe(self.nodelist.render(context))
        return render_to_string(self.template_name, resolved,
                                request=context.get('request'))


def _block_tag(name, template_name):
    """{% name arg=… %}…{% endname %} -> template_name render eder."""
    def compile_fn(parser, token):
        bits = token.split_contents()[1:]
        kwargs = {}
        positional = []
        for bit in bits:
            if '=' in bit and not bit.startswith('"') and not bit.startswith("'"):
                key, _eq, raw = bit.partition('=')
                kwargs[key] = parser.compile_filter(raw)
            else:
                positional.append(parser.compile_filter(bit))
        if positional:
            kwargs['title'] = positional[0]
        nodelist = parser.parse((f'end{name}',))
        parser.delete_first_token()
        return _BlockNode(nodelist, template_name, kwargs)
    register.tag(name, compile_fn)


_block_tag('ui_sheet', 'ui/_sheet.html')
_block_tag('ui_group', 'ui/_group.html')
_block_tag('ui_button_box', 'ui/_button_box.html')
_block_tag('ui_kanban_card', 'ui/_kanban_card.html')
_block_tag('ui_x2many', 'ui/_x2many.html')


class _NotebookNode(template.Node):
    """Sekmeleri toplayıp tek seferde çizer (Odoo 'notebook')."""

    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        pages = []
        with context.push(_ui_pages=pages):
            self.nodelist.render(context)
        for index, page in enumerate(pages):
            page['is_first'] = index == 0
        return render_to_string('ui/_notebook.html', {'pages': pages},
                                request=context.get('request'))


class _PageNode(template.Node):
    def __init__(self, nodelist, title, badge):
        self.nodelist = nodelist
        self.title = title
        self.badge = badge

    def render(self, context):
        pages = context.get('_ui_pages')
        if pages is None:      # {% ui_notebook %} dışında kullanılmış
            return self.nodelist.render(context)
        title = self.title.resolve(context)
        pages.append({
            'title': title,
            'badge': self.badge.resolve(context) if self.badge else None,
            'slug': slugify(str(title)) or f'tab-{len(pages) + 1}',
            'content': mark_safe(self.nodelist.render(context)),
        })
        return ''


@register.tag('ui_notebook')
def _ui_notebook(parser, token):
    nodelist = parser.parse(('endui_notebook',))
    parser.delete_first_token()
    return _NotebookNode(nodelist)


@register.tag('ui_page')
def _ui_page(parser, token):
    bits = token.split_contents()[1:]
    if not bits:
        raise template.TemplateSyntaxError('ui_page bir başlık ister')
    title = parser.compile_filter(bits[0])
    badge = None
    for bit in bits[1:]:
        if bit.startswith('badge='):
            badge = parser.compile_filter(bit.split('=', 1)[1])
    nodelist = parser.parse(('endui_page',))
    parser.delete_first_token()
    return _PageNode(nodelist, title, badge)
