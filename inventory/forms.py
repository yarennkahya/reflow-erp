from django import forms

from .models import Warehouse


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ('name', 'city')
        labels = {
            'name': 'Depo adı',
            'city': 'Şehir',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Örn. Avrupa Yakası Ana Depo'}),
            'city': forms.TextInput(attrs={'placeholder': 'Örn. İstanbul'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data['name']
        existing = Warehouse.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError('Bu isimde bir depo zaten var.')
        return name
