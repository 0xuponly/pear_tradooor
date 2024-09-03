from pybit.unified_trading import HTTP
from config.config import BYBIT_CATEGORY, BYBIT_SETTLE_COIN

class BybitAPIClient:
    def __init__(self, api_key, api_secret, testnet=False):
        self.session = HTTP(
            testnet=testnet,
            api_key=api_key,
            api_secret=api_secret
        )

    def get_current_prices(self, symbol1, symbol2):
        try:
            price1 = float(self.session.get_tickers(category=BYBIT_CATEGORY, symbol=symbol1)['result']['list'][0]['lastPrice'])
            price2 = float(self.session.get_tickers(category=BYBIT_CATEGORY, symbol=symbol2)['result']['list'][0]['lastPrice'])
            return price1, price2
        except Exception as e:
            print(f"Error getting current prices: {e}")
            return None, None

    def get_quantity_precision(self, symbol):
        try:
            instrument_info = self.session.get_instruments_info(
                category=BYBIT_CATEGORY,
                symbol=symbol
            )
            if instrument_info['retCode'] == 0:
                for instrument in instrument_info['result']['list']:
                    if instrument['symbol'] == symbol:
                        return instrument['lotSizeFilter']['qtyStep'].index('1') - 1
            return 8  # Default to 8 decimal places if not found
        except Exception as e:
            print(f"Error getting quantity precision for {symbol}: {e}")
            return 8  # Default to 8 decimal places on error

    def place_order(self, symbol, side, order_type, qty, price=None, reduce_only=False):
        try:
            response = self.session.place_order(
                category=BYBIT_CATEGORY,
                symbol=symbol,
                side=side,
                orderType=order_type,
                qty=str(qty),
                price=price,
                reduceOnly=reduce_only
            )
            return response
        except Exception as e:
            print(f"Error placing order: {e}")
            return None

    def get_positions(self):
        try:
            return self.session.get_positions(
                category=BYBIT_CATEGORY,
                settleCoin=BYBIT_SETTLE_COIN
            )
        except Exception as e:
            print(f"Error getting positions: {e}")
            return None

    def get_wallet_balance(self):
        try:
            return self.session.get_wallet_balance(accountType="UNIFIED")
        except Exception as e:
            print(f"Error getting wallet balance: {e}")
            return None

    def get_kline_data(self, symbol, interval, limit):
        try:
            return self.session.get_kline(
                category=BYBIT_CATEGORY,
                symbol=symbol,
                interval=interval,
                limit=limit
            )
        except Exception as e:
            print(f"Error getting kline data: {e}")
            return None