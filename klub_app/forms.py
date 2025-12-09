from django import forms
from .models import Clan, Uplata, Sale, Stock, Merenje

class ClanForm(forms.ModelForm):
    class Meta:
        model = Clan
        fields = ['ime_prezime', 'telefon', 'email', 'datum_rodjenja', 'slika']
        widgets = {
            'datum_rodjenja': forms.DateInput(attrs={'type': 'date'}),
        }

class UplataForm(forms.ModelForm):
    class Meta:
        model = Uplata
        fields = ['iznos', 'meseci', 'od_datum', 'do_datum']
        widgets = {
            'od_datum': forms.DateInput(attrs={'type': 'date'}),
            'do_datum': forms.DateInput(attrs={'type': 'date'}),
        }

class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['clan', 'stock', 'kolicina']

# ========================================
# FORMA ZA MERENJA - DODATO 09.12.2024
# ========================================

class MerenjeForm(forms.ModelForm):
    class Meta:
        model = Merenje
        # ISKLJUČI polja koja se auto-generišu
        exclude = ['clan', 'kreirao', 'created_at', 'updated_at', 'datum', 'bmi']
        
        widgets = {
            'tezina': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 75.5',
                'step': '0.1',
                'min': '20',
                'max': '300'
            }),
            'visina': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 175',
                'step': '0.1',
                'min': '100',
                'max': '250'
            }),
            'procenat_masti': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 20.5',
                'step': '0.1',
                'min': '0',
                'max': '100'
            }),
            'misicna_masa': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 55.0',
                'step': '0.1',
                'min': '0',
                'max': '200'
            }),
            'telesna_voda': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 60.0',
                'step': '0.1',
                'min': '0',
                'max': '100'
            }),
            'visceralna_mast': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 5',
                'step': '1',
                'min': '0',
                'max': '30'
            }),
            'kostana_masa': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 2.5',
                'step': '0.1',
                'min': '0',
                'max': '10'
            }),
            'bazalni_metabolizam': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 1500',
                'step': '1',
                'min': '0',
                'max': '5000'
            }),
            'krvni_pritisak_sistolni': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 120',
                'step': '1',
                'min': '50',
                'max': '250'
            }),
            'krvni_pritisak_dijastolni': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 80',
                'step': '1',
                'min': '30',
                'max': '150'
            }),
            'broj_otkucaja_miru': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 70',
                'step': '1',
                'min': '30',
                'max': '200'
            }),
            'max_broj_otkucaja': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 180',
                'step': '1',
                'min': '100',
                'max': '250'
            }),
            'max_otkucaja_70': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 126',
                'step': '1',
                'min': '50',
                'max': '200'
            }),
            'max_otkucaja_80': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 144',
                'step': '1',
                'min': '50',
                'max': '200'
            }),
            'vo2_apsolutni': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 3.5',
                'step': '0.1',
                'min': '0',
                'max': '10'
            }),
            'vo2_relativni': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 45.0',
                'step': '0.1',
                'min': '0',
                'max': '100'
            }),
            'obim_struka': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 80',
                'step': '0.1',
                'min': '30',
                'max': '200'
            }),
            'obim_grudi': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 95',
                'step': '0.1',
                'min': '50',
                'max': '200'
            }),
            'obim_bokova': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 100',
                'step': '0.1',
                'min': '50',
                'max': '200'
            }),
            'obim_podlaktice': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 26',
                'step': '0.1',
                'min': '15',
                'max': '50'
            }),
            'obim_podkolenice': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 35',
                'step': '0.1',
                'min': '20',
                'max': '70'
            }),
            'obim_nadlaktica_leva': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 32',
                'step': '0.1',
                'min': '15',
                'max': '70'
            }),
            'obim_nadlaktica_desna': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 32',
                'step': '0.1',
                'min': '15',
                'max': '70'
            }),
            'obim_butina_leva': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 55',
                'step': '0.1',
                'min': '30',
                'max': '100'
            }),
            'obim_butina_desna': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Npr. 55',
                'step': '0.1',
                'min': '30',
                'max': '100'
            }),
            'fizicki_status': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Skala 1-9',
                'step': '1',
                'min': '1',
                'max': '9'
            }),
            'napomena': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Unesite napomenu...',
                'rows': 4
            }),
        }
