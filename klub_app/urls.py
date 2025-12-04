# klub_app/urls.py
from django.urls import path
from . import views
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
    path('brisi-clana/<int:clan_id>/', views.brisi_clana, name='brisi_clana'),
    
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
    path('brisi-rezervaciju/<int:rezervacija_id>/', views.brisi_rezervaciju, name='brisi_rezervaciju'),
    
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
]
