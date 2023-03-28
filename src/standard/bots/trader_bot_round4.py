import pandas as pd
import numpy as np
import math
import json
import time
import traceback
import copy

from typing import Dict, List, Tuple, Any
from datamodel import OrderDepth, TradingState, Order, Listing, ProsperityEncoder
from datamodel import Symbol, Product, Position

from statistics import NormalDist

Price = int

PRINT_OURS = True
# PRINT_OURS = False
REDUCE_STR = True

MAX_POS = {
    "PEARLS": 20,
    "BANANAS": 20,
    "COCONUTS": 600,
    "PINA_COLADAS": 300,
    "BERRIES": 250,
    "DIVING_GEAR": 50,
    "BAGUETTE": 150,
    "DIP": 300,
    "UKULELE": 70,
    "PICNIC_BASKET": 70,
}

PARAMS = {
    # game parameters
    "max_timestamp": 1000000,
    "time_step": 100,

    # auto-close 
    "is_close": False,
    "close_turns": 30,

    # market-making params
    "is_penny": {
        "PEARLS": True,
        "BANANAS": True,
        "COCONUTS": True,
        "PINA_COLADAS": True,
        "BERRIES": True,
        "DIVING_GEAR": True,
        # round 4
        "BAGUETTE": True,
        "DIP": True,
        "UKULELE": True,
        "PICNIC_BASKET": True,
    },

    "take_flag": {
        "PEARLS": True,
        "BANANAS": True,
        "COCONUTS": False,
        "PINA_COLADAS": False,
        "BERRIES": False,
        "DIVING_GEAR": False,
        # round 4
        "BAGUETTE": False,
        "DIP": False,
        "UKULELE": False,
        "PICNIC_BASKET": False,
    },

    "make_flag": {
        "PEARLS": True,
        "BANANAS": True,
        "COCONUTS": False,
        "PINA_COLADAS": False,
        "BERRIES": False,
        "DIVING_GEAR": False,
        # round 4
        "BAGUETTE": False,
        "DIP": False,
        "UKULELE": False,
        "PICNIC_BASKET": False,
    },

    "pairs_model_weights": [1.5, 3000],

    "match_size": False,

    "min_take_edge": 0.25,

    # how many historical data points to use for analysis
    "DM.lookback": 100,

    # how many days used to compute true value
    "DM.ema_eval_true_days": 10,

    # how many days to test EMA against true
    "DM.ema_test_days": 100,

    "DM.ema_spans": [5, 21, 100],
    # "DM.ema_spans": [3, 10, 21, 100],
    # "DM.ema_spans": [3, 5, 10, 21, 30, 50, 100],
}

# WHALE_QUOTE_BOUNDS = {
#     # round 1
#     "BANANAS": {
#         "spread": (6, 11), # (6, 7)
#         "size": (13, 40), # (20, 40)
#     },
#     "PEARLS": {
#         "spread": (6, 11), # (10, 10)
#         "size": (15, 35), # (20, 30)
#     },
#     # round 2
#     "COCONUTS": {
#         "spread": (2, 4), # (3, 3)
#         "size": (80, 300), # (100, 250)
#     },
#     "PINA_COLADAS": {
#         "spread": (2, 5), # (3, 4)
#         "size": (40, 150), # (50, 120)
#     },
#     # round 3
#     'DIVING_GEAR':{
#         "spread": (2,5), # (3, 4)
#         "size": (8, 40), # (10, 30)
#     },
#     'BERRIES':{
#         "spread": (7, 10), # (8, 9)
#         "size": (35, 100), # (40, 80)
#     },
#     # round 4
#     "BAGUETTE": {
#         "spread": (0, 100), # (8, 9)
#         "size": (0, 150), # (40, 80)
#     },
#     "DIP": {
#         "spread": (0, 100), # (8, 9)
#         "size": (0, 100), # (40, 80)
#     },
#     'UKULELE':{
#         "spread": (0, 100), # (8, 9)
#         "size": (0, 100), # (40, 80)
#     },
#     'PICNIC_BASKET':{
#         "spread": (0, 100), # (8, 9)
#         "size": (0, 100), # (40, 80)
#     },
# }


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



def _get_desc():
    _description = f"""
    PRINT_OURS:
    {PRINT_OURS}

    PARAMS:
    {json.dumps(PARAMS, indent=2)}

    WHALE_QUOTE_BOUNDS:
    {json.dumps("n/a", indent=2)}

    REF_OPP_COSTS:
    {REF_OPP_COSTS}

    
    Description:
    dynamic EMA

    - DataManager lookback=100

    - dynamic EMA by measuring how good ema
        - compare 10, 21, 100

    - no closing at end of game
    """

    return _description



""" setup logging """


class Logger:
    def __init__(self) -> None:
        self.logs = ""

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]]) -> None:
        logs = self.logs
        if logs.endswith("\n"):
            logs = logs[:-1]

        if PRINT_OURS:
            _print(logs)
        else: # print jaspers
            _print(json.dumps({
                "state": state,
                "orders": orders,
                "logs": "",
            }, cls=ProsperityEncoder, separators=(",", ":"), sort_keys=True))

        self.state = None
        self.orders = {}
        self.logs = ""

logger = Logger()
_print = print
if PRINT_OURS:
    pass
else:
    print = logger.print




""" TRADER Class """

class Trader:

    def __init__(self, 
            player_id=None, 
            position_limits=None,
            is_main=False,
            ):
        
        # print description to help identify bot/params
        print(_get_desc())

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

        # parameters
        self.is_close = PARAMS["is_close"]
        self.close_turns = PARAMS["close_turns"]
        self.max_timestamp = PARAMS["max_timestamp"]
        self.time_step = PARAMS["time_step"]

        self.is_penny = PARAMS["is_penny"]
        self.match_size = PARAMS["match_size"]
        self.min_take_edge  = PARAMS["min_take_edge"]
        self.make_flag = PARAMS["make_flag"]
        self.take_flag = PARAMS["take_flag"]

        # pairs trading logic
        pairs_model_weights = PARAMS["pairs_model_weights"]
        self.pairs_model = np.poly1d(pairs_model_weights)

        # macd vars
        # self.macd_pos = 0


        ## gear vars
        self.has_gear_target = False
        self.gear_target = 0


    def turn_start(self, state: TradingState):
        # measure time
        self.wall_start_time = time.time()
        self.process_start_time = time.process_time()

        # print round header
        self.turn += 1

        print("-"*5)
        print(f"ROUND {state.timestamp}, {self.turn}")

        # used by self.reduce
        self.__reduce_symbols = list(state.order_depths.keys())


        # print raw json, for analysis
        self.record_game_state(state)

        # preprocess game state
        Preprocess.preprocess(state)

        # setup list of current products
        self.symbols = set([sym for sym in state.order_depths.keys()])
        self.products = set([state.listings[sym].product for sym in self.symbols])

        self.symbols = sorted(list(self.symbols))
        self.products = sorted(list(self.products))

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

        # _print("_"*100)

        state_json = json.loads(state.toJSON())

        orders = {}

    
        # turn setup
        self.turn_start(state)

        # main body
        self.run_internal(state)

        # cleanup / info reporting section
        orders = self.turn_end(state)
        # logger.flush(state_json, orders)

        # validate orders
        for sym, ods in orders.items():
            # print(sym, state.position[sym], ods)
            max_buy = -np.inf
            min_sell = np.inf
            total_buy_size = 0

            for ord in ods:
                if ord.quantity > 0:
                    max_buy = max(ord.price, max_buy)
                elif ord.quantity < 0:
                    min_sell = min(ord.price, min_sell)
                else:
                    print("WARNING: ORDER SIZE 0", ord)

            if max_buy >= min_sell:
                print("WARNING: SELF TRADE")

            if self.OM.get_rem_buy_size(state, sym) < 0:
                print("WARNING: BUY LIMIT")

            if self.OM.get_rem_sell_size(state, sym) < 0:
                print("WARNING: SELL LIMIT")


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
    




    def run_internal(self, state: TradingState):
        """ Main body of logic
        - analyzes current market
        - places new orders for this turn
        """

        OM = self.OM

        # close all positions if `is_close` flag is on, and we are at end of game
        # if self.is_close and state.timestamp >= self.max_timestamp - self.time_step * self.close_turns:
        #     self.close_positions(state)
        #     return

        # setup all_buys / all_sells
        self.all_buys = {}
        self.all_sells = {}

        for sym in state.order_depths.keys():
            book = state.order_depths[sym]

            buys: List[Tuple[Price, Position]] = sorted(list(book.buy_orders.items()), reverse=True)
            sells: List[Tuple[Price, Position]] = sorted(list(book.sell_orders.items()), reverse=False)

            self.all_buys[sym] = buys            
            self.all_sells[sym] = sells 

        # copy the original buy/sell books (we may change them on the fly)
        self.orig_all_buys = copy.deepcopy(self.all_buys)
        self.orig_all_sells = copy.deepcopy(self.all_sells)


        # Iterate over all the keys (the available products) contained in the order depths
        for sym in state.order_depths.keys():

            prod: Product = state.listings[sym].product

            # calc fair value
            fair_value = self.get_fair_value(sym)   
            mid_ema = self.get_ema_mid(sym)  
            
            if self.take_flag[sym]:
                self.take_logic(
                    state=state,
                    sym=sym,
                    fair_value=fair_value,
                )

            if self.make_flag[sym]:
                self.make_logic(
                    state=state,
                    sym=sym,
                    fair_value=fair_value,
                )
            
            # macd logic
            # if sym in ["DIVING_GEAR"]:
            #     self.macd_logic(
            #         state=state,
            #         sym=sym,
            #         fair_value=fair_value,
            #         ema=mid_ema,
            #     )

                    

        # round 2
        self.pairs_trading_logic(
            state=state, 
            main_sym="PINA_COLADAS",
            the_weights={
                "PINA_COLADAS": 1,
                "COCONUTS": -1.5,
            },
            the_bias=-3000,
            threshold=13.25 - 0.01,
            hedge_margin=5,
        )

        # round 4
        self.pairs_trading_logic(
            state=state, 
            main_sym="PICNIC_BASKET",
            the_weights={
                "PICNIC_BASKET": 1,
                "DIP": -4,
                "BAGUETTE": -2,
                "UKULELE": -1,
            },
            the_bias=-375,
            threshold=80 - 0.01,
            hedge_margin=5,
        )


        # round 3
        self.take_gear_logic(
            state=state, 
            sym="DIVING_GEAR",
            obs_name="DOLPHIN_SIGHTINGS",
        )

        # round 3
        self.take_berries_logic(
            state=state,
            sym="BERRIES",
            manual_adjust=5,
        )

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
    

    def get_best_buy_order(self, sym: Symbol):
        buys = self.all_buys[sym]
        if len(buys) > 0:
            return buys[0]
        else:
            return None, None

    def get_best_sell_order(self, sym: Symbol):
        sells = self.all_sells[sym]
        if len(sells) > 0:
            return sells[0]
        else:
            return None, None

    def place_market_buy(self, state: TradingState, sym: Symbol, max_quantity: int):
        price, quantity = self.get_best_sell_order(sym)

        # we are buying
        limit = self.OM.get_rem_buy_size(state, sym)
        if limit <= 0:
            return

        if price is not None:
            self.OM.place_buy_order(
                symbol=sym,
                price=price,
                quantity=min([limit, quantity, max_quantity]),
                is_take=True,
            )

    def place_market_sell(self, state: TradingState, sym: Symbol, max_quantity: int):
        price, quantity = self.get_best_buy_order(sym)

        # we are selling
        limit = self.OM.get_rem_sell_size(state, sym)
        if limit <= 0:
            return

        if price is not None:
            self.OM.place_sell_order(
                symbol=sym,
                price=price,
                quantity=min([limit, quantity, max_quantity]),
                is_take=True,
            )
                    

    def pairs_trading_logic(self, 
            state: TradingState,
            main_sym: Symbol,
            the_weights: Dict[Symbol, float],
            the_bias: float,
            threshold: float,
            hedge_margin: int,
            ):

        ### start of basic vars
        OM = self.OM


        syms = list(the_weights.keys())
        prods = [state.listings[sym].product for sym in syms]
        # main_sym should be in syms
        assert main_sym in syms

        # compute maximum contract position
        limits = [self._position_limits[prod] // abs(the_weights[prod]) for prod in prods]
        max_contract_pos = min(limits)
        # print("max_contract_pos", max_contract_pos, limits)


        def get_target_contract_pos(pred_error, cur_pair_pos):

            if abs(pred_error) > threshold:
                if pred_error > 0: # if A is overpriced, sell it
                    return -1 * max_contract_pos
                else: # if A is underpriced, buy it
                    return +1 * max_contract_pos
            else:
                # if we are not past the line, make sure our position is the correct sign
                if np.sign(cur_pair_pos) != np.sign(pred_error):
                    # if error is positive, and our position is negative
                    # we can keep our position
                    return cur_pair_pos
                else:
                    return 0
                
        
        def get_cur_contract_pos(weights):
            """ Returns 'cur_contract_pos', 'diff_a', 'diff_b'
            """

            cur_positions = {prod: OM.get_expected_pos(state, prod) for prod in prods}

            # use sign of first one
            contract_size = cur_positions[main_sym] / weights[main_sym]

            diffs = {}
            for prod in prods:
                target_pos = contract_size * weights[prod]
                cur_pos = cur_positions[prod]

                diffs[prod] = round(target_pos - cur_pos)

            return int(contract_size), diffs




        # place in its own method, to avoid accidental variable reuse
        def trade_contract(weights, bias):
            """  
            Check if buying the contract is profitable
            (if the value of the contract is <0, then buy)
            """

            # check if trade is doable
            contract_value = bias

            top_size = 2 * max_contract_pos
            top_prices = {}

            for sym in syms:
                if weights[sym] > 0: # we buy from sellers
                    book = self.all_sells[sym]
                    limit = OM.get_rem_buy_size(state, sym)
                else: # we sell to buyers
                    book = self.all_buys[sym]
                    limit = OM.get_rem_sell_size(state, sym)

                # if the book is empty here, give up
                if len(book) == 0:
                    return
                
                price, size = book[0]
                # print("price", sym, price)

                # record the book's top price
                top_prices[sym] = price

                # how much of the contract can we trade at book top
                top_size = min(top_size, min(limit, size) / abs(weights[sym]))

                # tally price
                contract_value += price * weights[sym]

            # if top_size <= 0:
            #     return

            # print("----")
            # print("ARB TAKE", main_sym, weights[main_sym])
            # print("----\n")

            # print("contract_value", contract_value)

            cur_contract_pos, _diffs = get_cur_contract_pos(weights)
            target_contract_pos = get_target_contract_pos(contract_value, cur_contract_pos)

            contract_diff = target_contract_pos - cur_contract_pos
            contract_diff_size = abs(contract_diff)

            # our trade size is limited by how much we want to trade
            # and the amt of trades avail at the book top
            contract_trade_size = min(top_size, contract_diff_size)

            # print("cur", cur_contract_pos)
            # print("targ", target_contract_pos)
            # print("diff", contract_diff, contract_diff_size)
            # print("c_tradesize", contract_trade_size, top_size)

            if contract_trade_size <= 0:
                # print("skipping")
                return


            # if we are supposed to buy this contract
            if contract_diff > 0:

                # print("I AM TAKING", "-"*50)

                # loop through each symbol and place the order
                for sym in syms:
                    # trade_size is signed
                    trade_size = int(round(contract_trade_size * weights[sym]))
                    # print("TAKING", sym, trade_size, top_prices[sym])

                    # buy
                    if trade_size > 0:
                        trade_func = OM.place_buy_order
                    else:
                        trade_func = OM.place_sell_order

                    trade_func(
                        symbol=sym,
                        price=top_prices[sym],
                        quantity=abs(trade_size),
                        is_take=True,
                    )

        def hedge(weights):
            ## hedge
            # if we have Q shares of stock A
            # we should have -Q * model_m shares of stock B to be hedged

            # diff_A is how much A we need to trade to be hedged, same for diff_B
            cur_contract_pos, diffs = get_cur_contract_pos(weights)

            for sym in syms:
                diff = diffs[sym]
                trade_size = abs(diff)
                if trade_size > hedge_margin:
                    if diff > 0: # we need to buy
                        # print("hedging buy", sym, diff)
                        trade_func = self.place_market_buy
                    else: # we need to sell
                        # print("hedging sell", sym, diff)
                        trade_func = self.place_market_sell
                    
                    # place the trade
                    trade_func(
                        state=state,
                        sym=sym,
                        max_quantity=trade_size, # use abs value
                    )
                    
                        
        # try to buy the contract
        trade_contract(
            weights=the_weights,
            bias=the_bias,
        )
        
        # try to sell the contract
        trade_contract(
            weights={k: -1 * v for k, v in the_weights.items()}, 
            bias=-1 * the_bias,
        )

        # hedge our position
        hedge(the_weights)
        

    def macd_logic(self, 
            state: TradingState,
            sym: Symbol, 
            fair_value: float,
            ema: float,
            ):
        
        # print("macd_logic", sym)
        
        buys, sells = self.all_buys[sym], self.all_sells[sym]
        OM = self.OM
        prod = state.listings[sym].product

        max_position = self._position_limits[prod]
        
        # get mid price, margin, and macd
        mid_price = self.DM.history[sym][-1]['mid']
        margin = mid_price * 0.005 / 10
        macd = self.DM.history[sym][-1]['macd']

        cur_pos = state.position[prod]

        if abs(macd) > margin:
            if macd > 0:
                self.take_to_target_pos(state=state, sym=sym, target_pos=+1 * max_position)
            else:
                self.take_to_target_pos(state=state, sym=sym, target_pos=-1 * max_position)
        else:
            # macd and cur_pos should be same sign
            # if they are different signs, flatten our position
            if np.sign(macd) != np.sign(cur_pos):
                self.take_to_target_pos(state=state, sym=sym, target_pos=0)


    def take_logic(self, 
            state: TradingState,
            sym: Symbol, 
            fair_value: float,
            custom_opp_cost: Dict[Position, float]=None,
            ):
        
        buys, sells = self.all_buys[sym], self.all_sells[sym]
        OM = self.OM
        prod = state.listings[sym].product

        # setup opp costs
        OPP_COST = REF_OPP_COSTS[prod]
        # use custom_opp_cost sometimes
        if custom_opp_cost is not None:
            OPP_COST = custom_opp_cost


        # take orders on buy_side (we sell to existing buy orders)
        for index, (price, quantity) in enumerate(buys):
            cur_pos = OM.get_expected_pos(state, prod)
            limit = OM.get_rem_sell_size(state, sym)

            max_take_size = min(limit, quantity)

            scores = []
            for take_size in range(0, max_take_size + 1):
                # we are selling
                new_pos = cur_pos - take_size

                opp_change = OPP_COST[new_pos] - OPP_COST[cur_pos]
                edge = price - fair_value
                adj_rtn = edge * take_size + opp_change

                scores += [(adj_rtn, take_size)]

            # get the size with the optimal expected adjusted return
            if len(scores) > 0:
                adj_rtn, take_size = max(scores)
                if adj_rtn >= 0 and take_size > 0:
                    OM.place_sell_order(
                        symbol=sym,
                        price=price,
                        quantity=take_size,
                        is_take=True,
                    )

                # delete it
                top_buy_price, top_buy_size = buys[index]
                buys[index] = (top_buy_price, top_buy_size - take_size)

        # remove extraneous buys
        self.all_buys[sym] = [(p, q) for p, q in buys if q != 0]


        # take orders on sell_side (we buy from existing sellers)
        for index, (price, quantity) in enumerate(sells):
            cur_pos = OM.get_expected_pos(state, prod)
            limit = OM.get_rem_buy_size(state, sym)

            max_take_size = min(limit, quantity)

            scores = []
            for take_size in range(0, max_take_size + 1):
                # we are buying
                new_pos = cur_pos + take_size

                opp_change = OPP_COST[new_pos] - OPP_COST[cur_pos]
                edge = fair_value - price
                adj_rtn = edge * take_size + opp_change

                scores += [(adj_rtn, take_size)]

            # get the size with the optimal expected adjusted return
            if len(scores) > 0:
                adj_rtn, take_size = max(scores)
                if adj_rtn >= 0 and take_size > 0:
                    OM.place_buy_order(
                        symbol=sym,
                        price=price,
                        quantity=take_size,
                        is_take=True,
                    )

                # delete it
                top_sell_price, top_sell_size = sells[index]
                sells[index] = (top_sell_price, top_sell_size - take_size)

        # remove extraneous sells
        self.all_sells[sym] = [(p, q) for p, q in sells if q != 0]


    def take_gear_logic(self,
            state: TradingState,
            sym: Symbol,
            obs_name: str,
            ):
        
        """ start of var setup """
    
        buys, sells = self.all_buys[sym], self.all_sells[sym]
        OM = self.OM
        prod = state.listings[sym].product

        sym_history = self.DM.history[sym]
        obs_history = self.DM.history[obs_name]

        max_position_limit = self._position_limits[sym]
        """ end of var setup """

        # if we don't have a gear target, don't try to change our position
        if not self.has_gear_target:
            self.gear_target = state.position[sym]

        # print("gear_logic", len(sym_history), len(obs_history))

        ## skip if no history
        min_history_len = 2
        if len(sym_history) < min_history_len or len(obs_history) < min_history_len:
            return
        
        
        # get historical dol levels
        cur_obs = obs_history[-1]
        past_obs = obs_history[-2]

        # sanity check our historical data
        if cur_obs["time"] != state.timestamp or past_obs["time"] != state.timestamp - self.time_step:
            print("WARNING: take_gear_logic bad history obs")
            print("cur", cur_obs)
            print("prev", past_obs)
            return


        cur_dol = cur_obs["mid"]
        past_dol = past_obs["mid"]
        

        dol_change = cur_dol - past_dol
        # print("dols", cur_dol, past_dol, dol_change)

        # if theres been at least 2 dol change in either direction, trade that direction
        if abs(dol_change) > 1:
            signal = np.sign(dol_change)

            self.has_gear_target = True
            self.gear_target = signal * max_position_limit
            # print("BIG DOL CHANGE", dol_change, cur_dol, past_dol, self.gear_target)

        # print("gear target", self.gear_target)
        self.take_to_target_pos(state, sym, target_pos=self.gear_target)


    def take_berries_logic(self,
            state: TradingState,
            sym: Symbol,
            manual_adjust: float,
            ):
        
        """ start of var setup """
    
        buys, sells = self.all_buys[sym], self.all_sells[sym]
        OM = self.OM
        prod = state.listings[sym].product

        sym_history = self.DM.history[sym]

        max_position_limit = self._position_limits[sym]
        """ end of var setup """

        cycle_time = (state.timestamp % 1000000) / 1000000
        fair_value = self.get_fair_value(sym)        
        limit = max_position_limit

        print("cycle_time", cycle_time)

        # timing constants
        base_trade_rate = 1.6 / 2
        gain_end = 10000 * 1/2
        loss_end = 10000 * 1

        ## function for expected price
        exp_params = [ 3.87997198e+03,  1.52237911e+00,  9.15550042e-04, -8.53005765e-01]
        def _get_expected_rtn(a, b, c, d, s, r, t1, t2, earn_sign):
            s = s - t1 * r # adjust initial position

            midpoint = gain_end

            # s = initial pos
            # r = change in pos per turn
            def int_fun(t):
                return b * np.exp(c * t + d) * (r * (c * t - 1) + c * s) / c
            
            def int_fun_neg(t):
                return b * np.exp(c * -(t - 2 * midpoint) + d) * (r * (c * t + 1) + c * s) / c
            
            if earn_sign > 0:
                return int_fun(t2) - int_fun(t1)
            else:
                return int_fun_neg(t2) - int_fun_neg(t1)
        
        # the main function used to calculate opportunity cost
        opp_cost_fn = lambda s, r, t1, t2, earn_sign : manual_adjust * _get_expected_rtn(*exp_params, s, r, t1, t2, earn_sign)

        def get_custom_opp_cost():
            # remaining gain time (rem_gain = rem gain per contract)

            cur_day = cycle_time * 10000

            opp_costs = {i: 0 for i in range(-limit, limit + 1)}

            def modify_opp_cost(prd_end, earn_sign):
                if cur_day >= prd_end:
                    return
                
                trade_rate = np.sign(earn_sign) * base_trade_rate
                target_pos = np.sign(earn_sign) * limit                

                rem_gain_days = prd_end - cur_day

                for start_pos in range(-limit, limit + 1):
                    pos_miss = target_pos - start_pos

                    # changing days are # of days during gain period, where we increase our pos
                    num_change_days = min(rem_gain_days, pos_miss / trade_rate)

                    # number of days we are at the target pos
                    max_pos_day = cur_day + num_change_days

                    # period of p(x) changing
                    ## from cur_day to max_pos_day
                    value1 = opp_cost_fn(start_pos, trade_rate, cur_day, max_pos_day, earn_sign)

                    # period of p(x) = target_pos
                    ## from max_pos_day to prd_end
                    value2 = opp_cost_fn(target_pos, 0, max_pos_day, prd_end, earn_sign)

                    # final value
                    opp_costs[start_pos] += value1 + value2

                    # if abs(start_pos) == limit:
                    #     print(f"start_pos {start_pos}:", opp_costs[start_pos])
                    #     print("ex_pos", exp_pos, exp_pos_miss)
                    #     print("num_chg_days", num_change_days, avg_pos)
                    #     print("maxed_days", max_pos_day, num_max_days)

            modify_opp_cost(
                prd_end=gain_end,
                earn_sign = 1,
            )

            if cur_day >= gain_end:
                modify_opp_cost(
                    prd_end=loss_end,
                    earn_sign=-1,
                )

            opp_costs = {k: round(v, 1) for k, v in opp_costs.items()}

            return opp_costs
            
        # dict
        base_opp_cost = REF_OPP_COSTS[sym]
        custom_opp_cost = get_custom_opp_cost()
        used_opp_cost = {i: base_opp_cost[i] + custom_opp_cost[i] for i in range(-limit, limit + 1)}



        def trade_standard():

            # market make
            self.take_logic(
                state=state,
                sym=sym,
                fair_value=fair_value,
                custom_opp_cost=used_opp_cost,
            )
            self.make_logic(
                state=state,
                sym=sym,
                fair_value=fair_value,
                custom_opp_cost=used_opp_cost,
            )

        trade_standard()

    def take_to_target_pos(self, state: TradingState, sym: Symbol, target_pos: int):

        # target pos
        cur_pos = state.position[sym]
        pos_diff = target_pos - cur_pos
        trade_size = abs(pos_diff)

        if pos_diff > 0:
            self.place_market_buy(
                state=state, 
                sym=sym, 
                max_quantity=trade_size
            )
        elif pos_diff < 0:
            self.place_market_sell(
                state=state, 
                sym=sym, 
                max_quantity=trade_size
            )
                

    def make_logic(self, 
            state: TradingState,
            sym: Symbol, 
            fair_value: float,
            custom_opp_cost: Dict[Position, float]=None,
            ):
        
        buys, sells = self.all_buys[sym], self.all_sells[sym]
        OM = self.OM
        prod = state.listings[sym].product


        should_penny = False
        if self.is_penny[sym]:
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
                    OM.place_sell_order(
                        symbol=sym,
                        price=price,
                        quantity=sell_size,
                        is_take=False,
                    )
        




    def get_large_quote_mid(self, sym):
        """ Checks if we should calculate the fair value using the mid of the order book
        - Gets the buy and sell orders with the maximum size
        - Checks if the maximum size is >= 15 for both buy/sell, and checks if the width is from 6 to 8 
        - If yes, return prices of max size buy/sell from order book, else return None
        """



        buys, sells = self.orig_all_buys[sym], self.orig_all_sells[sym]
        
        buy_price, buy_size = max(buys, key=lambda x:x[1])
        sell_price, sell_size = max(sells, key=lambda x:x[1])

        spread = sell_price - buy_price
        
        # quote_bounds = WHALE_QUOTE_BOUNDS[sym]
        # spread_lb, spread_ub = quote_bounds["spread"]
        # size_lb, size_ub = quote_bounds["size"]
        # should_use = \
        #     spread_lb <= spread <= spread_ub and \
        #     size_lb <= buy_size <= size_ub and \
        #     size_lb <= sell_size <= size_ub
        ### always use whale quote bounds
        should_use = True

        return (buy_price + sell_price) / 2, should_use



    def close_positions(self, state: TradingState):
        """ Closes out our position at the end of the game
        - was previously used since IMC's engine uses weird fair values
        """
        OM = self.OM

        for prod, pos in state.position.items():
            if pos < 0:
                OM.place_buy_order(symbol=prod, price=1e9, quantity=1, is_take=False)
            elif pos > 0:
                OM.place_sell_order(symbol=prod, price=0, quantity=1, is_take=False)



    def record_game_state(self, state: TradingState):
        """
        Prints out the state of the game when received
        """

        state.turn = self.turn
        state.finish_turn = self.finish_turn

        s = state.toJSON()
        s = self.reduce_str(s)
        
        print(f"__g_s{s}__g_e")

        # print("__g_s")
        # num_iters = int(np.ceil(len(s) / 100))
        # for i in range(num_iters):
        #     print(s[i*100:(i+1)*100])
        # print("__g_e")


    def record_turn_end(self, state: TradingState):
        """ Prints out end of turn info, including:
        - orders we sent this turn
        """

        OM = self.OM

        my_orders = {sym: { "buy_orders": OM._buy_orders[sym], "sell_orders": OM._sell_orders[sym] } for sym in self.symbols}

        emas = { sym: self.DM.history[sym][-1]["emas"] for sym in self.symbols }
        best_emas = { sym: self.DM.history[sym][-1]["best_ema"] for sym in self.symbols }
        best_ema_spans = { sym: self.DM.history[sym][-1]["best_ema_span"] for sym in self.symbols }

        # get large quote mid data
        quote_mids_data = { sym: self.get_large_quote_mid(sym) for sym in self.symbols}
        quote_mids = {sym: mid for sym, (mid, use) in quote_mids_data.items() }
        use_quote_mids = {sym: use for sym, (mid, use) in quote_mids_data.items() }

        fair_values = { sym: self.get_fair_value(sym) for sym in self.symbols}

        obj = {
            # timing
            "time": state.timestamp,
            "wall_time": round(time.time() - self.wall_start_time, 4),
            "process_time": round(time.process_time() - self.process_start_time, 4),

            # my orders
            "my_orders": my_orders,

            ### fair values ###

            # # ema
            # "emas": emas,
            # "best_emas": best_emas,
            # "best_ema_spans": best_ema_spans,

            # # large quote mid
            # "quote_mids": quote_mids,
            # "use_quote_mids": use_quote_mids,

            # fair value
            "fair_values": fair_values,

            # history length
            "history_len": len(self.DM.history["BANANAS"]),
        }


        
        # convert obj to 
        s = json.dumps(obj, default=lambda o: o.__dict__, sort_keys=True, separators=(',', ":"))
        s = self.reduce_str(s)

        print(f"__t_s\n{s}\n__t_e")



    def reduce_str(self, s):

        if not REDUCE_STR:
            return s

        unused_chars = "!@$^?~`" # add "%" if needed
        def get_unused_char(i):
            x = i // 10
            y = i % 10
            return unused_chars[x] + str(y)

        words = self.__reduce_symbols + [
            "buy_orders", "sell_orders", 
            "price", "quantity", 
            "symbol", "product", "denomination",
            "buyer", "seller", "timestamp", "SUBMISSION",
            "DOLPHIN_SIGHTINGS",
            "own_trades", "position", "observations", "market_trades", "turn", 
        ]
        words = [f'"{w}"' for w in words]
        words.sort(key=lambda x:(len(x), x), reverse=True)

        convert_list = [ (sym, get_unused_char(i)) for i, sym in enumerate(words) ]
        
        for k, v in convert_list:
            s = s.replace(k, v)

        return s


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

        self.history = {}


    def add_history(self, state: TradingState, symbols: List[Symbol], products: List[Product]):
        """
        Stores state
        - should be called after preprocessing / recording of game state
        """
        self.symbols = symbols
        self.products = products

        for sym in symbols:
            self.add_history_sym(state, sym)

        for obs_name in ["DOLPHIN_SIGHTINGS"]:
            self.add_history_obs(state, obs_name)


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

        # get previous emas
        if len(sym_history) == 0:
            old_emas = {span: mid for span in self.ema_spans}
        else:
            old_emas = sym_history[-1]["emas"]

        # calculate ema for each span
        new_emas = {}
        for span in self.ema_spans:
            # calculate ema
            alpha = 2 / (span + 1)
            new_ema = mid * alpha + (1 - alpha) * old_emas[span]
            # round for pretty print
            new_emas[span] = round(new_ema, 2)

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

        # macd calculations
        fast_ema = new_emas[21]
        slow_ema = new_emas[100]
        macd = fast_ema - slow_ema

        # add obj to history
        obj = {
            "time": state.timestamp,
            "best_buy": best_buy,
            "best_sell": best_sell,
            "mid": mid,
            "emas": new_emas,
            "best_ema": new_emas[best_ema_span],
            "best_ema_span": best_ema_span,
            "macd": macd,
        }
        self.history[sym] += [obj]


    def add_history_obs(self, state: TradingState, obs_name: str):
        # add sym to history if not present
        if obs_name not in self.history:
            self.history[obs_name] = []

        obs_history = self.history[obs_name]
        mid = state.observations[obs_name]

        obj = {
            "time": state.timestamp,
            "mid": mid,
        }

        obs_history += [obj]


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