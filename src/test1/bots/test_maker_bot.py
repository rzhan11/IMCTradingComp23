import pandas as pd
import numpy as np
import json
import random

random.seed(1)

from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order, Symbol


class MakerBot:

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

        self.make_market("PEARLS", 10000, 10, 2)
        
        self.make_market("BANANAS", 5000, 5, 2)




    def make_market(self, symbol : Symbol, fair : int, spread : int, size : int):
        
        self.place_buy_order(Order(
            symbol=symbol,
            price=fair - spread,
            quantity=size,
        ))

        self.place_sell_order(Order(
            symbol=symbol,
            price=fair + spread,
            quantity=size,
        ))




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


    def _unit_test(self, state):
        pass