import firebase_admin
from firebase_admin import credentials, messaging
import os
import json
from django.conf import settings

# Inicijalizuj Firebase samo jednom
if not firebase_admin._apps:
    # Pokušaj učitati iz environment variable prvo
    firebase_creds = os.environ.get('FIREBASE_CREDENTIALS')
    
    if firebase_creds:
        # Production (Render) - iz environment variable
        cred_dict = json.loads(firebase_creds)
        cred = credentials.Certificate(cred_dict)
    else:
        # Local development - iz fajla
        cred_path = os.path.join(settings.BASE_DIR, 'credentials', 'firebase-key.json')
        cred = credentials.Certificate(cred_path)
    
    firebase_admin.initialize_app(cred)

def send_push_notification(fcm_token, title, body, data=None):
    """
    Šalje push notifikaciju na određeni FCM token
    
    Args:
        fcm_token: FCM registration token
        title: Naslov notifikacije
        body: Tekst notifikacije
        data: Dodatni podaci (opciono)
    
    Returns:
        Response string ili None ako greška
    """
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data if data else {},
            token=fcm_token,
        )
        
        response = messaging.send(message)
        print(f'✅ Notifikacija poslata! Response: {response}')
        return response
    
    except Exception as e:
        print(f'❌ Greška pri slanju notifikacije: {e}')
        return None

def send_push_notification_to_multiple(fcm_tokens, title, body, data=None):
    """
    Šalje push notifikaciju na više FCM tokena odjednom
    
    Args:
        fcm_tokens: Lista FCM registration tokena
        title: Naslov notifikacije
        body: Tekst notifikacije
        data: Dodatni podaci (opciono)
    
    Returns:
        BatchResponse objekat
    """
    try:
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data if data else {},
            tokens=fcm_tokens,
        )
        
        response = messaging.send_multicast(message)
        print(f'✅ Poslato na {response.success_count} uređaja!')
        if response.failure_count > 0:
            print(f'❌ Neuspešno: {response.failure_count}')
        
        return response
    
    except Exception as e:
        print(f'❌ Greška pri slanju notifikacija: {e}')
        return None
