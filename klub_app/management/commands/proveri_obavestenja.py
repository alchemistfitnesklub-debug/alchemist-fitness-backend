# klub_app/management/commands/proveri_obavestenja.py
from django.core.management.base import BaseCommand
from klub_app.tasks import proveri_obavestenja

class Command(BaseCommand):
    help = 'Proveri i pošalji obaveštenja za članarinu i rođendane'

    def handle(self, *args, **options):
        proveri_obavestenja()
        self.stdout.write(self.style.SUCCESS('Obaveštenja poslata!'))