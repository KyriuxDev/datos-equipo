"""
IMSS Oaxaca - Datos del Equipo
Ventana principal con datos del equipo y generación de QR cifrado.
Compatible con Windows y Linux.
"""

import sys
import os
import platform
import socket
import uuid
import tempfile
import threading
import tkinter as tk
from tkinter import messagebox, font as tkfont

try:
    import qrcode
except ImportError:
    qrcode = None

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import pystray
    from pystray import MenuItem as Item
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

IS_WINDOWS = platform.system() == "Windows"

# ── constantes ────────────────────────────────────────────────────────
AES_KEY      = b"IMSS_OAX_2024_QR"
APP_NAME     = "IMSS_TrayApp"
SINGLETON_FILE = os.path.join(tempfile.gettempdir(), f"{APP_NAME}.lock")

COLOR_BG     = "#f0f4f8"
COLOR_PANEL  = "#ffffff"
COLOR_ACCENT = "#0066cc"
COLOR_BTN_G  = "#0066cc"
COLOR_BTN_R  = "#cc3333"
COLOR_LABEL  = "#444444"
COLOR_VALUE  = "#111111"

# ── singleton ─────────────────────────────────────────────────────────
def check_singleton():
    if os.path.exists(SINGLETON_FILE):
        try:
            with open(SINGLETON_FILE) as f:
                pid = int(f.read().strip())
            if platform.system() == "Windows":
                import ctypes
                h = ctypes.windll.kernel32.OpenProcess(0x100000, False, pid)
                if h:
                    ctypes.windll.kernel32.CloseHandle(h)
                    return False
            else:
                os.kill(pid, 0)
                return False
        except (ValueError, OSError):
            pass
    with open(SINGLETON_FILE, "w") as f:
        f.write(str(os.getpid()))
    return True

def remove_singleton():
    try:
        os.remove(SINGLETON_FILE)
    except OSError:
        pass

# ── hardware ──────────────────────────────────────────────────────────
def get_hardware_info():
    info = {}
    info["hostname"] = socket.gethostname()
    info["username"] = os.environ.get("USERNAME") or os.environ.get("USER", "N/A")
    info["domain"]   = os.environ.get("USERDOMAIN") or os.environ.get("LOGNAME", "N/A")
    info["os"]       = f"{platform.system()} {platform.release()} ({platform.machine()})"

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        info["ip"] = s.getsockname()[0]
        s.close()
    except Exception:
        info["ip"] = "N/A"

    try:
        mac_int = uuid.getnode()
        info["mac"] = ":".join(f"{(mac_int >> (8*i)) & 0xFF:02X}" for i in reversed(range(6)))
    except Exception:
        info["mac"] = "N/A"

    info["brand"] = info["model"] = info["serial"] = "N/A"

    if platform.system() == "Windows":
        try:
            import wmi
            c = wmi.WMI()
            for item in c.Win32_SystemEnclosure():
                info["brand"]  = item.Manufacturer or "N/A"
                info["serial"] = item.SerialNumber  or "N/A"
                break
            for item in c.Win32_ComputerSystem():
                info["model"] = item.Model or "N/A"
                break
        except Exception:
            import subprocess
            def wmic(q):
                try:
                    r = subprocess.check_output(["wmic"] + q.split(), text=True, stderr=subprocess.DEVNULL)
                    lines = [l.strip() for l in r.splitlines() if l.strip()]
                    return lines[1] if len(lines) > 1 else "N/A"
                except Exception:
                    return "N/A"
            info["brand"]  = wmic("csproduct get Vendor")
            info["model"]  = wmic("csproduct get Name")
            info["serial"] = wmic("bios get SerialNumber")
    else:
        import subprocess
        def dmi(t, field):
            try:
                r = subprocess.check_output(["sudo", "dmidecode", "-t", t],
                                            text=True, stderr=subprocess.DEVNULL)
                for line in r.splitlines():
                    if field in line:
                        return line.split(":", 1)[1].strip()
            except Exception:
                pass
            return "N/A"
        info["brand"]  = dmi("system", "Manufacturer")
        info["model"]  = dmi("system", "Product Name")
        info["serial"] = dmi("system", "Serial Number")

    return info

# ── cifrado + QR ──────────────────────────────────────────────────────
def cifrar_hex(texto):
    if not HAS_CRYPTO:
        return texto.encode().hex().upper()
    cipher = AES.new(AES_KEY, AES.MODE_CBC)
    ct = cipher.encrypt(pad(texto.encode("utf-8"), AES.block_size))
    return (cipher.iv + ct).hex().upper()

def generar_qr(datos, ruta):
    if not qrcode:
        return False
    try:
        qrcode.make(datos).save(ruta)
        return True
    except Exception:
        return False

# ── ventana QR ────────────────────────────────────────────────────────
def mostrar_ventana_qr(root, ruta_img):
    win = tk.Toplevel(root)
    win.title("Código QR — IMSS Oaxaca")
    win.resizable(False, False)
    win.configure(bg=COLOR_PANEL)
    win.attributes("-topmost", True)

    tk.Label(win, text="Escanea para exportar datos",
             font=("Segoe UI", 10, "bold"), bg=COLOR_PANEL,
             fg=COLOR_ACCENT).pack(pady=(16, 8))

    if HAS_PIL:
        img   = Image.open(ruta_img).resize((280, 280), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        lbl   = tk.Label(win, image=photo, bg=COLOR_PANEL, bd=2, relief="solid")
        lbl.image = photo
        lbl.pack(padx=20)
    else:
        tk.Label(win, text=f"QR guardado en:\n{ruta_img}",
                 font=("Consolas", 9), bg=COLOR_PANEL, fg=COLOR_LABEL,
                 wraplength=280).pack(padx=20, pady=10)

    tk.Button(win, text="Cerrar", command=win.destroy,
              bg=COLOR_BTN_R, fg="white", font=("Segoe UI", 9, "bold"),
              relief="flat", padx=20, pady=6, cursor="hand2").pack(pady=16)

    # centrar
    win.update_idletasks()
    w, h = win.winfo_width(), win.winfo_height()
    x = (win.winfo_screenwidth()  - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"+{x}+{y}")

# ── ventana principal ─────────────────────────────────────────────────
def construir_ventana(root, info):
    root.title("IMSS Oaxaca — Datos del Equipo")
    root.resizable(False, False)
    root.configure(bg=COLOR_BG)

    # ── encabezado ──
    header = tk.Frame(root, bg=COLOR_ACCENT, pady=12)
    header.pack(fill="x")
    tk.Label(header, text="IMSS Oaxaca",
             font=("Segoe UI", 14, "bold"), bg=COLOR_ACCENT, fg="white").pack()
    tk.Label(header, text="Datos del Equipo",
             font=("Segoe UI", 9), bg=COLOR_ACCENT, fg="#cce0ff").pack()

    # ── panel de datos ──
    panel = tk.Frame(root, bg=COLOR_PANEL, padx=24, pady=16, bd=0)
    panel.pack(fill="both", padx=16, pady=12)

    campos = [
        ("Equipo",   info["hostname"]),
        ("Usuario",  info["username"]),
        ("Dominio",  info["domain"]),
        ("IP",       info["ip"]),
        ("MAC",      info["mac"]),
        ("Sistema",  info["os"]),
        ("",         ""),
        ("Marca",    info["brand"]),
        ("Modelo",   info["model"]),
        ("Serie",    info["serial"]),
    ]

    for i, (lbl, val) in enumerate(campos):
        if lbl == "":
            tk.Frame(panel, bg="#e0e0e0", height=1).grid(
                row=i, column=0, columnspan=2, sticky="ew", pady=4)
            continue
        tk.Label(panel, text=f"{lbl}:", font=("Segoe UI", 9),
                 bg=COLOR_PANEL, fg=COLOR_LABEL, anchor="w", width=10
                 ).grid(row=i, column=0, sticky="w", pady=2)
        tk.Label(panel, text=val, font=("Consolas", 9, "bold"),
                 bg=COLOR_PANEL, fg=COLOR_VALUE, anchor="w"
                 ).grid(row=i, column=1, sticky="w", padx=(8, 0))

    # ── botones ──
    btn_frame = tk.Frame(root, bg=COLOR_BG, pady=4)
    btn_frame.pack(fill="x", padx=16, pady=(0, 14))

    def copiar():
        texto = "\n".join(
            f"{l}: {v}" for l, v in campos if l and v
        )
        root.clipboard_clear()
        root.clipboard_append(texto)
        messagebox.showinfo("Copiado", "Datos copiados al portapapeles.")

    def generar():
        datos = (
            f"INVENTARIO IMSS\n"
            f"HOST: {info['hostname']}\n"
            f"USER: {info['username']}\n"
            f"IP: {info['ip']} | MAC: {info['mac']}\n"
            f"SN: {info['serial']} | MOD: {info['model']}"
        )
        cifrado = cifrar_hex(datos)
        ruta = os.path.join(tempfile.gettempdir(), f"QR_IMSS_{info['hostname']}.png")
        if os.path.exists(ruta):
            os.remove(ruta)

        def _run():
            ok = generar_qr(cifrado, ruta)
            if ok:
                root.after(0, lambda: mostrar_ventana_qr(root, ruta))
            else:
                root.after(0, lambda: messagebox.showerror(
                    "Error", "No se pudo generar el QR.\nInstala: pip install qrcode[pil]"))

        threading.Thread(target=_run, daemon=True).start()

    btn_cfg = dict(font=("Segoe UI", 9, "bold"), relief="flat",
                   fg="white", padx=14, pady=7, cursor="hand2")

    tk.Button(btn_frame, text="📋  Copiar Datos", bg=COLOR_BTN_G,
              command=copiar, **btn_cfg).pack(side="left", expand=True, fill="x", padx=(0, 6))
    tk.Button(btn_frame, text="📷  Generar QR", bg="#1a7a1a",
              command=generar, **btn_cfg).pack(side="left", expand=True, fill="x", padx=(0, 6))
    tk.Button(btn_frame, text="✕  Salir", bg=COLOR_BTN_R,
              command=root.quit, **btn_cfg).pack(side="left", expand=True, fill="x")

    # centrar
    root.update_idletasks()
    w = root.winfo_width()
    h = root.winfo_height()
    x = (root.winfo_screenwidth()  - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f"+{x}+{y}")

# ── tray icon (Windows) ───────────────────────────────────────────────
def crear_icono_tray():
    img = Image.new("RGB", (64, 64), color=(0, 102, 204))
    return img

def iniciar_tray(info, root):
    ventana_abierta = [False]

    def on_datos(icon, item):
        if ventana_abierta[0]:
            return
        ventana_abierta[0] = True
        def abrir():
            win = tk.Toplevel(root)
            construir_ventana_toplevel(win, info)
            win.protocol("WM_DELETE_WINDOW", lambda: (win.destroy(), ventana_abierta.__setitem__(0, False)))
        root.after(0, abrir)

    def on_qr(icon, item):
        def _run():
            datos = (
                f"INVENTARIO IMSS\n"
                f"HOST: {info['hostname']}\n"
                f"USER: {info['username']}\n"
                f"IP: {info['ip']} | MAC: {info['mac']}\n"
                f"SN: {info['serial']} | MOD: {info['model']}"
            )
            cifrado = cifrar_hex(datos)
            ruta = os.path.join(tempfile.gettempdir(), f"QR_IMSS_{info['hostname']}.png")
            if os.path.exists(ruta):
                os.remove(ruta)
            ok = generar_qr(cifrado, ruta)
            if ok:
                root.after(0, lambda: mostrar_ventana_qr(root, ruta))
            else:
                root.after(0, lambda: messagebox.showerror(
                    "Error", "No se pudo generar el QR."))
        threading.Thread(target=_run, daemon=True).start()

    def on_salir(icon, item):
        icon.stop()
        root.after(0, root.quit)

    icono = pystray.Icon(
        APP_NAME,
        icon=crear_icono_tray(),
        title="IMSS Oaxaca - Datos del Equipo",
        menu=pystray.Menu(
            Item("1. Ver Datos del Equipo", on_datos),
            Item(pystray.Menu.SEPARATOR, None),
            Item("2. Generar Código QR", on_qr),
            Item(pystray.Menu.SEPARATOR, None),
            Item("Salir", on_salir),
        )
    )
    threading.Thread(target=icono.run, daemon=True).start()

def construir_ventana_toplevel(win, info):
    """Versión Toplevel de la ventana (para usar desde el tray)."""
    win.title("IMSS Oaxaca — Datos del Equipo")
    win.resizable(False, False)
    win.configure(bg=COLOR_BG)
    win.attributes("-topmost", True)

    header = tk.Frame(win, bg=COLOR_ACCENT, pady=12)
    header.pack(fill="x")
    tk.Label(header, text="IMSS Oaxaca",
             font=("Segoe UI", 14, "bold"), bg=COLOR_ACCENT, fg="white").pack()
    tk.Label(header, text="Datos del Equipo",
             font=("Segoe UI", 9), bg=COLOR_ACCENT, fg="#cce0ff").pack()

    panel = tk.Frame(win, bg=COLOR_PANEL, padx=24, pady=16)
    panel.pack(fill="both", padx=16, pady=12)

    campos = [
        ("Equipo",  info["hostname"]),
        ("Usuario", info["username"]),
        ("Dominio", info["domain"]),
        ("IP",      info["ip"]),
        ("MAC",     info["mac"]),
        ("Sistema", info["os"]),
        ("",        ""),
        ("Marca",   info["brand"]),
        ("Modelo",  info["model"]),
        ("Serie",   info["serial"]),
    ]

    for i, (lbl, val) in enumerate(campos):
        if lbl == "":
            tk.Frame(panel, bg="#e0e0e0", height=1).grid(
                row=i, column=0, columnspan=2, sticky="ew", pady=4)
            continue
        tk.Label(panel, text=f"{lbl}:", font=("Segoe UI", 9),
                 bg=COLOR_PANEL, fg=COLOR_LABEL, anchor="w", width=10
                 ).grid(row=i, column=0, sticky="w", pady=2)
        tk.Label(panel, text=val, font=("Consolas", 9, "bold"),
                 bg=COLOR_PANEL, fg=COLOR_VALUE, anchor="w"
                 ).grid(row=i, column=1, sticky="w", padx=(8, 0))

    btn_frame = tk.Frame(win, bg=COLOR_BG, pady=4)
    btn_frame.pack(fill="x", padx=16, pady=(0, 14))

    def copiar():
        texto = "\n".join(f"{l}: {v}" for l, v in campos if l and v)
        win.clipboard_clear()
        win.clipboard_append(texto)
        messagebox.showinfo("Copiado", "Datos copiados al portapapeles.", parent=win)

    btn_cfg = dict(font=("Segoe UI", 9, "bold"), relief="flat",
                   fg="white", padx=14, pady=7, cursor="hand2")
    tk.Button(btn_frame, text="📋  Copiar Datos", bg=COLOR_BTN_G,
              command=copiar, **btn_cfg).pack(side="left", expand=True, fill="x", padx=(0, 6))
    tk.Button(btn_frame, text="✕  Cerrar", bg=COLOR_BTN_R,
              command=win.destroy, **btn_cfg).pack(side="left", expand=True, fill="x")

    win.update_idletasks()
    w, h = win.winfo_width(), win.winfo_height()
    x = (win.winfo_screenwidth()  - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"+{x}+{y}")

# ── main ──────────────────────────────────────────────────────────────
def main():
    if not check_singleton():
        tmp = tk.Tk(); tmp.withdraw()
        messagebox.showinfo("Aviso", "La aplicación ya está en ejecución.")
        tmp.destroy(); sys.exit(0)

    try:
        info = get_hardware_info()
        root = tk.Tk()
        root.withdraw()  # ocultar ventana raíz siempre

        if IS_WINDOWS and HAS_TRAY:
            # Windows: bandeja del sistema como el original
            iniciar_tray(info, root)
        else:
            # Linux: ventana directa
            root.deiconify()
            construir_ventana(root, info)

        root.mainloop()
    finally:
        remove_singleton()

if __name__ == "__main__":
    main()