from datamodel import *


""" constants """

MAX_TIME = 100000
TIME_STEP = 100

trader_position_limits : Dict[Product, int] = {
    "BANANAS": 20,
    "PEARLS": 20,
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
}

PRODUCTS = list(trader_position_limits.keys())
SYMBOLS = list(LISTINGS.keys())



""" player parameters """

from .fair import Fair

FAIR = Fair(
    products=PRODUCTS,
)

from .bots.taker_bot import TakerBot
from .bots.maker_bot import MakerBot
from .bots.trader_bot import Trader

PLAYERS = [
    MakerBot(
        player_id=100, 
        position_limits=market_position_limits, 
        fair_obj=FAIR
    ),
    Trader(player_id=1717, position_limits=trader_position_limits),
    TakerBot(
        player_id=500, 
        position_limits=market_position_limits, 
        fair_obj=FAIR
    ),
]

# players must have unique ids
assert len(PLAYERS) == len(set([p._player_id for p in PLAYERS])), "Player ids not unique"