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