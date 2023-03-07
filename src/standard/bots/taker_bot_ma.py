import pandas as pd
import numpy as np
import json
import random

random.seed(1)

from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order, Symbol

HISTORY = {
    "MID" : {"PEARLS": [],
            "BANANAS": [],
            },
    "VOL" : {"PEARLS": [],
            "BANANAS": [],
            },

}

class TakerBot_ma:

    def __init__(self, 
            player_id=None, 
            position_limits=None,
            fair_obj=None):

        self.turn = -1
        self._player_id = player_id
        self._position_limits = position_limits
        self._fair_obj = fair_obj

    def turn_start(self, state):
        self.turn += 1
        self._buy_orders = {sym: [] for sym in state.listings.keys()}
        self._sell_orders = {sym: [] for sym in state.listings.keys()}

        self.negate_sell_book_quantities(state)

    def negate_sell_book_quantities(self, state: TradingState):
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


    def run(self, state: TradingState) -> Dict[Symbol, List[Order]]:
        """
        Only method required. It takes all buy and sell orders for all symbols as an input,
        and outputs a list of orders to be sent
        """
        # Initialize the method output dict as an empty dict
        self.turn_start(state)

        self.run_internal(state)



        my_orders = self.get_orders()
        print("My orders", my_orders)
        return my_orders

    def run_internal(self, state):

        self.take_trade(state, "PEARLS")
        self.take_trade(state, "BANANAS")
        


    def take_trade(self, state: TradingState, symbol: Symbol):

        for sym in state.order_depths.keys():

            prod = state.listings[sym].product

            book = state.order_depths[sym]

            buys: List[Price, Position] = sorted(list(book.buy_orders.items()), reverse=True)
            sells: List[Price, Position] = sorted(list(book.sell_orders.items()), reverse=False)
            if len(buys) > 0 and len(sells) > 0:
                HISTORY['MID'][sym].append((buys[0][0]+sells[0][0])/2) #update mid price 
                if len ( HISTORY['MID'][sym])==1:
                    HISTORY['VOL'][sym]=0  # initialize volatility
                else:
                    logreturn=np.log(HISTORY['MID'][sym]/HISTORY['MID'][sym].shift())
                    HISTORY['VOL'][sym]=logreturn.std()*(len(HISTORY['MID'][sym])**.5) # period  vol

            volatility_cap = 0.05* HISTORY['VOL'][sym]
            lookback = 30
        
            signal=0 # 0 for no action, -1 for sell ,1 for buy
            if self.turn>= lookback: 
                ma=self.calc_ma( list(reversed(HISTORY['MID'][sym])),lookback)
                curr_best_bid = buys[0][0]
                curr_best_ask = sells[0][0]
                if curr_best_bid > (1 + volatility_cap) * ma:
                    #above threshold of MA, sell
                    signal= -1
                if curr_best_ask < (1 - volatility_cap) * ma:
                    #below threshold of MA, buy
                    signal = 1

            if signal >0:
                book = state.order_depths[sym].sell_orders
                is_reverse = False
                place_order_func = self.place_buy_order
            if signal <0:
                book = state.order_depths[sym].buy_orders
                is_reverse = True
                place_order_func = self.place_sell_order


            if len(book) > 0:
            # place order
                if signal < 0:
                    place_order_func(Order(
                    symbol=sym,
                    price=buys[1][0], #willing to take a slippage of up to 2 best price
                    quantity=buys[0][0], # trade best price's volume 
                    ))
                if signal > 0: 
                    place_order_func(Order(
                    symbol=sym,
                    price=sells[1][0],
                    quantity=sells[0][0],
                    )   )








    def calc_ma(self, lst, x): 
        return np.average( lst[:x])
    def place_buy_order(self, order: Order):
        self._buy_orders[order.symbol] += [order]

    def place_sell_order(self, order: Order):
        self._sell_orders[order.symbol] += [order]

    def get_orders(self):
        # iterate through sell orders
        for sym, orders in self._sell_orders.items():
            for order in orders:
                order.quantity = -1 * order.quantity

        return {sym: self._buy_orders[sym] + self._sell_orders[sym] for sym in self._buy_orders.keys()}