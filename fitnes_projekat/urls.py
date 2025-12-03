# fitnes_projekat/urls.py – SA FCM ENDPOINTS!
from django.contrib import admin
from django.urls import path, include
from klub_app import views as klub_views
from klub_app import fcm_views  # 🔥 NOVO - za FCM endpoints!

# MEDIA ZA SLIKE – OBAVEZNO!
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin panel
    path('admin/', admin.site.urls),
    
    # Naši custom login/logout
    path('login/', klub_views.login_view, name='login'),
    path('logout/', klub_views.logout_view, name='logout'),
    
    # 🔥 NOVO - FCM Token API endpoints
    path('api/fcm-token/save/', fcm_views.save_fcm_token, name='save_fcm_token'),
    path('api/fcm-token/delete/', fcm_views.delete_fcm_token, name='delete_fcm_token'),
    
    # Sve ostale stranice preko klub_app
    path('', include('klub_app.urls')),
]

# SERVIRANJE SLIKA I MEDIJA U DEVELOPMENTU
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
