import pandas as pd
import numpy as np
import json

from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order, Symbol


MAX_POS = {
    "PEARLS": 20,
    "BANANAS": 20,
}


class Trader:

    def __init__(self, 
            player_id=None, 
            position_limits=None):

        self.turn = -1
        self.player_id = player_id
        self.position_limits = position_limits

    def turn_start(self, state):
        self.turn += 1
        self._buy_orders = {sym: [] for sym in state.listings.keys()}
        self._sell_orders = {sym: [] for sym in state.listings.keys()}

        print("-"*50)
        print(f"Round {state.timestamp}, {self.turn}")
        print("-"*50)

        # print json, for analysis
        self.print_reconstruct(state)


    def run(self, state: TradingState) -> Dict[Symbol, List[Order]]:
        """
        Only method required. It takes all buy and sell orders for all symbols as an input,
        and outputs a list of orders to be sent
        """
        # Initialize the method output dict as an empty dict
        self.turn_start(state)


        # Iterate over all the keys (the available products) contained in the order depths
        for sym in state.order_depths.keys():


            book = state.order_depths[sym]

            buys = book.buy_orders
            sells = book.sell_orders

            # calc buy prices
            if len(buys) > 0:
                best_buy = max(buys.keys())
                buy_size = buys[best_buy]
            else:
                best_buy, buy_size = None, None

            # calc sell prices
            if len(sells) > 0:
                best_sell = max(sells.keys())
                sell_size = sells[best_sell]
            else:
                best_sell, sell_size = None, None

            # place orders
            if best_buy is not None:
                self.place_buy_order(Order(symbol=sym, price=best_buy, quantity=1))

            if best_sell is not None:
                self.place_sell_order(Order(symbol=sym, price=best_sell, quantity=1))

        my_orders = self.get_orders()
        print("my orders", my_orders)
        return my_orders

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




    def print_reconstruct(self, state):
        s = state.toJSON()

        print(f"__json_start\n{s}\n_json_end\n")
