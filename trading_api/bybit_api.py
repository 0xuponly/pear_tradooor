from pybit.unified_trading import HTTP
from config.config import API_KEY, API_SECRET, TESTNET

class BybitAPI:
    def __init__(self):
        self.session = HTTP(
            testnet=TESTNET,
            api_key=API_KEY,
            api_secret=API_SECRET
        )

    def get_ticker(self, symbol):
        return self.session.get_tickers(category="linear", symbol=symbol)

    def get_kline_data(self, symbol, interval="1", limit=200):
        return self.session.get_kline(
            category="linear",
            symbol=symbol,
            interval=interval,
            limit=limit
        )

    def get_positions(self, symbol):
        return self.session.get_positions(category="linear", symbol=symbol)

    def place_order(self, symbol, side, qty, order_type="Market", price=None, subaccount_id=None):
        order_params = {
            "category": "linear",
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "qty": qty,
            "price": price
        }
        if subaccount_id:
            order_params["subMemberId"] = subaccount_id
        return self.session.place_order(**order_params)

    def cancel_order(self, symbol, order_id):
        return self.session.cancel_order(
            category="linear",
            symbol=symbol,
            orderId=order_id
        )

    def get_subaccounts(self):
        return self.session.get_sub_uid_list()
