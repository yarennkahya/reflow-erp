from django import forms
from django.db.models import Q

from sales.forms import CustomerForm  # noqa: F401  (crm.views buradan import ediyor)
from sales.models import Customer

from .models import Opportunity


# CustomerForm sales/forms.py'de yaşıyor: Customer modeli sales'a ait.
# Burada yeniden tanımlamak iki formun zamanla ayrışmasına yol açardı.

class SaleForm(forms.ModelForm):
    class Meta:
        model = Opportunity
        fields = ('customer', 'title', 'status', 'stage', 'estimated_value', 'notes')
        labels = {
            'customer': 'Müşteri',
            'title': 'Satış adı',
            'status': 'Satış durumu',
            'stage': 'Mevcut aşama',
            'estimated_value': 'Tahmini tutar (₺)',
            'notes': 'Notlar',
        }
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Örn. Eylül aylık kahve tedariki'}),
            'estimated_value': forms.NumberInput(attrs={'min': '0', 'step': '0.01', 'placeholder': '0,00'}),
            'notes': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Görüşme notları, sonraki adım veya ihtiyaçlar'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        customer_queryset = Customer.objects.filter(is_active=True)
        if self.instance and self.instance.customer_id:
            customer_queryset = Customer.objects.filter(
                Q(is_active=True) | Q(pk=self.instance.customer_id)
            )
        self.fields['customer'].queryset = customer_queryset.order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        stage = cleaned_data.get('stage')

        if status == Opportunity.Status.WON:
            cleaned_data['stage'] = Opportunity.Stage.WON
        elif status == Opportunity.Status.LOST:
            cleaned_data['stage'] = Opportunity.Stage.LOST
        elif stage in (Opportunity.Stage.WON, Opportunity.Stage.LOST):
            self.add_error(
                'stage',
                'Kazanıldı veya kaybedildi aşaması için satış durumunu da güncelleyin.',
            )

        return cleaned_data


class OpportunityCreateForm(forms.ModelForm):
    class Meta:
        model = Opportunity
        fields = ('customer', 'title', 'estimated_value', 'notes')
        labels = {
            'customer': 'Müşteri',
            'title': 'Fırsat adı',
            'estimated_value': 'Tahmini tutar (₺)',
            'notes': 'Notlar',
        }
        widgets = {
            'title': forms.TextInput(
                attrs={'placeholder': 'Örn. Eylül aylık kahve tedariki'}
            ),
            'estimated_value': forms.NumberInput(
                attrs={'min': '0', 'step': '0.01', 'placeholder': '0,00'}
            ),
            'notes': forms.Textarea(
                attrs={
                    'rows': 4,
                    'placeholder': 'Görüşme notları, sonraki adım veya ihtiyaçlar',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].queryset = Customer.objects.filter(
            is_active=True
        ).order_by('name')
