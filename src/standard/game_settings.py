from datamodel import *
import pandas as pd

""" constants """

MAX_TIME = 1000000
TIME_STEP = 100

_use_special = True
_day_range = [1]

# _day_range = [1]
# _day_range = [-1, 0, 1]
# _day_range = [0, 1, 2]
#_day_range = [1, 2, 3]
#_use_special = False

_round_num = 4
_time_in_day = 1000000

trader_position_limits : Dict[Product, int] = {
    "BANANAS": 20,
    "PEARLS": 20,
    "COCONUTS": 600,
    "PINA_COLADAS": 300,
    "BERRIES": 250,
    "DIVING_GEAR": 50,
    "SEASHELLS": float("inf"),
    "BAGUETTE": 150,
    "DIP": 300,
    "UKULELE": 70,
    "PICNIC_BASKET": 70,
}

market_position_limits = { k: float("inf") for k in trader_position_limits.keys() }

LISTINGS : Dict[Symbol, Listing] = {
    prod: Listing(symbol=prod, product=prod, denomination=1)
    for prod in trader_position_limits.keys()
}
del LISTINGS["SEASHELLS"]

PRODUCTS = list(trader_position_limits.keys())
SYMBOLS = list(LISTINGS.keys())



""" read csvs into dataframe """

def get_special():
    fname = f"../data/round5/prices_round_6_day_5.csv"
    df = pd.read_csv(fname, sep=";")
    df["day"] = _day_range[0]
    return df

def get_file_trades(day):
    fname = f"../data/round5/trades_round_{_round_num}_day_{day}_wn.csv"
    print("fname", fname)
    return pd.read_csv(fname, sep=";")

def get_file_prices(day):
    fname = f"../data/round{_round_num}/prices_round_{_round_num}_day_{day}.csv"
    print("fname", fname)
    return pd.read_csv(fname, sep=";")



if _use_special:
    price_df = get_special()
else:
    prices = []
    for day in _day_range:
        price_df = get_file_prices(day)
        prices += [price_df]
    price_df = pd.concat(prices)

trades = []
for day in _day_range:
    # get data from files
    trade_df = get_file_trades(day)
    trade_df["day"] = day
    trades += [trade_df]

# concat all data
trade_df = pd.concat(trades)

if _use_special:
    trade_df = pd.DataFrame([], columns=trade_df.columns)

# reset indexes
trade_df = trade_df.reset_index(drop=True)
price_df = price_df.reset_index(drop=True)

# drop irrelevant columns
trade_df = trade_df.drop(["currency"], axis=1)
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

trade_df = trade_df.iloc[0:0]


## init observations
obs_names = ["DOLPHIN_SIGHTINGS"]
obs_df = price_df[price_df["symbol"].isin(obs_names)][["mid_price", "symbol", "time"]]
obs_df = obs_df.pivot(index="time", columns="symbol")["mid_price"].astype(int)
OBSERVATIONS = obs_df.T.to_dict()

print(trade_df.columns)
## init market_trades
all_market_trades = {}
for index, row in trade_df.iterrows():
    time = row["time"]
    sym = row["symbol"]
    if time not in all_market_trades:
        all_market_trades[time] = {}
    if sym not in all_market_trades[time]:
        all_market_trades[time][sym] = []
    
    trade = Trade(
        symbol=row["symbol"],
        price=row["price"], 
        quantity=row["quantity"], 
        buyer=row["buyer"], 
        seller=row["seller"],
        timestamp=row["time"],
    )
        
    all_market_trades[time][sym] += [trade]
    
MARKET_TRADES = all_market_trades


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
# from .bots.trader_bot_arb import Trader
from .bots.trader_bot_round4 import Trader

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
