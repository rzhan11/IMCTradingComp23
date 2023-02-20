import json
from typing import Dict, List
from json import JSONEncoder
import bisect

import copy

Time = int
Symbol = str
Product = str
Position = int
UserId = str
Observation = int
PlayerID = int
OrderID = int


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

    def to_book_order(self, order_id, player_id):
        assert self.quantity != 0
        if self.quantity > 0:
            return BuyOrder(
                symbol=self.symbol,
                price=self.price,
                quantity=self.quantity,
                order_id=order_id,
                player_id=player_id,
            )
        else:
            return SellOrder(
                symbol=self.symbol,
                price=self.price,
                quantity=-1 * self.quantity,
                order_id=order_id,
                player_id=player_id,
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


class BookOrder:
    def __init__(self, symbol : Symbol, price : int, quantity : int, order_id : OrderID, player_id : PlayerID):
         # book orders always have positive quantities
        assert quantity > 0

        self.symbol = symbol
        self.price = price
        self.quantity = quantity
        self.order_id = order_id
        self.player_id = player_id

    def __eq__(self, other):
        return self.price == other.price and self.quantity == other.quantity

class BuyOrder(BookOrder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_buy = True

    def __lt__(self, other):
        return self.price > other.price or (self.price == other.price and self.player_id < other.player_id)

class SellOrder(BookOrder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_buy = False

    def __lt__(self, other):
        return self.price < other.price or (self.price == other.price and self.player_id < other.player_id)

class Book:
    def __init__(self, buys: List[BuyOrder], sells: List[SellOrder]):
        self.buys = buys
        self.sells = sells

    def to_order_depth(self):
        od = OrderDepth()
        od.buy_orders = {k.price: k.quantity for k in self.buys}
        od.sell_orders = {k.price: k.quantity for k in self.sells}
        return od

    def remove_player_orders(self, pid):
        """
        Removes all orders placed by pid
        """
        self.buys = [ord for ord in self.buys if ord.player_id != pid]
        self.sells = [ord for ord in self.sells if ord.player_id != pid]


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
                 observations: Dict[Product, Observation],
        ):

        self.timestamp = timestamp
        self.listings = listings
        self.order_depths = order_depths
        self.own_trades = own_trades
        self.market_trades = market_trades
        self.position = position
        self.observations = observations

        """ extra fields """
        self.__position_limits : Dict[PlayerID, Dict[Product, int]] = {}
        self.__positions : Dict[PlayerID, Dict[Product, int]] = {}
        self.__trades : List[Trade] = []
        self.__books : Dict[Symbol, Book] = {}
        self.__id_counter : int = 0


    def init_game(self, products, symbols, listings, players):
        """ Initializes game state, should be called once per game

        Args:
            products (_type_): _description_
            symbols (_type_): _description_
            listings (_type_): _description_
            players (_type_): _description_
        """
        self.__products = products
        self.__symbols = symbols
        self.__listings = listings
        self.__position_limits = {p.id : p.position_limits for p in players}



    def fresh_order_id(self):
        self.__id_counter += 1
        return self.__id_counter

        
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True)

    def copy(self):
        state = TradingState(
            timestamp=self.timestamp,
            listings={k: v.copy() for k, v in self.listings},
            order_depths={},
            own_trades={},
            market_trades={},
            position={},
            observations={},
        )
        
        # copy additional fields
        state.__position_limits = { 
            pid: copy.deepcopy(pos) 
            for pid, pos in self.__position_limits.items() 
        }
        state.__positions = { 
            pid: copy.deepcopy(pos) 
            for pid, pos in self.__positions.items() 
        }
        state.__trades = [trade.copy() for trade in self.__trades]
        state.__books = { sym: book.copy for sym, book in self.__books.items() }
        state.__id_counter = self.__id_counter

        return state


    def get_player_copy(self, pid : PlayerID):
        """ Returns a copy of this state for the specified player

        Args:
            pid (int): player id
        """

        # make copy
        self = self.copy()


        # create position
        self.position = self.__positions[pid]
        
        # create own_trades / market_trades
        for trade in self.__trades:
            # sort into own/market trades
            if trade.buyer == pid or trade.seller == pid:
                self.own_trades[trade.symbol] = self.own_trades.get(trade.symbol, default=[]) + [trade]
            else:
                self.market_trades[trade.symbol] = self.market_trades.get(trade.symbol, default=[]) + [trade]

            # remap the buyer/seller tags
            if trade.buyer == pid:
                trade.buyer = "SUBMISSION"
            else:
                trade.buyer = ""

            if trade.seller == pid:
                trade.seller = "SUBMISSION"
            else:
                trade.seller = ""


        # create order_depths
        for sym, book in self.__books.items():
            # remove player orders
            book.remove_player_orders(pid)
            self.order_depths[sym] = book.to_order_depth()

        

        # remove extraneous fields
        del self.__positions
        del self.__trades
        del self.__books
        del self.__id_counter

        return self
        



    # return a list of trader books
    def apply_orders(self, pid, new_orders: Dict[Symbol, List[Order]]):

        buy_total = {0 for prod in self.__products.keys()}
        sell_total = {0 for prod in self.__products.keys()}

        limits = self.__position_limits[pid]

        allowed_orders: List[BookOrder] = []

        for sym, orders in new_orders.items():
            for ord in orders:
                assert ord.symbol == sym
                assert(type(ord.quantity) == int)

                prod = self.__listings[sym].product
                
                works = True

                # if we would exceed the position limit, ignore this order
                if ord.quantity > 0:
                    if buy_total[prod] + ord.quantity > limits[prod]:
                        eprint("ERROR - Ignoring order {ord}")
                        works = False
                    else:
                        buy_total[prod] += ord.quantity
                elif ord.quantity < 0:
                    if sell_total[prod] + ord.quantity < -limits[prod]:
                        eprint("ERROR - Ignoring order {ord}")
                        works = False
                    else:
                        sell_total[prod] += ord.quantity
                else:
                    # ord.quantity = 0
                    works = False
                

                # record successful order
                if works:
                    allowed_orders += [ord.to_book_order(order_id=self.fresh_order_id(), player_id=pid)]

        # match allowed orders against the book
        self.match_orders(pid=pid, orders=allowed_orders)



    # participant
    def match_orders(self, orders: List[BookOrder]):
        new_trades: List[Trade] = []

        # match against the book
        for ord in orders:
            if ord.is_buy: # trader buys, match against sellers
                sells = self.__books[ord.symbol].sells
                new_sells = []
                for book_ind, book_ord in sells:
                    if ord.price >= book_ord.price:
                        trade_size = min(book_ord.quantity, ord.quantity)

                        # record trade 
                        new_trades += [Trade(ord.symbol, ord.price, trade_size, buyer=orders.player_id, seller=book_ord.player_id)]

                        # update order
                        ord.quantity -= trade_size

                        # update book
                        book_ord.quantity -= trade_size
                        if book_ord.quantity > 0:
                            new_sells += [book_ord]

                        if ord.quantity == 0:
                            # add rest of the original sells (not including this one)
                            new_sells += sells[book_ind + 1:]
                            break
                    else:
                        # add rest of the original sells (including this one)
                        new_sells += sells[book_ind:]

                # want to buy, add as order
                if ord.quantity != 0:
                    buys = self.__books[ord.symbol].buys
                    self.__books[ord.symbol].buys = bisect.insort(buys, ord)


            else: # trader sells, match against buyers
                buys = self.__books[ord.symbol].buys
                new_buys = []
                for book_ind, book_ord in buys:
                    if ord.price >= book_ord.price:
                        trade_size = min(book_ord.quantity, ord.quantity)

                        # record trade 
                        new_trades += [Trade(ord.symbol, ord.price, trade_size, buyer=orders.player_id, seller=book_ord.player_id)]

                        # update order
                        ord.quantity -= trade_size

                        # update book
                        book_ord.quantity -= trade_size
                        if book_ord.quantity > 0:
                            new_buys += [book_ord]

                        if ord.quantity == 0:
                            # add rest of the original buys (not including this one)
                            new_buys += buys[book_ind + 1:]
                            break
                    else:
                        # add rest of the original buys (including this one)
                        new_buys += buys[book_ind:]

                # want to buy, add as order
                if ord.quantity != 0:
                    sells = self.__books[ord.symbol].sells
                    self.__books[ord.symbol].sells = bisect.insort(sells, ord)

        # add trades to state
        self.__trades += new_trades


    
    
class ProsperityEncoder(JSONEncoder):
        def default(self, o):
            return o.__dict__


""" utility functions """



def eprint(*args, **kwargs):
    print("[ENG]", *args, **kwargs)


