from flask import Flask, render_template, request, redirect, session, send_from_directory
import psycopg2
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = "renova2026"

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================================
# DATABASE
# =========================================

def get_connection():
    return psycopg2.connect(
        os.environ.get("DATABASE_URL")
    )

# =========================================
# INIT DB
# =========================================

def init_db():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cursos(
        id SERIAL PRIMARY KEY,
        nombre TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS docentes(
        id SERIAL PRIMARY KEY,
        nombre TEXT,
        correo TEXT UNIQUE,
        password TEXT,
        curso_id INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estudiantes(
        id SERIAL PRIMARY KEY,
        nombre TEXT,
        documento TEXT,
        correo TEXT UNIQUE,
        password TEXT,
        curso_id INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS modulos(
        id SERIAL PRIMARY KEY,
        titulo TEXT,
        descripcion TEXT,
        docente_id INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contenidos(
        id SERIAL PRIMARY KEY,
        titulo TEXT,
        tipo TEXT,
        url TEXT,
        modulo_id INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notas(
        id SERIAL PRIMARY KEY,
        estudiante_id INTEGER,
        materia TEXT,
        nota REAL,
        observacion TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS entregas(
        id SERIAL PRIMARY KEY,
        estudiante_id INTEGER,
        modulo_id INTEGER,
        archivo TEXT,
        fecha TEXT
    )
    """)

    conn.commit()
    cursor.close()
    conn.close()

init_db()

# =========================================
# LOGIN ADMIN
# =========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    error = ""

    if request.method == "POST":

        usuario = request.form["usuario"]
        password = request.form["password"]

        if usuario == "adminrenova" and password == "Renova2026!Panel$84":

            session["admin"] = True

            return redirect("/admin")

        error = "Datos incorrectos"

    return render_template(
        "login.html",
        error=error
    )

# =========================================
# ADMIN
# =========================================

@app.route("/admin")
def admin():

    if "admin" not in session:
        return redirect("/login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM cursos")
    cursos = cursor.fetchall()

    cursor.execute("SELECT * FROM docentes")
    docentes = cursor.fetchall()

    cursor.execute("SELECT * FROM estudiantes")
    estudiantes = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin.html",
        cursos=cursos,
        docentes=docentes,
        estudiantes=estudiantes
    )

# =========================================
# CREAR CURSO
# =========================================

@app.route("/crear_curso", methods=["POST"])
def crear_curso():

    nombre = request.form["nombre"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO cursos(nombre)
        VALUES(%s)
    """, (nombre,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/admin")

# =========================================
# CREAR DOCENTE
# =========================================

@app.route("/crear_docente", methods=["POST"])
def crear_docente():

    nombre = request.form["nombre"]
    correo = request.form["correo"]
    password = request.form["password"]
    curso_id = request.form["curso_id"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO docentes(
            nombre,
            correo,
            password,
            curso_id
        )
        VALUES(%s,%s,%s,%s)
    """, (
        nombre,
        correo,
        password,
        curso_id
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/admin")

# =========================================
# CREAR ESTUDIANTE
# =========================================

@app.route("/crear_estudiante", methods=["POST"])
def crear_estudiante():

    nombre = request.form["nombre"]
    documento = request.form["documento"]
    correo = request.form["correo"]
    password = request.form["password"]
    curso_id = request.form["curso_id"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO estudiantes(
            nombre,
            documento,
            correo,
            password,
            curso_id
        )
        VALUES(%s,%s,%s,%s,%s)
    """, (
        nombre,
        documento,
        correo,
        password,
        curso_id
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/admin")

# =========================================
# LOGIN DOCENTE
# =========================================

@app.route("/docente_login", methods=["GET", "POST"])
def docente_login():

    error = ""

    if request.method == "POST":

        correo = request.form["correo"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id,nombre
            FROM docentes
            WHERE correo=%s
            AND password=%s
        """, (correo, password))

        docente = cursor.fetchone()

        cursor.close()
        conn.close()

        if docente:

            session["docente_id"] = docente[0]

            return redirect("/panel_docente")

        error = "Correo o contraseña incorrectos"

    return render_template(
        "docente_login.html",
        error=error
    )

# =========================================
# LOGIN ESTUDIANTE
# =========================================

@app.route("/estudiante_login", methods=["GET", "POST"])
def estudiante_login():

    error = ""

    if request.method == "POST":

        correo = request.form["correo"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id,nombre
            FROM estudiantes
            WHERE correo=%s
            AND password=%s
        """, (correo, password))

        estudiante = cursor.fetchone()

        cursor.close()
        conn.close()

        if estudiante:

            session["estudiante_id"] = estudiante[0]

            return redirect("/panel_estudiante")

        error = "Correo o contraseña incorrectos"

    return render_template(
        "estudiante_login.html",
        error=error
    )
    # =========================================
# PANEL DOCENTE
# =========================================

@app.route("/panel_docente")
def panel_docente():

    if "docente_id" not in session:
        return redirect("/docente_login")

    conn = get_connection()
    cursor = conn.cursor()

    docente_id = session["docente_id"]

    # DOCENTE
    cursor.execute("""
        SELECT id,nombre,correo
        FROM docentes
        WHERE id=%s
    """, (docente_id,))

    d = cursor.fetchone()

    docente = {
        "id": d[0],
        "nombre": d[1],
        "correo": d[2]
    }

    # MODULOS
    cursor.execute("""
        SELECT id,titulo,descripcion
        FROM modulos
        WHERE docente_id=%s
        ORDER BY id DESC
    """, (docente_id,))

    modulos_raw = cursor.fetchall()

    modulos = []

    for m in modulos_raw:

        modulos.append({
            "id": m[0],
            "titulo": m[1],
            "descripcion": m[2]
        })

    # CONTENIDOS
    cursor.execute("""
        SELECT id,titulo,tipo,url,modulo_id
        FROM contenidos
        ORDER BY id DESC
    """)

    contenidos_raw = cursor.fetchall()

    contenidos = []

    for c in contenidos_raw:

        contenidos.append({
            "id": c[0],
            "titulo": c[1],
            "tipo": c[2],
            "url": c[3],
            "modulo_id": c[4]
        })

    # ESTUDIANTES + NOTAS
    cursor.execute("""
        SELECT
            estudiantes.id,
            estudiantes.nombre,
            estudiantes.correo,
            estudiantes.documento,
            notas.materia,
            notas.nota,
            notas.observacion

        FROM estudiantes

        LEFT JOIN notas
        ON estudiantes.id = notas.estudiante_id

        ORDER BY estudiantes.id DESC
    """)

    estudiantes_raw = cursor.fetchall()

    estudiantes = []

    for e in estudiantes_raw:

        estudiantes.append({
            "id": e[0],
            "nombre": e[1],
            "correo": e[2],
            "documento": e[3],
            "materia": e[4],
            "nota": e[5],
            "observacion": e[6]
        })

    # ENTREGAS
    cursor.execute("""
        SELECT
            entregas.id,
            estudiantes.nombre,
            modulos.titulo,
            entregas.archivo,
            entregas.fecha

        FROM entregas

        INNER JOIN estudiantes
        ON entregas.estudiante_id = estudiantes.id

        INNER JOIN modulos
        ON entregas.modulo_id = modulos.id

        ORDER BY entregas.id DESC
    """)

    entregas_raw = cursor.fetchall()

    entregas = []

    for x in entregas_raw:

        entregas.append({
            "id": x[0],
            "estudiante": x[1],
            "modulo": x[2],
            "archivo": x[3],
            "fecha": x[4]
        })

    cursor.close()
    conn.close()

    return render_template(
        "panel_docente.html",
        docente=docente,
        modulos=modulos,
        contenidos=contenidos,
        estudiantes=estudiantes,
        entregas=entregas
    )

# =========================================
# GUARDAR NOTA
# =========================================

@app.route("/guardar_nota", methods=["POST"])
def guardar_nota():

    estudiante_id = request.form["estudiante_id"]
    materia = request.form["materia"]
    nota = request.form["nota"]
    observacion = request.form["observacion"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO notas(
            estudiante_id,
            materia,
            nota,
            observacion
        )
        VALUES(%s,%s,%s,%s)
    """, (
        estudiante_id,
        materia,
        nota,
        observacion
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/panel_docente")

# =========================================
# RUN
# =========================================

if __name__ == "__main__":
    app.run(debug=True)