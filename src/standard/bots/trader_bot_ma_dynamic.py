import pandas as pd
import numpy as np
import json
import time

from typing import Dict, List, Tuple, Any
from datamodel import OrderDepth, TradingState, Order, Listing, ProsperityEncoder
from datamodel import Symbol, Product, Position


Price = int


MAX_POS = {
    "PEARLS": 20,
    "BANANAS": 20,
}

PARAMS = {
    # game parameters
    "max_timestamp": 100000,
    "time_step": 100,

    # auto-close 
    "is_close": False,
    "close_turns": 30,

    # market-making params
    "is_penny": True,
    "match_size": False,

    "min_take_edge": 0.25,

    # how many historical data points to use for analysis
    "DM.lookback": 100,

    # how many days used to compute true value
    "DM.ema_eval_true_days": 10,

    # how many days to test EMA against true
    "DM.ema_test_days": 100,

    "DM.ema_spans": [10],
    # "DM.ema_spans": [3, 10, 21, 100],
    # "DM.ema_spans": [3, 5, 10, 21, 30, 50, 100],
}


_description = f"""
PARAMS:
{json.dumps(PARAMS, indent=2)}

Description:
dynamic EMA

- DataManager lookback=100

- dynamic EMA by measuring how good ema
    - compare 10, 21, 100

- no closing at end of game
"""


class Logger:
    def __init__(self) -> None:
        self.logs = ""

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]]) -> None:
        logs = self.logs
        if logs.endswith("\n"):
            logs = logs[:-1]

        _print(json.dumps({
            "state": state,
            "orders": orders,
            "logs": logs,
        }, cls=ProsperityEncoder, separators=(",", ":"), sort_keys=True))

        self.state = None
        self.orders = {}
        self.logs = ""


logger = Logger()
_print = print
print = logger.print

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
            ema_eval_true_days=PARAMS["DM.ema_eval_true_days"],
            ema_test_days=PARAMS["DM.ema_test_days"],
            ema_spans=PARAMS["DM.ema_spans"],
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
        self.match_size = PARAMS["match_size"]
        self.min_take_edge  = PARAMS["min_take_edge"]


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

        self.products = sorted(list(self.products))
        self.symbols = sorted(list(self.symbols))

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

        _print()

        state_json = json.loads(state.toJSON())

        try:
        
            # turn setup
            self.turn_start(state)

            # main body
            self.run_internal(state)

            # cleanup / info reporting section
            orders = self.turn_end(state)
        
        finally:
            logger.flush(state_json, orders)

        return orders
    

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

        self.all_buys = {}
        self.all_sells = {}

        # Iterate over all the keys (the available products) contained in the order depths
        for sym in state.order_depths.keys():

            prod: Product = state.listings[sym].product

            book = state.order_depths[sym]

            buys: List[Tuple[Price, Position]] = sorted(list(book.buy_orders.items()), reverse=True)
            sells: List[Tuple[Price, Position]] = sorted(list(book.sell_orders.items()), reverse=False)

            self.all_buys[sym] = buys            
            self.all_sells[sym] = sells 

            # calc fair value
            fair_value = self.get_fair_value(sym)   
            mid_ema = self.get_ema_mid(sym)  

            self.take_logic(
                state=state,
                sym=sym,
                fair_value=fair_value,
                ema=mid_ema,
            )

            self.make_logic(
                state=state,
                sym=sym,
                fair_value=fair_value,
            )


    def get_ema_mid(self, sym: Symbol) -> float:
        
        # calc mid_ema
        sym_history = self.DM.history[sym]
        mid_ema = sym_history[-1]["best_ema"]
        mid_ema_span = sym_history[-1]["best_ema_span"]

        return mid_ema



    def get_fair_value(self, sym: Symbol) -> float:

        buys, sells = self.all_buys[sym], self.all_sells[sym]

        mid_ema = self.get_ema_mid(sym)

        # get large_quote_mid
        large_quote_mid, use_large_quote_mid = self.get_large_quote_mid(sym)

        # if conditions were good, use large_quote_mid
        if use_large_quote_mid:
            return large_quote_mid
        else: # else, use ema
            return mid_ema
        



    def take_logic(self, 
            state: TradingState,
            sym: Symbol, 
            fair_value: float,
            ema: float,
            ):
        
        buys, sells = self.all_buys[sym], self.all_sells[sym]
        OM = self.OM
        
        # min edge params
        min_buy_edge = self.min_take_edge
        min_sell_edge = self.min_take_edge

        # take orders on buy_side (we sell to existing buy orders)
        for price, quantity in buys:
            if price > fair_value + min_buy_edge:
            # if price > fair_value + min_buy_edge or price > ema:
                limit = OM.get_rem_sell_size(state, sym)
                if limit > 0:
                    OM.place_sell_order(Order(
                        symbol=sym,
                        price=price,
                        quantity=min(limit, quantity)
                    ))

        # take orders on sell side (we buy from existing sell orders)
        for price, quantity in sells:
            if price < fair_value - min_sell_edge:
            # if price < fair_value - min_sell_edge or price < ema:
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
            fair_value: float,
            ):
        
        buys, sells = self.all_buys[sym], self.all_sells[sym]
        OM = self.OM
        prod = state.listings[sym].product

        # """ If we have high positions, place good orders at the money """

        # # estimate position after taker trades occur
        # pos_estimate = state.position[prod] + OM._get_cur_order_buy_size(sym) - OM._get_cur_order_sell_size(sym)
        # pos_limit = self._position_limits[prod]
        # limit_goal = int(1/3 * pos_limit)

        # buy_limit = pos_limit - pos_estimate
        # sell_limit = pos_limit - (-pos_estimate)

        # # can't buy, place good sells
        # if buy_limit < limit_goal:
        #     limit = OM.get_max_sell_size(state, sym)

        #     price = np.ceil(fair_value)
        #     quantity = min(limit_goal - buy_limit, limit)

        #     OM.place_sell_order(Order(
        #         symbol=sym,
        #         price=price,
        #         quantity=quantity,
        #     ))

        # # can't sell, place good buys
        # if sell_limit < limit_goal:
        #     limit = OM.get_max_buy_size(state, sym)

        #     price = np.floor(fair_value)
        #     quantity = min(limit_goal - sell_limit, limit)

        #     OM.place_buy_order(Order(
        #         symbol=sym,
        #         price=price,
        #         quantity=quantity,
        #     ))


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
            if price > fair_value:
                continue

            limit = OM.get_rem_buy_size(state, sym)
            if limit > 0:
                if self.match_size:
                    order_quantity = min(limit, quantity)
                else:
                    order_quantity = limit

                OM.place_buy_order(Order(
                    symbol=sym,
                    price=price,
                    quantity=order_quantity,
                ))

        # match orders on sell-side
        for price, quantity in sells:
            if should_penny:
                price -= 1

            # don't carp if sell price is higher than EMA
            if price < fair_value:
                continue

            limit = OM.get_rem_sell_size(state, sym)
            if limit > 0:
                if self.match_size:
                    order_quantity = min(limit, quantity)
                else:
                    order_quantity = limit

                OM.place_sell_order(Order(
                    symbol=sym,
                    price=price,
                    quantity=order_quantity,
                ))



    def get_large_quote_mid(self, sym):
        """ Checks if we should calculate the fair value using the mid of the order book
        - Gets the buy and sell orders with the maximum size
        - Checks if the maximum size is >= 15 for both buy/sell, and checks if the width is from 6 to 8 
        - If yes, return prices of max size buy/sell from order book, else return None
        """

        buys, sells = self.all_buys[sym], self.all_sells[sym]
        
        buy_price, buy_size = max(buys, key=lambda x:x[1])
        sell_price, sell_size = max(sells, key=lambda x:x[1])

        spread = sell_price - buy_price
        
        should_use = \
            6 <= spread <= 11 and \
            15 <= buy_size <= 35 and \
            15 <= sell_size <= 35
        
        return (buy_price + sell_price) / 2, should_use



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

        emas = { sym: self.DM.history[sym][-1]["emas"] for sym in self.symbols }
        best_emas = { sym: self.DM.history[sym][-1]["best_ema"] for sym in self.symbols }
        best_ema_spans = { sym: self.DM.history[sym][-1]["best_ema_span"] for sym in self.symbols }

        # get large quote mid data
        quote_mids_data = { sym: self.get_large_quote_mid(sym) for sym in self.symbols}
        quote_mids = {sym: mid for sym, (mid, use) in quote_mids_data.items() }
        use_quote_mids = {sym: use for sym, (mid, use) in quote_mids_data.items() }

        fair_values = { sym: self.get_fair_value(sym) for sym in self.symbols}

        obj = {
            # timing
            "time": state.timestamp,
            "wall_time": time.time() - self.wall_start_time,
            "process_time": time.process_time() - self.process_start_time,

            # my orders
            "my_orders": my_orders,

            ### fair values ###

            # ema
            "emas": emas,
            "best_emas": best_emas,
            "best_ema_spans": best_ema_spans,

            # large quote mid
            "quote_mids": quote_mids,
            "use_quote_mids": use_quote_mids,

            # fair value
            "fair_values": fair_values,
        }


        
        # convert obj to 
        s = json.dumps(obj, default=lambda o: o.__dict__, sort_keys=True)

        print(f"__turn_end_start\n{s}\n__turn_end_end")



class DataManager:
    """
    This class stores historical data + contains all of our data analysis code
    """

    def __init__(
                self, 
                lookback, 
                ema_eval_true_days,
                ema_test_days,
                ema_spans,
            ):
        """
        lookback - defines how many historical days are used by our data analysis
        """

        self.lookback = lookback
        self.ema_eval_true_days = ema_eval_true_days
        self.ema_test_days = ema_test_days
        self.ema_spans = ema_spans
        self.default_ema_span = ema_spans[0]

        self.history = {}


    def add_history(self, state: TradingState, symbols: List[Symbol], products: List[Product]):
        """
        Stores state
        - should be called after preprocessing / recording of game state
        """
        self.symbols = symbols
        self.products = products

        for sym in symbols:
            self.add_history_sym(state, sym)

    def add_history_sym(self, state: TradingState, sym: Symbol):
        # add sym to history if not present
        if sym not in self.history:
            self.history[sym] = []
        sym_history = self.history[sym]

        book = state.order_depths[sym]

        buys: List[Tuple[Price, Position]] = sorted(list(book.buy_orders.items()), reverse=True)
        sells: List[Tuple[Price, Position]] = sorted(list(book.sell_orders.items()), reverse=False)

        if len(buys) > 0:
            best_buy = buys[0][0]

        if len(sells) > 0:
            best_sell = sells[0][0]

        mid = (best_buy + best_sell) / 2

        # get previous emas
        if len(sym_history) == 0:
            old_emas = {span: mid for span in self.ema_spans}
        else:
            old_emas = sym_history[-1]["emas"]

        # calculate ema for each span
        new_emas = {}
        for span in self.ema_spans:
            # calculate ema
            alpha = 2 / (span + 1)
            new_ema = mid * alpha + (1 - alpha) * old_emas[span]
            # round for pretty print
            new_emas[span] = round(new_ema, 2)

        # find best ema
        if len(sym_history) < self.ema_eval_true_days + 1:
            # use default if no history
            best_ema_span = self.default_ema_span
        else:
            # find best ema (using L1 difference)
            scores = []
            # need ema_test_days + ema_eval_true_days + 1
            n_days = min(self.ema_test_days + self.ema_eval_true_days + 1, len(sym_history))

            # calc SMAs
            old_mids = [sym_history[-(i + 1)]["mid"] for i in range(n_days - 1)]
            old_mids = list(reversed(old_mids))

            def moving_average(a, n=3) :
                ret = np.cumsum(a)
                ret[n:] = ret[n:] - ret[:-n]
                return ret[n - 1:] / n
            
            # sma = moving_average(old_mids, n=1)
            smas = moving_average(old_mids, n=self.ema_eval_true_days)

            # print(smas)
            # print(old_mids)
            
            for span in self.ema_spans:

                ema_preds = [sym_history[-(i + self.ema_eval_true_days + 1)]["emas"][span] for i in range(len(smas))]
                ema_preds = list(reversed(ema_preds))
                # print(ema_preds)

                # compare true SMA vs pred EMA
                diffs = abs(smas - ema_preds)
                score = np.mean(diffs)
                scores += [(score, span)]

            best_score, best_ema_span = min(scores)

        # add obj to history
        obj = {
            "best_buy": best_buy,
            "best_sell": best_sell,
            "mid": mid,
            "emas": new_emas,
            "best_ema": new_emas[best_ema_span],
            "best_ema_span": best_ema_span,
        }
        self.history[sym] += [obj]




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