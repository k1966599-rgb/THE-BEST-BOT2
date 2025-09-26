import pandas as pd
import mplfinance as mpf
import io
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def generate_analysis_chart(
    df: pd.DataFrame,
    analysis_info: Dict[str, Any],
    symbol: str,
    timeframe: str
) -> Optional[io.BytesIO]:
    """
    Generates a candlestick chart with analysis overlays.

    Args:
        df (pd.DataFrame): The OHLCV data.
        analysis_info (Dict[str, Any]): The dictionary containing analysis results.
        symbol (str): The trading symbol.
        timeframe (str): The timeframe of the chart.

    Returns:
        Optional[io.BytesIO]: A buffer containing the PNG image of the chart, or None if an error occurs.
    """
    try:
        # Ensure the DataFrame has a DatetimeIndex as required by mplfinance
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
        elif not isinstance(df.index, pd.DatetimeIndex):
            logger.error("DataFrame must have a 'timestamp' column or a DatetimeIndex.")
            return None

        # Take the last N candles to make the chart readable
        plot_df = df.tail(100)

        # --- Prepare Plotting Elements ---
        hlines_data = {'hlines': [], 'colors': [], 'linestyles': '--'}

        # Fibonacci Levels
        fib_levels = analysis_info.get('retracements', {})
        if fib_levels:
            for price in fib_levels.values():
                hlines_data['hlines'].append(price)
                hlines_data['colors'].append('blue')

        # Swing High/Low
        swing_high = analysis_info.get('swing_high', {}).get('price')
        swing_low = analysis_info.get('swing_low', {}).get('price')
        if swing_high:
            hlines_data['hlines'].append(swing_high)
            hlines_data['colors'].append('red')
        if swing_low:
            hlines_data['hlines'].append(swing_low)
            hlines_data['colors'].append('green')

        # Risk levels from scenarios
        scenario1 = analysis_info.get('scenarios', {}).get('scenario1', {})
        entry_price = scenario1.get('entry')
        stop_loss = scenario1.get('stop_loss')
        take_profit = scenario1.get('target')

        if entry_price:
            hlines_data['hlines'].append(entry_price)
            hlines_data['colors'].append('gray')
        if stop_loss:
            hlines_data['hlines'].append(stop_loss)
            hlines_data['colors'].append('orange')
        if take_profit:
            hlines_data['hlines'].append(take_profit)
            hlines_data['colors'].append('purple')

        # --- Create Plot ---
        style = mpf.make_mpf_style(base_mpf_style='yahoo', gridstyle='--')
        fig, axlist = mpf.plot(
            plot_df,
            type='candle',
            style=style,
            title=f"Analysis for {symbol} on {timeframe}",
            ylabel='Price (USDT)',
            volume=True,
            hlines=hlines_data,
            figsize=(15, 8),
            returnfig=True
        )

        # --- Save to buffer ---
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)

        logger.info(f"Successfully generated chart for {symbol} on {timeframe}.")
        return buf

    except Exception as e:
        logger.error(f"Failed to generate chart for {symbol}: {e}", exc_info=True)
        return None