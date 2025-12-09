from django import forms
from .models import Clan, Uplata, Sale, Stock

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

from .models import Merenje

class MerenjeForm(forms.ModelForm):
    class Meta:
        model = Merenje
        exclude = ['clan', 'kreirao', 'created_at', 'updated_at']
        widgets = {
            'datum': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'tezina': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': '66.5'}),
            'visina': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': '177'}),
            'procenat_masti': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'misicna_masa': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'telesna_voda': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'visceralna_mast': forms.NumberInput(attrs={'class': 'form-control'}),
            'kostana_masa': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'bmi': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'bazalni_metabolizam': forms.NumberInput(attrs={'class': 'form-control'}),
            'krvni_pritisak_sistolni': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '120'}),
            'krvni_pritisak_dijastolni': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '80'}),
            'broj_otkucaja_miru': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '70'}),
            'max_broj_otkucaja': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_otkucaja_70': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_otkucaja_80': forms.NumberInput(attrs={'class': 'form-control'}),
            'vo2_apsolutni': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'vo2_relativni': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'obim_struka': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'obim_grudi': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'obim_bokova': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'obim_podlaktice': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'obim_podkolenice': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'obim_nadlaktica_leva': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'obim_nadlaktica_desna': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'obim_butina_leva': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'obim_butina_desna': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'fizicki_status': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '9', 'placeholder': '5'}),
            'napomena': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Dodatne napomene...'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        tezina = cleaned_data.get('tezina')
        visina = cleaned_data.get('visina')
        
        if tezina and visina:
            visina_m = float(visina) / 100
            bmi = float(tezina) / (visina_m ** 2)
            cleaned_data['bmi'] = round(bmi, 2)
        
        return cleaned_data
