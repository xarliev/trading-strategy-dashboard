from __future__ import annotations
from pathlib import Path
import pandas as pd

COLUMNS = [
    'trade_id','created_at','symbol','broker','setup','status','entry_order_type',
    'entry_stop','entry_limit','max_allowed_open_price','entry_price','stop_loss','qty',
    'risk_amount','target_2r','exit_price','exit_date','gross_pnl',
    'commission_buy_eur','commission_sell_eur','fees','net_pnl','r_multiple','notes'
]


def load_journal(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame(columns=COLUMNS)


def append_pending_signals(journal_path: Path, signals: pd.DataFrame) -> pd.DataFrame:
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    journal = load_journal(journal_path)
    if signals.empty:
        journal.to_csv(journal_path, index=False)
        return journal
    existing_keys = set((journal['created_at'].astype(str) + '_' + journal['symbol'].astype(str)).tolist()) if not journal.empty else set()
    rows = []
    for _, s in signals.iterrows():
        key = f"{s['date']}_{s['symbol']}"
        if key in existing_keys:
            continue
        rows.append({
            'trade_id': key,
            'created_at': s['date'],
            'symbol': s['symbol'],
            'broker': s.get('broker', ''),
            'setup': s['setup'],
            'status': 'pending_entry',
            'entry_order_type': s.get('entry_order_type', 'buy_stop'),
            'entry_stop': s['entry_stop'],
            'entry_limit': s.get('entry_limit', ''),
            'max_allowed_open_price': s.get('max_allowed_open_price', ''),
            'entry_price': '',
            'stop_loss': s['stop_loss'],
            'qty': s['qty'],
            'risk_amount': s['risk_amount'],
            'target_2r': s['target_2r'],
            'exit_price': '',
            'exit_date': '',
            'gross_pnl': '',
            'commission_buy_eur': s.get('commission_buy_eur', ''),
            'commission_sell_eur': s.get('commission_sell_eur', ''),
            'fees': s.get('estimated_roundtrip_fees', ''),
            'net_pnl': '',
            'r_multiple': '',
            'notes': s['notes'],
        })
    if rows:
        journal = pd.concat([journal, pd.DataFrame(rows)], ignore_index=True)
    journal.to_csv(journal_path, index=False)
    return journal
