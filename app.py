from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import psycopg2
import os
from login import login_bp   # Importar el Blueprint de login

app = Flask(__name__)
app.secret_key = "clave_secreta_segura"  # Necesario para manejar sesiones

# Conexión a PostgreSQL usando variables de entorno
def get_conn():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        port="5432",
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASS"),
        options='-c client_encoding=UTF8'
    )

# Registrar el Blueprint de login
app.register_blueprint(login_bp)

# Página principal (dashboard protegido)
@app.route("/")
def index():
    if "usuario" in session:
        return render_template("index.html", usuario=session["usuario"], rol=session.get("rol"))
    else:
        return redirect(url_for("login.login"))  # Redirige al login si no hay sesión

# Registrar producto (solo si hay sesión)
@app.route("/registrar", methods=["POST"])
def registrar():
    if "usuario" not in session:
        return redirect(url_for("login.login"))

    nombre = request.form["nombre"]
    precio = request.form["precio"]

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO productos (nombre, precio) VALUES (%s, %s)", (nombre, precio))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for("index"))

# Listar productos (incluye id)
@app.route("/listar_productos")
def listar_productos():
    if "usuario" not in session:
        return redirect(url_for("login.login"))

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, precio, id FROM productos ORDER BY id DESC;")
    productos = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(productos)

# Registrar venta
@app.route("/registrar_venta", methods=["POST"])
def registrar_venta():
    if "usuario" not in session:
        return redirect(url_for("login.login"))

    productos = request.json.get("productos", [])

    conn = get_conn()
    cursor = conn.cursor()

    # 1. Crear cabecera de la venta
    cursor.execute("INSERT INTO venta DEFAULT VALUES RETURNING id;")
    venta_id = cursor.fetchone()[0]

    # 2. Insertar cada detalle
    for prod in productos:
        producto_id = prod["id"]
        nombre = prod["nombre"]
        cantidad = prod["cantidad"]

        cursor.execute("""
            INSERT INTO venta_detalle (venta_id, producto_id, nombre, cantidad)
            VALUES (%s, %s, %s, %s)
        """, (venta_id, producto_id, nombre, cantidad))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"mensaje": "Venta registrada", "venta_id": venta_id})

# Endpoint de prueba de conexión
@app.route("/test_db")
def test_db():
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        cursor.close()
        conn.close()
        return jsonify({"status": "ok", "message": "Conexión exitosa a PostgreSQL"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


# Listar mesas con total acumulado
@app.route("/listar_mesas")
def listar_mesas():
    if "usuario" not in session:
        return redirect(url_for("login.login"))
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.id, m.numero, m.estado,
               COALESCE(SUM(mp.precio * mp.cantidad), 0) as total
        FROM mesas m
        LEFT JOIN mesa_pedido mp ON m.id = mp.mesa_id
        GROUP BY m.id, m.numero, m.estado
        ORDER BY m.numero
    """)
    mesas = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{"id": r[0], "numero": r[1], "estado": r[2], "total": float(r[3])} for r in mesas])

# Agregar producto a mesa
@app.route("/agregar_mesa", methods=["POST"])
def agregar_mesa():
    if "usuario" not in session:
        return redirect(url_for("login.login"))
    data = request.json
    mesa_id = data["mesa_id"]
    productos = data["productos"]
    conn = get_conn()
    cur = conn.cursor()
    # Actualizar estado mesa a ocupada
    cur.execute("UPDATE mesas SET estado='ocupada' WHERE id=%s", (mesa_id,))
    for p in productos:
        # Si ya existe el producto en la mesa, sumar cantidad
        cur.execute("""
            SELECT id, cantidad FROM mesa_pedido 
            WHERE mesa_id=%s AND producto_id=%s
        """, (mesa_id, p["id"]))
        existe = cur.fetchone()
        if existe:
            cur.execute("UPDATE mesa_pedido SET cantidad=%s WHERE id=%s",
                       (existe[1] + p["cantidad"], existe[0]))
        else:
            cur.execute("""
                INSERT INTO mesa_pedido (mesa_id, producto_id, nombre, cantidad, precio)
                VALUES (%s, %s, %s, %s, %s)
            """, (mesa_id, p["id"], p["nombre"], p["cantidad"], p["precio"]))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})

# Obtener pedido de una mesa
@app.route("/pedido_mesa/<int:mesa_id>")
def pedido_mesa(mesa_id):
    if "usuario" not in session:
        return redirect(url_for("login.login"))
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT producto_id, nombre, cantidad, precio
        FROM mesa_pedido WHERE mesa_id=%s
    """, (mesa_id,))
    pedido = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{"id": r[0], "nombre": r[1], "cantidad": r[2], "precio": float(r[3])} for r in pedido])

# Confirmar venta de mesa
@app.route("/confirmar_mesa", methods=["POST"])
def confirmar_mesa():
    if "usuario" not in session:
        return redirect(url_for("login.login"))
    data = request.json
    mesa_id = data["mesa_id"]
    conn = get_conn()
    cur = conn.cursor()
    # Obtener pedido
    cur.execute("SELECT producto_id, nombre, cantidad, precio FROM mesa_pedido WHERE mesa_id=%s", (mesa_id,))
    pedido = cur.fetchall()
    if pedido:
        # Crear venta
        cur.execute("INSERT INTO venta DEFAULT VALUES RETURNING id")
        venta_id = cur.fetchone()[0]
        # Insertar detalle
        for p in pedido:
            cur.execute("""
                INSERT INTO venta_detalle (venta_id, producto_id, nombre, cantidad)
                VALUES (%s, %s, %s, %s)
            """, (venta_id, p[0], p[1], p[2]))
        # Limpiar mesa_pedido
        cur.execute("DELETE FROM mesa_pedido WHERE mesa_id=%s", (mesa_id,))
        # Mesa vuelve a libre
        cur.execute("UPDATE mesas SET estado='libre' WHERE id=%s", (mesa_id,))
        conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
