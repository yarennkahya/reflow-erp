"""
Paylaşılan ay ızgarası kurucuları.

Önceden meetings/views.py içinde gömülüydü ve yalnızca tek günlük olayları
kovalıyordu. İzin talepleri (start_date -> end_date) bir ARALIK olduğu için
ikinci bir fonksiyon gerekiyor.
"""
import calendar as pycal
from datetime import date, datetime, timedelta

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

MONTH_NAMES = [
    '',
    _('Ocak'), _('Şubat'), _('Mart'), _('Nisan'), _('Mayıs'), _('Haziran'),
    _('Temmuz'), _('Ağustos'), _('Eylül'), _('Ekim'), _('Kasım'), _('Aralık'),
]

WEEKDAY_NAMES = [
    _('Pzt'), _('Sal'), _('Çar'), _('Per'), _('Cum'), _('Cmt'), _('Paz'),
]


def normalize_period(year, month, today=None, period=None):
    """
    ?year=&month= parametrelerini güvenli bir (year, month) çiftine indirger.

    Alternatif olarak <input type="month"> tarayıcı seçicisinden gelen
    ``period=YYYY-MM`` biçimini de kabul eder; year/month verilmemişse buradan
    ayrıştırır. Böylece manuel ay seçimi tek bir alanla çalışabilir.
    """
    today = today or timezone.localdate()
    if (year is None or month is None) and period:
        parts = str(period).split('-')
        if len(parts) == 2:
            year, month = parts[0], parts[1]
    try:
        year, month = int(year), int(month)
    except (TypeError, ValueError):
        return today.year, today.month
    if not 1 <= year <= 9999 or not 1 <= month <= 12:
        return today.year, today.month
    return year, month


def period_nav(year, month):
    """Önceki/sonraki ay bağlantıları için gereken dört sayı."""
    prev_month, prev_year = (12, year - 1) if month == 1 else (month - 1, year)
    next_month, next_year = (1, year + 1) if month == 12 else (month + 1, year)
    return {
        'month_label': f'{MONTH_NAMES[month]} {year}',
        'prev_year': prev_year, 'prev_month': prev_month,
        'next_year': next_year, 'next_month': next_month,
        # <input type="month"> value biçimi (YYYY-MM); manuel seçici için.
        'period_value': f'{year:04d}-{month:02d}',
        'weekday_names': WEEKDAY_NAMES,
    }


def _empty_weeks(year, month, today):
    """Ayın hafta/gün iskeletini kurar; her gün için boş bir olay listesi açar."""
    weeks = []
    for week in pycal.Calendar(firstweekday=0).monthdayscalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(None)
            else:
                row.append({
                    'day': day,
                    'date': date(year, month, day),
                    'events': [],
                    'is_today': date(year, month, day) == today,
                })
        weeks.append(row)
    return weeks


def _index(weeks):
    """gün numarası -> gün sözlüğü (hızlı yerleştirme için)."""
    return {cell['day']: cell for week in weeks for cell in week if cell}


def month_grid(year, month, objects, date_of, today=None):
    """
    Tek günlük olaylar için ay ızgarası.

    date_of(obj) -> date | datetime | None

    Saat dilimi duyarlı datetime'lar yerel saate çevrilir; aksi halde UTC'de
    gece yarısına yakın olaylar yanlış güne düşer.
    """
    today = today or timezone.localdate()
    weeks = _empty_weeks(year, month, today)
    by_day = _index(weeks)

    for obj in objects:
        moment = date_of(obj)
        if moment is None:
            continue
        if isinstance(moment, datetime):
            if timezone.is_aware(moment):
                moment = timezone.localtime(moment)
            moment = moment.date()
        if moment.year == year and moment.month == month:
            cell = by_day.get(moment.day)
            if cell is not None:
                cell['events'].append(obj)

    return weeks


def month_grid_spans(year, month, objects, start_of, end_of, today=None):
    """
    ARALIK olaylar için ay ızgarası (ör. izin talepleri).

    Aralığın bu aya düşen her günü ilgili hücreye eklenir; ayrıca hücre başına
    'is_start' / 'is_end' işaretleri üretilir ki şablon aralığı tek bir şerit
    gibi çizebilsin.
    """
    today = today or timezone.localdate()
    weeks = _empty_weeks(year, month, today)
    by_day = _index(weeks)

    first = date(year, month, 1)
    last = date(year, month, pycal.monthrange(year, month)[1])

    for obj in objects:
        start, end = start_of(obj), end_of(obj)
        if start is None:
            continue
        if end is None or end < start:
            end = start
        # aralığı görünen aya kırp
        lo, hi = max(start, first), min(end, last)
        if lo > hi:
            continue
        cursor = lo
        while cursor <= hi:
            cell = by_day.get(cursor.day)
            if cell is not None:
                cell['events'].append({
                    'object': obj,
                    'is_start': cursor == start,
                    'is_end': cursor == end,
                })
            cursor += timedelta(days=1)

    return weeks
