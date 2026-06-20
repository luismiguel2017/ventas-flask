# -*- coding: utf-8 -*-
import imaplib
import email
import os
import pandas as pd
import psycopg2
from io import BytesIO
from datetime import datetime
from flask import Blueprint, render_template_string

yape_bp = Blueprint('yape', __name__)

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS")
    )

# =====================
# IMPORTAR DESDE GMAIL
# =====================
@yape_bp.route("/yape/importar")
def importar_yape():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login("luis.adriano.ga@gmail.com", os.getenv("GMAIL_PASS"))
        mail.select("inbox")

        status, mensajes = mail.search(None, '(FROM "luis_007_ga@hotmail.com" SUBJECT "Historial de Movimientos")')
        ids = mensajes[0].split()

        if not ids:
            mail.logout()
            return "<h3>⚠️ No se encontró ningún reporte Yape en Gmail.</h3>"

        status, datos = mail.fetch(ids[-1], '(RFC822)')
        mensaje = email.message_from_bytes(datos[0][1])
        mail.logout()

        for parte in mensaje.walk():
            if parte.get_content_disposition() == "attachment":
                nombre = parte.get_filename()
                if nombre and nombre.endswith(".xlsx"):
                    contenido = parte.get_payload(decode=True)
                    df = pd.read_excel(BytesIO(contenido), header=None)
                    df.columns = ["Tipo", "Origen", "Destino", "Monto", "Mensaje", "Fecha"]
                    df = df[df["Tipo"] == "TE PAGÓ"]
                    df = df[["Tipo", "Origen", "Monto", "Fecha"]]

                    # Convertir fecha de "DD/MM/YYYY HH:MM:SS" a datetime real
                    def parsear_fecha(valor):
                        if isinstance(valor, str):
                            return datetime.strptime(valor, "%d/%m/%Y %H:%M:%S")
                        return valor  # ya es datetime (pandas a veces lo detecta solo)

                    df["Fecha"] = df["Fecha"].apply(parsear_fecha)

                    conn = get_conn()
                    cur = conn.cursor()
                    insertados = 0
                    for _, row in df.iterrows():
                        cur.execute("""
                            INSERT INTO yape_pagos (tipo, origen, monto, fecha)
                            SELECT %s, %s, %s, %s
                            WHERE NOT EXISTS (
                                SELECT 1 FROM yape_pagos
                                WHERE origen = %s AND monto = %s AND fecha = %s
                            )
                        """, (row["Tipo"], row["Origen"], row["Monto"], row["Fecha"],
                              row["Origen"], row["Monto"], row["Fecha"]))
                        if cur.rowcount > 0:
                            insertados += 1

                    conn.commit()
                    cur.close()
                    conn.close()

                    # Redirigir al reporte con mensaje de éxito
                    from flask import redirect, url_for
                    return redirect(f"/yape?importados={insertados}")

        return "<h3>⚠️ No se encontró adjunto Excel en el correo.</h3>"

    except Exception as e:
        return f"<h3>❌ Error: {str(e)}</h3>"


# =====================
# VER REPORTE DESDE DB
# =====================
@yape_bp.route("/yape")
def reporte_yape():
    from flask import request
    importados = request.args.get("importados", None)

    try:
        conn = get_conn()
        cur = conn.cursor()

        # Total general
        cur.execute("SELECT COALESCE(SUM(monto),0) FROM yape_pagos")
        total_general = cur.fetchone()[0]

        # Total hoy
        cur.execute("SELECT COALESCE(SUM(monto),0) FROM yape_pagos WHERE DATE(fecha) = CURRENT_DATE")
        total_hoy = cur.fetchone()[0]

        # Cantidad hoy
        cur.execute("SELECT COUNT(*) FROM yape_pagos WHERE DATE(fecha) = CURRENT_DATE")
        cantidad_hoy = cur.fetchone()[0]

        # Todos los registros
        cur.execute("SELECT tipo, origen, monto, fecha FROM yape_pagos ORDER BY fecha DESC")
        filas = cur.fetchall()

        cur.close()
        conn.close()

        return render_template_string(HTML_TEMPLATE,
                                      filas=filas,
                                      total_general=total_general,
                                      total_hoy=total_hoy,
                                      cantidad_hoy=cantidad_hoy,
                                      importados=importados)
    except Exception as e:
        return f"<h3>❌ Error: {str(e)}</h3>"


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Yape – Cafetería Walter</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet"/>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Lato:wght@300;400;700&display=swap" rel="stylesheet"/>
  <style>
    :root {
      --bg:#0e0804; --sidebar-bg:#1a0e06; --topbar-bg:#1e1208;
      --card-bg:rgba(40,22,8,0.90); --card-border:rgba(210,160,90,0.15);
      --accent:#c8883a; --cream:#f2e4cc; --muted:#8a6a48;
      --green:#4caf7d; --yape:#6b21a8; --yape2:#9333ea;
    }
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
    body{font-family:'Lato',sans-serif;background:var(--bg);color:var(--cream);min-height:100vh;display:flex;}

    /* SIDEBAR */
    .sidebar{width:240px;min-height:100vh;background:var(--sidebar-bg);border-right:1px solid var(--card-border);display:flex;flex-direction:column;position:fixed;top:0;left:0;z-index:100;transition:transform .3s;}
    .sidebar-header{padding:1.4rem 1.2rem;border-bottom:1px solid var(--card-border);display:flex;align-items:center;gap:.7rem;}
    .cup-icon{width:36px;height:36px;background:linear-gradient(145deg,#c8883a,#7c4a1a);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1rem;color:#fff;flex-shrink:0;}
    .sidebar-header span{font-family:'Playfair Display',serif;font-size:1.05rem;}
    .sidebar-nav{padding:1rem 0;flex:1;}
    .nav-item{display:flex;align-items:center;gap:.8rem;padding:.75rem 1.4rem;color:var(--muted);font-size:.93rem;cursor:pointer;transition:all .2s;border-left:3px solid transparent;text-decoration:none;}
    .nav-item:hover{color:var(--cream);background:rgba(200,136,58,.08);}
    .nav-item.active{color:var(--accent);border-left-color:var(--accent);background:rgba(200,136,58,.12);}
    .nav-item i{font-size:1.1rem;width:20px;text-align:center;}

    /* MAIN */
    .main{margin-left:240px;flex:1;display:flex;flex-direction:column;}
    .topbar{background:var(--topbar-bg);border-bottom:1px solid var(--card-border);padding:.85rem 1.5rem;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:50;}
    .topbar h1{font-family:'Playfair Display',serif;font-size:1.25rem;margin:0;}
    .user-pill{display:flex;align-items:center;gap:.5rem;background:rgba(200,136,58,.12);border:1px solid var(--card-border);border-radius:20px;padding:.35rem .9rem;font-size:.85rem;}
    .menu-toggle{display:none;background:none;border:none;color:var(--cream);font-size:1.3rem;cursor:pointer;}

    /* CONTENT */
    .content{padding:1.5rem;flex:1;overflow-y:auto;}

    /* KPIs */
    .kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-bottom:1.5rem;}
    .kpi{background:var(--card-bg);border:1px solid var(--card-border);border-radius:12px;padding:1.2rem;text-align:center;}
    .kpi-label{font-size:.75rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:.5rem;}
    .kpi-value{font-family:'Playfair Display',serif;font-size:1.5rem;color:var(--accent);font-weight:700;}
    .kpi-value.yape-color{color:var(--yape2);}
    .kpi-value.green{color:var(--green);}

    /* TABLA */
    .tabla-section{background:var(--card-bg);border:1px solid var(--card-border);border-radius:14px;overflow:hidden;}
    .tabla-hdr{padding:1rem 1.2rem;border-bottom:1px solid var(--card-border);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.8rem;}
    .tabla-title{font-size:.88rem;font-weight:700;color:var(--cream);}

    .btn-importar{background:linear-gradient(135deg,#6b21a8,#9333ea);border:none;border-radius:8px;color:#fff;font-family:'Lato',sans-serif;font-size:.85rem;font-weight:700;padding:.5rem 1.1rem;cursor:pointer;display:inline-flex;align-items:center;gap:.4rem;text-decoration:none;transition:opacity .2s;}
    .btn-importar:hover{opacity:.85;color:#fff;}

    .search-inp{background:rgba(255,255,255,.05);border:1px solid var(--card-border);border-radius:7px;color:var(--cream);font-size:.8rem;padding:.35rem .8rem;outline:none;width:180px;}
    .search-inp:focus{border-color:var(--accent);}

    table{width:100%;border-collapse:collapse;font-size:.82rem;}
    thead tr{border-bottom:1px solid var(--card-border);}
    thead th{padding:.65rem 1rem;font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);text-align:left;}
    tbody tr{border-bottom:1px solid rgba(210,160,90,.07);transition:background .15s;}
    tbody tr:hover{background:rgba(200,136,58,.04);}
    tbody tr:last-child{border:none;}
    tbody td{padding:.75rem 1rem;color:var(--cream);}

    .monto{color:var(--green);font-weight:700;}

    /* TOAST */
    .toast-c{position:fixed;bottom:1.5rem;right:1.5rem;z-index:300;background:#1e1208;border-radius:10px;padding:.8rem 1.2rem;display:flex;align-items:center;gap:.6rem;font-size:.88rem;font-weight:700;box-shadow:0 8px 24px rgba(0,0,0,.5);border:1px solid var(--green);color:var(--green);}

    .overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:99;}
    .overlay.show{display:block;}

    @media(max-width:900px){.kpis{grid-template-columns:repeat(2,1fr);}}
    @media(max-width:768px){
      .sidebar{transform:translateX(-100%);}
      .sidebar.open{transform:translateX(0);}
      .main{margin-left:0;}
      .menu-toggle{display:block;}
      .content{padding:1rem;}
      .kpis{grid-template-columns:1fr;}
      .search-inp{width:100%;}
    }
  </style>
</head>
<body>

<!-- Sidebar -->
<aside class="sidebar" id="sidebar">
  <div class="sidebar-header">
    <div class="cup-icon"><i class="bi bi-cup-hot-fill"></i></div>
    <span>Cafetería Walter</span>
    <button class="menu-toggle ms-auto" id="closeBtn" style="background:none;border:none;color:var(--muted);cursor:pointer;font-size:1.1rem;"><i class="bi bi-x-lg"></i></button>
  </div>
  <nav class="sidebar-nav">
    <a class="nav-item" href="/"><i class="bi bi-house-fill"></i> Inicio</a>
    <a class="nav-item" href="/mesas"><i class="bi bi-grid-3x3-gap-fill"></i> Mesas</a>
    <a class="nav-item" href="/registrar"><i class="bi bi-plus-circle-fill"></i> Ingresar Producto</a>
    <a class="nav-item" href="/delivery"><i class="bi bi-bicycle"></i> Delivery</a>
    <a class="nav-item active" href="/yape"><i class="bi bi-phone-fill"></i> Yape</a>
  </nav>
</aside>
<div class="overlay" id="overlay"></div>

<!-- Main -->
<div class="main">
  <header class="topbar">
    <div style="display:flex;align-items:center;gap:1rem;">
      <button class="menu-toggle" id="openBtn"><i class="bi bi-list"></i></button>
      <div style="width:32px;height:32px;background:linear-gradient(135deg,#6b21a8,#9333ea);border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:.85rem;flex-shrink:0;">Y</div>
      <h1>Reporte Yape</h1>
    </div>
    <div class="user-pill"><i class="bi bi-person-circle"></i> Hola, admin</div>
  </header>

  <div class="content">

    {% if importados %}
    <div style="background:rgba(76,175,125,.15);border:1px solid var(--green);border-radius:10px;padding:.8rem 1.2rem;margin-bottom:1.2rem;color:var(--green);font-size:.88rem;font-weight:700;">
      <i class="bi bi-check-circle-fill me-2"></i> {{ importados }} pagos nuevos importados correctamente
    </div>
    {% endif %}

    <!-- KPIs -->
    <div class="kpis">
      <div class="kpi">
        <div class="kpi-label">Total recibido hoy</div>
        <div class="kpi-value green">S/ {{ "%.2f"|format(total_hoy) }}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Pagos hoy</div>
        <div class="kpi-value yape-color">{{ cantidad_hoy }}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Total histórico</div>
        <div class="kpi-value">S/ {{ "%.2f"|format(total_general) }}</div>
      </div>
    </div>

    <!-- TABLA -->
    <div class="tabla-section">
      <div class="tabla-hdr">
        <div class="tabla-title"><i class="bi bi-table me-2" style="color:var(--accent)"></i>Pagos recibidos</div>
        <div style="display:flex;gap:.6rem;align-items:center;flex-wrap:wrap;">
          <input class="search-inp" type="text" placeholder="Buscar nombre…" oninput="filtrar(this.value)"/>
          <a href="/yape/importar" class="btn-importar"><i class="bi bi-cloud-download-fill"></i> Importar desde Gmail</a>
        </div>
      </div>
      <div style="overflow-x:auto">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Tipo</th>
              <th>Origen</th>
              <th>Monto</th>
              <th>Fecha</th>
            </tr>
          </thead>
          <tbody id="tablabody">
            {% for f in filas %}
            <tr>
              <td style="color:var(--muted);font-size:.75rem">{{ loop.index }}</td>
              <td><span style="background:rgba(76,175,125,.15);color:var(--green);padding:.15rem .5rem;border-radius:20px;font-size:.7rem;font-weight:700;">{{ f[0] }}</span></td>
              <td><strong>{{ f[1] }}</strong></td>
              <td class="monto">S/ {{ "%.2f"|format(f[2]) }}</td>
              <td style="color:var(--muted);">{{ f[3] }}</td>
            </tr>
            {% endfor %}
            {% if not filas %}
            <tr><td colspan="5" style="text-align:center;padding:2rem;color:var(--muted);">Sin datos — haz clic en "Importar desde Gmail"</td></tr>
            {% endif %}
          </tbody>
        </table>
      </div>
    </div>

  </div>
</div>

<script>
function filtrar(q) {
  const f = q.toLowerCase();
  document.querySelectorAll('#tablabody tr').forEach(tr => {
    const txt = tr.textContent.toLowerCase();
    tr.style.display = txt.includes(f) ? '' : 'none';
  });
}

document.getElementById('openBtn').addEventListener('click', () => {
  document.getElementById('sidebar').classList.add('open');
  document.getElementById('overlay').classList.add('show');
});
['closeBtn','overlay'].forEach(id =>
  document.getElementById(id).addEventListener('click', () => {
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('overlay').classList.remove('show');
  })
);
</script>
</body>
</html>
"""