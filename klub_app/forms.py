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
        # EKSPLICITNO navedi SAMO polja koja želiš (bez kardiovaskularnih i obima)
        fields = [
            'tezina',
            'visina', 
            'procenat_masti',
            'misicna_masa',
            'telesna_voda',
            'visceralna_mast',
            'kostana_masa',
            'bazalni_metabolizam',
            'fizicki_status',
            'metabolic_age',  # ← DODAJ OVO
            'napomena'
        ]
        
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
            'fizicki_status': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Skala 1-9',
                'step': '1',
                'min': '1',
                'max': '9'
            }),
            'metabolic_age': forms.NumberInput(attrs={  # ← DODAJ OVO
                'class': 'form-control',
                'placeholder': 'Npr. 35',
                'step': '1',
                'min': '18',
                'max': '100'
            }),
            'napomena': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Unesite napomenu...',
                'rows': 4
            }),
        }
