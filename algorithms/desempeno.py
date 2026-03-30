import json
import time
import argparse
from pathlib import Path

try:
    from . import algoritmos_ordenamiento
except ImportError:
    import algoritmos_ordenamiento


def _bitonic_sort_wrapper(data):
    """Ejecuta bitonic sort sobre una copia adaptada a potencia de 2."""
    if not data:
        return data

    n = len(data)
    objetivo = 1
    while objetivo < n:
        objetivo <<= 1

    # Rellenamos con el maximo para no afectar el orden de los datos reales.
    max_item = max(data, key=lambda x: (x["fecha"], x["close"]))
    data_ext = list(data) + [max_item] * (objetivo - n)
    algoritmos_ordenamiento.bitonic_sort(data_ext, 0, len(data_ext), 1)
    return data_ext[:n]


def cargar_dataset_desde_historicos(ruta_hist):
    """
    Carga y unifica todos los archivos *_historico.json de una carpeta.
    Retorna una lista de dicts con llaves: fecha, close, volumen, ticker.
    """
    base = Path(ruta_hist)
    if not base.exists():
        raise FileNotFoundError(f"No existe la ruta: {base}")

    def _to_float(value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            normalizado = value.strip().replace(",", "")
            if not normalizado:
                return None
            try:
                return float(normalizado)
            except ValueError:
                return None
        return None

    def _to_int(value):
        num = _to_float(value)
        if num is None:
            return None
        return int(num)

    datos_unif = []
    archivos = sorted(base.glob("*_historico.json"))

    for archivo in archivos:
        if archivo.name == "resumen_descarga.json":
            continue

        tic_arch = archivo.name.replace("_historico.json", "")

        with archivo.open("r", encoding="utf-8") as f:
            contenido = json.load(f)

        if not isinstance(contenido, list):
            continue

        for fila in contenido:
            fecha = fila.get("fecha") or fila.get("date")
            close = _to_float(fila.get("close"))
            volumen = fila.get("volumen")
            if volumen is None:
                volumen = fila.get("volume")
            volumen = _to_int(volumen)
            ticker = fila.get("ticker") or fila.get("mnemonic") or tic_arch

            if fecha is None or close is None or volumen is None:
                continue

            datos_unif.append(
                {
                    "fecha": fecha,
                    "close": close,
                    "volumen": volumen,
                    "ticker": ticker,
                }
            )

    return datos_unif

def medir_desempeno_ordenamiento(datos_unif):
    """
    Ejecuta los 12 algoritmos y retorna una lista de resultados
    con el nombre, tamaño del dataset y tiempo de ejecución.
    """
    algoritmos = [
        ("TimSort", algoritmos_ordenamiento.tim_sort),
        ("Comb Sort", algoritmos_ordenamiento.comb_sort),
        ("Selection Sort", algoritmos_ordenamiento.selection_sort),
        ("Tree Sort", algoritmos_ordenamiento.tree_sort),
        ("Pigeonhole Sort", algoritmos_ordenamiento.pigeonhole_sort),
        ("Bucket Sort", algoritmos_ordenamiento.bucket_sort),
        ("QuickSort", algoritmos_ordenamiento.quick_sort),
        ("HeapSort", algoritmos_ordenamiento.heap_sort),
        ("Bitonic Sort", _bitonic_sort_wrapper),
        ("Gnome Sort", algoritmos_ordenamiento.gnome_sort),
        ("Binary Insertion Sort", algoritmos_ordenamiento.binary_insertion_sort),
        ("RadixSort", algoritmos_ordenamiento.radix_sort)
    ]
    
    res_tabla = []
    tam_datos = len(datos_unif) # Tamaño del dato entero [cite: 33]

    for nombre, func in algoritmos:
        # Creamos una copia para no afectar el dataset original en cada iteración
        datos_cpy = list(datos_unif)

        try:
            inicio = time.perf_counter()
            func(datos_cpy)
            fin = time.perf_counter()

            tiempo_total = fin - inicio
            res_tabla.append(
                {
                    "Metodo": nombre,
                    "Tamano": tam_datos,
                    "Tiempo": f"{tiempo_total:.6f} seg",
                    "Estado": "OK",
                }
            )
            print(f"✅ {nombre} finalizado en {tiempo_total:.6f} segundos.")
        except Exception as exc:
            res_tabla.append(
                {
                    "Metodo": nombre,
                    "Tamano": tam_datos,
                    "Tiempo": "N/A",
                    "Estado": f"ERROR: {type(exc).__name__}",
                }
            )
            print(f"⚠️ {nombre} fallo: {type(exc).__name__}: {exc}")

    return res_tabla


def ordenar_dataset_unificado(datos_unif):
    """Ordena ascendente por fecha y luego por close usando TimSort."""
    return algoritmos_ordenamiento.tim_sort(list(datos_unif))


def parse_tiempo_segundos(val_tiempo):
    if not isinstance(val_tiempo, str) or val_tiempo == "N/A":
        return None
    if not val_tiempo.endswith(" seg"):
        return None
    try:
        return float(val_tiempo.replace(" seg", ""))
    except ValueError:
        return None


def ordenar_tiempos_ascendente(res_tabla):
    """Ordena ascendente por tiempo de ejecucion; errores al final."""
    return sorted(
        res_tabla,
        key=lambda r: (
            parse_tiempo_segundos(r.get("Tiempo")) is None,
            parse_tiempo_segundos(r.get("Tiempo")) or float("inf"),
        ),
    )


def generar_grafico_barras_tiempos(res_ord, ruta_graf):
    """Genera diagrama de barras horizontal (ascendente) de los 12 algoritmos."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print(
            "⚠️ No se pudo generar el grafico: falta matplotlib. "
            "Instala con: pip install matplotlib"
        )
        return False

    validos = [
        r for r in res_ord if parse_tiempo_segundos(r.get("Tiempo")) is not None
    ]
    if not validos:
        print("⚠️ No hay tiempos validos para graficar.")
        return False

    metodos = [r["Metodo"] for r in validos]
    tiempos = [parse_tiempo_segundos(r["Tiempo"]) for r in validos]

    plt.figure(figsize=(10, 6))
    bars = plt.barh(metodos, tiempos, color="#2E86AB")
    plt.xlabel("Tiempo (segundos)")
    plt.ylabel("Algoritmo")
    plt.title("Tiempos de Algoritmos de Ordenamiento (Ascendente)")

    for barra, tiempo in zip(bars, tiempos):
        plt.text(
            barra.get_width() + 0.001,
            barra.get_y() + barra.get_height() / 2,
            f"{tiempo:.6f}",
            va="center",
            fontsize=8,
        )

    plt.tight_layout()
    plt.savefig(ruta_graf, dpi=150)
    plt.close()
    return True


def top_15_mayor_volumen_por_activo(datos_unif):
    """
    Para cada ticker:
    1) toma los 15 dias con mayor volumen,
    2) los devuelve ordenados ascendente por volumen.
    """
    por_tic = {}
    for fila in datos_unif:
        ticker = fila.get("ticker") or "SIN_TICKER"
        por_tic.setdefault(ticker, []).append(fila)

    salida = {}
    for ticker, filas in por_tic.items():
        top_desc = sorted(filas, key=lambda x: x["volumen"], reverse=True)[:15]
        top_asc = sorted(top_desc, key=lambda x: (x["volumen"], x["fecha"], x["close"]))
        salida[ticker] = top_asc

    return salida


def guardar_json(ruta, data):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ejecutar_analisis_ordenamiento(
    ruta_hist,
    max_registros=0,
    carpeta_salida=None,
    generar_grafico=True,
):
    """Ejecuta el analisis completo y devuelve los resultados en memoria."""
    datos = cargar_dataset_desde_historicos(ruta_hist)
    if max_registros and max_registros > 0:
        datos = datos[:max_registros]

    if not datos:
        raise ValueError("No se encontraron datos validos para analizar.")

    if carpeta_salida is None:
        carpeta_salida = Path(__file__).resolve().parents[1] / "etl" / "resultados_analisis"
    else:
        carpeta_salida = Path(carpeta_salida)

    datos_ord = ordenar_dataset_unificado(datos)
    resultados = medir_desempeno_ordenamiento(datos)
    res_asc = ordenar_tiempos_ascendente(resultados)
    top15_activo = top_15_mayor_volumen_por_activo(datos)

    ruta_datos_ord = carpeta_salida / "dataset_unificado_ordenado.json"
    ruta_tiem = carpeta_salida / "tiempos_algoritmos_asc.json"
    ruta_top15 = carpeta_salida / "top_15_mayor_volumen_por_activo.json"
    ruta_graf = carpeta_salida / "tiempos_algoritmos_barras_asc.png"

    guardar_json(ruta_datos_ord, datos_ord)
    guardar_json(ruta_tiem, res_asc)
    guardar_json(ruta_top15, top15_activo)

    graf_gen = False
    if generar_grafico:
        graf_gen = generar_grafico_barras_tiempos(res_asc, ruta_graf)

    return {
        "total_registros": len(datos),
        "dataset_ordenado": datos_ord,
        "resultados_tiempos": res_asc,
        "top_15_por_activo": top15_activo,
        "rutas_archivos": {
            "dataset_ordenado": str(ruta_datos_ord),
            "tiempos_asc": str(ruta_tiem),
            "top_15": str(ruta_top15),
            "grafico_barras": str(ruta_graf) if graf_gen else None,
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Medicion de algoritmos de ordenamiento")
    parser.add_argument(
        "--ruta-historicos",
        type=str,
        default=str(Path(__file__).resolve().parents[1] / "etl" / "historicos"),
        help="Ruta de la carpeta con archivos *_historico.json",
    )
    parser.add_argument(
        "--max-registros",
        type=int,
        default=0,
        help="Limita el dataset a N registros (0 = sin limite)",
    )
    parser.add_argument(
        "--carpeta-salida",
        type=str,
        default=str(Path(__file__).resolve().parents[1] / "etl" / "resultados_analisis"),
        help="Carpeta donde se guardan los resultados (JSON y grafico)",
    )
    args = parser.parse_args()

    try:
        analisis = ejecutar_analisis_ordenamiento(
            ruta_hist=args.ruta_historicos,
            max_registros=args.max_registros,
            carpeta_salida=args.carpeta_salida,
            generar_grafico=True,
        )
    except ValueError as exc:
        print(str(exc))
    else:
        print(f"Dataset cargado: {analisis['total_registros']} registros")
        print(f"📁 Dataset ordenado guardado en: {analisis['rutas_archivos']['dataset_ordenado']}")
        print(f"📁 Tiempos ordenados guardados en: {analisis['rutas_archivos']['tiempos_asc']}")
        if analisis["rutas_archivos"]["grafico_barras"]:
            print(f"📊 Grafico de barras guardado en: {analisis['rutas_archivos']['grafico_barras']}")
        print(f"📁 Top 15 por activo guardado en: {analisis['rutas_archivos']['top_15']}")

        print("\nResumen:")
        for row in analisis["resultados_tiempos"]:
            print(
                f"- {row['Metodo']}: {row['Tiempo']} ({row['Tamano']} registros) | {row['Estado']}"
            )