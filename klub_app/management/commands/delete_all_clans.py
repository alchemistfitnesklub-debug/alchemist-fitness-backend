from django.core.management.base import BaseCommand
from klub_app.models import Clan, Rezervacija, Uplata, Obavestenje

class Command(BaseCommand):
    help = 'Briše sve članove, rezervacije, uplate i obaveštenja iz baze podataka'

    def handle(self, *args, **kwargs):
        Rezervacija.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Sve rezervacije obrisane.'))
        Uplata.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Sve uplate obrisane.'))
        Obavestenje.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Sva obaveštenja obrisana.'))
        Clan.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Svi članovi obrisani.'))