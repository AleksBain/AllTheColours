from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Analiza, ProfilUzytkownika, TypKolorystyczny, PlikAnalizy


class RejestracjaForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email address")
    wiek = forms.IntegerField(required=False, min_value=13, max_value=100, label="Age")
    plec = forms.ChoiceField(
        choices=ProfilUzytkownika.PLEC_CHOICES, 
        required=False, 
        label="Gender"
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        labels = {
            'username': 'Username',
            'password1': 'Password',
            'password2': 'Confirm password',
        }
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            ProfilUzytkownika.objects.create(
                uzytkownik=user,
                wiek=self.cleaned_data.get('wiek'),
                plec=self.cleaned_data.get('plec', 'N')
            )
        return user


class AnalizaForm(forms.ModelForm):
    class Meta:
        model = Analiza
        fields = ['zdjecie_nadgarstka', 'zdjecie_oczu', 'zdjecie_wlosow', 'notatki']
        widgets = {
            'zdjecie_nadgarstka': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'id': 'id_zdjecie_nadgarstka'
            }),
            'zdjecie_oczu': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'id': 'id_zdjecie_oczu'
            }),
            'zdjecie_wlosow': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'id': 'id_zdjecie_wlosow'
            }),
        }
        labels = {
            'zdjecie_nadgarstka': 'Wrist/Forearm Photo',
            'zdjecie_oczu': 'Eye Photo',
            'zdjecie_wlosow': 'Hair Photo',
            'notatki': 'Additional Notes',
        }
        error_messages = {
            'zdjecie_nadgarstka': {
                'required': 'Wrist photo is required.',
                'invalid': 'Invalid wrist image file.',
            },
            'zdjecie_oczu': {
                'required': 'Eye photo is required.',
                'invalid': 'Invalid eye image file.',
            },
            'zdjecie_wlosow': {
                'required': 'Hair photo is required.',
                'invalid': 'Invalid hair image file.',
            },
        }

    def clean_zdjecie_nadgarstka(self):
        zdjecie = self.cleaned_data.get('zdjecie_nadgarstka')
        if zdjecie and zdjecie.size > 5 * 1024 * 1024:
            raise forms.ValidationError('File too large. Maximum size is 5MB.')
        return zdjecie

    def clean_zdjecie_oczu(self):
        zdjecie = self.cleaned_data.get('zdjecie_oczu')
        if zdjecie and zdjecie.size > 5 * 1024 * 1024:
            raise forms.ValidationError('File too large. Maximum size is 5MB.')
        return zdjecie

    def clean_zdjecie_wlosow(self):
        zdjecie = self.cleaned_data.get('zdjecie_wlosow')
        if zdjecie and zdjecie.size > 5 * 1024 * 1024:
            raise forms.ValidationError('File too large. Maximum size is 5MB.')
        return zdjecie


class FiltrAnalizForm(forms.Form):
    typ_kolorystyczny = forms.ModelChoiceField(
        queryset=TypKolorystyczny.objects.all(),
        required=False,
        empty_label="All Types",
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Color Type"
    )
    wiek_min = forms.IntegerField(
        required=False,
        min_value=13,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Age from'
        }),
        label="Age From"
    )
    wiek_max = forms.IntegerField(
        required=False,
        min_value=13,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Age to'
        }),
        label="Age To"
    )
    data_od = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="Date From"
    )
    data_do = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="Date To"
    )

    def clean(self):
        cleaned_data = super().clean()
        wiek_min = cleaned_data.get('wiek_min')
        wiek_max = cleaned_data.get('wiek_max')

        if wiek_min and wiek_max and wiek_min > wiek_max:
            raise forms.ValidationError('"Age From" cannot be greater than "Age To".')
        return cleaned_data


class EdycjaProfiluForm(forms.ModelForm):
    class Meta:
        model = ProfilUzytkownika
        fields = ['wiek', 'plec', 'ulubiony_typ']
        widgets = {
            'wiek': forms.NumberInput(attrs={'class': 'form-control'}),
            'plec': forms.Select(attrs={'class': 'form-select'}),
            'ulubiony_typ': forms.Select(attrs={'class': 'form-select'})
        }
        labels = {
            'wiek': 'Age',
            'plec': 'Gender',
            'ulubiony_typ': 'Favorite Color Type',
        }


class PlikAnalizyForm(forms.ModelForm):
    class Meta:
        model = PlikAnalizy
        fields = ['plik']
        widgets = {
            'plik': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.txt,.csv,.xlsx,.pdf',
                'id': 'id_plik_analizy'
            })
        }
        labels = {
            'plik': 'File',
        }

    def clean_plik(self):
        plik = self.cleaned_data.get('plik')
        if plik:
            if plik.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File too large. Maximum size is 10MB.')

            allowed_types = ['.txt', '.csv', '.xlsx', '.pdf']
            if not any(plik.name.lower().endswith(ext) for ext in allowed_types):
                raise forms.ValidationError('Allowed file types: TXT, CSV, XLSX, PDF.')
        return plik


class WybierTypForm(forms.Form):
    typ_kolorystyczny = forms.ModelChoiceField(
        queryset=TypKolorystyczny.objects.all().order_by('nazwa'),
        widget=forms.RadioSelect,
        empty_label=None,
        label="Color Type"
    )
