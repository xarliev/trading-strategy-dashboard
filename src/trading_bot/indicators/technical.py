from __future__ import annotations
import pandas as pd


def add_indicators(df: pd.DataFrame, atr_period: int = 14) -> pd.DataFrame:
    out = df.copy().sort_values(['symbol', 'Date'])
    pieces = []
    for symbol, g in out.groupby('symbol', sort=False):
        g = g.copy().sort_values('Date')
        g['EMA20'] = g['Close'].ewm(span=20, adjust=False).mean()
        g['EMA10'] = g['Close'].ewm(span=10, adjust=False).mean()
        g['SMA50'] = g['Close'].rolling(50).mean()
        g['SMA200'] = g['Close'].rolling(200).mean()
        prev_close = g['Close'].shift(1)
        tr = pd.concat([
            g['High'] - g['Low'],
            (g['High'] - prev_close).abs(),
            (g['Low'] - prev_close).abs(),
        ], axis=1).max(axis=1)
        g['ATR14'] = tr.rolling(atr_period).mean()
        g['AVG_VOL20'] = g['Volume'].rolling(20).mean()
        g['DIST_SMA50_PCT'] = (g['Close'] / g['SMA50']) - 1
        pieces.append(g)
    return pd.concat(pieces, ignore_index=True)
