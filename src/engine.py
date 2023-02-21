from datamodel import *

import argparse
import importlib
import sys
from pathlib import Path

import traceback


def main(package: str):
    # init world state
    GS = importlib.import_module(".game_settings", package=package)

    fair_obj = GS.FAIR


    empty_book: Dict[Symbol, OrderDepth] = {
        sym: OrderDepth() for sym in GS.SYMBOLS
    }

    state: TradingState = TradingState(
        timestamp=0,
        listings=GS.LISTINGS,
        order_depths=empty_book,
        own_trades={},
        market_trades={},
        position={},
        observations={},
    )

    state.init_game(
        products=GS.PRODUCTS,
        symbols=GS.SYMBOLS,
        listings=GS.LISTINGS,
        players=GS.PLAYERS,
    )



    for cur_turn, cur_time in enumerate(range(0, GS.MAX_TIME, GS.TIME_STEP)):

        eprint(f"Time: {cur_time}, Turn: {cur_turn}")
        state.timestamp = cur_time

        fair_obj.update_fairs(timestamp=cur_time, turn=cur_turn)

        for player in GS.PLAYERS:

            pid = player._player_id
            
            # remove expired orders
            state.remove_player_orders(pid=pid)
            state_player_copy = state.get_player_copy(pid=pid)

            eprint("Books:")
            for sym, book in state._TradingState__books.items():
                eprint("BIDS")
                for b in book.buys:
                    eprint(b)
                eprint("ASKS")
                for b in book.sells:
                    eprint(b)

            # run trader actions
            orders = player.run(state_player_copy)
            orders = {k: [el.copy() for el in v] for k, v in orders.items()}

            eprint(f"Player {pid} orders:", orders)

            # apply trades to trader actions
            state.apply_orders(pid=pid, orders=orders)


            # remove expired trades (from last turn)
            state.remove_player_trades(pid=pid)

            state.validate()



    # caclculate pnls
    pnls = {}

    fairs = fair_obj.fairs
    final_positions = state.get_positions()

    for player, all_pos in final_positions.items():
        pnls[player] = 0
        for prod, pos in all_pos.items():
            pnls[player] += pos * fairs[prod]


    # print pnls
    print("\n"*5)
    eprint("Final positions:")
    for player, all_pos in final_positions.items():
        eprint(f"{player}, pnl: {pnls[player]}, {all_pos}")

    





if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(
        prog = 'IMC Trading 23 Game Engine',
        description = 'This file runs the game.'
    )

    parser.add_argument("-p", "--package", required=True)
    parser.add_argument("-lf", "--log_to_file", action="store_true")

    args = parser.parse_args()

    if args.log_to_file:
        log_file = Path("../replays/local.log")

        print(f"Writing to {log_file} ...")

        with open(log_file, "w") as f:
            old_stdout, old_stderr = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = f, f
            try:
                main(
                    package=args.package
                )
            except:
                traceback.print_exc()
                sys.stdout, sys.stderr = old_stdout, old_stderr
                print(
                    "\n"*3,
                    "-"*50, 
                    "LOG FILE HAS ERROR", 
                    "-"*50, 
                    "\n",
                    sep="\n"
                )
                traceback.print_exc()
                
    else:
        print("Writing to stdout...")
        main(
            package=args.package
        )