from django import forms

from .models import Application, Candidate, CandidateDocument, Department, Employee, JobOpening, LeaveRequest, Position


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ('name', 'email', 'phone', 'department', 'position',
                  'manager', 'hire_date', 'employment_status', 'salary')
        labels = {
            'name': 'Ad Soyad',
            'email': 'E-posta',
            'phone': 'Telefon',
            'department': 'Departman',
            'position': 'Pozisyon',
            'manager': 'Yönetici',
            'hire_date': 'İşe giriş tarihi',
            'employment_status': 'Durum',
            'salary': 'Maaş (TL)',
        }
        widgets = {
            'hire_date': forms.DateInput(attrs={'type': 'date'}),
            'salary': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['manager'].queryset = Employee.objects.order_by('name')
        self.fields['manager'].required = False
        self.fields['salary'].required = False

    def clean(self):
        cleaned_data = super().clean()
        department = cleaned_data.get('department')
        position = cleaned_data.get('position')
        if department and position and position.department_id != department.pk:
            self.add_error('position', 'Pozisyon seçili departmana ait olmalıdır.')
        return cleaned_data


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

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'Bitiş tarihi başlangıç tarihinden önce olamaz.')
        return cleaned_data


_CV_ALLOWED = {'.pdf', '.doc', '.docx'}
_CV_ACCEPT  = '.pdf,.doc,.docx'


def _validate_cv(file):
    ext = '.' + file.name.rsplit('.', 1)[-1].lower() if '.' in file.name else ''
    if ext not in _CV_ALLOWED:
        raise forms.ValidationError('Yalnızca PDF, DOC veya DOCX dosyaları kabul edilir.')


class CandidateForm(forms.ModelForm):
    cv_file = forms.FileField(
        required=False,
        label='CV Dosyası',
        help_text='PDF, DOC veya DOCX yükleyin.',
        validators=[_validate_cv],
        widget=forms.ClearableFileInput(attrs={'accept': _CV_ACCEPT}),
    )

    class Meta:
        model = Candidate
        fields = ('name', 'email', 'phone', 'resume_note')
        labels = {
            'name': 'Ad Soyad',
            'email': 'E-posta',
            'phone': 'Telefon',
            'resume_note': 'Notlar',
        }
        widgets = {
            'resume_note': forms.Textarea(
                attrs={'rows': 3, 'placeholder': 'Aday hakkında kısa bir not ekleyin'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class CandidateDocumentForm(forms.ModelForm):
    class Meta:
        model = CandidateDocument
        fields = ('file', 'label')
        labels = {'file': 'Dosya', 'label': 'Etiket (opsiyonel)'}
        widgets = {
            'label': forms.TextInput(attrs={'placeholder': 'Örn. CV 2026, Portfolyo…'}),
            'file': forms.ClearableFileInput(attrs={'accept': _CV_ACCEPT}),
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            _validate_cv(file)
        return file


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


class JobOpeningForm(forms.ModelForm):
    class Meta:
        model = JobOpening
        fields = ('title', 'department', 'position', 'headcount', 'closing_date')
        labels = {
            'title': 'İlan başlığı',
            'department': 'Departman',
            'position': 'Pozisyon',
            'headcount': 'Kontenjan',
            'closing_date': 'Son başvuru tarihi',
        }
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Örn. Kıdemli Kavurma Uzmanı'}),
            'headcount': forms.NumberInput(attrs={'min': '1'}),
            'closing_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        department = cleaned_data.get('department')
        position = cleaned_data.get('position')
        if department and position and position.department_id != department.pk:
            self.add_error('position', 'Pozisyon seçili departmana ait olmalıdır.')
        return cleaned_data
