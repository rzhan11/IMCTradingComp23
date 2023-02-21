from datamodel import *

import random



random.seed(1)

class Fair:

    def __init__(self, products):

        self.products = products

        self.fairs = {
            "BANANAS": 5000,
            "PEARLS": 10000,
            "SEASHELLS": 1,
        }
        

    def update_fairs(self, timestamp, turn):
        
        self.fairs["SEASHELLS"] = 1
        
        self.fairs["PEARLS"] = 10000

        self.fairs["BANANAS"] = 5000