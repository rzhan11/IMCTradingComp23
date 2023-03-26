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
            is_main=False,
            fair_obj=None,
            trade_df=None):

        self.turn = -1
        self._player_id = player_id
        self._is_main = is_main
        self._position_limits = position_limits
        self._fair_obj = fair_obj
        self.trade_df = trade_df

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
        print("TAKER BOT ORDERS at time ", state.timestamp, ":", my_orders)
        return my_orders

    def run_internal(self, state):

        time = state.timestamp

        # filter df to only look at current time
        cur_df = self.trade_df
        cur_df = cur_df[cur_df["time"] == time]


        for sym in self.symbols:
            self.take_trade(state, sym, cur_df)
        


    def take_trade(self, state: TradingState, symbol: Symbol, cur_df):

        # filters cur_df to only use current symbol
        trades = cur_df[cur_df["symbol"] == symbol]
        
        for _, trade in trades.iterrows():
            trade_price = trade["price"]
            trade_quantity = trade["quantity"]

            # look at current best buy, potentially sell to them
            buy_book = state.order_depths[symbol].buy_orders
            if len(buy_book) > 0:
                buy_price, buy_quantity = max(buy_book.items())
                if trade_price < buy_price:
                    # sell to their buy order
                    self.place_sell_order(Order(
                        symbol=symbol,
                        price=trade_price,
                        quantity=trade_quantity,
                    ))

            sell_book = state.order_depths[symbol].sell_orders
            if len(sell_book) > 0:
                sell_price, sell_quantity = min(sell_book.items())
                if trade_price > sell_price:
                    # buy from their sell order
                    self.place_buy_order(Order(
                        symbol=symbol,
                        price=trade_price,
                        quantity=trade_quantity,
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