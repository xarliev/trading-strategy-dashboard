# Trading Strategy Dashboard

Sistema educativo de swing trading diario basado en:

- descarga diaria de datos con `yfinance`
- cálculo de EMA20, EMA10, SMA50, SMA200 y ATR(14)
- filtro de tendencia
- detección de retroceso y vela señal
- cálculo de entrada mediante orden Stop compatible con Trade Republic, stop loss, tamaño de posición y objetivo 2R
- diario de operaciones persistente en CSV
- dashboard HTML estático publicable con GitHub Pages
- automatización diaria con GitHub Actions

> No es recomendación financiera. Es una base técnica para investigación, revisión y paper trading.

## Estructura

```text
.github/workflows/daily_scan_and_pages.yml  # workflow automático
config/universe.yml                         # tickers, riesgo, comisiones y reglas
src/trading_bot/                            # código Python
data/processed/trading_journal.csv          # diario persistente generado/actualizado
dashboard/index.html                        # dashboard publicado por GitHub Pages
docs/SETUP_GUIDE.md                         # guía completa desde cero
```

## Arranque local opcional

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Luego abre:

```text
dashboard/index.html
```

## Uso recomendado en GitHub

1. Crea una cuenta en GitHub.
2. Crea un repositorio nuevo.
3. Sube todos estos archivos.
4. Activa Actions.
5. Configura GitHub Pages con source = GitHub Actions.
6. Ejecuta manualmente el workflow una vez.

Guía detallada: [`docs/SETUP_GUIDE.md`](docs/SETUP_GUIDE.md)

## Diario de operaciones

Sí, el proyecto incluye diario persistente y descargable:

```text
data/processed/trading_journal.csv
```

El dashboard también enlaza este CSV para descarga.

## Personalización rápida

Edita `config/universe.yml`:

- `symbols`: universo de tickers.
- `equity`: capital base.
- `risk_per_trade_pct`: riesgo por trade.
- `broker.commission_buy_eur`: comisión fija estimada de compra.
- `broker.commission_sell_eur`: comisión fija estimada de venta.
- `broker.supports_stop_limit`: para Trade Republic queda en `false`.
- `broker.max_open_gap_above_entry_pct`: protección para no entrar si la apertura se aleja demasiado de la entrada planificada.
- `min_avg_volume_20`: filtro de liquidez.

Para acciones españolas usa sufijo Yahoo `.MC`:

```yaml
symbols:
  - SAN.MC
  - BBVA.MC
  - ITX.MC
```


## Configuración Trade Republic

Esta versión queda ajustada a Trade Republic:

- Entrada: `buy_stop`.
- Sin `stop-limit`: `supports_stop_limit: false`.
- Stop loss: `sell_stop`.
- Objetivo 2R: `sell_limit`.
- Comisión compra: 1 EUR.
- Comisión venta: 1 EUR.
- Comisión estimada ida y vuelta: 2 EUR.

Como no se usa stop-limit, el sistema añade una protección: `max_allowed_open_price`. Si la acción abre por encima de ese precio, no deberías cursar la entrada manualmente aunque exista señal. Es el cinturón de seguridad anti-gap; cutre no, pragmático.

## Qué hace y qué no hace

Hace:

- buscar setups diarios
- calcular entrada/stop/tamaño
- guardar señales
- actualizar diario
- publicar dashboard

No hace todavía:

- enviar órdenes al broker
- confirmar earnings calendar
- gestionar fiscalidad
- validar datos con proveedor institucional
- backtesting avanzado

## Diagnóstico de escaneo por ticker

Cada ejecución genera ahora un informe de auditoría de la estrategia:

- `data/processed/scan_diagnostics_latest.csv`: último diagnóstico, una fila por ticker evaluado.
- `data/processed/scan_diagnostics_latest.parquet`: lo mismo en formato Parquet.
- `data/processed/scan_diagnostics_history.csv`: histórico acumulado por fecha y ticker.

Este diagnóstico permite ver por qué un ticker no ha generado señal. Campos útiles:

- `classification`: `valid_signal`, `almost_valid`, `trend_only`, `blocked_by_market`, `rejected`, etc.
- `score_pct`: porcentaje de checks superados.
- `failed_checks`: condiciones que han fallado.
- `trend_ok`, `pullback_ok`, `bullish_turn_ok`, `market_ok`: checks principales.
- `entry_stop`, `stop_loss`, `target_2r`, `qty`: niveles calculados aunque el ticker no llegue a señal válida, cuando sea posible.

Así no dependes de que `signals_latest.csv` tenga filas para saber si el sistema está trabajando. Si no hay señales, el diagnóstico te dice si los tickers están lejos, cerca o bloqueados por mercado.
