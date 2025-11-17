from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_admin = models.BooleanField(default=False)
    is_trener = models.BooleanField(default=False)
    is_klijent = models.BooleanField(default=False)
    fcm_token = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.user.username

class Clan(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    ime_prezime = models.CharField(max_length=100)
    telefon = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    datum_rodjenja = models.DateField(null=True, blank=True)
    slika = models.ImageField(upload_to='clanovi/', null=True, blank=True)
    krediti_voda = models.FloatField(default=0.0)
    tip = models.CharField(max_length=10, choices=[('Trener', 'Trener'), ('Klijent', 'Klijent')], default='Klijent')

    def __str__(self):
        return self.ime_prezime

class Uplata(models.Model):
    clan = models.ForeignKey(Clan, on_delete=models.CASCADE)
    iznos = models.DecimalField(max_digits=10, decimal_places=2)
    meseci = models.IntegerField(default=1)
    datum = models.DateField(auto_now_add=True)
    od_datum = models.DateField()
    do_datum = models.DateField()
    notification_sent = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.od_datum:
            self.od_datum = timezone.now().date()
        if not self.do_datum:
            self.do_datum = self.od_datum + timedelta(days=30 * self.meseci)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.clan.ime_prezime} - {self.iznos} EUR"

class Rezervacija(models.Model):
    clan = models.ForeignKey(Clan, on_delete=models.CASCADE)
    datum = models.DateField()
    sat = models.IntegerField()

    class Meta:
        unique_together = ('datum', 'sat', 'clan')

    def __str__(self):
        return f"{self.clan.ime_prezime} - {self.datum} {self.sat}:00"

class Stock(models.Model):
    naziv = models.CharField(max_length=100)
    kolicina = models.IntegerField(default=0)
    cena = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.naziv

class Sale(models.Model):
    clan = models.ForeignKey(Clan, on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    kolicina = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    datum = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.clan.ime_prezime} - {self.stock.naziv} x{self.kolicina}"

class Obavestenje(models.Model):
    clan = models.ForeignKey(Clan, on_delete=models.CASCADE)
    tip = models.CharField(max_length=10)  # sms ili email
    poruka = models.TextField()
    status = models.CharField(max_length=20, default='sent')
    datum_slanja = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tip.upper()} za {self.clan.ime_prezime}"