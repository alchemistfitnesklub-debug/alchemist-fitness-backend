# klub_app/urls.py
from django.urls import path
from . import views
from . import api_views
from .fcm_views import save_fcm_token, delete_fcm_token

urlpatterns = [
    # ========== Osnovne stranice ==========
    path('', views.pocetna, name='pocetna'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('statistike/', views.statistike, name='statistike'),
    
    # ========== Klijenti ==========
    path('klijenti/', views.klijenti, name='klijenti'),
    path('klijenti/json/', views.klijenti_json_clanovi, name='klijenti_json_clanovi'),
    path('profil/<int:clan_id>/', views.profil, name='profil'),
    path('brisi_clana/<int:clan_id>/', views.brisi_clana, name='brisi_clana'),
    
    # ========== Šank ==========
    path('sank/', views.sank, name='sank'),
    path('sank/json/clanovi/', views.sank_json_clanovi, name='sank_json_clanovi'),
    
    # ========== Obaveštenja ==========
    path('obavestenja/', views.obavestenja, name='obavestenja'),
    
    # ========== Rezervacije ==========
    path('rezervacije/', views.rezervacije, name='rezervacije'),
    path('rezervacije/lista/', views.rezervacije_lista, name='rezervacije_lista'),
    path('rezervacije/json/', views.rezervacije_json, name='rezervacije_json'),
    path('rezervacije/json/clanovi/', views.rezervacije_json_clanovi, name='rezervacije_json_clanovi'),
    path('brisi_rezervaciju/<int:rezervacija_id>/', views.brisi_rezervaciju, name='brisi_rezervaciju'),
    
    # ========== Trener i Klijent dashboards ==========
    path('trener-home/', views.trener_home, name='trener_home'),
    path('klijent-dashboard/', views.klijent_dashboard, name='klijent_dashboard'),
    
    # ========== Push notifikacije ==========
    path('test-push/', views.test_push, name='test_push'),
    path('save-push-token/', views.save_push_token, name='save_push_token'),
    
    # ========== Automatska obaveštenja ==========
    path('test-notifications/', views.test_notifications, name='test_notifications'),
    path('send-training-reminders/', views.send_training_reminders_view, name='send_training_reminders'),
    
    # ========== Test kalendar ==========
    path('test-calendar/', views.test_calendar, name='test_calendar'),
    
    # ========== Krediti ==========
    path('krediti/<int:clan_id>/', views.krediti_json, name='krediti_json'),
    
    # ========== FCM Token Management ==========
    path('api/fcm-token/save/', save_fcm_token, name='save_fcm_token_api'),
    path('api/fcm-token/delete/', delete_fcm_token, name='delete_fcm_token_api'),
    
    # ========== API endpoints za mobilnu aplikaciju ==========
    path('api/login/', api_views.api_login, name='api_login'),
    path('api/logout/', api_views.api_logout, name='api_logout'),
    path('api/moj-profil/', api_views.moj_profil, name='api_moj_profil'),
    path('api/moja-clanarina/', api_views.moja_clanarina, name='api_moja_clanarina'),
    path('api/moje-rezervacije/', api_views.moje_rezervacije, name='api_moje_rezervacije'),
    path('api/kreiraj-rezervaciju/', api_views.kreiraj_rezervaciju, name='api_kreiraj_rezervaciju'),
    path('api/otkazi-rezervaciju/<int:pk>/', api_views.otkazi_rezervaciju, name='api_otkazi_rezervaciju'),
    path('api/dostupni-termini/', api_views.dostupni_termini, name='api_dostupni_termini'),
    path('api/moja-obavestenja/', api_views.moja_obavestenja, name='api_moja_obavestenja'),
    path('api/promeni-lozinku/', api_views.promeni_lozinku, name='api_promeni_lozinku'),
    path('api/promeni-username/', api_views.promeni_username, name='api_promeni_username'),
    path('api/kontaktiraj-klub/', api_views.kontaktiraj_klub, name='api_kontaktiraj_klub'),
    path('api/azuriraj-fcm-token/', api_views.azuriraj_fcm_token, name='api_azuriraj_fcm_token'),
]
