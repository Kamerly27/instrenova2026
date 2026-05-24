from flask import Flask, render_template, request, redirect, session, send_from_directory, make_response
import psycopg2
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

app = Flask(__name__)
app.secret_key = "renova2026"

# =========================
# CONFIG
# =========================
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# BASE DE DATOS
# =========================
def init_db():
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cursor = conn.cursor()

    # CURSOS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cursos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT
    )
    """)

    # DOCENTES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS docentes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        correo TEXT,
        password TEXT,
        curso_id INTEGER
    )
    """)

    # ESTUDIANTES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estudiantes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        documento TEXT,
        correo TEXT,
        password TEXT,
        curso_id INTEGER
    )
    """)

    # MODULOS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS modulos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT,
        descripcion TEXT,
        docente_id INTEGER
    )
    """)

    # CONTENIDOS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contenidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT,
        tipo TEXT,
        url TEXT,
        modulo_id INTEGER
    )
    """)

    # NOTAS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id INTEGER,
        materia TEXT,
        nota REAL
    )
    """)

    # ENTREGAS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS entregas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id INTEGER,
        modulo_id INTEGER,
        archivo TEXT,
        fecha TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================
# INICIO
# =========================
@app.route("/")
def inicio():
    return redirect("/login")

# =========================
# LOGIN ADMIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        usuario = request.form["usuario"]
        password = request.form["password"]
        if usuario == "adminrenova" and password == "Renova2026@Segura":
            session["admin"] = True
            return redirect("/admin")
        else:
            error = "Datos incorrectos"
    return render_template("login.html", error=error)

# =========================
# PANEL ADMIN
# =========================
@app.route("/admin")
def admin():
    if "admin" not in session:
        return redirect("/login")
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        cursor = conn.cursor()
    cursos = cursor.execute("SELECT * FROM cursos ORDER BY id DESC").fetchall()
    docentes = cursor.execute("""
        SELECT docentes.id,
               docentes.nombre,
               docentes.correo,
               cursos.nombre AS curso
        FROM docentes
        LEFT JOIN cursos
        ON docentes.curso_id = cursos.id
        ORDER BY docentes.id DESC
    """).fetchall()
    estudiantes = cursor.execute("""
        SELECT estudiantes.id,
               estudiantes.nombre,
               estudiantes.documento,
               estudiantes.correo,
               cursos.nombre AS curso
        FROM estudiantes
        LEFT JOIN cursos
        ON estudiantes.curso_id = cursos.id
        ORDER BY estudiantes.id DESC
    """).fetchall()
    conn.close()
    return render_template("admin.html", cursos=cursos, docentes=docentes, estudiantes=estudiantes)

# =========================
# CREAR CURSO
# =========================
@app.route("/crear_curso", methods=["POST"])
def crear_curso():
   conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cursor = conn.cursor()
    cursor.execute("INSERT INTO cursos(nombre) VALUES(?)", (request.form["nombre"],))
    conn.commit()
    conn.close()
    return redirect("/admin")

# =========================
# CREAR DOCENTE
# =========================
@app.route("/crear_docente", methods=["POST"])
def crear_docente():
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cursor = conn.cursor()
    cursor.execute("INSERT INTO docentes (nombre, correo, password, curso_id) VALUES (?, ?, ?, ?)",
                   (request.form["nombre"], request.form["correo"], request.form["password"], request.form["curso_id"]))
    conn.commit()
    conn.close()
    return redirect("/admin")

# =========================
# CREAR ESTUDIANTE
# =========================
@app.route("/crear_estudiante", methods=["POST"])
def crear_estudiante():
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cursor = conn.cursor()
    cursor.execute("INSERT INTO estudiantes (nombre, documento, correo, password, curso_id) VALUES (?, ?, ?, ?, ?)",
                   (request.form["nombre"], request.form["documento"], request.form["correo"], request.form["password"], request.form["curso_id"]))
    conn.commit()
    conn.close()
    return redirect("/admin")

# =========================
# LOGIN DOCENTE
# =========================
@app.route("/docente_login", methods=["GET", "POST"])
def docente_login():
    error = ""
    if request.method == "POST":
        correo = request.form["correo"]
        password = request.form["password"]
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
                cursor = conn.cursor()
        docente = cursor.execute("SELECT * FROM docentes WHERE correo=? AND password=?", (correo, password)).fetchone()
        conn.close()
        if docente:
            session["docente_id"] = docente["id"]
            return redirect("/panel_docente")
        else:
            error = "Datos incorrectos"
    return render_template("docente_login.html", error=error)

# =========================
# LOGIN ESTUDIANTE
# =========================
@app.route("/estudiante_login", methods=["GET", "POST"])
def estudiante_login():
    error = ""
    if request.method == "POST":
        correo = request.form["correo"]
        password = request.form["password"]
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        cursor = conn.cursor()
        estudiante = cursor.execute("SELECT * FROM estudiantes WHERE correo=? AND password=?", (correo, password)).fetchone()
        conn.close()
        if estudiante:
            session["estudiante_id"] = estudiante["id"]
            return redirect("/panel_estudiante")
        else:
            error = "Datos incorrectos"
    return render_template("estudiante_login.html", error=error)

# =========================
# PANEL DOCENTE
# =========================
@app.route("/panel_docente")
def panel_docente():
    if "docente_id" not in session:
        return redirect("/docente_login")
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cursor = conn.cursor()
    docente_id = session["docente_id"]
    docente = cursor.execute("""
        SELECT docentes.*,
               cursos.nombre AS curso_nombre
        FROM docentes
        LEFT JOIN cursos
        ON docentes.curso_id = cursos.id
        WHERE docentes.id=?
    """, (docente_id,)).fetchone()
    curso_id = docente["curso_id"]
    estudiantes = cursor.execute("SELECT estudiantes.* FROM estudiantes WHERE estudiantes.curso_id=? ORDER BY estudiantes.id DESC", (curso_id,)).fetchall()
    modulos = cursor.execute("SELECT * FROM modulos WHERE docente_id=? ORDER BY id DESC", (docente_id,)).fetchall()
    contenidos = cursor.execute("SELECT * FROM contenidos ORDER BY id DESC").fetchall()
    entregas = cursor.execute("""
        SELECT entregas.*,
               estudiantes.nombre AS estudiante_nombre,
               modulos.titulo AS modulo_nombre
        FROM entregas
        JOIN estudiantes
        ON entregas.estudiante_id = estudiantes.id
        JOIN modulos
        ON entregas.modulo_id = modulos.id
        ORDER BY entregas.id DESC
    """).fetchall()
    notas = cursor.execute("""
        SELECT notas.*,
               estudiantes.nombre AS estudiante_nombre
        FROM notas
        JOIN estudiantes
        ON notas.estudiante_id = estudiantes.id
        ORDER BY notas.id DESC
    """).fetchall()
    conn.close()
    return render_template("panel_docente.html", docente=docente, estudiantes=estudiantes, modulos=modulos, contenidos=contenidos, entregas=entregas, notas=notas)

# =========================
# PANEL ESTUDIANTE
# =========================
@app.route("/panel_estudiante")
def panel_estudiante():
    if "estudiante_id" not in session:
        return redirect("/estudiante_login")
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cursor = conn.cursor()
    estudiante_id = session["estudiante_id"]
    estudiante = cursor.execute("""
        SELECT estudiantes.*,
               cursos.nombre AS curso_nombre
        FROM estudiantes
        LEFT JOIN cursos
        ON estudiantes.curso_id = cursos.id
        WHERE estudiantes.id=%s
    """, (estudiante_id,)).fetchone()
    modulos = cursor.execute("""
        SELECT modulos.*
        FROM modulos
        JOIN docentes
        ON modulos.docente_id = docentes.id
        WHERE docentes.curso_id=?
        ORDER BY modulos.id DESC
    """, (estudiante["curso_id"],)).fetchall()
    contenidos = cursor.execute("""
        SELECT contenidos.*
        FROM contenidos
        JOIN modulos
        ON contenidos.modulo_id = modulos.id
        JOIN docentes
        ON modulos.docente_id = docentes.id
        WHERE docentes.curso_id=?
        ORDER BY contenidos.id DESC
    """, (estudiante["curso_id"],)).fetchall()
    entregas = cursor.execute("""
        SELECT entregas.*,
               modulos.titulo AS modulo_nombre
        FROM entregas
        JOIN modulos
        ON entregas.modulo_id = modulos.id
        WHERE entregas.estudiante_id=?
        ORDER BY entregas.id DESC
    """, (estudiante_id,)).fetchall()
    notas = cursor.execute("SELECT * FROM notas WHERE estudiante_id=? ORDER BY id DESC", (estudiante_id,)).fetchall()
    conn.close()
    return render_template("panel_estudiante.html", estudiante=estudiante, modulos=modulos, contenidos=contenidos, entregas=entregas, notas=notas)

# =========================
# CREAR MODULO
# =========================
@app.route("/crear_modulo", methods=["POST"])
def crear_modulo():
    titulo = request.form["titulo"]
    descripcion = request.form["descripcion"]
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cursor = conn.cursor()
    cursor.execute("INSERT INTO modulos (titulo, descripcion, docente_id) VALUES (?, ?, ?)",
                   (titulo, descripcion, session["docente_id"]))
    conn.commit()
    conn.close()
    return redirect("/panel_docente")

# =========================
# SUBIR ARCHIVO DOCENTE
# =========================
@app.route("/subir_archivo/<int:modulo_id>", methods=["POST"])
def subir_archivo(modulo_id):
    archivo = request.files["archivo"]
    titulo = request.form["titulo"]
    tipo = request.form["tipo"]
    nombre_archivo = secure_filename(archivo.filename)
    ruta_guardado = os.path.join(app.config["UPLOAD_FOLDER"], nombre_archivo)
    archivo.save(ruta_guardado)
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cursor = conn.cursor()
    cursor.execute("INSERT INTO contenidos (titulo, tipo, url, modulo_id) VALUES (?, ?, ?, ?)",
                   (titulo, tipo, nombre_archivo, modulo_id))
    conn.commit()
    conn.close()
    return redirect("/panel_docente")

# =========================
# SUBIR TAREA ESTUDIANTE
# =========================
@app.route("/subir_tarea/<int:modulo_id>", methods=["POST"])
def subir_tarea(modulo_id):
    if "estudiante_id" not in session:
        return redirect("/estudiante_login")
    archivo = request.files["archivo"]
    if archivo.filename == "":
        return "No seleccionaste archivo"
    if not archivo.filename.lower().endswith(".pdf"):
        return "Solo se permiten PDF"
    nombre_archivo = secure_filename(archivo.filename)
    ruta = os.path.join(app.config["UPLOAD_FOLDER"], nombre_archivo)
    archivo.save(ruta)
   conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cursor = conn.cursor()
    cursor.execute("INSERT INTO entregas (estudiante_id, modulo_id, archivo, fecha) VALUES (?, ?, ?, ?)",
                   (session["estudiante_id"], modulo_id, nombre_archivo, datetime.now().strftime("%d/%m/%Y")))
    conn.commit()
    conn.close()
    return redirect("/panel_estudiante")

# =========================
# GUARDAR NOTA
# =========================
@app.route("/guardar_nota", methods=["POST"])
def guardar_nota():
    if "docente_id" not in session:
        return redirect("/docente_login")

    estudiante_id = request.form["estudiante_id"]
    materia = request.form["materia"]
    nota = request.form["nota"]

    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cursor = conn.cursor()
    cursor.execute("INSERT INTO notas (estudiante_id, materia, nota) VALUES (?, ?, ?)",
                   (estudiante_id, materia, nota))
    conn.commit()
    conn.close()
    return redirect("/panel_docente")

# =========================
# VER ARCHIVOS
# =========================
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# =========================
# CERTIFICADO PDF
# =========================
@app.route("/certificado/<int:estudiante_id>")
def certificado(estudiante_id):

    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cursor = conn.cursor()

    estudiante = cursor.execute(
        """
        SELECT estudiantes.*,
               cursos.nombre AS curso_nombre
        FROM estudiantes
        LEFT JOIN cursos
        ON estudiantes.curso_id = cursos.id
        WHERE estudiantes.id=?
        """,
        (estudiante_id,),
    ).fetchone()

    notas = cursor.execute(
        """
        SELECT * FROM notas
        WHERE estudiante_id=?
        """,
        (estudiante_id,),
    ).fetchall()

    conn.close()

    if not estudiante:
        return "Estudiante no encontrado"

    promedio = 0

    if len(notas) > 0:
        suma = 0

        for nota in notas:
            suma += nota["nota"]

        promedio = round(suma / len(notas), 1)

    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import Image

    nombre_pdf = f"certificado_{estudiante['id']}.pdf"

    ruta_pdf = os.path.join(
        app.config["UPLOAD_FOLDER"],
        nombre_pdf
    )

    c = canvas.Canvas(ruta_pdf, pagesize=letter)

    width, height = letter

    # =========================
    # BORDE ELEGANTE
    # =========================

    c.setStrokeColor(HexColor("#0b1f4d"))
    c.setLineWidth(6)

    c.rect(30, 30, width - 60, height - 60)

    c.setLineWidth(2)

    c.rect(45, 45, width - 90, height - 90)

    # =========================
    # LOGO
    # =========================

    logo_path = "static/img/logorenova.png"

    if os.path.exists(logo_path):

        c.drawImage(
            logo_path,
            width / 2 - 60,
            660,
            width=120,
            height=120,
            preserveAspectRatio=True
        )

    # =========================
    # TITULO
    # =========================

    c.setFillColor(HexColor("#0b1f4d"))

    c.setFont("Helvetica-Bold", 28)

    c.drawCentredString(
        width / 2,
        620,
        "CERTIFICADO ACADÉMICO"
    )

    # =========================
    # TEXTO
    # =========================

    c.setFont("Helvetica", 16)

    c.drawCentredString(
        width / 2,
        570,
        "El Instituto Renova certifica que:"
    )

    # =========================
    # NOMBRE
    # =========================

    c.setFont("Helvetica-Bold", 24)

    c.drawCentredString(
        width / 2,
        520,
        estudiante["nombre"]
    )

    # =========================
    # CURSO
    # =========================

    c.setFont("Helvetica", 16)

    c.drawCentredString(
        width / 2,
        470,
        "Completó satisfactoriamente el programa:"
    )

    c.setFont("Helvetica-Bold", 22)

    c.drawCentredString(
        width / 2,
        435,
        estudiante["curso_nombre"]
    )

    # =========================
    # PROMEDIO
    # =========================

    c.setFont("Helvetica", 16)

    c.drawCentredString(
        width / 2,
        385,
        f"Promedio académico final: {promedio}"
    )

    # =========================
    # FECHA
    # =========================

    fecha = datetime.now().strftime("%d/%m/%Y")

    c.setFont("Helvetica", 14)

    c.drawCentredString(
        width / 2,
        340,
        f"Fecha de expedición: {fecha}"
    )

    # =========================
    # CODIGO CERTIFICADO
    # =========================

    codigo = f"RENOVA-{estudiante['id']}-{datetime.now().year}"

    c.setFont("Helvetica", 12)

    c.drawCentredString(
        width / 2,
        310,
        f"Código de certificado: {codigo}"
    )

    # =========================
    # FIRMA
    # =========================

    c.line(180, 180, 420, 180)

    c.setFont("Helvetica-Bold", 14)

    c.drawCentredString(
        width / 2,
        160,
        "Dirección Académica"
    )

    c.setFont("Helvetica", 12)

    c.drawCentredString(
        width / 2,
        142,
        "Instituto Renova"
    )

    # =========================
    # PIE
    # =========================

    c.setFont("Helvetica-Oblique", 10)

    c.drawCentredString(
        width / 2,
        80,
        "Documento generado automáticamente por la plataforma educativa Renova"
    )

    c.save()

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        nombre_pdf,
        as_attachment=True
    )
# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)
