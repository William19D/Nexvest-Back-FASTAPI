import requests
import uuid
import time
import base64
import json
import os
from datetime import date, timedelta

# ============================================================
# CONFIGURACIÓN
# ============================================================

# Activos de la BVC (Bolsa de Valores de Colombia)
BVC_ASSETS = [
    {"mnemonic": "ECOPETROL", "board": "EQTY"},
    {"mnemonic": "ISA",       "board": "EQTY"},
    {"mnemonic": "GEB",       "board": "EQTY"},
    {"mnemonic": "PFBCOLOM",  "board": "EQTY"},  # Bancolombia preferencial
    {"mnemonic": "NUTRESA",   "board": "EQTY"},
    {"mnemonic": "GRUPOSURA", "board": "EQTY"},
    {"mnemonic": "CELSIA",    "board": "EQTY"},
    {"mnemonic": "ÉXITO",     "board": "EQTY"},  # Grupo Éxito
    {"mnemonic": "CEMARGOS",  "board": "EQTY"},  # Cementos Argos
    {"mnemonic": "CNEC",      "board": "EQTY"},  # Canacol Energy
    {"mnemonic": "CORFICOLCF","board": "EQTY"},  # Corficolombiana
    {"mnemonic": "PROMIGAS",  "board": "EQTY"},
    {"mnemonic": "MINEROS",   "board": "EQTY"},
    {"mnemonic": "CLH",       "board": "EQTY"},  # Constructora LH (Conconcreto)
    {"mnemonic": "PFDAVVNDA", "board": "EQTY"},  # Davivienda preferencial
]

# ETFs / activos globales — se obtienen via Yahoo Finance (scraping CSV)
YAHOO_ASSETS = [
    "VOO",    # Vanguard S&P 500 ETF
    "CSPX",   # iShares Core S&P 500 UCITS ETF
    "SPY",    # SPDR S&P 500 ETF
    "QQQ",    # Invesco QQQ (Nasdaq 100)
    "IVV",    # iShares Core S&P 500
    "GLD",    # SPDR Gold Shares
]

YEARS_BACK = 5
INTERVAL_DAYS = 1        # diario (todos los días hábiles)
MAX_RETRY_DAYS = 7
OUTPUT_DIR = "historicos"

# ============================================================
# UTILIDADES COMUNES
# ============================================================

def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_date_range(years_back):
    end = date.today()
    start = end - timedelta(days=years_back * 365)
    return start, end

def get_all_weekdays(start, end):
    """Devuelve todos los días de lunes a viernes en el rango [start, end]."""
    days = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return days

# ============================================================
# DESCARGA BVC
# ============================================================

def get_bvc_token(session):
    ts = int(time.time() * 1000)
    r = str(uuid.uuid4())
    response = session.get(
        "https://www.bvc.com.co/api/handshake",
        params={"ts": ts, "r": r},
        timeout=15
    )
    response.raise_for_status()
    return response.json()["token"]

def build_k_header(trade_date):
    query = (
        f"filters[marketDataRv][tradeDate]={trade_date}"
        f"&filters[marketDataRv][board]=EQTY"
        f"&filters[marketDataRv][board]=REPO"
        f"&filters[marketDataRv][board]=TTV"
        f"&sorter[]=tradeValue&sorter[]=DESC"
    )
    return base64.b64encode(query.encode()).decode()

def fetch_bvc_date(session, trade_date, mnemonic, board):
    """Consulta una fecha en la BVC. Retorna (asset, fecha_usada) o (None, None)."""
    token = get_bvc_token(session)
    r = session.get(
        "https://rest.bvc.com.co/market-information/rv/lvl-2",
        params={
            "filters[marketDataRv][tradeDate]": trade_date,
            "filters[marketDataRv][board]": ["EQTY", "REPO", "TTV"],
            "sorter[]": ["tradeValue", "DESC"]
        },
        headers={"token": token, "k": build_k_header(trade_date)},
        timeout=15
    )
    r.raise_for_status()
    data = r.json()
    tab = data.get("data", {}).get("tab", [])
    if not tab:
        return None, None
    asset = next((x for x in tab if x["mnemonic"] == mnemonic and x["board"] == board), None)
    return asset, trade_date

def fetch_bvc_with_retry(session, trade_date_str, mnemonic, board):
    base = date.fromisoformat(trade_date_str)
    for delta in range(MAX_RETRY_DAYS):
        candidate = base + timedelta(days=delta)
        while candidate.weekday() >= 5:
            candidate += timedelta(days=1)
        candidate_str = candidate.strftime("%Y-%m-%d")
        try:
            asset, used_date = fetch_bvc_date(session, candidate_str, mnemonic, board)
            if asset and asset.get("lastPrice") is not None:
                return asset, used_date
            time.sleep(0.3)
        except Exception as e:
            print(f"    [ERROR en {candidate_str}] {e}")
            time.sleep(1)
    return None, None

def download_bvc_asset(mnemonic, board, start, end):
    """Descarga el histórico de un activo de la BVC y lo guarda en JSON."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Origin": "https://www.bvc.com.co",
        "Referer": "https://www.bvc.com.co/"
    })

    all_days = get_all_weekdays(start, end)
    total = len(all_days)
    results = []
    print(f"\n{'='*60}")
    print(f"[BVC] {mnemonic} — {total} días hábiles potenciales")
    print(f"{'='*60}")

    # Para eficiencia, en lugar de pedir cada día individual (>1200 días),
    # hacemos muestreo semanal y rellenamos con los datos disponibles.
    # La API de BVC retorna TODOS los activos del día en una sola llamada,
    # así que muestreamos cada semana (cada 5 días hábiles aprox).
    weekly_days = all_days[::5]  # cada 5 días hábiles ≈ semanal

    for i, trade_date in enumerate(weekly_days):
        print(f"  [{i+1}/{len(weekly_days)}] {trade_date}...", end=" ", flush=True)
        try:
            asset, used_date = fetch_bvc_with_retry(session, trade_date, mnemonic, board)
            if asset:
                record = {
                    "date":      used_date,
                    "targetDate": trade_date,
                    "open":      asset.get("openPrice"),
                    "high":      asset.get("highPrice"),
                    "low":       asset.get("lowPrice"),
                    "close":     asset.get("lastPrice"),
                    "volume":    asset.get("volume"),
                    "tradeValue": asset.get("tradeValue"),
                    "mnemonic":  mnemonic,
                    "board":     board,
                    "raw":       asset
                }
                results.append(record)
                print(f"OK  close={asset.get('lastPrice')}  vol={asset.get('volume')}")
            else:
                print(f"SIN DATOS")
            time.sleep(0.5)
        except Exception as e:
            print(f"ERROR: {e}")
            time.sleep(2)

    output_file = os.path.join(OUTPUT_DIR, f"{mnemonic}_historico.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"  -> Guardado: {output_file}  ({len(results)} registros)")
    return results

# ============================================================
# DESCARGA YAHOO FINANCE (CSV directo)
# ============================================================

def yahoo_period_to_unix(d: date) -> int:
    return int(time.mktime(d.timetuple()))

def download_yahoo_asset(ticker, start, end):
    """
    Descarga datos históricos de Yahoo Finance usando su endpoint de descarga CSV
    (petición HTTP directa, sin librerías de alto nivel como yfinance).
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://finance.yahoo.com",
    })

    print(f"\n{'='*60}")
    print(f"[Yahoo] {ticker}")
    print(f"{'='*60}")

    period1 = yahoo_period_to_unix(start)
    period2 = yahoo_period_to_unix(end)

    # Paso 1: obtener cookie y crumb
    crumb = None
    try:
        # Visitar la página del ticker para obtener cookies
        page_url = f"https://finance.yahoo.com/quote/{ticker}"
        resp = session.get(page_url, timeout=15)
        resp.raise_for_status()

        # Obtener crumb
        crumb_url = "https://query1.finance.yahoo.com/v1/test/getcrumb"
        crumb_resp = session.get(crumb_url, timeout=10)
        if crumb_resp.status_code == 200:
            crumb = crumb_resp.text.strip()
            print(f"  Crumb obtenido: {crumb[:10]}...")
        else:
            print(f"  [WARN] No se pudo obtener crumb, intentando sin él...")
    except Exception as e:
        print(f"  [WARN] Error obteniendo crumb: {e}")

    # Paso 2: descargar CSV histórico
    csv_url = (
        f"https://query1.finance.yahoo.com/v7/finance/download/{ticker}"
        f"?period1={period1}&period2={period2}&interval=1d&events=history"
    )
    if crumb:
        csv_url += f"&crumb={crumb}"

    results = []
    try:
        print(f"  Descargando CSV desde Yahoo Finance...")
        csv_resp = session.get(csv_url, timeout=30)
        csv_resp.raise_for_status()

        lines = csv_resp.text.strip().split("\n")
        if len(lines) < 2:
            print(f"  [FAIL] Respuesta vacía o inválida")
            _save_empty(ticker)
            return []

        header = [h.strip().lower() for h in lines[0].split(",")]
        print(f"  Columnas: {header}")

        for line in lines[1:]:
            parts = line.strip().split(",")
            if len(parts) < len(header):
                continue
            row = dict(zip(header, parts))

            # Saltar filas con datos nulos
            if "null" in row.get("close", "").lower() or row.get("close", "") == "":
                continue

            try:
                record = {
                    "date":   row.get("date", ""),
                    "open":   float(row.get("open", 0) or 0),
                    "high":   float(row.get("high", 0) or 0),
                    "low":    float(row.get("low", 0) or 0),
                    "close":  float(row.get("close", 0) or 0),
                    "adjClose": float(row.get("adj close", row.get("adjclose", 0)) or 0),
                    "volume": int(float(row.get("volume", 0) or 0)),
                    "ticker": ticker,
                }
                results.append(record)
            except (ValueError, TypeError) as e:
                print(f"  [SKIP] Fila inválida ({row.get('date','')}): {e}")
                continue

        print(f"  -> {len(results)} registros descargados")

    except requests.HTTPError as e:
        print(f"  [HTTP ERROR] {e}")
        print(f"  Respuesta: {csv_resp.text[:300]}")
    except Exception as e:
        print(f"  [ERROR] {e}")

    output_file = os.path.join(OUTPUT_DIR, f"{ticker}_historico.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  -> Guardado: {output_file}")

    return results

def _save_empty(ticker):
    output_file = os.path.join(OUTPUT_DIR, f"{ticker}_historico.json")
    with open(output_file, "w") as f:
        json.dump([], f)

# ============================================================
# MAIN
# ============================================================

def main():
    ensure_output_dir()
    start, end = get_date_range(YEARS_BACK)
    print(f"\nDescargando históricos de {start} a {end}")
    print(f"Directorio de salida: {OUTPUT_DIR}/")

    summary = {}

    # --- Activos de la BVC ---
    print(f"\n{'#'*60}")
    print(f"# ACTIVOS BVC ({len(BVC_ASSETS)} activos)")
    print(f"{'#'*60}")
    for asset_cfg in BVC_ASSETS:
        mnemonic = asset_cfg["mnemonic"]
        board = asset_cfg["board"]
        try:
            records = download_bvc_asset(mnemonic, board, start, end)
            summary[mnemonic] = {"source": "BVC", "records": len(records), "status": "OK"}
        except Exception as e:
            print(f"[FATAL] Error en {mnemonic}: {e}")
            summary[mnemonic] = {"source": "BVC", "records": 0, "status": f"ERROR: {e}"}
        time.sleep(1)

    # --- ETFs / activos globales (Yahoo Finance) ---
    print(f"\n{'#'*60}")
    print(f"# ETFs GLOBALES ({len(YAHOO_ASSETS)} activos)")
    print(f"{'#'*60}")
    for ticker in YAHOO_ASSETS:
        try:
            records = download_yahoo_asset(ticker, start, end)
            summary[ticker] = {"source": "Yahoo", "records": len(records), "status": "OK"}
        except Exception as e:
            print(f"[FATAL] Error en {ticker}: {e}")
            summary[ticker] = {"source": "Yahoo", "records": 0, "status": f"ERROR: {e}"}
        time.sleep(1)

    # --- Resumen final ---
    print(f"\n{'='*60}")
    print("RESUMEN DE DESCARGA")
    print(f"{'='*60}")
    total_assets = len(summary)
    total_records = sum(v["records"] for v in summary.values())
    ok_count = sum(1 for v in summary.values() if v["status"] == "OK")

    for name, info in summary.items():
        status_icon = "✓" if info["status"] == "OK" else "✗"
        print(f"  {status_icon} {name:<20} [{info['source']:<6}]  {info['records']:>4} registros  {info['status']}")

    print(f"\nTotal: {ok_count}/{total_assets} activos exitosos | {total_records} registros totales")
    print(f"Archivos guardados en: {OUTPUT_DIR}/")

    # Guardar resumen
    summary_file = os.path.join(OUTPUT_DIR, "resumen_descarga.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump({
            "fecha_descarga": date.today().isoformat(),
            "rango": {"inicio": start.isoformat(), "fin": end.isoformat()},
            "activos": summary
        }, f, ensure_ascii=False, indent=2)
    print(f"Resumen guardado en: {summary_file}")

if __name__ == "__main__":
    main()