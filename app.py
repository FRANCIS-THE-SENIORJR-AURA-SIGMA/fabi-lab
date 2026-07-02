from flask import Flask, render_template, request, jsonify, send_from_directory
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

DB = "fabilab.db"

# ── Crear base de datos si no existe ──────────────────────
def init_db():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reservas (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre   TEXT NOT NULL,
            servicio TEXT NOT NULL,
            fecha    TEXT NOT NULL,
            hora     TEXT NOT NULL,
            telefono TEXT NOT NULL,
            creado   TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    con.commit()
    con.close()

init_db()

# ── Servicios ──────────────────────────────────────────────
SERVICIOS = [
    {"id": 1, "nombre": "Manicura Clásica",  "descripcion": "Limpieza, corte y esmaltado tradicional.",        "precio": 50,  "icono": "💅"},
    {"id": 2, "nombre": "Manicura en Gel",   "descripcion": "Esmaltado semipermanente de larga duración.",     "precio": 80,  "icono": "✨"},
    {"id": 3, "nombre": "Pedicura Clásica",  "descripcion": "Cuidado completo de pies y esmaltado.",           "precio": 60,  "icono": "🦶"},
    {"id": 4, "nombre": "Pedicura Spa",      "descripcion": "Exfoliación, hidratación y esmaltado premium.",   "precio": 100, "icono": "🌸"},
    {"id": 5, "nombre": "Nail Art",          "descripcion": "Diseños personalizados y decoraciones únicas.",   "precio": 120, "icono": "🎨"},
    {"id": 6, "nombre": "Uñas Acrílicas",   "descripcion": "Extensión y modelado de uñas acrílicas.",         "precio": 150, "icono": "💎"},
]

# ── Horarios según día ─────────────────────────────────────
# Lunes a Viernes: 15:00 a 18:00
HORARIOS_SEMANA = [
    "15:00","15:30","16:00","16:30","17:00","17:30","18:00",
]
# Sábado y Domingo: 08:00 a 18:00
HORARIOS_FIN_DE_SEMANA = [
    "08:00","08:30","09:00","09:30","10:00","10:30","11:00","11:30",
    "12:00","12:30","13:00","13:30","14:00","14:30","15:00","15:30",
    "16:00","16:30","17:00","17:30","18:00",
]

def get_horarios_del_dia(fecha):
    """Devuelve los horarios según si es día de semana o fin de semana."""
    try:
        dia = datetime.strptime(fecha, "%Y-%m-%d").weekday()
        # 0=Lunes, 1=Martes ... 4=Viernes, 5=Sábado, 6=Domingo
        return HORARIOS_FIN_DE_SEMANA if dia >= 5 else HORARIOS_SEMANA
    except:
        return HORARIOS_SEMANA

# ── Galería ────────────────────────────────────────────────
GALERIA = [
    {"antes": "manicura_antes.jpg",  "despues": "manicura_despues.jpg",  "servicio": "Manicura Clásica"},
    {"antes": "pedicura_antes.jpg",  "despues": "pedicura_despues.jpg",  "servicio": "Pedicura Spa"},
    {"antes": "nailart_antes.jpg",   "despues": "nailart_despues.jpg",   "servicio": "Nail Art"},
    {"antes": "acrilicas_antes.jpg", "despues": "acrilicas_despues.jpg", "servicio": "Uñas Acrílicas"},
]

# ── Helpers ────────────────────────────────────────────────
def get_reservados(fecha):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("SELECT hora FROM reservas WHERE fecha = ?", (fecha,))
    reservados = [r[0] for r in cur.fetchall()]
    con.close()
    return reservados

def get_horarios_disponibles(fecha=None):
    if not fecha:
        fecha = datetime.now().strftime("%Y-%m-%d")
    ahora      = datetime.now().strftime("%H:%M")
    hoy        = datetime.now().strftime("%Y-%m-%d")
    reservados = get_reservados(fecha)
    horarios   = get_horarios_del_dia(fecha)
    return [
        h for h in horarios
        if h not in reservados and (fecha != hoy or h > ahora)
    ]

# ── Rutas ──────────────────────────────────────────────────
@app.route("/")
def index():
    horarios = get_horarios_disponibles()
    return render_template("index.html",
                           servicios=SERVICIOS,
                           horarios=horarios,
                           galeria=GALERIA)

@app.route("/reservar", methods=["POST"])
def reservar():
    nombre   = request.form.get("nombre",   "").strip()
    servicio = request.form.get("servicio", "").strip()
    fecha    = request.form.get("fecha",    "").strip()
    hora     = request.form.get("hora",     "").strip()
    telefono = request.form.get("telefono", "").strip()

    if not all([nombre, servicio, fecha, hora, telefono]):
        return jsonify({"ok": False, "msg": "Por favor completa todos los campos."})

    # Verificar si el horario ya está tomado
    if hora in get_reservados(fecha):
        return jsonify({"ok": False, "msg": f"El horario {hora} del {fecha} ya está reservado."})

    # Guardar en base de datos
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("""
        INSERT INTO reservas (nombre, servicio, fecha, hora, telefono)
        VALUES (?, ?, ?, ?, ?)
    """, (nombre, servicio, fecha, hora, telefono))
    con.commit()
    con.close()

    return jsonify({"ok": True, "msg": f"¡Reserva confirmada para {nombre} el {fecha} a las {hora}! 💅"})

@app.route("/horarios-disponibles")
def horarios_disponibles():
    fecha = request.args.get("fecha", datetime.now().strftime("%Y-%m-%d"))
    return jsonify(get_horarios_disponibles(fecha))

@app.route("/admin/reservas")
def ver_reservas():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("SELECT id, nombre, servicio, fecha, hora, telefono, creado FROM reservas ORDER BY fecha, hora")
    filas = cur.fetchall()
    con.close()
    html = "<h2 style='font-family:sans-serif;color:#e91e8c'>📋 Reservas Fabi Lab</h2>"
    html += "<table border='1' cellpadding='8' style='border-collapse:collapse;font-family:sans-serif'>"
    html += "<tr style='background:#f8c8d4'><th>#</th><th>Nombre</th><th>Servicio</th><th>Fecha</th><th>Hora</th><th>Teléfono</th><th>Registrado</th></tr>"
    for f in filas:
        html += f"<tr><td>{f[0]}</td><td>{f[1]}</td><td>{f[2]}</td><td>{f[3]}</td><td>{f[4]}</td><td>{f[5]}</td><td>{f[6]}</td></tr>"
    html += "</table>"
    return html

if __name__ == "__main__":
    app.run(debug=True)