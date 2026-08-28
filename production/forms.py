from django import forms

from hr.models import Employee

from .models import QualityCheck


class QualityCheckForm(forms.Form):
    result = forms.ChoiceField(
        choices=QualityCheck.Result.choices,
        label='Kontrol sonucu',
    )
    score = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=100,
        label='Cupping skoru',
        help_text='İsteğe bağlı, 0 ile 100 arasında bir değer girin.',
    )
    inspector = forms.ModelChoiceField(
        queryset=Employee.objects.none(),
        label='Kontrolü yapan',
        empty_label='Çalışan seçin',
    )
    notes = forms.CharField(
        required=False,
        label='Notlar',
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['inspector'].queryset = Employee.objects.filter(
            employment_status=Employee.EmploymentStatus.ACTIVE
        ).select_related('department', 'position')
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        self.fields['result'].widget.attrs['class'] = 'form-select'
        self.fields['inspector'].widget.attrs['class'] = 'form-select'
