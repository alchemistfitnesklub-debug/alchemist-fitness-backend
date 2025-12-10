# klub_app/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, Clan  # ← DODAO SAM CLAN

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={'is_admin': False, 'is_trener': False, 'is_klijent': False}
        )

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    UserProfile.objects.get_or_create(
        user=instance,
        defaults={'is_admin': False, 'is_trener': False, 'is_klijent': False}
    )

# Automatsko kreiranje User naloga za nove članove
@receiver(post_save, sender=Clan)
def kreiraj_user_za_clana(sender, instance, created, **kwargs):
    """
    Kada se kreira novi Član, automatski kreiraj User nalog ako ne postoji
    """
    if not instance.user:
        # Generiši username iz imena
        username = instance.ime_prezime.lower().replace(' ', '_').replace('đ', 'dj').replace('š', 's').replace('č', 'c').replace('ć', 'c').replace('ž', 'z')
        
        # Proveri da li username već postoji
        original_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{original_username}_{counter}"
            counter += 1
        
        try:
            # Kreiraj User nalog
            user = User.objects.create_user(
                username=username,
                password='default123',
                email=instance.email if instance.email else f'{username}@alchemist.rs'
            )
            
            # Kreiraj UserProfile
            UserProfile.objects.create(user=user, is_klijent=True)
            
            # Poveži sa Član profilom
            instance.user = user
            instance.save()
            
            print(f"✅ Auto-kreiran nalog: {username} / default123")
            
        except Exception as e:
            print(f"❌ Greška pri auto-kreiranju naloga: {e}")

# ========================================
# SIGNAL ZA TRACKING PRISUSTVA RADNIKA
# DODATO 10.12.2024
# ========================================

from django.contrib.auth.signals import user_logged_in
from django.utils import timezone
from .models import RadnikPrisustvo

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """
    Automatski beleži prisustvo kada se radnik loguje
    Samo za trenere i admine, ne za klijente
    """
    try:
        profile = UserProfile.objects.get(user=user)
        
        # Samo za trenere i admine
        if profile.is_trener or profile.is_admin:
            today = timezone.now().date()
            
            # Kreiraj prisustvo ako ne postoji za danas
            RadnikPrisustvo.objects.get_or_create(
                user=user,
                datum=today,
                defaults={'vreme_logovanja': timezone.now()}
            )
    except UserProfile.DoesNotExist:
        pass  # Klijenti nemaju tracking
