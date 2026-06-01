# Archivo Diseño Latinoamericano — Backend

## Estructura

```
archivo-diseno/
├── backend/
│   └── app.py          # Flask API REST
├── static/
│   └── admin.html      # Panel de administración
├── data/
│   └── products.json   # Base de datos (auto-generada al iniciar)
├── uploads/            # Archivos Excel temporales
└── README.md
```

## Setup

```bash
# 1. Instalar dependencias
pip3 install flask flask-cors pandas openpyxl --break-system-packages

# 2. Levantar el servidor
cd backend
python3 app.py

# 3. Abrir admin
open http://localhost:5000
```

## API REST

| Método | Endpoint                  | Descripción                              |
|--------|---------------------------|------------------------------------------|
| GET    | /api/products             | Lista con filtros: q, country, decade    |
| GET    | /api/products/:id         | Detalle de un producto                   |
| POST   | /api/products             | Crear producto                           |
| PUT    | /api/products/:id         | Editar producto                          |
| DELETE | /api/products/:id         | Eliminar producto                        |
| GET    | /api/meta                 | Países, décadas, industrias disponibles  |
| GET    | /api/stats                | Estadísticas por país / industria        |
| POST   | /api/upload/excel         | Subir y analizar Excel                   |
| POST   | /api/upload/confirm       | Confirmar importación masiva             |
| GET    | /api/export/json          | Exportar colección completa (JSON)       |
| GET    | /api/export/excel         | Exportar colección completa (.xlsx)      |
| GET    | /health                   | Health check                             |

## Columnas del Excel detectadas automáticamente

País · Década · Producto · Tipología · Industria · Diseñador · Empresa
Análisis · Material · Premios · Impacto · Masividad · GINI · Políticas · Región

## Conectar el front-end público

En `static/admin.html`, la variable `const API = ''` usa mismo origen.
Para conectar el front-end del catálogo (el HTML de la plataforma pública),
cambiar la URL de fetch a `http://localhost:5000/api/products`.

## Deploy en producción

```bash
# Con gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 backend.app:app

# Variables de entorno opcionales
export FLASK_ENV=production
export DATA_FILE=/ruta/a/products.json
```
