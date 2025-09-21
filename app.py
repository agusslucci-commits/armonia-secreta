# app.py  — MÍNIMO FUNCIONAL PARA RENDER

from flask import Flask, request, jsonify
from flask_cors import CORS

# 1) crear la app ANTES de usar @app.route
app = Flask(__name__)

# 2) habilitar CORS (solo tu dominio o * para pruebas)
CORS(app, resources={r"/api/*": {"origins": "https://armoniasecreta.com.ar"}})
# para pruebas, podés usar: CORS(app, resources={r"/api/*": {"origins": "*"}})

# 3) endpoint raíz para healthcheck
@app.get("/")
def health():
    return "Armonía Secreta API OK", 200

# 4) endpoint de prueba (eco) — luego lo reemplazamos por el real
@app.post("/api/carta-natal")
def carta_natal():
    data = request.get_json(force=True, silent=True) or {}
    # solo para validar que Render responde bien
    return jsonify({"ok": True, "echo": data}), 200

# 5) para ejecución local opcional
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
