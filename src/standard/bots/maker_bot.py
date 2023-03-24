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


        # preprocess price_df
        # maps time to list of rows
        # self.grouped_df = price_df.groupby("time")



    def turn_start(self, state):
        self.turn += 1
        self._buy_orders = {sym: [] for sym in state.listings.keys()}
        self._sell_orders = {sym: [] for sym in state.listings.keys()}

        self.symbols = set([listing.symbol for sym, listing in state.listings.items()])

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
        print("MAKER BOT ORDERS at time ", state.timestamp, ":", my_orders)
        return my_orders

    def run_internal(self, state):

        time = state.timestamp

        # this df only contains rows for our time
        cur_df = self.price_df
        cur_df = cur_df[cur_df["time"] == time]
        # cur_df = self.grouped_df.get_group(time)

        for sym in self.symbols:

            # grab first row
            time_state = cur_df[cur_df["symbol"] == sym].iloc[0]

            for num in range(1, 4):
                
                # place buys
                buy_price = time_state[f"buy_price_{num}"]
                buy_size = time_state[f"buy_volume_{num}"]
                if (not np.isnan(buy_price)) and (not np.isnan(buy_size)):
                    self.place_buy_order(Order(
                        symbol=sym,
                        price=int(buy_price),
                        quantity=int(buy_size),
                    ))

                # place sells
                sell_price = time_state[f"sell_price_{num}"]
                sell_size = time_state[f"sell_volume_{num}"]
                if (not np.isnan(sell_price)) and (not np.isnan(sell_size)):
                    self.place_sell_order(Order(
                        symbol=sym,
                        price=int(sell_price),
                        quantity=int(sell_size),
                    ))



    def make_market(self, symbol : Symbol, action : str, price : int, size : int):
        """ not used currently """


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