# binance-auto-trader
It is a auto trader based on user trade strategy.
The project is written in Django framework and use telegram bot API for communication with database and views.
Orders are commited in Binance platform ( The biggest in cryptocurrancy brokers)

# features
- spot orders 
- future orders
- auto sell and buy in three steps
- check status of a order (binance API has limition)


in signals/tasks.py implement a trade strategy based on a trader. Controlling and managing tasks are with Celery.
