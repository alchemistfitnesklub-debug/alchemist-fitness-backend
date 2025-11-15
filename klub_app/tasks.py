# klub_app/tasks.py
from datetime import date, timedelta
from .models import Clan, Uplata, Obavestenje
from .utils import send_notification_email, send_notification_sms
import logging

logger = logging.getLogger(__name__)

def proveri_obavestenja():
    danas = date.today()
    za_7_dana = danas + timedelta(days=7)

    # 1. ČLANARINA ISTIČE ZA 7 DANA
    uplate = Uplata.objects.filter(to_date=za_7_dana, notification_sent=False)
    for uplata in uplate:
        clan = uplata.clan
        subject = "Obaveštenje o isteku članarine"
        message = (
            f"Poštovani/a,\n\n"
            f"Vaš paket ističe {uplata.to_date.strftime('%d.%m.%Y')}.\n"
            f"Podsećamo Vas da produžite paket.\n\n"
            f"Sportski pozdrav!\nVaš Alchemist"
        )

        # Email
        if clan.email:
            send_notification_email(clan.email, subject, message)
            Obavestenje.objects.create(clan=clan, tip='email', poruka=message, status='sent')
        # SMS
        if clan.telefon:
            sms_text = f"Vaš paket ističe {uplata.to_date.strftime('%d.%m.%Y')}. Produžite paket! Vaš Alchemist"
            send_notification_sms(clan.telefon, sms_text)
            Obavestenje.objects.create(clan=clan, tip='sms', poruka=sms_text, status='sent')

        uplata.notification_sent = True
        uplata.save()

    # 2. ROĐENDAN DANAS
    rodjendani = Clan.objects.filter(datum_rodjenja__month=danas.month, datum_rodjenja__day=danas.day)
    for clan in rodjendani:
        subject = "Srećan rođendan!"
        message = (
            f"Neko misli na vas, srećan rođendan!!!\n\n"
            f"Vaš Alchemist"
        )

        # Email
        if clan.email:
            send_notification_email(clan.email, subject, message)
            Obavestenje.objects.create(clan=clan, tip='email', poruka=message, status='sent')
        # SMS
        if clan.telefon:
            sms_text = f"Neko misli na vas, srećan rođendan!!! Vaš Alchemist"
            send_notification_sms(clan.telefon, sms_text)
            Obavestenje.objects.create(clan=clan, tip='sms', poruka=sms_text, status='sent')