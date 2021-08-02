from django.db import models
from django.utils.timezone import now


class TelegramUser(models.Model):
    id = models.IntegerField(primary_key=True)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return str(self.id)

class BinanceUser(models.Model):
    telegram_user = models.OneToOneField("TelegramUser", on_delete=models.CASCADE, primary_key=True)
    api_key = models.CharField(max_length=160, null=True, blank=True)
    secret_key = models.CharField(max_length=160, null=True, blank=True)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.telegram_user.__str__()