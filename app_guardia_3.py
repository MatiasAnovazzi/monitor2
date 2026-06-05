from flask import Flask, render_template_string, jsonify
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import os
import re
import time
from datetime import datetime, timedelta
import shutil
import threading
import platform
app = Flask(__name__)

URL_SISTEMA_TURNOS = "https://www.santafe.gov.ar/sicap/ambulatorio/turnos_guardia"

# Variables globales para mantener el navegador vivo y seguro entre peticiones
driver = None
driver_lock = threading.Lock()

# Índices de columnas
COL_HORA      = 1
COL_APELLIDO  = 3
COL_NOMBRE    = 4
COL_ESTADO    = 6
COL_URGENCIA  = 7
COL_T_ESPERA  = 8


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────
def parsear_tiempo_espera_hhmm(texto):
    if not texto:
        return None
    m = re.search(r'(\d{1,3}):(\d{2})', texto.strip())
    if m:
        return int(m.group(1)) + int(m.group(2)) / 60.0
    return None

def obtener_prioridad_triage(color):
    c = str(color).lower().strip().replace(' ', '').replace('#', '')
    if not c or c in ['-', 'transparent', 'none', 'inherit']:
        return 99
    if c in ['ff0000', 'f00', 'red'] or 'red' in c or 'rojo' in c: return 1
    if c in ['ffa500', 'ff8c00', 'orange'] or 'orange' in c or 'naranja' in c: return 2
    if c in ['ffff00', 'ffd700', 'ffc', 'yellow'] or 'yellow' in c or 'amarillo' in c or 'ffd700' in c: return 3
    if c in ['008000', '00ff00', '3cb371', '4caf50', 'green'] or 'green' in c or 'verde' in c: return 4
    if c in ['0000ff', '0000cd', 'blue'] or 'blue' in c or 'azul' in c: return 5
    return 98


# ──────────────────────────────────────────────
# SCRAPING PRINCIPAL (LEE EL NAVEGADOR ABIERTO)
# ──────────────────────────────────────────────
def scrapear_sicap_abierto():
    global driver
    pacientes = []
    
    # Usamos un Lock para que si recargas la página rápido, no choque el navegador
    with driver_lock:
        try:
            # 1. Intentamos hacer click en el botón actualizar del SICAP
            try:
                btn = driver.find_element(By.ID, "actualizar")
                btn.click()
                time.sleep(2) # Pausa para que el DOM se actualice en la pantalla
            except Exception:
                pass # Si falla, igual intentamos leer el código fuente actual
                
            contenido_html = driver.page_source
        except Exception as e:
            print(f"Error interactuando con el navegador: {e}")
            return []

    if not contenido_html:
        return []

    soup = BeautifulSoup(contenido_html, "html.parser")
    tabla = soup.find("table", {"id": "tabla_turnos"})
    if not tabla:
        tabla = soup.find("table")
    if not tabla:
        return []

    filas = tabla.find("tbody").find_all("tr") if tabla.find("tbody") else tabla.find_all("tr")

    for fila in filas:
        tds = fila.find_all("td")
        if len(tds) < 9:
            continue

        td_espera = tds[COL_T_ESPERA]
        strong_espera = td_espera.find("strong")
        texto_espera = strong_espera.get_text(strip=True) if strong_espera else td_espera.get_text(strip=True)
        horas_espera = parsear_tiempo_espera_hhmm(texto_espera)

        if horas_espera is not None and horas_espera > 6:
            continue

        td_hora = tds[COL_HORA]
        hidden_hora = td_hora.find("input", {"type": "hidden"})
        hora_ingreso = hidden_hora["value"].strip() if hidden_hora else td_hora.get_text(strip=True)
        hora_ingreso = hora_ingreso.split('\n')[0].strip()

        if not re.search(r'\d{1,2}:\d{2}', hora_ingreso):
            continue

        apellido = tds[COL_APELLIDO].get_text(strip=True)
        texto_nombre = tds[COL_NOMBRE].get_text("\n", strip=True)
        nombre = texto_nombre.split('\n')[0].strip()

        nombre_visible = f"{apellido}, {nombre}"
        if "Nombre Elegido:" in texto_nombre:
            nombre_visible = texto_nombre.split("Nombre Elegido:")[-1].strip()

        td_estado = tds[COL_ESTADO]
        span_estado = td_estado.find("span", class_="estado-turno")
        estado_turno = span_estado.get_text(strip=True) if span_estado else td_estado.get_text(strip=True)
        es_tomado = "otro profesional" in estado_turno.lower()

        td_urgencia = tds[COL_URGENCIA]
        color_urgencia = "-"
        style_td = td_urgencia.get("style", "")
        if "background-color:" in style_td:
            color_urgencia = style_td.split("background-color:")[1].split(";")[0].strip()
        elif td_urgencia.has_attr("bgcolor"):
            color_urgencia = td_urgencia["bgcolor"]

        m = re.search(r'(\d{1,2}):(\d{2})', hora_ingreso)
        if m:
            ahora = datetime.now()
            ingreso_dt = ahora.replace(
                hour=int(m.group(1)),
                minute=int(m.group(2)),
                second=0, microsecond=0
            )
            if ingreso_dt > ahora:
                diff = (ingreso_dt - ahora).total_seconds() / 3600.0
                ingreso_dt = ingreso_dt - timedelta(days=1) if diff > 4 else ahora
            timestamp = ingreso_dt.timestamp()
        else:
            timestamp = float('inf')

        pacientes.append({
            "nombre_visible":  nombre_visible,
            "hora_ingreso":    hora_ingreso,
            "tiempo_espera":   texto_espera,
            "estado_turno":    estado_turno,
            "color_urgencia":  color_urgencia,
            "es_tomado":       es_tomado,
            "_prio":           obtener_prioridad_triage(color_urgencia),
            "_ts":             timestamp,
        })

    pacientes.sort(key=lambda x: (x['es_tomado'], x['_prio'], x['_ts']))

    for p in pacientes:
        del p['_prio']
        del p['_ts']

    return pacientes


# ──────────────────────────────────────────────
# TEMPLATE HTML/CSS/JS (Se mantiene exacto al tuyo)
# ──────────────────────────────────────────────
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitor de Guardia · Triage Activo</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #f1f5f9; --card: #ffffff; --primary: #0f172a; --accent: #2563eb; --muted: #64748b; --border: #e2e8f0; --row-hover: #f8fafc; }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', sans-serif; background: var(--bg); min-height: 100vh; display: flex; flex-direction: column; align-items: center; padding: 32px 16px; }
        .container { width: 100%; max-width: 1000px; background: var(--card); border-radius: 18px; box-shadow: 0 8px 32px rgba(15,23,42,0.08); border: 1px solid var(--border); overflow: hidden; }
        .header { background: var(--primary); padding: 22px 32px; display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid var(--accent); }
        .header h1 { color: #fff; font-size: 1.2rem; font-weight: 700; }
        .header p { color: #94a3b8; font-size: 0.78rem; margin-top: 4px; }
        #spinner { display: none; width: 22px; height: 22px; border: 3px solid #334155; border-top-color: #60a5fa; border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0; }
        @keyframes spin { to { transform: rotate(360deg); } }
        table { width: 100%; border-collapse: collapse; }
        thead tr { background: #f8fafc; }
        th { color: var(--muted); font-weight: 600; text-transform: uppercase; font-size: 0.68rem; letter-spacing: 0.07em; padding: 13px 22px; border-bottom: 1px solid var(--border); white-space: nowrap; }
        td { padding: 15px 22px; border-bottom: 1px solid var(--border); vertical-align: middle; }
        tbody tr:last-child td { border-bottom: none; }
        tbody tr:hover td { background: var(--row-hover); }
        tr.tomado td { opacity: 0.38; }
        .dot { width: 26px; height: 26px; border-radius: 50%; display: block; margin: 0 auto; box-shadow: 0 1px 5px rgba(0,0,0,0.2); border: 2px solid rgba(255,255,255,0.8); }
        .nombre { font-weight: 600; font-size: 1rem; color: var(--primary); }
        .hora { font-weight: 700; font-size: 0.95rem; color: var(--primary); }
        .espera { font-size: 0.75rem; color: var(--muted); margin-top: 3px; }
        .badge { display: inline-block; padding: 5px 12px; border-radius: 7px; font-size: 0.81rem; font-weight: 600; color: #fff; background: #1e293b; white-space: nowrap; }
        .badge.tomado { background: #64748b; }
        .empty { text-align: center; padding: 52px 24px; color: var(--muted); font-size: 0.95rem; }
        .footer { padding: 10px 28px; background: #f8fafc; border-top: 1px solid var(--border); font-size: 0.74rem; color: var(--muted); display: flex; justify-content: space-between; align-items: center; }
        .footer span { font-weight: 600; color: var(--primary); }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div>
            <h1>🏥 Monitor de Guardia · Triage Activo</h1>
            <p>Pacientes con más de 6 hs de espera excluidos · Se refresca automáticamente</p>
        </div>
        <div id="spinner"></div>
    </div>
    <div style="overflow-x:auto;">
        <table>
            <thead>
                <tr>
                    <th style="text-align:center; width:70px;">Triage</th>
                    <th style="width:130px;">Ingreso / Espera</th>
                    <th>Paciente</th>
                    <th>Estado Actual</th>
                </tr>
            </thead>
            <tbody id="tbody">
                {% if pacientes %}
                    {% for p in pacientes %}
                    <tr class="{{ 'tomado' if p.es_tomado else '' }}">
                        <td style="text-align:center;">
                            <span class="dot" style="background-color:
                                {%- if p.color_urgencia and p.color_urgencia not in ['-','transparent','none','inherit'] -%}
                                    {{ p.color_urgencia }}
                                {%- else -%}
                                    #cbd5e1
                                {%- endif %};"></span>
                        </td>
                        <td>
                            <div class="hora">{{ p.hora_ingreso }}</div>
                            {% if p.tiempo_espera and p.tiempo_espera not in ['-', ''] %}
                                <div class="espera">⏱ {{ p.tiempo_espera }}</div>
                            {% endif %}
                        </td>
                        <td><span class="nombre">{{ p.nombre_visible }}</span></td>
                        <td>
                            <span class="badge {{ 'tomado' if p.es_tomado else '' }}">
                                {{ p.estado_turno }}
                            </span>
                        </td>
                    </tr>
                    {% endfor %}
                {% else %}
                    <tr><td colspan="4" class="empty">No hay turnos pendientes (bajo 6 hs de espera).</td></tr>
                {% endif %}
            </tbody>
        </table>
    </div>
    <div class="footer">
        <span>{{ pacientes|length }} paciente{{ 's' if pacientes|length != 1 else '' }}</span>
        <span id="ts">Última actualización: {{ hora_sync }}</span>
    </div>
</div>

<script>
    const INTERVALO_MS = 90 * 1000;

    async function refrescar() {
        const spinner = document.getElementById('spinner');
        spinner.style.display = 'block';
        try {
            const resp = await fetch('/api/actualizar');
            if (!resp.ok) throw new Error('HTTP ' + resp.status);
            const lista = await resp.json();
            const tbody = document.getElementById('tbody');

            if (!lista.length) {
                tbody.innerHTML = '<tr><td colspan="4" class="empty">No hay turnos pendientes (bajo 6 hs de espera).</td></tr>';
                document.querySelector('.footer span').textContent = '0 pacientes';
            } else {
                let html = '';
                lista.forEach(p => {
                    const color = (p.color_urgencia && !['-','transparent','none','inherit',''].includes(p.color_urgencia))
                                  ? p.color_urgencia : '#cbd5e1';
                    const espera = (p.tiempo_espera && p.tiempo_espera !== '-')
                                   ? `<div class="espera">⏱ ${p.tiempo_espera}</div>` : '';
                    const claseRow   = p.es_tomado ? 'tomado' : '';
                    const claseBadge = p.es_tomado ? 'tomado' : '';
                    html += `
                    <tr class="${claseRow}">
                        <td style="text-align:center;"><span class="dot" style="background-color:${color};"></span></td>
                        <td><div class="hora">${p.hora_ingreso}</div>${espera}</td>
                        <td><span class="nombre">${p.nombre_visible}</span></td>
                        <td><span class="badge ${claseBadge}">${p.estado_turno}</span></td>
                    </tr>`;
                });
                tbody.innerHTML = html;
                const n = lista.length;
                document.querySelector('.footer span').textContent = n + ' paciente' + (n !== 1 ? 's' : '');
            }
            const ahora = new Date().toLocaleTimeString('es-AR', {hour:'2-digit', minute:'2-digit', second:'2-digit'});
            document.getElementById('ts').textContent = 'Última actualización: ' + ahora;
        } catch(e) {
            console.error('Error al refrescar:', e);
        } finally {
            spinner.style.display = 'none';
        }
    }

    setInterval(refrescar, INTERVALO_MS);
</script>
</body>
</html>
"""

# ──────────────────────────────────────────────
# RUTAS FLASK
# ──────────────────────────────────────────────
@app.route('/')
def index():
    lista = scrapear_sicap_abierto()
    hora_sync = datetime.now().strftime("%H:%M:%S")
    return render_template_string(HTML_TEMPLATE, pacientes=lista, hora_sync=hora_sync)

@app.route('/api/actualizar')
def api_actualizar():
    return jsonify(scrapear_sicap_abierto())

if __name__ == '__main__':
    print("Iniciando navegador...")
    options = uc.ChromeOptions()
    
    # IMPORTANTE: NO usamos headless aquí para mantener el navegador vivo.
    
    # --- INICIO LÓGICA MULTIPLATAFORMA ---
    sistema = platform.system()
    browser_path = None

    if sistema == "Windows":
        rutas_windows = [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]
        for ruta in rutas_windows:
            if os.path.exists(ruta):
                browser_path = ruta
                break
    else: # Lógica para Linux
        browser_path = (shutil.which("brave-browser") or 
                        shutil.which("brave") or 
                        shutil.which("google-chrome") or 
                        shutil.which("chromium-browser") or 
                        shutil.which("chromium"))
    # --- FIN LÓGICA MULTIPLATAFORMA ---
    
    # Inicializamos el driver con la ruta detectada según el SO
    driver = uc.Chrome(options=options, browser_executable_path=browser_path, version_main=148)
    driver.get(URL_SISTEMA_TURNOS)
    
    print("\n" + "="*60)
    print(" 1. Iniciá sesión en el SICAP en la ventana de Brave/Chrome.")
    print(" 2. Resolvé cualquier redirección del SSO.")
    print(" 3. Cuando estés viendo la tabla de la guardia,")
    print("    volvé a esta terminal y presioná ENTER.")
    print("="*60 + "\n")
    
    input("Presioná ENTER para arrancar el monitor...")
    
    print("\nLevantando servidor web en http://127.0.0.1:5000")
    print("Podes minimizar el navegador (pero NO LO CIERRES).")
    
    # use_reloader=False es CRÍTICO para que Flask no intente abrir 2 navegadores al mismo tiempo
    app.run(debug=True, port=5000, use_reloader=False)