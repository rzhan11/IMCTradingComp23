from datamodel import *
from pathlib import Path
from bot import Trader
from market import Market
import copy

""" constants """

MAX_TIME = 500
TIME_STEP = 100

trader_position_limits : Dict[Product, int] = {
    "BANANAS": 20,
    "PEARLS": 20,
    "SEASHELLS": float("inf")
}

market_position_limits = { k: float("inf") for k in trader_position_limits.keys() }

listings : Dict[Symbol, Listing] = {
    "BANANAS": Listing(
        symbol = "BANANAS",
        product = "BANANAS",
        denomination = 1,
    ),
    "PEARLS": Listing(
        symbol = "PEARLS",
        product = "PEARLS",
        denomination = 1,
    ),
}

products = list(trader_position_limits.keys())
symbols = list(listings.keys())

""" player parameters """

players = [
    Market(player_id=200, position_limits=market_position_limits),
    Trader(player_id=100, position_limits=trader_position_limits),
]

# players must have unique ids
assert len(players) == len(set([p.player_id for p in players])), "Player ids not unique"


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

    state.init_game(
        products=products,
        symbols=symbols,
        listings=listings,
        players=players,
    )



    for cur_time in range(0, MAX_TIME, TIME_STEP):

        eprint(f"Time: {cur_time}")
        state.timestamp = cur_time


        for player in players:
            
            state_player_copy = state.get_player_copy(pid=player.player_id)

            print(state._TradingState__books)
            print(state_player_copy._TradingState__books)

            # run trader actions
            orders = player.run(state_player_copy)
            orders = {k: [el.copy() for el in v] for k, v in orders.items()}

            eprint(f"Player {player.player_id} orders:", orders)

            # apply trades to trader actions
            state.apply_orders(pid=player.player_id, orders=orders)






if __name__ == "__main__":
    main()