from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient

app = Flask(__name__)

MONGO_URI = "mongodb+srv://chinopacas:123@prueba.soxywwh.mongodb.net/?retryWrites=true&w=majority&appName=prueba"

# Conexión a MongoDB local
client = MongoClient(MONGO_URI)
db = client["cien_anos_soledad"]  # Tu base de datos

# Colecciones disponibles
colecciones = {
    "eventos": db["eventos"],
    "familias": db["familias"],
    "lugares": db["lugares"],
    "magia": db["magia"],
    "personajes": db["personajes"]
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/buscar")
def buscar():
    categoria = request.args.get("categoria")
    q = request.args.get("q", "").lower()
    resultados = []

    if categoria in colecciones:
        cursor = colecciones[categoria].find({
            "nombre": {"$regex": q, "$options": "i"}
        })
        resultados = [doc["nombre"] for doc in cursor if "nombre" in doc]

    return jsonify({"resultados": resultados})

if __name__ == "__main__":
    app.run(debug=True)
