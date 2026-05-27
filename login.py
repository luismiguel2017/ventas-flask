from flask import Blueprint, render_template, request, redirect, url_for, session
from app import get_conn   # Importar la función de conexión centralizada

# Crear blueprint
login_bp = Blueprint("login", __name__)

@login_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        contrasena = request.form["contrasena"]

        # Usar la conexión centralizada
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, rol FROM usuarios WHERE usuario=%s AND contrasena=%s", (usuario, contrasena))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            session["usuario"] = usuario
            session["rol"] = user[1]
            return redirect(url_for("index"))  # redirige al dashboard principal
        else:
            return render_template("login.html", error="⚠️ Usuario o contraseña incorrectos")

    return render_template("login.html")

@login_bp.route("/logout")
def logout():
    session.pop("usuario", None)
    return redirect(url_for("login.login"))
