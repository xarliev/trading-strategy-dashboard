from __future__ import annotations
from pathlib import Path
import json
import pandas as pd
import plotly.express as px
from jinja2 import Template

HTML_TEMPLATE = '''<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Trading Strategy Dashboard</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; background:#fafafa; color:#222; }
    .grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:12px; }
    .card { background:white; border:1px solid #ddd; border-radius:12px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,.06); }
    table { border-collapse: collapse; width:100%; background:white; }
    th, td { border:1px solid #ddd; padding:8px; text-align:left; font-size:14px; }
    th { background:#f0f0f0; }
    .small { color:#666; font-size:13px; }
    .pill { display:inline-block; padding:2px 8px; border-radius:999px; background:#eee; }
  </style>
</head>
<body>
  <h1>Dashboard de estrategia de trading</h1>
  <p class="small">Actualizado: {{ updated_at }} UTC. Uso educativo/investigación; no es recomendación financiera.</p>
  <div class="grid">
    <div class="card"><b>Tickers evaluados</b><br><span style="font-size:28px">{{ metrics.evaluated_count }}</span></div>
    <div class="card"><b>Señales hoy</b><br><span style="font-size:28px">{{ metrics.signals_count }}</span></div>
    <div class="card"><b>Casi válidas</b><br><span style="font-size:28px">{{ metrics.almost_valid_count }}</span></div>
    <div class="card"><b>Operaciones en diario</b><br><span style="font-size:28px">{{ metrics.journal_count }}</span></div>
    <div class="card"><b>Pendientes</b><br><span style="font-size:28px">{{ metrics.pending_count }}</span></div>
    <div class="card"><b>Net PnL registrado</b><br><span style="font-size:28px">{{ metrics.net_pnl }}</span></div>
  </div>

  <h2>Diagnóstico del escaneo</h2>
  <p class="small">
    Este informe muestra todos los tickers evaluados y qué condiciones han fallado. Útil para ver cuáles están cerca de generar señal.
    <br><a href="../data/processed/scan_diagnostics_latest.csv">Descargar scan_diagnostics_latest.csv</a> ·
    <a href="../data/processed/scan_diagnostics_history.csv">Descargar histórico de diagnósticos</a>
  </p>
  {{ diagnostics_table }}

  <h2>Señales detectadas</h2>
  <p><a href="../data/processed/signals_latest.csv">Descargar señales últimas</a></p>
  {{ signals_table }}

  <h2>Diario de operaciones</h2>
  <p><a href="../data/processed/trading_journal.csv">Descargar trading_journal.csv</a></p>
  {{ journal_table }}

  <h2>Gráfico de PnL acumulado registrado</h2>
  {{ pnl_chart }}
</body>
</html>'''


def _table(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return '<p>No hay datos todavía.</p>'
    return df.to_html(index=False, escape=False)


def _diagnostics_view(diagnostics: pd.DataFrame) -> pd.DataFrame:
    if diagnostics is None or diagnostics.empty:
        return pd.DataFrame()
    cols = [
        'symbol', 'classification', 'score_pct', 'failed_checks', 'reason',
        'close', 'ema20', 'sma50', 'sma200', 'atr14', 'avg_vol20',
        'dist_sma50_pct', 'entry_stop', 'stop_loss', 'target_2r', 'qty',
        'max_allowed_open_price'
    ]
    existing = [c for c in cols if c in diagnostics.columns]
    out = diagnostics[existing].copy()
    # Ordena primero señales válidas/casi válidas, luego mayor puntuación.
    order = {'valid_signal': 0, 'almost_valid': 1, 'trend_only': 2, 'blocked_by_market': 3, 'rejected': 4}
    out['_order'] = out['classification'].map(order).fillna(9) if 'classification' in out else 9
    out = out.sort_values(['_order', 'score_pct'], ascending=[True, False]).drop(columns=['_order'])
    return out


def build_dashboard(signals: pd.DataFrame, journal: pd.DataFrame, out_dir: Path, diagnostics: pd.DataFrame | None = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if journal is None:
        journal = pd.DataFrame()
    if signals is None:
        signals = pd.DataFrame()
    if diagnostics is None:
        diagnostics = pd.DataFrame()

    pnl_chart = '<p>No hay operaciones cerradas con PnL todavía.</p>'
    net_pnl = 0.0
    if not journal.empty and 'net_pnl' in journal.columns:
        closed = journal.copy()
        closed['net_pnl_num'] = pd.to_numeric(closed['net_pnl'], errors='coerce')
        closed = closed.dropna(subset=['net_pnl_num'])
        if not closed.empty:
            closed['cum_net_pnl'] = closed['net_pnl_num'].cumsum()
            net_pnl = closed['net_pnl_num'].sum()
            fig = px.line(closed, x='trade_id', y='cum_net_pnl', title='PnL neto acumulado')
            pnl_chart = fig.to_html(include_plotlyjs='cdn', full_html=False)

    almost_valid_count = 0
    if not diagnostics.empty and 'classification' in diagnostics.columns:
        almost_valid_count = int((diagnostics['classification'] == 'almost_valid').sum())

    metrics = {
        'evaluated_count': int(len(diagnostics)) if diagnostics is not None else 0,
        'signals_count': int(len(signals)),
        'almost_valid_count': almost_valid_count,
        'journal_count': int(len(journal)),
        'pending_count': int((journal.get('status', pd.Series(dtype=str)) == 'pending_entry').sum()) if not journal.empty else 0,
        'net_pnl': round(float(net_pnl), 2),
    }
    html = Template(HTML_TEMPLATE).render(
        updated_at=pd.Timestamp.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        metrics=metrics,
        diagnostics_table=_table(_diagnostics_view(diagnostics)),
        signals_table=_table(signals),
        journal_table=_table(journal.tail(100) if not journal.empty else journal),
        pnl_chart=pnl_chart,
    )
    (out_dir / 'index.html').write_text(html, encoding='utf-8')
    (out_dir / 'metrics.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
