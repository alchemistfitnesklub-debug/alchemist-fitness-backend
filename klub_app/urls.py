# klub_app/urls.py
from django.urls import path
from . import views
from . import api_views
from .fcm_views import save_fcm_token, delete_fcm_token

urlpatterns = [
    # ========== Osnovne stranice ==========
    path('', views.pocetna, name='pocetna'),
    path('dashboard/', views.dashboard, name='dashboard'),
    # ========== MANAGEMENT DASHBOARD - DODATO 10.12.2024 ==========
    path('dashboard/management/', views.management_dashboard, name='management_dashboard'),
    path('dashboard/management/predicted-income/', views.management_predicted_income, name='management_predicted_income'),
    path('dashboard/management/client-payments/', views.management_client_payments, name='management_client_payments'),
    path('dashboard/management/monthly-chart/', views.management_monthly_chart, name='management_monthly_chart'),
    path('dashboard/management/staff-attendance/', views.management_staff_attendance, name='management_staff_attendance'),
    path('statistike/', views.statistike, name='statistike'),
    # ========== MANAGEMENT DASHBOARD - FAZA 2 (BONUS) ==========
    path('dashboard/management/cash-flow/', views.management_cash_flow, name='management_cash_flow'),
    path('dashboard/management/retention-rate/', views.management_retention_rate, name='management_retention_rate'),
    path('dashboard/management/top-clients/', views.management_top_clients, name='management_top_clients'),
    path('dashboard/management/ghost-members/', views.management_ghost_members, name='management_ghost_members'),
    path('dashboard/management/attendance-heatmap/', views.management_attendance_heatmap, name='management_attendance_heatmap'),
    path('dashboard/management/monthly-payments/', views.management_monthly_payments, name='management_monthly_payments'),
    path('dashboard/management/customer-value/', views.management_customer_value, name='management_customer_value'),
    
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
    # Zatvaranje termina
    path('zatvori-termin/', views.zatvori_termin, name='zatvori_termin'),
    path('otvori-termin/', views.otvori_termin, name='otvori_termin'),
    
    # ========== Trener i Klijent dashboards ==========
    path('trener-home/', views.trener_home, name='trener_home'),
    path('klijent-dashboard/', views.klijent_dashboard, name='klijent_dashboard'),
    
    # ========== Push notifikacije ==========
    path('push-panel/', views.push_notification_panel, name='push_panel'),
    path('test-push/', views.test_push, name='test_push'),
    path('save-push-token/', views.save_push_token, name='save_push_token'),
    
    # ========== Automatska obaveštenja ==========
    path('test-notifications/', views.test_notifications, name='test_notifications'),
    path('send-training-reminders/', views.send_training_reminders_view, name='send_training_reminders'),
    
    # ========== Test kalendar ==========
    path('test-calendar/', views.test_calendar, name='test_calendar'),
    
    # ========== Krediti ==========
    path('krediti/<int:clan_id>/', views.krediti_json, name='krediti_json'),
    
    # ========== MERENJA - DODATO 09.12.2024 ==========
    path('profil/<int:clan_id>/dodaj-merenje/', views.dodaj_merenje, name='dodaj_merenje'),
    path('merenja/<int:merenje_id>/obrisi/', views.obrisi_merenje, name='obrisi_merenje'),
    path('merenja/<int:merenje_id>/posalji-email/', views.posalji_merenje_email, name='posalji_merenje_email'),
    path('profil/<int:clan_id>/merenja/json/', views.merenja_json, name='merenja_json'),
    path('api/clan/<int:clan_id>/merenja/', views.api_merenja_lista, name='api_merenja_lista'),
    
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
    path('api/rezervacije/kreiraj/', api_views.kreiraj_rezervaciju, name='api_kreiraj_rezervaciju_alias'),
    path('api/otkazi-rezervaciju/<int:pk>/', api_views.otkazi_rezervaciju, name='api_otkazi_rezervaciju'),
    path('api/dostupni-termini/', api_views.dostupni_termini, name='api_dostupni_termini'),
    path('api/moja-obavestenja/', api_views.moja_obavestenja, name='api_moja_obavestenja'),
    path('api/promeni-lozinku/', api_views.promeni_lozinku, name='api_promeni_lozinku'),
    path('api/promeni-username/', api_views.promeni_username, name='api_promeni_username'),
    path('api/kontaktiraj-klub/', api_views.kontaktiraj_klub, name='api_kontaktiraj_klub'),
    path('api/azuriraj-fcm-token/', api_views.azuriraj_fcm_token, name='api_azuriraj_fcm_token'),
    # Progress Dashboard API - DODATO 22.12.2024
    path('api/progress/merenja/', views.api_progress_merenja, name='api_progress_merenja'),
    path('api/progress/statistika/', views.api_progress_statistika, name='api_progress_statistika'),
    path('api/progress/achievements/', views.api_progress_achievements, name='api_progress_achievements'),
    
    # ========== API aliases za Flutter mobile app (stari endpoint-i) ==========
    path('api/profil/', api_views.moj_profil, name='api_profil_alias'),
    path('api/rezervacije/', api_views.moje_rezervacije, name='api_rezervacije_alias'),
    path('api/clanarina/', api_views.moja_clanarina, name='api_clanarina_alias'),
    path('api/termini/', api_views.dostupni_termini, name='api_termini_alias'),
    path('api/rezervacije/kreiraj/', api_views.kreiraj_rezervaciju, name='api_kreiraj_rezervaciju_alias'),
    path('api/rezervacije/<int:pk>/otkazi/', api_views.otkazi_rezervaciju, name='api_otkazi_rezervaciju_alias'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),

    # Izmena/Brisanje Uplata - Samo Admin
    path('uplata/delete/<int:uplata_id>/', views.delete_uplata, name='delete_uplata'),
    path('uplata/edit/<int:uplata_id>/', views.edit_uplata, name='edit_uplata'),

    # ========== image ==========
    path('api/share/generate-image/', views.api_generate_share_image, name='api_generate_share_image'),
]
