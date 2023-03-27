import pandas as pd
import numpy as np
import json
import time

from typing import Dict, List, Tuple, Any
from datamodel import OrderDepth, TradingState, Order, Listing, ProsperityEncoder
from datamodel import Symbol, Product, Position


Price = int


MAX_POS = {
    "PEARLS": 20,
    "BANANAS": 20,
    "COCONUTS": 600,
    "PINA_COLADAS": 300,
    "BERRIES": 300,
    'DIVING_GEAR': 50, 
    'BAGUETTE': 140,
    'DIP': 280,
    'UKULELE': 70,
    'PICNIC_BASKET': 70,
}

PARAMS = {
    # game parameters
    "max_timestamp": 200000,
    "time_step": 100,
    # auto-close 
    "is_close": False,
    "close_turns": 30,

    # market-making params
    "is_penny": True,
    "match_size": False,

    # how many historical data points to use for analysis
    "DM.lookback": 100,

    # how many days used to compute true value
    "DM.ema_eval_true_days": 10,

    # how many days to test EMA against true
    "DM.ema_test_days": 120,

    "DM.ema_spans": [13,63],

    'rela':1.81,

    "make_flag": {
        "PEARLS": True,
        "BANANAS": True,
        "COCONUTS": False,
        "PINA_COLADAS": False,
        "BERRIES": False,
        "DIVING_GEAR": False,
        # round 4
        "BAGUETTE": True,
        "DIP": True,
        "UKULELE": True,
        "PICNIC_BASKET": True,
        },
    # "DM.ema_spans": [3, 10, 21, 100],
    # "DM.ema_spans": [3, 5, 10, 21, 30, 50, 100],
}


_description = f"""
PARAMS:
{json.dumps(PARAMS, indent=2)}
Description:
dynamic EMA
- DataManager lookback=100
- dynamic EMA by measuring how good ema
    - compare 10, 21, 100
- no closing at end of game
"""

class Logger:
    def __init__(self) -> None:
        self.logs = ""

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]]) -> None:
        print(json.dumps({
            "state": state,
            "orders": orders,
            "logs": self.logs,
        }, cls=ProsperityEncoder, separators=(",", ":"), sort_keys=True))

        self.logs = ""

logger = Logger()

REF_OPP_COSTS = {
    "BANANAS": {-20: -6.94, -19: -5.72, -18: -4.71, -17: -3.83, -16: -3.04, -15: -2.32, -14: -1.66, -13: -1.08, -12: -0.57, -11: -0.13, -10: 0.24, -9: 0.53, -8: 0.76, -7: 0.91, -6: 0.98, -5: 0.99, -4: 0.93, -3: 0.79, -2: 0.6, -1: 0.33, 0: 0.0, 1: -0.4, 2: -0.87, 3: -1.4, 4: -2.0, 5: -2.67, 6: -3.41, 7: -4.21, 8: -5.07, 9: -6.01, 10: -7.01, 11: -8.07, 12: -9.2, 13: -10.38, 14: -11.62, 15: -12.89, 16: -14.21, 17: -15.56, 18: -16.96, 19: -18.42, 20: -20.04},

    "PEARLS": {-20: -10.18, -19: -8.72, -18: -7.48, -17: -6.42, -16: -5.47, -15: -4.63, -14: -3.88, -13: -3.21, -12: -2.62, -11: -2.1, -10: -1.66, -9: -1.28, -8: -0.96, -7: -0.7, -6: -0.49, -5: -0.32, -4: -0.19, -3: -0.1, -2: -0.03, -1: -0.0, 0: 0.0, 1: -0.03, 2: -0.09, 3: -0.18, 4: -0.3, 5: -0.46, 6: -0.65, 7: -0.9, 8: -1.19, 9: -1.53, 10: -1.94, 11: -2.41, 12: -2.95, 13: -3.56, 14: -4.25, 15: -5.03, 16: -5.9, 17: -6.86, 18: -7.94, 19: -9.19, 20: -10.66},

    "BERRIES": {-250: 0.72, -249: 1.65, -248: 2.55, -247: 3.43, -246: 4.27, -245: 5.08, -244: 5.85, -243: 6.58, -242: 7.27, -241: 7.92, -240: 8.53, -239: 9.07, -238: 9.57, -237: 10.03, -236: 10.45, -235: 10.84, -234: 11.2, -233: 11.54, -232: 11.85, -231: 12.14, -230: 12.41, -229: 12.66, -228: 12.89, -227: 13.11, -226: 13.32, -225: 13.51, -224: 13.69, -223: 13.86, -222: 14.02, -221: 14.17, -220: 14.31, -219: 14.44, -218: 14.56, -217: 14.67, -216: 14.77, -215: 14.87, -214: 14.96, -213: 15.05, -212: 15.13, -211: 15.2, -210: 15.27, -209: 15.34, -208: 15.4, -207: 15.46, -206: 15.51, -205: 15.56, -204: 15.6, -203: 15.65, -202: 15.69, -201: 15.72, -200: 15.76, -199: 15.79, -198: 15.82, -197: 15.84, -196: 15.87, -195: 15.89, -194: 15.91, -193: 15.93, -192: 15.95, -191: 15.97, -190: 15.99, -189: 16.0, -188: 16.01, -187: 16.02, -186: 16.04, -185: 16.05, -184: 16.05, -183: 16.06, -182: 16.07, -181: 16.08, -180: 16.08, -179: 16.09, -178: 16.09, -177: 16.09, -176: 16.1, -175: 16.1, -174: 16.1, -173: 16.1, -172: 16.1, -171: 16.1, -170: 16.1, -169: 16.1, -168: 16.1, -167: 16.1, -166: 16.1, -165: 16.1, -164: 16.09, -163: 16.09, -162: 16.09, -161: 16.08, -160: 16.08, -159: 16.07, -158: 16.07, -157: 16.06, -156: 16.06, -155: 16.05, -154: 16.05, -153: 16.04, -152: 16.03, -151: 16.03, -150: 16.02, -149: 16.01, -148: 16.0, -147: 15.99, -146: 15.99, -145: 15.98, -144: 15.97, -143: 15.96, -142: 15.95, -141: 15.94, -140: 15.93, -139: 15.92, -138: 15.9, -137: 15.89, -136: 15.88, -135: 15.87, -134: 15.85, -133: 15.84, -132: 15.83, -131: 15.81, -130: 15.8, -129: 15.78, -128: 15.77, -127: 15.75, -126: 15.74, -125: 15.72, -124: 15.7, -123: 15.69, -122: 15.67, -121: 15.65, -120: 15.63, -119: 15.61, -118: 15.59, -117: 15.57, -116: 15.55, -115: 15.53, -114: 15.51, -113: 15.48, -112: 15.46, -111: 15.44, -110: 15.41, -109: 15.39, -108: 15.36, -107: 15.33, -106: 15.3, -105: 15.28, -104: 15.25, -103: 15.22, -102: 15.19, -101: 15.16, -100: 15.12, -99: 15.09, -98: 15.06, -97: 15.02, -96: 14.99, -95: 14.95, -94: 14.91, -93: 14.87, -92: 14.83, -91: 14.79, -90: 14.75, -89: 14.71, -88: 14.66, -87: 14.62, -86: 14.57, -85: 14.52, -84: 14.48, -83: 14.42, -82: 14.37, -81: 14.32, -80: 14.27, -79: 14.21, -78: 14.15, -77: 14.1, -76: 14.04, -75: 13.97, -74: 13.91, -73: 13.85, -72: 13.78, -71: 13.71, -70: 13.64, -69: 13.57, -68: 13.5, -67: 13.42, -66: 13.34, -65: 13.26, -64: 13.18, -63: 13.1, -62: 13.01, -61: 12.92, -60: 12.83, -59: 12.74, -58: 12.65, -57: 12.55, -56: 12.45, -55: 12.35, -54: 12.24, -53: 12.13, -52: 12.02, -51: 11.91, -50: 11.79, -49: 11.67, -48: 11.55, -47: 11.42, -46: 11.3, -45: 11.16, -44: 11.03, -43: 10.89, -42: 10.75, -41: 10.6, -40: 10.45, -39: 10.3, -38: 10.14, -37: 9.98, -36: 9.81, -35: 9.64, -34: 9.47, -33: 9.29, -32: 9.1, -31: 8.91, -30: 8.72, -29: 8.52, -28: 8.32, -27: 8.11, -26: 7.9, -25: 7.68, -24: 7.46, -23: 7.23, -22: 6.99, -21: 6.75, -20: 6.5, -19: 6.25, -18: 5.98, -17: 5.72, -16: 5.44, -15: 5.16, -14: 4.87, -13: 4.58, -12: 4.28, -11: 3.96, -10: 3.65, -9: 3.32, -8: 2.99, -7: 2.64, -6: 2.29, -5: 1.93, -4: 1.57, -3: 1.19, -2: 0.8, -1: 0.41, 0: 0.0, 1: -0.42, 2: -0.84, 3: -1.29, 4: -1.75, 5: -2.22, 6: -2.71, 7: -3.21, 8: -3.72, 9: -4.24, 10: -4.77, 11: -5.31, 12: -5.87, 13: -6.43, 14: -7.01, 15: -7.59, 16: -8.19, 17: -8.8, 18: -9.41, 19: -10.04, 20: -10.68, 21: -11.32, 22: -11.98, 23: -12.64, 24: -13.32, 25: -14.0, 26: -14.69, 27: -15.39, 28: -16.1, 29: -16.81, 30: -17.54, 31: -18.27, 32: -19.01, 33: -19.76, 34: -20.52, 35: -21.28, 36: -22.06, 37: -22.83, 38: -23.62, 39: -24.41, 40: -25.21, 41: -26.02, 42: -26.83, 43: -27.66, 44: -28.48, 45: -29.32, 46: -30.16, 47: -31.0, 48: -31.86, 49: -32.71, 50: -33.58, 51: -34.45, 52: -35.33, 53: -36.21, 54: -37.1, 55: -37.99, 56: -38.89, 57: -39.8, 58: -40.71, 59: -41.63, 60: -42.55, 61: -43.48, 62: -44.41, 63: -45.35, 64: -46.29, 65: -47.24, 66: -48.2, 67: -49.15, 68: -50.12, 69: -51.09, 70: -52.06, 71: -53.04, 72: -54.02, 73: -55.01, 74: -56.01, 75: -57.0, 76: -58.01, 77: -59.01, 78: -60.03, 79: -61.04, 80: -62.06, 81: -63.09, 82: -64.12, 83: -65.15, 84: -66.19, 85: -67.23, 86: -68.28, 87: -69.33, 88: -70.39, 89: -71.45, 90: -72.51, 91: -73.58, 92: -74.65, 93: -75.73, 94: -76.81, 95: -77.89, 96: -78.98, 97: -80.07, 98: -81.16, 99: -82.26, 100: -83.37, 101: -84.47, 102: -85.58, 103: -86.7, 104: -87.82, 105: -88.94, 106: -90.06, 107: -91.19, 108: -92.32, 109: -93.46, 110: -94.6, 111: -95.74, 112: -96.89, 113: -98.04, 114: -99.19, 115: -100.34, 116: -101.5, 117: -102.67, 118: -103.83, 119: -105.0, 120: -106.17, 121: -107.35, 122: -108.53, 123: -109.71, 124: -110.89, 125: -112.08, 126: -113.27, 127: -114.46, 128: -115.66, 129: -116.86, 130: -118.06, 131: -119.26, 132: -120.47, 133: -121.68, 134: -122.89, 135: -124.11, 136: -125.33, 137: -126.55, 138: -127.77, 139: -129.0, 140: -130.23, 141: -131.46, 142: -132.69, 143: -133.93, 144: -135.17, 145: -136.41, 146: -137.65, 147: -138.9, 148: -140.14, 149: -141.39, 150: -142.65, 151: -143.9, 152: -145.16, 153: -146.42, 154: -147.68, 155: -148.94, 156: -150.21, 157: -151.48, 158: -152.75, 159: -154.02, 160: -155.29, 161: -156.57, 162: -157.85, 163: -159.13, 164: -160.41, 165: -161.69, 166: -162.98, 167: -164.27, 168: -165.56, 169: -166.85, 170: -168.14, 171: -169.43, 172: -170.73, 173: -172.03, 174: -173.33, 175: -174.63, 176: -175.93, 177: -177.24, 178: -178.54, 179: -179.85, 180: -181.16, 181: -182.47, 182: -183.78, 183: -185.09, 184: -186.41, 185: -187.73, 186: -189.04, 187: -190.36, 188: -191.68, 189: -193.01, 190: -194.33, 191: -195.65, 192: -196.98, 193: -198.31, 194: -199.63, 195: -200.96, 196: -202.29, 197: -203.62, 198: -204.96, 199: -206.29, 200: -207.63, 201: -208.96, 202: -210.3, 203: -211.64, 204: -212.98, 205: -214.32, 206: -215.66, 207: -217.0, 208: -218.34, 209: -219.69, 210: -221.03, 211: -222.38, 212: -223.73, 213: -225.07, 214: -226.42, 215: -227.78, 216: -229.13, 217: -230.48, 218: -231.83, 219: -233.19, 220: -234.54, 221: -235.9, 222: -237.25, 223: -238.6, 224: -239.95, 225: -241.3, 226: -242.65, 227: -243.99, 228: -245.34, 229: -246.69, 230: -248.04, 231: -249.39, 232: -250.75, 233: -252.11, 234: -253.47, 235: -254.83, 236: -256.2, 237: -257.58, 238: -258.96, 239: -260.35, 240: -261.76, 241: -263.18, 242: -264.62, 243: -266.06, 244: -267.51, 245: -268.96, 246: -270.39, 247: -271.8, 248: -273.19, 249: -274.57, 250: -275.93},

    "PICNIC_BASKET": {-70: -7.93, -69: -6.27, -68: -4.91, -67: -3.82, -66: -2.94, -65: -2.25, -64: -1.73, -63: -1.33, -62: -0.99, -61: -0.73, -60: -0.55, -59: -0.42, -58: -0.32, -57: -0.24, -56: -0.18, -55: -0.14, -54: -0.1, -53: -0.08, -52: -0.06, -51: -0.04, -50: -0.03, -49: -0.02, -48: -0.02, -47: -0.01, -46: -0.01, -45: -0.01, -44: -0.0, -43: -0.0, -42: -0.0, -41: 0.0, -40: 0.0, -39: 0.0, -38: 0.0, -37: 0.0, -36: 0.0, -35: 0.0, -34: 0.0, -33: 0.0, -32: 0.0, -31: 0.0, -30: 0.0, -29: 0.0, -28: 0.0, -27: 0.0, -26: 0.0, -25: 0.0, -24: 0.0, -23: 0.0, -22: 0.0, -21: 0.0, -20: 0.0, -19: 0.0, -18: 0.0, -17: 0.0, -16: 0.0, -15: 0.0, -14: 0.0, -13: 0.0, -12: 0.0, -11: 0.0, -10: 0.0, -9: 0.0, -8: 0.0, -7: 0.0, -6: 0.0, -5: 0.0, -4: 0.0, -3: 0.0, -2: 0.0, -1: 0.0, 0: 0.0, 1: -0.0, 2: -0.0, 3: -0.0, 4: -0.0, 5: -0.0, 6: -0.0, 7: -0.0, 8: -0.0, 9: -0.0, 10: -0.0, 11: -0.01, 12: -0.01, 13: -0.01, 14: -0.01, 15: -0.01, 16: -0.01, 17: -0.01, 18: -0.02, 19: -0.02, 20: -0.02, 21: -0.03, 22: -0.03, 23: -0.03, 24: -0.04, 25: -0.04, 26: -0.05, 27: -0.06, 28: -0.07, 29: -0.08, 30: -0.09, 31: -0.1, 32: -0.12, 33: -0.13, 34: -0.15, 35: -0.18, 36: -0.2, 37: -0.23, 38: -0.26, 39: -0.3, 40: -0.34, 41: -0.39, 42: -0.45, 43: -0.51, 44: -0.59, 45: -0.67, 46: -0.77, 47: -0.88, 48: -1.0, 49: -1.14, 50: -1.31, 51: -1.49, 52: -1.71, 53: -1.95, 54: -2.23, 55: -2.55, 56: -2.91, 57: -3.33, 58: -3.8, 59: -4.33, 60: -4.93, 61: -5.65, 62: -6.45, 63: -7.43, 64: -8.54, 65: -9.74, 66: -11.02, 67: -12.45, 68: -14.0, 69: -15.7, 70: -17.51},

    # PINA_COLADAS, COCONUTS are initialized in init_ref_opp_costs()
}

def init_ref_opp_costs():
    global REF_OPP_COSTS
    default_syms = [
        "PINA_COLADAS", "COCONUTS", # round 2
        "DIVING_GEAR", # round 3 
        "BAGUETTE", "DIP", "UKULELE", #"PICNIC_BASKET", # round 4
    ]

    for sym in default_syms:
        assert sym not in REF_OPP_COSTS

        limit = MAX_POS[sym]
        REF_OPP_COSTS[sym] = {i: round(-1 * abs(i) / limit, 3) for i in range(-limit, limit + 1)}

init_ref_opp_costs()

# print = logger.print

class Trader:

    def __init__(self, 
            player_id=None, 
            position_limits=None,
            is_main=False,
            ):
        
        # print description to help identify bot/params
        logger.print(_description)

        # local engine vars
        self._player_id = player_id
        self._is_main = is_main

        self._position_limits = position_limits
        if self._position_limits is None:
            self._position_limits = MAX_POS
        
        # init history tracker
        self.DM : DataManager = DataManager(
            lookback=PARAMS["DM.lookback"],
            ema_eval_true_days=PARAMS["DM.ema_eval_true_days"],
            ema_test_days=PARAMS["DM.ema_test_days"],
            ema_spans=PARAMS["DM.ema_spans"],
        )

        # helper vars
        self.turn = -1
        self.finish_turn = -1
        self.lead=0
        # parameters
        self.is_close = PARAMS["is_close"]
        self.close_turns = PARAMS["close_turns"]
        self.max_timestamp = PARAMS["max_timestamp"]
        self.time_step = PARAMS["time_step"]
        self.long=0
        self.long_berry=0
        self.is_penny = PARAMS["is_penny"]
        self.match_size = PARAMS["match_size"]



    def turn_start(self, state: TradingState):
        # measure time
        self.wall_start_time = time.time()
        self.process_start_time = time.process_time()

        # print round header
        self.turn += 1

        logger.print(f"Round {state.timestamp}, {self.turn}")
        logger.print("-"*50)



        # print raw json, for analysis
        self.record_game_state(state)

        # preprocess game state
        Preprocess.preprocess(state)

        # setup list of current products
        self.products = set([listing.product for sym, listing in state.listings.items()])
        self.symbols = set([listing.symbol for sym, listing in state.listings.items()])

        self.products = sorted(list(self.products))
        self.symbols = sorted(list(self.symbols))

        # reset _buy_orders/_sell_orders for this turn
        self.OM : OrderManager = OrderManager(
            symbols=self.symbols,
            position_limits=self._position_limits,
            listings=state.listings,
        )


        # store/process game state into history
        self.DM.add_history(state, self.products, self.symbols)
        # self.DM.process_history()


    def run(self, state: TradingState) -> Dict[Symbol, List[Order]]:
        """ Called by game engine, returns dict of buy/sell orders
        """


        state_json = json.loads(state.toJSON())

        
        # turn setup
        self.turn_start(state)

        # main body
        self.run_internal(state)
        # cleanup / info reporting section
        orders = self.turn_end(state)
        
        logger.flush(state_json, orders)

        return orders
    

    def turn_end(self, state):
        """ Runs at end of turn
        - records the orders we submit
        - postprocess orders to get them inthe 
        """
        
        # post process orders
        my_orders = self.OM.postprocess_orders()

        # record end of turn (after post-processing)
        self.record_turn_end(state)

        # return my orders
        self.finish_turn += 1
        return my_orders
    


    def get_ema_mid(self, sym: Symbol) -> float:
        
        # calc mid_ema
        sym_history = self.DM.history[sym]
        mid_ema = sym_history[-1]["best_ema"]
        # mid_ema_span = sym_history[-1]["best_ema_span"]

        return mid_ema



    def get_fair_value(self, sym: Symbol) -> float:

        mid_ema = self.get_ema_mid(sym)

        # get large_quote_mid
        large_quote_mid, use_large_quote_mid = self.get_large_quote_mid(sym)
        

        # if conditions were good, use large_quote_mid
        if use_large_quote_mid:
            return large_quote_mid
        else: # else, use ema
            return mid_ema

    def run_internal(self, state: TradingState):
        """ Main body of logic
        - analyzes current market
        - places new orders for this turn
        """

        OM = self.OM
        round_1_goods= {
        "PEARLS",
        "BANANAS"}
        round_4_goods={ 'BAGUETTE','DIP','UKULELE','PICNIC_BASKET'}

        self.all_buys = {}
        self.all_sells = {}

        for sym in state.order_depths.keys():
            book = state.order_depths[sym]

            buys: List[Tuple[Price, Position]] = sorted(list(book.buy_orders.items()), reverse=True)
            sells: List[Tuple[Price, Position]] = sorted(list(book.sell_orders.items()), reverse=False)

            self.all_buys[sym] = buys            
            self.all_sells[sym] = sells 
        # close all positions if `is_close` flag is on, and we are at end of game
        if self.is_close and state.timestamp >= self.max_timestamp - self.time_step * self.close_turns:
            self.close_positions(state)
            return



        # Iterate over all the keys (the available products) contained in the order depths
        for sym in state.order_depths.keys():

            prod: Product = state.listings[sym].product

            book = state.order_depths[sym]

            buys: List[Tuple[Price, Position]] = sorted(list(book.buy_orders.items()), reverse=True)
            sells: List[Tuple[Price, Position]] = sorted(list(book.sell_orders.items()), reverse=False)

            # Use exponential moving average to check for price spikes
            # should_carp_bid = True
            # should_carp_ask = True
            # volatility_cap = 0.0005
            # lookback = 10
            
            # book_tops = self.DM.book_tops
            sym_history = self.DM.history[sym]

            mid_ema = sym_history[-1]["best_ema"]
            mid_ema_span = sym_history[-1]["best_ema_span"]
            logger.print(f"{sym} EMA (span: {mid_ema_span}), {mid_ema}")
            arb_flag=False
            self.arbed=False
            if sym in round_4_goods and not arb_flag:
                arb_flag=True
                self.arb_logic(state=state,sym='BAGUETTE',sym1='DIP',sym2='UKULELE',etf='PICNIC_BASKET')

            if self.arbed==False and sym in round_4_goods:
                fair_value = self.get_fair_value(sym)   
                mid_ema = self.get_ema_mid(sym) 
                self.make_logic_etf(state, sym, fair_value, None)

            if sym in round_1_goods:
                self.take_logic(
                state=state,
                sym=sym,
                buys=buys,
                sells=sells, 
                mid_ema=mid_ema,
                )

                self.make_logic(
                    state=state,
                    sym=sym,
                    buys=buys,
                    sells=sells, 
                    mid_ema=mid_ema,
                )
            if sym ==' BERRIES':
                self.take_logic_3(
                state=state,
                sym=sym,
                buys=buys,
                sells=sells, 
                mid_ema=mid_ema,
                )
            if sym== ' DIVING_GEAR':
                self.take_logic_lead(
                state=state,
                sym=sym,
                buys=buys,
                sells=sells, 
                mid_ema=mid_ema,
                )

            else: 
                self.take_logic_2(
                state=state,
                sym=sym,
                buys=buys,
                sells=sells, 
                mid_ema=mid_ema,
                )
    def arb_logic(self,state: TradingState,
            sym, sym1,sym2, etf
            ):
        OM = self.OM
        book = state.order_depths[sym]
        buys: List[Tuple[Price, Position]] = sorted(list(book.buy_orders.items()), reverse=True)
        sells: List[Tuple[Price, Position]] = sorted(list(book.sell_orders.items()), reverse=False)

        book1 = state.order_depths[sym1]
        buys1: List[Tuple[Price, Position]] = sorted(list(book1.buy_orders.items()), reverse=True)
        sells1: List[Tuple[Price, Position]] = sorted(list(book1.sell_orders.items()), reverse=False)

        book2 = state.order_depths[sym2]
        buys2: List[Tuple[Price, Position]] = sorted(list(book2.buy_orders.items()), reverse=True)
        sells2: List[Tuple[Price, Position]] = sorted(list(book2.sell_orders.items()), reverse=False)

        book_etf = state.order_depths[etf]
        buys_etf: List[Tuple[Price, Position]] = sorted(list(book_etf.buy_orders.items()), reverse=True)
        sells_etf: List[Tuple[Price, Position]] = sorted(list(book_etf.sell_orders.items()), reverse=False)

        if sells[0][0]*2+sells1[0][0]*4+sells2[0][0]<buys_etf[0][0]:
            limit=OM.get_rem_buy_size(state, sym)
            limit1= OM.get_rem_buy_size(state, sym1)
            limit2= OM.get_rem_buy_size(state, sym2)
            limit_etf= OM.get_rem_sell_size(state, etf)
            true_lim=min(limit//2,limit1//4,limit2,limit_etf)
            if true_lim==0:
                pass
            self.arbed=True
            OM.place_buy_order( Order(
                        symbol=sym,
                        price=sells[0][0],
                        quantity=true_lim*2,
                        is_take=True,
                    ))
            OM.place_buy_order( Order(
                        symbol=sym1,
                        price=sells1[0][0],
                        quantity=true_lim*4,
                        is_take=True,
                    ))
            OM.place_buy_order( Order(
                        symbol=sym2,
                        price=sells2[0][0],
                        quantity=true_lim,
                        is_take=True,
                    ))
            OM.place_sell_order( Order(
                        symbol=etf,
                        price=buys_etf[0][0],
                        quantity=true_lim,
                        is_take=True,
                    ))
        if buys[0][0]*2+buys1[0][0]*4+buys2[0][0]>sells_etf[0][0]:

            limit=OM.get_rem_sell_size(state, sym)
            limit1= OM.get_rem_sell_size(state, sym1)
            limit2= OM.get_rem_sell_size(state, sym2)
            limit_etf= OM.get_rem_buy_size(state, etf)
            true_lim=min(limit//2,limit1//4,limit2,limit_etf)
            if true_lim==0:
                pass
            self.arbed=True
            OM.place_sell_order( Order(
                        symbol=sym,
                        price=buys[0][0],
                        quantity=true_lim*2,
                        is_take=True,
                    ))
            OM.place_sell_order( Order(
                        symbol=sym1,
                        price=buys1[0][0],
                        quantity=true_lim*4,
                        is_take=True,
                    ))
            OM.place_sell_order( Order(
                        symbol=sym2,
                        price=buys2[0][0],
                        quantity=true_lim,
                        is_take=True,
                    ))
            OM.place_buy_order( Order(
                        symbol=etf,
                        price=sells_etf[0][0],
                        quantity=true_lim
                        ,is_take=True,
                    ))
            
        
    def make_logic_etf(self, 
            state: TradingState,
            sym: Symbol, 
            fair_value: float,
            custom_opp_cost: Dict[Position, float]=None,
            ):
        
        buys, sells = self.all_buys[sym], self.all_sells[sym]
        OM = self.OM
        prod = state.listings[sym].product


        should_penny = False
        if self.is_penny:
            # if len(buys) > 0 and len(sells) > 0:
            #     spread = sells[0][0] - buys[0][0]
            #     if spread > 2:
                    # should_penny = True
            should_penny = True
        OPP_COST = REF_OPP_COSTS[prod]

        ### special case for bananas
        if custom_opp_cost is not None:
            OPP_COST = custom_opp_cost


        for price, quantity in buys:
            if should_penny:
                price += 1

            cur_pos = OM.get_expected_pos(state, prod)
            limit = OM.get_rem_buy_size(state, sym)

            # max_buy_size = min(limit, quantity)
            max_buy_size = limit

            scores = []
            for buy_size in range(0, max_buy_size + 1):
                # we are putting buy orders
                new_pos = cur_pos + buy_size

                opp_change = OPP_COST[new_pos] - OPP_COST[cur_pos]
                edge = fair_value - price
                adj_rtn = edge * buy_size + opp_change

                scores += [(adj_rtn, buy_size)]

            # get the size with the optimal expected adjusted return
            if len(scores) > 0:
                adj_rtn, buy_size = max(scores)
                if adj_rtn > 0 and buy_size > 0:
                    if buy_size==0:
                        pass
                    OM.place_buy_order(
                        symbol=sym,
                        price=price,
                        quantity=buy_size,
                        is_take=False,
                    )
            

        for price, quantity in sells:
            if should_penny:
                price -= 1

            cur_pos = OM.get_expected_pos(state, prod)
            limit = OM.get_rem_sell_size(state, sym)

            # max_sell_size = min(limit, quantity)
            max_sell_size = limit

            scores = []
            for sell_size in range(0, max_sell_size + 1):
                # we are putting sell orders
                new_pos = cur_pos - sell_size

                opp_change = OPP_COST[new_pos] - OPP_COST[cur_pos]
                edge = price - fair_value
                adj_rtn = edge * sell_size + opp_change

                scores += [(adj_rtn, sell_size)]

            # get the size with the optimal expected adjusted return
            if len(scores) > 0:
                adj_rtn, sell_size = max(scores)
                if adj_rtn > 0 and sell_size > 0:
                    if sell_size==0:
                        pass
                    OM.place_sell_order(
                        symbol=sym,
                        price=price,
                        quantity=sell_size,
                        is_take=False,
                    )
        
    
    def take_logic_lead(self,state: TradingState,
            sym: Symbol, 
            buys: List[Tuple[Price, Position]], 
            sells: List[Tuple[Price, Position]], 
            mid_ema: float,
            ):
        OM = self.OM
        if len(self.DM.dolph) < 6:
            pass
        def mono_up( l, n):
            flag=False
            for i in range(len(l),-1,-1):
                if l[i]<l[i-1]:
                    return flag
                n-=1
                if n ==0:
                    return True
        def jump_up(l):
            loc_min= min(l[-10:-1])
            if l[-1]-l[-2]>= 1:
                return True
            else:
                return False
        def jump_down(l):
            loc_max=max(l[-10:-1])
            if l[-1]-l[-2]<= -1:
                return True
            else:
                return False
        def mono_down( l, n):
            flag=False
            for i in range(len(l),-1,-1):
                if l[i]>l[i-1]:
                    return flag
                n-=1
                if n ==0:
                    return True
        dolph=self.DM.dolph
        if jump_up(dolph)  :
            cur= 50-OM.get_rem_sell_size(state, sym) 
            limit = OM.get_rem_sell_size(state, sym)                   
            #OM.place_buy_order(Order(
                       # symbol=sym,
                       # price=sells[-1][0],
                        #quantity=min(limit,cur)
                    #))
        
            '''
        if self.lead==1 and mono_down(self.DM.dolph,3):
            limit = 50-OM.get_rem_sell_size(state, sym)                   
            OM.place_sell_order(Order(
                        symbol=sym,
                        price=buys[-1][0],
                        quantity=limit
                    ))
            self.lead=0
        '''
        if jump_down(dolph)  :
            cur=50-OM.get_rem_buy_size(state, sym)  
            limit = OM.get_rem_buy_size(state, sym)                   
            #OM.place_sell_order(Order(
                        #symbol=sym,
                        #price=buys[-1][0],
                        #quantity=min(limit,cur)
                   # ))
      
        '''
        if self.lead==-1 and mono_up(self.DM.dolph,3):
            limit = 50-OM.get_rem_buy_size(state, sym)                   
            OM.place_buy_order(Order(
                        symbol=sym,
                        price=sells[-1][0],
                        quantity=limit
                    ))
            self.lead=0
        '''



    def take_logic(self, 
            state: TradingState,
            sym: Symbol, 
            buys: List[Tuple[Price, Position]], 
            sells: List[Tuple[Price, Position]], 
            mid_ema: float,
            ):
        
        OM = self.OM

        min_buy_edge = 1
        min_sell_edge = 1
        limit = OM.get_rem_sell_size(state, sym)
        limit_buy= OM.get_rem_buy_size(state, sym)


        # take orders on buy_side (we sell to existing buy orders)
        for price, quantity in buys:
            if price > mid_ema + min_buy_edge:
                if limit_buy > 0:
                    OM.place_sell_order(Order(
                        symbol=sym,
                        price=price,
                        quantity=min(limit_buy, quantity),
                        is_take=True
                    ))

        # take orders on sell side (we buy from existing sell orders)
        for price, quantity in sells:
            if price < mid_ema - min_sell_edge:
                if limit > 0:
                    OM.place_buy_order(Order(
                        symbol=sym,
                        price=price,
                        quantity=min(limit, quantity),
                        is_take=True,
                    ))

    def take_logic_2( self, 
            state: TradingState,
            sym: Symbol, 
            buys: List[Tuple[Price, Position]], 
            sells: List[Tuple[Price, Position]], 
            mid_ema: float,
            ):
        OM = self.OM
        limit = OM.get_rem_sell_size(state, sym)
        limit_buy= OM.get_rem_buy_size(state, sym)
        margin= self.DM.history[sym][-1]['mid']*0.0002
        if self.DM.history[sym][-1]['macd']>0+margin and self.long<=0:
                OM.place_buy_order(Order(
                        symbol=sym,
                        price=sells[-1][0],
                        quantity=limit,is_take=True,
                    ))
                self.long=1

        if self.DM.history[sym][-1]['macd']< 0-margin and self.long>=0:
                OM.place_sell_order(Order(
                        symbol=sym,
                        price=buys[-1][0],
                        quantity=limit_buy,
                        is_take=True,
                    ))
                self.long=-1 

    def take_logic_3( self, 
            state: TradingState,
            sym: Symbol, 
            buys: List[Tuple[Price, Position]], 
            sells: List[Tuple[Price, Position]], 
            mid_ema: float,
            ):

            if len(self.DM.history[sym]) <500: 
                OM = self.OM
                limit = OM.get_rem_sell_size(state, sym)
                limit_buy= OM.get_rem_buy_size(state, sym)
                margin= self.DM.history[sym][-1]['mid']*0.0002
                if self.DM.history[sym][-1]['macd']>0+margin and self.long_berry<=0:
                    OM.place_buy_order(Order(
                        symbol=sym,
                        price=sells[-1][0],
                        quantity=limit,
                        is_take=True,
                    ))
                    self.long_berry=1

                if self.DM.history[sym][-1]['macd']< 0-margin and self.long_berry>=0:
                    OM.place_sell_order(Order(
                        symbol=sym,
                        price=buys[-1][0],
                        quantity=limit_buy,
                        is_take=True,
                    ))
                    self.long_berry=-1 

            else: 
                if mid_ema < self.DM.history[sym][-1]['highest'] and self.long_berry>=0:

                    limit_buy= OM.get_rem_buy_size(state, sym)
                    OM.place_sell_order(Order(
                        symbol=sym,
                        price=buys[-1][0],
                        quantity=limit_buy,
                        is_take=True,
                    ))
                    self.long_berry=-1
            
    


        
                          

    def make_logic(self, 
            state: TradingState,
            sym: Symbol, 
            buys: List[Tuple[Price, Position]], 
            sells: List[Tuple[Price, Position]], 
            mid_ema: float,
            ):
        
        OM = self.OM

        should_penny = False
        if self.is_penny:
            if len(buys) > 0 and len(sells) > 0:
                spread = sells[0][0] - buys[0][0]
                if spread > 2 :
                    should_penny = True
        span=self.DM.ema_spans

        # match orders on buy-side
        for price, quantity in buys:
            if should_penny:
                price += 1

            # don't carp if buy price is higher than EMA
            if price > mid_ema:
                continue

            limit = OM.get_rem_buy_size(state, sym)
            if limit > 0:
                if self.match_size:
                    limit_1=int(limit)
                    limit_2=limit-limit_1
                    order_quantity_1 = limit_1
                    order_quantity_2= limit_2
                else:
                    limit_1=int(limit)
                    order_quantity_1 = limit_1


                OM.place_buy_order(Order(
                    symbol=sym,
                    price=price,
                    quantity=order_quantity_1,
                    is_take=False,
                ))



        # match orders on sell-side
        for price, quantity in sells:
            if should_penny:
                price -= 1

            # don't carp if sell price is higher than EMA
            if price < mid_ema:
                continue

            limit = OM.get_rem_sell_size(state, sym)

            if limit > 0:
                if self.match_size:
                    limit_1=int(limit)
                    limit_2=limit-limit_1
                    order_quantity_1 = limit_1
                    
                else:
                    limit_1=int(limit)
                    limit_2=limit-limit_1
                    order_quantity_1 = limit_1
                    
                OM.place_sell_order(Order(
                    symbol=sym,
                    price=price,
                    quantity=order_quantity_1,
                    is_take=False,
                ))

    def make_logic_2(self, 
            state: TradingState,
            sym: Symbol, 
            buys: List[Tuple[Price, Position]], 
            sells: List[Tuple[Price, Position]], 
            mid_ema: float,
            ):
        if len(self.DM.history[sym]) <500:
            self.make_logic(state,sym,buys,sells,mid_ema)

        else: 
            OM = self.OM
            limit = OM.get_rem_sell_size(state, sym)
            if limit > 0:
                price= int(self.DM.history[sym][-1]['mid'])
                OM.place_sell_order(Order(
                    symbol=sym,
                    price=price,
                    quantity=min(limit,sells[0][1]),is_take=False,
                ))
            
            lim_buy= OM.get_rem_buy_size(state, sym)
            lim_buy= min(lim_buy,100)
            if lim_buy>0:
                price= buys[0][0]
                OM.place_buy_order(Order(
                    symbol=sym,
                    price=price,
                    quantity=min(lim_buy,buys[0][1]),is_take=False,
                ))








    #calculates EMA of past x days
    def calc_ema(self, ser : pd.Series, span : int):
        return ser.ewm(span=span, adjust=False).mean().iloc[-1]


    def close_positions(self, state: TradingState):
        """ Closes out our position at the end of the game
        - was previously used since IMC's engine uses weird fair values
        """
        OM = self.OM

        for prod, pos in state.position.items():
            if pos < 0:
                OM.place_buy_order(Order(symbol=prod, price=1e9, quantity=1))
            elif pos > 0:
                OM.place_sell_order(Order(symbol=prod, price=0, quantity=1))



    def record_game_state(self, state: TradingState):
        """
        Prints out the state of the game when received
        """

        state.turn = self.turn
        state.finish_turn = self.finish_turn

        s = state.toJSON()

        print(f"__game_state_start\n{s}\n__game_state_end\n")

        

    def record_turn_end(self, state: TradingState):
        """ Prints out end of turn info, including:
        - orders we sent this turn
        """

        OM = self.OM
        good_sym=[]
        for sym in self.symbols:
            if sym != 'DOLPHIN_SIGHTINGS':
                good_sym.append(sym)

        my_orders = {sym: { "buy_orders": OM._buy_orders[sym], "sell_orders": OM._sell_orders[sym] } for sym in self.symbols}

        emas = { sym: self.DM.history[sym][-1]["emas"] for sym in good_sym }
        best_emas = { sym: self.DM.history[sym][-1]["best_ema"] for sym in good_sym }
        best_ema_spans = { sym: self.DM.history[sym][-1]["best_ema_span"] for sym in good_sym }


        obj = {
            "time": state.timestamp,
            "wall_time": time.time() - self.wall_start_time,
            "process_time": time.process_time() - self.process_start_time,
            "my_orders": my_orders,
            "emas": emas,
            "best_emas": best_emas,
            "best_ema_spans": best_ema_spans,
        }


        
        # convert obj to 
        s = json.dumps(obj, default=lambda o: o.__dict__, sort_keys=True)

        print(f"__turn_end_start\n{s}\n__turn_end_end")



class DataManager:
    """
    This class stores historical data + contains all of our data analysis code
    """

    def __init__(
                self, 
                lookback, 
                ema_eval_true_days,
                ema_test_days,
                ema_spans,
            ):
        """
        lookback - defines how many historical days are used by our data analysis
        """

        self.lookback = lookback
        self.ema_eval_true_days = ema_eval_true_days
        self.ema_test_days = ema_test_days
        self.ema_spans = ema_spans
        self.default_ema_span = ema_spans[0]
        self.rela=PARAMS["rela"]
        self.rela_ema=[]
        self.history = {}
        self.dolph=[]


    def add_history(self, state: TradingState, symbols: List[Symbol], products: List[Product]):
        """
        Stores state
        - should be called after preprocessing / recording of game state
        """
        self.symbols = symbols
        self.products = products

        for sym in symbols:
            if sym=='DOLPHIN_SIGHTINGS':
                self.dolph.append(state.observations[sym])
                continue
            else:
                self.add_history_sym(state, sym)

    def add_history_sym(self, state: TradingState, sym: Symbol):
        # add sym to history if not present
        if sym not in self.history:
            self.history[sym] = []
        sym_history = self.history[sym]

        book = state.order_depths[sym]

        buys: List[Tuple[Price, Position]] = sorted(list(book.buy_orders.items()), reverse=True)
        sells: List[Tuple[Price, Position]] = sorted(list(book.sell_orders.items()), reverse=False)

        if len(buys) > 0:
            best_buy = buys[0][0]

        if len(sells) > 0:
            best_sell = sells[0][0]

        mid = (best_buy + best_sell) / 2

        if len(sym_history)==0 or mid > sym_history[-1]["highest"]:
            high_res=mid
        else:
            high_res= sym_history[-1]["highest"]
        # get previous emas
        if len(sym_history) == 0:
            old_emas = {span: mid for span in self.ema_spans}
        else:
            old_emas = sym_history[-1]["emas"]

        # calculate ema for each span
        new_emas = {}
        ema_rec=[]
        fast=0
        slow=0
        for span in self.ema_spans:
            # calculate ema
            alpha = 2 / (span + 1)
            new_ema = mid * alpha + (1 - alpha) * old_emas[span]
            # round for pretty print
            ema_rec.append(new_ema)
            new_emas[span] = round(new_ema, 2)
        fast=ema_rec[0]
        slow=ema_rec[1]
        macd= fast-slow
        # find best ema
        if len(sym_history) < self.ema_eval_true_days + 1:
            # use default if no history
            best_ema_span = self.default_ema_span
        else:
            # find best ema (using L1 difference)
            scores = []
            # need ema_test_days + ema_eval_true_days + 1
            n_days = min(self.ema_test_days + self.ema_eval_true_days + 1, len(sym_history))

            # calc SMAs
            old_mids = [sym_history[-(i + 1)]["mid"] for i in range(n_days - 1)]
            old_mids = list(reversed(old_mids))

            def moving_average(a, n=3) :
                ret = np.cumsum(a)
                ret[n:] = ret[n:] - ret[:-n]
                return ret[n - 1:] / n
            
            # sma = moving_average(old_mids, n=1)
            smas = moving_average(old_mids, n=self.ema_eval_true_days)
            # print(smas)
            # print(old_mids)
            
            for span in self.ema_spans:

                ema_preds = [sym_history[-(i + self.ema_eval_true_days + 1)]["emas"][span] for i in range(len(smas))]
                ema_preds = list(reversed(ema_preds))
                # print(ema_preds)

                # compare true SMA vs pred EMA
                diffs = abs(smas - ema_preds)
                score = np.mean(diffs)
                scores += [(score, span)]

            best_score, best_ema_span = min(scores)


                
            


        # add obj to history
        obj = {
            "best_buy": best_buy,
            "best_sell": best_sell,
            "mid": mid,
            "emas": new_emas,
            "best_ema": new_emas[best_ema_span],
            "best_ema_span": best_ema_span,
            'macd': macd,
            'highest': high_res
        }
        self.history[sym] += [obj]




class OrderManager:
    """
    This class provides an API to placing orders.
    Buy/sell orders can be queued by calling the 'place_buy_order/place_sell_order'
    These orders are recorded in the OrderManager object and will be returned at the end of the turn.
    """
    
    
    def __init__(self, symbols, position_limits, listings):
        self._buy_orders : Dict[Symbol, List[Order]] = {sym: [] for sym in symbols}
        self._sell_orders : Dict[Symbol, List[Order]] = {sym: [] for sym in symbols}
        self._position_limits = position_limits
        self._expected_change : Dict[Symbol, Position] = {sym: 0 for sym in symbols}
        self._listings: List[Listing] = listings


    def place_buy_order(self, symbol: Symbol, price: Price, quantity: int, is_take: bool):
        """ Queues a buy order
        If this order is a taking order, then it should update our expected position
        """
        
        if type(price) != int or type(quantity) != int:
            print("WARNING: BUY BAD ORDER TYPE", type(price), type(quantity))

        self._buy_orders[symbol] += [Order(symbol, price, quantity)]
        
        if is_take:
            self._update_expected_change(self._listings[symbol].product, +1 * quantity)

    def place_sell_order(self, symbol: Symbol, price: Price, quantity: int, is_take: bool):
        """ Queues a sell order
        """
        
        if type(price) != int or type(quantity) != int:
            print("WARNING: SELL BAD ORDER TYPE", type(price), type(quantity))

        self._sell_orders[symbol] += [Order(symbol, price, quantity)]

        if is_take:
            self._update_expected_change(self._listings[symbol].product, -1 * quantity)


    def get_rem_buy_size(self, state: TradingState, sym: Symbol) -> int:
        """ Returns additional capacity for trading a symbol, while taking into account current orders
        """
        return self.get_max_buy_size(state, sym) - self._get_cur_order_buy_size(sym)

    def get_rem_sell_size(self, state: TradingState, sym: Symbol) -> int:
        return self.get_max_sell_size(state, sym) - self._get_cur_order_sell_size(sym)

    def get_max_buy_size(self, state: TradingState, sym: Symbol) -> int:
        """ Returns maximum buy size for a specified symbol for this turn
        """
        prod = state.listings[sym].product
        limit = self._position_limits[prod]
        pos = state.position[prod]
        return limit - pos

    def get_max_sell_size(self, state: TradingState, sym: Symbol) -> int:
        """ Returns maximum sell size for a specified symbol for this turn
        """
        prod = state.listings[sym].product
        limit = self._position_limits[prod]
        pos = state.position[prod]
        return pos - (-limit)


    def _get_cur_order_buy_size(self, sym: Symbol) -> int:
        """ Returns cumulative size of buy orders for a specified symbol (private) 
        """
        
        orders = self._buy_orders[sym]
        return sum([ord.quantity for ord in orders])


    def _get_cur_order_sell_size(self, sym: Symbol) -> int:
        """ Returns cumulative size of sell orders for a specified symbol (private) 
        """
        orders = self._sell_orders[sym]
        return sum([ord.quantity for ord in orders])


    def _update_expected_change(self, prod: Product, change: int) -> None:
        self._expected_change[prod] += change


    def get_expected_pos(self, state: TradingState, prod: Product) -> int:
        """ Returns expected position of a product, given that we are 
        """

        return state.position[prod] + self._expected_change[prod]



    def postprocess_orders(self):
        """ Returns final orders
        - makes sell_orders have negative quantity (since the IMC engine wants it that way)
        - this method actually modifies the Order's directly, so it should only be called at the end of the turn once.
        """

        # iterate through sell orders
        for sym, orders in self._sell_orders.items():
            for order in orders:
                order.quantity = -1 * order.quantity
                
        return {sym: self._buy_orders[sym] + self._sell_orders[sym] for sym in self._buy_orders.keys()}





class Preprocess:
    """
    This class does all the preprocessing for the input game state
    """

    @classmethod
    def preprocess(cls, state: TradingState) -> None:
        """
        Call this method to perform all desired preprocessing
        """
        cls.fix_listings(state)
        cls.fix_position(state)
        cls.negate_sell_book_quantities(state)



    @classmethod
    def fix_listings(cls, state: TradingState):
        """
        The IMC engine gives each Listing as a Dict.
        This standardizes the input, so that we always see Listing instead of Dicts
        """

        # process listings dict
        if type(list(state.listings.values())[0]) == dict:
            new_listings = {}
            for sym, listing_dict in state.listings.items():
                new_listings[sym] = Listing(
                    symbol=listing_dict["symbol"], 
                    product=listing_dict["product"], 
                    denomination=listing_dict["denomination"], 
                )
            state.listings = new_listings


    @classmethod
    def fix_position(cls, state: TradingState):
        """
        The IMC engine does not include products that haven't been traded for state.position
        This standardizes the input, so that we always see each product as a key 
        """

        products = { listing.product for sym, listing in state.listings.items() }
        
        for prod in products:
            if prod not in state.position.keys():
                state.position[prod] = 0


    @classmethod
    def negate_sell_book_quantities(cls, state: TradingState):
        """
        The IMC engine's sell orders have negative quantity.
        We preprocess them to make them all positive
        """

        for sym, book in state.order_depths.items():
            # negate sell_quantity
            new_sell_orders = {}
            for sell_price, sell_quantity in book.sell_orders.items():
                assert sell_quantity < 0
                new_sell_orders[sell_price] = -1 * sell_quantity
            book.sell_orders = new_sell_orders