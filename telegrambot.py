import telebot
import pymysql
import time

#50 30 20
#kasper* sentrifiyozh
#btc eth 
#normal: luna sol matic dot ada 
#riski: hbar certik crv nfta nftb

# TODO show live data 
# TODO transaction request status
# TODO ramz kardan key ha

# INITIALIZATION
apikey = "1944746017:AAHU-JFds0PwQQhEhQbqbWeLJNbbaumsblg"
bot = telebot.TeleBot(apikey)
connector = pymysql.connect(db="telebot", user="root", passwd="kingking",host="127.0.0.1",port=3306,autocommit=True)
levrage_numbers = [i for i in range(1,126)]


# start button
@bot.message_handler(commands=['start'])
def start(message):
    with connector.cursor () as cursor:
        user_exist_sql = f"select * from users where tel_id={message.chat.id};"
        user_exist_resp = cursor.execute(user_exist_sql)
        if user_exist_resp == 0:
            sql = f"INSERT INTO users (tel_id) VALUES ({message.chat.id});"
            cursor.execute(sql)
    bot.reply_to(message, "خوش آمدید")

#  save api keys button
@bot.message_handler(commands=['savekeys'])
def save_keys(message):
    sent = bot.reply_to(message, "Enter your binance api_key")
    bot.register_next_step_handler(sent, save_api_key)

def save_api_key(message):
    if len(message.text) == 64:
        with connector.cursor () as cursor:
            sql = f"UPDATE users SET api_key='{message.text}' WHERE tel_id={message.chat.id};"
            cursor.execute(sql)
        sent = bot.send_message(message.chat.id, "Enter your binance secret key")
        bot.register_next_step_handler(sent, save_secret_key)

    else:
        bot.send_message(message.chat.id, 'Please enter a correct keys')
        bot.register_next_step_handler(message, save_api_key)
    
    bot.delete_message(message.chat.id, message.message_id)

def save_secret_key(message):
    if len(message.text) == 64:
        with connector.cursor () as cursor:
            sql = f"UPDATE users SET secret_key='{message.text}' WHERE (tel_id={message.chat.id});"
            cursor.execute(sql)
        bot.send_message(message.chat.id, 'DONE')
    else:
        bot.send_message(message.chat.id, 'Please enter a correct keys')
        bot.register_next_step_handler(message, save_secret_key)
    
    bot.delete_message(message.chat.id, message.message_id)

# show api keys
@bot.message_handler(commands=['showkeys'])
def show_keys(message):
    with connector.cursor () as cursor:
        sql = f"select api_key, secret_key from users where tel_id={message.chat.id};"
        cursor.execute(sql)
        result = cursor.fetchone()
    if all(result):
        bot.send_message(
            message.chat.id,
            f"api_key: \n{result[0][:10]}*****{result[0][55:]} \nsecret_key: \n{result[1][:10]}*****{result[1][55:]}")
    else:
        bot.send_message(message.chat.id, "you have to save keys first")

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

# NEW SIGNAL BUTTON
@bot.message_handler(commands=['newsignal'])
def signal_receiver(message):
    sent = bot.reply_to(message, "Enter your symbol\nfor example (BTCUSDT) ")
    bot.register_next_step_handler(sent, symbol_receiver)

def symbol_receiver(message):
    if message.text.lower() == "btcusdt":
        sent = bot.reply_to(message, 'Enter your entry price')
        bot.register_next_step_handler(sent, entry_price_reciever)
    else:
        sent = bot.send_message(message.chat.id, 'Incorrect')
        bot.register_next_step_handler(message, symbol_receiver)


def entry_price_reciever(message):
    if message.text.isdigit():
        sent = bot.reply_to(message, 'Enter your volume')
        bot.register_next_step_handler(sent, volume_reciever)
    else:
        sent = bot.send_message(message.chat.id, 'please enter a number')
        bot.register_next_step_handler(message, entry_price_reciever)

def volume_reciever(message):
    if message.text.isdigit():
        sent = bot.reply_to(message, 'Enter your 3 take profit price\n for example (1000 1500 1800)')
        bot.register_next_step_handler(sent, take_profit_reciever)
    else:
        sent = bot.send_message(message.chat.id, 'please enter a number')
        bot.register_next_step_handler(message, volume_reciever) 

def take_profit_reciever(message):
    tps = message.text.split()

    # check all of the three is integer
    if len(tps) == 3 and all(x.isdigit() for x in tps) :
        tpsint = [int(x) for x in tps]
        sent = bot.reply_to(message, 'Enter your stop loss price')
        bot.register_next_step_handler(sent, stop_loss_reciever)
    else:
        sent = bot.send_message(message.chat.id, 'please enter numbers')
        bot.register_next_step_handler(message, take_profit_reciever) 

def stop_loss_reciever(message):
    if message.text.isdigit():
        sent = bot.reply_to(message, 'Enter your levrage \n between 1-125')
        bot.register_next_step_handler(sent, levrage_reciever)
    else:
        sent = bot.send_message(message.chat.id, 'please enter a number')
        bot.register_next_step_handler(message, stop_loss_reciever) 

def levrage_reciever(message):
    if  message.text.isdigit() and int(message.text) in levrage_numbers:
        sent = bot.reply_to(message, 'Enter your position side (buy or sell)')
        bot.register_next_step_handler(sent, position_reciever)
    else:
        sent = bot.send_message(message.chat.id, 'please enter a correct number  between 1-125')
        bot.register_next_step_handler(message, levrage_reciever) 

def position_reciever(message):
    if  message.text.lower() in ["buy", "sell"]:
        sent = bot.reply_to(message, 'your request is pending')
    else:
        sent = bot.send_message(message.chat.id, 'please enter buy or sell word')
        bot.register_next_step_handler(message, position_reciever)



# @bot.message_handler()
# def stock_request(message):
#     request = message.text.split()
#     bot.send_message(message.chat.id, message.text)

bot.polling()
