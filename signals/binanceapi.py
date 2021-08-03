from _typeshed import FileDescriptor
import os
import random
from traderbot.signals.models import EntryPrice, SpotControler, SpotSignal, SpotOrder
from users.models import TelegramUser, BinanceUser
from binance import Client
from binance.exceptions import BinanceRequestException, BinanceAPIException, BinanceOrderException, \
    BinanceOrderMinAmountException, BinanceOrderMinPriceException, BinanceOrderMinTotalException, \
    BinanceOrderUnknownSymbolException, BinanceOrderInactiveSymbolException

############################# CELERY CONFIGURATOIN
from celery import Celery
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = os.environ.get('REDIS_PORT', '6379')
BROKER_URL = 'redis://' + REDIS_HOST + ':' + REDIS_PORT + '/0'
app = Celery('tasks', broker=BROKER_URL, backend=BROKER_URL)
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Tehran',
    enable_utc=True,
)


# import os
# # for combining django and telegram
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "traderbot.settings")
# from django.core.wsgi import get_wsgi_application
# application = get_wsgi_application()

# from django.conf import settings
# from traderbot.celery import app


# secretkey = settings.BINANCE_SECRET_KEY
# apikey = settings.BINANCE_API_KEY
secretkey = "hnA7Zepip4mpX3WqbUBStyLwa5ZPrpVbnjrERYL0VymjTqwNUo5LUUYEYj8MIqBv"
apikey = "ZrZe7Sl17mcok8gEKe5SKQy9Jcpcggn3JK0J7LZWXmCU6d6ZZ8073Mjr3nw476JT"

# initialization 
def intialize_symbol_name():
    client = Client(apikey, secretkey)
    all_tackers_name = client.get_all_tickers()
    symbol_names = [all_tackers_name[i]['symbol'] for i in range(len(all_tackers_name))]
    return symbol_names


# main
def live_price(symb):
    client = Client(apikey, secretkey)
    if symb.upper() in intialize_symbol_name():
        price_dic = client.get_symbol_ticker(symbol=symb)
        return float(price_dic['price'])
    else:
        return "wrong symbol name"

@app.task
def spot_controller_checker1(apikey, secretkey, spot_controller_id, first_stage=True, second_stage=False):
    client = Client(apikey, secretkey)
    spot_controller = SpotControler.objects.get(id=spot_controller_id)
    # TODO be in another function when first_stage=False   
    if second_stage:
        order4, order5, order6 = spot_controller.second_orders.all().order_by("priority")
        # mesle payiini faghat order haye oonvaro bayad cancell kone 
        # baraye check kardanesh bayad did OCO che joorie
        if order4.isin_next_level == False:
            if order4.status == client.ORDER_STATUS_FILLED:
                order4.isin_next_level = True
                order4.save()
                first_stage = False
            else:
                # get order status
                pass
        elif order5.isin_next_level == False:
            if order5.status == client.ORDER_STATUS_FILLED:
                order5.isin_next_level = True
                order5.save()
                first_stage = False
            else:
                # get order status
                pass
    if first_stage:
        order1, order2, order3 = spot_controller.first_orders.all().order_by("priority")
        # OCO1 gozashte shode? are pas boro baadi age na bebin filled shode ya na? age na check kon status age are pas bezar
        if order1.isin_next_level == False:

            if order1.status == client.ORDER_STATUS_FILLED:
                # Create 3 OCO
                second_stage = True 
                order1.isin_next_level = True
                order1.save()
            else:
                # get order status
                pass
        elif order2.isin_next_level == False:
            if order2.status == client.ORDER_STATUS_FILLED:
                order4, order5, order6 = spot_controller.second_orders.all().order_by("priority")
                # cancell  last 3 OCO
                spot_controller.second_orders.remove(order4, order5, order6)

                # Create 3 OCO
                second_stage = True
                order2.isin_next_level = True
                order2.save()
            else:
                # get order status
                pass
        elif order3.isin_next_level == False:
            if order3.status == client.ORDER_STATUS_FILLED:
                order4, order5, order6 = spot_controller.second_orders.all().order_by("priority")
                # cancell  last 3 OCO binance
                spot_controller.second_orders.remove(order4, order5, order6)
                # Create 3 OCO binance
                second_stage = True 
                order3.isin_next_level = True
                order3.save()
            else:
                # get order status
                order = client.get_order(symbol=order3.symbol_name, orderId=order3.order_id)
                if order["status"] == client.ORDER_STATUS_FILLED:
                    order3.status = client.ORDER_STATUS_FILLED
                    order3.save()
                    first_stage = False

        spot_controller_checker1.apply_async(
            (apikey, secretkey, spot_controller.id, first_stage, second_stage),
            countdown=random.uniform(10, 15),
            )

@app.task
def spot_strategy(apikey, secretkey, signal_id):
    client = Client(apikey, secretkey)
    # initalized
    signal = SpotSignal.objects.get(id=signal_id)
    symbol = signal.symbol_name
    entry_price = signal.entry_prices[0]
    price = live_price(symbol)
    volume = signal.volume

    if entry_price.max_price < price:
        try:            
            limit_order1 = client.order_limit_buy(symbol=symbol, quantity=(volume/5))
            order1 = SpotOrder.objects.create(order_id=limit_order1["orderId"], spot_signal=signal, symbol_name=symbol, price=entry_price.max_price,
                                                volume=volume/5, side="BUY", priority=1, type="LIMIT")
            
            mid_price = (entry_price.max_price + entry_price.min_price) / 2
            limit_order2 = client.order_limit_buy(symbol=symbol, quantity=(2*volume/5), price=mid_price)
            order2 = SpotOrder.objects.create(order_id=limit_order2["orderId"], spot_signal=signal, symbol_name=symbol, price=mid_price,
                                                volume=(2*volume/5), side="BUY", priority=2, type="LIMIT")
            limit_order3 = client.order_limit_buy(symbol=symbol, quantity=(2*volume/5), price=entry_price.min_price)
            order3 = SpotOrder.objects.create(order_id=limit_order3["orderId"], spot_signal=signal, symbol_name=symbol, price=entry_price.min_price,
                                                volume=(2*volume/5), side="BUY", priority=3, type="LIMIT")
            spot_controller = SpotControler.objects.create(spot_signal=signal)
            spot_controller.first_orders.add(order1, order2, order3)
            print(limit_order1, limit_order2, limit_order3)
            spot_controller_checker1.apply_async(
                (apikey, secretkey, spot_controller.id),
                countdown=random.uniform(10, 15),
            )
        except BinanceRequestException:
            pass
        except BinanceAPIException:
            pass
        except (BinanceOrderException, BinanceOrderMinAmountException, BinanceOrderMinPriceException, BinanceOrderMinTotalException):
            pass
        except (BinanceOrderUnknownSymbolException, BinanceOrderInactiveSymbolException):
            pass
    else:
        # 20 40 40
        try:            
            market_order = client.order_market_buy(symbol=symbol, quantity=(volume/5))
            order1 = SpotOrder.objects.create(order_id=market_order["orderId"], spot_signal=signal, symbol_name=symbol, price=price,
                                              volume=volume/5, side="BUY", priority=1, type="MARKET")
            
            mid_price = (entry_price.max_price + entry_price.min_price) / 2
            limit_order1 = client.order_limit_buy(symbol=symbol, quantity=(2*volume/5), price=mid_price)
            order2 = SpotOrder.objects.create(order_id=limit_order1["orderId"], spot_signal=signal, symbol_name=symbol, price=mid_price,
                                              volume=(2*volume/5), side="BUY", priority=2, type="LIMIT")
            limit_order2 = client.order_limit_buy(symbol=symbol, quantity=(2*volume/5), price=entry_price.min_price)
            order3 = SpotOrder.objects.create(order_id=limit_order2["orderId"], spot_signal=signal, symbol_name=symbol, price=entry_price.min_price,
                                              volume=(2*volume/5), side="BUY", priority=3, type="LIMIT")
            spot_controller = SpotControler.objects.create(spot_signal=signal)
            spot_controller.first_orders.add(order1, order2, order3)
            print(market_order, limit_order1, limit_order2)

            spot_controller_checker1.apply_async(
                (apikey, secretkey, spot_controller.id),
                countdown=random.uniform(10, 15),
            )
        except BinanceRequestException:
            pass
        except BinanceAPIException:
            pass
        except (BinanceOrderException, BinanceOrderMinAmountException, BinanceOrderMinPriceException, BinanceOrderMinTotalException):
            pass
        except (BinanceOrderUnknownSymbolException, BinanceOrderInactiveSymbolException):
            pass




# spot_strategy(apikey, secretkey, "BTCUSDT", 41000, 100)


