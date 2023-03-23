from datamodel import *

import random

import numpy as np

np.random.seed(1)


random.seed(1)

class Fair:

    def __init__(self, products, price_df):

        self.products = products

        self.value = {
            "BANANAS": 5000,
            "PEARLS": 10000,
            "COCONUTS": 8000,
            "PINA_COLADAS": 15000,
            "SEASHELLS": 1,
        }

        self.vols = {
            "BANANAS": 0.31 / 100, # 0.31% every 100 turns -> 1% every 1000 turns
            "PEARLS": 0,
            "PINA_COLADAS": 3 / 100,
            "COCONUTS": 1.5 / 100,
        }

        self.price_df = price_df
        # self._update_func = self.update_lognormal
        self._update_func = self.update_mid_price

        self.vol_turns = 100

        # do not update these values
        self.constant_set = {"SEASHELLS"}
        self.update_set = set(self.products) - self.constant_set

    def update_fairs(self, timestamp, turn):
        for prod in self.update_set:
            self._update_func(timestamp, prod)

    # update fair values based on the mid price
    def update_mid_price(self, timestamp, prod):
        time_state = self.price_df[(self.price_df["time"] == timestamp)
                & (self.price_df["symbol"] == prod)]
        mid_price = time_state["mid_price"].values[-1]
        self.value[prod] = mid_price

    def update_lognormal(self, prod):
        value = self.value[prod]
        vol = self.vols[prod]

        change = np.random.lognormal(
            mean=0, 
            sigma=vol * 1 / np.sqrt(self.vol_turns)
        )

        self.value[prod] = value * change