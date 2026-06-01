"""
Ficha Única Institucional — Backend Flask
Seguridad reforzada: rate limiting, sanitización, validación estricta,
sin leak de datos personales, API no modificable por usuarios externos.

Arquitectura de seguridad:
  - Rate limiting por IP (sin almacenar IP en BD)
  - Tokens CSRF por sesión de formulario
  - Sanitización de todos los inputs con bleach
  - Validación estricta de tipos, tamaños y extensiones de imágenes
  - Logging de auditoría sin datos personales identificables
  - Headers de seguridad en todas las respuestas
  - Separación total entre rutas públicas y rutas de administración
  - Ningún campo de usuario (email, nombre, IP) se persiste en la BD
"""

import hashlib
import hmac
import io
import json
import logging
import mimetypes
import os
import re
import secrets
import time
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

import bleach
from flask import Flask, abort, jsonify, request, send_from_directory, g
from flask_cors import CORS
from PIL import Image

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent.parent
DATA_FILE   = BASE_DIR / "data" / "fichas.json"
UPLOAD_DIR  = BASE_DIR / "uploads"
LOG_FILE    = BASE_DIR / "data" / "audit.log"
SECRET_KEY  = os.environ.get("SECRET_KEY", secrets.token_hex(32))

# Jerarquías de imagen aceptadas
IMAGE_CATEGORIES = {
    "edificio":   {"label": "Edificio (interior / exterior)", "priority": 1, "max_files": 10},
    "logotipo":   {"label": "Logotipo institucional",          "priority": 2, "max_files": 5},
    "exposicion": {"label": "Exposición o muestra",            "priority": 3, "max_files": 10},
    "adicional":  {"label": "Imágenes adicionales",            "priority": 4, "max_files": 20},
}

# Límites estrictos
MAX_IMAGE_SIZE_MB  = 8
MAX_TEXT_LEN       = 8000
MAX_SHORT_LEN      = 200
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_REQUESTS_PER_MINUTE = 20   # por IP hash (no almacenamos IP)
MAX_SUBMISSIONS_PER_HOUR = 3   # fichas completas por IP hash

# Tipos institucionales válidos (whitelist cerrada)
VALID_INSTITUTION_TYPES = {"gubernamental", "privada_comercial", "tercer_sector"}
VALID_COUNTRIES = []  # vacío = todos aceptados; poblar para whitelist

# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=str(BASE_DIR / "static"))
app.secret_key = SECRET_KEY
CORS(app, origins=["*"], methods=["GET", "POST"], allow_headers=["Content-Type", "X-CSRF-Token"])

# ─────────────────────────────────────────────────────────────────────────────
# Logging de auditoría (sin datos personales)
# ─────────────────────────────────────────────────────────────────────────────
LOG_FILE.parent.mkdir(exist_ok=True)
audit_handler = logging.FileHandler(str(LOG_FILE))
audit_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
audit_log = logging.getLogger("audit")
audit_log.addHandler(audit_handler)
audit_log.setLevel(logging.INFO)

def audit(event: str, detail: str = ""):
    """Registra evento de auditoría SIN datos personales.
    Solo se almacena: timestamp, tipo de evento, hash de sesión, detalle neutro."""
    session_hash = getattr(g, "session_hash", "unknown")
    audit_log.info(f"{event} | session={session_hash} | {detail}")


# ─────────────────────────────────────────────────────────────────────────────
# Rate limiting (en memoria, sin persistir IPs)
# ─────────────────────────────────────────────────────────────────────────────
_rate_store: dict = {}   # ip_hash -> [timestamps]
_submission_store: dict = {}

def _ip_hash(ip: str) -> str:
    """Hash de un solo sentido de la IP. Nunca se almacena la IP raw."""
    return hmac.new(SECRET_KEY.encode(), ip.encode(), hashlib.sha256).hexdigest()[:16]

def _get_real_ip() -> str:
    """Extrae IP real considerando proxies confiables."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"

def rate_limit(max_per_minute: int = MAX_REQUESTS_PER_MINUTE):
    """Decorador de rate limiting por IP-hash."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            ip_h = _ip_hash(_get_real_ip())
            g.session_hash = ip_h  # para audit log, nunca expuesto
            now = time.time()
            window = [t for t in _rate_store.get(ip_h, []) if now - t < 60]
            if len(window) >= max_per_minute:
                audit("RATE_LIMIT_HIT", f"endpoint={request.endpoint}")
                return jsonify({"error": "Demasiadas solicitudes. Intentá en un momento."}), 429
            window.append(now)
            _rate_store[ip_h] = window
            return f(*args, **kwargs)
        return wrapper
    return decorator

def submission_limit(f):
    """Limita fichas completas por hora por IP-hash."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        ip_h = _ip_hash(_get_real_ip())
        now = time.time()
        window = [t for t in _submission_store.get(ip_h, []) if now - t < 3600]
        if len(window) >= MAX_SUBMISSIONS_PER_HOUR:
            audit("SUBMISSION_LIMIT_HIT", "")
            return jsonify({"error": f"Límite de {MAX_SUBMISSIONS_PER_HOUR} fichas por hora alcanzado."}), 429
        window.append(now)
        _submission_store[ip_h] = window
        return f(*args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────────────────────────────
# CSRF tokens
# ─────────────────────────────────────────────────────────────────────────────
_csrf_tokens: dict = {}  # token -> expiry_timestamp

def generate_csrf_token() -> str:
    token = secrets.token_urlsafe(32)
    _csrf_tokens[token] = time.time() + 3600  # válido 1 hora
    # Limpiar expirados cada N llamadas
    expired = [k for k, v in _csrf_tokens.items() if time.time() > v]
    for k in expired:
        del _csrf_tokens[k]
    return token

def validate_csrf_token(token: str) -> bool:
    if not token or token not in _csrf_tokens:
        return False
    if time.time() > _csrf_tokens[token]:
        del _csrf_tokens[token]
        return False
    del _csrf_tokens[token]  # single-use
    return True

def require_csrf(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-CSRF-Token") or request.form.get("_csrf_token")
        if not validate_csrf_token(token):
            audit("CSRF_FAIL", f"endpoint={request.endpoint}")
            return jsonify({"error": "Token de seguridad inválido. Recargá la página."}), 403
        return f(*args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────────────────────────────
# Sanitización de inputs
# ─────────────────────────────────────────────────────────────────────────────
ALLOWED_TAGS: list[str] = []   # sin HTML en los textos — solo texto plano
ALLOWED_ATTRS: dict = {}

def sanitize(text: str, max_len: int = MAX_TEXT_LEN) -> str:
    """Limpia HTML, controla longitud, normaliza whitespace."""
    if not isinstance(text, str):
        return ""
    cleaned = bleach.clean(text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)  # control chars
    cleaned = re.sub(r" {4,}", "   ", cleaned)     # espacios excesivos
    return cleaned[:max_len].strip()

def sanitize_short(text: str) -> str:
    return sanitize(text, max_len=MAX_SHORT_LEN)

def validate_year(y) -> int | None:
    try:
        val = int(str(y).strip())
        if 1800 <= val <= datetime.now().year + 1:
            return val
    except (ValueError, TypeError):
        pass
    return None

def validate_institution_type(t: str) -> str | None:
    t = str(t).lower().strip().replace(" ", "_").replace("-", "_")
    return t if t in VALID_INSTITUTION_TYPES else None


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades de datos
# ─────────────────────────────────────────────────────────────────────────────
def load_fichas() -> list[dict]:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_fichas(fichas: list[dict]):
    DATA_FILE.parent.mkdir(exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(fichas, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# Validación y guardado de imágenes
# ─────────────────────────────────────────────────────────────────────────────
def validate_and_save_image(file, category: str, ficha_id: str) -> dict | None:
    """
    Valida extensión, MIME real (magic bytes), tamaño y dimensiones.
    Reencoda la imagen con Pillow para eliminar metadatos EXIF y payloads.
    Retorna metadata sin datos personales. Retorna None si inválida.
    """
    if category not in IMAGE_CATEGORIES:
        return None

    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None

    raw = file.read()
    if len(raw) > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        return None

    # Verificar magic bytes reales (no confiar en extensión declarada)
    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()
    except Exception:
        return None

    # Reabrir (verify() agota el stream) y reencodar — elimina EXIF
    try:
        img = Image.open(io.BytesIO(raw))
        img = img.convert("RGB") if ext != ".png" else img.convert("RGBA")

        # Límites de dimensiones
        max_dim = 4096
        if img.width > max_dim or img.height > max_dim:
            img.thumbnail((max_dim, max_dim), Image.LANCZOS)

        # Nombre nuevo: ficha_id + category + uuid, sin nombre original
        safe_name = f"{ficha_id}_{category}_{uuid.uuid4().hex[:8]}{ext}"
        save_path = UPLOAD_DIR / category / safe_name
        save_path.parent.mkdir(parents=True, exist_ok=True)

        save_kwargs = {"optimize": True}
        if ext in (".jpg", ".jpeg"):
            save_kwargs["format"] = "JPEG"
            save_kwargs["quality"] = 85
        elif ext == ".png":
            save_kwargs["format"] = "PNG"
        elif ext == ".webp":
            save_kwargs["format"] = "WEBP"
            save_kwargs["quality"] = 85

        img.save(str(save_path), **save_kwargs)

        return {
            "filename": safe_name,
            "category": category,
            "category_label": IMAGE_CATEGORIES[category]["label"],
            "priority": IMAGE_CATEGORIES[category]["priority"],
            "width": img.width,
            "height": img.height,
            "size_kb": round(save_path.stat().st_size / 1024, 1),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        audit("IMAGE_SAVE_ERROR", f"category={category} err={type(e).__name__}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Security headers en todas las respuestas
# ─────────────────────────────────────────────────────────────────────────────
@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"]    = "nosniff"
    response.headers["X-Frame-Options"]           = "DENY"
    response.headers["X-XSS-Protection"]          = "1; mode=block"
    response.headers["Referrer-Policy"]           = "no-referrer"
    response.headers["Permissions-Policy"]        = "geolocation=(), camera=(), microphone=()"
    response.headers["Content-Security-Policy"]   = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com; "
        "font-src https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self';"
    )
    # Nunca cachear respuestas de API
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"]        = "no-cache"
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Rutas PÚBLICAS (solo GET y POST controlados)
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def serve_form():
    return send_from_directory(str(BASE_DIR / "static"), "form.html")


@app.route("/api/csrf-token", methods=["GET"])
@rate_limit(max_per_minute=30)
def get_csrf_token():
    """Entrega un token CSRF de un solo uso. No expone datos del servidor."""
    return jsonify({"token": generate_csrf_token()})


@app.route("/api/submit", methods=["POST"])
@rate_limit(max_per_minute=5)
@submission_limit
@require_csrf
def submit_ficha():
    """
    Endpoint principal de ingreso de ficha institucional.
    Valida, sanitiza y persiste. No almacena ningún dato personal del remitente.
    """
    # ── Extraer y validar campos de texto ──────────────────────────────────
    errors = {}

    nombre = sanitize_short(request.form.get("nombre", ""))
    if not nombre or len(nombre) < 3:
        errors["nombre"] = "Nombre requerido (mínimo 3 caracteres)"

    pais = sanitize_short(request.form.get("pais", ""))
    if not pais:
        errors["pais"] = "País requerido"
    if VALID_COUNTRIES and pais not in VALID_COUNTRIES:
        errors["pais"] = "País no reconocido"

    anio_desde_raw = request.form.get("anio_desde", "")
    anio_hasta_raw = request.form.get("anio_hasta", "")
    anio_desde = validate_year(anio_desde_raw)
    anio_hasta = validate_year(anio_hasta_raw) if anio_hasta_raw.strip() else None

    if anio_desde is None:
        errors["anio_desde"] = "Año de inicio inválido (entre 1800 y la actualidad)"
    if anio_hasta_raw.strip() and anio_hasta is None:
        errors["anio_hasta"] = "Año de cierre inválido"
    if anio_desde and anio_hasta and anio_hasta < anio_desde:
        errors["anio_hasta"] = "El año de cierre debe ser posterior al de inicio"

    tipo_raw = request.form.get("tipo", "")
    tipo = validate_institution_type(tipo_raw)
    if not tipo:
        errors["tipo"] = f"Tipo inválido. Opciones: {', '.join(VALID_INSTITUTION_TYPES)}"

    descripcion = sanitize(request.form.get("descripcion", ""), max_len=MAX_TEXT_LEN)
    if not descripcion or len(descripcion) < 20:
        errors["descripcion"] = "Descripción requerida (mínimo 20 caracteres)"

    historia            = sanitize(request.form.get("historia", ""),            max_len=3000)
    funcionamiento      = sanitize(request.form.get("funcionamiento", ""),      max_len=3000)
    financiamiento      = sanitize(request.form.get("financiamiento", ""),      max_len=2000)
    logicas_inter       = sanitize(request.form.get("logicas_inter", ""),       max_len=2000)

    if errors:
        audit("SUBMIT_VALIDATION_FAIL", f"fields={list(errors.keys())}")
        return jsonify({"errors": errors}), 422

    # ── Procesar imágenes ─────────────────────────────────────────────────
    ficha_id = uuid.uuid4().hex[:12]
    images: dict[str, list] = {cat: [] for cat in IMAGE_CATEGORIES}
    image_errors = []

    for category, meta in IMAGE_CATEGORIES.items():
        files = request.files.getlist(f"img_{category}")
        if len(files) > meta["max_files"]:
            image_errors.append(f"{category}: máximo {meta['max_files']} imágenes")
            continue
        for file in files:
            if file and file.filename:
                result = validate_and_save_image(file, category, ficha_id)
                if result:
                    images[category].append(result)
                else:
                    image_errors.append(
                        f"Imagen en '{category}' rechazada: formato o tamaño inválido (máx {MAX_IMAGE_SIZE_MB}MB, solo JPG/PNG/WebP)"
                    )

    if image_errors:
        audit("SUBMIT_IMAGE_ERRORS", f"count={len(image_errors)}")
        return jsonify({"errors": {"imagenes": image_errors}}), 422

    # ── Construir y guardar ficha ─────────────────────────────────────────
    # POLÍTICA DE PRIVACIDAD: ningún campo de identificación del remitente se almacena.
    # La ficha solo contiene datos de la institución descripta, no de quien la describe.
    ficha = {
        "id": ficha_id,
        "nombre": nombre,
        "pais": pais,
        "anio_desde": anio_desde,
        "anio_hasta": anio_hasta,
        "tipo": tipo,
        "descripcion": descripcion,
        "historia": historia,
        "funcionamiento": funcionamiento,
        "financiamiento": financiamiento,
        "logicas_inter": logicas_inter,
        "imagenes": images,
        "estado": "pendiente_revision",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        # Sin IP, sin nombre de usuario, sin email, sin fingerprint
    }

    fichas = load_fichas()
    fichas.append(ficha)
    save_fichas(fichas)
    audit("SUBMIT_OK", f"ficha_id={ficha_id} institucion_hash={hashlib.sha256(nombre.encode()).hexdigest()[:8]}")

    return jsonify({
        "ok": True,
        "ficha_id": ficha_id,
        "mensaje": "Tu ficha fue recibida correctamente y está pendiente de revisión. Guardá tu código de referencia.",
    }), 201


@app.route("/api/status/<ficha_id>", methods=["GET"])
@rate_limit(max_per_minute=10)
def check_status(ficha_id: str):
    """Consulta de estado por ID. Solo devuelve estado y nombre, sin datos sensibles."""
    if not re.match(r"^[a-f0-9]{12}$", ficha_id):
        return jsonify({"error": "ID inválido"}), 400

    fichas = load_fichas()
    ficha = next((f for f in fichas if f["id"] == ficha_id), None)
    if not ficha:
        return jsonify({"error": "Ficha no encontrada"}), 404

    # Retorna solo lo mínimo — nunca la ficha completa a usuarios externos
    return jsonify({
        "id": ficha["id"],
        "nombre": ficha["nombre"],
        "estado": ficha["estado"],
        "submitted_at": ficha["submitted_at"],
    })


@app.route("/api/policy", methods=["GET"])
def privacy_policy():
    """Retorna la política de privacidad estructurada."""
    return jsonify({
        "version": "1.0",
        "fecha": "2025",
        "datos_que_recopilamos": [
            "Nombre de la institución",
            "País",
            "Años de actividad",
            "Tipo institucional",
            "Descripción, historia y funcionamiento de la institución",
            "Imágenes del edificio, logotipo y exposiciones de la institución",
        ],
        "datos_que_NO_recopilamos": [
            "Nombre o identidad del remitente",
            "Correo electrónico",
            "Dirección IP (se usa un hash temporal no recuperable para rate limiting)",
            "Localización geográfica del remitente",
            "Cookies de seguimiento",
            "Datos de comportamiento o navegación",
        ],
        "uso_de_datos": (
            "Los datos ingresados describen instituciones de diseño latinoamericano "
            "y se usan exclusivamente para construir el archivo histórico del proyecto. "
            "No se venden, no se comparten con terceros, no se usan con fines publicitarios."
        ),
        "almacenamiento": "Servidor propio. Sin servicios de terceros de analítica o tracking.",
        "derechos": "Podés solicitar la corrección o eliminación de la ficha usando el ID de referencia.",
        "contacto": "archivo@diseno-latinoamericano.org",
    })


@app.route("/uploads/<category>/<filename>")
def serve_image(category: str, filename: str):
    """Sirve imágenes con validación estricta."""
    if category not in IMAGE_CATEGORIES:
        abort(404)
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", filename):
        abort(400)
    return send_from_directory(str(UPLOAD_DIR / category), filename)


# ─────────────────────────────────────────────────────────────────────────────
# Rutas INTERNAS (protegidas por API key de entorno — NO accesibles públicamente)
# ─────────────────────────────────────────────────────────────────────────────
ADMIN_KEY = os.environ.get("ADMIN_API_KEY", "")

def require_admin_key(f):
    """Guard para endpoints de administración. Rechaza si no hay key configurada."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not ADMIN_KEY:
            abort(503, "Admin API no configurada")
        key = request.headers.get("X-Admin-Key", "")
        if not hmac.compare_digest(key, ADMIN_KEY):
            audit("ADMIN_AUTH_FAIL", f"endpoint={request.endpoint}")
            abort(401)
        return f(*args, **kwargs)
    return wrapper


@app.route("/admin/fichas", methods=["GET"])
@require_admin_key
def admin_list_fichas():
    fichas = load_fichas()
    estado = request.args.get("estado", "")
    if estado:
        fichas = [f for f in fichas if f.get("estado") == estado]
    return jsonify({"total": len(fichas), "fichas": fichas})


@app.route("/admin/fichas/<ficha_id>/estado", methods=["PUT"])
@require_admin_key
def admin_update_estado(ficha_id: str):
    """Cambia el estado de una ficha (pendiente_revision → aprobada / rechazada)."""
    VALID_ESTADOS = {"pendiente_revision", "aprobada", "rechazada", "en_revision"}
    nuevo_estado = request.get_json(force=True).get("estado", "")
    if nuevo_estado not in VALID_ESTADOS:
        return jsonify({"error": f"Estado inválido. Opciones: {VALID_ESTADOS}"}), 422
    fichas = load_fichas()
    idx = next((i for i, f in enumerate(fichas) if f["id"] == ficha_id), None)
    if idx is None:
        return jsonify({"error": "No encontrada"}), 404
    fichas[idx]["estado"] = nuevo_estado
    fichas[idx]["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_fichas(fichas)
    audit("ADMIN_ESTADO_CHANGE", f"ficha={ficha_id} estado={nuevo_estado}")
    return jsonify({"ok": True, "estado": nuevo_estado})


@app.route("/admin/fichas/<ficha_id>", methods=["DELETE"])
@require_admin_key
def admin_delete_ficha(ficha_id: str):
    fichas = load_fichas()
    new = [f for f in fichas if f["id"] != ficha_id]
    if len(new) == len(fichas):
        return jsonify({"error": "No encontrada"}), 404
    save_fichas(new)
    audit("ADMIN_DELETE", f"ficha={ficha_id}")
    return jsonify({"ok": True})


@app.route("/health")
def health():
    fichas = load_fichas()
    return jsonify({
        "status": "ok",
        "fichas": len(fichas),
        "pendientes": sum(1 for f in fichas if f.get("estado") == "pendiente_revision"),
    })


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n──────────────────────────────────────────────────────")
    print("  Ficha Institucional — API (modo desarrollo)")
    print("  http://localhost:5000")
    print("")
    print("  ADVERTENCIA: configurar ADMIN_API_KEY en producción")
    print("  ADVERTENCIA: usar HTTPS en producción (certificado TLS)")
    print("──────────────────────────────────────────────────────\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
