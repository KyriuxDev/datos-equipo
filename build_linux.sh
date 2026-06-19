#!/bin/bash
echo "Instalando dependencias..."
pip install pystray Pillow "qrcode[pil]" pycryptodome psutil pyinstaller

echo ""
echo "Compilando ejecutable..."
pyinstaller --onefile --name "IMSS_TrayApp" imss_tray.py

echo ""
echo "Listo! El ejecutable está en: dist/IMSS_TrayApp"
