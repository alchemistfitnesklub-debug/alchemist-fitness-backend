from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout, login, authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta, datetime, date
from decimal import Decimal
import time
import urllib.parse
import base64
import json
import requests
from django.http import JsonResponse, HttpResponse
from django.utils.dateparse import parse_date
from django.core.mail import send_mail
from twilio.rest import Client
from django.conf import settings
import phonenumbers
import pandas as pd
import os
from django.core.files import File
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt
import firebase_admin
from firebase_admin import credentials, messaging
from django.core.files.storage import default_storage
from .models import Clan, Uplata, Rezervacija, Stock, Sale, Obavestenje, UserProfile, Merenje, ZatvorenTermin
from .forms import ClanForm, UplataForm, SaleForm, MerenjeForm
from .services.firebase_service import send_push_notification
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate('/Users/dusansamardzic/fitnes_klub_app/firebase_service_account.json')
        firebase_admin.initialize_app(cred)


def admin_only(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        try:
            profile = request.user.userprofile
            if not profile.is_admin:
                if profile.is_trener:
                    messages.warning(request, 'Ova stranica je dostupna samo administratoru.')
                    return redirect('trener_home')
                messages.error(request, 'Nemate pristup ovoj stranici.')
                return redirect('login')
            return view_func(request, *args, **kwargs)
        except (AttributeError, UserProfile.DoesNotExist):
            return redirect('login')
    return wrapper


def trener_or_admin_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        try:
            profile = request.user.userprofile
            if not (profile.is_admin or profile.is_trener):
                messages.error(request, 'Nemate dozvolu.')
                return redirect('login')
            return view_func(request, *args, **kwargs)
        except (AttributeError, UserProfile.DoesNotExist):
            return redirect('login')
    return wrapper


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        recaptcha_response = request.POST.get('g-recaptcha-response')

        if not recaptcha_response:
            messages.error(request, 'Morate popuniti reCAPTCHA.')
            return render(request, 'registration/login.html')

        verify = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={'secret': settings.RECAPTCHA_PRIVATE_KEY, 'response': recaptcha_response}
        ).json()

        if not verify.get('success'):
            messages.error(request, 'reCAPTCHA greška. Pokušajte ponovo.')
            return render(request, 'registration/login.html')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Dobrodošao, {username}!')

            # ================== PRVO PROVERI UserProfile (trener/admin) ==================
            try:
                profile = UserProfile.objects.get(user=user)
                
                # Ako je admin (preko UserProfile)
                if profile.is_admin:
                    print(f"✅ Admin login: {user.username}")
                    return redirect('dashboard')
                
                # Ako je trener (preko UserProfile)
                if profile.is_trener:
                    print(f"✅ Trener login: {user.username}")
                    return redirect('rezervacije')  # Treneri idu na rezervacije
                
            except UserProfile.DoesNotExist:
                print(f"⚠️ UserProfile ne postoji za {user.username}, proveravam Clan...")
            
            # ================== AKO NIJE TRENER/ADMIN, PROVERI CLAN ==================
            try:
                clan = Clan.objects.get(user=user)
                print(f"🔍 DEBUG: User={user.username}, Clan={clan.ime_prezime}, Tip='{clan.tip}'")

                if clan.tip == 'Trener':
                    print("✅ Redirect to trener_home")
                    return redirect('trener_home')
                elif clan.tip == 'Klijent':
                    print("✅ Redirect to klijent_dashboard")
                    return redirect('klijent_dashboard')
                elif clan.tip == 'Admin':
                    print("✅ Redirect to dashboard (admin)")
                    return redirect('dashboard')
                else:
                    print(f"❌ Nepoznat tip: '{clan.tip}'")
                    messages.error(request, 'Nemate dodeljenu ulogu.')
                    auth_logout(request)
                    return render(request, 'registration/login.html')

            except Clan.DoesNotExist:
                print(f"❌ Clan.DoesNotExist za korisnika {user.username}")
                messages.error(request, 'Niste povezani sa profilom člana.')
                auth_logout(request)
                return render(request, 'registration/login.html')
            # ==============================================================

        else:
            messages.error(request, 'Pogrešno korisničko ime ili lozinka.')
            return render(request, 'registration/login.html')

    return render(request, 'registration/login.html')


@login_required
def pocetna(request):
    try:
        profile = request.user.userprofile
        
        # Admin ide na Dashboard
        if profile.is_admin:
            return redirect('dashboard')
        
        # Trener ide na Rezervacije
        if profile.is_trener:
            return redirect('rezervacije')
        
    except UserProfile.DoesNotExist:
        pass
    
    # Ako nema profil, proveravamo Clan
    try:
        clan = Clan.objects.get(user=request.user)
        if clan.tip == 'Admin':
            return redirect('dashboard')
        elif clan.tip == 'Trener':
            return redirect('trener_home')
        elif clan.tip == 'Klijent':
            return redirect('klijent_dashboard')
    except Clan.DoesNotExist:
        pass
    
    # Default fallback
    return redirect('login')


@admin_only
def dashboard(request):
    try:
        # ========================================
        # DEFAULT PERIOD: DANAS + 30 DANA UNAPRED
        # ========================================
        from_date_str = request.GET.get('from_date')
        to_date_str = request.GET.get('to_date')

        today = timezone.now().date()
        
        if from_date_str:
            from_date = parse_date(from_date_str)
            if not from_date:
                from_date = today
        else:
            from_date = today  # ← PROMENA: Danas umesto -30 dana

        if to_date_str:
            to_date = parse_date(to_date_str)
            if not to_date:
                to_date = today + timedelta(days=30)
        else:
            to_date = today + timedelta(days=30)  # ← PROMENA: +30 dana unapred

        # Postojeći kod za uplate, sales, itd...
        uplate = Uplata.objects.filter(od_datum__gte=from_date, od_datum__lte=to_date).select_related('clan')
        daily_payments = uplate.values('od_datum').annotate(total=Sum('iznos')).order_by('od_datum')
        sales = Sale.objects.filter(datum__date__gte=from_date, datum__date__lte=to_date).select_related('stock')
        daily_sales = sales.values('datum__date').annotate(total=Sum('price')).order_by('datum__date')
        water_sales = sales.filter(stock__naziv__icontains='voda').values('datum__date').annotate(total=Sum('price')).order_by('datum__date')

        labels = [entry['od_datum'].strftime('%Y-%m') for entry in daily_payments if entry['od_datum']]
        data = [float(entry['total']) or 0 for entry in daily_payments]
        bar_data = [0] * len(labels)
        water_data = [0] * len(labels)

        for sale in daily_sales:
            date_str = sale['datum__date'].strftime('%Y-%m')
            if date_str in labels:
                idx = labels.index(date_str)
                bar_data[idx] = float(sale['total']) or 0

        for ws in water_sales:
            date_str = ws['datum__date'].strftime('%Y-%m')
            if date_str in labels:
                idx = labels.index(date_str)
                water_data[idx] = float(ws['total']) or 0

        expirations_in_period = Uplata.objects.filter(do_datum__gte=from_date, do_datum__lte=to_date).select_related('clan')
        total_payments_in_period = uplate.aggregate(total=Sum('iznos'))['total'] or 0
        total_bar_revenue = sales.aggregate(total=Sum('price'))['total'] or 0
        total_members = Clan.objects.count()
        active_memberships = Uplata.objects.filter(do_datum__gte=timezone.now().date()).count()
        total_revenue = Uplata.objects.aggregate(total=Sum('iznos'))['total'] or 0
        recent_obavestenja = Obavestenje.objects.all().order_by('-datum_slanja').select_related('clan')[:5]

        monthly_payments = uplate.values('datum__year', 'datum__month').annotate(total=Sum('iznos')).order_by('datum__year', 'datum__month')
        monthly_labels = [f"{entry['datum__year']}-{entry['datum__month']:02d}" for entry in monthly_payments]
        monthly_data = [float(entry['total']) or 0 for entry in monthly_payments]

        context = {
            'labels': json.dumps(labels),
            'data': json.dumps(data),
            'bar_data': json.dumps(bar_data),
            'water_data': json.dumps(water_data),
            'monthly_labels': json.dumps(monthly_labels),
            'monthly_data': json.dumps(monthly_data),
            'expirations_in_period': expirations_in_period,
            'total_payments_in_period': total_payments_in_period,
            'total_bar_revenue': total_bar_revenue,
            'total_members': total_members,
            'active_memberships': active_memberships,
            'total_revenue': total_revenue,
            'recent_obavestenja': recent_obavestenja,
            'from_date': from_date.strftime('%Y-%m-%d'),
            'to_date': to_date.strftime('%Y-%m-%d'),
            'today': today.strftime('%Y-%m-%d'),  # ← NOVO
            'uplate': uplate,
        }
        return render(request, 'dashboard.html', context)
    except Exception as e:
        messages.error(request, f'Greška u dashboardu: {str(e)}')
        return redirect('klijenti')


@admin_only
def statistike(request):
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    if from_date_str:
        from_date = parse_date(from_date_str)
        if not from_date:
            from_date = timezone.now().date() - timedelta(days=30)
    else:
        from_date = timezone.now().date() - timedelta(days=30)
    if to_date_str:
        to_date = parse_date(to_date_str)
        if not to_date:
            to_date = timezone.now().date()
    else:
        to_date = timezone.now().date()

    rezervacije = Rezervacija.objects.filter(datum__gte=from_date, datum__lte=to_date).select_related('clan')
    clanovi_stats = rezervacije.values('clan__ime_prezime').annotate(total=Count('id')).order_by('-total')
    months = max((to_date - from_date).days / 30.0, 1)
    avg_visits = [
        {'ime_prezime': stat['clan__ime_prezime'], 'avg_visits': round(stat['total'] / months, 2)}
        for stat in clanovi_stats
    ]

    labels = [stat['clan__ime_prezime'] for stat in clanovi_stats]
    data = [stat['total'] for stat in clanovi_stats]

    daily_visits = rezervacije.values('datum__week_day').annotate(total=Count('id')).order_by('datum__week_day')
    daily_labels = ['Nedelja', 'Ponedeljak', 'Utorak', 'Sreda', 'Četvrtak', 'Petak', 'Subota']
    daily_data = [0] * 7
    for entry in daily_visits:
        daily_data[entry['datum__week_day'] - 1] = entry['total']

    if request.GET.get('export') == 'excel':
        df = pd.DataFrame({
            'Klijent': labels,
            'Broj rezervacija': data,
            'Prosečan broj poseta mesečno': [v['avg_visits'] for v in avg_visits]
        })
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=statistike.xlsx'
        df.to_excel(response, index=False)
        return response

    context = {
        'labels': json.dumps(labels[:10]),
        'data': json.dumps(data[:10]),
        'daily_labels': json.dumps(daily_labels),
        'daily_data': json.dumps(daily_data),
        'from_date': from_date.strftime('%Y-%m-%d'),
        'to_date': to_date.strftime('%Y-%m-%d'),
        'clanovi_stats': clanovi_stats[:10],
        'avg_visits': avg_visits[:10],
    }
    return render(request, 'statistike.html', context)


@trener_or_admin_required
def klijenti(request):
    if request.method == 'POST':
        if 'excel_file' in request.FILES:
            try:
                excel_file = request.FILES['excel_file']
                df = pd.read_excel(excel_file)
                created_count = 0
                updated_count = 0
                errors = []
                if df.empty:
                    messages.error(request, 'Excel fajl je prazan!')
                    return redirect('klijenti')
                for index, row in df.iterrows():
                    try:
                        ime_prezime = str(row.get('Ime i prezime', '') or row.get('ime_prezime', '') or '').strip()
                        telefon = str(row.get('Mobilni telefon', '') or row.get('telefon', '') or '').strip()
                        email = str(row.get('E-mail', '') or row.get('email', '') or '').strip()
                        datum_rodjenja_str = row.get('Datum rodjenja', None)
                        datum_rodjenja = None
                        if pd.notna(datum_rodjenja_str):
                            datum_rodjenja_str = str(datum_rodjenja_str).strip()
                            for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d'):
                                try:
                                    datum_rodjenja = datetime.strptime(datum_rodjenja_str, fmt).date()
                                    break
                                except ValueError:
                                    continue
                            if not datum_rodjenja:
                                errors.append(f"Red {index+2}: Nevalidan datum rodjenja: {datum_rodjenja_str}")
                                continue
                        krediti = float(row.get('Saldo', 0) or row.get('krediti_voda', 0) or 0)
                        if not ime_prezime:
                            errors.append(f"Red {index+2}: Nedostaje ime i prezime")
                            continue

                        clan = None
                        if email:
                            clan = Clan.objects.filter(email__iexact=email).first()
                        if not clan and telefon:
                            clan = Clan.objects.filter(telefon=telefon).first()
                        if not clan:
                            clan = Clan.objects.filter(ime_prezime__iexact=ime_prezime).first()

                        is_new = clan is None
                        if is_new:
                            clan = Clan()
                            username = f"clan_{int(time.time())}_{index}"
                            password = "default123"
                            user = User.objects.create_user(username=username, password=password)
                            profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'is_klijent': True})
                            profile.is_klijent = True
                            profile.save()
                            clan.user = user
                            created_count += 1
                        else:
                            updated_count += 1

                        clan.ime_prezime = ime_prezime
                        clan.telefon = telefon or clan.telefon
                        clan.email = email or clan.email
                        clan.datum_rodjenja = datum_rodjenja or clan.datum_rodjenja
                        clan.krediti_voda = krediti

                        old_slika = clan.slika.name if clan.slika else None
                        if 'Slika' in row and pd.notna(row['Slika']):
                            slika = str(row['Slika']).strip()
                            if slika:
                                try:
                                    if os.path.exists(slika):
                                        with open(slika, 'rb') as f:
                                            clan.slika.save(os.path.basename(slika), File(f), save=False)
                                    elif slika.startswith(('http://', 'https://')):
                                        resp = requests.get(slika, timeout=10)
                                        if resp.status_code == 200:
                                            filename = os.path.basename(urllib.parse.urlparse(slika).path) or f"slika_{index}.jpg"
                                            clan.slika.save(filename, ContentFile(resp.content), save=False)
                                    elif slika.startswith('data:image'):
                                        format, imgstr = slika.split(';base64,')
                                        ext = format.split('/')[-1]
                                        data = ContentFile(base64.b64decode(imgstr), name=f'clan_{index}.{ext}')
                                        clan.slika.save(f'clan_{index}.{ext}', data, save=False)
                                except Exception as e:
                                    errors.append(f"Greška sa slikom za {ime_prezime}: {e}")

                        clan.full_clean()
                        clan.save()

                        if old_slika and clan.slika.name != old_slika:
                            if default_storage.exists(old_slika):
                                default_storage.delete(old_slika)

                        if is_new and clan.email:
                            subject = "Fitness Klub - Podaci za logovanje"
                            message = f"Dobrodošli!\nUsername: {username}\nLozinka: default123\nhttp://127.0.0.1:8000/login/"
                            send_mail(subject, message, settings.EMAIL_HOST_USER, [clan.email], fail_silently=True)

                    except Exception as e:
                        errors.append(f"Red {index+2}: {str(e)}")

                msg = f'Excel uvoz završen! Dodato: {created_count}, Ažurirano: {updated_count}'
                if errors:
                    msg += f" | Greške: {len(errors)}"
                    messages.warning(request, msg)
                else:
                    messages.success(request, msg)
                return redirect('klijenti')
            except Exception as e:
                messages.error(request, f'Greška u Excel uvozu: {str(e)}')
                return redirect('klijenti')
        else:
            form = ClanForm(request.POST, request.FILES)
            if form.is_valid():
                clan = form.save(commit=False)
                if not clan.user:
                    username = f"clan_{int(time.time())}"
                    user = User.objects.create_user(username=username, password="default123")
                    profile, created = UserProfile.objects.get_or_create(user=user, defaults={'is_klijent': True})
                    profile.is_klijent = True
                    profile.save()
                    clan.user = user
                clan.save()
                messages.success(request, 'Klijent uspešno dodat/ažuriran!')
                return redirect('klijenti')
            else:
                messages.error(request, f'Greška: {form.errors.as_text()}')

    if request.GET.get('export') == 'excel':
        df = pd.DataFrame(list(Clan.objects.values('ime_prezime', 'telefon', 'email', 'datum_rodjenja', 'krediti_voda')))
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=klijenti.xlsx'
        df.to_excel(response, index=False)
        return response

    q = request.GET.get('q', '')
    clanovi = Clan.objects.filter(ime_prezime__icontains=q) if q else Clan.objects.all().order_by('-id')
    form = ClanForm()
    context = {'clanovi': clanovi, 'form': form, 'q': q}
    return render(request, 'klijenti.html', context)


@trener_or_admin_required
def sank(request):
    """Šank modul sa statistikama i upravljanjem"""
    
    if request.method == 'POST':
        if 'add_product' in request.POST:
            naziv = request.POST.get('naziv')
            kolicina = request.POST.get('kolicina')
            cena = request.POST.get('cena')
            try:
                kolicina = int(kolicina)
                cena = float(cena)
                if naziv and kolicina >= 0 and cena >= 0:
                    Stock.objects.create(naziv=naziv, kolicina=kolicina, cena=cena)
                    messages.success(request, 'Proizvod dodat!')
                else:
                    messages.error(request, 'Nevalidan unos za naziv, količinu ili cenu!')
            except ValueError:
                messages.error(request, 'Nevalidan unos za količinu ili cenu!')
            return redirect('sank')
        
        elif 'update_stock' in request.POST:
            stock_id = request.POST.get('stock_id')
            dodatna_kolicina = request.POST.get('dodatna_kolicina')
            try:
                dodatna_kolicina = int(dodatna_kolicina)
                stock = Stock.objects.get(id=stock_id)
                if dodatna_kolicina > 0:
                    stock.kolicina += dodatna_kolicina
                    stock.save()
                    messages.success(request, 'Količina ažurirana!')
                else:
                    messages.error(request, 'Dodatna količina mora biti veća od 0!')
            except ValueError:
                messages.error(request, 'Nevalidan unos za količinu!')
            except Stock.DoesNotExist:
                messages.error(request, 'Proizvod nije pronađen.')
            return redirect('sank')
        
        else:
            form = SaleForm(request.POST)
            if form.is_valid():
                sale = form.save(commit=False)
                clan = form.cleaned_data['clan']
                stock = form.cleaned_data['stock']
                kolicina = form.cleaned_data['kolicina']
                ukupna_cena = stock.cena * kolicina
                
                if stock.kolicina < kolicina:
                    messages.error(request, 'Nedovoljno zaliha!')
                    return redirect('sank')
                
                clan.krediti_voda -= float(ukupna_cena)
                clan.save()
                
                stock.kolicina -= kolicina
                stock.save()
                
                sale.price = ukupna_cena
                sale.save()
                
                messages.success(request, f'Prodaja uspešna! Skinuto {ukupna_cena:.2f} EUR. {clan.ime_prezime} ima {clan.krediti_voda:.2f} EUR kredita preostalo.')
                
                if clan.krediti_voda < 0:
                    messages.warning(request, f'{clan.ime_prezime} je u minusu: -{abs(clan.krediti_voda):.2f} EUR!')
                
                return redirect('sank')
            else:
                messages.error(request, f'Greška pri prodaji: {form.errors.as_text()}')
    
    danas = date.today()
    danas_zarada = Sale.objects.filter(datum__date=danas).aggregate(total=Sum('price'))['total'] or 0
    danas_prodato = Sale.objects.filter(datum__date=danas).aggregate(total=Sum('kolicina'))['total'] or 0
    ukupno_proizvoda = Stock.objects.count()
    najprodavaniji_query = Sale.objects.filter(datum__date=danas).values('stock__naziv').annotate(ukupno=Sum('kolicina')).order_by('-ukupno').first()
    najprodavaniji = najprodavaniji_query['stock__naziv'] if najprodavaniji_query else None
    
    stocks = Stock.objects.all()
    
    context = {
        'clanovi': Clan.objects.all(),
        'stocks': stocks,
        'sales': Sale.objects.all().order_by('-datum').select_related('clan', 'stock'),
        'sale_form': SaleForm(),
        'stocks_json': json.dumps([{'id': s.id, 'cena': float(s.cena)} for s in stocks]),
        'danas_zarada': float(danas_zarada),
        'danas_prodato': int(danas_prodato),
        'ukupno_proizvoda': ukupno_proizvoda,
        'najprodavaniji': najprodavaniji,
    }
    
    return render(request, 'sank.html', context)


@trener_or_admin_required
def sank_json_clanovi(request):
    q = request.GET.get('q', '')
    clanovi = Clan.objects.filter(ime_prezime__icontains=q).values('id', 'ime_prezime')[:20]
    return JsonResponse(list(clanovi), safe=False)


@trener_or_admin_required
def obavestenja(request):
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    failed_only = request.GET.get('failed_only') == 'true'
    if not from_date:
        from_date = (timezone.now() - timedelta(days=30)).date()
    if not to_date:
        to_date = timezone.now().date()
    from_date = parse_date(from_date) if isinstance(from_date, str) else from_date
    to_date = parse_date(to_date) if isinstance(to_date, str) else to_date
    query = Obavestenje.objects.filter(
        datum_slanja__date__gte=from_date,
        datum_slanja__date__lte=to_date
    ).select_related('clan').order_by('-datum_slanja')
    if failed_only:
        query = query.filter(status='failed')
    obavestenja = query[:50]
    context = {
        'obavestenja': obavestenja,
        'from_date': from_date.strftime('%Y-%m-%d') if from_date else '',
        'to_date': to_date.strftime('%Y-%m-%d') if to_date else '',
        'failed_only': failed_only,
    }
    return render(request, 'obavestenja.html', context)


@trener_or_admin_required
def rezervacije(request):
    if request.method == 'POST':
        action = request.POST.get('action', 'book')
        clan_id = request.POST.get('clan_id')
        datum = request.POST.get('datum')
        sat_str = request.POST.get('sat')
        if not (clan_id and datum and sat_str):
            return JsonResponse({'status': 'error', 'message': 'Nedostaju podaci.'})
        try:
            sat = int(sat_str.split(':')[0])
            if sat < 6 or sat > 22:
                return JsonResponse({'status': 'error', 'message': 'Sat mora biti između 6 i 22!'})
        except:
            return JsonResponse({'status': 'error', 'message': 'Nevalidan sat!'})
        
        # ========================================
        # PROVERI DA LI JE TERMIN ZATVOREN
        # ========================================
        zatvoren_termin = ZatvorenTermin.objects.filter(
            datum=datum,
            sat=sat
        ).exists()
        
        if zatvoren_termin:
            return JsonResponse({
                'status': 'error',
                'message': 'Ovaj termin je zatvoren i nije dostupan za rezervaciju.'
            })
        # ========================================
        
        try:
            clan = get_object_or_404(Clan, id=clan_id)
            if action != 'confirm':
                existing = Rezervacija.objects.filter(clan=clan, datum=datum).first()
                if existing:
                    return JsonResponse({
                        'status': 'confirm',
                        'message': f'{clan.ime_prezime} već ima rezervaciju u {existing.sat}:00. Da li želite da dodate još jednu?'
                    })
                count = Rezervacija.objects.filter(datum=datum, sat=sat).count()
                if count >= 6:
                    return JsonResponse({'status': 'error', 'message': 'Slot je pun! Maksimalno 6 po satu.'})
            Rezervacija.objects.create(clan=clan, datum=datum, sat=sat)
            return JsonResponse({
                'status': 'success',
                'message': f'Rezervacija za {clan.ime_prezime} u {sat}:00 uspešno dodata!'
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Greška: {str(e)}'})

    today = timezone.now().date()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    from_date = request.GET.get('from_date') or monday.strftime('%Y-%m-%d')
    to_date = request.GET.get('to_date') or sunday.strftime('%Y-%m-%d')
    context = {'from_date': from_date, 'to_date': to_date}
    return render(request, 'rezervacije.html', context)


@trener_or_admin_required
def rezervacije_lista(request):
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    if not from_date:
        from_date = timezone.now().date()
    else:
        from_date = parse_date(from_date)
    if not to_date:
        to_date = timezone.now().date()
    else:
        to_date = parse_date(to_date)
    rezervacije = Rezervacija.objects.filter(
        datum__gte=from_date,
        datum__lte=to_date
    ).select_related('clan').order_by('-datum', '-sat')
    context = {
        'rezervacije': rezervacije,
        'from_date': from_date.strftime('%Y-%m-%d'),
        'to_date': to_date.strftime('%Y-%m-%d'),
    }
    return render(request, 'rezervacije_lista.html', context)


@trener_or_admin_required
def profil(request, clan_id):
    try:
        profile = request.user.userprofile
    except (AttributeError, UserProfile.DoesNotExist):
        messages.error(request, 'Nemate pristup.')
        return redirect('login')

    clan = get_object_or_404(Clan, id=clan_id)
    if profile.is_klijent and clan.user != request.user:
        messages.error(request, 'Nemate pristup ovom profilu.')
        return redirect('klijent_dashboard')

    uplate = Uplata.objects.filter(clan=clan).select_related('clan')
    istorija_rezervacija = Rezervacija.objects.filter(clan=clan).order_by('-datum').select_related('clan')
    is_trener = profile.is_trener if hasattr(profile, 'is_trener') else False
    is_klijent = profile.is_klijent if hasattr(profile, 'is_klijent') else False

    if request.method == 'POST':
        if is_klijent:
            messages.error(request, 'Klijenti ne mogu menjati podatke.')
            return redirect('profil', clan_id=clan_id)

        action = request.POST.get('action')

        if action == 'add_uplata':
            form = UplataForm(request.POST)
            if form.is_valid():
                uplata = form.save(commit=False)
                uplata.clan = clan
                uplata.datum = form.cleaned_data['od_datum']
                uplata.do_datum = form.cleaned_data['do_datum']
                uplata.save()
                messages.success(request, f'Članarina uspešno dodata! Iznos: {uplata.iznos} EUR. Važi do: {uplata.do_datum.strftime("%d.%m.%Y")}')
            else:
                messages.error(request, f'Greška: {form.errors.as_text()}')

        elif action == 'update_clan':
            form = ClanForm(request.POST, request.FILES, instance=clan)
            if form.is_valid():
                form.save()
                messages.success(request, 'Podaci ažurirani!')
            else:
                messages.error(request, f'Greška pri ažuriranju: {form.errors.as_text()}')

        elif action == 'add_kredit':
            if not (profile.is_trener or profile.is_admin):
                messages.error(request, 'Nemate dozvolu.')
                return redirect('profil', clan_id=clan_id)
            try:
                kredit_iznos_str = request.POST.get('kredit_iznos', '').strip()
                if not kredit_iznos_str:
                    messages.error(request, 'Molimo unesite iznos.')
                    return redirect('profil', clan_id=clan_id)
                
                kredit_iznos_str = kredit_iznos_str.replace(',', '.')
                iznos = float(kredit_iznos_str)
                
                if iznos <= 0:
                    messages.error(request, 'Iznos mora biti veći od 0.')
                else:
                    clan.krediti_voda += iznos
                    clan.save()
                    messages.success(request, f'Uspešno dodato {iznos:.2f} € kredita za vodu! Trenutni kredit: {clan.krediti_voda:.2f} €')
            except ValueError:
                messages.error(request, 'Neispravan format iznosa. Molimo unesite broj (npr. 10.00 ili 10,50).')
            except Exception as e:
                messages.error(request, f'Greška pri dodavanju kredita: {str(e)}')
            return redirect('profil', clan_id=clan_id)

        elif action == 'send_message':
            message_text = request.POST.get('message_text')
            send_to = request.POST.getlist('send_to')
            client = Client(settings.TWILIO_SID, settings.TWILIO_AUTH_TOKEN)
            if 'email' in send_to and clan.email:
                send_mail(
                    'Obaveštenje iz kluba',
                    message_text,
                    settings.EMAIL_HOST_USER,
                    [clan.email],
                    fail_silently=True
                )
                Obavestenje.objects.create(
                    clan=clan,
                    tip='email',
                    poruka=message_text,
                    status='sent'
                )
            if 'sms' in send_to and clan.telefon:
                try:
                    telefon = str(clan.telefon).replace('.0', '').replace(' ', '')
                    if not telefon.startswith('+'):
                        telefon = '+381' + telefon.lstrip('0')
                    parsed_number = phonenumbers.parse(telefon, "RS")
                    if phonenumbers.is_valid_number(parsed_number):
                        sms_obj = client.messages.create(
                            body=message_text,
                            from_=settings.TWILIO_PHONE_NUMBER,
                            to=phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
                        )
                        status = sms_obj.status
                        display_status = 'delivered' if status in ['delivered', 'sent', 'queued'] else 'failed'
                        Obavestenje.objects.create(
                            clan=clan,
                            tip='sms',
                            poruka=message_text,
                            status=display_status
                        )
                    else:
                        Obavestenje.objects.create(
                            clan=clan,
                            tip='sms',
                            poruka=message_text,
                            status='failed'
                        )
                except Exception as e:
                    Obavestenje.objects.create(
                        clan=clan,
                        tip='sms',
                        poruka=message_text,
                        status='failed'
                    )
            messages.success(request, 'Poruka poslata!')

        elif action == 'send_login':
            if not clan.user:
                base = clan.ime_prezime.lower()
                translit = str.maketrans('đščćžĐŠČĆŽ', 'djscczDSCCZ')
                base = base.translate(translit)
                username = ''.join(c if c.isalnum() else '_' for c in base.strip())
                original_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{original_username}_{counter}"
                    counter += 1

                password = "default123"
                user = User.objects.create_user(username=username, password=password, email=clan.email)
                UserProfile.objects.get_or_create(user=user, defaults={'is_klijent': True})
                clan.user = user
                clan.save()
            else:
                username = clan.user.username
            # ========================================
            # HTML EMAIL SA APP STORE DUGMETOM
            # ========================================
            if clan.email:
                from django.core.mail import EmailMessage
                
                # App Store Links
                ios_link = "https://apps.apple.com/us/app/alchemist-health-club/id6756538673"
                android_link = "OVDE_CE_BITI_GOOGLE_PLAY_LINK"  # ← Ovo ces kasnije zameniti!
                
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                </head>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f4f4f4; margin: 0; padding: 0;">
                    <div style="max-width: 600px; margin: 30px auto; background-color: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        
                        <!-- Header -->
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                            <h1 style="color: white; margin: 0; font-size: 28px;">🔐 Pristupni podaci</h1>
                            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">Alchemist Health Club</p>
                        </div>
                        
                        <!-- Body -->
                        <div style="padding: 40px 30px;">
                            <p style="font-size: 16px; margin-bottom: 20px;">Pozdrav <strong>{clan.ime_prezime}</strong>! 👋</p>
                            
                            <p style="font-size: 15px; color: #555; margin-bottom: 25px;">
                                Evo vaših pristupnih podataka za Alchemist Health Club aplikaciju:
                            </p>
                            
                            <!-- Kredencijali Box -->
                            <div style="background-color: #f8f9fa; padding: 25px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #667eea;">
                                <div style="margin-bottom: 15px;">
                                    <span style="color: #666; font-size: 13px; text-transform: uppercase; letter-spacing: 1px;">Korisničko ime</span>
                                    <div style="font-size: 18px; font-weight: bold; color: #333; margin-top: 5px;">{username}</div>
                                </div>
                                <div>
                                    <span style="color: #666; font-size: 13px; text-transform: uppercase; letter-spacing: 1px;">Privremena lozinka</span>
                                    <div style="font-size: 18px; font-weight: bold; color: #333; margin-top: 5px;">default123</div>
                                </div>
                            </div>
                            
                            <!-- App Store Buttons -->
                            <div style="text-align: center; margin: 35px 0;">
                                <p style="font-size: 16px; font-weight: bold; margin-bottom: 15px; color: #333;">📲 Preuzmite aplikaciju:</p>
                                
                                <!-- iOS App Store -->
                                <a href="{ios_link}" style="display: inline-block; text-decoration: none; margin: 10px;">
                                    <img src="https://tools.applemediaservices.com/api/badges/download-on-the-app-store/black/en-us?size=250x83" 
                                         alt="Download on the App Store" 
                                         style="width: 200px; height: auto; border: 0;">
                                </a>
                                
                                <br>
                                
                                <!-- Google Play Store -->
                                <a href="{android_link}" style="display: inline-block; text-decoration: none; margin: 10px;">
                                    <img src="https://play.google.com/intl/en_us/badges/static/images/badges/en_badge_web_generic.png" 
                                         alt="Get it on Google Play" 
                                         style="width: 230px; height: auto; border: 0;">
                                </a>
                            </div>
                            
                            <!-- Instrukcije -->
                            <div style="background-color: #fff3cd; padding: 20px; border-radius: 8px; border-left: 4px solid #ffc107; margin: 25px 0;">
                                <p style="margin: 0 0 10px 0; font-weight: bold; color: #856404;">📱 Koraci za prijavljivanje:</p>
                                <ol style="margin: 10px 0; padding-left: 20px; color: #856404;">
                                    <li>Preuzmite aplikaciju za vaš uređaj klikom na dugme iznad</li>
                                    <li>Otvorite aplikaciju</li>
                                    <li>Unesite korisničko ime i lozinku</li>
                                    <li>Nakon prvog prijavljivanja, promenite lozinku u postavkama</li>
                                </ol>
                            </div>
                            
                            <!-- Savet -->
                            <div style="background-color: #d1ecf1; padding: 15px; border-radius: 8px; border-left: 4px solid #17a2b8; margin: 20px 0;">
                                <p style="margin: 0; color: #0c5460;">
                                    💡 <strong>VAŽNO:</strong> Sačuvajte ovu poruku dok ne promenite lozinku!
                                </p>
                            </div>
                            
                            <p style="margin-top: 30px; color: #666;">
                                Ako imate bilo kakvih problema, odgovorite na ovaj email! 😊
                            </p>
                        </div>
                        
                        <!-- Footer -->
                        <div style="background-color: #f8f9fa; padding: 25px; text-align: center; border-top: 1px solid #dee2e6;">
                            <p style="margin: 0 0 10px 0; font-weight: bold; color: #333;">Srećno sa novom aplikacijom! 💪</p>
                            <p style="margin: 0; font-size: 13px; color: #666;">
                                📧 alchemist.fitnesklub@gmail.com | 📱 011 4076290<br>
                                Alchemist Ladies Fitness & Health Club | Beograd
                            </p>
                        </div>
                        
                    </div>
                </body>
                </html>
                """
                
                email = EmailMessage(
                    subject='🔐 Podaci za logovanje - Alchemist App',
                    body=html_content,
                    from_email=settings.EMAIL_HOST_USER,
                    to=[clan.email],
                )
                email.content_subtype = 'html'
                email.send(fail_silently=True)
                
                messages.success(request, f'✅ Podaci za logovanje poslati na {clan.email}!')
            else:
                messages.error(request, '❌ Član nema email adresu!')




        return redirect('profil', clan_id=clan_id)

    context = {
        'clan': clan,
        'uplate': uplate,
        'istorija_rezervacija': istorija_rezervacija,
        'is_trener': is_trener,
        'is_klijent': is_klijent,
        'clan_form': ClanForm(instance=clan),
        'uplata_form': UplataForm(),
        'merenja': clan.merenja.all(),  # ← NOVO - JEDINA PROMENA!
    }
    return render(request, 'profil.html', context)


@login_required
def klijenti_json_clanovi(request):
    try:
        profile = request.user.userprofile
    except (AttributeError, UserProfile.DoesNotExist):
        return JsonResponse([], safe=False)
    if not profile or (not profile.is_trener and not profile.is_admin):
        return JsonResponse([], safe=False)
    q = request.GET.get('q', '')
    clanovi = Clan.objects.filter(ime_prezime__icontains=q).values(
        'id', 'ime_prezime', 'telefon', 'email', 'krediti_voda'
    )[:20]
    return JsonResponse(list(clanovi), safe=False)


@trener_or_admin_required
def trener_home(request):
    """
    Početna stranica za trenere - BEZ osetljivih finansijskih podataka
    """
    today = timezone.now().date()
    rezervacije_danas = Rezervacija.objects.filter(datum=today).select_related('clan').order_by('sat')
    
    ukupno_clanova = Clan.objects.count()
    aktivnih_clanova = Uplata.objects.filter(do_datum__gte=today).count()
    
    prvi_dan_meseca = today.replace(day=1)
    prihod_meseca = Uplata.objects.filter(datum__gte=prvi_dan_meseca).aggregate(Sum('iznos'))['iznos__sum'] or 0
    
    context = {
        'total_members': ukupno_clanova,
        'active_memberships': aktivnih_clanova,
        'rezervacije_danas': rezervacije_danas,
        'prihod_meseca': prihod_meseca,
    }
    return render(request, 'trener_home.html', context)


@login_required
def klijent_dashboard(request):
    try:
        profile = request.user.userprofile
    except (AttributeError, UserProfile.DoesNotExist):
        messages.error(request, 'Nemate pristup ovoj stranici.')
        return redirect('login')
    if not profile or not profile.is_klijent:
        messages.error(request, 'Nemate pristup ovoj stranici.')
        return redirect('login')
    clan = Clan.objects.filter(user=request.user).first()
    if not clan:
        messages.error(request, 'Niste povezani sa klijentom.')
        return redirect('login')
    uplate = Uplata.objects.filter(clan=clan).order_by('-datum')
    rezervacije = Rezervacija.objects.filter(clan=clan).order_by('-datum')
    context = {
        'clan': clan,
        'uplate': uplate,
        'rezervacije': rezervacije,
    }
    return render(request, 'klijent_dashboard.html', context)


def send_expiration_notifications():
    """Šalje notifikacije (Email + SMS + Push) 7 dana pre isteka članarine"""
    from .models import FCMToken
    
    sedam_dana = timezone.now().date() + timedelta(days=7)
    expirations_7_days = Uplata.objects.filter(
        do_datum=sedam_dana,
        notification_sent=False
    ).select_related('clan')
    
    client = Client(settings.TWILIO_SID, settings.TWILIO_AUTH_TOKEN)
    
    for uplata in expirations_7_days:
        message = f"Poštovani/a, Vaš paket ({uplata.meseci} meseci) ističe {uplata.do_datum.strftime('%d.%m.%Y')}. Podsećamo Vas da produžite paket. Sportski pozdrav, Vaš Alchemist!"
        
        # EMAIL
        if uplata.clan.email:
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
        
        # SMS
        if uplata.clan.telefon:
            try:
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
            except Exception:
                Obavestenje.objects.create(
                    clan=uplata.clan,
                    tip='sms',
                    poruka=message,
                    status='failed'
                )
        
        # PUSH NOTIFIKACIJA
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
                print(f"Push greška: {e}")
        
        uplata.notification_sent = True
        uplata.save()


def send_birthday_notifications():
    """Šalje rođendanske čestitke (Email + SMS + Push)"""
    from .models import FCMToken
    
    today = timezone.now().date()
    birthdays = Clan.objects.filter(
        datum_rodjenja__month=today.month,
        datum_rodjenja__day=today.day
    )
    
    client = Client(settings.TWILIO_SID, settings.TWILIO_AUTH_TOKEN)
    
    for clan in birthdays:
        message = "Neko misli na Vas, srećan rođendan!!! Vaš Alchemist"
        
        # EMAIL
        if clan.email:
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
        
        # SMS
        if clan.telefon:
            try:
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
            except Exception:
                Obavestenje.objects.create(
                    clan=clan,
                    tip='sms',
                    poruka=message,
                    status='failed'
                )
        
        # PUSH NOTIFIKACIJA
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
                print(f"Push greška: {e}")


def send_training_reminders():
    """Šalje push notifikacije 2 sata pre treninga"""
    from .models import FCMToken
    
    now = timezone.now()
    two_hours_later = now + timedelta(hours=2)
    target_date = two_hours_later.date()
    target_hour = two_hours_later.hour
    
    rezervacije = Rezervacija.objects.filter(
        datum=target_date,
        sat=target_hour
    ).select_related('clan', 'clan__user')
    
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
                message = f"Podsetnik: Za 2 sata imate zakazan trening u {rezervacija.sat}:00!"
                response = send_push_notification(
                    fcm_token=token_obj.token,
                    title="Podsetnik za trening",
                    body=message
                )
                if response:
                    sent_count += 1
        except Exception as e:
            print(f"Greška: {e}")
    
    return sent_count


@trener_or_admin_required
def send_training_reminders_view(request):
    """View za ručno pokretanje podsетnika"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Samo administrator može pokrenuti podsetnik.')
            return redirect('dashboard')
    except (AttributeError, UserProfile.DoesNotExist):
        messages.error(request, 'Nemate pristup.')
        return redirect('login')
    
    try:
        sent_count = send_training_reminders()
        if sent_count > 0:
            messages.success(request, f'Poslato {sent_count} podsетnika!')
        else:
            messages.info(request, 'Nema treninga za sledeca 2 sata.')
    except Exception as e:
        messages.error(request, f'Greska: {str(e)}')
    
    return redirect('dashboard')


@trener_or_admin_required
def test_notifications(request):
    """
    Ručno slanje automatskih obaveštenja - samo za Admin
    """
    try:
        profile = request.user.userprofile
        
        if not profile.is_admin:
            messages.error(request, 'Samo administrator može pokrenuti obaveštenja.')
            return redirect('rezervacije')
        
    except (AttributeError, UserProfile.DoesNotExist):
        messages.error(request, 'Nemate pristup ovoj stranici.')
        return redirect('login')
    
    try:
        today = timezone.now().date()
        sedam_dana = today + timedelta(days=7)
        
        clanarinske_count = Uplata.objects.filter(
            do_datum=sedam_dana,
            notification_sent=False
        ).count()
        
        rodjendanske_count = Clan.objects.filter(
            datum_rodjenja__month=today.month,
            datum_rodjenja__day=today.day
        ).count()
        
        send_expiration_notifications()
        send_birthday_notifications()
        
        if clanarinske_count > 0 or rodjendanske_count > 0:
            messages.success(
                request, 
                f'✅ Poslato {clanarinske_count} obaveštenja o članarinama i {rodjendanske_count} rođendanskih čestitki!'
            )
        else:
            messages.info(request, 'ℹ️ Nema novih obaveštenja za slanje danas.')
        
    except Exception as e:
        messages.error(request, f'❌ Greška pri slanju obaveštenja: {str(e)}')
    
    return redirect('dashboard')

@login_required
def rezervacije_json(request):
    try:
        profile = request.user.userprofile
    except (AttributeError, UserProfile.DoesNotExist):
        return JsonResponse([], safe=False)
    if not profile or (not profile.is_trener and not profile.is_admin):
        return JsonResponse([], safe=False)
    start = request.GET.get('start')
    end = request.GET.get('end')
    try:
        start_date = datetime.strptime(start.split('T')[0], '%Y-%m-%d').date()
        end_date = datetime.strptime(end.split('T')[0], '%Y-%m-%d').date()
    except:
        start_date = end_date = datetime.now().date()
    rezervacije = Rezervacija.objects.filter(datum__gte=start_date, datum__lte=end_date).select_related('clan')
    events = []
    for r in rezervacije:
        try:
            sat_int = int(r.sat)
        except:
            sat_int = 0
        sat_str = f"{sat_int:02d}"
        events.append({
            'id': r.id,
            'title': r.clan.ime_prezime,
            'start': f"{r.datum}T{sat_str}:00"
        })
    
    # ========================================
    # DODAJ ZATVORENE TERMINE
    # ========================================
    zatvoreni = ZatvorenTermin.objects.filter(
        datum__gte=start_date,
        datum__lte=end_date
    )
    
    for z in zatvoreni:
        events.append({
            'id': f'closed_{z.id}',
            'title': z.razlog or 'ZATVORENO',
            'start': f"{z.datum}T{z.sat:02d}:00:00",
            'color': '#ff0000',
            'textColor': '#ffffff',
            'closed': True  # Oznaka da je zatvoren termin
        })
    # ========================================
    
    return JsonResponse(events, safe=False)


@login_required
def rezervacije_json_clanovi(request):
    try:
        profile = request.user.userprofile
    except (AttributeError, UserProfile.DoesNotExist):
        return JsonResponse([], safe=False)
    if not profile or (not profile.is_trener and not profile.is_admin):
        return JsonResponse([], safe=False)
    q = request.GET.get('q', '')
    clanovi = Clan.objects.filter(ime_prezime__icontains=q).values('id', 'ime_prezime')
    return JsonResponse(list(clanovi), safe=False)


@login_required
def brisi_rezervaciju(request, rezervacija_id):
    try:
        profile = request.user.userprofile
    except (AttributeError, UserProfile.DoesNotExist):
        return JsonResponse({'status': 'error', 'message': 'Nemate dozvolu.'})
    if not profile or (not profile.is_trener and not profile.is_admin):
        return JsonResponse({'status': 'error', 'message': 'Nemate dozvolu.'})
    if request.method == 'POST':
        try:
            rezervacija = get_object_or_404(Rezervacija, id=rezervacija_id)
            rezervacija.delete()
            return JsonResponse({'status': 'success', 'message': 'Rezervacija obrisana.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Greška: {str(e)}'})
    return JsonResponse({'status': 'error', 'message': 'Samo POST zahtev.'})


@login_required
def brisi_clana(request, clan_id):
    try:
        profile = request.user.userprofile
    except (AttributeError, UserProfile.DoesNotExist):
        return JsonResponse({'status': 'error', 'message': 'Nemate dozvolu.'})
    if not profile or not profile.is_admin:
        return JsonResponse({'status': 'error', 'message': 'Samo admin može obrisati člana.'})
    if request.method == 'POST':
        try:
            clan = get_object_or_404(Clan, id=clan_id)
            clan.delete()
            return JsonResponse({'success': True, 'message': 'Član obrisan.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Greška: {str(e)}'})
    return JsonResponse({'status': 'error', 'message': 'Samo POST zahtev.'})


@login_required
def krediti_json(request, clan_id):
    try:
        profile = request.user.userprofile
    except (AttributeError, UserProfile.DoesNotExist):
        return JsonResponse({'error': 'Nemate pristup'}, status=403)
    if not profile or (not profile.is_trener and not profile.is_admin):
        return JsonResponse({'error': 'Nemate dozvolu'}, status=403)
    try:
        clan = Clan.objects.get(id=clan_id)
        return JsonResponse({
            'krediti_voda': float(clan.krediti_voda),
            'ime_prezime': clan.ime_prezime
        })
    except Clan.DoesNotExist:
        return JsonResponse({'error': 'Član ne postoji'}, status=404)


@csrf_exempt
def save_push_token(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            token = data.get('token')
            user_id = data.get('user_id')
            if not token or not user_id:
                return JsonResponse({'error': 'Token i user_id su obavezni'}, status=400)
            try:
                clan = Clan.objects.get(user_id=user_id)
                clan.fcm_token = token
                clan.save()
                return JsonResponse({'success': True, 'message': 'Token sačuvan'})
            except Clan.DoesNotExist:
                return JsonResponse({'error': 'Član ne postoji'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Nevalidan JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Samo POST zahtevi'}, status=405)


@trener_or_admin_required
def test_push(request):
    if request.method == 'POST':
        clan_id = request.POST.get('clan_id')
        title = request.POST.get('title', 'Test notifikacija')
        body = request.POST.get('body', 'Ovo je test poruka')
        try:
            clan = get_object_or_404(Clan, id=clan_id)
            if not clan.fcm_token:
                messages.error(request, 'Član nema registrovan FCM token')
                return redirect('test_push')
            response = send_push_notification(
                fcm_token=clan.fcm_token,
                title=title,
                body=body
            )
            
            if response:
                messages.success(request, f'Notifikacija poslata! Response: {response}')
            else:
                raise Exception("Failed to send notification")
        except Exception as e:
            messages.error(request, f'Greška: {str(e)}')
        return redirect('test_push')
    clanovi = Clan.objects.exclude(fcm_token__isnull=True).exclude(fcm_token='')
    context = {'clanovi': clanovi}
    return render(request, 'test_push.html', context)


@trener_or_admin_required
def test_calendar(request):
    return render(request, 'test_calendar.html')


def privacy_policy(request):
    """Privacy Policy stranica za Google Play Store"""
    return render(request, 'privacy_policy.html')

def logout_view(request):
    auth_logout(request)
    messages.success(request, 'Uspešno ste se odjavili.')
    return redirect('login')  

# ========================================
# VIEWS ZA MERENJA - DODATO 09.12.2024
# ========================================

@login_required
def dodaj_merenje(request, clan_id):
    clan = get_object_or_404(Clan, id=clan_id)
    
    if request.method == 'POST':
        form = MerenjeForm(request.POST)
        if form.is_valid():
            merenje = form.save(commit=False)
            merenje.clan = clan
            merenje.kreirao = request.user
            merenje.save()
            messages.success(request, f'✅ Merenje za {clan.ime_prezime} je uspešno sačuvano!')
            return redirect('profil', clan_id=clan.id)
        else:
            # DODAJ OVO - prikaži greške
            print("❌ FORM ERRORS:", form.errors)
            print("❌ FORM DATA:", request.POST)
            messages.error(request, f'❌ Greška: {form.errors}')  # ← IZMENJENO
    else:
        poslednje_merenje = Merenje.objects.filter(clan=clan).first()
        initial_data = {}
        if poslednje_merenje and poslednje_merenje.visina:
            initial_data['visina'] = poslednje_merenje.visina
        form = MerenjeForm(initial=initial_data)
    
    return render(request, 'merenje_forma.html', {'form': form, 'clan': clan})


@login_required
def merenja_json(request, clan_id):
    clan = get_object_or_404(Clan, id=clan_id)
    merenja = Merenje.objects.filter(clan=clan).order_by('datum')[:20]
    
    data = {
        'labels': [m.datum.strftime('%d.%m.%Y') for m in merenja],
        'tezina': [float(m.tezina) if m.tezina else None for m in merenja],
        'procenat_masti': [float(m.procenat_masti) if m.procenat_masti else None for m in merenja],
        'misicna_masa': [float(m.misicna_masa) if m.misicna_masa else None for m in merenja],
        'visceralna_mast': [int(m.visceralna_mast) if m.visceralna_mast else None for m in merenja],
        'bmi': [float(m.bmi) if m.bmi else None for m in merenja],
    }
    
    return JsonResponse(data)


@login_required
def obrisi_merenje(request, merenje_id):
    merenje = get_object_or_404(Merenje, id=merenje_id)
    clan_id = merenje.clan.id
    
    if request.method == 'POST':
        merenje.delete()
        messages.success(request, '✅ Merenje je uspešno obrisano!')
    
    return redirect('profil', clan_id=clan_id)


@login_required
def posalji_merenje_email(request, merenje_id):
    merenje = get_object_or_404(Merenje, id=merenje_id)
    clan = merenje.clan
    
    if not clan.email:
        messages.error(request, '❌ Klijent nema unesen email.')
        return redirect('profil', clan_id=clan.id)
    
    try:
        from django.template.loader import render_to_string
        from django.core.mail import EmailMessage
        
        html_content = render_to_string('emails/merenje_izvestaj.html', {
            'clan': clan,
            'merenje': merenje,
        })
        
        email = EmailMessage(
            subject=f'Rezultati merenja - {clan.ime_prezime}',
            body=html_content,
            from_email='office@alchemist-fitnessclub.com',
            to=[clan.email],
        )
        email.content_subtype = 'html'
        email.send()
        
        messages.success(request, f'✅ Izveštaj poslat na {clan.email}')
    except Exception as e:
        messages.error(request, f'❌ Greška: {str(e)}')
    
    return redirect('profil', clan_id=clan.id)


@login_required
def api_merenja_lista(request, clan_id):
    clan = get_object_or_404(Clan, id=clan_id)
    merenja = Merenje.objects.filter(clan=clan).order_by('-datum')
    
    data = []
    for m in merenja:
        data.append({
            'id': m.id,
            'datum': m.datum.strftime('%d.%m.%Y %H:%M'),
            'tezina': float(m.tezina) if m.tezina else None,
            'procenat_masti': float(m.procenat_masti) if m.procenat_masti else None,
            'bmi': float(m.bmi) if m.bmi else None,
        })
    
    return JsonResponse({'merenja': data})

# ========================================
# MANAGEMENT DASHBOARD - DODATO 10.12.2024
# ========================================

@admin_only
def management_dashboard(request):
    """Glavni Management Dashboard sa svim menadžerskim metrikama"""
    today = timezone.now().date()
    
    context = {
        'today': today,
    }
    return render(request, 'management_dashboard.html', context)


@admin_only
def management_predicted_income(request):
    """Predviđene uplate - ko treba da plati i koliko"""
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    
    today = timezone.now().date()
    
    if from_date_str:
        from_date = parse_date(from_date_str) or today
    else:
        from_date = today
    
    if to_date_str:
        to_date = parse_date(to_date_str) or (today + timedelta(days=30))
    else:
        to_date = today + timedelta(days=30)
    
    # Članarine koje ističu u periodu
    expirations = Uplata.objects.filter(
        do_datum__gte=from_date,
        do_datum__lte=to_date
    ).select_related('clan').order_by('do_datum')
    
    # Prognoza - pretpostavka da će platiti isto kao prošli put
    predicted_data = []
    total_predicted = Decimal('0.00')
    
    for uplata in expirations:
        predicted_amount = uplata.iznos  # Očekujemo istu cifru
        predicted_data.append({
            'clan': uplata.clan,
            'expires': uplata.do_datum,
            'last_amount': uplata.iznos,
            'predicted_amount': predicted_amount,
            'meseci': uplata.meseci,
        })
        total_predicted += predicted_amount
    
    context = {
        'from_date': from_date.strftime('%Y-%m-%d'),
        'to_date': to_date.strftime('%Y-%m-%d'),
        'predicted_data': predicted_data,
        'total_predicted': total_predicted,
        'count': len(predicted_data),
    }
    return render(request, 'management_predicted_income.html', context)


@admin_only
def management_client_payments(request):
    """Uplate po klijentu - search box"""
    q = request.GET.get('q', '').strip()
    
    results = []
    total_sum = Decimal('0.00')
    
    if q:
        # Pronađi klijenta
        clanovi = Clan.objects.filter(ime_prezime__icontains=q)
        
        if clanovi.exists():
            clan = clanovi.first()
            uplate = Uplata.objects.filter(clan=clan).order_by('-datum')
            total_sum = uplate.aggregate(Sum('iznos'))['iznos__sum'] or Decimal('0.00')
            results = uplate
    
    context = {
        'q': q,
        'results': results,
        'total_sum': total_sum,
        'clan': clanovi.first() if q and clanovi.exists() else None,
    }
    return render(request, 'management_client_payments.html', context)


@admin_only
def management_monthly_chart(request):
    """Chart za tekući kalendarski mesec sa prognozama"""
    today = timezone.now().date()
    first_day = today.replace(day=1)
    
    # Poslednji dan meseca
    if today.month == 12:
        last_day = today.replace(day=31)
    else:
        last_day = (today.replace(month=today.month + 1, day=1) - timedelta(days=1))
    
    # Stvarne uplate ovog meseca
    uplate_meseca = Uplata.objects.filter(
        datum__gte=first_day,
        datum__lte=last_day
    ).aggregate(Sum('iznos'))['iznos__sum'] or Decimal('0.00')
    
    # Predviđene uplate (članarine koje ističu ovog meseca)
    predvidjene = Uplata.objects.filter(
        do_datum__gte=first_day,
        do_datum__lte=last_day
    ).aggregate(Sum('iznos'))['iznos__sum'] or Decimal('0.00')
    
    # Klijenti koji nisu pravili rezervaciju 30+ dana (potencijalni gubitak)
    trideset_dana_unazad = today - timedelta(days=30)
    aktivni_clanovi = Clan.objects.filter(
        uplata__do_datum__gte=today  # Ima aktivnu članarinu
    ).distinct()
    
    ghost_count = 0
    potential_loss = Decimal('0.00')
    
    for clan in aktivni_clanovi:
        poslednja_rezervacija = Rezervacija.objects.filter(clan=clan).order_by('-datum').first()
        
        if not poslednja_rezervacija or poslednja_rezervacija.datum < trideset_dana_unazad:
            ghost_count += 1
            # Proceni gubitak kao poslednju uplatu
            poslednja_uplata = Uplata.objects.filter(clan=clan).order_by('-datum').first()
            if poslednja_uplata:
                potential_loss += poslednja_uplata.iznos
    
    context = {
        'first_day': first_day,
        'last_day': last_day,
        'uplate_meseca': uplate_meseca,
        'predvidjene': predvidjene,
        'ghost_count': ghost_count,
        'potential_loss': potential_loss,
        'chart_labels': json.dumps(['Ostvareno', 'Predviđeno', 'Potencijalni gubitak']),
        'chart_data': json.dumps([
            float(uplate_meseca),
            float(predvidjene),
            float(potential_loss)
        ]),
    }
    return render(request, 'management_monthly_chart.html', context)


@admin_only
def management_staff_attendance(request):
    """Broj radnih dana zaposlenih - tracking prisustva"""
    from .models import RadnikPrisustvo
    
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    
    today = timezone.now().date()
    prvi_dan_meseca = today.replace(day=1)
    
    if from_date_str:
        from_date = parse_date(from_date_str) or prvi_dan_meseca
    else:
        from_date = prvi_dan_meseca
    
    if to_date_str:
        to_date = parse_date(to_date_str) or today
    else:
        to_date = today
    
    # Svi treneri i admini
    staff_profiles = UserProfile.objects.filter(
        is_trener=True
    ) | UserProfile.objects.filter(is_admin=True)
    
    staff_data = []
    
    for profile in staff_profiles:
        prisustva = RadnikPrisustvo.objects.filter(
            user=profile.user,
            datum__gte=from_date,
            datum__lte=to_date
        ).order_by('-datum')
        
        radni_dani = prisustva.count()
        
        staff_data.append({
            'user': profile.user,
            'radni_dani': radni_dani,
            'prisustva': prisustva[:10],  # Poslednje 10 za prikaz
        })
    
    context = {
        'from_date': from_date.strftime('%Y-%m-%d'),
        'to_date': to_date.strftime('%Y-%m-%d'),
        'staff_data': staff_data,
    }
    return render(request, 'management_staff_attendance.html', context)

# ========================================
# MANAGEMENT DASHBOARD - FAZA 2 (BONUS)
# DODATO 10.12.2024
# ========================================

@admin_only
def management_cash_flow(request):
    """Cash Flow prognoza - 3 meseca unapred"""
    today = timezone.now().date()
    
    # Kreiraj datume za naredna 3 meseca
    months = []
    for i in range(3):
        if today.month + i > 12:
            year = today.year + 1
            month = (today.month + i) % 12
        else:
            year = today.year
            month = today.month + i
        
        first_day = date(year, month, 1)
        
        # Poslednji dan meseca
        if month == 12:
            last_day = date(year, 12, 31)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)
        
        # Članarine koje ističu u ovom mesecu
        expirations = Uplata.objects.filter(
            do_datum__gte=first_day,
            do_datum__lte=last_day
        )
        
        predicted_income = expirations.aggregate(Sum('iznos'))['iznos__sum'] or Decimal('0.00')
        
        months.append({
            'name': first_day.strftime('%B %Y'),
            'first_day': first_day,
            'last_day': last_day,
            'predicted_income': predicted_income,
            'count': expirations.count(),
        })
    
    total_predicted = sum(m['predicted_income'] for m in months)
    
    context = {
        'months': months,
        'total_predicted': total_predicted,
        'chart_labels': json.dumps([m['name'] for m in months]),
        'chart_data': json.dumps([float(m['predicted_income']) for m in months]),
    }
    return render(request, 'management_cash_flow.html', context)

@admin_only
def management_retention_rate(request):
    """Retention Rate - stopa zadržavanja klijenata"""
    today = timezone.now().date()
    
    # Članarine koje su istekle u poslednjih 30 dana
    thirty_days_ago = today - timedelta(days=30)
    
    # Pronađi sve klijente čija je članarina istekla u zadnjih 30 dana
    expired_memberships = Uplata.objects.filter(
        do_datum__gte=thirty_days_ago,
        do_datum__lt=today
    ).select_related('clan').order_by('do_datum')
    
    total_expired = 0
    renewed_count = 0
    not_renewed = []
    
    # Grupiši po klijentu (jer jedan klijent može imati više uplata)
    processed_clients = set()
    
    for uplata in expired_memberships:
        # Preskoči ako smo već obradili ovog klijenta
        if uplata.clan.id in processed_clients:
            continue
        
        processed_clients.add(uplata.clan.id)
        total_expired += 1
        
        # Proveri da li klijent TRENUTNO ima aktivnu članarinu
        has_active_membership = Uplata.objects.filter(
            clan=uplata.clan,
            od_datum__lte=today,
            do_datum__gte=today
        ).exists()
        
        if has_active_membership:
            renewed_count += 1
        else:
            # Pronađi poslednju uplatu za prikaz iznosa
            poslednja_uplata = Uplata.objects.filter(
                clan=uplata.clan
            ).order_by('-datum').first()
            
            not_renewed.append({
                'clan': uplata.clan,
                'expired': uplata.do_datum,
                'amount': poslednja_uplata.iznos if poslednja_uplata else Decimal('0.00'),
                'last_payment': poslednja_uplata.datum if poslednja_uplata else None,
            })
    
    retention_rate = (renewed_count / total_expired * 100) if total_expired > 0 else 0
    
    context = {
        'total_expired': total_expired,
        'renewed_count': renewed_count,
        'not_renewed_count': len(not_renewed),
        'retention_rate': round(retention_rate, 1),
        'not_renewed': sorted(not_renewed, key=lambda x: x['expired'], reverse=True)[:20],
    }
    return render(request, 'management_retention_rate.html', context)


@admin_only
def management_top_clients(request):
    """Top 10 klijenata po zaradi"""
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    
    today = timezone.now().date()
    
    if from_date_str:
        from_date = parse_date(from_date_str) or (today - timedelta(days=365))
    else:
        from_date = today - timedelta(days=365)  # Poslednja godina
    
    if to_date_str:
        to_date = parse_date(to_date_str) or today
    else:
        to_date = today
    
    # Grupiši uplate po klijentu
    top_clients = Uplata.objects.filter(
        datum__gte=from_date,
        datum__lte=to_date
    ).values('clan__ime_prezime', 'clan__id').annotate(
        total=Sum('iznos'),
        count=Count('id')
    ).order_by('-total')[:10]
    
    total_revenue = sum(c['total'] for c in top_clients)
    
    context = {
        'from_date': from_date.strftime('%Y-%m-%d'),
        'to_date': to_date.strftime('%Y-%m-%d'),
        'top_clients': top_clients,
        'total_revenue': total_revenue,
        'chart_labels': json.dumps([c['clan__ime_prezime'] for c in top_clients]),
        'chart_data': json.dumps([float(c['total']) for c in top_clients]),
    }
    return render(request, 'management_top_clients.html', context)


@admin_only
def management_ghost_members(request):
    """Ghost Members - detaljniji prikaz"""
    today = timezone.now().date()
    days_threshold = int(request.GET.get('days', 30))
    
    threshold_date = today - timedelta(days=days_threshold)
    
    # Svi sa aktivnom članarinom
    active_members = Clan.objects.filter(
        uplata__do_datum__gte=today
    ).distinct()
    
    ghost_members = []
    total_potential_loss = Decimal('0.00')
    
    for clan in active_members:
        # Poslednja rezervacija
        last_reservation = Rezervacija.objects.filter(clan=clan).order_by('-datum').first()
        
        if not last_reservation or last_reservation.datum < threshold_date:
            days_inactive = (today - last_reservation.datum).days if last_reservation else 999
            
            # Poslednja uplata
            last_uplata = Uplata.objects.filter(clan=clan).order_by('-datum').first()
            potential_loss = last_uplata.iznos if last_uplata else Decimal('0.00')
            
            ghost_members.append({
                'clan': clan,
                'last_reservation': last_reservation.datum if last_reservation else None,
                'days_inactive': days_inactive,
                'potential_loss': potential_loss,
                'expires': last_uplata.do_datum if last_uplata else None,
            })
            
            total_potential_loss += potential_loss
    
    # Sortiraj po broju dana neaktivnosti
    ghost_members.sort(key=lambda x: x['days_inactive'], reverse=True)
    
    context = {
        'days_threshold': days_threshold,
        'ghost_members': ghost_members,
        'count': len(ghost_members),
        'total_potential_loss': total_potential_loss,
    }
    return render(request, 'management_ghost_members.html', context)


@admin_only
def management_attendance_heatmap(request):
    """Attendance Heatmap - najpopularniji dani/termini"""
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    
    today = timezone.now().date()
    
    if from_date_str:
        from_date = parse_date(from_date_str) or (today - timedelta(days=30))
    else:
        from_date = today - timedelta(days=30)
    
    if to_date_str:
        to_date = parse_date(to_date_str) or today
    else:
        to_date = today
    
    # Rezervacije u periodu
    rezervacije = Rezervacija.objects.filter(
        datum__gte=from_date,
        datum__lte=to_date
    )
    
    # Grupiši po danu u nedelji
    day_counts = rezervacije.extra(
        select={'day_of_week': "EXTRACT(DOW FROM datum)"}
    ).values('day_of_week').annotate(count=Count('id')).order_by('day_of_week')
    
    day_labels = ['Nedelja', 'Ponedeljak', 'Utorak', 'Sreda', 'Četvrtak', 'Petak', 'Subota']
    day_data = [0] * 7
    
    for entry in day_counts:
        day_index = int(entry['day_of_week'])
        day_data[day_index] = entry['count']
    
    # Grupiši po satu
    hour_counts = rezervacije.values('sat').annotate(count=Count('id')).order_by('sat')
    
    hour_labels = [f"{h}:00" for h in range(6, 23)]
    hour_data = [0] * len(hour_labels)
    
    for entry in hour_counts:
        hour_index = entry['sat'] - 6  # Offset jer počinje od 6
        if 0 <= hour_index < len(hour_data):
            hour_data[hour_index] = entry['count']
    
    # Najpopularniji termin
    most_popular = hour_counts.first()
    most_popular_time = f"{most_popular['sat']}:00" if most_popular else "N/A"
    most_popular_count = most_popular['count'] if most_popular else 0
    
    context = {
        'from_date': from_date.strftime('%Y-%m-%d'),
        'to_date': to_date.strftime('%Y-%m-%d'),
        'total_reservations': rezervacije.count(),
        'most_popular_time': most_popular_time,
        'most_popular_count': most_popular_count,
        'day_labels': json.dumps(day_labels),
        'day_data': json.dumps(day_data),
        'hour_labels': json.dumps(hour_labels),
        'hour_data': json.dumps(hour_data),
    }
    return render(request, 'management_attendance_heatmap.html', context)


@admin_only
def management_customer_value(request):
    """Average Customer Value - prosečna vrednost člana"""
    # Svi članovi sa uplatama
    clanovi_sa_uplatama = Clan.objects.annotate(
        total_paid=Sum('uplata__iznos'),
        payment_count=Count('uplata')
    ).filter(total_paid__gt=0).order_by('-total_paid')
    
    total_members = clanovi_sa_uplatama.count()
    total_revenue = clanovi_sa_uplatama.aggregate(Sum('total_paid'))['total_paid__sum'] or Decimal('0.00')
    
    average_value = (total_revenue / total_members) if total_members > 0 else Decimal('0.00')
    
    # Raspodela po kategorijama
    categories = {
        'low': clanovi_sa_uplatama.filter(total_paid__lt=100).count(),
        'medium': clanovi_sa_uplatama.filter(total_paid__gte=100, total_paid__lt=500).count(),
        'high': clanovi_sa_uplatama.filter(total_paid__gte=500, total_paid__lt=1000).count(),
        'vip': clanovi_sa_uplatama.filter(total_paid__gte=1000).count(),
    }
    
    context = {
        'total_members': total_members,
        'total_revenue': total_revenue,
        'average_value': round(average_value, 2),
        'categories': categories,
        'top_spenders': clanovi_sa_uplatama[:10],
        'chart_labels': json.dumps(['< 100€', '100-500€', '500-1000€', '1000€+']),
        'chart_data': json.dumps([categories['low'], categories['medium'], categories['high'], categories['vip']]),
    }
    return render(request, 'management_customer_value.html', context)

@admin_only
def management_monthly_payments(request):
    """Pregled svih uplata po mesecima"""
    # Filter parametri
    month_str = request.GET.get('month')
    year_str = request.GET.get('year')
    
    today = timezone.now().date()
    
    # Ako nisu uneti, uzmi trenutni mesec
    if month_str and year_str:
        month = int(month_str)
        year = int(year_str)
    else:
        month = today.month
        year = today.year
    
    # Prvi i poslednji dan meseca
    first_day = date(year, month, 1)
    
    if month == 12:
        last_day = date(year, 12, 31)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    # Sve uplate u tom mesecu (po od_datum)
    uplate = Uplata.objects.filter(
        od_datum__gte=first_day,
        od_datum__lte=last_day
    ).select_related('clan').order_by('od_datum')
    
    total_sum = uplate.aggregate(Sum('iznos'))['iznos__sum'] or Decimal('0.00')
    total_count = uplate.count()
    
    # Mesečni nazivi
    month_names = {
        1: 'Januar', 2: 'Februar', 3: 'Mart', 4: 'April',
        5: 'Maj', 6: 'Jun', 7: 'Jul', 8: 'Avgust',
        9: 'Septembar', 10: 'Oktobar', 11: 'Novembar', 12: 'Decembar'
    }
    
    context = {
        'uplate': uplate,
        'total_sum': total_sum,
        'total_count': total_count,
        'selected_month': month,
        'selected_year': year,
        'month_name': month_names[month],
        'first_day': first_day,
        'last_day': last_day,
    }
    return render(request, 'management_monthly_payments.html', context)

# ========================================
# IZMENA I BRISANJE UPLATA - SAMO ADMIN
# DODATO 16.12.2024
# ========================================

@admin_only
def delete_uplata(request, uplata_id):
    """Brisanje uplate - samo admin"""
    uplata = get_object_or_404(Uplata, id=uplata_id)
    clan_id = uplata.clan.id
    
    uplata.delete()
    messages.success(request, f'Uplata od {uplata.iznos}€ je uspešno obrisana!')
    
    return redirect('profil', clan_id=clan_id)  # ← IZMENJENO!


@admin_only
def edit_uplata(request, uplata_id):
    """Izmena uplate - samo admin"""
    uplata = get_object_or_404(Uplata, id=uplata_id)
    
    if request.method == 'POST':
        iznos = request.POST.get('iznos')
        datum = request.POST.get('datum')
        od_datum = request.POST.get('od_datum')
        do_datum = request.POST.get('do_datum')
        
        # Validacija
        try:
            uplata.iznos = Decimal(iznos)
            uplata.datum = parse_date(datum)
            uplata.od_datum = parse_date(od_datum)
            uplata.do_datum = parse_date(do_datum)
            uplata.save()
            
            uplata.save()
            
            messages.success(request, 'Uplata uspešno izmenjena!')
            return redirect('profil', clan_id=uplata.clan.id)  # ← IZMENJENO!
        except Exception as e:
            messages.error(request, f'Greška pri izmeni: {str(e)}')
    
    context = {
        'uplata': uplata,
    }
    return render(request, 'edit_uplata.html', context)

# ========================================
# ZATVARANJE TERMINA
# DODATO 16.12.2024
# ========================================

@admin_only
def zatvori_termin(request):
    """Zatvori termin (admin)"""
    if request.method == 'POST':
        datum = request.POST.get('datum')
        sat = request.POST.get('sat')
        razlog = request.POST.get('razlog', '')
        
        try:
            # Ekstraktuj sat iz formata "08:00"
            sat_int = int(sat.split(':')[0])
            
            # Kreiraj zatvoreni termin
            zatvoren, created = ZatvorenTermin.objects.get_or_create(
                datum=datum,
                sat=sat_int,
                defaults={
                    'razlog': razlog,
                    'zatvorio': request.user
                }
            )
            
            if created:
                return JsonResponse({
                    'status': 'success',
                    'message': f'Termin {datum} u {sat} je zatvoren!'
                })
            else:
                return JsonResponse({
                    'status': 'info',
                    'message': 'Termin je već zatvoren.'
                })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Greška: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Pogrešan metod'})


@admin_only
def otvori_termin(request):
    """Otvori zatvoreni termin (admin)"""
    if request.method == 'POST':
        datum = request.POST.get('datum')
        sat = request.POST.get('sat')
        
        try:
            sat_int = int(sat.split(':')[0])
            
            ZatvorenTermin.objects.filter(
                datum=datum,
                sat=sat_int
            ).delete()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Termin {datum} u {sat} je ponovo otvoren!'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Greška: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Pogrešan metod'})

# ========================================
# PUSH NOTIFICATION PANEL ZA ADMINA
# DODATO 18.12.2024
# ========================================

@admin_only
def push_notification_panel(request):
    """Admin panel za slanje push notifikacija svim klijentima"""
    from .models import FCMToken
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        body = request.POST.get('body', '').strip()
        send_to = request.POST.get('send_to', 'all')  # 'all' ili 'selected'
        selected_clients = request.POST.getlist('selected_clients')  # Lista ID-jeva
        
        if not title or not body:
            messages.error(request, '❌ Naslov i poruka su obavezni!')
            return redirect('push_panel')
        
        # Pronađi sve aktivne FCM tokene
        tokens_query = FCMToken.objects.filter(is_active=True).select_related('user', 'user__clan')
        
        # Ako je odabrano "selected", filtriraj po ID-jevima
        if send_to == 'selected' and selected_clients:
            tokens_query = tokens_query.filter(user__clan__id__in=selected_clients)
        
        sent_count = 0
        failed_count = 0
        
        for token_obj in tokens_query:
            try:
                response = send_push_notification(
                    fcm_token=token_obj.token,
                    title=title,
                    body=body
                )
                
                if response:
                    sent_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                print(f"Push greška za {token_obj.user.username}: {e}")
                failed_count += 1
        
        if sent_count > 0:
            messages.success(request, f'✅ Poslato {sent_count} notifikacija! ({failed_count} neuspešnih)')
        else:
            messages.error(request, f'❌ Nijedna notifikacija nije poslata. ({failed_count} neuspešnih)')
        
        return redirect('push_panel')
    
    # GET request - prikaži formu
    from .models import FCMToken
    
    # Svi klijenti koji imaju FCM token
    clanovi_sa_tokenima = Clan.objects.filter(
        user__fcm_tokens__is_active=True
    ).distinct().order_by('ime_prezime')
    
    total_devices = FCMToken.objects.filter(is_active=True).count()
    
    context = {
        'clanovi': clanovi_sa_tokenima,
        'total_devices': total_devices,
    }
    return render(request, 'push_panel.html', context)

    # ========================================
# PROGRESS DASHBOARD API ZA MOBILNU APP
# DODATO 22.12.2024
# ========================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_progress_merenja(request):
    """
    API endpoint za progress dashboard u mobilnoj aplikaciji
    Vraća sva merenja korisnika sortirana po datumu
    """
    try:
        # Pronađi člana povezanog sa user-om
        clan = Clan.objects.get(user=request.user)
        
        # Uzmi sva merenja sortirana po datumu (najstarije prvo za grafikon)
        merenja = Merenje.objects.filter(clan=clan).order_by('datum')
        
        # Pripremi podatke za Flutter app
        data = {
            'success': True,
            'clan_id': clan.id,
            'clan_ime': clan.ime_prezime,
            'merenja': []
        }
        
        for m in merenja:
            data['merenja'].append({
                'id': m.id,
                'datum': m.datum.strftime('%Y-%m-%d'),
                'datum_display': m.datum.strftime('%d.%m.%Y'),
                'tezina': float(m.tezina) if m.tezina else None,
                'bmi': float(m.bmi) if m.bmi else None,
                'procenat_masti': float(m.procenat_masti) if m.procenat_masti else None,
                'misicna_masa': float(m.misicna_masa) if m.misicna_masa else None,
                'telesna_voda': float(m.telesna_voda) if m.telesna_voda else None,
                'visceralna_mast': int(m.visceralna_mast) if m.visceralna_mast else None,
                'kostana_masa': float(m.kostana_masa) if m.kostana_masa else None,
                'bazalni_metabolizam': int(m.bazalni_metabolizam) if m.bazalni_metabolizam else None,
                'fizicki_status': int(m.fizicki_status) if m.fizicki_status else None,
                'napomena': m.napomena if m.napomena else ''
            })
        
        return Response(data)
        
    except Clan.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Korisnik nema povezan profil člana'
        }, status=404)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_progress_statistika(request):
    """
    API endpoint za statistiku treninga
    Vraća broj treninga, streak, proseke
    """
    try:
        clan = Clan.objects.get(user=request.user)
        
        today = timezone.now().date()
        
        # Ovaj mesec
        first_day_this_month = today.replace(day=1)
        rezervacije_ovaj_mesec = Rezervacija.objects.filter(
            clan=clan,
            datum__gte=first_day_this_month,
            datum__lte=today
        ).count()
        
        # Prošli mesec
        if today.month == 1:
            first_day_last_month = today.replace(year=today.year - 1, month=12, day=1)
            last_day_last_month = today.replace(day=1) - timedelta(days=1)
        else:
            first_day_last_month = today.replace(month=today.month - 1, day=1)
            last_day_last_month = today.replace(day=1) - timedelta(days=1)
        
        rezervacije_prosli_mesec = Rezervacija.objects.filter(
            clan=clan,
            datum__gte=first_day_last_month,
            datum__lte=last_day_last_month
        ).count()
        
        # Ukupno treninga (svih vremena)
        ukupno_treninga = Rezervacija.objects.filter(clan=clan).count()
        
        # Poslednja rezervacija
        poslednja_rezervacija = Rezervacija.objects.filter(clan=clan).order_by('-datum').first()
        
        # Streak - koliko uzastopnih dana
        streak = 0
        if poslednja_rezervacija:
            current_date = today
            while True:
                # Proveri da li ima rezervaciju na current_date
                ima_rezervaciju = Rezervacija.objects.filter(
                    clan=clan,
                    datum=current_date
                ).exists()
                
                if ima_rezervaciju:
                    streak += 1
                    current_date = current_date - timedelta(days=1)
                else:
                    # Ako je current_date danas i nema rezervaciju, nastavi jedan dan unazad
                    if current_date == today:
                        current_date = current_date - timedelta(days=1)
                        continue
                    else:
                        break
                
                # Sigurnosni break nakon 365 dana
                if streak >= 365:
                    break
        
        # Prosek nedeljno (zadnjih 30 dana)
        thirty_days_ago = today - timedelta(days=30)
        rezervacije_30_dana = Rezervacija.objects.filter(
            clan=clan,
            datum__gte=thirty_days_ago,
            datum__lte=today
        ).count()
        prosek_nedeljno = round((rezervacije_30_dana / 30) * 7, 1)
        
        # Sledeća rezervacija
        sledeca_rezervacija = Rezervacija.objects.filter(
            clan=clan,
            datum__gte=today
        ).order_by('datum', 'sat').first()
        
        data = {
            'success': True,
            'treninga_ovaj_mesec': rezervacije_ovaj_mesec,
            'treninga_prosli_mesec': rezervacije_prosli_mesec,
            'ukupno_treninga': ukupno_treninga,
            'streak_dana': streak,
            'prosek_nedeljno': prosek_nedeljno,
            'poslednja_rezervacija': {
                'datum': poslednja_rezervacija.datum.strftime('%Y-%m-%d'),
                'datum_display': poslednja_rezervacija.datum.strftime('%d.%m.%Y'),
                'sat': poslednja_rezervacija.sat
            } if poslednja_rezervacija else None,
            'sledeca_rezervacija': {
                'datum': sledeca_rezervacija.datum.strftime('%Y-%m-%d'),
                'datum_display': sledeca_rezervacija.datum.strftime('%d.%m.%Y'),
                'sat': sledeca_rezervacija.sat
            } if sledeca_rezervacija else None
        }
        
        return Response(data)
        
    except Clan.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Korisnik nema povezan profil člana'
        }, status=404)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_progress_achievements(request):
    """
    API endpoint za achievements/badges
    Vraća sve otkačene i zakačene badges
    """
    try:
        clan = Clan.objects.get(user=request.user)
        
        # Ukupan broj treninga
        ukupno_treninga = Rezervacija.objects.filter(clan=clan).count()
        
        # Trenutni streak
        today = timezone.now().date()
        streak = 0
        poslednja_rezervacija = Rezervacija.objects.filter(clan=clan).order_by('-datum').first()
        
        if poslednja_rezervacija:
            current_date = today
            while True:
                ima_rezervaciju = Rezervacija.objects.filter(
                    clan=clan,
                    datum=current_date
                ).exists()
                
                if ima_rezervaciju:
                    streak += 1
                    current_date = current_date - timedelta(days=1)
                else:
                    if current_date == today:
                        current_date = current_date - timedelta(days=1)
                        continue
                    else:
                        break
                
                if streak >= 365:
                    break
        
        # Maksimalni streak ikada
        max_streak = 0
        if poslednja_rezervacija:
            all_dates = list(Rezervacija.objects.filter(clan=clan).values_list('datum', flat=True).distinct().order_by('-datum'))
            if all_dates:
                current_streak = 1
                for i in range(len(all_dates) - 1):
                    diff = (all_dates[i] - all_dates[i + 1]).days
                    if diff == 1:
                        current_streak += 1
                        max_streak = max(max_streak, current_streak)
                    else:
                        current_streak = 1
                max_streak = max(max_streak, current_streak)
        
        # Weight loss
        weight_loss = 0
        merenja = Merenje.objects.filter(clan=clan).order_by('datum')
        if merenja.count() >= 2:
            prvo_merenje = merenja.first()
            poslednje_merenje = merenja.last()
            if prvo_merenje.tezina and poslednje_merenje.tezina:
                weight_loss = float(prvo_merenje.tezina) - float(poslednje_merenje.tezina)
        
        # Definiši sve achievements
        achievements = [
            # BRONZE TIER
            {
                'id': 'bronze_10',
                'title': 'Početnik 🥉',
                'description': 'Završi 10 treninga',
                'tier': 'bronze',
                'progress': ukupno_treninga,
                'target': 10,
                'unlocked': ukupno_treninga >= 10,
                'icon': '🥉'
            },
            {
                'id': 'bronze_streak_3',
                'title': 'Posvećen 🔥',
                'description': '3 dana uzastopno',
                'tier': 'bronze',
                'progress': max_streak,
                'target': 3,
                'unlocked': max_streak >= 3,
                'icon': '🔥'
            },
            
            # SILVER TIER
            {
                'id': 'silver_30',
                'title': 'Redovan 🥈',
                'description': 'Završi 30 treninga',
                'tier': 'silver',
                'progress': ukupno_treninga,
                'target': 30,
                'unlocked': ukupno_treninga >= 30,
                'icon': '🥈'
            },
            {
                'id': 'silver_streak_7',
                'title': 'Nedeljni Warrior 💪',
                'description': '7 dana uzastopno',
                'tier': 'silver',
                'progress': max_streak,
                'target': 7,
                'unlocked': max_streak >= 7,
                'icon': '💪'
            },
            {
                'id': 'silver_weight_5',
                'title': 'Transformer ⚡',
                'description': 'Izgubi 5kg',
                'tier': 'silver',
                'progress': round(weight_loss, 1),
                'target': 5,
                'unlocked': weight_loss >= 5,
                'icon': '⚡'
            },
            
            # GOLD TIER
            {
                'id': 'gold_100',
                'title': 'Veteran 🥇',
                'description': 'Završi 100 treninga',
                'tier': 'gold',
                'progress': ukupno_treninga,
                'target': 100,
                'unlocked': ukupno_treninga >= 100,
                'icon': '🥇'
            },
            {
                'id': 'gold_streak_30',
                'title': 'Mesečni Champion 🏆',
                'description': '30 dana uzastopno',
                'tier': 'gold',
                'progress': max_streak,
                'target': 30,
                'unlocked': max_streak >= 30,
                'icon': '🏆'
            },
            {
                'id': 'gold_weight_10',
                'title': 'Super Transformer 🌟',
                'description': 'Izgubi 10kg',
                'tier': 'gold',
                'progress': round(weight_loss, 1),
                'target': 10,
                'unlocked': weight_loss >= 10,
                'icon': '🌟'
            },
            
            # PLATINUM TIER
            {
                'id': 'platinum_365',
                'title': 'Godišnji Legend 💎',
                'description': 'Završi 365 treninga',
                'tier': 'platinum',
                'progress': ukupno_treninga,
                'target': 365,
                'unlocked': ukupno_treninga >= 365,
                'icon': '💎'
            },
            {
                'id': 'platinum_streak_100',
                'title': 'Unstoppable 🚀',
                'description': '100 dana uzastopno',
                'tier': 'platinum',
                'progress': max_streak,
                'target': 100,
                'unlocked': max_streak >= 100,
                'icon': '🚀'
            },
        ]
        
        # Podeli na unlocked i locked
        unlocked = [a for a in achievements if a['unlocked']]
        locked = [a for a in achievements if not a['unlocked']]
        
        data = {
            'success': True,
            'total_achievements': len(achievements),
            'unlocked_count': len(unlocked),
            'unlocked': unlocked,
            'locked': locked,
            'stats': {
                'ukupno_treninga': ukupno_treninga,
                'trenutni_streak': streak,
                'max_streak': max_streak,
                'weight_loss': round(weight_loss, 1) if weight_loss > 0 else 0
            }
        }
        
        return Response(data)
        
    except Clan.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Korisnik nema povezan profil člana'
        }, status=404)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)

        def check_and_send_achievement_notifications(clan):
    """
    Proveri nove achievements i pošalji push notifikacije
    """
    from .models import AchievementNotification
    from .push_notifications import send_push_to_user
    
    # Dobavi trenutne achievements
    ukupno_treninga = Rezervacija.objects.filter(clan=clan).count()
    
    # Proveri streak
    today = timezone.now().date()
    max_streak = 0
    poslednja_rezervacija = Rezervacija.objects.filter(clan=clan).order_by('-datum').first()
    
    if poslednja_rezervacija:
        all_dates = list(Rezervacija.objects.filter(clan=clan).values_list('datum', flat=True).distinct().order_by('-datum'))
        if all_dates:
            current_streak = 1
            for i in range(len(all_dates) - 1):
                diff = (all_dates[i] - all_dates[i + 1]).days
                if diff == 1:
                    current_streak += 1
                    max_streak = max(max_streak, current_streak)
                else:
                    current_streak = 1
            max_streak = max(max_streak, current_streak)
    
    # Proveri weight loss
    weight_loss = 0
    merenja = Merenje.objects.filter(clan=clan).order_by('datum')
    if merenja.count() >= 2:
        prvo_merenje = merenja.first()
        poslednje_merenje = merenja.last()
        if prvo_merenje.tezina and poslednje_merenje.tezina:
            weight_loss = float(prvo_merenje.tezina) - float(poslednje_merenje.tezina)
    
    # Lista achievements za proveru
    achievements_to_check = [
        # Bronze
        {'id': 'bronze_10', 'title': 'Početnik 🥉', 'condition': ukupno_treninga >= 10, 'message': 'Čestitamo! Završili ste 10 treninga! 🥉'},
        {'id': 'bronze_streak_3', 'title': 'Posvećen 🔥', 'condition': max_streak >= 3, 'message': 'Neverovatno! 3 dana uzastopno! 🔥'},
        
        # Silver
        {'id': 'silver_30', 'title': 'Redovan 🥈', 'condition': ukupno_treninga >= 30, 'message': 'Sjajno! Završili ste 30 treninga! 🥈'},
        {'id': 'silver_streak_7', 'title': 'Nedeljni Warrior 💪', 'condition': max_streak >= 7, 'message': 'Odlično! Cela nedelja uzastopno! 💪'},
        {'id': 'silver_weight_5', 'title': 'Transformer ⚡', 'condition': weight_loss >= 5, 'message': 'Bravo! Izgubili ste 5kg! ⚡'},
        
        # Gold
        {'id': 'gold_100', 'title': 'Veteran 🥇', 'condition': ukupno_treninga >= 100, 'message': 'Fenomenalno! 100 treninga! 🥇'},
        {'id': 'gold_streak_30', 'title': 'Mesečni Champion 🏆', 'condition': max_streak >= 30, 'message': 'Legendarno! 30 dana uzastopno! 🏆'},
        {'id': 'gold_weight_10', 'title': 'Super Transformer 🌟', 'condition': weight_loss >= 10, 'message': 'Neverovatno! Izgubili ste 10kg! 🌟'},
        
        # Platinum
        {'id': 'platinum_365', 'title': 'Godišnji Legend 💎', 'condition': ukupno_treninga >= 365, 'message': 'Legenda! 365 treninga! 💎'},
        {'id': 'platinum_streak_100', 'title': 'Unstoppable 🚀', 'condition': max_streak >= 100, 'message': 'Nezaustavljivi! 100 dana uzastopno! 🚀'},
    ]
    
    # Proveri svaki achievement
    for achievement in achievements_to_check:
        if achievement['condition']:
            # Proveri da li je već notifikovan
            already_notified = AchievementNotification.objects.filter(
                clan=clan,
                achievement_id=achievement['id']
            ).exists()
            
            if not already_notified:
                # Novi achievement! Pošalji notifikaciju
                try:
                    send_push_to_user(
                        user=clan.user,
                        title=f"🏆 Novo postignuće!",
                        body=achievement['message'],
                        data={
                            'type': 'achievement',
                            'achievement_id': achievement['id'],
                            'achievement_title': achievement['title']
                        }
                    )
                    
                    # Sačuvaj da je notifikovan
                    AchievementNotification.objects.create(
                        clan=clan,
                        achievement_id=achievement['id']
                    )
                    
                    print(f"✅ Poslata notifikacija za {achievement['id']} korisniku {clan.ime_prezime}")
                    
                except Exception as e:
                    print(f"❌ Greška pri slanju notifikacije: {e}")

       
