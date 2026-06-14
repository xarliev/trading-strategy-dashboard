from __future__ import annotations
import pandas as pd


def _market_ok(df: pd.DataFrame, market_symbol: str) -> bool:
    m = df[df['symbol'] == market_symbol].sort_values('Date')
    if len(m) < 200:
        return False
    last = m.iloc[-1]
    return bool(last['Close'] > last['SMA200'] and (last['Close'] > last['EMA20'] or m.iloc[-2]['Close'] < m.iloc[-2]['EMA20']))


def detect_signals(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    s_cfg = cfg['strategy']
    account = cfg['account']
    market_symbol = cfg.get('market_index', 'SPY')
    market_ok = _market_ok(df, market_symbol)
    signals = []

    for symbol, g in df.groupby('symbol'):
        if symbol == market_symbol:
            continue
        g = g.sort_values('Date').reset_index(drop=True)
        if len(g) < 205:
            continue
        last = g.iloc[-1]
        prev = g.iloc[-2]
        if pd.isna(last[['EMA20','SMA50','SMA200','ATR14','AVG_VOL20']]).any():
            continue

        trend_ok = (
            last['Close'] > last['SMA200'] and
            last['SMA50'] > last['SMA200'] and
            last['Close'] >= s_cfg['min_price'] and
            last['AVG_VOL20'] >= s_cfg['min_avg_volume_20'] and
            last['DIST_SMA50_PCT'] <= s_cfg['max_distance_above_sma50_pct']
        )
        if not (market_ok and trend_ok):
            continue

        # Retroceso: al menos 2 velas de corrección reciente y toque/proximidad a EMA20 o SMA50 sin cerrar bajo SMA50.
        recent = g.iloc[-6:]
        last2 = g.iloc[-2:]
        pullback_ok = (
            (last2['Close'].diff().iloc[-1] < 0 or (last2['High'].iloc[-1] < last2['High'].iloc[-2])) and
            (recent['Low'].min() <= max(last['EMA20'], last['SMA50']) * 1.01) and
            (recent['Close'] >= recent['SMA50']).all()
        )

        candle_range = max(last['High'] - last['Low'], 1e-9)
        close_upper_half = last['Close'] >= last['Low'] + 0.5 * candle_range
        bullish_turn = close_upper_half and ((last['High'] > prev['High']) or (last['Close'] > prev['Close']))
        if not (pullback_ok and bullish_turn):
            continue

        entry = float(last['High'] * (1 + s_cfg['entry_buffer_pct']))
        stop = float(last['Low'] - (s_cfg['stop_atr_buffer_mult'] * last['ATR14']))
        risk_per_share = entry - stop
        if risk_per_share <= 0:
            continue
        risk_amount = account['equity'] * account['risk_per_trade_pct']
        qty = int(risk_amount / risk_per_share)
        if qty <= 0:
            continue
        target_2r = entry + (s_cfg['partial_exit_r'] * risk_per_share)

        broker = cfg.get('broker', {})
        commission_buy = float(broker.get('commission_buy_eur', account.get('commission_per_side', 0)))
        commission_sell = float(broker.get('commission_sell_eur', account.get('commission_per_side', 0)))
        estimated_fees = commission_buy + commission_sell
        max_gap_pct = float(broker.get('max_open_gap_above_entry_pct', 0.01))
        max_gap_atr_mult = float(broker.get('max_open_gap_above_entry_atr_mult', 1.0))
        max_allowed_open_by_pct = entry * (1 + max_gap_pct)
        max_allowed_open_by_atr = entry + (max_gap_atr_mult * float(last['ATR14']))
        max_allowed_open = min(max_allowed_open_by_pct, max_allowed_open_by_atr)

        signals.append({
            'date': str(last['Date']),
            'symbol': symbol,
            'close': round(float(last['Close']), 4),
            'broker': broker.get('name', 'Unknown'),
            'entry_order_type': broker.get('entry_order_type', 'buy_stop'),
            'entry_stop': round(entry, 4),
            'entry_limit': '',
            'stop_loss': round(stop, 4),
            'risk_per_share': round(risk_per_share, 4),
            'target_2r': round(float(target_2r), 4),
            'qty': qty,
            'risk_amount': round(float(qty * risk_per_share), 2),
            'commission_buy_eur': round(float(commission_buy), 2),
            'commission_sell_eur': round(float(commission_sell), 2),
            'estimated_roundtrip_fees': round(float(estimated_fees), 2),
            'max_allowed_open_price': round(float(max_allowed_open), 4),
            'max_open_gap_above_entry_pct': round(float(max_gap_pct), 4),
            'setup': 'trend_pullback_signal_candle',
            'status': 'pending_entry',
            'notes': 'Trade Republic: usar orden BUY STOP, no stop-limit. Antes de ejecutar, cancelar/no cursar si la apertura supera max_allowed_open_price o si no activa en 2 sesiones.'
        })
    return pd.DataFrame(signals)
