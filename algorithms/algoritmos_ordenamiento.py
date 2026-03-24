def es_menor(activa, activb):
    # Criterio 1: Fecha 
    if activa['fecha'] < activb['fecha']:
        return True
    if activa['fecha'] > activb['fecha']:
        return False
    # Criterio 2: Precio de cierre (si las fechas son iguales) 
    return activa['close'] < activb['close']

def tim_sort(data):
    data.sort(key=lambda x: (x['fecha'], x['close'])) # Implementación nativa permitida
    return data

def comb_sort(data):
    gap = len(data)
    shrink = 1.3
    sorted = False
    while not sorted:
        gap = int(gap / shrink)
        if gap <= 1:
            gap = 1
            sorted = True
        for i in range(len(data) - gap):
            if es_menor(data[i + gap], data[i]):
                data[i], data[i + gap] = data[i + gap], data[i]
                sorted = False
    return data

def selection_sort(data):
    for i in range(len(data)):
        min_idx = i
        for j in range(i + 1, len(data)):
            if es_menor(data[j], data[min_idx]):
                min_idx = j
        data[i], data[min_idx] = data[min_idx], data[i]
    return data

class Node:
    def __init__(self, val):
        self.val = val
        self.left = self.right = None

def insert(root, val):
    if root is None: return Node(val)
    if es_menor(val, root.val): root.left = insert(root.left, val)
    else: root.right = insert(root.right, val)
    return root

def inorder(root, res):
    if root:
        inorder(root.left, res)
        res.append(root.val)
        inorder(root.right, res)

def tree_sort(data):
    if not data: return []
    root = None
    for x in data: root = insert(root, x)
    res = []
    inorder(root, res)
    return res



def pigeonhole_sort(data, key='volumen'):
    min_val = min(d[key] for d in data)
    max_val = max(d[key] for d in data)
    size = int(max_val - min_val + 1)
    holes = [[] for _ in range(size)]
    for x in data:
        holes[int(x[key] - min_val)].append(x)
    res = []
    for hole in holes:
        res.extend(hole)
    return res

def bucket_sort(data):
    # Ejemplo usando el precio de cierre normalizado
    if not data: return []
    num_buckets = 10
    max_val = max(d['close'] for d in data)
    buckets = [[] for _ in range(num_buckets)]
    for x in data:
        index = int((x['close'] / max_val) * (num_buckets - 1))
        buckets[index].append(x)
    for b in buckets:
        b.sort(key=lambda x: (x['fecha'], x['close']))
    return [item for b in buckets for item in b]

def quick_sort(data):
    if len(data) <= 1: return data
    pivot = data[len(data) // 2]
    left = [x for x in data if es_menor(x, pivot)]
    middle = [x for x in data if x == pivot]
    right = [x for x in data if es_menor(pivot, x)]
    return quick_sort(left) + middle + quick_sort(right)

def heapify(data, n, i):
    largest = i
    l, r = 2 * i + 1, 2 * i + 2
    if l < n and es_menor(data[largest], data[l]): largest = l
    if r < n and es_menor(data[largest], data[r]): largest = r
    if largest != i:
        data[i], data[largest] = data[largest], data[i]
        heapify(data, n, largest)

def heap_sort(data):
    n = len(data)
    for i in range(n // 2 - 1, -1, -1): heapify(data, n, i)
    for i in range(n - 1, 0, -1):
        data[i], data[0] = data[0], data[i]
        heapify(data, i, 0)
    return data

def bitonic_sort(data, low, cnt, dire):
    if cnt > 1:
        k = cnt // 2
        bitonic_sort(data, low, k, 1)
        bitonic_sort(data, low + k, k, 0)
        bitonic_merge(data, low, cnt, dire)

def bitonic_merge(data, low, cnt, dire):
    if cnt > 1:
        k = cnt // 2
        for i in range(low, low + k):
            if dire == (es_menor(data[i + k], data[i])):
                data[i], data[i + k] = data[i + k], data[i]
        bitonic_merge(data, low, k, dire)
        bitonic_merge(data, low + k, k, dire)

def gnome_sort(data):
    i = 0
    while i < len(data):
        if i == 0 or not es_menor(data[i], data[i-1]): i += 1
        else:
            data[i], data[i-1] = data[i-1], data[i]
            i -= 1
    return data

def binary_insertion_sort(data):
    for i in range(1, len(data)):
        val = data[i]
        low, high = 0, i - 1
        while low <= high:
            mid = (low + high) // 2
            if es_menor(val, data[mid]): high = mid - 1
            else: low = mid + 1
        data[:] = data[:low] + [val] + data[low:i] + data[i+1:]
    return data

def radix_sort(data):
    # Suponiendo que la fecha está en formato AAAAMMDD como entero
    max_val = max(int(d['fecha'].replace('-','')) for d in data)
    exp = 1
    while max_val // exp > 0:
        # Aquí se aplicaría un counting sort interno por cada dígito (exp)
        # ... (implementación de counting sort por dígito)
        exp *= 10
    return data