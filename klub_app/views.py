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
from .models import Clan, Uplata, Rezervacija, Stock, Sale, Obavestenje, UserProfile
from .forms import ClanForm, UplataForm, SaleForm
from .services.firebase_service import send_push_notification


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

        uplate = Uplata.objects.filter(datum__gte=from_date, datum__lte=to_date).select_related('clan')
        daily_payments = uplate.values('datum').annotate(total=Sum('iznos')).order_by('datum')
        sales = Sale.objects.filter(datum__date__gte=from_date, datum__date__lte=to_date).select_related('stock')
        daily_sales = sales.values('datum__date').annotate(total=Sum('price')).order_by('datum__date')
        water_sales = sales.filter(stock__naziv__icontains='voda').values('datum__date').annotate(total=Sum('price')).order_by('datum__date')

        labels = [entry['datum'].strftime('%Y-%m') for entry in daily_payments if entry['datum']]
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

            message = f"Vaši podaci za logovanje: Username: {username}, Password: default123"

            if clan.email:
                send_mail(
                    'Podaci za logovanje',
                    message,
                    settings.EMAIL_HOST_USER,
                    [clan.email],
                    fail_silently=True
                )
                messages.success(request, 'Podaci za logovanje poslati na email!')
            else:
                messages.error(request, 'Član nema email adresu!')

        return redirect('profil', clan_id=clan_id)

    context = {
        'clan': clan,
        'uplate': uplate,
        'istorija_rezervacija': istorija_rezervacija,
        'is_trener': is_trener,
        'is_klijent': is_klijent,
        'clan_form': ClanForm(instance=clan),
        'uplata_form': UplataForm(),
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
    return render(request, 'klub_app/privacy_policy.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'Uspešno ste se odjavili.')
    return redirect('klub_app:login')
