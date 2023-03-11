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
            
            book_tops = self.DM.book_tops

            mid_ema = self.calc_ema(
                book_tops[f"{sym}_mid"], 
                span=self.ema_span,
            )
            print(type(mid_ema), mid_ema)

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

        emas = {}
        for sym in self.symbols:
            emas[sym] = self.calc_ema(self.DM.book_tops[f"{sym}_mid"], span=self.ema_span)


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

    def __init__(self, lookback):
        """
        lookback - defines how many historical days are used by our data analysis
        """

        self.history = []
        self.lookback = lookback

    def add_history(self, state: TradingState, symbols: List[Symbol], products: List[Product]):
        """
        Stores state
        - should be called after preprocessing / recording of game state
        """
        self.history += [json.loads(state.toJSON())]
        self.symbols = symbols
        self.products = products


    def process_history(self):
        """
        Creates processed df
        """

        # process only some historical data
        data = self.history[-1 * self.lookback:]
        raw_df = pd.DataFrame(data)
        raw_df = self.preprocess_df(raw_df)

        book_tops = self.calc_book_tops(raw_df)

        market_trades, my_trades = self.process_trades(raw_df)

        self.book_tops = book_tops
        self.market_trades = market_trades
        self.my_trades = my_trades


    def preprocess_df(self, raw_df):
        """
        - Modifies column names
        - Converts raw_df["book"] to be all ints
        """

        # print(raw_df)

        # modify column names
        raw_df = raw_df.drop("listings", axis=1)
        raw_df = raw_df.rename({
            "timestamp": "time",
            "order_depths": "book",
        }, axis=1)

        # modify raw_df["book"] to be all ints
        raw_df["book"] = raw_df["book"].apply(lambda x: {
            sym: {
                typ: {
                    int(k) : v for k, v in orders.items()
                }
                for typ, orders in all_orders.items()
            }
            for sym, all_orders in x.items()
        })

        return raw_df


    def calc_book_tops(self, raw_df):
        _symbols: List[Symbol] = self.symbols


        book_data = []
        book_cols = []

        for sym in _symbols:
            ### buys
            col = raw_df["book"].apply(lambda x: x[sym])
            # convert dicts into int -> int
            col = col.apply(lambda x : [(int(k), v) for k, v in x["buy_orders"].items()])
            col = col.apply(lambda x : sorted(x, reverse=True))
            col = col.apply(lambda x : x[0][0] if len(x) > 0 else np.nan).astype(float)
            
            book_data += [col]
            book_cols += [f"{sym}_best_buy"]
            
            
            ### sells
            col = raw_df["book"].apply(lambda x: x[sym])
            col = col.apply(lambda x : [(int(k), v) for k, v in x["sell_orders"].items()])
            col = col.apply(lambda x : sorted(x, reverse=False))
            col = col.apply(lambda x: x[0][0] if len(x) > 0 else np.nan).astype(float)
            
            book_data += [col]
            book_cols += [f"{sym}_best_sell"]
            
            
        book_tops = pd.concat(book_data, axis=1)
        book_tops.columns = book_cols

        # all book tops
        for sym in _symbols:
            book_tops[f"{sym}_mid"] = (book_tops[f"{sym}_best_buy"] + book_tops[f"{sym}_best_sell"]) / 2
            book_tops[f"{sym}_spread"] = book_tops[f"{sym}_best_sell"] - book_tops[f"{sym}_best_buy"]
            
            print("missing mids", sym, list(book_tops.index[book_tops[f"{sym}_mid"].isna()]))
            
            book_tops[f"{sym}_mid"] = book_tops[f"{sym}_mid"].bfill()
            assert book_tops[f"{sym}_spread"].all() > 0

        # sort columns
        book_tops = book_tops.reindex(sorted(book_tops.columns), axis=1)
        book_tops["time"] = raw_df["time"]

        return book_tops


    def process_trades(self, raw_df):

        def flatten_trades(df, col, is_me):
            # get market trades

            data = []
            for index, row  in df.iterrows():
                all_trades = list(row[col].values())
                for sym_trades in all_trades:
                    for trade in sym_trades:
                        trade["time"] = row["time"] # fill time
                        trade["turn"] = row["turn"] # fill time
                    data += sym_trades

            df = pd.DataFrame(data, columns=['buyer', 'price', 'quantity', 'seller', 'symbol', 'timestamp', 'time', 'turn'])

            df = df.rename({"timestamp": "order_time"}, axis=1)
            
            # calculate info about my trades
            df["is_me"] = is_me
            df["my_buy"] = df["buyer"] == "SUBMISSION"
            df["my_sell"] = df["seller"] == "SUBMISSION"
            df["my_quantity"] = df["quantity"] * (df["my_buy"].astype(int) - df["my_sell"].astype(int))
            df["self_trade"] = df["my_buy"] & df["my_sell"]
            
            # report self trades
            self_trades = df[df["self_trade"]]
            # report_issue_and_continue( len(self_trades) == 0, self_trades)
            
            return df

        # get my_trades, market_trades, and trade_df (all_trades)
        market_trades = flatten_trades(
            raw_df, 
            "market_trades", 
            is_me=False
        ).sort_values(by="time")

        my_trades = flatten_trades(
            raw_df, 
            "own_trades", 
            is_me=True
        ).sort_values(by="time")

        # filter duplicate trades
        market_trades = market_trades.drop_duplicates(subset=["buyer", "price", "quantity", "seller", "symbol", "order_time"])
        my_trades = my_trades.drop_duplicates(subset=["buyer", "price", "quantity", "seller", "symbol", "order_time"])

        trade_df = pd.concat([market_trades, my_trades])
        trade_df = trade_df.sort_values(by="time").reset_index(drop=True)
        # trade_df = trade_df.drop(["order_time", "buyer", "seller"], axis=1)

        my_trades = trade_df[trade_df["is_me"]]
        market_trades = trade_df[~trade_df["is_me"]]

        return my_trades, market_trades



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