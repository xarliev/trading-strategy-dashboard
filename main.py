from pathlib import Path
import pandas as pd
from src.trading_bot.utils.config import load_config, ROOT
from src.trading_bot.data.fetch_yfinance import fetch_universe
from src.trading_bot.indicators.technical import add_indicators
from src.trading_bot.strategy.signals import scan_universe
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

    signals, diagnostics = scan_universe(enriched, cfg)
    signals.to_csv(data_processed / 'signals_latest.csv', index=False)
    signals.to_parquet(data_processed / 'signals_latest.parquet', index=False)
    diagnostics.to_csv(data_processed / 'scan_diagnostics_latest.csv', index=False)
    diagnostics.to_parquet(data_processed / 'scan_diagnostics_latest.parquet', index=False)

    # Histórico acumulado para poder revisar cómo evolucionan los tickers día a día.
    diagnostics_history_path = data_processed / 'scan_diagnostics_history.csv'
    if diagnostics_history_path.exists():
        previous = pd.read_csv(diagnostics_history_path)
        diagnostics_history = pd.concat([previous, diagnostics], ignore_index=True)
        diagnostics_history = diagnostics_history.drop_duplicates(subset=['run_date', 'symbol'], keep='last')
    else:
        diagnostics_history = diagnostics.copy()
    diagnostics_history.to_csv(diagnostics_history_path, index=False)

    journal_path = data_processed / 'trading_journal.csv'
    journal = append_pending_signals(journal_path, signals)
    build_dashboard(signals, journal, dashboard_dir, diagnostics=diagnostics)

    print(f'Downloaded rows: {len(prices)}')
    print(f'Failed symbols: {failed}')
    print(f'Signals: {len(signals)}')
    print(f'Diagnostics rows: {len(diagnostics)}')
    print(f'Journal rows: {len(journal)}')


if __name__ == '__main__':
    main()
