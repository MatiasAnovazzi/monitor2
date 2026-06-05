#!/bin/bash

# Evitar ejecución con sudo
if [ "$EUID" -eq 0 ]; then
    echo "❌ No ejecutes este script con sudo"
    echo "Ejecuta: ./iniciar.sh"
    exit 1
fi

# Ir al directorio del script
cd "$(dirname "$0")" || exit

# Variables de entorno gráfica
export DISPLAY=:0
export XAUTHORITY="$HOME/.Xauthority"
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias
echo "Instalando dependencias..."
pip install -r requirements.txt --quiet

# Ejecutar app
echo "Iniciando Monitor..."
python3 app_guardia_3.py

# Mantener terminal abierta
read -p "Presiona Enter para salir..."