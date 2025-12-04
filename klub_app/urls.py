# klub_app/urls.py
from django.urls import path
from . import views
from . import api_views
from .fcm_views import save_fcm_token, delete_fcm_token

urlpatterns = [
    # POSTOJEĆE WEB RUTE
    path('dashboard/', views.dashboard, name='dashboard'),
    path('rezervacije/', views.rezervacije, name='rezervacije'),
    path('klijenti/', views.klijenti, name='klijenti'),
    # FCM Token endpoints
    path('api/fcm-token/', save_fcm_token, name='save_fcm_token'),
    path('api/fcm-token/delete/', delete_fcm_token, name='delete_fcm_token'),
    
    # ========== DODATO ZA AUTOCOMPLETE ==========
    path('klijenti/json/clanovi/', views.klijenti_json_clanovi, name='klijenti_json_clanovi'),
    # ============================================
    
    path('sank/', views.sank, name='sank'),
    path('obavestenja/', views.obavestenja, name='obavestenja'),
    path('statistike/', views.statistike, name='statistike'),
    path('profil/<int:clan_id>/', views.profil, name='profil'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('klijent-dashboard/', views.klijent_dashboard, name='klijent_dashboard'),
    path('rezervacije/json/', views.rezervacije_json, name='rezervacije_json'),
    path('rezervacije/json/clanovi/', views.rezervacije_json_clanovi, name='rezervacije_json_clanovi'),
    path('brisi-rezervaciju/<int:rezervacija_id>/', views.brisi_rezervaciju, name='brisi_rezervaciju'),
    path('brisi-clana/<int:clan_id>/', views.brisi_clana, name='brisi_clana'),
    path('rezervacije/lista/', views.rezervacije_lista, name='rezervacije_lista'),
    path('test-calendar/', views.test_calendar, name='test_calendar'),
    path('krediti/json/<int:clan_id>/', views.krediti_json, name='krediti_json'),
    path('save-push-token/', views.save_push_token, name='save_push_token'),
    path('test-push/', views.test_push, name='test_push'),
    path('sank/json/clanovi/', views.sank_json_clanovi, name='sank_json_clanovi'),
    path('brisi_rezervaciju/<int:rezervacija_id>/', views.brisi_rezervaciju, name='brisi_rezervaciju'),
    
    # ========== NOVO - Automatska obaveštenja ==========
    path('test-notifications/', views.test_notifications, name='test_notifications'),
    path('send-training-reminders/', views.send_training_reminders_view, name='send_training_reminders'),
    # ===================================================
    
    # API RUTE ZA MOBILNU APLIKACIJU
    path('api/login/', api_views.api_login, name='api_login'),
    path('api/logout/', api_views.api_logout, name='api_logout'),
    path('api/profil/', api_views.moj_profil, name='api_profil'),
    path('api/clanarina/', api_views.moja_clanarina, name='api_clanarina'),
    path('api/rezervacije/', api_views.moje_rezervacije, name='api_rezervacije'),
    path('api/rezervacije/kreiraj/', api_views.kreiraj_rezervaciju, name='api_kreiraj_rezervaciju'),
    path('api/rezervacije/<int:pk>/otkazi/', api_views.otkazi_rezervaciju, name='api_otkazi_rezervaciju'),
    path('api/termini/', api_views.dostupni_termini, name='api_termini'),
    path('api/obavestenja/', api_views.moja_obavestenja, name='api_obavestenja'),
    path('api/promeni-lozinku/', api_views.promeni_lozinku, name='api_promeni_lozinku'),
    path('api/promeni-username/', api_views.promeni_username, name='api_promeni_username'),
    path('api/fcm-token/', api_views.azuriraj_fcm_token, name='api_fcm_token'),
    path('api/kontaktiraj-klub/', api_views.kontaktiraj_klub, name='api_kontaktiraj_klub'),
    path('trener/', views.trener_home, name='trener_home'),
]
