from django.contrib import admin
from .models import Clan, Uplata, Rezervacija, FCMToken, AchievementNotification

admin.site.register(Clan)
admin.site.register(Uplata)
admin.site.register(Rezervacija)

# FCM Token Admin
@admin.register(FCMToken)
class FCMTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_type', 'token_preview', 'is_active', 'created_at']
    list_filter = ['device_type', 'is_active', 'created_at']
    search_fields = ['user__username', 'token']
    readonly_fields = ['created_at', 'updated_at']
    
    def token_preview(self, obj):
        if obj.token:
            return f"{obj.token[:30]}..."
        return "No token"
    token_preview.short_description = 'Token'

@admin.register(AchievementNotification)
class AchievementNotificationAdmin(admin.ModelAdmin):
    list_display = ['clan', 'achievement_id', 'notified_at']
    list_filter = ['notified_at']
    search_fields = ['clan__ime_prezime', 'achievement_id']
