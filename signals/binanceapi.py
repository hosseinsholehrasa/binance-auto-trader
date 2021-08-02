import os
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


def spot_strategy(apikey, secretkey,  symbol, entry_price, volume):
    client = Client(apikey, secretkey)
    price = live_price(symbol)
    if entry_price < price:
        pass
    else:
        # 20 40 40
        try:
            market_order = client.create_test_order(symbol=symbol, side="BUY", type=client.ORDER_TYPE_MARKET, quantity=(volume/5))
            # market_order = client.order_market_buy(symbol=symbol, quantity=(volume/5))
            # limit_order1 = client.order_limit_buy(symbol=symbol, quantity=(2*volume/5), price=entry_price)
            # limit_order2 = client.order_limit_buy(symbol=symbol, quantity=(2*volume/5), price=entry_price)
            # print(market_order, limit_order1, limit_order2)
            print(market_order)
        except BinanceRequestException:
            pass
        except BinanceAPIException:
            pass
        except (BinanceOrderException, BinanceOrderMinAmountException, BinanceOrderMinPriceException, BinanceOrderMinTotalException):
            pass
        except (BinanceOrderUnknownSymbolException, BinanceOrderInactiveSymbolException):
            pass

spot_strategy(apikey, secretkey, "BTCUSDT", 41000, 100)
# client = Client(apikey, secretkey)
# order = client.create_test_order(
#         symbol="BTCUSDT",
#         side=position_type,
#         type=Client.FUTURE,
#         timeInForce=Client.TIME_IN_FORCE_GTC,
#         quantity=volume,
#         price=entry_price)
# print(client.futures_liquidation_orders())

