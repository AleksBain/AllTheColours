from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Analiza, ProfilUzytkownika, TypKolorystyczny, PlikAnalizy


class RejestracjaForm(UserCreationForm):
    email = forms.EmailField(required=True)
    wiek = forms.IntegerField(required=False, min_value=13, max_value=100)
    plec = forms.ChoiceField(choices=ProfilUzytkownika.PLEC_CHOICES, required=False)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
    
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
            'zdjecie_nadgarstka': 'Zdjęcie nadgarstka/przedramienia',
            'zdjecie_oczu': 'Zdjęcie oczu',
            'zdjecie_wlosow': 'Zdjęcie włosów',
            'notatki': 'Dodatkowe notatki'
        }
    
    def clean_zdjecie_nadgarstka(self):
        zdjecie = self.cleaned_data.get('zdjecie_nadgarstka')
        if zdjecie:
            if zdjecie.size > 5 * 1024 * 1024:  # 5MB
                raise forms.ValidationError('Plik jest za duży. Maksymalny rozmiar to 5MB.')
        return zdjecie
    
    def clean_zdjecie_oczu(self):
        zdjecie = self.cleaned_data.get('zdjecie_oczu')
        if zdjecie:
            if zdjecie.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Plik jest za duży. Maksymalny rozmiar to 5MB.')
        return zdjecie
    
    def clean_zdjecie_wlosow(self):
        zdjecie = self.cleaned_data.get('zdjecie_wlosow')
        if zdjecie:
            if zdjecie.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Plik jest za duży. Maksymalny rozmiar to 5MB.')
        return zdjecie


class FiltrAnalizForm(forms.Form):
    typ_kolorystyczny = forms.ModelChoiceField(
        queryset=TypKolorystyczny.objects.all(),
        required=False,
        empty_label="Wszystkie typy",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    wiek_min = forms.IntegerField(
        required=False,
        min_value=13,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Wiek od'
        })
    )
    wiek_max = forms.IntegerField(
        required=False,
        min_value=13,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Wiek do'
        })
    )
    data_od = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    data_do = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        wiek_min = cleaned_data.get('wiek_min')
        wiek_max = cleaned_data.get('wiek_max')
        
        if wiek_min and wiek_max and wiek_min > wiek_max:
            raise forms.ValidationError('Wiek "od" nie może być większy niż wiek "do".')
        
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
    
    def clean_plik(self):
        plik = self.cleaned_data.get('plik')
        if plik:
            if plik.size > 10 * 1024 * 1024:  # 10MB
                raise forms.ValidationError('Plik jest za duży. Maksymalny rozmiar to 10MB.')
            
            allowed_types = ['.txt', '.csv', '.xlsx', '.pdf']
            if not any(plik.name.lower().endswith(ext) for ext in allowed_types):
                raise forms.ValidationError('Dozwolone typy plików: TXT, CSV, XLSX, PDF.')
        
        return plik


class WybierTypForm(forms.Form):
    typ_kolorystyczny = forms.ModelChoiceField(
        queryset=TypKolorystyczny.objects.all(),
        widget=forms.RadioSelect,
        empty_label=None
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['typ_kolorystyczny'].queryset = TypKolorystyczny.objects.all().order_by('nazwa')