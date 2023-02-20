import pandas as pd
import numpy as np
import json

from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order, Symbol


class Market:

    def __init__(self, 
            player_id=None, 
            position_limits=None):

        self.turn = -1
        self.player_id = player_id
        self.position_limits = position_limits

    def run(self, state: TradingState) -> Dict[Symbol, List[Order]]:
        self._orders = {sym: [] for sym in state.listings.keys()}

        q = 1 + state.timestamp // 10

        self.place_order(Order("BANANAS", price=4499, quantity=q))
        self.place_order(Order("BANANAS", price=4501, quantity=-1 * q))

        self.place_order(Order("PEARLS", price=9999, quantity=q))
        self.place_order(Order("PEARLS", price=10001, quantity=-1 * q))


        return self._orders

    def place_order(self, order: Order):
        self._orders[order.symbol] += [order]