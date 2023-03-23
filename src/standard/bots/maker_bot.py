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
            position_limits=None,
            is_main=False,
            fair_obj=None,
            price_df=None):

        self.turn = -1
        self._player_id = player_id
        self._is_main = is_main
        self._position_limits = position_limits
        # make this the median price
        self._fair_obj = fair_obj
        self.price_df = price_df

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
        print("MAKER BOT ORDERS at time ", state.timestamp, ":", my_orders)
        return my_orders

    def run_internal(self, state):

        time = state.timestamp
        fairs = self._fair_obj.value

        for prod, _ in fairs.items():
            if prod == "SEASHELLS":
                continue

            for num in range(1, 4):
                time_state = self.price_df[(self.price_df["time"] == time)
                    & (self.price_df["symbol"] == prod)]
                
                buy_price = time_state[f"buy_price_{num}"].values[-1]
                buy_size = time_state[f"buy_volume_{num}"].values[-1]
                if (not np.isnan(buy_price)) | (not np.isnan(buy_size)):
                    self.make_market(prod, "buy", int(buy_price), int(buy_size))

                sell_price = time_state[f"sell_price_{num}"].values[-1]
                sell_size = time_state[f"sell_volume_{num}"].values[-1]
                if (not np.isnan(sell_price)) | (not np.isnan(sell_size)):
                    self.make_market(prod, "sell", int(sell_price), int(sell_size))



    def make_market(self, symbol : Symbol, action : str, price : int, size : int):
        if (action == "buy"):
            self.place_buy_order(Order(
                symbol=symbol,
                price=price,
                quantity=size,
            ))
            # print("MAKER BOT places buy order:", symbol, "price:", price, "size:", size)

        if (action == "sell"):
            self.place_sell_order(Order(
                symbol=symbol,
                price=price,
                quantity=size,
            ))
            # print("MAKER BOT places sell order:", symbol, "price:", price, "size:", size)



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