from django.contrib import admin
from users.models import BinanceUser, TelegramUser


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('id',)
    search_fields = ('id',)
    list_filter = ("created_at", "updated_at")
    ordering = ('-created_at',)


@admin.register(BinanceUser)
class BinanceUserAdmin(admin.ModelAdmin):
    list_display = ('telegram_user',)
    search_fields = ('telegram_user__id', 'api_key', 'secret_key')
    list_filter = ("created_at", "updated_at")
    ordering = ('-created_at',)
    autocomplete_fields = ("telegram_user",)


