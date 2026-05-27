# login.py
from flask import Blueprint, render_template, request, redirect, url_for, session
import psycopg2

# Crear blueprint
login_bp = Blueprint("login", __name__)

@login_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        contrasena = request.form["contrasena"]

        # Validar contra la base de datos en Render
        conn = psycopg2.connect("dbname=ventas user=postgres password=tu_password host=tu_host")
        cur = conn.cursor()
        cur.execute("SELECT * FROM usuarios WHERE usuario=%s AND contrasena=%s", (usuario, contrasena))
        user = cur.fetchone()
        conn.close()

        if user:
            session["usuario"] = usuario
            return redirect(url_for("dashboard"))
        else:
            return "⚠️ Usuario o contraseña incorrectos"

    return render_template("login.html")

@login_bp.route("/logout")
def logout():
    session.pop("usuario", None)
    return redirect(url_for("login"))
