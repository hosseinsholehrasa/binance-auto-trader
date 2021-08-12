##################################
# import os
# # for combining django and telegram
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "traderbot.settings")
# from django.core.wsgi import get_wsgi_application
# application = get_wsgi_application()
############################# CELERY CONFIGURATOIN
# from celery import Celery
# REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
# REDIS_PORT = os.environ.get('REDIS_PORT', '6379')
# BROKER_URL = 'redis://' + REDIS_HOST + ':' + REDIS_PORT + '/0'
# app = Celery('binanceapi', broker=BROKER_URL, backend=BROKER_URL)
# app.conf.update(
#     task_serializer='json',
#     accept_content=['json'],
#     result_serializer='json',
#     timezone='Asia/Tehran',
#     enable_utc=True,
# )
#########################################

import os
import random
import math
import requests
import time
from signals.models import EntryPrice, SpotControler, SpotSignal, SpotOrder
from users.models import TelegramUser, BinanceUser
from binance import Client
from binance.exceptions import BinanceRequestException, BinanceAPIException, BinanceOrderException, \
    BinanceOrderMinAmountException, BinanceOrderMinPriceException, BinanceOrderMinTotalException, \
    BinanceOrderUnknownSymbolException, BinanceOrderInactiveSymbolException





# from django.conf import settings
from traderbot.celery import app


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

stp1_spot = 50/100
stp2_spot = 30/100
stp3_spot = 20/100
stp4_spot = 40/100
stp5_spot = 40/100
stp6_spot = 20/100
slp_pr_ordr = 1.5
min_signal_price = 110 # dollor

# main
def live_price(symb):
    client = Client(apikey, secretkey)
    if symb.upper() in intialize_symbol_name():
        price_dic = client.get_symbol_ticker(symbol=symb)
        return float(price_dic['price'])
    else:
        return "wrong symbol name"

def show_user_balance(apikey, secretkey, symbol, type="spot"):
    client = Client(apikey, secretkey)
    if type == 'spot':
        balance = client.get_asset_balance(symbol)
        return balance
    return None

def volume_checker(volume, symbol):
    client = Client(apikey, secretkey)
    info = client.get_symbol_info(symbol)
    balance = client.get_asset_balance(info['quoteAsset'])
    if float(balance['free']) < volume:
        return False
    usd_volume = volume
    if not info['quoteAsset'] in ["USDT", "BUSD", "USDC"]:
        price = live_price(f"{info['quoteAsset']}USDT")
        usd_volume = price * volume
    if usd_volume < min_signal_price:
        return False
    return True

def round_decimals_down(number:float, decimals:int=6):
    """
    Returns a value rounded down to a specific number of decimal places.
    """
    if decimals == 0:
        return math.floor(number)

    factor = 10 ** decimals
    return math.floor(number * factor) / factor


def volume_calculator(volume, commission=0.001):
    # precision = 10 - len(str(int(tick_size * (10 ** 10)))) + 1
    precision = 6
    amount = round_decimals_down(volume - volume * commission , 6)
    amount_str = '{:0.0{}f}'.format(amount, precision)
    return amount_str


def price_calculator(price, tick_size):
    # calculate the precision 
    precision = 10 - len(str(int(tick_size * (10 ** 10)))) + 1
    amount = round_decimals_down(price, precision)
    amount_str = '{:0.0{}f}'.format(amount, precision)
    return amount

def price_filter_check(symbol, amount):
    client = Client(apikey, secretkey)
    info = client.get_symbol_info(symbol)
    price = live_price(symbol)
    for filter in info["filters"]:
        if filter['filterType'] == "PERCENT_PRICE":
            if not price * float(filter['multiplierDown'])  <= amount <= price * float(filter['multiplierUp']):
                return False
        if filter['filterType'] == "PRICE_FILTER":
            if not float(filter['minPrice']) <= amount <= float(filter['maxPrice']):
                return False
    return True

# def volume_filter_check(client, symbol, amount):
#     info = client.get_symbol_info(symbol)
#     for filter in info["filters"]:
#         if filter['filterType'] == "LOT_SIZE":
#             if not round_decimals_down(stp1_spot * volume / entry_price.max_price)price * filter['multiplierDown']  <= amount <= price * filter['multiplierUp']:
#                 return False
#     return True


def get_oco_order(client, order_list_id):
    timestamp = client.get_server_time()["serverTime"]
    params = {
        "timestamp": timestamp,
        "orderListId": order_list_id
    }
    return client._get("orderList", True , version='v3', data=params)


def create_3_oco_orders(apikey, secretkey, spot_controller_id):
    pass

def cancel_oco_orders(client, *args):
    for order in args:
        order_response = get_oco_order(client, order.order_id)
        if not order_response['listOrderStatus'] == "ALL_DONE":
            client.cancel_order(symbol=order.symbol_name, orderId=order_response["orders"][0]["orderId"])
            order.status = client.ORDER_STATUS_CANCELED
            order.save()


# in OCO sell price is tp and limit and stop is stop loss
# limit maker hamoon tp 
@app.task
def spot_controller_checker(apikey, secretkey, spot_controller_id, first_stage=True, second_stage=False):
    print(f"first stage: {first_stage},second stage: {second_stage}")
    # INITIALIZATION
    try:
        client = Client(apikey, secretkey)
        spot_controller = SpotControler.objects.get(id=spot_controller_id)
        spot_signal = spot_controller.spot_signal
        # price = live_price(spot_controller.spot_signal.symbol_name)
        symbol = spot_controller.spot_signal.symbol_name
        tp1, tp2 , tp3 = spot_controller.spot_signal.take_profits.all().order_by("level")
        sl = spot_controller.spot_signal.stop_loss
        entry_price =  spot_controller.spot_signal.entry_prices.all()[0]
        tick_size = 0.1
        for filter in client.get_symbol_info(symbol)["filters"]:
            if filter['filterType'] == "PRICE_FILTER":
                tick_size = float(filter['tickSize'])

        mid_price = (entry_price.max_price + entry_price.min_price) / 2
    except Exception as e:
        print(e.message)
        return 0

    ###################### SECOND STAGE #####################  
    if second_stage:
        try:
            order1, order2, order3 = spot_controller.first_orders.all().order_by("priority")
            order4, order5, order6 = spot_controller.second_orders.all().order_by("priority")
            print(f"order4 second stage next level: {order4.isin_next_level},status: {order4.status}")
            print(f"order5 second stage next level: {order5.isin_next_level},status: {order5.status}")
        except Exception as e:
            print(e.message)

        # mesle payiini faghat order haye oonvaro bayad cancell kone 
        if not order4.isin_next_level:
            if order4.status == client.ORDER_STATUS_FILLED:
                order4.isin_next_level = True
                order4.save()
                first_stage = False

                # check limit orders that not filled to cancel it
                # cancel order 2 va 3
                if not order2.status == client.ORDER_STATUS_FILLED:
                    try:
                        client.cancel_order(symbol=symbol, orderId=order2.id)
                        order2.status = client.ORDER_STATUS_CANCELED
                        order2.save()
                    except binance_exceptions as e:
                        print(e)
                        print(repr(e))
                        print(e.message)

                if not order3.status == client.ORDER_STATUS_FILLED:
                    try:
                        client.cancel_order(symbol=symbol, orderId=order3.id)
                        order3.status = client.ORDER_STATUS_CANCELED
                        order3.save()
                    except binance_exceptions as e:
                        print(e)
                        print(repr(e))
                        print(e.message)

                # cancel oco orders
                cancel_oco_orders(client, order5, order6)
                # remove oco orders
                spot_controller.second_orders.remove(order5, order6)

                # darsad kharid ghablan rooye hajm anjam shode
                order5_volume = order5.volume
                order6_volume = order6.volume

                try:
                    # order5 - order OCOs changes
                    OCO_order5 = client.order_oco_sell(
                        symbol=symbol,
                        quantity=round_decimals_down(order5_volume),
                        price=price_calculator(tp2.price, tick_size),
                        stopPrice=price_calculator(((1/100*mid_price) + mid_price), tick_size),
                        stopLimitPrice=price_calculator(mid_price, tick_size),
                        stopLimitTimeInForce="GTC"
                        )
                    order5 = SpotOrder.objects.create(
                        order_id=OCO_order5["orderListId"],
                        spot_signal=spot_signal,
                        symbol_name=symbol,
                        price=price_calculator(tp2.price, tick_size),
                        take_profit=price_calculator(tp2.price, tick_size),
                        stop_loss=price_calculator(mid_price, tick_size),
                        volume=round_decimals_down(order5_volume),
                        side="SELL",
                        priority=2,
                        type="OCO"
                    )
                except binance_exceptions as e:
                    print(e)
                    print(repr(e))
                    print(e.message)

                time.sleep(slp_pr_ordr)
                try:
                    # order6 - order OCOs updates
                    OCO_order6 = client.order_oco_sell(
                        symbol=symbol,
                        quantity=round_decimals_down(order6_volume),
                        price=price_calculator(tp3.price, tick_size),
                        stopPrice=price_calculator(((1/100*mid_price) + mid_price), tick_size),
                        stopLimitPrice=price_calculator(mid_price, tick_size),
                        stopLimitTimeInForce="GTC"
                    )
                    order6 = SpotOrder.objects.create(
                        order_id=OCO_order6["orderListId"],
                        spot_signal=spot_signal,
                        symbol_name=symbol,
                        price=price_calculator(tp3.price, tick_size),
                        take_profit=price_calculator(tp3.price, tick_size),
                        stop_loss=price_calculator(mid_price, tick_size),
                        volume=round_decimals_down(order6_volume),
                        side="SELL",
                        priority=3,
                        type="OCO"
                    )
                except binance_exceptions as e:
                    print(e)
                    print(repr(e))
                    print(e.message)

                spot_controller.second_orders.add(order5, order6)

            else:
                try:
                    # get order status
                    order4_response = get_oco_order(client, order4.order_id)
                    if order4_response['listOrderStatus'] == "ALL_DONE":
                        order4_1 = client.get_order(symbol=order4.symbol_name,
                                                    orderId=order4_response["orders"][0]["orderId"])
                        # we reached first take profit
                        if order4_1["status"] == client.ORDER_STATUS_FILLED and \
                                order4_1["type"] == client.ORDER_TYPE_LIMIT_MAKER:
                            order4.status = client.ORDER_STATUS_FILLED
                            order4.save()
                        # stop loss triglled
                        else:
                            order4.status = client.ORDER_STATUS_CANCELED
                            order4.price = sl
                            order4.save()
                            order5.status = client.ORDER_STATUS_CANCELED
                            order5.price = sl
                            order5.save()
                            order6.status = client.ORDER_STATUS_CANCELED
                            order6.price = sl
                            order6.save()
                            return 0
                except binance_exceptions as e:
                    print(e)
                    print(repr(e))
                    print(e.message)

        elif order5.isin_next_level == False:
            if order5.status == client.ORDER_STATUS_FILLED:
                order5.isin_next_level = True
                order5.save()

                # cancel oco orders 
                cancel_oco_orders(client, order6)
                # remove oco orders
                spot_controller.second_orders.remove(order6)

                order6_volume = order6.volume

                try:
                    # order6 - order OCOs changes
                    OCO_order6 = client.order_oco_sell(
                        symbol=symbol,
                        quantity=round_decimals_down(order6_volume),
                        price=price_calculator(tp3.price, tick_size),
                        stopPrice=price_calculator(((1/100*tp1.price) + tp1.price), tick_size),
                        stopLimitPrice=price_calculator(tp1.price, tick_size),
                        stopLimitTimeInForce="GTC"
                    )
                    order6 = SpotOrder.objects.create(
                        order_id=OCO_order6["orderListId"],
                        spot_signal=spot_signal,
                        symbol_name=symbol,
                        price=price_calculator(tp3.price, tick_size),
                        take_profit=price_calculator(tp3.price, tick_size),
                        stop_loss=price_calculator(tp1.price, tick_size),
                        volume=round_decimals_down(order6_volume),
                        side="SELL",
                        priority=3,
                        type="OCO"
                    )
                except binance_exceptions as e:
                    print(e)
                    print(repr(e))
                    print(e.message)

                spot_controller.second_orders.add(order6)

            else:
                try:
                    # get order status
                    order5_response = get_oco_order(client, order5.order_id)
                    if order5_response['listOrderStatus'] == "ALL_DONE":
                        order5_1 = client.get_order(symbol=symbol, orderId=order5_response["orders"][0]["orderId"])
                        # we get first take profit
                        if order5_1["status"] == client.ORDER_STATUS_FILLED and order5_1["type"] == client.ORDER_TYPE_LIMIT_MAKER:
                            order5.status = client.ORDER_STATUS_FILLED
                            order5.save()
                            # read bellow description
                            order6.status = client.ORDER_STATUS_FILLED
                            order6.save()
                        # stop loss triglled
                        else:
                            order5.status = client.ORDER_STATUS_CANCELED
                            order5.price = mid_price
                            order5.save()
                            order6.status = client.ORDER_STATUS_CANCELED
                            order6.price = mid_price
                            order6.save()
                            return 0
                except binance_exceptions as e:
                    print(e)
                    print(repr(e))
                    print(e.message)

        # TODO we can track the order6 but not neccessery for now just get it filled
        else:
            return 0



    ###################### FIRST STAGE #####################
    if first_stage:
        try:
            order1, order2, order3 = spot_controller.first_orders.all().order_by("priority")
        except:
            pass

        print(f"order1 first stage next level: {order1.isin_next_level},status: {order1.status}")
        print(f"order2 first stage next level: {order2.isin_next_level},status: {order2.status}")
        print(f"order3 first stage next level: {order3.isin_next_level},status: {order3.status}")

        # OCO1 gozashte shode? are pas boro baadi age na bebin filled shode ya na? age na check kon status age are pas bezar
        if not order1.isin_next_level:
            if order1.status == client.ORDER_STATUS_FILLED:
                try:
                    # order4 - order OCO for order 1
                    OCO_order4 = client.order_oco_sell(
                        symbol=symbol,
                        quantity=round_decimals_down(stp4_spot * order1.volume),
                        price=price_calculator(tp1.price, tick_size),
                        stopPrice=price_calculator(((1/100*sl) + sl), tick_size),
                        stopLimitPrice=price_calculator(sl, tick_size),
                        stopLimitTimeInForce="GTC"
                    )
                    order4 = SpotOrder.objects.create(
                        order_id=OCO_order4["orderListId"],
                        spot_signal=spot_signal,
                        symbol_name=symbol,
                        price=price_calculator(tp1.price, tick_size),
                        take_profit=price_calculator(tp1.price, tick_size),
                        stop_loss=price_calculator(sl, tick_size),
                        volume=round_decimals_down(stp4_spot * order1.volume),
                        side="SELL",
                        priority=1,
                        type="OCO"
                    )
                    print(OCO_order4)
                except binance_exceptions as e:
                    print(e)
                    print(repr(e))
                    print(e.message)

                time.sleep(slp_pr_ordr)
                try:
                    # order5 - order OCO for order 1
                    OCO_order5 = client.order_oco_sell(
                        symbol=symbol,
                        quantity=round_decimals_down(stp5_spot * order1.volume),
                        price=price_calculator(tp2.price, tick_size),
                        stopPrice=price_calculator(((1/100*sl) + sl), tick_size),
                        stopLimitPrice=price_calculator(sl, tick_size),
                        stopLimitTimeInForce="GTC"
                        )
                    order5 = SpotOrder.objects.create(
                        order_id=OCO_order5["orderListId"],
                        spot_signal=spot_signal,
                        symbol_name=symbol,
                        price=price_calculator(tp2.price, tick_size),
                        take_profit=price_calculator(tp2.price, tick_size),
                        stop_loss=price_calculator(sl, tick_size),
                        volume=round_decimals_down(stp5_spot * order1.volume),
                        side="SELL",
                        priority=2,
                        type="OCO"
                    )

                    print(OCO_order5)
                    print(price_calculator(tp3.price, tick_size))
                    print(order1.volume)
                    print(round_decimals_down(stp6_spot * order1.volume))
                except binance_exceptions as e:
                    print(e)
                    print(repr(e))
                    print(e.message)

                time.sleep(slp_pr_ordr)
                try:
                    # order6 - order OCO for order 1
                    OCO_order6 = client.order_oco_sell(
                        symbol=symbol,
                        quantity=round_decimals_down(stp6_spot * order1.volume),
                        price=price_calculator(tp3.price, tick_size),
                        stopPrice=price_calculator(((1/100*sl) + sl), tick_size),
                        stopLimitPrice=price_calculator(sl, tick_size),
                        stopLimitTimeInForce="GTC"
                    )
                    order6 = SpotOrder.objects.create(
                        order_id=OCO_order6["orderListId"],
                        spot_signal=spot_signal,
                        symbol_name=symbol,
                        price=price_calculator(tp3.price, tick_size),
                        take_profit=price_calculator(tp3.price, tick_size),
                        stop_loss=price_calculator(sl, tick_size),
                        volume=round_decimals_down(stp6_spot * order1.volume),
                        side="SELL",
                        priority=3,
                        type="OCO"
                    )
                    print(OCO_order6)

                except binance_exceptions as e:
                    print(e)
                    print(repr(e))
                    print(e.message)

                spot_controller.second_orders.add(order4, order5, order6)
                # time to check OCOs
                second_stage = True
                order1.isin_next_level = True
                order1.save()

            else:
                # get order status
                try:
                    order = client.get_order(symbol=symbol, orderId=order1.order_id)
                    if order["status"] == client.ORDER_STATUS_FILLED:
                        order1.status = client.ORDER_STATUS_FILLED
                        print("order1 status filled")
                        order1.save()

                except binance_exceptions as e:
                    print(e)
                    print(repr(e))
                    print(e.message)

        elif not order2.isin_next_level:
            if order2.status == client.ORDER_STATUS_FILLED:
                try:
                    order4, order5, order6 = spot_controller.second_orders.all().order_by("priority")
                except:
                    pass

                # cancel 3 oco order
                cancel_oco_orders(client, order4, order5, order6)
                # remove last 3 orders
                spot_controller.second_orders.remove(order4, order5, order6)
                try:
                    # order4 - order OCO for order 2
                    OCO_order4 = client.order_oco_sell(
                        symbol=symbol,
                        quantity=round_decimals_down(stp4_spot * (order1.volume + order2.volume)),
                        price=price_calculator(tp1.price, tick_size),
                        stopPrice=price_calculator(((1/100*sl) + sl), tick_size),
                        stopLimitPrice=price_calculator(sl, tick_size),
                        stopLimitTimeInForce="GTC"
                    )
                    order4 = SpotOrder.objects.create(
                        order_id=OCO_order4["orderListId"],
                        spot_signal=spot_signal,
                        symbol_name=symbol,
                        price=price_calculator(tp1.price, tick_size),
                        take_profit=price_calculator(tp1.price, tick_size),
                        stop_loss=price_calculator(sl, tick_size),
                        volume=round_decimals_down(stp4_spot * (order1.volume + order2.volume)),
                        side="SELL",
                        priority=1,
                        type="OCO"
                    )
                except binance_exceptions as e:
                    print(e)
                    print(repr(e))
                    print(e.message)

                time.sleep(slp_pr_ordr)
                try:
                    # order5 - order OCO for order 2
                    OCO_order5 = client.order_oco_sell(
                        symbol=symbol,
                        quantity=round_decimals_down(stp5_spot * (order1.volume + order2.volume)),
                        price=price_calculator(tp2.price, tick_size),
                        stopPrice=price_calculator(((1/100*sl) + sl), tick_size),
                        stopLimitPrice=price_calculator(sl, tick_size),
                        stopLimitTimeInForce="GTC"
                        )
                    order5 = SpotOrder.objects.create(
                        order_id=OCO_order5["orderListId"],
                        spot_signal=spot_signal,
                        symbol_name=symbol,
                        price=price_calculator(tp2.price, tick_size),
                        take_profit=price_calculator(tp2.price, tick_size),
                        stop_loss=price_calculator(sl, tick_size),
                        volume=round_decimals_down(stp5_spot * (order1.volume + order2.volume)),
                        side="SELL",
                        priority=2,
                        type="OCO"
                    )
                except binance_exceptions as e:
                    print(e)
                    print(repr(e))
                    print(e.message)

                time.sleep(slp_pr_ordr)
                try:
                    # order6 - order OCO for order 2
                    OCO_order6 = client.order_oco_sell(
                        symbol=symbol,
                        quantity=round_decimals_down(stp6_spot * (order1.volume + order2.volume)),
                        price=price_calculator(tp3.price, tick_size),
                        stopPrice=price_calculator(((1/100*sl) + sl), tick_size),
                        stopLimitPrice=price_calculator(sl, tick_size),
                        stopLimitTimeInForce="GTC"
                    )
                    order6 = SpotOrder.objects.create(
                        order_id=OCO_order6["orderListId"],
                        spot_signal=spot_signal,
                        symbol_name=symbol,
                        price=price_calculator(tp3.price, tick_size),
                        take_profit=price_calculator(tp3.price, tick_size),
                        stop_loss=price_calculator(sl, tick_size),
                        volume=round_decimals_down(stp6_spot * (order1.volume + order2.volume)),
                        side="SELL",
                        priority=3,
                        type="OCO"
                    )

                except binance_exceptions as e:
                    print(e)
                    print(repr(e))
                    print(e.message)

                spot_controller.second_orders.add(order4, order5, order6)
                order2.isin_next_level = True
                order2.save()
            else:
                try:
                    # get order status
                    order = client.get_order(symbol=symbol, orderId=order2.order_id)
                    if order["status"] == client.ORDER_STATUS_FILLED:
                        order2.status = client.ORDER_STATUS_FILLED
                        order2.save()
                except binance_exceptions as e:
                    print(e)
                    print(repr(e))
                    print(e.message)

        elif not order3.isin_next_level:
            if order3.status == client.ORDER_STATUS_FILLED:
                try:
                    order4, order5, order6 = spot_controller.second_orders.all().order_by("priority")
                except:
                    pass

                # cancel 3 oco order
                cancel_oco_orders(client, order4, order5, order6)
                # remove last 3 orders
                spot_controller.second_orders.remove(order4, order5, order6)
                try:
                    # order4 - order OCO for order 3
                    OCO_order4 = client.order_oco_sell(
                        symbol=symbol,
                        quantity=round_decimals_down(stp4_spot * (order1.volume + order2.volume + order3.volume)),
                        price=price_calculator(tp1.price, tick_size),
                        stopPrice=price_calculator(((1/100*sl) + sl), tick_size),
                        stopLimitPrice=price_calculator(sl, tick_size),
                        stopLimitTimeInForce="GTC"
                    )
                    order4 = SpotOrder.objects.create(
                        order_id=OCO_order4["orderListId"],
                        spot_signal=spot_signal,
                        symbol_name=symbol,
                        price=price_calculator(tp1.price, tick_size),
                        take_profit=price_calculator(tp1.price, tick_size),
                        stop_loss=price_calculator(sl, tick_size),
                        volume=round_decimals_down(stp4_spot * (order1.volume + order2.volume + order3.volume)),
                        side="SELL",
                        priority=1,
                        type="OCO"
                    )
                except binance_exceptions as e:
                    print(e)
                    print(repr(e))
                    print(e.message)

                time.sleep(slp_pr_ordr)
                try:
                    # order5 - order OCO for order 3
                    OCO_order5 = client.order_oco_sell(
                        symbol=symbol,
                        quantity=round_decimals_down(stp5_spot * (order1.volume + order2.volume + order3.volume)),
                        price=price_calculator(tp2.price, tick_size),
                        stopPrice=price_calculator(((1/100*sl) + sl), tick_size),
                        stopLimitPrice=price_calculator(sl, tick_size),
                        stopLimitTimeInForce="GTC"
                        )
                    order5 = SpotOrder.objects.create(
                        order_id=OCO_order5["orderListId"],
                        spot_signal=spot_signal,
                        symbol_name=symbol,
                        price=price_calculator(tp2.price, tick_size),
                        take_profit=price_calculator(tp2.price, tick_size),
                        stop_loss=price_calculator(sl, tick_size),
                        volume=round_decimals_down(stp5_spot * (order1.volume + order2.volume + order3.volume)),
                        side="SELL",
                        priority=2,
                        type="OCO"
                    )
                except binance_exceptions as e:
                    print(e)
                    print(repr(e))
                    print(e.message)

                time.sleep(slp_pr_ordr)
                try:
                    # order6 - order OCO for order 3
                    OCO_order6 = client.order_oco_sell(
                        symbol=symbol,
                        quantity=round_decimals_down(stp6_spot * (order1.volume + order2.volume + order3.volume)),
                        price=price_calculator(tp3.price, tick_size),
                        stopPrice=price_calculator(((1/100*sl) + sl), tick_size),
                        stopLimitPrice=price_calculator(sl, tick_size),
                        stopLimitTimeInForce="GTC"
                    )
                    order6 = SpotOrder.objects.create(
                        order_id=OCO_order6["orderListId"],
                        spot_signal=spot_signal,
                        symbol_name=symbol,
                        price=price_calculator(tp3.price, tick_size),
                        take_profit=price_calculator(tp3.price, tick_size),
                        stop_loss=price_calculator(sl, tick_size),
                        volume=round_decimals_down(stp6_spot * (order1.volume + order2.volume + order3.volume)),
                        side="SELL",
                        priority=3,
                        type="OCO"
                    )
                except binance_exceptions as e:
                    print(e)
                    print(repr(e))
                    print(e.message)

                spot_controller.second_orders.add(order4, order5, order6)

                first_stage = False
                second_stage = True
                order3.isin_next_level = True
                order3.save()
            else:
                try:
                    # get order status
                    order = client.get_order(symbol=symbol, orderId=order3.order_id)
                    if order["status"] == client.ORDER_STATUS_FILLED:
                        order3.status = client.ORDER_STATUS_FILLED
                        order3.save()
                except binance_exceptions as e:
                    print(e)
                    print(repr(e))
                    print(e.message)

    spot_controller_checker.apply_async(
        (apikey, secretkey, spot_controller.id, first_stage, second_stage),
        countdown=random.uniform(10, 15),
        )

@app.task
def spot_strategy(apikey, secretkey, signal_id):
    client = Client(apikey, secretkey)
    # initalized
    try:
        signal = SpotSignal.objects.get(id=signal_id)
        symbol = signal.symbol_name
        entry_price = signal.entry_prices.all()[0]
        price = live_price(symbol)
        volume = signal.volume
        tick_size = 0.1
        for filter in client.get_symbol_info(symbol)["filters"]:
            if filter['filterType'] == "PRICE_FILTER":
                tick_size = float(filter['tickSize'])

        mid_price = (entry_price.max_price + entry_price.min_price) / 2
        binance_exceptions = (BinanceRequestException, BinanceAPIException, BinanceOrderException,
                              BinanceOrderMinAmountException, BinanceOrderMinPriceException, BinanceOrderMinTotalException,
                              BinanceOrderUnknownSymbolException, BinanceOrderInactiveSymbolException)
    except Exception as e:
        print(e.message)
        return 0

    if entry_price.max_price < price:
        try:
            # ORDER 1 -  LIMIT order            
            limit_order1 = client.order_limit_buy(
                symbol=symbol,
                quantity=round_decimals_down(stp1_spot * volume / entry_price.max_price),
                price=price_calculator(entry_price.max_price, tick_size),
                timeInForce="GTC"
                )
            print("limit order1 halat aval:", limit_order1)
            order1 = SpotOrder.objects.create(
                order_id=limit_order1["orderId"],
                spot_signal=signal,
                symbol_name=symbol,
                price=price_calculator(entry_price.max_price, tick_size),
                volume=volume_calculator(float(limit_order1["origQty"])),
                side="BUY",
                priority=1,
                type="LIMIT"
            )
        except binance_exceptions as e:
            print(e)
            print(repr(e))
            print(e.message)

        time.sleep(slp_pr_ordr)
        try:
            # ORDER 2 -  LIMIT order
            limit_order2 = client.order_limit_buy(
                symbol=symbol,
                quantity=round_decimals_down(stp2_spot * volume / mid_price),
                price=price_calculator(mid_price, tick_size),
                timeInForce="GTC"
            )
            print("limit order2 halat aval:", limit_order2)
            order2 = SpotOrder.objects.create(
                order_id=limit_order2["orderId"],
                spot_signal=signal,
                symbol_name=symbol,
                price=price_calculator(mid_price, tick_size),
                volume=volume_calculator(float(limit_order2["origQty"])),
                side="BUY",
                priority=2,
                type="LIMIT"
            )
        except binance_exceptions as e:
            print(e)
            print(repr(e))
            print(e.message)

        time.sleep(slp_pr_ordr)
        try:
            # ORDER 3 -  LIMIT order 
            limit_order3 = client.order_limit_buy(
                symbol=symbol,
                quantity=round_decimals_down(stp3_spot * volume / entry_price.min_price),
                price=price_calculator(entry_price.min_price, tick_size),
                timeInForce="GTC"
            )
            order3 = SpotOrder.objects.create(
                order_id=limit_order3["orderId"],
                spot_signal=signal,
                symbol_name=symbol,
                price=price_calculator(entry_price.min_price, tick_size),
                volume=volume_calculator(float(limit_order3["origQty"])),
                side="BUY",
                priority=3,
                type="LIMIT"
            )
            print("limit order3 halat aval:", limit_order3)
        except binance_exceptions as e:
            print(e)
            print(repr(e))
            print(e.message)

        # create spot controller
        spot_controller = SpotControler.objects.create(spot_signal=signal)
        spot_controller.first_orders.add(order1, order2, order3)
        spot_controller_checker.apply_async(
            (apikey, secretkey, spot_controller.id),
            countdown=random.uniform(10, 15),
        )

    else:
        try:
            # jabejayii noghte hadaksar
            entry_price.max_price = price
            entry_price.save()
            # ORDER 1 -  MARKET order    
            market_order1 = client.order_market_buy(
                symbol=symbol,
                quoteOrderQty=(stp1_spot * volume)
            )
            print("market order1 halat dovom", market_order1)
            order1 = SpotOrder.objects.create(
                order_id=market_order1["orderId"],
                spot_signal=signal,
                symbol_name=symbol,
                price=price_calculator(price, tick_size),
                volume=volume_calculator(float(market_order1["origQty"])),
                side="BUY",
                priority=1,
                type="MARKET"
            )
        except binance_exceptions as e:
            print(e)
            print(repr(e))
            print(e.message)

        time.sleep(slp_pr_ordr)
        try:
            # ORDER 2 -  LIMIT order 
            mid_price = (entry_price.max_price + entry_price.min_price) / 2
            limit_order2 = client.order_limit_buy(
                symbol=symbol,
                quantity=round_decimals_down(stp2_spot * volume / mid_price),
                price=price_calculator(mid_price, tick_size),
                timeInForce="GTC"
            )
            print("limit order halat dovom", limit_order2)
            order2 = SpotOrder.objects.create(
                order_id=limit_order2["orderId"],
                spot_signal=signal,
                symbol_name=symbol,
                price=price_calculator(mid_price, tick_size),
                volume=volume_calculator(float(limit_order2["origQty"])),
                side="BUY",
                priority=2,
                type="LIMIT"
            )
        except binance_exceptions as e:
            print(e)
            print(repr(e))
            print(e.message)

        time.sleep(slp_pr_ordr)
        try:
            # ORDER 3 -  LIMIT order
            limit_order3 = client.order_limit_buy(
                symbol=symbol,
                quantity=round_decimals_down(stp3_spot * volume / entry_price.min_price),
                price=price_calculator(entry_price.min_price, tick_size),
                timeInForce="GTC"
            )
            print("limit order3 halat dovom", limit_order3)
            order3 = SpotOrder.objects.create(
                order_id=limit_order3["orderId"],
                spot_signal=signal,
                symbol_name=symbol,
                price=price_calculator(entry_price.min_price, tick_size),
                volume=volume_calculator(float(limit_order3["origQty"])),
                side="BUY",
                priority=3,
                type="LIMIT"
            )
        except binance_exceptions as e:
            print(e)
            print(repr(e))
            print(e.message)

        # create spot controller
        spot_controller = SpotControler.objects.create(spot_signal=signal)
        spot_controller.first_orders.add(order1, order2, order3)

        spot_controller_checker.apply_async(
            (apikey, secretkey, spot_controller.id),
            countdown=random.uniform(10, 15),
        )


# spot_strategy(apikey, secretkey, "BTCUSDT", 41000, 100)


