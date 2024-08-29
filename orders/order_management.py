from pybit.unified_trading import HTTP
import time

class OrderManager:
    def __init__(self, api_key, api_secret, testnet=True):
        self.session = HTTP(
            testnet=testnet,
            api_key=api_key,
            api_secret=api_secret
        )

    def place_order(self, category, symbol, side, order_type, qty, price=None, time_in_force="GTC", **kwargs):
        order_params = {
            "category": category,
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "qty": qty,
            "price": price,
            "timeInForce": time_in_force,
            **kwargs
        }
        
        response = self.session.place_order(**order_params)
        return self.parse_order_id(response)

    def cancel_order(self, category, symbol, order_id):
        return self.session.cancel_order(
            category=category,
            symbol=symbol,
            orderId=order_id
        )

    def cancel_all_orders(self, category, symbol):
        return self.session.cancel_all_orders(
            category=category,
            symbol=symbol
        )

    @staticmethod
    def parse_order_id(response):
        result = response.get('result')
        return result.get('orderId')

    def place_and_manage_order(self, category, symbol, side, order_type, qty, price, time_in_force="GTC", cancel_after=20):
        order_id = self.place_order(category, symbol, side, order_type, qty, price, time_in_force)
        print(f"Order placed with ID: {order_id}")
        
        time.sleep(cancel_after)
        
        cancel_response = self.cancel_order(category, symbol, order_id)
        print(f"Order cancellation response: {cancel_response}")

    def get_orderbook(self, category, symbol, limit=50):
        response = self.session.get_orderbook(
            category=category,
            symbol=symbol,
            limit=limit
        ).get('result')
        return self.format_order_book(response)

    @staticmethod
    def format_order_book(response):
        bids = response.get('b')
        asks = response.get('a')
        return bids, asks

# Example usage
if __name__ == "__main__":
    api_key = "YOUR_API_KEY"
    api_secret = "YOUR_API_SECRET"
    
    order_manager = OrderManager(api_key, api_secret)
    
    # Place and manage an order
    order_manager.place_and_manage_order(
        category='linear',
        symbol='BTCUSDT',
        side='Buy',
        order_type='Limit',
        qty='0.001',
        price='25000',
        cancel_after=30  # Cancel after 30 seconds
    )
    
    # Get and print orderbook
    bids, asks = order_manager.get_orderbook("linear", "BTCUSDT")
    print("Top 5 bids:")
    for bid in bids[:5]:
        print(f"Bid price: {bid[0]}, quantity: {bid[1]}")
