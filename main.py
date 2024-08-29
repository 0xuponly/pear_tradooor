from pybit.unified_trading import HTTP
import pandas as pd
import numpy as np
import statsmodels.api as sm
from dotenv import load_dotenv
import os
import logging
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from config.config import TESTNET, UPDATE_INTERVAL
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QLineEdit, QLabel, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QDoubleSpinBox, QComboBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.dates as mdates
from PyQt5.QtCore import Qt, QTimer
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize the Bybit API client
try:
    session = HTTP(
        testnet=TESTNET,
        api_key=os.getenv("API_KEY"),
        api_secret=os.getenv("API_SECRET")
    )
except Exception as e:
    logger.error(f"Failed to initialize Bybit API client: {e}")
    exit(1)

def get_kline_data(symbol, interval="1", limit=200):
    try:
        return session.get_kline(
            category="linear",
            symbol=symbol,
            interval=interval,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Error getting kline data for {symbol}: {e}")
        return None

def calculate_pair_price(symbol1, symbol2):
    try:
        # Get kline data for both symbols
        data1 = session.get_kline(
            category="linear",
            symbol=symbol1,
            interval=1,
            limit=1000
        )
        data2 = session.get_kline(
            category="linear",
            symbol=symbol2,
            interval=1,
            limit=1000
        )
        
        if data1 is None or data2 is None:
            return None
        
        df1 = pd.DataFrame(data1['result']['list'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
        df2 = pd.DataFrame(data2['result']['list'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
        
        df1['close'] = df1['close'].astype(float)
        df2['close'] = df2['close'].astype(float)
        
        # Convert timestamp to datetime
        df1['timestamp'] = pd.to_datetime(df1['timestamp'].astype(int), unit='ms')
        df2['timestamp'] = pd.to_datetime(df2['timestamp'].astype(int), unit='ms')
        
        # Set timestamp as index
        df1.set_index('timestamp', inplace=True)
        df2.set_index('timestamp', inplace=True)
        
        # Align the dataframes and calculate the pair_price
        df1, df2 = df1.align(df2, join='inner')
        pair_price = df2['close'] / df1['close']
        
        return pair_price
    except Exception as e:
        logger.error(f"Error calculating pair price: {e}")
        return None

class ControlPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle("Pear Tradooor - Control Panel")
        self.setGeometry(100, 100, 300, 200)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.session = session  # Add this line to use the global session object

        layout = QVBoxLayout()

        self.symbol1_input = QLineEdit()
        self.symbol2_input = QLineEdit()
        self.symbol1_input.setPlaceholderText("default: BTCUSDT")
        self.symbol2_input.setPlaceholderText("e.g., POPCATUSDT")

        layout.addWidget(QLabel("Base:"))
        layout.addWidget(self.symbol1_input)
        layout.addWidget(QLabel("Quote:"))
        layout.addWidget(self.symbol2_input)

        self.start_button = QPushButton("Chart")
        layout.addWidget(self.start_button)

        self.positions_label = QLabel("Open Positions:")
        layout.addWidget(self.positions_label)

        self.positions_layout = QVBoxLayout()
        positions_widget = QWidget()
        positions_widget.setLayout(self.positions_layout)
        layout.addWidget(positions_widget)

        self.close_all_button = QPushButton("Close All Positions")
        layout.addWidget(self.close_all_button)

        self.setLayout(layout)

        self.connect_signals()

    def connect_signals(self):
        self.symbol2_input.returnPressed.connect(self.start_button.click)

    def update_positions(self, positions):
        # Clear the existing layout
        while self.positions_layout.count():
            item = self.positions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if positions and isinstance(positions, list):
            for index, position in enumerate(positions):
                if isinstance(position, dict):
                    position_type = position.get('type', '').upper()
                    symbols = [key for key in position.keys() if key != 'type']
                    if len(symbols) >= 2:
                        symbol1, symbol2 = symbols[:2]
                        qty1 = position[symbol1].get('qty', 0)
                        qty2 = position[symbol2].get('qty', 0)
                        entry_price1 = position[symbol1].get('entry_price', 0)
                        entry_price2 = position[symbol2].get('entry_price', 0)
                        
                        # Calculate dollar values
                        dollar_value1 = qty1 * entry_price1
                        dollar_value2 = qty2 * entry_price2
                        average_dollar_value = (dollar_value1 + dollar_value2) / 2
                        
                        # Calculate combined UPNL
                        current_price1 = self.get_current_price(symbol1)
                        current_price2 = self.get_current_price(symbol2)
                        upnl1 = (current_price1 - entry_price1) * qty1 * (-1 if position[symbol1]['side'] == 'Sell' else 1)
                        upnl2 = (current_price2 - entry_price2) * qty2 * (-1 if position[symbol2]['side'] == 'Sell' else 1)
                        combined_upnl = upnl1 + upnl2
                        
                        # Calculate percentage UPNL
                        order_size = self.get_order_size()
                        upnl_percentage = (combined_upnl / order_size) * 100 if order_size else 0
                        
                        # Truncate symbols
                        symbol1_truncated = symbol1[:-4] if symbol1.endswith(('USDT', 'USDC')) else symbol1
                        symbol2_truncated = symbol2[:-4] if symbol2.endswith(('USDT', 'USDC')) else symbol2
                        
                        position_text = f"{position_type} ${average_dollar_value:.2f} {symbol2_truncated}/{symbol1_truncated} ${combined_upnl:.2f} {upnl_percentage:.2f}%"
                        
                        position_widget = QWidget()
                        position_layout = QHBoxLayout(position_widget)
                        position_label = QLabel(position_text)
                        position_layout.addWidget(position_label)
                        
                        close_button = QPushButton("Close")
                        close_button.clicked.connect(lambda checked, idx=index: self.close_position(idx))
                        position_layout.addWidget(close_button)
                        
                        self.positions_layout.addWidget(position_widget)
        else:
            no_positions_label = QLabel("No open positions")
            self.positions_layout.addWidget(no_positions_label)

        # Force update of the layout
        self.positions_label.updateGeometry()
        self.updateGeometry()

    def get_current_price(self, symbol):
        try:
            ticker = session.get_tickers(category="linear", symbol=symbol)
            if ticker['retCode'] == 0:
                return float(ticker['result']['list'][0]['lastPrice'])
            else:
                logger.error(f"Error getting current price for {symbol}: {ticker['retMsg']}")
                return None
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None

    def get_order_size(self):
        if hasattr(self.parent(), 'trading_dialog'):
            return self.parent().trading_dialog.order_size.value()
        else:
            return 1000  # Default value if trading dialog is not available

    def closeEvent(self, event):
        self.parent().close()
        event.accept()

    def close_position(self, index):
        if hasattr(self.parent(), 'trading_dialog'):
            self.parent().trading_dialog.close_position(index)
        else:
            QMessageBox.warning(self, "Error", "Trading dialog not initialized.")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pear Tradooor - Chart")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)

        # Create control panel
        self.control_panel = ControlPanel(self)
        self.control_panel.start_button.clicked.connect(self.start_chart)
        self.control_panel.close_all_button.clicked.connect(self.close_all_positions)

        # Initialize trading dialog with default symbols
        self.trading_dialog = TradingDialog(self, "BTCUSDT", "ETHUSDT")

        self.fig = None
        self.ax = None
        self.canvas = None
        self.ani = None

        # Set up a timer to refresh positions
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_positions)
        self.refresh_timer.start(10000)  # Refresh every 10 seconds

        # Load position information
        self.current_position = self.load_position()
        self.refresh_positions()

    def showEvent(self, event):
        super().showEvent(event)
        self.control_panel.show()
        self.control_panel.raise_()
        self.control_panel.activateWindow()

    def closeEvent(self, event):
        self.control_panel.close()
        event.accept()

    def start_chart(self):
        symbol1 = self.control_panel.symbol1_input.text().upper() or "BTCUSDT"
        symbol2 = self.control_panel.symbol2_input.text().upper() or "ETHUSDT"

        if self.validate_symbols(symbol1, symbol2):
            self.create_chart(symbol1, symbol2)
            # Update the trading dialog with new symbols
            self.trading_dialog.update_symbols(symbol1, symbol2)
        else:
            QMessageBox.warning(self, "Invalid Symbols", "Please enter valid symbols.")

    def validate_symbols(self, symbol1, symbol2):
        # Add your symbol validation logic here
        # For now, we'll just check if they're not empty
        return bool(symbol1 and symbol2)

    def create_chart(self, symbol1, symbol2):
        if self.fig:
            self.layout.removeWidget(self.canvas)
            self.canvas.deleteLater()
            plt.close(self.fig)

        self.fig, self.ax = plt.subplots(figsize=(8, 5))
        self.canvas = FigureCanvas(self.fig)
        self.layout.addWidget(self.canvas)

        self.ani = FuncAnimation(self.fig, self.update_chart, interval=UPDATE_INTERVAL, 
                                 fargs=(symbol1, symbol2), save_count=100)
        self.canvas.draw()

        # Show the trading dialog
        self.trading_dialog.show()

    def update_chart(self, frame, symbol1, symbol2):
        pair_price = calculate_pair_price(symbol1, symbol2)
        if pair_price is not None:
            self.ax.clear()
            self.ax.plot(pair_price.index, pair_price.values)
            symbol1_truncated = symbol1[:-4] if symbol1.endswith(('USDT', 'USDC')) else symbol1
            symbol2_truncated = symbol2[:-4] if symbol2.endswith(('USDT', 'USDC')) else symbol2
            self.ax.set_title(f"{symbol2_truncated}/{symbol1_truncated} Pear Price")
            self.ax.set_xlabel("Time")
            self.ax.set_ylabel("Pear Price")
            
            self.ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d %H:%M:%S'))
            plt.xticks(rotation=45, ha='right')
            
            plt.tight_layout()
            self.canvas.draw()

    def refresh_positions(self):
        positions = []
        if hasattr(self, 'trading_dialog'):
            positions = self.trading_dialog.current_position or []
        else:
            positions = self.current_position or []
        
        self.control_panel.update_positions(positions)

    def load_position(self):
        if os.path.exists('current_position.json') and os.path.getsize('current_position.json') > 0:
            with open('current_position.json', 'r') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return None
        else:
            return None

    def close_all_positions(self):
        if hasattr(self, 'trading_dialog'):
            self.trading_dialog.close_all_positions()
        else:
            QMessageBox.warning(self, "Error", "Trading dialog not initialized.")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'trading_dialog'):
            screen = QApplication.primaryScreen().geometry()
            dialog_width = 300  # Make sure this matches the width in TradingDialog
            dialog_height = 150
            self.trading_dialog.setGeometry(screen.left(), screen.bottom() - dialog_height, dialog_width, dialog_height)

class TradingDialog(QDialog):
    def __init__(self, parent=None, symbol1="", symbol2=""):
        super().__init__(parent)
        self.setWindowTitle("Pear Tradooor")
        self.symbol1 = symbol1
        self.symbol2 = symbol2
        self.session = session  # Use the global session object
        self.current_position = None  # Add this line to store the current position

        # Set the dialog position at the bottom of the screen
        screen = QApplication.primaryScreen().geometry()
        dialog_width = 200  # Adjust this value as needed
        dialog_height = 125
        self.setGeometry(screen.left(), screen.bottom() - dialog_height, dialog_width, dialog_height)

        layout = QVBoxLayout()

        # Pair information
        symbol1_truncated = symbol1[:-4] if symbol1.endswith(('USDT', 'USDC')) else symbol1
        symbol2_truncated = symbol2[:-4] if symbol2.endswith(('USDT', 'USDC')) else symbol2
        self.pair_label = QLabel(f"Trading Pair: {symbol2_truncated}/{symbol1_truncated}")
        layout.addWidget(self.pair_label)

        # Long and Short buttons
        button_layout = QHBoxLayout()
        self.long_button = QPushButton("Long Pair")
        self.short_button = QPushButton("Short Pair")
        button_layout.addWidget(self.long_button)
        button_layout.addWidget(self.short_button)
        layout.addLayout(button_layout)

        # Order size
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Order Size ($):"))
        self.order_size = QDoubleSpinBox()
        self.order_size.setRange(10, 1000000)
        self.order_size.setValue(60)
        self.order_size.setPrefix("$")
        size_layout.addWidget(self.order_size)
        layout.addLayout(size_layout)

        self.setLayout(layout)

        # Connect buttons to trading methods
        self.long_button.clicked.connect(self.long_pair)
        self.short_button.clicked.connect(self.short_pair)

        self.load_position()

    def update_symbols(self, symbol1, symbol2):
        self.symbol1 = symbol1
        self.symbol2 = symbol2
        self.setWindowTitle(f"Pear Tradooor - {symbol2}/{symbol1}")
        
        symbol1_truncated = symbol1[:-4] if symbol1.endswith(('USDT', 'USDC')) else symbol1
        symbol2_truncated = symbol2[:-4] if symbol2.endswith(('USDT', 'USDC')) else symbol2
        self.pair_label.setText(f"Trading Pair: {symbol2_truncated}/{symbol1_truncated}")

class TradingDialog(QDialog):
    def __init__(self, parent=None, symbol1="", symbol2=""):
        super().__init__(parent)
        self.setWindowTitle("Pear Tradooor - Trading Panel")
        self.symbol1 = symbol1
        self.symbol2 = symbol2
        self.session = session  # Use the global session object
        self.current_position = None  # Add this line to store the current position

        # Set the dialog position at the bottom of the screen
        screen = QApplication.primaryScreen().geometry()
        dialog_width = 300  # Adjust this value as needed
        dialog_height = 150
        self.setGeometry(screen.left(), screen.bottom() - dialog_height, dialog_width, dialog_height)

        layout = QVBoxLayout()

        # Pair information
        symbol1_truncated = symbol1[:-4] if symbol1.endswith(('USDT', 'USDC')) else symbol1
        symbol2_truncated = symbol2[:-4] if symbol2.endswith(('USDT', 'USDC')) else symbol2
        self.pair_label = QLabel(f"Trading Pair: {symbol2_truncated}/{symbol1_truncated}")
        layout.addWidget(self.pair_label)

        # Long and Short buttons
        button_layout = QHBoxLayout()
        self.long_button = QPushButton("Long Pair")
        self.short_button = QPushButton("Short Pair")
        button_layout.addWidget(self.long_button)
        button_layout.addWidget(self.short_button)
        layout.addLayout(button_layout)

        # Order size
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Order Size ($):"))
        self.order_size = QDoubleSpinBox()
        self.order_size.setRange(10, 1000000)
        self.order_size.setValue(1000)
        self.order_size.setPrefix("$")
        size_layout.addWidget(self.order_size)
        layout.addLayout(size_layout)

        self.setLayout(layout)

        # Connect buttons to trading methods
        self.long_button.clicked.connect(self.long_pair)
        self.short_button.clicked.connect(self.short_pair)

        self.load_position()

    def get_current_prices(self):
        try:
            price1 = float(self.session.get_tickers(category="linear", symbol=self.symbol1)['result']['list'][0]['lastPrice'])
            price2 = float(self.session.get_tickers(category="linear", symbol=self.symbol2)['result']['list'][0]['lastPrice'])
            return price1, price2
        except Exception as e:
            logger.error(f"Error getting current prices: {e}")
            return None, None

    def get_quantity_precision(self, symbol):
        try:
            instrument_info = self.session.get_instruments_info(
                category="linear",
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

    def calculate_quantities(self, price1, price2):
        total_order_size = self.order_size.value()
        precision1 = self.get_quantity_precision(self.symbol1)
        precision2 = self.get_quantity_precision(self.symbol2)
        qty1 = round(total_order_size / price1, precision1)
        qty2 = round(total_order_size / price2, precision2)
        return qty1, qty2

    def calculate_dollar_value(self, quantity, price):
        return quantity * price

    def long_pair(self):
        price1, price2 = self.get_current_prices()
        if price1 is None or price2 is None:
            QMessageBox.warning(self, "Error", "Failed to get current prices.")
            return

        qty1, qty2 = self.calculate_quantities(price1, price2)
        dollar_value1 = self.calculate_dollar_value(qty1, price1)
        dollar_value2 = self.calculate_dollar_value(qty2, price2)

        print(f"Long Pair Order:")
        print(f"Short {self.symbol1}: {qty1:.8f} ({dollar_value1:.2f} USD)")
        print(f"Long {self.symbol2}: {qty2:.8f} ({dollar_value2:.2f} USD)")

        try:
            # Short SYMBOL1
            response1 = self.session.place_order(
                category="linear",
                symbol=self.symbol1,
                side="Sell",
                orderType="Market",
                qty=str(qty1)
            )
            
            # Long SYMBOL2
            response2 = self.session.place_order(
                category="linear",
                symbol=self.symbol2,
                side="Buy",
                orderType="Market",
                qty=str(qty2)
            )
            
            if response1['retCode'] == 0 and response2['retCode'] == 0:
                new_position = {
                    'type': 'long',
                    self.symbol1: {'side': 'Sell', 'qty': qty1, 'entry_price': price1},
                    self.symbol2: {'side': 'Buy', 'qty': qty2, 'entry_price': price2}
                }
                
                if self.current_position is None:
                    self.current_position = [new_position]
                else:
                    self.current_position.append(new_position)
                
                self.save_position()
                self.parent().refresh_positions()  # Refresh the positions display
                QMessageBox.information(self, "Success", "Long pair order placed successfully.")
            else:
                error_msg = f"Failed to place long pair order:\n{self.symbol1}: {response1['retMsg']}\n{self.symbol2}: {response2['retMsg']}"
                QMessageBox.warning(self, "Error", error_msg)
        except Exception as e:
            logger.error(f"Error placing long pair order: {e}")
            QMessageBox.warning(self, "Error", f"Failed to place long pair order: {e}")

    def short_pair(self):
        price1, price2 = self.get_current_prices()
        if price1 is None or price2 is None:
            QMessageBox.warning(self, "Error", "Failed to get current prices.")
            return

        qty1, qty2 = self.calculate_quantities(price1, price2)
        dollar_value1 = self.calculate_dollar_value(qty1, price1)
        dollar_value2 = self.calculate_dollar_value(qty2, price2)

        print(f"Short Pair Order:")
        print(f"Long {self.symbol1}: {qty1:.8f} ({dollar_value1:.2f} USD)")
        print(f"Short {self.symbol2}: {qty2:.8f} ({dollar_value2:.2f} USD)")

        try:
            # Long SYMBOL1
            response1 = self.session.place_order(
                category="linear",
                symbol=self.symbol1,
                side="Buy",
                orderType="Market",
                qty=str(qty1)
            )
            
            # Short SYMBOL2
            response2 = self.session.place_order(
                category="linear",
                symbol=self.symbol2,
                side="Sell",
                orderType="Market",
                qty=str(qty2)
            )
            
            if response1['retCode'] == 0 and response2['retCode'] == 0:
                new_position = {
                    'type': 'short',
                    self.symbol1: {'side': 'Buy', 'qty': qty1, 'entry_price': price1},
                    self.symbol2: {'side': 'Sell', 'qty': qty2, 'entry_price': price2}
                }
                
                if self.current_position is None:
                    self.current_position = [new_position]
                else:
                    self.current_position.append(new_position)
                
                self.save_position()
                self.parent().refresh_positions()  # Refresh the positions display
                QMessageBox.information(self, "Success", "Short pair order placed successfully.")
            else:
                error_msg = f"Failed to place short pair order:\n{self.symbol1}: {response1['retMsg']}\n{self.symbol2}: {response2['retMsg']}"
                QMessageBox.warning(self, "Error", error_msg)
        except Exception as e:
            logger.error(f"Error placing short pair order: {e}")
            QMessageBox.warning(self, "Error", f"Failed to place short pair order: {e}")

    def close_all_positions(self):
        self.load_position()  # Reload the position in case it was opened in a previous session
        if not self.current_position:
            QMessageBox.information(self, "Info", "No open positions to close.")
            return False

        try:
            for position in self.current_position:
                for symbol, pos_data in position.items():
                    if symbol != 'type':
                        close_side = "Buy" if pos_data['side'] == "Sell" else "Sell"
                        response = self.session.place_order(
                            category="linear",
                            symbol=symbol,
                            side=close_side,
                            orderType="Market",
                            qty=str(pos_data['qty']),
                            reduceOnly=True
                        )
                        print(f"Close position response for {symbol}: {response}")
        
            QMessageBox.information(self, "Success", "All positions closed successfully.")
            self.current_position = None
            self.save_position()  # Save the updated (empty) position
            self.parent().refresh_positions()
            return True
        except Exception as e:
            logger.error(f"Error closing all positions: {e}")
            QMessageBox.warning(self, "Error", f"Failed to close all positions: {str(e)}")
            return False

    def close_position(self, index):
        if self.current_position and 0 <= index < len(self.current_position):
            position = self.current_position[index]
            try:
                for symbol, pos_data in position.items():
                    if symbol != 'type':
                        close_side = "Buy" if pos_data['side'] == "Sell" else "Sell"
                        response = self.session.place_order(
                            category="linear",
                            symbol=symbol,
                            side=close_side,
                            orderType="Market",
                            qty=str(pos_data['qty']),
                            reduceOnly=True
                        )
                        print(f"Close position response for {symbol}: {response}")
                
                del self.current_position[index]
                self.save_position()
                self.parent().refresh_positions()
                QMessageBox.information(self, "Success", "Position closed successfully.")
            except Exception as e:
                logger.error(f"Error closing position: {e}")
                QMessageBox.warning(self, "Error", f"Failed to close position: {e}")
        else:
            QMessageBox.warning(self, "Error", "Invalid position index.")

    def update_upnl(self, upnl):
        self.upnl_label.setText(f"UPnL: ${upnl:.2f}")

    def save_position(self):
        if self.current_position:
            with open('current_position.json', 'w') as f:
                json.dump(self.current_position, f)
        else:
            if os.path.exists('current_position.json'):
                os.remove('current_position.json')

    def load_position(self):
        if os.path.exists('current_position.json') and os.path.getsize('current_position.json') > 0:
            with open('current_position.json', 'r') as f:
                try:
                    self.current_position = json.load(f)
                except json.JSONDecodeError:
                    print("Warning: Invalid JSON in current_position.json. Setting current_position to None.")
                    self.current_position = None
        else:
            print("Info: current_position.json doesn't exist or is empty. Setting current_position to None.")
            self.current_position = None

    def update_symbols(self, symbol1, symbol2):
        self.symbol1 = symbol1
        self.symbol2 = symbol2
        symbol1_truncated = symbol1[:-4] if symbol1.endswith(('USDT', 'USDC')) else symbol1
        symbol2_truncated = symbol2[:-4] if symbol2.endswith(('USDT', 'USDC')) else symbol2
        self.setWindowTitle(f"Pear Tradooor - {symbol2_truncated}/{symbol1_truncated}")
        
        symbol1_truncated = symbol1[:-4] if symbol1.endswith(('USDT', 'USDC')) else symbol1
        symbol2_truncated = symbol2[:-4] if symbol2.endswith(('USDT', 'USDC')) else symbol2
        self.pair_label.setText(f"Trading Pair: {symbol2_truncated}/{symbol1_truncated}")

def main():
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()