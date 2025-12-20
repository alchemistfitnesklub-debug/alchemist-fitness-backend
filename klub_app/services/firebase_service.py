import firebase_admin
from firebase_admin import credentials, messaging
import os
import json
from django.conf import settings

# Inicijalizuj Firebase samo jednom
if not firebase_admin._apps:
    # Pokušaj prvo da učitaš iz environment variable (Render)
    firebase_creds = os.environ.get('FIREBASE_CREDENTIALS')
    
    if firebase_creds:
        # Production (Render) - čitaj iz environment variable
        cred_dict = json.loads(firebase_creds)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        print('✅ Firebase initialized from environment variable')
    else:
        # Development (lokalno) - čitaj iz fajla
        cred_path = os.path.join(settings.BASE_DIR, 'credentials', 'firebase-key.json')
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        print('✅ Firebase initialized from file')


def send_push_notification(fcm_token, title, body, data=None):
    """
    Šalje push notifikaciju na određeni FCM token (Android + iOS)
    
    Args:
        fcm_token: FCM registration token
        title: Naslov notifikacije
        body: Tekst notifikacije
        data: Dodatni podaci (opciono)
    
    Returns:
        Response string ili None ako greška
    """
    try:
        # iOS APNs konfiguracija - OBAVEZNO za iOS!
        apns_config = messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    alert=messaging.ApsAlert(
                        title=title,
                        body=body,
                    ),
                    badge=1,
                    sound='default',
                    content_available=True,  # Omogućava background processing
                )
            )
        )
        
        # Android konfiguracija
        android_config = messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                title=title,
                body=body,
                sound='default',
            )
        )
        
        # Univerzalna poruka koja radi za iOS + Android
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data if data else {},
            token=fcm_token,
            apns=apns_config,      # ← iOS specifično
            android=android_config  # ← Android specifično
        )
        
        response = messaging.send(message)
        print(f'✅ Notifikacija poslata! Response: {response}')
        return response
    
    except Exception as e:
        print(f'❌ Greška pri slanju notifikacije: {e}')
        print(f'Token: {fcm_token[:50]}...')  # Debug - prvih 50 karaktera
        return None


def send_push_notification_to_multiple(fcm_tokens, title, body, data=None):
    """
    Šalje push notifikaciju na više FCM tokena odjednom (Android + iOS)
    
    Args:
        fcm_tokens: Lista FCM registration tokena
        title: Naslov notifikacije
        body: Tekst notifikacije
        data: Dodatni podaci (opciono)
    
    Returns:
        BatchResponse objekat
    """
    try:
        # iOS APNs konfiguracija
        apns_config = messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    alert=messaging.ApsAlert(
                        title=title,
                        body=body,
                    ),
                    badge=1,
                    sound='default',
                    content_available=True,
                )
            )
        )
        
        # Android konfiguracija
        android_config = messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                title=title,
                body=body,
                sound='default',
            )
        )
        
        # Multicast poruka za batch slanje
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data if data else {},
            tokens=fcm_tokens,
            apns=apns_config,      # ← iOS specifično
            android=android_config  # ← Android specifično
        )
        
        response = messaging.send_multicast(message)
        print(f'✅ Poslato na {response.success_count} uređaja!')
        if response.failure_count > 0:
            print(f'❌ Neuspešno: {response.failure_count}')
            # Debug - prikaži greške
            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    print(f'  - Token {idx}: {resp.exception}')
        
        return response
    
    except Exception as e:
        print(f'❌ Greška pri slanju notifikacija: {e}')
        return None
