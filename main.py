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
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QLineEdit, QLabel, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QDoubleSpinBox, QComboBox, QSpacerItem, QSizePolicy
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.dates as mdates
from PyQt5.QtCore import Qt, QTimer
import json
from PyQt5.QtGui import QPalette, QColor
from datetime import datetime
import uuid

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
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.session = session  # Add this line to use the global session object

        layout = QVBoxLayout()

        self.account_info_label = QLabel("Account Balance: $0.00")
        layout.addWidget(self.account_info_label)

        self.positions_label = QLabel("  ")
        layout.addWidget(self.positions_label)

        self.positions_layout = QVBoxLayout()
        positions_widget = QWidget()
        positions_widget.setLayout(self.positions_layout)
        layout.addWidget(positions_widget)

        self.combined_upnl_label = QLabel("Combined UPnL: $0.00")
        layout.addWidget(self.combined_upnl_label)

        self.close_all_button = QPushButton("Close All Pears")
        layout.addWidget(self.close_all_button)

        # Add toggle trading panel button
        self.toggle_trading_panel_button = QPushButton("Hide Trading Panel")
        self.toggle_trading_panel_button.clicked.connect(self.toggle_trading_panel)
        layout.addWidget(self.toggle_trading_panel_button)

        self.script_positions_label = QLabel("  Open Pears:")
        layout.addWidget(self.script_positions_label)

        self.script_positions_layout = QVBoxLayout()
        script_positions_widget = QWidget()
        script_positions_widget.setLayout(self.script_positions_layout)
        layout.addWidget(script_positions_widget)

        self.all_positions_label = QLabel("  Open Apples:")
        layout.addWidget(self.all_positions_label)

        self.all_positions_layout = QVBoxLayout()
        all_positions_widget = QWidget()
        all_positions_widget.setLayout(self.all_positions_layout)
        layout.addWidget(all_positions_widget)

        self.setLayout(layout)

        self.set_dark_theme()
        self.setGeometry(0, 0, 400, 200)  # x, y, width, height

    def set_dark_theme(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #353535;
                color: white;
            }
            QPushButton {
                background-color: #2A82DA;
                color: white;
                border: none;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #3A92EA;
            }
            QLineEdit, QDoubleSpinBox {
                background-color: #252525;
                color: white;
                border: 1px solid #555555;
            }
            QLabel { color: white; }
        """)
    def update_positions(self, positions):
        self.update_account_info()

        # Clear existing layouts
        self.clear_layout(self.script_positions_layout)
        self.clear_layout(self.all_positions_layout)

        # Update script positions
        if positions and isinstance(positions, list):
            for index, position in enumerate(positions):
                self.add_position_to_layout(position, index, self.script_positions_layout, is_script_position=True)
        else:
            no_positions_label = QLabel("- - - - -")
            self.script_positions_layout.addWidget(no_positions_label)

        # Update all positions
        all_positions = self.get_all_open_positions()
        if all_positions:
            for index, position in enumerate(all_positions):
                self.add_position_to_layout(position, index, self.all_positions_layout, is_script_position=False)
        else:
            no_positions_label = QLabel("- - - - -")
            self.all_positions_layout.addWidget(no_positions_label)

        # Calculate and display combined UPnL
        combined_upnl = sum(position.get('combined_upnl', 0) for position in positions if isinstance(position, dict))
        self.combined_upnl_label.setText(f"  Total UPnL: ${combined_upnl:.2f}")

        # Force update of the layout
        self.positions_label.updateGeometry()
        self.updateGeometry()

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def add_position_to_layout(self, position, index, layout, is_script_position):
        if isinstance(position, dict):
            if is_script_position:
                position_type = position.get('type', '').upper()[0]
                symbols = [key for key in position.keys() if key not in ['type', 'timestamp', 'timestamp_rounded', 'combined_upnl', 'trade_id']]
                if len(symbols) >= 2:
                    symbol1, symbol2 = symbols[:2]
                    pos1 = position.get(symbol1, {})
                    pos2 = position.get(symbol2, {})
                    if isinstance(pos1, dict) and isinstance(pos2, dict):
                        qty1 = pos1.get('qty', 0)
                        qty2 = pos2.get('qty', 0)
                        entry_price1 = pos1.get('entry_price', 0)
                        entry_price2 = pos2.get('entry_price', 0)
                        
                        # Calculate dollar values
                        dollar_value1 = qty1 * entry_price1
                        dollar_value2 = qty2 * entry_price2
                        average_dollar_value = (dollar_value1 + dollar_value2) / 2
                        
                        # Calculate combined UPNL
                        current_price1 = self.get_current_price(symbol1)
                        current_price2 = self.get_current_price(symbol2)
                        upnl1 = (current_price1 - entry_price1) * qty1 * (-1 if pos1['side'] == 'Sell' else 1)
                        upnl2 = (current_price2 - entry_price2) * qty2 * (-1 if pos2['side'] == 'Sell' else 1)
                        combined_upnl = upnl1 + upnl2
                        position['combined_upnl'] = combined_upnl
                        
                        # Calculate percentage UPNL
                        order_size = self.get_order_size()
                        upnl_percentage = (combined_upnl / order_size) * 100 if order_size else 0
                        
                        # Truncate symbols
                        symbol1_truncated = symbol1[:-4] if symbol1.endswith(('USDT', 'USDC')) else symbol1
                        symbol2_truncated = symbol2[:-4] if symbol2.endswith(('USDT', 'USDC')) else symbol2
                        
                        position_text = f"{position_type} ${average_dollar_value:.2f} {symbol2_truncated}/{symbol1_truncated} ${combined_upnl:.2f} {upnl_percentage:.2f}%"
                        
                        position_widget = QWidget()
                        position_layout = QHBoxLayout(position_widget)
                        position_layout.setContentsMargins(0, 5, 0, 5)  # Adjust top and bottom margins
                        position_label = QLabel(position_text)
                        position_layout.addWidget(position_label)
                        
                        close_button = QPushButton("Close")
                        close_button.clicked.connect(lambda checked, idx=index: self.close_position(idx))
                        position_layout.addWidget(close_button)
                        
                        layout.addWidget(position_widget)
                    else:
                        logger.error(f"Invalid position data structure for {symbol1} or {symbol2}")
            else:
                try:
                    symbol = position['symbol']
                    qty = float(position['size'])
                    entry_price = float(position.get('entryPrice', position.get('entry_price', 0)))
                    side = position['side']
                    unrealised_pnl = float(position.get('unrealisedPnl', position.get('unrealized_pnl', 0)))
                    
                    # Get current price
                    current_price = self.get_current_price(symbol)
                    
                    # Calculate initial position value
                    initial_position_value = qty * entry_price
                    
                    # Calculate dollar value using current price
                    dollar_value = qty * current_price if current_price else 0
                    
                    # Calculate percentage UPNL
                    order_size = self.get_order_size()
                    upnl_percentage = (unrealised_pnl / initial_position_value) * 100 if initial_position_value else 0
                    
                    # Truncate symbol
                    symbol_truncated = symbol[:-4] if symbol.endswith(('USDT', 'USDC')) else symbol
                    
                    position_text = f"{'LONG' if side == 'Buy' else 'SHORT'} ${dollar_value:.2f} {symbol_truncated} ${unrealised_pnl:.2f} {upnl_percentage:.2f}%"
                    
                    position_widget = QWidget()
                    position_layout = QHBoxLayout(position_widget)
                    position_layout.setContentsMargins(0, 5, 0, 5)  # Adjust top and bottom margins
                    position_label = QLabel(position_text)
                    position_layout.addWidget(position_label)
                    
                    layout.addWidget(position_widget)
                except KeyError as e:
                    logger.error(f"KeyError in position data: {e}")
                    logger.error(f"Position data: {position}")
                except Exception as e:
                    logger.error(f"Error processing position: {e}")
                    logger.error(f"Position data: {position}")

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

    def get_account_info(self):
        try:
            account_info = self.session.get_wallet_balance(accountType="UNIFIED")
            if account_info['retCode'] == 0:
                wallet_info = account_info['result']['list'][0]
                total_equity = float(wallet_info['totalEquity'])
                return total_equity
            else:
                logger.error(f"Error getting account info: {account_info['retMsg']}")
                return None
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None
    def update_account_info(self):
        total_equity = self.get_account_info()
        if total_equity is not None:
            self.account_info_label.setText(f"  Account Balance: ${total_equity:.2f}")
        else:
            self.account_info_label.setText("  Account Balance: N/A")

    def toggle_trading_panel(self):
        parent = self.parent()
        if hasattr(parent, 'toggle_trading_panel'):
            parent.toggle_trading_panel()
        else:
            logger.warning("Parent does not have toggle_trading_panel method")

    def get_all_open_positions(self):
        try:
            positions = self.session.get_positions(
                category="linear",
                settleCoin="USDT"
            )
            if positions['retCode'] == 0:
                return [pos for pos in positions['result']['list'] if float(pos['size']) > 0]
            else:
                logger.error(f"Error getting all open positions: {positions['retMsg']}")
                return None
        except Exception as e:
            logger.error(f"Error getting all open positions: {e}")
            return None

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pear Tradooor - Chart")
        screen = QApplication.primaryScreen().geometry()
        self.control_panel = ControlPanel(self)
        control_panel_width = self.control_panel.width()
        self.setGeometry(control_panel_width, 0, screen.width() - control_panel_width, screen.height())

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Create chart widget
        self.chart_widget = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_widget)
        self.layout.addWidget(self.chart_widget)

        # Initialize trading dialog with default symbols
        self.symbol1 = "BTCUSDT"
        self.symbol2 = "POPCATUSDT"
        self.trading_dialog = TradingDialog(self, self.symbol1, self.symbol2)
        self.trading_dialog.show()

        # Create control panel as a separate window
        self.control_panel = ControlPanel(self)
        self.control_panel.close_all_button.clicked.connect(self.close_all_positions)
        self.control_panel.show()

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'trading_dialog'):
            screen = QApplication.primaryScreen().geometry()
            dialog_width = 400  # Make sure this matches the width in TradingDialog
            dialog_height = 250
            self.trading_dialog.setGeometry(screen.left(), screen.bottom() - dialog_height, dialog_width, dialog_height)

    def validate_symbols(self, symbol1, symbol2):
        # Add your symbol validation logic here
        # For now, we'll just check if they're not empty
        return bool(symbol1 and symbol2)

    def create_chart(self, symbol1, symbol2):
        if self.fig:
            self.chart_layout.removeWidget(self.canvas)
            self.canvas.deleteLater()
            plt.close(self.fig)

        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setStyleSheet("background-color: #353535;")
        self.chart_layout.addWidget(self.canvas)

        self.ani = FuncAnimation(self.fig, self.update_chart, interval=UPDATE_INTERVAL, 
                                 blit=False, save_count=100)
        self.canvas.draw()

    def update_chart(self, frame):
        pair_price = calculate_pair_price(self.symbol1, self.symbol2)
        positions = self.trading_dialog.current_position if hasattr(self, 'trading_dialog') else []
        if pair_price is not None and not pair_price.empty:
            self.ax.clear()
            self.ax.plot(pair_price.index, pair_price.values, color='#2A82DA')
            symbol1_truncated = self.symbol1[:-4] if self.symbol1.endswith(('USDT', 'USDC')) else self.symbol1
            symbol2_truncated = self.symbol2[:-4] if self.symbol2.endswith(('USDT', 'USDC')) else self.symbol2
            self.ax.set_title(f"{symbol2_truncated}/{symbol1_truncated} Pear Price", color='white')
            self.ax.set_xlabel("Time", color='white')
            self.ax.set_ylabel("Pear Price", color='white')
            
            # Add horizontal dotted line at current price
            try:
                current_price = pair_price.iloc[0]
                self.ax.axhline(y=current_price, color='white', linestyle=':', linewidth=0.5)
            except IndexError:
                logger.warning("Unable to get current price: pair_price is empty")
            
            # Plot arrows for positions
            if positions:  # Add this check
                for position in positions:
                    if 'timestamp_rounded' in position:
                        timestamp = datetime.fromisoformat(position['timestamp_rounded'])
                        if timestamp in pair_price.index:
                            price = pair_price.loc[timestamp]
                            if position['type'] == 'long':
                                self.ax.annotate('↑', (timestamp, price), xytext=(0, -20), 
                                                 textcoords='offset points', ha='center', va='bottom',
                                                 color='green', fontsize=15)
                            elif position['type'] == 'short':
                                self.ax.annotate('↓', (timestamp, price), xytext=(0, 20), 
                                                 textcoords='offset points', ha='center', va='top',
                                                 color='red', fontsize=15)
                    else:
                        logger.warning(f"Position without rounded timestamp: {position}")
            
            self.ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d %H:%M:%S'))
            plt.xticks(rotation=45, ha='right', color='white')
            plt.yticks(color='white')
            
            self.ax.set_facecolor('#252525')
            self.fig.patch.set_facecolor('#353535')
            
            plt.tight_layout()
            self.canvas.draw()
        else:
            logger.warning("Unable to update chart: pair_price is None or empty")

    def refresh_positions(self):
        positions = []
        if hasattr(self, 'trading_dialog'):
            positions = self.trading_dialog.current_position or []
        else:
            positions = self.current_position or []
        
        self.control_panel.update_positions(positions)
        self.control_panel.update_account_info()
        
        if self.ani:
            self.ani.event_source.stop()
            self.ani = FuncAnimation(self.fig, self.update_chart, interval=UPDATE_INTERVAL, 
                                     blit=False, save_count=100)
            self.canvas.draw()

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

    def toggle_trading_panel(self):
        if self.trading_dialog.is_closed:
            self.trading_dialog = TradingDialog(self, self.symbol1, self.symbol2)
            self.trading_dialog.show()
            self.control_panel.toggle_trading_panel_button.setText("Hide Trading Panel")
        elif self.trading_dialog.isVisible():
            self.trading_dialog.hide()
            self.control_panel.toggle_trading_panel_button.setText("Show Trading Panel")
        else:
            self.trading_dialog.show()
            self.control_panel.toggle_trading_panel_button.setText("Hide Trading Panel")

class TradingDialog(QDialog):
    def __init__(self, parent=None, symbol1="", symbol2=""):
        super().__init__(parent)
        self.setWindowTitle("Pear Tradooor - Trading Panel")
        self.symbol1 = symbol1
        self.symbol2 = symbol2
        self.session = session  # Use the global session object
        self.current_position = None  # Add this line to store the current position
        self.is_closed = False

        # Set the dialog position at the bottom of the screen
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(100, 100, 400, 200)  # Increased height to accommodate new elements

        layout = QVBoxLayout()

        # Add input boxes for base and quote
        self.symbol1_input = QLineEdit(self.symbol1)
        self.symbol2_input = QLineEdit(self.symbol2)
        self.symbol1_input.setPlaceholderText("Base (e.g., BTCUSDT)")
        self.symbol2_input.setPlaceholderText("Quote (e.g., ETHUSDT)")

        layout.addWidget(QLabel("Quote:"))
        layout.addWidget(self.symbol2_input)
        layout.addWidget(QLabel("Base:"))
        layout.addWidget(self.symbol1_input)
        
        # Add Chart button
        self.load_pair_button = QPushButton("Load Pear")
        layout.addWidget(self.load_pair_button)

        # Pair information
        symbol1_truncated = symbol1[:-4] if symbol1.endswith(('USDT', 'USDC')) else symbol1
        symbol2_truncated = symbol2[:-4] if symbol2.endswith(('USDT', 'USDC')) else symbol2
        self.pair_label = QLabel(f"Trading Pair: {symbol2_truncated}/{symbol1_truncated}")
        layout.addWidget(self.pair_label)

        # Long and Short buttons
        button_layout = QHBoxLayout()
        self.long_button = QPushButton("LONG")
        self.short_button = QPushButton("SHORT")
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
        self.load_pair_button.clicked.connect(self.update_chart)

        self.load_position()
        self.set_dark_theme()

    def set_dark_theme(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #353535;
                color: white;
            }
            QPushButton {
                background-color: #2A82DA;
                color: white;
                border: none;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #3A92EA;
            }
            QLineEdit, QDoubleSpinBox {
                background-color: #252525;
                color: white;
                border: 1px solid #555555;
            }
        """)

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
                trade_id = self.generate_trade_id()
                new_position = {
                    'type': 'long',
                    'trade_id': trade_id,
                    'timestamp': datetime.now().isoformat(),
                    'timestamp_rounded': datetime.now().replace(second=0, microsecond=0).isoformat(),
                    'combined_upnl': 0,
                    self.symbol1: {'side': 'Sell', 'qty': qty1, 'entry_price': price1},
                    self.symbol2: {'side': 'Buy', 'qty': qty2, 'entry_price': price2}
                }
                
                if self.current_position is None:
                    self.current_position = [new_position]
                else:
                    self.current_position.append(new_position)
                
                self.save_position()
                self.log_trade('LONG', self.symbol1, self.symbol2, qty1, qty2, price1, price2, trade_id)
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
                trade_id = self.generate_trade_id()
                new_position = {
                    'type': 'short',
                    'trade_id': trade_id,
                    'timestamp': datetime.now().isoformat(),
                    'timestamp_rounded': datetime.now().replace(second=0, microsecond=0).isoformat(),
                    'combined_upnl': 0,
                    self.symbol1: {'side': 'Buy', 'qty': qty1, 'entry_price': price1},
                    self.symbol2: {'side': 'Sell', 'qty': qty2, 'entry_price': price2}
                }
                
                if self.current_position is None:
                    self.current_position = [new_position]
                else:
                    self.current_position.append(new_position)
                
                self.save_position()
                self.log_trade('SHORT', self.symbol1, self.symbol2, qty1, qty2, price1, price2, trade_id)
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
                    if symbol not in ['type', 'timestamp', 'timestamp_rounded'] and isinstance(pos_data, dict):
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
                    if symbol not in ['type', 'timestamp', 'timestamp_rounded', 'combined_upnl', 'trade_id'] and isinstance(pos_data, dict):
                        if float(pos_data['qty']) > 0:  # Only close if there's an open position
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
                        else:
                            print(f"No open position for {symbol}, skipping.")

                self.log_trade('CLOSE', self.symbol1, self.symbol2, 
                               position.get(self.symbol1, {}).get('qty', 0), 
                               position.get(self.symbol2, {}).get('qty', 0), 
                               self.get_current_prices()[0], self.get_current_prices()[1], 
                               position.get('trade_id', ''))
                del self.current_position[index]
                self.save_position()
                self.parent().refresh_positions()
                QMessageBox.information(self, "Success", "Position closed successfully.")
            except Exception as e:
                logger.error(f"Error closing position: {e}")
                QMessageBox.warning(self, "Error", f"Failed to close position: {str(e)}")
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
                    print("Warning: Invalid JSON in current_position.json. Setting current_position to an empty list.")
                    self.current_position = []
        else:
            print("Info: current_position.json doesn't exist or is empty. Setting current_position to an empty list.")
            self.current_position = []
        return self.current_position  # Add this line to always return a list

    def update_symbols(self, symbol1, symbol2):
        self.symbol1 = symbol1
        self.symbol2 = symbol2
        symbol1_truncated = symbol1[:-4] if symbol1.endswith(('USDT', 'USDC')) else symbol1
        symbol2_truncated = symbol2[:-4] if symbol2.endswith(('USDT', 'USDC')) else symbol2

        self.setWindowTitle(f"Pear Tradooor - {symbol2_truncated}/{symbol1_truncated}")
        
        symbol1_truncated = symbol1[:-4] if symbol1.endswith(('USDT', 'USDC')) else symbol1
        symbol2_truncated = symbol2[:-4] if symbol2.endswith(('USDT', 'USDC')) else symbol2
        self.pair_label.setText(f"Trading Pair: {symbol2_truncated}/{symbol1_truncated}")

    def update_chart(self):
        symbol1 = self.symbol1_input.text().upper() or self.symbol1
        symbol2 = self.symbol2_input.text().upper() or self.symbol2
        if self.parent().validate_symbols(symbol1, symbol2):
            self.symbol1 = symbol1
            self.symbol2 = symbol2
            self.parent().symbol1 = symbol1
            self.parent().symbol2 = symbol2
            self.parent().create_chart(symbol1, symbol2)
            self.update_symbols(symbol1, symbol2)
        else:
            QMessageBox.warning(self, "Invalid Symbols", "Please enter valid symbols.")

    def closeEvent(self, event):
        self.hide()
        self.is_closed = True
        self.parent().control_panel.toggle_trading_panel_button.setText("Show Trading Panel")
        event.ignore()

    def log_trade(self, trade_type, symbol1, symbol2, qty1, qty2, price1, price2, trade_id):
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp},{trade_id},{trade_type},{symbol1},{qty1},{price1},{symbol2},{qty2},{price2}\n"
        
        file_exists = os.path.exists('trade_log.csv')
        
        with open('trade_log.csv', 'a') as f:
            if not file_exists:
                f.write("timestamp,trade_id,trade_type,symbol1,qty1,price1,symbol2,qty2,price2\n")  # Write header
            f.write(log_entry)

    def generate_trade_id(self):
        return str(uuid.uuid4())

def main():
    app = QApplication([])
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    window = MainWindow()
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()