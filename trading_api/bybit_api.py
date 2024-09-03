from pybit.unified_trading import HTTP
import logging

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
                category="linear",
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
                category="linear",
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