"""
Archivo Diseño Latinoamericano — Backend Flask
API REST para gestión de productos, upload de Excel y sync con Claude
"""

import json
import os
import re
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent.parent
DATA_FILE  = BASE_DIR / "data" / "products.json"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder=str(BASE_DIR / "static"))
CORS(app)

# ── Utilidades de datos ───────────────────────────────────────────────────────
def load_data() -> list[dict]:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return list(DEFAULT_PRODUCTS)

def save_data(products: list[dict]):
    DATA_FILE.parent.mkdir(exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

def next_id(products: list[dict]) -> int:
    return max((p.get("id", 0) for p in products), default=0) + 1

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text)

# ── Dataset inicial ───────────────────────────────────────────────────────────
DEFAULT_PRODUCTS = [
    {"id":1,"name":"Estantería Unilabor","country":"Brasil","decade":"50-60","industry":"Metalmecánica","type":"Mobiliario","material":"Metal","designer":"Geraldo de Barros","company":"Unilabor","desc":"Estantería surgida de una cooperativa de trabajo autogestionada. Para Geraldo de Barros, las relaciones sociales de producción debían dar forma al objeto, no solo la función.","awards":"","impact":"Modelo de diseño cooperativista en Brasil, fusión arte-industria.","color":"#D4C5A9"},
    {"id":2,"name":"Línea Hobjeto","country":"Brasil","decade":"60-70","industry":"Metalmecánica","type":"Mobiliario","material":"Metal / Formica","designer":"Geraldo de Barros","company":"Hobjeto","desc":"Post-Unilabor, conserva lenguaje constructivo. De Barros diseñó líneas industriales hasta 1989.","awards":"","impact":"Continuidad del lenguaje constructivo brasileño en producción industrial.","color":"#B5C4B1"},
    {"id":3,"name":"Silla Favela","country":"Brasil","decade":"90-00","industry":"Madera","type":"Mobiliario","material":"Madera de desecho","designer":"Fernando y Humberto Campana","company":"Edra","desc":"Sillón de residuos de madera. Las piezas se unen artesanalmente. Representa las carencias materiales de las favelas.","awards":"Ícono del diseño crítico latinoamericano","impact":"Referente mundial del diseño de autor latinoamericano.","color":"#C8A882"},
    {"id":4,"name":"El Cherito","country":"El Salvador","decade":"60-70","industry":"Automotriz","type":"Transporte","material":"Acero / Fibra de vidrio","designer":"Ing. Francisco Rodríguez Ruiz","company":"Fábrica Superior de Centroamérica","desc":"Automóvil para el ambiente semi-rústico salvadoreño. Piezas fabricadas localmente excepto motor y caja (GM).","awards":"","impact":"Primer intento automotriz centroamericano de producción local.","color":"#D4A96A"},
    {"id":5,"name":"Los Vulcanizados","country":"El Salvador","decade":"60-70","industry":"Calzado","type":"Calzado","material":"Cuero / Sintéticos","designer":"Don Roberto Palomo","company":"Doc","desc":"Calzado fuerte para trabajo de campo. Cuero genuino con forros sintéticos de alta calidad.","awards":"","impact":"Referente del calzado industrial en Soyapango.","color":"#8B6F47"},
    {"id":6,"name":"Sillón Ovejo","country":"Colombia","decade":"70-80","industry":"Madera","type":"Mobiliario","material":"Piel de ovejo / Cuero / Madera","designer":"Jaime Gutiérrez Lega","company":"Gercol","desc":"Inspirado en Villa de Leyva. Fabricado con piel de ovejo, tiras de correa y cilindros de madera.","awards":"Mención de honor CIDEM","impact":"Síntesis de paisaje rural colombiano en objeto de diseño.","color":"#C4A882"},
    {"id":7,"name":"Jarros de aluminio Imusa","country":"Colombia","decade":"50-60","industry":"Metalmecánica","type":"Utensilios","material":"Aluminio","designer":"—","company":"Imusa","desc":"Democratizaron la cocina colombiana reemplazando recipientes de barro por aluminio accesible.","awards":"","impact":"Transformación de la cultura material doméstica colombiana.","color":"#B8C4C8"},
    {"id":8,"name":"Bus Halcón CM-580","country":"Colombia","decade":"80-90","industry":"Automotriz","type":"Transporte","material":"Fibra de vidrio / Acero","designer":"Jorge Montaña y Mauricio Mejía","company":"Colcar","desc":"Primer colectivo colombiano con baño y estructura de fibra de vidrio.","awards":"","impact":"Referente en transporte público con innovación técnica.","color":"#A8B4C0"},
    {"id":9,"name":"Silla Mariposa","country":"Colombia","decade":"90-00","industry":"Plástica","type":"Mobiliario","material":"Metal / Plástico inyectado","designer":"Oscar Muñoz","company":"Muma","desc":"Primera silla metal-plástico inyectada en Colombia. Equilibra ligereza y funcionalidad.","awards":"","impact":"Innovación técnica en manufactura colombiana.","color":"#C4B8D4"},
    {"id":10,"name":"Cabinas telefónicas","country":"Colombia","decade":"60-70","industry":"Metalmecánica","type":"Mobiliario urbano","material":"Plástico / Metal","designer":"Jaime Gutiérrez Lega","company":"ETB","desc":"Diseñadas para la visita del Papa Paulo VI (1968). Forma de burbuja esférica, símbolo de modernización urbana.","awards":"","impact":"Ícono del diseño urbano moderno en Colombia.","color":"#B4C8B4"},
    {"id":11,"name":"Mateo's Crib","country":"Colombia","decade":"90-00","industry":"Madera","type":"Mobiliario","material":"Madera laminada","designer":"Alberto Mantilla","company":"—","desc":"Cuna premiada internacionalmente. Time magazine la incluyó en Best of 1997.","awards":"Premio IDSA oro · Time Best of 1997","impact":"Proyección internacional del diseño colombiano.","color":"#D4C8A8"},
    {"id":12,"name":"Sombrero Panamá","country":"Ecuador","decade":"50-60","industry":"Artesanal","type":"Indumentaria","material":"Fibra de paja toquilla","designer":"Artesanos serranos","company":"Serrano Hat / Chordeleg","desc":"Tejido con fibras de palmera toquillal. Representó el 22% de las exportaciones ecuatorianas en 1945.","awards":"Patrimonio UNESCO","impact":"El producto artesanal más exportado de Ecuador.","color":"#E8D4A0"},
    {"id":13,"name":"Auto Cóndor","country":"Ecuador","decade":"70-80","industry":"Automotriz","type":"Transporte","material":"Fibra de vidrio","designer":"—","company":"Aymesa","desc":"Producido bajo políticas ISI. Carrocería de fibra de vidrio. Símbolo de la industrialización ecuatoriana.","awards":"","impact":"Primer automóvil ecuatoriano. Fruto de la sustitución de importaciones.","color":"#C8B89A"},
    {"id":14,"name":"Silla Miro","country":"Ecuador","decade":"80-90","industry":"Metalmecánica","type":"Mobiliario","material":"Metal","designer":"Rodney Verdezoto","company":"ATU","desc":"Inspirada en 'Personajes y perro ante el sol' de Joan Miró (1928). Síntesis diseño-arte.","awards":"","impact":"Síntesis de diseño-arte en producción industrial ecuatoriana.","color":"#B4C4D4"},
    {"id":15,"name":"Sillón Euforia","country":"Ecuador","decade":"90-00","industry":"Metalmecánica","type":"Mobiliario","material":"Metal / Tejido","designer":"Raúl Guarderas","company":"ATU","desc":"Primer sillón con sistema ergonómico activo en Latinoamérica. ATU exportó desde 1992.","awards":"","impact":"Pionero en ergonomía activa en oficina latinoamericana.","color":"#A8C4B8"},
    {"id":16,"name":"Sofá Excellence","country":"Ecuador","decade":"90-00","industry":"Metalmecánica","type":"Mobiliario","material":"Cuero / Madera laminada","designer":"Rodney Verdezoto","company":"ATU","desc":"Línea de sofás que sigue en venta. Apoyabrazos en madera laminada curvada, cuerpo revestido en cuero.","awards":"","impact":"Producto de exportación del diseño ecuatoriano.","color":"#C4A880"},
    {"id":17,"name":"Botas 7 Vidas","country":"Ecuador","decade":"70-80","industry":"Calzado","type":"Calzado","material":"PVC","designer":"—","company":"PICA","desc":"Primera gran industria de calzado de PVC en Ecuador. El nombre alude a la durabilidad de los gatos.","awards":"","impact":"Democratización del calzado resistente en Ecuador.","color":"#D4B894"},
    {"id":18,"name":"Línea Viva Indurama","country":"Ecuador","decade":"70-80","industry":"Electrodomésticos","type":"Electrodomésticos","material":"Metal / Plástico","designer":"—","company":"Indurama","desc":"Indurama nace en 1972 por emprendedores cuencanos. Ensamble de refrigeradores con licencia WCI-USA.","awards":"","impact":"Referente de electrodomésticos nacionales. Cuenca como polo industrial.","color":"#B8C4C0"},
    {"id":19,"name":"Bicicleta Mister","country":"Perú","decade":"70-80","industry":"Metalmecánica","type":"Transporte","material":"Metal","designer":"—","company":"INBISA","desc":"En contexto de crisis petrolera. Manubrio chopper y asiento banana. Símbolo generacional de los 70s.","awards":"","impact":"Símbolo generacional de la juventud peruana de los 70s.","color":"#C4B8A8"},
    {"id":20,"name":"Inca Kola","country":"Perú","decade":"50-60","industry":"Alimentos","type":"Envase","material":"Vidrio","designer":"—","company":"Lindley","desc":"Gaseosa con mayor número de ventas en Perú. Campaña que resalta símbolos y valores nacionales.","awards":"","impact":"Identidad nacional en envase. Resistió la presión de Coca-Cola.","color":"#E8D440"},
    {"id":21,"name":"Silla Canella","country":"Perú","decade":"90-00","industry":"Madera","type":"Mobiliario","material":"Madera","designer":"Alejandro Guerrero","company":"Canella Mobiliario","desc":"Mueble poliforme. Al alterar su posición se adapta a distintas necesidades del usuario.","awards":"1er puesto concurso Canella S.L. (España)","impact":"Diseño conceptual peruano con reconocimiento internacional.","color":"#C8B08C"},
    {"id":22,"name":"Casco Espacial Moraveco","country":"Perú","decade":"60-70","industry":"Plástica","type":"Juguete","material":"Plástico","designer":"Samuel Drassinower","company":"Moraveco","desc":"Apareció en plena carrera espacial. Moldes adaptados de máscaras de soldar.","awards":"","impact":"Industria juguetera nacional bajo restricciones de importación.","color":"#E0E4E8"},
    {"id":23,"name":"Grifería FV","country":"Ecuador","decade":"70-80","industry":"Metalmecánica","type":"Griferías","material":"Latón / Plástico cromado","designer":"Mario Arias","company":"FV","desc":"FV abre su primera fábrica en 1977. 40 toneladas/mes de latón. Empresa icónica en construcción.","awards":"","impact":"Referente nacional en griferías. Exportación regional.","color":"#C8CCD0"},
    {"id":24,"name":"Artículos PICA","country":"Ecuador","decade":"70-80","industry":"Plástica","type":"Juguetes","material":"Plástico inyectado","designer":"—","company":"PICA","desc":"PICA apuesta en 1975 por juguetes plásticos. Cicciobellos y otros productos consolidan la marca.","awards":"","impact":"PICA se convierte en referente del plástico inyectado en Ecuador.","color":"#D4C4B4"},
    {"id":25,"name":"Sanitarios Royal","country":"Colombia","decade":"60-70","industry":"Cerámica","type":"Sanitarios","material":"Cerámica / Porcelana","designer":"—","company":"Corona","desc":"Corona fundada en 1881. Los Royal se siguen produciendo. Su morfología se volvió estándar nacional.","awards":"","impact":"Estándar del sanitario colombiano. Corona como empresa nacional icónica.","color":"#E8E4DC"},
]

# Inicializar archivo si no existe
if not DATA_FILE.exists():
    save_data(list(DEFAULT_PRODUCTS))

# ── RUTAS: Productos ──────────────────────────────────────────────────────────

@app.route("/api/products", methods=["GET"])
def get_products():
    """Lista completa con filtros opcionales."""
    products = load_data()
    q = request.args.get("q", "").lower()
    country = request.args.get("country", "")
    decade = request.args.get("decade", "")
    industry = request.args.get("industry", "")

    if q:
        products = [p for p in products if q in p.get("name","").lower()
                    or q in p.get("designer","").lower()
                    or q in p.get("desc","").lower()
                    or q in p.get("company","").lower()]
    if country:
        products = [p for p in products if p.get("country") == country]
    if decade:
        products = [p for p in products if p.get("decade","").startswith(decade)]
    if industry:
        products = [p for p in products if p.get("industry") == industry
                    or p.get("type") == industry]

    return jsonify({"total": len(products), "products": products})


@app.route("/api/products/<int:pid>", methods=["GET"])
def get_product(pid):
    products = load_data()
    p = next((x for x in products if x["id"] == pid), None)
    if not p:
        return jsonify({"error": "Not found"}), 404
    return jsonify(p)


@app.route("/api/products", methods=["POST"])
def create_product():
    products = load_data()
    data = request.get_json(force=True)
    if not data.get("name"):
        return jsonify({"error": "name requerido"}), 400
    data["id"] = next_id(products)
    data.setdefault("color", "#C8C0B4")
    data["created_at"] = datetime.utcnow().isoformat()
    products.append(data)
    save_data(products)
    return jsonify(data), 201


@app.route("/api/products/<int:pid>", methods=["PUT"])
def update_product(pid):
    products = load_data()
    idx = next((i for i, p in enumerate(products) if p["id"] == pid), None)
    if idx is None:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json(force=True)
    data["id"] = pid
    data["updated_at"] = datetime.utcnow().isoformat()
    products[idx] = data
    save_data(products)
    return jsonify(data)


@app.route("/api/products/<int:pid>", methods=["DELETE"])
def delete_product(pid):
    products = load_data()
    new = [p for p in products if p["id"] != pid]
    if len(new) == len(products):
        return jsonify({"error": "Not found"}), 404
    save_data(new)
    return jsonify({"deleted": pid})


# ── RUTAS: Excel Upload ───────────────────────────────────────────────────────

EXCEL_COLUMN_MAP = {
    "país": "country",
    "pais": "country",
    "década": "decade",
    "decada": "decade",
    "producto": "name",
    "tipología de producto": "type",
    "tipologia": "type",
    "tipología": "type",
    "industria": "industry",
    "diseñador": "designer",
    "disenador": "designer",
    "empresa": "company",
    "análisis de producto": "desc",
    "analisis de producto": "desc",
    "análisis": "desc",
    "analisis": "desc",
    "material": "material",
    "premios": "awards",
    "impacto en territorio": "impact",
    "impacto": "impact",
    "masividad": "masividad",
    "marco teórico expandido": "marco_teorico",
    "marco teorico": "marco_teorico",
    "región": "region",
    "region": "region",
    "gini": "gini",
    "políticas de industrialización": "politicas",
    "politicas": "politicas",
}

@app.route("/api/upload/excel", methods=["POST"])
def upload_excel():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if not file.filename.endswith((".xlsx", ".xls", ".csv")):
        return jsonify({"error": "Formato no soportado. Usá .xlsx, .xls o .csv"}), 400

    filename = f"{uuid.uuid4().hex}_{file.filename}"
    path = UPLOAD_DIR / filename
    file.save(str(path))

    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(str(path))
        else:
            df = pd.read_excel(str(path))

        # Normalizar encabezados
        df.columns = [str(c).strip().lower() for c in df.columns]

        # Detectar columnas reconocidas
        detected = {}
        unknown = []
        for col in df.columns:
            if col in EXCEL_COLUMN_MAP:
                detected[col] = EXCEL_COLUMN_MAP[col]
            else:
                unknown.append(col)

        # Construir preview (primeras 5 filas)
        preview = []
        products_to_import = []
        existing = load_data()
        new_id = next_id(existing)

        for _, row in df.iterrows():
            product = {"id": new_id, "color": "#C8C0B4"}
            new_id += 1
            for raw_col, mapped in detected.items():
                val = row.get(raw_col, "")
                product[mapped] = "" if pd.isna(val) else str(val).strip()
            product.setdefault("name", product.get("name", f"Producto {new_id}"))
            products_to_import.append(product)
            if len(preview) < 5:
                preview.append(product)

        return jsonify({
            "filename": file.filename,
            "rows": len(df),
            "detected_columns": detected,
            "unknown_columns": unknown,
            "preview": preview,
            "import_ready": products_to_import,
            "temp_file": filename
        })

    except Exception as e:
        return jsonify({"error": f"Error procesando archivo: {str(e)}"}), 500


@app.route("/api/upload/confirm", methods=["POST"])
def confirm_import():
    """Confirma la importación masiva desde Excel."""
    data = request.get_json(force=True)
    products_to_import = data.get("products", [])
    mode = data.get("mode", "append")  # append | replace

    if not products_to_import:
        return jsonify({"error": "No hay productos para importar"}), 400

    existing = load_data()
    if mode == "replace":
        new_list = products_to_import
    else:
        max_id = next_id(existing)
        for i, p in enumerate(products_to_import):
            p["id"] = max_id + i
        new_list = existing + products_to_import

    save_data(new_list)
    return jsonify({
        "imported": len(products_to_import),
        "total": len(new_list),
        "mode": mode
    })


# ── RUTAS: Metadata ───────────────────────────────────────────────────────────

@app.route("/api/meta", methods=["GET"])
def get_meta():
    products = load_data()
    countries = sorted(set(p.get("country","") for p in products if p.get("country")))
    decades   = sorted(set(p.get("decade","")  for p in products if p.get("decade")))
    industries= sorted(set(p.get("industry","") for p in products if p.get("industry")))
    types     = sorted(set(p.get("type","")    for p in products if p.get("type")))
    return jsonify({
        "total": len(products),
        "countries": countries,
        "decades": decades,
        "industries": industries,
        "types": types,
    })


@app.route("/api/stats", methods=["GET"])
def get_stats():
    products = load_data()
    by_country  = {}
    by_industry = {}
    by_decade   = {}
    for p in products:
        by_country[p.get("country","?")] = by_country.get(p.get("country","?"),0)+1
        by_industry[p.get("industry","?")] = by_industry.get(p.get("industry","?"),0)+1
        by_decade[p.get("decade","?")] = by_decade.get(p.get("decade","?"),0)+1
    return jsonify({
        "total": len(products),
        "by_country": by_country,
        "by_industry": by_industry,
        "by_decade": by_decade,
    })


# ── RUTAS: Export ─────────────────────────────────────────────────────────────

@app.route("/api/export/json", methods=["GET"])
def export_json():
    products = load_data()
    from flask import Response
    return Response(
        json.dumps(products, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment;filename=archivo_diseno.json"}
    )


@app.route("/api/export/excel", methods=["GET"])
def export_excel():
    import io
    products = load_data()
    df = pd.DataFrame(products)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Productos")
    buf.seek(0)
    from flask import send_file
    return send_file(
        buf,
        as_attachment=True,
        download_name="archivo_diseno.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ── RUTAS: Static / Admin ─────────────────────────────────────────────────────

@app.route("/")
def serve_admin():
    static_dir = BASE_DIR / "static"
    return send_from_directory(str(static_dir), "admin.html")


@app.route("/health")
def health():
    products = load_data()
    return jsonify({"status": "ok", "products": len(products), "time": datetime.utcnow().isoformat()})


if __name__ == "__main__":
    print("\n──────────────────────────────────────────")
    print("  Archivo Diseño Latinoamericano — API")
    print("  http://localhost:5000")
    print("  Admin: http://localhost:5000/")
    print("──────────────────────────────────────────\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
