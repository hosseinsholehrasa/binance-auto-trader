from django.contrib import admin
from signals.models import FutureSignal, SpotSignal, SpotControler, EntryPrice, TakeProfit


# @admin.register(FutureSignal)
# class FutureSignalAdmin(admin.ModelAdmin):
#     list_display = ('telegram_user',"order_id", "symbol_name")
#     search_fields = ('telegram_user__id', 'order_id', 'symbol_name')
#     list_filter = ("created_at", "updated_at")
#     ordering = ('-created_at',)
#     autocomplete_fields = ("telegram_user",)


admin.site.register(FutureSignal)
admin.site.register(SpotSignal)
admin.site.register(SpotControler)
admin.site.register(EntryPrice)
admin.site.register(TakeProfit)