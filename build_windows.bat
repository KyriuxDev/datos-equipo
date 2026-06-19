@echo off
echo Instalando dependencias...
python -m pip install pystray Pillow "qrcode[pil]" pycryptodome psutil wmi pyinstaller

echo.
echo Compilando ejecutable...
python -m PyInstaller --onefile --windowed --name "IMSS_TrayApp" imss_tray.py

echo.
echo Listo! El ejecutable esta en: dist\IMSS_TrayApp.exe
pause