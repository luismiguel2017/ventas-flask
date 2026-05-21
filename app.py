from flask import Flask, render_template, request, redirect, url_for, jsonify
import psycopg2

app = Flask(__name__)

# Conexión a PostgreSQL
def get_conn():
    return psycopg2.connect(
        host="localhost",
        port="5432",
        database="ventas",
        user="postgres",
        password="luis1988",   # cámbiala si usas otra contraseña
        options='-c client_encoding=UTF8'
    )

# Página principal
@app.route("/")
def index():
    return render_template("index.html")

# Registrar producto
@app.route("/registrar", methods=["POST"])
def registrar():
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

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
