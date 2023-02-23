from datamodel import *

import random

import numpy as np

np.random.seed(1)


random.seed(1)

class Fair:

    def __init__(self, products):

        self.products = products

        self.value = {
            "BANANAS": 5000,
            "PEARLS": 10000,
            "SEASHELLS": 1,
        }

        self.vols = {
            "BANANAS": 1 / 100,
            "PEARLS": 0,
        }

        self._update_func = self.update_lognormal

        self.vol_turns = 100

        # do not update these values
        self.constant_set = {"SEASHELLS"}
        self.update_set = set(self.products) - self.constant_set

    def update_fairs(self, timestamp, turn):
        for prod in self.update_set:
            self._update_func(prod)



    def update_lognormal(self, prod):
        value = self.value[prod]
        vol = self.vols[prod]

        change = np.random.lognormal(
            mean=0, 
            sigma=vol * 1 / np.sqrt(self.vol_turns)
        )

        self.value[prod] = value * change