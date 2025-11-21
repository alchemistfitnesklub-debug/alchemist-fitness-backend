# klub_app/urls.py - KOMPLETAN FAJL sa svim rutama

from django.urls import path
from . import views

urlpatterns = [
    # Osnovne stranice
    path('', views.pocetna, name='pocetna'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('trener/', views.trener_home, name='trener_home'),
    path('klijent/', views.klijent_dashboard, name='klijent_dashboard'),
    
    # Klijenti
    path('klijenti/', views.klijenti, name='klijenti'),
    path('profil/<int:clan_id>/', views.profil, name='profil'),
    
    # Rezervacije
    path('rezervacije/', views.rezervacije, name='rezervacije'),
    path('rezervacije/lista/', views.rezervacije_lista, name='rezervacije_lista'),
    
    # Statistike i ostalo
    path('statistike/', views.statistike, name='statistike'),
    path('sank/', views.sank, name='sank'),
    path('obavestenja/', views.obavestenja, name='obavestenja'),
    
    # JSON API endpoints
    path('rezervacije/json/', views.rezervacije_json, name='rezervacije_json'),
    path('rezervacije/json/clanovi/', views.rezervacije_json_clanovi, name='rezervacije_json_clanovi'),
    path('klijenti/json/clanovi/', views.klijenti_json_clanovi, name='klijenti_json_clanovi'),
    path('sank/json/clanovi/', views.sank_json_clanovi, name='sank_json_clanovi'),
    path('krediti/<int:clan_id>/', views.krediti_json, name='krediti_json'),
    
    # Actions
    path('brisi_rezervaciju/<int:rezervacija_id>/', views.brisi_rezervaciju, name='brisi_rezervaciju'),
    path('brisi_clana/<int:clan_id>/', views.brisi_clana, name='brisi_clana'),
    
    # Push notifikacije
    path('save-push-token/', views.save_push_token, name='save_push_token'),
    path('test-push/', views.test_push, name='test_push'),
    
    # Test stranice
    path('test-calendar/', views.test_calendar, name='test_calendar'),
    
    # ========== NOVO - Automatska obaveštenja ==========
    path('test-notifications/', views.test_notifications, name='test_notifications'),
    # ====================================================
]
