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

    def __init__(self):
        self.turn = -1

        pass


    def run(self, state: TradingState) -> Dict[Symbol, List[Order]]:
        """
        Only method required. It takes all buy and sell orders for all symbols as an input,
        and outputs a list of orders to be sent
        """
        # Initialize the method output dict as an empty dict

        self.turn += 1
        self._orders = {sym: [] for sym in state.listings.keys()}

        print("-"*50)
        print(f"Round {state.timestamp}, {self.turn}")
        print("-"*50)


        # print json, for analysis
        self.print_reconstruct(state)


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
                self.place_order(Order(symbol=sym, price=best_buy, quantity=buy_size))

            if best_sell is not None:
                self.place_order(Order(symbol=sym, price=best_sell, quantity=sell_size))


        return self._orders

    def place_order(self, order: Order):
        self._orders[order.symbol] += [order]





    def print_reconstruct(self, state):
        s = state.toJSON()

        print(f"__json_start\n{s}\n_json_end\n")
