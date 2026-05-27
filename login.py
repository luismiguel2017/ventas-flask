from flask import Blueprint, render_template, request, redirect, url_for, session
import psycopg2, os

login_bp = Blueprint("login", __name__)

def get_conn():
    return psycopg2.connect(
           host=os.environ.get("DB_HOST"),
        port="5432",
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASS"),
        options='-c client_encoding=UTF8'
    )

@login_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        contrasena = request.form["contrasena"]

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
