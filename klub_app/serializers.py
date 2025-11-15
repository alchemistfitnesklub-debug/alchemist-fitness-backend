# klub_app/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Clan, Uplata, Rezervacija, Obavestenje, UserProfile

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class ClanSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Clan
        fields = ['id', 'ime_prezime', 'telefon', 'email', 'datum_rodjenja', 
                  'slika', 'krediti_voda', 'user']

class UplataSerializer(serializers.ModelSerializer):
    clan_ime = serializers.CharField(source='clan.ime_prezime', read_only=True)
    
    class Meta:
        model = Uplata
        fields = ['id', 'clan', 'clan_ime', 'iznos', 'meseci', 'datum', 
                  'od_datum', 'do_datum', 'notification_sent']

class RezervacijaSerializer(serializers.ModelSerializer):
    clan_ime = serializers.CharField(source='clan.ime_prezime', read_only=True)
    
    class Meta:
        model = Rezervacija
        fields = ['id', 'clan', 'clan_ime', 'datum', 'sat']

class ObavestenjeSerializer(serializers.ModelSerializer):
    clan_ime = serializers.CharField(source='clan.ime_prezime', read_only=True)
    
    class Meta:
        model = Obavestenje
        fields = ['id', 'clan', 'clan_ime', 'tip', 'poruka', 'status', 'datum_slanja']