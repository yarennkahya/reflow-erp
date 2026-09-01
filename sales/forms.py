from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Customer


class CustomerForm(forms.ModelForm):
    """
    Musteri formu.

    Customer modeli sales'a ait oldugu icin form da burada yasar; crm bu formu
    import eder (crm zaten sales.models'tan Customer'i aliyor, bagimlilik yonu
    dogru). Widget CSS sinifi VERILMEZ -- {% ui_field %} sinifi widget tipinden
    turetir.
    """

    class Meta:
        model = Customer
        fields = ('name', 'customer_type', 'contact_email', 'contact_phone')
        labels = {
            'name': _('Müşteri adı'),
            'customer_type': _('Müşteri türü'),
            'contact_email': _('E-posta adresi'),
            'contact_phone': _('Telefon numarası'),
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': _('Örn. Kahve Molası Cafe')}),
            'contact_email': forms.EmailInput(attrs={'placeholder': 'ornek@firma.com'}),
            'contact_phone': forms.TextInput(attrs={'placeholder': '+90 5XX XXX XX XX'}),
        }

    def clean_name(self):
        """Ayni isimde ikinci bir musteri acilmasini engeller (buyuk/kucuk harf duyarsiz)."""
        name = (self.cleaned_data['name'] or '').strip()
        existing = Customer.objects.filter(name__iexact=name)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError('Bu isimde bir müşteri zaten kayıtlı.')
        return name
