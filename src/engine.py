from datamodel import *
from pathlib import Path
from bot import Trader
from market import Market
import copy




def main():
    # init world state

    empty_book: Dict[Symbol, OrderDepth] = {
        sym: OrderDepth() for sym in symbols
    }

    state: TradingState = TradingState(
        timestamp=0,
        listings=listings,
        order_depths=empty_book,
        own_trades={},
        market_trades={},
        position={},
        observations={},
    )
    state.label_papers()


    trader = Trader()
    market = Market()

    for t in range(0, MAX_TIME, TIME_STEP):

        print(f"Engine time: {t}")
        state.timestamp = t

        # run market actions
        market.run(state)

        # cleanup trader actions
        state.clear_trader_orders()
        state.unlabel_papers()

        # run trader actions
        trader_actions = trader.run(state.copy())
        trader_actions = {k: [el.copy() for el in v] for k, v in trader_actions.items()}

        # label papers
        state.label_papers(1)

        # reset trades
        state.own_trades = {}
        state.market_trades = {}

        print("Trader actions", trader_actions)
        # add trader actions to book


        # apply trades to trader actions
        apply_trader_actions(state, trader_actions)






def eprint(*args, **kwargs):
    print("[ENG]", *args, **kwargs)


def is_trader_order(order : List[int]):
    pass


def remove_trader_actions(state):
    pass


# return a list of trader books
def apply_trader_actions(state : TradingState, trader_actions: Dict[Symbol, List[Order]]):

    trader_buy_limit = copy.deepcopy(state.position)
    trader_sell_limit = copy.deepcopy(state.position)

    all_orders: List[Order] = []

    for sym, orders in trader_actions.items():
        for ord in orders:
            assert ord.symbol == sym
            assert(type(ord.quantity) == int)

            prod = listings[sym].product
            
            works = True

            # if we would exceed the position limit, ignore this order
            if ord.quantity > 0:
                if trader_buy_limit[prod] + ord.quantity > max_positions[prod]:
                    eprint("ERROR - Ignoring order {ord}")
                    works = False
                else:
                    trader_buy_limit[prod] += ord.quantity
            elif ord.quantity < 0:
                if trader_sell_limit[prod] + ord.quantity < -max_positions[prod]:
                    eprint("ERROR - Ignoring order {ord}")
                    works = False
                else:
                    trader_sell_limit[prod] += ord.quantity

            # record successful order
            if works:
                all_orders += [ord]

    state.match_orders(all_orders, is_trader=True)

    return all_orders








if __name__ == "__main__":
    main()