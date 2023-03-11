import pandas as pd
import numpy as np
import json
import time

from typing import Dict, List, Tuple
from datamodel import OrderDepth, TradingState, Order, Listing
from datamodel import Symbol, Product, Position


Price = int


MAX_POS = {
    "PEARLS": 20,
    "BANANAS": 20,
}

PARAMS = {
    # game parameters
    "max_timestamp": 200000,
    "time_step": 100,

    # how many historical data points to use for analysis
    "DM.lookback": 100,

    # auto-close 
    "is_close": False,
    "close_turns": 30,

    # market-making params
    "is_penny": False,
    "ema_span": 21,
}


_description = f"""
PARAMS:
{json.dumps(PARAMS, indent=2)}

Description:
uses faster ema (no pandas)

- DataManager lookback=100

- EMA span 10

- taker logic
    - ema as fair
    - min_buy/sell_edge = 1

- maker logic
    - ema as fair
    - no pennying

- no closing at end of game
"""


class Trader:

    def __init__(self, 
            player_id=None, 
            position_limits=None,
            is_main=False,
            ):
        
        # print description to help identify bot/params
        print(_description)

        # local engine vars
        self._player_id = player_id
        self._is_main = is_main

        self._position_limits = position_limits
        if self._position_limits is None:
            self._position_limits = MAX_POS
        
        # init history tracker
        self.DM : DataManager = DataManager(
            lookback=PARAMS["DM.lookback"],
            ema_span=PARAMS["ema_span"],
        )

        # helper vars
        self.turn = -1
        self.finish_turn = -1

        # parameters
        self.is_close = PARAMS["is_close"]
        self.close_turns = PARAMS["close_turns"]
        self.max_timestamp = PARAMS["max_timestamp"]
        self.time_step = PARAMS["time_step"]

        self.is_penny = PARAMS["is_penny"]

        self.ema_span = PARAMS["ema_span"]
        

    def turn_start(self, state: TradingState):
        # measure time
        self.wall_start_time = time.time()
        self.process_start_time = time.process_time()

        # print round header
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
        self.OM : OrderManager = OrderManager(
            symbols=self.symbols,
            position_limits=self._position_limits,
        )

        # store/process game state into history
        self.DM.add_history(state, self.products, self.symbols)
        # self.DM.process_history()


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

            buys: List[Tuple[Price, Position]] = sorted(list(book.buy_orders.items()), reverse=True)
            sells: List[Tuple[Price, Position]] = sorted(list(book.sell_orders.items()), reverse=False)

            # Use exponential moving average to check for price spikes
            # should_carp_bid = True
            # should_carp_ask = True
            # volatility_cap = 0.0005
            # lookback = 10
            
            # book_tops = self.DM.book_tops

            mid_ema = self.DM.emas[sym]
            print(f"ema {sym}", mid_ema)

            self.take_logic(
                state=state,
                sym=sym,
                buys=buys,
                sells=sells, 
                mid_ema=mid_ema,
            )

            self.make_logic(
                state=state,
                sym=sym,
                buys=buys,
                sells=sells, 
                mid_ema=mid_ema,
            )


    def take_logic(self, 
            state: TradingState,
            sym: Symbol, 
            buys: List[Tuple[Price, Position]], 
            sells: List[Tuple[Price, Position]], 
            mid_ema: float,
            ):
        
        OM = self.OM

        min_buy_edge = 1
        min_sell_edge = 1

        # take orders on buy_side (we sell to existing buy orders)
        for price, quantity in buys:
            if price > mid_ema + min_buy_edge:
                limit = OM.get_rem_sell_size(state, sym)
                if limit > 0:
                    OM.place_sell_order(Order(
                        symbol=sym,
                        price=price,
                        quantity=min(limit, quantity)
                    ))

        # take orders on sell side (we buy from existing sell orders)
        for price, quantity in sells:
            if price < mid_ema - min_sell_edge:
                limit = OM.get_rem_buy_size(state, sym)
                if limit > 0:
                    OM.place_buy_order(Order(
                        symbol=sym,
                        price=price,
                        quantity=min(limit, quantity)
                    ))

    def make_logic(self, 
            state: TradingState,
            sym: Symbol, 
            buys: List[Tuple[Price, Position]], 
            sells: List[Tuple[Price, Position]], 
            mid_ema: float,
            ):
        
        OM = self.OM

        should_penny = False
        if self.is_penny:
            if len(buys) > 0 and len(sells) > 0:
                spread = sells[0][0] - buys[0][0]
                if spread > 2:
                    should_penny = True

        # match orders on buy-side
        for price, quantity in buys:
            if should_penny:
                price += 1

            # don't carp if buy price is higher than EMA
            if price > mid_ema:
                continue

            limit = OM.get_rem_buy_size(state, sym)
            if limit > 0:
                OM.place_buy_order(Order(
                    symbol=sym,
                    price=price,
                    quantity=min(limit, quantity)
                ))

        # match orders on sell-side
        for price, quantity in sells:
            if should_penny:
                price -= 1

            # don't carp if sell price is higher than EMA
            if price < mid_ema:
                continue

            limit = OM.get_rem_sell_size(state, sym)
            if limit > 0:
                OM.place_sell_order(Order(
                    symbol=sym,
                    price=price,
                    quantity=min(limit, quantity)
                ))



    #calculates EMA of past x days
    def calc_ema(self, ser : pd.Series, span : int):
        return ser.ewm(span=span, adjust=False).mean().iloc[-1]


    def close_positions(self, state: TradingState):
        """ Closes out our position at the end of the game
        - was previously used since IMC's engine uses weird fair values
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

        emas = self.DM.emas
        # emas = {}
        # for sym in self.symbols:
        #     emas[sym] = self.calc_ema(self.DM.book_tops[f"{sym}_mid"], span=self.ema_span)


        obj = {
            "time": state.timestamp,
            "wall_time": time.time() - self.wall_start_time,
            "process_time": time.process_time() - self.process_start_time,
            "my_orders": my_orders,
            "ema": emas,
        }


        
        # convert obj to 
        s = json.dumps(obj, default=lambda o: o.__dict__, sort_keys=True)

        print(f"__turn_end_start\n{s}\n__turn_end_end")



class DataManager:
    """
    This class stores historical data + contains all of our data analysis code
    """

    def __init__(self, lookback, ema_span):
        """
        lookback - defines how many historical days are used by our data analysis
        """

        self.lookback = lookback
        self.ema_span = ema_span

        self.history = {}
        self.emas = {}


    def add_history(self, state: TradingState, symbols: List[Symbol], products: List[Product]):
        """
        Stores state
        - should be called after preprocessing / recording of game state
        """
        self.symbols = symbols
        self.products = products

        for sym in symbols:
            book = state.order_depths[sym]

            buys: List[Tuple[Price, Position]] = sorted(list(book.buy_orders.items()), reverse=True)
            sells: List[Tuple[Price, Position]] = sorted(list(book.sell_orders.items()), reverse=False)

            if len(buys) > 0:
                best_buy = buys[0][0]

            if len(sells) > 0:
                best_sell = sells[0][0]

            mid = (best_buy + best_sell) / 2

            obj = {
                "best_buy": best_buy,
                "best_sell": best_sell,
                "mid": mid,
            }

            # add obj to history
            if sym not in self.history:
                self.history[sym] = []
            self.history[sym] += [obj]


            # calculate ema
            alpha = 2 / (self.ema_span + 1)
            old_ema = self.emas.get(sym, mid)
            new_ema = mid * alpha + (1 - alpha) * old_ema
            # round for pretty print
            new_ema = round(new_ema, 2)

            obj["ema"] = new_ema
            self.emas[sym] = new_ema






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