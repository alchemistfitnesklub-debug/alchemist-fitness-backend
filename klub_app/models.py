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

# FCM Token Model za Push Notifikacije
class FCMToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fcm_tokens')
    token = models.CharField(max_length=255, unique=True)
    device_type = models.CharField(max_length=20, choices=[
        ('android', 'Android'),
        ('ios', 'iOS'),
    ], default='android')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'FCM Token'
        verbose_name_plural = 'FCM Tokens'
        ordering = ['-created_at']
    
    def __str__(self):
        try:
            username = self.user.username if self.user else "No user"
            token_preview = self.token[:20] if self.token else "No token"
            return f"{username} - {self.device_type} - {token_preview}..."
        except Exception:
            return f"FCMToken {self.id if self.id else 'New'}"

# ========================================
# MODEL ZA MERENJA - DODATO 09.12.2024
# ========================================

from django.utils import timezone
from decimal import Decimal

class Merenje(models.Model):
    """
    Model za čuvanje fizičkih merenja članova fitness kluba
    """
    clan = models.ForeignKey(Clan, on_delete=models.CASCADE, related_name='merenja')
    datum = models.DateTimeField(default=timezone.now, verbose_name="Datum i vreme merenja")
    
    # OSNOVNA MERENJA
    tezina = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Telesna masa (kg)")
    visina = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name="Visina (cm)")
    procenat_masti = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name="Telesnih masti (%)")
    misicna_masa = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Mišićna masa (kg)")
    telesna_voda = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Telesne vode (kg)")
    visceralna_mast = models.IntegerField(null=True, blank=True, verbose_name="Visceralne masti (nivo)")
    kostana_masa = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Koštana masa (kg)")
    bmi = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="BMI")
    bazalni_metabolizam = models.IntegerField(null=True, blank=True, verbose_name="Bazalni metabolizam (kcal)")
    
    # KARDIOVASKULARNA MERENJA
    krvni_pritisak_sistolni = models.IntegerField(null=True, blank=True, verbose_name="Sistolni pritisak (mmHg)")
    krvni_pritisak_dijastolni = models.IntegerField(null=True, blank=True, verbose_name="Dijastolni pritisak (mmHg)")
    broj_otkucaja_miru = models.IntegerField(null=True, blank=True, verbose_name="Broj srčanih otkucaja u miru")
    max_broj_otkucaja = models.IntegerField(null=True, blank=True, verbose_name="Max. broj srčanih otkucaja")
    max_otkucaja_70 = models.IntegerField(null=True, blank=True, verbose_name="70% od max otkucaja")
    max_otkucaja_80 = models.IntegerField(null=True, blank=True, verbose_name="80% od max otkucaja")
    vo2_apsolutni = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name="Apsolutni max VO2")
    vo2_relativni = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name="Relativni max VO2")
    
    # OBIMI TELA
    obim_struka = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name="Obim struka (cm)")
    obim_grudi = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name="Obim grudi (cm)")
    obim_bokova = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name="Obim bokova (cm)")
    obim_podlaktice = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name="Obim podlaktice (cm)")
    obim_podkolenice = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name="Obim podkolenice (cm)")
    obim_nadlaktica_leva = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name="Obim leve nadlaktice (cm)")
    obim_nadlaktica_desna = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name="Obim desne nadlaktice (cm)")
    obim_butina_leva = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name="Obim leve butine (cm)")
    obim_butina_desna = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name="Obim desne butine (cm)")
    
    # DODATNO
    fizicki_status = models.IntegerField(null=True, blank=True, verbose_name="Fizički status (1-9)")
    metabolic_age = models.IntegerField(null=True, blank=True, verbose_name="Metabolička starost")  # NOVO
    napomena = models.TextField(blank=True, verbose_name="Napomena trenera")
    kreirao = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Merenje izvršio")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-datum']
        verbose_name = 'Merenje'
        verbose_name_plural = 'Merenja'
    
    def __str__(self):
        return f"{self.clan.ime_prezime} - {self.datum.strftime('%d.%m.%Y')}"
    
    def izracunaj_bmi(self):
        if self.tezina and self.visina:
            visina_m = float(self.visina) / 100
            bmi = float(self.tezina) / (visina_m ** 2)
            return round(bmi, 2)
        return None
    
    def bmi_kategorija(self):
        if not self.bmi:
            return "N/A"
        bmi = float(self.bmi)
        if bmi < 18.5:
            return "Pothranjen"
        elif 18.5 <= bmi < 25:
            return "Normalna težina"
        elif 25 <= bmi < 30:
            return "Prekomerna težina"
        else:
            return "Gojaznost"
    
    def status_telesne_masti(self):
        if not self.procenat_masti:
            return "N/A"
        procenat = float(self.procenat_masti)
        if procenat < 20:
            return "Podhranjen"
        elif 20 <= procenat < 30:
            return "Zdrav"
        elif 30 <= procenat < 35:
            return "Prehranjen"
        else:
            return "Gojazan"
    
    def procena_rizika_visceralne_masti(self):
        if not self.visceralna_mast:
            return "N/A"
        nivo = int(self.visceralna_mast)
        if nivo <= 9:
            return "Normalno (nizak rizik)"
        elif 10 <= nivo <= 14:
            return "Visok rizik"
        else:
            return "Veoma visok rizik"
    
    def save(self, *args, **kwargs):
        if self.tezina and self.visina and not self.bmi:
            self.bmi = self.izracunaj_bmi()
        super().save(*args, **kwargs)

# ========================================
# MODEL ZA TRACKING PRISUSTVA RADNIKA
# DODATO 10.12.2024
# ========================================

class RadnikPrisustvo(models.Model):
    """Beleženje radnih dana zaposlenih"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prisustva')
    datum = models.DateField(auto_now_add=True)
    vreme_logovanja = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Prisustvo Radnika"
        verbose_name_plural = "Prisustva Radnika"
        ordering = ['-datum']
        unique_together = ['user', 'datum']  # Jedno prisustvo po danu
    
    def __str__(self):
        return f"{self.user.username} - {self.datum.strftime('%d.%m.%Y')}"


class ZatvorenTermin(models.Model):
    """Model za zatvaranje termina (npr. praznici, održavanje)"""
    datum = models.DateField()
    sat = models.IntegerField()  # 8-19
    razlog = models.CharField(max_length=200, blank=True, null=True)
    zatvorio = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    kreiran = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['datum', 'sat']
        verbose_name = 'Zatvoren termin'
        verbose_name_plural = 'Zatvoreni termini'
    
    def __str__(self):
        return f"{self.datum} u {self.sat}:00 - {self.razlog or 'Zatvoren'}"
