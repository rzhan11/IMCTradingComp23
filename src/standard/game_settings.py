from datamodel import *
import pandas as pd

""" constants """

MAX_TIME = 3000000
TIME_STEP = 100

trader_position_limits : Dict[Product, int] = {
    "BANANAS": 20,
    "PEARLS": 20,
    "COCONUTS": 600,
    "PINA_COLADAS": 300,
    "SEASHELLS": float("inf")
}

market_position_limits = { k: float("inf") for k in trader_position_limits.keys() }

LISTINGS : Dict[Symbol, Listing] = {
    "BANANAS": Listing(
        symbol = "BANANAS",
        product = "BANANAS",
        denomination = 1,
    ),
    "PEARLS": Listing(
        symbol = "PEARLS",
        product = "PEARLS",
        denomination = 1,
    ),
    "COCONUTS": Listing(
        symbol = "COCONUTS",
        product = "COCONUTS",
        denomination = 1,
    ),
    "PINA_COLADAS": Listing(
        symbol = "PINA_COLADAS",
        product = "PINA_COLADAS",
        denomination = 1,
    ),
}
# LISTINGS : Dict[Symbol, Dict] = {
#     "BANANAS": {
#         "symbol": "BANANAS",
#         "product": "BANANAS",
#         "denomination": 1,
#     },
#     "PEARLS": {
#         "symbol": "PEARLS",
#         "product": "PEARLS",
#         "denomination": 1,
#     },
# }

PRODUCTS = list(trader_position_limits.keys())
SYMBOLS = list(LISTINGS.keys())



""" read csvs into dataframe """

# _day_range = [1]
_day_range = [-1, 0, 1]

_time_in_day = 1000000
_round_num = 2

def get_file_trades(day):
    fname = f"../data/round{_round_num}/trades_round_{_round_num}_day_{day}_nn.csv"
    print("fname", fname)
    return pd.read_csv(fname, sep=";")

def get_file_prices(day):
    fname = f"../data/round{_round_num}/prices_round_{_round_num}_day_{day}.csv"
    print("fname", fname)
    return pd.read_csv(fname, sep=";")

trades = []
prices = []

for day in _day_range:
    # get data from files
    trade_df = get_file_trades(day)
    price_df = get_file_prices(day)
    
    trade_df["day"] = day
    
    trades += [trade_df]
    prices += [price_df]


# concat all data
trade_df = pd.concat(trades)
price_df = pd.concat(prices)

# reset indexes
trade_df = trade_df.reset_index(drop=True)
price_df = price_df.reset_index(drop=True)

# drop irrelevant columns
trade_df = trade_df.drop(["currency", "buyer", "seller"], axis=1)
price_df = price_df.drop(["profit_and_loss"], axis=1)

# rename columns
price_df = price_df.rename({"product": "symbol"}, axis=1)
price_df = price_df.rename({"timestamp": "time"}, axis=1)
trade_df = trade_df.rename({"timestamp": "time"}, axis=1)


# calculate new time (for multiday)
trade_df["time"] = trade_df["time"] + (trade_df["day"] - min(_day_range)) * _time_in_day
price_df["time"] = price_df["time"] + (price_df["day"] - min(_day_range)) * _time_in_day

# rename "bid" to "buy"
# rename "ask" to "sell"
price_df = price_df.rename({col: col.replace("bid", "buy") for col in price_df.columns if "bid" in col}, axis=1)
price_df = price_df.rename({col: col.replace("ask", "sell") for col in price_df.columns if "ask" in col}, axis=1)



""" player parameters """

from .fair import Fair

FAIR = Fair(
    products=PRODUCTS,
    price_df=price_df,
)

from .bots.taker_bot import TakerBot
from .bots.maker_bot import MakerBot
# from .bots.trader_bot import Trader
# from .bots.trader_bot_ma_dynamic import Trader
from .bots.trader_bot_ma_position import Trader

PLAYERS = [
    MakerBot(
        player_id=100, 
        position_limits=market_position_limits, 
        is_main=False,
        fair_obj=FAIR,
        price_df=price_df, 
    ),
    Trader(
        player_id=1717, 
        position_limits=trader_position_limits,
        is_main=True,
    ),
    TakerBot(
        player_id=500, 
        position_limits=market_position_limits, 
        is_main=False,
        fair_obj=FAIR,
        trade_df=trade_df
    ),
]

# players must have unique ids
assert len(PLAYERS) == len(set([p._player_id for p in PLAYERS])), "Player ids not unique"