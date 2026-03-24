import json
import time
import argparse
from pathlib import Path

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


def cargar_dataset_desde_historicos(ruta_historicos):
    """
    Carga y unifica todos los archivos *_historico.json de una carpeta.
    Retorna una lista de dicts con llaves: fecha, close, volumen, ticker.
    """
    base = Path(ruta_historicos)
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

    dataset_unificado = []
    archivos = sorted(base.glob("*_historico.json"))

    for archivo in archivos:
        if archivo.name == "resumen_descarga.json":
            continue

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

            if fecha is None or close is None or volumen is None:
                continue

            dataset_unificado.append(
                {
                    "fecha": fecha,
                    "close": close,
                    "volumen": volumen,
                    "ticker": fila.get("ticker"),
                }
            )

    return dataset_unificado

def medir_desempeno_ordenamiento(dataset_unificado):
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
    
    resultados_tabla = []
    tamanio_datos = len(dataset_unificado) # Tamaño del dato entero [cite: 33]

    for nombre, func in algoritmos:
        # Creamos una copia para no afectar el dataset original en cada iteración
        datos_copia = list(dataset_unificado)

        try:
            inicio = time.perf_counter()
            func(datos_copia)
            fin = time.perf_counter()

            tiempo_total = fin - inicio
            resultados_tabla.append(
                {
                    "Metodo": nombre,
                    "Tamano": tamanio_datos,
                    "Tiempo": f"{tiempo_total:.6f} seg",
                    "Estado": "OK",
                }
            )
            print(f"✅ {nombre} finalizado en {tiempo_total:.6f} segundos.")
        except Exception as exc:
            resultados_tabla.append(
                {
                    "Metodo": nombre,
                    "Tamano": tamanio_datos,
                    "Tiempo": "N/A",
                    "Estado": f"ERROR: {type(exc).__name__}",
                }
            )
            print(f"⚠️ {nombre} fallo: {type(exc).__name__}: {exc}")

    return resultados_tabla


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
    args = parser.parse_args()

    dataset = cargar_dataset_desde_historicos(args.ruta_historicos)
    if args.max_registros and args.max_registros > 0:
        dataset = dataset[: args.max_registros]

    if not dataset:
        print("No se encontraron datos validos para medir desempeno.")
    else:
        print(f"Dataset cargado: {len(dataset)} registros")
        resultados = medir_desempeno_ordenamiento(dataset)
        print("\nResumen:")
        for row in resultados:
            print(f"- {row['Metodo']}: {row['Tiempo']} ({row['Tamano']} registros)")