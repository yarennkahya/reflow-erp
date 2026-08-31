from django import forms

from .models import LeaveRequest


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ('employee', 'leave_type', 'start_date', 'end_date', 'notes')
        labels = {
            'employee': 'Çalışan',
            'leave_type': 'İzin türü',
            'start_date': 'Başlangıç tarihi',
            'end_date': 'Bitiş tarihi',
            'notes': 'Notlar',
        }
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(
                attrs={'rows': 4, 'placeholder': 'İzin talebinizle ilgili not ekleyin'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        self.fields['employee'].widget.attrs['class'] = 'form-select'
        self.fields['leave_type'].widget.attrs['class'] = 'form-select'

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'Bitiş tarihi başlangıç tarihinden önce olamaz.')
        return cleaned_data
