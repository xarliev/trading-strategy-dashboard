# Guía paso a paso: poner en marcha el sistema en GitHub desde cero

Esta guía asume que nunca has usado GitHub. Vamos al grano, pero sin saltarnos botones importantes.

## 1. Crear una cuenta en GitHub

1. Entra en github.com.
2. Pulsa **Sign up**.
3. Introduce email, contraseña y nombre de usuario.
4. Verifica tu email.
5. Elige el plan gratuito.

No necesitas instalar nada para la primera versión. Usaremos la web de GitHub.

---

## 2. Crear el repositorio

1. Una vez dentro de GitHub, arriba a la derecha pulsa el botón **+**.
2. Pulsa **New repository**.
3. Nombre recomendado: `trading-strategy-dashboard`.
4. Visibilidad:
   - **Public**: recomendado para coste cero más simple.
   - **Private**: también suele bastar en uso pequeño, pero tiene límites de minutos/almacenamiento.
5. No marques todavía README, `.gitignore` ni license, porque este ZIP ya los incluye.
6. Pulsa **Create repository**.

GitHub te mostrará una página vacía con instrucciones. No te asustes: parece cabina de avión, pero de momento solo necesitamos subir archivos.

---

## 3. Subir los archivos del ZIP sin usar consola

1. Descomprime el ZIP que te he dado en tu ordenador.
2. En tu repo vacío de GitHub, pulsa **uploading an existing file** o **Add file > Upload files**.
3. Arrastra TODO el contenido de la carpeta descomprimida. Importante: arrastra los archivos y carpetas internos, no la carpeta contenedora entera.
4. Espera a que suba.
5. Abajo, en **Commit changes**, escribe por ejemplo: `Initial trading bot upload`.
6. Pulsa **Commit changes**.

Cuando termine, deberías ver carpetas como `.github`, `src`, `config`, `dashboard`, `data`, `docs`.

---

## 4. Activar GitHub Actions

1. En el repo, entra en la pestaña **Actions**.
2. Si GitHub muestra un aviso de seguridad, pulsa **I understand my workflows, go ahead and enable them**.
3. Verás el workflow llamado **Daily trading scan and dashboard**.
4. Entra en él.
5. Pulsa **Run workflow**.
6. Pulsa el botón verde **Run workflow**.

Esto ejecuta el sistema manualmente por primera vez. Tardará unos minutos.

---

## 5. Dar permisos al workflow para guardar resultados

Normalmente el workflow ya declara los permisos necesarios, pero revisa esto si falla al hacer `git push`:

1. Entra en **Settings** del repo.
2. Menú izquierdo: **Actions > General**.
3. Busca **Workflow permissions**.
4. Marca **Read and write permissions**.
5. Guarda.

Después vuelve a **Actions** y ejecuta otra vez **Run workflow**.

---

## 6. Activar GitHub Pages

1. Entra en **Settings** del repo.
2. Menú izquierdo: **Pages**.
3. En **Build and deployment**, selecciona:
   - **Source**: `GitHub Actions`.
4. Guarda si aparece botón de guardar.
5. Vuelve a **Actions** y ejecuta el workflow manualmente si todavía no se ha ejecutado bien.

Cuando termine, dentro del run verás una URL tipo:

`https://tu_usuario.github.io/trading-strategy-dashboard/`

Esa será la URL del dashboard.

---

## 7. Qué ocurre cada día

El workflow se ejecuta de lunes a viernes con esta línea:

```yaml
- cron: "45 21 * * 1-5"
```

Eso está en UTC. En España suele equivaler aproximadamente a:

- 22:45 en horario de invierno
- 23:45 en horario de verano

La idea es ejecutarlo después del cierre del mercado USA. Puedes cambiar la hora editando `.github/workflows/daily_scan_and_pages.yml`.

---

## 8. Cambiar tickers, capital o riesgo

Abre el archivo:

`config/universe.yml`

Ahí puedes modificar:

- `symbols`: lista de acciones/ETFs.
- `equity`: capital de referencia.
- `risk_per_trade_pct`: riesgo por operación.
- `broker.commission_buy_eur`: comisión de compra en Trade Republic, por defecto 1 EUR.
- `broker.commission_sell_eur`: comisión de venta en Trade Republic, por defecto 1 EUR.
- `broker.supports_stop_limit`: queda en `false`, porque el sistema no asume órdenes stop-limit.
- `broker.max_open_gap_above_entry_pct`: filtro para no entrar si la apertura se va demasiado por encima de la entrada.
- filtros de volumen/precio.

Para acciones españolas, usa tickers de Yahoo Finance con `.MC`, por ejemplo:

- `SAN.MC`
- `BBVA.MC`
- `ITX.MC`
- `IBE.MC`

---

## 9. Descargar el diario de operaciones

Sí: el sistema genera un diario descargable y persistente.

Archivo principal:

`data/processed/trading_journal.csv`

Puedes descargarlo así:

1. Entra en tu repo.
2. Abre `data/processed/trading_journal.csv`.
3. Pulsa **Download raw file**.

También aparece enlazado desde el dashboard publicado en GitHub Pages.

Además se guarda:

- `data/processed/signals_latest.csv`: señales detectadas en la última ejecución.
- `data/processed/prices_indicators_latest.parquet`: precios con indicadores.

---

## 10. Cómo usar las señales con Trade Republic

El CSV y el dashboard mostrarán para cada señal:

- `entry_order_type`: normalmente `buy_stop`.
- `entry_stop`: precio al que colocarías la orden Stop de compra.
- `entry_limit`: vacío, porque no se usa Stop-Limit.
- `max_allowed_open_price`: si al revisar la operación el mercado abre por encima de ese precio, mejor cancelar/no cursar la entrada.
- `stop_loss`: precio de stop loss tras entrar.
- `target_2r`: objetivo para venta limitada parcial o total, según cómo quieras gestionar la salida.
- `fees`: comisión estimada de ida y vuelta, por defecto 2 EUR.

Flujo manual recomendado:

1. Revisas el dashboard después de la ejecución diaria.
2. Si hay señal, creas en Trade Republic una orden Stop de compra en `entry_stop`.
3. Si la apertura está por encima de `max_allowed_open_price`, no la curses. Sin stop-limit, perseguir gaps es deporte de riesgo y no de los olímpicos.
4. Si entra la compra, registras el precio real en `entry_price`.
5. Colocas stop loss en `stop_loss`.
6. Colocas o vigilas objetivo en `target_2r`.

---

## 11. Cómo registrar cierres de operaciones manualmente

Esta primera versión detecta señales y crea entradas pendientes en el diario. Para cerrar una operación manualmente:

1. Abre `data/processed/trading_journal.csv`.
2. Pulsa el icono del lápiz para editar.
3. Cambia:
   - `status`: por ejemplo `closed`.
   - `entry_price`: precio real de entrada.
   - `exit_price`: precio real de salida.
   - `exit_date`: fecha de salida.
   - `gross_pnl`, `fees`, `net_pnl`, `r_multiple`.
4. Pulsa **Commit changes**.
5. Ejecuta el workflow o espera al siguiente día para regenerar el dashboard.

En una versión posterior se puede crear un formulario más cómodo para esto, pero CSV es simple, auditable y no se rompe por mirar mal una pestaña.

---

## 12. Limitaciones importantes

- No ejecuta órdenes reales en broker.
- No sustituye una revisión humana.
- yfinance no es una fuente institucional garantizada.
- El dashboard es estático; se regenera con cada ejecución.
- El diario queda en CSV dentro del repo, así que si el repo es público, cualquiera podrá verlo.

Si quieres privacidad, usa repo privado.
