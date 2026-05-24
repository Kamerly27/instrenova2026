from flask import Flask, render_template, request, redirect, session, send_from_directory, make_response
import psycopg2
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor # Importado para uso en certificado
from reportlab.platypus import Image # Importado para uso en certificado

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
    # Conexión a la base de datos usando la variable de entorno
    # Asegúrate de que la variable DATABASE_URL esté configurada correctamente
    try:
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        cursor = conn.cursor()

        # CURSOS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cursos (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL UNIQUE
        )
        """)

        # DOCENTES
        # Combinada la definición para incluir password y curso_id
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS docentes (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            correo TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            curso_id INTEGER REFERENCES cursos(id) ON DELETE SET NULL
        )
        """)

        # ESTUDIANTES
        # Combinada la definición para incluir password y curso_id
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS estudiantes (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            documento TEXT NOT NULL UNIQUE,
            correo TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            curso_id INTEGER REFERENCES cursos(id) ON DELETE SET NULL
        )
        """)

        # MODULOS
        # Combinada la definición para incluir docente_id
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS modulos (
            id SERIAL PRIMARY KEY,
            titulo TEXT NOT NULL,
            descripcion TEXT,
            docente_id INTEGER REFERENCES docentes(id) ON DELETE CASCADE
        )
        """)

        # CONTENIDOS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS contenidos (
            id SERIAL PRIMARY KEY,
            titulo TEXT NOT NULL,
            tipo TEXT NOT NULL, -- e.g., 'video', 'documento', 'enlace'
            url TEXT NOT NULL, -- Nombre del archivo o URL
            modulo_id INTEGER REFERENCES modulos(id) ON DELETE CASCADE
        )
        """)

        # NOTAS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notas (
            id SERIAL PRIMARY KEY,
            estudiante_id INTEGER REFERENCES estudiantes(id) ON DELETE CASCADE,
            materia TEXT NOT NULL,
            nota REAL NOT NULL CHECK (nota >= 0 AND nota <= 10) -- Asumiendo una escala de 0 a 10
        )
        """)

        # ENTREGAS
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS entregas (
            id SERIAL PRIMARY KEY,
            estudiante_id INTEGER REFERENCES estudiantes(id) ON DELETE CASCADE,
            modulo_id INTEGER REFERENCES modulos(id) ON DELETE CASCADE,
            archivo TEXT NOT NULL, -- Nombre del archivo subido
            fecha TEXT NOT NULL -- Fecha de entrega
        )
        """)

        conn.commit()
        cursor.close()
        conn.close()
        print("Base de datos inicializada correctamente.")
    except Exception as e:
        print(f"Error al inicializar la base de datos: {e}")
        # En un entorno de producción, podrías querer manejar esto de forma más robusta

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
        usuario = request.form.get("usuario") # Usar .get() para evitar KeyError
        password = request.form.get("password")
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

    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        cursor = conn.cursor()

        # Obtener cursos
        cursor.execute("SELECT id, nombre FROM cursos ORDER BY id DESC")
        cursos = cursor.fetchall()

        # Obtener docentes con nombre de curso
        cursor.execute("""
            SELECT d.id, d.nombre, d.correo, c.nombre AS curso_nombre
            FROM docentes d
            LEFT JOIN cursos c ON d.curso_id = c.id
            ORDER BY d.id DESC
        """)
        docentes = cursor.fetchall()

        # Obtener estudiantes con nombre de curso
        cursor.execute("""
            SELECT e.id, e.nombre, e.documento, e.correo, c.nombre AS curso_nombre
            FROM estudiantes e
            LEFT JOIN cursos c ON e.curso_id = c.id
            ORDER BY e.id DESC
        """)
        estudiantes = cursor.fetchall()

        # Obtener todos los cursos para los formularios de creación
        cursor.execute("SELECT id, nombre FROM cursos ORDER BY nombre ASC")
        all_cursos = cursor.fetchall()

        return render_template("admin.html", cursos=cursos, docentes=docentes, estudiantes=estudiantes, all_cursos=all_cursos)

    except (Exception, psycopg2.Error) as error:
        print(f"Error al obtener datos del admin: {error}")
        return "Error al cargar el panel de administración."
    finally:
        if conn:
            cursor.close()
            conn.close()

# =========================
# CREAR CURSO
# =========================
@app.route("/crear_curso", methods=["POST"])
def crear_curso():
    if "admin" not in session:
        return redirect("/login")

    nombre_curso = request.form.get("nombre")
    if not nombre_curso:
        return "El nombre del curso es requerido", 400

    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        cursor = conn.cursor()
        # Usar %s para placeholders en psycopg2
        cursor.execute("INSERT INTO cursos(nombre) VALUES(%s)", (nombre_curso,))
        conn.commit()
        return redirect("/admin")
    except psycopg2.errors.UniqueViolation:
        conn.rollback() # Deshacer la transacción si hay violación de unicidad
        return "El nombre del curso ya existe.", 400
    except (Exception, psycopg2.Error) as error:
        print(f"Error al crear curso: {error}")
        if conn:
            conn.rollback()
        return "Error al crear el curso."
    finally:
        if conn:
            cursor.close()
            conn.close()

# =========================
# CREAR DOCENTE
# =========================
@app.route("/crear_docente", methods=["POST"])
def crear_docente():
    if "admin" not in session:
        return redirect("/login")

    nombre = request.form.get("nombre")
    correo = request.form.get("correo")
    password = request.form.get("password")
    curso_id = request.form.get("curso_id") # Puede ser None si no se selecciona curso

    if not nombre or not correo or not password:
        return "Nombre, correo y contraseña son requeridos.", 400

    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        cursor = conn.cursor()
        # Convertir curso_id a int, manejar si es None o vacío
        curso_id_int = int(curso_id) if curso_id and curso_id.isdigit() else None

        cursor.execute("INSERT INTO docentes (nombre, correo, password, curso_id) VALUES (%s, %s, %s, %s)",
                       (nombre, correo, password, curso_id_int))
        conn.commit()
        return redirect("/admin")
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return "El correo del docente ya está registrado.", 400
    except (Exception, psycopg2.Error) as error:
        print(f"Error al crear docente: {error}")
        if conn:
            conn.rollback()
        return "Error al crear el docente."
    finally:
        if conn:
            cursor.close()
            conn.close()

# =========================
# CREAR ESTUDIANTE
# =========================
@app.route("/crear_estudiante", methods=["POST"])
def crear_estudiante():
    if "admin" not in session:
        return redirect("/login")

    nombre = request.form.get("nombre")
    documento = request.form.get("documento")
    correo = request.form.get("correo")
    password = request.form.get("password")
    curso_id = request.form.get("curso_id") # Puede ser None si no se selecciona curso

    if not nombre or not documento or not correo or not password:
        return "Nombre, documento, correo y contraseña son requeridos.", 400

    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        cursor = conn.cursor()
        # Convertir curso_id a int, manejar si es None o vacío
        curso_id_int = int(curso_id) if curso_id and curso_id.isdigit() else None

        cursor.execute("INSERT INTO estudiantes (nombre, documento, correo, password, curso_id) VALUES (%s, %s, %s, %s, %s)",
                       (nombre, documento, correo, password, curso_id_int))
        conn.commit()
        return redirect("/admin")
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return "El documento o correo del estudiante ya está registrado.", 400
    except (Exception, psycopg2.Error) as error:
        print(f"Error al crear estudiante: {error}")
        if conn:
            conn.rollback()
        return "Error al crear el estudiante."
    finally:
        if conn:
            cursor.close()
            conn.close()

# =========================
# LOGIN DOCENTE
# =========================
@app.route("/docente_login", methods=["GET", "POST"])
def docente_login():
    error = ""
    if request.method == "POST":
        correo = request.form.get("correo")
        password = request.form.get("password")

        if not correo or not password:
            error = "Por favor, ingrese correo y contraseña."
        else:
            conn = None
            cursor = None
            try:
                conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
                cursor = conn.cursor()
                # Usar %s para placeholders en psycopg2
                cursor.execute("SELECT id, nombre, correo FROM docentes WHERE correo=%s AND password=%s", (correo, password))
                docente = cursor.fetchone()
                conn.close() # Cerrar conexión aquí después de fetchone

                if docente:
                    # psycopg2 devuelve tuplas, necesitamos acceder por índice
                    session["docente_id"] = docente[0] # ID del docente
                    session["docente_nombre"] = docente[1] # Nombre del docente
                    return redirect("/panel_docente")
                else:
                    error = "Correo o contraseña incorrectos."
            except (Exception, psycopg2.Error) as error:
                print(f"Error en login docente: {error}")
                error = "Error interno al intentar iniciar sesión."
            finally:
                if conn and cursor: # Asegurarse de que conn y cursor existen antes de intentar cerrar
                    cursor.close()
                    conn.close()

    return render_template("docente_login.html", error=error)

# =========================
# LOGIN ESTUDIANTE
# =========================
@app.route("/estudiante_login", methods=["GET", "POST"])
def estudiante_login():
    error = ""
    if request.method == "POST":
        correo = request.form.get("correo")
        password = request.form.get("password")

        if not correo or not password:
            error = "Por favor, ingrese correo y contraseña."
        else:
            conn = None
            cursor = None
            try:
                conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
                cursor = conn.cursor()
                # Usar %s para placeholders en psycopg2
                cursor.execute("SELECT id, nombre, correo FROM estudiantes WHERE correo=%s AND password=%s", (correo, password))
                estudiante = cursor.fetchone()
                conn.close() # Cerrar conexión aquí después de fetchone

                if estudiante:
                    # psycopg2 devuelve tuplas, necesitamos acceder por índice
                    session["estudiante_id"] = estudiante[0] # ID del estudiante
                    session["estudiante_nombre"] = estudiante[1] # Nombre del estudiante
                    return redirect("/panel_estudiante")
                else:
                    error = "Correo o contraseña incorrectos."
            except (Exception, psycopg2.Error) as error:
                print(f"Error en login estudiante: {error}")
                error = "Error interno al intentar iniciar sesión."
            finally:
                if conn and cursor:
                    cursor.close()
                    conn.close()

    return render_template("estudiante_login.html", error=error)

# =========================
# PANEL DOCENTE
# =========================
@app.route("/panel_docente")
def panel_docente():
    if "docente_id" not in session:
        return redirect("/docente_login")

    docente_id = session["docente_id"]
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        cursor = conn.cursor()

        # Obtener datos del docente y su curso
        cursor.execute("""
            SELECT d.id, d.nombre, d.correo, c.nombre AS curso_nombre, d.curso_id
            FROM docentes d
            LEFT JOIN cursos c ON d.curso_id = c.id
            WHERE d.id = %s
        """, (docente_id,))
        docente = cursor.fetchone()

        if not docente:
            return "Docente no encontrado.", 404

        curso_id = docente[4] # El curso_id está en la posición 4 de la tupla

        # Obtener estudiantes del curso del docente
        if curso_id:
            cursor.execute("SELECT id, nombre, documento, correo FROM estudiantes WHERE curso_id = %s ORDER BY id DESC", (curso_id,))
            estudiantes = cursor.fetchall()
        else:
            estudiantes = [] # Si el docente no está asignado a un curso

        # Obtener módulos creados por este docente
        cursor.execute("SELECT id, titulo, descripcion FROM modulos WHERE docente_id = %s ORDER BY id DESC", (docente_id,))
        modulos = cursor.fetchall()

        # Obtener todos los contenidos (para visualización general, o se podría filtrar por módulo)
        # Si se quiere ver contenidos de los módulos del docente:
        modulo_ids = [m[0] for m in modulos] if modulos else []
        contenidos = []
        if modulo_ids:
            cursor.execute(f"SELECT id, titulo, tipo, url, modulo_id FROM contenidos WHERE modulo_id IN %s ORDER BY id DESC", (tuple(modulo_ids),))
            contenidos = cursor.fetchall()
        else:
            # Si no hay módulos, no hay contenidos asociados directamente
            pass # O podrías querer mostrar todos los contenidos de todos los módulos si el rol lo permite

        # Obtener entregas (se puede filtrar por los módulos del docente)
        entregas = []
        if modulo_ids:
            cursor.execute("""
                SELECT e.id, e.estudiante_id, e.modulo_id, e.archivo, e.fecha,
                       est.nombre AS estudiante_nombre, mod.titulo AS modulo_nombre
                FROM entregas e
                JOIN estudiantes est ON e.estudiante_id = est.id
                JOIN modulos mod ON e.modulo_id = mod.id
                WHERE e.modulo_id IN %s
                ORDER BY e.id DESC
            """, (tuple(modulo_ids),))
            entregas = cursor.fetchall()

        # Obtener notas (se puede filtrar por los estudiantes del curso del docente)
        notas = []
        estudiante_ids = [e[0] for e in estudiantes] if estudiantes else []
        if estudiante_ids:
            cursor.execute("""
                SELECT n.id, n.estudiante_id, n.materia, n.nota, est.nombre AS estudiante_nombre
                FROM notas n
                JOIN estudiantes est ON n.estudiante_id = est.id
                WHERE n.estudiante_id IN %s
                ORDER BY n.id DESC
            """, (tuple(estudiante_ids),))
            notas = cursor.fetchall()

        # Preparar datos para el template
        # Convertir tuplas a diccionarios para facilitar el acceso por nombre de columna en el template
        # Esto es opcional, pero mejora la legibilidad del template.
        # Si no se hace, se accede por índice (ej: docente[0] para id, docente[1] para nombre)
        docente_dict = {
            "id": docente[0], "nombre": docente[1], "correo": docente[2],
            "curso_nombre": docente[3], "curso_id": docente[4]
        }
        estudiantes_list = [{"id": e[0], "nombre": e[1], "documento": e[2], "correo": e[3]} for e in estudiantes]
        modulos_list = [{"id": m[0], "titulo": m[1], "descripcion": m[2]} for m in modulos]
        contenidos_list = [{"id": c[0], "titulo": c[1], "tipo": c[2], "url": c[3], "modulo_id": c[4]} for c in contenidos]
        entregas_list = [{"id": ent[0], "estudiante_id": ent[1], "modulo_id": ent[2], "archivo": ent[3], "fecha": ent[4],
                          "estudiante_nombre": ent[5], "modulo_nombre": ent[6]} for ent in entregas]
        notas_list = [{"id": n[0], "estudiante_id": n[1], "materia": n[2], "nota": n[3], "estudiante_nombre": n[4]} for n in notas]

        # Obtener todos los cursos para el dropdown de asignación de curso al docente
        cursor.execute("SELECT id, nombre FROM cursos ORDER BY nombre ASC")
        all_cursos = cursor.fetchall()
        all_cursos_list = [{"id": c[0], "nombre": c[1]} for c in all_cursos]

        return render_template("panel_docente.html",
                               docente=docente_dict,
                               estudiantes=estudiantes_list,
                               modulos=modulos_list,
                               contenidos=contenidos_list,
                               entregas=entregas_list,
                               notas=notas_list,
                               all_cursos=all_cursos_list)

    except (Exception, psycopg2.Error) as error:
        print(f"Error en panel_docente: {error}")
        return "Error al cargar el panel del docente."
    finally:
        if conn:
            cursor.close()
            conn.close()

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
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        cursor = conn.cursor()

        # Obtener datos del estudiante y su curso
        cursor.execute("""
            SELECT e.id, e.nombre, e.documento, e.correo, c.nombre AS curso_nombre, e.curso_id
            FROM estudiantes e
            LEFT JOIN cursos c ON e.curso_id = c.id
            WHERE e.id = %s
        """, (estudiante_id,))
        estudiante = cursor.fetchone()

        if not estudiante:
            return "Estudiante no encontrado.", 404

        curso_id = estudiante[5] # El curso_id está en la posición 5 de la tupla

        # Obtener módulos del curso del estudiante
        modulos = []
        if curso_id:
            cursor.execute("""
                SELECT m.id, m.titulo, m.descripcion, m.docente_id
                FROM modulos m
                JOIN docentes d ON m.docente_id = d.id
                WHERE d.curso_id = %s
                ORDER BY m.id DESC
            """, (curso_id,))
            modulos = cursor.fetchall()

        # Obtener contenidos asociados a los módulos del curso del estudiante
        contenidos = []
        modulo_ids = [m[0] for m in modulos] if modulos else []
        if modulo_ids:
            cursor.execute(f"SELECT c.id, c.titulo, c.tipo, c.url, c.modulo_id FROM contenidos c WHERE c.modulo_id IN %s ORDER BY c.id DESC", (tuple(modulo_ids),))
            contenidos = cursor.fetchall()

        # Obtener entregas del estudiante
        entregas = cursor.execute("""
            SELECT e.id, e.modulo_id, e.archivo, e.fecha, m.titulo AS modulo_nombre
            FROM entregas e
            JOIN modulos m ON e.modulo_id = m.id
            WHERE e.estudiante_id = %s
            ORDER BY e.id DESC
        """, (estudiante_id,)).fetchall()

        # Obtener notas del estudiante
        notas = cursor.execute("SELECT id, materia, nota FROM notas WHERE estudiante_id = %s ORDER BY id DESC", (estudiante_id,)).fetchall()

        # Preparar datos para el template
        estudiante_dict = {
            "id": estudiante[0], "nombre": estudiante[1], "documento": estudiante[2],
            "correo": estudiante[3], "curso_nombre": estudiante[4], "curso_id": estudiante[5]
        }
        modulos_list = [{"id": m[0], "titulo": m[1], "descripcion": m[2], "docente_id": m[3]} for m in modulos]
        contenidos_list = [{"id": c[0], "titulo": c[1], "tipo": c[2], "url": c[3], "modulo_id": c[4]} for c in contenidos]
        entregas_list = [{"id": ent[0], "modulo_id": ent[1], "archivo": ent[2], "fecha": ent[3], "modulo_nombre": ent[4]} for ent in entregas]
        notas_list = [{"id": n[0], "materia": n[1], "nota": n[2]} for n in notas]

        return render_template("panel_estudiante.html",
                               estudiante=estudiante_dict,
                               modulos=modulos_list,
                               contenidos=contenidos_list,
                               entregas=entregas_list,
                               notas=notas_list)

    except (Exception, psycopg2.Error) as error:
        print(f"Error en panel_estudiante: {error}")
        return "Error al cargar el panel del estudiante."
    finally:
        if conn:
            cursor.close()
            conn.close()

# =========================
# CREAR MODULO
# =========================
@app.route("/crear_modulo", methods=["POST"])
def crear_modulo():
    if "docente_id" not in session:
        return redirect("/docente_login")

    titulo = request.form.get("titulo")
    descripcion = request.form.get("descripcion")
    docente_id = session["docente_id"]

    if not titulo:
        return "El título del módulo es requerido.", 400

    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        cursor = conn.cursor()
        cursor.execute("INSERT INTO modulos (titulo, descripcion, docente_id) VALUES (%s, %s, %s)",
                       (titulo, descripcion, docente_id))
        conn.commit()
        return redirect("/panel_docente")
    except (Exception, psycopg2.Error) as error:
        print(f"Error al crear módulo: {error}")
        if conn:
            conn.rollback()
        return "Error al crear el módulo."
    finally:
        if conn:
            cursor.close()
            conn.close()

# =========================
# SUBIR ARCHIVO DOCENTE (Contenido de Módulo)
# =========================
@app.route("/subir_archivo/<int:modulo_id>", methods=["POST"])
def subir_archivo(modulo_id):
    if "docente_id" not in session:
        return redirect("/docente_login")

    archivo = request.files.get("archivo")
    titulo = request.form.get("titulo")
    tipo = request.form.get("tipo") # e.g., 'documento', 'video', 'enlace'

    if not archivo or archivo.filename == "":
        return "No se seleccionó ningún archivo.", 400
    if not titulo or not tipo:
        return "Título y tipo de contenido son requeridos.", 400

    nombre_archivo_original = secure_filename(archivo.filename)
    # Podrías querer generar un nombre de archivo único para evitar colisiones
    # o guardar en subcarpetas por módulo/docente. Por ahora, usamos el nombre seguro.
    ruta_guardado_fs = os.path.join(app.config["UPLOAD_FOLDER"], nombre_archivo_original)
    archivo.save(ruta_guardado_fs)

    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        cursor = conn.cursor()
        cursor.execute("INSERT INTO contenidos (titulo, tipo, url, modulo_id) VALUES (%s, %s, %s, %s)",
                       (titulo, tipo, nombre_archivo_original, modulo_id))
        conn.commit()
        return redirect("/panel_docente")
    except (Exception, psycopg2.Error) as error:
        print(f"Error al subir archivo de contenido: {error}")
        if conn:
            conn.rollback()
        # Considerar eliminar el archivo guardado si la inserción en DB falla
        if os.path.exists(ruta_guardado_fs):
            os.remove(ruta_guardado_fs)
        return "Error al guardar el contenido."
    finally:
        if conn:
            cursor.close()
            conn.close()

# =========================
# SUBIR TAREA ESTUDIANTE
# =========================
@app.route("/subir_tarea/<int:modulo_id>", methods=["POST"])
def subir_tarea(modulo_id):
    if "estudiante_id" not in session:
        return redirect("/estudiante_login")

    estudiante_id = session["estudiante_id"]
    archivo = request.files.get("archivo")

    if not archivo or archivo.filename == "":
        return "No seleccionaste archivo."
    # Validación de tipo de archivo (solo PDF)
    if not archivo.filename.lower().endswith(".pdf"):
        return "Solo se permiten archivos PDF."

    nombre_archivo_seguro = secure_filename(archivo.filename)
    ruta_guardado_fs = os.path.join(app.config["UPLOAD_FOLDER"], nombre_archivo_seguro)
    archivo.save(ruta_guardado_fs)

    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        cursor = conn.cursor()
        fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M:%S") # Formato más detallado
        cursor.execute("INSERT INTO entregas (estudiante_id, modulo_id, archivo, fecha) VALUES (%s, %s, %s, %s)",
                       (estudiante_id, modulo_id, nombre_archivo_seguro, fecha_actual))
        conn.commit()
        return redirect("/panel_estudiante")
    except (Exception, psycopg2.Error) as error:
        print(f"Error al subir tarea: {error}")
        if conn:
            conn.rollback()
        # Considerar eliminar el archivo guardado si la inserción en DB falla
        if os.path.exists(ruta_guardado_fs):
            os.remove(ruta_guardado_fs)
        return "Error al guardar la entrega."
    finally:
        if conn:
            cursor.close()
            conn.close()

# =========================
# GUARDAR NOTA
# =========================
@app.route("/guardar_nota", methods=["POST"])
def guardar_nota():
    if "docente_id" not in session:
        return redirect("/docente_login")

    estudiante_id = request.form.get("estudiante_id")
    materia = request.form.get("materia")
    nota_str = request.form.get("nota")

    if not estudiante_id or not materia or not nota_str:
        return "Faltan datos para guardar la nota.", 400

    try:
        nota = float(nota_str)
        # Validar rango de nota (ej: 0 a 10)
        if not (0 <= nota <= 10):
            return "La nota debe estar entre 0 y 10.", 400
    except ValueError:
        return "Formato de nota inválido.", 400

    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        cursor = conn.cursor()
        cursor.execute("INSERT INTO notas (estudiante_id, materia, nota) VALUES (%s, %s, %s)",
                       (estudiante_id, materia, nota))
        conn.commit()
        return redirect("/panel_docente")
    except (Exception, psycopg2.Error) as error:
        print(f"Error al guardar nota: {error}")
        if conn:
            conn.rollback()
        return "Error al guardar la nota."
    finally:
        if conn:
            cursor.close()
            conn.close()

# =========================
# VER ARCHIVOS SUBIDOS
# =========================
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    # Esta ruta sirve archivos desde la carpeta UPLOAD_FOLDER
    # Se usa para que los estudiantes puedan descargar sus entregas o ver contenidos subidos por docentes.
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear() # Limpia todas las claves de sesión
    return redirect("/login")

# =========================
# CERTIFICADO PDF
# =========================
@app.route("/certificado/<int:estudiante_id>")
def certificado(estudiante_id):
    # Verificar si el usuario está logueado (admin, docente o el propio estudiante)
    # Por simplicidad, aquí se asume que quien llama a esta ruta tiene permiso.
    # En una app real, se necesitaría una verificación de permisos.

    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        cursor = conn.cursor()

        # Obtener datos del estudiante y su curso
        cursor.execute(
            """
            SELECT e.id, e.nombre, c.nombre AS curso_nombre
            FROM estudiantes e
            LEFT JOIN cursos c ON e.curso_id = c.id
            WHERE e.id = %s
            """,
            (estudiante_id,),
        )
        estudiante = cursor.fetchone()

        # Obtener notas del estudiante
        cursor.execute(
            """
            SELECT nota FROM notas
            WHERE estudiante_id = %s
            """,
            (estudiante_id,),
        )
        notas = cursor.fetchall()

        if not estudiante:
            return "Estudiante no encontrado.", 404

        # Calcular promedio
        promedio = 0
        if notas:
            suma_notas = sum(nota[0] for nota in notas) # nota[0] porque fetchall devuelve tuplas
            promedio = round(suma_notas / len(notas), 1)

        # --- Generación del PDF ---
        nombre_pdf = f"certificado_{estudiante[0]}.pdf" # Usar ID del estudiante
        ruta_pdf = os.path.join(app.config["UPLOAD_FOLDER"], nombre_pdf)

        c = canvas.Canvas(ruta_pdf, pagesize=letter)
        width, height = letter

        # =========================
        # BORDE ELEGANTE
        # =========================
        c.setStrokeColor(HexColor("#0b1f4d")) # Azul oscuro
        c.setLineWidth(6)
        c.rect(30, 30, width - 60, height - 60) # Borde exterior
        c.setLineWidth(2)
        c.rect(45, 45, width - 90, height - 90) # Borde interior

        # =========================
        # LOGO
        # =========================
        logo_path = "static/img/logorenova.png" # Asegúrate de que esta ruta sea correcta
        if os.path.exists(logo_path):
            c.drawImage(
                logo_path,
                width / 2 - 60, # Centrar horizontalmente
                height - 180, # Posición vertical (cerca de la parte superior)
                width=120,
                height=120,
                preserveAspectRatio=True
            )
        else:
            print(f"Advertencia: Logo no encontrado en {logo_path}")

        # =========================
        # TÍTULO
        # =========================
        c.setFillColor(HexColor("#0b1f4d")) # Azul oscuro
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(width / 2, height - 240, "CERTIFICADO ACADÉMICO") # Ajuste de posición

        # =========================
        # TEXTO INTRODUCTORIO
        # =========================
        c.setFont("Helvetica", 16)
        c.drawCentredString(width / 2, height - 290, "El Instituto Renova certifica que:")

        # =========================
        # NOMBRE DEL ESTUDIANTE
        # =========================
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(width / 2, height - 340, estudiante[1]) # Nombre del estudiante

        # =========================
        # CURSO
        # =========================
        c.setFont("Helvetica", 16)
        c.drawCentredString(width / 2, height - 390, "Completó satisfactoriamente el programa:")
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(width / 2, height - 425, estudiante[2]) # Nombre del curso

        # =========================
        # PROMEDIO
        # =========================
        c.setFont("Helvetica", 16)
        c.drawCentredString(width / 2, height - 475, f"Promedio académico final: {promedio}")

        # =========================
        # FECHA DE EXPEDICIÓN
        # =========================
        fecha_expedicion = datetime.now().strftime("%d de %B de %Y") # Formato más amigable
        c.setFont("Helvetica", 14)
        c.drawCentredString(width / 2, height - 510, f"Fecha de expedición: {fecha_expedicion}")

        # =========================
        # CÓDIGO DE CERTIFICADO
        # =========================
        codigo_certificado = f"RENOVA-{estudiante[0]}-{datetime.now().year}"
        c.setFont("Helvetica", 12)
        c.drawCentredString(width / 2, height - 540, f"Código de certificado: {codigo_certificado}")

        # =========================
        # FIRMA
        # =========================
        # Línea para la firma
        c.line(width / 2 - 120, height - 620, width / 2 + 120, height - 620) # Centrada
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width / 2, height - 640, "Dirección Académica")
        c.setFont("Helvetica", 12)
        c.drawCentredString(width / 2, height - 660, "Instituto Renova")

        # =========================
        # PIE DE PÁGINA
        # =========================
        c.setFont("Helvetica-Oblique", 10)
        c.drawCentredString(width / 2, 80, "Documento generado automáticamente por la plataforma educativa Renova")

        c.save() # Guarda el PDF

        # Enviar el PDF generado al navegador como descarga
        return send_from_directory(
            app.config["UPLOAD_FOLDER"],
            nombre_pdf,
            as_attachment=True # Indica que debe ser descargado
        )

    except (Exception, psycopg2.Error) as error:
        print(f"Error al generar certificado: {error}")
        return "Error al generar el certificado."
    finally:
        if conn:
            cursor.close()
            conn.close()

# =========================
# RUN
# =========================
if __name__ == "__main__":
        app.run(debug=True)