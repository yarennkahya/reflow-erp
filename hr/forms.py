from django import forms

from .models import Application, Candidate, JobOpening, LeaveRequest


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


class CandidateForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ('name', 'email', 'phone', 'resume_note')
        labels = {
            'name': 'Ad Soyad',
            'email': 'E-posta',
            'phone': 'Telefon',
            'resume_note': 'Özgeçmiş Notu',
        }
        widgets = {
            'resume_note': forms.Textarea(
                attrs={'rows': 4, 'placeholder': 'Aday hakkında kısa bir not ekleyin'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ('candidate', 'job_opening')
        labels = {
            'candidate': 'Aday',
            'job_opening': 'İş İlanı',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['job_opening'].queryset = JobOpening.objects.filter(status='open')
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-select')
