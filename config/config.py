# Trading parameters
UPDATE_INTERVAL = 10000  # Update interval in milliseconds

# Other settings
TESTNET = False  # Set to True for testnet, False for live trading

# Chart settings
CHART_FIGSIZE = (12, 8)
CHART_INTERVAL = "1"
CHART_LIMIT = 300

# UI settings
CONTROL_PANEL_WIDTH = 400
CONTROL_PANEL_HEIGHT = 200
TRADING_DIALOG_WIDTH = 400
TRADING_DIALOG_HEIGHT = 250

# Order settings
DEFAULT_ORDER_SIZE = 1000
MIN_ORDER_SIZE = 10
MAX_ORDER_SIZE = 1000000

# File paths
CURRENT_POSITION_FILE = 'current_position.json'
TRADE_LOG_FILE = 'trade_log.csv'

# API settings
API_KEY_ENV_VAR = "API_KEY"
API_SECRET_ENV_VAR = "API_SECRET"

# Bybit API settings
BYBIT_CATEGORY = "linear"
BYBIT_SETTLE_COIN = "USDT"

# Default symbols
DEFAULT_SYMBOL1 = "BTCUSDT"
DEFAULT_SYMBOL2 = "POPCATUSDT"
