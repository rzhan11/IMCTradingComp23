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
# keeps track of best bid and ask each time step
# symbols are hardcoded
HISTORY = {
    "BID" : {"PEARLS": [],
            "BANANAS": [],
            },
    "ASK" : {"PEARLS": [],
            "BANANAS": [],
            },
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
        self.is_close = False
        self.close_turns = 30
        self.max_timestamp = 200000
        self.time_step = 100

        self.is_penny = False

    def turn_start(self, state: TradingState):
        self.turn += 1

        print("-"*50)
        print(f"Round {state.timestamp}, {self.turn}")
        print("-"*50)

        

        # print raw json, for analysis
        self.record_game_state(state)

        # preprocess game state
        Preprocess.preprocess(state)

        # setup list of current products
        self.products = set([listing.product for sym, listing in state.listings.items()])
        self.symbols = set([listing.symbol for sym, listing in state.listings.items()])

        # reset _buy_orders/_sell_orders for this turn
        self.OM = OrderManager(
            symbols=self.symbols,
            position_limits=self._position_limits,
        )

    def run(self, state: TradingState) -> Dict[Symbol, List[Order]]:
        """ Called by game engine, returns dict of buy/sell orders
        """
        # turn setup
        self.turn_start(state)

        # main body
        self.run_internal(state)

        # cleanup / info reporting section
        return self.turn_end(state)
    

    def turn_end(self, state):
        """ Runs at end of turn
        - records the orders we submit
        - postprocess orders to get them inthe 
        """
        
        # post process orders
        my_orders = self.OM.postprocess_orders()

        # record end of turn (after post-processing)
        self.record_turn_end(state)

        # return my orders
        self.finish_turn += 1
        return my_orders
    




    def run_internal(self, state: TradingState):
        """ Main body of logic
        - analyzes current market
        - places new orders for this turn
        """

        OM = self.OM

        # close all positions if `is_close` flag is on, and we are at end of game
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
        
            # Use exponential moving average to check for price spikes
            should_carp_bid = True
            should_carp_ask = True
            volatility_cap = 0.0005
            lookback = 10
            if self.turn > lookback and len(HISTORY['BID'][sym]) > lookback and len(HISTORY['ASK'][sym]) > lookback:
                bid_ema = self.calc_ema(list(reversed(HISTORY['BID'][sym])), lookback)
                ask_ema = self.calc_ema(list(reversed(HISTORY['ASK'][sym])), lookback)
                curr_best_bid = buys[0][0]
                curr_best_ask = sells[0][0]
                if curr_best_bid > (1 + volatility_cap) * bid_ema:
                    # best bid is 0.05% above 10 day moving average, dont carp
                    should_carp_bid = False
                if curr_best_ask < (1 - volatility_cap) * ask_ema:
                    # best ask is 0.05% above 10 day moving average, dont carp
                    should_carp_ask = False

            # store best bid and ask 
            if len(buys) > 0:
                HISTORY['BID'][sym].append(buys[0][0])
            if len(sells) > 0:
                HISTORY['ASK'][sym].append(sells[0][0])


            # match orders on buy-side
            if should_carp_bid:
                for price, quantity in buys:
                    if should_penny:
                        price += 1

                    limit = OM.get_rem_buy_size(state, sym)
                    if limit > 0:
                        OM.place_buy_order(Order(
                            symbol=sym,
                            price=price,
                            quantity=min(limit, quantity)
                        ))

            # match orders on sell-side
            if should_carp_ask:
                for price, quantity in sells:
                    if should_penny:
                        price -= 1

                    limit = OM.get_rem_sell_size(state, sym)
                    if limit > 0:
                        OM.place_sell_order(Order(
                            symbol=sym,
                            price=price,
                            quantity=min(limit, quantity)
                        ))

    #calculates EMA of past x days
    def calc_ema(self, lst, x):
        # alpha = 2 / (x + 1)  # calculate smoothing factor
        alpha = 0.3
        ema = [lst[0]]       # initialize EMA with first value of the list
        for i in range(1, x):
            ema.append(alpha * lst[i] + (1 - alpha) * ema[-1])  # calculate EMA using recursive formula
        return ema[-1]  # return last value of EMA




    def close_positions(self, state: TradingState):
        """ Closes out our position at the end of the game
        - is currently used since IMC's engine uses weird fair values
        """
        OM = self.OM

        for prod, pos in state.position.items():
            if pos < 0:
                OM.place_buy_order(Order(symbol=prod, price=1e9, quantity=1))
            elif pos > 0:
                OM.place_sell_order(Order(symbol=prod, price=0, quantity=1))




    def record_game_state(self, state: TradingState):
        """
        Prints out the state of the game when received
        """
        state.turn = self.turn
        state.finish_turn = self.finish_turn

        s = state.toJSON()

        print(f"__game_state_start\n{s}\n__game_state_end\n")

        

    def record_turn_end(self, state: TradingState):
        """ Prints out end of turn info, including:
        - orders we sent this turn
        """

        OM = self.OM

        my_orders = {sym: { "buy_orders": OM._buy_orders[sym], "sell_orders": OM._sell_orders[sym] } for sym in self.symbols}

        obj = {
            "time": state.timestamp,
            "my_orders": my_orders,
        }
        
        # convert obj to 
        s = json.dumps(obj, default=lambda o: o.__dict__, sort_keys=True)

        print(f"__turn_end_start\n{s}\n__turn_end_end")



class OrderManager:
    """
    This class provides an API to placing orders.
    Buy/sell orders can be queued by calling the 'place_buy_order/place_sell_order'
    These orders are recorded in the OrderManager object and will be returned at the end of the turn.
    """
    
    
    def __init__(self, symbols, position_limits):
        self._buy_orders : Dict[Symbol, List[Order]] = {sym: [] for sym in symbols}
        self._sell_orders : Dict[Symbol, List[Order]] = {sym: [] for sym in symbols}
        self._position_limits = position_limits


    def place_buy_order(self, order: Order):
        """ Queues a buy order
        """
        self._buy_orders[order.symbol] += [order]

    def place_sell_order(self, order: Order):
        """ Queues a sell order
        """
        self._sell_orders[order.symbol] += [order]


    def get_rem_buy_size(self, state: TradingState, sym: Symbol) -> int:
        """ Returns additional capacity for trading a symbol, while taking into account current orders
        """
        return self.get_max_buy_size(state, sym) - self._get_cur_order_buy_size(sym)

    def get_rem_sell_size(self, state: TradingState, sym: Symbol) -> int:
        return self.get_max_sell_size(state, sym) - self._get_cur_order_sell_size(sym)

    def get_max_buy_size(self, state: TradingState, sym: Symbol) -> int:
        """ Returns maximum buy size for a specified symbol for this turn
        """
        prod = state.listings[sym].product
        limit = self._position_limits[prod]
        pos = state.position[prod]
        return limit - pos

    def get_max_sell_size(self, state: TradingState, sym: Symbol) -> int:
        """ Returns maximum sell size for a specified symbol for this turn
        """
        prod = state.listings[sym].product
        limit = self._position_limits[prod]
        pos = state.position[prod]
        return pos - (-limit)


    def _get_cur_order_buy_size(self, sym: Symbol) -> int:
        """ Returns cumulative size of buy orders for a specified symbol (private) 
        """
        
        orders = self._buy_orders[sym]
        return sum([ord.quantity for ord in orders])


    def _get_cur_order_sell_size(self, sym: Symbol) -> int:
        """ Returns cumulative size of sell orders for a specified symbol (private) 
        """
        orders = self._sell_orders[sym]
        return sum([ord.quantity for ord in orders])




    def postprocess_orders(self):
        """ Returns final orders
        - makes sell_orders have negative quantity (since the IMC engine wants it that way)
        - this method actually modifies the Order's directly, so it should only be called at the end of the turn once.
        """

        # iterate through sell orders
        for sym, orders in self._sell_orders.items():
            for order in orders:
                order.quantity = -1 * order.quantity
                
        return {sym: self._buy_orders[sym] + self._sell_orders[sym] for sym in self._buy_orders.keys()}




class Preprocess:
    """
    This class does all the preprocessing for the input game state

    """

    @classmethod
    def preprocess(cls, state: TradingState) -> None:
        """
        Call this method to perform all desired preprocessing
        """
        cls.fix_listings(state)
        cls.fix_position(state)
        cls.negate_sell_book_quantities(state)



    @classmethod
    def fix_listings(cls, state: TradingState):
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


    @classmethod
    def fix_position(cls, state: TradingState):
        """
        The IMC engine does not include products that haven't been traded for state.position
        This standardizes the input, so that we always see each product as a key 
        """

        products = { listing.product for sym, listing in state.listings.items() }
        
        for prod in products:
            if prod not in state.position.keys():
                state.position[prod] = 0


    @classmethod
    def negate_sell_book_quantities(cls, state: TradingState):
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