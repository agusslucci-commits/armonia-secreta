# 1) Logs visibles en Render
import traceback
def log(e):
    print("ERROR >>>", e)
    print(traceback.format_exc(), flush=True)

# 2) Envía email pero no tira abajo todo si falla
def enviar_pdf_seguro(destino, asunto, html, pdf_bytes, filename):
    try:
        enviar_pdf(destino, asunto, html, pdf_bytes, filename)
        return True, None
    except Exception as e:
        log(e)
        return False, str(e)

@app.post("/api/carta-natal")
def carta_endpoint():
    try:
        d = request.get_json(force=True)
        name=d.get("name"); email=d.get("email"); bdate=d.get("birth_date"); btime=d.get("birth_time")
        city=d.get("birth_city"); country=d.get("birth_country"); notes=d.get("notes","")
        tz=float(d.get("tz",-3))

        # Validaciones
        missing = [k for k,v in {"name":name,"email":email,"birth_date":bdate,"birth_time":btime,"birth_city":city,"birth_country":country}.items() if not v]
        if missing:
            return jsonify({"error": f"Faltan campos: {', '.join(missing)}"}), 400

        # Geocoding
        lat, lon = d.get("lat"), d.get("lon")
        if lat is None or lon is None:
            lat, lon = geocode(city, country)
        if lat is None or lon is None:
            return jsonify({"error":"No se pudo geolocalizar la ciudad/país"}), 400

        # Cálculo
        chart = compute_chart(bdate,btime,lat,lon,tz)

        # PDF
        pdf   = pdf_violeta(chart,name,email,notes, logo_path=os.path.join("assets","logo.png"))

        # Email (si falla, devolvemos 200 con aviso)
        ok, err = enviar_pdf_seguro(
            email,"Tu Carta Natal | Armonía Secreta",
            f"<p>Hola {name},</p><p>Adjuntamos tu Carta Natal en PDF. ✨</p>",
            pdf,"Carta_Natal_Armonia_Secreta.pdf"
        )

        if not ok:
            return jsonify({"ok": True, "warning": f"PDF generado pero no se pudo enviar el email: {err}"}), 200

        return jsonify({"ok": True, "message": "PDF enviado por email"}), 200

    except Exception as e:
        log(e)
        return jsonify({"error":"Error interno en el servidor"}), 500
