from abc import ABC, abstractmethod
from deepdiff import DeepDiff
from datamodel import OrderDepth, TradingState, Order, Trade, Listing, Symbol


class AbstractBot(ABC):

    # eval unit test
    def eval_unit_test(self, state, exp_state):


        
        # clean trades
        for sym, trade_list in exp_state.own_trades.items():
            for trade in trade_list:
                trade.clean()
        for sym, trade_list in exp_state.market_trades.items():
            for trade in trade_list:
                trade.clean()

        # check that all attributes are expected
        for attr in ["listings", "order_depths", "own_trades", "market_trades", "position", "observations"]:
            exp = getattr(exp_state, attr)
            rec = getattr(state, attr)

            assert exp == rec, "\n".join([
                f"timestamp: {exp_state.timestamp}, attr: `{attr}`",
                f"exp: {exp}",
                f"rec: {rec}",
                f"diff: {DeepDiff(exp, rec)}",
            ])