import json
from typing import Dict, List
from json import JSONEncoder

import copy

Time = int
Symbol = str
Product = str
Position = int
UserId = str
Observation = int


class Listing:
    def __init__(self, symbol: Symbol, product: Product, denomination: Product):
        self.symbol = symbol
        self.product = product
        self.denomination = denomination

    def copy(self):
        return Listing(
            self.symbol,
            self.product,    
            self.denomination,    
        )


class Order:
    def __init__(self, symbol: Symbol, price: int, quantity: int) -> None:
        self.symbol = symbol
        self.price = price
        self.quantity = quantity

    def __str__(self) -> str:
        return "(" + self.symbol + ", " + str(self.price) + ", " + str(self.quantity) + ")"

    def __repr__(self) -> str:
        return "(" + self.symbol + ", " + str(self.price) + ", " + str(self.quantity) + ")"

    def copy(self):
        return Order(
            self.symbol, 
            self.price, 
            self.quantity
        )
    

class OrderDepth:
    def __init__(self):
        self.buy_orders: Dict[int, int] = {}
        self.sell_orders: Dict[int, int] = {}

    def copy(self):
        od = OrderDepth()
        od.buy_orders = copy.deepcopy(self.buy_orders)
        od.sell_orders= copy.deepcopy(self.sell_orders)
        return od


    def label_paper(self, id):
        self.buy_orders = {(k, id, False): v for k, v in self.buy_orders}
        self.sell_orders = {(k, id, False): v for k, v in self.sell_orders}

    def unlabel_paper(self):
        self.buy_orders = {k: v for (k, _, _), v in self.buy_orders}
        self.sell_orders = {k: v for (k, _, _), v in self.sell_orders}

    def clear_trader_orders(self):
        self.buy_orders = {(k, id, is_trader): v for (k, id, is_trader), v in self.buy_orders if (not is_trader)}
        self.sell_orders = {(k, id, is_trader): v for (k, id, is_trader), v in self.sell_orders if (not is_trader)}



class Trade:
    def __init__(self, symbol: Symbol, price: int, quantity: int, buyer: UserId = "", seller: UserId = "") -> None:
        self.symbol = symbol
        self.price: int = price
        self.quantity: int = quantity
        self.buyer = buyer
        self.seller = seller

    def __str__(self) -> str:
        return "(" + self.symbol + ", " + self.buyer + " << " + self.seller + ", " + str(self.price) + ", " + str(self.quantity) + ")"

    def __repr__(self) -> str:
        return "(" + self.symbol + ", " + self.buyer + " << " + self.seller + ", " + str(self.price) + ", " + str(self.quantity) + ")"

    def copy(self):
        return Trade(
            self.symbol,
            self.price,
            self.quantity,
            self.buyer,
            self.seller,
        )










class TradingState(object):
    def __init__(self,
                 timestamp: Time,
                 listings: Dict[Symbol, Listing],
                 order_depths: Dict[Symbol, OrderDepth],
                 own_trades: Dict[Symbol, List[Trade]],
                 market_trades: Dict[Symbol, List[Trade]],
                 position: Dict[Product, Position],
                 observations: Dict[Product, Observation]):
        self.timestamp = timestamp
        self.listings = listings
        self.order_depths = order_depths
        self.own_trades = own_trades
        self.market_trades = market_trades
        self.position = position
        self.observations = observations

        self.__id_counter = 0

    def fresh_id(self):
        self.__id_counter += 1
        return self.__id_counter

        
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True)

    def copy(self):
        state = TradingState(
            self.timestamp,
            listings={k: v.copy() for k, v in self.listings},
            order_depths={k: v.copy() for k, v in self.order_depths},
            own_trades={k: [el.copy() for el in v] for k, v in self.order_depths},
            market_trades={k: [el.copy() for el in v] for k, v in self.order_depths},
            position=copy.deepcopy(self.position),
            observations=copy.deepcopy(self.observations),
        )

        del state.__id_counter
        return state


    # labels markets as maker vs paper
    def label_papers(self):
        for sym, book in self.order_depths.items():
            book.label_paper(self.fresh_id)

    # unlabels markets as maker vs paper
    def unlabel_papers(self):
        for sym, book in self.order_depths.items():
            book.unlabel_paper()

    # removes all makers from books
    def clear_trader_orders(self):
        for sym, book in self.order_depths.items():
            book.clear_trader_orders()





    # participant
    def match_orders(self, all_orders: List[Order], is_trader):
        if is_trader:
            order_name = TRADER_NAME
        else:
            order_name = ""

        trades: List[Trade] = []

        # match against the book
        for ord in all_orders:
            if ord.quantity > 0: # trader buys, match against sellers
                sells = self.order_depths[ord.symbol].sell_orders
                book = sorted(list(sells.items()), reverse=False)
                for (book_price, id, is_trader), book_size in book.items():
                    if ord.price >= book_price:
                        trade_size = min(book_size, ord.quantity)

                        # record trade 
                        trades += [Trade(ord.symbol, ord.price, trade_size, buyer=order_name, seller="")]

                        # update order
                        ord.quantity -= trade_size

                        # update book
                        sells[book_price] -= trade_size
                        if sells[book_price] == 0:
                            del sells[book_price]

                        if ord.quantity == 0:
                            break
                    else:
                        break

                # want to buy, add as order
                if ord.quantity != 0:
                    buys = self.order_depths[ord.symbol].buy_orders
                    buys[ord.price] = ord.quantity + buys.get(ord.price, default=0)


            elif ord.quantity < 0: # trader sells, match against buyers
                buys = self.order_depths[ord.symbol].buy_orders
                book = sorted(list(buys.items()), reverse=True) # want highest at top
                for book_price, book_size in book.items():
                    if ord.price >= book_price:
                        trade_size = min(book_size, -1 * ord.quantity)

                        # record trade 
                        trades += [Trade(ord.symbol, ord.price, trade_size, buyer="", seller=order_name)]

                        # update order (use negative size)
                        ord.size -= -1 * trade_size

                        # update book
                        buys[book_price] -= trade_size
                        if buys[book_price] == 0:
                            del buys[book_price]

                        if ord.size == 0:
                            break
                    else:
                        break

                # want to sell, add as order
                if ord.quantity != 0:
                    sells = self.order_depths[ord.symbol].sell_orders
                    sells[ord.price] = (-1 * ord.quantity) + sells.get(ord.price, default=0)


        for t in trades:
            if t.buyer == TRADER_NAME or t.seller == TRADER_NAME:
                # record in own_trades
                self.own_trades[t.symbol] += [t]
                
                # update positions
                prod = listings[t.symbol].product
                if t.buyer == TRADER_NAME: # bought
                    self.position[prod] += t.quantity
                else: # sold
                    self.position[prod] += -1 * t.quantity
            else: # record in market_trades
                self.market_trades[t.symbol] += [t]


    
    
class ProsperityEncoder(JSONEncoder):
        def default(self, o):
            return o.__dict__



""" constants """

MAX_TIME = 200000
TIME_STEP = 100
TRADER_NAME = "SUBMISSION"

max_positions : Dict[Product, int] = {
    "BANANAS": 20,
    "PEARLS": 20,
}

# products
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

products = list(max_positions.keys())
symbols = list(listings.keys())