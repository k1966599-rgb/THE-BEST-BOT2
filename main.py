import argparse
import logging
import sys
from src.config import get_config

# --- Setup logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """
    The main entry point for the application.
    Parses command-line arguments to decide which mode to run:
    - 'cli': The command-line analysis tool.
    - 'interactive': The interactive Telegram bot.
    """
    parser = argparse.ArgumentParser(description='The Best Bot - Main Entry Point')
    parser.add_argument(
        'mode',
        choices=['cli', 'interactive'],
        help="The mode to run the application in ('cli' or 'interactive')."
    )
    # Allow the CLI app to still accept its own arguments
    # We parse known args here and let the app parse the rest.
    args, unknown_args = parser.parse_known_args()

    # --- Initialize Components ---
    from src.data.okx_fetcher import OKXDataFetcher
    from src.analysis.orchestrator import AnalysisOrchestrator
    from src.decision_engine.engine import DecisionEngine
    from src.analysis import (
        TechnicalIndicators, TrendAnalysis, PriceChannels,
        SupportResistanceAnalysis, FibonacciAnalysis, ClassicPatterns, TrendLineAnalysis,
        VolumeProfileAnalysis
    )

    config = get_config()
    fetcher = OKXDataFetcher(config)

    analysis_modules = [
        TechnicalIndicators(config=config.get('analysis')),
        TrendAnalysis(config=config.get('analysis')),
        PriceChannels(config=config.get('analysis')),
        SupportResistanceAnalysis(config=config.get('analysis')),
        FibonacciAnalysis(config=config.get('analysis')),
        ClassicPatterns(config=config.get('analysis')),
        TrendLineAnalysis(config=config.get('analysis')),
        VolumeProfileAnalysis(config=config.get('analysis'))
    ]
    orchestrator = AnalysisOrchestrator(analysis_modules, config=config)
    decision_engine = DecisionEngine(config)

    # --- Run Selected Mode ---
    if args.mode == 'cli':
        logger.info("Starting in CLI mode...")
        # We need to pass the unknown args back to the app
        sys.argv = [sys.argv[0]] + unknown_args
        from src.app import main as cli_main
        cli_main(config, fetcher, orchestrator, decision_engine)

    elif args.mode == 'interactive':
        logger.info("Starting in Interactive mode...")
        from src.notifiers.telegram_notifier import InteractiveTelegramBot
        from src.service_manager import ServiceManager

        # The interactive bot needs access to all the core components
        interactive_bot = InteractiveTelegramBot(
            config=config,
            fetcher=fetcher,
            orchestrator=orchestrator,
            decision_engine=decision_engine
        )

        service_manager = ServiceManager(fetcher)

        # Start background data services before running the bot
        logger.info("🚀 Starting background data services for interactive bot...")
        watchlist = config.get('trading', {}).get('WATCHLIST', [])
        okx_symbols = [s.replace('/', '-') for s in watchlist]
        service_manager.start_services(okx_symbols)
        logger.info("⏳ Waiting 10 seconds for initial data...")
        import time
        time.sleep(10)

        try:
            interactive_bot.start()
        finally:
            logger.info("⏹️ Stopping data services for interactive bot...")
            service_manager.stop_services()

if __name__ == "__main__":
    main()
