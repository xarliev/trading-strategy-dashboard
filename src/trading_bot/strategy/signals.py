from __future__ import annotations
import pandas as pd


def _market_ok(df: pd.DataFrame, market_symbol: str) -> tuple[bool, dict]:
    """Return market filter state and useful context."""
    m = df[df['symbol'] == market_symbol].sort_values('Date')
    context = {
        'market_symbol': market_symbol,
        'market_rows': int(len(m)),
        'market_close': None,
        'market_ema20': None,
        'market_sma200': None,
        'market_price_above_sma200': False,
        'market_above_or_recovering_ema20': False,
    }
    if len(m) < 200:
        return False, context
    last = m.iloc[-1]
    prev = m.iloc[-2]
    context.update({
        'market_close': round(float(last['Close']), 4),
        'market_ema20': round(float(last['EMA20']), 4) if pd.notna(last['EMA20']) else None,
        'market_sma200': round(float(last['SMA200']), 4) if pd.notna(last['SMA200']) else None,
        'market_price_above_sma200': bool(last['Close'] > last['SMA200']),
        'market_above_or_recovering_ema20': bool(last['Close'] > last['EMA20'] or prev['Close'] < prev['EMA20']),
    })
    ok = bool(context['market_price_above_sma200'] and context['market_above_or_recovering_ema20'])
    return ok, context


def _base_empty_signal_columns() -> list[str]:
    return [
        'date', 'symbol', 'close', 'broker', 'entry_order_type', 'entry_stop', 'entry_limit',
        'stop_loss', 'risk_per_share', 'target_2r', 'qty', 'risk_amount',
        'commission_buy_eur', 'commission_sell_eur', 'estimated_roundtrip_fees',
        'max_allowed_open_price', 'max_open_gap_above_entry_pct', 'setup', 'status', 'notes'
    ]


def _base_diagnostic_columns() -> list[str]:
    return [
        'run_date', 'symbol', 'role', 'latest_date', 'rows', 'classification', 'passed_checks',
        'total_checks', 'score_pct', 'failed_checks', 'reason', 'market_ok', 'trend_ok',
        'setup_ok', 'signal_ok', 'enough_data', 'indicators_ok', 'price_ok', 'volume_ok',
        'close_above_sma200', 'sma50_above_sma200', 'distance_sma50_ok', 'pullback_ok',
        'bullish_turn_ok', 'close_upper_half', 'recent_low_near_ema20_or_sma50',
        'recent_close_above_sma50', 'recent_correction_ok', 'qty_ok', 'risk_per_share_ok',
        'close', 'ema20', 'sma50', 'sma200', 'atr14', 'avg_vol20', 'dist_sma50_pct',
        'entry_stop', 'stop_loss', 'risk_per_share', 'target_2r', 'qty',
        'max_allowed_open_price'
    ]


def scan_universe(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Evaluate every configured ticker and return:
    - signals: only valid pending-entry signals.
    - diagnostics: one row per evaluated ticker with every condition and why it passed/failed.
    """
    s_cfg = cfg['strategy']
    account = cfg['account']
    market_symbol = cfg.get('market_index', 'SPY')
    market_ok, market_ctx = _market_ok(df, market_symbol)
    signals = []
    diagnostics = []
    run_date = pd.Timestamp.utcnow().strftime('%Y-%m-%d')

    for symbol, g in df.groupby('symbol'):
        g = g.sort_values('Date').reset_index(drop=True)
        role = 'market_index' if symbol == market_symbol else 'candidate'

        diag = {
            'run_date': run_date,
            'symbol': symbol,
            'role': role,
            'latest_date': '',
            'rows': int(len(g)),
            'classification': 'rejected',
            'passed_checks': 0,
            'total_checks': 0,
            'score_pct': 0.0,
            'failed_checks': '',
            'reason': '',
            'market_ok': bool(market_ok),
            'trend_ok': False,
            'setup_ok': False,
            'signal_ok': False,
            'enough_data': False,
            'indicators_ok': False,
            'price_ok': False,
            'volume_ok': False,
            'close_above_sma200': False,
            'sma50_above_sma200': False,
            'distance_sma50_ok': False,
            'pullback_ok': False,
            'bullish_turn_ok': False,
            'close_upper_half': False,
            'recent_low_near_ema20_or_sma50': False,
            'recent_close_above_sma50': False,
            'recent_correction_ok': False,
            'qty_ok': False,
            'risk_per_share_ok': False,
            'close': None,
            'ema20': None,
            'sma50': None,
            'sma200': None,
            'atr14': None,
            'avg_vol20': None,
            'dist_sma50_pct': None,
            'entry_stop': None,
            'stop_loss': None,
            'risk_per_share': None,
            'target_2r': None,
            'qty': None,
            'max_allowed_open_price': None,
        }

        if symbol == market_symbol:
            diag['classification'] = 'market_ok' if market_ok else 'market_filter_failed'
            diag['reason'] = 'Filtro de mercado general usado para permitir/bloquear nuevas entradas.'
            diagnostics.append(diag)
            continue

        if len(g) < 205:
            diag['classification'] = 'insufficient_data'
            diag['reason'] = 'No hay suficientes velas para calcular SMA200 y validar la estrategia.'
            diag['failed_checks'] = 'enough_data'
            diagnostics.append(diag)
            continue

        last = g.iloc[-1]
        prev = g.iloc[-2]
        diag['latest_date'] = str(last['Date'])
        indicator_cols = ['EMA20', 'SMA50', 'SMA200', 'ATR14', 'AVG_VOL20']
        indicators_ok = not pd.isna(last[indicator_cols]).any()
        diag['indicators_ok'] = bool(indicators_ok)

        for src_col, out_col in [
            ('Close', 'close'), ('EMA20', 'ema20'), ('SMA50', 'sma50'), ('SMA200', 'sma200'),
            ('ATR14', 'atr14'), ('AVG_VOL20', 'avg_vol20'), ('DIST_SMA50_PCT', 'dist_sma50_pct')
        ]:
            if src_col in last and pd.notna(last[src_col]):
                diag[out_col] = round(float(last[src_col]), 4)

        if not indicators_ok:
            diag['classification'] = 'insufficient_indicators'
            diag['reason'] = 'Hay indicadores NaN en la última vela.'
            diag['failed_checks'] = 'indicators_ok'
            diagnostics.append(diag)
            continue

        diag['enough_data'] = True
        diag['price_ok'] = bool(last['Close'] >= s_cfg['min_price'])
        diag['volume_ok'] = bool(last['AVG_VOL20'] >= s_cfg['min_avg_volume_20'])
        diag['close_above_sma200'] = bool(last['Close'] > last['SMA200'])
        diag['sma50_above_sma200'] = bool(last['SMA50'] > last['SMA200'])
        diag['distance_sma50_ok'] = bool(last['DIST_SMA50_PCT'] <= s_cfg['max_distance_above_sma50_pct'])

        trend_ok = (
            diag['close_above_sma200'] and
            diag['sma50_above_sma200'] and
            diag['price_ok'] and
            diag['volume_ok'] and
            diag['distance_sma50_ok']
        )
        diag['trend_ok'] = bool(trend_ok)

        recent = g.iloc[-6:]
        last2 = g.iloc[-2:]
        diag['recent_correction_ok'] = bool(
            (last2['Close'].diff().iloc[-1] < 0) or (last2['High'].iloc[-1] < last2['High'].iloc[-2])
        )
        diag['recent_low_near_ema20_or_sma50'] = bool(
            recent['Low'].min() <= max(last['EMA20'], last['SMA50']) * 1.01
        )
        diag['recent_close_above_sma50'] = bool((recent['Close'] >= recent['SMA50']).all())
        pullback_ok = (
            diag['recent_correction_ok'] and
            diag['recent_low_near_ema20_or_sma50'] and
            diag['recent_close_above_sma50']
        )
        diag['pullback_ok'] = bool(pullback_ok)

        candle_range = max(last['High'] - last['Low'], 1e-9)
        close_upper_half = last['Close'] >= last['Low'] + 0.5 * candle_range
        bullish_turn = close_upper_half and ((last['High'] > prev['High']) or (last['Close'] > prev['Close']))
        diag['close_upper_half'] = bool(close_upper_half)
        diag['bullish_turn_ok'] = bool(bullish_turn)
        setup_ok = bool(pullback_ok and bullish_turn)
        diag['setup_ok'] = setup_ok

        entry = float(last['High'] * (1 + s_cfg['entry_buffer_pct']))
        stop = float(last['Low'] - (s_cfg['stop_atr_buffer_mult'] * last['ATR14']))
        risk_per_share = entry - stop
        diag['entry_stop'] = round(entry, 4)
        diag['stop_loss'] = round(stop, 4)
        diag['risk_per_share'] = round(float(risk_per_share), 4)
        diag['risk_per_share_ok'] = bool(risk_per_share > 0)
        qty = 0
        target_2r = None
        max_allowed_open = None
        if risk_per_share > 0:
            risk_amount = account['equity'] * account['risk_per_trade_pct']
            qty = int(risk_amount / risk_per_share)
            target_2r = entry + (s_cfg['partial_exit_r'] * risk_per_share)
            diag['qty'] = int(qty)
            diag['target_2r'] = round(float(target_2r), 4)
            diag['qty_ok'] = bool(qty > 0)

            broker = cfg.get('broker', {})
            max_gap_pct = float(broker.get('max_open_gap_above_entry_pct', 0.01))
            max_gap_atr_mult = float(broker.get('max_open_gap_above_entry_atr_mult', 1.0))
            max_allowed_open_by_pct = entry * (1 + max_gap_pct)
            max_allowed_open_by_atr = entry + (max_gap_atr_mult * float(last['ATR14']))
            max_allowed_open = min(max_allowed_open_by_pct, max_allowed_open_by_atr)
            diag['max_allowed_open_price'] = round(float(max_allowed_open), 4)

        checks = {
            'market_ok': diag['market_ok'],
            'enough_data': diag['enough_data'],
            'indicators_ok': diag['indicators_ok'],
            'price_ok': diag['price_ok'],
            'volume_ok': diag['volume_ok'],
            'close_above_sma200': diag['close_above_sma200'],
            'sma50_above_sma200': diag['sma50_above_sma200'],
            'distance_sma50_ok': diag['distance_sma50_ok'],
            'pullback_ok': diag['pullback_ok'],
            'bullish_turn_ok': diag['bullish_turn_ok'],
            'risk_per_share_ok': diag['risk_per_share_ok'],
            'qty_ok': diag['qty_ok'],
        }
        failed = [name for name, ok in checks.items() if not ok]
        passed = len(checks) - len(failed)
        diag['passed_checks'] = int(passed)
        diag['total_checks'] = int(len(checks))
        diag['score_pct'] = round((passed / len(checks)) * 100, 2)
        diag['failed_checks'] = ','.join(failed)
        signal_ok = bool(market_ok and trend_ok and setup_ok and risk_per_share > 0 and qty > 0)
        diag['signal_ok'] = signal_ok

        if signal_ok:
            diag['classification'] = 'valid_signal'
            diag['reason'] = 'Cumple todos los filtros y genera señal operable.'
        elif market_ok and trend_ok and (pullback_ok or bullish_turn):
            diag['classification'] = 'almost_valid'
            diag['reason'] = 'Tiene tendencia y parte del setup, pero le falta alguna condición final.'
        elif market_ok and trend_ok:
            diag['classification'] = 'trend_only'
            diag['reason'] = 'Cumple tendencia, pero todavía no hay retroceso/vela señal válida.'
        elif not market_ok:
            diag['classification'] = 'blocked_by_market'
            diag['reason'] = 'El filtro del mercado general bloquea nuevas entradas.'
        else:
            diag['classification'] = 'rejected'
            diag['reason'] = 'No cumple los filtros mínimos de tendencia/liquidez/precio.'

        diagnostics.append(diag)

        if not signal_ok:
            continue

        broker = cfg.get('broker', {})
        commission_buy = float(broker.get('commission_buy_eur', account.get('commission_per_side', 0)))
        commission_sell = float(broker.get('commission_sell_eur', account.get('commission_per_side', 0)))
        estimated_fees = commission_buy + commission_sell
        max_gap_pct = float(broker.get('max_open_gap_above_entry_pct', 0.01))

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

    signals_df = pd.DataFrame(signals, columns=_base_empty_signal_columns())
    diagnostics_df = pd.DataFrame(diagnostics, columns=_base_diagnostic_columns())
    return signals_df, diagnostics_df


def detect_signals(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Backward-compatible helper: return only valid signals."""
    signals, _ = scan_universe(df, cfg)
    return signals
