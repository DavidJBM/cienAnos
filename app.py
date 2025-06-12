from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
import ast 

app = Flask(__name__)

# Conexión a MongoDB Atlas
MONGO_URI = "mongodb+srv://chinopacas:123@prueba.soxywwh.mongodb.net/?retryWrites=true&w=majority&appName=prueba"
client = MongoClient(MONGO_URI)
db = client["cien_anos_soledad"]

# Diccionario de colecciones
colecciones = {
    "eventos": db["eventos"],
    "familias": db["familias"],
    "lugares": db["lugares"],
    "magia": db["magia"],
    "personajes": db["personajes"]
}

# Función auxiliar para obtener nombre por ID
def obtener_nombre(coleccion, _id):
    try:
        doc = db[coleccion].find_one({"_id": ObjectId(_id)})
        return doc["nombre"] if doc and "nombre" in doc else "Desconocido"
    except:
        return "Desconocido"

# Función para convertir una lista de IDs a nombres
def obtener_nombres(coleccion, ids):
    nombres = []
    for _id in ids:
        try:
            nombre = obtener_nombre(coleccion, _id)
            nombres.append(nombre)
        except:
            continue
    return nombres if nombres else ["Desconocido"]

# Serializador base
def serializar_documento(doc):
    doc["_id"] = str(doc["_id"])
    for key in doc:
        if isinstance(doc[key], ObjectId):
            doc[key] = str(doc[key])
        elif isinstance(doc[key], list):
            doc[key] = [str(i) if isinstance(i, ObjectId) else i for i in doc[key]]
    return doc

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/buscar")
def buscar():
    categoria = request.args.get("categoria")
    q = request.args.get("q", "").strip().lower()
    resultados = []

    if categoria not in colecciones:
        return jsonify({"resultados": []})

    filtro = {"nombre": {"$regex": q, "$options": "i"}} if q else {}
    for doc in colecciones[categoria].find(filtro):
        doc["_id"] = str(doc["_id"])

        # EVENTOS
        if categoria == "eventos":
            if "lugar" in doc:
                doc["lugar"] = obtener_nombre("lugares", doc["lugar"])
            if "personajes_involucrados" in doc:
                doc["personajes_involucrados"] = obtener_nombres("personajes", doc["personajes_involucrados"])

        # FAMILIAS
        elif categoria == "familias":
            if "parejas" in doc:
                doc["parejas"] = obtener_nombres("personajes", doc["parejas"])
            if "hijos" in doc:
                doc["hijos"] = obtener_nombres("personajes", doc["hijos"])

        # MAGIA
        elif categoria == "magia":
            if "personajes_relacionados" in doc:
                doc["personajes_relacionados"] = obtener_nombres("personajes", doc["personajes_relacionados"])
            if "eventos_relacionados" in doc:
                doc["eventos_relacionados"] = obtener_nombres("eventos", doc["eventos_relacionados"])

        # LUGARES
        elif categoria == "lugares":
            if "personajes_relacionados" in doc:
                doc["personajes_relacionados"] = obtener_nombres("personajes", doc["personajes_relacionados"])

        else:
            doc = serializar_documento(doc)

        resultados.append(doc)

    return jsonify({"resultados": resultados})

@app.route("/eliminar", methods=["POST"])
def eliminar():
    data = request.get_json()
    categoria = data.get("categoria")
    doc_id = data.get("id")

    if categoria not in colecciones or not doc_id:
        return jsonify({"success": False, "error": "Datos inválidos"}), 400

    try:
        result = colecciones[categoria].delete_one({"_id": ObjectId(doc_id)})
        if result.deleted_count == 1:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "No se encontró el documento"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/editar", methods=["POST"])
def editar():
    data = request.get_json()
    categoria = data.get("categoria")
    doc_id = data.get("id")
    nuevos_datos = data.get("datos", {})

    if categoria not in colecciones or not doc_id or not nuevos_datos:
        return jsonify({"success": False, "error": "Datos inválidos"}), 400

    # Convierte listas de strings a listas si es necesario
    for k, v in nuevos_datos.items():
        if isinstance(v, str) and v.startswith("[") and v.endswith("]"):
            try:
                nuevos_datos[k] = eval(v)
            except:
                pass

    try:
        result = colecciones[categoria].update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": nuevos_datos}
        )
        if result.modified_count == 1:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "No se actualizó el documento"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/insertar", methods=["POST"])
def insertar():
    data = request.get_json()
    categoria = data.get("categoria")
    nuevo_doc = data.get("datos", {})

    if categoria not in colecciones or not nuevo_doc:
        return jsonify({"success": False, "error": "Datos inválidos"}), 400

    # Procesar campos tipo lista (ej. ["id1", "id2"]) y convertir a ObjectId si corresponde
    for k, v in nuevo_doc.items():
        # Convertir string tipo lista segura
        if isinstance(v, str) and v.startswith("[") and v.endswith("]"):
            try:
                nuevo_doc[k] = ast.literal_eval(v)
            except:
                pass

        # Convertir elementos a ObjectId si son candidatos
        if isinstance(nuevo_doc[k], list):
            nuevo_doc[k] = [ObjectId(i) if ObjectId.is_valid(i) else i for i in nuevo_doc[k]]
        elif isinstance(nuevo_doc[k], str) and ObjectId.is_valid(nuevo_doc[k]):
            nuevo_doc[k] = ObjectId(nuevo_doc[k])

    try:
        resultado = colecciones[categoria].insert_one(nuevo_doc)
        return jsonify({"success": True, "id": str(resultado.inserted_id)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
