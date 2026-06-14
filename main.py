from pathlib import Path
import pandas as pd
from src.trading_bot.utils.config import load_config, ROOT
from src.trading_bot.data.fetch_yfinance import fetch_universe
from src.trading_bot.indicators.technical import add_indicators
from src.trading_bot.strategy.signals import detect_signals
from src.trading_bot.journal.journal import append_pending_signals, load_journal
from src.trading_bot.reporting.dashboard import build_dashboard


def main():
    cfg = load_config()
    data_raw = ROOT / 'data' / 'raw'
    data_processed = ROOT / 'data' / 'processed'
    dashboard_dir = ROOT / 'dashboard'
    data_raw.mkdir(parents=True, exist_ok=True)
    data_processed.mkdir(parents=True, exist_ok=True)

    prices, failed = fetch_universe(cfg['symbols'], cfg['strategy']['lookback_days'])
    if prices.empty:
        raise RuntimeError('No data downloaded. Check yfinance/connectivity/symbols.')
    prices.to_parquet(data_raw / 'prices_latest.parquet', index=False)

    enriched = add_indicators(prices, atr_period=cfg['strategy']['atr_period'])
    enriched.to_parquet(data_processed / 'prices_indicators_latest.parquet', index=False)

    signals = detect_signals(enriched, cfg)
    signals.to_csv(data_processed / 'signals_latest.csv', index=False)
    signals.to_parquet(data_processed / 'signals_latest.parquet', index=False)

    journal_path = data_processed / 'trading_journal.csv'
    journal = append_pending_signals(journal_path, signals)
    build_dashboard(signals, journal, dashboard_dir)

    print(f'Downloaded rows: {len(prices)}')
    print(f'Failed symbols: {failed}')
    print(f'Signals: {len(signals)}')
    print(f'Journal rows: {len(journal)}')


if __name__ == '__main__':
    main()
