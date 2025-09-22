# arriba de todo
import time, traceback

def log(msg):
    print(f"[AS] {msg}", flush=True)

# --- Geocoding: agregar timeout y logs ---
def geocode(city, country):
    from geopy.geocoders import Nominatim
    g = Nominatim(user_agent="armonia_secreta")
    log(f"Geocode start: {city}, {country}")
    try:
        loc = g.geocode(f"{city}, {country}", timeout=10)  # <-- timeout 10s
    except Exception as e:
        log(f"Geocode error: {e}")
        return None, None
    if not loc:
        log("Geocode not found")
        return None, None
    log(f"Geocode ok: {loc.latitude}, {loc.longitude}")
    return float(loc.latitude), float(loc.longitude)

# --- SMTP: agregar timeout y logs ---
def enviar_pdf(destino, asunto, html, pdf_bytes, filename):
    log("SMTP connect...")
    msg = EmailMessage()
    msg["From"] = MAIL_FROM; msg["To"] = destino; msg["Subject"] = asunto
    msg.set_content("Tu carta natal está adjunta.")
    msg.add_alternative(html, subtype="html")
    msg.add_attachment(pdf_bytes.getvalue(), maintype="application", subtype="pdf", filename=filename)

    # timeout de socket SMTP en 15s
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
        s.starttls()
        log("SMTP login...")
        s.login(SMTP_USER, SMTP_PASS)
        log("SMTP send_message...")
        s.send_message(msg)
    log("SMTP done.")

# app.py — Armonía Secreta (Swiss Ephemeris + PDF + Email)
import io, os, smtplib, datetime as dt, traceback
from email.message import EmailMessage
from flask import Flask, request, jsonify
from flask_cors import CORS
from geopy.geocoders import Nominatim
import swisseph as swe
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm

# -------------------- APP & CORS --------------------
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "https://armoniasecreta.com.ar"}})  # podés usar "*" mientras probás

# -------------------- SMTP (Render env) -------------
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
MAIL_FROM = os.getenv("MAIL_FROM", "Armonía Secreta <no-reply@armoniasecreta.com.ar>")

# -------------------- Swiss Ephemeris ----------------
EPHE_PATH = os.path.join(os.path.dirname(__file__), "ephe")
swe.set_ephe_path(EPHE_PATH)

ZODIAC = ["Aries","Tauro","Géminis","Cáncer","Leo","Virgo","Libra","Escorpio","Sagitario","Capricornio","Acuario","Piscis"]

def sign_deg(ecl_lon):
    e = ecl_lon % 360.0
    s_idx = int(e // 30)
    return ZODIAC[s_idx], round(e - s_idx*30, 2)

def geocode(city, country):
    g = Nominatim(user_agent="armonia_secreta")
    loc = g.geocode(f"{city}, {country}")
    if not loc: return None, None
    return float(loc.latitude), float(loc.longitude)

def julday_utc(date_str, time_str, tz_hours=-3.0):
    y,m,d = map(int, date_str.split("-"))
    hh,mm = map(int, time_str.split(":"))
    local = dt.datetime(y,m,d,hh,mm)
    utc   = local - dt.timedelta(hours=tz_hours)
    return swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0)

def compute_chart(date_str, time_str, lat, lon, tz=-3.0):
    jd_ut = julday_utc(date_str, time_str, tz)
    planets = {
        "Sol": swe.SUN, "Luna": swe.MOON, "Mercurio": swe.MERCURY,
        "Venus": swe.VENUS, "Marte": swe.MARS, "Júpiter": swe.JUPITER,
        "Saturno": swe.SATURN, "Urano": swe.URANUS, "Neptuno": swe.NEPTUNE, "Plutón": swe.PLUTO
    }
    pos = {}
    for name, pl in planets.items():
        p, _ = swe.calc_ut(jd_ut, pl, swe.FLG_SWIEPH)
        s, d = sign_deg(p[0])
        pos[name] = {"signo": s, "grado": d, "lon": round(p[0],2)}

    ascmc, houses = swe.houses_ex(jd_ut, lat, lon, b'P', swe.FLG_SWIEPH)  # Plácidus
    asc_s, asc_d  = sign_deg(ascmc[0])
    mc_s,  mc_d   = sign_deg(ascmc[1])

    return {
        "datetime_local": f"{date_str} {time_str}",
        "tz": tz, "lat": lat, "lon": lon,
        "planetas": pos,
        "ascendente": {"signo": asc_s, "grado": asc_d, "lon": round(ascmc[0],2)},
        "mc":         {"signo": mc_s,  "grado": mc_d,  "lon": round(ascmc[1],2)},
        "casas": [round(h,2) for h in houses]
    }

# -------------------- PDF Violeta --------------------
def pdf_violeta(chart, name, email, notes=None, logo_path=None):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W,H = A4
    vio1 = HexColor("#211328"); vio2 = HexColor("#1a0f22")
    gold = HexColor("#D4AF37"); text = HexColor("#EDE7F6")

    # Fondo + marco
    c.setFillColor(vio1); c.rect(10*mm,10*mm,W-20*mm,H-20*mm,fill=True,stroke=0)
    c.setFillColor(vio2); c.rect(11*mm,11*mm,W-22*mm,H-22*mm,fill=True,stroke=0)
    c.setStrokeColor(gold); c.rect(12*mm,12*mm,W-24*mm,H-24*mm,stroke=1,fill=0)

    # Branding
    c.setFillColor(gold); c.setFont("Times-Bold",22); c.drawString(20*mm,H-30*mm,"ARMONÍA SECRETA")
    c.setFillColor(text); c.setFont("Times-Bold",18); c.drawString(20*mm,H-40*mm,"Carta Natal Personalizada")

    # Datos
    y=H-55*mm; c.setFont("Times-Roman",12)
    def row(lbl,val):
        nonlocal y
        c.setFillColor(gold); c.drawString(20*mm,y,lbl)
        c.setFillColor(text); c.drawString(55*mm,y,str(val)); y-=7*mm
    row("Nombre:", name); row("Email:", email)
    row("Fecha/Hora:", chart["datetime_local"])
    row("Lugar (lat,lon):", f'{chart["lat"]:.4f}, {chart["lon"]:.4f}')
    row("TZ:", chart["tz"])
    if notes:
        c.setFillColor(gold); c.drawString(20*mm,y,"Notas:")
        c.setFillColor(text); c.setFont("Times-Roman",11)
        c.drawString(55*mm,y,notes[:90]); y-=9*mm; c.setFont("Times-Roman",12)

    # Posiciones clave
    c.setFillColor(gold); c.setFont("Times-Bold",14); c.drawString(20*mm,y,"Posiciones clave"); y-=7*mm
    c.setFillColor(text); c.setFont("Times-Roman",12)
    asc=chart["ascendente"]; c.drawString(20*mm,y,f"Ascendente: {asc['signo']} {asc['grado']}°"); y-=6*mm
    mc =chart["mc"];         c.drawString(20*mm,y,f"Medio Cielo: {mc['signo']} {mc['grado']}°"); y-=8*mm

    # Planetas (dos columnas)
    base_y=y
    for i,(pl,data) in enumerate(chart["planetas"].items()):
        x  = 20*mm if i<5 else 90*mm
        yy = base_y - (i%5)*6*mm
        c.drawString(x,yy,f"{pl}: {data['signo']} {data['grado']}°")

    # Logo opcional
    if logo_path and os.path.exists(logo_path):
        c.drawImage(logo_path, W-55*mm, H-40*mm, width=35*mm, height=20*mm, mask='auto')

    c.setFillColor(gold); c.setFont("Times-Roman",10)
    c.drawRightString(W-20*mm,15*mm,"© Armonía Secreta")
    c.showPage(); c.save(); buf.seek(0); return buf

# -------------------- Email -------------------------
def enviar_pdf(destino, asunto, html, pdf_bytes, filename):
    msg = EmailMessage()
    msg["From"] = MAIL_FROM; msg["To"] = destino; msg["Subject"] = asunto
    msg.set_content("Tu carta natal está adjunta.")
    msg.add_alternative(html, subtype="html")
    msg.add_attachment(pdf_bytes.getvalue(), maintype="application", subtype="pdf", filename=filename)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls(); s.login(SMTP_USER, SMTP_PASS); s.send_message(msg)

def log(e):
    print("ERROR >>>", e)
    print(traceback.format_exc(), flush=True)

# -------------------- Rutas -------------------------
@app.get("/")
def health(): return "Armonía Secreta API OK", 200

@app.post("/api/carta-natal")
def carta_endpoint():
    try:
        d = request.get_json(force=True)
        name=d.get("name"); email=d.get("email"); bdate=d.get("birth_date"); btime=d.get("birth_time")
        city=d.get("birth_city"); country=d.get("birth_country"); notes=d.get("notes","")
        tz=float(d.get("tz",-3))

        # Validación
        required = {"name":name,"email":email,"birth_date":bdate,"birth_time":btime,"birth_city":city,"birth_country":country}
        miss = [k for k,v in required.items() if not v]
        if miss: return jsonify({"error":f"Faltan campos: {', '.join(miss)}"}), 400

        # Geocoding
        lat, lon = d.get("lat"), d.get("lon")
        if lat is None or lon is None:
            lat, lon = geocode(city, country)
        if lat is None or lon is None:
            return jsonify({"error":"No se pudo geolocalizar la ciudad/país"}), 400

        # Carta
        chart = compute_chart(bdate, btime, float(lat), float(lon), tz)

        # PDF
        logo_path = os.path.join("assets","logo.png") if os.path.exists(os.path.join("assets","logo.png")) else None
        pdf = pdf_violeta(chart, name, email, notes, logo_path=logo_path)

        # Email
        try:
            enviar_pdf(
                email, "Tu Carta Natal | Armonía Secreta",
                f"<p>Hola {name},</p><p>Adjuntamos tu Carta Natal en PDF con la estética de <b>Armonía Secreta</b>. ✨</p>",
                pdf, "Carta_Natal_Armonia_Secreta.pdf"
            )
        except Exception as e:
            log(e)
            # devolvemos igual el OK con aviso (para que tu front no marque error)
            return jsonify({"ok":True,"warning":"PDF generado pero no se pudo enviar el email. Verificar SMTP en Render."}), 200

        return jsonify({"ok": True, "message": "PDF enviado por email"}), 200

    except Exception as e:
        log(e)
        return jsonify({"error":"Error interno en el servidor"}), 500

# -------------------- Local run ---------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT","3000")), debug=True)
