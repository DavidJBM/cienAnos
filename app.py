# ======================
# IMPORTACIÓN DE MÓDULOS
# ======================
from flask import Flask, render_template, request, jsonify
import re
from pymongo import MongoClient
from bson import ObjectId
import ast 

# ======================
# CONFIGURACIÓN DE FLASK
# ======================
app = Flask(__name__)

# ======================
# CONFIGURACIÓN DE MONGODB
# ======================
MONGO_URI = "mongodb+srv://chinopacas:123@prueba.soxywwh.mongodb.net/?retryWrites=true&w=majority&appName=prueba"
client = MongoClient(MONGO_URI)
db = client["cien_anos_soledad"]  

# Mapeo de colecciones
colecciones = {
    "eventos": db["eventos"],     
    "familias": db["familias"],     
    "lugares": db["lugares"],       
    "magia": db["magia"],           
    "personajes": db["personajes"]  
}

def obtener_nombre(coleccion, _id):
    """
    Recupera el campo 'nombre' de un documento en la colección especificada.
    
    Parámetros:
        coleccion (str): Nombre de la colección objetivo
        _id (str): ID del documento en formato string
    
    Retorna:
        str: Nombre del documento o "Desconocido" si no se encuentra
    """
    try:
        doc = db[coleccion].find_one({"_id": ObjectId(_id)})
        return doc["nombre"] if doc and "nombre" in doc else "Desconocido"
    except Exception:
        return "Desconocido"

def obtener_nombres(coleccion, ids):
    """
    Transforma una lista de IDs de documentos a sus nombres correspondientes.
    
    Parámetros:
        coleccion (str): Nombre de la colección objetivo
        ids (list): Lista de IDs de documentos
    
    Retorna:
        list: Lista de nombres o ["Desconocido"] si no hay coincidencias
    """
    nombres = []
    for _id in ids:
        try:
            nombre = obtener_nombre(coleccion, _id)
            nombres.append(nombre)
        except Exception:
            continue
    return nombres if nombres else ["Desconocido"]

def serializar_documento(doc):
    """
    Estandariza documentos MongoDB para serialización JSON:
    - Convierte ObjectId a strings
    - Procesa referencias anidadas
    
    Parámetros:
        doc (dict): Documento MongoDB crudo
    
    Retorna:
        dict: Documento preparado para respuesta JSON
    """
    doc["_id"] = str(doc["_id"])
    for key in doc:
        if isinstance(doc[key], ObjectId):
            doc[key] = str(doc[key])
        elif isinstance(doc[key], list):
            doc[key] = [str(i) if isinstance(i, ObjectId) else i for i in doc[key]]
    return doc

@app.route("/")  
def index():
    """
    Endpoint raiz
    Sirve la interfaz principal de la aplicación.
    
    Retorna:
        HTML: Plantilla renderizada para el frontend
    """
    return render_template("index.html")

@app.route("/buscar")
def buscar():
    """
    ENDPOINT DE BÚSQUEDA AVANZADA
    ------------------------------
    Realiza búsquedas en las colecciones con capacidad para:
    - Búsqueda simple por nombre
    - Filtros especiales por capítulo, generación o importancia
    - Resolución automática de relaciones entre documentos
    """
    
    # Obtener parámetros de la URL
    categoria = request.args.get("categoria")  # Nombre de la colección a buscar
    consulta = request.args.get("q", "").strip().lower()  # Término de búsqueda (normalizado a minúsculas)
    resultados = []  # Lista para almacenar los resultados

    # Validar que la categoría exista
    if categoria not in colecciones:
        return jsonify({"resultados": []})  # Retorna lista vacía si la categoría no existe

    # Preparar filtro de búsqueda
    filtro = {}

    # --- SECCIÓN DE INTERPRETACIÓN DE LA CONSULTA ---
    if consulta:
        # 1. Búsqueda por capítulo 
        if re.search(r'cap[íi]tulo\s*(\d+)', consulta):
            cap = re.search(r'cap[íi]tulo\s*(\d+)', consulta).group(1)
            filtro["capitulo"] = int(cap)  # Convertir a número entero
            
        # 2. Búsqueda por generación 
        elif re.search(r'generaci[oó]n\s*(\d+)', consulta):
            gen = re.search(r'generaci[oó]n\s*(\d+)', consulta).group(1)
            filtro["generacion"] = gen
            
        # 3. Búsqueda por importancia (alta/media/baja)
        elif re.search(r'importancia\s*(alta|media|baja)', consulta):
            imp = re.search(r'importancia\s*(alta|media|baja)', consulta).group(1).capitalize()
            filtro["importancia"] = imp
            
        # 4. Búsqueda por nombre 
        else:
            filtro["nombre"] = {"$regex": consulta, "$options": "i"}  # Búsqueda case-insensitive

    # --- SECCIÓN DE EJECUCIÓN DE LA BÚSQUEDA ---
    for doc in colecciones[categoria].find(filtro):
        # Convertir ObjectId a string
        doc["_id"] = str(doc["_id"])

        # --- RESOLUCIÓN DE RELACIONES ---
        # Para eventos: resolver lugar y personajes
        if categoria == "eventos":
            if "lugar" in doc:
                doc["lugar"] = obtener_nombre("lugares", doc["lugar"])
            if "personajes_involucrados" in doc:
                doc["personajes_involucrados"] = obtener_nombres("personajes", doc["personajes_involucrados"])
                
        # Para familias: resolver parejas e hijos
        elif categoria == "familias":
            if "parejas" in doc:
                doc["parejas"] = obtener_nombres("personajes", doc["parejas"])
            if "hijos" in doc:
                doc["hijos"] = obtener_nombres("personajes", doc["hijos"])
                
        # Para magia: resolver personajes y eventos relacionados
        elif categoria == "magia":
            if "personajes_relacionados" in doc:
                doc["personajes_relacionados"] = obtener_nombres("personajes", doc["personajes_relacionados"])
            if "eventos_relacionados" in doc:
                doc["eventos_relacionados"] = obtener_nombres("eventos", doc["eventos_relacionados"])
                
        # Para lugares: resolver personajes relacionados
        elif categoria == "lugares":
            if "personajes_relacionados" in doc:
                doc["personajes_relacionados"] = obtener_nombres("personajes", doc["personajes_relacionados"])
                
        # Para otras colecciones: solo serializar
        else:
            doc = serializar_documento(doc)

        # Agregar documento procesado a resultados
        resultados.append(doc)

    # Retornar resultados en formato JSON
    return jsonify({"resultados": resultados})

@app.route("/eliminar", methods=["POST"])
def eliminar():
    """
    Elimina documentos de la colección especificada.
    
    JSON Esperado:
        - categoria: Colección objetivo
        - id: ID del documento a eliminar
    
    Retorna:
        JSON: Estado de la operación
    """
    data = request.get_json()
    categoria = data.get("categoria")
    doc_id = data.get("id")

    if categoria not in colecciones or not doc_id:
        return jsonify({"success": False, "error": "Datos inválidos"}), 400

    try:
        result = colecciones[categoria].delete_one({"_id": ObjectId(doc_id)})
        if result.deleted_count == 1:
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Documento no encontrado"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/editar", methods=["POST"])
def editar():
    """
    Modifica documentos existentes con nuevos datos.
    
    JSON Esperado:
        - categoria: Colección objetivo
        - id: ID del documento
        - datos: Nuevos valores
    
    Retorna:
        JSON: Estado de la operación
    """
    data = request.get_json()
    categoria = data.get("categoria")
    doc_id = data.get("id")
    nuevos_datos = data.get("datos", {})

    if categoria not in colecciones or not doc_id or not nuevos_datos:
        return jsonify({"success": False, "error": "Datos inválidos"}), 400

    # Conversión de listas en formato string
    for key, value in nuevos_datos.items():
        if isinstance(value, str) and value.startswith("[") and value.endswith("]"):
            try:
                nuevos_datos[key] = eval(value)
            except Exception:
                pass

    try:
        result = colecciones[categoria].update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": nuevos_datos}
        )
        if result.modified_count == 1:
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Documento no actualizado"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/insertar", methods=["POST"])
def insertar():
    """
    Crea nuevos documentos en la colección especificada.
    
    JSON Esperado:
        - categoria: Colección objetivo
        - datos: Contenido del documento
    
    Retorna:
        JSON: Estado de la operación con ID del nuevo documento
    """
    data = request.get_json()
    categoria = data.get("categoria")
    nuevo_doc = data.get("datos", {})

    if categoria not in colecciones or not nuevo_doc:
        return jsonify({"success": False, "error": "Datos inválidos"}), 400

    # Procesamiento de referencias ObjectId
    for key, value in nuevo_doc.items():
        if isinstance(value, str) and value.startswith("[") and value.endswith("]"):
            try:
                nuevo_doc[key] = ast.literal_eval(value)
            except Exception:
                pass

        if isinstance(nuevo_doc[key], list):
            nuevo_doc[key] = [ObjectId(i) if ObjectId.is_valid(i) else i for i in nuevo_doc[key]]
        elif isinstance(nuevo_doc[key], str) and ObjectId.is_valid(nuevo_doc[key]):
            nuevo_doc[key] = ObjectId(nuevo_doc[key])

    try:
        resultado = colecciones[categoria].insert_one(nuevo_doc)
        return jsonify({"success": True, "id": str(resultado.inserted_id)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
