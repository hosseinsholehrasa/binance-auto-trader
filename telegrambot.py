####################################################################################
import os

# for combining django and telegram
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "traderbot.settings")
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
#####################################################################################
import telebot
import time
import random
from traderbot import settings
from signals.models import FutureSignal, SpotSignal, EntryPrice, TakeProfit
from users.models import BinanceUser, TelegramUser
from signals.tasks import intialize_symbol_name, live_price, spot_strategy, price_filter_check, \
    volume_checker, show_user_balance

# TODO transaction request status
# TODO ramz kardan key ha


# INITIALIZATION
apikey = settings.TELEGRAM_KEY
bot = telebot.TeleBot(apikey)
levrage_numbers = [i for i in range(1, 126)]
symboles = intialize_symbol_name()
moneybag_emojy = u'\U0001F4B0'
key_emojy = u'\U0001F511'

""" for convert string to int or float and check its str or not """


def int_or_float(str):
    if str.isdigit():
        return True, int(str)
    else:
        try:
            return True, float(str)
        except:
            return False, str


def not_cancelled(message):
    print(message.text)
    if message.text == "cancel":
        return False
    return True


##########################################################################
# start button
@bot.message_handler(commands=['start'])
def start(message):
    telegram_user, is_created = TelegramUser.objects.get_or_create(id=message.chat.id)
    BinanceUser.objects.get_or_create(telegram_user=telegram_user)
    text = """خوش آمدید
"""

    # برای ثبت سیگنال اسپات از دستور /newsignalspot
    # ثبت api key و secret key بایننس /savekeys
    # نمایش کلید ذخیره کرده بایننس /showkeys
    # نمایش بالانس حساب شما /showbalance
    # )
    keyboard = telebot.types.ReplyKeyboardMarkup(True)
    keyboard.row("new signal spot")
    keyboard.row(f"show balance {moneybag_emojy}", f"save binance keys {key_emojy}", f"show binance keys {key_emojy}")

    bot.send_message(message.chat.id, text, reply_markup=keyboard)


# show balance
@bot.message_handler(regexp="show balance .*")
def show_asset_balance(message):
    sent = bot.reply_to(message, "Enter symbol name\n for example USDT")
    bot.register_next_step_handler(sent, symbol_asset_balance_reciever)


def symbol_asset_balance_reciever(message):
    user = BinanceUser.objects.get(telegram_user=message.chat.id)
    balance = show_user_balance(user.api_key, user.secret_key, message.text)
    if not balance:
        sent = bot.send_message(message.chat.id, "enter correct symbol name")
        bot.register_next_step_handler(sent, symbol_asset_balance_reciever)
    else:
        sent = bot.send_message(
            message.chat.id,
            f"{balance['asset']}: \nfree:{balance['free']}\nlocked:{balance['locked']}"
        )


#  save binance api keys button
@bot.message_handler(commands=['savekeys'])
def save_keys(message):
    sent = bot.reply_to(message, "Enter your binance api_key")
    bot.register_next_step_handler(sent, save_api_key)


def save_api_key(message):
    if len(message.text) == 64:
        user = BinanceUser.objects.get(telegram_user=message.chat.id)
        user.api_key = message.text
        user.save()
        sent = bot.send_message(message.chat.id, "Enter your binance secret key")
        bot.register_next_step_handler(sent, save_secret_key)

    else:
        bot.send_message(message.chat.id, 'Please enter a correct keys')
        bot.register_next_step_handler(message, save_api_key)

    bot.delete_message(message.chat.id, message.message_id)


def save_secret_key(message):
    if len(message.text) == 64:
        user = BinanceUser.objects.get(telegram_user=message.chat.id)
        user.secret_key = message.text
        user.save()
        bot.send_message(message.chat.id, 'DONE')
    else:
        bot.send_message(message.chat.id, 'Please enter a correct keys')
        bot.register_next_step_handler(message, save_secret_key)

    bot.delete_message(message.chat.id, message.message_id)


# show api keys
@bot.message_handler(commands=['showkeys'])
def show_keys(message):
    binance_user = BinanceUser.objects.get(telegram_user=message.chat.id)
    if binance_user.api_key and binance_user.secret_key:
        # censor the keys
        bot.send_message(
            message.chat.id,
            f"api_key: \n{binance_user.api_key[:10]}*****{binance_user.api_key[55:]} \
                \nsecret_key: \n{binance_user.secret_key[:10]}*****{binance_user.secret_key[55:]}")
    else:
        bot.send_message(message.chat.id, "you have to save keys first")


##########################################################################

# Balance button
@bot.message_handler(commands=['balance'])
def show_balance(message):
    pass


# live data button
@bot.message_handler(commands=['price'])
def show_live_price(message):
    pass


# show transaction status button
@bot.message_handler(commands=['price'])
def show_transaction_status(message):
    pass


##########################################################################
# NEW SIGNAL BUTTON
@bot.message_handler(commands=['newsignalF'])
def signal_receiver(message):
    sent = bot.reply_to(message, "Enter your symbol\nfor example (BTCUSDT) ")
    bot.register_next_step_handler(sent, symbol_receiver)


def symbol_receiver(message):
    signal_id = 0
    if message.text.upper() in symboles:
        with connector.cursor() as cursor:
            # get last signal id 
            last_id_query = f"SELECT id FROM signal_futures ORDER BY ID DESC LIMIT 1;"
            cursor.execute(last_id_query)
            last_id = cursor.fetchmany()
            signal_id = last_id[0][0] + 1

            sql = f"INSERT INTO signal_futures(tel_id, symbol_name) VALUES ({message.chat.id}, '{message.text.upper()}');"
            cursor.execute(sql)

        sent = bot.reply_to(
            message, f'Enter your entry price \nprice now is {live_price(message.text.upper())}')
        bot.register_next_step_handler(sent, entry_price_reciever, signal_id)
    else:
        sent = bot.send_message(message.chat.id, 'Incorrect')
        bot.register_next_step_handler(message, symbol_receiver)


def entry_price_reciever(message, signal_id):
    is_number, txt = int_or_float(message.text)
    if is_number:
        with connector.cursor() as cursor:
            query = f"UPDATE signal_futures SET entry_price='{txt}' WHERE (id={signal_id});"
            cursor.execute(query)

        sent = bot.reply_to(message, 'Enter your volume')
        bot.register_next_step_handler(sent, volume_reciever, signal_id)
    else:
        sent = bot.send_message(message.chat.id, 'please enter a number')
        bot.register_next_step_handler(message, entry_price_reciever, signal_id)


def volume_reciever(message, signal_id):
    is_number, txt = int_or_float(message.text)
    if is_number:
        with connector.cursor() as cursor:
            query = f"UPDATE signal_futures SET volume='{txt}' WHERE (id={signal_id});"
            cursor.execute(query)
        sent = bot.reply_to(message, 'Enter your 3 take profit price\n for example (1000 1500 1800)')
        bot.register_next_step_handler(sent, take_profit_reciever, signal_id)
    else:
        sent = bot.send_message(message.chat.id, 'please enter a number')
        bot.register_next_step_handler(message, volume_reciever, signal_id)


def take_profit_reciever(message, signal_id):
    tps = message.text.split()

    # check all of the three is integer
    if len(tps) == 3 and all(x.isdigit() for x in tps):
        tpsint = [int(x) for x in tps]
        sent = bot.reply_to(message, 'Enter your stop loss price')
        bot.register_next_step_handler(sent, stop_loss_reciever, signal_id)
    else:
        sent = bot.send_message(message.chat.id, 'please enter numbers')
        bot.register_next_step_handler(message, take_profit_reciever, signal_id)


def stop_loss_reciever(message, signal_id):
    is_number, txt = int_or_float(message.text)
    if message.text.isdigit():
        sent = bot.reply_to(message, 'Enter your levrage \n between 1-125')
        bot.register_next_step_handler(sent, levrage_reciever, signal_id)
    else:
        sent = bot.send_message(message.chat.id, 'please enter a number')
        bot.register_next_step_handler(message, stop_loss_reciever, signal_id)


def levrage_reciever(message, signal_id):
    is_number, txt = int_or_float(message.text)
    if message.text.isdigit() and txt in levrage_numbers:
        with connector.cursor() as cursor:
            query = f"UPDATE signal_futures SET levrage='{txt}' WHERE (id={signal_id});"
            cursor.execute(query)
        sent = bot.reply_to(message, 'Enter your position side (buy or sell)')
        bot.register_next_step_handler(sent, position_reciever, signal_id)
    else:
        sent = bot.send_message(message.chat.id, 'please enter a correct number  between 1-125')
        bot.register_next_step_handler(message, levrage_reciever, signal_id)


def position_reciever(message, signal_id):
    if message.text.lower() in ["buy", "sell"]:
        # if position side is buy then position is 1 and for sell is 0
        if message.text.lower() == "buy":
            position = 1
        else:
            position = 0

        with connector.cursor() as cursor:
            query = f"UPDATE signal_futures SET position='{position}' WHERE (id={signal_id});"
            cursor.execute(query)
        sent = bot.reply_to(message, 'your request is pending')
    else:
        sent = bot.send_message(message.chat.id, 'please enter buy or sell word')
        bot.register_next_step_handler(message, position_reciever, signal_id)


# TODO give volume by percent or dollor
# TODO add check that a user have all api
########################################################################### NEW SIGNAL SPOT

@bot.message_handler(commands=['newsignalspot'])
def spot_signal_receiver(message):
    sent = bot.reply_to(message, "Enter your symbol\nfor example (BTCUSDT) ")
    bot.register_next_step_handler(sent, spot_symbol_receiver)


def spot_symbol_receiver(message):
    if message.text.upper() in symboles:
        tel_user = TelegramUser.objects.get(id=message.chat.id)
        spot = SpotSignal.objects.create(telegram_user=tel_user, symbol_name=message.text.upper())

        sent = bot.reply_to(
            message, f'Enter your entry price zone \nfor example 38000-44000\
                 \nprice now is {live_price(message.text.upper())} \nyou have to wait ~20 second to validate your price numbers')
        bot.register_next_step_handler(sent, spot_entry_price_reciever, spot.id)
    else:
        sent = bot.send_message(message.chat.id, 'Incorrect')
        bot.register_next_step_handler(message, spot_symbol_receiver)


def spot_entry_price_reciever(message, signal_id):
    numbers = message.text.split("-")
    numbers_arr = []
    for number in numbers:
        is_number, txt = int_or_float(number)
        if is_number:
            numbers_arr.append(txt)
    is_two_number = len(numbers_arr) == 2
    if is_two_number:
        spot = SpotSignal.objects.get(id=signal_id)
        number1_ = price_filter_check(spot.symbol_name, numbers_arr[0])
        number2_ = price_filter_check(spot.symbol_name, numbers_arr[1])

        if number1_ and number2_:
            entry_price = EntryPrice.objects.create(min_price=numbers_arr[0], max_price=numbers_arr[1])
            spot.entry_prices.add(entry_price)
            sent = bot.reply_to(message, 'Enter your volume')
            bot.register_next_step_handler(sent, spot_volume_reciever, signal_id)
        else:
            sent = bot.send_message(message.chat.id, "your price numbers are not in range of this symbol price")
            bot.register_next_step_handler(message, spot_entry_price_reciever, signal_id)
    else:
        sent = bot.send_message(message.chat.id, 'please enter a number and check the correct format')
        bot.register_next_step_handler(message, spot_entry_price_reciever, signal_id)


def spot_volume_reciever(message, signal_id):
    is_number, txt = int_or_float(message.text)
    if is_number:
        spot = SpotSignal.objects.get(id=signal_id)
        volume_pass = volume_checker(txt, spot.symbol_name)
        if volume_pass:
            spot.volume = txt
            spot.save()
            # TODO will get numbers of take profits
            sent = bot.reply_to(message, 'Enter your take profit numbers \nfor now just accept 3')
            bot.register_next_step_handler(sent, spot_take_profit_number_reciever, signal_id)
        else:
            sent = bot.send_message(message.chat.id, 'you dont have enough money to start signal \nminimum need 120$')
            bot.register_next_step_handler(message, spot_volume_reciever, signal_id)
    else:
        sent = bot.send_message(message.chat.id, 'please enter a number')
        bot.register_next_step_handler(message, spot_volume_reciever, signal_id)


def spot_take_profit_number_reciever(message, signal_id):
    if message.text.isdigit():
        take_profit_number = 3
        sent = bot.send_message(message.chat.id, 'please enter your take profit price 1:\n'
                                                 'you have to wait ~20 second to validate your price numbers')
        bot.register_next_step_handler(sent, spot_take_profit_reciever, signal_id, take_profit_number)
    else:
        sent = bot.send_message(message.chat.id, 'please enter a number')
        bot.register_next_step_handler(message, spot_take_profit_number_reciever, signal_id)


def spot_take_profit_reciever(message, signal_id, take_profit_number, number_position=1):
    print(number_position)
    is_number, txt = int_or_float(message.text)
    if number_position < take_profit_number:
        if is_number:
            spot = SpotSignal.objects.get(id=signal_id)
            price_filter = price_filter_check(spot.symbol_name, txt)
            if price_filter:
                take_profit = TakeProfit.objects.create(price=txt, level=number_position)
                print(take_profit)
                spot.take_profits.add(take_profit)
                number_position += 1
                sent = bot.send_message(message.chat.id, f'please enter your take profit price {number_position}:\n'
                                                         f'you have to wait ~20 second to validate your price numbers')
                bot.register_next_step_handler(message, spot_take_profit_reciever, signal_id, take_profit_number,
                                               number_position)
            else:
                sent = bot.send_message(message.chat.id, "your price number not in range of this symbol price")
                bot.register_next_step_handler(message, spot_take_profit_reciever, signal_id, take_profit_number,
                                               number_position)
        else:
            sent = bot.send_message(message.chat.id, 'please enter numbers')
            bot.register_next_step_handler(message, spot_take_profit_reciever, signal_id, take_profit_number,
                                           number_position)
    elif number_position == take_profit_number:
        if is_number:
            spot = SpotSignal.objects.get(id=signal_id)
            price_filter = price_filter_check(spot.symbol_name, txt)
            if price_filter:
                take_profit = TakeProfit.objects.create(price=txt, level=number_position)
                print(take_profit)
                spot.take_profits.add(take_profit)
                sent = bot.reply_to(message, 'Enter your stop loss price')
                bot.register_next_step_handler(sent, spot_stop_loss_reciever, signal_id)
            else:
                sent = bot.send_message(message.chat.id, "your price number not in range of this symbol price")
                bot.register_next_step_handler(message, spot_take_profit_reciever, signal_id, take_profit_number,
                                               number_position)
        else:
            sent = bot.send_message(message.chat.id, 'please enter numbers')
            bot.register_next_step_handler(message, spot_take_profit_reciever, signal_id, take_profit_number,
                                           number_position)
    else:
        sent = bot.reply_to(message, 'Enter your stop loss price')
        bot.register_next_step_handler(sent, spot_stop_loss_reciever, signal_id)


def spot_stop_loss_reciever(message, signal_id):
    is_number, txt = int_or_float(message.text)
    if is_number:
        spot = SpotSignal.objects.get(id=signal_id)
        price_filter = price_filter_check(spot.symbol_name, txt)

        if price_filter:
            binance = BinanceUser.objects.get(telegram_user=message.chat.id)
            spot.stop_loss = txt
            spot.save()
            spot_strategy.apply_async(
                (binance.api_key, binance.secret_key, spot.id),
                countdown=random.uniform(10, 15),
            )

            sent = bot.reply_to(message, f'your order is submitted\n your order id is {spot.id} you can get more information \
            by sending your order id to /orderstatus')
        else:
            sent = bot.send_message(message.chat.id, "your price number not in range of this symbol price")
            bot.register_next_step_handler(sent, spot_stop_loss_reciever, signal_id)

    else:
        sent = bot.send_message(message.chat.id, 'please enter a number')
        bot.register_next_step_handler(message, spot_stop_loss_reciever, signal_id)


@bot.message_handler(commands=['orderstatus'])
def spot_order_status(message):
    sent = bot.reply_to(message, "Enter your spot signal id ")
    bot.register_next_step_handler(sent, spot_order_status_check)


def spot_order_status_check(message):
    spot = SpotSignal.objects.filter(telegram_user=message.chat.id, id=message.text)
    if spot:
        spot = spot[0]
        tp1, tp2, tp3 = spot.take_profits.all().order_by("level")
        entry_price = spot.entry_prices.all()[0]
        sent = bot.reply_to(message,
                            f"symbol: {spot.symbol_name} \nmin entry price: {entry_price.max_price}\n"
                            f"max entry price: {entry_price.min_price} \nvolume: {spot.volume} \n"
                            f"take profites-> tp1:{tp1.price} - tp2:{tp2.price} - tp3:{tp3.price} \n"
                            f"stop loss: {spot.stop_loss}\n"
                            f"  ")
    else:
        sent = bot.reply_to(message, "You dont have access to this order or not found")


try:
    print('~~~~~~~~~~~~~~~~ BOT IS STARTED ~~~~~~~~~~~~~~')
    bot.polling(none_stop=True)

except Exception as e:
    print(e)
    time.sleep(15)
    print('~~~~~~~~~~~~~~~~ BOT IS RESTARTED ~~~~~~~~~~~~~~')
    bot.polling(none_stop=True)
finally:
    time.sleep(15)
    print('~~~~~~~~~~~~~~~~ BOT IS RESTARTED ~~~~~~~~~~~~~~')
    bot.polling(none_stop=True)
