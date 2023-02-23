import pandas as pd
import numpy as np
import json
import random

random.seed(1)

from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order, Symbol


class TakerBot:

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
        
        is_buy = random.random() < 0.5

        if is_buy:
            book = state.order_depths[symbol].sell_orders
            is_reverse = False
            place_order_func = self.place_buy_order
        else:
            book = state.order_depths[symbol].buy_orders
            is_reverse = True
            place_order_func = self.place_sell_order


        if len(book) > 0:
            # find best price
            sorts = sorted(list(book.items()), reverse=is_reverse)
            best_order = sorts[0]

            # place order
            place_order_func(Order(
                symbol=symbol,
                price=best_order[0],
                quantity=best_order[1],
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