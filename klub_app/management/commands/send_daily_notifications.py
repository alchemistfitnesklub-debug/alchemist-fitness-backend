from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from klub_app.models import Clan, Uplata, FCMToken, Obavestenje
from klub_app.services.firebase_service import send_push_notification
from django.core.mail import send_mail
from django.conf import settings
from twilio.rest import Client
import phonenumbers


class Command(BaseCommand):
    help = 'Šalje automatska obaveštenja (članarine + rođendani)'

    def handle(self, *args, **kwargs):
        self.stdout.write('🤖 Pokrećem automatska obaveštenja...')
        
        try:
            # 1. Članarine koje ističu za 7 dana
            expirations_sent = self.send_expiration_notifications()
            
            # 2. Rođendanske čestitke
            birthdays_sent = self.send_birthday_notifications()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Poslato {expirations_sent} obaveštenja o članarinama i {birthdays_sent} rođendanskih čestitki!'
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Greška: {str(e)}'))

    def send_expiration_notifications(self):
        """Članarine koje ističu za 7 dana"""
        today = timezone.now().date()
        sedam_dana = today + timedelta(days=7)
        
        expirations = Uplata.objects.filter(
            do_datum=sedam_dana,
            notification_sent=False
        ).select_related('clan')
        
        sent_count = 0
        
        for uplata in expirations:
            message = f"Poštovani/a, Vaš paket ({uplata.meseci} meseci) ističe {uplata.do_datum.strftime('%d.%m.%Y')}. Podsećamo Vas da produžite paket. Sportski pozdrav, Vaš Alchemist!"
            
            # EMAIL
            if uplata.clan.email:
                try:
                    send_mail(
                        'Obaveštenje o isteku članarine',
                        message,
                        settings.EMAIL_HOST_USER,
                        [uplata.clan.email],
                        fail_silently=True
                    )
                    Obavestenje.objects.create(
                        clan=uplata.clan,
                        tip='email',
                        poruka=message,
                        status='sent'
                    )
                    sent_count += 1
                except Exception as e:
                    self.stdout.write(f'Email greška za {uplata.clan.ime_prezime}: {e}')
            
            # SMS (Twilio - za sada)
            if uplata.clan.telefon:
                try:
                    client = Client(settings.TWILIO_SID, settings.TWILIO_AUTH_TOKEN)
                    telefon = str(uplata.clan.telefon).replace('.0', '').replace(' ', '')
                    if not telefon.startswith('+'):
                        telefon = '+381' + telefon.lstrip('0')
                    
                    parsed_number = phonenumbers.parse(telefon, "RS")
                    if phonenumbers.is_valid_number(parsed_number):
                        sms_obj = client.messages.create(
                            body=message,
                            from_=settings.TWILIO_PHONE_NUMBER,
                            to=phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
                        )
                        status = 'delivered' if sms_obj.status in ['delivered', 'sent', 'queued'] else 'failed'
                        Obavestenje.objects.create(
                            clan=uplata.clan,
                            tip='sms',
                            poruka=message,
                            status=status
                        )
                        sent_count += 1
                except Exception as e:
                    self.stdout.write(f'SMS greška za {uplata.clan.ime_prezime}: {e}')
                    Obavestenje.objects.create(
                        clan=uplata.clan,
                        tip='sms',
                        poruka=message,
                        status='failed'
                    )
            
            # PUSH
            if uplata.clan.user:
                try:
                    token_obj = FCMToken.objects.filter(
                        user=uplata.clan.user,
                        is_active=True
                    ).first()
                    
                    if token_obj:
                        send_push_notification(
                            fcm_token=token_obj.token,
                            title="Članarina ističe za 7 dana",
                            body=message
                        )
                except Exception as e:
                    self.stdout.write(f'Push greška za {uplata.clan.ime_prezime}: {e}')
            
            # Označi da je poslato
            uplata.notification_sent = True
            uplata.save()
        
        return sent_count

    def send_birthday_notifications(self):
        """Rođendanske čestitke"""
        today = timezone.now().date()
        
        birthdays = Clan.objects.filter(
            datum_rodjenja__month=today.month,
            datum_rodjenja__day=today.day
        )
        
        sent_count = 0
        message = "Neko misli na Vas, srećan rođendan!!! Vaš Alchemist"
        
        for clan in birthdays:
            # EMAIL
            if clan.email:
                try:
                    send_mail(
                        'Srećan rođendan!',
                        message,
                        settings.EMAIL_HOST_USER,
                        [clan.email],
                        fail_silently=True
                    )
                    Obavestenje.objects.create(
                        clan=clan,
                        tip='email',
                        poruka=message,
                        status='sent'
                    )
                    sent_count += 1
                except Exception as e:
                    self.stdout.write(f'Email greška za {clan.ime_prezime}: {e}')
            
            # SMS (Twilio - za sada)
            if clan.telefon:
                try:
                    client = Client(settings.TWILIO_SID, settings.TWILIO_AUTH_TOKEN)
                    telefon = str(clan.telefon).replace('.0', '').replace(' ', '')
                    if not telefon.startswith('+'):
                        telefon = '+381' + telefon.lstrip('0')
                    
                    parsed_number = phonenumbers.parse(telefon, "RS")
                    if phonenumbers.is_valid_number(parsed_number):
                        sms_obj = client.messages.create(
                            body=message,
                            from_=settings.TWILIO_PHONE_NUMBER,
                            to=phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
                        )
                        status = 'delivered' if sms_obj.status in ['delivered', 'sent', 'queued'] else 'failed'
                        Obavestenje.objects.create(
                            clan=clan,
                            tip='sms',
                            poruka=message,
                            status=status
                        )
                        sent_count += 1
                except Exception as e:
                    self.stdout.write(f'SMS greška za {clan.ime_prezime}: {e}')
                    Obavestenje.objects.create(
                        clan=clan,
                        tip='sms',
                        poruka=message,
                        status='failed'
                    )
            
            # PUSH
            if clan.user:
                try:
                    token_obj = FCMToken.objects.filter(
                        user=clan.user,
                        is_active=True
                    ).first()
                    
                    if token_obj:
                        send_push_notification(
                            fcm_token=token_obj.token,
                            title="Srećan rođendan!",
                            body=message
                        )
                except Exception as e:
                    self.stdout.write(f'Push greška za {clan.ime_prezime}: {e}')
        
        return sent_count
