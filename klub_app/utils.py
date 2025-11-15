# klub_app/utils.py
from django.core.mail import send_mail
from django.conf import settings
from twilio.rest import Client
import phonenumbers
import logging

logger = logging.getLogger(__name__)

def send_notification_email(to_email, subject, message):
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[to_email],
            fail_silently=False,
        )
        logger.info(f"Email poslat: {to_email}")
    except Exception as e:
        logger.error(f"Email greška: {e}")

def send_notification_sms(to_phone, message):
    try:
        client = Client(settings.TWILIO_SID, settings.TWILIO_AUTH_TOKEN)
        telefon = str(to_phone).replace('.0', '').replace(' ', '')
        if not telefon.startswith('+'):
            telefon = '+381' + telefon.lstrip('0')
        parsed = phonenumbers.parse(telefon, "RS")
        if phonenumbers.is_valid_number(parsed):
            sms = client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            )
            logger.info(f"SMS poslat: {to_phone}")
        else:
            logger.error(f"Neispravan broj: {to_phone}")
    except Exception as e:
        logger.error(f"SMS greška: {e}")