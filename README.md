# 📈 NexVest API

<div align="center">

![Python](https://img.shields.io/badge/python-3.13+-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688?style=for-the-badge&logo=fastapi)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-13AA52?style=for-the-badge&logo=mongodb)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

**API de Análisis Financiero Avanzado para la BVC**

Proporciona acceso a datos históricos de la Bolsa de Valores de Colombia e implementa algoritmos de análisis de rendimiento.

[Documentación](#-documentación) • [Instalación](#-instalación) • [Uso](#-uso) • [Contribuir](#-contribución)

</div>

---

## 📋 Tabla de Contenidos

- [✨ Características](#-características)
- [🚀 Inicio Rápido](#-inicio-rápido)
- [📦 Instalación](#-instalación)
- [🔧 Configuración](#-configuración)
- [💻 Comandos](#-comandos)
- [📚 Endpoints](#-endpoints)
- [🏗️ Estructura del Proyecto](#️-estructura-del-proyecto)
- [🔐 Variables de Entorno](#-variables-de-entorno)
- [📝 Documentación](#-documentación)
- [🤝 Contribución](#-contribución)
- [📄 Licencia](#-licencia)

---

## ✨ Características

✅ **Análisis de Datos Históricos**
- Acceso a datos históricos de acciones de la BVC
- Filtrado flexible por rango de fechas
- Exportación de resultados en JSON

✅ **Benchmarking de Algoritmos**
- Análisis de rendimiento de 12 algoritmos de ordenamiento
- Medición precisa de tiempos de ejecución
- Generación de gráficos comparativos

✅ **Algoritmos Implementados**
- TimSort, Comb Sort, Selection Sort, Tree Sort
- Pigeonhole Sort, Bucket Sort, QuickSort, HeapSort
- Bitonic Sort, Gnome Sort, Binary Insertion Sort, RadixSort

✅ **Arquitectura Moderna**
- Framework FastAPI (async ready)
- MongoDB Atlas para almacenamiento
- CORS habilitado para frontend
- Logging y error handling robusto
- Documentación automática (Swagger/ReDoc)

✅ **Producción Ready**
- Compatible con Vercel serverless
- Type hints completos en Python
- Validaciones exhaustivas
- Health checks integrados

---

## 🚀 Inicio Rápido

### Requisitos Previos

- **Python 3.13+** (64-bit)
- **pip** (gestor de paquetes Python)
- **Git** (para clonar el repositorio)
- **MongoDB Atlas** (base de datos en la nube)

### Instalación en 3 Pasos

```bash
# 1️⃣ Clonar el repositorio
git clone https://github.com/tu-usuario/Nexvest-Back-FASTAPI.git
cd Nexvest-Back-FASTAPI

# 2️⃣ Configurar variables de entorno
cp .env.example .env
# Edita .env y agrega tu MONGO_URI

# 3️⃣ Instalar dependencias  y levantar servidor
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt --prefer-binary
python -m uvicorn main:app --reload
```

✅ **Listo!** Accede a `http://localhost:8000/docs`

---

## 📦 Instalación

### Opción A: Instalación Estándar (Recomendado)

```bash
# Actualizar pip y herramientas de build
python -m pip install --upgrade pip setuptools wheel

# Instalar dependencias con wheels precompilados
python -m pip install -r requirements.txt --prefer-binary
```

### Opción B: Instalación con entorno virtual

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno
# En Windows:
venv\Scripts\activate
# En macOS/Linux:
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt --prefer-binary
```

### Opción C: Instalación de Rust (si es necesario)

Si encuentras errores con `pydantic-core`, instala Rust:

```bash
# Windows
Invoke-WebRequest -Uri https://win.rustup.rs -UseBasicParsing -OutFile rustup-init.exe
.\rustup-init.exe -y
Remove-Item rustup-init.exe

# Luego instala las dependencias
pip install -r requirements.txt
```

---

## 🔧 Configuración

### 1. Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
# MongoDB Atlas (REQUERIDO)
MONGO_URI=mongodb+srv://usuario:contraseña@cluster.mongodb.net/?retryWrites=true&w=majority

# Nombre de la base de datos (opcional, default: nexvest)
MONGO_DB_NAME=nexvest

# Vercel (agrega automáticamente en Vercel, no necesita cambios)
# VERCEL=
```

### 2. Obtener MONGO_URI

1. Ve a [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Crea un cluster gratuito
3. Copia la connection string
4. Reemplaza `<usuario>` y `<contraseña>` en `.env`

### 3. Cargar Datos Históricos (Opcional)

```bash
# Los datos históricos deben estar en: etl/historicos/*.json
# Ejemplo de estructura:
# etl/
#   └── historicos/
#       ├── ECOPETROL_historico.json
#       ├── GEB_historico.json
#       └── ...
```

---

## 💻 Comandos

### 🎯 Desarrollo

```bash
# Levantar servidor en modo desarrollo (hot reload)
python -m uvicorn main:app --reload

# Levantar en puerto específico
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Levantar sin reload (producción simulada)
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 📊 Ejecución de Análisis

```bash
# Ejecutar análisis de algoritmos (desde Python)
python -m algorithms.desempeno

# Con parámetros personalizados
python -m algorithms.desempeno --max-registros 1000 --generar-grafico True
```

### 📝 Verificación y Testing

```bash
# Compilar búsqueda de errores de sintaxis
python -m py_compile main.py database.py

# Ver información de la aplicación
python -c "import main; print(main.app.__dict__)"

# Listar endpoints disponibles
python -c "from main import app; [print(route.path) for route in app.routes]"
```

### 🧹 Limpieza

```bash
# Eliminar caché de Python
Remove-Item -Recurse -Force __pycache__
Remove-Item -Recurse -Force .pytest_cache

# Eliminar archivos de compilación
Remove-Item -Recurse -Force *.pyc
```

---

## 📚 Endpoints

### Health Check ❤️

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/` | Health check básico |
| `GET` | `/health` | Health check detallado |

**Ejemplo:**
```bash
curl http://localhost:8000/health
```

### Históricos 📊

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/historicos/mnemonics` | Lista de acciones disponibles |
| `GET` | `/api/historicos/{mnemonic}` | Datos históricos con filtros |
| `GET` | `/api/historicos/{mnemonic}/{date}` | Dato de fecha específica |

**Ejemplos:**

```bash
# Listar mnemonics disponibles
curl http://localhost:8000/api/historicos/mnemonics

# Obtener datos de ECOPETROL
curl "http://localhost:8000/api/historicos/ecopetrol"

# Filtrar por rango de fechas
curl "http://localhost:8000/api/historicos/ecopetrol?desde=2024-01-01&hasta=2024-12-31&limit=100"

# Obtener dato de fecha específica
curl http://localhost:8000/api/historicos/ecopetrol/2024-01-15
```

### Análisis 📈

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/analisis/ordenamiento` | Benchmarking de 12 algoritmos |
| `GET` | `/api/analisis/info` | Info de algoritmos soportados |

**Ejemplos:**

```bash
# Ejecutar análisis completo
curl http://localhost:8000/api/analisis/ordenamiento

# Con límite de registros
curl "http://localhost:8000/api/analisis/ordenamiento?max_registros=5000"

# Incluir dataset ordenado en respuesta
curl "http://localhost:8000/api/analisis/ordenamiento?incluir_dataset_ordenado=true"

# Ver algoritmos soportados
curl http://localhost:8000/api/analisis/info
```

---

## 🏗️ Estructura del Proyecto

```
Nexvest-Back-FASTAPI/
├── main.py                    # 🚀 Punto de entrada de la aplicación
├── database.py                # 🗄️ Configuración de MongoDB
├── requirements.txt           # 📦 Dependencias del proyecto
│
├── routers/                   # 🛣️ Endpoints de la API
│   ├── __init__.py           # Inicializador del módulo
│   ├── historicos.py         # Endpoints de datos históricos
│   └── analisis.py           # Endpoints de análisis
│
├── algorithms/                # 🧮 Algoritmos personalizados
│   ├── __init__.py
│   ├── desempeno.py          # Medición de rendimiento
│   ├── algoritmos_ordenamiento.py  # Implementaciones de algoritmos
│   └── euclidean.py, pearson.py... # Otros algoritmos
│
├── etl/                       # 📥 Pipeline de datos
│   ├── historicos/           # Datos históricos (JSON)
│   ├── storage.py            # Almacenamiento en MongoDB
│   └── resultados_analisis/  # Salida de análisis
│
├── .env.example               # 📋 Template de variables
├── .gitignore                 # Git ignore patterns
├── README.md                  # 📖 Este archivo
└── vercel.json               # ⚡ Config Vercel serverless
```

### Directorios Importantes

| Directorio | Propósito |
|-----------|----------|
| `/routers` | Endpoints de la API REST |
| `/algorithms` | Algoritmos de análisis (implementados desde cero) |
| `/etl` | Datos históricos y resultados de análisis |
| `/etl/historicos` | JSON con datos de acciones BVC |
| `/etl/resultados_analisis` | Salida de benchmarks (JSON + PNG) |

---

## 🔐 Variables de Entorno

### Requeridas

```env
MONGO_URI=mongodb+srv://usuario:contraseña@host/
```

**Formato:**
```
mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
```

### Opcionales

```env
MONGO_DB_NAME=nexvest          # Default: nexvest
VERCEL=1                        # Auto-detectado en Vercel
```

### Cómo obtener MONGO_URI

1. Registrate en [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Crea un cluster gratuito (M0)
3. En "Database" → "Connect" → "Connect your application"
4. Copia la connection string
5. Reemplaza credenciales y pega en `.env`

---

## 📚 Documentación

Una vez que levantes el servidor, accede a:

| Recurso | URL |
|---------|-----|
| **Swagger UI** | http://localhost:8000/docs |
| **ReDoc** | http://localhost:8000/redoc |
| **OpenAPI JSON** | http://localhost:8000/openapi.json |

La documentación es **interactiva** y generada automáticamente desde el código.

### Explorar API desde Swagger

1. Ve a http://localhost:8000/docs
2. Haz clic en cualquier endpoint
3. Haz clic en "Try it out"
4. Modifica parámetros y "Execute"

---

## 📋 Stack Técnico

### Backend

| Tecnología | Versión | Propósito |
|-----------|---------|----------|
| **FastAPI** | 0.109.0 | Framework web async |
| **Uvicorn** | 0.27.0 | ASGI server |
| **Pydantic** | 2.5.3 | Validación de datos |
| **pymongo** | 4.6.1 | Cliente MongoDB |
| **python-dotenv** | 1.0.0 | Manejo de .env |
| **matplotlib** | 3.9.2 | Generación de gráficos |
| **requests** | 2.31.0 | HTTP client |

### Almacenamiento

| Servicio | Rol |
|----------|-----|
| **MongoDB Atlas** | Base de datos en la nube |
| **JSON Files** | Datos históricos locales |

### Deployment

| Plataforma | Soporte |
|----------|---------|
| **Vercel** | ✅ Serverless function |
| **Docker** | ✅ Containerización |
| **Local** | ✅ Desarrollo |

---

## 🤝 Contribución

¡Contribuciones son bienvenidas! 🎉

### Pasos para Contribuir

1. **Fork** el repositorio
   ```bash
   git clone https://github.com/tu-usuario/Nexvest-Back-FASTAPI.git
   cd Nexvest-Back-FASTAPI
   ```

2. **Crear rama** para tu feature
   ```bash
   git checkout -b feature/mi-feature
   ```

3. **Hacer cambios** y commits
   ```bash
   git add .
   git commit -m "feat: Agregar mi feature"
   ```

4. **Push a tu fork**
   ```bash
   git push origin feature/mi-feature
   ```

5. **Crear Pull Request** en GitHub

### Estándares de Código

- ✅ Seguir [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- ✅ Type hints en todas las funciones
- ✅ Docstrings completos
- ✅ Tests para nueva funcionalidad
- ✅ Commits descriptivos

---

## 🐛 Troubleshooting

### Error: `pydantic-core` no compila

**Problema:** Rust no está instalado
```
error: Cargo, the Rust package manager, is not installed
```

**Solución:**
```bash
# Opción 1: Instalar Rust
Invoke-WebRequest -Uri https://win.rustup.rs -UseBasicParsing -OutFile rustup-init.exe
.\rustup-init.exe -y

# Opción 2: Usar wheels precompilados
pip install --prefer-binary -r requirements.txt
```

### Error: `MONGO_URI not set`

**Problema:** Variable de entorno no configurada
```
EnvironmentError: MONGO_URI is not set
```

**Solución:**
```bash
# Crear .env con tu MONGO_URI
cp .env.example .env
# Editar .env y agregar: MONGO_URI=mongodb+srv://...
```

### Error: Módulo no encontrado

**Problema:** Dependencias no instaladas
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solución:**
```bash
pip install --upgrade pip
pip install -r requirements.txt --prefer-binary
```

### Puerto 8000 ya está en uso

**Problema:** Otro proceso usa el puerto
```
OSError: [Errno 48] Address already in use
```

**Solución:**
```bash
# Usar puerto diferente
python -m uvicorn main:app --reload --port 8001
```

---

## 📞 Soporte

- 📧 **Email:** desarrollo@nexvest.com
- 🐦 **Twitter:** @NexVestAPI
- 💬 **Issues:** [GitHub Issues](https://github.com/tu-usuario/Nexvest-Back-FASTAPI/issues)
- 📖 **Docs:** [Wiki](https://github.com/tu-usuario/Nexvest-Back-FASTAPI/wiki)

---

## 📄 Licencia

Este proyecto está bajo la licencia **MIT**. Ver [LICENSE](LICENSE) para más detalles.

```
MIT License

Copyright (c) 2024 NexVest Development Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software...
```

---

## 🎯 Roadmap

### Próximas Características

- [ ] 🔐 Autenticación JWT
- [ ] 📊 Nuevos algoritmos de análisis
- [ ] 🧪 Suite de tests completa
- [ ] 🐳 Docker compose
- [ ] 📱 API mobile
- [ ] 🤖 Machine Learning predictions
- [ ] 📈 WebSockets en tiempo real

---

<div align="center">

### ⭐ Si te es útil, no olvides dar una estrella!

[![GitHub stars](https://img.shields.io/github/stars/tu-usuario/Nexvest-Back-FASTAPI?style=social)](https://github.com/tu-usuario/Nexvest-Back-FASTAPI)
[![GitHub forks](https://img.shields.io/github/forks/tu-usuario/Nexvest-Back-FASTAPI?style=social)](https://github.com/tu-usuario/Nexvest-Back-FASTAPI/fork)

**Hecho con ❤️ por el equipo NexVest**

---

Last Updated: March 2024 | Version: 1.0.0

</div>
