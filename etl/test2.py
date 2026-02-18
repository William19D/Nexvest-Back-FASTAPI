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
BVC_ASSETS = [
    {"mnemonic": "ECOPETROL", "board": "EQTY"},
    {"mnemonic": "NUTRESA",   "board": "EQTY"},
    {"mnemonic": "PFBCOLOM",  "board": "EQTY"},
]

YEARS_BACK = 5
MAX_RETRY_DAYS = 7
OUTPUT_DIR = "historicos"
MAX_WORKERS = 20       # hilos concurrentes por fechas
DELAY = 0.05           # delay mínimo — un hilo por fecha no satura
# ============================================================

print_lock = threading.Lock()
progress = {"done": 0, "total": 0, "ok": 0, "skip": 0, "errors": 0}

def log(msg: str):
    with print_lock:
        print(msg)

def print_dashboard(trade_date: str = ""):
    with print_lock:
        d = progress
        total = d["total"] or 1
        done = d["done"]
        pct = int((done / total) * 40)
        bar = f"[{'█' * pct}{'░' * (40 - pct)}]"
        pct_num = int((done / total) * 100)
        eta_str = ""
        if d.get("start_time") and done > 0:
            elapsed = time.time() - d["start_time"]
            rate = done / elapsed
            remaining = (total - done) / rate if rate > 0 else 0
            eta_str = f"ETA: {int(remaining//60)}m {int(remaining%60)}s"
        print(
            f"\r  {bar} {pct_num:>3}% | "
            f"Fechas: {done}/{total} | "
            f"OK: {d['ok']} | "
            f"Skip: {d['skip']} | "
            f"Err: {d['errors']} | "
            f"{eta_str} | {trade_date:<12}",
            end="", flush=True
        )

# ============================================================
# BVC
# ============================================================

def get_bvc_token(session: requests.Session) -> str:
    ts = int(time.time() * 1000)
    r = str(uuid.uuid4())
    resp = session.get(
        "https://www.bvc.com.co/api/handshake",
        params={"ts": ts, "r": r},
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()["token"]

def build_k_header(trade_date: str) -> str:
    query = (
        f"filters[marketDataRv][tradeDate]={trade_date}"
        f"&filters[marketDataRv][board]=EQTY"
        f"&filters[marketDataRv][board]=REPO"
        f"&filters[marketDataRv][board]=TTV"
        f"&sorter[]=tradeValue&sorter[]=DESC"
    )
    return base64.b64encode(query.encode()).decode()

def fetch_day(session: requests.Session, trade_date: str) -> list:
    """
    UNA sola llamada trae TODOS los activos del día.
    Retorna el tab completo o [] si no hay datos.
    """
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
    return r.json().get("data", {}).get("tab", [])

def fetch_day_with_retry(trade_date_str: str) -> tuple:
    """
    Cada hilo tiene su propia sesión.
    Retorna (tab, fecha_usada) o ([], None).
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Origin": "https://www.bvc.com.co",
        "Referer": "https://www.bvc.com.co/"
    })

    base = date.fromisoformat(trade_date_str)
    for delta in range(MAX_RETRY_DAYS):
        candidate = base + timedelta(days=delta)
        while candidate.weekday() >= 5:
            candidate += timedelta(days=1)
        candidate_str = candidate.strftime("%Y-%m-%d")
        try:
            tab = fetch_day(session, candidate_str)
            if tab:
                return tab, candidate_str
            time.sleep(0.2)
        except Exception as e:
            time.sleep(0.5)
    return [], None

def process_day(trade_date: str, mnemonics_boards: list) -> dict:
    """
    Worker por fecha — descarga el día y extrae todos los activos pedidos.
    Retorna dict: { mnemonic: record }
    """
    tab, used_date = fetch_day_with_retry(trade_date)

    result = {}
    if not tab:
        with print_lock:
            progress["skip"] += 1
            progress["done"] += 1
        print_dashboard(trade_date)
        return result

    # Indexar tab por (mnemonic, board) para O(1)
    tab_index = {(item["mnemonic"], item["board"]): item for item in tab}

    for cfg in mnemonics_boards:
        mnemonic = cfg["mnemonic"]
        board = cfg["board"]
        asset = tab_index.get((mnemonic, board))
        if asset and asset.get("lastPrice") is not None:
            result[mnemonic] = {
                "date":                used_date,
                "targetDate":          trade_date,
                "open":                asset.get("openPrice"),
                "high":                asset.get("maximumPrice"),
                "low":                 asset.get("minimumPrice"),
                "close":               asset.get("lastPrice"),
                "volume":              asset.get("volume"),
                "averagePrice":        asset.get("averagePrice"),
                "absoluteVariation":   asset.get("absoluteVariation"),
                "percentageVariation": asset.get("percentageVariation"),
                "mnemonic":            mnemonic,
                "board":               board,
            }

    with print_lock:
        progress["ok"] += len(result)
        progress["done"] += 1
    print_dashboard(trade_date)

    time.sleep(DELAY)
    return result

# ============================================================
# MAIN
# ============================================================

def get_all_weekdays(start: date, end: date) -> list:
    days = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return days

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    end = date.today()
    start = end - timedelta(days=YEARS_BACK * 365)
    all_days = get_all_weekdays(start, end)

    progress["total"] = len(all_days)
    progress["start_time"] = time.time()

    print(f"\nNexVest ETL — Modo turbo ({MAX_WORKERS} hilos por fecha)")
    print(f"Rango: {start} → {end} | {len(all_days)} fechas")
    print(f"Activos por fecha: {[a['mnemonic'] for a in BVC_ASSETS]}")
    print(f"Optimización: 1 request = todos los activos del día\n")

    # Acumuladores por activo
    all_results = {cfg["mnemonic"]: [] for cfg in BVC_ASSETS}

    # Lanzar un hilo por fecha
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_day, d, BVC_ASSETS): d
            for d in all_days
        }
        for future in as_completed(futures):
            try:
                day_result = future.result()
                # Distribuir registros a cada activo
                for mnemonic, record in day_result.items():
                    all_results[mnemonic].append(record)
            except Exception as e:
                with print_lock:
                    progress["errors"] += 1

    print("\n")  # salto de línea tras barra de progreso
    elapsed = time.time() - progress["start_time"]

    # Ordenar por fecha y guardar
    print(f"\n{'='*65}")
    print(f"GUARDANDO ARCHIVOS...")
    total_records = 0
    for mnemonic, records in all_results.items():
        records.sort(key=lambda x: x["date"])
        output_file = os.path.join(OUTPUT_DIR, f"{mnemonic}_historico.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        total_records += len(records)
        print(f"  ✓ {mnemonic:<15} {len(records):>4} registros → {output_file}")

    print(f"\n{'='*65}")
    print(f"COMPLETADO en {elapsed:.1f}s | {total_records} registros totales")
    print(f"Velocidad: {len(all_days)/elapsed:.1f} fechas/seg")
    print(f"{'='*65}")

    # Resumen
    summary_file = os.path.join(OUTPUT_DIR, "resumen_descarga.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump({
            "fecha_descarga": date.today().isoformat(),
            "rango": {"inicio": start.isoformat(), "fin": end.isoformat()},
            "duracion_segundos": round(elapsed, 2),
            "fechas_procesadas": len(all_days),
            "activos": {m: len(r) for m, r in all_results.items()}
        }, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()