from pybit.unified_trading import HTTP
import logging
from requests import Session
from config.config import BYBIT_CATEGORY, BYBIT_SETTLE_COIN

logger = logging.getLogger(__name__)

class BybitAPIClient:
    def __init__(self, api_key, api_secret, testnet=False):
        self.session = HTTP(
            testnet=testnet,
            api_key=api_key,
            api_secret=api_secret
        )

    def get_kline_data(self, symbol, interval, limit):
        try:
            response = self.session.get_kline(
                category=BYBIT_CATEGORY,
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            return response
        except Exception as e:
            logger.error(f"Error getting kline data: {e}")
            return None

    def get_tickers(self, category, symbol):
        try:
            return self.session.get_tickers(category=category, symbol=symbol)
        except Exception as e:
            logger.error(f"Error getting tickers: {e}")
            return None

    def get_wallet_balance(self, accountType):
        try:
            return self.session.get_wallet_balance(accountType=accountType)
        except Exception as e:
            logger.error(f"Error getting wallet balance: {e}")
            return None

    def get_positions(self, category, settleCoin):
        try:
            return self.session.get_positions(category=category, settleCoin=settleCoin)
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return None

    def place_order(self, symbol, side, order_type, qty, reduce_only=False):
        try:
            return self.session.place_order(
                category=BYBIT_CATEGORY,
                symbol=symbol,
                side=side,
                orderType=order_type,
                qty=qty,
                reduceOnly=reduce_only
            )
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    def get_instruments_info(self, category, symbol):
        try:
            return self.session.get_instruments_info(category=category, symbol=symbol)
        except Exception as e:
            logger.error(f"Error getting instruments info: {e}")
            return None

    def get_current_prices(self, symbol1, symbol2):
        price1 = self.get_current_price(symbol1)
        price2 = self.get_current_price(symbol2)
        return price1, price2

    def get_current_price(self, symbol):
        try:
            ticker = self.session.get_tickers(category=BYBIT_CATEGORY, symbol=symbol)
            if ticker['retCode'] == 0:
                return float(ticker['result']['list'][0]['lastPrice'])
            else:
                logger.error(f"Error getting current price for {symbol}: {ticker['retMsg']}")
                return None
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None
        
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
            logger.error(f"Error getting quantity precision for {symbol}: {e}")
            return 8  # Default to 8 decimal places on error