from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from .models import FCMToken, User
import json

@csrf_exempt
@require_http_methods(["POST"])
def save_fcm_token(request):
    """
    API endpoint za čuvanje FCM tokena
    
    POST /api/fcm-token/
    Body: {
        "token": "FCM_TOKEN_HERE",
        "user_id": 123,
        "device_type": "android"  # ili "ios"
    }
    """
    try:
        data = json.loads(request.body)
        token = data.get('token')
        user_id = data.get('user_id')
        device_type = data.get('device_type', 'android')
        
        if not token or not user_id:
            return JsonResponse({
                'status': 'error',
                'message': 'Token i user_id su obavezni!'
            }, status=400)
        
        # Pronađi korisnika
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Korisnik ne postoji!'
            }, status=404)
        
        # Sačuvaj ili ažuriraj token
        fcm_token, created = FCMToken.objects.update_or_create(
            token=token,
            defaults={
                'user': user,
                'device_type': device_type,
                'is_active': True
            }
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Token uspešno sačuvan!' if created else 'Token ažuriran!',
            'token_id': fcm_token.id
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Neispravan JSON!'
        }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def delete_fcm_token(request):
    """
    API endpoint za brisanje FCM tokena (npr. pri logout-u)
    
    POST /api/fcm-token/delete/
    Body: {
        "token": "FCM_TOKEN_HERE"
    }
    """
    try:
        data = json.loads(request.body)
        token = data.get('token')
        
        if not token:
            return JsonResponse({
                'status': 'error',
                'message': 'Token je obavezan!'
            }, status=400)
        
        # Deaktiviraj token
        FCMToken.objects.filter(token=token).update(is_active=False)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Token deaktiviran!'
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
