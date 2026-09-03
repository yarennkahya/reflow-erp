"""Kanban kolonları için tek gruplama yardımcısı (6 sayfada kullanılır)."""


def group_by_choice(objects, field, choices, key=None, aggregate=None):
    """
    Nesneleri bir TextChoices alanına göre kolonlara böler.

    field     : gruplanacak alan adı (key verilirse yok sayılır)
    choices   : Model.Field.choices — kolon SIRASINI bu belirler
    key       : özel değer çıkarıcı (hesaplanan alanlar / dict satırları için)
    aggregate : kolon başına toplanacak sayıyı döndüren callable

    Boş kolonlar da döner — kanban'da sütun kaybolmamalı.
    """
    getter = key or (lambda obj: getattr(obj, field))

    buckets = {value: [] for value, _label in choices}
    for obj in objects:
        buckets.setdefault(getter(obj), []).append(obj)

    columns = []
    for value, label in choices:
        items = buckets.get(value, [])
        column = {
            'value': value,
            'label': label,
            'items': items,
            'count': len(items),
        }
        if aggregate is not None:
            column['total'] = sum((aggregate(o) or 0) for o in items)
        columns.append(column)
    return columns
