# 🏥 Monitor de Guardia SICAP

Este proyecto es un monitor local en tiempo real para el sistema de turnos de guardia del SICAP (Provincia de Santa Fe). Extrae los datos de los pacientes en espera y los presenta en un dashboard web moderno, limpio y fácil de leer, que se actualiza automáticamente.

## ✨ Características

- **Bypass de SSO:** Utiliza una arquitectura de "Navegador Persistente" con Selenium (`undetected-chromedriver`) para evitar los bloqueos del Single Sign-On (SSO) del gobierno. Te logueas una vez y el sistema mantiene la sesión viva.
- **Auto-Refresh:** El tablero web se actualiza automáticamente cada 90 segundos sin necesidad de recargar la página.
- **Filtrado Inteligente:** Excluye automáticamente a los pacientes con más de 6 horas de espera.
- **Triage Visual:** Identifica rápidamente la prioridad médica mediante puntos de colores (Rojo, Naranja, Amarillo, Verde, Azul).
- **Ordenamiento Lógico:** Prioriza a los pacientes libres sobre los ya tomados, luego por urgencia médica y finalmente por hora de llegada.
- **Multiplataforma:** Funciona nativamente tanto en Linux como en Windows.

---

## 🛠️ Requisitos del Sistema

- **Sistema Operativo:** Linux (Debian, Ubuntu, Zorin, etc.) o Windows (10/11).
- **Lenguaje:** Python 3.12+
- **Navegador:** Brave, Google Chrome o Chromium instalados en el sistema.

---

## 📦 Instalación

Abre una terminal (Linux) o la Línea de Comandos / PowerShell (Windows) en la carpeta del proyecto.

### 1. Crear el entorno virtual

**Linux**

```bash
python3 -m venv venv
```

**Windows**

```powershell
python -m venv venv
```

### 2. Activar el entorno virtual

**Linux**

```bash
source venv/bin/activate
```

**Windows (CMD)**

```bat
venv\Scripts\activate.bat
```

**Windows (PowerShell)**

```powershell
venv\Scripts\Activate.ps1
```

> **Nota:** Si PowerShell muestra un error de permisos, ejecuta primero:

```powershell
Set-ExecutionPolicy Unrestricted -Scope CurrentUser
```

### 3. Instalar las dependencias

Asegúrate de tener el archivo `requirements.txt` en la carpeta del proyecto y ejecuta:

```bash
pip install -r requirements.txt
```

---

## 🚀 Uso

1. Activa el entorno virtual si aún no está activo (siguiendo el paso 2 según tu sistema operativo).

2. Ejecuta el servidor principal:

```bash
python app_guardia_2.py
```

3. Se abrirá automáticamente una ventana del navegador (Brave/Chrome).

4. Inicia sesión en el sistema SICAP con tus credenciales y completa cualquier redirección del SSO.

5. Una vez que estés visualizando la tabla de turnos de guardia, vuelve a la terminal y presiona **ENTER**.

6. Abre tu navegador habitual e ingresa a:

```text
http://127.0.0.1:5000
```

### ⚠️ Importante

Puedes minimizar la ventana del navegador que abrió el script para iniciar sesión, pero **NO LA CIERRES**.

El servidor Flask utiliza esa misma ventana persistente en segundo plano para hacer clic en **"Actualizar"** y extraer los datos periódicamente sin perder la sesión.

---

## 🛑 Detener el sistema

Para apagar el monitor de forma segura:

1. Ve a la terminal donde se está ejecutando Flask y presiona:

```text
CTRL + C
```

2. Cierra manualmente la ventana del navegador del SICAP que quedó abierta en segundo plano.

---

## 🧩 Tecnologías utilizadas

### Backend

- Python
- Flask

### Scraping

- Selenium
- undetected-chromedriver
- BeautifulSoup4

### Frontend

- HTML5
- CSS3 (Custom Properties, Flexbox)
- Vanilla JavaScript

---

## 📋 Descripción

Herramienta desarrollada para optimizar la visualización y gestión de pacientes en la guardia médica, proporcionando una interfaz clara, actualizada y orientada a la toma rápida de decisiones.