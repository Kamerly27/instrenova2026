from flask import Flask, render_template, request, redirect, session, send_from_directory
import psycopg2
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor

app = Flask(__name__)
app.secret_key = "renova2026"

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# DB INIT
# =========================
def init_db():
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cursos (
        id SERIAL PRIMARY KEY,
        nombre TEXT UNIQUE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS docentes (
        id SERIAL PRIMARY KEY,
        nombre TEXT,
        correo TEXT UNIQUE,
        password TEXT,
        curso_id INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estudiantes (
        id SERIAL PRIMARY KEY,
        nombre TEXT,
        documento TEXT UNIQUE,
        correo TEXT UNIQUE,
        password TEXT,
        curso_id INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS modulos (
        id SERIAL PRIMARY KEY,
        titulo TEXT,
        descripcion TEXT,
        docente_id INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contenidos (
        id SERIAL PRIMARY KEY,
        titulo TEXT,
        tipo TEXT,
        url TEXT,
        modulo_id INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notas (
        id SERIAL PRIMARY KEY,
        estudiante_id INTEGER,
        materia TEXT,
        nota REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS entregas (
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

# =========================
# LOGIN SIMPLE ADMIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        if request.form["usuario"] == "adminrenova" and request.form["password"] == "Renova2026!Panel$84"::
            session["admin"] = True
            return redirect("/admin")
        error = "Incorrecto"
    return render_template("login.html", error=error)

# =========================
# ADMIN
# =========================
@app.route("/admin")
def admin():
    if "admin" not in session:
        return redirect("/login")

    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM cursos")
    cursos = cursor.fetchall()

    cursor.execute("SELECT * FROM docentes")
    docentes = cursor.fetchall()

    cursor.execute("SELECT * FROM estudiantes")
    estudiantes = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("admin.html",
                           cursos=cursos,
                           docentes=docentes,
                           estudiantes=estudiantes)

# =========================
# LOGIN ESTUDIANTE
# =========================
@app.route("/estudiante_login", methods=["GET", "POST"])
def estudiante_login():

    error = ""

    if request.method == "POST":

        correo = request.form["correo"]
        password = request.form["password"]

        conn = psycopg2.connect(
            os.environ.get("DATABASE_URL")
        )

        cursor = conn.cursor()

        cursor.execute("""
            SELECT id
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
# =========================
# LOGIN DOCENTE
# =========================
@app.route("/docente_login", methods=["GET", "POST"])
def docente_login():

    error = ""

    if request.method == "POST":

        correo = request.form["correo"]
        password = request.form["password"]

        conn = psycopg2.connect(
            os.environ.get("DATABASE_URL")
        )

        cursor = conn.cursor()

        cursor.execute("""

            SELECT id,nombre
            FROM docentes
            WHERE correo=%s
            AND password=%s

        """,(correo,password))

        docente = cursor.fetchone()

        cursor.close()
        conn.close()

        if docente:

            session["docente_id"] = docente[0]
            session["docente_nombre"] = docente[1]

            return redirect("/panel_docente")

        error="Correo o contraseña incorrectos"

    return render_template(
        "docente_login.html",
        error=error
    )


# =========================
# LOGIN DOCENTE
# =========================
@app.route("/docente_login", methods=["GET", "POST"])
def docente_login():

    error = ""

    if request.method == "POST":

        correo = request.form["correo"]
        password = request.form["password"]

        conn = psycopg2.connect(
            os.environ.get("DATABASE_URL")
        )

        cursor = conn.cursor()

        cursor.execute("""

            SELECT
                id,
                nombre

            FROM docentes

            WHERE correo=%s
            AND password=%s

        """, (correo, password))

        docente = cursor.fetchone()

        cursor.close()
        conn.close()

        if docente:

            session["docente_id"] = docente[0]

            return redirect(
                "/panel_docente"
            )

        error = "Correo o contraseña incorrectos"

    return render_template(
        "docente_login.html",
        error=error
    )
# =========================
# PANEL DOCENTE
# =========================
@app.route("/panel_docente")
def panel_docente():

    if "docente_id" not in session:

        return redirect("/docente_login")

    return render_template(
        "panel_docente.html"
    ) 
# =========================
# PANEL ESTUDIANTE
# =========================
@app.route("/panel_estudiante")
def panel_estudiante():

    if "estudiante_id" not in session:
        return redirect("/estudiante_login")

    estudiante_id = session["estudiante_id"]

    conn = None
    cursor = None

    try:

        conn = psycopg2.connect(
            os.environ.get("DATABASE_URL")
        )

        cursor = conn.cursor()

        # DATOS ESTUDIANTE
        cursor.execute("""
            SELECT
                id,
                nombre,
                documento,
                correo,
                curso_id
            FROM estudiantes
            WHERE id=%s
        """, (estudiante_id,))

        estudiante = cursor.fetchone()

        if estudiante is None:
            return "Estudiante no encontrado", 404

        # NOTAS
        cursor.execute("""
            SELECT
                id,
                materia,
                nota
            FROM notas
            WHERE estudiante_id=%s
            ORDER BY id DESC
        """, (estudiante_id,))

        notas = cursor.fetchall()

        if notas is None:
            notas = []

        return render_template(
            "panel_estudiante.html",
            estudiante=estudiante,
            notas=notas
        )

    except Exception as e:

        print(
            "ERROR PANEL ESTUDIANTE:",
            str(e)
        )

        import traceback
        traceback.print_exc()

        return (
            "Error al cargar el panel del estudiante.",
            500
        )

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

# =========================
# UPLOADS
# =========================
@app.route("/uploads/<filename>")
def uploads(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)