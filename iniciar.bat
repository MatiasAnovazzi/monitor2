@echo off
:: Comprobar si Python 3.12 está disponible
python --version 2>NUL | find "3.12" >NUL
if "%ERRORLEVEL%" NEQ "0" (
    echo ⚙️ Python 3.12 no detectado en el sistema o no esta en el PATH.
    echo Descargando e instalando Python 3.12 ^(esto puede tomar unos minutos^)...
    
    :: Descargar el instalador silenciosamente
    curl -# -o python_installer.exe https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe
    
    :: Ejecutar la instalacion silenciosa y agregar al PATH
    start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    
    :: Borrar el instalador
    del python_installer.exe
    
    echo ✅ Instalacion completa. 
    echo ⚠️ ATENCION: Es posible que necesites cerrar esta ventana y volver a abrir el archivo iniciar.bat para que Windows reconozca Python.
    pause
    exit
)

title Monitor de Guardia SICAP

:: Ir al directorio del script
cd /d "%~dp0"

:: Crear entorno virtual si no existe
if not exist venv\ (
    echo Creando entorno virtual...
    python -m venv venv
)

:: Activar entorno virtual
call venv\Scripts\activate.bat

:: Instalar dependencias
echo Instalando dependencias...
pip install -r requirements.txt --quiet

:: Ejecutar app
echo Iniciando Monitor...
python app_guardia_3.py

:: Mantener terminal abierta
echo.
pause