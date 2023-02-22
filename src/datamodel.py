import json
from typing import Dict, List
from json import JSONEncoder
import bisect
from abc import ABC

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

    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False
    
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

    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False

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
    def __init__(self, buy_orders={}, sell_orders={}):
        self.buy_orders: Dict[int, int] = buy_orders
        self.sell_orders: Dict[int, int] = sell_orders

    def __str__(self) -> str:
        return f"(BIDS:{self.buy_orders}, ASKS:{self.sell_orders})"

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False

    def copy(self):
        return OrderDepth(
            buy_orders=copy.deepcopy(self.buy_orders),
            sell_orders=copy.deepcopy(self.sell_orders),
        )


class Trade:
    def __init__(self, 
            symbol: Symbol, 
            price: int, 
            quantity: int, 
            buyer: UserId = "", 
            seller: UserId = "",
            timestamp : Time = None, 
            taker_pid : PlayerID = None,
            ) -> None:
        self.symbol = symbol
        self.price: int = price
        self.quantity: int = quantity
        self.buyer = buyer
        self.seller = seller
        self.__timestamp = timestamp
        self.__taker_pid = taker_pid

    def __str__(self) -> str:
        return f"({self.symbol}, {self.buyer} << {self.seller}, {self.price}, {self.quantity})"

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False

    def copy(self):
        return Trade(
            symbol=self.symbol,
            price=self.price,
            quantity=self.quantity,
            buyer=self.buyer,
            seller=self.seller,
            timestamp=self.__timestamp,
            taker_pid=self.__taker_pid,
        )

    def clean(self):
        self.timestamp = self.__timestamp
        del self.__timestamp
        del self.__taker_pid

    def is_expired(self, cur_timestamp: Time, cur_pid: PlayerID) -> bool:
        return cur_timestamp > self.__timestamp and cur_pid == self.__taker_pid


""" custom classes """

class BookOrder(ABC):
    def __init__(self, symbol : Symbol, price : int, quantity : int, order_id : OrderID, player_id : PlayerID):
         # book orders always have positive quantities
        assert quantity > 0, f"Bad BookOrder {symbol, price, quantity, order_id, player_id}"

        self.symbol = symbol
        self.price = price
        self.quantity = quantity
        self.order_id = order_id
        self.player_id = player_id
        self.is_buy = None

    def __str__(self) -> str:
        if self.is_buy:
            s = "BUY"
        else:
            s = "SELL"

        return f"([{s}] {self.symbol}, ${self.price}, q: {self.quantity}, pid: {self.player_id}, oid: {self.order_id})"

    def __repr__(self) -> str:
        return str(self)


    def copy_subclass(self, Constructor):
        return Constructor(
            symbol=self.symbol,
            price=self.price,
            quantity=self.quantity,
            order_id=self.order_id,
            player_id=self.player_id,
        )


    def __eq__(self, other):
        return self.price == other.price and self.quantity == other.quantity

class BuyOrder(BookOrder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_buy = True

    def copy(self):
        return self.copy_subclass(BuyOrder)

    def __lt__(self, other):
        return self.price > other.price or (self.price == other.price and self.player_id < other.player_id)

class SellOrder(BookOrder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_buy = False

    def copy(self):
        return self.copy_subclass(SellOrder)

    def __lt__(self, other):
        return self.price < other.price or (self.price == other.price and self.player_id < other.player_id)

class Book:
    def __init__(self, buys: List[BuyOrder], sells: List[SellOrder]):
        self.buys = buys
        self.sells = sells

    def __str__(self) -> str:
        return f"(BIDS:{self.buys}, ASKS:{self.sells})"

    def __repr__(self) -> str:
        return str(self)

    def copy(self):
        return Book(
            buys=[b.copy() for b in self.buys],
            sells=[b.copy() for b in self.sells],
        )

    def to_order_depth(self):
        buy_orders = {}
        for order in self.buys:
            buy_orders[order.price] = buy_orders.get(order.price, 0) + order.quantity

        sell_orders = {}
        for order in self.sells:
            sell_orders[order.price] = sell_orders.get(order.price, 0) + order.quantity
        
        return OrderDepth(
            buy_orders=buy_orders,
            sell_orders=sell_orders,
        )

    def remove_player_orders(self, pid):
        """
        Removes all orders placed by pid
        """
        self.buys = [ord for ord in self.buys if ord.player_id != pid]
        self.sells = [ord for ord in self.sells if ord.player_id != pid]













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

        # """ extra fields """
        # self.__pids : List[PlayerID] = None
        # self.__position_limits : Dict[PlayerID, Dict[Product, int]] = None
        # self.__positions : Dict[PlayerID, Dict[Product, int]] = None
        # self.__trades : List[Trade] = None
        # self.__books : Dict[Symbol, Book] = None
        # self.__id_counter : int = None
        # self.__fairs = None


    def init_game(self, products, symbols, listings, players, fairs):
        """ Initializes game state, should be called once per game

        Args:
            products (_type_): _description_
            symbols (_type_): _description_
            listings (_type_): _description_
            players (_type_): _description_
        """
        self.__id_counter : int = 0
        self.__products : List[PlayerID] = products
        self.__symbols : List[Symbol] = symbols
        self.__listings : List[Listing] = listings
        self.__fairs = fairs

        self.__trades : List[Trade] = []
        self.__books : Dict[Symbol, Book] = {sym: Book(buys=[], sells=[]) for sym in symbols}

        self.__pids : List[PlayerID] = [p._player_id for p in players]
        self.__position_limits : Dict[PlayerID, Dict[Product, int]] = {p._player_id : p._position_limits for p in players}
        # init positions to 0
        self.__positions : Dict[PlayerID, Dict[Product, int]] = { 
            pid : {prod: 0 for prod in self.__products} 
            for pid in self.__pids
        }



    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False


    def fresh_order_id(self):
        self.__id_counter += 1
        return self.__id_counter

        
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True)

    def get_positions(self):
        return self.__positions


    def remove_player_orders(self, pid : PlayerID):
        # remove player orders
        for sym, book in self.__books.items():
            book.remove_player_orders(pid)


    def remove_player_trades(self, pid : PlayerID):
        self.__trades = [
            trade 
            for trade in self.__trades 
            if not trade.is_expired(cur_timestamp=self.timestamp, cur_pid=pid)
        ]

    def update_fairs(self, turn : int):
        self.__fairs.update_fairs(timestamp=self.timestamp, turn=turn)

    def get_pnls(self) -> Dict[PlayerID, int]:

        pnls = {}

        for player, all_pos in self.__positions.items():
            pnls[player] = 0
            for prod, pos in all_pos.items():
                pnls[player] += pos * self.__fairs.fairs[prod]

        return pnls


    def get_player_copy(self, pid : PlayerID):
        """ Returns a copy of this state for the specified player

        Args:
            pid (int): player id
        """

        # own_trades + market_trades
        own_trades = {sym: [] for sym in self.__symbols}
        market_trades = {sym: [] for sym in self.__symbols}

        # create own_trades / market_trades
        for trade in self.__trades:
            trade = trade.copy()

            # sort into own/market trades
            if trade.buyer == pid or trade.seller == pid:
                own_trades[trade.symbol] += [trade]
            else:
                market_trades[trade.symbol] += [trade]

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
        order_depths = { 
            sym: book.copy().to_order_depth()
            for sym, book in self.__books.items() 
        }
            
        position = copy.deepcopy(self.__positions[pid])
        del position["SEASHELLS"]


        state = TradingState(
            timestamp=self.timestamp,
            listings={sym : listing.copy() for sym, listing in self.__listings.items()},
            order_depths=order_depths,
            own_trades=own_trades,
            market_trades=market_trades,
            position=position,
            observations=copy.deepcopy({}),
        )

        # cleanup state
        state.clean()

        return state
        

    def clean(self):

        # cleanup trades
        for sym, trade_list in self.own_trades.items():
            for trade in trade_list:
                trade.clean()

        for sym, trade_list in self.market_trades.items():
            for trade in trade_list:
                trade.clean()


        # cleanup state
        # del self.__id_counter
        # del self.__products
        # del self.__symbols
        # del self.__listings
        # del self.__fairs

        # del self.__trades
        # del self.__books

        # del self.__pids
        # del self.__position_limits
        # del self.__positions



    # return a list of trader books
    def apply_orders(self, pid, orders: Dict[Symbol, List[Order]]):

        buy_order_total = {prod: 0 for prod in self.__products}
        sell_order_total = {prod: 0 for prod in self.__products}

        position = self.__positions[pid]
        limits = self.__position_limits[pid]

        allowed_orders: List[BookOrder] = []

        for sym, order_list in orders.items():
            for ord in order_list:
                assert ord.symbol == sym
                assert(type(ord.quantity) == int)

                prod = self.__listings[sym].product
                
                works = True

                # if we would exceed the position limit, ignore this order
                if ord.quantity > 0:
                    new_quantity = position[prod] + buy_order_total[prod] + ord.quantity
                    if new_quantity > limits[prod]:
                        eprint(f"ERROR - Ignoring order {ord}")
                        works = False
                    else:
                        buy_order_total[prod] += ord.quantity
                elif ord.quantity < 0:
                    new_quantity = position[prod] + sell_order_total[prod] + ord.quantity
                    if new_quantity < -limits[prod]:
                        eprint(f"ERROR - Ignoring order {ord}")
                        works = False
                    else:
                        sell_order_total[prod] += ord.quantity
                else:
                    # this means that ord.quantity = 0
                    works = False
                

                # record successful order
                if works:
                    allowed_orders += [ord.to_book_order(order_id=self.fresh_order_id(), player_id=pid)]

        # match allowed orders against the book
        self.match_orders(orders=allowed_orders)



    # participant
    def match_orders(self, orders: List[BookOrder]):
        new_trades: List[Trade] = []

        # match against the book
        for ord in orders:
            new_book_diff = []
            if ord.is_buy:
                book_same = self.__books[ord.symbol].buys
                book_diff = self.__books[ord.symbol].sells
                will_trade = lambda price, book_price : price >= book_price
                get_buyer = lambda ord, book : ord
                get_seller = lambda ord, book : book
            else:
                book_same = self.__books[ord.symbol].sells
                book_diff = self.__books[ord.symbol].buys
                will_trade = lambda price, book_price : price <= book_price
                get_buyer = lambda ord, book : book
                get_seller = lambda ord, book : ord

            for book_ind, book_ord in enumerate(book_diff):
                if will_trade(ord.price, book_ord.price):
                    trade_size = min(book_ord.quantity, ord.quantity)

                    # record trade
                    new_trades += [Trade(
                        symbol=ord.symbol, 
                        price=book_ord.price, 
                        quantity=trade_size, 
                        buyer=get_buyer(ord.player_id, book_ord.player_id), 
                        seller=get_seller(ord.player_id, book_ord.player_id),
                        timestamp=self.timestamp,
                        taker_pid=ord.player_id,
                    )]

                    # update order
                    ord.quantity -= trade_size

                    # update book
                    book_ord.quantity -= trade_size
                    if book_ord.quantity > 0:
                        new_book_diff += [book_ord]

                    if ord.quantity == 0:
                        # add rest of the original sells (not including this one)
                        new_book_diff += book_diff[book_ind + 1:]
                        break
                else:
                    # add rest of the original sells (including this one)
                    new_book_diff += book_diff[book_ind:]
                    break

            # record new book values
            if ord.is_buy:
                self.__books[ord.symbol].sells = new_book_diff
            else:
                self.__books[ord.symbol].buys = new_book_diff

            # want to buy, add as order
            if ord.quantity != 0:
                bisect.insort(book_same, ord) # modifies in-place


        # update positions based on trades
        for t in new_trades:
            prod = self.__listings[t.symbol].product
            self.__positions[t.buyer][prod] += t.quantity
            self.__positions[t.buyer]["SEASHELLS"] -= t.quantity * t.price
            self.__positions[t.seller][prod] -= t.quantity
            self.__positions[t.seller]["SEASHELLS"] += t.quantity * t.price



        # add trades to state
        self.__trades += new_trades


    def validate_position_limits(self):
        """ Ensures that all players are following position limits
        """

        for pid, all_pos in self.__positions.items():
            for prod, pos in all_pos.items():
                limit = self.__position_limits[pid][prod]
                assert -limit <= pos <= limit, f"Player {pid} has illegal position in {prod}, cur: {pos}, limit: {limit}"


    def validate_position_totals(self):
        """ Ensures that all positions add up to 0
        """

        for prod in self.__products:
            total = 0
            for pid in self.__pids:
                total += self.__positions[pid][prod]

            assert total == 0, f"{prod} has nonzero total: {total}"

    
    def validate(self):
        self.validate_position_limits()
        self.validate_position_totals()

    
    
class ProsperityEncoder(JSONEncoder):
        def default(self, o):
            return o.__dict__


""" utility functions """



def eprint(*args, **kwargs):
    print("[ENG]", *args, **kwargs)


