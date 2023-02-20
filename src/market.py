import pandas as pd
import numpy as np
import json

from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order, Symbol


class Market:
    def __init__(self, player_id=-1):
        self.player_id = player_id
        pass

    def run(self, state: TradingState):
        pass