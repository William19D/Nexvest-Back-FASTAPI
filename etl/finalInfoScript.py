"""
descarga_bvc_turbo.py
=====================
Descarga histórica BVC al máximo de velocidad.

Optimizaciones clave:
  1. 1 request por fecha = TODOS los activos (no 1 request por activo/fecha)
  2. ThreadPoolExecutor con N hilos — cada hilo procesa UNA fecha
  3. Session reutilizable por hilo (via threading.local)
  4. Sin sleep innecesario — solo retry real en errores
  5. Barra de progreso en tiempo real con ETA
  6. TODOS los activos del script original incluidos
"""

import requests
import uuid
import time
import base64
import json
import os
import threading
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================
# CONFIGURACIÓN — todos los activos originales
# ============================================================

BVC_ASSETS = [
    {"mnemonic": "ECOPETROL",  "board": "EQTY"},
    {"mnemonic": "ISA",        "board": "EQTY"},
    {"mnemonic": "GEB",        "board": "EQTY"},
    {"mnemonic": "PFBCOLOM",   "board": "EQTY"},
    {"mnemonic": "NUTRESA",    "board": "EQTY"},
    {"mnemonic": "GRUPOSURA",  "board": "EQTY"},
    {"mnemonic": "CELSIA",     "board": "EQTY"},
    {"mnemonic": "EXITO",       "board": "EQTY"},  # Sin tilde — así lo registra la BVC en su API
    {"mnemonic": "CEMARGOS",   "board": "EQTY"},
    {"mnemonic": "CNEC",       "board": "EQTY"},
    {"mnemonic": "CORFICOLCF", "board": "EQTY"},
    {"mnemonic": "PROMIGAS",   "board": "EQTY"},
    {"mnemonic": "MINEROS",    "board": "EQTY"},
    {"mnemonic": "CLH",        "board": "EQTY"},
    {"mnemonic": "PFDAVVNDA",  "board": "EQTY"},
]

YAHOO_ASSETS = ["VOO", "CSPX.L", "SPY", "QQQ", "IVV", "GLD"]

YEARS_BACK     = 5
MAX_RETRY_DAYS = 7
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "historicos")

# Ajusta según tu conexión. 20-30 es el sweet spot para la BVC.
BVC_WORKERS   = 25
YAHOO_WORKERS = 3   # más bajo para no saturar Yahoo con sesiones simultáneas

# ============================================================
# ESTADO COMPARTIDO — thread-safe
# ============================================================

print_lock = threading.Lock()
_tls = threading.local()   # sesión requests por hilo

progress = {
    "bvc_done": 0, "bvc_total": 0,
    "bvc_ok": 0,   "bvc_skip": 0, "bvc_errors": 0,
    "start_time": 0.0,
}

def get_session() -> requests.Session:
    """Una sesión requests reutilizable por hilo."""
    if not hasattr(_tls, "session"):
        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept":     "application/json",
            "Origin":     "https://www.bvc.com.co",
            "Referer":    "https://www.bvc.com.co/",
        })
        _tls.session = s
    return _tls.session

def print_bar(current_date: str = ""):
    """Imprime barra de progreso en la misma línea."""
    d = progress
    total   = d["bvc_total"] or 1
    done    = d["bvc_done"]
    pct_f   = done / total
    filled  = int(pct_f * 38)
    bar     = "█" * filled + "░" * (38 - filled)
    pct_num = int(pct_f * 100)

    eta_str = ""
    if done > 0 and d["start_time"]:
        elapsed = time.time() - d["start_time"]
        rate    = done / elapsed
        remain  = (total - done) / rate if rate > 0 else 0
        eta_str = f"ETA {int(remain // 60)}m{int(remain % 60):02d}s"

    print(
        f"\r  [{bar}] {pct_num:3d}% "
        f"| {done}/{total} fechas "
        f"| ✓{d['bvc_ok']} ✗{d['bvc_errors']} -{d['bvc_skip']} "
        f"| {eta_str} {current_date:<12}",
        end="", flush=True
    )

# ============================================================
# BVC — núcleo de descarga
# ============================================================

def bvc_token(session: requests.Session) -> str:
    ts = int(time.time() * 1000)
    r  = str(uuid.uuid4())
    resp = session.get(
        "https://www.bvc.com.co/api/handshake",
        params={"ts": ts, "r": r},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["token"]

def k_header(trade_date: str) -> str:
    q = (
        f"filters[marketDataRv][tradeDate]={trade_date}"
        "&filters[marketDataRv][board]=EQTY"
        "&filters[marketDataRv][board]=REPO"
        "&filters[marketDataRv][board]=TTV"
        "&sorter[]=tradeValue&sorter[]=DESC"
    )
    return base64.b64encode(q.encode()).decode()

def fetch_day(session: requests.Session, trade_date: str) -> list:
    """1 request → todos los activos del día."""
    token = bvc_token(session)
    r = session.get(
        "https://rest.bvc.com.co/market-information/rv/lvl-2",
        params={
            "filters[marketDataRv][tradeDate]": trade_date,
            "filters[marketDataRv][board]":     ["EQTY", "REPO", "TTV"],
            "sorter[]":                         ["tradeValue", "DESC"],
        },
        headers={"token": token, "k": k_header(trade_date)},
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("data", {}).get("tab", [])

def worker_day(trade_date_str: str, asset_set: set) -> dict:
    """
    Worker por fecha. Busca datos en trade_date_str y hasta
    MAX_RETRY_DAYS días siguientes si ese día no tiene datos.
    Devuelve { mnemonic: record_dict }.
    """
    session = get_session()
    base    = date.fromisoformat(trade_date_str)

    tab, used_date = [], None
    for delta in range(MAX_RETRY_DAYS):
        candidate = base + timedelta(days=delta)
        while candidate.weekday() >= 5:          # saltar fin de semana
            candidate += timedelta(days=1)
        cstr = candidate.strftime("%Y-%m-%d")
        try:
            tab = fetch_day(session, cstr)
            if tab:
                used_date = cstr
                break
        except Exception:
            time.sleep(0.3)

    result = {}

    if not tab:
        with print_lock:
            progress["bvc_skip"]  += 1
            progress["bvc_done"]  += 1
        print_bar(trade_date_str)
        return result

    # Índice O(1)
    idx = {(x["mnemonic"], x["board"]): x for x in tab}

    for a in BVC_ASSETS:
        mn  = a["mnemonic"]
        brd = a["board"]
        row = idx.get((mn, brd))
        if row and row.get("lastPrice") is not None:
            result[mn] = {
                "date":                used_date,
                "targetDate":          trade_date_str,
                "open":                row.get("openPrice"),
                "high":                row.get("maximumPrice"),
                "low":                 row.get("minimumPrice"),
                "close":               row.get("lastPrice"),
                "volume":              row.get("volume"),
                "averagePrice":        row.get("averagePrice"),
                "absoluteVariation":   row.get("absoluteVariation"),
                "percentageVariation": row.get("percentageVariation"),
                "mnemonic":            mn,
                "board":               brd,
            }

    with print_lock:
        progress["bvc_ok"]   += len(result)
        progress["bvc_done"] += 1
    print_bar(trade_date_str)
    return result

# ============================================================
# YAHOO FINANCE — endpoint v8 con cookie/crumb (fix 401)
# ============================================================

# Crumb compartido entre todos los hilos de Yahoo (se obtiene una sola vez)
_yahoo_crumb: str | None = None
_yahoo_crumb_lock = threading.Lock()
_yahoo_session: requests.Session | None = None

YAHOO_HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection":      "keep-alive",
    "Referer":         "https://finance.yahoo.com/",
}

def yahoo_init_session() -> tuple:
    """
    Crea una sesión con cookies válidas y obtiene el crumb.
    Yahoo requiere:
      1. Aceptar consent (para IPs fuera de EE.UU.)
      2. Visitar la página de un ticker para fijar cookies
      3. Pedir el crumb con esas cookies activas
    """
    s = requests.Session()
    s.headers.update(YAHOO_HEADERS)

    # Paso 1 — aceptar consent si aparece (Europa/LATAM)
    try:
        consent = s.post(
            "https://consent.yahoo.com/v2/collectConsent",
            data={"agree": ["agree", "agree"], "consentUUID": "default", "sessionId": "default"},
            timeout=10,
        )
    except Exception:
        pass  # no crítico

    # Paso 2 — visitar página del ticker para fijar cookies __cf_bm, etc.
    try:
        s.get("https://finance.yahoo.com/quote/SPY/history/", timeout=15)
        time.sleep(1)  # dar tiempo a que las cookies se asienten
    except Exception:
        pass

    # Paso 3 — obtener crumb (intentar ambos subdominios)
    crumb = None
    for endpoint in [
        "https://query1.finance.yahoo.com/v1/test/getcrumb",
        "https://query2.finance.yahoo.com/v1/test/getcrumb",
    ]:
        for _ in range(3):
            try:
                r = s.get(endpoint, timeout=10)
                if r.status_code == 200 and r.text.strip() and r.text.strip() != "":
                    crumb = r.text.strip()
                    break
                time.sleep(1)
            except Exception:
                time.sleep(1)
        if crumb:
            break

    return s, crumb

def get_yahoo_session_and_crumb():
    """Inicializa la sesión Yahoo una sola vez (thread-safe)."""
    global _yahoo_crumb, _yahoo_session
    with _yahoo_crumb_lock:
        if _yahoo_session is None:
            _yahoo_session, _yahoo_crumb = yahoo_init_session()
            if _yahoo_crumb:
                print(f"  [Yahoo] Sesión lista — crumb: {_yahoo_crumb[:10]}...")
            else:
                print("  [Yahoo] ⚠ Sin crumb — se intentará sin él")
    return _yahoo_session, _yahoo_crumb

def download_yahoo_ticker(ticker: str, start: date, end: date) -> list:
    import calendar as _cal
    p1 = int(_cal.timegm(start.timetuple()))
    p2 = int(_cal.timegm(end.timetuple()))

    # Cada ticker usa su propia sesión independiente para evitar
    # que la sesión compartida se rate-limite con 6 hilos simultáneos
    session, crumb = yahoo_init_session()
    if crumb:
        with print_lock:
            print(f"  [Yahoo] {ticker} — sesión lista (crumb: {crumb[:8]}...)")
    else:
        with print_lock:
            print(f"  [Yahoo] {ticker} — ⚠ sin crumb, intentando igual")

    records = _yahoo_v8_json(session, ticker, p1, p2, crumb)
    if not records:
        records = _yahoo_v7_csv(session, ticker, p1, p2, crumb)

    return records

def _yahoo_v8_json(session, ticker, p1, p2, crumb) -> list:
    """Endpoint moderno — devuelve OHLCV como JSON."""
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?period1={p1}&period2={p2}&interval=1d&events=history&includeAdjustedClose=true"
    )
    if crumb:
        url += f"&crumb={crumb}"
    try:
        r = session.get(url, timeout=30)

        if r.status_code in (401, 403):
            # Reinicializar sesión y reintentar UNA vez
            with print_lock:
                print(f"\n  [Yahoo] {r.status_code} en {ticker}, renovando sesión...")
            global _yahoo_session, _yahoo_crumb
            with _yahoo_crumb_lock:
                _yahoo_session, _yahoo_crumb = yahoo_init_session()
            session, crumb = _yahoo_session, _yahoo_crumb
            url = (
                f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
                f"?period1={p1}&period2={p2}&interval=1d&events=history&includeAdjustedClose=true"
            )
            if crumb:
                url += f"&crumb={crumb}"
            r = session.get(url, timeout=30)

        r.raise_for_status()
        data      = r.json()
        result    = data["chart"]["result"][0]
        timestamps = result.get("timestamp", [])
        ohlcv     = result["indicators"]["quote"][0]
        adj_close = result["indicators"].get("adjclose", [{}])[0].get("adjclose", [])

        records = []
        for i, ts in enumerate(timestamps):
            close_val = ohlcv["close"][i]
            if close_val is None:
                continue
            records.append({
                "date":     date.fromtimestamp(ts).isoformat(),
                "open":     round(ohlcv["open"][i]   or 0, 6),
                "high":     round(ohlcv["high"][i]   or 0, 6),
                "low":      round(ohlcv["low"][i]    or 0, 6),
                "close":    round(close_val,            6),
                "adjClose": round(adj_close[i] if adj_close and i < len(adj_close) and adj_close[i] else close_val, 6),
                "volume":   int(ohlcv["volume"][i]   or 0),
                "ticker":   ticker,
            })
        return records
    except Exception as e:
        with print_lock:
            print(f"\n  [Yahoo v8 ✗] {ticker}: {e}")
        return []

def _yahoo_v7_csv(session, ticker, p1, p2, crumb) -> list:
    """Fallback CSV clásico."""
    url = (
        f"https://query1.finance.yahoo.com/v7/finance/download/{ticker}"
        f"?period1={p1}&period2={p2}&interval=1d&events=history"
    )
    if crumb:
        url += f"&crumb={crumb}"
    try:
        r = session.get(url, timeout=30)
        r.raise_for_status()
        lines = r.text.strip().split("\n")
        if len(lines) < 2:
            return []
        header = [h.strip().lower() for h in lines[0].split(",")]
        records = []
        for line in lines[1:]:
            parts = line.strip().split(",")
            if len(parts) < len(header):
                continue
            row = dict(zip(header, parts))
            if not row.get("close") or "null" in row["close"].lower():
                continue
            try:
                records.append({
                    "date":     row.get("date", ""),
                    "open":     float(row.get("open")   or 0),
                    "high":     float(row.get("high")   or 0),
                    "low":      float(row.get("low")    or 0),
                    "close":    float(row.get("close")  or 0),
                    "adjClose": float(row.get("adj close", row.get("adjclose", 0)) or 0),
                    "volume":   int(float(row.get("volume", 0) or 0)),
                    "ticker":   ticker,
                })
            except (ValueError, TypeError):
                continue
        return records
    except Exception as e:
        with print_lock:
            print(f"\n  [Yahoo v7 ✗] {ticker}: {e}")
        return []

# ============================================================
# UTILIDADES
# ============================================================

def weekdays_in_range(start: date, end: date) -> list[str]:
    days, current = [], start
    while current <= end:
        if current.weekday() < 5:
            days.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return days

def save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============================================================
# MAIN
# ============================================================

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    end   = date.today()
    start = end - timedelta(days=YEARS_BACK * 365)
    all_days = weekdays_in_range(start, end)

    asset_set = {a["mnemonic"] for a in BVC_ASSETS}

    progress["bvc_total"]  = len(all_days)
    progress["start_time"] = time.time()

    print("=" * 65)
    print(f"  BVC TURBO DOWNLOADER")
    print(f"  Rango  : {start} → {end}")
    print(f"  Fechas : {len(all_days)} días hábiles")
    print(f"  Activos: {len(BVC_ASSETS)} BVC + {len(YAHOO_ASSETS)} Yahoo")
    print(f"  Hilos  : {BVC_WORKERS} BVC | {YAHOO_WORKERS} Yahoo (en paralelo)")
    print(f"  Truco  : 1 request/fecha = todos los activos a la vez")
    print("=" * 65)

    # ---------- BVC ----------
    print(f"\n[BVC] Iniciando descarga...\n")
    all_results: dict[str, list] = {a["mnemonic"]: [] for a in BVC_ASSETS}

    with ThreadPoolExecutor(max_workers=BVC_WORKERS) as executor:
        futures = {
            executor.submit(worker_day, d, asset_set): d
            for d in all_days
        }
        for future in as_completed(futures):
            try:
                day_result = future.result()
                for mn, record in day_result.items():
                    all_results[mn].append(record)
            except Exception:
                with print_lock:
                    progress["bvc_errors"] += 1

    elapsed_bvc = time.time() - progress["start_time"]
    print(f"\n\n[BVC] Completado en {elapsed_bvc:.1f}s")

    # ---------- Yahoo (paralelo) ----------
    print(f"\n[Yahoo] Iniciando descarga de {len(YAHOO_ASSETS)} tickers...\n")
    yahoo_results: dict[str, list] = {}
    t_yahoo = time.time()

    with ThreadPoolExecutor(max_workers=YAHOO_WORKERS) as executor:
        futures_y = {
            executor.submit(download_yahoo_ticker, ticker, start, end): ticker
            for ticker in YAHOO_ASSETS
        }
        for future in as_completed(futures_y):
            ticker = futures_y[future]
            try:
                records = future.result()
                yahoo_results[ticker] = records
                print(f"  ✓ {ticker:<8} {len(records):>4} registros")
            except Exception as e:
                yahoo_results[ticker] = []
                print(f"  ✗ {ticker:<8} ERROR: {e}")

    elapsed_yahoo = time.time() - t_yahoo

    # ---------- Guardar ----------
    print(f"\n{'='*65}")
    print("GUARDANDO ARCHIVOS...")
    total_records = 0

    for mn, records in all_results.items():
        records.sort(key=lambda x: x["date"])
        path = os.path.join(OUTPUT_DIR, f"{mn}_historico.json")
        save_json(path, records)
        total_records += len(records)
        status = "✓" if records else "⚠ sin datos"
        print(f"  {status} {mn:<20} {len(records):>4} registros")

    for ticker, records in yahoo_results.items():
        path = os.path.join(OUTPUT_DIR, f"{ticker}_historico.json")
        save_json(path, records)
        total_records += len(records)
        status = "✓" if records else "⚠ sin datos"
        print(f"  {status} {ticker:<20} {len(records):>4} registros")

    # ---------- Resumen ----------
    elapsed_total = time.time() - progress["start_time"]
    print(f"\n{'='*65}")
    print(f"  COMPLETADO")
    print(f"  BVC   : {elapsed_bvc:.1f}s  ({len(all_days)/elapsed_bvc:.1f} fechas/seg)")
    print(f"  Yahoo : {elapsed_yahoo:.1f}s")
    print(f"  Total : {elapsed_total:.1f}s | {total_records} registros | {OUTPUT_DIR}/")
    print(f"{'='*65}")

    save_json(os.path.join(OUTPUT_DIR, "resumen_descarga.json"), {
        "fecha_descarga":     date.today().isoformat(),
        "rango":              {"inicio": start.isoformat(), "fin": end.isoformat()},
        "duracion_segundos":  round(elapsed_total, 2),
        "fechas_procesadas":  len(all_days),
        "bvc_activos":        {m: len(r) for m, r in all_results.items()},
        "yahoo_activos":      {t: len(r) for t, r in yahoo_results.items()},
    })

if __name__ == "__main__":
    main()