# klub_app/management/commands/send_daily_notifications.py
from django.core.management.base import BaseCommand
from klub_app.views import send_expiration_notifications, send_birthday_notifications

class Command(BaseCommand):
    help = 'Šalje automatska obaveštenja za isteke članarina i rođendane'

    def handle(self, *args, **options):
        self.stdout.write('Pokrećem slanje obaveštenja...')
        
        # Pošalji obaveštenja za istekle članarine
        send_expiration_notifications()
        self.stdout.write(self.style.SUCCESS('✓ Obaveštenja za članarine poslata'))
        
        # Pošalji rođendanske čestitke
        send_birthday_notifications()
        self.stdout.write(self.style.SUCCESS('✓ Rođendanske čestitke poslate'))
        
        self.stdout.write(self.style.SUCCESS('Sva obaveštenja uspešno poslata!'))