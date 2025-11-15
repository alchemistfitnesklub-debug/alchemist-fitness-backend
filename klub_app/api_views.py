# klub_app/api_views.py
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timedelta
from .models import Clan, Uplata, Rezervacija, Obavestenje, UserProfile
from .serializers import (
    ClanSerializer, UplataSerializer, 
    RezervacijaSerializer, ObavestenjeSerializer
)

# LOGIN API - za mobilnu aplikaciju
@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = authenticate(username=username, password=password)
    
    if user:
        # Kreiraj ili uzmi postojeći token
        token, created = Token.objects.get_or_create(user=user)
        
        # Proveri da li je korisnik klijent
        try:
            profile = UserProfile.objects.get(user=user)
            if not profile.is_klijent:
                return Response({
                    'error': 'Samo klijenti mogu pristupiti mobilnoj aplikaciji'
                }, status=status.HTTP_403_FORBIDDEN)
        except UserProfile.DoesNotExist:
            return Response({
                'error': 'Profil ne postoji'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Uzmi podatke o članu
        try:
            clan = Clan.objects.get(user=user)
            clan_data = ClanSerializer(clan).data
        except Clan.DoesNotExist:
            clan_data = None
        
        return Response({
            'token': token.key,
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'clan': clan_data
        })
    
    return Response({
        'error': 'Pogrešno korisničko ime ili lozinka'
    }, status=status.HTTP_401_UNAUTHORIZED)

# LOGOUT API
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    # Obriši token
    request.user.auth_token.delete()
    return Response({'message': 'Uspešno ste se odjavili'})

# PROFIL KLIJENTA
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def moj_profil(request):
    try:
        clan = Clan.objects.get(user=request.user)
        serializer = ClanSerializer(clan)
        return Response(serializer.data)
    except Clan.DoesNotExist:
        return Response({
            'error': 'Profil člana ne postoji'
        }, status=status.HTTP_404_NOT_FOUND)

# ČLANARINA - aktivna i istorija
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def moja_clanarina(request):
    try:
        clan = Clan.objects.get(user=request.user)
        uplate = Uplata.objects.filter(clan=clan).order_by('-datum')
        
        # Pronađi aktivnu članarinu
        danas = timezone.now().date()
        aktivna_clanarina = uplate.filter(
            od_datum__lte=danas,
            do_datum__gte=danas
        ).first()
        
        return Response({
            'aktivna': UplataSerializer(aktivna_clanarina).data if aktivna_clanarina else None,
            'istorija': UplataSerializer(uplate, many=True).data
        })
    except Clan.DoesNotExist:
        return Response({
            'error': 'Profil člana ne postoji'
        }, status=status.HTTP_404_NOT_FOUND)

# REZERVACIJE - moje rezervacije
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def moje_rezervacije(request):
    try:
        clan = Clan.objects.get(user=request.user)
        danas = timezone.now().date()
        
        # Buduce rezervacije
        buduće = Rezervacija.objects.filter(
            clan=clan,
            datum__gte=danas
        ).order_by('datum', 'sat')
        
        # Prošle rezervacije
        prošle = Rezervacija.objects.filter(
            clan=clan,
            datum__lt=danas
        ).order_by('-datum', '-sat')[:10]  # Poslednje 10
        
        return Response({
            'buduće': RezervacijaSerializer(buduće, many=True).data,
            'prošle': RezervacijaSerializer(prošle, many=True).data
        })
    except Clan.DoesNotExist:
        return Response({
            'error': 'Profil člana ne postoji'
        }, status=status.HTTP_404_NOT_FOUND)

# KREIRANJE REZERVACIJE
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def kreiraj_rezervaciju(request):
    try:
        clan = Clan.objects.get(user=request.user)
        datum = request.data.get('datum')
        sat = request.data.get('sat')
        
        # Proveri radno vreme
        try:
            datum_obj = datetime.strptime(datum, '%Y-%m-%d')
            dan_u_nedelji = datum_obj.weekday()  # 0=ponedeljak, 6=nedelja
            
            # Nedelja zatvoreno
            if dan_u_nedelji == 6:
                return Response({
                    'error': 'Nedelja je neradni dan'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Subota samo do 14h
            if dan_u_nedelji == 5 and sat >= 15:
                return Response({
                    'error': 'Subotom radimo samo do 14h'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Radni dani 8-20h
            if dan_u_nedelji < 5 and (sat < 8 or sat > 20):
                return Response({
                    'error': 'Radno vreme je od 8h do 20h'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except ValueError:
            return Response({
                'error': 'Neispravan format datuma'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Proveri da li već postoji rezervacija za taj termin (maksimalno 6)
        if Rezervacija.objects.filter(datum=datum, sat=sat).count() >= 6:
            return Response({
                'error': 'Termin je popunjen (maksimalno 6 članova)'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Proveri da li korisnik već ima rezervaciju za taj termin
        # Proveri da li korisnik već ima rezervaciju za taj DAN (bilo koji sat)
        existing_reservation = Rezervacija.objects.filter(clan=clan, datum=datum).first()
        if existing_reservation:
          return Response({
        'error': f'Već imate rezervaciju za {datum} u {existing_reservation.sat}:00h. Molimo vas da je prvo otkažete.'
    }, status=status.HTTP_400_BAD_REQUEST)
        
        # Kreiraj rezervaciju
        rezervacija = Rezervacija.objects.create(
            clan=clan,
            datum=datum,
            sat=sat
        )
        
        # POŠALJI EMAIL OBAVEŠTENJE
        try:
            subject = f'Nova rezervacija - {clan.ime_prezime}'
            message = f'''
Nova rezervacija u Alchemist Fitness Club!

DETALJI:
--------
Klijent: {clan.ime_prezime}
Datum: {datum}
Vreme: {sat}:00h
Telefon: {clan.telefon}
Email: {clan.email}

Broj rezervacija za ovaj termin: {Rezervacija.objects.filter(datum=datum, sat=sat).count()}/6

--
Alchemist Fitness Club
            '''
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[settings.EMAIL_HOST_USER],  # Šalje tebi
                fail_silently=True,  # Ne prekida ako email ne uspe
            )
        except Exception as e:
            print(f"Email error: {e}")
            # Nastavlja dalje čak i ako email ne uspe
        
        return Response(
            RezervacijaSerializer(rezervacija).data,
            status=status.HTTP_201_CREATED
        )
    except Clan.DoesNotExist:
        return Response({
            'error': 'Profil člana ne postoji'
        }, status=status.HTTP_404_NOT_FOUND)

# OTKAŽI REZERVACIJU
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def otkazi_rezervaciju(request, pk):
    try:
        clan = Clan.objects.get(user=request.user)
        rezervacija = Rezervacija.objects.get(pk=pk, clan=clan)
        # Proveri da li je rezervacija za danas
        from datetime import date
        danas = date.today()
    
        if rezervacija.datum == danas:
         return Response({
            'error': 'Nije moguće otkazati termin istog dana. Molimo vas kontaktirajte klub telefonom ili emailom.'
        }, status=status.HTTP_400_BAD_REQUEST)
        
        # Sačuvaj podatke pre brisanja za email
        datum = rezervacija.datum
        sat = rezervacija.sat
        
        rezervacija.delete()
        
        # POŠALJI EMAIL O OTKAZIVANJU
        try:
            subject = f'Otkazana rezervacija - {clan.ime_prezime}'
            message = f'''
Rezervacija je otkazana u Alchemist Fitness Club.

DETALJI:
--------
Klijent: {clan.ime_prezime}
Datum: {datum}
Vreme: {sat}:00h
Telefon: {clan.telefon}
Email: {clan.email}

--
Alchemist Fitness Club
            '''
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[settings.EMAIL_HOST_USER],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Email error: {e}")
        
        return Response({
            'message': 'Rezervacija je otkazana'
        }, status=status.HTTP_200_OK)
    except Clan.DoesNotExist:
        return Response({
            'error': 'Profil člana ne postoji'
        }, status=status.HTTP_404_NOT_FOUND)
    except Rezervacija.DoesNotExist:
        return Response({
            'error': 'Rezervacija ne postoji'
        }, status=status.HTTP_404_NOT_FOUND)

# DOSTUPNI TERMINI (za zakazivanje)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dostupni_termini(request):
    datum = request.query_params.get('datum')
    
    if not datum:
        return Response({
            'error': 'Datum je obavezan parametar'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        datum_obj = datetime.strptime(datum, '%Y-%m-%d')
        dan_u_nedelji = datum_obj.weekday()  # 0=ponedeljak, 6=nedelja
        
        # Proveri da li je nedelja (6)
        if dan_u_nedelji == 6:
            return Response([])  # Vraća prazan niz - nedelja zatvoreno
        
        # Definiši termine prema danu
        if dan_u_nedelji == 5:  # Subota
            svi_termini = list(range(8, 15))  # 8:00 - 14:00
        else:  # Ponedeljak-Petak
            svi_termini = list(range(8, 21))  # 8:00 - 20:00
        
        # Zauzetost po terminima
        termini_data = []
        for sat in svi_termini:
            broj_rezervacija = Rezervacija.objects.filter(
                datum=datum,
                sat=sat
            ).count()
            
            termini_data.append({
                'sat': sat,
                'zauzeto': broj_rezervacija,
                'dostupno': 6 - broj_rezervacija,  # Maksimalno 6
                'popunjeno': broj_rezervacija >= 6  # Popunjeno ako ima 6 ili više
            })
        
        return Response(termini_data)
    except ValueError:
        return Response({
            'error': 'Neispravan format datuma'
        }, status=status.HTTP_400_BAD_REQUEST)

# OBAVEŠTENJA
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def moja_obavestenja(request):
    try:
        clan = Clan.objects.get(user=request.user)
        obavestenja = Obavestenje.objects.filter(clan=clan).order_by('-datum_slanja')[:20]
        
        return Response(
            ObavestenjeSerializer(obavestenja, many=True).data
        )
    except Clan.DoesNotExist:
        return Response({
            'error': 'Profil člana ne postoji'
        }, status=status.HTTP_404_NOT_FOUND)

# PROMENI LOZINKU
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def promeni_lozinku(request):
    stara_lozinka = request.data.get('stara_lozinka')
    nova_lozinka = request.data.get('nova_lozinka')
    
    if not stara_lozinka or not nova_lozinka:
        return Response({
            'error': 'Stara i nova lozinka su obavezne'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Proveri da li je stara lozinka tačna
    if not request.user.check_password(stara_lozinka):
        return Response({
            'error': 'Stara lozinka nije tačna'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Proveri da li je nova lozinka dovoljno jaka
    if len(nova_lozinka) < 6:
        return Response({
            'error': 'Nova lozinka mora imati najmanje 6 karaktera'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Postavi novu lozinku
    request.user.set_password(nova_lozinka)
    request.user.save()
    
    # Obriši stari token i kreiraj novi
    request.user.auth_token.delete()
    token = Token.objects.create(user=request.user)
    
    return Response({
        'message': 'Lozinka uspešno promenjena',
        'token': token.key  # Novi token
    })

# PROMENI USERNAME
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def promeni_username(request):
    novi_username = request.data.get('novi_username')
    
    if not novi_username:
        return Response({
            'error': 'Novi username je obavezan'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Proveri da li username već postoji
    if User.objects.filter(username=novi_username).exclude(id=request.user.id).exists():
        return Response({
            'error': 'Ovaj username već postoji'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Proveri dužinu
    if len(novi_username) < 3:
        return Response({
            'error': 'Username mora imati najmanje 3 karaktera'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Promeni username
    request.user.username = novi_username
    request.user.save()
    
    return Response({
        'message': 'Username uspešno promenjen',
        'novi_username': novi_username
    })
# KONTAKTIRAJ KLUB
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def kontaktiraj_klub(request):
    naslov = request.data.get('naslov')
    poruka = request.data.get('poruka')
    
    if not naslov or not poruka:
        return Response({
            'error': 'Naslov i poruka su obavezni'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        clan = Clan.objects.get(user=request.user)
        
        # Kreiraj email poruku
        email_body = f"""
Nova poruka od klijenta:

Od: {clan.ime_prezime} ({request.user.username})
Email: {clan.email}
Telefon: {clan.telefon}

Naslov: {naslov}

Poruka:
{poruka}

---
Poslato iz Alchemist Fitness mobilne aplikacije
        """
        
        # Pošalji email
        send_mail(
            subject=f'Kontakt od klijenta: {naslov}',
            message=email_body,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[settings.EMAIL_HOST_USER],
            fail_silently=False,
        )
        
        return Response({
            'message': 'Poruka uspešno poslata!'
        })
        
    except Clan.DoesNotExist:
        return Response({
            'error': 'Profil člana ne postoji'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Greška pri slanju: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# AŽURIRAJ FCM TOKEN (za push notifikacije)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def azuriraj_fcm_token(request):
    fcm_token = request.data.get('fcm_token')
    
    if not fcm_token:
        return Response({
            'error': 'FCM token je obavezan'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        profile = UserProfile.objects.get(user=request.user)
        profile.fcm_token = fcm_token
        profile.save()
        
        return Response({
            'message': 'FCM token uspešno ažuriran'
        })
    except UserProfile.DoesNotExist:
        return Response({
            'error': 'Profil ne postoji'
        }, status=status.HTTP_404_NOT_FOUND)