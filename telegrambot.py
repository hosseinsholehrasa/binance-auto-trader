####################################################################################
import os
# for combining django and telegram
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "traderbot.settings")
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
#####################################################################################
import telebot
import time
from traderbot import settings
from signals.models import FutureSignal, SpotSignal, EntryPrice, TakeProfit
from users.models import BinanceUser, TelegramUser
from signals.binanceapi import intialize_symbol_name, live_price, spot_strategy

# TODO show live data 
# TODO transaction request status
# TODO ramz kardan key ha


# INITIALIZATION
apikey = settings.TELEGRAM_KEY
bot = telebot.TeleBot(apikey)
levrage_numbers = [i for i in range(1,126)]
symboles = intialize_symbol_name()

""" for convert string to int or float and check its str or not """
def int_or_float(str):
    if str.isdigit():
        return True, int(str)
    else:
        try:
            return True, float(str)
        except:
            return False, str

##########################################################################
# start button
@bot.message_handler(commands=['start'])
def start(message):
    telegram_user, is_created = TelegramUser.objects.get_or_create(id=message.chat.id)
    BinanceUser.objects.get_or_create(telegram_user=telegram_user)
    bot.reply_to(message,
"""خوش آمدید
برای ثبت سیگنال فیوچرز از دستور /newsignalF
برای ثبت سیگنال اسپات از دستور /newsignalS
ثبت api key و secret key بایننس /savekeys
نمایش کلید ذخیره کرده بایننس /showkeys"""
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
    if len(tps) == 3 and all(x.isdigit() for x in tps) :
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
    if  message.text.lower() in ["buy", "sell"]:
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
# TODO give correct number of TPs 
# TODO start task 
# TODO add check that a user have all api
########################################################################### NEW SIGNAL SPOT

@bot.message_handler(commands=['newsignalS'])
def spot_signal_receiver(message):
    sent = bot.reply_to(message, "Enter your symbol\nfor example (BTCUSDT) ")
    bot.register_next_step_handler(sent, spot_symbol_receiver)

def spot_symbol_receiver(message):
    if message.text.upper() in symboles:
        tel_user = TelegramUser.objects.get(id=message.chat.id)
        spot = SpotSignal.objects.create(telegram_user=tel_user ,symbol_name=message.text.upper())

        sent = bot.reply_to(
            message, f'Enter your entry price zone \nfor example 1000-1400\
                 \nprice now is {live_price(message.text.upper())}')
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
        entry_price = EntryPrice.objects.create(min_price=numbers_arr[0], max_price=numbers_arr[1])
        spot = SpotSignal.objects.get(id=signal_id)
        spot.entry_prices.add(entry_price)

        sent = bot.reply_to(message, 'Enter your volume')
        bot.register_next_step_handler(sent, spot_volume_reciever, signal_id)
    else:
        sent = bot.send_message(message.chat.id, 'please enter a number and check the correct format')
        bot.register_next_step_handler(message, spot_entry_price_reciever, signal_id)


def spot_volume_reciever(message, signal_id):
    is_number, txt = int_or_float(message.text)
    if is_number:
        spot = SpotSignal.objects.get(id=signal_id)
        spot.volume = txt
        spot.save()
        # TODO will get numbers of take profits
        sent = bot.reply_to(message, 'Enter your take profit numbers \nfor now just accept 3')
        bot.register_next_step_handler(sent, spot_take_profit_number_reciever, signal_id)
    else:
        sent = bot.send_message(message.chat.id, 'please enter a number')
        bot.register_next_step_handler(message, spot_volume_reciever, signal_id)

def spot_take_profit_number_reciever(message, signal_id):
    if message.text.isdigit():
        take_profit_number=3
        sent = bot.send_message(message.chat.id, 'please enter your take profit price 1:')
        bot.register_next_step_handler(sent, spot_take_profit_reciever, signal_id, take_profit_number)
    else:
        sent = bot.send_message(message.chat.id, 'please enter a number')
        bot.register_next_step_handler(message, spot_take_profit_number_reciever, signal_id)

def spot_take_profit_reciever(message, signal_id, take_profit_number, number_position= 1):
    if number_position < take_profit_number:
        is_number, txt = int_or_float(message.text)
        if is_number:
            take_profit = TakeProfit.objects.create(price=txt, level=number_position)
            spot = SpotSignal.objects.get(id=signal_id)
            spot.take_profits.add(take_profit)
            number_position += 1
            sent = bot.send_message(message.chat.id, f'please enter your take profit price {number_position}:')
            bot.register_next_step_handler(message, spot_take_profit_reciever, signal_id, take_profit_number, number_position)
        else:
            sent = bot.send_message(message.chat.id, 'please enter numbers')
            bot.register_next_step_handler(message, spot_take_profit_reciever, signal_id, take_profit_number, number_position)
    else:
        sent = bot.reply_to(message, 'Enter your stop loss price')
        bot.register_next_step_handler(sent, spot_stop_loss_reciever, signal_id)

def spot_stop_loss_reciever(message, signal_id):
    is_number, txt = int_or_float(message.text)
    if is_number:
        spot = SpotSignal.objects.get(id=signal_id)
        spot.stop_loss = txt
        spot.save()
        sent = bot.send_message(message.chat.id, 'please wait about ~10 second')
        # start a task and place order
        sent = bot.reply_to(message, f'your order is submitted\n your order id is {spot.id} you can get more information \
        by sending your order id to /orderstatus')
    else:
        sent = bot.send_message(message.chat.id, 'please enter a number')
        bot.register_next_step_handler(message, spot_stop_loss_reciever, signal_id)



# @bot.message_handler()
# def stock_request(message):
#     request = message.text.split()
#     bot.send_message(message.chat.id, message.text)

bot.polling(none_stop=True)
