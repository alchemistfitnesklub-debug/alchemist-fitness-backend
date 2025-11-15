# fitnes_projekat/urls.py – CEO FAJL – 100% KOMPLETAN, ISPRAVLJEN, RADI ODMAH!

from django.contrib import admin
from django.urls import path, include
from klub_app import views as klub_views  # ← OVO MORA BITI GORE!

# MEDIA ZA SLIKE – OBAVEZNO!
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin panel
    path('admin/', admin.site.urls),

    # Naši custom login/logout
    path('login/', klub_views.login_view, name='login'),
    path('logout/', klub_views.logout_view, name='logout'),

    # Sve ostale stranice preko klub_app
    path('', include('klub_app.urls')),
]

# SERVIRANJE SLIKA I MEDIJA U DEVELOPMENTU
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)