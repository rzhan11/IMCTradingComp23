import pandas as pd
import numpy as np
import json

from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order, Listing
from datamodel import Symbol, Product, Position


Price = int


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

        self.is_penny = True


    def turn_start(self, state: TradingState):
        self.turn += 1
        self._buy_orders : Dict[Symbol, List[Order]] = {sym: [] for sym in state.listings.keys()}
        self._sell_orders : Dict[Symbol, List[Order]] = {sym: [] for sym in state.listings.keys()}

        print("-"*50)
        print(f"Round {state.timestamp}, {self.turn}")
        print("-"*50)

        # print json, for analysis
        self.print_reconstruct(state)

        self.fix_listings(state)
        self.products = set([listing.product for sym, listing in state.listings.items()])
        self.fix_position(state)

        self.negate_sell_book_quantities(state)

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
        self.finish_turn += 1
        return my_orders

    def run_internal(self, state: TradingState):

        if self.is_close and state.timestamp >= self.max_timestamp - self.time_step * self.close_turns:
            self.close_positions(state)
            return

        # Iterate over all the keys (the available products) contained in the order depths
        for sym in state.order_depths.keys():

            prod: Product = state.listings[sym].product

            book = state.order_depths[sym]

            buys: List[Price, Position] = sorted(list(book.buy_orders.items()), reverse=True)
            sells: List[Price, Position] = sorted(list(book.sell_orders.items()), reverse=False)

            should_penny = False
            if self.is_penny:
                if len(buys) > 0 and len(sells) > 0:
                    spread = sells[0][0] - buys[0][0]
                    should_penny = spread >= 5
                else:
                    should_penny = True


            # match orders on buy-side
            for price, quantity in buys:
                if should_penny:
                    price += 1

                limit = self.get_rem_buy_size(state, sym)
                if limit > 0:
                    self.place_buy_order(Order(
                        symbol=sym,
                        price=price,
                        quantity=min(limit, quantity)
                    ))

            # match orders on sell-side
            for price, quantity in sells:
                if should_penny:
                    price -= 1

                limit = self.get_rem_sell_size(state, sym)
                if limit > 0:
                    self.place_sell_order(Order(
                        symbol=sym,
                        price=price,
                        quantity=min(limit, quantity)
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


    def get_rem_buy_size(self, state: TradingState, sym: Symbol) -> int:
        return self.get_max_buy_size(state, sym) - self.get_cur_order_buy_size(sym)

    def get_rem_sell_size(self, state: TradingState, sym: Symbol) -> int:
        return self.get_max_sell_size(state, sym) - self.get_cur_order_sell_size(sym)

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


    def get_cur_order_buy_size(self, sym: Symbol) -> int:
        orders = self._buy_orders[sym]
        return sum([ord.quantity for ord in orders])


    def get_cur_order_sell_size(self, sym: Symbol) -> int:
        orders = self._sell_orders[sym]
        return sum([ord.quantity for ord in orders])


    def print_reconstruct(self, state: TradingState):
        state.turn = self.turn
        state.finish_turn = self.finish_turn

        s = state.toJSON()

        print(f"__json_start\n{s}\n__json_end\n")
