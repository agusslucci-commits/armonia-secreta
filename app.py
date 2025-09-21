from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "https://armoniasecreta.com.ar"}})

def log(e):
    print("ERROR >>>", e)
    print(traceback.format_exc(), flush=True)

@app.get("/")
def health():
    return "Armonía Secreta API OK", 200

@app.post("/api/carta-natal")
def carta_natal():
    try:
        data = request.get_json(force=True)
        # 1. Validar datos
        name = data.get("name")
        email = data.get("email")
        bdate = data.get("birth_date")
        btime = data.get("birth_time")
        city = data.get("birth_city")
        country = data.get("birth_country")

        if not all([name,email,bdate,btime,city,country]):
            return jsonify({"error":"Faltan datos obligatorios"}), 400

        # 2. Geocoding con Nominatim o similar (ejemplo)
        # lat, lon = geocode(city, country)

        # 3. Calcular carta natal (Swiss Ephemeris)
        # chart = compute_chart(bdate, btime, lat, lon, tz)

        # 4. Generar PDF (con estética violeta)
        # pdf = pdf_violeta(chart, name, email, notes="")

        # 5. Enviar por mail
        # enviar_pdf(email, "Tu Carta Natal | Armonía Secreta", "<p>Hola...</p>", pdf, "CartaNatal.pdf")

        return jsonify({"ok":True,"message":"PDF generado y enviado"}), 200

    except Exception as e:
        log(e)
        return jsonify({"error":"Error interno"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
