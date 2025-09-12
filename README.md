# THE-BEST-BOT: Comprehensive Crypto Analysis Bot

THE-BEST-BOT is an advanced Python-based system for collecting, analyzing, and reporting on cryptocurrency market data from the OKX exchange. It features a dual-mode interface (CLI and interactive Telegram bot), a sophisticated analysis engine, and a real-time monitoring system for trade setups.

## ✨ Key Features

-   📊 **Live & Historical Data:** Continuous WebSocket connection for real-time prices and a robust system for fetching and caching years of historical data.
-   🧠 **Advanced Analysis Engine:**
    -   **Trend Analysis:** Uses multiple EMAs and ADX to determine trend direction and strength.
    -   **Support & Resistance:** Identifies key levels from pivots, Fibonacci retracements, and price channels.
    -   **Classic Patterns:** Detects a wide range of patterns like Triangles, Wedges, Flags, and Double Bottoms.
    -   **Technical Indicators:** Utilizes RSI, MACD, Bollinger Bands, and more to generate a technical score.
-   🤖 **Dual-Mode Operation:**
    -   **Interactive Telegram Bot:** A full-featured bot for on-demand analysis, report generation, and trade monitoring.
    -   **Command-Line Interface (CLI):** For automated analysis and integration with other systems.
-   🔔 **Real-time Trade Monitoring:** Follow promising trade setups and receive real-time alerts on Telegram for key events (e.g., breakouts, target hits, stop-loss triggers).
-   💾 **Smart Caching:** Multi-level caching (in-memory and file-based) for historical data to minimize API calls and improve performance.
-   ⚙️ **Highly Configurable:** Easily configure symbols, timeframes, analysis parameters, and notification settings.

## 📋 Requirements

-   Python 3.8+
-   A stable internet connection
-   A Telegram Bot Token and Chat ID for notifications

## 🚀 Installation and Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd THE-BEST-BOT
    ```

2.  **Install the required libraries:**
    ```bash
    pip install -r requirements.txt
    pip install -r requirements-dev.txt # For development and testing
    ```

3.  **Configure your environment:**
    Create a `.env` file in the root directory of the project and add your API keys and tokens:
    ```env
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
    TELEGRAM_CHAT_ID="your_telegram_chat_id"

    # OKX API Credentials (Optional - for authenticated endpoints)
    EXCHANGE_API_KEY="your_okx_api_key"
    EXCHANGE_API_SECRET="your_okx_api_secret"
    EXCHANGE_API_PASSWORD="your_okx_api_password"
    ```

4.  **Populate Historical Data (Recommended):**
    To ensure the bot has enough data for analysis, run the data population script. This will fetch and cache historical data for all symbols and timeframes defined in `src/config.py`.
    ```bash
    python populate_historical_data.py
    ```
    You can also fetch data for a specific symbol or timeframe:
    ```bash
    python populate_historical_data.py --symbol BTC/USDT --timeframe 1D
    ```

## 💡 Usage

The application can be run in two modes: `interactive` (Telegram bot) or `cli` (command-line tool).

### Interactive Mode (Telegram Bot)

This mode starts the interactive Telegram bot, which allows you to request analysis, view reports, and monitor trades in real-time.

```bash
python main.py interactive
```
Once the bot is running, you can interact with it on Telegram using the `/start` command.

### CLI Mode

This mode runs a one-time analysis for the symbols specified in the `WATCHLIST` in `src/config.py` and sends a report to the configured Telegram chat.

```bash
python main.py cli
```
You can also specify which symbols to analyze directly from the command line:
```bash
python main.py cli BTC/USDT ETH/USDT
```

## ⚙️ Configuration

The main configuration for the application is located in `src/config.py`. Here you can customize:
-   `WATCHLIST`: The list of currency pairs to monitor and analyze.
-   `TIMEFRAMES_TO_ANALYZE`: The timeframes to use for analysis.
-   `TIMEFRAME_GROUPS`: Groupings of timeframes for different analysis types (long-term, medium-term, short-term).
-   `ANALYSIS_CONFIG`: Parameters for the analysis modules, including indicator periods, lookbacks, and timeframe-specific overrides.

## 📁 Project Structure
```
THE-BEST-BOT/
├── src/
│   ├── analysis/         # Core analysis modules (trends, patterns, S/R)
│   ├── data/             # Data fetching (OKX API, WebSocket)
│   ├── decision_engine/  # Logic for making trade recommendations
│   ├── monitoring/       # Real-time trade monitoring
│   ├── notifiers/        # Telegram bot and alert sender
│   ├── reporting/        # Report generation
│   ├── utils/            # Helper functions and validators
│   ├── app.py            # Main logic for the CLI mode
│   ├── config.py         # Main configuration file
│   └── service_manager.py# Manages background services
├── tests/                # Unit and integration tests
├── main.py               # Main entry point for the application
├── populate_historical_data.py # Script to pre-load data
├── requirements.txt      # Main dependencies
└── README.md             # This file
```

## 📈 Future Development

-   [ ] Integration with more exchanges.
-   [ ] Addition of more technical indicators and patterns.
-   [ ] A web interface for monitoring and configuration.
-   [ ] Support for futures and other derivatives.
-   [ ] AI/ML-based predictive analysis.