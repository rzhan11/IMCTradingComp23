import pandas as pd
import numpy as np
import json
import time
import traceback
import copy

from typing import Dict, List, Tuple, Any
from datamodel import OrderDepth, TradingState, Order, Listing, ProsperityEncoder
from datamodel import Symbol, Product, Position

from statistics import NormalDist

Price = int

PRINT_OURS = True
# PRINT_OURS = False

MAX_POS = {
    "PEARLS": 20,
    "BANANAS": 20,
    "COCONUTS": 600,
    "PINA_COLADAS": 300,
    # "COCONUTS": 300,
    # "PINA_COLADAS": 150,
}

PARAMS = {
    # game parameters
    "max_timestamp": 100000,
    "time_step": 100,

    # auto-close 
    "is_close": False,
    "close_turns": 30,

    # market-making params
    "is_penny": {
        "PEARLS": True,
        "BANANAS": True,
        "COCONUTS": True,
        "PINA_COLADAS": True,
    },

    "make_flag": {
        "PEARLS": True,
        "BANANAS": True,
        "COCONUTS": False,
        "PINA_COLADAS": False,
    },

    "pairs_model_weights": [1.55131931e+00, 2.59237689e+03],

    "match_size": False,

    "min_take_edge": 0.25,

    # how many historical data points to use for analysis
    "DM.lookback": 100,

    # how many days used to compute true value
    "DM.ema_eval_true_days": 10,

    # how many days to test EMA against true
    "DM.ema_test_days": 100,

    "DM.ema_spans": [21],
    # "DM.ema_spans": [3, 10, 21, 100],
    # "DM.ema_spans": [3, 5, 10, 21, 30, 50, 100],
}

WHALE_QUOTE_BOUNDS = {
    "BANANAS": {
        "spread": (6, 11), # (6, 7)
        "size": (13, 40), # (20, 40)
    },
    "PEARLS": {
        "spread": (6, 11), # (10, 10)
        "size": (15, 35), # (20, 30)
    },
    # "COCONUTS": {
    #     "spread": (6, 11), # (6, 7)
    #     "size": (15, 35), # (20, 35)
    # },
    # "PINA_COLADAS": {
    #     "spread": (6, 11), # (10, 10)
    #     "size": (15, 35), # (20, 30)
    # },
    "COCONUTS": {
        "spread": (2, 4), # (3, 3)
        "size": (80, 300), # (100, 250)
    },
    "PINA_COLADAS": {
        "spread": (2, 5), # (3, 4)
        "size": (40, 150), # (50, 120)
    },
}


REF_OPP_COSTS = {
    "BANANAS": {-20: -14.7657647292217, -19: -13.29629710340663, -18: -11.976129707870797, -17: -10.731811549403986, -16: -9.55300207809519, -15: -8.431620448101867, -14: -7.372766144924583, -13: -6.370120709708132, -12: -5.4357848840440965, -11: -4.570192384670548, -10: -3.7789819145585426, -9: -3.061733357707581, -8: -2.4200483551583005, -7: -1.8572060711246365, -6: -1.3698460547685016, -5: -0.9527868395582715, -4: -0.6088603749412016, -3: -0.34176439982319096, -2: -0.151297120607083, -1: -0.03748894542513881, 0: 0.0, 1: -0.03748894542513881, 2: -0.151297120607083, 3: -0.34176439982319096, 4: -0.6088603749412016, 5: -0.9527868395582715, 6: -1.3698460547685016, 7: -1.8572060711246365, 8: -2.4200483551583005, 9: -3.061733357707581, 10: -3.7789819145585426, 11: -4.570192384670548, 12: -5.4357848840440965, 13: -6.370120709708132, 14: -7.372766144924583, 15: -8.431620448101867, 16: -9.55300207809519, 17: -10.731811549403986, 18: -11.976129707870797, 19: -13.29629710340663, 20: -14.7657647292217},

    "PEARLS": {-20: -9.358567646428455, -19: -7.989049751739401, -18: -6.8314889942520125, -17: -5.831273378701653, -16: -4.94852483794422, -15: -4.168928678794217, -14: -3.496046552750144, -13: -2.9038189040225575, -12: -2.380425686706502, -11: -1.921814634768623, -10: -1.5229631167164257, -9: -1.1786437884677667, -8: -0.8924477057999951, -7: -0.6589991257793457, -6: -0.46900551524882417, -5: -0.31659342743445507, -4: -0.19758614628661064, -3: -0.1088561356903881, -2: -0.0476532206260174, -1: -0.01183670456754271, 0: 0.0, 1: -0.01183670456754271, 2: -0.0476532206260174, 3: -0.1088561356903881, 4: -0.19758614628661064, 5: -0.31659342743445507, 6: -0.46900551524882417, 7: -0.6589991257793457, 8: -0.8924477057999951, 9: -1.1786437884677667, 10: -1.5229631167164257, 11: -1.921814634768623, 12: -2.380425686706502, 13: -2.9038189040225575, 14: -3.496046552750144, 15: -4.168928678794217, 16: -4.94852483794422, 17: -5.831273378701653, 18: -6.8314889942520125, 19: -7.989049751739401, 20: -9.358567646428455},

    # PINA_COLADAS, COCONUTS are initialized in init_ref_opp_costs()
}

def init_ref_opp_costs():
    global REF_OPP_COSTS

    for sym in ["PINA_COLADAS", "COCONUTS"]:
        limit = MAX_POS[sym]
        REF_OPP_COSTS[sym] = {i: 0 for i in range(-limit, limit + 1)}

init_ref_opp_costs()



def _get_desc():
    _description = f"""
    PRINT_OURS:
    {PRINT_OURS}

    PARAMS:
    {json.dumps(PARAMS, indent=2)}

    WHALE_QUOTE_BOUNDS:
    {json.dumps(WHALE_QUOTE_BOUNDS, indent=2)}

    REF_OPP_COSTS:
    {REF_OPP_COSTS}

    
    Description:
    dynamic EMA

    - DataManager lookback=100

    - dynamic EMA by measuring how good ema
        - compare 10, 21, 100

    - no closing at end of game
    """

    return _description



""" setup logging """


class Logger:
    def __init__(self) -> None:
        self.logs = ""

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]]) -> None:
        logs = self.logs
        if logs.endswith("\n"):
            logs = logs[:-1]

        if PRINT_OURS:
            _print(logs)
        else: # print jaspers
            _print(json.dumps({
                "state": state,
                "orders": orders,
                "logs": "",
            }, cls=ProsperityEncoder, separators=(",", ":"), sort_keys=True))

        self.state = None
        self.orders = {}
        self.logs = ""

logger = Logger()
_print = print
if PRINT_OURS:
    pass
else:
    print = logger.print




""" TRADER Class """

class Trader:

    def __init__(self, 
            player_id=None, 
            position_limits=None,
            is_main=False,
            ):
        
        # print description to help identify bot/params
        print(_get_desc())

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
        self.make_flag = PARAMS["make_flag"]

        # pairs trading logic
        pairs_model_weights = PARAMS["pairs_model_weights"]
        self.pairs_model = np.poly1d(pairs_model_weights)


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
            listings=state.listings,
        )

        # store/process game state into history
        self.DM.add_history(state, self.products, self.symbols)
        # self.DM.process_history()


    def run(self, state: TradingState) -> Dict[Symbol, List[Order]]:
        """ Called by game engine, returns dict of buy/sell orders
        """

        _print("_"*100)

        state_json = json.loads(state.toJSON())

        orders = {}

    
        # turn setup
        self.turn_start(state)

        # main body
        self.run_internal(state)

        # cleanup / info reporting section
        orders = self.turn_end(state)
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
        # if self.is_close and state.timestamp >= self.max_timestamp - self.time_step * self.close_turns:
        #     self.close_positions(state)
        #     return

        # setup all_buys / all_sells
        self.all_buys = {}
        self.all_sells = {}

        for sym in state.order_depths.keys():
            book = state.order_depths[sym]

            buys: List[Tuple[Price, Position]] = sorted(list(book.buy_orders.items()), reverse=True)
            sells: List[Tuple[Price, Position]] = sorted(list(book.sell_orders.items()), reverse=False)

            self.all_buys[sym] = buys            
            self.all_sells[sym] = sells 

        # copy the original buy/sell books (we may change them on the fly)
        self.orig_all_buys = copy.deepcopy(self.all_buys)
        self.orig_all_sells = copy.deepcopy(self.all_sells)

        # Iterate over all the keys (the available products) contained in the order depths
        for sym in state.order_depths.keys():

            prod: Product = state.listings[sym].product

            # calc fair value
            fair_value = self.get_fair_value(sym)   
            mid_ema = self.get_ema_mid(sym)  

            if sym in ["PEARLS", "BANANAS"]:
                self.take_logic(
                    state=state,
                    sym=sym,
                    fair_value=fair_value,
                    ema=mid_ema,
                )

            if self.make_flag[sym]:
                self.make_logic(
                    state=state,
                    sym=sym,
                    fair_value=fair_value,
                )

        self.pairs_trading_logic(
            state=state, 
            sym_a="PINA_COLADAS", 
            sym_b="COCONUTS", 
        )

    def get_ema_mid(self, sym: Symbol) -> float:
        
        # calc mid_ema
        sym_history = self.DM.history[sym]
        mid_ema = sym_history[-1]["best_ema"]
        # mid_ema_span = sym_history[-1]["best_ema_span"]

        return mid_ema



    def get_fair_value(self, sym: Symbol) -> float:

        mid_ema = self.get_ema_mid(sym)

        # get large_quote_mid
        large_quote_mid, use_large_quote_mid = self.get_large_quote_mid(sym)
        

        # if conditions were good, use large_quote_mid
        if use_large_quote_mid:
            return large_quote_mid
        else: # else, use ema
            return mid_ema
    

    def get_best_buy_order(self, sym: Symbol):
        buys = self.all_buys[sym]
        if len(buys) > 0:
            return buys[0]
        else:
            return None, None

    def get_best_sell_order(self, sym: Symbol):
        sells = self.all_sells[sym]
        if len(sells) > 0:
            return sells[0]
        else:
            return None, None

    def place_take_best_buy(self, state: TradingState, sym: Symbol, max_quantity: int):

        limit = self.OM.get_rem_buy_size(state, sym)
        price, quantity = self.get_best_buy_order(sym)

        if price is not None:
            self.OM.place_buy_order(
                symbol=sym,
                price=price,
                quantity=min([limit, quantity, max_quantity]),
                is_take=True,
            )

    def place_take_best_sell(self, state: TradingState, sym: Symbol, max_quantity: int):

        limit = self.OM.get_rem_sell_size(state, sym)
        price, quantity = self.get_best_sell_order(sym)

        if price is not None:
            self.OM.place_sell_order(
                symbol=sym,
                price=price,
                quantity=min([limit, quantity, max_quantity]),
                is_take=True,
            )


    def pairs_trading_logic(self, 
            state: TradingState,
            sym_a: Symbol, 
            sym_b: Symbol,
            ):
        
        # use this to predict prices
        model = self.pairs_model
        model_m, _ = self.pairs_model.coef
        
        #assuming (price of sym_hi)/(price of sym_lo) == fair_RV
        
        OM = self.OM

        prod_a = state.listings[sym_a].product
        prod_b = state.listings[sym_b].product

        # compute maximum contract position
        max_contract_pos = int(min(
            self._position_limits[prod_a] // 1,
            self._position_limits[prod_b] // model_m,
        ))


        def sigmoid(k, x):
            return 1 / (1 + np.exp(-k*x))

        def get_target_contract_pos_sigmoid(pred_error):

            # sigmoid function is directly fit onto the error
            fit_fn = lambda x : sigmoid(0.05435088 * 2.5, x)

            ratio = (fit_fn(pred_error) - 0.5) / 0.5

            # target pos is opposite sign of error
            target_pos = -1 * ratio * max_contract_pos

            # cap the bounds
            target_pos = min(target_pos, max_contract_pos)
            target_pos = max(target_pos, -1 * max_contract_pos)

            return target_pos

        def get_target_contract_pos_custom_linear(pred_error):

            # from 15 to 50, linearly max out positions
            lb, ub = 20, 50

            ratio = (abs(pred_error) - lb) / (ub - lb)
            ratio = max(ratio, 0)

            # target pos is opposite sign of error
            target_pos = -1 * np.sign(pred_error) * ratio * max_contract_pos

            # cap the bounds
            target_pos = min(target_pos, max_contract_pos)
            target_pos = max(target_pos, -1 * max_contract_pos)

            return target_pos
        

        # def get_target_contract_pos_linear(pred_error):
        #     target_pos = -1 * (pred_error / 50) * max_contract_pos
        #     target_pos = min(target_pos, max_contract_pos)
        #     target_pos = max(target_pos, -1 * max_contract_pos)

        #     # round target_pos to nearest 5

        #     target_pos = round(target_pos) 

        #     return target_pos

        # def get_target_contract_pos_gaussian(pred_error):

        #     one_sd = 30
        #     error_sigma = abs(pred_error) / one_sd

        #     ratio = abs(NormalDist(mu=0, sigma=1).cdf(error_sigma) - 0.5) / 0.5

        #     # target pos is opposite sign of error            
        #     target_pos = -1 * np.sign(pred_error) * ratio * max_contract_pos

        #     # cap the bounds
        #     target_pos = min(target_pos, max_contract_pos)
        #     target_pos = max(target_pos, -1 * max_contract_pos)

        #     return target_pos

        # def get_target_contract_pos_ngrid(grid_lines, pred_error):

        #     one_sd = 30
        #     error_sigma = abs(pred_error) / one_sd

        #     # sanity check
        #     total_grid_ratio = sum([ratio_diff for _, ratio_diff in grid_lines])
        #     print(total_grid_ratio)
        #     assert total_grid_ratio == 1

        #     # calculate our target ratio
        #     ratio = 0
        #     for sigma, ratio_diff in grid_lines:
        #         if error_sigma > sigma:
        #             ratio += ratio_diff

        #     # target pos is opposite sign of error            
        #     target_pos = -1 * np.sign(pred_error) * ratio * max_contract_pos

        #     # normalize the bounds
        #     target_pos = min(target_pos, max_contract_pos)
        #     target_pos = max(target_pos, -1 * max_contract_pos)

        #     return target_pos
        
        
        # choose function for target_contract_pos
        grid_lines4 = [(0.5, 0.45), (1, 0.4), (2, 0.13), (3, 0.02)]
        # grid_lines3 = [(1, 0.8), (2, 0.18), (3, 0.02)]

        grid_lines = grid_lines4
        # get_target_contract_pos = lambda x : get_target_contract_pos_ngrid(grid_lines, x)
        # get_target_contract_pos = lambda x : get_target_contract_pos_gaussian(x)
        get_target_contract_pos = lambda x : get_target_contract_pos_sigmoid(x)
        # get_target_contract_pos = lambda x : get_target_contract_pos_custom_linear(x)

        
        def get_cur_contract_pos():
            """ Returns 'cur_contract_pos', 'diff_a', 'diff_b'
            """

            cur_pos_A = OM.get_expected_pos(state, prod_a)
            cur_pos_B = OM.get_expected_pos(state, prod_b)

            # if they don't have opposite signs, we aren't pairs trading
            if np.sign(cur_pos_A) * np.sign(cur_pos_B) >= 0:
                return 0, -1 * cur_pos_A, -1 * cur_pos_B
            
            else:
                contract_size_A = cur_pos_A
                contract_size_B = -1 * cur_pos_B / model_m

                # find our actual contract size
                contract_size = np.sign(contract_size_A) * min(abs(contract_size_A), abs(contract_size_B))

                # find the diffs between our contract size and A/B
                diff_A = round(contract_size - cur_pos_A)
                diff_B = round(contract_size * model_m - cur_pos_B)

                return int(contract_size), int(diff_A), int(diff_B)




        # place in its own method, to avoid accidental variable reuse
        def sell_a_buy_b():
            """  
            Check if A is OVER-priced (SELL A, BUY B)
            Sell contracts
            """

            # get book
            buys_a = self.all_buys[sym_a]
            sells_b = self.all_sells[sym_b]

            # check if trade is profitable
            if len(buys_a) > 0 and len(sells_b) > 0:
                # what orders does book display
                price_a, size_a = buys_a[0]
                price_b, size_b = sells_b[0]

                # what price should A be
                price_a_pred = model(price_b)

                # if we can SELL A at a price better than it's supposed to be at
                pred_error = price_a - price_a_pred

                # get cur/target contract pos
                target_contract_pos = get_target_contract_pos(pred_error)
                cur_contract_pos, diff_A, diff_B = get_cur_contract_pos()


                contract_diff = target_contract_pos - cur_contract_pos
                contract_diff_size = abs(contract_diff)

                # print("\nSELL")
                # print("pred", price_a, price_a_pred)
                # print("pred_error", pred_error)
                # print("target", target_contract_pos, cur_contract_pos)
                # print("diff", contract_diff)

                # if we want to sell
                if contract_diff < 0:
                    # print("try to sell", contract_diff_size)

                    # see trade limits
                    limit_a = OM.get_rem_sell_size(state, sym_a)
                    limit_b = OM.get_rem_buy_size(state, sym_b)

                    # find amt of contract that we can trade
                    trade_size_a = min(limit_a, size_a)
                    trade_size_b = min(limit_b, size_b)

                    # size of "pairs trades" that we do
                    contract_size = min([contract_diff_size, trade_size_a, trade_size_b // model_m])

                    # we trade 'contract_size' of A and 'contract_size * model_m' of B 
                    trade_size_a = int(round(contract_size))
                    trade_size_b = int(round(contract_size * model_m))

                    # sell A
                    OM.place_sell_order(
                        symbol=sym_a,
                        price=price_a,
                        quantity=trade_size_a,
                        is_take=True,
                    )
                    # buy B
                    OM.place_buy_order(
                        symbol=sym_b,
                        price=price_b,
                        quantity=trade_size_b,
                        is_take=True,
                    )

                    
        def buy_a_sell_b():
            # check if A is UNDERpriced (BUY A, SELL B)

            # get book
            sells_a = self.all_sells[sym_a]
            buys_b = self.all_buys[sym_b]

            # check if trade is profitable
            if len(sells_a) > 0 and len(buys_b) > 0:
                # what orders does book display
                price_a, size_a = sells_a[0]
                price_b, size_b = buys_b[0]

                # what price should A be
                price_a_pred = model(price_b)

                # if we can BUY A at a price better than it's supposed to be at
                pred_error = price_a - price_a_pred

                # get cur/target contract pos
                target_contract_pos = get_target_contract_pos(pred_error)
                cur_contract_pos, diff_A, diff_B = get_cur_contract_pos()

                contract_diff = target_contract_pos - cur_contract_pos
                contract_diff_size = abs(contract_diff)

                # print("\nBUY")
                # print("pred", price_a, price_a_pred)
                # print("pred_error", pred_error)
                # print("target", target_contract_pos, cur_contract_pos)
                # print("diff", contract_diff)


                # if we want to buy
                if contract_diff > 0:
                    # print("try to buy", contract_diff_size)
                    
                    # see trade limits
                    limit_a = OM.get_rem_buy_size(state, sym_a)
                    limit_b = OM.get_rem_sell_size(state, sym_b)

                    # find amt of contract that we can trade
                    trade_size_a = min(limit_a, size_a)
                    trade_size_b = min(limit_b, size_b)

                    # size of "pairs trades" that we do
                    contract_size = min([contract_diff_size, trade_size_a, trade_size_b // model_m])

                    # we trade 'contract_size' of A and 'contract_size * model_m' of B 
                    trade_size_a = int(round(contract_size))
                    trade_size_b = int(round(contract_size * model_m))
                    
                    # sell A
                    OM.place_buy_order(
                        symbol=sym_a,
                        price=price_a,
                        quantity=trade_size_a,
                        is_take=True,
                    )
                    # buy B
                    OM.place_sell_order(
                        symbol=sym_b,
                        price=price_b,
                        quantity=trade_size_b,
                        is_take=True,
                    )


        def hedge():
            ## hedge
            # if we have Q shares of stock A
            # we should have -Q * model_m shares of stock B to be hedged

            hedge_margin = 5

            # diff_A is how much A we need to trade to be hedged, same for diff_B
            cur_contract_pos, diff_A, diff_B = get_cur_contract_pos()
            trade_size_A, trade_size_B = abs(diff_A), abs(diff_B)

            # print("\nHEDGE")
            # print("cur_pos", OM.get_expected_pos(state, prod_a), OM.get_expected_pos(state, prod_b))
            # print(cur_contract_pos, diff_A, diff_B, trade_size_A, trade_size_B)

            # hedge A
            if abs(diff_A) > hedge_margin:
                if diff_A > 0: # we are too long, need to sell
                    # print("hedging sell A")
                    self.place_take_best_sell(
                        state=state,
                        sym=sym_a,
                        max_quantity=trade_size_A,
                    )
                else: # we are too short, need to buy
                    # print("hedging buy A")
                    self.place_take_best_buy(
                        state=state,
                        sym=sym_a,
                        max_quantity=trade_size_A,
                    )

            # hedge B
            if abs(diff_B) > hedge_margin * model_m:
                if diff_B > 0: # we are too long, need to sell
                    # print("hedging sell B")
                    self.place_take_best_sell(
                        state=state,
                        sym=sym_b,
                        max_quantity=trade_size_B,
                    )
                else: # we are too short, need to buy
                    # print("hedging buy B")
                    self.place_take_best_buy(
                        state=state,
                        sym=sym_b,
                        max_quantity=trade_size_B,
                    )


        sell_a_buy_b()
        buy_a_sell_b()
        hedge()
        


        

    def take_logic(self, 
            state: TradingState,
            sym: Symbol, 
            fair_value: float,
            ema: float,
            ):
        
        buys, sells = self.all_buys[sym], self.all_sells[sym]
        OM = self.OM
        prod = state.listings[sym].product

        OPP_COST = REF_OPP_COSTS[prod]


        # take orders on buy_side (we sell to existing buy orders)
        for index, (price, quantity) in enumerate(buys):
            cur_pos = OM.get_expected_pos(state, prod)
            limit = OM.get_rem_sell_size(state, sym)

            max_take_size = min(limit, quantity)

            scores = []
            for take_size in range(0, max_take_size + 1):
                # we are selling
                new_pos = cur_pos - take_size

                opp_change = OPP_COST[new_pos] - OPP_COST[cur_pos]
                edge = price - fair_value
                adj_rtn = edge * take_size + opp_change

                scores += [(adj_rtn, take_size)]

            # get the size with the optimal expected adjusted return
            if len(scores) > 0:
                adj_rtn, take_size = max(scores)
                if adj_rtn >= 0 and take_size > 0:
                    OM.place_sell_order(
                        symbol=sym,
                        price=price,
                        quantity=take_size,
                        is_take=True,
                    )

                # delete it
                top_buy_price, top_buy_size = buys[index]
                buys[index] = (top_buy_price, top_buy_size - take_size)

        # remove extraneous buys
        self.all_buys[sym] = [(p, q) for p, q in buys if q != 0]


        # take orders on sell_side (we buy from existing sellers)
        for index, (price, quantity) in enumerate(sells):
            cur_pos = OM.get_expected_pos(state, prod)
            limit = OM.get_rem_buy_size(state, sym)

            max_take_size = min(limit, quantity)

            scores = []
            for take_size in range(0, max_take_size + 1):
                # we are buying
                new_pos = cur_pos + take_size

                opp_change = OPP_COST[new_pos] - OPP_COST[cur_pos]
                edge = fair_value - price
                adj_rtn = edge * take_size + opp_change

                scores += [(adj_rtn, take_size)]

            # get the size with the optimal expected adjusted return
            if len(scores) > 0:
                adj_rtn, take_size = max(scores)
                if adj_rtn >= 0 and take_size > 0:
                    OM.place_buy_order(
                        symbol=sym,
                        price=price,
                        quantity=take_size,
                        is_take=True,
                    )

                # delete it
                top_sell_price, top_sell_size = sells[index]
                sells[index] = (top_sell_price, top_sell_size - take_size)

        # remove extraneous sells
        self.all_sells[sym] = [(p, q) for p, q in sells if q != 0]

                

    def make_logic(self, 
            state: TradingState,
            sym: Symbol, 
            fair_value: float,
            ):
        
        buys, sells = self.all_buys[sym], self.all_sells[sym]
        OM = self.OM
        prod = state.listings[sym].product


        should_penny = False
        if self.is_penny[sym]:
            # if len(buys) > 0 and len(sells) > 0:
            #     spread = sells[0][0] - buys[0][0]
            #     if spread > 2:
                    # should_penny = True
            should_penny = True
                    

        OPP_COST = REF_OPP_COSTS[prod]

        for price, quantity in buys:
            if should_penny:
                price += 1

            cur_pos = OM.get_expected_pos(state, prod)
            limit = OM.get_rem_buy_size(state, sym)

            # max_buy_size = min(limit, quantity)
            max_buy_size = limit

            scores = []
            for buy_size in range(0, max_buy_size + 1):
                # we are putting buy orders
                new_pos = cur_pos + buy_size

                opp_change = OPP_COST[new_pos] - OPP_COST[cur_pos]
                edge = fair_value - price
                adj_rtn = edge * buy_size + opp_change

                scores += [(adj_rtn, buy_size)]

            # get the size with the optimal expected adjusted return
            if len(scores) > 0:
                adj_rtn, buy_size = max(scores)
                if adj_rtn >= 0 and buy_size > 0:
                    OM.place_buy_order(
                        symbol=sym,
                        price=price,
                        quantity=buy_size,
                        is_take=False,
                    )
            

        for price, quantity in sells:
            if should_penny:
                price -= 1

            cur_pos = OM.get_expected_pos(state, prod)
            limit = OM.get_rem_sell_size(state, sym)

            # max_sell_size = min(limit, quantity)
            max_sell_size = limit

            scores = []
            for sell_size in range(0, max_sell_size + 1):
                # we are putting sell orders
                new_pos = cur_pos - sell_size

                opp_change = OPP_COST[new_pos] - OPP_COST[cur_pos]
                edge = price - fair_value
                adj_rtn = edge * sell_size + opp_change

                scores += [(adj_rtn, sell_size)]

            # get the size with the optimal expected adjusted return
            if len(scores) > 0:
                adj_rtn, sell_size = max(scores)
                if adj_rtn >= 0 and sell_size > 0:
                    OM.place_sell_order(
                        symbol=sym,
                        price=price,
                        quantity=sell_size,
                        is_take=False,
                    )
        


        # # match orders on buy-side
        # for price, quantity in buys:
        #     if should_penny:
        #         price += 1

        #     # don't carp if buy price is higher than EMA
        #     if price > fair_value:
        #         continue

        #     limit = OM.get_rem_buy_size(state, sym)
        #     if limit > 0:
        #         if self.match_size:
        #             order_quantity = min(limit, quantity)
        #         else:
        #             order_quantity = limit

        #         OM.place_buy_order(
        #             symbol=sym,
        #             price=price,
        #             quantity=order_quantity,
        #         )

        # # match orders on sell-side
        # for price, quantity in sells:
        #     if should_penny:
        #         price -= 1

        #     # don't carp if sell price is higher than EMA
        #     if price < fair_value:
        #         continue

        #     limit = OM.get_rem_sell_size(state, sym)
        #     if limit > 0:
        #         if self.match_size:
        #             order_quantity = min(limit, quantity)
        #         else:
        #             order_quantity = limit

        #         OM.place_sell_order(
        #             symbol=sym,
        #             price=price,
        #             quantity=order_quantity,
        #         )





    def get_large_quote_mid(self, sym):
        """ Checks if we should calculate the fair value using the mid of the order book
        - Gets the buy and sell orders with the maximum size
        - Checks if the maximum size is >= 15 for both buy/sell, and checks if the width is from 6 to 8 
        - If yes, return prices of max size buy/sell from order book, else return None
        """

        quote_bounds = WHALE_QUOTE_BOUNDS[sym]
        spread_lb, spread_ub = quote_bounds["spread"]
        size_lb, size_ub = quote_bounds["size"]


        buys, sells = self.orig_all_buys[sym], self.orig_all_sells[sym]
        
        buy_price, buy_size = max(buys, key=lambda x:x[1])
        sell_price, sell_size = max(sells, key=lambda x:x[1])

        spread = sell_price - buy_price
        
        should_use = \
            spread_lb <= spread <= spread_ub and \
            size_lb <= buy_size <= size_ub and \
            size_lb <= sell_size <= size_ub
        
        return (buy_price + sell_price) / 2, should_use



    def close_positions(self, state: TradingState):
        """ Closes out our position at the end of the game
        - was previously used since IMC's engine uses weird fair values
        """
        OM = self.OM

        for prod, pos in state.position.items():
            if pos < 0:
                OM.place_buy_order(symbol=prod, price=1e9, quantity=1, is_take=False)
            elif pos > 0:
                OM.place_sell_order(symbol=prod, price=0, quantity=1, is_take=False)



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

            # history length
            "history_len": len(self.DM.history["BANANAS"]),
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
    
    
    def __init__(self, symbols, position_limits, listings):
        self._buy_orders : Dict[Symbol, List[Order]] = {sym: [] for sym in symbols}
        self._sell_orders : Dict[Symbol, List[Order]] = {sym: [] for sym in symbols}
        self._position_limits = position_limits
        self._expected_change : Dict[Symbol, Position] = {sym: 0 for sym in symbols}
        self._listings: List[Listing] = listings


    def place_buy_order(self, symbol: Symbol, price: Price, quantity: int, is_take: bool):
        """ Queues a buy order

        If this order is a taking order, then it should update our expected position
        """
        self._buy_orders[symbol] += [Order(symbol, price, quantity)]
        
        if is_take:
            self._update_expected_change(self._listings[symbol].product, +1 * quantity)

    def place_sell_order(self, symbol: Symbol, price: Price, quantity: int, is_take: bool):
        """ Queues a sell order
        """
        self._sell_orders[symbol] += [Order(symbol, price, quantity)]

        if is_take:
            self._update_expected_change(self._listings[symbol].product, -1 * quantity)


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


    def _update_expected_change(self, prod: Product, change: int) -> None:
        self._expected_change[prod] += change


    def get_expected_pos(self, state: TradingState, prod: Product) -> int:
        """ Returns expected position of a product, given that we are 
        """

        return state.position[prod] + self._expected_change[prod]



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