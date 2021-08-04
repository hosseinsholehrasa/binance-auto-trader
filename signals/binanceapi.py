##################################
# import os
# # for combining django and telegram
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "traderbot.settings")
# from django.core.wsgi import get_wsgi_application
# application = get_wsgi_application()
#########################################


import os
import random
import math
import requests
from signals.models import EntryPrice, SpotControler, SpotSignal, SpotOrder
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

def get_oco_order(client, order_list_id):
    timestamp = client.get_server_time()["serverTime"]
    params = {
        "timestamp": timestamp,
        "orderListId": order_list_id
    }
    return client._get("orderList", True , version='v3', data=params)


def create_3_oco_orders(apikey, secretkey, spot_controller_id):
    pass

def cancel_3_oco_orders(client, order4, order5, order6):
    order4_response = get_oco_order(client, order4.order_id)
    if not order4_response['listOrderStatus'] == "ALL_DONE":
        client.cancel_order(symbol=order4.symbol_name, orderId=order4_response["orders"][0]["orderId"])
        order4.status = client.ORDER_STATUS_CANCELED
        order4.save()
    
    order5_response = get_oco_order(client, order5.order_id)
    if not order5_response['listOrderStatus'] == "ALL_DONE":
        client.cancel_order(symbol=order5.symbol_name, orderId=order5_response["orders"][0]["orderId"])
        order5.status = client.ORDER_STATUS_CANCELED
        order5.save()

    order6_response = get_oco_order(client, order6.order_id)
    if not order6_response['listOrderStatus'] == "ALL_DONE":
        client.cancel_order(symbol=order6.symbol_name, orderId=order6_response["orders"][0]["orderId"])
        order6.status = client.ORDER_STATUS_CANCELED
        order6.save()

# in OCO sell price is tp and limit and stop is stop loss
# limit maker hamoon tp 
@app.task
def spot_controller_checker1(apikey, secretkey, spot_controller_id, first_stage=True, second_stage=False):
    client = Client(apikey, secretkey)
    spot_controller = SpotControler.objects.get(id=spot_controller_id)
    price = live_price(spot_controller.spot_signal.symbol_name)

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
    ###################### FIRST STAGE #####################
    if first_stage:
        order1, order2, order3 = spot_controller.first_orders.all().order_by("priority")
        tp1, tp2 , tp3 = spot_controller.spot_signal.take_profits.all().order_by("level")
        sl = spot_controller.spot_signal.stop_loss
        # OCO1 gozashte shode? are pas boro baadi age na bebin filled shode ya na? age na check kon status age are pas bezar
        if order1.isin_next_level == False:
            if order1.status == client.ORDER_STATUS_FILLED:

                # order4 - order OCO for order 1
                OCO_order4 = client.order_oco_sell(
                    symbol=order1.symbol_name,
                    quantity=((2*order1.volume/5)/price),
                    price=tp1,
                    stopPrice=((1/100*sl) + sl),
                    stopLimitPrice=sl,
                    stopLimitTimeInForce="GTC"
                )
                order4 = SpotOrder.objects.create(
                    order_id=OCO_order4["orderListId"],
                    spot_signal=order1.spot_signal,
                    symbol_name=order1.symbol,
                    price=tp1,
                    take_profit=tp1,
                    stop_loss=sl,
                    volume=(2*order1.volume/5),
                    side="SELL",
                    priority=1,
                    type="OCO"
                )
                # order5 - order OCO for order 1
                OCO_order5 = client.order_oco_sell(
                    symbol=order1.symbol_name,
                    quantity=((2*order1.volume/5)/price),
                    price=tp2,
                    stopPrice=((1/100*sl) + sl),
                    stopLimitPrice=sl,
                    stopLimitTimeInForce="GTC"
                    )
                order5 = SpotOrder.objects.create(
                    order_id=OCO_order5["orderListId"],
                    spot_signal=order1.spot_signal,
                    symbol_name=order1.symbol,
                    price=tp2,
                    take_profit=tp2,
                    stop_loss=sl,
                    volume=(2*order1.volume/5),
                    side="SELL",
                    priority=2,
                    type="OCO"
                )               
                # order6 - order OCO for order 1
                OCO_order6 = client.order_oco_sell(
                    symbol=order1.symbol_name,
                    quantity=((order1.volume/5)/price),
                    price=tp3,
                    stopPrice=((1/100*sl) + sl),
                    stopLimitPrice=sl,
                    stopLimitTimeInForce="GTC"
                )
                order6 = SpotOrder.objects.create(
                    order_id=OCO_order6["orderListId"],
                    spot_signal=order1.spot_signal,
                    symbol_name=order1.symbol,
                    price=tp3,
                    take_profit=tp3,
                    stop_loss=sl,
                    volume=(order1.volume/5),
                    side="SELL",
                    priority=3,
                    type="OCO"
                )               
                
                spot_controller.second_orders.add(order4, order5, order6)
                second_stage = True 
                order1.isin_next_level = True
                order1.save()

            else:
                # get order status
                order = client.get_order(symbol=order1.symbol_name, orderId=order1.order_id)
                if order["status"] == client.ORDER_STATUS_FILLED:
                    order1.status = client.ORDER_STATUS_FILLED
                    order1.save()

        elif order2.isin_next_level == False:
            if order2.status == client.ORDER_STATUS_FILLED:
                order4, order5, order6 = spot_controller.second_orders.all().order_by("priority")
                
                # cancel 3 oco order
                cancel_3_oco_orders(client, order4, order5, order6)
                # remove last 3 orders
                spot_controller.second_orders.remove(order4, order5, order6)

                # order4 - order OCO for order 2
                OCO_order4 = client.order_oco_sell(
                    symbol=order2.symbol_name,
                    quantity=((2*(order1.volume + order2.volume)/5)/price),
                    price=tp1,
                    stopPrice=((1/100*sl) + sl),
                    stopLimitPrice=sl,
                    stopLimitTimeInForce="GTC"
                )
                order4 = SpotOrder.objects.create(
                    order_id=OCO_order4["orderListId"],
                    spot_signal=order2.spot_signal,
                    symbol_name=order2.symbol,
                    price=tp1,
                    take_profit=tp1,
                    stop_loss=sl,
                    volume=(2*(order1.volume + order2.volume)/5),
                    side="SELL",
                    priority=1,
                    type="OCO"
                )
                # order5 - order OCO for order 2
                OCO_order5 = client.order_oco_sell(
                    symbol=order2.symbol_name,
                    quantity=((2*(order1.volume + order2.volume)/5)/price),
                    price=tp2,
                    stopPrice=((1/100*sl) + sl),
                    stopLimitPrice=sl,
                    stopLimitTimeInForce="GTC"
                    )
                order5 = SpotOrder.objects.create(
                    order_id=OCO_order5["orderListId"],
                    spot_signal=order2.spot_signal,
                    symbol_name=order2.symbol,
                    price=tp2,
                    take_profit=tp2,
                    stop_loss=sl,
                    volume=(2*(order1.volume + order2.volume)/5),
                    side="SELL",
                    priority=2,
                    type="OCO"
                )               
                # order6 - order OCO for order 2
                OCO_order6 = client.order_oco_sell(
                    symbol=order2.symbol_name,
                    quantity=(((order1.volume + order2.volume)/5)/price),
                    price=tp3,
                    stopPrice=((1/100*sl) + sl),
                    stopLimitPrice=sl,
                    stopLimitTimeInForce="GTC"
                )
                order6 = SpotOrder.objects.create(
                    order_id=OCO_order6["orderListId"],
                    spot_signal=order2.spot_signal,
                    symbol_name=order2.symbol,
                    price=tp3,
                    take_profit=tp3,
                    stop_loss=sl,
                    volume=((order1.volume + order2.volume)/5),
                    side="SELL",
                    priority=3,
                    type="OCO"
                )  

                spot_controller.second_orders.add(order4, order5, order6)
                second_stage = True
                order2.isin_next_level = True
                order2.save()
            else:
                # get order status
                order = client.get_order(symbol=order2.symbol_name, orderId=order2.order_id)
                if order["status"] == client.ORDER_STATUS_FILLED:
                    order2.status = client.ORDER_STATUS_FILLED
                    order2.save()
        elif order3.isin_next_level == False:
            if order3.status == client.ORDER_STATUS_FILLED:
                order4, order5, order6 = spot_controller.second_orders.all().order_by("priority")
                
                # cancel 3 oco order
                cancel_3_oco_orders(client, order4, order5, order6)
                # remove last 3 orders
                spot_controller.second_orders.remove(order4, order5, order6)

                # order4 - order OCO for order 3
                OCO_order4 = client.order_oco_sell(
                    symbol=order3.symbol_name,
                    quantity=((2*(order1.volume + order2.volume + order3.volume)/5)/price),
                    price=tp1,
                    stopPrice=((1/100*sl) + sl),
                    stopLimitPrice=sl,
                    stopLimitTimeInForce="GTC"
                )
                order4 = SpotOrder.objects.create(
                    order_id=OCO_order4["orderListId"],
                    spot_signal=order3.spot_signal,
                    symbol_name=order3.symbol,
                    price=tp1,
                    take_profit=tp1,
                    stop_loss=sl,
                    volume=(2*(order1.volume + order2.volume + order3.volume)/5),
                    side="SELL",
                    priority=1,
                    type="OCO"
                )
                # order5 - order OCO for order 3
                OCO_order5 = client.order_oco_sell(
                    symbol=order3.symbol_name,
                    quantity=((2*(order1.volume + order2.volume + order3.volume)/5)/price),
                    price=tp2,
                    stopPrice=((1/100*sl) + sl),
                    stopLimitPrice=sl,
                    stopLimitTimeInForce="GTC"
                    )
                order5 = SpotOrder.objects.create(
                    order_id=OCO_order5["orderListId"],
                    spot_signal=order3.spot_signal,
                    symbol_name=order3.symbol,
                    price=tp2,
                    take_profit=tp2,
                    stop_loss=sl,
                    volume=(2*(order1.volume + order2.volume + order3.volume)/5),
                    side="SELL",
                    priority=2,
                    type="OCO"
                )               
                # order6 - order OCO for order 3
                OCO_order6 = client.order_oco_sell(
                    symbol=order3.symbol_name,
                    quantity=(((order1.volume + order2.volume + order3.volume)/5)/price),
                    price=tp3,
                    stopPrice=((1/100*sl) + sl),
                    stopLimitPrice=sl,
                    stopLimitTimeInForce="GTC"
                )
                order6 = SpotOrder.objects.create(
                    order_id=OCO_order6["orderListId"],
                    spot_signal=order3.spot_signal,
                    symbol_name=order3.symbol,
                    price=tp3,
                    take_profit=tp3,
                    stop_loss=sl,
                    volume=((order1.volume + order2.volume + order3.volume)/5),
                    side="SELL",
                    priority=3,
                    type="OCO"
                )

                spot_controller.second_orders.add(order4, order5, order6)

                first_stage = False
                second_stage = True 
                order3.isin_next_level = True
                order3.save()
            else:
                # get order status
                order = client.get_order(symbol=order3.symbol_name, orderId=order3.order_id)
                if order["status"] == client.ORDER_STATUS_FILLED:
                    order3.status = client.ORDER_STATUS_FILLED
                    order3.save()


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
            # ORDER 1 -  LIMIT order            
            limit_order1 = client.order_limit_buy(
                symbol=symbol,
                quantity=(math.floor((volume/5)/price)),
                price=entry_price.max_price,
                timeInForce="GTC"
                )
            order1 = SpotOrder.objects.create(
                order_id=limit_order1["orderId"],
                spot_signal=signal,
                symbol_name=symbol,
                price=entry_price.max_price,
                volume=volume/5,
                side="BUY",
                priority=1,
                type="LIMIT"
            )
            
            # ORDER 2 -  LIMIT order    
            mid_price = (entry_price.max_price + entry_price.min_price) / 2
            limit_order2 = client.order_limit_buy(
                symbol=symbol,
                quantity=math.floor((2*volume/5)/price),
                price=mid_price,
                timeInForce="GTC"
            )
            order2 = SpotOrder.objects.create(
                order_id=limit_order2["orderId"],
                spot_signal=signal,
                symbol_name=symbol,
                price=mid_price,
                volume=(2*volume/5),
                side="BUY",
                priority=2,
                type="LIMIT"
            )

            # ORDER 3 -  LIMIT order 
            limit_order3 = client.order_limit_buy(
                symbol=symbol,
                quantity=math.floor((2*volume/5)/price),
                price=entry_price.min_price,
                timeInForce="GTC"
            )
            order3 = SpotOrder.objects.create(
                order_id=limit_order3["orderId"],
                spot_signal=signal,
                symbol_name=symbol,
                price=entry_price.min_price,
                volume=(2*volume/5),
                side="BUY",
                priority=3,
                type="LIMIT"
            )
            print(limit_order1, limit_order2, limit_order3)

            # create spot controller
            spot_controller = SpotControler.objects.create(spot_signal=signal)
            spot_controller.first_orders.add(order1, order2, order3)
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

            # ORDER 1 -  MARKET order    
            market_order1 = client.order_market_buy(
                symbol=symbol,
                quoteOrderQty=(volume/5)
            )
            order1 = SpotOrder.objects.create(
                order_id=market_order1["orderId"],
                spot_signal=signal,
                symbol_name=symbol,
                price=price,
                volume=volume/5,
                side="BUY",
                priority=1,
                type="MARKET"
            )

            # ORDER 2 -  LIMIT order 
            mid_price = (entry_price.max_price + entry_price.min_price) / 2
            limit_order2 = client.order_limit_buy(
                symbol=symbol,
                quantity=math.floor((2*volume/5)/price),
                price=mid_price,
                timeInForce="GTC"
            )
            order2 = SpotOrder.objects.create(
                order_id=limit_order2["orderId"],
                spot_signal=signal,
                symbol_name=symbol,
                price=mid_price,
                volume=(2*volume/5),
                side="BUY",
                priority=2,
                type="LIMIT"
            )

            # ORDER 3 -  LIMIT order 
            limit_order3 = client.order_limit_buy(
                symbol=symbol,
                quantity=math.floor((2*volume/5)/price),
                price=entry_price.min_price,
                timeInForce="GTC"
            )
            order3 = SpotOrder.objects.create(
                order_id=limit_order3["orderId"],
                spot_signal=signal,
                symbol_name=symbol,
                price=entry_price.min_price,
                volume=(2*volume/5),
                side="BUY",
                priority=3,
                type="LIMIT"
            )
            print(market_order1, limit_order2, limit_order3)


            # create spot controller
            spot_controller = SpotControler.objects.create(spot_signal=signal)
            spot_controller.first_orders.add(order1, order2, order3)

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


