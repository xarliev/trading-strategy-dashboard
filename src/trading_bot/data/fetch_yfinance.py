from __future__ import annotations

from datetime import datetime, timedelta, timezone
import time
import pandas as pd
import yfinance as yf


def fetch_symbol(symbol: str, lookback_days: int = 370, retries: int = 3) -> pd.DataFrame:
    end = datetime.now(timezone.utc).date() + timedelta(days=1)
    start = end - timedelta(days=lookback_days)
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            df = yf.download(
                symbol,
                start=str(start),
                end=str(end),
                interval='1d',
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            if df is None or df.empty:
                raise ValueError('yfinance returned empty data')
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            df = df.reset_index()
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            df['symbol'] = symbol
            required = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'symbol']
            return df[required].dropna(subset=['Open', 'High', 'Low', 'Close'])
        except Exception as exc:
            last_error = exc
            time.sleep(2 * attempt)
    raise RuntimeError(f'Failed to fetch {symbol}: {last_error}')


def fetch_universe(symbols: list[str], lookback_days: int = 370) -> tuple[pd.DataFrame, list[str]]:
    frames = []
    failed = []
    for symbol in symbols:
        try:
            frames.append(fetch_symbol(symbol, lookback_days=lookback_days))
        except Exception as exc:
            print(f'[WARN] {symbol}: {exc}')
            failed.append(symbol)
    if not frames:
        return pd.DataFrame(), failed
    return pd.concat(frames, ignore_index=True), failed
