import pandas as pd
import numpy as np
import json

from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order, Symbol, Listing, Product


MAX_POS = {
    "PEARLS": 20,
    "BANANAS": 20,
}


class Trader:

    def __init__(self, 
            player_id=None, 
            position_limits=None):

        self._player_id = player_id
        self._position_limits = position_limits
        if self._position_limits is None:
            self._position_limits = MAX_POS

        self.turn = -1
        self.finish_turn = -1

        # number of turns used to close
        self.is_close = True
        self.close_turns = 30
        self.max_timestamp = 200000
        self.time_step = 100


    def turn_start(self, state: TradingState):
        self.turn += 1
        self._buy_orders = {sym: [] for sym in state.listings.keys()}
        self._sell_orders = {sym: [] for sym in state.listings.keys()}

        print("-"*50)
        print(f"Round {state.timestamp}, {self.turn}")
        print("-"*50)

        # print json, for analysis
        self.print_reconstruct(state)

        self.fix_listings(state)
        self.products = set([listing.product for sym, listing in state.listings.items()])
        self.fix_position(state)


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
        self.finish_turn += 1
        return my_orders

    def fix_position(self, state: TradingState):
        """
        The IMC engine does not include products that haven't been traded for state.position
        This standardizes the input, so that we always see each product as a key 
        """

        for prod in self.products:
            if prod not in state.position.keys():
                state.position[prod] = 0


    def fix_listings(self, state: TradingState):
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

    def run_internal(self, state: TradingState):

        if self.is_close and state.timestamp >= self.max_timestamp - self.time_step * self.close_turns:
            self.close_positions(state)
            return

        # Iterate over all the keys (the available products) contained in the order depths
        for sym in state.order_depths.keys():

            prod = state.listings[sym].product

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
                best_sell = min(sells.keys())
                sell_size = sells[best_sell]
            else:
                best_sell, sell_size = None, None

            # place orders
            if best_buy is not None:
                max_size = self.get_max_buy_size(state, sym)
                if max_size > 0:
                    self.place_buy_order(Order(
                        symbol=sym, 
                        price=best_buy, 
                        quantity=max_size
                    ))

            if best_sell is not None:
                max_size = self.get_max_sell_size(state, sym)
                if max_size > 0:
                    self.place_sell_order(Order(
                        symbol=sym, 
                        price=best_sell, 
                        quantity=max_size
                    ))




    def close_positions(self, state: TradingState):

        for prod, pos in state.position.items():
            if pos < 0:
                self.place_buy_order(Order(symbol=prod, price=1e9, quantity=1))
            elif pos > 0:
                self.place_sell_order(Order(symbol=prod, price=0, quantity=1))




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


    def get_max_buy_size(self, state: TradingState, sym: Symbol) -> int:
        prod = state.listings[sym].product
        limit = self._position_limits[prod]
        pos = state.position[prod]
        return limit - pos

    def get_max_sell_size(self, state: TradingState, sym: Symbol) -> int:
        prod = state.listings[sym].product
        limit = self._position_limits[prod]
        pos = state.position[prod]
        return pos - (-limit)



    def print_reconstruct(self, state: TradingState):
        state.turn = self.turn
        state.finish_turn = self.finish_turn

        s = state.toJSON()

        print(f"__json_start\n{s}\n__json_end\n")
