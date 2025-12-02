from django.contrib import admin
from .models import Clan, Uplata, Rezervacija
from .models import FCMToken  # Dodaj u postojeće imports

admin.site.register(Clan)
admin.site.register(Uplata)
admin.site.register(Rezervacija)
# FCM Token Admin
# FCM Token Admin
@admin.register(FCMToken)
class FCMTokenAdmin(admin.ModelAdmin):
    pass  # POTPUNO BASIC - BEZ CUSTOMIZACIJA
