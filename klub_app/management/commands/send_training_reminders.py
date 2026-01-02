from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import pytz
from klub_app.models import Rezervacija, FCMToken
from klub_app.services.firebase_service import send_push_notification

class Command(BaseCommand):
    help = 'Šalje push notifikacije 1 sat pre treninga'
    
    def handle(self, *args, **kwargs):
        self.stdout.write('🏋️ Proveravam trening podsetnika...')
        
        # ✅ KORISTI SRPSKO VREME (Belgrade timezone)
        belgrade_tz = pytz.timezone('Europe/Belgrade')
        now = timezone.now().astimezone(belgrade_tz)
        
        one_hour_later = now + timedelta(hours=1)
        target_date = one_hour_later.date()
        target_hour = one_hour_later.hour
        
        self.stdout.write(f'🕐 Trenutno vreme (Beograd): {now.strftime("%H:%M")}')
        self.stdout.write(f'🎯 Tražim treninge za: {target_date} u {target_hour}:00')
        
        # Pronađi rezervacije za 1 sat
        rezervacije = Rezervacija.objects.filter(
            datum=target_date,
            sat=target_hour
        ).select_related('clan', 'clan__user')
        
        if not rezervacije.exists():
            self.stdout.write(f'✓ Nema treninga za {target_hour}:00')
            return
        
        sent_count = 0
        
        for rezervacija in rezervacije:
            if not rezervacija.clan.user:
                continue
            
            try:
                token_obj = FCMToken.objects.filter(
                    user=rezervacija.clan.user,
                    is_active=True
                ).first()
                
                if token_obj:
                    message = f"Podsetnik: Za 1 sat imate zakazan trening u {rezervacija.sat}:00! 💪"
                    response = send_push_notification(
                        fcm_token=token_obj.token,
                        title="⏰ Trening za 1 sat",
                        body=message
                    )
                    if response:
                        sent_count += 1
                        self.stdout.write(f'✓ Poslato: {rezervacija.clan.ime_prezime}')
            except Exception as e:
                self.stdout.write(f'✗ Greška za {rezervacija.clan.ime_prezime}: {e}')
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Poslato {sent_count} trening podsетnika!')
        )
