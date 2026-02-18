import requests
import uuid
import time
import base64
import json
from datetime import date, timedelta

# ============================================================
MNEMONIC = "ECOPETROL"
BOARD = "EQTY"
YEARS_BACK = 5
INTERVAL_DAYS = 90
OUTPUT_FILE = f"{MNEMONIC}_historico.json"
MAX_RETRY_DAYS = 5  # si tab vacío, intenta los siguientes N días
# ============================================================

def get_bvc_token(session):
    ts = int(time.time() * 1000)
    r = str(uuid.uuid4())
    response = session.get("https://www.bvc.com.co/api/handshake", params={"ts": ts, "r": r})
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

def fetch_date(session, trade_date):
    """Obtiene token fresco y consulta una fecha. Retorna (asset, fecha_usada) o (None, None)."""
    token = get_bvc_token(session)
    r = session.get(
        "https://rest.bvc.com.co/market-information/rv/lvl-2",
        params={
            "filters[marketDataRv][tradeDate]": trade_date,
            "filters[marketDataRv][board]": ["EQTY", "REPO", "TTV"],
            "sorter[]": ["tradeValue", "DESC"]
        },
        headers={"token": token, "k": build_k_header(trade_date)}
    )
    data = r.json()
    tab = data.get("data", {}).get("tab", [])
    if not tab:
        return None, None
    asset = next((x for x in tab if x["mnemonic"] == MNEMONIC and x["board"] == BOARD), None)
    return asset, trade_date

def fetch_with_retry(session, trade_date_str):
    """Si la fecha es festivo/vacío, reintenta los siguientes días hábiles."""
    base = date.fromisoformat(trade_date_str)
    for delta in range(MAX_RETRY_DAYS):
        candidate = base + timedelta(days=delta)
        # Saltar fines de semana
        while candidate.weekday() >= 5:
            candidate += timedelta(days=1)
        candidate_str = candidate.strftime("%Y-%m-%d")
        asset, used_date = fetch_date(session, candidate_str)
        if asset and asset.get("lastPrice") is not None:
            if delta > 0:
                print(f"    [RETRY] Festivo detectado, usando {used_date} (+{delta} días)")
            return asset, used_date
        else:
            print(f"    [SKIP]  {candidate_str} — tab vacío o sin datos, reintentando...")
        time.sleep(0.4)
    return None, None

def get_sampled_dates(years_back, interval_days):
    end = date.today()
    start = end - timedelta(days=years_back * 365)
    dates = []
    current = start
    while current <= end:
        while current.weekday() >= 5:
            current += timedelta(days=1)
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=interval_days)
    return dates

def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Origin": "https://www.bvc.com.co",
        "Referer": "https://www.bvc.com.co/"
    })

    dates = get_sampled_dates(YEARS_BACK, INTERVAL_DAYS)
    total = len(dates)
    print(f"Descargando {MNEMONIC} — {total} puntos cada {INTERVAL_DAYS} días\n")

    results = []

    for i, trade_date in enumerate(dates):
        print(f"[{i+1}/{total}] Consultando {trade_date}...")
        try:
            asset, used_date = fetch_with_retry(session, trade_date)
            if asset:
                asset["tradeDate"] = used_date
                asset["targetDate"] = trade_date  # fecha original pedida
                results.append(asset)
                print(f"    [OK] Close: {asset['lastPrice']} | Vol: {asset['volume']}")
            else:
                print(f"    [FAIL] Sin datos tras {MAX_RETRY_DAYS} intentos")
            time.sleep(0.5)
        except Exception as e:
            print(f"    [ERROR] {e}")
            time.sleep(2)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"Listo. {len(results)}/{total} registros guardados en '{OUTPUT_FILE}'")

if __name__ == "__main__":
    main()