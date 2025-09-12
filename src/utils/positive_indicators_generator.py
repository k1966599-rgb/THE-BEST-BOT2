from typing import Dict, List

def generate_positive_indicators(analysis_results: Dict, current_price: float) -> List[str]:
    """Analyzes the full results dictionary and generates a human-readable list
    of positive (bullish) indicators.

    Args:
        analysis_results (Dict): The dictionary containing all analysis results.
        current_price (float): The current price of the asset.

    Returns:
        List[str]: A list of human-readable strings describing positive indicators.
    """
    indicators = []

    indicator_data = analysis_results.get('indicators', {})
    sr_data = analysis_results.get('support_resistance', {})
    pattern_data = analysis_results.get('patterns', {})
    fib_data = analysis_results.get('fibonacci', {})

    if indicator_data.get('rsi', 50) < 35:
        indicators.append("✅ RSI is approaching the oversold zone")

    if indicator_data.get('macd_is_bullish'):
        indicators.append("✅ MACD shows a positive signal")

    demand_zone = sr_data.get('primary_demand_zone')
    if demand_zone and current_price > 0 and (demand_zone.get('distance', 1) / current_price) < 0.02:
        indicators.append("✅ Price is near a strong support zone")

    found_patterns = pattern_data.get('found_patterns', [])
    if found_patterns:
        bullish_patterns = ['Double Bottom', 'Triangle/Wedge Forming', 'قاع مزدوج (Double Bottom)']
        for p in found_patterns:
            if p.get('name') in bullish_patterns:
                indicators.append(f"✅ Positive technical pattern: {p.get('name')}")
                break

    retracements = fib_data.get('retracement_levels', [])
    key_fib_levels = ['61.8%', '38.2%']
    for level in retracements:
        if level.get('level') in key_fib_levels and current_price > 0:
            if 0 < (current_price - level.get('price', 0)) / current_price < 0.015:
                 indicators.append(f"✅ Fibonacci level {level.get('level')} is holding as support")

    bb_data = indicator_data.get('bollinger_bands', {})
    if bb_data and current_price < bb_data.get('lower', float('inf')):
        indicators.append("✅ Price is touching the lower Bollinger Band")

    stoch_data = indicator_data.get('stochastic', {})
    if stoch_data and stoch_data.get('slowk', 100) < 20:
        indicators.append("✅ Stochastic indicator is in the oversold zone")

    return indicators
