from os import terminal_size
from django.db import models
from django.db.models.base import Model
from django.utils.timezone import now


ORDER_STATUS_CHOICES = (
    ('NEW', 'NEW'),
    ('PARTIALLY_FILLED', 'PARTIALLY_FILLED'),
    ('FILLED', 'FILLED'),
    ('CANCELED', 'CANCELED'),
    ('PENDING_CANCEL', 'PENDING_CANCEL'),
    ('REJECTED', 'REJECTED'),
    ('EXPIRED', 'EXPIRED')
)

SIDE_CHOICES = (
    ("BUY", "BUY"),
    ("SELL", "SELL")
)


class EntryPrice(models.Model):
    min_price = models.FloatField(null=True, blank=True)
    max_price = models.FloatField(null=True, blank=True)


class TakeProfit(models.Model):
    price = models.FloatField(null=True, blank=True)
    level = models.IntegerField(default=1)


class FutureSignal(models.Model):
    telegram_user = models.ForeignKey("users.TelegramUser", on_delete=models.CASCADE)
    order_id = models.IntegerField(null=True, blank=True)
    symbol_name = models.CharField(max_length=32, null=True, blank=True)
    entry_prices = models.ManyToManyField("EntryPrice", related_name="future_signals", blank=True)

    stop_loss = models.FloatField(null=True, blank=True)
    take_profits = models.ManyToManyField("TakeProfit", related_name="future_signals",blank=True)
    volume = models.FloatField(null=True, blank=True)

    levrage = models.IntegerField(null=True, blank=True)
    position = models.CharField(max_length=32, null=True, blank=True)
    side = models.CharField(max_length=32, null=True, blank=True, choices=SIDE_CHOICES)

    order_type = models.CharField(max_length=32, null=True, blank=True)
    order_status = models.CharField(max_length=32, null=True, blank=True, choices=ORDER_STATUS_CHOICES)
    isin_next_level = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.telegram_user.__str__()

class SpotSignal(models.Model):
    telegram_user = models.ForeignKey("users.TelegramUser", on_delete=models.CASCADE)
    symbol_name = models.CharField(max_length=32, null=True, blank=True)
    entry_prices = models.ManyToManyField("EntryPrice", related_name="spot_signals", blank=True)

    stop_loss = models.FloatField(null=True, blank=True)
    take_profits = models.ManyToManyField("TakeProfit", related_name="spot_signals", blank=True)
    volume = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.telegram_user.__str__()


class SpotOrder(models.Model):
    spot_signal = models.ForeignKey("SpotSignal", null=True, on_delete=models.SET_NULL)
    order_id = models.IntegerField(null=True, blank=True)
    symbol_name = models.CharField(max_length=32, null=True, blank=True)

    price = models.FloatField(null=True, blank=True)
    stop_loss = models.FloatField(null=True, blank=True)
    take_profit = models.FloatField(null=True, blank=True)
    volume = models.FloatField(null=True, blank=True)

    type = models.CharField(max_length=32, null=True, blank=True)
    status = models.CharField(max_length=32, null=True, blank=True, choices=ORDER_STATUS_CHOICES)
    side = models.CharField(max_length=32, null=True, blank=True, choices=SIDE_CHOICES)

    isin_next_level = models.BooleanField(default=False)
    priority = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)


class SpotControler(models.Model):
    spot_signal = models.ForeignKey("SpotSignal", null=True, on_delete=models.SET_NULL)
    first_orders = models.ManyToManyField("SpotOrder", related_name="first_orders")
    second_orders = models.ManyToManyField("SpotOrder", related_name="second_orders")