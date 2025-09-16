# Professional Trading Bot for OKX

This is a Python-based trading bot designed for the OKX exchange. It provides a framework for developing, backtesting, and deploying automated trading strategies. The bot is built with a modular structure to allow for easy extension and customization.

## Key Features

- **OKX Exchange Integration**: Connects to the OKX V5 API for both market data and trade execution.
- **Sandbox & Live Trading**: A simple configuration flag (`SANDBOX_MODE`) allows switching between a safe demo environment and live trading.
- **Pluggable Strategy Framework**: Easily create new strategies by inheriting from a `BaseStrategy` class. Comes with a sample Fibonacci-based strategy.
- **Backtesting Engine**: A simple, event-driven backtester to evaluate strategy performance on historical data before deployment.
- **Data Population Utility**: Includes a script to download and store historical candle data locally for backtesting.
- **Unit Testing Framework**: Uses `pytest` to ensure the reliability of individual components.

## Project Structure

```
.
├── data/                 # Stores historical market data for backtesting
├── src/                  # Main source code
│   ├── backtesting/      # Backtesting engine and data loader
│   ├── core/             # Core trading engine logic
│   ├── data_retrieval/   # Data fetching from the exchange
│   ├── execution/        # Order execution handler
│   ├── strategies/       # Trading strategy implementations
│   └── utils/            # Helper functions (e.g., technical indicators)
├── tests/                # Unit and integration tests
├── .env                  # Environment variables (API keys, etc.) - MUST BE CREATED
├── main.py               # Main entry point to run the bot
├── populate_data.py      # Script to download historical data
├── requirements.txt      # Python dependencies
└── README.md
```

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create the environment file:**
    Create a file named `.env` in the project root. This file will hold your secret API keys. Copy the following into it and replace the placeholder values.

    ```ini
    # OKX API Credentials
    # Get these from your OKX account
    EXCHANGE_API_KEY="your_api_key"
    EXCHANGE_API_SECRET="your_secret_key"
    EXCHANGE_API_PASSWORD="your_api_password"

    # Trading Mode: 'True' for sandbox/demo, 'False' for live trading
    SANDBOX_MODE=True
    ```

## Usage

### 1. Populate Historical Data

Before backtesting, you need to download the data for the symbols in your watchlist.

```bash
python populate_data.py
```
This will create JSON files in the `data/` directory.

### 2. Run a Backtest

To test your strategy against the historical data you just downloaded:

```bash
python -m src.backtesting.backtester
```
This will run the backtest defined in the `if __name__ == '__main__':` block of the `backtester.py` file and print the results.

### 3. Run the Live/Sandbox Bot

To start the bot in live or sandbox mode (depending on your `.env` setting):

```bash
python main.py
```
The bot will start running and log its activities to the console and to `trading_bot.log`. Press `Ctrl+C` to stop it.

## Strategy Development

To create your own strategy:
1.  Create a new Python file in the `src/strategies/` directory (e.g., `my_strategy.py`).
2.  Create a class that inherits from `BaseStrategy`.
3.  Implement the `generate_signals` method. This method receives a pandas DataFrame of historical data and must return a dictionary with a `signal` key ('BUY', 'SELL', or 'HOLD').

See `src/strategies/fibo_strategy.py` for an example.
