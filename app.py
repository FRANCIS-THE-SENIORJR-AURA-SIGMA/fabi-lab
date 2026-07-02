from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "fabilab2026secretkey"
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

DB = "fabilab.db"

# ── Crear base de datos ────────────────────────────────────
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
            estado   TEXT DEFAULT 'pendiente',
            creado   TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    # Agregar columnas si no existen (para bases de datos antiguas)
    try:
        cur.execute("ALTER TABLE reservas ADD COLUMN estado TEXT DEFAULT 'pendiente'")
    except:
        pass
    try:
        cur.execute("ALTER TABLE reservas ADD COLUMN creado TEXT DEFAULT (datetime('now','localtime'))")
    except:
        pass
    con.commit()
    con.close()

init_db()

# ── Credenciales del admin ─────────────────────────────────
ADMIN_USER = "fabi"
ADMIN_PASS = "fabilab2026"

# ── Servicios ──────────────────────────────────────────────
SERVICIOS = [
    {"id": 1, "nombre": "Manicura Clásica",  "descripcion": "Limpieza, corte y esmaltado tradicional.",       "precio": 50,  "icono": "💅"},
    {"id": 2, "nombre": "Manicura en Gel",   "descripcion": "Esmaltado semipermanente de larga duración.",    "precio": 80,  "icono": "✨"},
    {"id": 3, "nombre": "Pedicura Clásica",  "descripcion": "Cuidado completo de pies y esmaltado.",          "precio": 60,  "icono": "🦶"},
    {"id": 4, "nombre": "Pedicura Spa",      "descripcion": "Exfoliación, hidratación y esmaltado premium.",  "precio": 100, "icono": "🌸"},
    {"id": 5, "nombre": "Nail Art",          "descripcion": "Diseños personalizados y decoraciones únicas.",  "precio": 120, "icono": "🎨"},
    {"id": 6, "nombre": "Uñas Acrílicas",   "descripcion": "Extensión y modelado de uñas acrílicas.",        "precio": 150, "icono": "💎"},
]

# ── Horarios ───────────────────────────────────────────────
HORARIOS_SEMANA = ["15:00","15:30","16:00","16:30","17:00","17:30","18:00"]
HORARIOS_FIN_DE_SEMANA = [
    "08:00","08:30","09:00","09:30","10:00","10:30","11:00","11:30",
    "12:00","12:30","13:00","13:30","14:00","14:30","15:00","15:30",
    "16:00","16:30","17:00","17:30","18:00",
]

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
    cur.execute("SELECT hora FROM reservas WHERE fecha=? AND estado != 'cancelada'", (fecha,))
    r = [x[0] for x in cur.fetchall()]
    con.close()
    return r

def get_horarios_del_dia(fecha):
    try:
        dia = datetime.strptime(fecha, "%Y-%m-%d").weekday()
        return HORARIOS_FIN_DE_SEMANA if dia >= 5 else HORARIOS_SEMANA
    except:
        return HORARIOS_SEMANA

def get_horarios_disponibles(fecha=None):
    if not fecha:
        fecha = datetime.now().strftime("%Y-%m-%d")
    ahora      = datetime.now().strftime("%H:%M")
    hoy        = datetime.now().strftime("%Y-%m-%d")
    reservados = get_reservados(fecha)
    horarios   = get_horarios_del_dia(fecha)
    return [h for h in horarios if h not in reservados and (fecha != hoy or h > ahora)]

# ── Rutas principales ──────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html",
                           servicios=SERVICIOS,
                           horarios=get_horarios_disponibles(),
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

    if hora in get_reservados(fecha):
        return jsonify({"ok": False, "msg": f"El horario {hora} del {fecha} ya está reservado."})

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("INSERT INTO reservas (nombre,servicio,fecha,hora,telefono) VALUES (?,?,?,?,?)",
                (nombre, servicio, fecha, hora, telefono))
    con.commit()
    con.close()
    return jsonify({"ok": True, "msg": f"¡Reserva confirmada para {nombre} el {fecha} a las {hora}! 💅"})

@app.route("/horarios-disponibles")
def horarios_disponibles():
    fecha = request.args.get("fecha", datetime.now().strftime("%Y-%m-%d"))
    return jsonify(get_horarios_disponibles(fecha))

# ── Rutas del admin ────────────────────────────────────────
@app.route("/admin", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        u = request.form.get("usuario","")
        p = request.form.get("password","")
        if u == ADMIN_USER and p == ADMIN_PASS:
            session["admin"] = True
            return redirect(url_for("admin_panel"))
        return render_template("admin_login.html", error="Usuario o contraseña incorrectos.")
    return render_template("admin_login.html", error=None)

@app.route("/admin/panel")
def admin_panel():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    filtro = request.args.get("filtro", "todas")
    fecha  = request.args.get("fecha", "")
    con = sqlite3.connect(DB)
    cur = con.cursor()
    if filtro == "hoy":
        hoy = datetime.now().strftime("%Y-%m-%d")
        cur.execute("SELECT * FROM reservas WHERE fecha=? ORDER BY hora", (hoy,))
    elif filtro == "fecha" and fecha:
        cur.execute("SELECT * FROM reservas WHERE fecha=? ORDER BY hora", (fecha,))
    elif filtro == "pendientes":
        cur.execute("SELECT * FROM reservas WHERE estado='pendiente' ORDER BY fecha,hora")
    elif filtro == "confirmadas":
        cur.execute("SELECT * FROM reservas WHERE estado='confirmada' ORDER BY fecha,hora")
    elif filtro == "canceladas":
        cur.execute("SELECT * FROM reservas WHERE estado='cancelada' ORDER BY fecha,hora")
    else:
        cur.execute("SELECT * FROM reservas ORDER BY fecha,hora")
    reservas = cur.fetchall()
    # Estadísticas
    cur.execute("SELECT COUNT(*) FROM reservas WHERE estado='pendiente'")
    pendientes = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM reservas WHERE estado='confirmada'")
    confirmadas = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM reservas WHERE estado='cancelada'")
    canceladas = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM reservas WHERE fecha=?", (datetime.now().strftime("%Y-%m-%d"),))
    hoy_total = cur.fetchone()[0]
    con.close()
    return render_template("admin_panel.html",
                           reservas=reservas, filtro=filtro, fecha=fecha,
                           pendientes=pendientes, confirmadas=confirmadas,
                           canceladas=canceladas, hoy_total=hoy_total)

@app.route("/admin/accion/<int:id>/<accion>")
def admin_accion(id, accion):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    if accion in ["confirmada", "cancelada", "pendiente"]:
        con = sqlite3.connect(DB)
        cur = con.cursor()
        cur.execute("UPDATE reservas SET estado=? WHERE id=?", (accion, id))
        con.commit()
        con.close()
    return redirect(url_for("admin_panel"))

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))

if __name__ == "__main__":
    app.run(debug=True)