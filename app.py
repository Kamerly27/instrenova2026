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

def get_connection():
    return psycopg2.connect(
        os.environ.get("DATABASE_URL")
    )

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

@app.route("/panel_docente")
def panel_docente():

    if "docente_id" not in session:
        return redirect("/docente_login")

    return render_template("panel_docente.html")

@app.route("/panel_estudiante")
def panel_estudiante():

    if "estudiante_id" not in session:
        return redirect("/estudiante_login")

    return render_template("panel_estudiante.html")

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)