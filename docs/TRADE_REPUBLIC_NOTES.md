# Notas de ejecución con Trade Republic

Esta versión del repo asume operativa manual con Trade Republic.

## Tipos de órdenes usados

- Entrada: orden Stop de compra (`buy_stop`).
- Stop loss: orden Stop de venta (`sell_stop`).
- Objetivo: orden Limit de venta (`sell_limit`).
- Stop-Limit: no se usa; `supports_stop_limit: false`.

## Comisiones

Configuración por defecto en `config/universe.yml`:

```yaml
broker:
  name: Trade Republic
  commission_buy_eur: 1.00
  commission_sell_eur: 1.00
```

El sistema calcula una estimación de ida y vuelta:

```text
fees = commission_buy_eur + commission_sell_eur
```

Por defecto: 2 EUR por operación completa.

## Protección por gap

Como no usamos Stop-Limit, el sistema genera el campo:

```text
max_allowed_open_price
```

Regla práctica:

- Si la apertura o el precio disponible está por encima de `max_allowed_open_price`, no cursar la entrada.
- Si no activa en 2 sesiones, cancelar.

Este filtro intenta evitar comprar una ruptura demasiado alejada de la entrada calculada.

## Campos nuevos del diario

`data/processed/trading_journal.csv` incluye:

- `broker`
- `entry_order_type`
- `entry_stop`
- `entry_limit`
- `max_allowed_open_price`
- `commission_buy_eur`
- `commission_sell_eur`
- `fees`

