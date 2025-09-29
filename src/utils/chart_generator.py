import mplfinance as mpf
import pandas as pd
from typing import Dict, Any
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

def generate_analysis_chart(df: pd.DataFrame, analysis_data: Dict[str, Any], symbol: str) -> str:
    """
    Generates a candlestick chart with technical analysis overlays and saves it as a PNG file.

    Args:
        df (pd.DataFrame): The DataFrame containing the OHLCV data and indicators.
        analysis_data (Dict[str, Any]): The dictionary containing the analysis results.
        symbol (str): The trading symbol (e.g., 'BTC-USDT').

    Returns:
        str: The file path of the generated chart image, or an empty string if an error occurs.
    """
    try:
        # --- 1. Data Preparation ---
        # Ensure the DataFrame has the correct column names and index for mplfinance
        chart_df = df.copy()
        chart_df.rename(columns={
            'timestamp': 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }, inplace=True)
        chart_df['Date'] = pd.to_datetime(chart_df['Date'], unit='ms')
        chart_df.set_index('Date', inplace=True)

        # We only want to plot the last N candles to keep the chart clean
        chart_df = chart_df.tail(100)

        # --- 2. Styling and Title ---
        chart_style = 'charles' # A good dark-mode style
        market_colors = mpf.make_marketcolors(up='#00ff00', down='#ff0000', inherit=True)
        style = mpf.make_mpf_style(base_mpf_style=chart_style, marketcolors=market_colors, gridstyle=':')

        title = f"\nتحليل فني لـ {symbol} | {analysis_data.get('timeframe', 'N/A')}"

        # --- 3. Prepare Overlays and Plots ---
        plots_to_add = []

        # Add Moving Averages
        if 'sma_fast' in chart_df.columns and 'sma_slow' in chart_df.columns:
            plots_to_add.append(mpf.make_addplot(chart_df['sma_fast'], color='cyan', width=0.7))
            plots_to_add.append(mpf.make_addplot(chart_df['sma_slow'], color='orange', width=0.7))

        # Prepare horizontal lines for Fibonacci levels, swing high/low
        hlines_data = []
        colors = []

        swing_high = analysis_data.get('swing_high', {}).get('price')
        swing_low = analysis_data.get('swing_low', {}).get('price')

        if swing_high:
            hlines_data.append(swing_high)
            colors.append('red') # Swing High is a resistance
        if swing_low:
            hlines_data.append(swing_low)
            colors.append('green') # Swing Low is a support

        retracements = analysis_data.get('retracements', {})
        fib_levels_to_plot = ['fib_382', 'fib_500', 'fib_618']
        for level in fib_levels_to_plot:
            if level in retracements:
                hlines_data.append(retracements[level])
                colors.append('yellow')

        # --- 4. Generate and Save the Chart ---
        # Ensure the 'charts' directory exists
        output_dir = "charts"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Define a unique filename
        output_path = os.path.join(output_dir, f"{symbol.replace('/', '_')}_{analysis_data.get('timeframe', 'N/A')}.png")

        mpf.plot(
            chart_df,
            type='candle',
            style=style,
            title=title,
            ylabel='السعر (USDT)',
            volume=True,
            ylabel_lower='حجم التداول',
            addplot=plots_to_add if plots_to_add else None,
            hlines=dict(hlines=hlines_data, colors=colors, linestyle='--'),
            figratio=(16, 9),
            savefig=output_path
        )

        logger.info(f"Successfully generated chart and saved to {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Failed to generate chart for {symbol}: {e}", exc_info=True)
        return ""