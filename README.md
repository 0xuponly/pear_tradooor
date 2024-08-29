# Bybit Trading Bot

This project implements an automated trading bot for the Bybit cryptocurrency exchange.

## Features

- Connects to Bybit API
- Implements a simple moving average crossover strategy
- Manages orders and positions
- Fetches historical price data
- Provides basic risk management

## Project Structure

```
bybit_trading/
├── config/
│   └── config.py
├── trading_api/
│   └── bybit_api.py
├── trading_brain/
│   └── strategy.py
├── data/
│   └── historical_data.py
├── orders/
│   └── order_management.py
├── utils/
│   └── helpers.py
├── main.py
├── requirements.txt
└── README.md

```

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up your Bybit API credentials in `config/config.py`

## Usage

Run the bot with:

```
python main.py
```

## Configuration

Edit `config/config.py` to adjust trading parameters such as:

- Trading pair
- Strategy parameters
- Risk management settings
- yo mama

## Disclaimer

This bot is for educational purposes only. Use at your own risk. Cryptocurrency trading carries a high level of risk and may not be suitable for all investors. You will like go insane or lose it all, possibly both. Tread with caution, nerd.

## License

[MIT License](https://opensource.org/licenses/MIT)

## Virtual Environment Setup

To set up the virtual environment, follow these steps:

1. ??? (good luck)
   ```
2. Create a virtual environment:
   ```
   python3 -m venv new_env
   ```
3. Activate the virtual environment:
   - On Windows:
     ```
     new_env\Scripts\activate
     ```
   - On macOS and Linux:
     ```
     source new_env/bin/activate
     ```