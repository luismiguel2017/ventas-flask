# -*- coding: utf-8 -*-
import imaplib
import email
import os
import pandas as pd
import psycopg2
from io import BytesIO
from datetime import datetime
from flask import Blueprint, render_template_string, request, redirect, jsonify, jsonify

yape_bp = Blueprint('yape', __name__)

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS")
    )

# =====================
# IMPORTAR YAPE DESDE GMAIL
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

                    def parsear_fecha(valor):
                        if isinstance(valor, str):
                            return datetime.strptime(valor, "%d/%m/%Y %H:%M:%S")
                        return valor

                    df["Fecha"] = df["Fecha"].apply(parsear_fecha)

                    conn = get_conn()
                    cur = conn.cursor()
                    insertados = 0
                    for _, row in df.iterrows():
                        cur.execute("""
                            INSERT INTO yape_pagos (tipo, origen, monto, fecha)
                            SELECT 'Yape', %s, %s, %s
                            WHERE NOT EXISTS (
                                SELECT 1 FROM yape_pagos
                                WHERE origen = %s AND monto = %s AND fecha = %s
                            )
                        """, (row["Origen"], row["Monto"], row["Fecha"],
                              row["Origen"], row["Monto"], row["Fecha"]))
                        if cur.rowcount > 0:
                            insertados += 1

                    conn.commit()
                    cur.close()
                    conn.close()

                    return redirect(f"/yape?importados={insertados}")

        return "<h3>⚠️ No se encontró adjunto Excel en el correo.</h3>"

    except Exception as e:
        return f"<h3>❌ Error: {str(e)}</h3>"


# =====================
# INSERTAR PLIN MASIVO
# =====================
@yape_bp.route("/yape/insertar_plin", methods=["POST"])
def insertar_plin():
    try:
        data = request.json
        pagos = data.get("pagos", [])
        fecha = data.get("fecha")

        conn = get_conn()
        cur = conn.cursor()
        insertados = 0

        for p in pagos:
            cur.execute("""
                INSERT INTO yape_pagos (tipo, origen, monto, fecha)
                SELECT 'PLIN', %s, %s, %s
                WHERE NOT EXISTS (
                    SELECT 1 FROM yape_pagos
                    WHERE origen = %s AND monto = %s AND DATE(fecha) = %s
                )
            """, (p["nombre"], p["monto"], fecha,
                  p["nombre"], p["monto"], fecha))
            if cur.rowcount > 0:
                insertados += 1

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"ok": True, "insertados": insertados})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# =====================
# VER REPORTE DESDE DB
# =====================
@yape_bp.route("/yape")
def reporte_yape():
    importados = request.args.get("importados", None)
    fecha_filtro = request.args.get("fecha", datetime.now().strftime("%Y-%m-%d"))

    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT COALESCE(SUM(monto),0) FROM yape_pagos
            WHERE DATE(fecha AT TIME ZONE 'UTC' AT TIME ZONE 'America/Lima') = %s
        """, (fecha_filtro,))
        total_hoy = cur.fetchone()[0]

        cur.execute("""
            SELECT 'YAPE' as tipo, origen, monto, fecha FROM yape_pagos
            WHERE DATE(fecha AT TIME ZONE 'UTC' AT TIME ZONE 'America/Lima') = %s
            ORDER BY fecha DESC
        """, (fecha_filtro,))
        filas = cur.fetchall()

        cur.close()
        conn.close()

        return render_template_string(HTML_TEMPLATE,
                                      filas=filas,
                                      total_hoy=total_hoy,
                                      importados=importados,
                                      fecha_filtro=fecha_filtro)
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
      --green:#4caf7d; --red:#e05050; --yape2:#9333ea; --plin:#00a86b;
    }
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
    body{font-family:'Lato',sans-serif;background:var(--bg);color:var(--cream);min-height:100vh;display:flex;}

    .sidebar{width:240px;min-height:100vh;background:var(--sidebar-bg);border-right:1px solid var(--card-border);display:flex;flex-direction:column;position:fixed;top:0;left:0;z-index:100;transition:transform .3s;}
    .sidebar-header{padding:1.4rem 1.2rem;border-bottom:1px solid var(--card-border);display:flex;align-items:center;gap:.7rem;}
    .cup-icon{width:36px;height:36px;background:linear-gradient(145deg,#c8883a,#7c4a1a);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1rem;color:#fff;flex-shrink:0;}
    .sidebar-header span{font-family:'Playfair Display',serif;font-size:1.05rem;}
    .sidebar-nav{padding:1rem 0;flex:1;}
    .nav-item{display:flex;align-items:center;gap:.8rem;padding:.75rem 1.4rem;color:var(--muted);font-size:.93rem;cursor:pointer;transition:all .2s;border-left:3px solid transparent;text-decoration:none;}
    .nav-item:hover{color:var(--cream);background:rgba(200,136,58,.08);}
    .nav-item.active{color:var(--accent);border-left-color:var(--accent);background:rgba(200,136,58,.12);}
    .nav-item i{font-size:1.1rem;width:20px;text-align:center;}

    .main{margin-left:240px;flex:1;display:flex;flex-direction:column;}
    .topbar{background:var(--topbar-bg);border-bottom:1px solid var(--card-border);padding:.85rem 1.5rem;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:50;}
    .topbar h1{font-family:'Playfair Display',serif;font-size:1.25rem;margin:0;}
    .user-pill{display:flex;align-items:center;gap:.5rem;background:rgba(200,136,58,.12);border:1px solid var(--card-border);border-radius:20px;padding:.35rem .9rem;font-size:.85rem;}
    .menu-toggle{display:none;background:none;border:none;color:var(--cream);font-size:1.3rem;cursor:pointer;}
    .content{padding:1.5rem;flex:1;overflow-y:auto;}

    .tabs{display:flex;gap:.5rem;margin-bottom:1.5rem;}
    .tab{background:var(--card-bg);border:1px solid var(--card-border);border-radius:8px;padding:.5rem 1.2rem;font-size:.85rem;color:var(--muted);cursor:pointer;transition:all .2s;}
    .tab.active{border-color:var(--accent);color:var(--accent);background:rgba(200,136,58,.10);font-weight:700;}

    .vista{display:none;}
    .vista.active{display:block;animation:fadeUp .3s ease;}
    @keyframes fadeUp{from{opacity:0;transform:translateY(10px);}to{opacity:1;transform:translateY(0);}}

    .kpi{background:var(--card-bg);border:1px solid var(--card-border);border-radius:12px;padding:1.2rem;text-align:center;margin-bottom:1.2rem;max-width:250px;}
    .kpi-label{font-size:.75rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:.5rem;}
    .kpi-value{font-family:'Playfair Display',serif;font-size:1.5rem;color:var(--green);font-weight:700;}

    .filtro-wrap{background:var(--card-bg);border:1px solid var(--card-border);border-radius:12px;padding:1rem 1.2rem;margin-bottom:1.2rem;display:flex;align-items:center;gap:1rem;flex-wrap:wrap;}
    .filtro-label{font-size:.75rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;}
    .date-inp{background:rgba(255,255,255,.05);border:1px solid var(--card-border);border-radius:7px;color:var(--cream);font-size:.85rem;padding:.4rem .8rem;outline:none;}
    .date-inp:focus{border-color:var(--accent);}
    .btn-filtrar{background:linear-gradient(135deg,#d49040,#a0601a);border:none;border-radius:7px;color:#fff;font-family:'Lato',sans-serif;font-size:.82rem;font-weight:700;padding:.4rem .9rem;cursor:pointer;}
    .btn-hoy{background:rgba(200,136,58,.15);border:1px solid rgba(200,136,58,.3);border-radius:7px;color:var(--accent);font-family:'Lato',sans-serif;font-size:.82rem;font-weight:700;padding:.4rem .9rem;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:.3rem;}

    .tabla-section{background:var(--card-bg);border:1px solid var(--card-border);border-radius:14px;overflow:hidden;}
    .tabla-hdr{padding:1rem 1.2rem;border-bottom:1px solid var(--card-border);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.8rem;}
    .tabla-title{font-size:.88rem;font-weight:700;color:var(--cream);}
    .btn-importar{background:linear-gradient(135deg,#6b21a8,#9333ea);border:none;border-radius:8px;color:#fff;font-family:'Lato',sans-serif;font-size:.82rem;font-weight:700;padding:.45rem 1rem;cursor:pointer;display:inline-flex;align-items:center;gap:.4rem;text-decoration:none;}
    .search-inp{background:rgba(255,255,255,.05);border:1px solid var(--card-border);border-radius:7px;color:var(--cream);font-size:.8rem;padding:.35rem .8rem;outline:none;width:160px;}
    .search-inp:focus{border-color:var(--accent);}

    table{width:100%;border-collapse:collapse;font-size:.82rem;}
    thead tr{border-bottom:1px solid var(--card-border);}
    thead th{padding:.65rem 1rem;font-size:.7rem;font-weight:700;text-transform:uppercase;color:var(--muted);text-align:left;}
    tbody tr{border-bottom:1px solid rgba(210,160,90,.07);transition:background .15s;}
    tbody tr:hover{background:rgba(200,136,58,.04);}
    tbody tr:last-child{border:none;}
    tbody td{padding:.75rem 1rem;color:var(--cream);}
    .monto{color:var(--green);font-weight:700;}
    .badge-yape{background:rgba(147,51,234,.15);color:var(--yape2);padding:.15rem .5rem;border-radius:20px;font-size:.7rem;font-weight:700;}
    .badge-plin{background:rgba(0,168,107,.15);color:var(--plin);padding:.15rem .5rem;border-radius:20px;font-size:.7rem;font-weight:700;}

    /* FORMULARIO PLIN */
    .card{background:var(--card-bg);border:1px solid var(--card-border);border-radius:14px;padding:1.5rem;margin-bottom:1.5rem;}
    .card-title{font-size:.82rem;font-weight:700;color:var(--cream);text-transform:uppercase;letter-spacing:.05em;margin-bottom:1rem;display:flex;align-items:center;gap:.5rem;}
    .paste-area{width:100%;background:rgba(255,255,255,.04);border:2px dashed rgba(200,136,58,.3);border-radius:10px;color:var(--cream);font-family:'Lato',sans-serif;font-size:.85rem;padding:1rem;outline:none;resize:vertical;min-height:160px;line-height:1.7;}
    .paste-area:focus{border-color:var(--accent);}
    .paste-area::placeholder{color:var(--muted);}
    .form-row{display:flex;gap:1rem;align-items:flex-end;margin-top:1rem;flex-wrap:wrap;}
    .form-group{display:flex;flex-direction:column;gap:.3rem;}
    .form-label{font-size:.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;}
    .fctrl{background:rgba(255,255,255,.05);border:1px solid var(--card-border);border-radius:8px;color:var(--cream);font-family:'Lato',sans-serif;font-size:.88rem;padding:.55rem .8rem;outline:none;}
    .fctrl:focus{border-color:var(--accent);}
    .btn-leer{background:linear-gradient(135deg,#5090e0,#2060a0);border:none;border-radius:8px;color:#fff;font-family:'Lato',sans-serif;font-size:.88rem;font-weight:700;padding:.6rem 1.2rem;cursor:pointer;display:inline-flex;align-items:center;gap:.4rem;}
    .btn-guardar-todos{width:100%;background:linear-gradient(135deg,#d49040,#a0601a);border:none;border-radius:8px;color:#fff;font-family:'Lato',sans-serif;font-size:.9rem;font-weight:700;padding:.75rem;cursor:pointer;box-shadow:0 3px 12px rgba(200,136,58,.3);transition:transform .15s;margin-top:1rem;display:flex;align-items:center;justify-content:center;gap:.5rem;}
    .btn-guardar-todos:hover{transform:translateY(-2px);}

    .preview-item{display:flex;align-items:center;justify-content:space-between;padding:.65rem .9rem;background:rgba(255,255,255,.03);border-radius:8px;margin-bottom:.4rem;border:1px solid rgba(210,160,90,.08);}
    .preview-item-left{display:flex;align-items:center;gap:.7rem;}
    .preview-nombre{font-size:.85rem;font-weight:700;}
    .preview-monto{font-size:.9rem;color:var(--plin);font-weight:700;font-family:'Playfair Display',serif;}
    .btn-quitar{background:rgba(224,80,80,.15);border:none;color:var(--red);font-size:.7rem;padding:.2rem .5rem;border-radius:5px;cursor:pointer;}
    .preview-total{display:flex;justify-content:space-between;padding:.8rem;background:rgba(200,136,58,.12);border-radius:8px;border:1px solid rgba(200,136,58,.25);margin-top:.8rem;}
    .preview-total-label{font-size:.75rem;color:var(--muted);text-transform:uppercase;}
    .preview-total-val{font-family:'Playfair Display',serif;font-size:1.2rem;color:var(--accent);font-weight:700;}

    .toast-c{position:fixed;bottom:1.5rem;right:1.5rem;z-index:300;background:#1e1208;border-radius:10px;padding:.8rem 1.2rem;display:flex;align-items:center;gap:.6rem;font-size:.88rem;font-weight:700;box-shadow:0 8px 24px rgba(0,0,0,.5);transform:translateY(80px);opacity:0;transition:all .3s;border:1px solid var(--green);color:var(--green);}
    .toast-c.show{transform:translateY(0);opacity:1;}
    .overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:99;}
    .overlay.show{display:block;}

    @media(max-width:768px){
      .sidebar{transform:translateX(-100%);}
      .sidebar.open{transform:translateX(0);}
      .main{margin-left:0;}
      .menu-toggle{display:block;}
      .content{padding:1rem;}
      .search-inp{width:100%;}
    }
  </style>
</head>
<body>

<aside class="sidebar" id="sidebar">
  <div class="sidebar-header">
    <div class="cup-icon"><i class="bi bi-cup-hot-fill"></i></div>
    <span>Cafetería Walter</span>
    <button id="closeBtn" style="margin-left:auto;background:none;border:none;color:var(--muted);cursor:pointer;font-size:1.1rem;"><i class="bi bi-x-lg"></i></button>
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

<div class="main">
  <header class="topbar">
    <div style="display:flex;align-items:center;gap:1rem;">
      <button class="menu-toggle" id="openBtn"><i class="bi bi-list"></i></button>
      <div style="width:32px;height:32px;background:linear-gradient(135deg,#6b21a8,#9333ea);border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:.85rem;">Y</div>
      <h1>Reporte Yape / Plin</h1>
    </div>
    <div class="user-pill"><i class="bi bi-person-circle"></i> Hola, admin</div>
  </header>

  <div class="content">

    {% if importados %}
    <div style="background:rgba(76,175,125,.15);border:1px solid var(--green);border-radius:10px;padding:.8rem 1.2rem;margin-bottom:1.2rem;color:var(--green);font-size:.88rem;font-weight:700;">
      <i class="bi bi-check-circle-fill me-2"></i> {{ importados }} pagos nuevos importados correctamente
    </div>
    {% endif %}

    <div class="tabs">
      <button class="tab active" onclick="switchTab('reporte',this)"><i class="bi bi-table me-1"></i>Reporte</button>
      <button class="tab" onclick="switchTab('plin',this)"><i class="bi bi-clipboard-fill me-1"></i>Ingresar PLIN</button>
    </div>

    <!-- TAB REPORTE -->
    <div id="tab-reporte" class="vista active">

      <div class="kpi">
        <div class="kpi-label">Total del día</div>
        <div class="kpi-value">S/ {{ "%.2f"|format(total_hoy) }}</div>
      </div>

      <div class="filtro-wrap">
        <span class="filtro-label"><i class="bi bi-calendar3 me-1"></i>Ver pagos del día:</span>
        <input class="date-inp" type="date" id="fechaFiltro" value="{{ fecha_filtro }}"/>
        <button class="btn-filtrar" onclick="filtrarFecha()"><i class="bi bi-search me-1"></i> Buscar</button>
        <a class="btn-hoy" href="/yape"><i class="bi bi-clock"></i> Hoy</a>
      </div>

      <div class="tabla-section">
        <div class="tabla-hdr">
          <div class="tabla-title"><i class="bi bi-table me-1" style="color:var(--accent)"></i>Pagos recibidos</div>
          <div style="display:flex;gap:.5rem;flex-wrap:wrap;align-items:center;">
            <input class="search-inp" type="text" placeholder="Buscar…" oninput="filtrarNombre(this.value)"/>
            <a href="/yape/importar" class="btn-importar"><i class="bi bi-cloud-download-fill"></i> Importar Yape</a>
          </div>
        </div>
        <div style="overflow-x:auto">
          <table>
            <thead><tr><th>Tipo</th><th>Origen</th><th>Monto</th><th>Fecha</th></tr></thead>
            <tbody id="tablabody">
              {% for f in filas %}
              <tr>
                <td><span class="{{ 'badge-plin' if 'PLIN' in f[1] else 'badge-yape' }}">{{ 'PLIN' if 'PLIN' in f[1] else 'Yape' }}</span></td>
                <td><strong>{{ f[1] }}</strong></td>
                <td class="monto">S/ {{ "%.2f"|format(f[2]) }}</td>
                <td style="color:var(--muted)">{{ f[3] }}</td>
              </tr>
              {% endfor %}
              {% if not filas %}
              <tr><td colspan="4" style="text-align:center;padding:2rem;color:var(--muted)">Sin pagos para esta fecha</td></tr>
              {% endif %}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB PLIN -->
    <div id="tab-plin" class="vista">
      <div class="card">
        <div class="card-title"><i class="bi bi-clipboard-fill" style="color:var(--plin)"></i>Pegar notificaciones PLIN</div>
        <p style="font-size:.82rem;color:var(--muted);margin-bottom:1rem;">
          Copia el texto de tus notificaciones de Interbank y pégalo aquí. El sistema detecta automáticamente los nombres y montos.
        </p>
        <textarea class="paste-area" id="textoPlin" placeholder="Pega aquí, por ejemplo:

Ana Maria Quispe Canta te ha plineado S/ 15.00
Gladys Geovanna Barzola te ha plineado S/ 8.50
Blanca Ysabel Morales te ha plineado S/ 212.00"></textarea>

        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Fecha de los pagos</label>
            <input class="fctrl" type="date" id="fechaPlin"/>
          </div>
          <button class="btn-leer" onclick="leerTexto()"><i class="bi bi-magic"></i> Detectar pagos</button>
        </div>
      </div>

      <div id="previewWrap" style="display:none">
        <div class="card">
          <div class="card-title"><i class="bi bi-eye-fill" style="color:var(--accent)"></i>Pagos detectados — revisa antes de guardar</div>
          <div id="previewLista"></div>
          <div class="preview-total">
            <div class="preview-total-label">Total a guardar</div>
            <div class="preview-total-val" id="previewTotal">S/ 0.00</div>
          </div>
          <button class="btn-guardar-todos" onclick="guardarTodos()">
            <i class="bi bi-check-circle-fill"></i> Guardar todos en la base de datos
          </button>
        </div>
      </div>
    </div>

  </div>
</div>

<div class="toast-c" id="toast"><i class="bi bi-check-circle-fill"></i><span id="toastMsg">OK</span></div>

<script>
let detectados = [];

// Poner fecha de hoy por defecto
document.getElementById('fechaPlin').value = new Date().toISOString().split('T')[0];

function switchTab(tab, btn) {
  document.querySelectorAll('.vista').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + tab).classList.add('active');
  btn.classList.add('active');
}

function filtrarFecha() {
  const fecha = document.getElementById('fechaFiltro').value;
  if (fecha) window.location.href = '/yape?fecha=' + fecha;
}

function filtrarNombre(q) {
  const f = q.toLowerCase();
  document.querySelectorAll('#tablabody tr').forEach(tr => {
    tr.style.display = tr.textContent.toLowerCase().includes(f) ? '' : 'none';
  });
}

function leerTexto() {
  const texto = document.getElementById('textoPlin').value.trim();
  if (!texto) { showToast('⚠ Pega el texto primero'); return; }

  // Detectar: "Nombre te ha plineado S/ monto"
  const regex = /(.+?)\s+te ha plineado\s+S\/\s*([\d,.]+)/gi;
  detectados = [];
  let match;

  while ((match = regex.exec(texto)) !== null) {
    const nombre = match[1].trim();
    const monto = parseFloat(match[2].replace(',', '.'));
    if (nombre && !isNaN(monto)) {
      detectados.push({ nombre, monto });
    }
  }

  if (detectados.length === 0) {
    showToast('⚠ No se detectaron pagos. Revisa el formato.');
    return;
  }

  renderPreview();
  document.getElementById('previewWrap').style.display = 'block';
  showToast('✓ ' + detectados.length + ' pagos detectados');
}

function renderPreview() {
  const lista = document.getElementById('previewLista');
  let total = 0;
  lista.innerHTML = detectados.map((p, i) => {
    total += p.monto;
    return `
    <div class="preview-item">
      <div class="preview-item-left">
        <span class="badge-plin">PLIN</span>
        <span class="preview-nombre">${p.nombre}</span>
      </div>
      <div style="display:flex;align-items:center;gap:.7rem;">
        <span class="preview-monto">S/ ${p.monto.toFixed(2)}</span>
        <button class="btn-quitar" onclick="quitarDetectado(${i})"><i class="bi bi-x-lg"></i></button>
      </div>
    </div>`;
  }).join('');
  document.getElementById('previewTotal').textContent = 'S/ ' + total.toFixed(2);
}

function quitarDetectado(i) {
  detectados.splice(i, 1);
  if (detectados.length === 0) {
    document.getElementById('previewWrap').style.display = 'none';
    return;
  }
  renderPreview();
}

function guardarTodos() {
  if (detectados.length === 0) return;
  const fecha = document.getElementById('fechaPlin').value;

  fetch('/yape/insertar_plin', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pagos: detectados, fecha })
  })
  .then(r => r.json())
  .then(data => {
    if (data.ok) {
      showToast('✓ ' + data.insertados + ' pagos guardados en la base de datos');
      detectados = [];
      document.getElementById('textoPlin').value = '';
      document.getElementById('previewWrap').style.display = 'none';
      setTimeout(() => window.location.href = '/yape?fecha=' + fecha, 1800);
    } else {
      showToast('❌ Error: ' + data.error);
    }
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

function showToast(msg) {
  const t = document.getElementById('toast');
  document.getElementById('toastMsg').textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}
</script>
</body>
</html>
"""