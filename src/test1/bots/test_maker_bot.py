import pandas as pd
import numpy as np
import json

from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order, Trade, Listing, Symbol
from .abstract_bot import AbstractBot


class MakerBot(AbstractBot):

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

        self.run_unit_test(state)

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

        if state.timestamp == 0:
            self.make_market("PEARLS", 10000, 10, 2)
            self.make_market("BANANAS", 5000, 10, 2)
        elif state.timestamp == 100:
            # test order coalescing
            self.make_market("PEARLS", 10000, 100, 2)
            self.make_market("PEARLS", 10000, 100, 2)
            pass
        elif state.timestamp == 200:
            pass
            # self.make_market("PEARLS", 10000, 100, 2)
            # self.make_market("BANANAS", 10000, 100, 2)
        else:
            assert False, f"run_internal - unexpected timestamp, {state.timestamp}"




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


    def run_unit_test(self, state):
        _me = "SUBMISSION"

        exp_listings = {
            "BANANAS": Listing(
                symbol = "BANANAS",
                product = "BANANAS",
                denomination = 1,
            ),
            "PEARLS": Listing(
                symbol = "PEARLS",
                product = "PEARLS",
                denomination = 1,
            ),
        }


        if state.timestamp == 0:
            order_depths = { 
                "BANANAS": OrderDepth(), 
                "PEARLS": OrderDepth()
            }
            own_trades = { 
                "BANANAS": [], 
                "PEARLS": [] 
            }
            market_trades = { 
                "BANANAS": [], 
                "PEARLS": [] 
            }
            position = { 
                "BANANAS": 0, 
                "PEARLS": 0
            }
        elif state.timestamp == 100:
            order_depths = {
                "BANANAS": OrderDepth(
                    buy_orders={},
                    sell_orders={},
                ),
                "PEARLS": OrderDepth(
                    buy_orders={},
                    sell_orders={},
                ),
            }
            own_trades = { 
                "BANANAS": [
                    Trade("BANANAS", 4990, 2, buyer=_me, timestamp=100),
                ], 
                "PEARLS": [
                    Trade("PEARLS", 9990, 2, buyer=_me, timestamp=100),
                ] 
            }
            market_trades = { 
                "BANANAS": [], 
                "PEARLS": [],
            }
            position = { 
                "BANANAS": 2, 
                "PEARLS": 2,
            }
        elif state.timestamp == 200:
            order_depths = {
                "BANANAS": OrderDepth(
                    buy_orders={},
                    sell_orders={},
                ),
                "PEARLS": OrderDepth(
                    buy_orders={},
                    sell_orders={},
                ),
            }
            own_trades = { 
                "BANANAS": [], 
                "PEARLS": [
                    Trade("PEARLS", 10100, 2, seller=_me, timestamp=200),
                    Trade("PEARLS", 10100, 2, seller=_me, timestamp=200),
                ], 
            }
            market_trades = { 
                "BANANAS": [], 
                "PEARLS": [] 
            }
            position = { 
                "BANANAS": 2, 
                "PEARLS": -2,
            }
        else:
            assert False, f"unexpected timestamp {state.timestamp}"



        exp_state = TradingState(
            timestamp=state.timestamp,
            listings=exp_listings,
            order_depths=order_depths,
            own_trades=own_trades,
            market_trades=market_trades,
            position=position,
            observations={},
        )

        self.eval_unit_test(state, exp_state)