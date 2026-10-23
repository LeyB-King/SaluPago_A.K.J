import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD
from tkinter import ttk, messagebox, simpledialog, filedialog
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import webbrowser
import json
import os
import pandas as pd
import time
import fitz
from PIL import Image, ImageTk
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import subprocess  
import sys  
import urllib.parse
from datetime import datetime
import sqlite3
from datetime import datetime as dt
import zipfile
import re
import shutil
import threading
import tempfile
import math
import qrcode
from PIL import Image, ImageTk
import cv2
from pyzbar.pyzbar import decode
from PIL import Image, ImageTk
import numpy as np
import secrets
import shutil


if getattr(sys, 'frozen', False):
    BASE_PATH = sys._MEIPASS
else:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))
IMG_PATH = os.path.join(BASE_PATH, "img")

_OriginalToplevel = tk.Toplevel

class Toplevel(_OriginalToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aplicar_icono_personalizado()
        self._configurar_como_emergente()

    def _aplicar_icono_personalizado(self):
        try:
            ruta_ico = os.path.join(IMG_PATH, "mi_icono.ico")   # Opcional (Windows)
            ruta_png = os.path.join(IMG_PATH, "mi_icono.png")   # Fallback (PNG)
            if sys.platform == 'win32' and os.path.exists(ruta_ico):
                self.iconbitmap(ruta_ico)
            elif os.path.exists(ruta_png):
                icono = tk.PhotoImage(file=ruta_png)
                self.iconphoto(True, icono)
                self._icono_ref = icono
        except Exception as e:
            print(f"⚠️ No se pudo aplicar el icono a una ventana: {e}")

    def _configurar_como_emergente(self):
        """
        Hace que la ventana se mantenga siempre por encima de su ventana padre.
        - transient(parent): la vincula al padre, evitando que se oculte detrás.
        - lift() + focus_force(): la trae al frente al momento de crearse.
        """
        try:
            parent = self.master
            if parent is not None:
                # Si el padre existe y está visible, marcar como transient.
                # Esto hace que la ventana no pueda quedar DETRÁS del padre.
                try:
                    if parent.winfo_exists():
                        self.transient(parent)
                except Exception:
                    pass
        except Exception:
            pass

        # Diferimos el lift/focus hasta que la ventana esté dibujada.
        # 80 ms suele ser suficiente; puedes subirlo si notas que aún
        # aparece detrás en equipos muy lentos.
        self.after(80, self._traer_al_frente)

    def _traer_al_frente(self):
        """Sube la ventana al frente y le da el foco."""
        try:
            if not self.winfo_exists():
                return
            # Por si la ventana fue minimizada o creada oculta
            self.deiconify()
            self.lift()
            self.focus_force()
            # Pequeño truco extra: forzar topmost 1 instante y quitarlo
            # garantiza que aparezca por encima incluso en Windows.
            self.attributes('-topmost', True)
            self.after(200, self._quitar_topmost)
        except Exception:
            pass

    def _quitar_topmost(self):
        try:
            if self.winfo_exists():
                self.attributes('-topmost', False)
        except Exception:
            pass

def _get_user_backup_path():
    r"""
    Ruta oculta FUERA de la carpeta del proyecto para respaldar usuarios.
    En Windows: %APPDATA%\.salupago_cache\users.dat
    En Linux/Mac: ~/.salupago_cache/users.dat
    """
    appdata = os.environ.get('APPDATA') or os.path.expanduser('~')
    folder = os.path.join(appdata, '.salupago_cache')
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, 'users.dat')

def validar_cedula(cedula):
    """Valida que la cédula tenga entre 8 y 10 dígitos numéricos (ignora puntos, guiones y espacios)."""
    cedula_limpia = re.sub(r'[^0-9]', '', cedula)
    return bool(re.match(r'^\d{8,10}$', cedula_limpia))

def validar_correo(correo):
    """Valida formato de correo electrónico."""
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', correo))

def validar_celular(celular):
    """Valida celular colombiano: 10 dígitos, empieza con 3 (ignora puntos, guiones y espacios)."""
    celular_limpio = re.sub(r'[^0-9]', '', celular)
    return bool(re.match(r'^3\d{9}$', celular_limpio))

# config_manager.py
import os
import json
from copy import deepcopy

# Configuración por defecto (valores iniciales)
DEFAULT_CONFIG = {
    "base_path": None,
    "db_filename": "saluPago.db",
    "precios": {
        "eps": 120000,
        "arl": {
            "ARL 1": 55000,
            "ARL 2": 65000,
            "ARL 3": 75000,
            "ARL 4": 85000,
            "ARL 5": 95000
        },
        "pension": 150000,
        "caja": 100000
    },
    "opciones": {
        "eps": ["-/-", "Sura EPS", "Nueva EPS", "Sanitas EPS", "Compensar EPS",
                "Famisanar EPS", "Aliansalud EPS", "Salud Total EPS"],
        "arl": ["-/-", "ARL 1", "ARL 2", "ARL 3", "ARL 4", "ARL 5"],
        "pension": ["-/-", "Protección", "Porvenir", "Colfondos", "Colpensiones"],
        "caja_compensacion": ["-/-", "Compensar", "Cafam", "Colsubsidio"],
        "meses": ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"],
        "metodos_pago": ["Transferencia", "Efectivo"]
    },
    "caja": {
        "base_caja": 30000
    },
    "notificaciones": {
        "plantillas": {}
    },
    "monitoreo_umbrales": {
        "activo_hasta_dias": 3,
        "proximo_suspender_dias": 5,
        "suspendido_dias": 7
    },
    "empresa": {
        "nombre": "SaluPago",
        "nit": "900.123.456-7",
        "direccion": "Calle 123 #45-67",
        "telefono": "3022386236",
        "correo": "contacto@salupago.com"
    },
    "pago_imagen": "Nequi.png",
    "camera_ip_url": "http://192.168.0.3:8080/video",
    "backup_automatico": {
        "activo": False,
        "intervalo_horas": 8,
        "ultimo_backup": None,
        "dias_conservar": 2
    },
    "sonidos": {
        "activo": True,
        "volumen": 0.6
    },
    "boton_panico": {
    "activo": True,
    "correo_alerta": "andresberri15@gmail.com",
    "whatsapp_alerta": "3022386236",
    "mostrar_pantalla_falsa": True
    },
        "google_drive": {
        "activo": False,
        "subir_backup_automatico": True,
        "subir_backup_manual": True,
        "carpeta": "SaluPago_Backups",
        "dias_conservar_drive": 30
    }
}
def animacion_corazon_ecg(ventana, duracion=5.0, callback=None):
    """
    Muestra una animación de onda ECG con un corazón latiente.
    ventana: Toplevel donde se dibuja.
    duracion: segundos que dura la animación (para simular carga).
    callback: función a ejecutar al finalizar.
    """
    # Limpiar ventana (si tenía elementos anteriores)
    for widget in ventana.winfo_children():
        widget.destroy()

    # Frame contenedor
    frame = ttk.Frame(ventana)
    frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    # Mensaje de bienvenida
    lbl_titulo = ttk.Label(frame, text="Cargando SaluPago...", font=('Segoe UI', 14, 'bold'))
    lbl_titulo.pack(pady=(0, 10))

    # Canvas para la onda ECG y el corazón
    canvas_ancho = 400
    canvas_alto = 150
    canvas = tk.Canvas(frame, width=canvas_ancho, height=canvas_alto, bg='white', highlightthickness=0)
    canvas.pack(pady=10)

    # Variables de animación
    puntos = []               # Lista de (x, y) para la onda
    paso = 0                  # Contador de pasos (0 a 100)
    max_pasos = 100
    escala_x = canvas_ancho / max_pasos

    # Coordenadas del corazón (centro en la parte inferior derecha)
    cx = canvas_ancho - 40
    cy = canvas_alto - 30
    radio = 15
    radio_actual = radio

    # Función para dibujar un corazón usando polígonos
    def dibujar_corazon(canvas, cx, cy, radio, color='#e74c3c'):
        # Elimina corazón anterior si existe
        canvas.delete("corazon")
        # Polígono que forma un corazón (coordenadas relativas)
        puntos_corazon = [
            (cx, cy - radio * 0.3),
            (cx - radio * 0.7, cy - radio * 0.8),
            (cx - radio * 1.2, cy - radio * 0.2),
            (cx - radio * 0.8, cy + radio * 0.4),
            (cx, cy + radio * 0.8),
            (cx + radio * 0.8, cy + radio * 0.4),
            (cx + radio * 1.2, cy - radio * 0.2),
            (cx + radio * 0.7, cy - radio * 0.8),
        ]
        # Convertir a lista plana
        coords = []
        for x, y in puntos_corazon:
            coords.extend([x, y])
        canvas.create_polygon(coords, fill=color, outline='#c0392b', width=2, tags="corazon")

    # Dibujar corazón inicial
    dibujar_corazon(canvas, cx, cy, radio)

    # Etiqueta de porcentaje
    lbl_porcentaje = ttk.Label(frame, text="0%", font=('Segoe UI', 12))
    lbl_porcentaje.pack(pady=5)

    # Función de actualización
    def actualizar(progreso):
        nonlocal puntos, paso, radio_actual

        # Actualizar porcentaje
        lbl_porcentaje.config(text=f"{progreso}%")

        # Limpiar línea anterior (excepto el corazón)
        canvas.delete("onda")

        # Calcular nuevo punto de la onda (ECG realista)
        x = progreso * escala_x
        # Simular una onda ECG: pico QRS, onda T, etc.
        # Usamos una función con picos agudos
        if progreso < 10:
            y = canvas_alto/2 - 10 * math.sin(progreso * math.pi / 10)
        elif progreso < 20:
            y = canvas_alto/2 - 25 * math.sin((progreso-10) * math.pi / 10)
        elif progreso < 25:
            # Pico R (más alto)
            y = canvas_alto/2 - 40 * math.sin((progreso-20) * math.pi / 5)
        elif progreso < 30:
            y = canvas_alto/2 - 20 * math.sin((progreso-25) * math.pi / 5)
        elif progreso < 40:
            y = canvas_alto/2 - 10 * math.sin((progreso-30) * math.pi / 10)
        else:
            # Onda suave (Seno)
            y = canvas_alto/2 - 15 * math.sin(progreso * math.pi / 20)

        # Añadir punto
        puntos.append((x, y))
        # Si hay más de 100 puntos, eliminar los primeros para que no se salga
        if len(puntos) > max_pasos:
            puntos.pop(0)

        # Dibujar la línea con todos los puntos
        if len(puntos) > 1:
            # Crear lista de coordenadas
            coords = []
            for px, py in puntos:
                coords.extend([px, py])
            canvas.create_line(coords, fill='#2c3e50', width=3, smooth=True, tags="onda")

        # Animar el corazón: latido (cambiar tamaño y color)
        # Cada cierto progreso, hacer un latido fuerte
        if progreso % 10 == 0:
            # Latido fuerte
            radio_actual = radio + 8
            dibujar_corazon(canvas, cx, cy, radio_actual, '#e74c3c')
            # Después de 100ms, volver al tamaño normal
            canvas.after(100, lambda: dibujar_corazon(canvas, cx, cy, radio, '#e74c3c'))
        else:
            # Latido suave (pequeño cambio)
            radio_actual = radio + 2 * math.sin(progreso * math.pi / 10)
            dibujar_corazon(canvas, cx, cy, radio_actual, '#e74c3c')

        # Programar siguiente paso si no hemos terminado
        if progreso < 100:
            paso += 1
            canvas.after(30, lambda: actualizar(progreso + 1))
        else:
            # Terminado: llamar al callback
            if callback:
                callback()

    # Iniciar animación
    actualizar(0)

class ConfigManager:
    def __init__(self, config_dir=None):
        if config_dir is None:
            # Usamos la carpeta .BT del proyecto
            base_path = os.path.dirname(os.path.abspath(__file__))
            config_dir = os.path.join(base_path, ".BT")
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "config.json")
        self._config = None
        self._load()

    def _load(self):
        """Carga la configuración desde el archivo JSON. Si no existe, crea una por defecto."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                # Validar que tenga todas las claves necesarias (fusionar con default)
                self._merge_defaults()
            except Exception:
                self._config = deepcopy(DEFAULT_CONFIG)
                self._save()
        else:
            # Crear directorio si no existe
            os.makedirs(self.config_dir, exist_ok=True)
            self._config = deepcopy(DEFAULT_CONFIG)
            # Rellenar base_path
            self._config["base_path"] = os.path.dirname(os.path.abspath(__file__))
            self._save()

    def _merge_defaults(self):
        """Asegura que todas las claves de DEFAULT_CONFIG estén presentes (para compatibilidad)."""
        def merge_recursive(default, current):
            for key, value in default.items():
                if key not in current:
                    current[key] = deepcopy(value)
                elif isinstance(value, dict) and isinstance(current.get(key), dict):
                    merge_recursive(value, current[key])
        merge_recursive(DEFAULT_CONFIG, self._config)

    def _save(self):
        """Guarda la configuración actual en el archivo JSON."""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)

    def get(self, key, default=None):
        """Obtiene un valor de configuración usando notación de punto (ej: 'precios.eps')."""
        keys = key.split('.')
        value = self._config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key, value):
        """Establece un valor de configuración (notación de punto) y guarda."""
        keys = key.split('.')
        target = self._config
        for k in keys[:-1]:
            target = target.setdefault(k, {})
        target[keys[-1]] = value
        self._save()

    def get_all(self):
        """Retorna toda la configuración como diccionario."""
        return self._config

    def update(self, new_config):
        """Actualiza múltiples claves y guarda."""
        def deep_update(base, updates):
            for k, v in updates.items():
                if isinstance(v, dict) and isinstance(base.get(k), dict):
                    deep_update(base[k], v)
                else:
                    base[k] = v
        deep_update(self._config, new_config)
        self._save()

    @property
    def db_path(self):
        """Devuelve la ruta completa de la base de datos."""
        base = self.get('base_path') or os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, ".BT", self.get('db_filename', 'saluPago.db'))

    # Métodos de conveniencia para acceder a precios y opciones
    def get_precio_eps(self):
        return self.get('precios.eps', 120000)

    def get_precio_arl(self, arl_name):
        arl_precios = self.get('precios.arl', {})
        return arl_precios.get(arl_name, 0)

    def get_precio_pension(self):
        return self.get('precios.pension', 150000)

    def get_precio_caja(self):
        return self.get('precios.caja', 100000)

    def get_opciones(self, key):
        return self.get(f'opciones.{key}', [])

    def get_base_caja(self):
        return self.get('caja.base_caja', 30000)

    def get_backup_activo(self):
        return self.get('backup_automatico.activo', True)

    def get_backup_intervalo(self):
        return self.get('backup_automatico.intervalo_horas', 24)

    def set_backup_activo(self, valor):
        self.set('backup_automatico.activo', valor)

    def set_backup_intervalo(self, horas):
        self.set('backup_automatico.intervalo_horas', horas)

    def get_ultimo_backup(self):
        return self.get('backup_automatico.ultimo_backup', None)

    def set_ultimo_backup(self, timestamp):
        self.set('backup_automatico.ultimo_backup', timestamp)

    def get_dias_conservar_backup(self):
        return self.get('backup_automatico.dias_conservar', 2)

    def set_dias_conservar_backup(self, dias):
        self.set('backup_automatico.dias_conservar', dias)

    def get_sonidos_activo(self):
        return self.get('sonidos.activo', True)

    def set_sonidos_activo(self, valor):
        self.set('sonidos.activo', bool(valor))

    def get_sonidos_volumen(self):
        return self.get('sonidos.volumen', 0.6)

    def set_sonidos_volumen(self, valor):
        try:
            v = float(valor)
            v = max(0.0, min(1.0, v))
            self.set('sonidos.volumen', v)
        except (ValueError, TypeError):
            pass
    
    def get_panico_activo(self):
        return self.get('boton_panico.activo', True)

    def set_panico_activo(self, valor):
        self.set('boton_panico.activo', bool(valor))

    def get_panico_correo(self):
        return self.get('boton_panico.correo_alerta', '')

    def get_panico_whatsapp(self):
        return self.get('boton_panico.whatsapp_alerta', '')

    def get_panico_pantalla_falsa(self):
        return self.get('boton_panico.mostrar_pantalla_falsa', True)

    def get_drive_activo(self):
        return self.get('google_drive.activo', False)

    def set_drive_activo(self, valor):
        self.set('google_drive.activo', bool(valor))

    def get_drive_subir_auto(self):
        return self.get('google_drive.subir_backup_automatico', True)

    def get_drive_subir_manual(self):
        return self.get('google_drive.subir_backup_manual', True)

    def get_drive_carpeta(self):
        return self.get('google_drive.carpeta', 'SaluPago_Backups')

class Database:
    def __init__(self, db_path=None, config=None):
        # Si no se pasa config, creamos una instancia local
        if config is None:
            config = ConfigManager() 
        self.config = config
        if db_path is None:
            self.db_path = config.db_path  # usa la ruta definida en configuración
        else:
            self.db_path = db_path
        # Asegurar que la carpeta .BT existe
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_tables()

        self._init_tables()
        self._migrar_desde_json_si_existe()
        self.exportar_a_json()

        # ========== LÍNEA DE DEPURACIÓN ==========
        print(f"📁 Base de datos en: {self.db_path}")
        # =========================================

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_tables(self):
        """Crea todas las tablas si no existen."""
        with self._get_connection() as conn:
            c = conn.cursor()
            # Usuarios
            c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            )''')
            # Afiliados (activos y retirados en una sola tabla)
            c.execute('''CREATE TABLE IF NOT EXISTS afiliados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cc TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                celular TEXT,
                direccion TEXT,
                correo TEXT,
                fecha_ingreso TEXT,
                eps TEXT,
                arl TEXT,
                pension TEXT,
                caja_compensacion TEXT,
                mes_pago TEXT,
                valor_pagado REAL,
                metodo_pago TEXT,
                fecha_pago TEXT,
                fecha_retiro TEXT
            )''')
            # Archivados
            c.execute('''CREATE TABLE IF NOT EXISTS archivados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cc TEXT NOT NULL,
                nombre TEXT NOT NULL,
                celular TEXT,
                direccion TEXT,
                correo TEXT,
                fecha_ingreso TEXT,
                eps TEXT,
                arl TEXT,
                pension TEXT,
                caja_compensacion TEXT,
                mes_pago TEXT,
                valor_pagado REAL,
                metodo_pago TEXT,
                fecha_pago TEXT,
                fecha_retiro TEXT,
                motivo_retiro TEXT,
                fecha_archivo TEXT NOT NULL,
                motivo_archivo TEXT,
                usuario_archivo TEXT
            )''')
            # Tabla de beneficiarios
            c.execute('''CREATE TABLE IF NOT EXISTS beneficiarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cotizante_cc TEXT NOT NULL,
                tipo TEXT NOT NULL,
                nombre TEXT NOT NULL,
                documento_identidad TEXT,
                registro_civil TEXT,
                fecha_nacimiento TEXT,
                telefono TEXT,
                correo TEXT,
                direccion TEXT,
                fecha_registro TEXT,
                FOREIGN KEY (cotizante_cc) REFERENCES afiliados(cc) ON DELETE CASCADE
            )''')
            # Ingresos
            c.execute('''CREATE TABLE IF NOT EXISTS ingresos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                cc TEXT,
                nombre TEXT,
                servicio TEXT,
                valor REAL NOT NULL,
                metodo_pago TEXT,
                comprobante TEXT
            )''')
            # Egresos
            c.execute('''CREATE TABLE IF NOT EXISTS egresos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                valor REAL NOT NULL,
                metodo_pago TEXT
            )''')
            # Novedades
            c.execute('''CREATE TABLE IF NOT EXISTS novedades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                cc TEXT,
                nombre TEXT,
                novedad TEXT NOT NULL
            )''')
            # Incapacidades (con estado y fecha_estado)
            c.execute('''CREATE TABLE IF NOT EXISTS incapacidades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                eps TEXT NOT NULL,
                tipo TEXT NOT NULL,
                fecha_inicio TEXT NOT NULL,
                fecha_final TEXT NOT NULL,
                dias INTEGER,
                valor REAL NOT NULL,
                fecha_pago TEXT,
                estado TEXT DEFAULT 'Recibida',
                fecha_estado TEXT,
                recibo_descargado INTEGER DEFAULT 0
            )''')
            # Monitoreo
            c.execute('''CREATE TABLE IF NOT EXISTS monitoreo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cc TEXT NOT NULL,
                nombre TEXT NOT NULL,
                eps TEXT,
                descripcion TEXT,
                dias_mora INTEGER DEFAULT 0,
                estado TEXT,
                fecha_ultimo_pago TEXT,
                fecha_registro_estado TEXT
            )''')
            # Notificaciones
            c.execute('''CREATE TABLE IF NOT EXISTS notificaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                tipo TEXT NOT NULL,
                cc TEXT,
                nombre TEXT,
                mensaje TEXT NOT NULL,
                estado TEXT,
                fecha_vencimiento TEXT,
                tag TEXT
            )''')
            # Plantillas
            c.execute('''CREATE TABLE IF NOT EXISTS plantillas_notificaciones (
                clave TEXT PRIMARY KEY,
                titulo TEXT,
                mensaje TEXT
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS solicitudes_pago (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cc_afiliado TEXT NOT NULL,
                estado TEXT NOT NULL,
                monto REAL,
                mes TEXT,
                metodo_pago TEXT,
                fecha_creacion TEXT NOT NULL,
                fecha_actualizacion TEXT NOT NULL,
                mensaje_whatsapp TEXT,
                FOREIGN KEY (cc_afiliado) REFERENCES afiliados(cc) ON DELETE CASCADE
            )''')
            # Tabla de historial de backups
            c.execute('''CREATE TABLE IF NOT EXISTS backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                hora TEXT NOT NULL,
                tipo TEXT NOT NULL,
                usuario TEXT NOT NULL,
                tamaño REAL NOT NULL,
                estado TEXT NOT NULL,
                ubicacion TEXT NOT NULL
            )''')
            # Tabla de auditoría
            c.execute('''CREATE TABLE IF NOT EXISTS auditoria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                usuario TEXT NOT NULL,
                rol TEXT NOT NULL,
                accion TEXT NOT NULL,
                modulo TEXT NOT NULL,
                resultado TEXT NOT NULL,
                detalles TEXT
            )''')
            conn.commit()

            # Migrar incapacidades existentes para agregar columnas si es necesario
            self._migrar_incapacidades()

            # --- NUEVO: migrar afiliados para agregar columna motivo_retiro ---
            self._migrar_afiliados()

            # Usuario por defecto si no hay ninguno
            c.execute("SELECT COUNT(*) FROM usuarios")
            if c.fetchone()[0] == 0:
                c.execute("INSERT INTO usuarios (username, password, role) VALUES (?,?,?)",
                        ("MyAdmin", "admin123", "Administrativo"))
                c.execute("INSERT INTO usuarios (username, password, role) VALUES (?,?,?)",
                        ("Auxiliar", "aux123", "Auxiliar"))
                conn.commit()

            # ========== NUEVO: Restaurar usuarios desde respaldo de pánico ==========
            backup_path = _get_user_backup_path()
            if os.path.exists(backup_path):
                try:
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        usuarios_respaldo = json.load(f)
                    # Reemplazar la tabla usuarios con los del respaldo
                    c.execute("DELETE FROM usuarios")
                    for u in usuarios_respaldo:
                        c.execute(
                            "INSERT INTO usuarios (username, password, role) VALUES (?,?,?)",
                            (u['username'], u['password'], u['role'])
                        )
                    conn.commit()
                    # Respaldo de un solo uso: eliminar tras restaurar
                    os.remove(backup_path)
                    print("✅ Usuarios restaurados desde respaldo de pánico.")
                except Exception as e:
                    print(f"⚠️ No se pudieron restaurar usuarios: {e}")
            # =======================================================================
              
    def _migrar_desde_json_si_existe(self):
        import os, json
        from datetime import datetime

        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM afiliados")
            if c.fetchone()[0] > 0:
                return

        base_path = os.path.dirname(os.path.abspath(__file__))
        bt_folder = os.path.join(base_path, ".BT")
        archivos = {
            'afiliados': 'afiliados.json',
            'retiros': 'retiros.json',
            'contabilidad': 'contabilidad.json'
        }
        datos = {}
        for key, fname in archivos.items():
            path = os.path.join(bt_folder, fname)
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    datos[key] = json.load(f)
            else:
                datos[key] = [] if key != 'contabilidad' else {}

        if not datos['afiliados'] and not datos['retiros'] and not datos.get('contabilidad', {}):
            return

        # Insertar afiliados activos
        for af in datos.get('afiliados', []):
            af['fecha_retiro'] = None
            self.add_afiliado(af)

        # Insertar retirados
        for ret in datos.get('retiros', []):
            if 'fecha_retiro' not in ret or not ret['fecha_retiro']:
                ret['fecha_retiro'] = datetime.now().strftime("%Y-%m-%d")
            self.add_afiliado(ret)

        # Insertar contabilidad
        cont = datos.get('contabilidad', {})
        for ing in cont.get('ingresos', []):
            self.add_ingreso(ing)
        for eg in cont.get('egresos', []):
            self.add_egreso(eg)
        for nov in cont.get('novedades', []):
            self.add_novedad(nov)
        for inc in cont.get('incapacidades', []):
            self.add_incapacidad(inc)
        for mon in cont.get('monitoreo', []):
            self.add_monitoreo(mon)
        for notif in cont.get('notificaciones', []):
            self.add_notificacion(notif)
        for clave, data in cont.get('plantillas_notificaciones', {}).items():
            self.save_plantilla(clave, data.get('titulo', ''), data.get('mensaje', ''))

        # Renombrar a .bak (con manejo de existencia previa)
        for fname in archivos.values():
            path = os.path.join(bt_folder, fname)
            if os.path.exists(path):
                bak_path = path + '.bak'
                if os.path.exists(bak_path):
                    os.remove(bak_path)  # Eliminar el .bak antiguo para evitar FileExistsError
                os.rename(path, bak_path)

    # ---------- BENEFICIARIOS ----------
    def get_beneficiarios(self, cotizante_cc):
        """Devuelve la lista de beneficiarios de un cotizante."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM beneficiarios WHERE cotizante_cc = ? ORDER BY tipo, nombre", (cotizante_cc,))
            return [dict(row) for row in c.fetchall()]

    def add_beneficiario(self, data):
        """Inserta un nuevo beneficiario."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO beneficiarios 
                (cotizante_cc, tipo, nombre, documento_identidad, registro_civil, 
                fecha_nacimiento, telefono, correo, direccion, fecha_registro)
                VALUES (?,?,?,?,?,?,?,?,?,?)''',
                (data['cotizante_cc'], data['tipo'], data['nombre'],
                data.get('documento_identidad', ''), data.get('registro_civil', ''),
                data.get('fecha_nacimiento', ''), data.get('telefono', ''),
                data.get('correo', ''), data.get('direccion', ''),
                data.get('fecha_registro', datetime.now().strftime("%Y-%m-%d"))))
            conn.commit()
            return c.lastrowid

    def update_beneficiario(self, id_benef, data):
        """Actualiza los datos de un beneficiario."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute('''UPDATE beneficiarios SET
                tipo=?, nombre=?, documento_identidad=?, registro_civil=?,
                fecha_nacimiento=?, telefono=?, correo=?, direccion=?
                WHERE id=?''',
                (data['tipo'], data['nombre'], data.get('documento_identidad', ''),
                data.get('registro_civil', ''), data.get('fecha_nacimiento', ''),
                data.get('telefono', ''), data.get('correo', ''),
                data.get('direccion', ''), id_benef))
            conn.commit()

    def delete_beneficiario(self, id_benef):
        """Elimina un beneficiario por su id."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM beneficiarios WHERE id=?", (id_benef,))
            conn.commit()
                  
    def exportar_a_json(self):
        import os, json
        base_path = os.path.dirname(os.path.abspath(__file__))
        bt_folder = os.path.join(base_path, ".BT")
        os.makedirs(bt_folder, exist_ok=True)

        afiliados = self.get_afiliados_activos()
        retiros = self.get_afiliados_retirados()

        # Si tienes beneficiarios, exportarlos también
        beneficiarios = {}
        for af in afiliados:
            beneficiarios[af['cc']] = self.get_beneficiarios(af['cc'])
        for ret in retiros:
            beneficiarios[ret['cc']] = self.get_beneficiarios(ret['cc'])

        contabilidad = {
            'ingresos': self.get_ingresos(),
            'egresos': self.get_egresos(),
            'novedades': self.get_novedades(),
            'incapacidades': self.get_incapacidades(),
            'monitoreo': self.get_monitoreo(),
            'notificaciones': self.get_notificaciones(),
            'plantillas_notificaciones': self.get_plantillas()
        }

        # Eliminar campos 'id' para limpieza
        for af in afiliados:
            af.pop('id', None)
        for ret in retiros:
            ret.pop('id', None)
        for lista in [contabilidad['ingresos'], contabilidad['egresos'], contabilidad['novedades'],
                    contabilidad['incapacidades'], contabilidad['monitoreo'], contabilidad['notificaciones']]:
            for item in lista:
                item.pop('id', None)

        # Guardar archivos JSON
        with open(os.path.join(bt_folder, 'afiliados.json'), 'w', encoding='utf-8') as f:
            json.dump(afiliados, f, indent=2, ensure_ascii=False)

        with open(os.path.join(bt_folder, 'retiros.json'), 'w', encoding='utf-8') as f:
            json.dump(retiros, f, indent=2, ensure_ascii=False)

        with open(os.path.join(bt_folder, 'contabilidad.json'), 'w', encoding='utf-8') as f:
            json.dump(contabilidad, f, indent=2, ensure_ascii=False)

        # Guardar beneficiarios si existen
        if beneficiarios:
            with open(os.path.join(bt_folder, 'beneficiarios.json'), 'w', encoding='utf-8') as f:
                json.dump(beneficiarios, f, indent=2, ensure_ascii=False)
                
    # ---------- USUARIOS ----------
    def get_user(self, username):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT username, password, role FROM usuarios WHERE username=?", (username,))
            row = c.fetchone()
            if row:
                return {"username": row[0], "password": row[1], "role": row[2]}
            return None

        # ---------- USUARIOS (ampliación) ----------
    def get_all_users(self):
        """Devuelve todos los usuarios como lista de diccionarios."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT username, password, role FROM usuarios ORDER BY username")
            return [dict(row) for row in c.fetchall()]

    def get_all_beneficiarios(self):
        """Devuelve todos los beneficiarios de todos los afiliados."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM beneficiarios ORDER BY cotizante_cc, tipo, nombre")
            return [dict(row) for row in c.fetchall()]

    def add_user(self, username, password, role):
        """Inserta un nuevo usuario."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO usuarios (username, password, role) VALUES (?,?,?)",
                      (username, password, role))
            conn.commit()

    def update_user(self, username, new_password, new_role):
        """Actualiza contraseña y rol de un usuario."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE usuarios SET password=?, role=? WHERE username=?",
                      (new_password, new_role, username))
            conn.commit()

    def delete_user(self, username):
        """Elimina un usuario por su nombre."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM usuarios WHERE username=?", (username,))
            conn.commit()

    # ---------- AFILIADOS ----------
    def get_afiliados_activos(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM afiliados WHERE fecha_retiro IS NULL")
            return [dict(row) for row in c.fetchall()]

    def get_afiliados_retirados(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM afiliados WHERE fecha_retiro IS NOT NULL")
            return [dict(row) for row in c.fetchall()]

    def _migrar_afiliados(self):
        """Agrega la columna motivo_retiro a la tabla afiliados si no existe."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("PRAGMA table_info(afiliados)")
            columnas = [col[1] for col in c.fetchall()]
            if 'motivo_retiro' not in columnas:
                c.execute("ALTER TABLE afiliados ADD COLUMN motivo_retiro TEXT")
                conn.commit()

    def add_afiliado(self, data):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO afiliados
                (cc, nombre, celular, direccion, correo, fecha_ingreso,
                 eps, arl, pension, caja_compensacion, mes_pago,
                 valor_pagado, metodo_pago, fecha_pago, fecha_retiro)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (data['cc'], data['nombre'], data.get('celular', ''),
                 data.get('direccion', ''), data.get('correo', ''),
                 data.get('fecha_ingreso', ''), data.get('eps', ''),
                 data.get('arl', ''), data.get('pension', ''),
                 data.get('caja_compensacion', ''), data.get('mes_pago', ''),
                 float(data.get('valor_pagado', 0) or 0),
                 data.get('metodo_pago', ''), data.get('fecha_pago', ''),
                 data.get('fecha_retiro', None)))
            conn.commit()

    def update_afiliado(self, cc, data):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute('''UPDATE afiliados SET
                cc=?, nombre=?, celular=?, direccion=?, correo=?, fecha_ingreso=?,
                eps=?, arl=?, pension=?, caja_compensacion=?, mes_pago=?,
                valor_pagado=?, metodo_pago=?, fecha_pago=?
                WHERE cc=?''',
                (data['cc'], data['nombre'], data.get('celular', ''), data.get('direccion', ''),
                data.get('correo', ''), data.get('fecha_ingreso', ''),
                data.get('eps', ''), data.get('arl', ''), data.get('pension', ''),
                data.get('caja_compensacion', ''), data.get('mes_pago', ''),
                float(data.get('valor_pagado', 0) or 0),
                data.get('metodo_pago', ''), data.get('fecha_pago', ''), cc))
            conn.commit()

    def retirar_afiliado(self, cc, fecha_retiro):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE afiliados SET fecha_retiro=? WHERE cc=?", (fecha_retiro, cc))
            conn.commit()

    def retirar_afiliado(self, cc, fecha_retiro, motivo=None):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE afiliados SET fecha_retiro=?, motivo_retiro=? WHERE cc=?",
                    (fecha_retiro, motivo, cc))
            conn.commit()

    def reactivar_afiliado(self, cc):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE afiliados SET fecha_retiro=NULL, motivo_retiro=NULL WHERE cc=?", (cc,))
            conn.commit()

    def delete_afiliado(self, cc):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM afiliados WHERE cc=?", (cc,))
            conn.commit()

    # ---------- ARCHIVADOS ----------

    def archivar_afiliado(self, cc, motivo_archivo="", usuario=""):
        """Mueve un afiliado (activo o retirado) a la tabla de archivados."""
        # Obtener los datos del afiliado
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM afiliados WHERE cc = ?", (cc,))
            row = c.fetchone()
            if not row:
                return False
            # Convertir a diccionario
            columns = [description[0] for description in c.description]
            data = dict(zip(columns, row))
            # Agregar campos de archivo
            data['fecha_archivo'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data['motivo_archivo'] = motivo_archivo
            data['usuario_archivo'] = usuario
            # Insertar en archivados
            placeholders = ', '.join(['?' for _ in data])
            columns_str = ', '.join(data.keys())
            c.execute(f"INSERT INTO archivados ({columns_str}) VALUES ({placeholders})", list(data.values()))
            # Eliminar de afiliados
            c.execute("DELETE FROM afiliados WHERE cc = ?", (cc,))
            # Eliminar también de monitoreo (ya no es necesario)
            c.execute("DELETE FROM monitoreo WHERE cc = ?", (cc,))
            conn.commit()
            return True

    def get_archivados(self):
        """Devuelve todos los registros archivados."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM archivados ORDER BY fecha_archivo DESC")
            return [dict(row) for row in c.fetchall()]

    def eliminar_definitivamente(self, cc):
        """Elimina físicamente un registro de la tabla archivados."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM archivados WHERE cc = ?", (cc,))
            conn.commit()

    def restaurar_archivado(self, cc):
        """Devuelve un archivado a la tabla afiliados (conservando fecha_retiro si existe)."""
        with self._get_connection() as conn:
            c = conn.cursor()
            # Obtener datos del archivado
            c.execute("SELECT * FROM archivados WHERE cc = ?", (cc,))
            row = c.fetchone()
            if not row:
                return False
            columns = [description[0] for description in c.description]
            data = dict(zip(columns, row))
            # Remover campos propios de archivo
            data.pop('fecha_archivo', None)
            data.pop('motivo_archivo', None)
            data.pop('usuario_archivo', None)
            # Insertar de nuevo en afiliados
            placeholders = ', '.join(['?' for _ in data])
            columns_str = ', '.join(data.keys())
            c.execute(f"INSERT INTO afiliados ({columns_str}) VALUES ({placeholders})", list(data.values()))
            # Eliminar de archivados
            c.execute("DELETE FROM archivados WHERE cc = ?", (cc,))
            # También restaurar monitoreo? Podemos crear un nuevo registro de monitoreo
            # (opcional, se actualizará automáticamente con actualizar_estados_pago)
            conn.commit()
            return True

    # ---------- INGRESOS ----------
    def get_ingresos(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM ingresos ORDER BY fecha DESC")
            return [dict(row) for row in c.fetchall()]

    def add_ingreso(self, data):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO ingresos
                (fecha, cc, nombre, servicio, valor, metodo_pago, comprobante)
                VALUES (?,?,?,?,?,?,?)''',
                (data['fecha'], data.get('cc', ''), data.get('nombre', ''),
                 data['servicio'], float(data['valor']), data.get('metodo_pago', ''),
                 data.get('comprobante', '')))
            conn.commit()
            return c.lastrowid

    def delete_ingreso(self, id):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM ingresos WHERE id=?", (id,))
            conn.commit()

    # ---------- EGRESOS ----------
    def get_egresos(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM egresos ORDER BY fecha DESC")
            return [dict(row) for row in c.fetchall()]

    def add_egreso(self, data):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO egresos
                (fecha, descripcion, valor, metodo_pago)
                VALUES (?,?,?,?)''',
                (data['fecha'], data['descripcion'], float(data['valor']),
                 data.get('metodo_pago', '')))
            conn.commit()
            return c.lastrowid

    def delete_egreso(self, id):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM egresos WHERE id=?", (id,))
            conn.commit()

    # ---------- NOVEDADES ----------
    def get_novedades(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM novedades ORDER BY fecha DESC")
            return [dict(row) for row in c.fetchall()]

    def add_novedad(self, data):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO novedades (fecha, cc, nombre, novedad)
                VALUES (?,?,?,?)''',
                (data['fecha'], data.get('cc', ''), data.get('nombre', ''), data['novedad']))
            conn.commit()
            return c.lastrowid

    def update_novedad(self, id, data):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute('''UPDATE novedades SET fecha=?, cc=?, nombre=?, novedad=?
                WHERE id=?''',
                (data['fecha'], data.get('cc', ''), data.get('nombre', ''),
                 data['novedad'], id))
            conn.commit()

    def delete_novedad(self, id):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM novedades WHERE id=?", (id,))
            conn.commit()

    # ---------- INCAPACIDADES ----------
    def _migrar_incapacidades(self):
        """Agrega las columnas estado, fecha_estado y recibo_descargado si no existen."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("PRAGMA table_info(incapacidades)")
            columns = [col[1] for col in c.fetchall()]
            if 'estado' not in columns:
                c.execute("ALTER TABLE incapacidades ADD COLUMN estado TEXT DEFAULT 'Recibida'")
            if 'fecha_estado' not in columns:
                c.execute("ALTER TABLE incapacidades ADD COLUMN fecha_estado TEXT")
            if 'recibo_descargado' not in columns:
                c.execute("ALTER TABLE incapacidades ADD COLUMN recibo_descargado INTEGER DEFAULT 0")
            # Actualizar registros existentes
            c.execute("UPDATE incapacidades SET estado='Pagada' WHERE fecha_pago IS NOT NULL AND estado IS NULL")
            c.execute("UPDATE incapacidades SET estado='Recibida' WHERE estado IS NULL")
            c.execute("UPDATE incapacidades SET fecha_estado = fecha_pago WHERE fecha_pago IS NOT NULL AND fecha_estado IS NULL")
            conn.commit()

    def get_incapacidades(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM incapacidades ORDER BY fecha_inicio DESC")
            return [dict(row) for row in c.fetchall()]

    def add_incapacidad(self, data):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO incapacidades
                (nombre, eps, tipo, fecha_inicio, fecha_final, dias, valor, fecha_pago, estado, fecha_estado, recibo_descargado)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                (data['nombre'], data['eps'], data['tipo'],
                data['fecha_inicio'], data['fecha_final'],
                data.get('dias', 0), float(data['valor']),
                data.get('fecha_pago', ''),
                data.get('estado', 'Recibida'),
                data.get('fecha_estado', ''),
                data.get('recibo_descargado', 0)
                ))
            conn.commit()
            return c.lastrowid

    def update_incapacidad(self, id, data):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute('''UPDATE incapacidades SET
                nombre=?, eps=?, tipo=?, fecha_inicio=?, fecha_final=?,
                dias=?, valor=?, fecha_pago=?, estado=?, fecha_estado=?, recibo_descargado=?
                WHERE id=?''',
                (data['nombre'], data['eps'], data['tipo'],
                data['fecha_inicio'], data['fecha_final'],
                data.get('dias', 0), float(data['valor']),
                data.get('fecha_pago', ''),
                data.get('estado', 'Recibida'),
                data.get('fecha_estado', ''),
                data.get('recibo_descargado', 0),
                id))
            conn.commit()

    def delete_incapacidad(self, id):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM incapacidades WHERE id=?", (id,))
            conn.commit()

    # ---------- MONITOREO ----------
    def get_monitoreo(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM monitoreo ORDER BY dias_mora DESC")
            return [dict(row) for row in c.fetchall()]

    def add_monitoreo(self, data):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO monitoreo
                (cc, nombre, eps, descripcion, dias_mora,
                 estado, fecha_ultimo_pago, fecha_registro_estado)
                VALUES (?,?,?,?,?,?,?,?)''',
                (data['cc'], data['nombre'], data.get('eps', ''),
                 data.get('descripcion', ''), data.get('dias_mora', 0),
                 data.get('estado', ''), data.get('fecha_ultimo_pago', ''),
                 data.get('fecha_registro_estado', '')))
            conn.commit()

    def update_monitoreo(self, cc, data):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute('''UPDATE monitoreo SET
                nombre=?, eps=?, descripcion=?, dias_mora=?,
                estado=?, fecha_ultimo_pago=?, fecha_registro_estado=?
                WHERE cc=?''',
                (data['nombre'], data.get('eps', ''), data.get('descripcion', ''),
                 data.get('dias_mora', 0), data.get('estado', ''),
                 data.get('fecha_ultimo_pago', ''),
                 data.get('fecha_registro_estado', ''), cc))
            conn.commit()

    def delete_monitoreo(self, cc):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM monitoreo WHERE cc=?", (cc,))
            conn.commit()

    # ---------- NOTIFICACIONES ----------
    def get_notificaciones(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM notificaciones ORDER BY fecha_vencimiento")
            return [dict(row) for row in c.fetchall()]

    def add_notificacion(self, data):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO notificaciones
                (fecha, tipo, cc, nombre, mensaje, estado, fecha_vencimiento, tag)
                VALUES (?,?,?,?,?,?,?,?)''',
                (data['fecha'], data['tipo'], data.get('cc', ''),
                 data.get('nombre', ''), data['mensaje'], data.get('estado', 'Pendiente'),
                 data.get('fecha_vencimiento', ''), data.get('tag', '')))
            conn.commit()
            return c.lastrowid

    def update_notificacion_estado(self, id, estado):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE notificaciones SET estado=? WHERE id=?", (estado, id))
            conn.commit()

    def delete_notificacion(self, id):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM notificaciones WHERE id=?", (id,))
            conn.commit()

    # ---------- PLANTILLAS ----------
    def get_plantillas(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM plantillas_notificaciones")
            return {row['clave']: {'titulo': row['titulo'], 'mensaje': row['mensaje']}
                    for row in c.fetchall()}

    def save_plantilla(self, clave, titulo, mensaje):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute('''INSERT OR REPLACE INTO plantillas_notificaciones (clave, titulo, mensaje)
                VALUES (?,?,?)''', (clave, titulo, mensaje))
            conn.commit()

    def afiliado_exists(self, cc):
        """Verifica si existe un afiliado (activo o retirado) con la cédula dada."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT 1 FROM afiliados WHERE cc = ?", (cc,))
            return c.fetchone() is not None

    def crear_solicitud(self, cc, monto=None, mes=None, metodo_pago=None, mensaje=None, estado='enviada'):
        self._cerrar_solicitudes_activas(cc)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO solicitudes_pago 
                (cc_afiliado, estado, monto, mes, metodo_pago, fecha_creacion, fecha_actualizacion, mensaje_whatsapp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (cc, estado, monto, mes, metodo_pago, now, now, mensaje))
            conn.commit()
            return c.lastrowid

    def _cerrar_solicitudes_activas(self, cc):
        """Marca como 'cancelada' las solicitudes activas anteriores (enviada o cliente_confirmado)."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute('''UPDATE solicitudes_pago SET estado='cancelada', fecha_actualizacion=?
                WHERE cc_afiliado=? AND estado IN ('enviada', 'cliente_confirmado')''',
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), cc))
            conn.commit()

    def obtener_solicitud_activa(self, cc):
        """Devuelve la solicitud activa (estado enviada o cliente_confirmado) o None."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('''SELECT * FROM solicitudes_pago 
                WHERE cc_afiliado=? AND estado IN ('enviada', 'cliente_confirmado')
                ORDER BY fecha_creacion DESC LIMIT 1''', (cc,))
            row = c.fetchone()
            return dict(row) if row else None

    def actualizar_solicitud(self, id_solicitud, estado, **kwargs):
        """Actualiza estado y campos adicionales de una solicitud."""
        campos = ['estado=?']
        valores = [estado]
        for campo in ['monto', 'mes', 'metodo_pago', 'mensaje_whatsapp']:
            if campo in kwargs and kwargs[campo] is not None:
                campos.append(f"{campo}=?")
                valores.append(kwargs[campo])
        valores.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))  # fecha_actualizacion
        valores.append(id_solicitud)
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(f"UPDATE solicitudes_pago SET {', '.join(campos)}, fecha_actualizacion=? WHERE id=?", valores)
            conn.commit()

    def obtener_solicitud_reciente(self, cc):
        """Devuelve la solicitud de pago más reciente para un afiliado (sin importar el estado)."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('''SELECT * FROM solicitudes_pago 
                WHERE cc_afiliado=? 
                ORDER BY fecha_creacion DESC LIMIT 1''', (cc,))
            row = c.fetchone()
            return dict(row) if row else None

    # ---------- BACKUPS ----------
    def add_backup(self, fecha, hora, tipo, usuario, tamaño, estado, ubicacion):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO backups (fecha, hora, tipo, usuario, tamaño, estado, ubicacion)
                        VALUES (?,?,?,?,?,?,?)''',
                    (fecha, hora, tipo, usuario, tamaño, estado, ubicacion))
            conn.commit()
            return c.lastrowid

    def get_backups(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM backups ORDER BY fecha DESC, hora DESC")
            return [dict(row) for row in c.fetchall()]

    def delete_backup(self, backup_id):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM backups WHERE id=?", (backup_id,))
            conn.commit()

    def get_backup_by_id(self, backup_id):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM backups WHERE id=?", (backup_id,))
            row = c.fetchone()
            return dict(row) if row else None

    def registrar_auditoria(self, fecha, usuario, rol, accion, modulo, resultado, detalles=None):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO auditoria 
                        (fecha, usuario, rol, accion, modulo, resultado, detalles)
                        VALUES (?,?,?,?,?,?,?)''',
                    (fecha, usuario, rol, accion, modulo, resultado, detalles))
            conn.commit()

    def get_auditoria(self, filtros=None):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            query = "SELECT * FROM auditoria WHERE 1=1"
            params = []
            if filtros:
                if filtros.get('fecha_desde'):
                    query += " AND fecha >= ?"
                    params.append(filtros['fecha_desde'])
                if filtros.get('fecha_hasta'):
                    query += " AND fecha <= ?"
                    params.append(filtros['fecha_hasta'])
                if filtros.get('usuario'):
                    query += " AND usuario LIKE ?"
                    params.append(f"%{filtros['usuario']}%")
                if filtros.get('modulo'):
                    query += " AND modulo LIKE ?"
                    params.append(f"%{filtros['modulo']}%")
            query += " ORDER BY fecha DESC"
            c.execute(query, params)
            return [dict(row) for row in c.fetchall()]
                            
#BASE_PATH = os.path.dirname(os.path.abspath(__file__)) #Relativa

# ============================================================
# GESTOR DE SONIDOS
# ============================================================
import threading

class SoundManager:
    """Gestor de sonidos asíncronos usando pygame.mixer."""
    _inicializado = False
    _sonidos = {}
    _habilitado = True
    _volumen = 0.6

    @classmethod
    def _init(cls):
        if cls._inicializado:
            return
        try:
            import pygame
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
            cls._inicializado = True
        except Exception as e:
            print(f"⚠️ No se pudo inicializar el audio: {e}")

    @classmethod
    def precargar(cls, carpeta):
        """Carga todos los .wav/.ogg/.mp3 de la carpeta."""
        cls._init()
        if not cls._inicializado:
            return
        import pygame
        if not os.path.exists(carpeta):
            print(f"⚠️ Carpeta de sonidos no encontrada: {carpeta}")
            return
        for archivo in os.listdir(carpeta):
            if archivo.lower().endswith((".wav", ".ogg", ".mp3")):
                clave = os.path.splitext(archivo)[0]
                try:
                    cls._sonidos[clave] = pygame.mixer.Sound(os.path.join(carpeta, archivo))
                    print(f"🔊 Sonido cargado: {clave}")
                except Exception as e:
                    print(f"No se pudo cargar {archivo}: {e}")

    @classmethod
    def reproducir(cls, clave, volumen=None):
        """Reproduce un sonido por su clave (sin extensión)."""
        if not cls._habilitado:
            return
        cls._init()
        if not cls._inicializado or clave not in cls._sonidos:
            return
        vol = volumen if volumen is not None else cls._volumen

        def _play():
            try:
                sonido = cls._sonidos[clave]
                sonido.set_volume(vol)
                sonido.play()
            except Exception:
                pass
        threading.Thread(target=_play, daemon=True).start()

    @classmethod
    def set_habilitado(cls, valor):
        cls._habilitado = bool(valor)

    @classmethod
    def set_volumen(cls, valor):
        cls._volumen = max(0.0, min(1.0, float(valor)))

    @classmethod
    def detener_todos(cls):
        try:
            import pygame
            pygame.mixer.stop()
        except Exception:
            pass

class MenuPrincipal:
    def __init__(self, root):
        self.root = root
        self.root.title("SaluPago - Menú Principal")
        self.root.geometry("550x400")  # Aumentado a 450 de alto
        self.root.resizable(False, False)
        self.centrar_ventana(550, 400)

        # Estilos (sin cambios)
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('.', background='#f0f4f8', font=('Segoe UI', 11))
        self.style.configure('TFrame', background='#f0f4f8')
        self.style.configure('TLabel', background='#f0f4f8')
        self.style.configure('Title.TLabel', font=('Segoe UI', 20, 'bold'), foreground='#1a237e')
        self.style.configure('Menu.TButton', font=('Segoe UI', 14, 'bold'), padding=15)

        # Frame principal
        main_frame = ttk.Frame(self.root, padding=30)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ---- Logo ----
        try:
            logo_path = os.path.join(IMG_PATH, "LogoSaluPago.png")
            if os.path.exists(logo_path):
                logo = Image.open(logo_path)
                logo = logo.resize((350, 180), Image.LANCZOS)  # Ajuste de tamaño
                logo_img = ImageTk.PhotoImage(logo)
                logo_label = ttk.Label(main_frame, image=logo_img)
                logo_label.image = logo_img
                logo_label.pack(pady=(0, 10))
            else:
                ttk.Label(main_frame, text="SaluPago", style='Title.TLabel').pack(pady=(0, 10))
        except:
            ttk.Label(main_frame, text="SaluPago", style='Title.TLabel').pack(pady=(0, 10))

        # ---- Botones horizontales ----
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)

        ttk.Button(
            btn_frame,
            text="👔 Empleado",
            style='Menu.TButton',
            width=12,
            command=self.abrir_login_empleado
        ).pack(side=tk.LEFT, padx=15)

        ttk.Button(
            btn_frame,
            text="👤 Cliente",
            style='Menu.TButton',
            width=12,
            command=self.abrir_portal_cliente
        ).pack(side=tk.LEFT, padx=15)

        # ---- Footer (solo versión) ----
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))

        ttk.Label(
            footer_frame,
            text="D. R.A.V Versión 4.0.8",
            font=('Segoe UI', 9, 'italic'),
            foreground='#999'
        ).pack(side=tk.RIGHT)

        # Referencias a ventanas (sin cambios)
        self.login_ventana = None
        self.cliente_ventana = None

    def aplicar_icono_a_ventana(self, ventana):
        """
        Aplica el icono personalizado a cualquier ventana (root o Toplevel).
        Úsalo después de crear cada Toplevel.
        """
        ruta_icono_ico = os.path.join(IMG_PATH, "mi_icono.ico")
        ruta_icono_png = os.path.join(IMG_PATH, "mi_icono.png")
        try:
            if sys.platform == 'win32' and os.path.exists(ruta_icono_ico):
                ventana.iconbitmap(ruta_icono_ico)
            elif os.path.exists(ruta_icono_png):
                # Es importante mantener una referencia para que no se borre de memoria
                icono = tk.PhotoImage(file=ruta_icono_png)
                ventana.iconphoto(True, icono)
                ventana._icono_ref = icono  # Referencia para evitar garbage collection
        except Exception as e:
            print(f"No se pudo aplicar el icono a la ventana: {e}")

    def centrar_ventana(self, width, height):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def abrir_login_empleado(self):
        self.root.withdraw()
        login_root = tk.Toplevel(self.root)
        login_root.title("SaluPago - Inicio de Sesión")
        login_root.geometry("400x450")
        login_root.resizable(False, False)
        self.centrar_toplevel(login_root, 400, 450)
        
        # ⬇️ AGREGA ESTA LÍNEA ⬇️
        self.aplicar_icono_a_ventana(login_root)

        self.login_ventana = LoginWindow(
            login_root,
            mostrar_boton_cliente=False,
            menu_principal=self
        )
        login_root.protocol("WM_DELETE_WINDOW", self.mostrar_menu_desde_login)

    def abrir_portal_cliente(self):
        self.root.withdraw()
        cliente_root = tk.Toplevel(self.root)
        cliente_root.title("Portal del Cliente - SaluPago")
        cliente_root.geometry("500x450")
        cliente_root.resizable(False, False)
        self.centrar_toplevel(cliente_root, 500, 450)

        # ⬇️ AGREGA ESTA LÍNEA ⬇️
        self.aplicar_icono_a_ventana(cliente_root)

        self.cliente_ventana = ClienteWindow(
            cliente_root,
            db=Database(),
            cedula=None,
            menu_principal=self
        )
        cliente_root.protocol("WM_DELETE_WINDOW", self.mostrar_menu_desde_cliente)

    def centrar_toplevel(self, window, width, height):
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        window.geometry(f'{width}x{height}+{x}+{y}')

    def mostrar_menu(self):
        """Muestra el menú principal y lo trae al frente de forma forzada."""
        self.root.deiconify()
        self.root.state('normal')          # Asegura que no esté minimizada
        self.root.lift()
        self.root.focus_force()
        # Coloca la ventana por encima de todas temporalmente
        self.root.attributes('-topmost', True)
        # Desactiva 'topmost' después de 100 ms para no interferir
        self.root.after(100, lambda: self.root.attributes('-topmost', False))

    def mostrar_menu_desde_login(self):
        """Se llama cuando se cierra la ventana de login (empleado)."""
        if self.login_ventana:
            self.login_ventana = None
        self.mostrar_menu()

    def mostrar_menu_desde_cliente(self):
        """Se llama cuando se cierra la ventana del cliente."""
        if self.cliente_ventana:
            self.cliente_ventana = None
        # Espera 100 ms para que la ventana hija termine de destruirse
        self.root.after(100, self.mostrar_menu)

class LoginWindow:
    def __init__(self, root, mostrar_boton_cliente=True, menu_principal=None):
        self.root = root
        self.mostrar_boton_cliente = mostrar_boton_cliente
        self.menu_principal = menu_principal
        self.db = Database()
        self.root.title("SaluPago - Inicio de Sesión")
        self.root.geometry("400x450")
        self.root.resizable(False, False)
        self.center_window(self.root, 400, 450)
        self.setup_styles()
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.setup_login_interface()
        # Para la aplicación principal (Toplevel)
        self.app_ventana = None
    
    
    def center_window(self, window, width, height):
        """Centra una ventana en la pantalla"""
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        
        # Calcular posición x e y
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        
        window.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_styles(self):
        """Configura los estilos visuales de la aplicación"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Configuraciones generales
        self.style.configure('.', background='#f0f0f0', font=('Arial', 10))
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0')
        self.style.configure('TButton', padding=5)
        
        # Estilos personalizados
        self.style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        # --- Cambio aquí: fondo gris en lugar de blanco ---
        self.style.configure('Login.TFrame', background='#f0f0f0', borderwidth=0, relief='flat')
        self.style.configure('Footer.TLabel', font=('Arial', 8), foreground='#666666')
    
    def load_users(self):
        # Ya no se usa, se obtienen de la BD en tiempo real
        return {}
    
    def save_users(self):
        """Guarda los usuarios en el archivo JSON"""
        try:
            users_path = os.path.join(BASE_PATH, 'users.json')
            with open(users_path, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron guardar los usuarios: {str(e)}")
    
    def setup_login_interface(self):
        """Configura la interfaz de inicio de sesión con logo a la izquierda y formulario a la derecha"""
        # Centrar la ventana con el tamaño deseado
        self.center_window(self.root, 850, 450)

        main_frame = ttk.Frame(self.root, style='Login.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)

        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=2)

        # ---- Columna izquierda: Logo ----
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)

        try:
            logo_path = os.path.join(IMG_PATH, "LogoSP2.png")
            if os.path.exists(logo_path):
                logo = Image.open(logo_path)
                logo = logo.resize((470, 400), Image.LANCZOS)
                logo_img = ImageTk.PhotoImage(logo)
                logo_label = ttk.Label(left_frame, image=logo_img)
                logo_label.image = logo_img
                logo_label.grid(row=0, column=0, sticky="nsew")
            else:
                ttk.Label(left_frame, text="SaluPago", style='Title.TLabel').grid(row=0, column=0)
        except Exception as e:
            print(f"❌ Error cargando el logo: {str(e)}")
            ttk.Label(left_frame, text="SaluPago", style='Title.TLabel').grid(row=0, column=0)

        # ---- Columna derecha: Formulario (centrado) ----
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)

        # Frame interno para centrar todo verticalmente
        center_frame = ttk.Frame(right_frame)
        center_frame.pack(expand=True, anchor='center')

        ttk.Label(center_frame, text="Sistema de Pagos", font=('Segoe UI', 14, 'bold')).pack(pady=(0, 20))

        form_frame = ttk.Frame(center_frame)
        form_frame.pack(pady=10)

        ttk.Label(form_frame, text="Usuario:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        # ========== CAMBIO: Combobox con autocompletado ==========
        # Obtener lista de nombres de usuario desde la base de datos
        usuarios = [u['username'] for u in self.db.get_all_users()]
        self.username_entry = ttk.Combobox(
            form_frame,
            textvariable=self.username_var,
            values=usuarios,
            width=25,
            state='normal'          # Permite escribir y seleccionar
        )
        self.username_entry.grid(row=0, column=1, padx=5, pady=5)
        self.username_entry.bind('<Return>', lambda event: self.verify_login())
        # ========================================================

        ttk.Label(form_frame, text="Contraseña:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.password_entry = ttk.Entry(
            form_frame,
            textvariable=self.password_var,
            show="*",
            width=25
        )
        self.password_entry.grid(row=1, column=1, padx=5, pady=5)
        self.password_entry.bind('<Return>', lambda event: self.verify_login())

        button_frame = ttk.Frame(center_frame)
        button_frame.pack(pady=20)

        login_button = ttk.Button(button_frame, text="🔐 Acceder", command=self.verify_login)
        login_button.pack(side=tk.LEFT, padx=10)

        ttk.Button(button_frame, text="↩️ Volver",
                command=self.cerrar_ventana).pack(side=tk.RIGHT, padx=10)

        # Asociar Enter también al botón de acceso
        self.username_entry.bind('<Return>', lambda event: self.verify_login())
        self.password_entry.bind('<Return>', lambda event: self.verify_login())
        login_button.bind('<Return>', lambda event: self.verify_login())

        footer_frame = ttk.Frame(center_frame)
        footer_frame.pack(fill=tk.X, pady=(20, 0))
        inner_footer = ttk.Frame(footer_frame)
        inner_footer.pack()
        ttk.Label(inner_footer, text="Desarrollado por: R.A.V", style='Footer.TLabel').pack()
        ttk.Label(inner_footer, text="Versión 4.0.8", font=('Segoe UI', 8, 'italic'), foreground='#999').pack()

        # Poner el foco en el campo de usuario
        self.username_entry.focus_set()
                                    
    def cerrar_ventana(self):
        """Cierra la ventana de login y muestra el menú principal si existe."""
        self.root.destroy()
        if self.menu_principal:
            self.menu_principal.mostrar_menu()

    def abrir_aplicacion(self, role):
        app_root = tk.Toplevel(self.root)
        app_root.title(f"SaluPago - {role.capitalize()}")
        app_root.state('zoomed')
        self.app_ventana = app_root
        app = SaluPagoApp(app_root, role, self.current_username, self.menu_principal)  # <--- Pasa menu_principal
        app_root.protocol("WM_DELETE_WINDOW", lambda: self.cerrar_aplicacion(app_root))
        self.root.destroy()

    def cerrar_aplicacion(self, app_root):
        """Cierra la aplicación y muestra el menú principal."""
        app_root.destroy()
        if self.menu_principal:
            self.menu_principal.mostrar_menu()
    
    def verify_login(self):
        username = self.username_var.get()
        password = self.password_var.get()
        if not username or not password:
            messagebox.showerror("Error", "Por favor ingrese usuario y contraseña")
            # Enfocar el campo que falta o el primero si ambos faltan
            if not username:
                self.username_entry.focus_set()
                self.username_entry.select_range(0, tk.END)
            else:
                self.password_entry.focus_set()
                self.password_entry.select_range(0, tk.END)
            return

        user = self.db.get_user(username)
        if user and user['password'] == password:
            self.current_username = username
            # Auditoría
            self.db.registrar_auditoria(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                username,
                user['role'],
                "Inició sesión",
                "Sistema",
                "Éxito"
            )
            self.show_loading_animation(user['role'])
        else:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos")
            # Enfocar y seleccionar el campo de contraseña
            self.password_entry.focus_set()
            self.password_entry.select_range(0, tk.END)
                    
    def show_loading_animation(self, role):
        """Muestra una animación de carga con corazón y onda ECG antes de abrir la aplicación principal"""
        # Crear ventana de carga
        loading_window = Toplevel(self.root)
        loading_window.title("Cargando SaluPago...")
        loading_window.geometry("450x300")
        loading_window.resizable(False, False)

        # Centrar la ventana de carga
        self.center_window(loading_window, 450, 300)

        # Ocultar la ventana de login
        self.root.withdraw()

        # Definir el callback que se ejecutará al terminar la animación
        def finalizar_carga():
            loading_window.destroy()
            self.abrir_aplicacion(role)

        # Llamar a la animación con corazón
        animacion_corazon_ecg(loading_window, duracion=5.0, callback=finalizar_carga)
        
    def open_main_application(self, role, username=None):
        """Abre la aplicación principal con el rol especificado"""
        root = tk.Tk()
        root.title(f"SaluPago - {role.capitalize()}")
        # Maximizar ventana (ocupa toda la pantalla menos barra de tareas)
        root.state('zoomed')
        app = SaluPagoApp(root, role, username or role.capitalize())
        root.mainloop()

    # En LoginWindow, después de open_main_application o en cualquier lugar dentro de la clase

    def abrir_portal_cliente(self):
        """Abre el portal del cliente en una nueva ventana (desde el login)."""
        self.root.withdraw()
        cliente_root = tk.Toplevel(self.root)
        cliente_root.title("Portal del Cliente - SaluPago")
        cliente_root.protocol("WM_DELETE_WINDOW", lambda: self.cerrar_portal_cliente(cliente_root))
        ClienteWindow(cliente_root, self.db, menu_principal=self.menu_principal)

    def cerrar_portal_cliente(self, cliente_root):
        cliente_root.destroy()
        if self.menu_principal:
            self.menu_principal.mostrar_menu()
        else:
            self.root.deiconify()

    def actualizar_barra_estado(self):
        """Actualiza la información de la barra de estado"""
        # Limpiar la barra de estado actual
        for widget in self.status_bar.winfo_children():
            widget.destroy()
        
        # Crear nueva barra de estado
        left_frame = ttk.Frame(self.status_bar)
        left_frame.pack(side=tk.LEFT)
        
        nombre_usuario = self.obtener_nombre_usuario()
        role_name = "Administrativo" if self.user_role == "Administrativo" else "Auxiliar"
        
        ttk.Label(left_frame, text=f"Usuario: {nombre_usuario}", 
                relief=tk.SUNKEN, padding=(5,2)).pack(side=tk.LEFT)
        
        ttk.Label(left_frame, text=f"Rol: {role_name}", 
                relief=tk.SUNKEN, padding=(5,2)).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(left_frame, text=f"Fecha: {datetime.now().strftime('%Y-%m-%d')}", 
                relief=tk.SUNKEN, padding=(5,2)).pack(side=tk.LEFT, padx=5)

class ClienteWindow:
    def __init__(self, root, db, cedula=None, menu_principal=None):
        self.root = root
        self.db = db
        self.menu_principal = menu_principal
        self.cedula = cedula
        self.afiliado = None
        self.monitoreo = None
        self.notificaciones = []
        self.incapacidades = []
        self.historial_pagos = []
        self.facturas = []
        self.modo_edicion = False
        
        # --- NUEVO: Tamaño fijo y sin redimensionar ---
        self.root.title("Portal del Cliente - SaluPago")
        self.root.geometry("400x450")
        self.root.resizable(False, False)
        self.root.minsize(400, 450)
        
        self.center_window(400, 450)
        self.setup_styles()
        
        if not self.cedula:
            self.show_login()
        else:
            self.autenticar_cliente(self.cedula)
    
    def setup_styles(self):
        """Configura los estilos visuales (igual que LoginWindow)"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Fondo general
        self.style.configure('.', background='#f0f0f0', font=('Arial', 10))
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0')
        self.style.configure('TButton', padding=5)
        
        # Estilo para el frame de login (fondo gris, sin borde)
        self.style.configure('Login.TFrame', background='#f0f0f0', borderwidth=0, relief='flat')
        
        # Títulos y etiquetas
        self.style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        self.style.configure('Action.TButton', font=('Segoe UI', 10), padding=8)
        
        # Estilos para el panel de cliente (también con fondo gris)
        self.style.configure('Subtitle.TLabel', font=('Segoe UI', 13, 'bold'), foreground='#283593')
        self.style.configure('Card.TFrame', background='#f0f0f0', relief='flat', borderwidth=0)
        self.style.configure('Info.TLabel', font=('Segoe UI', 11), foreground='#333')
        self.style.configure('Value.TLabel', font=('Segoe UI', 11, 'bold'), foreground='#1a237e')
        self.style.configure('Status.TLabel', font=('Segoe UI', 11, 'bold'))
        self.style.configure('Header.TLabel', font=('Segoe UI', 10, 'bold'), foreground='#37474f')
        self.style.configure('Small.TLabel', font=('Segoe UI', 10), foreground='#666')
    
    def center_window(self, width, height):
        """Centra la ventana en la pantalla"""
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def show_login(self):
        """Muestra la pantalla de login del cliente con logo a la izquierda y formulario a la derecha"""
        for widget in self.root.winfo_children():
            widget.destroy()

        self.root.title("Portal del Cliente - Iniciar Sesión")
        # Centrar la ventana con el tamaño deseado
        self.center_window(850, 450)

        main_frame = ttk.Frame(self.root, style='Login.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)

        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=2)

        # ---- Columna izquierda: Logo ----
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)

        try:
            logo_path = os.path.join(IMG_PATH, "LogoSP2.png")
            if os.path.exists(logo_path):
                logo = Image.open(logo_path)
                logo = logo.resize((470, 400), Image.LANCZOS)
                logo_img = ImageTk.PhotoImage(logo)
                logo_label = ttk.Label(left_frame, image=logo_img)
                logo_label.image = logo_img
                logo_label.grid(row=0, column=0, sticky="nsew")
            else:
                ttk.Label(left_frame, text="SaluPago", style='Title.TLabel').grid(row=0, column=0)
        except Exception:
            ttk.Label(left_frame, text="SaluPago", style='Title.TLabel').grid(row=0, column=0)

        # ---- Columna derecha: Formulario (centrado) ----
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)

        # Frame interno para centrar todo verticalmente
        center_frame = ttk.Frame(right_frame)
        center_frame.pack(expand=True, anchor='center')

        ttk.Label(center_frame, text="Portal del Cliente", font=('Segoe UI', 14, 'bold')).pack(pady=(0, 20))

        form_frame = ttk.Frame(center_frame)
        form_frame.pack(pady=10)

        ttk.Label(form_frame, text="Cédula:", font=('Segoe UI', 12)).pack(side=tk.LEFT, padx=10)
        self.cedula_var = tk.StringVar()
        # --- Guardamos referencia al campo de cédula ---
        self.cedula_entry = ttk.Entry(form_frame, textvariable=self.cedula_var, width=22, font=('Segoe UI', 12))
        self.cedula_entry.pack(side=tk.LEFT, padx=10)
        self.cedula_entry.focus_set()
        self.cedula_entry.bind('<Return>', lambda e: self.autenticar_cliente(self.cedula_var.get()))

        btn_frame = ttk.Frame(center_frame)
        btn_frame.pack(pady=25)

        ttk.Button(btn_frame, text="🔐 Acceder",
                command=lambda: self.autenticar_cliente(self.cedula_var.get()),
                style='Action.TButton').pack(side=tk.LEFT, padx=12)

        ttk.Button(btn_frame, text="📷 Escanear QR",
                command=self.abrir_escaner_qr,
                style='Action.TButton').pack(side=tk.LEFT, padx=12)

        ttk.Button(btn_frame, text="↩️ Volver",
                command=self.volver_login_principal,
                style='Action.TButton').pack(side=tk.LEFT, padx=12)

        ttk.Label(center_frame, text="Desarrollado por R.A.V",
                font=('Segoe UI', 9), foreground='#999').pack(pady=(20, 0))

        ttk.Label(center_frame, text="Versión 4.0.8",
            font=('Segoe UI', 8, 'italic'), foreground='#999').pack()
                        
    def autenticar_cliente(self, cedula):
        if not cedula:
            messagebox.showerror("Error", "Por favor ingrese su número de cédula")
            # Enfocar y seleccionar el campo de cédula
            self.cedula_entry.focus_set()
            self.cedula_entry.select_range(0, tk.END)
            return

        cedula = cedula.strip()

        for af in self.db.get_afiliados_activos():
            if af['cc'] == cedula:
                self.afiliado = af
                self.mostrar_panel_cliente()
                return

        for ret in self.db.get_afiliados_retirados():
            if ret['cc'] == cedula:
                self.afiliado = ret
                self.mostrar_panel_cliente()
                return

        messagebox.showerror("Error", "No se encontró ningún afiliado con esta cédula.\n\n"
                            "Si es un nuevo afiliado, contacte a la administración para su registro.")
        # Enfocar y seleccionar el campo de cédula
        self.cedula_entry.focus_set()
        self.cedula_entry.select_range(0, tk.END)
        
    def volver_login_principal(self):
        self.root.destroy()
        if self.menu_principal:
            self.menu_principal.mostrar_menu()
        else:
            # Fallback: abrir el login normal (si no hay menú)
            root = tk.Tk()
            LoginWindow(root, mostrar_boton_cliente=True)
            root.mainloop()
    
    def mostrar_toast(self, mensaje, duracion=3000, tipo="exito"):
        colores = {
            "exito": ("#2e7d32", "white"),      # verde oscuro
            "info": ("#0d47a1", "white"),       # azul oscuro
            "advertencia": ("#e65100", "white") # naranja oscuro
        }
        bg, fg = colores.get(tipo, ("#2c3e50", "white"))
        toast = Toast(self.root, mensaje, duration=duracion, bg=bg, fg=fg)
        toast.show()

        # ===== SONIDO según el tipo de toast =====
        if tipo == "exito":
            self.reproducir_sonido("pop", volumen=0.4)
        elif tipo == "advertencia":
            self.reproducir_sonido("alerta", volumen=0.5)
        elif tipo == "info":
            self.reproducir_sonido("pop", volumen=0.3)

    def cargar_datos_cliente(self):
        """Carga todos los datos del cliente desde la base de datos"""
        cc = self.afiliado['cc']
        
        # Monitoreo
        self.monitoreo = None
        for mon in self.db.get_monitoreo():
            if mon['cc'] == cc:
                self.monitoreo = mon
                break
        
        # Notificaciones
        self.notificaciones = []
        for notif in self.db.get_notificaciones():
            if notif['cc'] == cc:
                self.notificaciones.append(notif)
        self.notificaciones.sort(key=lambda x: x.get('fecha_vencimiento', ''), reverse=True)
        
        # Historial de pagos
        self.historial_pagos = []
        for ing in self.db.get_ingresos():
            if ing['cc'] == cc:
                self.historial_pagos.append(ing)
        self.historial_pagos.sort(key=lambda x: x.get('fecha', ''), reverse=True)
        
        # CORRECCIÓN: Cargar incapacidades del cliente
        self.incapacidades = []
        for inc in self.db.get_incapacidades():
            if inc['nombre'] == self.afiliado['nombre']:
                self.incapacidades.append(inc)
        
        # Facturas
        self.facturas = []
        facturas_path = os.path.join(BASE_PATH, "facturas")
        if os.path.exists(facturas_path):
            for f in os.listdir(facturas_path):
                if cc in f and f.endswith('.pdf'):
                    self.facturas.append(f)

        self.beneficiarios_list = self.db.get_beneficiarios(cc)
    
    def abrir_escaner_qr(self):
        """Abre la ventana de escaneo de QR usando la cámara del teléfono (IP Webcam)."""
        try:
            # Obtener la URL de la cámara desde la configuración
            camera_url = self.db.config.get('camera_ip_url', 'http://192.168.0.3:8080/video')
            # Verificar disponibilidad de la cámara IP
            cap = cv2.VideoCapture(camera_url)
            if not cap.isOpened():
                messagebox.showerror("Error", 
                    f"No se pudo acceder a la cámara IP en:\n{camera_url}\n\n"
                    "Verifique que:\n"
                    "1. El teléfono esté transmitiendo con IP Webcam.\n"
                    "2. Ambos dispositivos estén en la misma red WiFi.\n"
                    "3. La URL sea correcta (incluye /video al final).")
                return
            cap.release()
        except Exception as e:
            messagebox.showerror("Error", f"Error al acceder a la cámara:\n{str(e)}")
            return

        # Crear ventana de escaneo
        self.scan_window = Toplevel(self.root)
        self.scan_window.title("Escanear QR - SaluPago")
        self.scan_window.geometry("500x550")
        self.scan_window.resizable(False, False)
        self.scan_window.protocol("WM_DELETE_WINDOW", self.cerrar_escaner)

        # Canvas para mostrar el video
        self.canvas_video = tk.Canvas(self.scan_window, width=480, height=360, bg='black')
        self.canvas_video.pack(pady=10)

        # Etiqueta de estado
        self.estado_label = ttk.Label(self.scan_window, text="Buscando código QR...", font=('Segoe UI', 11))
        self.estado_label.pack(pady=5)

        # Botón para cerrar manualmente
        ttk.Button(self.scan_window, text="Cancelar", command=self.cerrar_escaner).pack(pady=10)

        # Iniciar captura con la URL de la cámara del teléfono
        self.cap = cv2.VideoCapture(self.db.config.get('camera_ip_url', 'http://192.168.0.3:8080/video'))
        self.scanning = True
        self.actualizar_frame_escaner()
        
    def actualizar_frame_escaner(self):
        """Actualiza el frame de la cámara y busca códigos QR."""
        if not self.scanning:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.estado_label.config(text="Error al leer la cámara", foreground='red')
            self.scan_window.after(500, self.actualizar_frame_escaner)
            return

        # Convertir a RGB para mostrar y para pyzbar
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)

        # Buscar códigos QR con pyzbar
        codigos = decode(pil_img)

        if codigos:
            # Tomar el primero detectado
            qr_data = codigos[0].data.decode('utf-8')
            # La cédula debe ser el contenido del QR
            cedula = qr_data.strip()
            # Dibujar rectángulo alrededor del QR en el frame (opcional)
            puntos = codigos[0].polygon
            if len(puntos) == 4:
                pts = [(p.x, p.y) for p in puntos]
                cv2.polylines(frame, [np.array(pts, dtype=np.int32)], True, (0, 255, 0), 2)
            else:
                # Fallback si no es cuadrado
                rect = codigos[0].rect
                cv2.rectangle(frame, (rect.left, rect.top), (rect.left + rect.width, rect.top + rect.height), (0, 255, 0), 2)

            # Mostrar mensaje
            self.estado_label.config(text=f"✅ QR detectado: {cedula}", foreground='green')
            self.scan_window.update()

            # Detener escaneo y autenticar
            self.scanning = False
            self.cap.release()
            self.scan_window.destroy()

            # Llamar a autenticación con la cédula leída
            self.autenticar_cliente(cedula)
            return

        # Si no hay QR, mostrar frame actualizado
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        imgtk = ImageTk.PhotoImage(image=img)
        self.canvas_video.create_image(0, 0, anchor=tk.NW, image=imgtk)
        self.canvas_video.imgtk = imgtk  # mantener referencia

        # Programar siguiente actualización
        self.scan_window.after(30, self.actualizar_frame_escaner)

    def cerrar_escaner(self):
        """Cierra la cámara y la ventana de escaneo."""
        self.scanning = False
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        if hasattr(self, 'scan_window') and self.scan_window.winfo_exists():
            self.scan_window.destroy()

    def mostrar_panel_cliente(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        self.root.title(f"Portal del Cliente - {self.afiliado['nombre']}")
        self.root.state('zoomed')
        self.root.resizable(True, True)
        self.root.minsize(900, 650)

        self.cargar_datos_cliente()
        # Obtener solicitud activa
        self.solicitud_activa = self.db.obtener_solicitud_activa(self.afiliado['cc'])

        # HEADER (sin botón de cerrar sesión)
        header_frame = ttk.Frame(self.root, style='Card.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 10), padx=15)
        header_inner = ttk.Frame(header_frame, padding=15)
        header_inner.pack(fill=tk.X)

        ttk.Label(header_inner, text=f"¡Bienvenido, {self.afiliado['nombre']}!", style='Title.TLabel').pack(side=tk.LEFT)

        estado = "🟢 Activo" if self.afiliado.get('fecha_retiro') is None else "🔴 Retirado"
        estado_color = "#2e7d32" if self.afiliado.get('fecha_retiro') is None else "#c62828"
        ttk.Label(header_inner, text=estado, style='Status.TLabel', foreground=estado_color).pack(side=tk.RIGHT, padx=15)
        ttk.Label(header_inner, text=datetime.now().strftime("%d/%m/%Y"), font=('Segoe UI', 11), foreground='#666').pack(side=tk.RIGHT, padx=15)

        # CONTENIDO
        content_frame = ttk.Frame(self.root)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=8)

        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        self.crear_tarjeta_editable(left_frame)
        self.crear_tarjeta_servicios(left_frame)
        self.crear_tarjeta_beneficiarios(left_frame)

        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))

        self.crear_tarjeta_pagos(right_frame)
        self.crear_tarjeta_historial(right_frame)
        self.crear_tarjeta_notificaciones(right_frame)

        # BOTONES DE ACCIÓN (con Cerrar Sesión al final)
        action_frame = ttk.Frame(self.root)
        action_frame.pack(fill=tk.X, pady=(10, 15), padx=15)
        btn_container = ttk.Frame(action_frame)
        btn_container.pack()

        ttk.Button(btn_container, text="📄 Ver Facturas", command=self.ver_facturas_cliente, style='Action.TButton').pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_container, text="📋 Incapacidades", command=self.gestionar_incapacidades, style='Action.TButton').pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_container, text="📄 Certificados", command=self.mostrar_opciones_certificado, style='Action.TButton').pack(side=tk.LEFT, padx=6)

        # Botón Pagar (se habilita solo si hay solicitud activa)
        pagar_btn = ttk.Button(btn_container, text="💳 Pagar", command=self.mostrar_ventana_pago, style='Action.TButton')
        if not self.solicitud_activa:
            pagar_btn.config(state="disabled")
        pagar_btn.pack(side=tk.LEFT, padx=6)
        
        ttk.Button(btn_container, text="📱 Mi QR", 
        command=lambda: self.mostrar_qr_cliente(), style='Action.TButton').pack(side=tk.LEFT, padx=6)

        # Botón Actualizar
        ttk.Button(btn_container, text="🔄 Actualizar", command=self.recargar_datos, style='Action.TButton').pack(side=tk.LEFT, padx=6)

        # ---- NUEVO: Botón Cerrar Sesión al final ----
        ttk.Button(btn_container, text="🚪 Cerrar Sesión", command=self.cerrar_sesion_cliente, style='Action.TButton').pack(side=tk.LEFT, padx=6)

    def mostrar_qr_cliente(self):
        """Muestra el código QR del cliente autenticado con opción de descarga."""
        if not self.afiliado:
            return
        try:
            import qrcode
            from PIL import Image, ImageTk
        except ImportError:
            messagebox.showerror("Error", "La librería qrcode no está instalada.")
            return

        cedula = self.afiliado['cc']
        nombre = self.afiliado['nombre']

        # --- QR para vista previa en pantalla ---
        qr = qrcode.QRCode(version=1, box_size=8, border=4)
        qr.add_data(cedula)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        img_qr = img_qr.resize((300, 300), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img_qr)

        ventana = Toplevel(self.root)
        ventana.title("Mi código QR")
        ventana.geometry("400x600")   # más alta para que quepan los 2 botones
        ventana.resizable(False, False)

        # ===== CENTRAR VENTANA =====
        ventana.update_idletasks()
        ancho, alto = 400, 600
        screen_width = ventana.winfo_screenwidth()
        screen_height = ventana.winfo_screenheight()
        x = (screen_width // 2) - (ancho // 2)
        y = (screen_height // 2) - (alto // 2)
        ventana.geometry(f"{ancho}x{alto}+{x}+{y}")
        # ===========================

        ttk.Label(ventana, text="Código QR de acceso rápido",
                font=('Segoe UI', 14, 'bold')).pack(pady=10)
        ttk.Label(ventana, text=f"Afiliado: {nombre}",
                font=('Segoe UI', 12)).pack(pady=5)

        label_img = ttk.Label(ventana, image=photo)
        label_img.image = photo
        label_img.pack(pady=10)

        ttk.Label(ventana, text=f"Cédula: {cedula}",
                font=('Segoe UI', 10, 'bold')).pack(pady=5)
        ttk.Label(ventana, text="Escanea este código para acceder sin teclear",
                font=('Segoe UI', 9), foreground='gray').pack()

        # ============ BOTÓN DE DESCARGA ============
        def descargar_qr():
            nombre_archivo = f"Qr{cedula}.png"
            # Abrir diálogo para elegir ubicación (por defecto en Documentos)
            try:
                documentos = os.path.join(os.path.expanduser("~"), "Documents")
                if not os.path.exists(documentos):
                    documentos = os.path.expanduser("~")
            except Exception:
                documentos = os.getcwd()

            ruta = filedialog.asksaveasfilename(
                title="Guardar código QR",
                defaultextension=".png",
                initialfile=nombre_archivo,
                initialdir=documentos,
                filetypes=[("Imagen PNG", "*.png"), ("Todos los archivos", "*.*")]
            )
            if not ruta:
                return  # Usuario canceló

            try:
                # Regenerar a mayor resolución para la descarga
                qr_descarga = qrcode.QRCode(version=1, box_size=12, border=4)
                qr_descarga.add_data(cedula)
                qr_descarga.make(fit=True)
                img_descarga = qr_descarga.make_image(
                    fill_color="black", back_color="white"
                ).convert('RGB')
                img_descarga.save(ruta, "PNG")

                messagebox.showinfo("Descarga exitosa",
                                    f"Código QR guardado en:\n{ruta}")

                # Ofrecer abrir la ubicación del archivo
                if messagebox.askyesno("Abrir ubicación",
                                    "¿Desea abrir la carpeta donde se guardó el QR?"):
                    carpeta = os.path.dirname(ruta)
                    try:
                        if sys.platform == "win32":
                            os.startfile(carpeta)
                        elif sys.platform == "darwin":
                            subprocess.Popen(["open", carpeta])
                        else:
                            subprocess.Popen(["xdg-open", carpeta])
                    except Exception:
                        pass
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar el QR:\n{str(e)}")
        # ============================================

        btn_frame = ttk.Frame(ventana)
        btn_frame.pack(pady=15)

        ttk.Button(btn_frame, text="💾 Descargar QR",
                command=descargar_qr).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cerrar",
                command=ventana.destroy).pack(side=tk.LEFT, padx=5)
                            
    def mostrar_ventana_pago(self):
        """Muestra la ventana de pago con barra de progreso y botón Pago Realizado."""
        if not self.solicitud_activa:
            messagebox.showinfo("Sin solicitud", "No hay una solicitud de pago activa. Contacte a su empleador.")
            return

        solicitud = self.solicitud_activa
        ventana = tk.Toplevel(self.root)
        ventana.title("Pago - SaluPago")
        ventana.geometry("750x550")
        ventana.resizable(False, False)
        ventana.transient(self.root)
        ventana.grab_set()

        # Centrar
        ventana.update_idletasks()
        x = (ventana.winfo_screenwidth() // 2) - (750 // 2)
        y = (ventana.winfo_screenheight() // 2) - (550 // 2)
        ventana.geometry(f"+{x}+{y}")

        paned = ttk.PanedWindow(ventana, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Columna izquierda: imagen
        left_frame = ttk.Frame(paned, padding=10)
        paned.add(left_frame, weight=1)
        imagen_ruta = self.db.config.get('pago_imagen', 'Nequi.png')
        if not os.path.isabs(imagen_ruta):
            imagen_ruta = os.path.join(IMG_PATH, imagen_ruta)
        try:
            if os.path.exists(imagen_ruta):
                img = Image.open(imagen_ruta)
                base_width = 350
                w_percent = base_width / float(img.size[0])
                h_size = int((float(img.size[1]) * float(w_percent)))
                img = img.resize((base_width, h_size), Image.LANCZOS)
                img_tk = ImageTk.PhotoImage(img)
                label_img = ttk.Label(left_frame, image=img_tk)
                label_img.image = img_tk
                label_img.pack(expand=True, fill=tk.BOTH)
            else:
                ttk.Label(left_frame, text="Imagen de pago no encontrada", font=('Arial', 12), foreground='red').pack(expand=True)
        except Exception as e:
            ttk.Label(left_frame, text=f"Error al cargar imagen:\n{str(e)}", font=('Arial', 10), foreground='red').pack(expand=True)

        # Columna derecha
        right_frame = ttk.Frame(paned, padding=10)
        paned.add(right_frame, weight=1)

        empresa = self.db.config.get('empresa', {})
        nombre = empresa.get('nombre', 'SaluPago')
        nit = empresa.get('nit', 'NIT no definido')
        direccion = empresa.get('direccion', 'Dirección no definida')
        telefono = empresa.get('telefono', 'Teléfono no definido')
        correo = empresa.get('correo', 'correo@empresa.com')

        ttk.Label(right_frame, text="Datos de la Empresa", style='Title.TLabel', font=('Arial', 14, 'bold')).pack(pady=(0, 10))

        for label, valor in [("Nombre:", nombre), ("NIT:", nit), ("Dirección:", direccion),
                            ("Teléfono:", telefono), ("Correo:", correo)]:
            fila = ttk.Frame(right_frame)
            fila.pack(fill=tk.X, pady=2)
            ttk.Label(fila, text=label, font=('Arial', 10, 'bold'), width=12, anchor=tk.W).pack(side=tk.LEFT, padx=5)
            ttk.Label(fila, text=valor, font=('Arial', 10)).pack(side=tk.LEFT, padx=5)

        ttk.Separator(right_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        ttk.Label(right_frame, text="Estado de la solicitud:", font=('Arial', 11, 'bold')).pack(anchor=tk.W, pady=(0,5))

        # Barra de progreso
        paso_frame = ttk.Frame(right_frame)
        paso_frame.pack(fill=tk.X, pady=5)
        pasos = ["Solicitud enviada", "Cliente confirma pago", "Factura generada"]
        estado_actual = solicitud['estado']
        progreso = 0
        if estado_actual == 'enviada':
            progreso = 0
        elif estado_actual == 'cliente_confirmado':
            progreso = 1
        elif estado_actual == 'facturado':
            progreso = 2
        else:
            progreso = 1  # pendiente/rechazado

        progress = ttk.Progressbar(paso_frame, orient='horizontal', length=300, mode='determinate', maximum=2, value=progreso)
        progress.pack(fill=tk.X, pady=5)
        labels_frame = ttk.Frame(paso_frame)
        labels_frame.pack(fill=tk.X)
        for i, paso in enumerate(pasos):
            lbl = ttk.Label(labels_frame, text=paso, font=('Arial', 8))
            lbl.config(foreground='green' if i <= progreso else 'gray')
            lbl.pack(side=tk.LEFT, expand=True, padx=2)

        monto = solicitud.get('monto', 0)
        ttk.Label(right_frame, text=f"Monto a pagar: ${monto:,.2f}", font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=5)
        if solicitud.get('mensaje_whatsapp'):
            msg = solicitud['mensaje_whatsapp'][:100] + "..." if len(solicitud['mensaje_whatsapp']) > 100 else solicitud['mensaje_whatsapp']
            ttk.Label(right_frame, text=f"Mensaje: {msg}", font=('Arial', 9), wraplength=300, justify=tk.LEFT).pack(anchor=tk.W, pady=5)

        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(pady=10)

        def pago_realizado():
            self.db.actualizar_solicitud(solicitud['id'], 'cliente_confirmado')
            self.mostrar_toast("Pago confirmado. El empleador podrá facturar ahora.", duracion=4000)
            ventana.destroy()
            self.recargar_datos()

        if estado_actual == 'enviada':
            ttk.Button(btn_frame, text="✅ Pago Realizado", command=pago_realizado, style='Accent.TButton').pack()
        else:
            ttk.Label(btn_frame, text="Esta solicitud ya ha sido procesada.", font=('Arial', 10), foreground='gray').pack()

        ttk.Button(btn_frame, text="Cerrar", command=ventana.destroy).pack(pady=5)
        
    def generar_certificado(self, tipo="afiliacion"):
        """
        Genera y guarda automáticamente el certificado en Documentos/{cc}/Certificado/
        tipo: 'afiliacion' o 'retiro'
        """
        if not self.afiliado:
            messagebox.showerror("Error", "No hay afiliado autenticado.")
            return

        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        import os, subprocess, sys

        af = self.afiliado
        cc = af['cc']
        carpeta_docs = os.path.join(BASE_PATH, "Documentos", cc, "Certificado")
        os.makedirs(carpeta_docs, exist_ok=True)

        if tipo == "afiliacion":
            nombre_archivo = f"Certificado_Afiliacion_{cc}.pdf"
        else:
            nombre_archivo = f"Certificado_Retiro_{cc}.pdf"
        file_path = os.path.join(carpeta_docs, nombre_archivo)

        doc = SimpleDocTemplate(file_path, pagesize=letter,
                                leftMargin=1.5*cm, rightMargin=1.5*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Title'],
            fontSize=22,
            textColor=colors.HexColor('#0d47a1'),
            alignment=TA_CENTER,
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )
        subtitle_style = ParagraphStyle(
            'SubtitleStyle',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#333333'),
            alignment=TA_CENTER,
            spaceAfter=12,
            fontName='Helvetica'
        )
        body_style = ParagraphStyle(
            'BodyStyle',
            parent=styles['Normal'],
            fontSize=12,
            leading=18,
            alignment=TA_LEFT,
            fontName='Helvetica'
        )
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#555555'),
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        signature_style = ParagraphStyle(
            'SignatureStyle',
            parent=styles['Normal'],
            fontSize=12,
            alignment=TA_CENTER,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )

        # Logo
        logo_path = os.path.join(IMG_PATH, "LogoSaluPago.png")
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=3.5*cm, height=3.5*cm)
                logo.hAlign = 'CENTER'
                elements.append(logo)
                elements.append(Spacer(1, 0.3*cm))
            except:
                pass

        if tipo == "afiliacion":
            titulo = "CERTIFICADO DE AFILIACIÓN"
            subtitulo = "La empresa CERTIFICA QUE:"
        else:
            titulo = "CERTIFICADO DE RETIRO"
            subtitulo = "La empresa CERTIFICA QUE el siguiente afiliado ha sido retirado:"

        elements.append(Paragraph(titulo, title_style))
        elements.append(Spacer(1, 0.3*cm))

        empresa = self.db.config.get('empresa.nombre', 'SaluPago') if hasattr(self.db, 'config') else 'SaluPago'
        elements.append(Paragraph(empresa.upper(), subtitle_style))
        elements.append(Spacer(1, 0.6*cm))

        nombre_completo = af['nombre']
        cedula = af['cc']
        eps = af.get('eps', 'No registrada')
        estado = "ACTIVO" if af.get('fecha_retiro') is None else "RETIRADO"

        elements.append(Paragraph(f"<b>{subtitulo}</b>", body_style))
        elements.append(Spacer(1, 0.4*cm))

        if tipo == "afiliacion":
            elementos_cuerpo = [
                f"El(La) Señor(a) <b>{nombre_completo}</b> identificado(a) con CC <b>{cedula}</b> se encuentra afiliado a la EPS <b>{eps}</b> en condición de <b>1° COTIZANTE</b>.",
                "Fecha de Activación de Servicios: " + af.get('fecha_ingreso', 'No registrada'),
                "Estado de la Afiliación: " + estado,
                "IPS: ASIGNADA POR LA EPS",
                "Categoría: A"
            ]
        else:
            fecha_retiro = af.get('fecha_retiro', 'No registrada')
            motivo_retiro = af.get('motivo_retiro', 'No especificado')
            elementos_cuerpo = [
                f"El(La) Señor(a) <b>{nombre_completo}</b> identificado(a) con CC <b>{cedula}</b> se encontraba afiliado a la EPS <b>{eps}</b> en condición de <b>1° COTIZANTE</b>.",
                f"Fecha de Retiro: {fecha_retiro}",
                f"Motivo de Retiro: {motivo_retiro}",
                "Estado de la Afiliación: RETIRADO"
            ]

        for parrafo in elementos_cuerpo:
            elements.append(Paragraph(parrafo, body_style))
            elements.append(Spacer(1, 0.2*cm))
        elements.append(Spacer(1, 0.4*cm))

        # Beneficiarios
        beneficiarios = self.db.get_beneficiarios(cc)
        if beneficiarios:
            elements.append(Paragraph("<b>Beneficiarios registrados:</b>", body_style))
            for b in beneficiarios:
                texto_benef = f"• {b['nombre']} ({b['tipo']})"
                if b.get('documento_identidad'):
                    texto_benef += f" - CC: {b['documento_identidad']}"
                elements.append(Paragraph(texto_benef, body_style))
            elements.append(Spacer(1, 0.5*cm))

        # Observaciones
        observaciones = "ESTA CERTIFICACIÓN NO APLICA PARA SERVICIOS MÉDICOS. NO VÁLIDO PARA TRASLADO A OTRA EPS."
        elements.append(Paragraph(f"<b>Observaciones:</b><br/>{observaciones}", body_style))
        elements.append(Spacer(1, 0.5*cm))

        fecha_actual = datetime.now()
        elements.append(Paragraph(
            f"La presente certificación se expide a solicitud del(de la) interesado(a) en Bogotá para QUIEN INTERESE, a los {fecha_actual.day} días del mes de {fecha_actual.strftime('%B')} del año {fecha_actual.year}.",
            body_style
        ))
        #if tipo == "afiliacion":
        #    fecha_validez = fecha_actual + timedelta(days=30)
        #    elements.append(Spacer(1, 0.3*cm))
        #    elements.append(Paragraph(
        #        f"La certificación tiene validez de un mes con respecto a la fecha de generación (hasta {fecha_validez.strftime('%d/%m/%Y')}).",
        #        footer_style
        #    ))

        elements.append(Spacer(1, 0.5*cm))

        # Firma
        elements.append(Paragraph("Cordialmente,", body_style))
        elements.append(Spacer(1, 0.3*cm))
        elements.append(Paragraph("_________________________", signature_style))
        elements.append(Paragraph("<b>SaluPago Andrés Renteria (CEO)</b>", signature_style))
        elements.append(Paragraph(empresa.upper(), signature_style))
        elements.append(Spacer(1, 0.2*cm))

        elements.append(Paragraph(f"Certificado generado el {fecha_actual.strftime('%d/%m/%Y %H:%M')}", footer_style))
        #elements.append(Paragraph("Este documento es una constancia y no tiene validez como factura.", footer_style))

        doc.build(elements)
        self.mostrar_toast("Certificado generado correctamente", duracion=3000)
        messagebox.showinfo("Certificado generado", f"Certificado guardado en:\n{file_path}")

        # Abrir automáticamente
        try:
            if sys.platform == 'win32':
                os.startfile(file_path)
            elif sys.platform == 'darwin':
                subprocess.call(('open', file_path))
            else:
                subprocess.call(('xdg-open', file_path))
        except:
            pass
        
    def mostrar_opciones_certificado(self):
        """Ventana con dos botones: Certificado de Afiliación y Certificado de Retiro.
        Se deshabilita el que no corresponda según el estado del afiliado."""
        ventana = Toplevel(self.root)
        ventana.title("Certificados")
        ventana.geometry("400x200")
        ventana.resizable(False, False)
        ventana.transient(self.root)
        ventana.grab_set()

        # Centrar la ventana en la pantalla
        ventana.update_idletasks()
        ancho = 400
        alto = 200
        x = (ventana.winfo_screenwidth() // 2) - (ancho // 2)
        y = (ventana.winfo_screenheight() // 2) - (alto // 2)
        ventana.geometry(f"{ancho}x{alto}+{x}+{y}")

        ttk.Label(ventana, text="Seleccione el certificado que desea descargar:", 
                font=('Segoe UI', 12)).pack(pady=20)

        frame = ttk.Frame(ventana)
        frame.pack(pady=10)

        # Estado del afiliado
        es_activo = self.afiliado.get('fecha_retiro') is None

        btn_afiliacion = ttk.Button(frame, text="Certificado de Afiliación",
                                    command=lambda: [ventana.destroy(), self.generar_certificado("afiliacion")])
        btn_afiliacion.pack(side=tk.LEFT, padx=10)

        btn_retiro = ttk.Button(frame, text="Certificado de Retiro",
                                command=lambda: [ventana.destroy(), self.generar_certificado("retiro")])
        btn_retiro.pack(side=tk.LEFT, padx=10)

        if es_activo:
            btn_retiro.config(state="disabled")
        else:
            btn_afiliacion.config(state="disabled")

        ttk.Button(ventana, text="Cerrar", command=ventana.destroy).pack(pady=20)

    def generar_certificado_desde_registro(self, registro, tipo="afiliacion"):
        """
        Genera certificado (afiliación o retiro) para un afiliado dado.
        Guarda automáticamente en Documentos/{cc}/Certificado/
        tipo: 'afiliacion' o 'retiro'
        """
        if not registro:
            return

        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        import os, subprocess, sys

        cc = registro['cc']
        carpeta_docs = os.path.join(BASE_PATH, "Documentos", cc, "Certificado")
        os.makedirs(carpeta_docs, exist_ok=True)

        if tipo == "afiliacion":
            nombre_archivo = f"Certificado_Afiliacion_{cc}.pdf"
        else:
            nombre_archivo = f"Certificado_Retiro_{cc}.pdf"
        file_path = os.path.join(carpeta_docs, nombre_archivo)

        doc = SimpleDocTemplate(file_path, pagesize=letter,
                                leftMargin=1.5*cm, rightMargin=1.5*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        elements = []
        styles = getSampleStyleSheet()

        # Estilos (con tamaños ligeramente mayores para aprovechar el espacio)
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Title'],
            fontSize=22,
            textColor=colors.HexColor('#0d47a1'),
            alignment=TA_CENTER,
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )
        subtitle_style = ParagraphStyle(
            'SubtitleStyle',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#333333'),
            alignment=TA_CENTER,
            spaceAfter=12,
            fontName='Helvetica'
        )
        body_style = ParagraphStyle(
            'BodyStyle',
            parent=styles['Normal'],
            fontSize=12,
            leading=18,
            alignment=TA_LEFT,
            fontName='Helvetica'
        )
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#555555'),
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        signature_style = ParagraphStyle(
            'SignatureStyle',
            parent=styles['Normal'],
            fontSize=12,
            alignment=TA_CENTER,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )

        # Logo
        logo_path = os.path.join(IMG_PATH, "LogoSaluPago.png")
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=3.5*cm, height=3.5*cm)
                logo.hAlign = 'CENTER'
                elements.append(logo)
                elements.append(Spacer(1, 0.3*cm))
            except:
                pass

        # Título
        if tipo == "afiliacion":
            titulo = "CERTIFICADO DE AFILIACIÓN"
            subtitulo = "La empresa CERTIFICA QUE:"
        else:
            titulo = "CERTIFICADO DE RETIRO"
            subtitulo = "La empresa CERTIFICA QUE el siguiente afiliado ha sido retirado:"

        elements.append(Paragraph(titulo, title_style))
        elements.append(Spacer(1, 0.3*cm))

        empresa = self.config.get('empresa.nombre', 'SaluPago')
        elements.append(Paragraph(empresa.upper(), subtitle_style))
        elements.append(Spacer(1, 0.6*cm))  # Espacio extra

        af = registro
        nombre_completo = af['nombre']
        cedula = af['cc']
        eps = af.get('eps', 'No registrada')

        # Cuerpo - Subtítulo "CERTIFICA QUE"
        elements.append(Paragraph(f"<b>{subtitulo}</b>", body_style))
        elements.append(Spacer(1, 0.4*cm))

        if tipo == "afiliacion":
            elementos_cuerpo = [
                f"El(La) Señor(a) <b>{nombre_completo}</b> identificado(a) con CC <b>{cedula}</b> se encuentra afiliado a la EPS <b>{eps}</b> en condición de <b>1° COTIZANTE</b>.",
                "Fecha de Activación de Servicios: " + af.get('fecha_ingreso', 'No registrada'),
                "Estado de la Afiliación: ACTIVO",
                "IPS: ASIGNADA POR LA EPS",
                "Categoría: A"
            ]
        else:
            fecha_retiro = af.get('fecha_retiro', 'No registrada')
            motivo_retiro = af.get('motivo_retiro', 'No especificado')
            elementos_cuerpo = [
                f"El(La) Señor(a) <b>{nombre_completo}</b> identificado(a) con CC <b>{cedula}</b> se encontraba afiliado a la EPS <b>{eps}</b> en condición de <b>1° COTIZANTE</b>.",
                f"Fecha de Retiro: {fecha_retiro}",
                f"Motivo de Retiro: {motivo_retiro}",
                "Estado de la Afiliación: RETIRADO"
            ]

        for parrafo in elementos_cuerpo:
            elements.append(Paragraph(parrafo, body_style))
            elements.append(Spacer(1, 0.2*cm))
        elements.append(Spacer(1, 0.4*cm))  # Espacio extra después del cuerpo

        # ---- Beneficiarios (si existen) ----
        beneficiarios = self.db.get_beneficiarios(cc)
        if beneficiarios:
            elements.append(Paragraph("<b>Beneficiarios registrados:</b>", body_style))
            for b in beneficiarios:
                texto_benef = f"• {b['nombre']} ({b['tipo']})"
                if b.get('documento_identidad'):
                    texto_benef += f" - CC: {b['documento_identidad']}"
                elements.append(Paragraph(texto_benef, body_style))
            elements.append(Spacer(1, 0.5*cm))  # Espacio después de beneficiarios

        # Observaciones
        observaciones = "ESTA CERTIFICACIÓN NO APLICA PARA SERVICIOS MÉDICOS. NO VÁLIDO PARA TRASLADO A OTRA EPS."
        elements.append(Paragraph(f"<b>Observaciones:</b><br/>{observaciones}", body_style))
        elements.append(Spacer(1, 0.5*cm))

        # Fecha y validez
        fecha_actual = datetime.now()
        elements.append(Paragraph(
            f"La presente certificación se expide a solicitud del(de la) interesado(a) en Bogotá para QUIEN INTERESE, a los {fecha_actual.day} días del mes de {fecha_actual.strftime('%B')} del año {fecha_actual.year}.",
            body_style
        ))
        #if tipo == "afiliacion":
        #    fecha_validez = fecha_actual + timedelta(days=30)
        #    elements.append(Spacer(1, 0.3*cm))
        #    elements.append(Paragraph(
        #        f"La certificación tiene validez de un mes con respecto a la fecha de generación (hasta {fecha_validez.strftime('%d/%m/%Y')}).",
        #        footer_style
        #    ))

        elements.append(Spacer(1, 0.5*cm))

        # Firma profesional
        elements.append(Paragraph("Cordialmente,", body_style))
        elements.append(Spacer(1, 0.3*cm))
        elements.append(Paragraph("_________________________", signature_style))
        elements.append(Paragraph("<b>SaluPago Andrés Renteria (CEO)</b>", signature_style))
        elements.append(Paragraph(empresa.upper(), signature_style))
        elements.append(Spacer(1, 0.2*cm))

        elements.append(Paragraph(f"Certificado generado el {fecha_actual.strftime('%d/%m/%Y %H:%M')}", footer_style))
        #elements.append(Paragraph("Este documento es una constancia y no tiene validez como factura.", footer_style))

        doc.build(elements)
        messagebox.showinfo("Certificado generado", f"Certificado guardado en:\n{file_path}")

        # Abrir automáticamente
        try:
            if sys.platform == 'win32':
                os.startfile(file_path)
            elif sys.platform == 'darwin':
                subprocess.call(('open', file_path))
            else:
                subprocess.call(('xdg-open', file_path))
        except:
            pass
            
    def crear_tarjeta_beneficiarios(self, parent):
        frame = ttk.Frame(parent, style='Card.TFrame')
        frame.pack(fill=tk.BOTH, expand=True, pady=6)

        inner = ttk.Frame(frame, padding=12)
        inner.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(inner)
        header.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(header, text="👨‍👩‍👧‍👦 Mis Beneficiarios", style='Subtitle.TLabel').pack(side=tk.LEFT)

        # Usar self.beneficiarios_list
        if not self.beneficiarios_list:
            ttk.Label(inner, text="No tiene beneficiarios registrados", style='Info.TLabel',
                    font=('Segoe UI', 11)).pack(anchor=tk.W, pady=10)
            return

        tree_frame = ttk.Frame(inner)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.beneficiarios_tree = ttk.Treeview(tree_frame, columns=("CC", "Nombre", "Tipo", "Fecha Nac."), show="headings", height=4)
        self.beneficiarios_tree.heading("CC", text="Cédula")
        self.beneficiarios_tree.heading("Nombre", text="Nombre")
        self.beneficiarios_tree.heading("Tipo", text="Tipo")
        self.beneficiarios_tree.heading("Fecha Nac.", text="Fecha Nac.")
        self.beneficiarios_tree.column("CC", width=100, anchor=tk.W)
        self.beneficiarios_tree.column("Nombre", width=150, anchor=tk.W)
        self.beneficiarios_tree.column("Tipo", width=80, anchor=tk.W)
        self.beneficiarios_tree.column("Fecha Nac.", width=100, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.beneficiarios_tree.yview)
        self.beneficiarios_tree.configure(yscrollcommand=scrollbar.set)
        self.beneficiarios_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for b in self.beneficiarios_list:
            self.beneficiarios_tree.insert("", tk.END, values=(
                b.get('documento_identidad', 'N/A'),
                b['nombre'],
                b['tipo'],
                b.get('fecha_nacimiento', '')
            ), iid=str(b['id']))

        self.beneficiarios_tree.bind("<Double-1>", self.mostrar_detalles_beneficiario)

    def mostrar_detalles_beneficiario(self, event=None):
        """Muestra ventana informativa (solo lectura) con los datos del beneficiario y sus documentos."""
        if not self.beneficiarios_tree:
            return
        selected = self.beneficiarios_tree.selection()
        if not selected:
            messagebox.showinfo("Selección", "Seleccione un beneficiario para ver detalles.")
            return

        id_benef = int(selected[0])
        benef = next((b for b in self.beneficiarios_list if b['id'] == id_benef), None)
        if not benef:
            messagebox.showerror("Error", "Beneficiario no encontrado.")
            return

        ventana = Toplevel(self.root)
        ventana.title(f"Detalles del Beneficiario - {benef['nombre']}")
        ventana.geometry("950x380")
        ventana.resizable(False, False)
        ventana.transient(self.root)
        ventana.grab_set()

        # Centrar ventana
        ventana.update_idletasks()
        x = (ventana.winfo_screenwidth() // 2) - (950 // 2)
        y = (ventana.winfo_screenheight() // 2) - (380 // 2)
        ventana.geometry(f"+{x}+{y}")

        paned = ttk.PanedWindow(ventana, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ---- Panel izquierdo: Datos (solo lectura) ----
        left_frame = ttk.Frame(paned, padding=10)
        paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Datos del Beneficiario", style='Title.TLabel').pack(pady=(0, 10))

        # Datos del beneficiario en etiquetas (no editables)
        campos = [
            ("Tipo:", benef['tipo']),
            ("Nombre:", benef['nombre']),
            ("Documento:", benef.get('documento_identidad', 'N/A')),
            ("Observaciones:", benef.get('registro_civil', '')),
            ("Fecha Nacimiento:", benef.get('fecha_nacimiento', '')),
            ("Teléfono:", benef.get('telefono', '')),
            ("Correo:", benef.get('correo', '')),
            ("Dirección:", benef.get('direccion', ''))
        ]
        for campo, valor in campos:
            row = ttk.Frame(left_frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=campo, font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=5)
            ttk.Label(row, text=valor if valor else '—', font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=5)

        # ---- Panel derecho: Documentos ----
        right_frame = ttk.Frame(paned, padding=10)
        paned.add(right_frame, weight=1)

        ttk.Label(right_frame, text="📁 Documentos", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0,5))

        tree_docs = ttk.Treeview(right_frame, columns=("Archivo",), show="headings", height=4)
        tree_docs.heading("Archivo", text="Nombre del archivo")
        tree_docs.column("Archivo", width=200, anchor=tk.W)
        tree_docs.pack(fill=tk.BOTH, expand=True, pady=5)

        scroll_docs = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=tree_docs.yview)
        tree_docs.configure(yscrollcommand=scroll_docs.set)
        scroll_docs.pack(side=tk.RIGHT, fill=tk.Y)

        # Botones solo para ver/abrir (sin subir/eliminar)
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        def abrir_seleccionado():
            sel = tree_docs.selection()
            if not sel:
                messagebox.showinfo("Selección", "Seleccione un documento para abrir.")
                return
            nombre = tree_docs.item(sel[0], 'values')[0]
            ruta = os.path.join(self._obtener_ruta_beneficiario(benef), nombre)
            if os.path.exists(ruta):
                try:
                    if sys.platform == "win32":
                        os.startfile(ruta)
                    else:
                        subprocess.Popen(['open', ruta] if sys.platform == 'darwin' else ['xdg-open', ruta])
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo abrir el archivo:\n{str(e)}")
            else:
                messagebox.showerror("Error", "El archivo no existe.")

        ttk.Button(btn_frame, text="👁️ Abrir Documento", command=abrir_seleccionado).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🔄 Refrescar", command=lambda: self._actualizar_lista_documentos_beneficiario(benef, tree_docs)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="📂 Abrir Carpeta", command=lambda: self._abrir_carpeta_beneficiario(benef)).pack(side=tk.LEFT, padx=2)

        tree_docs.bind("<Double-1>", lambda e: abrir_seleccionado())

        # Cargar documentos
        self._actualizar_lista_documentos_beneficiario(benef, tree_docs)

        # Botón Cerrar
        ttk.Button(ventana, text="Cerrar", command=ventana.destroy).pack(pady=10)

    def _obtener_ruta_beneficiario(self, benef):
        """Devuelve la ruta de la carpeta de documentos del beneficiario."""
        nombre_limpio = "".join(c for c in benef['nombre'] if c.isalnum() or c in " ._-").strip()
        if not nombre_limpio:
            nombre_limpio = "Sin_nombre"
        return os.path.join(BASE_PATH, "Documentos", self.afiliado['cc'], "Beneficiarios", nombre_limpio)

    def _actualizar_lista_documentos_beneficiario(self, benef, tree_docs):
        """Llena el Treeview con los archivos de la carpeta del beneficiario."""
        for item in tree_docs.get_children():
            tree_docs.delete(item)
        ruta = self._obtener_ruta_beneficiario(benef)
        if not os.path.exists(ruta):
            return
        try:
            archivos = os.listdir(ruta)
            for arch in sorted(archivos):
                tree_docs.insert("", tk.END, values=(arch,))
        except Exception as e:
            print(f"Error al leer carpeta: {e}")

    def _abrir_carpeta_beneficiario(self, benef):
        """Abre la carpeta del beneficiario en el explorador."""
        ruta = self._obtener_ruta_beneficiario(benef)
        if not os.path.exists(ruta):
            try:
                os.makedirs(ruta, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear la carpeta: {str(e)}")
                return
        try:
            if sys.platform == "win32":
                os.startfile(ruta)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", ruta])
            else:
                subprocess.Popen(["xdg-open", ruta])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta: {str(e)}")

    def crear_tarjeta_editable(self, parent):
        """Crea una tarjeta con datos editables y fuente más grande"""
        frame = ttk.Frame(parent, style='Card.TFrame')
        frame.pack(fill=tk.X, pady=6)
        
        inner = ttk.Frame(frame, padding=12)
        inner.pack(fill=tk.X)
        
        header_row = ttk.Frame(inner)
        header_row.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(header_row, text="👤 Mis Datos", style='Subtitle.TLabel').pack(side=tk.LEFT)
        
        self.btn_editar = ttk.Button(header_row, text="✏️ Editar", 
                                     command=self.toggle_edicion, width=12)
        self.btn_editar.pack(side=tk.RIGHT)
        
        self.cc_var = tk.StringVar(value=self.afiliado['cc'])
        self.nombre_var = tk.StringVar(value=self.afiliado['nombre'])
        self.celular_var = tk.StringVar(value=self.afiliado.get('celular', ''))
        self.correo_var = tk.StringVar(value=self.afiliado.get('correo', ''))
        self.direccion_var = tk.StringVar(value=self.afiliado.get('direccion', ''))
        
        # Grid para datos con más espacio
        data_grid = ttk.Frame(inner)
        data_grid.pack(fill=tk.X)
        
        campos = [
            ("Cédula:", self.cc_var, True),   # ← Seguirá siendo solo lectura
            ("Nombre:", self.nombre_var, True),  # ← Ahora editable
            ("Celular:", self.celular_var, True),
            ("Correo:", self.correo_var, True),
            ("Dirección:", self.direccion_var, True),
        ]
        
        self.entries = {}
        for i, (label, var, editable) in enumerate(campos):
            row = i // 2
            col = (i % 2) * 2
            
            ttk.Label(data_grid, text=label, style='Header.TLabel', width=10, font=('Segoe UI', 10, 'bold')).grid(
                row=row, column=col, sticky=tk.W, padx=5, pady=4)
            
            if editable:
                entry = ttk.Entry(data_grid, textvariable=var, width=25, font=('Segoe UI', 11))
                entry.grid(row=row, column=col+1, sticky=tk.W, padx=(0, 15), pady=4)
                self.entries[label] = entry
            else:
                ttk.Label(data_grid, textvariable=var, style='Value.TLabel', font=('Segoe UI', 11, 'bold')).grid(
                    row=row, column=col+1, sticky=tk.W, padx=(0, 15), pady=4)
        
        data_grid.columnconfigure(1, weight=1)
        data_grid.columnconfigure(3, weight=1)
    
    def crear_tarjeta_servicios(self, parent):
        """Crea una tarjeta con servicios activos"""
        frame = ttk.Frame(parent, style='Card.TFrame')
        frame.pack(fill=tk.X, pady=6)
        
        inner = ttk.Frame(frame, padding=12)
        inner.pack(fill=tk.X)
        
        ttk.Label(inner, text="🛡️ Mis Servicios", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 8))
        
        servicios = []
        if self.afiliado.get('eps'):
            servicios.append(("EPS", self.afiliado['eps']))
        if self.afiliado.get('arl'):
            servicios.append(("ARL", self.afiliado['arl']))
        if self.afiliado.get('pension'):
            servicios.append(("Pensión", self.afiliado['pension']))
        if self.afiliado.get('caja_compensacion'):
            servicios.append(("Caja Compensación", self.afiliado['caja_compensacion']))
        
        servicios_grid = ttk.Frame(inner)
        servicios_grid.pack(fill=tk.X)
        
        if servicios:
            for i, (servicio, valor) in enumerate(servicios):
                row = i // 2
                col = (i % 2) * 2
                ttk.Label(servicios_grid, text=f"• {servicio}:", 
                         style='Header.TLabel', width=16, font=('Segoe UI', 10, 'bold')).grid(
                    row=row, column=col, sticky=tk.W, padx=5, pady=4)
                ttk.Label(servicios_grid, text=valor, style='Value.TLabel', 
                         font=('Segoe UI', 11, 'bold')).grid(
                    row=row, column=col+1, sticky=tk.W, padx=(0, 15), pady=4)
        else:
            ttk.Label(inner, text="No tiene servicios activos", style='Info.TLabel', 
                     font=('Segoe UI', 11)).pack(anchor=tk.W)
        
        servicios_grid.columnconfigure(1, weight=1)
        servicios_grid.columnconfigure(3, weight=1)
    
    def crear_tarjeta_pagos(self, parent):
        """Crea una tarjeta con información de pagos"""
        frame = ttk.Frame(parent, style='Card.TFrame')
        frame.pack(fill=tk.X, pady=6)
        
        inner = ttk.Frame(frame, padding=12)
        inner.pack(fill=tk.X)
        
        ttk.Label(inner, text="💰 Pagos", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 8))
        
        info = self.calcular_info_pagos()
        info_grid = ttk.Frame(inner)
        info_grid.pack(fill=tk.X)
        
        for i, (clave, valor) in enumerate(info):
            row = i // 2
            col = (i % 2) * 2
            ttk.Label(info_grid, text=f"{clave}", style='Header.TLabel', width=16, 
                     font=('Segoe UI', 10, 'bold')).grid(
                row=row, column=col, sticky=tk.W, padx=5, pady=4)
            ttk.Label(info_grid, text=valor if valor else "No registrado", style='Info.TLabel', 
                     font=('Segoe UI', 11)).grid(
                row=row, column=col+1, sticky=tk.W, padx=(0, 15), pady=4)
        
        info_grid.columnconfigure(1, weight=1)
        info_grid.columnconfigure(3, weight=1)
    
    def crear_tarjeta_historial(self, parent):
        """Crea una tarjeta con historial de pagos"""
        frame = ttk.Frame(parent, style='Card.TFrame')
        frame.pack(fill=tk.BOTH, expand=True, pady=6)
        
        inner = ttk.Frame(frame, padding=12)
        inner.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(inner, text="📋 Historial", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 8))
        
        historial_frame = ttk.Frame(inner)
        historial_frame.pack(fill=tk.BOTH, expand=True)
        
        if not self.historial_pagos:
            ttk.Label(historial_frame, text="📭 No hay pagos registrados", style='Info.TLabel', 
                     font=('Segoe UI', 11)).pack(anchor=tk.W)
        else:
            for pago in self.historial_pagos[:4]:
                ttk.Label(historial_frame, text=f"📄 {pago.get('fecha', '')}  ${pago.get('valor', 0):,.0f} - {pago.get('servicio', '')[:20]}", 
                         style='Info.TLabel', font=('Segoe UI', 10)).pack(anchor=tk.W, pady=2)
            
            if len(self.historial_pagos) > 4:
                ttk.Label(historial_frame, text=f"... y {len(self.historial_pagos) - 4} más", 
                         style='Small.TLabel', font=('Segoe UI', 10), foreground='#1565c0').pack(anchor=tk.W, pady=2)
    
    def crear_tarjeta_notificaciones(self, parent):
        """Crea una tarjeta con notificaciones"""
        frame = ttk.Frame(parent, style='Card.TFrame')
        frame.pack(fill=tk.BOTH, expand=True, pady=6)
        
        inner = ttk.Frame(frame, padding=12)
        inner.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(inner, text="🔔 Notificaciones", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 8))
        
        notif_frame = ttk.Frame(inner)
        notif_frame.pack(fill=tk.BOTH, expand=True)
        
        if not self.notificaciones:
            ttk.Label(notif_frame, text="🔔 No hay notificaciones", style='Info.TLabel', 
                     font=('Segoe UI', 11)).pack(anchor=tk.W)
        else:
            for notif in self.notificaciones[:4]:
                estado = notif.get('estado', 'Pendiente')
                icono = "⚠️" if estado == "Pendiente" else "✅"
                mensaje = notif.get('mensaje', '')[:55]
                ttk.Label(notif_frame, text=f"{icono} {mensaje}...", 
                         style='Info.TLabel', font=('Segoe UI', 10)).pack(anchor=tk.W, pady=2)
            
            if len(self.notificaciones) > 4:
                ttk.Label(notif_frame, text=f"... y {len(self.notificaciones) - 4} más", 
                         style='Small.TLabel', font=('Segoe UI', 10), foreground='#1565c0').pack(anchor=tk.W, pady=2)
    
    def toggle_edicion(self):
        self.modo_edicion = not self.modo_edicion
        
        if self.modo_edicion:
            self.btn_editar.config(text="💾 Guardar")
            for entry in self.entries.values():
                entry.config(state='normal')
            messagebox.showinfo("Edición", "Puede modificar sus datos personales.\n"
                                          "Los cambios se reflejarán en el sistema Administrativo.")
        else:
            self.guardar_cambios_personales()
    
    def guardar_cambios_personales(self):
        try:
            correo = self.correo_var.get().strip()
            if correo and not validar_correo(correo):
                messagebox.showerror("Error", "Correo electrónico no tiene un formato válido")
                return

            celular = self.celular_var.get().strip()
            if celular and not validar_celular(celular):
                messagebox.showerror("Error", "Número de celular debe ser colombiano (10 dígitos, comenzando con 3)")
                return

            # (El resto del método sin cambios)
            data = {
                'cc': self.cc_var.get(),
                'nombre': self.nombre_var.get(),
                'celular': celular,   # se podría limpiar igual que en SaluPagoApp
                'correo': correo,
                'direccion': self.direccion_var.get().strip(),
                'fecha_ingreso': self.afiliado.get('fecha_ingreso', ''),
                'eps': self.afiliado.get('eps', ''),
                'arl': self.afiliado.get('arl', ''),
                'pension': self.afiliado.get('pension', ''),
                'caja_compensacion': self.afiliado.get('caja_compensacion', ''),
                'mes_pago': self.afiliado.get('mes_pago', ''),
                'valor_pagado': self.afiliado.get('valor_pagado', 0),
                'metodo_pago': self.afiliado.get('metodo_pago', ''),
                'fecha_pago': self.afiliado.get('fecha_pago', '')
            }

            self.db.update_afiliado(self.afiliado['cc'], data)
            self.afiliado.update(data)

            for entry in self.entries.values():
                entry.config(state='disabled')

            self.btn_editar.config(text="✏️ Editar")
            self.modo_edicion = False

            self.mostrar_toast("¡Sus datos han sido actualizados correctamente!")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron guardar los cambios:\n{str(e)}")
            
    def calcular_info_pagos(self):
        info = []
        ultimo_pago = self.afiliado.get('fecha_pago', 'No registrado')
        info.append(("Último Pago:", ultimo_pago))
        
        if ultimo_pago != 'No registrado':
            try:
                fecha_pago = datetime.strptime(ultimo_pago, "%Y-%m-%d")
                prox_vencimiento = fecha_pago + timedelta(days=30)
                dias_restantes = (prox_vencimiento - datetime.now()).days
                info.append(("Próximo vencimiento:", prox_vencimiento.strftime("%d/%m/%Y")))
                if dias_restantes < 0:
                    info.append(("Días en mora:", f"{abs(dias_restantes)} días"))
                else:
                    info.append(("Días restantes:", f"{dias_restantes} días"))
            except:
                pass
        
        valor = self.afiliado.get('valor_pagado', 0)
        info.append(("Valor último pago:", f"${float(valor):,.0f}" if valor else "No registrado"))
        info.append(("Método de pago:", self.afiliado.get('metodo_pago', 'No registrado')))
        
        return info

    def ver_facturas_cliente(self):
        fact_window = Toplevel(self.root)
        fact_window.title(f"Mis Facturas - {self.afiliado['nombre']}")
        fact_window.geometry("600x420")
        fact_window.resizable(False, False)
        
        fact_window.update_idletasks()
        x = (fact_window.winfo_screenwidth() // 2) - (600 // 2)
        y = (fact_window.winfo_screenheight() // 2) - (420 // 2)
        fact_window.geometry(f"+{x}+{y}")
        
        ttk.Label(fact_window, text="📄 Mis Facturas", style='Title.TLabel').pack(pady=15)
        
        self.cargar_facturas()
        
        list_frame = ttk.Frame(fact_window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=10)
        
        if not self.facturas:
            ttk.Label(list_frame, text="No hay facturas disponibles", style='Info.TLabel', 
                     font=('Segoe UI', 12)).pack(pady=40)
        else:
            listbox_frame = ttk.Frame(list_frame)
            listbox_frame.pack(fill=tk.BOTH, expand=True)
            
            scrollbar = ttk.Scrollbar(listbox_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            listbox = tk.Listbox(listbox_frame, font=('Segoe UI', 11), yscrollcommand=scrollbar.set, height=8)
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=listbox.yview)
            
            for factura in self.facturas:
                listbox.insert(tk.END, factura)
            
            def abrir_factura():
                seleccion = listbox.curselection()
                if seleccion:
                    archivo = self.facturas[seleccion[0]]
                    ruta = os.path.join(BASE_PATH, "facturas", archivo)
                    if os.path.exists(ruta):
                        webbrowser.open_new_tab(ruta)
                    else:
                        messagebox.showerror("Error", "El archivo no existe")
            
            btn_frame = ttk.Frame(list_frame)
            btn_frame.pack(pady=12)
            ttk.Button(btn_frame, text="📄 Abrir Factura", command=abrir_factura, 
                      style='Action.TButton').pack(side=tk.LEFT, padx=8)
            ttk.Button(btn_frame, text="📂 Abrir Carpeta", 
                      command=lambda: os.startfile(os.path.join(BASE_PATH, "facturas")),
                      style='Action.TButton').pack(side=tk.LEFT, padx=8)
        
        ttk.Button(fact_window, text="Cerrar", command=fact_window.destroy).pack(pady=12)
    
    def cargar_facturas(self):
        self.facturas = []
        facturas_path = os.path.join(BASE_PATH, "facturas")
        if os.path.exists(facturas_path):
            cc = self.afiliado['cc']
            for f in os.listdir(facturas_path):
                if cc in f and f.endswith('.pdf'):
                    self.facturas.append(f)
        self.facturas.sort(reverse=True)
    
    # =================================================================
    # 1. REEMPLAZA TU FUNCIÓN 'gestionar_incapacidades' POR ESTA:
    # =================================================================
    def gestionar_incapacidades(self):
        """Muestra la ventana de gestión de incapacidades del cliente con columna Valor y dos paneles en detalles."""
        incap_window = Toplevel(self.root)
        incap_window.title(f"Mis Incapacidades - {self.afiliado['nombre']}")
        incap_window.geometry("900x500")
        incap_window.resizable(False, False)
        
        incap_window.update_idletasks()
        x = (incap_window.winfo_screenwidth() // 2) - (900 // 2)
        y = (incap_window.winfo_screenheight() // 2) - (500 // 2)
        incap_window.geometry(f"+{x}+{y}")
        
        ttk.Label(incap_window, text="📋 Mis Incapacidades", style='Title.TLabel').pack(pady=15)
        
        main_frame = ttk.Frame(incap_window, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        list_frame = ttk.LabelFrame(main_frame, text="Mis Incapacidades", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.cargar_datos_cliente()
        
        if not hasattr(self, 'incapacidades') or not self.incapacidades:
            ttk.Label(list_frame, text="No tiene incapacidades registradas", style='Info.TLabel', 
                    font=('Segoe UI', 12)).pack(pady=40)
        else:
            # Agregar columna "Valor"
            columns = ("Fecha Inicio", "Fecha Final", "Tipo", "Días", "Valor", "Estado", "Archivo")
            
            style = ttk.Style()
            style.configure("ClienteIncap.Treeview", font=('Segoe UI', 10))
            style.configure("ClienteIncap.Treeview.Heading", font=('Segoe UI', 10, 'bold'))
            
            self.tree_incapacidades = ttk.Treeview(
                list_frame, 
                columns=columns, 
                show="headings", 
                height=6, 
                style="ClienteIncap.Treeview"
            )
            
            self.tree_incapacidades.column("Fecha Inicio", width=100, anchor=tk.CENTER)
            self.tree_incapacidades.column("Fecha Final", width=100, anchor=tk.CENTER)
            self.tree_incapacidades.column("Tipo", width=160, anchor=tk.W)
            self.tree_incapacidades.column("Días", width=60, anchor=tk.CENTER)
            self.tree_incapacidades.column("Valor", width=100, anchor=tk.CENTER)      # nueva columna
            self.tree_incapacidades.column("Estado", width=120, anchor=tk.CENTER)
            self.tree_incapacidades.column("Archivo", width=120, anchor=tk.CENTER)
            
            for col in columns:
                self.tree_incapacidades.heading(col, text=col)
            
            scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree_incapacidades.yview)
            self.tree_incapacidades.configure(yscroll=scrollbar.set)
            
            self.tree_incapacidades.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            for inc in self.incapacidades:
                estado = "✅ Pagada" if inc.get('fecha_pago') else "⏳ Pendiente"
                tiene_archivo = "📎 Sí" if inc.get('archivo') else "❌ No"
                valor = float(inc.get('valor', 0))
                
                self.tree_incapacidades.insert("", tk.END, values=(
                    inc.get('fecha_inicio', ''),
                    inc.get('fecha_final', ''),
                    inc.get('tipo', '')[:25],
                    inc.get('dias', 0),
                    f"${valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),   # valor formateado
                    estado,
                    tiene_archivo
                ))
            
            def abrir_pdf_por_columna(event):
                region = self.tree_incapacidades.identify_region(event.x, event.y)
                if region != "cell": 
                    return
                col_id = self.tree_incapacidades.identify_column(event.x)
                item_id = self.tree_incapacidades.identify_row(event.y)
                if not item_id or col_id != "#7":   # columna Archivo es la 7
                    return
                index = self.tree_incapacidades.index(item_id)
                if index < len(self.incapacidades):
                    registro = self.incapacidades[index]
                    self.ver_documentos_incapacidad(registro)
            
            self.tree_incapacidades.bind("<Button-1>", abrir_pdf_por_columna)
            self.tree_incapacidades.bind("<Double-1>", lambda e: self.mostrar_detalles_incapacidad_cliente())
        
        # Botones inferiores
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="📤 Subir", 
                command=lambda: self.abrir_subir_incapacidad(incap_window),
                style='Action.TButton').pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="📄 Detalles", 
                command=self.mostrar_detalles_incapacidad_cliente).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="📂 Abrir", 
                command=self.abrir_carpeta_incapacidades).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(incap_window, text="Cerrar", command=incap_window.destroy).pack(pady=12)
        
    def abrir_carpeta_incapacidades(self):
        """Abre la carpeta de incapacidades del cliente en el explorador de archivos"""
        import os
        import sys
        from tkinter import messagebox
        
        cc = self.afiliado['cc']
        incap_dir = os.path.join(BASE_PATH, "Incapacidades", cc)
        
        if os.path.exists(incap_dir):
            try:
                if sys.platform == "win32":
                    os.startfile(incap_dir)
                else:
                    import subprocess
                    subprocess.Popen(['open', incap_dir] if sys.platform == 'darwin' else ['xdg-open', incap_dir])
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir la carpeta:\n{str(e)}")
        else:
            messagebox.showwarning("Carpeta no existe", 
                f"No existe la carpeta de incapacidades para este cliente.\n\n"
                f"Puede subir documentos para crearla.")

    # =================================================================
    # 2. AGREGA ESTA NUEVA FUNCIÓN DEBAJO DE 'gestionar_incapacidades'
    #    (Esto corrige el error: 'object has no attribute...')
    # =================================================================
    def mostrar_detalles_incapacidad_cliente(self):
        selected_item = self.tree_incapacidades.selection()
        if not selected_item:
            messagebox.showinfo("Selección", "Seleccione una incapacidad para ver detalles.")
            return

        index = self.tree_incapacidades.index(selected_item[0])
        if index >= len(self.incapacidades):
            return
        registro = self.incapacidades[index]
        cc = self.afiliado['cc']
        id_incap = registro.get('id')

        # === Ruta de la carpeta de la incapacidad ===
        carpeta_incapacidad = os.path.join(BASE_PATH, "Incapacidades", cc, str(id_incap))
        # Migrar archivo principal si está en la raíz del afiliado
        if registro.get('archivo'):
            archivo_principal = registro['archivo']
            ruta_raiz = os.path.join(BASE_PATH, "Incapacidades", cc, archivo_principal)
            ruta_subcarpeta = os.path.join(carpeta_incapacidad, archivo_principal)
            if os.path.exists(ruta_raiz) and not os.path.exists(ruta_subcarpeta):
                os.makedirs(carpeta_incapacidad, exist_ok=True)
                try:
                    shutil.move(ruta_raiz, ruta_subcarpeta)
                except Exception as e:
                    print(f"Error al mover archivo: {e}")

        detalles_window = Toplevel(self.root)
        detalles_window.title(f"Detalles de Incapacidad - {registro['nombre']}")
        detalles_window.geometry("1000x500")
        detalles_window.resizable(False, False)

        detalles_window.update_idletasks()
        x = (detalles_window.winfo_screenwidth() // 2) - (1000 // 2)
        y = (detalles_window.winfo_screenheight() // 2) - (500 // 2)
        detalles_window.geometry(f"+{x}+{y}")

        paned = ttk.PanedWindow(detalles_window, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Panel izquierdo: Datos y pasos
        left_frame = ttk.Frame(paned, padding=10)
        paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Datos del Afiliado", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0,5))
        ttk.Label(left_frame, text=f"Nombre: {self.afiliado['nombre']}", font=('Segoe UI', 10)).pack(anchor=tk.W)
        ttk.Label(left_frame, text=f"Cédula: {self.afiliado['cc']}", font=('Segoe UI', 10)).pack(anchor=tk.W)
        ttk.Label(left_frame, text=f"EPS: {self.afiliado.get('eps', 'No registrada')}", font=('Segoe UI', 10)).pack(anchor=tk.W)
        ttk.Separator(left_frame, orient='horizontal').pack(fill=tk.X, pady=8)

        ttk.Label(left_frame, text="Detalles de la Incapacidad", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0,5))

        try:
            f_ini = datetime.strptime(registro.get('fecha_inicio', ''), "%Y-%m-%d").strftime("%d/%m/%Y")
        except:
            f_ini = registro.get('fecha_inicio', '')
        try:
            f_fin = datetime.strptime(registro.get('fecha_final', ''), "%Y-%m-%d").strftime("%d/%m/%Y")
        except:
            f_fin = registro.get('fecha_final', '')

        detalles = [
            ("Tipo:", registro.get('tipo', 'No especificado')),
            ("Fecha Inicio:", f_ini),
            ("Fecha Final:", f_fin),
            ("Días:", registro.get('dias', 0)),
            ("Valor a Pagar:", f"${float(registro.get('valor', 0)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
        ]
        for campo, valor in detalles:
            frame = ttk.Frame(left_frame)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=campo, font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=5)
            ttk.Label(frame, text=valor, font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=5)

        # Pasos
        pasos_frame = ttk.Frame(left_frame)
        pasos_frame.pack(fill=tk.X, pady=10)

        estado_actual = registro.get('estado', 'Recibida')
        recibo_descargado = registro.get('recibo_descargado', 0)
        pasos = ["Recibida", "En Revisión", "Pagada"]

        try:
            idx_actual = pasos.index(estado_actual)
        except ValueError:
            idx_actual = 0

        for i, paso in enumerate(pasos):
            if i < idx_actual:
                color = "#4CAF50"
            elif i == idx_actual:
                if paso == "Pagada" and recibo_descargado == 1:
                    color = "#4CAF50"
                else:
                    color = "#FF9800"
            else:
                color = "#BDBDBD"

            lbl = ttk.Label(pasos_frame, text=str(i+1), font=('Segoe UI', 10, 'bold'),
                            background=color, foreground='white', padding=5, relief='ridge')
            lbl.pack(side=tk.LEFT, padx=5)
            ttk.Label(pasos_frame, text=paso, font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=2)
            if i < 2:
                ttk.Label(pasos_frame, text="→", font=('Segoe UI', 12)).pack(side=tk.LEFT, padx=2)

        fecha_estado = registro.get('fecha_estado', '')
        if fecha_estado:
            try:
                fecha_estado_dt = datetime.strptime(fecha_estado, "%Y-%m-%d %H:%M:%S")
                fecha_estado_str = fecha_estado_dt.strftime("%d/%m/%Y %H:%M")
            except:
                fecha_estado_str = fecha_estado
            ttk.Label(left_frame, text=f"Última actualización: {fecha_estado_str}", font=('Segoe UI', 9, 'italic')).pack(anchor=tk.W, pady=5)

        if estado_actual == 'Pagada' and recibo_descargado == 1:
            ttk.Label(left_frame, text="✅ Recibo ya descargado", font=('Segoe UI', 9, 'bold'), foreground='green').pack(anchor=tk.W)

        # Panel derecho: Archivos
        right_frame = ttk.Frame(paned, padding=10)
        paned.add(right_frame, weight=1)

        ttk.Label(right_frame, text="📁 Archivos Adjuntos", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0,5))

        tree_archivos = ttk.Treeview(right_frame, columns=("Archivo",), show="headings", height=2)
        tree_archivos.heading("Archivo", text="Nombre del archivo")
        tree_archivos.column("Archivo", width=280, anchor=tk.W)
        tree_archivos.pack(fill=tk.BOTH, expand=True, pady=5)

        scroll_arch = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=tree_archivos.yview)
        tree_archivos.configure(yscrollcommand=scroll_arch.set)
        scroll_arch.pack(side=tk.RIGHT, fill=tk.Y)

        def actualizar_lista_archivos():
            for item in tree_archivos.get_children():
                tree_archivos.delete(item)
            if not cc or not id_incap:
                return
            carpeta = os.path.join(BASE_PATH, "Incapacidades", cc, str(id_incap))
            if os.path.exists(carpeta):
                for f in os.listdir(carpeta):
                    tree_archivos.insert("", tk.END, values=(f,))

        def eliminar_archivo_seleccionado():
            if not cc or not id_incap:
                messagebox.showerror("Error", "No se puede identificar la carpeta de la incapacidad.")
                return
            seleccion = tree_archivos.selection()
            if not seleccion:
                messagebox.showinfo("Selección", "Seleccione un archivo para eliminar.")
                return
            nombre = tree_archivos.item(seleccion[0], 'values')[0]
            carpeta = os.path.join(BASE_PATH, "Incapacidades", cc, str(id_incap))
            ruta_completa = os.path.join(carpeta, nombre)
            if not os.path.exists(ruta_completa):
                messagebox.showerror("Error", "El archivo no existe en el sistema.")
                return
            if messagebox.askyesno("Confirmar eliminación",
                                f"¿Está seguro de eliminar el archivo '{nombre}'?\n\nEsta acción no se puede deshacer."):
                try:
                    os.remove(ruta_completa)
                    messagebox.showinfo("Éxito", f"Archivo '{nombre}' eliminado correctamente.")
                    actualizar_lista_archivos()
                    if registro.get('archivo') == nombre:
                        registro['archivo'] = None
                        self.db.update_incapacidad(registro['id'], registro)
                        self.cargar_datos_cliente()
                        self.gestionar_incapacidades()
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo eliminar el archivo:\n{str(e)}")

        btn_archivos = ttk.Frame(right_frame)
        btn_archivos.pack(fill=tk.X, pady=5)

        def subir_archivo_adicional():
            if not cc or not id_incap:
                messagebox.showerror("Error", "No se puede identificar la carpeta de la incapacidad.")
                return
            ruta = filedialog.askopenfilename(
                title="Seleccionar archivo para adjuntar",
                filetypes=[("Todos los archivos", "*.*"), ("PDF", "*.pdf"), ("Imágenes", "*.jpg *.png")]
            )
            if not ruta:
                return
            carpeta = os.path.join(BASE_PATH, "Incapacidades", cc, str(id_incap))
            os.makedirs(carpeta, exist_ok=True)
            nombre = os.path.basename(ruta)
            destino = os.path.join(carpeta, nombre)
            try:
                shutil.copy2(ruta, destino)
                messagebox.showinfo("Éxito", f"Archivo '{nombre}' subido correctamente.")
                actualizar_lista_archivos()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo subir el archivo: {str(e)}")

        def ver_archivo_seleccionado():
            if not cc or not id_incap:
                messagebox.showerror("Error", "No se puede identificar la carpeta de la incapacidad.")
                return
            seleccion = tree_archivos.selection()
            if not seleccion:
                messagebox.showinfo("Selección", "Seleccione un archivo para ver.")
                return
            nombre = tree_archivos.item(seleccion[0], 'values')[0]
            carpeta = os.path.join(BASE_PATH, "Incapacidades", cc, str(id_incap))
            ruta_completa = os.path.join(carpeta, nombre)
            if os.path.exists(ruta_completa):
                try:
                    if sys.platform == "win32":
                        os.startfile(ruta_completa)
                    else:
                        subprocess.Popen(['open', ruta_completa] if sys.platform == 'darwin' else ['xdg-open', ruta_completa])
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo abrir el archivo: {str(e)}")
            else:
                messagebox.showerror("Error", "El archivo no existe en el sistema.")

        ttk.Button(btn_archivos, text="📤 Subir Archivo", command=subir_archivo_adicional).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_archivos, text="👁️ Ver Archivo", command=ver_archivo_seleccionado).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_archivos, text="🗑️ Borrar Archivo", command=eliminar_archivo_seleccionado).pack(side=tk.LEFT, padx=5)

        if estado_actual == 'Pagada':
            ttk.Button(btn_archivos, text="🧾 Recibo",
                    command=lambda: self.generar_recibo_incapacidad(registro, detalles_window)).pack(side=tk.LEFT, padx=5)

        ttk.Button(detalles_window, text="Cerrar", command=detalles_window.destroy).pack(pady=10)
        actualizar_lista_archivos()
        
    def generar_recibo_incapacidad(self, registro, ventana_padre=None):
        """Genera un PDF con el recibo de pago de la incapacidad y marca como descargado."""
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        import os, subprocess, sys
        from tkinter import filedialog, messagebox

        # Crear carpeta Recibos si no existe
        recibos_dir = os.path.join(BASE_PATH, "Recibos")
        os.makedirs(recibos_dir, exist_ok=True)

        # Nombre del archivo
        fecha_actual = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(recibos_dir, f"Recibo_Incapacidad_{registro['id']}_{fecha_actual}.pdf")

        doc = SimpleDocTemplate(filename, pagesize=letter,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        elements = []
        styles = getSampleStyleSheet()

        # Estilos personalizados
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Title'],
            fontSize=18,
            textColor=colors.HexColor('#0d47a1'),
            alignment=TA_CENTER,
            spaceAfter=12
        )
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
        )
        body_style = ParagraphStyle(
            'BodyStyle',
            parent=styles['Normal'],
            fontSize=11,
            leading=16,
            alignment=TA_LEFT,
        )

        # Logo (opcional)
        logo_path = os.path.join(IMG_PATH, "LogoSaluPago.png")
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=3*cm, height=3*cm)
                logo.hAlign = 'CENTER'
                elements.append(logo)
                elements.append(Spacer(1, 0.3*cm))
            except:
                pass

        # Título
        elements.append(Paragraph("RECIBO DE PAGO DE INCAPACIDAD", title_style))
        elements.append(Spacer(1, 0.3*cm))

        # Número de recibo
        num_recibo = f"REC-{registro['id']:04d}-{datetime.now().year}"
        elements.append(Paragraph(f"<b>Número de Recibo:</b> {num_recibo}", header_style))
        elements.append(Spacer(1, 0.3*cm))

        # Datos del afiliado
        afiliado = self.afiliado
        elements.append(Paragraph("<b>Datos del Afiliado</b>", body_style))
        elements.append(Paragraph(f"Nombre: {afiliado['nombre']}", body_style))
        elements.append(Paragraph(f"Cédula: {afiliado['cc']}", body_style))
        elements.append(Paragraph(f"EPS: {afiliado.get('eps', 'No registrada')}", body_style))
        elements.append(Spacer(1, 0.3*cm))

        # Datos de la incapacidad
        elements.append(Paragraph("<b>Detalles de la Incapacidad</b>", body_style))
        elements.append(Paragraph(f"Tipo: {registro.get('tipo', '')}", body_style))
        elements.append(Paragraph(f"Fecha de Inicio: {registro.get('fecha_inicio', '')}", body_style))
        elements.append(Paragraph(f"Fecha Final: {registro.get('fecha_final', '')}", body_style))
        elements.append(Paragraph(f"Días: {registro.get('dias', 0)}", body_style))
        elements.append(Paragraph(f"Valor Pagado: ${float(registro.get('valor', 0)):,.2f}", body_style))
        elements.append(Paragraph(f"Fecha de Pago: {registro.get('fecha_pago', '')}", body_style))
        elements.append(Spacer(1, 0.5*cm))

        # Pie de página
        elements.append(Paragraph("Este documento es un comprobante de pago válido.", header_style))
        elements.append(Paragraph(f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}", header_style))

        # Construir PDF
        doc.build(elements)

        # ===== ACTUALIZAR REGISTRO: marcar recibo como descargado =====
        registro['recibo_descargado'] = 1
        self.db.update_incapacidad(registro['id'], registro)
        # Actualizar la lista local (incapacidades) para reflejar el cambio
        for i, inc in enumerate(self.incapacidades):
            if inc['id'] == registro['id']:
                self.incapacidades[i]['recibo_descargado'] = 1
                break

        # Abrir el archivo
        try:
            if sys.platform == 'win32':
                os.startfile(filename)
            elif sys.platform == 'darwin':
                subprocess.call(('open', filename))
            else:
                subprocess.call(('xdg-open', filename))
            messagebox.showinfo("Recibo generado", f"Recibo guardado en:\n{filename}")
        except Exception as e:
            messagebox.showwarning("Recibo generado", f"Se generó el recibo pero no se pudo abrir:\n{str(e)}\nUbicación: {filename}")

        # Refrescar la ventana de detalles para que el color cambie inmediatamente
        if ventana_padre:
            # Reconstruir la ventana de detalles (llamar nuevamente a mostrar_detalles_incapacidad_cliente)
            # Para simplificar, cerramos y reabrimos los detalles
            ventana_padre.destroy()
            self.mostrar_detalles_incapacidad_cliente()
            
    def abrir_subir_incapacidad(self, parent_window):
        """Abre el formulario para que el cliente suba una incapacidad"""
        from tkinter import filedialog
        import os, shutil
        from datetime import datetime
        
        tipos = ["Enfermedad General", "Accidente de Trabajo", "Enfermedad Laboral", "Maternidad"]
        
        dialog = Toplevel(self.root)
        dialog.title("Subir Incapacidad")
        dialog.geometry("500x450")
        dialog.resizable(False, False)
        
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (450 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="📤 Subir Incapacidad", style='Title.TLabel').pack(pady=(0, 15))
        
        tipo_var = tk.StringVar()
        fecha_inicio_var = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        fecha_final_var = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        archivo_path_var = tk.StringVar()
        nombre_archivo_var = tk.StringVar(value="Ningún archivo seleccionado")
        
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(form_frame, text="Tipo de Incapacidad:*", font=('Segoe UI', 10)).pack(anchor=tk.W, pady=(0, 2))
        ttk.Combobox(form_frame, textvariable=tipo_var, values=tipos, state="readonly", 
                    width=45, font=('Segoe UI', 10)).pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(form_frame, text="Fecha de Inicio:* (DD/MM/AAAA)", font=('Segoe UI', 10)).pack(anchor=tk.W, pady=(0, 2))
        ttk.Entry(form_frame, textvariable=fecha_inicio_var, width=45, font=('Segoe UI', 10)).pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(form_frame, text="Fecha Final:* (DD/MM/AAAA)", font=('Segoe UI', 10)).pack(anchor=tk.W, pady=(0, 2))
        ttk.Entry(form_frame, textvariable=fecha_final_var, width=45, font=('Segoe UI', 10)).pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(form_frame, text="Archivo (PDF o imagen):*", font=('Segoe UI', 10)).pack(anchor=tk.W, pady=(0, 2))
        file_frame = ttk.Frame(form_frame)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(file_frame, text="📂 Seleccionar Archivo", 
                command=lambda: self.seleccionar_archivo_incapacidad(archivo_path_var, nombre_archivo_var)
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(file_frame, textvariable=nombre_archivo_var, font=('Segoe UI', 9), foreground='#666').pack(side=tk.LEFT)
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(btn_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📤 Subir", 
                command=lambda: self.guardar_incapacidad_con_archivo(
                    tipo_var.get(), fecha_inicio_var.get(), fecha_final_var.get(),
                    archivo_path_var.get(), dialog, parent_window
                ),
                style='Accent.TButton').pack(side=tk.RIGHT, padx=5)
        
    def subir_incapacidad(self, parent_window):
        """Permite al cliente subir directamente un archivo de incapacidad"""
        from tkinter import filedialog
        import shutil
        
        tipos = ["Enfermedad General", "Accidente de Trabajo", "Enfermedad Laboral", "Maternidad"]
        
        dialog = Toplevel(parent_window)
        dialog.title("Subir Incapacidad")
        dialog.geometry("500x450")
        dialog.resizable(False, False)
        
        # Centrar la ventana
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (450 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Frame principal
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="📤 Subir Incapacidad", style='Title.TLabel').pack(pady=(0, 15))
        
        # Variables
        tipo_var = tk.StringVar()
        fecha_inicio_var = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        fecha_final_var = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        archivo_path_var = tk.StringVar()
        nombre_archivo_var = tk.StringVar(value="Ningún archivo seleccionado")
        
        # Frame para campos
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.X, pady=5)
        
        # Tipo de incapacidad
        ttk.Label(form_frame, text="Tipo de Incapacidad:*", font=('Segoe UI', 10)).pack(anchor=tk.W, pady=(0, 2))
        ttk.Combobox(form_frame, textvariable=tipo_var, values=tipos, state="readonly", 
                    width=45, font=('Segoe UI', 10)).pack(fill=tk.X, pady=(0, 10))
        
        # Fecha de inicio
        ttk.Label(form_frame, text="Fecha de Inicio:* (DD/MM/AAAA)", font=('Segoe UI', 10)).pack(anchor=tk.W, pady=(0, 2))
        ttk.Entry(form_frame, textvariable=fecha_inicio_var, width=45, font=('Segoe UI', 10)).pack(fill=tk.X, pady=(0, 10))
        
        # Fecha final
        ttk.Label(form_frame, text="Fecha Final:* (DD/MM/AAAA)", font=('Segoe UI', 10)).pack(anchor=tk.W, pady=(0, 2))
        ttk.Entry(form_frame, textvariable=fecha_final_var, width=45, font=('Segoe UI', 10)).pack(fill=tk.X, pady=(0, 10))
        
        # Selección de archivo - MEJORADO
        ttk.Label(form_frame, text="Archivo (PDF o imagen):*", font=('Segoe UI', 10)).pack(anchor=tk.W, pady=(0, 2))
        
        # Frame para el selector de archivo
        file_frame = ttk.Frame(form_frame)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Botón para seleccionar archivo (más grande y visible)
        select_btn = ttk.Button(
            file_frame, 
            text="📂 Seleccionar Archivo", 
            command=lambda: self.seleccionar_archivo_incapacidad(archivo_path_var, nombre_archivo_var),
            style='Accent.TButton'
        )
        select_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Mostrar nombre del archivo seleccionado
        ttk.Label(file_frame, textvariable=nombre_archivo_var, font=('Segoe UI', 9), foreground='#666').pack(side=tk.LEFT)
        
        # Botones de acción
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(btn_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📤 Subir Incapacidad", 
                command=lambda: self.guardar_incapacidad_con_archivo(
                    tipo_var.get(), fecha_inicio_var.get(), fecha_final_var.get(),
                    archivo_path_var.get(), dialog, parent_window
                ),
                style='Accent.TButton').pack(side=tk.RIGHT, padx=5)

    def seleccionar_archivo_incapacidad(self, archivo_path_var, nombre_archivo_var):
        """Abre el diálogo para seleccionar un archivo y guarda su ruta"""
        from tkinter import filedialog
        
        archivo = filedialog.askopenfilename(
            title="Seleccionar documento de incapacidad",
            filetypes=[
                ("PDF", "*.pdf"),
                ("Imágenes", "*.jpg *.jpeg *.png *.bmp"),
                ("Documentos", "*.doc *.docx"),
                ("Todos los archivos", "*.*")
            ]
        )
        
        if archivo:
            archivo_path_var.set(archivo)
            # Mostrar solo el nombre del archivo (no la ruta completa)
            nombre_archivo = os.path.basename(archivo)
            nombre_archivo_var.set(f"✅ {nombre_archivo}")

    def guardar_incapacidad_con_archivo(self, tipo, fecha_inicio, fecha_final, archivo_path, dialog, parent_window):
        """Guarda la incapacidad y sube el archivo directamente, estado inicial: Recibida."""
        import shutil
        import os
        from datetime import datetime

        # Validaciones
        if not tipo:
            messagebox.showerror("Error", "Por favor seleccione el tipo de incapacidad")
            return

        if not archivo_path or not os.path.exists(archivo_path):
            messagebox.showerror("Error", "Por favor seleccione un archivo válido")
            return

        try:
            # Validar fechas
            fecha_inicio_dt = datetime.strptime(fecha_inicio, "%d/%m/%Y")
            fecha_final_dt = datetime.strptime(fecha_final, "%d/%m/%Y")

            if fecha_final_dt < fecha_inicio_dt:
                messagebox.showerror("Error", "La fecha final no puede ser anterior a la fecha de inicio")
                return

            fecha_inicio_str = fecha_inicio_dt.strftime("%Y-%m-%d")
            fecha_final_str = fecha_final_dt.strftime("%Y-%m-%d")
            dias = (fecha_final_dt - fecha_inicio_dt).days + 1

        except ValueError:
            messagebox.showerror("Error", "Formato de fecha incorrecto. Use DD/MM/AAAA")
            return

        try:
            cc = self.afiliado['cc']
            # Crear directorio temporal en la raíz (para luego mover)
            incapacidades_dir = os.path.join(BASE_PATH, "Incapacidades", cc)
            os.makedirs(incapacidades_dir, exist_ok=True)

            # Generar nombre único para el archivo
            fecha_actual = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_original = os.path.basename(archivo_path)
            extension = os.path.splitext(nombre_original)[1]
            nombre_archivo_destino = f"{fecha_actual}_{self.afiliado['nombre'].replace(' ', '_')}{extension}"
            archivo_destino_temporal = os.path.join(incapacidades_dir, nombre_archivo_destino)

            # Copiar el archivo al directorio temporal (raíz)
            shutil.copy2(archivo_path, archivo_destino_temporal)

            # Guardar en la base de datos con estado "Recibida" (sin archivo aún)
            data = {
                "nombre": self.afiliado['nombre'],
                "eps": self.afiliado.get('eps', ''),
                "tipo": tipo,
                "fecha_inicio": fecha_inicio_str,
                "fecha_final": fecha_final_str,
                "dias": dias,
                "valor": 0,
                "fecha_pago": None,
                "archivo": nombre_archivo_destino,
                "cedula": cc,
                "estado": "Recibida",
                "fecha_estado": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            new_id = self.db.add_incapacidad(data)
            data['id'] = new_id

            # Ahora mover el archivo a la subcarpeta con el ID
            carpeta_incapacidad = os.path.join(incapacidades_dir, str(new_id))
            os.makedirs(carpeta_incapacidad, exist_ok=True)
            archivo_destino_final = os.path.join(carpeta_incapacidad, nombre_archivo_destino)
            shutil.move(archivo_destino_temporal, archivo_destino_final)

            # Agregar a la lista de incapacidades del cliente
            if not hasattr(self, 'incapacidades'):
                self.incapacidades = []
            self.incapacidades.append(data)

            # Crear notificación para el administrador
            notif_data = {
                "fecha": datetime.now().strftime("%Y-%m-%d"),
                "tipo": "Solicitud de Incapacidad",
                "cc": self.afiliado['cc'],
                "nombre": self.afiliado['nombre'],
                "mensaje": f"El cliente {self.afiliado['nombre']} ha subido una incapacidad de tipo '{tipo}'.\nArchivo: {nombre_archivo_destino}",
                "estado": "Pendiente",
                "fecha_vencimiento": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
                "tag": "solicitud"
            }
            self.db.add_notificacion(notif_data)

            # Actualizar la lista de incapacidades del cliente
            self.cargar_datos_cliente()

            # Mostrar mensaje de éxito
            messagebox.showinfo(
                "Éxito",
                f"✅ Incapacidad subida exitosamente.\n\n"
                f"Tipo: {tipo}\n"
                f"Fecha: {fecha_inicio} al {fecha_final}\n"
                f"Días: {dias}\n"
                f"Archivo: {nombre_archivo_destino}\n\n"
                f"⚠️ Estado: RECIBIDA - Pendiente de revisión.\n"
                f"El administrador revisará la solicitud."
            )

            # Cerrar diálogo y actualizar
            dialog.destroy()
            if parent_window:
                parent_window.destroy()

            # Recargar la vista de incapacidades
            self.gestionar_incapacidades()

        except Exception as e:
            import traceback
            error_detalle = traceback.format_exc()
            messagebox.showerror("Error", f"No se pudo subir la incapacidad:\n{str(e)}\n\nDetalles:\n{error_detalle}")
            
    def ver_documentos_incapacidad(self, incapacidad):
        """Abre el archivo PDF de la incapacidad directamente (si existe)"""
        import os
        import subprocess
        from tkinter import messagebox
        
        try:
            cc = self.afiliado['cc']
            # Ruta donde se guardan las incapacidades
            incap_dir = os.path.join(BASE_PATH, "Incapacidades", cc)
            
            # Si el registro tiene un nombre de archivo específico
            archivo = incapacidad.get('archivo')
            if archivo:
                ruta_archivo = os.path.join(incap_dir, archivo)
                if os.path.exists(ruta_archivo):
                    # Abrir directamente el archivo (PDF, Imagen, etc)
                    try:
                        if sys.platform == "win32":
                            os.startfile(ruta_archivo)
                        else:
                            subprocess.Popen(['open', ruta_archivo] if sys.platform == 'darwin' else ['xdg-open', ruta_archivo])
                        return
                    except Exception as e:
                        messagebox.showerror("Error", f"No se pudo abrir el archivo:\n{str(e)}")
                        return
                else:
                    messagebox.showwarning("Archivo no encontrado", 
                        f"No se encontró el archivo:\n{archivo}\n\n"
                        f"Puede que haya sido movido o eliminado.")
                    # Opcional: abrir la carpeta para que el usuario vea qué hay
                    # if os.path.exists(incap_dir):
                    #     os.startfile(incap_dir)
            else:
                messagebox.showinfo("Sin archivo", "Esta incapacidad no tiene ningún archivo adjunto.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error inesperado:\n{str(e)}")

    def contactar_whatsapp(self):
        try:
            numero = self.afiliado['celular']
            if not numero:
                messagebox.showwarning("Sin número", "No tiene número de celular registrado")
                return
            mensaje = f"Hola {self.afiliado['nombre']}, nos comunicamos de SaluPago para brindarle información sobre su afiliación."
            self._enviar_whatsapp_texto(numero, mensaje)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir WhatsApp: {str(e)}")
    
    def recargar_datos(self):
        self.cargar_datos_cliente()
        self.mostrar_panel_cliente()
        messagebox.showinfo("Actualización", "Datos actualizados correctamente")
    
    def cerrar_sesion_cliente(self):
        if messagebox.askyesno("Cerrar Sesión", "¿Desea cerrar su sesión y volver al menú principal?"):
            self.root.destroy()
            if self.menu_principal:
                self.menu_principal.mostrar_menu()

class Toast:
    """Notificación tipo toast no intrusiva en la esquina superior derecha."""
    def __init__(self, root, message, duration=4000, bg="#2c3e50", fg="white", callback=None):
        self.root = root
        self.message = message
        self.duration = duration
        self.bg = bg
        self.fg = fg
        self.callback = callback
        self.window = None
        self.after_id = None

    def show(self):
        if self.window is not None:
            return  # Ya hay una notificación visible

        self.window = tk.Toplevel(self.root)
        self.window.overrideredirect(True)          # Sin bordes
        self.window.attributes('-topmost', True)    # Siempre encima
        self.window.configure(bg=self.bg)

        # Contenedor principal
        main_frame = ttk.Frame(self.window, style='Toast.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Etiqueta con el mensaje
        label = ttk.Label(main_frame, text=self.message, background=self.bg,
                          foreground=self.fg, font=('Segoe UI', 10, 'bold'),
                          padding=(15, 8))
        label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Botón cerrar
        close_btn = ttk.Button(main_frame, text="✖", command=self.dismiss,
                               style='Toast.TButton')
        close_btn.pack(side=tk.RIGHT, padx=(0, 8))

        # Posicionar en esquina superior derecha
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        screen_width = self.window.winfo_screenwidth()
        x = screen_width - width - 20
        y = 25
        self.window.geometry(f"+{x}+{y}")

        # Temporizador para auto‑cerrar
        self.after_id = self.root.after(self.duration, self.dismiss)

        # Al hacer clic en la etiqueta → ejecutar callback y cerrar
        if self.callback:
            label.bind("<Button-1>", lambda e: self.on_click())
            close_btn.bind("<Button-1>", lambda e: self.on_click())

    def on_click(self):
        self.dismiss()
        if self.callback:
            self.callback()

    def dismiss(self):
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        if self.window:
            self.window.destroy()
            self.window = None

class SaluPagoApp:
    def __init__(self, root, user_role, username=None, menu_principal=None):
        self.root = root
        self.user_role = user_role
        self.username = username or user_role.capitalize()
        self.menu_principal = menu_principal
        self.config = ConfigManager()
        self.root.title(f"SaluPago - Sistema de Pagos a EPS - {self.username}")
        self.root.geometry("1200x600")
        self.root.resizable(True, True)
        
        self.setup_styles()
        self.crear_menu_superior()
        self.setup_pricing_and_options()
        self.setup_variables()
        
        self.db = Database()
        self.cargar_datos_desde_db()

        if 'plantillas_notificaciones' not in self.contabilidad_data:
            self.contabilidad_data['plantillas_notificaciones'] = {}

        # ========== INICIALIZAR SONIDOS ==========
        carpeta_sonidos = os.path.join(IMG_PATH, "sonidos")
        SoundManager.precargar(carpeta_sonidos)
        SoundManager.set_habilitado(self.config.get_sonidos_activo())
        SoundManager.set_volumen(self.config.get_sonidos_volumen())
        # ========================================

        # Programar backup automático
        self.programar_backup_automatico()

        self.setup_interface()
        self.setup_bindings()
        self.setup_shortcuts()

        self.last_escape_time = 0
        self.escape_pending = False

        self.root.after(200, self.mostrar_alertas_vencimiento)
        self.show_welcome_message()

        # ========== ACTUALIZACIÓN CASI INMEDIATA ==========
        self.root.after(100, self.actualizar_estados_pago)

        self.tabs = {}   

    def crear_menu_superior(self):
        """Crea la barra de menú superior con Archivo, BD y Herramientas."""
        menubar = tk.Menu(self.root)

        # Menú Archivo
        menu_archivo = tk.Menu(menubar, tearoff=0)
        if self.user_role == "Administrativo":
            menu_archivo.add_command(label="Administrar Usuarios", command=self.gestion_usuarios)
            menu_archivo.add_command(label="Configuración", command=self.abrir_configuracion)
        menu_archivo.add_command(label="Refrescar Sistema", command=self.refrescar_sistema)
        menu_archivo.add_separator()
        menu_archivo.add_command(label="Cerrar Sesión", command=self.cerrar_sesion)
        menubar.add_cascade(label="Archivo", menu=menu_archivo)

        # ----- NUEVO MENÚ BD (solo admin) -----
        if self.user_role == "Administrativo":
            menu_bd = tk.Menu(menubar, tearoff=0)
            menu_bd.add_command(label="Backup", command=self.crear_copia_seguridad)
            menu_bd.add_separator()
            menu_bd.add_command(label="Nueva Base de Datos", command=self.crear_nueva_base_datos)
            menu_bd.add_command(label="Importar Base de Datos", command=self.importar_base_datos)
            menu_bd.add_separator()
            menu_bd.add_command(label="Historial", command=self.mostrar_historial_backups)
            menubar.add_cascade(label="Respaldo", menu=menu_bd)

            # Menú Auditoría (solo admin)
        if self.user_role == "Administrativo":
            menu_auditoria = tk.Menu(menubar, tearoff=0)
            menu_auditoria.add_command(label="Ver Auditoría", command=self.mostrar_ventana_auditoria)
            menu_auditoria.add_separator()
            menu_auditoria.add_command(label="Limpiar registros antiguos", command=self.limpiar_auditoria_antigua)
            menubar.add_cascade(label="Auditoría", menu=menu_auditoria)

        # Menú Ayuda
        menu_ayuda = tk.Menu(menubar, tearoff=0)
        menu_ayuda.add_command(label="Abrir Ayuda", command=self.mostrar_ayuda)
        menu_ayuda.add_command(label="Comandos", command=self.mostrar_comandos)
        menubar.add_cascade(label="Ayuda", menu=menu_ayuda)

        self.root.config(menu=menubar)

    def refrescar_sistema(self, silent=False):
        """
        Recarga todos los datos desde la base de datos y actualiza todas las tablas,
        contadores, monitoreo, caja, etc.
        Si silent=True, no muestra diálogos de confirmación ni mensajes de éxito.
        """
        if not silent:
            if not messagebox.askyesno("Refrescar Sistema", 
                                    "¿Está seguro de que desea refrescar todos los datos del sistema?\n"
                                    "Se recargarán los datos desde la base de datos."):
                return

        try:
            self.root.config(cursor="watch")
            self.root.update()

            self.data = self.db.get_afiliados_activos()
            self.retiros_data = self.db.get_afiliados_retirados()
            self.contabilidad_data = {
                'ingresos': self.db.get_ingresos(),
                'egresos': self.db.get_egresos(),
                'novedades': self.db.get_novedades(),
                'incapacidades': self.db.get_incapacidades(),
                'monitoreo': self.db.get_monitoreo(),
                'notificaciones': self.db.get_notificaciones(),
                'plantillas_notificaciones': self.db.get_plantillas()
            }

            self.update_afiliados_table()
            self.update_retiros_table()
            self.update_ingresos_table()
            self.update_egresos_table()
            self.update_novedades_table()
            self.update_incapacidades_table()
            self.update_monitoreo_table()

            # CORRECCIÓN: Solo actualizar notificaciones y caja si es Administrativo
            if self.user_role == "Administrativo":
                self.actualizar_notificaciones()
                self.hacer_caja()

            self.calcular_totales_contabilidad()
            self.actualizar_contadores()
            self.cargar_archivados()

            if hasattr(self, 'update_historial_pagos_table'):
                self.update_historial_pagos_table()

            self.root.config(cursor="")
            self.root.update()

            if not silent:
                messagebox.showinfo("Refresco completado", 
                                    "Todos los datos han sido recargados y las vistas actualizadas correctamente.")

        except Exception as e:
            self.root.config(cursor="")
            if not silent:
                messagebox.showerror("Error al refrescar", f"No se pudo completar el refresco:\n{str(e)}")
            else:
                print(f"Error en refresco silencioso: {e}")
                
    def mostrar_toast(self, mensaje, duracion=3000, tipo="exito"):
        colores = {
            "exito": ("#2e7d32", "white"),      # verde oscuro
            "info": ("#0d47a1", "white"),       # azul oscuro
            "advertencia": ("#e65100", "white") # naranja oscuro
        }
        bg, fg = colores.get(tipo, ("#2c3e50", "white"))
        toast = Toast(self.root, mensaje, duration=duracion, bg=bg, fg=fg)
        toast.show()

    def reproducir_sonido(self, clave="confirmar", volumen=None):
        """Reproduce un sonido de retroalimentación.
        Claves: 'agregar', 'editar', 'confirmar', 'eliminar', 'alerta', 'pop'.
        """
        if not self.config.get_sonidos_activo():
            return
        vol = volumen if volumen is not None else self.config.get_sonidos_volumen()
        SoundManager.reproducir(clave, volumen=vol)

    def crear_copia_seguridad(self):
        if not self.validar_password():
            return
        import threading
        threading.Thread(
            target=lambda: self._crear_backup_completo(mostrar_mensaje=True, tipo="manual", usuario=self.username),
            daemon=True
        ).start()

    def crear_copia_seguridad_automatica(self):
        """
        Crea una copia de seguridad automática de la base de datos actual (si existe)
        en la misma carpeta con un nombre con timestamp.
        Retorna la ruta de la copia o None si no se pudo.
        """
        db_path = self.db.db_path
        if not os.path.exists(db_path):
            return None  # No hay base para respaldar

        # Crear nombre de backup con fecha y hora
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.dirname(db_path)
        backup_name = f"backup_automatico_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_name)

        try:
            import shutil
            shutil.copy2(db_path, backup_path)
            return backup_path
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear la copia de seguridad automática:\n{str(e)}")
            return None

    def _crear_backup_completo(self, mostrar_mensaje=False, tipo="manual", usuario="MyAdmin"):
        """
        Realiza el backup completo (ZIP), lo registra y (opcionalmente) lo sube a Drive.
        """
        try:
            import tempfile, shutil, zipfile
            from datetime import datetime

            # Crear copia temporal de la base de datos
            temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
            temp_db.close()
            conn = sqlite3.connect(self.db.db_path)
            backup_conn = sqlite3.connect(temp_db.name)
            conn.backup(backup_conn)
            backup_conn.close()
            conn.close()

            backup_dir = os.path.join(BASE_PATH, "Backup")
            os.makedirs(backup_dir, exist_ok=True)

            ahora = datetime.now()
            fecha_str = ahora.strftime("%Y-%m-%d")
            hora_str = ahora.strftime("%H:%M:%S")
            nombre_zip = f"Backup_{ahora.strftime('%Y-%m-%d_%H-%M-%S')}.zip"
            ruta_zip = os.path.join(backup_dir, nombre_zip)

            with zipfile.ZipFile(ruta_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(temp_db.name, arcname="saluPago.db")
                carpetas = [".BT", "facturas", "Documentos", "BaseRetiros", "Caja", "Incapacidades"]
                for carpeta in carpetas:
                    ruta_carpeta = os.path.join(BASE_PATH, carpeta)
                    if os.path.exists(ruta_carpeta) and os.path.isdir(ruta_carpeta):
                        for raiz, dirs, archivos in os.walk(ruta_carpeta):
                            for archivo in archivos:
                                ruta_completa = os.path.join(raiz, archivo)
                                arcname = os.path.relpath(ruta_completa, BASE_PATH)
                                zipf.write(ruta_completa, arcname=arcname)

            os.unlink(temp_db.name)

            tamaño_bytes = os.path.getsize(ruta_zip)
            tamaño_mb = round(tamaño_bytes / (1024 * 1024), 2)

            # Registrar en BD local
            self.db.add_backup(
                fecha=fecha_str, hora=hora_str, tipo=tipo,
                usuario=usuario, tamaño=tamaño_mb,
                estado="Exitoso", ubicacion=ruta_zip
            )
            self.config.set_ultimo_backup(ahora.isoformat())
            self._limpiar_backups_antiguos()

            # ========== NUEVO: SUBIR A GOOGLE DRIVE ==========
            if self.config.get_drive_activo():
                subir = (
                    (tipo == "automatico" and self.config.get_drive_subir_auto()) or
                    (tipo == "manual" and self.config.get_drive_subir_manual())
                )
                if subir:
                    try:
                        from drive_manager import GoogleDriveManager
                        drive = GoogleDriveManager(folder_name=self.config.get_drive_carpeta())
                        file_id = drive.subir_archivo(ruta_zip, nombre_remoto=nombre_zip)
                        if file_id:
                            print(f"✅ Backup subido a Google Drive: {nombre_zip}")
                            # Opcional: guardar el file_id en la tabla backups
                            self.db.add_backup_drive_info(nombre_zip, file_id)
                        else:
                            print(f"⚠️ No se pudo subir {nombre_zip} a Drive")
                    except FileNotFoundError as e:
                        print(f"⚠️ Google Drive no configurado: {e}")
                    except Exception as e:
                        print(f"⚠️ Error subiendo a Drive: {e}")
            # =================================================

            if mostrar_mensaje:
                messagebox.showinfo("Backup automático", f"Backup completado en:\n{ruta_zip}")
            return True

        except Exception as e:
            try:
                self.db.add_backup(
                    fecha=datetime.now().strftime("%Y-%m-%d"),
                    hora=datetime.now().strftime("%H:%M:%S"),
                    tipo=tipo, usuario=usuario, tamaño=0,
                    estado="Fallido", ubicacion=str(e)
                )
            except:
                pass
            if mostrar_mensaje:
                messagebox.showerror("Error", f"Error en backup: {str(e)}")
            return False
            
    def programar_backup_automatico(self):
        """Inicia el ciclo de backup automático (si está activado)."""
        if self.config.get_backup_activo():
            # Esperar 10 segundos para que la app cargue completamente
            self.root.after(10000, self.ejecutar_backup_automatico)
        else:
            # Si está desactivado, cancelar cualquier ejecución pendiente (opcional)
            pass

    def ejecutar_backup_automatico(self):
        """Ejecuta el backup y programa el siguiente."""
        if not self.config.get_backup_activo():
            return  # Si se desactivó mientras tanto, salir

        import threading
        # Ejecutar backup en un hilo para no bloquear la interfaz
        threading.Thread(target=self._backup_en_hilo, daemon=True).start()

        # Programar la siguiente ejecución
        intervalo_segundos = self.config.get_backup_intervalo() * 3600  # horas -> segundos
        self.root.after(int(intervalo_segundos * 1000), self.ejecutar_backup_automatico)

    def _backup_en_hilo(self):
        try:
            exito = self._crear_backup_completo(mostrar_mensaje=False, tipo="automatico", usuario="Sistema")
            if exito:
                self.root.after(0, lambda: self._mostrar_toast_backup_exitoso())
        except Exception as e:
            print(f"Error en backup automático: {e}")

    def _mostrar_toast_backup_exitoso(self):
        """Muestra una notificación breve (toast) sin interrumpir."""
        # Reutiliza la clase Toast que ya tienes en el código
        toast = Toast(self.root, "✅ Backup automático completado", duration=3000)
        toast.show()

    def _limpiar_backups_antiguos(self):
        """
        Elimina los archivos ZIP y sus registros en la tabla backups que superen los días de conservación.
        """
        try:
            dias_conservar = self.config.get_dias_conservar_backup()
            backup_dir = os.path.join(BASE_PATH, "Backup")
            if not os.path.exists(backup_dir):
                return

            ahora = time.time()
            limite = ahora - (dias_conservar * 24 * 3600)

            # Obtener todos los backups de la BD
            backups_bd = self.db.get_backups()
            for reg in backups_bd:
                ubicacion = reg['ubicacion']
                if os.path.exists(ubicacion):
                    mtime = os.path.getmtime(ubicacion)
                    if mtime < limite:
                        try:
                            os.remove(ubicacion)
                            self.db.delete_backup(reg['id'])
                            print(f"Backup antiguo eliminado: {os.path.basename(ubicacion)}")
                        except Exception as e:
                            print(f"Error al eliminar {ubicacion}: {e}")
                else:
                    # Si el archivo no existe, eliminar el registro
                    self.db.delete_backup(reg['id'])
        except Exception as e:
            print(f"Error en limpieza de backups: {e}")

    def mostrar_historial_backups(self):
        """Abre una ventana con el historial de copias de seguridad."""
        backups = self.db.get_backups()
        if not backups:
            messagebox.showinfo("Historial", "No hay registros de backups en el sistema.")
            return

        ventana = Toplevel(self.root)
        ventana.title("Historial de Backups")
        ventana.geometry("1100x550")
        self.centrar_ventana(ventana, 1100, 550)
        ventana.resizable(True, True)

        main_frame = ttk.Frame(ventana, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Historial de Copias de Seguridad", style='Title.TLabel').pack(pady=(0,10))

        # --- Tabla ---
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0,10))

        columns = ("ID", "Fecha", "Hora", "Tipo", "Usuario", "Tamaño (MB)", "Estado", "Ubicación")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor=tk.W if col=="Ubicación" else tk.CENTER)
        tree.column("ID", width=50)
        tree.column("Fecha", width=90)
        tree.column("Hora", width=80)
        tree.column("Tipo", width=100)
        tree.column("Usuario", width=120)
        tree.column("Tamaño (MB)", width=90)
        tree.column("Estado", width=90)
        tree.column("Ubicación", width=350)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for reg in backups:
            tree.insert("", tk.END, iid=str(reg['id']), values=(
                reg['id'],
                reg['fecha'],
                reg['hora'],
                reg['tipo'],
                reg['usuario'],
                reg['tamaño'],
                reg['estado'],
                reg['ubicacion']
            ))

        # --- Botones de acción (parte inferior) ---
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        def abrir_ubicacion():
            sel = tree.selection()
            if not sel:
                messagebox.showinfo("Selección", "Seleccione un backup.")
                return
            reg = self.db.get_backup_by_id(int(sel[0]))
            if not reg:
                return
            ubicacion = reg['ubicacion']
            if os.path.exists(ubicacion):
                carpeta = os.path.dirname(ubicacion)
                try:
                    if sys.platform == "win32":
                        os.startfile(carpeta)
                    else:
                        subprocess.Popen(['open', carpeta] if sys.platform == 'darwin' else ['xdg-open', carpeta])
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo abrir la carpeta: {str(e)}")
            else:
                messagebox.showerror("Error", "El archivo ya no existe en el sistema.")

        def eliminar_backup():
            sel = tree.selection()
            if not sel:
                messagebox.showinfo("Selección", "Seleccione un backup.")
                return
            if not messagebox.askyesno("Eliminar", "¿Eliminar este backup? Se borrará el archivo y el registro."):
                return
            backup_id = int(sel[0])
            reg = self.db.get_backup_by_id(backup_id)
            if not reg:
                return
            ubicacion = reg['ubicacion']
            if os.path.exists(ubicacion):
                try:
                    os.remove(ubicacion)
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo eliminar el archivo: {str(e)}")
                    return
            self.db.delete_backup(backup_id)
            tree.delete(sel[0])
            messagebox.showinfo("Éxito", "Backup eliminado correctamente.")

        def restaurar_backup():
            sel = tree.selection()
            if not sel:
                messagebox.showinfo("Selección", "Seleccione un backup.")
                return
            if not messagebox.askyesno("Restaurar", 
                "ADVERTENCIA: Esta acción reemplazará la base de datos actual por la del backup seleccionado.\n"
                "Se creará una copia de seguridad de la base de datos actual antes de continuar.\n\n"
                "¿Desea continuar?"):
                return

            backup_id = int(sel[0])
            reg = self.db.get_backup_by_id(backup_id)
            if not reg:
                return
            ubicacion = reg['ubicacion']
            if not os.path.exists(ubicacion):
                messagebox.showerror("Error", "El archivo de backup no existe.")
                return

            try:
                import zipfile
                with zipfile.ZipFile(ubicacion, 'r') as zf:
                    if 'saluPago.db' not in zf.namelist():
                        messagebox.showerror("Error", "El backup no contiene una base de datos válida.")
                        return
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo leer el archivo ZIP: {str(e)}")
                return

            self.crear_copia_seguridad_automatica()

            try:
                import zipfile, tempfile, shutil
                with zipfile.ZipFile(ubicacion, 'r') as zf:
                    temp_dir = tempfile.mkdtemp()
                    zf.extract('saluPago.db', temp_dir)
                    temp_db = os.path.join(temp_dir, 'saluPago.db')
                    destino = self.db.db_path
                    shutil.copy2(temp_db, destino)
                    shutil.rmtree(temp_dir)
            except Exception as e:
                messagebox.showerror("Error", f"Error al restaurar: {str(e)}")
                return

            self.db = Database()
            self.cargar_datos_desde_db()
            self.update_afiliados_table()
            self.update_retiros_table()
            self.update_ingresos_table()
            self.update_egresos_table()
            self.update_novedades_table()
            self.update_incapacidades_table()
            self.update_monitoreo_table()
            self.actualizar_notificaciones()
            self.hacer_caja()
            self.calcular_totales_contabilidad()
            self.actualizar_contadores()

            messagebox.showinfo("Restauración exitosa", "La base de datos ha sido restaurada correctamente.")

        ttk.Button(btn_frame, text="📂 Abrir ubicación", command=abrir_ubicacion).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ Eliminar", command=eliminar_backup).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="♻️ Restaurar", command=restaurar_backup, style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cerrar", command=ventana.destroy).pack(side=tk.RIGHT, padx=5)

        tree.bind("<Double-1>", lambda e: abrir_ubicacion())
        
    def crear_nueva_base_datos(self):
        """
        Crea una nueva base de datos vacía (elimina la actual y la reinicia).
        Solo disponible para Administrativo.
        """
        if self.user_role != "Administrativo":
            messagebox.showerror("Error", "No tiene permisos para realizar esta acción.")
            return

        # Confirmación con contraseña
        if not self.validar_password():
            return

        if not messagebox.askyesno(
            "Confirmar",
            "¿Está seguro de que desea crear una nueva base de datos vacía?\n"
            "Se perderán TODOS los datos actuales (afiliados, retiros, contabilidad, etc.).\n"
            "Esta acción no se puede deshacer.",
            icon=messagebox.WARNING
        ):
            return

        try:
            # --- Crear copia de seguridad automática (si existe base actual) ---
            backup_path = self.crear_copia_seguridad_automatica()
            if backup_path:
                messagebox.showinfo("Copia de seguridad", f"Se ha creado una copia de seguridad automática en:\n{backup_path}")

            # Eliminar el archivo de base de datos actual
            db_path = self.db.db_path
            if os.path.exists(db_path):
                os.remove(db_path)

            # Crear una nueva instancia de Database (esto creará las tablas vacías)
            self.db = Database()
            # Recargar todos los datos desde la nueva base (vacía)
            self.recargar_todo()

            messagebox.showinfo("Éxito", "Base de datos nueva creada exitosamente.\nTodos los datos han sido reiniciados.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear la nueva base de datos:\n{str(e)}")

    def importar_base_datos(self):
        """
        Permite seleccionar un archivo .db externo y reemplazar la base de datos actual.
        Solo disponible para Administrativo.
        """
        if self.user_role != "Administrativo":
            messagebox.showerror("Error", "No tiene permisos para realizar esta acción.")
            return

        # Confirmación con contraseña
        if not self.validar_password():
            return

        # Seleccionar archivo .db
        archivo_db = filedialog.askopenfilename(
            title="Seleccionar base de datos SQLite",
            filetypes=[("Archivos SQLite", "*.db"), ("Todos los archivos", "*.*")]
        )
        if not archivo_db:
            return  # Usuario canceló

        # Confirmar la importación
        if not messagebox.askyesno(
            "Confirmar importación",
            f"Se reemplazará la base de datos actual con:\n{archivo_db}\n\n"
            "Todos los datos actuales se perderán.\n"
            "¿Desea continuar?",
            icon=messagebox.WARNING
        ):
            return

        try:
            # --- Crear copia de seguridad automática (si existe base actual) ---
            backup_path = self.crear_copia_seguridad_automatica()
            if backup_path:
                messagebox.showinfo("Copia de seguridad", f"Se ha creado una copia de seguridad automática en:\n{backup_path}")

            # Obtener la ruta de destino (donde está la base actual)
            destino = self.db.db_path

            # Copiar el archivo seleccionado al destino
            import shutil
            shutil.copy2(archivo_db, destino)

            # Recargar la base de datos
            self.db = Database()  # Reabre la conexión con el nuevo archivo
            self.recargar_todo()

            mensaje = "Base de datos importada exitosamente."
            if backup_path:
                mensaje += f"\nSe ha creado una copia de seguridad de la anterior en:\n{backup_path}"
            messagebox.showinfo("Éxito", mensaje)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo importar la base de datos:\n{str(e)}")

    def recargar_todo(self):
        """
        Recarga todos los datos desde la base de datos actual y actualiza todas las tablas.
        """
        # Volver a cargar datos desde la BD
        self.data = self.db.get_afiliados_activos()
        self.retiros_data = self.db.get_afiliados_retirados()
        self.contabilidad_data = {
            'ingresos': self.db.get_ingresos(),
            'egresos': self.db.get_egresos(),
            'novedades': self.db.get_novedades(),
            'incapacidades': self.db.get_incapacidades(),
            'monitoreo': self.db.get_monitoreo(),
            'notificaciones': self.db.get_notificaciones(),
            'plantillas_notificaciones': self.db.get_plantillas()
        }

        # Actualizar todas las tablas y contadores
        self.update_afiliados_table()
        self.update_retiros_table()
        self.update_ingresos_table()
        self.update_egresos_table()
        self.update_novedades_table()
        self.update_incapacidades_table()
        self.update_monitoreo_table()
        self.actualizar_notificaciones()
        self.hacer_caja()
        self.calcular_totales_contabilidad()
        self.actualizar_contadores()

        # Refrescar la interfaz de monitoreo (opcional)
        if hasattr(self, 'monitoreo_tree'):
            self.update_monitoreo_table()

        messagebox.showinfo("Recarga completa", "Todos los datos han sido recargados desde la base de datos.")

    def mostrar_ventana_auditoria(self):
        if self.user_role != "Administrativo":
            messagebox.showerror("Error", "No tiene permisos para ver la auditoría.")
            return

        ventana = Toplevel(self.root)
        ventana.title("Auditoría del Sistema")
        ventana.geometry("1100x500")
        self.centrar_ventana(ventana, 1100, 500)
        ventana.resizable(True, True)

        main_frame = ttk.Frame(ventana, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Registro de Auditoría", style='Title.TLabel').pack(pady=(0, 10))

        # Filtros
        filter_frame = ttk.Frame(main_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(filter_frame, text="Fecha desde:").pack(side=tk.LEFT, padx=5)
        fecha_desde_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=fecha_desde_var, width=15).pack(side=tk.LEFT, padx=5)

        ttk.Label(filter_frame, text="Fecha hasta:").pack(side=tk.LEFT, padx=5)
        fecha_hasta_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=fecha_hasta_var, width=15).pack(side=tk.LEFT, padx=5)

        ttk.Label(filter_frame, text="Usuario:").pack(side=tk.LEFT, padx=5)
        usuario_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=usuario_var, width=15).pack(side=tk.LEFT, padx=5)

        ttk.Label(filter_frame, text="Módulo:").pack(side=tk.LEFT, padx=5)
        modulo_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=modulo_var, width=15).pack(side=tk.LEFT, padx=5)

        def aplicar_filtros():
            filtros = {}
            if fecha_desde_var.get():
                filtros['fecha_desde'] = fecha_desde_var.get()
            if fecha_hasta_var.get():
                filtros['fecha_hasta'] = fecha_hasta_var.get()
            if usuario_var.get():
                filtros['usuario'] = usuario_var.get()
            if modulo_var.get():
                filtros['modulo'] = modulo_var.get()
            actualizar_tabla(filtros)

        ttk.Button(filter_frame, text="🔍 Filtrar", command=aplicar_filtros).pack(side=tk.LEFT, padx=5)
        ttk.Button(filter_frame, text="Mostrar todos", command=lambda: actualizar_tabla({})).pack(side=tk.LEFT, padx=5)

        # Tabla
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("Fecha", "Usuario", "Rol", "Acción", "Módulo", "Resultado", "Detalles")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120, anchor=tk.CENTER)
        tree.column("Detalles", width=200, anchor=tk.W)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def actualizar_tabla(filtros=None):
            for item in tree.get_children():
                tree.delete(item)
            registros = self.db.get_auditoria(filtros)
            for reg in registros:
                tree.insert("", tk.END, values=(
                    reg['fecha'],
                    reg['usuario'],
                    reg['rol'],
                    reg['accion'],
                    reg['modulo'],
                    reg['resultado'],
                    reg.get('detalles', '')
                ))

        actualizar_tabla({})

        # Botones
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        def exportar_excel():
            try:
                import openpyxl
            except ImportError:
                if messagebox.askyesno("Dependencia faltante", "Instalar openpyxl?"):
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl"])
                    import openpyxl
                else:
                    return
            datos = []
            for item in tree.get_children():
                valores = tree.item(item, 'values')
                datos.append({
                    'Fecha': valores[0],
                    'Usuario': valores[1],
                    'Rol': valores[2],
                    'Acción': valores[3],
                    'Módulo': valores[4],
                    'Resultado': valores[5],
                    'Detalles': valores[6] if len(valores) > 6 else ''
                })
            if not datos:
                messagebox.showinfo("Sin datos", "No hay registros para exportar.")
                return
            df = pd.DataFrame(datos)
            reportes_dir = os.path.join(BASE_PATH, "Reportes")
            os.makedirs(reportes_dir, exist_ok=True)
            filename = f"Auditoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = os.path.join(reportes_dir, filename)
            df.to_excel(filepath, index=False, engine='openpyxl')
            messagebox.showinfo("Exportado", f"Archivo guardado en:\n{filepath}")
            if messagebox.askyesno("Abrir carpeta", "¿Abrir ubicación?"):
                os.startfile(reportes_dir)

        ttk.Button(btn_frame, text="📊 Exportar a Excel", command=exportar_excel).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔄 Refrescar", command=lambda: actualizar_tabla({})).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cerrar", command=ventana.destroy).pack(side=tk.RIGHT, padx=5)

    def limpiar_auditoria_antigua(self):
        if self.user_role != "Administrativo":
            messagebox.showerror("Error", "No tiene permisos.")
            return
        dias = simpledialog.askinteger("Limpiar auditoría", 
                                    "¿Eliminar registros anteriores a cuántos días? (ej: 90)",
                                    parent=self.root, minvalue=1, maxvalue=365)
        if not dias:
            return
        if not messagebox.askyesno("Confirmar", f"¿Eliminar todos los registros de más de {dias} días?"):
            return
        fecha_limite = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S")
        with self.db._get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM auditoria WHERE fecha < ?", (fecha_limite,))
            conn.commit()
        messagebox.showinfo("Limpieza completada", f"Se eliminaron registros anteriores a {dias} días.")
        self._registrar_auditoria("Limpió registros antiguos", "Auditoría", "Éxito", 
                                f"Eliminados registros anteriores a {dias} días")

    def mostrar_ayuda(self):
        """Abre una ventana emergente con el contenido de ayuda."""
        ventana = Toplevel(self.root)
        ventana.title("Ayuda de SaluPago")
        ventana.geometry("850x500")
        self.centrar_ventana(ventana, 850, 500)  
        ventana.resizable(True, True)
        ventana.transient(self.root)   
        ventana.grab_set()            

        # Frame contenedor
        frame = ttk.Frame(ventana)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Llamar al método que construye la ayuda
        self.setup_ayuda_interface(frame)

        # Botón para cerrar (opcional, ya que la ventana tiene el botón X)
        ttk.Button(ventana, text="Cerrar", command=ventana.destroy).pack(pady=8)

        # Ajustar foco
        ventana.focus_force()

    def mostrar_comandos(self):
        """Abre una ventana centrada con la lista de comandos organizada en 3 secciones:
        izquierda, derecha y una sección inferior que ocupa todo el ancho."""
        ancho, alto = 1100, 620

        ventana = Toplevel(self.root)
        ventana.title("Comandos del Sistema - SaluPago")    

        # ---- 1) Ocultar la ventana mientras se posiciona (evita parpadeo) ----
        ventana.withdraw()

        # ---- 2) Configurar tamaño mínimo y permitir redimensionado ----
        ventana.minsize(900, 500)
        ventana.resizable(True, True)

        # ---- 3) Centrado robusto: se calcula DESPUÉS de update_idletasks ----
        ventana.update_idletasks()
        screen_w = ventana.winfo_screenwidth()
        screen_h = ventana.winfo_screenheight()
        x = max(0, (screen_w // 2) - (ancho // 2))
        y = max(0, (screen_h // 2) - (alto // 2))
        ventana.geometry(f"{ancho}x{alto}+{x}+{y}")

        # ---- 4) Mostrar y traer al frente ----
        ventana.deiconify()
        ventana.lift()
        ventana.focus_force()
        ventana.transient(self.root)
        ventana.grab_set()

        # ============ Encabezado ============
        header_frame = ttk.Frame(ventana, padding=(20, 14, 20, 6))
        header_frame.pack(fill=tk.X)

        ttk.Label(header_frame, text="⌨️  Comandos y Atajos de Teclado",
                style='Title.TLabel').pack(anchor=tk.W)
        ttk.Label(header_frame,
                text="Todos los comandos disponibles en el sistema. Presione la combinación indicada para ejecutar la acción.",
                font=('Segoe UI', 9, 'italic'), foreground='#555').pack(anchor=tk.W, pady=(4, 0))

        ttk.Separator(ventana, orient='horizontal').pack(fill=tk.X, padx=20)

        # ============ Contenedor principal (grid de 2 filas x 2 columnas) ============
        # Fila 0: izquierda y derecha  |  Fila 1: inferior (span 2 columnas)
        main_frame = ttk.Frame(ventana, padding=(20, 12, 20, 10))
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1, uniform="col")
        main_frame.columnconfigure(1, weight=1, uniform="col")
        main_frame.rowconfigure(0, weight=3)
        main_frame.rowconfigure(1, weight=1)

        # ============================================================
        # Helper: dibuja una sección (LabelFrame) con sus categorías
        # ============================================================
        def _render_seccion(parent, titulo, categorias):
            """Renderiza un LabelFrame con varias categorías, cada una con filas
            de 2 columnas: 'Atajo' y 'Descripción'."""
            seccion = ttk.LabelFrame(parent, text=titulo, padding=10)
            seccion.columnconfigure(0, weight=1)

            fila = 0
            for idx, (nombre_cat, items) in enumerate(categorias):
                # Título de categoría
                ttk.Label(seccion, text=nombre_cat,
                        font=('Segoe UI', 10, 'bold'),
                        foreground='#0d47a1').grid(
                    row=fila, column=0, sticky=tk.W, padx=4, pady=(4 if idx == 0 else 10, 4))
                fila += 1

                # Fila de encabezados (Atajo | Descripción)
                header_row = ttk.Frame(seccion)
                header_row.grid(row=fila, column=0, sticky=tk.EW, padx=4, pady=(0, 4))
                header_row.columnconfigure(0, weight=0, minsize=150)
                header_row.columnconfigure(1, weight=1)
                ttk.Label(header_row, text="Atajo",
                        font=('Segoe UI', 9, 'bold'),
                        foreground='#37474f').grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
                ttk.Label(header_row, text="Descripción",
                        font=('Segoe UI', 9, 'bold'),
                        foreground='#37474f').grid(row=0, column=1, sticky=tk.W)
                fila += 1

                # Filas de comandos
                for atajo, descripcion in items:
                    row = ttk.Frame(seccion)
                    row.grid(row=fila, column=0, sticky=tk.EW, padx=4, pady=3)
                    row.columnconfigure(0, weight=0, minsize=150)
                    row.columnconfigure(1, weight=1)

                    # Pastilla del atajo
                    tk.Label(
                        row, text=atajo,
                        font=('Consolas', 9, 'bold'),
                        bg='#e8eaf6', fg='#1a237e',
                        padx=8, pady=2,
                        relief='ridge', borderwidth=1
                    ).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))

                    # Descripción
                    ttk.Label(row, text=descripcion,
                            font=('Segoe UI', 9)).grid(
                        row=0, column=1, sticky=tk.W)
                    fila += 1

                # Separador entre categorías (excepto en la última)
                if idx < len(categorias) - 1:
                    ttk.Separator(seccion, orient='horizontal').grid(
                        row=fila, column=0, sticky=tk.EW, padx=4, pady=(8, 4))
                    fila += 1

            return seccion

        # ============================================================
        # Sección IZQUIERDA (fila 0, columna 0)
        # ============================================================
        cats_izquierda = [
            ("📁  Gestión de Afiliados", [
                ("Ctrl + N",   "Crear un nuevo afiliado"),
                ("Ctrl + E",   "Editar el afiliado seleccionado"),
                ("Ctrl + R",   "Retirar afiliado(s) seleccionado(s)"),
                ("Ctrl + D",   "Eliminar afiliado(s) seleccionado(s)"),
                ("Ctrl + C",   "Copiar la cédula del afiliado seleccionado"),
            ]),
            ("🔍  Búsquedas", [
                ("Ctrl + F",   "Enfocar búsqueda de Afiliados Activos"),
                ("Ctrl + B",   "Abrir la Búsqueda Global (activos, retirados y archivados)"),
            ]),
        ]
        seccion_izq = _render_seccion(main_frame, "Sección Izquierda", cats_izquierda)
        seccion_izq.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))

        # ============================================================
        # Sección DERECHA (fila 0, columna 1)
        # ============================================================
        cats_derecha = [
            ("💾  Sistema y Respaldos", [
                ("Ctrl + S",   "Crear copia de seguridad (solo Administrativo)"),
                ("F5",         "Refrescar el sistema (recargar datos)"),
                ("Ctrl + Q",   "Cerrar sesión del usuario actual"),
            ]),
            ("❓  Ayuda y Navegación", [
                ("F1",         "Abrir la ventana de Ayuda"),
                ("ESC",        "Cerrar ventana emergente activa"),
                ("ESC  ESC",   "Presione ESC dos veces seguidas para salir del programa"),
            ]),
        ]
        seccion_der = _render_seccion(main_frame, "Sección Derecha", cats_derecha)
        seccion_der.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 8))

        # ============================================================
        # Sección INFERIOR (fila 1, ocupa ambas columnas)
        # ============================================================
        cats_inferior = [
            ("🔐  Seguridad y Pánico (uso interno)", [
                ("Ctrl + Shift + P", "Activar el Botón de Pánico (silencioso)"),
                ("Ctrl + Shift + W", "WIPE TOTAL — borrado seguro de carpetas (destructivo)"),
            ]),
        ]
        seccion_inf = _render_seccion(main_frame, "Sección Inferior", cats_inferior)
        seccion_inf.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=0, pady=(8, 0))

        # ============ Pie de página con nota ============
        nota_frame = ttk.Frame(ventana, padding=(20, 4))
        nota_frame.pack(fill=tk.X)
        ttk.Label(nota_frame,
                text="ℹ️  Nota: algunos comandos (como Ctrl+R, Ctrl+D, Ctrl+S) requieren rol Administrativo.",
                font=('Segoe UI', 9, 'italic'), foreground='#666',
                wraplength=1000, justify=tk.LEFT).pack(anchor=tk.W)

        # ============ Botones inferiores ============
        bottom_frame = ttk.Frame(ventana, padding=(20, 10))
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Separator(bottom_frame, orient='horizontal').pack(fill=tk.X, pady=(0, 10))
        ttk.Button(bottom_frame, text="Cerrar", command=ventana.destroy,
                width=15).pack(side=tk.RIGHT)

        ventana.focus_force()

    def _registrar_auditoria(self, accion, modulo, resultado, detalles=None):
        from datetime import datetime
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.db.registrar_auditoria(fecha, self.username, self.user_role, accion, modulo, resultado, detalles)

    def cerrar_sesion(self):
        if messagebox.askyesno("Cerrar Sesión", "¿Está seguro de que desea cerrar sesión?"):
            self._registrar_auditoria("Cerró sesión", "Sistema", "Éxito")
            try:
                self.db.exportar_a_json()
            except:
                pass
            self.root.destroy()
            if self.menu_principal:
                self.menu_principal.mostrar_menu()
    
    def setup_styles(self):
        """Configura los estilos visuales de la aplicación"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Configuraciones generales
        self.style.configure('.', background='#f0f0f0', font=('Arial', 10))
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0')
        self.style.configure('TButton', padding=5)
        self.style.configure('Treeview', rowheight=25)
        self.style.configure('Treeview.Heading', font=('Arial', 10, 'bold'))
        
        # Estilos personalizados
        self.style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        self.style.configure('Section.TLabel', font=('Arial', 12, 'bold'))
        self.style.configure('Required.TLabel', font=('Arial', 10, 'bold'), foreground='red')

        # ======================================================
        # ESTILO PERSONALIZADO PARA CHECKBOX DE DOCUMENTOS
        # ======================================================
        # Fuente base del checkbox
        self.style.configure('Small.TCheckbutton', font=('Segoe UI', 9))
        
        # MAP: Cambia el color del texto según el estado del checkbox
        # - selected   -> cuando el checkbox está marcado (variable = True) -> negro
        # - !selected  -> cuando el checkbox NO está marcado (variable = False) -> gris
        self.style.map('Small.TCheckbutton',
            foreground=[
                ('selected', '#000000'),   # Negro cuando está marcado
                ('!selected', '#9e9e9e')   # Gris cuando NO está marcado
            ]
        )
        # ======================================================

        # Estilo para notificaciones Toast
        self.style.configure('Toast.TFrame', background='#2c3e50')
        self.style.configure('Toast.TButton', background='#2c3e50', foreground='white',
                            borderwidth=0, font=('Segoe UI', 10, 'bold'))
        self.style.map('Toast.TButton', background=[('active', '#34495e')])
           
    def setup_pricing_and_options(self):
        """Configura los precios y opciones disponibles desde el archivo de configuración."""
        self.precios = {
            'eps': self.config.get_precio_eps(),
            'arl': self.config.get('precios.arl', {}),
            'pension': self.config.get_precio_pension(),
            'caja': self.config.get_precio_caja()
        }
        self.eps_options = self.config.get_opciones('eps')
        self.arl_options = self.config.get_opciones('arl')
        self.pension_options = self.config.get_opciones('pension')
        self.caja_compensacion_options = self.config.get_opciones('caja_compensacion')
        self.meses = self.config.get_opciones('meses')
        self.metodos_pago = self.config.get_opciones('metodos_pago')
        self.base_caja = self.config.get_base_caja()
    
    def setup_variables(self):
        """Configura las variables de control de TKinter"""
        self.cc_var = tk.StringVar()
        self.nombre_var = tk.StringVar()
        self.celular_var = tk.StringVar()
        self.direccion_var = tk.StringVar()
        self.correo_var = tk.StringVar()
        self.fecha_ingreso_var = tk.StringVar()
        self.eps_var = tk.StringVar()
        self.arl_var = tk.StringVar()
        self.pension_var = tk.StringVar()
        self.caja_var = tk.StringVar()
        # self.mes_pago_var = tk.StringVar()
        self.valor_pagado_var = tk.StringVar()
        self.fecha_pago_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.metodo_pago_var = tk.StringVar()
        self.busqueda_var = tk.StringVar()
        self.busqueda_archivados_var = tk.StringVar() 

        # Variables para contabilidad
        self.total_ingresos_var = tk.StringVar(value="$0")
        self.total_egresos_var = tk.StringVar(value="$0")
        self.saldo_var = tk.StringVar(value="$0")

        # Variables para novedades
        self.novedad_desc_var = tk.StringVar()

        self.filtro_fecha_ingresos = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.filtro_fecha_egresos = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
    
    def cargar_datos_desde_db(self):
        """Carga todos los datos desde la base de datos SQLite a las listas en memoria."""
        self.data = self.db.get_afiliados_activos()
        self.retiros_data = self.db.get_afiliados_retirados()
        self.contabilidad_data = {
            'ingresos': self.db.get_ingresos(),
            'egresos': self.db.get_egresos(),
            'novedades': self.db.get_novedades(),
            'incapacidades': self.db.get_incapacidades(),
            'monitoreo': self.db.get_monitoreo(),
            'notificaciones': self.db.get_notificaciones(),
            'plantillas_notificaciones': self.db.get_plantillas()
        }
    
    def setup_interface(self):
        """Configura la interfaz principal con pestañas y la nueva pestaña Inicio."""
        # Frame superior para los contadores
        top_bar = ttk.Frame(self.root)
        top_bar.pack(fill=tk.X, padx=5, pady=5, anchor='ne')

        self.contador_afiliados = tk.StringVar()
        self.contador_retiros = tk.StringVar()
        self.contador_total = tk.StringVar()

        self.actualizar_contadores()

        # Empaquetar en orden inverso para alinear a la derecha:
        # Total (más a la derecha) -> Retiros -> Afiliados (más a la izquierda)
        ttk.Label(top_bar, textvariable=self.contador_total,
                relief=tk.SUNKEN, padding=(5,2)).pack(side=tk.RIGHT, padx=2)
        ttk.Label(top_bar, textvariable=self.contador_retiros,
                relief=tk.SUNKEN, padding=(5,2)).pack(side=tk.RIGHT, padx=2)
        ttk.Label(top_bar, textvariable=self.contador_afiliados,
                relief=tk.SUNKEN, padding=(5,2)).pack(side=tk.RIGHT, padx=2)
        
        # Crear pestañas
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # ====== OCULTAR PESTAÑAS ======
        self.style.configure('TNotebook', tabposition='none')

        # Diccionario para almacenar referencias a las pestañas
        self.tabs = {}

        # ---- Pestaña Inicio (la primera) ----
        inicio_frame = ttk.Frame(self.notebook)
        self.notebook.add(inicio_frame, text="🏠 Inicio")
        self.tabs["Inicio"] = inicio_frame
        self.setup_inicio_interface(inicio_frame)

        # ---- Resto de pestañas ----
        self.afiliados_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.afiliados_frame, text="👥 Afiliados Activos")
        self.tabs["Afiliados Activos"] = self.afiliados_frame

        self.retiros_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.retiros_frame, text="📋 Retiros")
        self.tabs["Retiros"] = self.retiros_frame

        self.archivados_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.archivados_frame, text="📦 Archivados")
        self.tabs["Archivados"] = self.archivados_frame

        self.contabilidad_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.contabilidad_frame, text="💰 C.H.I.N")
        self.tabs["C.H.I.N"] = self.contabilidad_frame

        self.monitoreo_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.monitoreo_frame, text="📊 Monitoreo")
        self.tabs["Monitoreo"] = self.monitoreo_frame

        # Notificaciones y Caja solo para Administrativo
        if self.user_role == "Administrativo":
            self.notificaciones_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.notificaciones_frame, text="🔔 Notificaciones")
            self.tabs["Notificaciones"] = self.notificaciones_frame
            
            self.caja_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.caja_frame, text="💵 Caja")
            self.tabs["Caja"] = self.caja_frame

        # Configurar cada pestaña (excepto Inicio que ya está configurada)
        self.setup_afiliados_interface()
        self.setup_retiros_interface()
        self.setup_contabilidad_interface()
        self.setup_monitoreo_interface(self.monitoreo_frame)
        self.setup_archivados_interface(self.archivados_frame)
        if self.user_role == "Administrativo":
            self.setup_notificaciones_interface(self.notificaciones_frame)
            self.setup_caja_interface(self.caja_frame)
            
    def setup_inicio_interface(self, parent):
        """Configura la pestaña de Inicio con logo, botones de acceso rápido, ayuda y cierre de sesión."""
        # Frame principal dividido en dos columnas
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Columna izquierda: Logo
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 20))

        try:
            logo_path = os.path.join(IMG_PATH, "LogoSaluPago.png")
            if os.path.exists(logo_path):
                img = Image.open(logo_path)
                img = img.resize((500, 500), Image.LANCZOS)
                logo_img = ImageTk.PhotoImage(img)
                logo_label = ttk.Label(left_frame, image=logo_img)
                logo_label.image = logo_img
                logo_label.pack(expand=True)
            else:
                ttk.Label(left_frame, text="SaluPago", font=('Segoe UI', 24, 'bold')).pack(expand=True)
        except Exception as e:
            ttk.Label(left_frame, text="SaluPago", font=('Segoe UI', 24, 'bold')).pack(expand=True)
            print(f"Error cargando logo: {e}")

        # Columna derecha: Botones de acceso
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        ttk.Label(right_frame, text="Acceso Rápido", font=('Segoe UI', 18, 'bold')).pack(pady=(0, 15))

        # Botones en una cuadrícula de 2 columnas
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(expand=True, fill=tk.BOTH)

        # Lista de botones: (texto, clave_pestaña, solo_admin)
        # Ahora incluye "Ayuda y Soporte" entre los botones principales
        botones = [
            ("👥 Afiliados Activos", "Afiliados Activos", False),
            ("📋 Retiros", "Retiros", False),
            ("📦 Archivados", "Archivados", False),
            ("💰 C.H.I.N", "C.H.I.N", False),
            ("📊 Monitoreo", "Monitoreo", False),
            ("❓ Ayuda y Soporte", "Ayuda", False),  
        ]
        if self.user_role == "Administrativo":
            botones.append(("🔔 Notificaciones", "Notificaciones", True))
            botones.append(("💵 Caja", "Caja", True))

        row, col = 0, 0
        for texto, clave, MyAdmin in botones:
            if MyAdmin and self.user_role != "Administrativo":
                continue

            # Comando especial para el botón de Ayuda
            if clave == "Ayuda":
                cmd = self.mostrar_ayuda
            else:
                cmd = lambda k=clave: self.notebook.select(self.tabs[k])

            btn = ttk.Button(
                btn_frame,
                text=texto,
                width=20,
                style='Menu.TButton',
                command=cmd
            )
            btn.grid(row=row, column=col, padx=10, pady=10, sticky="ew")
            col += 1
            if col > 1:
                col = 0
                row += 1

        # ---- Botón Cerrar Sesión en la parte inferior ----
        bottom_frame = ttk.Frame(right_frame)
        bottom_frame.pack(fill=tk.X, pady=(20, 0))
        ttk.Button(
            bottom_frame,
            text="🚪 Cerrar Sesión",
            width=20,
            style='Menu.TButton',
            command=self.cerrar_sesion
        ).pack(anchor=tk.CENTER, ipady=5)

        # Ajustar que las columnas se expandan
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
                
    def obtener_nombre_usuario(self):
        """
        Obtiene el nombre del usuario actual de la sesión.
        Si no se puede obtener, retorna el rol como nombre.
        """
        try:
            if hasattr(self, 'username'):
                return self.username
            else:
                # Si no tenemos el username guardado, usar el rol
                return self.user_role.capitalize()
        except:
            return self.user_role.capitalize()

    def actualizar_contadores(self):
        """Actualiza los contadores en la barra superior (Afiliados - Retiros - Total)"""
        total_afiliados = len(self.data)
        total_retiros = len(self.retiros_data)
        total_general = total_afiliados + total_retiros

        self.contador_afiliados.set(f"Afiliados: {total_afiliados}")
        self.contador_retiros.set(f"Retiros: {total_retiros}")
        self.contador_total.set(f"Total: {total_general}")

        # Programar próxima actualización (cada 1 segundo)
        self.root.after(1000, self.actualizar_contadores)
    
    def setup_afiliados_interface(self):
        """Configura la interfaz de afiliados activos"""
        # Frame principal
        main_frame = ttk.Frame(self.afiliados_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Título
        ttk.Label(main_frame, text="Afiliados Activos", style='Title.TLabel').pack(pady=(0, 20))
        
        # Controles superiores
        self.setup_search_controls(main_frame, self.buscar_afiliados)
        
        # Tabla de registros
        self.setup_afiliados_table(main_frame)
        
        # ========== AGREGAR MENÚ CONTEXTUAL ==========
        self.tree.bind("<Button-3>", lambda e: self.mostrar_menu_contextual(e, self.tree, 'activos'))
        # =============================================
        
        # Controles inferiores
        self.setup_afiliados_bottom_controls(main_frame)
        
        # ========== AGREGAR BINDING DE PEGADO EN BÚSQUEDA ==========
        # Buscar el Entry de búsqueda para añadir el binding de pegado
        for child in main_frame.winfo_children():
            if isinstance(child, ttk.Frame):
                for subchild in child.winfo_children():
                    if isinstance(subchild, ttk.Entry) and subchild['textvariable'] == self.busqueda_var:
                        subchild.bind('<<Paste>>', lambda e: self.root.after(50, self.buscar_afiliados))
                        break
        # ==========================================================  
    
    def generar_ventana_qr(self, cedula, nombre=""):
        """Genera y muestra una ventana con el código QR de la cédula dada,
        con opción de descarga."""
        if not cedula:
            messagebox.showerror("Error", "Cédula no válida")
            return

        # Crear el código QR (vista previa)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=8,
            border=4,
        )
        qr.add_data(cedula)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        img_qr = img_qr.resize((300, 300), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img_qr)

        # Ventana emergente
        ventana = Toplevel(self.root)
        ventana.title("Código QR de acceso")
        ventana.geometry("400x600")
        self.centrar_ventana(ventana, 400, 600)
        ventana.resizable(False, False)

        ttk.Label(ventana, text="Código QR para acceso rápido",
                font=('Segoe UI', 14, 'bold')).pack(pady=10)
        if nombre:
            ttk.Label(ventana, text=f"Afiliado: {nombre}",
                    font=('Segoe UI', 12)).pack(pady=5)

        label_img = ttk.Label(ventana, image=photo)
        label_img.image = photo  # mantener referencia
        label_img.pack(pady=10)

        ttk.Label(ventana, text=f"Cédula: {cedula}",
                font=('Segoe UI', 10, 'bold')).pack(pady=5)
        ttk.Label(ventana, text="Escanea este código desde tu teléfono",
                font=('Segoe UI', 9), foreground='gray').pack()

        # ============ BOTÓN DE DESCARGA ============
        def descargar_qr():
            nombre_archivo = f"Qr{cedula}.png"
            try:
                documentos = os.path.join(os.path.expanduser("~"), "Documents")
                if not os.path.exists(documentos):
                    documentos = os.path.expanduser("~")
            except Exception:
                documentos = os.getcwd()

            ruta = filedialog.asksaveasfilename(
                title="Guardar código QR",
                defaultextension=".png",
                initialfile=nombre_archivo,
                initialdir=documentos,
                filetypes=[("Imagen PNG", "*.png"), ("Todos los archivos", "*.*")]
            )
            if not ruta:
                return

            try:
                # Regenerar a mayor resolución para la descarga
                qr_descarga = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=12,
                    border=4,
                )
                qr_descarga.add_data(cedula)
                qr_descarga.make(fit=True)
                img_descarga = qr_descarga.make_image(
                    fill_color="black", back_color="white"
                ).convert('RGB')
                img_descarga.save(ruta, "PNG")

                messagebox.showinfo("Descarga exitosa",
                                    f"Código QR guardado en:\n{ruta}")

                if messagebox.askyesno("Abrir ubicación",
                                    "¿Desea abrir la carpeta donde se guardó el QR?"):
                    carpeta = os.path.dirname(ruta)
                    try:
                        if sys.platform == "win32":
                            os.startfile(carpeta)
                        elif sys.platform == "darwin":
                            subprocess.Popen(["open", carpeta])
                        else:
                            subprocess.Popen(["xdg-open", carpeta])
                    except Exception:
                        pass
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar el QR:\n{str(e)}")
        # ============================================

        btn_frame = ttk.Frame(ventana)
        btn_frame.pack(pady=15)

        ttk.Button(btn_frame, text="💾 Descargar QR",
                command=descargar_qr).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cerrar",
                command=ventana.destroy).pack(side=tk.LEFT, padx=5)
            
    def setup_search_controls(self, parent, search_command):
        """Configura los controles de búsqueda"""
        top_controls_frame = ttk.Frame(parent)
        top_controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(top_controls_frame, text="Buscar:").pack(side=tk.LEFT, padx=5)
        busqueda_entry = ttk.Entry(top_controls_frame, textvariable=self.busqueda_var, width=60)
        busqueda_entry.pack(side=tk.LEFT, padx=5)
        busqueda_entry.bind('<KeyRelease>', search_command)
        
        ttk.Button(top_controls_frame, text="Mostrar Todos", 
                  command=self.update_afiliados_table).pack(side=tk.LEFT, padx=5)
    
    def setup_afiliados_table(self, parent):
        """Configura la tabla de afiliados"""
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("CC", "Nombre", "Celular", "EPS", "ARL", "Pensión", "Caja", "Valor", "Fecha Pago", "Estado Pago")
        
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended")
        
        # Configurar columnas
        column_widths = {
            "CC": 80, "Nombre": 150, "Celular": 80, "EPS": 120, 
            "ARL": 80, "Pensión": 100, "Caja": 120, 
            "Valor": 80, "Fecha Pago": 90
        }
        
        for col in columns:
            self.tree.column(col, width=column_widths.get(col, 100), anchor=tk.CENTER)
            self.tree.heading(col, text=col)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.drop_target_register(DND_FILES)
        self.tree.dnd_bind('<<Drop>>', self.on_drop_afiliado)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
    
    def on_drop_afiliado(self, event):
        """Maneja el evento de soltar archivos en el Treeview de afiliados."""
        archivos = event.data.split()
        if not archivos:
            return

        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Sin selección", "Seleccione un afiliado para asociar los archivos.")
            return

        cc = selected[0]
        carpeta_destino = os.path.join(BASE_PATH, "Documentos", cc)
        os.makedirs(carpeta_destino, exist_ok=True)

        archivos_copiados = 0
        for ruta in archivos:
            ruta = ruta.strip('{}')
            if os.path.isfile(ruta):
                try:
                    shutil.copy2(ruta, carpeta_destino)
                    archivos_copiados += 1
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo copiar {os.path.basename(ruta)}:\n{str(e)}")

        if archivos_copiados > 0:
            messagebox.showinfo("Éxito", f"Se copiaron {archivos_copiados} archivo(s) a la carpeta del afiliado.")

    def on_drop_documentos_afiliado(self, event, cedula, treeview=None):
        """Maneja el drop de archivos en el panel de documentos de un afiliado."""
        archivos = event.data.split()
        if not archivos:
            return

        carpeta_destino = os.path.join(BASE_PATH, "Documentos", cedula)
        os.makedirs(carpeta_destino, exist_ok=True)

        archivos_copiados = 0
        for ruta in archivos:
            ruta = ruta.strip('{}')
            if os.path.isfile(ruta):
                try:
                    shutil.copy2(ruta, carpeta_destino)
                    archivos_copiados += 1
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo copiar {os.path.basename(ruta)}:\n{str(e)}")

        if archivos_copiados > 0 and treeview:
            self._actualizar_lista_documentos_afiliado(cedula, treeview)
            messagebox.showinfo("Éxito", f"Se copiaron {archivos_copiados} archivo(s) a la carpeta del afiliado.")

    def on_drop_incapacidad(self, event):
        """Maneja el drop de archivos en la tabla de incapacidades."""
        archivos = event.data.split()
        if not archivos:
            return

        selected = self.incapacidades_tree.selection()
        if not selected:
            messagebox.showwarning("Sin selección", "Seleccione una incapacidad para asociar los archivos.")
            return

        index = self.incapacidades_tree.index(selected[0])
        if index >= len(self.contabilidad_data['incapacidades']):
            return

        registro = self.contabilidad_data['incapacidades'][index]
        cc = registro.get('cedula', registro.get('cc', ''))
        id_incap = registro.get('id')

        if not cc or not id_incap:
            messagebox.showerror("Error", "No se puede identificar la carpeta de la incapacidad.")
            return

        carpeta_destino = os.path.join(BASE_PATH, "Incapacidades", cc, str(id_incap))
        os.makedirs(carpeta_destino, exist_ok=True)

        archivos_copiados = 0
        for ruta in archivos:
            ruta = ruta.strip('{}')
            if os.path.isfile(ruta):
                try:
                    shutil.copy2(ruta, carpeta_destino)
                    archivos_copiados += 1
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo copiar {os.path.basename(ruta)}:\n{str(e)}")

        if archivos_copiados > 0:
            messagebox.showinfo("Éxito", f"Se copiaron {archivos_copiados} archivo(s) a la carpeta de la incapacidad.")

    def on_drop_beneficiario(self, event):
        """Maneja el drop de archivos en la tabla de beneficiarios."""
        archivos = event.data.split()
        if not archivos:
            return

        selected = self.tree_benef.selection()
        if not selected:
            messagebox.showwarning("Sin selección", "Seleccione un beneficiario para asociar los archivos.")
            return

        id_benef = int(selected[0])
        benef = next((b for b in self.beneficiarios_list if b['id'] == id_benef), None)
        if not benef:
            messagebox.showerror("Error", "Beneficiario no encontrado.")
            return

        nombre_limpio = "".join(c for c in benef['nombre'] if c.isalnum() or c in " ._-").strip()
        if not nombre_limpio:
            nombre_limpio = "Sin_nombre"

        cc_cotizante = self.cc_var.get().strip()
        carpeta_destino = os.path.join(BASE_PATH, "Documentos", cc_cotizante, "Beneficiarios", nombre_limpio)
        os.makedirs(carpeta_destino, exist_ok=True)

        archivos_copiados = 0
        for ruta in archivos:
            ruta = ruta.strip('{}')
            if os.path.isfile(ruta):
                try:
                    shutil.copy2(ruta, carpeta_destino)
                    archivos_copiados += 1
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo copiar {os.path.basename(ruta)}:\n{str(e)}")

        if archivos_copiados > 0:
            # Actualizar la lista de documentos en la ventana de detalles si está abierta
            for child in self.tab_benef.winfo_children():
                if isinstance(child, ttk.Treeview):
                    self.actualizar_lista_documentos_beneficiario(cc_cotizante, benef['nombre'], child)
                    break
            messagebox.showinfo("Éxito", f"Se copiaron {archivos_copiados} archivo(s) a la carpeta del beneficiario.")

    def setup_afiliados_bottom_controls(self, parent):
        """Configura los controles inferiores de afiliados"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Frame(button_frame).pack(side=tk.LEFT, expand=True, fill=tk.X)

        # Botón de importación masiva (Administrativo y Auxiliar)
        if self.user_role in ("Administrativo", "Auxiliar"):
            ttk.Button(button_frame, text="📂 Importar Excel/CSV",
                    command=self.importar_afiliados).pack(side=tk.RIGHT, padx=5)

        # Botones exclusivos de Administrativo
        if self.user_role == "Administrativo":
            ttk.Button(button_frame, text="➖Retirar", command=self.retirar_afiliados).pack(side=tk.RIGHT, padx=5)

        # Botones para Administrativo y Auxiliar
        if self.user_role in ("Administrativo", "Auxiliar"):
            ttk.Button(button_frame, text="📦Archivar", command=self.archivar_afiliado).pack(side=tk.RIGHT, padx=5)
            ttk.Button(button_frame, text="✏️Editar", command=self.editar_afiliado).pack(side=tk.RIGHT, padx=5)

        # Agregar: todos los roles que usan esta pantalla (Administrativo y Auxiliar)
        ttk.Button(button_frame, text="➕Agregar", command=self.show_afiliado_form).pack(side=tk.RIGHT, padx=5)
                
    def setup_retiros_interface(self):
        """Configura la interfaz de retiros con opción de mostrar archivados."""
        main_frame = ttk.Frame(self.retiros_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text="Historial de Retiros", style='Title.TLabel').pack(pady=(0, 20))

        # ========== CONTROLES SUPERIORES (búsqueda + checkbox) ==========
        top_controls = ttk.Frame(main_frame)
        top_controls.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(top_controls, text="Buscar:").pack(side=tk.LEFT, padx=5)
        # Reutilizamos la variable de búsqueda existente (self.busqueda_var)
        busqueda_entry = ttk.Entry(top_controls, textvariable=self.busqueda_var, width=40)
        busqueda_entry.pack(side=tk.LEFT, padx=5)
        busqueda_entry.bind('<KeyRelease>', self.buscar_retiros)

        ttk.Button(top_controls, text="Mostrar Todos",
                command=self.update_retiros_table).pack(side=tk.LEFT, padx=5)

        # Checkbox "Mostrar archivados"
        self.mostrar_archivados_var = tk.BooleanVar(value=False)
        chk = ttk.Checkbutton(top_controls, text="Mostrar archivados",
                            variable=self.mostrar_archivados_var,
                            command=self.update_retiros_table)
        chk.pack(side=tk.LEFT, padx=10)

        # ========== TABLA DE RETIROS ==========
        self.setup_retiros_table(main_frame)

        # Menú contextual (clic derecho)
        self.retiros_tree.bind("<Button-3>", lambda e: self.mostrar_menu_contextual(e, self.retiros_tree, 'retiros'))

        # ========== BOTONES INFERIORES ==========
        self.setup_retiros_bottom_controls(main_frame)
    
    def setup_retiros_table(self, parent):
        """Configura la tabla de retiros"""
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("CC", "Nombre", "Celular", "EPS", "ARL", "Pensión", "Caja", "Valor", "Fecha Pago", "Fecha Retiro", "Motivo", "Estado Pago")

        self.retiros_tree = ttk.Treeview(table_frame, columns=columns, show="headings")

        # Configurar columnas
        column_widths = {
            "CC": 80, "Nombre": 150, "Celular": 80, "EPS": 120,
            "ARL": 80, "Pensión": 100, "Caja": 120, "Mes Pago": 80,
            "Valor": 80, "Método Pago": 100, "Fecha Pago": 90, "Fecha Retiro": 90, "Motivo": 120  # <-- NUEVO
        }

        for col in columns:
            self.retiros_tree.column(col, width=column_widths.get(col, 100), anchor=tk.CENTER)
            self.retiros_tree.heading(col, text=col)

        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.retiros_tree.yview)
        self.retiros_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.retiros_tree.pack(fill=tk.BOTH, expand=True)
    
    def setup_retiros_bottom_controls(self, parent):
        """Configura los controles inferiores de la pestaña Retiros."""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # Contenedor para alinear los botones a la derecha
        btn_container = ttk.Frame(button_frame)
        btn_container.pack(side=tk.RIGHT)

        # ========== BOTONES PARA Administrativo ==========
        if self.user_role == "Administrativo":
            # Reactivar afiliados seleccionados
            ttk.Button(btn_container, text="↩️Reactivar",
                    command=self.reactivar_afiliados).pack(side=tk.LEFT, padx=5)

            # Actualizar estados de pago
            ttk.Button(btn_container, text="🔄Actualizar",
                    command=self.actualizar_estados_pago).pack(side=tk.LEFT, padx=5)

            # Archivar retirados seleccionados (mover a tabla archivados)
            ttk.Button(btn_container, text="📦 Archivar",
                    command=self.archivar_retirados).pack(side=tk.LEFT, padx=5)

            # Eliminar definitivamente (borrado físico, solo para retirados NO archivados)
            #ttk.Button(btn_container, text="❌ Eliminar Definitivamente",
            #        command=self.eliminar_definitivo_retirado).pack(side=tk.LEFT, padx=5)

        # ========== BOTONES COMUNES (todos los roles) ==========
        # Compartir datos (WhatsApp / Gmail)
        #ttk.Button(btn_container, text="📤Compartir",
        #        command=self.mostrar_opciones_compartir).pack(side=tk.LEFT, padx=5)

        # Exportar a Excel
        ttk.Button(btn_container, text="♻️Exportar a Excel",
                command=self.exportar_a_excel).pack(side=tk.LEFT, padx=5)
        
    def seleccionar_motivo_retiro(self):
        """Muestra un diálogo para elegir el motivo de retiro. Retorna el motivo o None si se cancela."""
        opciones = ["Cambio de EPS", "Traslado", "Fallecimiento", "Voluntario", "Mora", "Otro"]
        ventana = Toplevel(self.root)
        ventana.title("Motivo de retiro")
        ventana.geometry("400x150")
        self.centrar_ventana(ventana, 400, 150)
        ventana.resizable(False, False)
        ventana.transient(self.root)
        ventana.grab_set()

        ttk.Label(ventana, text="Seleccione el motivo del retiro:", font=('Arial', 11)).pack(pady=10)
        motivo_var = tk.StringVar()
        combo = ttk.Combobox(ventana, textvariable=motivo_var, values=opciones, state="readonly", width=30)
        combo.pack(pady=5)
        combo.focus_set()

        resultado = [None]

        def aceptar():
            if motivo_var.get():
                resultado[0] = motivo_var.get()
                ventana.destroy()
            else:
                messagebox.showerror("Error", "Debe seleccionar un motivo.")

        def cancelar():
            ventana.destroy()

        btn_frame = ttk.Frame(ventana)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Cancelar", command=cancelar).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Aceptar", command=aceptar).pack(side=tk.LEFT, padx=10)

        ventana.wait_window()
        return resultado[0]

    def mostrar_opciones_compartir(self):
        """Muestra una ventana emergente con opciones para compartir"""
        share_window = Toplevel(self.root)
        share_window.title("Compartir Datos")
        share_window.geometry("300x150")
        share_window.resizable(False, False)
        
        # Centrar la ventana
        window_width = 300
        window_height = 150
        screen_width = share_window.winfo_screenwidth()
        screen_height = share_window.winfo_screenheight()
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        share_window.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        
        ttk.Label(share_window, text="Seleccione cómo compartir:", style='Title.TLabel').pack(pady=10)
        
        # Botón para WhatsApp
        whatsapp_btn = ttk.Button(share_window, text="WhatsApp", 
                                command=lambda: self.compartir_por_whatsapp(share_window))
        whatsapp_btn.pack(pady=5, fill=tk.X, padx=20)
        
        # Botón para Gmail
        gmail_btn = ttk.Button(share_window, text="Gmail", 
                            command=lambda: self.compartir_por_gmail(share_window))
        gmail_btn.pack(pady=5, fill=tk.X, padx=20)

    def compartir_por_whatsapp(self, ventana):
        """Abre WhatsApp para compartir el archivo"""
        try:
            # Primero exportamos el archivo
            self.exportar_a_excel()
            
            # Obtener la ruta del archivo más reciente
            base_retiros_path = os.path.join(BASE_PATH, "BaseRetiros")
            archivos = os.listdir(base_retiros_path)
            if archivos:
                archivo_reciente = max(archivos, key=lambda x: os.path.getmtime(os.path.join(base_retiros_path, x)))
                archivo_path = os.path.join(base_retiros_path, archivo_reciente)
                
                # Usar el protocolo whatsapp para compartir (esto puede variar según el sistema operativo)
                if sys.platform == "win32":
                    os.startfile(f"whatsapp://send?text=Adjunto archivo de retiros: {archivo_reciente}")
                else:
                    webbrowser.open(f"https://web.whatsapp.com/")
                
                messagebox.showinfo("WhatsApp", f"Archivo {archivo_reciente} listo para compartir en WhatsApp")
            else:
                messagebox.showerror("Error", "No se encontraron archivos para compartir")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir WhatsApp: {str(e)}")
        finally:
            ventana.destroy()

    def compartir_por_gmail(self, ventana):
        """Abre Gmail para compartir el archivo con un mensaje profesional"""
        try:
            # Primero exportamos el archivo
            self.exportar_a_excel()
            
            # Obtener la ruta del archivo más reciente
            base_retiros_path = os.path.join(BASE_PATH, "BaseRetiros")
            archivos = os.listdir(base_retiros_path)
            
            if not archivos:
                messagebox.showerror("Error", "No se encontraron archivos para compartir")
                ventana.destroy()
                return
                
            archivo_reciente = max(archivos, key=lambda x: os.path.getmtime(os.path.join(base_retiros_path, x)))
            archivo_path = os.path.join(base_retiros_path, archivo_reciente)
            
            # Obtener información de fechas y cantidad de retiros
            fecha_actual = datetime.now().strftime("%d/%m/%Y")
            total_retiros = len(self.retiros_data)
            
            # Determinar rango de fechas si hay datos
            if self.retiros_data:
                fechas = [datetime.strptime(r['fecha_retiro'], "%Y-%m-%d") for r in self.retiros_data if 'fecha_retiro' in r]
                if fechas:
                    fecha_min = min(fechas).strftime("%d/%m/%Y")
                    fecha_max = max(fechas).strftime("%d/%m/%Y")
                    rango_fechas = f"el período comprendido entre {fecha_min} y {fecha_max}"
                else:
                    rango_fechas = f"el día {fecha_actual}"
            else:
                rango_fechas = f"el día {fecha_actual}"
            
            # Construir el mensaje profesional
            mensaje = (
                f"Estimado/a Supervisor o a quien corresponda:\n\n"
                f"Por medio de la presente, le informo el detalle de los retiros realizados durante el período comprendido entre {rango_fechas}.\n\n"
                f"Resumen de Retiros:\n"
                f"Total de retiros: {total_retiros}\n\n"
                f"Adjunto encontrarás el reporte detallado en formato Excel.\n\n"
                f"Quedo atento a cualquier observación o requerimiento adicional.\n\n"
                f"Saludos cordiales,\n\n"
                f"R.A.V \n"
                f"Coordinador de Operaciones\n"
                f"3022386236\n"
                f"Sistema SaluPago"
            )

            
            # Configurar parámetros de Gmail
            correo_destino = "andresberri15@gmail.com"
            asunto = f"Reporte de Retiros - {fecha_actual}"
            
            # Construir URL de Gmail con parámetros
            url_gmail = (
                f"https://mail.google.com/mail/?view=cm&fs=1"
                f"&to={correo_destino}"
                f"&su={urllib.parse.quote(asunto)}"
                f"&body={urllib.parse.quote(mensaje)}"
            )
            
            # Abrir Gmail en el navegador con los parámetros
            webbrowser.open(url_gmail)
            
            messagebox.showinfo("Gmail", 
                            f"Correo preparado para:\n"
                            f"Destino: {correo_destino}\n"
                            f"Asunto: {asunto}\n"
                            f"Total retiros: {total_retiros}\n"
                            f"Archivo: {archivo_reciente}")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir Gmail: {str(e)}")
        finally:
            ventana.destroy()
    
    def importar_afiliados(self):
        """
        Abre un diálogo para seleccionar un archivo Excel/CSV y procesa la carga masiva.
        """
        if self.user_role not in ("Administrativo", "Auxiliar"):
            messagebox.showerror("Error", "No tiene permisos para importar afiliados.")
            return

        from tkinter import filedialog
        archivo = filedialog.askopenfilename(
            title="Seleccionar archivo de afiliados",
            filetypes=[("Archivos Excel", "*.xlsx *.xls"), ("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
        )
        if not archivo:
            return

        try:
            if archivo.endswith('.csv'):
                df = pd.read_csv(archivo, encoding='utf-8')
            else:
                df = pd.read_excel(archivo, engine='openpyxl')
        except Exception as e:
            messagebox.showerror("Error al leer", f"No se pudo leer el archivo:\n{str(e)}")
            return

        if df.empty:
            messagebox.showwarning("Archivo vacío", "El archivo seleccionado no contiene datos.")
            return

        self.mostrar_previsualizacion_importacion(df)
    
    def mostrar_previsualizacion_importacion(self, df):
        """
        Muestra una ventana con la previsualización de los datos, mapeo de columnas,
        opciones de duplicados y campos para datos faltantes (Dirección, Correo, Fecha Ingreso, Método Pago).
        """
        # Limpiar nombres de columnas (espacios, mayúsculas)
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

        # Mapeo automático de columnas comunes
        mapa_automatico = {
            'cc': ['cc', 'cedula', 'documento', 'identificacion', 'id'],
            'nombre': ['nombre', 'nombres', 'nombre_completo', 'full_name'],
            'celular': ['celular', 'telefono', 'movil', 'phone'],
            'direccion': ['direccion', 'dirección', 'address'],
            'correo': ['correo', 'email', 'mail', 'correo_electronico'],
            'fecha_ingreso': ['fecha_ingreso', 'fechaIngreso', 'ingreso'],
            'eps': ['eps', 'epss'],
            'arl': ['arl'],
            'pension': ['pension', 'pensión', 'fondo_pension'],
            'caja_compensacion': ['caja_compensacion', 'caja_compensación', 'caja_comp', 'caja'],
            'mes_pago': ['mes_pago', 'mes_pagado', 'mes'],
            'valor_pagado': ['valor_pagado', 'valor', 'valor_pagado', 'monto'],
            'metodo_pago': ['metodo_pago', 'método_pago', 'metodo', 'forma_pago'],
            'fecha_pago': ['fecha_pago', 'fecha_pagado', 'pago_fecha']
        }

        # Construir diccionario de mapeo sugerido
        sugerencia = {}
        for col in df.columns:
            for campo, sinonimos in mapa_automatico.items():
                if col in sinonimos:
                    sugerencia[col] = campo
                    break
            if col not in sugerencia:
                sugerencia[col] = None  # sin mapeo

        # ============================================================
        # VENTANA MÁS BAJA  →  1100x580 (antes 1100x710)
        # ============================================================
        ventana = Toplevel(self.root)
        ventana.title("Previsualización de importación")
        ventana.geometry("1100x580")
        self.centrar_ventana(ventana, 1100, 580)
        ventana.resizable(True, True)

        main_frame = ttk.Frame(ventana, padding=8)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Previsualización de datos a importar",
                style='Title.TLabel').pack(pady=(0, 6))

        # ---------- Frame superior: mapeo de columnas ----------
        mapeo_frame = ttk.LabelFrame(
            main_frame,
            text="Mapeo de columnas (selecciona el campo correspondiente)",
            padding=8
        )
        mapeo_frame.pack(fill=tk.X, pady=4)

        mapa_vars = {}
        for i, col in enumerate(df.columns):
            ttk.Label(mapeo_frame, text=f"{col}:").grid(
                row=i // 4, column=(i % 4) * 2, sticky=tk.W, padx=5, pady=2)
            var = tk.StringVar(value=sugerencia.get(col, ""))
            mapa_vars[col] = var
            combo = ttk.Combobox(
                mapeo_frame, textvariable=var,
                values=[""] + list(mapa_automatico.keys()),
                state="readonly", width=15
            )
            combo.grid(row=i // 4, column=(i % 4) * 2 + 1,
                    sticky=tk.W, padx=5, pady=2)

        # ============================================================
        # TABLA DE PREVISUALIZACIÓN  →  height=4  (antes 8)
        # ============================================================
        preview_frame = ttk.LabelFrame(
            main_frame, text="Vista previa (10 primeras filas)", padding=6
        )
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=4)

        # height=4 muestra sólo 4 filas visibles (con scroll interno para las 10)
        tree = ttk.Treeview(preview_frame, show="headings", height=4)
        vsb = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=tree.yview)
        hsb = ttk.Scrollbar(preview_frame, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        columnas_df = df.columns.tolist()
        tree["columns"] = columnas_df
        for col in columnas_df:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor=tk.CENTER)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        preview_frame.grid_rowconfigure(0, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)

        def formatear_valor(val):
            if val is None:
                return ""
            if hasattr(val, 'strftime'):
                return val.strftime("%Y-%m-%d")
            if isinstance(val, float) and math.isnan(val):
                return ""
            if isinstance(val, (int, float)):
                if isinstance(val, int) or val.is_integer():
                    return str(int(val))
                return f"{val:.2f}"
            return str(val).strip()

        # Insertamos las 10 filas, pero la tabla muestra solo 4 (el resto con scroll)
        for _, row in df.head(10).iterrows():
            tree.insert("", tk.END, values=[formatear_valor(v) for v in row])

        # ---------- Opciones de duplicados ----------
        opciones_frame = ttk.Frame(main_frame)
        opciones_frame.pack(fill=tk.X, pady=6)

        ttk.Label(opciones_frame, text="Si un afiliado ya existe:").pack(side=tk.LEFT, padx=5)
        duplicado_var = tk.StringVar(value="saltar")
        ttk.Radiobutton(opciones_frame, text="Saltar (no importar)",
                        variable=duplicado_var, value="saltar").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(opciones_frame, text="Sobrescribir",
                        variable=duplicado_var, value="sobrescribir").pack(side=tk.LEFT, padx=5)

        # ---------- Campos para datos faltantes ----------
        datos_faltantes_frame = ttk.LabelFrame(
            main_frame,
            text="Datos faltantes (se aplicarán a todos los registros si no vienen en el archivo)",
            padding=8
        )
        datos_faltantes_frame.pack(fill=tk.X, pady=4)

        direccion_global_var = tk.StringVar(value="")
        correo_global_var = tk.StringVar(value="")
        fecha_ingreso_global_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        metodo_pago_global_var = tk.StringVar(
            value=self.metodos_pago[0] if self.metodos_pago else ""
        )

        row_frame = ttk.Frame(datos_faltantes_frame)
        row_frame.pack(fill=tk.X, pady=4)

        ttk.Label(row_frame, text="Dirección:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(row_frame, textvariable=direccion_global_var, width=20).pack(side=tk.LEFT, padx=5)

        ttk.Label(row_frame, text="Correo Electrónico:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(row_frame, textvariable=correo_global_var, width=20).pack(side=tk.LEFT, padx=5)

        ttk.Label(row_frame, text="Fecha Ingreso:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(row_frame, textvariable=fecha_ingreso_global_var, width=15).pack(side=tk.LEFT, padx=5)

        ttk.Label(row_frame, text="Método de Pago:").pack(side=tk.LEFT, padx=5)
        ttk.Combobox(row_frame, textvariable=metodo_pago_global_var,
                    values=self.metodos_pago, state="readonly",
                    width=15).pack(side=tk.LEFT, padx=5)

        # ---------- Botones de acción ----------
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=6)

        ttk.Button(btn_frame, text="Cancelar",
                command=ventana.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Confirmar importación",
                command=lambda: self.confirmar_importacion(
                    df, mapa_vars, duplicado_var.get(), ventana,
                    direccion_global_var.get(), correo_global_var.get(),
                    fecha_ingreso_global_var.get(), metodo_pago_global_var.get()
                ),
                style='Accent.TButton').pack(side=tk.RIGHT, padx=5)

        ventana.tree = tree
                
    def confirmar_importacion(self, df, mapa_vars, opcion_duplicados, ventana_previa,
                            direccion_global="", correo_global="",
                            fecha_ingreso_global="", metodo_pago_global=""):
        """
        Procesa la importación según el mapeo seleccionado, la opción de duplicados
        y los valores globales para campos faltantes.
        """

        # ============================================================
        # 1) CONFIRMACIÓN PREVIA (modal a la ventana de previsualización)
        # ============================================================
        total_filas = len(df)
        texto_dup = "Saltar duplicados" if opcion_duplicados == "saltar" else "Sobrescribir duplicados"

        try:
            respuesta = messagebox.askyesno(
                "Confirmar importación",
                f"¿Está seguro de importar {total_filas} registro(s)?\n\n"
                f"Modo de duplicados: {texto_dup}\n\n"
                f"Esta acción modificará la base de datos de afiliados.",
                parent=ventana_previa
            )
        except Exception:
            respuesta = False

        if not respuesta:
            return

        try:
            ventana_previa.destroy()
        except Exception:
            pass

        # ============================================================
        # 2) CONSTRUIR MAPEO FINAL
        # ============================================================
        mapeo_final = {}
        for col, var in mapa_vars.items():
            campo = var.get().strip()
            if campo:
                mapeo_final[col] = campo

        if 'cc' not in mapeo_final.values() or 'nombre' not in mapeo_final.values():
            messagebox.showerror(
                "Error",
                "Debe mapear al menos las columnas 'cc' (cédula) y 'nombre'."
            )
            return

        inverso = {v: k for k, v in mapeo_final.items()}

        estadisticas = {
            "exitosos": 0,
            "duplicados_saltados": 0,
            "sobrescritos": 0,
            "errores": 0,
            "detalles_error": []
        }

        # ============================================================
        # 3) PROCESAR CADA FILA
        # ============================================================
        for idx, row in df.iterrows():
            try:
                cc = self._obtener_valor(row, inverso, 'cc')
                nombre = self._obtener_valor(row, inverso, 'nombre')
                celular = self._obtener_valor(row, inverso, 'celular')
                direccion = self._obtener_valor(row, inverso, 'direccion') or direccion_global
                correo = self._obtener_valor(row, inverso, 'correo') or correo_global
                fecha_ingreso = self._obtener_valor(row, inverso, 'fecha_ingreso') or fecha_ingreso_global
                eps = self._obtener_valor(row, inverso, 'eps')
                arl = self._obtener_valor(row, inverso, 'arl')
                pension = self._obtener_valor(row, inverso, 'pension')
                caja_compensacion = self._obtener_valor(row, inverso, 'caja_compensacion')
                mes_pago = self._obtener_valor(row, inverso, 'mes_pago')
                valor_pagado = self._obtener_valor(row, inverso, 'valor_pagado')
                metodo_pago = self._obtener_valor(row, inverso, 'metodo_pago') or metodo_pago_global
                fecha_pago = self._obtener_valor(row, inverso, 'fecha_pago')

                datos_validados, errores = self._validar_fila_afiliado(
                    cc, nombre, celular, direccion, correo, fecha_ingreso,
                    eps, arl, pension, caja_compensacion, mes_pago,
                    valor_pagado, metodo_pago, fecha_pago
                )

                if errores:
                    estadisticas["errores"] += 1
                    estadisticas["detalles_error"].append(f"Fila {idx+1}: {', '.join(errores)}")
                    continue

                existe = self.db.afiliado_exists(datos_validados['cc'])

                if existe:
                    if opcion_duplicados == "saltar":
                        estadisticas["duplicados_saltados"] += 1
                        continue
                    else:
                        self.db.update_afiliado(datos_validados['cc'], datos_validados)
                        for i, af in enumerate(self.data):
                            if af['cc'] == datos_validados['cc']:
                                self.data[i] = datos_validados
                                break
                        else:
                            for i, af in enumerate(self.retiros_data):
                                if af['cc'] == datos_validados['cc']:
                                    self.db.reactivar_afiliado(datos_validados['cc'])
                                    self.data.append(datos_validados)
                                    del self.retiros_data[i]
                                    break
                        estadisticas["sobrescritos"] += 1
                else:
                    self.db.add_afiliado(datos_validados)
                    self.data.append(datos_validados)
                    estadisticas["exitosos"] += 1

                self.actualizar_monitoreo_afiliado(datos_validados['cc'])

            except Exception as e:
                estadisticas["errores"] += 1
                estadisticas["detalles_error"].append(f"Fila {idx+1}: Error inesperado: {str(e)}")

        # ============================================================
        # 4) REFRESCAR TABLAS
        # ============================================================
        self.update_afiliados_table()
        self.update_retiros_table()
        self.update_monitoreo_table()
        self.update_ingresos_table()
        self.calcular_totales_contabilidad()
        
        # CORRECCIÓN: Solo actualizar caja si el rol tiene acceso a ella (Administrativo)
        if self.user_role == "Administrativo":
            self.hacer_caja()

        # ============================================================
        # 5) MOSTRAR RESUMEN
        # ============================================================
        self._mostrar_resumen_importacion(estadisticas)

        # ============================================================
        # 6) AUDITORÍA (Se registra siempre, sin importar el rol)
        # ============================================================
        self._registrar_auditoria(
            "Importación masiva de afiliados",
            "Afiliados",
            "Éxito" if estadisticas["errores"] == 0 else "Parcial",
            f"Exitosos: {estadisticas['exitosos']}, "
            f"Sobrescritos: {estadisticas['sobrescritos']}, "
            f"Saltados: {estadisticas['duplicados_saltados']}, "
            f"Errores: {estadisticas['errores']}"
        )

    def _obtener_valor(self, row, inverso, campo):
        """
        Obtiene el valor de una fila según el mapeo inverso.
        Si el valor es un Timestamp de pandas, lo convierte a string en formato YYYY-MM-DD.
        """
        if campo in inverso:
            col = inverso[campo]
            val = row.get(col)
            if val is None:
                return ""
            # Si es un Timestamp de pandas, extraer solo la fecha
            if hasattr(val, 'strftime'):
                return val.strftime("%Y-%m-%d")
            if isinstance(val, float) and math.isnan(val):
                return ""
            return str(val).strip()
        return ""
    
    def _validar_fila_afiliado(self, cc, nombre, celular, direccion, correo, fecha_ingreso,
                            eps, arl, pension, caja_compensacion, mes_pago, valor_pagado, metodo_pago, fecha_pago):
        """
        Valida los datos de una fila y retorna un diccionario con los datos limpios y una lista de errores.
        Soporta fechas en formato YYYY-MM-DD, DD/MM/YYYY, YYYY-MM-DD HH:MM:SS, etc.
        """
        errores = []
        datos = {}

        # Limpiar cédula (solo dígitos)
        cc_limpio = re.sub(r'[^0-9]', '', cc)
        if not cc_limpio or not validar_cedula(cc_limpio):
            errores.append("Cédula inválida (debe tener 8-10 dígitos)")
        else:
            datos['cc'] = cc_limpio

        # Nombre
        if not nombre:
            errores.append("Nombre es obligatorio")
        else:
            datos['nombre'] = nombre.strip()

        # Celular (opcional)
        if celular:
            celular_limpio = re.sub(r'[^0-9]', '', celular)
            if not validar_celular(celular_limpio):
                errores.append("Celular no válido (debe ser 10 dígitos empezando con 3)")
            else:
                datos['celular'] = celular_limpio
        else:
            datos['celular'] = ""

        # Dirección (opcional)
        datos['direccion'] = direccion.strip() if direccion else ""

        # Correo (opcional)
        if correo:
            if not validar_correo(correo):
                errores.append("Correo electrónico no válido")
            else:
                datos['correo'] = correo.strip()
        else:
            datos['correo'] = ""

        # --- FUNCIÓN Auxiliar PARA PARSEAR FECHAS ---
        def parsear_fecha(valor):
            if not valor:
                return None
            valor_str = str(valor).strip()
            # Lista de formatos aceptados (ordenados por especificidad)
            formatos = [
                "%Y-%m-%d %H:%M:%S",   # 2026-08-04 00:00:00
                "%Y-%m-%d %H:%M",      # 2026-08-04 00:00
                "%Y-%m-%d",            # 2026-08-04
                "%d/%m/%Y %H:%M:%S",
                "%d/%m/%Y %H:%M",
                "%d/%m/%Y",
                "%m/%d/%Y %H:%M:%S",
                "%m/%d/%Y %H:%M",
                "%m/%d/%Y",
                "%d-%m-%Y %H:%M:%S",
                "%d-%m-%Y %H:%M",
                "%d-%m-%Y",
            ]
            for fmt in formatos:
                try:
                    dt = datetime.strptime(valor_str, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            # Si falla, intentar con dateutil (más flexible, opcional)
            try:
                from dateutil import parser
                dt = parser.parse(valor_str)
                return dt.strftime("%Y-%m-%d")
            except:
                raise ValueError(f"Fecha no válida: '{valor_str}'")

        # Fecha ingreso (opcional)
        if fecha_ingreso:
            try:
                datos['fecha_ingreso'] = parsear_fecha(fecha_ingreso)
            except Exception:
                errores.append("Fecha ingreso no válida (use YYYY-MM-DD, DD/MM/YYYY, o YYYY-MM-DD HH:MM:SS)")
        else:
            datos['fecha_ingreso'] = ""

        # Servicios (EPS, ARL, Pensión, Caja) - deben estar en las opciones configuradas o "-/-"
        eps_opciones = self.eps_options
        if eps and eps not in eps_opciones:
            errores.append(f"EPS '{eps}' no válida. Opciones: {', '.join(eps_opciones)}")
        datos['eps'] = eps if eps in eps_opciones else ""

        arl_opciones = self.arl_options
        if arl and arl not in arl_opciones:
            errores.append(f"ARL '{arl}' no válida. Opciones: {', '.join(arl_opciones)}")
        datos['arl'] = arl if arl in arl_opciones else ""

        pension_opciones = self.pension_options
        if pension and pension not in pension_opciones:
            errores.append(f"Pensión '{pension}' no válida. Opciones: {', '.join(pension_opciones)}")
        datos['pension'] = pension if pension in pension_opciones else ""

        caja_opciones = self.caja_compensacion_options
        if caja_compensacion and caja_compensacion not in caja_opciones:
            errores.append(f"Caja Compensación '{caja_compensacion}' no válida. Opciones: {', '.join(caja_opciones)}")
        datos['caja_compensacion'] = caja_compensacion if caja_compensacion in caja_opciones else ""

        # Mes de pago (opcional)
        if mes_pago:
            meses_validos = self.meses
            if mes_pago not in meses_validos:
                errores.append(f"Mes de pago '{mes_pago}' no válido. Opciones: {', '.join(meses_validos)}")
            datos['mes_pago'] = mes_pago if mes_pago in meses_validos else ""
        else:
            datos['mes_pago'] = ""

        # Valor pagado (opcional, numérico)
        if valor_pagado:
            try:
                # Si es string, quitar comas y puntos de miles
                val_str = str(valor_pagado).replace(',', '').replace('.', '')
                datos['valor_pagado'] = float(val_str)
            except:
                errores.append("Valor pagado debe ser un número")
        else:
            datos['valor_pagado'] = 0.0

        # Método de pago (opcional)
        if metodo_pago:
            metodos_validos = self.metodos_pago
            if metodo_pago not in metodos_validos:
                errores.append(f"Método de pago '{metodo_pago}' no válido. Opciones: {', '.join(metodos_validos)}")
            datos['metodo_pago'] = metodo_pago if metodo_pago in metodos_validos else ""
        else:
            datos['metodo_pago'] = ""

        # Fecha pago (opcional)
        if fecha_pago:
            try:
                datos['fecha_pago'] = parsear_fecha(fecha_pago)
            except Exception:
                errores.append("Fecha pago no válida (use YYYY-MM-DD, DD/MM/YYYY, o YYYY-MM-DD HH:MM:SS)")
        else:
            datos['fecha_pago'] = ""

        # Verificar que al menos un servicio esté seleccionado
        servicios = [datos['eps'], datos['arl'], datos['pension'], datos['caja_compensacion']]
        if not any(servicios):
            errores.append("Debe seleccionar al menos un servicio (EPS, ARL, Pensión o Caja)")

        return datos, errores

    def formatear_valor(val):
        if hasattr(val, 'strftime'):
            return val.strftime("%Y-%m-%d")
        return val

    def _mostrar_resumen_importacion(self, estadisticas):
        """
        Muestra un cuadro de diálogo con el resumen de la importación.
        """
        mensaje = (
            f"✅ Importación completada\n\n"
            f"Registros exitosos (nuevos): {estadisticas['exitosos']}\n"
            f"Registros sobrescritos (actualizados): {estadisticas['sobrescritos']}\n"
            f"Registros saltados (duplicados): {estadisticas['duplicados_saltados']}\n"
            f"Errores: {estadisticas['errores']}\n"
        )
        messagebox.showinfo("Resumen de importación", mensaje)

    def setup_contabilidad_interface(self):
        """Configura la interfaz de contabilidad con pestañas para Ingresos, Egresos, HistoriPago, Novedades, Incapacidades."""
        main_frame = ttk.Frame(self.contabilidad_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # --- Título de la sección ---
        ttk.Label(main_frame, text="C.H.I.N", style='Title.TLabel').pack(pady=(0, 10))

        # Crear notebook para las pestañas de contabilidad
        contabilidad_notebook = ttk.Notebook(main_frame)
        contabilidad_notebook.pack(fill=tk.BOTH, expand=True)

        # Pestaña de Ingresos
        ingresos_frame = ttk.Frame(contabilidad_notebook)
        contabilidad_notebook.add(ingresos_frame, text="Ingresos")
        self.setup_ingresos_interface(ingresos_frame)

        # Pestaña de Egresos
        egresos_frame = ttk.Frame(contabilidad_notebook)
        contabilidad_notebook.add(egresos_frame, text="Egresos")
        self.setup_egresos_interface(egresos_frame)

        # Pestaña de Historial de Pagos
        historial_frame = ttk.Frame(contabilidad_notebook)
        contabilidad_notebook.add(historial_frame, text="HistoriPago")
        self.setup_historial_pagos_interface(historial_frame)

        # Pestaña de Incapacidades
        incapacidades_frame = ttk.Frame(contabilidad_notebook)
        contabilidad_notebook.add(incapacidades_frame, text="Incapacidades")
        self.setup_incapacidades_interface(incapacidades_frame)

        # Pestaña de Novedades
        novedades_frame = ttk.Frame(contabilidad_notebook)
        contabilidad_notebook.add(novedades_frame, text="Novedades")
        self.setup_novedades_interface(novedades_frame)

        # Totales
        self.setup_contabilidad_totales(main_frame)

        # --- NUEVO: Evento para actualizar al cambiar de pestaña ---
        def on_tab_selected(event):
            selected = contabilidad_notebook.select()
            tab_text = contabilidad_notebook.tab(selected, "text")
            hoy = datetime.now().strftime("%Y-%m-%d")
            if tab_text == "Ingresos":
                self.filtro_fecha_ingresos.set(hoy)
                self.update_ingresos_table(hoy)
            elif tab_text == "Egresos":
                self.filtro_fecha_egresos.set(hoy)
                self.update_egresos_table(hoy)

        contabilidad_notebook.bind("<<NotebookTabChanged>>", on_tab_selected)

    def _autenticar_drive(self):
        try:
            from drive_manager import GoogleDriveManager
            drive = GoogleDriveManager(folder_name=self.drive_carpeta_var.get() or "SaluPago_Backups")
            drive._autenticar()
            messagebox.showinfo("Google Drive",
                                "Autenticación exitosa. Se abrirá el navegador la primera vez.")
        except FileNotFoundError:
            messagebox.showerror(
                "credentials.json faltante",
                "No se encontró credentials.json.\n\n"
                "Descárgalo de Google Cloud Console y colócalo junto al script principal."
            )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo autenticar:\n{str(e)}")

    def setup_configuracion_interface(self, parent):
        """Interfaz de configuración en grid 3x2 con distribución proporcional mejorada"""
        from datetime import datetime

        main_frame = ttk.Frame(parent, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="⚙️ Configuración del Sistema",
                style='Title.TLabel').pack(pady=(0, 10))

        # ============================================================
        # GRID 3x2 (Con proporciones ajustadas)
        # ============================================================
        grid_container = ttk.Frame(main_frame)
        grid_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Columna 0: Empresa/Precios (Ancho base)
        # Columna 1: Monitoreo/Backup (Un poco más ancha)
        # Columna 2: Caja/Sonidos (La más ancha por los textos)
        grid_container.columnconfigure(0, weight=10, uniform="cfgcol")
        grid_container.columnconfigure(1, weight=11, uniform="cfgcol")
        grid_container.columnconfigure(2, weight=12, uniform="cfgcol")
        
        grid_container.rowconfigure(0, weight=1)
        grid_container.rowconfigure(1, weight=1)

        # ---------- (0,0) EMPRESA ----------
        empresa_frame = ttk.LabelFrame(grid_container,
                                        text="🏢 Empresa e Imagen de Pago",
                                        padding=10, relief='groove')
        empresa_frame.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        self.config_emp_nombre    = tk.StringVar(value=self.config.get('empresa.nombre', ''))
        self.config_emp_nit       = tk.StringVar(value=self.config.get('empresa.nit', ''))
        self.config_emp_direccion = tk.StringVar(value=self.config.get('empresa.direccion', ''))
        self.config_emp_telefono  = tk.StringVar(value=self.config.get('empresa.telefono', ''))
        self.config_emp_correo    = tk.StringVar(value=self.config.get('empresa.correo', ''))

        campos_emp = [
            ("Nombre:",    self.config_emp_nombre),
            ("NIT:",       self.config_emp_nit),
            ("Dirección:", self.config_emp_direccion),
            ("Teléfono:",  self.config_emp_telefono),
            ("Correo:",    self.config_emp_correo),
        ]
        for i, (label, var) in enumerate(campos_emp):
            ttk.Label(empresa_frame, text=label, font=('Arial', 9)).grid(
                row=i, column=0, sticky=tk.W, padx=2, pady=4)
            ttk.Entry(empresa_frame, textvariable=var, font=('Arial', 9)).grid(
                row=i, column=1, sticky=tk.EW, padx=2, pady=4)
        empresa_frame.columnconfigure(1, weight=1)

        ttk.Separator(empresa_frame, orient='horizontal').grid(
            row=len(campos_emp), column=0, columnspan=2, sticky=tk.EW, pady=6)
        ttk.Label(empresa_frame, text="Imagen de pago (factura):",
                font=('Arial', 9, 'bold')).grid(
            row=len(campos_emp)+1, column=0, columnspan=2, sticky=tk.W, padx=2, pady=(2, 3))

        self.config_pago_imagen_var = tk.StringVar(value=self.config.get('pago_imagen', 'Nequi.png'))
        ttk.Entry(empresa_frame, textvariable=self.config_pago_imagen_var,
                font=('Arial', 9)).grid(
            row=len(campos_emp)+2, column=0, sticky=tk.EW, padx=(2, 0), pady=1)
        ttk.Button(empresa_frame, text="📤", width=3,
                command=self.seleccionar_imagen_pago).grid(
            row=len(campos_emp)+2, column=1, padx=(4, 2), pady=1, sticky=tk.W)

        # ---------- (0,1) MONITOREO ----------
        monitoreo_frame = ttk.LabelFrame(grid_container,
                                        text="📊 Umbrales de Monitoreo",
                                        padding=10, relief='groove')
        monitoreo_frame.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)

        self.config_activo_dias     = tk.StringVar(value=str(self.config.get('monitoreo_umbrales.activo_hasta_dias', 3)))
        self.config_proximo_dias    = tk.StringVar(value=str(self.config.get('monitoreo_umbrales.proximo_suspender_dias', 5)))
        self.config_suspendido_dias = tk.StringVar(value=str(self.config.get('monitoreo_umbrales.suspendido_dias', 7)))

        ttk.Label(monitoreo_frame, text="Días para cada estado:",
                font=('Arial', 9, 'italic'), foreground='#555').grid(
            row=0, column=0, columnspan=2, sticky=tk.W, padx=2, pady=(0, 8))

        ttk.Label(monitoreo_frame, text="Activo (Próximo a vencer):",
                font=('Arial', 9)).grid(row=1, column=0, sticky=tk.W, padx=2, pady=4)
        ttk.Entry(monitoreo_frame, textvariable=self.config_activo_dias,
                width=8, font=('Arial', 9)).grid(row=1, column=1, sticky=tk.W, padx=6, pady=4)

        ttk.Label(monitoreo_frame, text="Próximo a Suspender:",
                font=('Arial', 9)).grid(row=2, column=0, sticky=tk.W, padx=2, pady=4)
        ttk.Entry(monitoreo_frame, textvariable=self.config_proximo_dias,
                width=8, font=('Arial', 9)).grid(row=2, column=1, sticky=tk.W, padx=6, pady=4)

        ttk.Label(monitoreo_frame, text="Suspendido:",
                font=('Arial', 9)).grid(row=3, column=0, sticky=tk.W, padx=2, pady=4)
        ttk.Entry(monitoreo_frame, textvariable=self.config_suspendido_dias,
                width=8, font=('Arial', 9)).grid(row=3, column=1, sticky=tk.W, padx=6, pady=4)

        ttk.Label(monitoreo_frame,
                text="Nota: los días son acumulativos desde\nel vencimiento del pago.",
                font=('Arial', 8), foreground='#777').grid(
            row=4, column=0, columnspan=2, sticky=tk.W, padx=2, pady=(10, 0))
        monitoreo_frame.columnconfigure(1, weight=1)

        # ---------- (0,2) CAJA / PAGO / SONIDOS ----------
        pago_frame = ttk.LabelFrame(grid_container,
                                    text="💳 Caja, Pago y Sonidos",
                                    padding=10, relief='groove')
        pago_frame.grid(row=0, column=2, sticky="nsew", padx=4, pady=4)

        self.config_base_caja = tk.StringVar(value=str(self.config.get_base_caja()))
        ttk.Label(pago_frame, text="Monto base de caja:",
                font=('Arial', 9, 'bold')).grid(
            row=0, column=0, sticky=tk.W, padx=2, pady=(0, 4))
        ttk.Entry(pago_frame, textvariable=self.config_base_caja, width=15,
                font=('Arial', 9)).grid(row=0, column=1, sticky=tk.EW, padx=6, pady=(0, 4))

        ttk.Separator(pago_frame, orient='horizontal').grid(
            row=1, column=0, columnspan=2, sticky=tk.EW, pady=6)

        ttk.Label(pago_frame, text="Métodos de pago (separados por comas):",
                font=('Arial', 9, 'bold')).grid(
            row=2, column=0, columnspan=2, sticky=tk.W, padx=2, pady=(2, 2))
        self.config_metodos_opts_var = tk.StringVar(
            value=",".join(self.config.get_opciones('metodos_pago')))
        ttk.Entry(pago_frame, textvariable=self.config_metodos_opts_var,
                font=('Arial', 9)).grid(
            row=3, column=0, columnspan=2, sticky=tk.EW, padx=2, pady=1)
        ttk.Label(pago_frame, text="Ej: Transferencia, Efectivo, Tarjeta",
                font=('Arial', 8), foreground='#666').grid(
            row=4, column=0, columnspan=2, sticky=tk.W, padx=2, pady=(0, 6))

        ttk.Separator(pago_frame, orient='horizontal').grid(
            row=5, column=0, columnspan=2, sticky=tk.EW, pady=6)

        ttk.Label(pago_frame, text="🔊 Sonidos de retroalimentación",
                font=('Arial', 9, 'bold')).grid(
            row=6, column=0, columnspan=2, sticky=tk.W, padx=2, pady=(0, 4))

        self.config_sonidos_activo_var = tk.BooleanVar(value=self.config.get_sonidos_activo())
        ttk.Checkbutton(pago_frame, text="Activar sonidos",
                        variable=self.config_sonidos_activo_var).grid(
            row=7, column=0, columnspan=2, sticky=tk.W, padx=2, pady=3)

        ttk.Label(pago_frame, text="Volumen (0.0 - 1.0):",
                font=('Arial', 9)).grid(row=8, column=0, sticky=tk.W, padx=2, pady=3)
        self.config_sonidos_volumen_var = tk.StringVar(value=str(self.config.get_sonidos_volumen()))
        ttk.Entry(pago_frame, textvariable=self.config_sonidos_volumen_var,
                width=8, font=('Arial', 9)).grid(row=8, column=1, sticky=tk.W, padx=6, pady=3)

        def probar_sonido():
            SoundManager.reproducir("confirmar", volumen=self.config.get_sonidos_volumen())

        ttk.Button(pago_frame, text="🔊 Probar sonido",
                command=probar_sonido).grid(
            row=9, column=0, columnspan=2, sticky=tk.EW, padx=2, pady=(6, 2))
        pago_frame.columnconfigure(1, weight=1)

        # ---------- (1,0) PRECIOS ----------
        price_frame = ttk.LabelFrame(grid_container, text="💰 Precios",
                                    padding=10, relief='groove')
        price_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

        self.config_eps_var     = tk.StringVar(value=str(self.config.get_precio_eps()))
        self.config_arl_vars    = {}
        arl_precios = self.config.get('precios.arl', {})
        for arl_name, valor in arl_precios.items():
            self.config_arl_vars[arl_name] = tk.StringVar(value=str(valor))
        self.config_pension_var = tk.StringVar(value=str(self.config.get_precio_pension()))
        self.config_caja_var    = tk.StringVar(value=str(self.config.get_precio_caja()))

        price_grid = ttk.Frame(price_frame)
        price_grid.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Fila 0: EPS + Pensión + Caja (3 columnas compactas)
        ttk.Label(price_grid, text="EPS:", font=('Arial', 9, 'bold')).grid(
            row=0, column=0, sticky=tk.W, padx=(0, 2), pady=3)
        ttk.Entry(price_grid, textvariable=self.config_eps_var,
                font=('Arial', 9), width=7).grid(
            row=0, column=1, sticky=tk.W, padx=(0, 10), pady=3)

        ttk.Label(price_grid, text="Pensión:", font=('Arial', 9, 'bold')).grid(
            row=0, column=2, sticky=tk.W, padx=(0, 2), pady=3)
        ttk.Entry(price_grid, textvariable=self.config_pension_var,
                font=('Arial', 9), width=7).grid(
            row=0, column=3, sticky=tk.W, padx=(0, 10), pady=3)

        ttk.Label(price_grid, text="Caja:", font=('Arial', 9, 'bold')).grid(
            row=0, column=4, sticky=tk.W, padx=(0, 2), pady=3)
        ttk.Entry(price_grid, textvariable=self.config_caja_var,
                font=('Arial', 9), width=7).grid(
            row=0, column=5, sticky=tk.W, padx=0, pady=3)

        # Fila 1: ARL (5 niveles en 2 sub-filas)
        ttk.Label(price_grid, text="ARL:", font=('Arial', 9, 'bold')).grid(
            row=1, column=0, sticky=tk.NW, padx=2, pady=(10, 3))

        arl_container = ttk.Frame(price_grid)
        arl_container.grid(row=1, column=1, columnspan=5, sticky=tk.W, padx=2, pady=(10, 3))

        for idx, (arl_name, var) in enumerate(self.config_arl_vars.items()):
            sub_row = idx // 3      # 3 por fila
            sub_col = (idx % 3) * 2
            ttk.Label(arl_container, text=f"{arl_name}:",
                    font=('Arial', 9)).grid(row=sub_row, column=sub_col,
                                            padx=(0, 2), pady=3, sticky=tk.W)
            ttk.Entry(arl_container, textvariable=var, width=7,
                    font=('Arial', 9)).grid(row=sub_row, column=sub_col+1,
                                            padx=(0, 8), pady=3, sticky=tk.W)

        # ---------- (1,1) AUTOGUARDADO ----------
        autoguardado_frame = ttk.LabelFrame(grid_container,
                                            text="🔄 Autoguardado (Backup)",
                                            padding=10, relief='groove')
        autoguardado_frame.grid(row=1, column=1, sticky="nsew", padx=4, pady=4)

        self.backup_activo_var      = tk.BooleanVar(value=self.config.get_backup_activo())
        self.backup_intervalo_var   = tk.StringVar(value=str(self.config.get_backup_intervalo()))
        self.config_dias_conservar  = tk.StringVar(value=str(self.config.get_dias_conservar_backup()))

        ttk.Checkbutton(autoguardado_frame, text="Activar backup automático",
                        variable=self.backup_activo_var).pack(anchor=tk.W, padx=2, pady=(0, 5))

        fila_int = ttk.Frame(autoguardado_frame)
        fila_int.pack(fill=tk.X, padx=2, pady=3)
        ttk.Label(fila_int, text="Intervalo (horas):").pack(side=tk.LEFT)
        self.entry_intervalo = ttk.Entry(fila_int, textvariable=self.backup_intervalo_var, width=10)
        self.entry_intervalo.pack(side=tk.LEFT, padx=6)

        fila_dias = ttk.Frame(autoguardado_frame)
        fila_dias.pack(fill=tk.X, padx=2, pady=3)
        ttk.Label(fila_dias, text="Días a conservar:").pack(side=tk.LEFT)
        self.entry_dias = ttk.Entry(fila_dias, textvariable=self.config_dias_conservar, width=10)
        self.entry_dias.pack(side=tk.LEFT, padx=6)

        # Google Drive
        drive_frame = ttk.LabelFrame(autoguardado_frame, text="☁️ Google Drive", padding=8)
        drive_frame.pack(fill=tk.X, padx=2, pady=(8, 2))

        self.drive_activo_var        = tk.BooleanVar(value=self.config.get_drive_activo())
        self.drive_subir_auto_var    = tk.BooleanVar(value=self.config.get_drive_subir_auto())
        self.drive_subir_manual_var  = tk.BooleanVar(value=self.config.get_drive_subir_manual())
        self.drive_carpeta_var       = tk.StringVar(value=self.config.get_drive_carpeta())

        ttk.Checkbutton(drive_frame, text="Activar subida a Google Drive",
                        variable=self.drive_activo_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(drive_frame, text="Subir backups automáticos",
                        variable=self.drive_subir_auto_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(drive_frame, text="Subir backups manuales",
                        variable=self.drive_subir_manual_var).pack(anchor=tk.W, pady=2)

        fila_carpeta = ttk.Frame(drive_frame)
        fila_carpeta.pack(fill=tk.X, pady=(6, 2))
        ttk.Label(fila_carpeta, text="Carpeta en Drive:").pack(side=tk.LEFT)
        ttk.Entry(fila_carpeta, textvariable=self.drive_carpeta_var, width=18).pack(side=tk.LEFT, padx=5)

        ttk.Button(drive_frame, text="🔗 Autenticar con Google",
                command=self._autenticar_drive).pack(fill=tk.X, pady=(6, 2))

        # Último backup
        ultimo = self.config.get_ultimo_backup()
        if ultimo:
            try:
                dt = datetime.fromisoformat(ultimo)
                ttk.Separator(autoguardado_frame, orient='horizontal').pack(fill=tk.X, pady=8)
                ttk.Label(autoguardado_frame,
                        text=f"Último backup:\n{dt.strftime('%d/%m/%Y %H:%M')}",
                        font=('Arial', 9), foreground='#555',
                        justify=tk.LEFT).pack(anchor=tk.W, padx=2)
            except Exception:
                pass

        def toggle_backup_fields():
            estado = 'normal' if self.backup_activo_var.get() else 'disabled'
            self.entry_intervalo.config(state=estado)
            self.entry_dias.config(state=estado)

        self.backup_activo_var.trace('w', lambda *args: toggle_backup_fields())
        toggle_backup_fields()

        # ---------- (1,2) INFORMACIÓN ----------
        info_frame = ttk.LabelFrame(grid_container, text="ℹ️ Información",
                                    padding=10, relief='groove')
        info_frame.grid(row=1, column=2, sticky="nsew", padx=4, pady=4)

        try:
            empresa_nombre = self.config.get('empresa.nombre', 'SaluPago')
            ultimo_bk = self.config.get_ultimo_backup() or "Nunca"
            try:
                if ultimo_bk != "Nunca":
                    ultimo_bk = datetime.fromisoformat(ultimo_bk).strftime('%d/%m/%Y %H:%M')
            except Exception:
                pass

            info_texto = (
                f"Empresa: {empresa_nombre}\n\n"
                f"Base de datos:\n{os.path.basename(self.config.db_path)}\n\n"
                f"Último backup:\n{ultimo_bk}\n\n"
                f"Versión: 4.0.8\n"
                f"Sistema SaluPago\n\n"
                f"💡 Tip: los cambios se guardan\nal presionar 'Guardar Cambios'."
            )
        except Exception:
            info_texto = "SaluPago\nVersión 4.0.8"

        ttk.Label(info_frame, text=info_texto,
                font=('Arial', 9), foreground='#555',
                justify=tk.LEFT).pack(anchor=tk.NW, padx=2, pady=2)

        # ============================================================
        # FILA 2: Botones de acción centrados
        # ============================================================
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        style = ttk.Style()
        style.configure("Config.TButton", padding=8, font=('Arial', 10, 'bold'))

        def guardar_config():
            try:
                nuevos_precios = {
                    'eps': int(self.config_eps_var.get()),
                    'arl': {name: int(var.get()) for name, var in self.config_arl_vars.items()},
                    'pension': int(self.config_pension_var.get()),
                    'caja': int(self.config_caja_var.get())
                }
                self.config.update({'precios': nuevos_precios})

                umbrales = {
                    'activo_hasta_dias': int(self.config_activo_dias.get()),
                    'proximo_suspender_dias': int(self.config_proximo_dias.get()),
                    'suspendido_dias': int(self.config_suspendido_dias.get())
                }
                self.config.update({'monitoreo_umbrales': umbrales})

                self.config.update({'caja': {'base_caja': int(self.config_base_caja.get())}})

                metodos = [item.strip() for item in self.config_metodos_opts_var.get().split(',') if item.strip()]
                self.config.update({'opciones': {'metodos_pago': metodos}})

                empresa_data = {
                    'nombre':    self.config_emp_nombre.get().strip(),
                    'nit':       self.config_emp_nit.get().strip(),
                    'direccion': self.config_emp_direccion.get().strip(),
                    'telefono':  self.config_emp_telefono.get().strip(),
                    'correo':    self.config_emp_correo.get().strip()
                }
                self.config.update({'empresa': empresa_data})

                self.config.update({'pago_imagen': self.config_pago_imagen_var.get().strip()})

                # Backup
                self.config.set_backup_activo(self.backup_activo_var.get())
                if self.backup_activo_var.get():
                    try:
                        horas = int(self.backup_intervalo_var.get())
                        if horas <= 0:
                            messagebox.showerror("Error", "El intervalo debe ser mayor a 0")
                            return
                        self.config.set_backup_intervalo(horas)
                    except ValueError:
                        messagebox.showerror("Error", "El intervalo debe ser un número entero positivo")
                        return

                    try:
                        dias = int(self.config_dias_conservar.get())
                        if dias <= 0:
                            messagebox.showerror("Error", "Los días a conservar deben ser mayor a 0")
                            return
                        self.config.set_dias_conservar_backup(dias)
                    except ValueError:
                        messagebox.showerror("Error", "Los días a conservar deben ser un número entero positivo")
                        return

                    self.programar_backup_automatico()

                self.setup_pricing_and_options()
                if hasattr(self, 'hacer_caja'):
                    self.hacer_caja()

                # Sonidos
                self.config.set_sonidos_activo(self.config_sonidos_activo_var.get())
                try:
                    vol = float(self.config_sonidos_volumen_var.get())
                    self.config.set_sonidos_volumen(vol)
                    SoundManager.set_volumen(vol)
                except ValueError:
                    messagebox.showerror("Error", "El volumen debe ser un número entre 0.0 y 1.0")
                    return
                SoundManager.set_habilitado(self.config_sonidos_activo_var.get())

                # Google Drive
                try:
                    self.config.set('google_drive.activo', self.drive_activo_var.get())
                    self.config.set('google_drive.subir_backup_automatico', self.drive_subir_auto_var.get())
                    self.config.set('google_drive.subir_backup_manual', self.drive_subir_manual_var.get())
                    self.config.set('google_drive.carpeta', self.drive_carpeta_var.get().strip())
                except Exception:
                    pass

                messagebox.showinfo("Éxito", "Configuración guardada correctamente.")
            except ValueError as e:
                messagebox.showerror("Error", f"Valor inválido: {str(e)}")

        def restaurar_defaults():
            if not messagebox.askyesno("Confirmar", "¿Restaurar configuración por defecto?"):
                return

            self.config.update(DEFAULT_CONFIG)
            self.setup_pricing_and_options()

            self.config_eps_var.set(str(self.config.get_precio_eps()))
            arl_precios = self.config.get('precios.arl', {})
            for arl_name, var in self.config_arl_vars.items():
                var.set(str(arl_precios.get(arl_name, 0)))
            self.config_pension_var.set(str(self.config.get_precio_pension()))
            self.config_caja_var.set(str(self.config.get_precio_caja()))

            self.config_activo_dias.set(str(self.config.get('monitoreo_umbrales.activo_hasta_dias', 3)))
            self.config_proximo_dias.set(str(self.config.get('monitoreo_umbrales.proximo_suspender_dias', 5)))
            self.config_suspendido_dias.set(str(self.config.get('monitoreo_umbrales.suspendido_dias', 7)))
            self.config_base_caja.set(str(self.config.get_base_caja()))
            self.config_metodos_opts_var.set(",".join(self.config.get_opciones('metodos_pago')))

            self.config_emp_nombre.set(self.config.get('empresa.nombre', ''))
            self.config_emp_nit.set(self.config.get('empresa.nit', ''))
            self.config_emp_direccion.set(self.config.get('empresa.direccion', ''))
            self.config_emp_telefono.set(self.config.get('empresa.telefono', ''))
            self.config_emp_correo.set(self.config.get('empresa.correo', ''))
            self.config_pago_imagen_var.set(self.config.get('pago_imagen', 'Nequi.png'))

            self.backup_activo_var.set(self.config.get_backup_activo())
            self.backup_intervalo_var.set(str(self.config.get_backup_intervalo()))
            self.config_dias_conservar.set(str(self.config.get_dias_conservar_backup()))
            toggle_backup_fields()

            # Sonidos
            self.config_sonidos_activo_var.set(self.config.get_sonidos_activo())
            self.config_sonidos_volumen_var.set(str(self.config.get_sonidos_volumen()))

            messagebox.showinfo("Restaurado", "Configuración restaurada a valores por defecto.")

        btn_container = ttk.Frame(btn_frame)
        btn_container.pack(anchor=tk.CENTER)

        ttk.Button(btn_container, text="💾 Guardar Cambios",
                command=guardar_config, style="Config.TButton").pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_container, text="↩️ Restaurar Defaults",
                command=restaurar_defaults, style="Config.TButton").pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_container, text="✖️ Cerrar",
                command=lambda: parent.winfo_toplevel().destroy(),
                style="Config.TButton").pack(side=tk.LEFT, padx=10)
                            
    def seleccionar_imagen_pago(self):
        """Abre un diálogo para seleccionar una imagen de pago y actualiza la variable."""
        from tkinter import filedialog
        ruta = filedialog.askopenfilename(
            title="Seleccionar imagen de pago",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.bmp *.gif"), ("Todos los archivos", "*.*")]
        )
        if ruta:
            self.config_pago_imagen_var.set(ruta)
                
    def abrir_configuracion(self):
        if self.user_role != "Administrativo":
            messagebox.showerror("Error", "No tiene permisos para acceder a la configuración.")
            return

        ventana = Toplevel(self.root)
        ventana.title("Configuración del Sistema")

        # ---- Ancho aumentado para ajustar secciones, altura compacta con scroll ----
        ancho, alto = 1260, 580  
        ventana.geometry(f"{ancho}x{alto}")
        ventana.minsize(1150, 500) 
        ventana.resizable(True, True)
        ventana.transient(self.root)
        ventana.grab_set()

        # ---- Centrar en pantalla ----
        ventana.update_idletasks()
        screen_w = ventana.winfo_screenwidth()
        screen_h = ventana.winfo_screenheight()
        x = (screen_w // 2) - (ancho // 2)
        y = max(20, (screen_h // 2) - (alto // 2))
        ventana.geometry(f"{ancho}x{alto}+{x}+{y}")

        # ---- Frame con Scroll ----
        main_container = ttk.Frame(ventana)
        main_container.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(main_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Configurar el scroll con la rueda del ratón
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # ---- Llamar a la interfaz ----
        self.setup_configuracion_interface(scrollable_frame)

        def cerrar_ventana():
            canvas.unbind_all("<MouseWheel>")
            ventana.destroy()

        ventana.protocol("WM_DELETE_WINDOW", cerrar_ventana)
                        
    def setup_historial_pagos_interface(self, parent):
        """Configura la interfaz del historial de pagos (agrupado por afiliado)"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Label(main_frame, text="Monitoreo", style='Title.TLabel').pack(pady=(0, 10))

        # Frame de búsqueda
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(search_frame, text="Buscar (Nombre o Cédula):").pack(side=tk.LEFT, padx=5)
        self.historial_search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.historial_search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        search_entry.bind("<KeyRelease>", lambda e: self.update_historial_pagos_table())

        ttk.Button(search_frame, text="🔍 Buscar", command=self.update_historial_pagos_table).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="🔄 Actualizar", command=lambda: [self.historial_search_var.set(""), self.update_historial_pagos_table()]).pack(side=tk.LEFT, padx=5)

        # Tabla de historial (agrupado)
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        # Nuevas columnas
        columns = ("CC", "Nombre", "Total Pagado", "# Pagos", "Último Pago")
        self.historial_tree = ttk.Treeview(table_frame, columns=columns, show="headings")

        column_widths = {
            "CC": 100,
            "Nombre": 200,
            "Total Pagado": 120,
            "# Pagos": 80,
            "Último Pago": 100
        }
        for col in columns:
            self.historial_tree.column(col, width=column_widths.get(col, 100), anchor=tk.CENTER)
            self.historial_tree.heading(col, text=col)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.historial_tree.yview)
        self.historial_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.historial_tree.pack(fill=tk.BOTH, expand=True)

        # Doble clic → mostrar todos los pagos del afiliado
        self.historial_tree.bind("<Double-1>", self.mostrar_historial_completo_afiliado)

        # Cargar datos iniciales
        self.update_historial_pagos_table()
        
    def update_historial_pagos_table(self):
        """Actualiza la tabla de historial mostrando un registro por afiliado (agrupado)"""
        # Limpiar tabla
        for item in self.historial_tree.get_children():
            self.historial_tree.delete(item)

        search_term = self.historial_search_var.get().lower().strip()
        ingresos = self.contabilidad_data.get('ingresos', [])

        # Agrupar por CC
        grupos = {}
        for ing in ingresos:
            cc = ing.get('cc', '').strip()
            if not cc:
                continue
            if cc not in grupos:
                grupos[cc] = {
                    'cc': cc,
                    'nombre': ing.get('nombre', ''),
                    'total': 0.0,
                    'count': 0,
                    'ultima_fecha': None,
                    'ultimo_pago': None  # para referencia
                }
            g = grupos[cc]
            g['total'] += float(ing.get('valor', 0))
            g['count'] += 1
            fecha = ing.get('fecha', '')
            if fecha and (g['ultima_fecha'] is None or fecha > g['ultima_fecha']):
                g['ultima_fecha'] = fecha
                g['ultimo_pago'] = ing

        # Aplicar filtro de búsqueda
        if search_term:
            grupos_filtrados = {}
            for cc, g in grupos.items():
                if search_term in cc.lower() or search_term in g['nombre'].lower():
                    grupos_filtrados[cc] = g
            grupos = grupos_filtrados

        # Insertar en el treeview
        for cc, g in grupos.items():
            total_str = f"${g['total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            self.historial_tree.insert("", tk.END, values=(
                g['cc'],
                g['nombre'],
                total_str,
                g['count'],
                g['ultima_fecha'] or "-/-"
            ))

    def mostrar_historial_completo_afiliado(self, event=None):
        """Muestra una ventana con todos los pagos del afiliado seleccionado"""
        selected = self.historial_tree.selection()
        if not selected:
            return

        item = self.historial_tree.item(selected[0])
        cc = item['values'][0]  # CC

        # Obtener todos los pagos de este afiliado
        pagos = [p for p in self.contabilidad_data.get('ingresos', []) if p.get('cc', '').strip() == cc]
        if not pagos:
            messagebox.showinfo("Sin pagos", f"No se encontraron pagos para la cédula {cc}.")
            return

        # Ordenar por fecha descendente
        pagos.sort(key=lambda x: x.get('fecha', ''), reverse=True)

        # Crear ventana
        ventana = Toplevel(self.root)
        ventana.title(f"Historial completo de pagos - {pagos[0].get('nombre', cc)}")
        ventana.geometry("850x400")
        self.centrar_ventana(ventana, 850, 400)
        ventana.resizable(True, True)

        main_frame = ttk.Frame(ventana, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=f"Pagos de {pagos[0].get('nombre', cc)} (CC: {cc})",
                style='Title.TLabel').pack(pady=(0, 10))

        # Tabla de pagos
        columns = ("Fecha", "Servicio", "Valor", "Método", "Comprobante")
        tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=12)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for pago in pagos:
            valor_str = f"${float(pago.get('valor', 0)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            tree.insert("", tk.END, values=(
                pago.get('fecha', ''),
                pago.get('servicio', ''),
                valor_str,
                pago.get('metodo_pago', ''),
                pago.get('comprobante', '')
            ))

        # Botones
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        def generar_pdf_desde_ventana():
            self.generar_pdf_historial_afiliado(pagos, cc)

        ttk.Button(btn_frame, text="📄 Generar PDF con todos los pagos",
                command=generar_pdf_desde_ventana).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cerrar", command=ventana.destroy).pack(side=tk.RIGHT, padx=5)
    
    def generar_pdf_historial_afiliado(self, pagos, cc):
        """Genera un PDF con el historial de pagos del afiliado (lista de pagos ya filtrada)"""
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch, cm
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

        if not pagos:
            messagebox.showwarning("Advertencia", "No hay pagos para generar el PDF.")
            return

        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(downloads_dir):
            downloads_dir = os.getcwd()

        nombre_persona = pagos[0].get('nombre', 'Sin_nombre').replace(" ", "_")
        fecha_actual = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(downloads_dir, f"historial_pagos_{nombre_persona}_{fecha_actual}.pdf")

        doc = SimpleDocTemplate(filename, pagesize=letter,
                                leftMargin=1.5*cm, rightMargin=1.5*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Title'],
            fontSize=16,
            textColor=colors.HexColor('#1a237e'),
            alignment=TA_CENTER,
            spaceAfter=12
        )
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
        )

        logo_path = os.path.join(IMG_PATH, "LogoSaluPago.png")
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=2*cm, height=2*cm)
                elements.append(logo)
            except:
                pass

        elements.append(Paragraph("HISTORIAL DE PAGOS", title_style))
        elements.append(Spacer(1, 0.2*cm))

        nombre_completo = pagos[0].get('nombre', '')
        info = f"Afiliado: {nombre_completo}  |  Cédula: {cc}  |  Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        elements.append(Paragraph(info, header_style))
        elements.append(Spacer(1, 0.5*cm))

        # Tabla de pagos
        table_data = [["Fecha", "Servicio", "Valor", "Método", "Comprobante"]]
        total = 0.0
        for pago in pagos:
            table_data.append([
                pago.get('fecha', ''),
                pago.get('servicio', ''),
                f"${float(pago.get('valor', 0)):,.2f}",
                pago.get('metodo_pago', ''),
                pago.get('comprobante', '')
            ])
            total += float(pago.get('valor', 0))

        table_data.append(["", "", "", "TOTAL:", f"${total:,.2f}"])

        tabla = Table(table_data, colWidths=[2*cm, 3.5*cm, 2.5*cm, 2.5*cm, 3*cm])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a237e')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
            ('FONTNAME', (0,1), (-1,-2), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-2), 8),
            ('BACKGROUND', (0,1), (-1,-2), colors.whitesmoke),
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e3f2fd')),
            ('FONTNAME', (-2,-1), (-1,-1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (-1,-1), (-1,-1), colors.HexColor('#1a237e')),
        ]))
        elements.append(tabla)

        elements.append(Spacer(1, 0.5*cm))
        footer = Paragraph("Este documento es un resumen del historial de pagos.", styles['Italic'])
        elements.append(footer)

        doc.build(elements)

        # Abrir automáticamente
        try:
            if sys.platform == 'win32':
                os.startfile(filename)
            elif sys.platform == 'darwin':
                subprocess.call(('open', filename))
            else:
                subprocess.call(('xdg-open', filename))
            messagebox.showinfo("PDF Generado", f"Historial de pagos guardado en:\n{filename}")
        except Exception as e:
            messagebox.showwarning("PDF Generado", f"Se generó el PDF pero no se pudo abrir:\n{str(e)}\n\nUbicación: {filename}")

    def generar_y_abrir_pdf_historial(self, event):
        """
        Genera un PDF con el historial de pagos del afiliado seleccionado, con formato profesional.
        """
        selected_item = self.historial_tree.selection()
        if not selected_item:
            return

        # Obtener datos del item seleccionado
        item_data = self.historial_tree.item(selected_item)
        cc = item_data['values'][0]

        # Filtrar todos los pagos de esta persona
        pagos_persona = [p for p in self.contabilidad_data.get('ingresos', []) if p.get('cc', '') == cc]

        if not pagos_persona:
            messagebox.showwarning("Advertencia", "No se encontraron pagos para esta persona")
            return

        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch, cm
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

        # Configurar directorio de descargas o reportes
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(downloads_dir):
            downloads_dir = os.getcwd()

        nombre_persona = pagos_persona[0].get('nombre', 'Sin_nombre').replace(" ", "_")
        fecha_actual = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(downloads_dir, f"historial_pagos_{nombre_persona}_{fecha_actual}.pdf")

        doc = SimpleDocTemplate(filename, pagesize=letter,
                                leftMargin=1.5*cm, rightMargin=1.5*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        elements = []
        styles = getSampleStyleSheet()

        # Estilos
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Title'],
            fontSize=16,
            textColor=colors.HexColor('#1a237e'),
            alignment=TA_CENTER,
            spaceAfter=12
        )
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
        )
        total_style = ParagraphStyle(
            'TotalStyle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#1a237e'),
            alignment=TA_RIGHT
        )

        # Encabezado con logo
        logo_path = os.path.join(IMG_PATH, "LogoSaluPago.png")
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=2*cm, height=2*cm)
                elements.append(logo)
            except:
                pass

        elements.append(Paragraph("HISTORIAL DE PAGOS", title_style))
        elements.append(Spacer(1, 0.2*cm))

        # Datos del afiliado
        nombre_completo = pagos_persona[0].get('nombre', '')
        info = f"Afiliado: {nombre_completo}  |  Cédula: {cc}  |  Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        elements.append(Paragraph(info, header_style))
        elements.append(Spacer(1, 0.5*cm))

        # Tabla de pagos
        if pagos_persona:
            table_data = [["Fecha", "Servicio", "Valor", "Método", "Comprobante"]]
            total = 0.0
            for pago in pagos_persona:
                table_data.append([
                    pago.get('fecha', ''),
                    pago.get('servicio', ''),
                    f"${float(pago.get('valor', 0)):,.2f}",
                    pago.get('metodo_pago', ''),
                    pago.get('comprobante', '')
                ])
                total += float(pago.get('valor', 0))

            # Fila de total
            table_data.append(["", "", "", "TOTAL:", f"${total:,.2f}"])

            tabla = Table(table_data, colWidths=[2*cm, 3.5*cm, 2.5*cm, 2.5*cm, 3*cm])
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a237e')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 9),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
                ('FONTNAME', (0,1), (-1,-2), 'Helvetica'),
                ('FONTSIZE', (0,1), (-1,-2), 8),
                ('BACKGROUND', (0,1), (-1,-2), colors.whitesmoke),
                ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e3f2fd')),
                ('FONTNAME', (-2,-1), (-1,-1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (-1,-1), (-1,-1), colors.HexColor('#1a237e')),
            ]))
            elements.append(tabla)
        else:
            elements.append(Paragraph("No hay pagos registrados para este afiliado.", styles['Normal']))

        # Pie
        elements.append(Spacer(1, 0.5*cm))
        footer = Paragraph("Este documento es un resumen del historial de pagos.", styles['Italic'])
        elements.append(footer)

        doc.build(elements)

        # ========== ABRIR AUTOMÁTICAMENTE (corregido) ==========
        try:
            import sys
            if sys.platform == 'win32':
                os.startfile(filename)
            elif sys.platform == 'darwin':
                subprocess.call(('open', filename))
            else:
                subprocess.call(('xdg-open', filename))
            messagebox.showinfo("PDF Generado", f"Historial de pagos guardado en:\n{filename}")
        except Exception as e:
            messagebox.showwarning("PDF Generado", f"Se generó el PDF pero no se pudo abrir:\n{str(e)}\n\nUbicación: {filename}")
            
    def setup_ingresos_interface(self, parent):
        """Configura la interfaz de ingresos con filtro por fecha."""
        # Frame principal
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Filtro por fecha ---
        filter_frame = ttk.Frame(main_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(filter_frame, text="Fecha:").pack(side=tk.LEFT, padx=5)
        entry_fecha = ttk.Entry(filter_frame, textvariable=self.filtro_fecha_ingresos, width=12)
        entry_fecha.pack(side=tk.LEFT, padx=5)

        ttk.Button(filter_frame, text="🔍 Filtrar",
                command=lambda: self.update_ingresos_table(self.filtro_fecha_ingresos.get())).pack(side=tk.LEFT, padx=5)
        ttk.Button(filter_frame, text="📋 Mostrar todos",
                command=lambda: self.update_ingresos_table()).pack(side=tk.LEFT, padx=5)

        # --- Tabla de ingresos ---
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("Fecha", "CC", "Nombre", "Servicio", "Valor", "Método Pago", "Comprobante")
        self.ingresos_tree = ttk.Treeview(table_frame, columns=columns, show="headings")

        # Configurar columnas
        column_widths = {
            "Fecha": 90, "CC": 100, "Nombre": 150, "Servicio": 150,
            "Valor": 100, "Método Pago": 120, "Comprobante": 150
        }

        for col in columns:
            self.ingresos_tree.column(col, width=column_widths.get(col, 100), anchor=tk.CENTER)
            self.ingresos_tree.heading(col, text=col)

        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.ingresos_tree.yview)
        self.ingresos_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.ingresos_tree.pack(fill=tk.BOTH, expand=True)

        # --- Botones inferiores ---
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        inner = ttk.Frame(btn_frame)
        inner.pack(side=tk.RIGHT)

        ttk.Button(inner, text="➕Agregar", command=self.registrar_ingreso).pack(side=tk.LEFT, padx=5)

        if self.user_role == "Administrativo":
            ttk.Button(inner, text="✖️Eliminar", command=self.eliminar_ingreso_seleccionado).pack(side=tk.LEFT, padx=5)
            ttk.Button(inner, text="↩️ Anular Pago", command=self.anular_pago, style='Accent.TButton').pack(side=tk.LEFT, padx=5)

        # Cargar tabla con la fecha actual
        self.update_ingresos_table(self.filtro_fecha_ingresos.get()) 

    def eliminar_ingreso_seleccionado(self):
        selected_item = self.ingresos_tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Por favor seleccione un ingreso para eliminar")
            return
        if not self.validar_password():
            return
        index = self.ingresos_tree.index(selected_item[0])
        registro = self.contabilidad_data['ingresos'][index]
        
        # Obtener el número de comprobante
        num_comprobante = registro.get('comprobante', '')
        # Si el comprobante tiene el formato "Factura CC1077421179-082026", extraer el número
        if num_comprobante.startswith("Factura "):
            num_comprobante = num_comprobante.replace("Factura ", "").strip()
        
        respuesta = messagebox.askyesnocancel(
            "Confirmar eliminación",
            f"¿Desea eliminar este ingreso?\n\nAfiliado: {registro['nombre']}\nComprobante: {registro['comprobante']}\n\n"
            f"¿Desea también eliminar los archivos asociados (facturas)?",
            icon=messagebox.WARNING
        )
        if respuesta is None:
            return
        
        eliminar_archivos = respuesta
        archivos_eliminados = 0
        
        if eliminar_archivos:
            # Directorio donde se guardan las facturas
            directorio_facturas = os.path.join(BASE_PATH, "facturas")
            
            # Verificar que el directorio existe
            if os.path.exists(directorio_facturas):
                # Buscar archivos que coincidan con el número de factura
                for archivo in os.listdir(directorio_facturas):
                    # Convertir a minúsculas para comparación insensible a mayúsculas
                    archivo_lower = archivo.lower()
                    num_comprobante_lower = num_comprobante.lower()
                    
                    # Verificar si el archivo contiene el número de factura
                    # Buscar en el nombre del archivo
                    if (num_comprobante_lower in archivo_lower or
                        archivo_lower.startswith(f"factura_{num_comprobante_lower}") or
                        archivo_lower.endswith(f"{num_comprobante_lower}.pdf") or
                        archivo_lower == f"factura_{num_comprobante_lower}.pdf"):
                        
                        try:
                            ruta_completa = os.path.join(directorio_facturas, archivo)
                            os.remove(ruta_completa)
                            archivos_eliminados += 1
                            print(f"Archivo eliminado: {archivo}")
                        except Exception as e:
                            messagebox.showerror("Error", f"No se pudo eliminar {archivo}: {str(e)}")
                
                # Si no se encontraron archivos, mostrar mensaje
                if archivos_eliminados == 0:
                    messagebox.showwarning("Advertencia", 
                                        f"No se encontraron archivos que coincidan con '{num_comprobante}' en:\n{directorio_facturas}\n\n"
                                        f"Archivos disponibles:\n{', '.join(os.listdir(directorio_facturas)) if os.path.exists(directorio_facturas) else 'Ninguno'}")
                else:
                    messagebox.showinfo("Información", f"Se eliminaron {archivos_eliminados} archivos asociados")
            else:
                messagebox.showwarning("Advertencia", f"El directorio de facturas no existe:\n{directorio_facturas}")
        
        # Eliminar de BD
        registro_id = registro.get('id')
        if registro_id:
            self.db.delete_ingreso(registro_id)
        del self.contabilidad_data['ingresos'][index]
        self.update_ingresos_table()
        self.calcular_totales_contabilidad()
        self.mostrar_toast("Ingreso eliminado correctamente")

    def setup_egresos_interface(self, parent):
        """Configura la interfaz de egresos con filtro por fecha."""
        # Frame principal
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Filtro por fecha ---
        filter_frame = ttk.Frame(main_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(filter_frame, text="Fecha:").pack(side=tk.LEFT, padx=5)
        entry_fecha = ttk.Entry(filter_frame, textvariable=self.filtro_fecha_egresos, width=12)
        entry_fecha.pack(side=tk.LEFT, padx=5)

        ttk.Button(filter_frame, text="🔍 Filtrar",
                command=lambda: self.update_egresos_table(self.filtro_fecha_egresos.get())).pack(side=tk.LEFT, padx=5)
        ttk.Button(filter_frame, text="📋 Mostrar todos",
                command=lambda: self.update_egresos_table()).pack(side=tk.LEFT, padx=5)

        # --- Tabla de egresos ---
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("Fecha", "Descripción", "Valor", "Método Pago")
        self.egresos_tree = ttk.Treeview(table_frame, columns=columns, show="headings")

        # Configurar columnas
        column_widths = {
            "Fecha": 90, "Descripción": 250, "Valor": 100, "Método Pago": 120
        }

        for col in columns:
            self.egresos_tree.column(col, width=column_widths.get(col, 100), anchor=tk.CENTER)
            self.egresos_tree.heading(col, text=col)

        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.egresos_tree.yview)
        self.egresos_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.egresos_tree.pack(fill=tk.BOTH, expand=True)

        # --- Botones inferiores ---
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        inner = ttk.Frame(btn_frame)
        inner.pack(side=tk.RIGHT)

        ttk.Button(inner, text="➕Agregar", command=self.registrar_egreso).pack(side=tk.LEFT, padx=5)

        if self.user_role == "Administrativo":
            ttk.Button(inner, text="✖️Eliminar",
                    command=lambda: self.eliminar_registro_contable('egresos')).pack(side=tk.LEFT, padx=5)

        # Cargar tabla con la fecha actual
        self.update_egresos_table(self.filtro_fecha_egresos.get())
        
    def anular_pago(self):
        """
        Anula el ingreso seleccionado:
        - Elimina el registro contable.
        - Elimina el archivo PDF de la factura.
        - Restaura al afiliado los datos del pago inmediatamente anterior
        (fecha, mes, valor y método). Si no existía un pago previo,
        limpia esos campos (quedando como Pendiente).
        - Cancela cualquier solicitud de pago activa para que el estado
        se calcule correctamente (sin influencia de solicitudes).
        """
        # 1. Selección y validación
        selected_item = self.ingresos_tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Seleccione un ingreso para anular.")
            return

        index = self.ingresos_tree.index(selected_item[0])
        ingreso = self.contabilidad_data['ingresos'][index]

        cc = ingreso.get('cc', '').strip()
        if not cc:
            messagebox.showerror("Error", "Este ingreso no está asociado a un afiliado (no se puede anular).")
            return

        # Verificar que el afiliado exista (activo o retirado)
        afiliado = None
        for a in self.data:
            if a['cc'] == cc:
                afiliado = a
                break
        if not afiliado:
            for a in self.retiros_data:
                if a['cc'] == cc:
                    afiliado = a
                    break
        if not afiliado:
            messagebox.showerror("Error", "No se encontró el afiliado asociado a este ingreso.")
            return

        # 2. Contraseña de administrador
        if not self.validar_password():
            return

        # Confirmación
        if not messagebox.askyesno("Confirmar anulación",
                                f"¿Anular el pago de {afiliado['nombre']} (CC: {cc}) del {ingreso['fecha']}?\n"
                                f"Comprobante: {ingreso['comprobante']}\n"
                                "Se eliminará la factura y se restaurará el pago anterior (si existe)."):
            return

        # 3. Obtener datos del ingreso a anular
        comprobante = ingreso.get('comprobante', '')
        num_factura = comprobante.replace("Factura ", "").strip() if comprobante.startswith("Factura ") else ""
        ingreso_id = ingreso.get('id')

        # 4. Buscar el ingreso anterior más reciente (excluyendo el actual)
        ingresos_afiliado = [ing for ing in self.contabilidad_data['ingresos'] 
                            if ing.get('cc', '') == cc and ing.get('id') != ingreso_id]
        ingresos_afiliado.sort(key=lambda x: (x['fecha'], x.get('id', 0)), reverse=True)
        
        ingreso_anterior = ingresos_afiliado[0] if ingresos_afiliado else None

        # 5. Eliminar el ingreso de la base de datos y de la lista en memoria
        if ingreso_id:
            self.db.delete_ingreso(ingreso_id)
        del self.contabilidad_data['ingresos'][index]

        # 6. Eliminar el archivo PDF de factura si existe
        if num_factura:
            facturas_dir = os.path.join(BASE_PATH, "facturas")
            if os.path.exists(facturas_dir):
                for archivo in os.listdir(facturas_dir):
                    if archivo.endswith('.pdf') and num_factura in archivo:
                        try:
                            os.remove(os.path.join(facturas_dir, archivo))
                        except Exception as e:
                            print(f"Error al eliminar {archivo}: {e}")

        # 7. Actualizar datos del afiliado con el ingreso anterior (o limpiar si no hay)
        def actualizar_afiliado(registro, datos_anterior):
            if datos_anterior:
                registro['fecha_pago'] = datos_anterior['fecha']
                registro['mes_pago'] = datos_anterior.get('mes', '')
                registro['valor_pagado'] = float(datos_anterior['valor'])
                registro['metodo_pago'] = datos_anterior.get('metodo_pago', '')
            else:
                registro['fecha_pago'] = ""
                registro['mes_pago'] = ""
                registro['valor_pagado'] = 0.0
                registro['metodo_pago'] = ""
            return registro

        # Buscar el afiliado en activos o retirados y actualizar
        for i, af in enumerate(self.data):
            if af['cc'] == cc:
                self.data[i] = actualizar_afiliado(af, ingreso_anterior)
                self.db.update_afiliado(cc, self.data[i])
                break
        else:
            for i, af in enumerate(self.retiros_data):
                if af['cc'] == cc:
                    self.retiros_data[i] = actualizar_afiliado(af, ingreso_anterior)
                    self.db.update_afiliado(cc, self.retiros_data[i])
                    break

        # 8. Cancelar la solicitud de pago activa (si existe)
        solicitud = self.db.obtener_solicitud_reciente(cc)
        if solicitud and solicitud['estado'] not in ('cancelada', 'rechazado'):
            self.db.actualizar_solicitud(solicitud['id'], 'cancelada')

        # 9. Actualizar monitoreo para este afiliado (se recalculará el estado)
        self.actualizar_monitoreo_afiliado(cc)

        # 10. Refrescar todas las tablas afectadas
        self.update_afiliados_table()
        self.update_retiros_table()
        self.update_ingresos_table()
        self.update_monitoreo_table()
        self.calcular_totales_contabilidad()
        self.hacer_caja()  # Actualiza la caja del día

        # ========== AUDITORÍA ==========
        if ingreso_anterior:
            detalles = f"Pago anulado. Se restauró el pago del {ingreso_anterior['fecha']}."
        else:
            detalles = f"Pago anulado. El afiliado {afiliado['nombre']} quedó sin pagos previos."
        self._registrar_auditoria("Anuló pago", "Pagos", "Éxito", detalles)
        # ===============================

        # Mensaje de confirmación
        if ingreso_anterior:
            self.mostrar_toast(f"Pago anulado. Se restauró el pago del {ingreso_anterior['fecha']}.", duracion=4000)
        else:
            self.mostrar_toast(f"Pago anulado. {afiliado['nombre']} quedó en estado Pendiente.", duracion=4000)
            self.refrescar_sistema(silent=True)
            
    def setup_contabilidad_totales(self, parent):
        """Configura los totales de contabilidad para mostrar los del día actual"""
        totales_frame = ttk.Frame(parent)
        totales_frame.pack(fill=tk.X, pady=10)
        
        # Variables para los totales
        self.total_ingresos_dia_var = tk.StringVar(value="$0.00")
        self.total_egresos_dia_var = tk.StringVar(value="$0.00")
        self.saldo_dia_var = tk.StringVar(value="$0.00")
        
        # Obtener la fecha actual en formato YYYY-MM-DD
        from datetime import datetime
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        
        # Calcular totales del día
        total_ingresos_dia = 0.0
        total_egresos_dia = 0.0
        
        # Calcular ingresos del día
        for ingreso in self.contabilidad_data.get('ingresos', []):
            if ingreso.get('fecha', '') == fecha_actual:
                try:
                    total_ingresos_dia += float(ingreso.get('valor', 0))
                except (ValueError, TypeError):
                    pass
        
        # Calcular egresos del día
        for egreso in self.contabilidad_data.get('egresos', []):
            if egreso.get('fecha', '') == fecha_actual:
                try:
                    total_egresos_dia += float(egreso.get('valor', 0))
                except (ValueError, TypeError):
                    pass
        
        # Calcular saldo del día
        saldo_dia = total_ingresos_dia - total_egresos_dia
        
        # Actualizar variables
        self.total_ingresos_dia_var.set(f"${total_ingresos_dia:,.2f}")
        self.total_egresos_dia_var.set(f"${total_egresos_dia:,.2f}")
        self.saldo_dia_var.set(f"${saldo_dia:,.2f}")
        
        # Etiquetas para los totales del día
        ttk.Label(totales_frame, text="Ingresos hoy:").pack(side=tk.LEFT, padx=10)
        ttk.Label(totales_frame, textvariable=self.total_ingresos_dia_var, 
                font=('Arial', 10, 'bold'), foreground='green').pack(side=tk.LEFT)
        
        ttk.Label(totales_frame, text="Egresos hoy:").pack(side=tk.LEFT, padx=10)
        ttk.Label(totales_frame, textvariable=self.total_egresos_dia_var, 
                font=('Arial', 10, 'bold'), foreground='red').pack(side=tk.LEFT)
        
        ttk.Label(totales_frame, text="Saldo hoy:").pack(side=tk.LEFT, padx=10)
        ttk.Label(totales_frame, textvariable=self.saldo_dia_var, 
                font=('Arial', 10, 'bold'), 
                foreground='blue' if saldo_dia >= 0 else 'red').pack(side=tk.LEFT)
        
        # Separador
        ttk.Separator(totales_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        # También mantener los totales generales (opcional)
        # ttk.Label(totales_frame, text="Total Ingresos:").pack(side=tk.LEFT, padx=10)
        # ttk.Label(totales_frame, textvariable=self.total_ingresos_var, 
        #        font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        
        # ttk.Label(totales_frame, text="Total Egresos:").pack(side=tk.LEFT, padx=10)
        # ttk.Label(totales_frame, textvariable=self.total_egresos_var, 
        #        font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        
        # ttk.Label(totales_frame, text="Saldo Total:").pack(side=tk.LEFT, padx=10)
        # ttk.Label(totales_frame, textvariable=self.saldo_var, 
        #        font=('Arial', 10, 'bold')).pack(side=tk.LEFT)

        # Botón para actualizar los totales
        ttk.Button(totales_frame, text="🔄Actualizar", 
                command=lambda: self.actualizar_totales_dia()).pack(side=tk.RIGHT, padx=5)

    def actualizar_totales_dia(self):
        """Actualiza los totales del día actual"""
        from datetime import datetime
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        
        total_ingresos_dia = 0.0
        total_egresos_dia = 0.0
        
        # Calcular ingresos del día
        for ingreso in self.contabilidad_data.get('ingresos', []):
            if ingreso.get('fecha', '') == fecha_actual:
                try:
                    total_ingresos_dia += float(ingreso.get('valor', 0))
                except (ValueError, TypeError):
                    pass
        
        # Calcular egresos del día
        for egreso in self.contabilidad_data.get('egresos', []):
            if egreso.get('fecha', '') == fecha_actual:
                try:
                    total_egresos_dia += float(egreso.get('valor', 0))
                except (ValueError, TypeError):
                    pass
        
        # Calcular saldo del día
        saldo_dia = total_ingresos_dia - total_egresos_dia
        
        # Actualizar variables
        self.total_ingresos_dia_var.set(f"${total_ingresos_dia:,.2f}")
        self.total_egresos_dia_var.set(f"${total_egresos_dia:,.2f}")
        self.saldo_dia_var.set(f"${saldo_dia:,.2f}")
        
        # Cambiar color del saldo según sea positivo o negativo
        label_saldo = self.saldo_dia_var._tk.globalgetvar(self.saldo_dia_var._name)
        label_saldo.config(foreground='blue' if saldo_dia >= 0 else 'red')

    def setup_novedades_interface(self, parent):
        """Configura la interfaz de novedades"""
        # Frame principal
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tabla de novedades
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("Fecha", "CC", "Nombre", "Novedad")
        self.novedades_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        # Configurar columnas
        column_widths = {
            "Fecha": 90, "CC": 100, "Nombre": 150, "Novedad": 250
        }
        
        for col in columns:
            self.novedades_tree.column(col, width=column_widths.get(col, 100), anchor=tk.CENTER)
            self.novedades_tree.heading(col, text=col)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.novedades_tree.yview)
        self.novedades_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.novedades_tree.pack(fill=tk.BOTH, expand=True)
        
        # Botones inferiores (alineados a la derecha)
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        inner = ttk.Frame(btn_frame)
        inner.pack(side=tk.RIGHT)
        
        # Botón Agregar Novedad
        ttk.Button(inner, text="➕Agregar", 
                command=self.registrar_novedad).pack(side=tk.LEFT, padx=5)
        
        # Botones de edición/eliminación - solo para Administrativo
        if self.user_role == "Administrativo":
            ttk.Button(inner, text="✏️Editar", 
                    command=self.editar_novedad).pack(side=tk.LEFT, padx=5)
            ttk.Button(inner, text="✖️Eliminar", 
                    command=lambda: self.eliminar_registro_contable('novedades')).pack(side=tk.LEFT, padx=5)
        
        # Actualizar tabla
        self.update_novedades_table()
        
    def setup_incapacidades_interface(self, parent):
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.incapacidad_id_var = tk.StringVar()
        self.incapacidad_nombre_var = tk.StringVar()
        self.incapacidad_eps_var = tk.StringVar()
        self.incapacidad_tipo_var = tk.StringVar()
        self.incapacidad_fecha_inicio_var = tk.StringVar()
        self.incapacidad_fecha_final_var = tk.StringVar()
        self.incapacidad_dias_var = tk.StringVar()
        self.incapacidad_valor_var = tk.StringVar()
        self.incapacidad_fecha_pago_var = tk.StringVar(value="")

        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(search_frame, text="Buscar:").pack(side=tk.LEFT, padx=5)
        busqueda_entry = ttk.Entry(search_frame, textvariable=self.busqueda_var, width=40)
        busqueda_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="🔍Buscar", command=self.buscar_incapacidades).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Mostrar Todos", command=self.update_incapacidades_table).pack(side=tk.LEFT, padx=5)

        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("ID", "Nombre", "EPS", "Tipo", "Fecha Inicio", "Fecha Final", "Días", "Valor", "Fecha Pago", "Estado")
        style = ttk.Style()
        style.configure("Incap.Treeview", font=('Segoe UI', 10))
        style.configure("Incap.Treeview.Heading", font=('Segoe UI', 10, 'bold'))

        self.incapacidades_tree = ttk.Treeview(table_frame, columns=columns, show="headings", style="Incap.Treeview")
        column_widths = {"ID": 50, "Nombre": 150, "EPS": 120, "Tipo": 120, "Fecha Inicio": 90, "Fecha Final": 90, "Días": 50, "Valor": 90, "Fecha Pago": 90, "Estado": 100}
        for col in columns:
            self.incapacidades_tree.column(col, width=column_widths.get(col, 100), anchor=tk.CENTER)
            self.incapacidades_tree.heading(col, text=col)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.incapacidades_tree.yview)
        self.incapacidades_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.incapacidades_tree.pack(fill=tk.BOTH, expand=True)
        self.incapacidades_tree.bind("<Double-1>", lambda e: self.mostrar_detalles_incapacidad())
        self.incapacidades_tree.drop_target_register(DND_FILES)
        self.incapacidades_tree.dnd_bind('<<Drop>>', self.on_drop_incapacidad)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        right_buttons = ttk.Frame(button_frame)
        right_buttons.pack(side=tk.RIGHT)

        ttk.Button(right_buttons, text="➕ Agregar", command=self.registrar_incapacidad).pack(side=tk.LEFT, padx=5)

        if self.user_role == "Administrativo":
            ttk.Button(right_buttons, text="✏️ Editar", command=self.editar_incapacidad).pack(side=tk.LEFT, padx=5)
            ttk.Button(right_buttons, text="✖ Eliminar", command=self.eliminar_incapacidad).pack(side=tk.LEFT, padx=5)
            # Los botones "✅ Pagada" y "⌛ Pendiente" ya no están aquí

        if 'incapacidades' not in self.contabilidad_data:
            self.contabilidad_data['incapacidades'] = []

        self.update_incapacidades_table()
        
    def marcar_incapacidad_pagada(self):
        selected = self.incapacidades_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Seleccione una incapacidad.")
            return
        index = self.incapacidades_tree.index(selected[0])
        registro = self.contabilidad_data['incapacidades'][index]
        self._marcar_incapacidad_pagada(registro)  # sin cerrar ventana
        
    def revertir_incapacidad_pendiente(self):
        selected = self.incapacidades_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Seleccione una incapacidad.")
            return
        index = self.incapacidades_tree.index(selected[0])
        registro = self.contabilidad_data['incapacidades'][index]
        self._marcar_incapacidad_pendiente(registro)  # sin cerrar ventana
        
    def registrar_incapacidad(self):
        """Muestra el formulario para registrar una incapacidad con búsqueda de afiliado"""
        ventana = Toplevel(self.root)
        ventana.title("Registrar Incapacidad")
        ventana.geometry("800x500")
        self.centrar_ventana(ventana, 800, 500) 
        ventana.resizable(False, False)
        
        # Variables
        busqueda_var = tk.StringVar()
        cc_var = tk.StringVar()
        nombre_var = tk.StringVar()
        estado_var = tk.StringVar(value="Estado: No identificado")
        eps_var = tk.StringVar()
        id_var = tk.StringVar(value=str(len(self.contabilidad_data['incapacidades']) + 1))
        tipo_var = tk.StringVar()
        fecha_inicio_var = tk.StringVar()
        fecha_final_var = tk.StringVar()
        dias_var = tk.StringVar()
        valor_var = tk.StringVar()
        # IMPORTANTE: fecha_pago_var DEBE estar vacío por defecto
        fecha_pago_var = tk.StringVar(value="")  # Vacío, NO fecha actual
        estado_pago_var = tk.StringVar(value="Pendiente")  # Nuevo: estado de pago
        
        # Tipos de incapacidad
        tipos_incapacidad = ["Enfermedad General", "Accidente de Trabajo", 
                            "Enfermedad Laboral", "Maternidad"]
        
        # Función para buscar afiliado
        def buscar_afiliado():
            texto_busqueda = busqueda_var.get().lower()
            if not texto_busqueda:
                messagebox.showwarning("Advertencia", "Ingrese un número de cédula o nombre para buscar")
                return
            
            encontrado = False
            
            # Buscar en afiliados activos
            for afiliado in self.data:
                if (texto_busqueda in afiliado['cc'].lower() or 
                    texto_busqueda in afiliado['nombre'].lower()):
                    cc_var.set(afiliado['cc'])
                    nombre_var.set(afiliado['nombre'])
                    eps_var.set(afiliado['eps'])
                    estado_var.set("Estado: Activo")
                    encontrado = True
                    break
            
            # Si no se encontró en activos, buscar en retirados
            if not encontrado:
                for retirado in self.retiros_data:
                    if (texto_busqueda in retirado['cc'].lower() or 
                        texto_busqueda in retirado['nombre'].lower()):
                        cc_var.set(retirado['cc'])
                        nombre_var.set(retirado['nombre'])
                        eps_var.set(retirado['eps'])
                        estado_var.set("Estado: Retirado")
                        encontrado = True
                        break
            
            if not encontrado:
                messagebox.showinfo("Información", "No se encontró ningún afiliado con ese nombre o cédula")
        
        # Función para calcular días automáticamente
        def calcular_dias_automatico(*args):
            try:
                if fecha_inicio_var.get() and fecha_final_var.get():
                    fecha_inicio = datetime.strptime(fecha_inicio_var.get(), "%d/%m/%Y")
                    fecha_final = datetime.strptime(fecha_final_var.get(), "%d/%m/%Y")
                    
                    if fecha_final < fecha_inicio:
                        messagebox.showerror("Error", "La fecha final no puede ser anterior a la fecha de inicio")
                        return
                        
                    dias = (fecha_final - fecha_inicio).days + 1
                    dias_var.set(str(dias))
            except ValueError:
                pass
        
        # Configurar trace para calcular días automáticamente
        fecha_inicio_var.trace("w", calcular_dias_automatico)
        fecha_final_var.trace("w", calcular_dias_automatico)
        
        # Frame principal con configuración de grid
        main_frame = ttk.Frame(ventana)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Título
        ttk.Label(main_frame, text="Registrar Incapacidad", style='Title.TLabel').grid(
            row=0, column=0, columnspan=2, pady=(0, 10))
        
        # ==============================================
        # Sección 1: Búsqueda de afiliado
        # ==============================================
        search_frame = ttk.LabelFrame(main_frame, text="Buscar Afiliado", padding=10)
        search_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        
        ttk.Label(search_frame, text="Buscar por CC o Nombre:").pack(side=tk.LEFT, padx=5)
        busqueda_entry = ttk.Entry(search_frame, textvariable=busqueda_var, width=30)
        busqueda_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(search_frame, text="Buscar", command=buscar_afiliado).pack(side=tk.LEFT, padx=5)
        
        # ==============================================
        # Sección 2: Datos del afiliado (izquierda)
        # ==============================================
        afiliado_frame = ttk.LabelFrame(main_frame, text="Datos del Afiliado", padding=10)
        afiliado_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        
        # Campos de información del afiliado (solo lectura)
        ttk.Label(afiliado_frame, text="CC:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(afiliado_frame, textvariable=cc_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(afiliado_frame, text="Nombre:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(afiliado_frame, textvariable=nombre_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(afiliado_frame, text="EPS:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(afiliado_frame, textvariable=eps_var).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(afiliado_frame, textvariable=estado_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        # ==============================================
        # Sección 3: Datos de la incapacidad (derecha)
        # ==============================================
        incapacidad_frame = ttk.LabelFrame(main_frame, text="Datos de la Incapacidad", padding=10)
        incapacidad_frame.grid(row=2, column=1, sticky="nsew", padx=5, pady=5)
        
        # Campos de la incapacidad
        self.create_form_field(incapacidad_frame, "ID:", id_var, 0, state='readonly')
        self.create_combobox_field(incapacidad_frame, "Tipo*:", tipo_var, tipos_incapacidad, 1, required=True)
        self.create_form_field(incapacidad_frame, "Fecha Inicio*:", fecha_inicio_var, 2, required=True)
        self.create_form_field(incapacidad_frame, "Fecha Final*:", fecha_final_var, 3, required=True)
        self.create_form_field(incapacidad_frame, "Días:", dias_var, 4, state='readonly')
        self.create_form_field(incapacidad_frame, "Valor a Pagar*:", valor_var, 5, required=True)
        
        # Fecha de pago - AHORA ESTÁ VACÍA POR DEFECTO
        self.create_form_field(incapacidad_frame, "Fecha de Pago:", fecha_pago_var, 6)
        
        # Nuevo: Estado de pago (solo lectura)
        ttk.Label(incapacidad_frame, text="Estado:").grid(row=7, column=0, sticky=tk.W, padx=5, pady=2)
        estado_label = ttk.Label(incapacidad_frame, textvariable=estado_pago_var, 
                                font=('Arial', 10, 'bold'))
        estado_label.grid(row=7, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Validación para que el valor no tenga decimales
        def validar_valor(*args):
            valor = valor_var.get()
            if '.' in valor:
                valor_var.set(valor.split('.')[0])
        
        valor_var.trace("w", validar_valor)
        
        # ==============================================
        # Botones en la parte inferior
        # ==============================================
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(button_frame, text="Cancelar", command=ventana.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Guardar", 
                command=lambda: self.guardar_incapacidad(
                    id_var.get(), nombre_var.get(), eps_var.get(), 
                    tipo_var.get(), fecha_inicio_var.get(), 
                    fecha_final_var.get(), dias_var.get(), 
                    valor_var.get(), fecha_pago_var.get(), 
                    ventana)).pack(side=tk.LEFT, padx=5)
        
        # Configurar pesos de las columnas para que se expandan
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
    def guardar_incapacidad(self, id_incap, nombre, eps, tipo, fecha_inicio, fecha_final, dias, valor, fecha_pago, ventana):
        if not nombre or not eps or not tipo or not fecha_inicio or not fecha_final or not valor:
            messagebox.showerror("Error", "Los campos marcados con * son obligatorios")
            return
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, "%d/%m/%Y")
            fecha_final_dt = datetime.strptime(fecha_final, "%d/%m/%Y")
            fecha_inicio_str = fecha_inicio_dt.strftime("%Y-%m-%d")
            fecha_final_str = fecha_final_dt.strftime("%Y-%m-%d")
            if fecha_final_dt < fecha_inicio_dt:
                messagebox.showerror("Error", "La fecha final no puede ser anterior a la fecha de inicio")
                return
        except ValueError:
            messagebox.showerror("Error", "Formato de fecha incorrecto. Use dd/mm/aaaa")
            return
        try:
            valor_int = int(float(valor))
        except ValueError:
            messagebox.showerror("Error", "El valor debe ser un número entero")
            return
        
        fecha_pago_str = None
        if fecha_pago and fecha_pago.strip():
            try:
                fecha_pago_dt = datetime.strptime(fecha_pago, "%d/%m/%Y")
                fecha_pago_str = fecha_pago_dt.strftime("%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Error", "Formato de fecha de pago incorrecto. Use dd/mm/aaaa")
                return
        
        data = {
            "nombre": nombre,
            "eps": eps,
            "tipo": tipo,
            "fecha_inicio": fecha_inicio_str,
            "fecha_final": fecha_final_str,
            "dias": dias,
            "valor": valor_int,
            "fecha_pago": fecha_pago_str,
            "estado": "Pagada" if fecha_pago_str else "Pendiente"
        }
        new_id = self.db.add_incapacidad(data)
        data['id'] = new_id
        self.contabilidad_data['incapacidades'].append(data)

        # === AUDITORÍA ===
        self._registrar_auditoria("Agregó incapacidad", "Incapacidades", "Éxito", f"ID {new_id}")

        # Agregar novedad automática
        cc_afiliado = ""
        for afiliado in self.data:
            if afiliado['nombre'] == nombre:
                cc_afiliado = afiliado['cc']
                break
        if not cc_afiliado:
            for retirado in self.retiros_data:
                if retirado['nombre'] == nombre:
                    cc_afiliado = retirado['cc']
                    break
        novedad_data = {
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "cc": cc_afiliado if cc_afiliado else "-/-",
            "nombre": nombre,
            "novedad": f"{tipo} - {'Pagada' if fecha_pago_str else 'Pendiente'}"
        }
        nov_id = self.db.add_novedad(novedad_data)
        novedad_data['id'] = nov_id
        self.contabilidad_data['novedades'].append(novedad_data)
        self.update_incapacidades_table()
        self.update_novedades_table()
        ventana.destroy()
        self.mostrar_toast("Incapacidad registrada correctamente")
        self.refrescar_sistema(silent=True)
        
    def editar_incapacidad(self):
        """Permite editar una incapacidad seleccionada con un diseño profesional horizontal"""
        selected_item = self.incapacidades_tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Por favor seleccione una incapacidad para editar")
            return
            
        # Obtener datos del registro seleccionado
        index = self.incapacidades_tree.index(selected_item[0])
        registro = self.contabilidad_data['incapacidades'][index]
        
        # Crear ventana de edición
        ventana = Toplevel(self.root)
        ventana.title("Editar Incapacidad")
        ventana.geometry("900x500")
        self.centrar_ventana(ventana, 900, 500) 
        ventana.resizable(False, False)
        
        # Variables
        id_var = tk.StringVar(value=registro['id'])
        nombre_var = tk.StringVar(value=registro['nombre'])
        eps_var = tk.StringVar(value=registro['eps'])
        tipo_var = tk.StringVar(value=registro['tipo'])
        fecha_inicio_var = tk.StringVar(value=datetime.strptime(registro['fecha_inicio'], "%Y-%m-%d").strftime("%d/%m/%Y"))
        fecha_final_var = tk.StringVar(value=datetime.strptime(registro['fecha_final'], "%Y-%m-%d").strftime("%d/%m/%Y"))
        dias_var = tk.StringVar(value=registro['dias'])
        valor_var = tk.StringVar(value=str(registro['valor']))
        # En editar_incapacidad, cambiar esta línea:
        fecha_pago_var = tk.StringVar(value=datetime.strptime(registro['fecha_pago'], "%Y-%m-%d").strftime("%d/%m/%Y") if 
                                      registro['fecha_pago'] else "")
        
        # Tipos de incapacidad
        tipos_incapacidad = ["Enfermedad General", "Accidente de Trabajo", "Enfermedad Laboral", "Maternidad"]
        
        # Frame principal con padding
        main_frame = ttk.Frame(ventana, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título con estilo
        ttk.Label(main_frame, text="Editar Incapacidad", 
                font=("Helvetica", 16, "bold")).grid(row=0, column=0, columnspan=4, pady=(0, 20))
        
        # ==============================================
        # Sección 1: Información del Afiliado (izquierda)
        # ==============================================
        afiliado_frame = ttk.LabelFrame(main_frame, text=" Información del Afiliado ", padding=15)
        afiliado_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        
        # Campos del afiliado
        self.create_form_field(afiliado_frame, "ID Incapacidad:", id_var, 0, state='readonly', width=20)
        self.create_form_field(afiliado_frame, "Nombre Completo*:", nombre_var, 1, width=30, required=True)
        self.create_combobox_field(afiliado_frame, "EPS*:", eps_var, self.eps_options, 2, required=True, width=28)
        
        # ==============================================
        # Sección 2: Detalles de la Incapacidad (derecha)
        # ==============================================
        incapacidad_frame = ttk.LabelFrame(main_frame, text=" Detalles de la Incapacidad ", padding=15)
        incapacidad_frame.grid(row=1, column=2, columnspan=2, padx=10, pady=5, sticky="nsew")
        
        # Campos de la incapacidad
        self.create_combobox_field(incapacidad_frame, "Tipo de Incapacidad*:", tipo_var, tipos_incapacidad, 0, required=True, width=25)
        
        # Frame para fechas (organización horizontal)
        fecha_frame = ttk.Frame(incapacidad_frame)
        fecha_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")
        
        self.create_form_field(fecha_frame, "Fecha Inicio* (dd/mm/aaaa):", fecha_inicio_var, 0, required=True, width=15)
        ttk.Label(fecha_frame, text="   a   ").grid(row=0, column=1, padx=5)
        self.create_form_field(fecha_frame, "Fecha Final* (dd/mm/aaaa):", fecha_final_var, 2, required=True, width=15)
        
        # Botón para calcular días
        ttk.Button(incapacidad_frame, text="Calcular Días Automáticamente", 
                command=lambda: self.calcular_dias_incapacidad(
                    fecha_inicio_var, fecha_final_var, dias_var),
                style='Accent.TButton').grid(row=2, column=0, columnspan=2, pady=(5, 10), sticky="ew")
        
        self.create_form_field(incapacidad_frame, "Días de Incapacidad:", dias_var, 3, state='readonly', width=10)
        self.create_form_field(incapacidad_frame, "Valor a Pagar* ($):", valor_var, 4, required=True, width=20)
        self.create_form_field(incapacidad_frame, "Fecha de Pago (dd/mm/aaaa):", fecha_pago_var, 5, width=15)
        
        # ==============================================
        # Sección 3: Botones de acción (parte inferior)
        # ==============================================
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=4, pady=(20, 0))
        
        # Botón Cancelar
        cancel_btn = ttk.Button(
            button_frame, 
            text="Cancelar", 
            command=ventana.destroy,
            style='Secondary.TButton'
        )
        cancel_btn.pack(side=tk.RIGHT, padx=10)
        
        # Botón Guardar
        save_btn = ttk.Button(
            button_frame, 
            text="Guardar Cambios", 
            command=lambda: self.actualizar_incapacidad(
                index, id_var.get(), nombre_var.get(), eps_var.get(), 
                tipo_var.get(), fecha_inicio_var.get(), 
                fecha_final_var.get(), dias_var.get(), 
                valor_var.get(), fecha_pago_var.get(), 
                ventana),
            style='Accent.TButton'
        )
        save_btn.pack(side=tk.RIGHT)
        
        # Configurar pesos para que los frames se expandan
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=1)
        main_frame.columnconfigure(3, weight=1)
        afiliado_frame.columnconfigure(1, weight=1)
        incapacidad_frame.columnconfigure(1, weight=1)
        
        # Añadir validación para el valor numérico
        def validar_valor(*args):
            valor = valor_var.get()
            if valor and not valor.isdigit():
                valor_var.set(''.join(filter(str.isdigit, valor)))
        
        valor_var.trace("w", validar_valor)
        
        # Función para calcular días al cambiar fechas
        def calcular_dias_automatico(*args):
            try:
                fecha_inicio = datetime.strptime(fecha_inicio_var.get(), "%d/%m/%Y")
                fecha_final = datetime.strptime(fecha_final_var.get(), "%d/%m/%Y")
                
                if fecha_final < fecha_inicio:
                    messagebox.showerror("Error", "La fecha final no puede ser anterior a la fecha de inicio")
                    return
                    
                dias = (fecha_final - fecha_inicio).days + 1  # +1 para incluir ambos días
                dias_var.set(str(dias))
            except ValueError:
                pass  # Ignorar errores mientras se está escribiendo
        
        fecha_inicio_var.trace("w", calcular_dias_automatico)
        fecha_final_var.trace("w", calcular_dias_automatico)

    def actualizar_incapacidad(self, index, id_incap, nombre, eps, tipo, fecha_inicio, 
                                fecha_final, dias, valor, fecha_pago, ventana):
        errors = []
        
        if not nombre:
            errors.append("El nombre es obligatorio")
        if not eps:
            errors.append("La EPS es obligatoria")
        if not tipo:
            errors.append("El tipo de incapacidad es obligatorio")
        
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, "%d/%m/%Y")
            fecha_inicio_str = fecha_inicio_dt.strftime("%Y-%m-%d")
            fecha_final_dt = datetime.strptime(fecha_final, "%d/%m/%Y")
            fecha_final_str = fecha_final_dt.strftime("%Y-%m-%d")
            if fecha_final_dt < fecha_inicio_dt:
                errors.append("La fecha final no puede ser anterior a la fecha de inicio")
        except ValueError:
            errors.append("Formato de fecha incorrecto. Use dd/mm/aaaa")
        
        try:
            valor_int = int(float(valor))
            if valor_int <= 0:
                errors.append("El valor debe ser positivo")
        except ValueError:
            errors.append("El valor debe ser un número entero válido")
        
        fecha_pago_str = None
        if fecha_pago:
            try:
                fecha_pago_dt = datetime.strptime(fecha_pago, "%d/%m/%Y")
                fecha_pago_str = fecha_pago_dt.strftime("%Y-%m-%d")
            except ValueError:
                errors.append("Formato de fecha de pago incorrecto. Use dd/mm/aaaa")
        
        if errors:
            messagebox.showerror("Errores de Validación", "\n".join(errors))
            return
        
        data = {
            "nombre": nombre,
            "eps": eps,
            "tipo": tipo,
            "fecha_inicio": fecha_inicio_str,
            "fecha_final": fecha_final_str,
            "dias": dias,
            "valor": valor_int,
            "fecha_pago": fecha_pago_str or datetime.now().strftime("%Y-%m-%d")
        }
        
        registro_id = self.contabilidad_data['incapacidades'][index]['id']
        self.db.update_incapacidad(registro_id, data)
        self.contabilidad_data['incapacidades'][index] = data

        # === AUDITORÍA ===
        self._registrar_auditoria("Editó incapacidad", "Incapacidades", "Éxito", f"ID {registro_id}")

        # Sincronizar novedad...
        novedad_actualizada = False
        for i, nov in enumerate(self.contabilidad_data['novedades']):
            if nov['nombre'] == nombre and nov.get('novedad') in [
                "Enfermedad General", "Accidente de Trabajo", "Enfermedad Laboral", "Maternidad"
            ]:
                self.contabilidad_data['novedades'][i]['novedad'] = tipo
                self.db.update_novedad(nov['id'], self.contabilidad_data['novedades'][i])
                novedad_actualizada = True
                break
        
        if not novedad_actualizada:
            cc_afiliado = ""
            for afiliado in self.data:
                if afiliado['nombre'] == nombre:
                    cc_afiliado = afiliado['cc']
                    break
            if not cc_afiliado:
                for retirado in self.retiros_data:
                    if retirado['nombre'] == nombre:
                        cc_afiliado = retirado['cc']
                        break
            novedad_data = {
                "fecha": datetime.now().strftime("%Y-%m-%d"),
                "cc": cc_afiliado if cc_afiliado else "-/-",
                "nombre": nombre,
                "novedad": tipo
            }
            new_id = self.db.add_novedad(novedad_data)
            novedad_data['id'] = new_id
            self.contabilidad_data['novedades'].append(novedad_data)
        
        self.update_incapacidades_table()
        self.update_novedades_table()
        ventana.destroy()
        self.mostrar_toast("Incapacidad actualizada correctamente")
        self.refrescar_sistema(silent=True)
        
    def eliminar_incapacidad(self):
        selected_item = self.incapacidades_tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Por favor seleccione una incapacidad para eliminar")
            return
        if not self.validar_password():
            return

        index = self.incapacidades_tree.index(selected_item[0])
        registro = self.contabilidad_data['incapacidades'][index]
        registro_id = registro['id']
        archivo = registro.get('archivo')
        cc = registro.get('cedula', registro.get('cc', ''))

        if archivo:
            confirm_msg = (f"¿Está seguro de eliminar esta incapacidad?\n\n"
                        f"Nombre: {registro['nombre']}\n"
                        f"Tipo: {registro['tipo']}\n"
                        f"Archivo: {archivo}\n\n"
                        f"⚠️ La carpeta de esta incapacidad también será eliminada permanentemente.")
        else:
            confirm_msg = (f"¿Está seguro de eliminar esta incapacidad?\n\n"
                        f"Nombre: {registro['nombre']}\n"
                        f"Tipo: {registro['tipo']}\n\n"
                        f"(Esta incapacidad no tiene archivos adjuntos).")

        if not messagebox.askyesno("Confirmar eliminación", confirm_msg, icon=messagebox.WARNING):
            return

        if cc:
            carpeta_incapacidad = os.path.join(BASE_PATH, "Incapacidades", cc, str(registro_id))
            if os.path.exists(carpeta_incapacidad):
                try:
                    shutil.rmtree(carpeta_incapacidad)
                    print(f"✅ Carpeta de incapacidad eliminada: {carpeta_incapacidad}")
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo eliminar la carpeta de la incapacidad:\n{str(e)}")

        if archivo:
            ruta_raiz = os.path.join(BASE_PATH, "Incapacidades", cc, archivo)
            if os.path.exists(ruta_raiz):
                try:
                    os.remove(ruta_raiz)
                    print(f"✅ Archivo raíz eliminado: {ruta_raiz}")
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo eliminar el archivo raíz:\n{str(e)}")

        self.db.delete_incapacidad(registro_id)
        del self.contabilidad_data['incapacidades'][index]

        # === AUDITORÍA ===
        self._registrar_auditoria("Eliminó incapacidad", "Incapacidades", "Éxito", f"ID {registro_id}")

        self.update_incapacidades_table()
        self.mostrar_toast("Incapacidad eliminada correctamente.")
        self.refrescar_sistema(silent=True)
            
    def buscar_incapacidades(self):
        """Busca incapacidades según los criterios especificados"""
        texto_busqueda = self.busqueda_var.get().lower()
        
        if not texto_busqueda:
            self.update_incapacidades_table()
            return
            
        resultados = []
        
        for incapacidad in self.contabilidad_data['incapacidades']:
            if (texto_busqueda in incapacidad['id'].lower() or 
                texto_busqueda in incapacidad['nombre'].lower() or
                texto_busqueda in incapacidad['eps'].lower()):
                resultados.append(incapacidad)
        
        self.update_incapacidades_table(resultados)

    def update_incapacidades_table(self, data=None):
        """Actualiza la tabla de incapacidades con los datos proporcionados o todos los datos."""
        self.clear_treeview(self.incapacidades_tree)

        data_to_show = data if data is not None else self.contabilidad_data.get('incapacidades', [])

        for registro in data_to_show:
            estado = registro.get('estado', 'Recibida')
            if estado == 'Pagada':
                estado_icon = "✅ Pagada"
            elif estado == 'En Revisión':
                estado_icon = "🔄 En Revisión"
            else:
                estado_icon = "⏳ Recibida"

            tiene_archivo = "📎" if registro.get('archivo') else ""
            estado_completo = f"{estado_icon} {tiene_archivo}".strip()

            self.incapacidades_tree.insert("", tk.END, values=(
                registro.get('id', ''),
                registro.get('nombre', ''),
                registro.get('eps', ''),
                registro.get('tipo', ''),
                registro.get('fecha_inicio', ''),
                registro.get('fecha_final', ''),
                registro.get('dias', 0),
                f"${float(registro.get('valor', 0)):,.0f}",
                registro.get('fecha_pago', ''),  # Vacío si no está pagada
                estado_completo
            ))

    def mostrar_detalles_incapacidad(self):
        """Muestra los detalles de la incapacidad seleccionada con dos paneles (datos + archivos)."""
        selected_item = self.incapacidades_tree.selection()
        if not selected_item:
            return

        index = self.incapacidades_tree.index(selected_item[0])
        if index >= len(self.contabilidad_data['incapacidades']):
            return
        registro = self.contabilidad_data['incapacidades'][index]
        cc = registro.get('cedula', registro.get('cc', ''))
        id_incap = registro.get('id')

        if not cc:
            for af in self.data + self.retiros_data:
                if af['nombre'] == registro['nombre']:
                    cc = af['cc']
                    break

        # === Ruta de la carpeta de la incapacidad ===
        carpeta_incapacidad = os.path.join(BASE_PATH, "Incapacidades", cc, str(id_incap))
        # Migrar archivo principal si está en la raíz del afiliado
        if registro.get('archivo'):
            archivo_principal = registro['archivo']
            ruta_raiz = os.path.join(BASE_PATH, "Incapacidades", cc, archivo_principal)
            ruta_subcarpeta = os.path.join(carpeta_incapacidad, archivo_principal)
            if os.path.exists(ruta_raiz) and not os.path.exists(ruta_subcarpeta):
                os.makedirs(carpeta_incapacidad, exist_ok=True)
                try:
                    shutil.move(ruta_raiz, ruta_subcarpeta)
                except Exception as e:
                    print(f"Error al mover archivo: {e}")

        detalles_window = Toplevel(self.root)
        detalles_window.title(f"Detalles de Incapacidad - {registro['nombre']}")
        detalles_window.geometry("1000x500")
        detalles_window.resizable(False, False)
        self.centrar_ventana(detalles_window, 1000, 500)

        paned = ttk.PanedWindow(detalles_window, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Panel izquierdo: Datos
        left_frame = ttk.Frame(paned, padding=10)
        paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Datos del Afiliado", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0,5))
        ttk.Label(left_frame, text=f"Nombre: {registro['nombre']}", font=('Segoe UI', 10)).pack(anchor=tk.W)
        ttk.Label(left_frame, text=f"Cédula: {cc if cc else 'No disponible'}", font=('Segoe UI', 10)).pack(anchor=tk.W)
        ttk.Label(left_frame, text=f"EPS: {registro.get('eps', 'No registrada')}", font=('Segoe UI', 10)).pack(anchor=tk.W)
        ttk.Separator(left_frame, orient='horizontal').pack(fill=tk.X, pady=8)

        ttk.Label(left_frame, text="Detalles de la Incapacidad", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0,5))

        try:
            f_ini = datetime.strptime(registro.get('fecha_inicio', ''), "%Y-%m-%d").strftime("%d/%m/%Y")
        except:
            f_ini = registro.get('fecha_inicio', '')
        try:
            f_fin = datetime.strptime(registro.get('fecha_final', ''), "%Y-%m-%d").strftime("%d/%m/%Y")
        except:
            f_fin = registro.get('fecha_final', '')

        estado = registro.get('estado', 'Recibida')
        if estado == 'Pagada':
            estado_texto = "✅ Pagada"
        elif estado == 'En Revisión':
            estado_texto = "🔄 En Revisión"
        else:
            estado_texto = "⏳ Recibida"

        detalles = [
            ("ID:", registro.get('id', '')),
            ("Tipo:", registro.get('tipo', 'No especificado')),
            ("Fecha Inicio:", f_ini),
            ("Fecha Final:", f_fin),
            ("Días:", registro.get('dias', 0)),
            ("Valor a Pagar:", f"${float(registro.get('valor', 0)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
            ("Estado:", estado_texto),
            ("Fecha Pago:", registro.get('fecha_pago', 'No pagada')),
        ]
        for campo, valor in detalles:
            frame = ttk.Frame(left_frame)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=campo, font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=5)
            ttk.Label(frame, text=valor, font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=5)

        if self.user_role == "Administrativo":
            btn_acciones = ttk.Frame(left_frame)
            btn_acciones.pack(fill=tk.X, pady=10)
            ttk.Button(btn_acciones, text="✏️ Editar",
                    command=lambda: [self.editar_incapacidad(), detalles_window.destroy()]).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_acciones, text="✖️ Eliminar",
                    command=lambda: [self.eliminar_incapacidad(), detalles_window.destroy()]).pack(side=tk.LEFT, padx=5)

        # Panel derecho: Archivos
        right_frame = ttk.Frame(paned, padding=10)
        paned.add(right_frame, weight=1)

        ttk.Label(right_frame, text="📁 Archivos Adjuntos", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0,5))

        tree_archivos = ttk.Treeview(right_frame, columns=("Archivo",), show="headings", height=6)
        tree_archivos.heading("Archivo", text="Nombre del archivo")
        tree_archivos.column("Archivo", width=280, anchor=tk.W)
        tree_archivos.pack(fill=tk.BOTH, expand=True, pady=5)

        scroll_arch = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=tree_archivos.yview)
        tree_archivos.configure(yscrollcommand=scroll_arch.set)
        scroll_arch.pack(side=tk.RIGHT, fill=tk.Y)

        def actualizar_lista_archivos():
            for item in tree_archivos.get_children():
                tree_archivos.delete(item)
            if not cc or not id_incap:
                return
            carpeta = os.path.join(BASE_PATH, "Incapacidades", cc, str(id_incap))
            if os.path.exists(carpeta):
                for f in os.listdir(carpeta):
                    tree_archivos.insert("", tk.END, values=(f,))

        def eliminar_archivo_seleccionado():
            if not cc or not id_incap:
                messagebox.showerror("Error", "No se puede identificar la carpeta de la incapacidad.")
                return
            seleccion = tree_archivos.selection()
            if not seleccion:
                messagebox.showinfo("Selección", "Seleccione un archivo para eliminar.")
                return
            nombre = tree_archivos.item(seleccion[0], 'values')[0]
            carpeta = os.path.join(BASE_PATH, "Incapacidades", cc, str(id_incap))
            ruta_completa = os.path.join(carpeta, nombre)
            if not os.path.exists(ruta_completa):
                messagebox.showerror("Error", "El archivo no existe en el sistema.")
                return
            if messagebox.askyesno("Confirmar eliminación",
                                f"¿Está seguro de eliminar el archivo '{nombre}'?\n\nEsta acción no se puede deshacer."):
                try:
                    os.remove(ruta_completa)
                    messagebox.showinfo("Éxito", f"Archivo '{nombre}' eliminado correctamente.")
                    actualizar_lista_archivos()
                    # Si el archivo eliminado era el principal, actualizar registro
                    if registro.get('archivo') == nombre:
                        registro['archivo'] = None
                        self.db.update_incapacidad(registro['id'], registro)
                        self.update_incapacidades_table()
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo eliminar el archivo:\n{str(e)}")

        btn_archivos = ttk.Frame(right_frame)
        btn_archivos.pack(fill=tk.X, pady=5)

        def subir_archivo_adicional():
            if not cc or not id_incap:
                messagebox.showerror("Error", "No se puede identificar la carpeta de la incapacidad.")
                return
            ruta = filedialog.askopenfilename(
                title="Seleccionar archivo para adjuntar",
                filetypes=[("Todos los archivos", "*.*"), ("PDF", "*.pdf"), ("Imágenes", "*.jpg *.png")]
            )
            if not ruta:
                return
            carpeta = os.path.join(BASE_PATH, "Incapacidades", cc, str(id_incap))
            os.makedirs(carpeta, exist_ok=True)
            nombre = os.path.basename(ruta)
            destino = os.path.join(carpeta, nombre)
            try:
                shutil.copy2(ruta, destino)
                messagebox.showinfo("Éxito", f"Archivo '{nombre}' subido correctamente.")
                actualizar_lista_archivos()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo subir el archivo: {str(e)}")

        def ver_archivo_seleccionado():
            if not cc or not id_incap:
                messagebox.showerror("Error", "No se puede identificar la carpeta de la incapacidad.")
                return
            seleccion = tree_archivos.selection()
            if not seleccion:
                messagebox.showinfo("Selección", "Seleccione un archivo para ver.")
                return
            nombre = tree_archivos.item(seleccion[0], 'values')[0]
            carpeta = os.path.join(BASE_PATH, "Incapacidades", cc, str(id_incap))
            ruta_completa = os.path.join(carpeta, nombre)
            if os.path.exists(ruta_completa):
                try:
                    if sys.platform == "win32":
                        os.startfile(ruta_completa)
                    else:
                        subprocess.Popen(['open', ruta_completa] if sys.platform == 'darwin' else ['xdg-open', ruta_completa])
                    # Cambiar estado a "En Revisión" si es "Recibida"
                    if registro.get('estado') == 'Recibida':
                        registro['estado'] = 'En Revisión'
                        registro['fecha_estado'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        self.db.update_incapacidad(registro['id'], registro)
                        self.update_incapacidades_table()
                        messagebox.showinfo("Estado actualizado", "La incapacidad ha pasado a estado 'En Revisión'.")
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo abrir el archivo: {str(e)}")
            else:
                messagebox.showerror("Error", "El archivo no existe en el sistema.")

        ttk.Button(btn_archivos, text="📤 Subir Archivo", command=subir_archivo_adicional).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_archivos, text="👁️ Ver Archivo", command=ver_archivo_seleccionado).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_archivos, text="🗑️ Borrar Archivo", command=eliminar_archivo_seleccionado).pack(side=tk.LEFT, padx=5)

        if self.user_role == "Administrativo":
            ttk.Button(btn_archivos, text="✅ Pagada",
                    command=lambda: self._marcar_incapacidad_pagada(registro, detalles_window)).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_archivos, text="⌛ Pendiente",
                    command=lambda: self._marcar_incapacidad_pendiente(registro, detalles_window)).pack(side=tk.LEFT, padx=5)

        ttk.Button(detalles_window, text="Cerrar", command=detalles_window.destroy).pack(pady=10)
        actualizar_lista_archivos()
        
    def _marcar_incapacidad_pagada(self, registro, cerrar_ventana=None):
        from tkinter import simpledialog
        valor_actual = float(registro.get('valor', 0))
        nuevo_valor = simpledialog.askfloat(
            "Valor pagado",
            f"Ingrese el valor pagado para la incapacidad de {registro['nombre']}:",
            initialvalue=valor_actual,
            parent=self.root,
            minvalue=0
        )
        if nuevo_valor is None:
            return

        fecha_pago_actual = datetime.now().strftime("%Y-%m-%d")
        registro['fecha_pago'] = fecha_pago_actual
        registro['valor'] = nuevo_valor
        registro['estado'] = 'Pagada'
        registro['fecha_estado'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.db.update_incapacidad(registro['id'], registro)
        self._actualizar_novedad_incapacidad(registro, f"{registro['tipo']} - Pagada ({fecha_pago_actual})")

        # === AUDITORÍA ===
        self._registrar_auditoria("Marcó incapacidad como pagada", "Incapacidades", "Éxito", f"ID {registro['id']}")

        self.update_incapacidades_table()
        self.update_novedades_table()

        if cerrar_ventana:
            cerrar_ventana.destroy()
        self.mostrar_toast(f"Incapacidad de {registro['nombre']} marcada como pagada. Valor: ${nuevo_valor:,.2f}", duracion=4000)
        self.refrescar_sistema(silent=True)
        
    def _marcar_incapacidad_pendiente(self, registro, cerrar_ventana=None):
        if not registro.get('fecha_pago'):
            messagebox.showinfo("Información", "Esta incapacidad ya está en estado Pendiente.")
            return
        if not messagebox.askyesno("Confirmar reversión",
                                f"¿Reactivar la incapacidad de {registro['nombre']} a estado PENDIENTE?"):
            return
        registro['fecha_pago'] = None
        registro['estado'] = 'Recibida'
        registro['fecha_estado'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.db.update_incapacidad(registro['id'], registro)
        self._actualizar_novedad_incapacidad(registro, registro['tipo'])

        # === AUDITORÍA ===
        self._registrar_auditoria("Marcó incapacidad como pendiente", "Incapacidades", "Éxito", f"ID {registro['id']}")

        self.update_incapacidades_table()
        self.update_novedades_table()
        if cerrar_ventana:
            cerrar_ventana.destroy()
        self.mostrar_toast(f"Incapacidad de {registro['nombre']} revertida a estado Recibida.")
        self.refrescar_sistema(silent=True)
        
    def _actualizar_novedad_incapacidad(self, registro, nuevo_texto):
        """Busca y actualiza la novedad asociada a una incapacidad."""
        for nov in self.contabilidad_data['novedades']:
            if nov['nombre'] == registro['nombre'] and registro['tipo'] in nov.get('novedad', ''):
                nov['novedad'] = nuevo_texto
                self.db.update_novedad(nov['id'], nov)
                break
            
    def _marcar_incapacidad_pendiente(self, registro, cerrar_ventana=None):
        """Revierte una incapacidad pagada a pendiente (elimina fecha de pago)."""
        if not registro.get('fecha_pago'):
            messagebox.showinfo("Información", "Esta incapacidad ya está en estado Pendiente.")
            return

        # Confirmar
        if not messagebox.askyesno("Confirmar reversión",
                                f"¿Reactivar la incapacidad de {registro['nombre']} a estado PENDIENTE?"):
            return

        registro['fecha_pago'] = None
        registro['estado'] = 'Pendiente'

        self.db.update_incapacidad(registro['id'], registro)

        # Actualizar novedad
        self._actualizar_novedad_incapacidad(registro, registro['tipo'])  # Solo el tipo

        self.update_incapacidades_table()
        self.update_novedades_table()

        if cerrar_ventana:
            cerrar_ventana.destroy()

        messagebox.showinfo("Éxito", f"Incapacidad de {registro['nombre']} revertida a Pendiente.")

    def _actualizar_novedad_incapacidad(self, registro, nuevo_texto):
        """Busca y actualiza la novedad asociada a una incapacidad."""
        for nov in self.contabilidad_data['novedades']:
            if nov['nombre'] == registro['nombre'] and registro['tipo'] in nov.get('novedad', ''):
                nov['novedad'] = nuevo_texto
                self.db.update_novedad(nov['id'], nov)
                break
        
    def gestionar_documentos_incapacidad(self, registro):
        """Muestra opciones para gestionar documentos de la incapacidad"""
        # Crear ventana emergente
        docs_window = Toplevel(self.root)
        docs_window.title(f"Documentos de Incapacidad - {registro['nombre']}")
        docs_window.geometry("400x200")
        
        # Frame principal
        main_frame = ttk.Frame(docs_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Título
        ttk.Label(main_frame, text=f"Documentos de Incapacidad", 
                style='Title.TLabel').pack(pady=(0, 20))
        
        # Botones
        ttk.Button(main_frame, text="⬆️ Subir Documentos", 
                command=lambda: self.subir_documentos_incapacidad(registro),
                width=20).pack(pady=10)
        
        ttk.Button(main_frame, text="👁️ Ver Documentos", 
                command=lambda: self.ver_documentos_incapacidad(registro),
                width=20).pack(pady=10)
        
        ttk.Button(main_frame, text="↩️ Cerrar", 
                command=docs_window.destroy).pack(pady=10)

    def subir_documentos_incapacidad(self, registro):
        """Permite subir documentos relacionados con la incapacidad"""
        from tkinter import filedialog
        import os
        from shutil import copy2
        from tkinter import messagebox
        
        cedula = registro.get('cedula', registro['id'])
        base_path = os.path.join(BASE_PATH, "Incapacidades")
        empleado_path = os.path.join(base_path, cedula)
        os.makedirs(empleado_path, exist_ok=True)
        
        filepaths = filedialog.askopenfilenames(
            title="Seleccionar documentos de incapacidad",
            filetypes=[("Todos los archivos", "*.*"), 
                    ("PDF", "*.pdf"), 
                    ("Imágenes", "*.jpg *.png *.jpeg")]
        )
        
        if filepaths:
            for filepath in filepaths:
                filename = os.path.basename(filepath)
                dest_path = os.path.join(empleado_path, filename)
                copy2(filepath, dest_path)
            
            messagebox.showinfo("Éxito", f"Se subieron {len(filepaths)} documentos a:\n{empleado_path}")

    def ver_documentos_incapacidad(self, registro):
        """Abre la carpeta con los documentos de la incapacidad"""
        import os
        import subprocess
        from tkinter import messagebox
        
        cedula = registro.get('cedula', registro['id'])
        empleado_path = os.path.join(BASE_PATH, "Incapacidades", cedula)
        
        if os.path.exists(empleado_path):
            try:
                if os.name == 'nt':
                    os.startfile(empleado_path)
                elif os.name == 'posix':
                    subprocess.run(['open', empleado_path] if sys.platform == 'darwin' else ['xdg-open', empleado_path])
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir la carpeta:\n{str(e)}")
        else:
            messagebox.showwarning("No hay documentos", f"No se encontraron documentos para la cédula {cedula}")
            
    def setup_monitoreo_interface(self, parent):
        """Configura la interfaz de monitoreo de pagos"""
        # Frame principal
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Label(main_frame, text="Monitoreo", style='Title.TLabel').pack(pady=(0, 10))
        
        # Variables para búsqueda
        self.busqueda_monitoreo_var = tk.StringVar()
        
        # Controles superiores (búsqueda + botones derechos)
        top_controls = ttk.Frame(main_frame)
        top_controls.pack(fill=tk.X, pady=(0, 10))
        
        # Parte izquierda: búsqueda
        left_controls = ttk.Frame(top_controls)
        left_controls.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(left_controls, text="Buscar:").pack(side=tk.LEFT, padx=5)
        busqueda_entry = ttk.Entry(left_controls, textvariable=self.busqueda_monitoreo_var, width=40)
        busqueda_entry.pack(side=tk.LEFT, padx=5)
        busqueda_entry.bind('<KeyRelease>', lambda e: self.buscar_en_monitoreo())
        
        ttk.Button(left_controls, text="Mostrar Todos", 
                command=self.update_monitoreo_table).pack(side=tk.LEFT, padx=5)
        
        # Parte derecha: Actualizar Estados y toggle
        right_controls = ttk.Frame(top_controls)
        right_controls.pack(side=tk.RIGHT, padx=5)
        
        # Botón Actualizar Estados
        ttk.Button(right_controls, text="🔄 Actualizar Estados", 
                command=lambda: self.actualizar_estados_pago(silent=False)).pack(side=tk.RIGHT, padx=5)
        
        # Toggle de actualización automática
        self.actualizacion_automatica_var = tk.BooleanVar(value=False)
        toggle = ttk.Checkbutton(right_controls, text="🔄 Actualización Automática (30s)",
                                variable=self.actualizacion_automatica_var,
                                command=self.alternar_actualizacion_automatica)
        toggle.pack(side=tk.RIGHT, padx=5)
        
        # Tabla de monitoreo
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("CC", "Nombre", "EPS", "Descripción", "Días en Mora", "Estado", "Fecha Último Pago", "Fecha Registro Estado")
        self.monitoreo_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        # Configurar columnas
        column_widths = {
            "CC": 80, "Nombre": 150, "EPS": 120, "Descripción": 200, 
            "Días en Mora": 80, "Estado": 100, "Fecha Último Pago": 120, 
            "Fecha Registro Estado": 140
        }
        
        for col in columns:
            self.monitoreo_tree.column(col, width=column_widths.get(col, 100), anchor=tk.CENTER)
            self.monitoreo_tree.heading(col, text=col)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.monitoreo_tree.yview)
        self.monitoreo_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.monitoreo_tree.pack(fill=tk.BOTH, expand=True)
        
        # Configurar doble click para ver detalles
        self.monitoreo_tree.bind("<Double-1>", lambda e: self.mostrar_detalles_monitoreo())
        
        # Menú contextual
        self.monitoreo_tree.bind("<Button-3>", lambda e: self.mostrar_menu_contextual_monitoreo(e))
        
        # Botones inferiores (resto de botones, sin los dos movidos)
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        if self.user_role == "Administrativo":
            ttk.Button(button_frame, text="❌ Eliminar", 
                    command=self.eliminar_monitoreo_seleccionado).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="📱 Enviar Recordatorio",
                command=self.enviar_recordatorio_individual).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="💳 Registrar Pago",
                command=self.registrar_pago_desde_monitoreo).pack(side=tk.LEFT, padx=5)
        #if self.user_role == "Administrativo":
        #    ttk.Button(button_frame, text="✏️ Cambiar Estado",
        #            command=self.cambiar_estado_manual).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="📊 Reporte de Morosidad",
                command=self.generar_reporte_morosidad).pack(side=tk.RIGHT, padx=5)
        
        # Inicializar datos de monitoreo si no existen
        if 'monitoreo' not in self.contabilidad_data:
            self.contabilidad_data['monitoreo'] = []
        
        # Actualizar tabla
        self.update_monitoreo_table()
        
        # Inicializar el after_id para la actualización automática
        self.after_id_auto = None
        
    def mostrar_menu_contextual_monitoreo(self, event):
        item = self.monitoreo_tree.identify_row(event.y)
        if item:
            self.monitoreo_tree.selection_set(item)
        else:
            return
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="📱 Enviar Recordatorio", command=self.enviar_recordatorio_individual)
        menu.add_command(label="💳 Registrar Pago", command=self.registrar_pago_desde_monitoreo)
        if self.user_role == "Administrativo":
            menu.add_command(label="✏️ Cambiar Estado", command=self.cambiar_estado_manual)
            menu.add_separator()
            menu.add_command(label="❌ Eliminar", command=self.eliminar_monitoreo_seleccionado)
        menu.post(event.x_root, event.y_root)

    def setup_archivados_interface(self, parent):
        """Configura la pestaña de archivados: tabla con scroll horizontal, búsqueda y botones."""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Título
        ttk.Label(main_frame, text="Afiliados Archivados", style='Title.TLabel').pack(pady=(0, 10))

        # ========== CONTROLES SUPERIORES (búsqueda) ==========
        top_controls = ttk.Frame(main_frame)
        top_controls.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(top_controls, text="Buscar:").pack(side=tk.LEFT, padx=5)
        busqueda_entry = ttk.Entry(top_controls, textvariable=self.busqueda_archivados_var, width=40)
        busqueda_entry.pack(side=tk.LEFT, padx=5)
        busqueda_entry.bind('<KeyRelease>', self.buscar_archivados)  # Filtro en tiempo real

        ttk.Button(top_controls, text="Mostrar Todos",
                command=lambda: [self.busqueda_archivados_var.set(""), self.cargar_archivados()]).pack(side=tk.LEFT, padx=5)

        # ========== TABLA CON SCROLL HORIZONTAL Y VERTICAL ==========
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("CC", "Nombre", "Celular", "EPS", "ARL", "Pensión", "Caja",
                "Mes Pago", "Valor", "Método Pago", "Fecha Pago", "Fecha Retiro",
                "Motivo Retiro", "Fecha Archivo", "Usuario")

        self.archivados_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="extended"
        )

        # Configurar anchos (igual que antes)
        anchos = {
            "CC": 80, "Nombre": 150, "Celular": 80, "EPS": 100, "ARL": 80,
            "Pensión": 80, "Caja": 80, "Mes Pago": 80, "Valor": 80,
            "Método Pago": 80, "Fecha Pago": 90, "Fecha Retiro": 90,
            "Motivo Retiro": 100, "Fecha Archivo": 120, "Usuario": 100
        }
        for col in columns:
            self.archivados_tree.column(col, width=anchos.get(col, 100), anchor=tk.CENTER)
            self.archivados_tree.heading(col, text=col)

        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.archivados_tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.archivados_tree.xview)
        self.archivados_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.archivados_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # ========== BOTONES INFERIORES ==========
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        inner = ttk.Frame(btn_frame)
        inner.pack(side=tk.RIGHT)

        ttk.Button(inner, text="↩️ Restaurar", command=self.restaurar_archivado).pack(side=tk.LEFT, padx=5)
        if self.user_role == "Administrativo":
            ttk.Button(inner, text="❌ Eliminar Definitivamente", command=self.eliminar_definitivo_archivado).pack(side=tk.LEFT, padx=5)
        ttk.Button(inner, text="🔄 Refrescar", command=self.cargar_archivados).pack(side=tk.LEFT, padx=5)

        # ========== DOBLE CLIC PARA DETALLES ==========
        self.archivados_tree.bind("<Double-1>", self.mostrar_detalles_archivado)

        # Cargar datos
        self.cargar_archivados()
                
    def cargar_archivados(self):
        """Carga todos los registros archivados en memoria y actualiza la tabla."""
        self.archivados_data = self.db.get_archivados()  # Guardar en variable
        self.actualizar_tabla_archivados(self.archivados_data)

    def actualizar_tabla_archivados(self, data=None):
        """Actualiza la tabla de archivados con los datos proporcionados (o todos)."""
        self.clear_treeview(self.archivados_tree)
        registros = data if data is not None else self.archivados_data

        for reg in registros:
            valor = float(reg.get('valor_pagado', 0))
            valor_str = f"${valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            self.archivados_tree.insert("", tk.END, values=(
                self._formatear_valor_tabla(reg.get('cc')),
                self._formatear_valor_tabla(reg.get('nombre')),
                self._formatear_valor_tabla(reg.get('celular')),
                self._formatear_valor_tabla(reg.get('eps')),
                self._formatear_valor_tabla(reg.get('arl')),
                self._formatear_valor_tabla(reg.get('pension')),
                self._formatear_valor_tabla(reg.get('caja_compensacion')),
                self._formatear_valor_tabla(reg.get('mes_pago')),
                valor_str,
                self._formatear_valor_tabla(reg.get('metodo_pago')),
                self._formatear_valor_tabla(reg.get('fecha_pago')),
                self._formatear_valor_tabla(reg.get('fecha_retiro')),
                self._formatear_valor_tabla(reg.get('motivo_retiro')),
                self._formatear_valor_tabla(reg.get('fecha_archivo')),
                self._formatear_valor_tabla(reg.get('usuario_archivo'))
            ))

    def buscar_archivados(self, event=None):
        """Filtra la tabla de archivados según el texto de búsqueda."""
        texto = self.busqueda_archivados_var.get().lower().strip()
        if not texto:
            self.actualizar_tabla_archivados(self.archivados_data)
            return

        filtrados = []
        for reg in self.archivados_data:
            # Buscar en varios campos
            if (texto in reg.get('cc', '').lower() or
                texto in reg.get('nombre', '').lower() or
                texto in reg.get('eps', '').lower() or
                texto in reg.get('arl', '').lower() or
                texto in reg.get('celular', '').lower()):
                filtrados.append(reg)

        self.actualizar_tabla_archivados(filtrados)

    def mostrar_detalles_archivado(self, event=None):
        """Muestra una ventana con los detalles del archivado seleccionado (organizados en 4 bloques)."""
        selected = self.archivados_tree.selection()
        if not selected:
            messagebox.showinfo("Selección", "Seleccione un registro para ver detalles.")
            return

        # Solo tomamos el primer elemento (si hay múltiples seleccionados, mostramos el primero)
        item = selected[0]
        values = self.archivados_tree.item(item, 'values')
        # Obtener el registro completo desde la base de datos (mejor que usar values)
        cc = values[0]
        archivados = self.db.get_archivados()
        registro = next((r for r in archivados if r['cc'] == cc), None)
        if not registro:
            messagebox.showerror("Error", "No se encontraron datos del archivado.")
            return

        # Usar el método Auxiliar para mostrar los detalles
        self._mostrar_detalles_archivado_desde_datos(registro)

    def _agregar_campo(self, parent, label, valor, row):
        """Auxiliar para agregar una fila de etiqueta+valor en un frame."""
        ttk.Label(parent, text=label, font=('Segoe UI', 9, 'bold')).grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(parent, text=valor, font=('Segoe UI', 9)).grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        parent.columnconfigure(1, weight=1)
    
    def restaurar_archivado_individual(self, cc):
        if self.user_role != "Administrativo":
            self._registrar_auditoria(
                "Intentó restaurar archivado (individual)",
                "Archivados",
                "Denegado",
                f"Cédula {cc}, usuario sin permisos"
            )
            messagebox.showerror("Error", "No tiene permisos para restaurar")
            return

        if not self.validar_password():
            return

        try:
            if self.db.restaurar_archivado(cc):
                # Recargar datos
                self.data = self.db.get_afiliados_activos()
                self.retiros_data = self.db.get_afiliados_retirados()
                self.update_afiliados_table()
                self.update_retiros_table()
                self.cargar_archivados()
                self.actualizar_estados_pago(silent=True)

                # === AUDITORÍA ===
                self._registrar_auditoria(
                    "Restauró archivado (individual)",
                    "Archivados",
                    "Éxito",
                    f"Cédula {cc}"
                )

                messagebox.showinfo("Éxito", "Registro restaurado correctamente")
            else:
                self._registrar_auditoria(
                    "Intento fallido de restaurar archivado",
                    "Archivados",
                    "Error",
                    f"Cédula {cc} - registro no encontrado"
                )
                messagebox.showerror("Error", "No se pudo restaurar el registro")
        except Exception as e:
            self._registrar_auditoria(
                "Error al restaurar archivado",
                "Archivados",
                "Error",
                f"Cédula {cc}, error: {str(e)}"
            )
            messagebox.showerror("Error", f"Error al restaurar: {str(e)}")
            
    def eliminar_definitivo_archivado_individual(self, cc):
        if self.user_role != "Administrativo":
            self._registrar_auditoria(
                "Intentó eliminar definitivamente archivado (individual)",
                "Archivados",
                "Denegado",
                f"Cédula {cc}, usuario sin permisos"
            )
            messagebox.showerror("Error", "No tiene permisos para eliminar definitivamente")
            return

        if not self.validar_password():
            return

        # Obtener nombre para el mensaje
        nombre = "desconocido"
        for reg in self.archivados_data:
            if reg['cc'] == cc:
                nombre = reg['nombre']
                break

        if not messagebox.askyesno(
            "Eliminar Definitivamente",
            f"¿Eliminar permanentemente a {nombre} (CC: {cc})?\nEsta acción no se puede deshacer.",
            icon=messagebox.WARNING
        ):
            return

        try:
            self.db.eliminar_definitivamente(cc)
            self.cargar_archivados()

            # === AUDITORÍA ===
            self._registrar_auditoria(
                "Eliminó definitivamente archivado (individual)",
                "Archivados",
                "Éxito",
                f"Cédula {cc} - {nombre}"
            )

            messagebox.showinfo("Éxito", "Registro eliminado definitivamente")
            self.refrescar_sistema(silent=True)
        except Exception as e:
            self._registrar_auditoria(
                "Error al eliminar definitivamente archivado",
                "Archivados",
                "Error",
                f"Cédula {cc}, error: {str(e)}"
            )
            messagebox.showerror("Error", f"No se pudo eliminar: {str(e)}")
            
    def restaurar_archivado(self):
        if self.user_role != "Administrativo":
            self._registrar_auditoria(
                "Intentó restaurar archivado",
                "Archivados",
                "Denegado",
                "Usuario sin permisos"
            )
            messagebox.showerror("Error", "No tiene permisos para restaurar")
            return

        selected = self.archivados_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Seleccione al menos un registro para restaurar")
            return

        if not self.validar_password():
            return

        # Recopilar CC y nombres
        ccs = []
        nombres = []
        for item in selected:
            values = self.archivados_tree.item(item, 'values')
            cc = values[0]
            nombre = values[1]
            ccs.append(cc)
            nombres.append(nombre)

        if not messagebox.askyesno(
            "Restaurar múltiples",
            f"¿Restaurar {len(ccs)} registro(s)?\n\n{', '.join(nombres)}"
        ):
            return

        restaurados = 0
        errores = []
        for cc in ccs:
            try:
                if self.db.restaurar_archivado(cc):
                    restaurados += 1
                    # === AUDITORÍA (cada uno) ===
                    self._registrar_auditoria(
                        "Restauró archivado",
                        "Archivados",
                        "Éxito",
                        f"Cédula {cc}"
                    )
                else:
                    errores.append(cc)
            except Exception as e:
                errores.append(f"{cc} (error: {str(e)})")
                self._registrar_auditoria(
                    "Error al restaurar archivado",
                    "Archivados",
                    "Error",
                    f"Cédula {cc}, error: {str(e)}"
                )

        # Recargar datos
        self.data = self.db.get_afiliados_activos()
        self.retiros_data = self.db.get_afiliados_retirados()
        self.update_afiliados_table()
        self.update_retiros_table()
        self.cargar_archivados()
        self.actualizar_estados_pago(silent=True)

        if restaurados > 0:
            self.mostrar_toast(f"{restaurados} registro(s) restaurado(s) correctamente")
        if errores:
            messagebox.showerror("Errores", f"No se pudieron restaurar: {', '.join(errores)}")
            
    def eliminar_definitivo_archivado(self):
        if self.user_role != "Administrativo":
            self._registrar_auditoria(
                "Intentó eliminar definitivamente archivado",
                "Archivados",
                "Denegado",
                "Usuario sin permisos"
            )
            messagebox.showerror("Error", "No tiene permisos para eliminar definitivamente")
            return

        selected = self.archivados_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Seleccione un registro para eliminar")
            return

        if not self.validar_password():
            return

        index = self.archivados_tree.index(selected[0])
        archivados = self.db.get_archivados()
        if index >= len(archivados):
            return
        reg = archivados[index]
        cc = reg['cc']
        nombre = reg['nombre']

        if not messagebox.askyesno(
            "Eliminar Definitivamente",
            f"¿Está seguro de eliminar permanentemente a {nombre} (CC: {cc})?\n"
            "Esta acción no se puede deshacer.",
            icon=messagebox.WARNING
        ):
            return

        try:
            self.db.eliminar_definitivamente(cc)
            self.cargar_archivados()

            # === AUDITORÍA ===
            self._registrar_auditoria(
                "Eliminó definitivamente archivado",
                "Archivados",
                "Éxito",
                f"Cédula {cc} - {nombre}"
            )

            self.mostrar_toast("Registro eliminado definitivamente")
            self.refrescar_sistema(silent=True)
        except Exception as e:
            self._registrar_auditoria(
                "Error al eliminar definitivamente archivado",
                "Archivados",
                "Error",
                f"Cédula {cc} - {nombre}, error: {str(e)}"
            )
            messagebox.showerror("Error", f"No se pudo eliminar: {str(e)}")
            
    # ======================
    # NUEVOS MÉTODOS PARA ACCIONES RÁPIDAS EN MONITOREO
    # ======================

    def enviar_recordatorio_individual(self):
        """Obtiene los afiliados seleccionados y abre el diálogo de envío."""
        selected = self.monitoreo_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Seleccione al menos un afiliado para enviar recordatorio.")
            return

        # Obtener las cédulas seleccionadas
        ccs = [self.monitoreo_tree.item(item, 'values')[0] for item in selected]

        # Buscar los afiliados en activos o retirados
        afiliados = []
        for cc in ccs:
            for a in self.data:
                if a['cc'] == cc:
                    afiliados.append(a)
                    break
            else:
                for a in self.retiros_data:
                    if a['cc'] == cc:
                        afiliados.append(a)
                        break

        if not afiliados:
            messagebox.showerror("Error", "No se encontraron afiliados para los seleccionados.")
            return

        # Abrir el diálogo de envío
        self.mostrar_dialogo_envio_recordatorio(afiliados)
        
    def mostrar_dialogo_envio_recordatorio(self, afiliados):
        """Crea un diálogo para elegir método y mostrar mensaje antes de enviar."""
        if not afiliados:
            return

        # Ventana principal
        ventana = Toplevel(self.root)
        ventana.title("Enviar Recordatorio")
        ventana.geometry("700x550")
        self.centrar_ventana(ventana, 700, 550)
        ventana.resizable(False, False)
        ventana.transient(self.root)
        ventana.grab_set()

        # Variables
        metodo_var = tk.StringVar(value="Ambos")

        # Frame principal
        main_frame = ttk.Frame(ventana, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ---- Lista de afiliados seleccionados ----
        list_frame = ttk.LabelFrame(main_frame, text="Afiliados seleccionados", padding=8)
        list_frame.pack(fill=tk.X, pady=5)

        nombres = ", ".join([a['nombre'] for a in afiliados])
        ttk.Label(list_frame, text=nombres, font=('Segoe UI', 10, 'bold'), wraplength=650).pack(anchor=tk.W)

        # ---- Selección de método ----
        metodo_frame = ttk.LabelFrame(main_frame, text="Método de envío", padding=8)
        metodo_frame.pack(fill=tk.X, pady=5)

        ttk.Label(metodo_frame, text="Seleccione el método:").pack(side=tk.LEFT, padx=5)
        ttk.Combobox(metodo_frame, textvariable=metodo_var, values=["WhatsApp", "Gmail", "Ambos"],
                    state="readonly", width=15).pack(side=tk.LEFT, padx=5)

        # ---- Vista previa del mensaje ----
        preview_frame = ttk.LabelFrame(main_frame, text="Vista previa del mensaje", padding=8)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Generar el mensaje para el primer afiliado (como ejemplo)
        mensaje_ejemplo = self._generar_mensaje_recordatorio(afiliados[0])
        if len(afiliados) > 1:
            mensaje_ejemplo += f"\n\n(El mismo mensaje se enviará a los {len(afiliados)} afiliados seleccionados, con sus respectivos nombres y datos.)"

        preview_text = tk.Text(preview_frame, wrap=tk.WORD, font=('Segoe UI', 10), height=12)
        preview_text.insert(tk.END, mensaje_ejemplo)
        preview_text.config(state=tk.DISABLED)  # Solo lectura
        preview_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ---- Botones de acción ----
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_frame, text="Cancelar", command=ventana.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Enviar", command=lambda: self._enviar_recordatorios_desde_dialogo(
            afiliados, metodo_var.get(), ventana), style='Accent.TButton').pack(side=tk.RIGHT, padx=5)

    def _generar_mensaje_recordatorio(self, afiliado):
        """Genera el mensaje de recordatorio personalizado para un afiliado."""
        hoy = datetime.now().date()
        fecha_pago = None
        try:
            if afiliado.get('fecha_pago'):
                fecha_pago = datetime.strptime(afiliado['fecha_pago'], "%Y-%m-%d").date()
        except:
            fecha_pago = None

        if not fecha_pago:
            return f"Estimado/a {afiliado['nombre']}, su pago de servicios de seguridad social está pendiente. Por favor regularice su situación. SaluPago."

        fecha_vencimiento = fecha_pago + timedelta(days=30)
        dias_restantes = (fecha_vencimiento - hoy).days
        dias_mora = (hoy - fecha_vencimiento).days if hoy > fecha_vencimiento else 0

        servicios = []
        if afiliado.get('eps'): servicios.append("EPS")
        if afiliado.get('arl'): servicios.append("ARL")
        if afiliado.get('pension'): servicios.append("Pensión")
        if afiliado.get('caja_compensacion'): servicios.append("Caja de Compensación")
        servicios_str = ", ".join(servicios) if servicios else "servicios"

        # Usar plantillas (si existen en la BD)
        plantillas = self.db.get_plantillas()
        if dias_mora > 0:
            if dias_mora >= 5:
                key = 'mora_5dias'
            elif dias_mora >= 3:
                key = 'mora_3dias'
            else:
                key = 'mora_1dia'
        else:
            if dias_restantes <= 1:
                key = 'recordatorio_1dia'
            elif dias_restantes <= 3:
                key = 'recordatorio_3dias'
            else:
                key = 'recordatorio_7dias'

        plantilla = plantillas.get(key, {})
        mensaje_template = plantilla.get('mensaje',
            "Estimado/a {nombre}, le recordamos que su pago para {servicios} está pendiente. "
            "Por favor regularice su situación.")

        mensaje = mensaje_template.format(
            nombre=afiliado['nombre'],
            servicios=servicios_str,
            fecha_vencimiento=fecha_vencimiento.strftime("%d/%m/%Y"),
            dias_restantes=dias_restantes,
            dias_mora=dias_mora
        )
        return mensaje

    def _enviar_recordatorios_desde_dialogo(self, afiliados, metodo, ventana):
        """Envía los recordatorios según el método elegido y cierra el diálogo."""
        enviar_whatsapp = metodo in ("WhatsApp", "Ambos")
        enviar_gmail = metodo in ("Gmail", "Ambos")

        enviados = 0
        for af in afiliados:
            mensaje = self._generar_mensaje_recordatorio(af)
            if enviar_whatsapp and af.get('celular'):
                self._enviar_whatsapp_texto(af['celular'], mensaje)
                enviados += 1
            if enviar_gmail and af.get('correo'):
                self._enviar_gmail_texto(af['correo'], mensaje)
                enviados += 1

        # Registrar notificaciones en BD
        for af in afiliados:
            notif_data = {
                "fecha": datetime.now().strftime("%Y-%m-%d"),
                "tipo": "Recordatorio manual",
                "cc": af['cc'],
                "nombre": af['nombre'],
                "mensaje": self._generar_mensaje_recordatorio(af)[:200] + "...",
                "estado": "Enviada",
                "fecha_vencimiento": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
                "tag": "recordatorio"
            }
            self.db.add_notificacion(notif_data)
            self.contabilidad_data['notificaciones'].append(notif_data)

        self.actualizar_notificaciones()
        ventana.destroy()
        messagebox.showinfo("Éxito", f"Se enviaron {enviados} recordatorios por {metodo}.")

    def registrar_pago_desde_monitoreo(self):
        """Abre el formulario de pago para el afiliado seleccionado en monitoreo (activo o retirado)."""
        selected = self.monitoreo_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Seleccione un afiliado para registrar pago.")
            return

        cc = self.monitoreo_tree.item(selected[0], 'values')[0]

        # Buscar en activos primero
        afiliado = None
        for a in self.data:
            if a['cc'] == cc:
                afiliado = a
                break
        if not afiliado:
            # Si no está activo, buscar en retirados (permitir pago a retirados)
            for a in self.retiros_data:
                if a['cc'] == cc:
                    afiliado = a
                    break

        if not afiliado:
            messagebox.showerror("Error", "No se encontró el afiliado en la base de datos.")
            return

        # No reactivar aquí, solo abrir el formulario
        self.mostrar_formulario_pago_para_afiliados([afiliado])

    def cambiar_estado_manual(self):
        """Permite cambiar manualmente el estado de los afiliados seleccionados en monitoreo"""
        if self.user_role != "Administrativo":
            messagebox.showerror("Error", "No tiene permisos para cambiar estados.")
            return

        selected = self.monitoreo_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Seleccione al menos un afiliado para cambiar estado.")
            return

        ccs = [self.monitoreo_tree.item(item, 'values')[0] for item in selected]

        # Diálogo para seleccionar nuevo estado
        estados = ["Activo", "Activo (Próximo a vencer)", "Próximo a Suspender", "Suspendido", "Retirado"]
        ventana = Toplevel(self.root)
        ventana.title("Cambiar Estado Manualmente")
        ventana.geometry("400x200")
        self.centrar_ventana(ventana, 400, 200)
        ventana.resizable(False, False)

        ttk.Label(ventana, text="Seleccione el nuevo estado para los afiliados seleccionados:", style='Title.TLabel').pack(pady=10)
        estado_var = tk.StringVar(value=estados[0])
        combo = ttk.Combobox(ventana, textvariable=estado_var, values=estados, state="readonly")
        combo.pack(pady=10)

        def aplicar_cambio():
            nuevo_estado = estado_var.get()
            if not nuevo_estado:
                return
            for cc in ccs:
                # Actualizar en memoria y BD
                for mon in self.contabilidad_data['monitoreo']:
                    if mon['cc'] == cc:
                        mon['estado'] = nuevo_estado
                        mon['fecha_registro_estado'] = datetime.now().strftime("%Y-%m-%d")
                        self.db.update_monitoreo(cc, mon)
                        # Si se cambia a Retirado, mover a retiros
                        if nuevo_estado == "Retirado":
                            for i, af in enumerate(self.data):
                                if af['cc'] == cc:
                                    af['fecha_retiro'] = datetime.now().strftime("%Y-%m-%d")
                                    self.db.retirar_afiliado(cc, af['fecha_retiro'])
                                    self.retiros_data.append(af)
                                    del self.data[i]
                                    break
                        break
            self.update_monitoreo_table()
            self.update_afiliados_table()
            self.update_retiros_table()
            messagebox.showinfo("Éxito", f"Estado cambiado a '{nuevo_estado}' para {len(ccs)} afiliados.")
            ventana.destroy()

        btn_frame = ttk.Frame(ventana)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Cancelar", command=ventana.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Aplicar", command=aplicar_cambio).pack(side=tk.LEFT, padx=5)

    # ======================
    # ACTUALIZACIÓN AUTOMÁTICA PERIÓDICA
    # ======================

    def alternar_actualizacion_automatica(self):
        """Activa o desactiva la actualización automática de estados cada 30 segundos"""
        if self.actualizacion_automatica_var.get():
            # Activar
            self.actualizacion_automatica_var.set(True)
            self.programar_actualizacion_automatica()
            messagebox.showinfo("Actualización automática", "Activada. Los estados se actualizarán cada 30 segundos.")
        else:
            # Desactivar
            if self.after_id_auto:
                self.root.after_cancel(self.after_id_auto)
                self.after_id_auto = None
            messagebox.showinfo("Actualización automática", "Desactivada.")

    def programar_actualizacion_automatica(self):
        """Programa la próxima actualización automática si está activa"""
        if not self.actualizacion_automatica_var.get():
            return
        # Llamar a actualizar_estados_pago (que ya actualiza monitoreo)
        self.actualizar_estados_pago()
        # Programar la siguiente ejecución en 30 segundos
        self.after_id_auto = self.root.after(30000, self.programar_actualizacion_automatica)
        self.actualizar_estados_pago(silent=True)

    def eliminar_monitoreo_seleccionado(self):
        if self.user_role != "Administrativo":
            messagebox.showerror("Error", "No tiene permisos para eliminar registros de monitoreo.")
            return

        selected = self.monitoreo_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Por favor seleccione un registro de monitoreo para eliminar.")
            return

        # Obtener la cédula desde la primera columna
        cc = self.monitoreo_tree.item(selected[0], 'values')[0]

        # Buscar el índice en la lista de monitoreo
        index = -1
        for i, m in enumerate(self.contabilidad_data['monitoreo']):
            if m['cc'] == cc:
                index = i
                break

        if index == -1:
            messagebox.showerror("Error", "El registro no existe en la lista de monitoreo.")
            return

        registro = self.contabilidad_data['monitoreo'][index]
        nombre = registro['nombre']

        if not messagebox.askyesno("Confirmar eliminación",
                                    f"¿Está seguro de eliminar el registro de monitoreo de '{nombre}' (CC: {cc})?\n"
                                    "Esta acción no se puede deshacer."):
            return

        try:
            self.db.delete_monitoreo(cc)
            del self.contabilidad_data['monitoreo'][index]
            self.update_monitoreo_table()
            messagebox.showinfo("Éxito", f"Registro de monitoreo de '{nombre}' eliminado correctamente.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar el registro:\n{str(e)}")
                    
    def update_monitoreo_table(self, data=None):
        """Actualiza la tabla de monitoreo con los datos proporcionados o todos los datos."""
        self.clear_treeview(self.monitoreo_tree)

        data_to_show = data if data is not None else self.contabilidad_data['monitoreo']

        for registro in data_to_show:
            self.monitoreo_tree.insert("", tk.END, iid=registro['cc'], values=(
                registro['cc'],
                registro['nombre'],
                registro['eps'],
                registro['descripcion'],
                registro['dias_mora'],
                registro['estado'],
                registro['fecha_ultimo_pago'],
                registro['fecha_registro_estado']
            ))

    def buscar_en_monitoreo(self):
        """Busca en la tabla de monitoreo según los criterios especificados"""
        texto_busqueda = self.busqueda_monitoreo_var.get().lower()
        
        if not texto_busqueda:
            self.update_monitoreo_table()
            return
            
        resultados = []
        
        for registro in self.contabilidad_data['monitoreo']:
            if (texto_busqueda in registro['cc'].lower() or 
                texto_busqueda in registro['nombre'].lower() or
                texto_busqueda in registro['eps'].lower() or
                texto_busqueda in registro['estado'].lower()):
                resultados.append(registro)
        
        self.update_monitoreo_table(resultados)

    def actualizar_estados_pago(self, silent=False):
        hoy = datetime.now()
        # Asegurar monitoreo para todos los activos
        for afiliado in self.data:
            if not any(m['cc'] == afiliado['cc'] for m in self.contabilidad_data['monitoreo']):
                nuevo = {
                    'cc': afiliado['cc'],
                    'nombre': afiliado['nombre'],
                    'eps': afiliado['eps'],
                    'descripcion': 'Pago de servicios de salud',
                    'dias_mora': 0,
                    'estado': 'Activo',
                    'fecha_ultimo_pago': afiliado.get('fecha_pago', 'No registrado'),
                    'fecha_registro_estado': hoy.strftime("%Y-%m-%d")
                }
                self.db.add_monitoreo(nuevo)
                self.contabilidad_data['monitoreo'].append(nuevo)

        # Actualizar cada registro de monitoreo
        for registro in self.contabilidad_data['monitoreo']:
            cc = registro['cc']
            # Determinar si el afiliado está en retirados
            en_retiros = any(r['cc'] == cc for r in self.retiros_data)

            # Si está en retiros, forzar estado "Retirado"
            if en_retiros:
                registro['estado'] = 'Retirado'
                registro['dias_mora'] = 0  # opcional
                registro['fecha_registro_estado'] = hoy.strftime("%Y-%m-%d")
                self.db.update_monitoreo(cc, registro)
                continue  # saltar el cálculo normal

            # Si está en activos, calcular según fecha de pago
            if registro['fecha_ultimo_pago'] and registro['fecha_ultimo_pago'] != 'No registrado':
                try:
                    fecha_pago = datetime.strptime(registro['fecha_ultimo_pago'], "%Y-%m-%d")
                    fecha_vencimiento = fecha_pago + timedelta(days=30)
                    dias_mora = (hoy - fecha_vencimiento).days
                    registro['dias_mora'] = max(0, dias_mora)

                    umbrales = self.config.get('monitoreo_umbrales', {})
                    activo_hasta = umbrales.get('activo_hasta_dias', 3)
                    proximo_suspender = umbrales.get('proximo_suspender_dias', 5)
                    suspendido = umbrales.get('suspendido_dias', 7)

                    if hoy < fecha_vencimiento:
                        estado = 'Activo'
                    elif 0 < dias_mora <= activo_hasta:
                        estado = 'Activo (Próximo a vencer)'
                    elif activo_hasta < dias_mora <= proximo_suspender:
                        estado = 'Próximo a Suspender'
                    elif proximo_suspender < dias_mora <= suspendido:
                        estado = 'Suspendido'
                    else:
                        estado = 'Retirado'

                    registro['estado'] = estado
                    registro['fecha_registro_estado'] = hoy.strftime("%Y-%m-%d")
                    self.db.update_monitoreo(cc, registro)

                    # Si el estado es Retirado, mover a retiros
                    if estado == 'Retirado':
                        if not any(r['cc'] == cc for r in self.retiros_data):
                            for i, af in enumerate(self.data):
                                if af['cc'] == cc:
                                    af['fecha_retiro'] = hoy.strftime("%Y-%m-%d")
                                    self.db.retirar_afiliado(af['cc'], af['fecha_retiro'])
                                    self.retiros_data.append(af)
                                    del self.data[i]
                                    break

                except ValueError:
                    registro['estado'] = 'Fecha de pago inválida'
                    self.db.update_monitoreo(cc, registro)
            else:
                # Sin fecha de pago → se considera en mora (pendiente)
                registro['estado'] = 'Activo (Próximo a vencer)'
                registro['dias_mora'] = 30  # o un valor por defecto
                self.db.update_monitoreo(cc, registro)

        # Refrescar tablas
        self.update_monitoreo_table()
        self.update_afiliados_table()
        self.update_retiros_table()
        self.mostrar_alertas_vencimiento()
        if not silent:
            self.mostrar_toast("Estados de pago actualizados correctamente")
                            
    def generar_reporte_morosidad(self):
        """
        Genera un reporte en PDF o Excel con la lista de afiliados en mora,
        días de retraso y monto adeudado.
        """
        # 1. Obtener los registros de monitoreo con días_mora > 0
        morosos = [m for m in self.contabilidad_data.get('monitoreo', []) if m.get('dias_mora', 0) > 0]

        if not morosos:
            messagebox.showinfo("Sin morosos", "Actualmente no hay afiliados en mora.")
            return

        # 2. Preparar los datos para el reporte
        datos_reporte = []
        for mon in morosos:
            cc = mon['cc']
            # Buscar el afiliado (activo o retirado) para obtener el valor del pago
            afiliado = None
            for a in self.data:
                if a['cc'] == cc:
                    afiliado = a
                    break
            if not afiliado:
                for a in self.retiros_data:
                    if a['cc'] == cc:
                        afiliado = a
                        break

            valor_pagado = float(afiliado.get('valor_pagado', 0)) if afiliado else 0.0
            datos_reporte.append({
                'Cédula': cc,
                'Nombre': mon['nombre'],
                'EPS': mon.get('eps', ''),
                'Días en mora': mon['dias_mora'],
                'Estado': mon.get('estado', ''),
                'Valor adeudado (mes)': valor_pagado,
                'Último pago': mon.get('fecha_ultimo_pago', '-/-'),
                'Fecha registro estado': mon.get('fecha_registro_estado', '-/-')
            })

        # 3. Preguntar formato de salida
        formato = messagebox.askquestion("Formato de reporte",
                                        "¿Desea exportar a Excel?\n(Si pulsa 'No' se generará un PDF)",
                                        icon='question')
        es_excel = (formato == 'yes')

        # 4. Generar el archivo
        if es_excel:
            self._exportar_reporte_excel(datos_reporte)
        else:
            self._exportar_reporte_pdf(datos_reporte)

    def _exportar_reporte_excel(self, datos):
        """Genera un archivo Excel con el reporte de morosidad."""
        try:
            import openpyxl  # verificar dependencia
        except ImportError:
            if messagebox.askyesno("Dependencia faltante",
                                "El módulo 'openpyxl' no está instalado. ¿Desea instalarlo ahora?"):
                subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl"])
                import openpyxl
            else:
                return

        # Crear directorio para reportes si no existe
        reportes_dir = os.path.join(BASE_PATH, "Reportes")
        os.makedirs(reportes_dir, exist_ok=True)

        # Nombre del archivo con fecha
        fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Reporte_Morosidad_{fecha_str}.xlsx"
        filepath = os.path.join(reportes_dir, filename)

        df = pd.DataFrame(datos)
        df.to_excel(filepath, index=False, engine='openpyxl')

        messagebox.showinfo("Reporte generado", f"Reporte guardado en:\n{filepath}")
        if messagebox.askyesno("Abrir carpeta", "¿Desea abrir la ubicación del archivo?"):
            os.startfile(reportes_dir)
    
    def _exportar_reporte_pdf(self, datos):
        """
        Genera un archivo PDF con el reporte de morosidad con formato profesional.
        """
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch, cm
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

        # Crear directorio para reportes
        reportes_dir = os.path.join(BASE_PATH, "Reportes")
        os.makedirs(reportes_dir, exist_ok=True)

        fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Reporte_Morosidad_{fecha_str}.pdf"
        filepath = os.path.join(reportes_dir, filename)

        doc = SimpleDocTemplate(filepath, pagesize=letter,
                                leftMargin=1.5*cm, rightMargin=1.5*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        elements = []
        styles = getSampleStyleSheet()

        # Estilos
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Title'],
            fontSize=16,
            textColor=colors.HexColor('#b71c1c'),
            alignment=TA_CENTER,
            spaceAfter=12
        )
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
        )

        # ========== ENCABEZADO ==========
        # Logo (opcional)
        logo_path = os.path.join(IMG_PATH, "LogoSaluPago.png")
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=2*cm, height=2*cm)
                elements.append(logo)
            except:
                pass

        elements.append(Paragraph("REPORTE DE MOROSIDAD", title_style))
        elements.append(Spacer(1, 0.2*cm))

        # Información de fecha y total de morosos
        total_morosos = len(datos)
        info = f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  Total de afiliados en mora: {total_morosos}"
        elements.append(Paragraph(info, header_style))
        elements.append(Spacer(1, 0.5*cm))

        # ========== TABLA DE DATOS ==========
        if not datos:
            elements.append(Paragraph("No hay afiliados en mora.", styles['Normal']))
        else:
            # Preparar datos para la tabla
            table_data = [["Cédula", "Nombre", "EPS", "Días mora", "Estado", "Valor adeudado", "Último pago"]]
            for row in datos:
                table_data.append([
                    row['Cédula'],
                    row['Nombre'],
                    row['EPS'],
                    str(row['Días en mora']),
                    row['Estado'],
                    f"${row['Valor adeudado (mes)']:,.2f}",
                    row['Último pago']
                ])

            tabla = Table(table_data, colWidths=[1.5*cm, 3*cm, 2.5*cm, 1.5*cm, 2.5*cm, 2.5*cm, 2.5*cm])
            tabla.setStyle(TableStyle([
                # Cabecera
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#b71c1c')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 9),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
                # Filas
                ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
                ('FONTSIZE', (0,1), (-1,-1), 8),
                ('BACKGROUND', (0,1), (-1,-2), colors.whitesmoke),
                ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#ffebee')),  # última fila de totales si la hubiera
                ('TEXTCOLOR', (-1,1), (-1,-1), colors.HexColor('#b71c1c')),
                ('FONTNAME', (-1,-1), (-1,-1), 'Helvetica-Bold'),
            ]))
            elements.append(tabla)

        # ========== PIE DE PÁGINA ==========
        elements.append(Spacer(1, 0.5*cm))
        footer = Paragraph("Reporte generado por SaluPago - Sistema de Gestión de Pagos", styles['Italic'])
        elements.append(footer)

        # Construir PDF
        doc.build(elements)

        # Abrir carpeta o archivo
        messagebox.showinfo("Reporte generado", f"Reporte guardado en:\n{filepath}")
        if messagebox.askyesno("Abrir carpeta", "¿Desea abrir la ubicación del archivo?"):
            os.startfile(reportes_dir)
            
    def mostrar_alertas_vencimiento(self):
        en_riesgo = [mon for mon in self.contabilidad_data.get('monitoreo', [])
                    if mon.get('estado') in ['Activo (Próximo a vencer)', 'Próximo a Suspender']]
        if not en_riesgo:
            return

        # ===== SONIDO DE ALERTA =====
        self.reproducir_sonido("alerta")

        # Mostrar notificación tipo toast
        mensaje = f"⚠️ {len(en_riesgo)} afiliado(s) en riesgo de vencimiento. ¡Haga clic para ver!"
        toast = Toast(self.root, mensaje, duration=5000,
                    callback=lambda: self._mostrar_ventana_alertas(en_riesgo))
        toast.show()
        
    def _mostrar_ventana_alertas(self, en_riesgo):
        """Muestra la ventana con la lista de afiliados en riesgo (no modal)."""
        if hasattr(self, '_alerta_ventana') and self._alerta_ventana is not None:
            try:
                self._alerta_ventana.lift()
                self._alerta_ventana.focus_force()
                return
            except tk.TclError:
                self._alerta_ventana = None

        alerta = Toplevel(self.root)
        self._alerta_ventana = alerta
        alerta.title("⚠️ Alertas de Vencimiento")
        alerta.geometry("800x480")
        alerta.resizable(False, False)
        alerta.transient(self.root)
        # No se usa grab_set()

        alerta.update_idletasks()
        w, h = 800, 480
        alerta.geometry(f"+{(alerta.winfo_screenwidth()-w)//2}+{(alerta.winfo_screenheight()-h)//2}")

        frame = ttk.Frame(alerta, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Atención: Afiliados próximos a vencer o en mora inicial",
                font=('Arial', 14, 'bold')).pack(pady=(0,10))
        ttk.Label(frame, text="Estos afiliados requieren seguimiento inmediato:",
                font=('Arial', 10)).pack(anchor=tk.W, pady=(0,10))

        columnas = ("Cédula", "Nombre", "Estado", "Días en Mora", "Último Pago")
        anchos = {"Cédula":110, "Nombre":220, "Estado":200, "Días en Mora":110, "Último Pago":130}

        tabla_frame = ttk.Frame(frame)
        tabla_frame.pack(fill=tk.BOTH, expand=True)

        tree = ttk.Treeview(tabla_frame, columns=columnas, show="headings", height=10)
        for col in columnas:
            tree.column(col, width=anchos[col], anchor=tk.CENTER if col!="Nombre" else tk.W)
            tree.heading(col, text=col)

        scroll = ttk.Scrollbar(tabla_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        for mon in en_riesgo:
            tree.insert("", tk.END, values=(
                mon.get('cc',''), mon.get('nombre',''), mon.get('estado',''),
                mon.get('dias_mora',0), mon.get('fecha_ultimo_pago','-/-')
            ))

        botones = ttk.Frame(frame)
        botones.pack(fill=tk.X, pady=(20,0))
        centrado = ttk.Frame(botones)
        centrado.pack(anchor=tk.CENTER)

        ttk.Button(centrado, text="📋  Ir a Monitoreo",
                command=lambda: [self.notebook.select(self.monitoreo_frame), alerta.destroy()],
                width=22).pack(side=tk.LEFT, padx=8, ipady=5)
        ttk.Button(centrado, text="Cerrar", command=alerta.destroy,
                width=12).pack(side=tk.LEFT, padx=8, ipady=5)

        alerta.protocol("WM_DELETE_WINDOW", lambda: [setattr(self, '_alerta_ventana', None), alerta.destroy()])
        
    def mostrar_detalles_monitoreo(self):
        selected_item = self.monitoreo_tree.selection()
        if not selected_item:
            return

        # Obtener la cédula desde la primera columna (values[0])
        cc = self.monitoreo_tree.item(selected_item[0], 'values')[0]

        # Buscar el registro en la lista completa de monitoreo
        registro = None
        for m in self.contabilidad_data['monitoreo']:
            if m['cc'] == cc:
                registro = m
                break

        if not registro:
            messagebox.showerror("Error", "No se encontró el registro de monitoreo.")
            return

        # --- Resto del código (creación de la ventana de detalles) ---
        detalles_window = Toplevel(self.root)
        detalles_window.title(f"Detalles de Monitoreo - {registro['nombre']}")
        detalles_window.geometry("500x400")
        self.centrar_ventana(detalles_window, 500, 400)

        main_frame = ttk.Frame(detalles_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text=f"Detalles de Monitoreo", style='Title.TLabel').pack(pady=(0, 20))

        detalles_frame = ttk.Frame(main_frame)
        detalles_frame.pack(fill=tk.BOTH, expand=True)

        detalles = [
            ("CC:", self._formatear_valor_detalle(registro['cc'])),
            ("Nombre:", self._formatear_valor_detalle(registro['nombre'])),
            ("EPS:", self._formatear_valor_detalle(registro['eps'])),
            ("Descripción:", self._formatear_valor_detalle(registro['descripcion'])),
            ("Días en Mora:", registro.get('dias_mora', 0)),
            ("Estado:", self._formatear_valor_detalle(registro['estado'])),
            ("Fecha Último Pago:", self._formatear_valor_detalle(registro['fecha_ultimo_pago'])),
            ("Fecha Registro Estado:", self._formatear_valor_detalle(registro['fecha_registro_estado']))
        ]

        for i, (campo, valor) in enumerate(detalles):
            ttk.Label(detalles_frame, text=campo).grid(row=i, column=0, sticky=tk.W, pady=2, padx=5)
            ttk.Label(detalles_frame, text=valor).grid(row=i, column=1, sticky=tk.W, pady=2)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(20, 10))

        ttk.Button(button_frame, text="↩️Cerrar", command=detalles_window.destroy).pack(side=tk.RIGHT, padx=5)

        if self.user_role == "Administrativo":
            ttk.Button(button_frame, text="✏️Editar Estado",
                    command=lambda: self.editar_estado_monitoreo(cc, detalles_window)).pack(side=tk.RIGHT, padx=5)
            
    def editar_estado_monitoreo(self, cc, ventana_padre):
        """Permite editar todos los campos del monitoreo: días, estado, fechas."""
        # Buscar el registro por cédula
        registro = None
        index = -1
        for i, m in enumerate(self.contabilidad_data['monitoreo']):
            if m['cc'] == cc:
                registro = m
                index = i
                break

        if not registro:
            messagebox.showerror("Error", "No se encontró el registro de monitoreo.")
            return

        # Crear ventana de edición (el resto del código es igual, usando 'registro' e 'index')
        edit_window = Toplevel(ventana_padre)
        edit_window.title(f"Editar Monitoreo - {registro['nombre']}")
        edit_window.geometry("450x360")
        self.centrar_ventana(edit_window, 450, 360)
        edit_window.resizable(False, False)

        # Variables
        estado_var = tk.StringVar(value=registro['estado'])
        descripcion_var = tk.StringVar(value=registro['descripcion'])
        dias_mora_var = tk.StringVar(value=str(registro['dias_mora']))
        fecha_ultimo_pago_var = tk.StringVar(value=registro['fecha_ultimo_pago'])
        fecha_registro_estado_var = tk.StringVar(value=registro['fecha_registro_estado'])

        estados = ["Activo", "Activo (Próximo a vencer)", "Próximo a Suspender", "Suspendido", "Retirado"]

        # Frame principal
        main_frame = ttk.Frame(edit_window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(main_frame, text=f"Editar Monitoreo - {registro['nombre']}",
                style='Title.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # Estado
        ttk.Label(main_frame, text="Estado*:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        cb_estado = ttk.Combobox(main_frame, textvariable=estado_var, values=estados, state="readonly")
        cb_estado.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)

        # Descripción
        ttk.Label(main_frame, text="Descripción:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        entry_desc = ttk.Entry(main_frame, textvariable=descripcion_var, width=40)
        entry_desc.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)

        # Días en mora
        ttk.Label(main_frame, text="Días en Mora:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        entry_dias = ttk.Entry(main_frame, textvariable=dias_mora_var, width=10)
        entry_dias.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)

        # Fecha último pago
        ttk.Label(main_frame, text="Último Pago (YYYY-MM-DD):").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        entry_fecha_pago = ttk.Entry(main_frame, textvariable=fecha_ultimo_pago_var, width=20)
        entry_fecha_pago.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)

        # Fecha registro estado
        ttk.Label(main_frame, text="Registro Estado (YYYY-MM-DD):").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        entry_fecha_reg = ttk.Entry(main_frame, textvariable=fecha_registro_estado_var, width=20)
        entry_fecha_reg.grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)

        # Botón recalcular
        def recalcular_dias():
            try:
                fecha_pago = datetime.strptime(fecha_ultimo_pago_var.get(), "%Y-%m-%d")
                hoy = datetime.now().date()
                fecha_vencimiento = fecha_pago.date() + timedelta(days=30)
                dias_mora = (hoy - fecha_vencimiento).days
                dias_mora = max(0, dias_mora)
                dias_mora_var.set(str(dias_mora))
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo recalcular los días:\n{str(e)}")

        ttk.Button(main_frame, text="🔄 Recalcular",
                command=recalcular_dias).grid(row=6, column=0, columnspan=2, pady=10)

        # Botones de acción
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=(20, 0), sticky=tk.E)

        ttk.Button(button_frame, text="Cancelar", command=edit_window.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Guardar",
                command=lambda: self.guardar_estado_monitoreo(
                    index,  # pasamos el índice (ya lo tenemos)
                    estado_var.get(),
                    descripcion_var.get(),
                    dias_mora_var.get(),
                    fecha_ultimo_pago_var.get(),
                    fecha_registro_estado_var.get(),
                    edit_window,
                    ventana_padre
                )).pack(side=tk.RIGHT, padx=5)
        
    def guardar_estado_monitoreo(self, index, estado, descripcion, dias_mora_str, fecha_ultimo_pago, fecha_registro_estado, edit_window, parent_window):
        """Guarda todos los campos editados y sincroniza con el afiliado."""
        # Validaciones
        if not estado:
            messagebox.showerror("Error", "El estado es obligatorio")
            return

        try:
            dias_mora = int(dias_mora_str) if dias_mora_str.strip() else 0
        except ValueError:
            messagebox.showerror("Error", "Los días en mora deben ser un número entero")
            return

        # Validar formato de fechas (opcional, pero recomendado)
        try:
            datetime.strptime(fecha_ultimo_pago, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Formato de fecha último pago inválido. Use YYYY-MM-DD")
            return

        try:
            datetime.strptime(fecha_registro_estado, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Formato de fecha registro estado inválido. Use YYYY-MM-DD")
            return

        # Obtener el registro de monitoreo
        registro = self.contabilidad_data['monitoreo'][index]
        cc = registro['cc']

        # Actualizar el registro de monitoreo
        registro['estado'] = estado
        registro['descripcion'] = descripcion
        registro['dias_mora'] = dias_mora
        registro['fecha_ultimo_pago'] = fecha_ultimo_pago
        registro['fecha_registro_estado'] = fecha_registro_estado

        # Guardar en la base de datos
        self.db.update_monitoreo(cc, registro)

        # --- Sincronizar con el afiliado (activo o retirado) ---
        # Buscar en activos
        afiliado_encontrado = None
        for i, af in enumerate(self.data):
            if af['cc'] == cc:
                afiliado_encontrado = (i, af, 'activo')
                break
        if not afiliado_encontrado:
            for i, af in enumerate(self.retiros_data):
                if af['cc'] == cc:
                    afiliado_encontrado = (i, af, 'retirado')
                    break

        if afiliado_encontrado:
            idx, af, tipo = afiliado_encontrado
            # Actualizar fecha_pago del afiliado con la fecha_ultimo_pago del monitoreo
            af['fecha_pago'] = fecha_ultimo_pago
            # Si se cambió el estado a Retirado, mover a retiros (si no lo está ya)
            if estado == "Retirado" and tipo == 'activo':
                # Mover a retiros
                af['fecha_retiro'] = datetime.now().strftime("%Y-%m-%d")
                self.db.retirar_afiliado(cc, af['fecha_retiro'])
                self.retiros_data.append(af)
                del self.data[idx]
                # Actualizar también el monitoreo para que ya no aparezca en activos? Ya está actualizado.
            elif estado != "Retirado" and tipo == 'retirado':
                # Si estaba retirado y ahora se reactiva (cambiar estado a otro que no sea retirado)
                # Lo movemos a activos
                if 'fecha_retiro' in af:
                    del af['fecha_retiro']
                self.db.reactivar_afiliado(cc)
                self.data.append(af)
                del self.retiros_data[idx]
            else:
                # Si es activo y sigue activo, solo actualizar fecha_pago
                if tipo == 'activo':
                    self.db.update_afiliado(cc, af)
                else:  # retirado y sigue retirado
                    self.db.update_afiliado(cc, af)  # update funciona igual

        # Actualizar todas las tablas
        self.update_monitoreo_table()
        self.update_afiliados_table()
        self.update_retiros_table()

        # Cerrar ventanas
        edit_window.destroy()
        parent_window.destroy()

        messagebox.showinfo("Éxito", "Monitoreo actualizado correctamente")
        
    def setup_notificaciones_interface(self, parent):
        """Configura la interfaz de notificaciones con alertas inteligentes"""
        # Frame principal
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(main_frame, text="Notificaciones", style='Title.TLabel').pack(pady=(0, 10))
        
        # Variables de control
        self.notificaciones_filtro_var = tk.StringVar(value="Todas")
        self.notificaciones_busqueda_var = tk.StringVar()
        
        # Controles superiores
        top_controls = ttk.Frame(main_frame)
        top_controls.pack(fill=tk.X, pady=(0, 10))
        
        # Filtro por tipo de notificación
        ttk.Label(top_controls, text="Filtrar:").pack(side=tk.LEFT, padx=5)
        filtro_cb = ttk.Combobox(top_controls, textvariable=self.notificaciones_filtro_var, 
                               values=["Todas", "Recordatorios", "Alertas", "Mora", "Pagos"], 
                               state="readonly", width=15)
        filtro_cb.pack(side=tk.LEFT, padx=5)
        filtro_cb.bind("<<ComboboxSelected>>", lambda e: self.actualizar_notificaciones())
        
        # Búsqueda
        ttk.Label(top_controls, text="Buscar:").pack(side=tk.LEFT, padx=5)
        busqueda_entry = ttk.Entry(top_controls, textvariable=self.notificaciones_busqueda_var, width=30)
        busqueda_entry.pack(side=tk.LEFT, padx=5)
        busqueda_entry.bind('<KeyRelease>', lambda e: self.actualizar_notificaciones())
        
        # Botón para enviar notificaciones
        ttk.Button(top_controls, text="🔄Actualizar Notificaciones", 
                 command=self.generar_notificaciones_automaticas).pack(side=tk.RIGHT, padx=5)
        
        # Tabla de notificaciones
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("Fecha", "Tipo", "Afiliado", "Mensaje", "Estado", "Fecha Vencimiento")
        
        # ======================================================
        # CORRECCIÓN 1: Aumentar el rowheight (Altura de fila)
        # Esto hace que el texto se vea más desahogado y ayuda a 
        # que si el texto es muy largo no choque con la fila de abajo.
        # ======================================================
        style = ttk.Style()
        style.configure("Notificaciones.Treeview", rowheight=40)  # <--- Aumentado de 25 a 40
        style.configure("Notificaciones.Treeview.Heading", font=('Arial', 10, 'bold'))
        
        self.notificaciones_tree = ttk.Treeview(
            table_frame, 
            columns=columns, 
            show="headings",
            style="Notificaciones.Treeview"
        )
        
        # Configurar columnas
        column_widths = {
            "Fecha": 100, 
            "Tipo": 120, 
            "Afiliado": 150, 
            "Mensaje": 350,  # <--- Aumentado de 250 a 350 para que entre más texto
            "Estado": 100,
            "Fecha Vencimiento": 120
        }
        
        for col in columns:
            self.notificaciones_tree.column(col, width=column_widths.get(col, 100), anchor=tk.CENTER)
            self.notificaciones_tree.heading(col, text=col)
        
        # Configurar tags para colores según tipo
        self.notificaciones_tree.tag_configure('recordatorio', background='#FFF9C4')  # Amarillo claro
        self.notificaciones_tree.tag_configure('alerta', background='#FFCC80')       # Naranja claro
        self.notificaciones_tree.tag_configure('mora', background='#FFCDD2')         # Rojo claro
        self.notificaciones_tree.tag_configure('pago', background='#C8E6C9')         # Verde claro
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.notificaciones_tree.yview)
        self.notificaciones_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.notificaciones_tree.pack(fill=tk.BOTH, expand=True)
        
        # Botones inferiores
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="📤 Enviar Seleccionadas", 
             command=self.enviar_notificaciones_seleccionadas).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="📝 Editar Plantilla", 
                command=self.editar_plantilla_mensaje).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="✔️ Marcar como Enviadas", 
                command=self.marcar_notificaciones_enviadas).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="✖️ Eliminar Notificación", 
                command=self.eliminar_notificacion).pack(side=tk.RIGHT, padx=5)
            
        # Inicializar datos de notificaciones si no existen
        if 'notificaciones' not in self.contabilidad_data:
            self.contabilidad_data['notificaciones'] = []
        
        # Generar notificaciones automáticas al iniciar
        self.generar_notificaciones_automaticas()
        
        # Configurar doble click para ver detalles
        self.notificaciones_tree.bind("<Double-1>", lambda e: self.mostrar_detalles_notificacion())

    def eliminar_notificacion(self):
        selected_items = self.notificaciones_tree.selection()
        if not selected_items:
            messagebox.showerror("Error", "Por favor seleccione al menos una notificación para eliminar")
            return
        password_window = Toplevel(self.root)
        password_window.title("Verificación de Administrador")
        password_window.geometry("350x150")
        ttk.Label(password_window, text="Ingrese la contraseña de administrador:").pack(pady=(15,5))
        password_var = tk.StringVar()
        password_entry = ttk.Entry(password_window, textvariable=password_var, show="*")
        password_entry.pack(pady=5)
        def verify_password():
            if password_var.get() == "admin123":
                password_window.destroy()
                self.confirmar_eliminacion_notificaciones(selected_items)
            else:
                messagebox.showerror("Error", "Contraseña incorrecta")
                password_window.destroy()
        ttk.Button(password_window, text="Cancelar", command=password_window.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(password_window, text="Verificar", command=verify_password).pack(side=tk.RIGHT, padx=5)
        password_entry.focus_set()

    def confirmar_eliminacion_notificaciones(self, selected_items):
        indices = [self.notificaciones_tree.index(item) for item in selected_items]
        indices.sort(reverse=True)
        if messagebox.askyesno("Confirmar Eliminación", f"¿Está seguro que desea eliminar {len(indices)} notificación(es) seleccionada(s)?"):
            for index in indices:
                if index < len(self.contabilidad_data['notificaciones']):
                    n = self.contabilidad_data['notificaciones'][index]
                    if 'id' in n:
                        self.db.delete_notificacion(n['id'])
                    del self.contabilidad_data['notificaciones'][index]
            self.actualizar_notificaciones()
            messagebox.showinfo("Éxito", f"Se eliminaron {len(indices)} notificación(es)")

    def generar_notificaciones_automaticas(self):
        hoy = datetime.now().date()
        nuevas_notificaciones = []
        plantillas = {
            'recordatorio_7dias': ("Recordatorio: Su pago vence en 7 días",
                "Estimado/a {nombre}, le recordamos que su pago para {servicios} vence el {fecha_vencimiento}. "
                "Por favor realice el pago a tiempo para evitar suspensiones."),
            'recordatorio_3dias': ("Recordatorio: Su pago vence en 3 días",
                "Estimado/a {nombre}, le recordamos que su pago para {servicios} vence el {fecha_vencimiento}. "
                "Por favor realice el pago para mantener sus servicios activos."),
            'recordatorio_1dia': ("Alerta: Su pago vence mañana",
                "Estimado/a {nombre}, su pago para {servicios} vence mañana {fecha_vencimiento}. "
                "Por favor realice el pago hoy para evitar interrupciones en su servicio."),
            'mora_1dia': ("Alerta: Su pago está vencido",
                "Estimado/a {nombre}, su pago para {servicios} venció el {fecha_vencimiento}. "
                "Por favor regularice su situación lo antes posible para reactivar sus servicios."),
            'mora_3dias': ("Alerta: Su pago tiene 3 días de mora",
                "Estimado/a {nombre}, su pago para {servicios} tiene 3 días de mora desde el {fecha_vencimiento}. "
                "Sus servicios serán suspendidos en 2 días si no realiza el pago."),
            'mora_5dias': ("Alerta: Sus servicios serán suspendidos",
                "Estimado/a {nombre}, su pago para {servicios} tiene 5 días de mora desde el {fecha_vencimiento}. "
                "Sus servicios serán suspendidos mañana si no realiza el pago."),
            'pago_recibido': ("Confirmación: Pago recibido",
                "Estimado/a {nombre}, hemos recibido su pago para {servicios}. "
                "Gracias por su puntualidad. Su próxima fecha de vencimiento es {fecha_vencimiento}.")
        }
        for registro in self.contabilidad_data.get('monitoreo', []):
            if not registro.get('fecha_ultimo_pago'):
                continue
            try:
                fecha_pago = datetime.strptime(registro['fecha_ultimo_pago'], "%Y-%m-%d").date()
                fecha_vencimiento = fecha_pago + timedelta(days=30)
                dias_restantes = (fecha_vencimiento - hoy).days
                dias_mora = (hoy - fecha_vencimiento).days if hoy > fecha_vencimiento else 0
                servicios = []
                if registro.get('eps'): servicios.append("EPS")
                if registro.get('arl'): servicios.append("ARL")
                if registro.get('pension'): servicios.append("Pensión")
                if registro.get('caja_compensacion'): servicios.append("Caja de Compensación")
                servicios_str = ", ".join(servicios) if servicios else "servicios"
                if dias_mora == 0:
                    if dias_restantes == 7:
                        titulo, mensaje = plantillas['recordatorio_7dias']
                        tipo, tag = "Recordatorio", "recordatorio"
                    elif dias_restantes == 3:
                        titulo, mensaje = plantillas['recordatorio_3dias']
                        tipo, tag = "Alerta", "alerta"
                    elif dias_restantes == 1:
                        titulo, mensaje = plantillas['recordatorio_1dia']
                        tipo, tag = "Alerta Urgente", "alerta"
                    else:
                        continue
                else:
                    if dias_mora == 1:
                        titulo, mensaje = plantillas['mora_1dia']
                        tipo, tag = "Mora", "mora"
                    elif dias_mora == 3:
                        titulo, mensaje = plantillas['mora_3dias']
                        tipo, tag = "Mora", "mora"
                    elif dias_mora == 5:
                        titulo, mensaje = plantillas['mora_5dias']
                        tipo, tag = "Suspensión", "mora"
                    else:
                        continue
                mensaje_formateado = mensaje.format(
                    nombre=registro['nombre'],
                    servicios=servicios_str,
                    fecha_vencimiento=fecha_vencimiento.strftime("%d/%m/%Y")
                )
                notificacion_existente = False
                for notif in self.contabilidad_data['notificaciones']:
                    if (notif['cc'] == registro['cc'] and 
                        notif['tipo'] == tipo and 
                        notif['fecha_vencimiento'] == fecha_vencimiento.strftime("%Y-%m-%d") and
                        datetime.strptime(notif['fecha'], "%Y-%m-%d").date() >= hoy - timedelta(days=1)):
                        notificacion_existente = True
                        break
                if not notificacion_existente:
                    nuevas_notificaciones.append({
                        "fecha": hoy.strftime("%Y-%m-%d"),
                        "tipo": tipo,
                        "cc": registro['cc'],
                        "nombre": registro['nombre'],
                        "mensaje": mensaje_formateado,
                        "estado": "Pendiente",
                        "fecha_vencimiento": fecha_vencimiento.strftime("%Y-%m-%d"),
                        "tag": tag
                    })
            except ValueError:
                continue
        for nueva in nuevas_notificaciones:
            # Insertar en BD
            self.db.add_notificacion(nueva)
            self.contabilidad_data['notificaciones'].append(nueva)
        self.actualizar_notificaciones()
        if nuevas_notificaciones:
            messagebox.showinfo("Notificaciones", f"Se generaron {len(nuevas_notificaciones)} nuevas notificaciones")
    
    def actualizar_notificaciones(self, data=None):
        """Actualiza la tabla de notificaciones con los datos proporcionados o todos los datos"""
        self.clear_treeview(self.notificaciones_tree)
        
        filtro = self.notificaciones_filtro_var.get()
        busqueda = self.notificaciones_busqueda_var.get().lower()
        
        data_to_show = []
        for notif in self.contabilidad_data['notificaciones']:
            # Aplicar filtro
            if filtro != "Todas":
                if filtro == "Recordatorios" and not notif['tipo'].startswith("Recordatorio"):
                    continue
                elif filtro == "Alertas" and not notif['tipo'].startswith("Alerta"):
                    continue
                elif filtro == "Mora" and notif['tipo'] not in ["Mora", "Suspensión"]:
                    continue
                elif filtro == "Pagos" and notif['tipo'] != "Confirmación":
                    continue
            
            # Aplicar búsqueda
            if busqueda and not (busqueda in notif['nombre'].lower() or 
                               busqueda in notif['cc'].lower() or
                               busqueda in notif['mensaje'].lower()):
                continue
            
            data_to_show.append(notif)
        
        # Ordenar por fecha de vencimiento (más cercanas primero)
        data_to_show.sort(key=lambda x: (
            x['estado'] != 'Pendiente',  # Pendientes primero
            datetime.strptime(x['fecha_vencimiento'], "%Y-%m-%d")
        ))
        
        for notif in data_to_show:
            self.notificaciones_tree.insert("", tk.END, values=(
                notif['fecha'],
                notif['tipo'],
                f"{notif['nombre']} (CC: {notif['cc']})",
                notif['mensaje'],
                notif['estado'],
                notif['fecha_vencimiento']
            ), tags=(notif.get('tag', ''),))
    
    def enviar_notificaciones_seleccionadas(self):
        """Envía las notificaciones seleccionadas por los medios disponibles"""
        selected_items = self.notificaciones_tree.selection()
        if not selected_items:
            messagebox.showerror("Error", "Por favor seleccione al menos una notificación para enviar")
            return
        
        # Obtener los índices de las notificaciones seleccionadas
        indices = [self.notificaciones_tree.index(item) for item in selected_items]
        
        # Filtrar solo las notificaciones pendientes
        notificaciones_a_enviar = []
        notificaciones_data = self.contabilidad_data['notificaciones']
        
        for index in indices:
            if index < len(notificaciones_data) and notificaciones_data[index]['estado'] == "Pendiente":
                notificaciones_a_enviar.append(notificaciones_data[index])
        
        if not notificaciones_a_enviar:
            messagebox.showinfo("Información", "No hay notificaciones pendientes seleccionadas")
            return
        
        # Mostrar opciones de envío
        ventana_envio = Toplevel(self.root)
        ventana_envio.title("Enviar Notificaciones")
        ventana_envio.geometry("500x300")
        
        # Variables
        self.metodo_envio_var = tk.StringVar(value="WhatsApp")
        self.plantilla_var = tk.StringVar()
        
        # Frame principal
        main_frame = ttk.Frame(ventana_envio)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        ttk.Label(main_frame, text="Enviar Notificaciones", style='Title.TLabel').pack(pady=(0, 20))
        
        # Método de envío
        metodo_frame = ttk.Frame(main_frame)
        metodo_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(metodo_frame, text="Método de envío:").pack(side=tk.LEFT, padx=5)
        ttk.Combobox(metodo_frame, textvariable=self.metodo_envio_var, 
                    values=["WhatsApp", "Email", "SMS"], state="readonly").pack(side=tk.LEFT, padx=5)
        
        # Resumen
        ttk.Label(main_frame, text=f"Se enviarán {len(notificaciones_a_enviar)} notificaciones:").pack(anchor=tk.W)
        
        # Lista de notificaciones con scroll
        lista_frame = ttk.Frame(main_frame)
        lista_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        canvas = tk.Canvas(lista_frame, height=100)
        scrollbar = ttk.Scrollbar(lista_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        for i, notif in enumerate(notificaciones_a_enviar):
            ttk.Label(scrollable_frame, 
                     text=f"{i+1}. {notif['nombre']} - {notif['tipo']}").pack(anchor=tk.W)
        
        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))
        
        ttk.Button(button_frame, text="Cancelar", command=ventana_envio.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Enviar", 
                 command=lambda: self.confirmar_envio_notificaciones(
                     notificaciones_a_enviar, ventana_envio)).pack(side=tk.RIGHT, padx=5)
    
    def confirmar_envio_notificaciones(self, notificaciones, ventana):
        metodo = self.metodo_envio_var.get()
        hoy = datetime.now().strftime("%Y-%m-%d")
        enviadas_con_exito = 0
        for notif in notificaciones:
            for i, n in enumerate(self.contabilidad_data['notificaciones']):
                if (n['cc'] == notif['cc'] and n['fecha'] == notif['fecha'] and
                    n['tipo'] == notif['tipo'] and n['estado'] == "Pendiente"):
                    n['estado'] = f"Enviada ({metodo} - {hoy})"
                    self.db.update_notificacion_estado(n['id'], n['estado'])
                    enviadas_con_exito += 1
                    break
        self.actualizar_notificaciones()
        messagebox.showinfo("Éxito", f"Se enviaron {enviadas_con_exito} notificaciones por {metodo}")
        ventana.destroy()
    
    def editar_plantilla_mensaje(self):
        """Permite editar las plantillas de mensajes para notificaciones"""
        ventana = Toplevel(self.root)
        ventana.title("Editar Plantillas de Mensajes")
        ventana.geometry("800x600")
        self.centrar_ventana(ventana, 800, 600)
        
        # Plantillas predefinidas
        plantillas = {
            'recordatorio_7dias': {
                'titulo': "Recordatorio: Su pago vence en 7 días",
                'mensaje': "Estimado/a {nombre}, le recordamos que su pago para {servicios} vence el {fecha_vencimiento}. "
                          "Por favor realice el pago a tiempo para evitar suspensiones."
            },
            'recordatorio_3dias': {
                'titulo': "Recordatorio: Su pago vence en 3 días",
                'mensaje': "Estimado/a {nombre}, le recordamos que su pago para {servicios} vence el {fecha_vencimiento}. "
                          "Por favor realice el pago para mantener sus servicios activos."
            },
            'recordatorio_1dia': {
                'titulo': "Alerta: Su pago vence mañana",
                'mensaje': "Estimado/a {nombre}, su pago para {servicios} vence mañana {fecha_vencimiento}. "
                          "Por favor realice el pago hoy para evitar interrupciones en su servicio."
            },
            'mora_1dia': {
                'titulo': "Alerta: Su pago está vencido",
                'mensaje': "Estimado/a {nombre}, su pago para {servicios} venció el {fecha_vencimiento}. "
                          "Por favor regularice su situación lo antes posible para reactivar sus servicios."
            },
            'mora_3dias': {
                'titulo': "Alerta: Su pago tiene 3 días de mora",
                'mensaje': "Estimado/a {nombre}, su pago para {servicios} tiene 3 días de mora desde el {fecha_vencimiento}. "
                          "Sus servicios serán suspendidos en 2 días si no realiza el pago."
            },
            'mora_5dias': {
                'titulo': "Alerta: Sus servicios serán suspendidos",
                'mensaje': "Estimado/a {nombre}, su pago para {servicios} tiene 5 días de mora desde el {fecha_vencimiento}. "
                          "Sus servicios serán suspendidos mañana si no realiza el pago."
            },
            'pago_recibido': {
                'titulo': "Confirmación: Pago recibido",
                'mensaje': "Estimado/a {nombre}, hemos recibido su pago para {servicios}. "
                          "Gracias por su puntualidad. Su próxima fecha de vencimiento es {fecha_vencimiento}."
            }
        }
        
        # Cargar plantillas personalizadas si existen
        if 'plantillas_notificaciones' in self.contabilidad_data:
            for key, value in self.contabilidad_data['plantillas_notificaciones'].items():
                if key in plantillas:
                    plantillas[key] = value
        
        # Variables para edición
        self.plantilla_seleccionada_var = tk.StringVar()
        self.plantilla_titulo_var = tk.StringVar()
        self.plantilla_mensaje_var = tk.StringVar()
        
        # Frame principal
        main_frame = ttk.Frame(ventana)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Frame de selección de plantilla
        seleccion_frame = ttk.LabelFrame(main_frame, text="Seleccionar Plantilla", padding=10)
        seleccion_frame.pack(fill=tk.X, pady=5)
        
        # Lista de plantillas
        plantillas_lista = ttk.Combobox(seleccion_frame, textvariable=self.plantilla_seleccionada_var, 
                                      values=list(plantillas.keys()), state="readonly")
        plantillas_lista.pack(fill=tk.X, padx=5, pady=5)
        plantillas_lista.bind("<<ComboboxSelected>>", lambda e: self.cargar_plantilla(plantillas))
        
        # Frame de edición
        edicion_frame = ttk.LabelFrame(main_frame, text="Editar Plantilla", padding=10)
        edicion_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Título
        ttk.Label(edicion_frame, text="Título:").pack(anchor=tk.W, padx=5, pady=2)
        titulo_entry = ttk.Entry(edicion_frame, textvariable=self.plantilla_titulo_var, width=80)
        titulo_entry.pack(fill=tk.X, padx=5, pady=5)
        
        # Mensaje
        ttk.Label(edicion_frame, text="Mensaje:").pack(anchor=tk.W, padx=5, pady=2)
        mensaje_text = tk.Text(edicion_frame, height=10, width=80)
        mensaje_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Variables disponibles
        variables_frame = ttk.LabelFrame(main_frame, text="Variables Disponibles", padding=10)
        variables_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(variables_frame, 
                 text="{nombre}, {servicios}, {fecha_vencimiento}, {dias_restantes}, {dias_mora}").pack()
        
        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))
        
        ttk.Button(button_frame, text="Cancelar", command=ventana.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Guardar Cambios", 
                 command=lambda: self.guardar_plantilla(
                     plantillas, mensaje_text.get("1.0", tk.END), ventana)).pack(side=tk.RIGHT, padx=5)
        
        # Cargar primera plantilla por defecto
        if plantillas:
            self.plantilla_seleccionada_var.set(next(iter(plantillas)))
            self.cargar_plantilla(plantillas)
    
    def cargar_plantilla(self, plantillas):
        """Carga los datos de la plantilla seleccionada en los campos de edición"""
        plantilla_key = self.plantilla_seleccionada_var.get()
        if plantilla_key in plantillas:
            plantilla = plantillas[plantilla_key]
            self.plantilla_titulo_var.set(plantilla['titulo'])
            
            # Necesitamos acceder al widget Text para actualizarlo
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Text):
                    widget.delete("1.0", tk.END)
                    widget.insert("1.0", plantilla['mensaje'])
                    break
    
    def guardar_plantilla(self, plantillas, mensaje, ventana):
        plantilla_key = self.plantilla_seleccionada_var.get()
        if plantilla_key in plantillas:
            titulo = self.plantilla_titulo_var.get()
            self.db.save_plantilla(plantilla_key, titulo, mensaje.strip())
            if 'plantillas_notificaciones' not in self.contabilidad_data:
                self.contabilidad_data['plantillas_notificaciones'] = {}
            self.contabilidad_data['plantillas_notificaciones'][plantilla_key] = {'titulo': titulo, 'mensaje': mensaje.strip()}
            messagebox.showinfo("Éxito", "Plantilla guardada correctamente")
            ventana.destroy()
    
    def marcar_notificaciones_enviadas(self):
        selected_items = self.notificaciones_tree.selection()
        if not selected_items:
            messagebox.showerror("Error", "Por favor seleccione al menos una notificación")
            return
        indices = [self.notificaciones_tree.index(item) for item in selected_items]
        hoy = datetime.now().strftime("%Y-%m-%d")
        contador = 0
        for index in indices:
            if index < len(self.contabilidad_data['notificaciones']):
                n = self.contabilidad_data['notificaciones'][index]
                if n['estado'] == "Pendiente":
                    n['estado'] = f"Enviada (Manual - {hoy})"
                    self.db.update_notificacion_estado(n['id'], n['estado'])
                    contador += 1
        if contador > 0:
            self.actualizar_notificaciones()
            messagebox.showinfo("Éxito", f"{contador} notificaciones marcadas como enviadas")
        else:
            messagebox.showinfo("Información", "No hay notificaciones pendientes seleccionadas")
    
    def mostrar_detalles_notificacion(self):
        """Muestra los detalles completos de una notificación seleccionada"""
        selected_item = self.notificaciones_tree.selection()
        if not selected_item:
            return
            
        # Obtener datos del registro seleccionado
        index = self.notificaciones_tree.index(selected_item[0])
        registro = self.contabilidad_data['notificaciones'][index]
        
        # Calcular el caracter según el tipo
        tipo = registro['tipo']
        if tipo == "Recordatorio":
            caracter = "Puede Esperar"
        elif tipo == "Solicitud de Incapacidad":
            caracter = "En Espera"
        elif tipo in ["Alerta", "Mora", "Suspensión"]:  
            caracter = "No Da Espera"
        else:
            caracter = "Sin clasificar"  
        
        # Crear ventana emergente
        detalles_window = Toplevel(self.root)
        detalles_window.title(f"Detalles de Notificación - {tipo}")
        
        # Centrar ventana (más ancha y alta para el nuevo layout)
        ancho_pantalla = detalles_window.winfo_screenwidth()
        alto_pantalla = detalles_window.winfo_screenheight()
        ancho_ventana = 700
        alto_ventana = 550
        x = (ancho_pantalla // 2) - (ancho_ventana // 2)
        y = (alto_pantalla // 2) - (alto_ventana // 2)
        detalles_window.geometry(f"{ancho_ventana}x{alto_ventana}+{x}+{y}")
        detalles_window.resizable(False, False)
        
        # Frame principal
        main_frame = ttk.Frame(detalles_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Título
        ttk.Label(main_frame, text="Detalles de Notificación", style='Title.TLabel').pack(pady=(0, 15))
        
        # ----- Frame superior: dos columnas -----
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=5)
        
        # Columna izquierda: Fecha, Tipo, Caracter
        left_frame = ttk.LabelFrame(top_frame, text="Información Básica", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        campos_izq = [
            ("Fecha:", registro['fecha']),
            ("Tipo:", tipo),
            ("Caracter:", caracter)
        ]
        
        for i, (campo, valor) in enumerate(campos_izq):
            ttk.Label(left_frame, text=campo, font=('TkDefaultFont', 10, 'bold')).grid(row=i, column=0, sticky=tk.W, pady=4, padx=5)
            ttk.Label(left_frame, text=valor if valor else "No especificado").grid(row=i, column=1, sticky=tk.W, pady=4, padx=5)
        
        left_frame.columnconfigure(0, weight=0)
        left_frame.columnconfigure(1, weight=1)
        
        # Columna derecha: Afiliado, Estado, Fecha Vencimiento
        right_frame = ttk.LabelFrame(top_frame, text="Datos del Afiliado", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        campos_der = [
            ("Afiliado:", f"{registro['nombre']} (CC: {registro['cc']})"),
            ("Estado:", registro['estado']),
            ("Fecha Vencimiento:", registro['fecha_vencimiento'])
        ]
        
        for i, (campo, valor) in enumerate(campos_der):
            ttk.Label(right_frame, text=campo, font=('TkDefaultFont', 10, 'bold')).grid(row=i, column=0, sticky=tk.W, pady=4, padx=5)
            ttk.Label(right_frame, text=valor if valor else "No especificado").grid(row=i, column=1, sticky=tk.W, pady=4, padx=5)
        
        right_frame.columnconfigure(0, weight=0)
        right_frame.columnconfigure(1, weight=1)
        
        # ----- Frame inferior: Mensaje (ocupa todo el ancho) -----
        bottom_frame = ttk.LabelFrame(main_frame, text="Mensaje", padding=10)
        bottom_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        from tkinter import scrolledtext
        mensaje_widget = scrolledtext.ScrolledText(
            bottom_frame,
            wrap=tk.WORD,
            font=('TkDefaultFont', 10),
            height=6,
            state='normal'
        )
        mensaje_widget.pack(fill=tk.BOTH, expand=True)
        mensaje_widget.insert('1.0', registro['mensaje'] if registro['mensaje'] else "Sin mensaje")
        mensaje_widget.config(state='disabled')  # Solo lectura
        
        # ----- Botones (abajo, centrados) -----
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(15, 5))
        
        ttk.Button(button_frame, text="↩️ Cerrar", command=detalles_window.destroy).pack(side=tk.RIGHT, padx=5)
        
        if self.user_role == "Administrativo":
            ttk.Button(button_frame, text="📤 Enviar Ahora",
                    command=lambda: self.enviar_notificacion_individual(index, detalles_window)).pack(side=tk.RIGHT, padx=5)
                                                    
    def enviar_notificacion_individual(self, index, ventana):
        if index >= len(self.contabilidad_data['notificaciones']):
            return
        notificacion = self.contabilidad_data['notificaciones'][index]
        hoy = datetime.now().strftime("%Y-%m-%d")
        notificacion['estado'] = f"Enviada (Manual - {hoy})"
        self.db.update_notificacion_estado(notificacion['id'], notificacion['estado'])
        self.actualizar_notificaciones()
        messagebox.showinfo("Éxito", f"Notificación enviada a {notificacion['nombre']}")
        ventana.destroy()
    
    def setup_caja_interface(self, parent):
        """Configura la interfaz de caja: solo movimientos (sin arqueo)"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(main_frame, text="Caja", style='Title.TLabel').pack(pady=(0, 10))

        # Variables para caja
        self.base_caja = 30000
        self.caja_fecha_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.caja_total_var = tk.StringVar(value=f"${self.base_caja:,.2f}")

        caja_container = ttk.Frame(main_frame)
        caja_container.pack(fill=tk.BOTH, expand=True)

        movimientos_frame = ttk.LabelFrame(caja_container, text="Movimientos de Caja", padding=10)
        movimientos_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Fecha (sigue arriba) ---
        top_controls = ttk.Frame(movimientos_frame)
        top_controls.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(top_controls, text="Fecha:").pack(side=tk.LEFT, padx=5)
        fecha_entry = ttk.Entry(top_controls, textvariable=self.caja_fecha_var, width=12)
        fecha_entry.pack(side=tk.LEFT, padx=5)
        # Los botones se han movido al final

        # --- Tabla ---
        table_frame = ttk.Frame(movimientos_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("Fecha", "Tipo", "Descripción", "Valor", "Método")
        self.caja_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        column_widths = {"Fecha": 90, "Tipo": 80, "Descripción": 200, "Valor": 100, "Método": 100}
        for col in columns:
            self.caja_tree.column(col, width=column_widths.get(col, 100), anchor=tk.CENTER)
            self.caja_tree.heading(col, text=col)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.caja_tree.yview)
        self.caja_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.caja_tree.pack(fill=tk.BOTH, expand=True)

        # --- Botones inferiores (Agregar, Editar, Eliminar) ---
        button_frame = ttk.Frame(movimientos_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="➕Agregar",
                command=self.agregar_movimiento_caja).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="✏️Editar",
                command=self.editar_movimiento_caja).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="✖️Eliminar",
                command=self.eliminar_movimiento_caja).pack(side=tk.LEFT, padx=5)

        # --- Total Caja (izquierda) y Botones de acción (derecha) ---
        bottom_frame = ttk.Frame(movimientos_frame)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))

        # Total a la izquierda
        total_frame = ttk.Frame(bottom_frame)
        total_frame.pack(side=tk.LEFT)
        ttk.Label(total_frame, text="Total Caja:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        ttk.Label(total_frame, textvariable=self.caja_total_var, font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)

        # Botones a la derecha
        action_frame = ttk.Frame(bottom_frame)
        action_frame.pack(side=tk.RIGHT)

        ttk.Button(action_frame, text="📦Registrar Caja", command=self.hacer_caja).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="📋Historial", command=self.mostrar_historial_cajas).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="♻️Exportar a Excel", command=self.exportar_caja_excel).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="🔒Cerrar Caja", command=self.cerrar_caja).pack(side=tk.LEFT, padx=5)

        self.hacer_caja()
            
    def cerrar_caja(self):
        """Abre la ventana de cierre de caja con conteo físico y resumen, y opciones de PDF/Excel."""
        fecha = self.caja_fecha_var.get()
        hoy = datetime.now().strftime("%Y-%m-%d")
        if fecha != hoy:
            if not messagebox.askyesno("Fecha diferente",
                                    f"La fecha de caja es {fecha}, pero hoy es {hoy}.\n"
                                    "¿Desea cambiar la fecha a hoy?"):
                return
            self.caja_fecha_var.set(hoy)
            fecha = hoy

        # Obtener ingresos y egresos del día
        ingresos_dia = [i for i in self.contabilidad_data['ingresos'] if i['fecha'] == fecha]
        egresos_dia = [e for e in self.contabilidad_data['egresos'] if e['fecha'] == fecha]

        total_ingresos_sistema = sum(i['valor'] for i in ingresos_dia)
        total_egresos = sum(e['valor'] for e in egresos_dia)
        total_caja_esperado = self.base_caja + total_ingresos_sistema - total_egresos

        # Ventana de cierre
        ventana = Toplevel(self.root)
        ventana.title("Cierre de Caja")
        ventana.geometry("1100x460")
        self.centrar_ventana(ventana, 1100, 460)
        ventana.resizable(False, False)

        # ========== FRAME SUPERIOR: HORAS ==========
        top_frame = ttk.Frame(ventana, padding=5)
        top_frame.pack(fill=tk.X, padx=10, pady=(5,0))
        ttk.Label(top_frame, text="Hora de Apertura:").pack(side=tk.LEFT, padx=5)
        apertura_var = tk.StringVar(value=f"{hoy} 08:00")
        ttk.Entry(top_frame, textvariable=apertura_var, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Label(top_frame, text="Hora de Cierre:").pack(side=tk.LEFT, padx=5)
        cierre_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d %H:%M"))
        ttk.Entry(top_frame, textvariable=cierre_var, width=20).pack(side=tk.LEFT, padx=5)

        # Panel principal con dos columnas
        paned = ttk.PanedWindow(ventana, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ========== PANEL IZQUIERDO (conteo) ==========
        left_frame = ttk.Frame(paned, padding=10)
        paned.add(left_frame, weight=1)
        left_frame.columnconfigure(0, weight=1)
        left_frame.columnconfigure(1, weight=1)

        # --- Monedas ---
        monedas_frame = ttk.LabelFrame(left_frame, text="Monedas", padding=5)
        monedas_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        ttk.Label(monedas_frame, text="Denominación").grid(row=0, column=0, padx=5, pady=2)
        ttk.Label(monedas_frame, text="Cantidad").grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(monedas_frame, text="Total").grid(row=0, column=2, padx=5, pady=2)
        monedas = [50, 100, 200, 500, 1000]
        vars_monedas = {}
        for i, valor in enumerate(monedas, 1):
            var = tk.IntVar(value=0)
            vars_monedas[str(valor)] = var
            ttk.Label(monedas_frame, text=f"${valor:,}").grid(row=i, column=0, padx=5, pady=2)
            ttk.Entry(monedas_frame, textvariable=var, width=5, justify=tk.CENTER).grid(row=i, column=1, padx=5, pady=2)
            total_var = tk.StringVar(value="$0")
            ttk.Label(monedas_frame, textvariable=total_var).grid(row=i, column=2, padx=5, pady=2)

        # --- Billetes ---
        billetes_frame = ttk.LabelFrame(left_frame, text="Billetes", padding=5)
        billetes_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        ttk.Label(billetes_frame, text="Denominación").grid(row=0, column=0, padx=5, pady=2)
        ttk.Label(billetes_frame, text="Cantidad").grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(billetes_frame, text="Total").grid(row=0, column=2, padx=5, pady=2)
        billetes = [1000, 2000, 5000, 10000, 20000, 50000, 100000]
        vars_billetes = {}
        for i, valor in enumerate(billetes, 1):
            var = tk.IntVar(value=0)
            vars_billetes[str(valor)] = var
            ttk.Label(billetes_frame, text=f"${valor:,}").grid(row=i, column=0, padx=5, pady=2)
            ttk.Entry(billetes_frame, textvariable=var, width=5, justify=tk.CENTER).grid(row=i, column=1, padx=5, pady=2)
            total_var = tk.StringVar(value="$0")
            ttk.Label(billetes_frame, textvariable=total_var).grid(row=i, column=2, padx=5, pady=2)

        # --- Transferencias ---
        transf_frame = ttk.LabelFrame(left_frame, text="Transferencias", padding=5)
        transf_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        ttk.Label(transf_frame, text="Monto declarado:").grid(row=0, column=0, padx=5, pady=2)
        transf_declarado_var = tk.DoubleVar(value=0.0)
        ttk.Entry(transf_frame, textvariable=transf_declarado_var, width=15).grid(row=0, column=1, padx=5, pady=2)

        # --- Tarjeta ---
        tarjeta_frame = ttk.LabelFrame(left_frame, text="Tarjeta", padding=5)
        tarjeta_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        if "Tarjeta" in self.metodos_pago:
            ttk.Label(tarjeta_frame, text="Monto declarado:").grid(row=0, column=0, padx=5, pady=2)
            tarjeta_declarado_var = tk.DoubleVar(value=0.0)
            ttk.Entry(tarjeta_frame, textvariable=tarjeta_declarado_var, width=15).grid(row=0, column=1, padx=5, pady=2)
        else:
            ttk.Label(tarjeta_frame, text="Método no activo", foreground="gray").pack(pady=10)

        # ========== PANEL DERECHO (Resumen del día) ==========
        right_frame = ttk.Frame(paned, padding=10)
        paned.add(right_frame, weight=1)

        ttk.Label(right_frame, text="Resumen del Día", style='Title.TLabel').pack(pady=(0, 10))
        ttk.Label(right_frame, text=f"Fecha: {fecha}", font=('Arial', 10)).pack(anchor=tk.W)

        # Variables dinámicas para el resumen
        efectivo_var = tk.StringVar(value="$0.00")
        transferencia_var = tk.StringVar(value="$0.00")
        tarjeta_var = tk.StringVar(value="$0.00") if "Tarjeta" in self.metodos_pago else None
        total_ingresos_arqueado_var = tk.StringVar(value="$0.00")

        # Ingresos por Método
        metodos_frame = ttk.LabelFrame(right_frame, text="Ingresos por Método", padding=5)
        metodos_frame.pack(fill=tk.X, pady=5)

        fila = 0
        ttk.Label(metodos_frame, text="Efectivo:", font=('Arial', 9, 'bold')).grid(row=fila, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(metodos_frame, textvariable=efectivo_var, font=('Arial', 9)).grid(row=fila, column=1, sticky=tk.W, padx=5, pady=2)
        fila += 1

        ttk.Label(metodos_frame, text="Transferencia:", font=('Arial', 9, 'bold')).grid(row=fila, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(metodos_frame, textvariable=transferencia_var, font=('Arial', 9)).grid(row=fila, column=1, sticky=tk.W, padx=5, pady=2)
        fila += 1

        if tarjeta_var is not None:
            ttk.Label(metodos_frame, text="Tarjeta:", font=('Arial', 9, 'bold')).grid(row=fila, column=0, sticky=tk.W, padx=5, pady=2)
            ttk.Label(metodos_frame, textvariable=tarjeta_var, font=('Arial', 9)).grid(row=fila, column=1, sticky=tk.W, padx=5, pady=2)
            fila += 1

        ttk.Separator(right_frame, orient='horizontal').pack(fill=tk.X, pady=10)

        # Totales generales
        total_frame = ttk.Frame(right_frame)
        total_frame.pack(fill=tk.X, pady=5)

        ttk.Label(total_frame, text="Total Ingresos:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Label(total_frame, textvariable=total_ingresos_arqueado_var, font=('Arial', 10)).grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(total_frame, text="Total Egresos:", font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, padx=5)
        ttk.Label(total_frame, text=f"${total_egresos:,.2f}", font=('Arial', 10)).grid(row=1, column=1, sticky=tk.W, padx=5)

        # ========== NUEVO: Opciones de cierre (checkboxes) ==========
        opciones_frame = ttk.LabelFrame(right_frame, text="Opciones de cierre", padding=5)
        opciones_frame.pack(fill=tk.X, pady=5)
        self.generar_pdf_var = tk.BooleanVar(value=True)
        self.exportar_excel_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opciones_frame, text="Generar comprobante PDF", variable=self.generar_pdf_var).pack(anchor=tk.W)
        ttk.Checkbutton(opciones_frame, text="Exportar a Excel", variable=self.exportar_excel_var).pack(anchor=tk.W)

        # ========== FUNCIÓN DE RECÁLCULO ==========
        def recalcular_arqueo(*args):
            total_efectivo = 0
            for valor_str, var in vars_monedas.items():
                total_efectivo += int(valor_str) * var.get()
            for valor_str, var in vars_billetes.items():
                total_efectivo += int(valor_str) * var.get()

            transf_dec = transf_declarado_var.get()
            tarjeta_dec = tarjeta_declarado_var.get() if tarjeta_var is not None else 0.0

            total_arqueado = total_efectivo + transf_dec + tarjeta_dec

            efectivo_var.set(f"${total_efectivo:,.2f}")
            transferencia_var.set(f"${transf_dec:,.2f}")
            if tarjeta_var is not None:
                tarjeta_var.set(f"${tarjeta_dec:,.2f}")
            total_ingresos_arqueado_var.set(f"${total_arqueado:,.2f}")

        # Vincular eventos
        for var in vars_monedas.values():
            var.trace('w', recalcular_arqueo)
        for var in vars_billetes.values():
            var.trace('w', recalcular_arqueo)
        transf_declarado_var.trace('w', recalcular_arqueo)
        if tarjeta_var is not None:
            tarjeta_declarado_var.trace('w', recalcular_arqueo)

        # ========== BOTONES ==========
        button_frame = ttk.Frame(ventana)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="🧹 Limpiar", command=lambda: self._limpiar_campos_cierre(
            vars_monedas, vars_billetes, transf_declarado_var,
            tarjeta_declarado_var if tarjeta_var is not None else None
        )).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="✅ Confirmar Cierre", command=lambda: self._confirmar_cierre(
            ventana, fecha, apertura_var.get(), cierre_var.get(),
            total_ingresos_sistema, total_egresos, total_caja_esperado,
            vars_monedas, vars_billetes,
            transf_declarado_var,
            tarjeta_declarado_var if tarjeta_var is not None else None,
            ingresos_dia, egresos_dia,
            self.generar_pdf_var.get(), self.exportar_excel_var.get()
        )).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="✖ Cerrar", command=ventana.destroy).pack(side=tk.LEFT, padx=5)

        # Cálculo inicial
        recalcular_arqueo()
                    
    def _limpiar_campos_cierre(self, vars_monedas, vars_billetes, transf_var, tarjeta_var):
        """Pone todas las cantidades a cero."""
        for var in vars_monedas.values():
            var.set(0)
        for var in vars_billetes.values():
            var.set(0)
        if transf_var:
            transf_var.set(0.0)
        if tarjeta_var:
            tarjeta_var.set(0.0)

    def _confirmar_cierre(self, ventana, fecha, apertura, cierre,
                        total_ingresos, total_egresos, caja_esperada,
                        vars_monedas, vars_billetes,
                        transf_var, tarjeta_var,
                        ingresos_dia, egresos_dia,
                        generar_pdf=True, exportar_excel=False):
        """Genera el comprobante en PDF y/o Excel según las opciones, y cierra la ventana."""
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        import os, sys, subprocess

        # Calcular el arqueo a partir de las variables
        total_efectivo = 0
        detalle_monedas = []
        for valor_str, var in vars_monedas.items():
            cant = var.get()
            if cant:
                subtotal = int(valor_str) * cant
                total_efectivo += subtotal
                detalle_monedas.append([f"${int(valor_str):,}", str(cant), f"${subtotal:,.2f}"])
        detalle_billetes = []
        for valor_str, var in vars_billetes.items():
            cant = var.get()
            if cant:
                subtotal = int(valor_str) * cant
                total_efectivo += subtotal
                detalle_billetes.append([f"${int(valor_str):,}", str(cant), f"${subtotal:,.2f}"])

        transf_dec = transf_var.get() if transf_var else 0.0
        tarjeta_dec = tarjeta_var.get() if tarjeta_var else 0.0
        total_arqueado = total_efectivo + transf_dec + tarjeta_dec

        # ========== VALIDACIÓN: debe haber al menos un medio de pago registrado ==========
        if total_arqueado == 0:
            messagebox.showerror("Error", "No hay ningún medio de pago registrado.\n"
                                        "Debe ingresar al menos un monto en Efectivo, Transferencia o Tarjeta.")
            return

        # Crear directorio Caja (unificado)
        caja_dir = os.path.join(BASE_PATH, "Caja")
        os.makedirs(caja_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"Cierre_{fecha}_{timestamp}"

        # ========== GENERAR PDF si está activado ==========
        if generar_pdf:
            pdf_path = os.path.join(caja_dir, f"{base_filename}.pdf")
            doc = SimpleDocTemplate(pdf_path, pagesize=letter,
                                    leftMargin=1.5*cm, rightMargin=1.5*cm,
                                    topMargin=1.5*cm, bottomMargin=1.5*cm)
            elements = []
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle('TitleStyle', parent=styles['Title'],
                                        fontSize=16, textColor=colors.HexColor('#1a237e'),
                                        alignment=TA_CENTER, spaceAfter=12)
            header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'],
                                        fontSize=10, textColor=colors.HexColor('#333333'))

            # Logo
            logo_path = os.path.join(IMG_PATH, "LogoSaluPago.png")
            if os.path.exists(logo_path):
                try:
                    logo = Image(logo_path, width=3*cm, height=3*cm)
                    elements.append(logo)
                except:
                    pass

            elements.append(Paragraph("COMPROBANTE DE CIERRE DE CAJA", title_style))
            elements.append(Spacer(1, 0.3*cm))

            # Datos del cierre
            empresa = self.config.get('empresa.nombre', 'SaluPago')
            responsable = self.username
            datos = [
                ["Empresa:", empresa],
                ["Responsable:", responsable],
                ["Fecha de Apertura:", apertura],
                ["Fecha de Cierre:", cierre],
                ["Fondo inicial:", f"${self.base_caja:,.2f}"],
                ["Total Ingresos del día:", f"${total_ingresos:,.2f}"],
                ["Total Egresos del día:", f"${total_egresos:,.2f}"],
                ["Caja esperada:", f"${caja_esperada:,.2f}"],
                ["Total Arqueado:", f"${total_arqueado:,.2f}"],
                ["Diferencia:", f"${total_arqueado - caja_esperada:,.2f}"]
            ]
            tabla_datos = Table(datos, colWidths=[4*cm, 6*cm])
            tabla_datos.setStyle(TableStyle([
                ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
                ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('ALIGN', (0,0), (0,-1), 'RIGHT'),
                ('ALIGN', (1,0), (1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e3f2fd')),
            ]))
            elements.append(tabla_datos)
            elements.append(Spacer(1, 0.5*cm))

            # Desglose de monedas y billetes
            if detalle_monedas:
                elements.append(Paragraph("Monedas contadas:", header_style))
                tabla_monedas = Table([["Denominación", "Cantidad", "Subtotal"]] + detalle_monedas,
                                    colWidths=[2.5*cm, 2.5*cm, 3*cm])
                tabla_monedas.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a237e')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0), (-1,0), 9),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
                    ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
                ]))
                elements.append(tabla_monedas)
                elements.append(Spacer(1, 0.3*cm))

            if detalle_billetes:
                elements.append(Paragraph("Billetes contados:", header_style))
                tabla_billetes = Table([["Denominación", "Cantidad", "Subtotal"]] + detalle_billetes,
                                    colWidths=[2.5*cm, 2.5*cm, 3*cm])
                tabla_billetes.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a237e')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0), (-1,0), 9),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
                    ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
                ]))
                elements.append(tabla_billetes)
                elements.append(Spacer(1, 0.3*cm))

            if transf_dec:
                elements.append(Paragraph(f"Transferencias declaradas: ${transf_dec:,.2f}", header_style))
            if tarjeta_dec:
                elements.append(Paragraph(f"Tarjeta declarada: ${tarjeta_dec:,.2f}", header_style))

            elements.append(Spacer(1, 0.5*cm))
            elements.append(Paragraph("Este comprobante es un registro del cierre de caja.", styles['Italic']))
            elements.append(Paragraph(f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Italic']))

            doc.build(elements)

            # Abrir automáticamente el PDF
            try:
                if sys.platform == 'win32':
                    os.startfile(pdf_path)
                elif sys.platform == 'darwin':
                    subprocess.call(('open', pdf_path))
                else:
                    subprocess.call(('xdg-open', pdf_path))
            except:
                pass

            messagebox.showinfo("Comprobante generado", f"Comprobante PDF guardado en:\n{pdf_path}")

        # ========== GENERAR EXCEL si está activado ==========
        if exportar_excel:
            excel_path = os.path.join(caja_dir, f"{base_filename}.xlsx")
            self._generar_excel_cierre(
                excel_path,
                fecha, apertura, cierre,
                ingresos_dia, egresos_dia,
                total_ingresos, total_egresos,
                caja_esperada, total_arqueado,
                detalle_monedas, detalle_billetes,
                transf_dec, tarjeta_dec
            )
            messagebox.showinfo("Exportación Excel", f"Archivo Excel guardado en:\n{excel_path}")

        # Cerrar la ventana de cierre
        ventana.destroy()
            
    def _generar_excel_cierre(self, excel_path, fecha, apertura, cierre,
                            ingresos_dia, egresos_dia,
                            total_ingresos, total_egresos,
                            caja_esperada, total_arqueado,
                            detalle_monedas, detalle_billetes,
                            transf_dec, tarjeta_dec):
        """
        Genera un archivo Excel con el resumen del cierre de caja.
        """
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
            from openpyxl.utils import get_column_letter
        except ImportError:
            if messagebox.askyesno("Dependencia faltante",
                                "El módulo 'openpyxl' es requerido para exportar a Excel.\n"
                                "¿Desea instalarlo ahora?"):
                import subprocess, sys
                subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl"])
                import openpyxl
                from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
                from openpyxl.utils import get_column_letter
            else:
                return

        wb = openpyxl.Workbook()

        # ========== Hoja 1: Resumen ==========
        ws_resumen = wb.active
        ws_resumen.title = "Resumen"

        empresa = self.config.get('empresa.nombre', 'SaluPago')
        responsable = self.username

        bold_font = Font(bold=True)
        center_align = Alignment(horizontal='center', vertical='center')
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                            top=Side(style='thin'), bottom=Side(style='thin'))

        datos_resumen = [
            ("Empresa:", empresa),
            ("Responsable:", responsable),
            ("Fecha de Apertura:", apertura),
            ("Fecha de Cierre:", cierre),
            ("Fondo inicial:", f"${self.base_caja:,.2f}"),
            ("Total Ingresos del día:", f"${total_ingresos:,.2f}"),
            ("Total Egresos del día:", f"${total_egresos:,.2f}"),
            ("Caja esperada:", f"${caja_esperada:,.2f}"),
            ("Total Arqueado:", f"${total_arqueado:,.2f}"),
            ("Diferencia:", f"${total_arqueado - caja_esperada:,.2f}")
        ]

        for row_idx, (label, value) in enumerate(datos_resumen, start=1):
            ws_resumen.cell(row=row_idx, column=1, value=label).font = bold_font
            ws_resumen.cell(row=row_idx, column=2, value=value)

        ws_resumen.column_dimensions['A'].width = 20
        ws_resumen.column_dimensions['B'].width = 20

        # ========== Hoja 2: Movimientos ==========
        ws_mov = wb.create_sheet("Movimientos")
        headers = ["Fecha", "Tipo", "Descripción", "Valor", "Método"]
        ws_mov.append(headers)
        for col in range(1, len(headers)+1):
            ws_mov.cell(row=1, column=col).font = bold_font
            ws_mov.cell(row=1, column=col).alignment = center_align

        for i in ingresos_dia:
            ws_mov.append([i['fecha'], "Ingreso", i['servicio'], i['valor'], i['metodo_pago']])
        for e in egresos_dia:
            ws_mov.append([e['fecha'], "Egreso", e['descripcion'], e['valor'], e['metodo_pago']])

        for col in range(1, len(headers)+1):
            ws_mov.column_dimensions[get_column_letter(col)].width = 15

        # ========== Hoja 3: Arqueo ==========
        ws_arq = wb.create_sheet("Arqueo")

        if detalle_monedas:
            ws_arq.append(["MONEDAS", "", ""])
            ws_arq.append(["Denominación", "Cantidad", "Subtotal"])
            for row in detalle_monedas:
                ws_arq.append(row)
            ws_arq.append([])

        if detalle_billetes:
            ws_arq.append(["BILLETES", "", ""])
            ws_arq.append(["Denominación", "Cantidad", "Subtotal"])
            for row in detalle_billetes:
                ws_arq.append(row)
            ws_arq.append([])

        ws_arq.append(["OTROS CONCEPTOS", "", ""])
        ws_arq.append(["Transferencias declaradas", "", f"${transf_dec:,.2f}"])
        if tarjeta_dec > 0:
            ws_arq.append(["Tarjeta declarada", "", f"${tarjeta_dec:,.2f}"])
        ws_arq.append([])
        ws_arq.append(["Total Arqueado", "", f"${total_arqueado:,.2f}"])

        for row in ws_arq.iter_rows(min_row=1, max_row=ws_arq.max_row):
            for cell in row:
                cell.alignment = center_align

        wb.save(excel_path)
                            
    def center_window(self, window):
        """Centra la ventana en la pantalla"""
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f'+{x}+{y}')
    
    def calc_button_pressed(self, button):
        """Maneja los eventos de los botones de la calculadora"""
        current = self.calc_input.get()
        
        if button == 'C':
            self.calc_input.set("0")
        elif button == 'CE':
            self.calc_input.set(current[:-1] if len(current) > 1 else "0")
        elif button == '=':
            try:
                result = eval(current)
                self.calc_input.set(str(result))
            except:
                self.calc_input.set("Error")
        else:
            if current == "0" or current == "Error":
                self.calc_input.set(button)
            else:
                self.calc_input.set(current + button)

    def mostrar_historial_cajas(self):
        """Muestra una ventana con el historial de cajas exportadas (PDF y Excel)."""
        try:
            historial_window = Toplevel(self.root)
            historial_window.title("Historial de Cajas Exportadas")
            historial_window.geometry("850x450")
            self.centrar_ventana(historial_window, 850, 450)

            main_frame = ttk.Frame(historial_window, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)

            ttk.Label(main_frame, text="Historial de Archivos de Caja", 
                    style='Title.TLabel').pack(pady=(0, 10))

            columns = ("Fecha", "Tipo", "Archivo", "Ubicación")
            tree = ttk.Treeview(main_frame, columns=columns, show="headings", selectmode="browse")

            tree.column("Fecha", width=120, anchor=tk.W)
            tree.column("Tipo", width=80, anchor=tk.CENTER)
            tree.column("Archivo", width=200, anchor=tk.W)
            tree.column("Ubicación", width=350, anchor=tk.W)

            for col in columns:
                tree.heading(col, text=col)

            scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscroll=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            tree.pack(fill=tk.BOTH, expand=True)

            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=(10, 0))

            ttk.Button(button_frame, text="Abrir Archivo", 
                    command=lambda: self.abrir_archivo_caja(tree)).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Actualizar", 
                    command=lambda: self.cargar_archivos_caja(tree)).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Cerrar", 
                    command=historial_window.destroy).pack(side=tk.RIGHT, padx=5)

            self.cargar_archivos_caja(tree)
            tree.bind("<Double-1>", lambda e: self.abrir_archivo_caja(tree))

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el historial:\n{str(e)}")
            
    def cargar_archivos_caja(self, tree):
        """Carga los archivos de caja (PDF y Excel) desde la carpeta Caja."""
        try:
            for item in tree.get_children():
                tree.delete(item)

            caja_path = os.path.join(BASE_PATH, "Caja")
            if not os.path.exists(caja_path):
                messagebox.showinfo("Información", "No se ha encontrado la carpeta de caja.")
                return

            # Listar todos los archivos .pdf y .xlsx
            archivos = [f for f in os.listdir(caja_path) if f.endswith((".pdf", ".xlsx"))]
            if not archivos:
                messagebox.showinfo("Información", "No hay archivos de caja en el historial.")
                return

            archivos.sort(reverse=True)

            for archivo in archivos:
                fecha = self._extraer_fecha_del_nombre(archivo)
                tipo = "PDF" if archivo.endswith(".pdf") else "Excel"
                ruta = os.path.join(caja_path, archivo)
                tree.insert("", tk.END, values=(fecha, tipo, archivo, ruta))

        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los archivos:\n{str(e)}")
                    
    def _extraer_fecha_del_nombre(self, nombre):
        import re
        # Busca YYYY-MM-DD o YYYYMMDD
        patrones = [
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
            r'(\d{8})'               # YYYYMMDD
        ]
        for patron in patrones:
            match = re.search(patron, nombre)
            if match:
                fecha_str = match.group(1)
                try:
                    if len(fecha_str) == 8:
                        fecha = datetime.strptime(fecha_str, "%Y%m%d").strftime("%Y-%m-%d")
                    else:
                        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").strftime("%Y-%m-%d")
                    return fecha
                except:
                    pass
        return "Fecha desconocida"

    def abrir_archivo_caja(self, tree):
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showwarning("Advertencia", "Por favor seleccione un archivo del historial")
            return

        item = tree.item(selected_item[0])
        ruta_archivo = item['values'][3]  # columna Ubicación
        tipo = item['values'][1]          # columna Tipo

        if not os.path.exists(ruta_archivo):
            messagebox.showerror("Error", "El archivo seleccionado ya no existe en la ubicación original")
            return

        try:
            if tipo == "PDF":
                # Usar el visor interno de PDF
                self.mostrar_pdf_interno(ruta_archivo, self.root)
            else:
                # Excel: abrir con programa predeterminado
                if sys.platform == 'win32':
                    os.startfile(ruta_archivo)
                elif sys.platform == 'darwin':
                    subprocess.run(['open', ruta_archivo])
                else:
                    subprocess.run(['xdg-open', ruta_archivo])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el archivo:\n{str(e)}")
                            
    def cargar_archivos_caja(self, tree):
        """Carga los archivos de caja exportados en el Treeview"""
        try:
            # Limpiar treeview
            for item in tree.get_children():
                tree.delete(item)
            
            # Definir ruta de la carpeta Caja
            caja_path = os.path.join(BASE_PATH, "Caja")
            
            # Verificar si existe la carpeta
            if not os.path.exists(caja_path):
                messagebox.showinfo("Información", "No se ha encontrado la carpeta de cajas exportadas")
                return
            
            # Obtener todos los archivos Excel de caja
            archivos = [f for f in os.listdir(caja_path) if f.startswith("Caja_") and f.endswith(".xlsx")]
            
            if not archivos:
                messagebox.showinfo("Información", "No hay cajas exportadas en el historial")
                return
            
            # Ordenar archivos por fecha (más reciente primero)
            archivos.sort(reverse=True)
            
            # Agregar al treeview
            for archivo in archivos:
                try:
                    # Extraer fecha del nombre del archivo
                    fecha_str = archivo.replace("Caja_", "").replace(".xlsx", "")
                    fecha = datetime.strptime(fecha_str, "%Y-%m-%d").strftime("%Y-%m-%d")
                    
                    # Agregar al treeview
                    tree.insert("", tk.END, values=(fecha, archivo, os.path.join(caja_path, archivo)))
                except:
                    continue  # Si hay un archivo con formato incorrecto, lo saltamos
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los archivos:\n{str(e)}")

    def abrir_archivo_caja(self, tree):
        """Abre el archivo de caja seleccionado con el programa predeterminado"""
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showwarning("Advertencia", "Por favor seleccione un archivo del historial")
            return

        item = tree.item(selected_item[0])
        ruta_archivo = item['values'][2]

        if not os.path.exists(ruta_archivo):
            messagebox.showerror("Error", "El archivo seleccionado ya no existe en la ubicación original")
            return

        try:
            if sys.platform == 'win32':
                os.startfile(ruta_archivo)
            elif sys.platform == 'darwin':
                subprocess.run(['open', ruta_archivo])
            else:
                subprocess.run(['xdg-open', ruta_archivo])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el archivo:\n{str(e)}")
            
    def hacer_caja(self):
        fecha_seleccionada = self.caja_fecha_var.get()
        self.clear_treeview(self.caja_tree)
        movimientos = []
        total_caja = self.base_caja
        for ingreso in self.contabilidad_data['ingresos']:
            if ingreso['fecha'] == fecha_seleccionada:
                movimientos.append({
                    "Fecha": ingreso['fecha'],
                    "Tipo": "Ingreso",
                    "Descripción": f"{ingreso['servicio']} - {ingreso['nombre']}",
                    "Valor": ingreso['valor'],
                    "Método": ingreso['metodo_pago']
                })
                total_caja += ingreso['valor']
        for egreso in self.contabilidad_data['egresos']:
            if egreso['fecha'] == fecha_seleccionada:
                movimientos.append({
                    "Fecha": egreso['fecha'],
                    "Tipo": "Egreso",
                    "Descripción": egreso['descripcion'],
                    "Valor": -egreso['valor'],
                    "Método": egreso['metodo_pago']
                })
                total_caja -= egreso['valor']
        movimientos.sort(key=lambda x: x['Fecha'])
        for mov in movimientos:
            valor_formateado = f"${abs(mov['Valor']):,.2f}"
            if mov['Valor'] < 0:
                valor_formateado = f"(${abs(mov['Valor']):,.2f})"
            self.caja_tree.insert("", tk.END, values=(
                mov['Fecha'],
                mov['Tipo'],
                mov['Descripción'],
                valor_formateado,
                mov['Método']
            ))
        self.caja_total_var.set(f"${total_caja:,.2f}")
        # Ya no se llama a calcular_arqueo()
        
    def agregar_movimiento_caja(self):
        """Muestra formulario para agregar un movimiento manual a la caja"""
        ventana = Toplevel(self.root)
        ventana.title("Editar Movimiento de Caja")
        ventana.geometry("400x300")
        self.centrar_ventana(ventana, 400, 300)
        
        # Variables
        fecha_var = tk.StringVar(value=self.caja_fecha_var.get())
        tipo_var = tk.StringVar(value="Ingreso")
        descripcion_var = tk.StringVar()
        valor_var = tk.StringVar()
        metodo_pago_var = tk.StringVar(value="Efectivo")
        
        # Formulario
        ttk.Label(ventana, text="Agregar Movimiento", style='Title.TLabel').pack(pady=10)
        
        frame = ttk.Frame(ventana)
        frame.pack(pady=10, padx=20, fill=tk.X)
        
        self.create_form_field(frame, "Fecha:", fecha_var, 0)
        self.create_combobox_field(frame, "Tipo:", tipo_var, ["Ingreso", "Egreso"], 1)
        self.create_form_field(frame, "Descripción:", descripcion_var, 2, width=30)
        self.create_form_field(frame, "Valor:", valor_var, 3)
        self.create_combobox_field(frame, "Método Pago:", metodo_pago_var, 
                                 self.metodos_pago, 4)
        
        # Botones
        button_frame = ttk.Frame(ventana)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Cancelar", command=ventana.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Guardar", 
                  command=lambda: self.guardar_movimiento_caja(
                      fecha_var.get(), tipo_var.get(), descripcion_var.get(), 
                      valor_var.get(), metodo_pago_var.get(), ventana)).pack(side=tk.LEFT, padx=5)

    def guardar_movimiento_caja(self, fecha, tipo, descripcion, valor, metodo_pago, ventana):
        if not descripcion or not valor:
            messagebox.showerror("Error", "Descripción y valor son obligatorios")
            return
        try:
            valor_float = float(valor)
        except ValueError:
            messagebox.showerror("Error", "El valor debe ser un número válido")
            return
        if tipo == "Ingreso":
            data = {
                "fecha": fecha,
                "cc": "Manual",
                "nombre": "Movimiento manual",
                "servicio": descripcion,
                "valor": valor_float,
                "metodo_pago": metodo_pago,
                "comprobante": "Manual"
            }
            new_id = self.db.add_ingreso(data)
            data['id'] = new_id
            self.contabilidad_data['ingresos'].append(data)
            # === AUDITORÍA ===
            self._registrar_auditoria("Agregó movimiento de caja", "Caja", "Éxito", f"Descripción: {descripcion}")
        else:
            data = {
                "fecha": fecha,
                "descripcion": descripcion,
                "valor": valor_float,
                "metodo_pago": metodo_pago
            }
            new_id = self.db.add_egreso(data)
            data['id'] = new_id
            self.contabilidad_data['egresos'].append(data)
            # === AUDITORÍA ===
            self._registrar_auditoria("Agregó movimiento de caja", "Caja", "Éxito", f"Descripción: {descripcion}")
        self.hacer_caja()
        ventana.destroy()
        self.mostrar_toast("Movimiento registrado correctamente")
        self.refrescar_sistema(silent=True)
        
    def editar_movimiento_caja(self):
        """Permite editar un movimiento de caja seleccionado"""
        selected_item = self.caja_tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Por favor seleccione un movimiento para editar")
            return
            
        # Obtener datos del registro seleccionado
        item = self.caja_tree.item(selected_item[0])
        valores = item['values']
        
        # Determinar si es ingreso o egreso
        es_ingreso = valores[1] == "Ingreso"
        
        # Buscar el registro original en los datos
        fecha = valores[0]
        descripcion = valores[2]
        valor_str = valores[3].replace("(", "").replace(")", "").replace("$", "")
        valor = float(valor_str.replace(",", ""))
        metodo = valores[4]
        
        registro = None
        index = -1
        
        if es_ingreso:
            for i, ingreso in enumerate(self.contabilidad_data['ingresos']):
                if (ingreso['fecha'] == fecha and 
                    ingreso['servicio'] in descripcion and 
                    ingreso['valor'] == valor and 
                    ingreso['metodo_pago'] == metodo):
                    registro = ingreso
                    index = i
                    break
        else:
            for i, egreso in enumerate(self.contabilidad_data['egresos']):
                if (egreso['fecha'] == fecha and 
                    egreso['descripcion'] == descripcion and 
                    egreso['valor'] == valor and 
                    egreso['metodo_pago'] == metodo):
                    registro = egreso
                    index = i
                    break
        
        if not registro:
            messagebox.showerror("Error", "No se encontró el registro original")
            return
            
        # Crear ventana de edición
        ventana = Toplevel(self.root)
        ventana.title("Editar Movimiento de Caja")
        ventana.geometry("400x300")
        
        # Variables
        fecha_var = tk.StringVar(value=registro['fecha'])
        tipo_var = tk.StringVar(value="Ingreso" if es_ingreso else "Egreso")
        descripcion_var = tk.StringVar(value=registro['servicio'] if es_ingreso else registro['descripcion'])
        valor_var = tk.StringVar(value=str(registro['valor']))
        metodo_pago_var = tk.StringVar(value=registro['metodo_pago'])
        
        # Formulario
        ttk.Label(ventana, text="Editar Movimiento", style='Title.TLabel').pack(pady=10)
        
        frame = ttk.Frame(ventana)
        frame.pack(pady=10, padx=20, fill=tk.X)
        
        self.create_form_field(frame, "Fecha:", fecha_var, 0)
        tipo_cb = self.create_combobox_field(frame, "Tipo:", tipo_var, ["Ingreso", "Egreso"], 1)
        tipo_cb.config(state='readonly')  # No permitir cambiar el tipo
        
        desc_entry = self.create_form_field(frame, "Descripción:", descripcion_var, 2, width=30)
        valor_entry = self.create_form_field(frame, "Valor:", valor_var, 3)
        metodo_cb = self.create_combobox_field(frame, "Método Pago:", metodo_pago_var, 
                                             self.metodos_pago, 4)
        
        # Botones
        button_frame = ttk.Frame(ventana)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Cancelar", command=ventana.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Guardar", 
                  command=lambda: self.actualizar_movimiento_caja(
                      es_ingreso, index, fecha_var.get(), descripcion_var.get(), 
                      valor_var.get(), metodo_pago_var.get(), ventana)).pack(side=tk.LEFT, padx=5)

    def actualizar_movimiento_caja(self, es_ingreso, index, fecha, descripcion, valor, metodo_pago, ventana):
        if not descripcion or not valor:
            messagebox.showerror("Error", "Descripción y valor son obligatorios")
            return
        try:
            valor_float = float(valor)
        except ValueError:
            messagebox.showerror("Error", "El valor debe ser un número válido")
            return
        if es_ingreso:
            if index < len(self.contabilidad_data['ingresos']):
                old = self.contabilidad_data['ingresos'][index]
                data = {
                    "fecha": fecha,
                    "cc": old.get('cc', 'Manual'),
                    "nombre": old.get('nombre', 'Movimiento manual'),
                    "servicio": descripcion,
                    "valor": valor_float,
                    "metodo_pago": metodo_pago,
                    "comprobante": old.get('comprobante', 'Manual')
                }
                self.db.delete_ingreso(old['id'])
                new_id = self.db.add_ingreso(data)
                data['id'] = new_id
                self.contabilidad_data['ingresos'][index] = data
                # === AUDITORÍA ===
                self._registrar_auditoria("Editó movimiento de caja", "Caja", "Éxito", f"Descripción: {descripcion}")
        else:
            if index < len(self.contabilidad_data['egresos']):
                old = self.contabilidad_data['egresos'][index]
                data = {
                    "fecha": fecha,
                    "descripcion": descripcion,
                    "valor": valor_float,
                    "metodo_pago": metodo_pago
                }
                self.db.delete_egreso(old['id'])
                new_id = self.db.add_egreso(data)
                data['id'] = new_id
                self.contabilidad_data['egresos'][index] = data
                # === AUDITORÍA ===
                self._registrar_auditoria("Editó movimiento de caja", "Caja", "Éxito", f"Descripción: {descripcion}")
        self.hacer_caja()
        ventana.destroy()
        self.mostrar_toast("Movimiento actualizado correctamente")
        self.refrescar_sistema(silent=True)
        
    def eliminar_movimiento_caja(self):
        selected_item = self.caja_tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Por favor seleccione un movimiento para eliminar")
            return
        if not self.validar_password():
            return
        item = self.caja_tree.item(selected_item[0])
        valores = item['values']
        es_ingreso = valores[1] == "Ingreso"
        fecha = valores[0]
        descripcion = valores[2]
        valor_str = valores[3].replace("(", "").replace(")", "").replace("$", "")
        valor = float(valor_str.replace(",", ""))
        metodo = valores[4]
        index = -1
        if es_ingreso:
            for i, ing in enumerate(self.contabilidad_data['ingresos']):
                if (ing['fecha'] == fecha and ing['servicio'] in descripcion and
                    ing['valor'] == valor and ing['metodo_pago'] == metodo):
                    index = i
                    break
            if index >= 0:
                self.db.delete_ingreso(self.contabilidad_data['ingresos'][index]['id'])
                del self.contabilidad_data['ingresos'][index]
                # === AUDITORÍA ===
                self._registrar_auditoria("Eliminó movimiento de caja", "Caja", "Éxito", f"Descripción: {descripcion}")
        else:
            for i, eg in enumerate(self.contabilidad_data['egresos']):
                if (eg['fecha'] == fecha and eg['descripcion'] == descripcion and
                    eg['valor'] == valor and eg['metodo_pago'] == metodo):
                    index = i
                    break
            if index >= 0:
                self.db.delete_egreso(self.contabilidad_data['egresos'][index]['id'])
                del self.contabilidad_data['egresos'][index]
                # === AUDITORÍA ===
                self._registrar_auditoria("Eliminó movimiento de caja", "Caja", "Éxito", f"Descripción: {descripcion}")
        if index < 0:
            messagebox.showerror("Error", "No se encontró el registro original")
            return
        self.hacer_caja()
        self.mostrar_toast("Movimiento eliminado correctamente")
        self.refrescar_sistema(silent=True)
        
    def exportar_caja_excel(self):
        """Exporta el reporte de caja a Excel (solo movimientos del día)."""
        try:
            try:
                import openpyxl
            except ImportError:
                if messagebox.askyesno("Dependencia faltante", 
                                    "El módulo 'openpyxl' es requerido pero no está instalado. ¿Instalarlo ahora?"):
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl"])
                    import openpyxl
                else:
                    return

            caja_path = os.path.join(BASE_PATH, "Caja")
            os.makedirs(caja_path, exist_ok=True)

            fecha_actual = datetime.now().strftime("%Y-%m-%d")
            file_path = os.path.join(caja_path, f"Caja_{fecha_actual}.xlsx")

            movimientos = []
            for item in self.caja_tree.get_children():
                valores = self.caja_tree.item(item)['values']
                movimientos.append({
                    "Fecha": valores[0],
                    "Tipo": valores[1],
                    "Descripción": valores[2],
                    "Valor": float(valores[3].replace("(", "").replace(")", "").replace("$", "").replace(",", "")),
                    "Método": valores[4]
                })

            movimientos.append({
                "Fecha": "",
                "Tipo": "",
                "Descripción": "TOTAL CAJA",
                "Valor": float(self.caja_total_var.get().replace("$", "").replace(",", "")),
                "Método": ""
            })

            df = pd.DataFrame(movimientos)
            df.to_excel(file_path, index=False, engine='openpyxl')

            if messagebox.askyesno("Éxito", f"Archivo guardado en:\n{file_path}\n\n¿Abrir carpeta?"):
                os.startfile(caja_path)

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar:\n{str(e)}")
            
    def setup_ayuda_interface(self, parent):
        """Configura la interfaz de ayuda dentro del contenedor 'parent'"""
        main_frame = ttk.Frame(parent)   # <-- usar parent
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        ttk.Label(main_frame, text="❓ Ayuda y Soporte", style='Title.TLabel').pack(pady=(0, 20))
        
        # Pestañas de ayuda
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Pestaña de instrucciones
        self.setup_instrucciones_tab(notebook)
        
        # Pestaña de información
        self.setup_info_tab(notebook)
        
        # Pestaña de roles (solo para Administrativo)
        if self.user_role == "Administrativo":
            self.setup_roles_tab(notebook)

        # Pestaña de soporte
        self.setup_soporte_tab(notebook)

    def setup_soporte_tab(self, notebook):
        """Configura la pestaña de soporte técnico con opciones de contacto"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Soporte Técnico")
        
        # Contenedor principal
        container = ttk.Frame(frame)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Información de contacto
        info_label = ttk.Label(
            container,
            text="""Si necesita asistencia técnica o tiene alguna pregunta, puede contactarnos a través de los siguientes medios:""",
            font=('Arial', 10),
            justify=tk.LEFT
        )
        info_label.pack(pady=(0, 20), anchor=tk.W)
        
        # Datos de contacto
        contact_frame = ttk.Frame(container)
        contact_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(contact_frame, text="Desarrollador:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Label(contact_frame, text="R.A.V ").grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(contact_frame, text="Teléfono:", font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Label(contact_frame, text="3022386236").grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(contact_frame, text="Email:", font=('Arial', 10, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Label(contact_frame, text="andresberri15@gmail.com").grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Botones de contacto
        button_frame = ttk.Frame(container)
        button_frame.pack(pady=20)
        
        whatsapp_btn = ttk.Button(
            button_frame,
            text="Contactar por WhatsApp",
            command=self.abrir_whatsapp,
            style='Accent.TButton'
        )
        whatsapp_btn.pack(side=tk.LEFT, padx=10, ipadx=10, ipady=5)
        
        email_btn = ttk.Button(
            button_frame,
            text="Contactar por Email",
            command=self.abrir_email,
            style='Accent.TButton'
        )
        email_btn.pack(side=tk.LEFT, padx=10, ipadx=10, ipady=5)

    def abrir_whatsapp(self):
        """Abre WhatsApp con el número de soporte"""
        numero = "3022386236"
        mensaje = "Hola, podrías asesorarme necesito ayuda de soporte técnico para el sistema de SaluPago."
        
        # Crear ventana emergente
        popup = tk.Toplevel()
        popup.title("Contactar por WhatsApp")
        popup.geometry("400x230")
        popup.resizable(False, False)
        
        # Centrar ventana
        popup.update_idletasks()
        ancho = popup.winfo_width()
        alto = popup.winfo_height()
        x = (popup.winfo_screenwidth() // 2) - (ancho // 2)
        y = (popup.winfo_screenheight() // 2) - (alto // 2)
        popup.geometry(f"+{x}+{y}")
        
        # Contenido de la ventana
        ttk.Label(popup, text="¿Desea contactar al soporte técnico por WhatsApp?", 
                font=('Arial', 10)).pack(pady=20)
        
        ttk.Label(popup, text=f"Número: {numero}", font=('Arial', 10, 'bold')).pack()
        ttk.Label(popup, text="Mensaje predeterminado:", font=('Arial', 10)).pack(pady=(10, 0))
        ttk.Label(popup, text=mensaje, font=('Arial', 9), wraplength=350).pack()
        
        # Botones
        btn_frame = ttk.Frame(popup)
        btn_frame.pack(pady=15)
        
        ttk.Button(
            btn_frame,
            text="Abrir WhatsApp",
            command=lambda: self.iniciar_whatsapp(numero, mensaje),
            style='Accent.TButton'
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(
            btn_frame,
            text="Cancelar",
            command=popup.destroy
        ).pack(side=tk.LEFT, padx=10)

    def iniciar_whatsapp(self, numero, mensaje):
        """Inicia WhatsApp con el número y mensaje predeterminado"""
        try:
            import webbrowser
            url = f"https://wa.me/{numero}?text={mensaje.replace(' ', '%20')}"
            webbrowser.open_new(url)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir WhatsApp: {str(e)}")

    def abrir_email(self):
        """Abre el cliente de email con los datos de soporte"""
        email = "andresberri15@gmail.com"
        asunto = "Soporte Técnico - Sistema SaluPago"
        cuerpo = "Hola, necesito asistencia con el siguiente tema:"
        
        # Crear ventana emergente
        popup = tk.Toplevel()
        popup.title("Contactar por Email")
        popup.geometry("450x250")
        popup.resizable(False, False)
        
        # Centrar ventana
        popup.update_idletasks()
        ancho = popup.winfo_width()
        alto = popup.winfo_height()
        x = (popup.winfo_screenwidth() // 2) - (ancho // 2)
        y = (popup.winfo_screenheight() // 2) - (alto // 2)
        popup.geometry(f"+{x}+{y}")
        
        # Contenido de la ventana
        ttk.Label(popup, text="¿Desea contactar al soporte técnico por Email?", 
                font=('Arial', 10)).pack(pady=20)
        
        ttk.Label(popup, text=f"Email: {email}", font=('Arial', 10, 'bold')).pack()
        ttk.Label(popup, text="Asunto predeterminado:", font=('Arial', 10)).pack(pady=(10, 0))
        ttk.Label(popup, text=asunto, font=('Arial', 9)).pack()
        ttk.Label(popup, text="Cuerpo del mensaje:", font=('Arial', 10)).pack(pady=(10, 0))
        ttk.Label(popup, text=cuerpo, font=('Arial', 9), wraplength=400).pack()
        
        # Botones
        btn_frame = ttk.Frame(popup)
        btn_frame.pack(pady=15)
        
        ttk.Button(
            btn_frame,
            text="Abrir Email",
            command=lambda: self.iniciar_email(email, asunto, cuerpo),
            style='Accent.TButton'
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(
            btn_frame,
            text="Cancelar",
            command=popup.destroy
        ).pack(side=tk.LEFT, padx=10)

    def iniciar_email(self, email, asunto, cuerpo):
        """Inicia Gmail en el navegador con los datos predeterminados"""
        try:
            import webbrowser
            import urllib.parse
            
            # URL para abrir Gmail directamente con los datos del correo
            url = f"https://mail.google.com/mail/?view=cm&fs=1&to={email}&su={urllib.parse.quote(asunto)}&body={urllib.parse.quote(cuerpo)}"
            
            webbrowser.open_new(url)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir Gmail: {str(e)}")
    
    def setup_instrucciones_tab(self, notebook):
        """Configura la pestaña de instrucciones (manual de uso)"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Instrucciones")
        
        text = tk.Text(frame, wrap=tk.WORD, padx=10, pady=10, font=('Arial', 10))
        text.pack(fill=tk.BOTH, expand=True)
        
        # Texto del manual actualizado
        instrucciones = """
        MANUAL DE USO COMPLETO - SISTEMA SALUPAGO

        IMPORTANTE: Todos los precios, opciones (EPS, ARL, fondos de pensión,
        cajas de compensación, métodos de pago) y datos de la empresa se
        configuran desde el menú Archivo → Configuración (solo para usuarios
        Administrativos). El sistema aplica automáticamente esos valores en
        toda la interfaz.


        1. GESTIÓN DE AFILIADOS

        1.1 Agregar un nuevo afiliado
        ----------------------------------------
        1. Vaya a la pestaña "Afiliados Activos"
        2. Presione el botón "Agregar"
        3. Complete el formulario:
            - Campos obligatorios: CC (cédula) y Nombre completo.
            - Debe seleccionar al menos un servicio (EPS, ARL, Pensión o Caja).
            - El sistema calculará automáticamente el valor a pagar según los
            precios configurados.
        4. Seleccione el mes de pago, método de pago y fecha de pago.
        5. Haga clic en "Guardar".

        Nota: El valor se calcula en tiempo real según los servicios elegidos
        y los precios definidos en la configuración del sistema.


        1.2 Editar un afiliado existente
        ----------------------------------------
        1. Seleccione el afiliado en la tabla (haga clic en la fila).
        2. Presione el botón "Editar" (solo visible para Administrativo).
        3. Modifique los campos necesarios (los precios se actualizan al cambiar servicios).
        4. Haga clic en "Guardar" para confirmar los cambios.


        1.3 Eliminar un afiliado (solo Administrativo)
        ----------------------------------------
        1. Seleccione el afiliado en la tabla.
        2. Presione el botón "Eliminar".
        3. Confirme la operación (se requiere autenticación administrativa).
        4. El afiliado será eliminado permanentemente del sistema.


        1.4 Añadir pago y generar factura
        ----------------------------------------
        1. Seleccione uno o más afiliados en la tabla (use Ctrl+clic para selección múltiple).
        2. Presione el botón "Generar Pago".
        3. Se abrirá una ventana de búsqueda; puede buscar y añadir más afiliados si lo desea.
        4. Seleccione los afiliados y haga clic en "Añadir Pago".
        5. Complete los datos del pago (mes, valor, método, fecha) y confirme.
        6. El sistema registrará el pago en contabilidad y generará automáticamente
        una factura en PDF, que se abrirá al finalizar.
        7. También puede generar la factura directamente desde la ventana de búsqueda.


        1.5 Retirar afiliados (solo Administrativo)
        ----------------------------------------
        1. Seleccione uno o más afiliados en la tabla.
        2. Presione el botón "Retirar".
        3. Confirme la operación.
        4. Los afiliados pasarán a la pestaña "Retiros" con la fecha de retiro actual.


        1.6 Ver detalles completos
        ----------------------------------------
        1. Localice al afiliado en la tabla.
        2. Haga doble clic sobre el registro.
        3. Se abrirá una ventana con todos los datos del afiliado (incluyendo beneficiarios).
        4. También puede acceder a la carpeta de documentos del afiliado desde allí.


        2. GESTIÓN DE RETIROS

        2.1 Exportar a Excel
        ----------------------------------------
        1. Vaya a la pestaña "Retiros".
        2. Presione el botón "Exportar a Excel".
        3. El archivo se guardará automáticamente en la carpeta "BaseRetiros"
        con el nombre "Retiros-MM-YYYY.xlsx".

        2.2 Reactivar afiliados (solo Administrativo)
        ----------------------------------------
        1. Seleccione uno o más retirados en la tabla.
        2. Presione el botón "Reactivar".
        3. Confirme la operación.
        4. Los afiliados volverán a la pestaña "Afiliados Activos" y su estado
        de monitoreo se actualizará a "Activo".

        2.3 Ver detalles de retirados
        ----------------------------------------
        1. Localice al retirado en la tabla.
        2. Haga doble clic sobre el registro.
        3. Se abrirá una ventana con todos los datos, incluyendo la fecha de retiro.


        3. GESTIÓN CONTABLE (C.H.I.N.)

        La pestaña C.H.I.N. agrupa Ingresos, Egresos, HistoriPago, Incapacidades y Novedades.

        3.1 Registrar ingresos manuales
        ----------------------------------------
        1. Vaya a C.H.I.N. → "Ingresos".
        2. Presione "Agregar".
        3. Complete los campos: fecha, CC, nombre, servicio, valor, método de pago y comprobante.
        4. Haga clic en "Guardar".
        (El ingreso se reflejará en los totales y en la caja del día).

        3.2 Registrar egresos
        ----------------------------------------
        1. Vaya a C.H.I.N. → "Egresos".
        2. Presione "Agregar".
        3. Complete: fecha, descripción, valor y método de pago.
        4. Haga clic en "Guardar".

        3.3 Registrar novedades
        ----------------------------------------
        1. Vaya a C.H.I.N. → "Novedades".
        2. Presione "Agregar".
        3. Busque al afiliado por CC o nombre.
        4. Ingrese la descripción de la novedad y guarde.

        3.4 Gestionar incapacidades
        ----------------------------------------
        1. Vaya a C.H.I.N. → "Incapacidades".
        2. Puede agregar, editar, eliminar o marcar como pagada/pendiente.
        3. Al agregar, busque al afiliado y complete los datos (tipo, fechas, valor).
        4. El sistema crea automáticamente una novedad asociada.

        3.5 Consultar movimientos y ver detalles
        ----------------------------------------
        - Todas las tablas muestran los movimientos ordenados por fecha.
        - Los totales (ingresos, egresos, saldo) se actualizan automáticamente.
        - Haga doble clic en cualquier registro para ver sus detalles completos.
        - En ingresos, puede buscar y abrir la factura PDF asociada desde la ventana de detalles.


        4. MONITOREO Y NOTIFICACIONES

        4.1 Monitoreo de pagos
        ----------------------------------------
        - La pestaña "Monitoreo" muestra el estado de cada afiliado según su fecha de pago.
        - Los estados (Activo, Próximo a vencer, Próximo a Suspender, Suspendido, Retirado)
        se calculan automáticamente según los umbrales definidos en Configuración.
        - Puede actualizar los estados manualmente o editar un registro específico.

        4.2 Notificaciones (solo Administrativo)
        ----------------------------------------
        - La pestaña "Notificaciones" gestiona alertas automáticas (recordatorios, mora, etc.)
        - Se generan en función de los días de mora y vencimiento.
        - Puede enviar notificaciones por WhatsApp o Gmail (si el afiliado tiene datos de contacto).
        - También puede editar las plantillas de mensajes desde el botón correspondiente.


        5. CAJA (solo Administrativo)

        5.1 Movimientos del día
        ----------------------------------------
        - La pestaña "Caja" muestra los ingresos y egresos del día seleccionado.
        - Puede agregar, editar o eliminar movimientos manualmente.
        - El total de caja se calcula automáticamente (base + ingresos - egresos).

        5.2 Arqueo de caja
        ----------------------------------------
        - En la sección derecha, ingrese las cantidades de monedas y billetes.
        - El sistema calcula el total arqueado y la diferencia con el total de caja.
        - Puede exportar el reporte de caja a Excel desde el botón correspondiente.


        6. FUNCIONES ADICIONALES

        6.1 Búsqueda de registros
        ----------------------------------------
        - En cada pestaña, use el campo "Buscar" para filtrar en tiempo real.
        - También puede usar el atajo Ctrl+F para enfocar la búsqueda en Afiliados Activos.
        - Presione Ctrl+B para abrir la búsqueda global (todos los afiliados, activos y retirados).

        6.2 Atajos de teclado
        ----------------------------------------
        - Ctrl+N : Nuevo afiliado
        - Ctrl+E : Editar afiliado seleccionado
        - Ctrl+R : Retirar afiliado seleccionado
        - Ctrl+D : Eliminar afiliado seleccionado
        - Ctrl+F : Enfocar búsqueda en Afiliados Activos
        - Ctrl+B : Búsqueda global
        - Ctrl+C : Copiar cédula del afiliado seleccionado
        - Ctrl+Q : Cerrar sesión
        - Ctrl+S : Crear copia de seguridad (Administrativo)
        - ESC    : Cerrar ventana emergente (doble ESC para salir del programa)

        6.3 Configuración del sistema (solo Administrativo)
        ----------------------------------------
        - Acceda desde Archivo → Configuración.
        - Allí puede modificar:
            - Precios de EPS, ARL, Pensión y Caja.
            - Umbrales de monitoreo (días para cambiar de estado).
            - Métodos de pago disponibles.
            - Datos de la empresa (nombre, NIT, dirección, teléfono, correo).
            - Ruta de la imagen de pago (mostrada en la ventana de pago).


        7. SOPORTE TÉCNICO

        Para asistencia con el sistema, contacte al desarrollador:

        * Desarrollador:R.A.V
        * Contacto: 3022386236
        * Email: andresberri15@gmail.com

        Notas importantes:
        - Todos los cambios se guardan automáticamente en la base de datos.
        - Se recomienda realizar copias de seguridad periódicas (Archivo → Respaldo → Backup).
        - Las facturas generadas se almacenan en la carpeta "facturas" y se abren automáticamente.
        - Los precios y opciones se toman de la configuración activa; asegúrese de revisarla
        antes de realizar operaciones masivas.

        Este manual está integrado en el sistema a través del menú Ayuda → Abrir Ayuda.
        """
        text.insert(tk.END, instrucciones)
        text.config(state=tk.DISABLED)
        
    def setup_info_tab(self, notebook):
        """Configura la pestaña de información"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Información del Sistema")
        
        text = tk.Text(frame, wrap=tk.WORD, padx=10, pady=10, font=('Arial', 10))
        text.pack(fill=tk.BOTH, expand=True)
        
        info = """
        INFORMACIÓN DEL SISTEMA

        Nombre: SaluPago - Sistema de Pagos a EPS
        Versión: 2.0
        Desarrollador:R.A.V
        Contacto: 3022386236
        Email: andresberri15@gmail.com
        Año: 2025

        Este sistema fue diseñado para:
        - Gestionar afiliados a EPS y ARL
        - Registrar pagos de seguridad social
        - Generar facturas y reportes
        - Llevar control contable automático

        Requisitos:
        - Python 3.6 o superior
        - Bibliotecas: tkinter, reportlab, pandas
        """
        text.insert(tk.END, info)
        text.config(state=tk.DISABLED)
    
    def setup_roles_tab(self, notebook):
        """Configura la pestaña de roles (solo para Administrativo)"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Gestión de Roles")
        
        text = tk.Text(frame, wrap=tk.WORD, padx=10, pady=10, font=('Arial', 10))
        text.pack(fill=tk.BOTH, expand=True)
        
        roles_info = """
        GESTIÓN DE ROLES Y PERMISOS

        El sistema cuenta con dos roles principales:

        1. Rol Administrativo:
           - Acceso completo a todas las funciones del sistema
           - Puede agregar, editar, eliminar y retirar afiliados
           - Acceso completo al módulo de contabilidad
           - Puede reactivar afiliados retirados
           - Puede gestionar usuarios y roles

        2. Rol Auxiliar:
           - Puede agregar nuevos afiliados
           - Puede facturar afiliados
           - Puede exportar datos a Excel
           - No puede editar, eliminar o retirar afiliados
           - No tiene acceso al módulo de contabilidad
           - No puede reactivar afiliados retirados

        Para cambiar entre roles o crear nuevos usuarios, contacte al administrador del sistema.
        """
        text.insert(tk.END, roles_info)
        text.config(state=tk.DISABLED)
    
    def setup_bindings(self):
        """Configura los eventos y bindings"""
        # Eventos de selección
        self.tree.bind("<<TreeviewSelect>>", self.seleccionar_registro)
        self.tree.bind("<Double-1>", self.mostrar_detalles_afiliado)
        self.retiros_tree.bind("<Double-1>", self.mostrar_detalles_retirado)
        
        if self.user_role == "Administrativo":
            self.ingresos_tree.bind("<Double-1>", lambda e: self.mostrar_detalles_contabilidad('ingresos'))
            self.egresos_tree.bind("<Double-1>", lambda e: self.mostrar_detalles_contabilidad('egresos'))
            self.novedades_tree.bind("<Double-1>", lambda e: self.mostrar_detalles_contabilidad('novedades'))
        
        # Actualizar tablas al inicio
        self.update_afiliados_table()
        self.update_retiros_table()
        
        if self.user_role == "Administrativo":
            self.update_contabilidad_tables()
    
    # ======================
    # Funcionalidades CRUD
    # ======================
    
    def create_form_field(self, parent, label, variable, row, width=25, required=False, state='normal'):
        """Crea un campo de formulario con label y entry"""
        label_style = 'Required.TLabel' if required else 'TLabel'
        ttk.Label(parent, text=label, style=label_style).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=2)
        entry = ttk.Entry(parent, textvariable=variable, width=width, state=state)
        # Cambiado a sticky=tk.W para que no se estire al ancho total
        entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        return entry
    
    def create_combobox_field(self, parent, label, variable, values, row, width=25, 
                            required=False, callback=None):
        """Crea un campo de formulario con combobox"""
        label_style = 'Required.TLabel' if required else 'TLabel'
        ttk.Label(parent, text=label, style=label_style).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=2)
        combobox = ttk.Combobox(parent, textvariable=variable, values=values, width=width)
        # Cambiado a sticky=tk.W para que no se estire al ancho total
        combobox.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        
        if callback:
            combobox.bind("<<ComboboxSelected>>", lambda e: callback())
        
        return combobox

    def show_afiliado_form(self, edit_mode=False, index=None):
        """Muestra el formulario para agregar/editar afiliados, con pestaña de beneficiarios."""
        self.beneficiarios_list = []
        self.tree_benef = None

        afiliado_window = Toplevel(self.root)
        afiliado_window.title("Editar Afiliado" if edit_mode else "Nuevo Afiliado")
        
        afiliado_window.geometry("1300x550")  
        self.centrar_ventana(afiliado_window, 1300, 550) 
        afiliado_window.resizable(False, False)

        main_frame = ttk.Frame(afiliado_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        self.notebook_afiliado = notebook

        # ---------- Pestaña 1: Datos del Afiliado ----------
        tab_datos = ttk.Frame(notebook)
        notebook.add(tab_datos, text="Datos del Afiliado")

        ttk.Label(tab_datos, text="Editar Afiliado" if edit_mode else "Nuevo Afiliado",
                style='Title.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 10))

        sections_frame = ttk.Frame(tab_datos)
        sections_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)

        tab_datos.columnconfigure(0, weight=1)
        tab_datos.columnconfigure(1, weight=1)
        tab_datos.rowconfigure(1, weight=1)

        sections_frame.columnconfigure(0, weight=1)
        sections_frame.columnconfigure(1, weight=2)
        sections_frame.columnconfigure(2, weight=3) 
        sections_frame.rowconfigure(0, weight=1)
        sections_frame.rowconfigure(1, weight=1)

        # ARRIBA IZQUIERDA: Imagen
        avatar_frame = ttk.Frame(sections_frame, padding=5)
        avatar_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        try:
            avatar_path = os.path.join(IMG_PATH, "LogoSaluPago.png")
            if os.path.exists(avatar_path):
                img = Image.open(avatar_path)
                img = img.resize((220, 220), Image.LANCZOS)
                img_tk = ImageTk.PhotoImage(img)
                img_label = ttk.Label(avatar_frame, image=img_tk)
                img_label.image = img_tk
                img_label.pack(expand=True)
            else:
                ttk.Label(avatar_frame, text="LogoSaluPago.png no encontrado", 
                         font=('Segoe UI', 10), foreground='gray').pack(expand=True)
        except Exception as e:
            ttk.Label(avatar_frame, text="Error al cargar imagen", 
                     font=('Segoe UI', 10), foreground='red').pack(expand=True)

        # ARRIBA CENTRO: Información Básica
        basic_frame = ttk.LabelFrame(sections_frame, text="Información Básica", padding=5)
        basic_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        
        self.create_form_field(basic_frame, "Número de CC*:", self.cc_var, 0, width=32, required=True)
        self.create_form_field(basic_frame, "Nombre Completo*:", self.nombre_var, 1, width=32, required=True)
        self.create_form_field(basic_frame, "Celular:", self.celular_var, 2, width=32)
        self.create_form_field(basic_frame, "Dirección:", self.direccion_var, 3, width=32)
        self.create_form_field(basic_frame, "Correo Electrónico:", self.correo_var, 4, width=32)
        self.create_form_field(basic_frame, "Fecha de Ingreso:", self.fecha_ingreso_var, 5, width=32)
        basic_frame.columnconfigure(1, weight=1)

        # ABAJO IZQUIERDA: Seguridad Social
        social_frame = ttk.LabelFrame(sections_frame, text="Seguridad Social", padding=5)
        social_frame.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        
        self.create_combobox_field(social_frame, "EPS:", self.eps_var, self.eps_options, 0, width=30, required=False, callback=self.calcular_precio)
        self.create_combobox_field(social_frame, "ARL:", self.arl_var, self.arl_options, 1, width=30, callback=self.calcular_precio)
        self.create_combobox_field(social_frame, "Fondo de Pensiones:", self.pension_var, self.pension_options, 2, width=30, callback=self.calcular_precio)
        self.create_combobox_field(social_frame, "Caja de Compensación:", self.caja_var, self.caja_compensacion_options, 3, width=30, callback=self.calcular_precio)
        social_frame.columnconfigure(1, weight=1)

        # ABAJO CENTRO: Información de Pago
        payment_frame = ttk.LabelFrame(sections_frame, text="Información de Pago", padding=5)
        payment_frame.grid(row=1, column=1, sticky="nsew", padx=2, pady=2)
        
        self.create_form_field(payment_frame, "Valor Pagado:", self.valor_pagado_var, 0, width=25)
        self.create_combobox_field(payment_frame, "Método de Pago:", self.metodo_pago_var, self.metodos_pago, 1, width=23)
        self.create_form_field(payment_frame, "Fecha de Pago:", self.fecha_pago_var, 2, width=25)
        payment_frame.columnconfigure(1, weight=1)

        # ==============================================
        # NUEVA COLUMNA DERECHA: Documentos Requeridos
        # ==============================================
        docs_frame = ttk.LabelFrame(sections_frame, text="Documentos Requeridos", padding=5)
        docs_frame.grid(row=0, column=2, rowspan=2, sticky="nsew", padx=2, pady=2)

        contenedor_checkboxes = ttk.Frame(docs_frame)
        contenedor_checkboxes.pack(fill=tk.BOTH, expand=True)

        # Variables de los checkboxes
        self.doc_id_afiliado_var = tk.BooleanVar(value=False)
        self.doc_id_hijo_var = tk.BooleanVar(value=False)
        self.doc_rc_hijo_var = tk.BooleanVar(value=False)
        self.doc_conyuge_var = tk.BooleanVar(value=False)
        self.doc_id_conyuge_var = tk.BooleanVar(value=False)
        self.doc_id_padre_var = tk.BooleanVar(value=False)
        self.doc_rc_padre_var = tk.BooleanVar(value=False)
        self.doc_id_madre_var = tk.BooleanVar(value=False)
        self.doc_rc_madre_var = tk.BooleanVar(value=False)
        self.doc_id_hermano_var = tk.BooleanVar(value=False)
        self.doc_rc_hermano_var = tk.BooleanVar(value=False)

        # Etiquetas y checkboxes estáticos (Afiliado)
        ttk.Label(contenedor_checkboxes, text="Documento de Identidad:\nMínimo para afiliación", 
                 font=('Segoe UI', 8, 'bold'), foreground='red', justify=tk.LEFT).pack(anchor=tk.W, pady=(0,5))
        ttk.Checkbutton(contenedor_checkboxes, text="Doc. Identidad (Afiliado)", variable=self.doc_id_afiliado_var, state='normal').pack(anchor=tk.W, pady=2)
        
        ttk.Separator(contenedor_checkboxes, orient='horizontal').pack(fill=tk.X, pady=5)
        
        ttk.Label(contenedor_checkboxes, text="Si tiene beneficiarios:", font=('Segoe UI', 8, 'italic')).pack(anchor=tk.W, pady=(0,5))

        # --- FRAMES DINÁMICOS (AHORA SIEMPRE VISIBLES) ---
        
        # Frame para Hijo
        frame_hijo = ttk.Frame(contenedor_checkboxes)
        frame_hijo.columnconfigure(0, weight=1, uniform="cb_col")
        frame_hijo.columnconfigure(1, weight=1, uniform="cb_col")
        ttk.Label(frame_hijo, text="Hijo", font=('Segoe UI', 9, 'bold'), foreground='#1a237e').grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(5, 2))
        ttk.Checkbutton(frame_hijo, text="Documento de Identidad", variable=self.doc_id_hijo_var, style='Small.TCheckbutton', state='normal').grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Checkbutton(frame_hijo, text="Registro Civil", variable=self.doc_rc_hijo_var, style='Small.TCheckbutton', state='normal').grid(row=1, column=1, sticky=tk.W, padx=(5, 0))
        ttk.Separator(frame_hijo, orient='horizontal').grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=(5,0))

        # Frame para Padres (Padre y Madre unificados)
        frame_padres = ttk.Frame(contenedor_checkboxes)
        frame_padres.columnconfigure(0, weight=1, uniform="cb_col")
        frame_padres.columnconfigure(1, weight=1, uniform="cb_col")
        ttk.Label(frame_padres, text="Padres", font=('Segoe UI', 9, 'bold'), foreground='#1a237e').grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(5, 2))
        ttk.Checkbutton(frame_padres, text="Doc. Identidad Padre", variable=self.doc_id_padre_var, style='Small.TCheckbutton', state='normal').grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Checkbutton(frame_padres, text="Registro Civil Padre", variable=self.doc_rc_padre_var, style='Small.TCheckbutton', state='normal').grid(row=1, column=1, sticky=tk.W, padx=(5, 0))
        ttk.Checkbutton(frame_padres, text="Doc. Identidad Madre", variable=self.doc_id_madre_var, style='Small.TCheckbutton', state='normal').grid(row=2, column=0, sticky=tk.W, padx=(0, 5), pady=(2,0))
        ttk.Checkbutton(frame_padres, text="Registro Civil Madre", variable=self.doc_rc_madre_var, style='Small.TCheckbutton', state='normal').grid(row=2, column=1, sticky=tk.W, padx=(5, 0), pady=(2,0))
        ttk.Separator(frame_padres, orient='horizontal').grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=(5,0))

        # Frame para Cónyuge
        frame_conyuge = ttk.Frame(contenedor_checkboxes)
        frame_conyuge.columnconfigure(0, weight=1, uniform="cb_col")
        frame_conyuge.columnconfigure(1, weight=1, uniform="cb_col")
        ttk.Label(frame_conyuge, text="Cónyuge", font=('Segoe UI', 9, 'bold'), foreground='#1a237e').grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(5, 2))
        ttk.Checkbutton(frame_conyuge, text="Carta de Unión", variable=self.doc_conyuge_var, style='Small.TCheckbutton', state='normal').grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Checkbutton(frame_conyuge, text="Documento de Identidad", variable=self.doc_id_conyuge_var, style='Small.TCheckbutton', state='normal').grid(row=1, column=1, sticky=tk.W, padx=(5, 0))
        ttk.Separator(frame_conyuge, orient='horizontal').grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=(5,0))

        # Frame para Hermano
        frame_hermano = ttk.Frame(contenedor_checkboxes)
        frame_hermano.columnconfigure(0, weight=1, uniform="cb_col")
        frame_hermano.columnconfigure(1, weight=1, uniform="cb_col")
        ttk.Label(frame_hermano, text="Hermano", font=('Segoe UI', 9, 'bold'), foreground='#1a237e').grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(5, 2))
        ttk.Checkbutton(frame_hermano, text="Documento de Identidad", variable=self.doc_id_hermano_var, style='Small.TCheckbutton', state='normal').grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Checkbutton(frame_hermano, text="Registro Civil", variable=self.doc_rc_hermano_var, style='Small.TCheckbutton', state='normal').grid(row=1, column=1, sticky=tk.W, padx=(5, 0))
        ttk.Separator(frame_hermano, orient='horizontal').grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=(5,0))

        # Empaquetar SIEMPRE los frames para que sean visibles desde el inicio
        frame_hijo.pack(anchor=tk.W, fill=tk.X, pady=(0, 5))
        frame_padres.pack(anchor=tk.W, fill=tk.X, pady=(0, 5))
        frame_conyuge.pack(anchor=tk.W, fill=tk.X, pady=(0, 5))
        frame_hermano.pack(anchor=tk.W, fill=tk.X, pady=(0, 5))

        # ---------- Pestaña 2: Beneficiarios ----------
        tab_benef = ttk.Frame(notebook)
        notebook.add(tab_benef, text="Beneficiarios")
        self.tab_benef = tab_benef
        self.setup_beneficiarios_tab(tab_benef, edit_mode, index, callback_actualizar_docs=None)

        self.actualizar_estado_pestania_beneficiarios()

        # Botones inferiores
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="Cancelar", command=afiliado_window.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Limpiar", command=self.limpiar_formulario).pack(side=tk.RIGHT, padx=5)

        if edit_mode:
            ttk.Button(button_frame, text="Guardar Cambios",
                    command=lambda: [self.guardar_afiliado(index, edit_mode=True),
                                        afiliado_window.destroy()]).pack(side=tk.RIGHT, padx=5)
        else:
            ttk.Button(button_frame, text="Guardar",
                    command=lambda: [self.guardar_afiliado(),
                                        afiliado_window.destroy()]).pack(side=tk.RIGHT, padx=5)

        if edit_mode and index is not None:
            registro = self.data[index]
            self.cc_var.set(registro['cc'])
            self.nombre_var.set(registro['nombre'])
            self.celular_var.set(registro['celular'])
            self.direccion_var.set(registro['direccion'])
            self.correo_var.set(registro['correo'])
            self.fecha_ingreso_var.set(registro['fecha_ingreso'])
            self.eps_var.set(registro['eps'] if registro['eps'] else "-/-")
            self.arl_var.set(registro['arl'] if registro['arl'] else "-/-")
            self.pension_var.set(registro['pension'] if registro['pension'] else "-/-")
            self.caja_var.set(registro['caja_compensacion'] if registro['caja_compensacion'] else "-/-")
            self.valor_pagado_var.set(registro['valor_pagado'])
            self.metodo_pago_var.set(registro.get('metodo_pago', ''))
            self.fecha_pago_var.set(registro['fecha_pago'])
            
            self.beneficiarios_list = self.db.get_beneficiarios(registro['cc'])
            self.actualizar_tabla_beneficiarios()
            self.actualizar_estado_pestania_beneficiarios()

            # Cargar estado de documentos requeridos (raíz + beneficiarios)
            self._cargar_estado_documentos(registro['cc'])
            self.actualizar_tabla_beneficiarios()
            self.actualizar_estado_pestania_beneficiarios()

    def actualizar_estado_pestania_beneficiarios(self):
        if hasattr(self, 'notebook_afiliado') and hasattr(self, 'tab_benef'):
            eps = self.eps_var.get().strip()
            if eps and eps != "-/-":
                self.notebook_afiliado.tab(self.tab_benef, state="normal")
            else:
                self.notebook_afiliado.tab(self.tab_benef, state="disabled")

    def _cargar_estado_documentos(self, cc_cotizante):
        """
        Escanea TODOS los documentos del afiliado (raíz + subcarpetas de beneficiarios)
        y marca los checkboxes de 'Documentos Requeridos' que correspondan.
        """
        # Resetear todos los checkboxes si existen
        variables = [
            'doc_id_afiliado_var', 'doc_id_hijo_var', 'doc_rc_hijo_var',
            'doc_id_padre_var', 'doc_rc_padre_var',
            'doc_id_madre_var', 'doc_rc_madre_var',
            'doc_conyuge_var', 'doc_id_conyuge_var',
            'doc_id_hermano_var', 'doc_rc_hermano_var'
        ]
        for var_name in variables:
            if hasattr(self, var_name):
                getattr(self, var_name).set(False)

        if not cc_cotizante:
            return

        carpeta_afiliado = os.path.join(BASE_PATH, "Documentos", cc_cotizante)
        if not os.path.exists(carpeta_afiliado):
            return

        # 1) Escanear archivos en la raíz del afiliado
        for arch in os.listdir(carpeta_afiliado):
            ruta_arch = os.path.join(carpeta_afiliado, arch)
            if os.path.isfile(ruta_arch):
                self._marcar_checkbox_por_archivo(arch)

        # 2) Escanear subcarpetas de Beneficiarios (una por cada beneficiario)
        carpeta_benef = os.path.join(carpeta_afiliado, "Beneficiarios")
        if os.path.exists(carpeta_benef):
            for nombre_benef in os.listdir(carpeta_benef):
                ruta_benef = os.path.join(carpeta_benef, nombre_benef)
                if os.path.isdir(ruta_benef):
                    for arch in os.listdir(ruta_benef):
                        ruta_arch = os.path.join(ruta_benef, arch)
                        if os.path.isfile(ruta_arch):
                            self._marcar_checkbox_por_archivo(arch)


    def _marcar_checkbox_por_archivo(self, nombre_archivo):
        """Marca el checkbox correspondiente según el prefijo del nombre del archivo."""
        if not nombre_archivo:
            return

        mapeo = {
            'ID_Afiliado':  'doc_id_afiliado_var',
            'ID_Hijo':      'doc_id_hijo_var',
            'RC_Hijo':      'doc_rc_hijo_var',
            'ID_Padre':     'doc_id_padre_var',
            'RC_Padre':     'doc_rc_padre_var',
            'ID_Madre':     'doc_id_madre_var',
            'RC_Madre':     'doc_rc_madre_var',
            'Carta_Union':  'doc_conyuge_var',
            'ID_Conyuge':   'doc_id_conyuge_var',
            'ID_Hermano':   'doc_id_hermano_var',
            'RC_Hermano':   'doc_rc_hermano_var',
        }

        for prefijo, var_name in mapeo.items():
            if nombre_archivo.startswith(prefijo):
                if hasattr(self, var_name):
                    getattr(self, var_name).set(True)
                return

    # =============================================================================
    # MÉTODOS AuxiliarES PARA LA GESTIÓN DE BENEFICIARIOS
    # =============================================================================

    def setup_beneficiarios_tab(self, parent, edit_mode, index, ventana_principal=None, callback_actualizar_docs=None):
        """Configura la pestaña de gestión de beneficiarios con botones abajo."""
        self.beneficiarios_list = []
        self.beneficiario_seleccionado = None
        self.callback_actualizar_docs = callback_actualizar_docs

        ttk.Label(parent, text="Beneficiarios", font=('Segoe UI', 14, 'bold')).pack(anchor=tk.CENTER, pady=(0, 5))

        columns = ("Documento", "Nombre", "Tipo", "Fecha Nac.")
        self.tree_benef = ttk.Treeview(parent, columns=columns, show="headings", height=4)
        for col in columns:
            self.tree_benef.heading(col, text=col)
            if col == "Documento": self.tree_benef.column(col, width=100, anchor=tk.CENTER)
            elif col == "Nombre": self.tree_benef.column(col, width=150, anchor=tk.CENTER)
            elif col == "Tipo": self.tree_benef.column(col, width=80, anchor=tk.CENTER)
            elif col == "Fecha Nac.": self.tree_benef.column(col, width=100, anchor=tk.CENTER)
        self.tree_benef.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        self.tree_benef.drop_target_register(DND_FILES)
        self.tree_benef.dnd_bind('<<Drop>>', self.on_drop_beneficiario)

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(btn_frame, text="➕ Agregar", command=lambda: self.agregar_beneficiario(parent)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="✖ Eliminar", command=lambda: self.eliminar_beneficiario(parent)).pack(side=tk.LEFT, padx=2)

        if edit_mode and index is not None:
            cc = self.data[index]['cc']
            self.beneficiarios_list = self.db.get_beneficiarios(cc)
            self.actualizar_tabla_beneficiarios()

        self.tree_benef.bind("<Double-1>", lambda e: self.editar_beneficiario(parent))

    def actualizar_tabla_beneficiarios(self):
        """Actualiza la tabla de beneficiarios con el nuevo orden de columnas."""
        for item in self.tree_benef.get_children():
            self.tree_benef.delete(item)
        for b in self.beneficiarios_list:
            self.tree_benef.insert("", tk.END, values=(
                b.get('documento_identidad', 'N/A'),  # Documento
                b['nombre'],                          # Nombre
                b['tipo'],                            # Tipo
                b.get('fecha_nacimiento', '')         # Fecha Nac.
            ), iid=str(b['id']))

    def agregar_beneficiario(self, parent):
        """Abre un diálogo para agregar un beneficiario, con panel de documentos."""
        cc_cotizante = self.cc_var.get().strip()
        if not cc_cotizante:
            messagebox.showerror("Error", "Primero debe ingresar la cédula del cotizante.")
            return

        ventana_principal = parent.winfo_toplevel()
        dialogo = Toplevel(ventana_principal)
        dialogo.title("Agregar Beneficiario")
        dialogo.geometry("950x380")
        self.centrar_ventana(dialogo, 950, 400)
        dialogo.resizable(False, False)
        dialogo.transient(ventana_principal)
        dialogo.grab_set()

        tipo_var = tk.StringVar()
        nombre_var = tk.StringVar()
        doc_var = tk.StringVar()
        observaciones_var = tk.StringVar()
        fecha_nac_var = tk.StringVar()
        telefono_var = tk.StringVar()
        correo_var = tk.StringVar()
        direccion_var = tk.StringVar()

        tipos = ["Hijo", "Padre", "Madre", "Cónyuge", "Hermano"]

        paned = ttk.PanedWindow(dialogo, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(paned, padding=10)
        paned.add(left_frame, weight=1)
        right_frame = ttk.Frame(paned, padding=10)
        paned.add(right_frame, weight=1)

        # ---- Panel Izquierdo: Datos ----
        ttk.Label(left_frame, text="Datos del Beneficiario", style='Title.TLabel').pack(pady=(0, 10))
        form_frame = ttk.Frame(left_frame)
        form_frame.pack(fill=tk.X)
        self.create_combobox_field(form_frame, "Tipo*:", tipo_var, tipos, 0, required=True, width=30)
        self.create_form_field(form_frame, "Nombre Completo*:", nombre_var, 1, width=30, required=True)
        self.create_form_field(form_frame, "Documento de Identidad:", doc_var, 2, width=30)
        self.create_form_field(form_frame, "Observaciones:", observaciones_var, 3, width=30)
        self.create_form_field(form_frame, "Fecha de Nacimiento (DD/MM/AAAA):", fecha_nac_var, 4, width=30)
        self.create_form_field(form_frame, "Teléfono:", telefono_var, 5, width=30)
        self.create_form_field(form_frame, "Correo:", correo_var, 6, width=30)
        self.create_form_field(form_frame, "Dirección:", direccion_var, 7, width=30)

        # ---- Panel Derecho: Documentos ----
        docs_container = ttk.Frame(right_frame)
        docs_container.pack(fill=tk.BOTH, expand=True)
        docs_group = ttk.LabelFrame(docs_container, text="", padding=10)
        docs_group.pack(fill=tk.BOTH, expand=True)

        tree_docs = ttk.Treeview(docs_group, columns=("Archivo",), show="headings", height=4)
        tree_docs.heading("Archivo", text="Archivos subidos")
        tree_docs.column("Archivo", width=200, anchor=tk.W)
        tree_docs.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        scroll_docs = ttk.Scrollbar(docs_group, orient=tk.VERTICAL, command=tree_docs.yview)
        tree_docs.configure(yscrollcommand=scroll_docs.set)
        scroll_docs.pack(side=tk.RIGHT, fill=tk.Y)

        doc_btn_frame = ttk.Frame(docs_group)
        doc_btn_frame.pack(fill=tk.X, pady=5)

        # MODIFICADO: Se pasa tipo_var.get() como argumento
        ttk.Button(doc_btn_frame, text="📤 Subir Documento",
                command=lambda: self.subir_documento_beneficiario(
                    cc_cotizante, nombre_var.get(), tipo_var.get(), docs_group)).pack(side=tk.LEFT, padx=2)

        ttk.Button(doc_btn_frame, text="🔄 Refrescar",
                command=lambda: self.actualizar_lista_documentos_beneficiario(
                    cc_cotizante, nombre_var.get(), tree_docs)).pack(side=tk.LEFT, padx=2)

        ttk.Button(doc_btn_frame, text="📂 Abrir Carpeta",
                command=lambda: self.abrir_carpeta_beneficiario(cc_cotizante, nombre_var.get())).pack(side=tk.LEFT, padx=2)

        # ---- Botones de acción ----
        btn_frame = ttk.Frame(dialogo)
        btn_frame.pack(fill=tk.X, pady=10, padx=10)
        btn_frame.columnconfigure(0, weight=1)

        ttk.Button(btn_frame, text="Cancelar", command=dialogo.destroy).grid(row=0, column=1, padx=5, sticky=tk.E)
        ttk.Button(btn_frame, text="Guardar",
                command=lambda: self.guardar_beneficiario(
                    cc_cotizante, tipo_var.get(), nombre_var.get(), doc_var.get(),
                    observaciones_var.get(), fecha_nac_var.get(), telefono_var.get(),
                    correo_var.get(), direccion_var.get(), dialogo, ventana_principal)).grid(row=0, column=2, padx=5, sticky=tk.E)

        def cargar_docs_iniciales():
            if nombre_var.get():
                self.actualizar_lista_documentos_beneficiario(cc_cotizante, nombre_var.get(), tree_docs)

        nombre_var.trace("w", lambda *args: cargar_docs_iniciales())
        cargar_docs_iniciales()

    def guardar_beneficiario(self, cc, tipo, nombre, doc, observaciones, fecha_nac, telefono, correo, direccion, dialogo, ventana_principal):
        if not tipo or not nombre:
            messagebox.showerror("Error", "Tipo y nombre son obligatorios")
            return

        if fecha_nac:
            try:
                datetime.strptime(fecha_nac, "%d/%m/%Y")
            except ValueError:
                messagebox.showerror("Error", "Formato de fecha incorrecto (DD/MM/AAAA)")
                return

        data = {
            "cotizante_cc": cc, "tipo": tipo, "nombre": nombre,
            "documento_identidad": doc, "registro_civil": observaciones,
            "fecha_nacimiento": fecha_nac, "telefono": telefono,
            "correo": correo, "direccion": direccion,
            "fecha_registro": datetime.now().strftime("%Y-%m-%d")
        }
        self.db.add_beneficiario(data)
        self.beneficiarios_list = self.db.get_beneficiarios(cc)
        self.actualizar_tabla_beneficiarios()

        # Refrescar checkboxes desde el disco (puede haber docs previos del beneficiario)
        self._cargar_estado_documentos(self.cc_var.get().strip())

        dialogo.destroy()
        ventana_principal.lift()
        ventana_principal.focus_force()
        self.mostrar_toast("Beneficiario agregado correctamente")

    def editar_beneficiario(self, parent):
        """Abre un diálogo para editar el beneficiario seleccionado, con panel de documentos."""
        selected = self.tree_benef.selection()
        if not selected:
            messagebox.showerror("Error", "Seleccione un beneficiario para editar")
            return
        id_benef = int(selected[0])
        benef = None
        for b in self.beneficiarios_list:
            if b['id'] == id_benef:
                benef = b
                break
        if not benef:
            messagebox.showerror("Error", "Beneficiario no encontrado")
            return

        ventana_principal = parent.winfo_toplevel()
        dialogo = Toplevel(ventana_principal)
        dialogo.title("Editar Beneficiario")
        dialogo.geometry("950x380")
        self.centrar_ventana(dialogo, 950, 400)
        dialogo.resizable(False, False)
        dialogo.transient(ventana_principal)
        dialogo.grab_set()

        tipo_var = tk.StringVar(value=benef['tipo'])
        nombre_var = tk.StringVar(value=benef['nombre'])
        doc_var = tk.StringVar(value=benef['documento_identidad'] or '')
        observaciones_var = tk.StringVar(value=benef['registro_civil'] or '')
        fecha_nac_var = tk.StringVar(value=benef['fecha_nacimiento'] or '')
        telefono_var = tk.StringVar(value=benef['telefono'] or '')
        correo_var = tk.StringVar(value=benef['correo'] or '')
        direccion_var = tk.StringVar(value=benef['direccion'] or '')

        tipos = ["Hijo", "Padre", "Madre", "Cónyuge", "Hermano"]

        paned = ttk.PanedWindow(dialogo, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(paned, padding=10)
        paned.add(left_frame, weight=1)
        right_frame = ttk.Frame(paned, padding=10)
        paned.add(right_frame, weight=1)

        ttk.Label(left_frame, text="Datos del Beneficiario", style='Title.TLabel').pack(pady=(0, 10))
        form_frame = ttk.Frame(left_frame)
        form_frame.pack(fill=tk.X)
        self.create_combobox_field(form_frame, "Tipo*:", tipo_var, tipos, 0, required=True, width=30)
        self.create_form_field(form_frame, "Nombre Completo*:", nombre_var, 1, width=30, required=True)
        self.create_form_field(form_frame, "Documento de Identidad:", doc_var, 2, width=30)
        self.create_form_field(form_frame, "Observaciones:", observaciones_var, 3, width=30)
        self.create_form_field(form_frame, "Fecha de Nacimiento (DD/MM/AAAA):", fecha_nac_var, 4, width=30)
        self.create_form_field(form_frame, "Teléfono:", telefono_var, 5, width=30)
        self.create_form_field(form_frame, "Correo:", correo_var, 6, width=30)
        self.create_form_field(form_frame, "Dirección:", direccion_var, 7, width=30)

        docs_container = ttk.Frame(right_frame)
        docs_container.pack(fill=tk.BOTH, expand=True)
        docs_group = ttk.LabelFrame(docs_container, text="", padding=10)
        docs_group.pack(fill=tk.BOTH, expand=True)

        tree_docs = ttk.Treeview(docs_group, columns=("Archivo",), show="headings", height=4)
        tree_docs.heading("Archivo", text="Archivos subidos")
        tree_docs.column("Archivo", width=200, anchor=tk.W)
        tree_docs.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        scroll_docs = ttk.Scrollbar(docs_group, orient=tk.VERTICAL, command=tree_docs.yview)
        tree_docs.configure(yscrollcommand=scroll_docs.set)
        scroll_docs.pack(side=tk.RIGHT, fill=tk.Y)

        doc_btn_frame = ttk.Frame(docs_group)
        doc_btn_frame.pack(fill=tk.X, pady=5)

        cc = self.cc_var.get().strip()

        # MODIFICADO: Se pasa tipo_var.get() como argumento
        ttk.Button(doc_btn_frame, text="📤 Subir Documento",
                command=lambda: self.subir_documento_beneficiario(
                    cc, nombre_var.get(), tipo_var.get(), docs_group)).pack(side=tk.LEFT, padx=2)

        ttk.Button(doc_btn_frame, text="🔄 Refrescar",
                command=lambda: self.actualizar_lista_documentos_beneficiario(
                    cc, nombre_var.get(), tree_docs)).pack(side=tk.LEFT, padx=2)

        ttk.Button(doc_btn_frame, text="📂 Abrir Carpeta",
                command=lambda: self.abrir_carpeta_beneficiario(cc, nombre_var.get())).pack(side=tk.LEFT, padx=2)

        self.actualizar_lista_documentos_beneficiario(cc, nombre_var.get(), tree_docs)

        nombre_var.trace("w", lambda *args: self.actualizar_lista_documentos_beneficiario(cc, nombre_var.get(), tree_docs))

        btn_frame = ttk.Frame(dialogo)
        btn_frame.pack(fill=tk.X, pady=10, padx=10)
        btn_frame.columnconfigure(0, weight=1)

        ttk.Button(btn_frame, text="Cancelar", command=dialogo.destroy).grid(row=0, column=1, padx=5, sticky=tk.E)

        def guardar_cambios():
            if not tipo_var.get() or not nombre_var.get():
                messagebox.showerror("Error", "Tipo y nombre son obligatorios")
                return
            if fecha_nac_var.get():
                try:
                    datetime.strptime(fecha_nac_var.get(), "%d/%m/%Y")
                except ValueError:
                    messagebox.showerror("Error", "Formato de fecha incorrecto (DD/MM/AAAA)")
                    return
            data = {
                "tipo": tipo_var.get(), "nombre": nombre_var.get(),
                "documento_identidad": doc_var.get(), "registro_civil": observaciones_var.get(),
                "fecha_nacimiento": fecha_nac_var.get(), "telefono": telefono_var.get(),
                "correo": correo_var.get(), "direccion": direccion_var.get()
            }
            self.db.update_beneficiario(id_benef, data)
            cc_act = self.cc_var.get()
            self.beneficiarios_list = self.db.get_beneficiarios(cc_act)
            self.actualizar_tabla_beneficiarios()

            if hasattr(self, 'callback_actualizar_docs') and self.callback_actualizar_docs:
                self.callback_actualizar_docs()

            dialogo.destroy()
            ventana_principal.lift()
            ventana_principal.focus_force()
            messagebox.showinfo("Éxito", "Beneficiario actualizado correctamente")
            self.refrescar_sistema(silent=True)   
        
        ttk.Button(btn_frame, text="Guardar", command=guardar_cambios).grid(row=0, column=2, padx=5, sticky=tk.E)
        
    def obtener_ruta_beneficiario(self, cc_cotizante, nombre_beneficiario):
        if not nombre_beneficiario:
            return None
        nombre_limpio = "".join(c for c in nombre_beneficiario if c.isalnum() or c in " ._-").strip()
        if not nombre_limpio:
            nombre_limpio = "Sin_nombre"
        return os.path.join(BASE_PATH, "Documentos", cc_cotizante, "Beneficiarios", nombre_limpio)

    def subir_documento_beneficiario(self, cc_cotizante, nombre_beneficiario, tipo_beneficiario, parent_frame):
        if not nombre_beneficiario:
            messagebox.showerror("Error", "Primero ingrese el nombre del beneficiario")
            return
        
        ruta = self.obtener_ruta_beneficiario(cc_cotizante, nombre_beneficiario)
        if not ruta:
            return
        os.makedirs(ruta, exist_ok=True)
        
        archivos = filedialog.askopenfilenames(
            title="Seleccionar documentos para el beneficiario",
            filetypes=[("Todos los archivos", "*.*"), ("PDF", "*.pdf"), ("Imágenes", "*.jpg *.png *.jpeg")]
        )
        if not archivos:
            return

        # --- CORRECCIÓN: La ventana depende del padre para que aparezca sobre él ---
        tipo_dialog = Toplevel(parent_frame.winfo_toplevel())
        tipo_dialog.title("Tipo de Documento")
        tipo_dialog.geometry("400x250") 
        self.centrar_ventana(tipo_dialog, 400, 250)
        tipo_dialog.transient(parent_frame.winfo_toplevel()) # <--- Se ancla a la ventana padre
        tipo_dialog.grab_set()

        ttk.Label(tipo_dialog, text="Seleccione el tipo de documento a subir:", font=('Segoe UI', 10)).pack(pady=15)

        # Determinar las opciones según el tipo de beneficiario
        if tipo_beneficiario == "Hijo":
            opciones = ["Doc. Identidad Hijo", "Registro Civil Hijo"]
        elif tipo_beneficiario == "Cónyuge":
            opciones = ["Carta de Unión (Cónyuge)", "Doc. Identidad Cónyuge"] # <--- NUEVO
        elif tipo_beneficiario in ["Padre", "Madre"]:
            opciones = ["Doc. Identidad Padre/Madre", "Registro Civil Padre/Madre"]
        elif tipo_beneficiario == "Hermano":
            opciones = ["Doc. Identidad Hermano", "Registro Civil Hermano"]
        else:
            # Fallback a todas las opciones
            opciones = [
                "Doc. Identidad (Afiliado)", "Doc. Identidad Hijo", "Registro Civil Hijo",
                "Carta de Unión (Cónyuge)", "Doc. Identidad Cónyuge", # <--- NUEVO
                "Doc. Identidad Padre/Madre", "Registro Civil Padre/Madre", 
                "Doc. Identidad Hermano", "Registro Civil Hermano"
            ]

        tipo_doc_var = tk.StringVar()
        combo = ttk.Combobox(tipo_dialog, textvariable=tipo_doc_var, values=opciones, state="readonly", width=35)
        combo.pack(pady=10)
        if opciones:
            combo.current(0)
        combo.focus_set()

        def guardar_tipo_y_copiar():
            tipo_doc = tipo_doc_var.get()
            if not tipo_doc:
                messagebox.showerror("Error", "Seleccione un tipo de documento.")
                return

            prefijos = {
                "Doc. Identidad (Afiliado)": "ID_Afiliado", 
                "Doc. Identidad Hijo": "ID_Hijo",
                "Registro Civil Hijo": "RC_Hijo", 
                "Carta de Unión (Cónyuge)": "Carta_Union",
                "Doc. Identidad Cónyuge": "ID_Conyuge", # <--- NUEVO
                "Doc. Identidad Padre/Madre": "ID_Padre", 
                "Registro Civil Padre/Madre": "RC_Padre",
                "Doc. Identidad Hermano": "ID_Hermano", 
                "Registro Civil Hermano": "RC_Hermano"
            }
            prefijo = prefijos.get(tipo_doc, "Documento")

            for archivo in archivos:
                try:
                    nombre_original = os.path.basename(archivo)
                    nombre_destino = f"{prefijo}_{nombre_original}"
                    destino = os.path.join(ruta, nombre_destino)
                    shutil.copy2(archivo, destino)
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo copiar {nombre_original}: {str(e)}")
                    return

            # Refrescar TODOS los checkboxes escaneando las carpetas reales
            # (raíz del afiliado + subcarpetas de beneficiarios)
            self._cargar_estado_documentos(cc_cotizante)

            messagebox.showinfo("Éxito", f"Se subieron {len(archivos)} archivo(s) como '{tipo_doc}'.")
            
            # Refrescar la lista de documentos en el diálogo del beneficiario
            for child in parent_frame.winfo_children():
                if isinstance(child, ttk.Treeview):
                    self.actualizar_lista_documentos_beneficiario(cc_cotizante, nombre_beneficiario, child)
                    break
            
            tipo_dialog.destroy()

        btn_frame = ttk.Frame(tipo_dialog)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="Aceptar", command=guardar_tipo_y_copiar).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=tipo_dialog.destroy).pack(side=tk.LEFT, padx=5)
        
    def actualizar_lista_documentos_beneficiario(self, cc_cotizante, nombre_beneficiario, tree_docs):
        if not tree_docs:
            return
        for item in tree_docs.get_children():
            tree_docs.delete(item)
        if not nombre_beneficiario:
            return
        ruta = self.obtener_ruta_beneficiario(cc_cotizante, nombre_beneficiario)
        if not os.path.exists(ruta):
            return
        try:
            archivos = os.listdir(ruta)
            for arch in archivos:
                tree_docs.insert("", tk.END, values=(arch,))
        except Exception as e:
            print(f"Error al leer carpeta: {e}")

    def abrir_carpeta_beneficiario(self, cc_cotizante, nombre_beneficiario):
        """Abre la carpeta del beneficiario en el explorador."""
        import os, sys, subprocess
        nombre_limpio = "".join(c for c in nombre_beneficiario if c.isalnum() or c in " ._-").strip()
        if not nombre_limpio:
            nombre_limpio = "Sin_nombre"
        ruta = os.path.join(BASE_PATH, "Documentos", cc_cotizante, "Beneficiarios", nombre_limpio)
        if not os.path.exists(ruta):
            try:
                os.makedirs(ruta, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear la carpeta: {str(e)}")
                return
        try:
            if sys.platform == "win32":
                os.startfile(ruta)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", ruta])
            else:
                subprocess.Popen(["xdg-open", ruta])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta: {str(e)}")

    def eliminar_beneficiario(self, parent):
        selected = self.tree_benef.selection()
        if not selected:
            messagebox.showerror("Error", "Seleccione un beneficiario para eliminar")
            return
        id_benef = int(selected[0])
        nombre = ""
        for b in self.beneficiarios_list:
            if b['id'] == id_benef:
                nombre = b['nombre']
                break
        if not nombre:
            nombre = "el beneficiario"

        password = simpledialog.askstring("Verificación de Administrador",
                                        "Ingrese la contraseña de administrador para eliminar este beneficiario:",
                                        parent=self.root, show='*')
        if not password:
            return

        usuarios = self.db.get_all_users()
        autorizado = False
        for usuario in usuarios:
            if usuario['role'] == 'Administrativo' and usuario['password'] == password:
                autorizado = True
                break

        if not autorizado:
            messagebox.showerror("Error", "Contraseña incorrecta o usuario sin permisos de administrador")
            return

        if messagebox.askyesno("Confirmar", f"¿Está seguro de eliminar a '{nombre}'?"):
            self.db.delete_beneficiario(id_benef)
            cc = self.cc_var.get()
            self.beneficiarios_list = self.db.get_beneficiarios(cc)
            self.actualizar_tabla_beneficiarios()

            # Refrescar checkboxes desde el disco (puede haber docs previos del beneficiario)
            self._cargar_estado_documentos(self.cc_var.get().strip())

            messagebox.showinfo("Éxito", "Beneficiario eliminado correctamente")
            self.refrescar_sistema(silent=True)

    def create_form_field(self, parent, label, variable, row, width=25, required=False, state='normal'):
        """Crea un campo de formulario con label y entry"""
        label_style = 'Required.TLabel' if required else 'TLabel'
        # Reducimos pady de 5 a 2 para compactar verticalmente
        ttk.Label(parent, text=label, style=label_style).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=2)
        entry = ttk.Entry(parent, textvariable=variable, width=width, state=state)
        entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=2)
        return entry
    
    def create_combobox_field(self, parent, label, variable, values, row, width=25, 
                            required=False, callback=None):
        """Crea un campo de formulario con combobox"""
        label_style = 'Required.TLabel' if required else 'TLabel'
        # Reducimos pady de 5 a 2 para compactar verticalmente
        ttk.Label(parent, text=label, style=label_style).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=2)
        combobox = ttk.Combobox(parent, textvariable=variable, values=values, width=width)
        combobox.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=2)
        
        if callback:
            combobox.bind("<<ComboboxSelected>>", lambda e: callback())
        
        return combobox
    
    def guardar_afiliado(self, index=None, edit_mode=False):
        cc_ingresado = self.cc_var.get().strip()
        cc_limpio = re.sub(r'[^0-9]', '', cc_ingresado)
        self.cc_var.set(cc_limpio)

        cc_original = None
        if edit_mode and index is not None:
            cc_original = self.data[index]['cc']

        if not self.validar_campos_obligatorios(cc_original):
            self.reproducir_sonido("alerta")
            return False

        # Validar que el valor pagado sea numérico
        try:
            valor_pagado = float(self.valor_pagado_var.get()) if self.valor_pagado_var.get() else 0.0
        except ValueError:
            messagebox.showerror("Error", "El valor pagado debe ser un número válido.")
            self.reproducir_sonido("alerta")
            return False

        # ==========================================================
        # NUEVO: Validación del Documento de Identidad Mínimo
        # ==========================================================
        if not self.doc_id_afiliado_var.get():
            if not messagebox.askyesno("Documento Faltante", 
                                    "El 'Documento de Identidad del Afiliado' es un requisito mínimo para la afiliación.\n\n"
                                    "¿Está seguro de que desea guardar el afiliado sin este documento?\n"
                                    "(Puede subirlo más tarde desde el menú de edición)."):
                self.reproducir_sonido("alerta")
                return False
        # ==========================================================

        data = {
            'cc': self.cc_var.get(),
            'nombre': self.nombre_var.get().strip(),
            'celular': self.celular_var.get().strip(),
            'direccion': self.direccion_var.get().strip(),
            'correo': self.correo_var.get().strip(),
            'fecha_ingreso': self.fecha_ingreso_var.get().strip(),
            'eps': self.eps_var.get() if self.eps_var.get() != "-/-" else "",
            'arl': self.arl_var.get() if self.arl_var.get() != "-/-" else "",
            'pension': self.pension_var.get() if self.pension_var.get() != "-/-" else "",
            'caja_compensacion': self.caja_var.get() if self.caja_var.get() != "-/-" else "",
            'valor_pagado': valor_pagado,
            'metodo_pago': self.metodo_pago_var.get().strip(),
            'fecha_pago': self.fecha_pago_var.get().strip()
        }

        if edit_mode and index is not None:
            if self.user_role not in ("Administrativo", "Auxiliar"):
                messagebox.showerror("Error", "No tiene permisos para editar afiliados")
                self.reproducir_sonido("alerta")
                return False
            cc_original = self.data[index]['cc']
            try:
                self.db.update_afiliado(cc_original, data)
                self.data[index] = data
                self._registrar_auditoria("Editó afiliado", "Afiliados", "Éxito",
                                        f"Cédula {data['cc']}")
                self.actualizar_monitoreo_afiliado(cc_original if cc_original == data['cc'] else data['cc'])
                self.update_monitoreo_table()
                mensaje = "Registro actualizado correctamente"
                self.reproducir_sonido("editar")   # <-- SONIDO EDITAR
            except Exception as e:
                messagebox.showerror("Error de BD", f"No se pudo guardar el cambio en la base de datos:\n{str(e)}")
                self.reproducir_sonido("alerta")
                return False
        else:
            try:
                self.db.add_afiliado(data)
                self.data.append(data)
                self._registrar_auditoria("Agregó afiliado", "Afiliados", "Éxito",
                                        f"Cédula {data['cc']} - {data['nombre']}")
                mensaje = "Registro agregado correctamente"
                self.reproducir_sonido("agregar")   # <-- SONIDO AGREGAR
                if not edit_mode:
                    self.mostrar_opciones_notificacion_afiliacion(data)
            except Exception as e:
                messagebox.showerror("Error de BD", f"No se pudo agregar el afiliado:\n{str(e)}")
                self.reproducir_sonido("alerta")
                return False

        self.update_afiliados_table()
        self.limpiar_formulario()
        self.mostrar_toast(mensaje)
        self.refrescar_sistema(silent=True)
        return True
    
    def mostrar_opciones_notificacion_afiliacion(self, afiliado):
        """
        Muestra una ventana con dos paneles: izquierda (datos y checkboxes) y derecha (vista previa).
        """
        tiene_whatsapp = bool(afiliado.get('celular'))
        tiene_email = bool(afiliado.get('correo'))

        if not tiene_whatsapp and not tiene_email:
            messagebox.showinfo("Sin contacto", "El afiliado no tiene celular ni correo registrados. No se puede enviar notificación.")
            return

        ventana = Toplevel(self.root)
        ventana.title("Notificar al afiliado")
        ventana.geometry("750x450")
        ventana.resizable(False, False)
        ventana.transient(self.root)
        ventana.grab_set()

        # Centrar
        ventana.update_idletasks()
        x = (ventana.winfo_screenwidth() // 2) - (750 // 2)
        y = (ventana.winfo_screenheight() // 2) - (450 // 2)
        ventana.geometry(f"+{x}+{y}")

        # Variables para checkboxes
        enviar_whatsapp = tk.BooleanVar(value=tiene_whatsapp)
        enviar_gmail = tk.BooleanVar(value=tiene_email)

        # Frame principal
        main_frame = ttk.Frame(ventana, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Título
        ttk.Label(main_frame, text="Notificar al afiliado", style='Title.TLabel').pack(pady=(0, 10))

        # Panel dividido (izquierda y derecha)
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=5)

        # Panel izquierdo
        left_frame = ttk.Frame(paned, padding=5)
        paned.add(left_frame, weight=1)

        # Panel derecho
        right_frame = ttk.Frame(paned, padding=5)
        paned.add(right_frame, weight=1)

        # --- IZQUIERDA: Datos del afiliado y checkboxes ---
        info_frame = ttk.LabelFrame(left_frame, text="Datos del afiliado", padding=8)
        info_frame.pack(fill=tk.X, pady=5)

        ttk.Label(info_frame, text=f"Nombre: {afiliado['nombre']}").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"CC: {afiliado['cc']}").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"Servicios: {self._obtener_servicios_str(afiliado)}").pack(anchor=tk.W)
        valor_formateado = f"${float(afiliado['valor_pagado']):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        ttk.Label(info_frame, text=f"Valor pagado: {valor_formateado}").pack(anchor=tk.W)

        checkbox_frame = ttk.LabelFrame(left_frame, text="Seleccione los medios de envío", padding=8)
        checkbox_frame.pack(fill=tk.X, pady=5)

        if tiene_whatsapp:
            ttk.Checkbutton(checkbox_frame, text=f"WhatsApp (celular: {afiliado['celular']})",
                            variable=enviar_whatsapp).pack(anchor=tk.W, pady=2)
        else:
            ttk.Label(checkbox_frame, text="WhatsApp: No hay número de celular registrado", foreground="gray").pack(anchor=tk.W)

        if tiene_email:
            ttk.Checkbutton(checkbox_frame, text=f"Gmail (correo: {afiliado['correo']})",
                            variable=enviar_gmail).pack(anchor=tk.W, pady=2)
        else:
            ttk.Label(checkbox_frame, text="Gmail: No hay correo electrónico registrado", foreground="gray").pack(anchor=tk.W)

        # --- DERECHA: Vista previa del mensaje ---
        preview_frame = ttk.LabelFrame(right_frame, text="Vista previa del mensaje", padding=8)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        preview_text = tk.Text(preview_frame, wrap=tk.WORD, font=('Arial', 9), height=12)
        preview_text.insert(tk.END, self._generar_mensaje_afiliacion(afiliado))
        preview_text.config(state=tk.DISABLED)
        preview_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Botones de acción (abajo, centrados) ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="Omitir", command=ventana.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Enviar notificaciones",
                command=lambda: self._enviar_notificaciones_afiliacion(
                    afiliado, enviar_whatsapp.get(), enviar_gmail.get(), ventana)
                ).pack(side=tk.RIGHT, padx=5)

    def _obtener_servicios_str(self, afiliado):
        servicios = []
        if afiliado.get('eps'):
            servicios.append(f"EPS: {afiliado['eps']}")
        if afiliado.get('arl'):
            servicios.append(f"ARL: {afiliado['arl']}")
        if afiliado.get('pension'):
            servicios.append(f"Pensión: {afiliado['pension']}")
        if afiliado.get('caja_compensacion'):
            servicios.append(f"Caja de Compensación: {afiliado['caja_compensacion']}")
        return ", ".join(servicios) if servicios else "Ninguno"
    
    def _generar_mensaje_afiliacion(self, afiliado):
        try:
            fecha_pago = datetime.strptime(afiliado['fecha_pago'], "%Y-%m-%d")
            proxima_fecha = fecha_pago + timedelta(days=30)
            proxima_fecha_str = proxima_fecha.strftime("%d/%m/%Y")
        except:
            proxima_fecha_str = "No especificada"

        servicios = self._obtener_servicios_str(afiliado)
        valor = float(afiliado['valor_pagado'])

        # --- NUEVO: Obtener beneficiarios ---
        beneficiarios = self.db.get_beneficiarios(afiliado['cc'])
        beneficiarios_text = ""
        if beneficiarios:
            lista_benef = []
            for b in beneficiarios:
                nombre = b.get('nombre', '')
                tipo = b.get('tipo', '')
                lista_benef.append(f"{nombre} ({tipo})")
            beneficiarios_text = "\nBeneficiarios: " + ", ".join(lista_benef)
        # --- Fin de la modificación ---

        mensaje = (
            f"Estimado/a {afiliado['nombre']},\n\n"
            f"Le damos la bienvenida a SaluPago. A partir de hoy {afiliado['fecha_ingreso'] or 'fecha actual'}, "
            f"usted ha sido afiliado a los siguientes servicios de seguridad social:\n"
            f"{servicios}\n\n"
            f"Valor pagado: ${valor:,.2f}\n"
            f"Fecha de pago: {afiliado['fecha_pago']}\n"
            f"Próxima fecha de pago: {proxima_fecha_str}"
            f"{beneficiarios_text}\n\n"   # <--- Se inserta aquí
            f"Gracias por confiar en nosotros.\n"
            f"Atentamente,\nSaluPago"
        )
        return mensaje

    def _enviar_notificaciones_afiliacion(self, afiliado, enviar_whatsapp, enviar_gmail, ventana):
        mensaje = self._generar_mensaje_afiliacion(afiliado)
        if enviar_whatsapp:
            self._enviar_whatsapp_texto(afiliado['celular'], mensaje)
        if enviar_gmail:
            self._enviar_gmail_texto(afiliado['correo'], mensaje)
        ventana.destroy()
        messagebox.showinfo("Notificaciones enviadas",
                            "Las notificaciones han sido enviadas exitosamente.")

    def _enviar_whatsapp_texto(self, numero, mensaje):
        """Abre WhatsApp (app si está instalada, o web en su defecto)."""
        import sys, subprocess, urllib.parse, webbrowser
        try:
            numero_limpio = ''.join(filter(str.isdigit, numero))
            mensaje_codificado = urllib.parse.quote(mensaje)
            url_protocolo = f"whatsapp://send?phone={numero_limpio}&text={mensaje_codificado}"
            
            if sys.platform == 'win32':
                # Windows: usar os.startfile para el protocolo
                import os
                os.startfile(url_protocolo)
            elif sys.platform == 'darwin':
                # macOS
                subprocess.call(['open', url_protocolo])
            else:
                # Linux y otros Unix
                subprocess.call(['xdg-open', url_protocolo])
        except Exception:
            # Si falla (app no instalada), abrir la versión web
            try:
                url_web = f"https://wa.me/{numero_limpio}?text={urllib.parse.quote(mensaje)}"
                webbrowser.open(url_web)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir WhatsApp: {str(e)}")

    def _enviar_gmail_texto(self, correo, mensaje):
        """Abre Gmail en el navegador con el mensaje."""
        try:
            asunto = "Bienvenid@s - SaluPago"
            correo_codificado = urllib.parse.quote(correo)
            asunto_codificado = urllib.parse.quote(asunto)
            mensaje_codificado = urllib.parse.quote(mensaje)
            url_gmail = (
                f"https://mail.google.com/mail/?view=cm&fs=1"
                f"&to={correo_codificado}"
                f"&su={asunto_codificado}"
                f"&body={mensaje_codificado}"
            )
            webbrowser.open_new_tab(url_gmail)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir Gmail: {str(e)}")

    def validar_campos_obligatorios(self, cc_original=None):
        errores = []
        cc = self.cc_var.get().strip()
        nombre = self.nombre_var.get().strip()
        celular = self.celular_var.get().strip()
        correo = self.correo_var.get().strip()

        # Validar cédula
        if not cc:
            errores.append("Número de CC es obligatorio")
        elif not validar_cedula(cc):
            errores.append("Número de CC debe tener entre 8 y 10 dígitos numéricos (puntos y guiones permitidos)")
        else:
            cc_limpio = re.sub(r'[^0-9]', '', cc)
            if cc_original is None or cc_limpio != cc_original:
                if self.db.afiliado_exists(cc_limpio):
                    errores.append(f"Ya existe un afiliado con la cédula {cc_limpio}")

        if not nombre:
            errores.append("Nombre Completo es obligatorio")

        if correo and not validar_correo(correo):
            errores.append("Correo electrónico no tiene un formato válido")

        if celular and not validar_celular(celular):
            errores.append("Número de celular debe ser colombiano (10 dígitos, comenzando con 3)")

        # Al menos un servicio seleccionado (ignorando "-/-")
        servicios = [
            self.eps_var.get(),
            self.arl_var.get(),
            self.pension_var.get(),
            self.caja_var.get()
        ]
        servicios_seleccionados = [s for s in servicios if s and s != "-/-"]
        if not servicios_seleccionados:
            errores.append("Debe seleccionar al menos un servicio (EPS, ARL, Pensión o Caja de Compensación)")

        if errores:
            messagebox.showerror("Error de validación", "\n".join(errores))
            return False
        return True

    def calcular_precio(self):
        total = 0
        eps = self.eps_var.get()
        if eps and eps != "-/-":
            total += self.precios['eps']
        
        arl = self.arl_var.get()
        if arl and arl != "-/-" and arl in self.precios['arl']:
            total += self.precios['arl'][arl]
        
        pension = self.pension_var.get()
        if pension and pension != "-/-":
            total += self.precios['pension']
        
        caja = self.caja_var.get()
        if caja and caja != "-/-":
            total += self.precios['caja']
        
        self.valor_pagado_var.set(str(total))
        self.actualizar_estado_pestania_beneficiarios()
    
    def seleccionar_registro(self, event):
        selected_item = self.tree.selection()
        if not selected_item or len(selected_item) > 1:
            return
            
        index = self.tree.index(selected_item[0])
        registro = self.data[index]
        
        self.cc_var.set(registro['cc'])
        self.nombre_var.set(registro['nombre'])
        self.celular_var.set(registro['celular'])
        self.direccion_var.set(registro['direccion'])
        self.correo_var.set(registro['correo'])
        self.fecha_ingreso_var.set(registro['fecha_ingreso'])
        self.eps_var.set(registro['eps'] if registro['eps'] else "-/-")
        self.arl_var.set(registro['arl'] if registro['arl'] else "-/-")
        self.pension_var.set(registro['pension'] if registro['pension'] else "-/-")
        self.caja_var.set(registro['caja_compensacion'] if registro['caja_compensacion'] else "-/-")
        # self.mes_pago_var.set(registro['mes_pago'])   # ELIMINADO
        self.valor_pagado_var.set(registro['valor_pagado'])
        self.metodo_pago_var.set(registro.get('metodo_pago', ''))
        self.fecha_pago_var.set(registro['fecha_pago'])
    
    def editar_afiliado(self):
        # Administrativo y Auxiliar pueden editar datos del afiliado
        if self.user_role not in ("Administrativo", "Auxiliar"):
            self._registrar_auditoria("Intentó editar afiliado", "Afiliados", "Denegado",
                                    "Usuario sin permisos")
            messagebox.showerror("Error", "No tiene permisos para editar afiliados")
            return

        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Por favor seleccione un registro para editar")
            return

        cc = selected_item[0]
        index = None
        for i, a in enumerate(self.data):
            if a['cc'] == cc:
                index = i
                break
        if index is None:
            messagebox.showerror("Error", "El afiliado seleccionado no se encuentra en la lista activa")
            return
        self.show_afiliado_form(edit_mode=True, index=index)
        
    def archivar_afiliado(self):
        """Archiva los afiliados seleccionados (los mueve a la tabla archivados)."""
        if self.user_role not in ("Administrativo", "Auxiliar"):
            messagebox.showerror("Error", "No tiene permisos para archivar afiliados")
            return

        indices = self.mostrar_ventana_seleccion_masiva('eliminar')  # Usar la misma ventana de selección
        if indices is None or not indices:
            return

        # Solicitar motivo de archivo
        motivo = simpledialog.askstring("Motivo de archivo", "Ingrese el motivo del archivo (opcional):",
                                        parent=self.root)
        motivo = motivo if motivo else "Archivo Administrativo"

        # Confirmación
        if not messagebox.askyesno("Confirmar archivado",
                                f"¿Está seguro de archivar a {len(indices)} afiliados?\n"
                                "Serán movidos a la tabla de archivo histórico."):
            return

        usuario_actual = self.username or "MyAdmin"
        for index in sorted(indices, reverse=True):
            if index < len(self.data):
                registro = self.data[index]
                cc = registro['cc']
                if self.db.archivar_afiliado(cc, motivo, usuario_actual):
                    self._registrar_auditoria("Archivó afiliado", "Afiliados", "Éxito",
                                            f"Cédula {cc}, motivo: {motivo}")
                    del self.data[index]
                    # Eliminar de monitoreo en memoria
                    self.contabilidad_data['monitoreo'] = [m for m in self.contabilidad_data['monitoreo'] if m['cc'] != cc]

        self.update_afiliados_table()
        self.update_monitoreo_table()
        self.mostrar_toast(f"{len(indices)} afiliados archivados correctamente.")
        self.refrescar_sistema(silent=True)
        
    def archivar_retirados(self):
        if self.user_role != "Administrativo":
            messagebox.showerror("Error", "No tiene permisos para archivar")
            return

        selected = self.retiros_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Seleccione uno o más retirados para archivar")
            return

        cedulas = [item for item in selected]  # iid es la cédula
        # Verificar que estén en retiros_data (no archivados)
        indices = []
        for cc in cedulas:
            for i, r in enumerate(self.retiros_data):
                if r['cc'] == cc:
                    indices.append(i)
                    break

        if not indices:
            messagebox.showerror("Error", "No hay retirados seleccionados (solo archivados)")
            return

        motivo = simpledialog.askstring("Motivo de archivo", "Ingrese el motivo del archivo (opcional):",
                                        parent=self.root)
        motivo = motivo if motivo else "Archivo Administrativo"
        if not messagebox.askyesno("Confirmar archivado",
                                f"¿Archivar {len(indices)} retirados a la tabla de archivo?"):
            return

        usuario = self.username or "MyAdmin"
        for idx in sorted(indices, reverse=True):
            if idx < len(self.retiros_data):
                reg = self.retiros_data[idx]
                cc = reg['cc']
                self.db.archivar_afiliado(cc, motivo, usuario)
                self._registrar_auditoria("Archivó afiliado", "Afiliados", "Éxito",
                                        f"Cédula {cc}, motivo: {motivo}")
                del self.retiros_data[idx]

        self.update_retiros_table()
        self.cargar_archivados()
        self.mostrar_toast(f"{len(indices)} retirados archivados")
        self.refrescar_sistema(silent=True)

    def eliminar_definitivo_retirado(self):
        if self.user_role != "Administrativo":
            self._registrar_auditoria(
                "Intentó eliminar definitivamente retirado",
                "Retiros",
                "Denegado",
                "Usuario sin permisos"
            )
            messagebox.showerror("Error", "No tiene permisos para eliminar definitivamente")
            return

        selected = self.retiros_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Seleccione un retirado para eliminar")
            return

        cc = selected[0]  # iid es la cédula
        # Verificar que esté en retiros_data (no archivado)
        encontrado = False
        nombre = ""
        for reg in self.retiros_data:
            if reg['cc'] == cc:
                encontrado = True
                nombre = reg['nombre']
                break

        if not encontrado:
            messagebox.showerror(
                "Error",
                "El registro seleccionado no es un retirado (probablemente archivado). "
                "Use la pestaña Archivados para eliminarlo."
            )
            return

        if not self.validar_password():
            return

        if not messagebox.askyesno(
            "Eliminar Definitivamente",
            f"¿Eliminar permanentemente a {nombre} (CC: {cc})?\nEsta acción no se puede deshacer.",
            icon=messagebox.WARNING
        ):
            return

        try:
            self.db.delete_afiliado(cc)
            self.db.delete_monitoreo(cc)
            self.retiros_data = [r for r in self.retiros_data if r['cc'] != cc]
            self.update_retiros_table()

            # === AUDITORÍA ===
            self._registrar_auditoria(
                "Eliminó definitivamente retirado",
                "Retiros",
                "Éxito",
                f"Cédula {cc} - {nombre}"
            )

            messagebox.showinfo("Éxito", "Retirado eliminado definitivamente")
            self.refrescar_sistema(silent=True)
        except Exception as e:
            self._registrar_auditoria(
                "Error al eliminar definitivamente retirado",
                "Retiros",
                "Error",
                f"Cédula {cc}, error: {str(e)}"
            )
            messagebox.showerror("Error", f"No se pudo eliminar: {str(e)}")
            
    def eliminar_afiliado(self):
        if self.user_role != "Administrativo":
            messagebox.showerror("Error", "No tiene permisos para eliminar afiliados")
            self.reproducir_sonido("alerta")
            return

        indices = self.mostrar_ventana_seleccion_masiva('eliminar')
        if indices is None:
            return

        if not indices:
            messagebox.showerror("Error", "No hay afiliados seleccionados para eliminar")
            self.reproducir_sonido("alerta")
            return

        if not self.validar_password():
            self.reproducir_sonido("alerta")
            return

        if not messagebox.askyesno("Confirmar eliminación masiva",
                                f"¿Está seguro de eliminar permanentemente a {len(indices)} afiliados?\n\n"
                                "Esta acción también eliminará sus registros de monitoreo y no se puede deshacer.",
                                icon=messagebox.WARNING):
            return

        for index in sorted(indices, reverse=True):
            if index < len(self.data):
                registro = self.data[index]
                cc_afiliado = registro['cc']
                self.db.delete_afiliado(cc_afiliado)
                self.db.delete_monitoreo(cc_afiliado)
                self._registrar_auditoria("Eliminó afiliado", "Afiliados", "Éxito",
                                        f"Cédula {cc_afiliado}")
                del self.data[index]
                self.contabilidad_data['monitoreo'] = [
                    m for m in self.contabilidad_data['monitoreo']
                    if m['cc'] != cc_afiliado
                ]

        self.update_afiliados_table()
        self.update_monitoreo_table()
        self.mostrar_toast(f"{len(indices)} afiliados eliminados permanentemente")
        self.reproducir_sonido("eliminar")   # <-- SONIDO ELIMINAR
        self.refrescar_sistema(silent=True)
            
    def validar_password(self):
        """
        Valida la contraseña para operaciones sensibles.
        Permite que cualquier usuario con rol 'Administrativo' pueda autorizar operaciones.
        """
        password = simpledialog.askstring("Contraseña", "Ingrese la contraseña de administrador:", show='*')
        if not password:
            return False
        
        # Verificar si la contraseña corresponde a algún usuario Administrativo
        usuarios = self.db.get_all_users()
        for usuario in usuarios:
            if usuario['role'] == 'Administrativo' and usuario['password'] == password:
                return True
        
        messagebox.showerror("Error", "Contraseña incorrecta o usuario no tiene permisos de administrador")
        return False

    def obtener_usuarios_Administrativos(self):
        """Obtiene la lista de usuarios con rol Administrativo"""
        usuarios = self.db.get_all_users()
        return [u for u in usuarios if u['role'] == 'Administrativo']
    
    def retirar_afiliados(self, cedulas=None):
        if self.user_role != "Administrativo":
            messagebox.showerror("Error", "No tiene permisos para retirar afiliados")
            self.reproducir_sonido("alerta")
            return

        if cedulas is None:
            selected = self.tree.selection()
            cedulas = [item for item in selected]

        if not cedulas:
            messagebox.showerror("Error", "No hay afiliados seleccionados para retirar")
            self.reproducir_sonido("alerta")
            return

        if not self.validar_password():
            self.reproducir_sonido("alerta")
            return

        motivo = self.seleccionar_motivo_retiro()
        if motivo is None:
            return

        fecha_retiro = datetime.now().strftime("%Y-%m-%d")
        indices_a_borrar = []
        for cc in cedulas:
            for i, registro in enumerate(self.data):
                if registro['cc'] == cc:
                    self.db.retirar_afiliado(cc, fecha_retiro, motivo)
                    registro['fecha_retiro'] = fecha_retiro
                    registro['motivo_retiro'] = motivo
                    self._registrar_auditoria("Retiró afiliado", "Afiliados", "Éxito",
                                            f"Cédula {cc}, motivo: {motivo}")
                    self.retiros_data.append(registro)
                    indices_a_borrar.append(i)
                    break

        for i in sorted(indices_a_borrar, reverse=True):
            del self.data[i]

        self.update_afiliados_table()
        self.update_retiros_table()
        self.mostrar_toast(f"{len(indices_a_borrar)} afiliados retirados correctamente")
        self.reproducir_sonido("eliminar")   # <-- SONIDO RETIRAR
        self.refrescar_sistema(silent=True)
        
    def mostrar_formulario_reactivacion(self, indices):
            """
            Muestra el formulario de reactivación para cada afiliado seleccionado.
            """
            if not indices:
                return

            for idx in indices:
                if idx >= len(self.retiros_data):
                    continue
                registro = self.retiros_data[idx]
                self._mostrar_formulario_reactivacion_individual(idx, registro)

    def _mostrar_formulario_reactivacion_individual(self, idx, registro):
        """
        Ventana de reactivación con tres secciones:
        - Izquierda: Información Básica
        - Derecha: Seguridad Social
        - Inferior (ambas columnas): Información de Pago (con checkbox)
        """
        datos = registro.copy()

        ventana = Toplevel(self.root)
        ventana.title(f"Reactivar - {datos['nombre']}")
        ventana.geometry("800x550")
        self.centrar_ventana(ventana, 800, 550)
        ventana.resizable(False, False)

        # Variables del formulario
        cc_var = tk.StringVar(value=datos['cc'])
        nombre_var = tk.StringVar(value=datos['nombre'])
        celular_var = tk.StringVar(value=datos.get('celular', ''))
        direccion_var = tk.StringVar(value=datos.get('direccion', ''))
        correo_var = tk.StringVar(value=datos.get('correo', ''))
        fecha_ingreso_var = tk.StringVar(value=datos.get('fecha_ingreso', ''))
        eps_var = tk.StringVar(value=datos.get('eps', '-/-') if datos.get('eps') else "-/-")
        arl_var = tk.StringVar(value=datos.get('arl', '-/-') if datos.get('arl') else "-/-")
        pension_var = tk.StringVar(value=datos.get('pension', '-/-') if datos.get('pension') else "-/-")
        caja_var = tk.StringVar(value=datos.get('caja_compensacion', '-/-') if datos.get('caja_compensacion') else "-/-")
        mes_pago_var = tk.StringVar(value=self.meses[datetime.now().month - 1])  # Mes actual por defecto
        valor_pagado_var = tk.StringVar(value=str(datos.get('valor_pagado', 0)))
        metodo_pago_var = tk.StringVar(value=datos.get('metodo_pago', ''))
        fecha_pago_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))  # Fecha actual por defecto

        # Checkbox para generar pago automático (dentro de la sección de pago)
        # MODIFICACIÓN: el checkbox ahora se llama "Generar pago y reactivar" y está marcado por defecto
        generar_pago_var = tk.BooleanVar(value=True)

        # ========== AÑADIR RECÁLCULO AUTOMÁTICO ==========
        def actualizar_precio(*args):
            total = 0
            eps = eps_var.get()
            if eps and eps != "-/-":
                total += self.precios['eps']
            arl = arl_var.get()
            if arl and arl != "-/-" and arl in self.precios['arl']:
                total += self.precios['arl'][arl]
            pension = pension_var.get()
            if pension and pension != "-/-":
                total += self.precios['pension']
            caja = caja_var.get()
            if caja and caja != "-/-":
                total += self.precios['caja']
            valor_pagado_var.set(str(total))

        eps_var.trace("w", actualizar_precio)
        arl_var.trace("w", actualizar_precio)
        pension_var.trace("w", actualizar_precio)
        caja_var.trace("w", actualizar_precio)

        # Frame principal
        main_frame = ttk.Frame(ventana, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ----- Título -----
        ttk.Label(main_frame, text=f"Reactivar Afiliado - {datos['nombre']}", style='Title.TLabel').pack(pady=(0, 10))

        # ----- Contenedor de dos columnas para las secciones 1 y 2 -----
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.BOTH, expand=True)
        top_frame.columnconfigure(0, weight=1)
        top_frame.columnconfigure(1, weight=1)

        # Sección 1: Información Básica (izquierda)
        basic_frame = ttk.LabelFrame(top_frame, text="Información Básica", padding=10)
        basic_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=5)
        self.create_form_field(basic_frame, "Cédula:", cc_var, 0, width=30, state='readonly')
        self.create_form_field(basic_frame, "Nombre Completo:", nombre_var, 1, width=30)
        self.create_form_field(basic_frame, "Celular:", celular_var, 2, width=30)
        self.create_form_field(basic_frame, "Dirección:", direccion_var, 3, width=30)
        self.create_form_field(basic_frame, "Correo Electrónico:", correo_var, 4, width=30)
        self.create_form_field(basic_frame, "Fecha de Ingreso:", fecha_ingreso_var, 5, width=30)

        # Sección 2: Seguridad Social (derecha)
        social_frame = ttk.LabelFrame(top_frame, text="Seguridad Social", padding=10)
        social_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=5)
        self.create_combobox_field(social_frame, "EPS:", eps_var, self.eps_options, 0, width=30)
        self.create_combobox_field(social_frame, "ARL:", arl_var, self.arl_options, 1, width=30)
        self.create_combobox_field(social_frame, "Fondo de Pensiones:", pension_var, self.pension_options, 2, width=30)
        self.create_combobox_field(social_frame, "Caja de Compensación:", caja_var, self.caja_compensacion_options, 3, width=30)

        # ----- Sección 3: Información de Pago (ocupa ambas columnas) -----
        payment_frame = ttk.LabelFrame(main_frame, text="Información de Pago (si se genera)", padding=10)
        payment_frame.pack(fill=tk.X, pady=10)

        # Frame interno para organizar los campos en dos columnas
        payment_inner = ttk.Frame(payment_frame)
        payment_inner.pack(fill=tk.X)
        payment_inner.columnconfigure(0, weight=1)
        payment_inner.columnconfigure(1, weight=1)

        # Columna izquierda de pago
        left_pay = ttk.Frame(payment_inner)
        left_pay.grid(row=0, column=0, sticky="nsew", padx=5)
        self.create_combobox_field(left_pay, "Mes de Pago:", mes_pago_var, self.meses, 0, width=25)
        self.create_form_field(left_pay, "Valor Pagado:", valor_pagado_var, 1, width=25)

        # Columna derecha de pago
        right_pay = ttk.Frame(payment_inner)
        right_pay.grid(row=0, column=1, sticky="nsew", padx=5)
        self.create_combobox_field(right_pay, "Método de Pago:", metodo_pago_var, self.metodos_pago, 0, width=25)
        self.create_form_field(right_pay, "Fecha de Pago:", fecha_pago_var, 1, width=25)

        # Checkbox dentro de la sección de pago (debajo de las columnas)
        # MODIFICACIÓN: el checkbox ahora se titula "Generar pago y reactivar"
        checkbox_frame = ttk.Frame(payment_frame)
        checkbox_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Checkbutton(checkbox_frame, text="Generar pago y reactivar",
                        variable=generar_pago_var).pack(anchor=tk.W)

        # ----- Botones de acción -----
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        def cancelar():
            ventana.destroy()

        def confirmar_reactivacion():
            # Validar campos
            cc = cc_var.get().strip()
            nombre = nombre_var.get().strip()
            if not cc or not nombre:
                messagebox.showerror("Error", "Cédula y nombre son obligatorios")
                return
            correo = correo_var.get().strip()
            if correo and not validar_correo(correo):
                messagebox.showerror("Error", "Correo electrónico no válido")
                return
            celular = celular_var.get().strip()
            if celular and not validar_celular(celular):
                messagebox.showerror("Error", "Número de celular no válido (debe ser colombiano, 10 dígitos, empezando con 3)")
                return

            # Preparar datos actualizados
            nuevos_datos = {
                'cc': cc,
                'nombre': nombre,
                'celular': celular,
                'direccion': direccion_var.get().strip(),
                'correo': correo,
                'fecha_ingreso': fecha_ingreso_var.get().strip(),
                'eps': eps_var.get() if eps_var.get() != "-/-" else "",
                'arl': arl_var.get() if arl_var.get() != "-/-" else "",
                'pension': pension_var.get() if pension_var.get() != "-/-" else "",
                'caja_compensacion': caja_var.get() if caja_var.get() != "-/-" else "",
                'mes_pago': mes_pago_var.get().strip() if generar_pago_var.get() else "",
                'valor_pagado': float(valor_pagado_var.get()) if valor_pagado_var.get() and generar_pago_var.get() else 0,
                'metodo_pago': metodo_pago_var.get().strip() if generar_pago_var.get() else "",
                'fecha_pago': fecha_pago_var.get().strip() if generar_pago_var.get() else ""
            }

            # ==========================================================
            # MODIFICACIÓN CLAVE: Separar la reactivación del pago
            # ==========================================================
            if generar_pago_var.get():
                self.db.reactivar_afiliado(cc)
                self.db.update_afiliado(cc, nuevos_datos)
                for i, reg in enumerate(self.retiros_data):
                    if reg['cc'] == cc:
                        reg.pop('fecha_retiro', None)
                        reg.pop('motivo_retiro', None)
                        reg.update(nuevos_datos)
                        self.data.append(reg)
                        del self.retiros_data[i]
                        break
                self._registrar_auditoria("Reactivó afiliado", "Afiliados", "Éxito",
                                        f"Cédula {cc}")

                # Actualizar monitoreo
                self.actualizar_monitoreo_afiliado(cc)

                # Generar factura (esto también registra el ingreso)
                self.generar_factura_reactivacion(nuevos_datos)

                # Notificar por WhatsApp si hay celular
                if nuevos_datos['celular']:
                    mensaje = self._generar_mensaje_reactivacion(nuevos_datos)
                    self._enviar_whatsapp_texto(nuevos_datos['celular'], mensaje)
                    messagebox.showinfo("Notificación", f"Se envió un mensaje de reactivación a {nuevos_datos['nombre']} por WhatsApp")
                else:
                    messagebox.showinfo("Sin contacto", "El afiliado no tiene número de celular, no se pudo notificar")

                self.mostrar_toast(f"Afiliado {nombre} reactivado y facturado correctamente")

            else:
                # --- Caso 2: No se genera pago -> solo actualizar datos (permanece retirado) ---
                for i, reg in enumerate(self.retiros_data):
                    if reg['cc'] == cc:
                        # Actualizar datos sin modificar fecha_retiro ni motivo_retiro
                        reg.update(nuevos_datos)
                        self.db.update_afiliado(cc, reg)   # No se elimina fecha_retiro
                        break
                self.mostrar_toast(f"Datos de {nombre} actualizados, pero sigue retirado.")

            # Refrescar tablas
            self.update_afiliados_table()
            self.update_retiros_table()
            self.update_monitoreo_table()
            ventana.destroy()
            self.refrescar_sistema(silent=True)

        ttk.Button(btn_frame, text="Cancelar", command=cancelar).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Reactivar", command=confirmar_reactivacion, style='Accent.TButton').pack(side=tk.RIGHT, padx=5)
                
    def _generar_mensaje_reactivacion(self, datos):
        """
        Genera mensaje de reactivación para WhatsApp.
        """
        return f"""Estimado/a {datos['nombre']},

        Nos complace informarle que su afiliación ha sido REACTIVADA exitosamente en SaluPago.

        Sus datos actualizados son:
        - EPS: {datos['eps'] or 'No especificada'}
        - ARL: {datos['arl'] or 'No especificada'}
        - Pensión: {datos['pension'] or 'No especificada'}
        - Caja de Compensación: {datos['caja_compensacion'] or 'No especificada'}

        Si tiene alguna pregunta, no dude en contactarnos.

        Atentamente,
        SaluPago
        """

    def reactivar_afiliados(self, cedulas=None):
        if self.user_role != "Administrativo":
            messagebox.showerror("Error", "No tiene permisos para reactivar afiliados")
            return

        if cedulas is None:
            # Si no se pasan cédulas, usar selección del Treeview
            selected = self.retiros_tree.selection()
            cedulas = [item for item in selected]  # iid es la cédula

        if not cedulas:
            messagebox.showerror("Error", "No hay retirados seleccionados para reactivar")
            return

        # Obtener los índices reales en self.retiros_data
        indices = []
        for cc in cedulas:
            for i, r in enumerate(self.retiros_data):
                if r['cc'] == cc:
                    indices.append(i)
                    break

        if not indices:
            messagebox.showerror("Error", "No se encontraron los afiliados en la lista de retiros")
            return

        # Llamar al formulario de reactivación con los índices
        self.mostrar_formulario_reactivacion(indices)

    def buscar_afiliados(self, event=None, por_cedula=False, por_nombre=False):
        """Busca afiliados según los criterios especificados"""
        texto_busqueda = self.busqueda_var.get().lower()
        
        if not texto_busqueda:
            self.update_afiliados_table()
            return
            
        resultados = []
        
        for afiliado in self.data:
            if por_cedula and texto_busqueda in afiliado['cc'].lower():
                resultados.append(afiliado)
            elif por_nombre and texto_busqueda in afiliado['nombre'].lower():
                resultados.append(afiliado)
            elif not por_cedula and not por_nombre:
                if (texto_busqueda in afiliado['cc'].lower() or 
                    texto_busqueda in afiliado['nombre'].lower() or
                    texto_busqueda in afiliado['eps'].lower()):
                    resultados.append(afiliado)
        
        self.update_afiliados_table(resultados)
    
    def buscar_retiros(self, event=None, por_cedula=False, por_nombre=False):
        """Busca afiliados retirados según los criterios especificados"""
        texto_busqueda = self.busqueda_var.get().lower()
        
        if not texto_busqueda:
            self.update_retiros_table()
            return
            
        resultados = []
        
        for retirado in self.retiros_data:
            if por_cedula and texto_busqueda in retirado['cc'].lower():
                resultados.append(retirado)
            elif por_nombre and texto_busqueda in retirado['nombre'].lower():
                resultados.append(retirado)
            elif not por_cedula and not por_nombre:
                if (texto_busqueda in retirado['cc'].lower() or 
                    texto_busqueda in retirado['nombre'].lower() or
                    texto_busqueda in retirado['eps'].lower()):
                    resultados.append(retirado)
        
        self.update_retiros_table(resultados)
    
    def _formatear_valor_tabla(self, valor):
        """Devuelve '-/-' si el valor es None, cadena vacía o solo espacios; de lo contrario, devuelve el valor original."""
        if valor is None or (isinstance(valor, str) and valor.strip() == ""):
            return "-/-"
        return valor

    def update_afiliados_table(self, data=None):
        self.clear_treeview(self.tree)
        data_to_show = data if data is not None else self.data

        for registro in data_to_show:
            estado_pago = self._calcular_estado_pago(registro)
            # Usar la cédula como iid
            self.tree.insert("", tk.END, iid=registro['cc'], values=(
                self._formatear_valor_tabla(registro['cc']),
                self._formatear_valor_tabla(registro['nombre']),
                self._formatear_valor_tabla(registro['celular']),
                self._formatear_valor_tabla(registro['eps']),
                self._formatear_valor_tabla(registro['arl']),
                self._formatear_valor_tabla(registro['pension']),
                self._formatear_valor_tabla(registro['caja_compensacion']),
                f"${float(registro['valor_pagado'] or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                self._formatear_valor_tabla(registro['fecha_pago']),
                estado_pago
            ))
    
    def update_retiros_table(self, data=None):
        self.clear_treeview(self.retiros_tree)
        data_to_show = data if data is not None else self.retiros_data

        for registro in data_to_show:
            estado_pago = self._calcular_estado_pago(registro)
            self.retiros_tree.insert("", tk.END, iid=registro['cc'], values=(
                registro.get('cc', ''),
                registro.get('nombre', ''),
                registro.get('celular', ''),
                registro.get('eps', ''),
                registro.get('arl', ''),
                registro.get('pension', ''),
                registro.get('caja_compensacion', ''),
                f"${float(registro.get('valor_pagado', 0)):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                registro.get('fecha_pago', ''),
                registro.get('fecha_retiro', '-/-'),
                registro.get('motivo_retiro', ''),
                estado_pago
            ))

    def _calcular_estado_pago(self, registro):
        hoy = datetime.now()
        mes_actual = hoy.month
        anio_actual = hoy.year

        # Verificar si la fecha de pago corresponde al mes actual
        if registro.get('fecha_pago'):
            try:
                fecha_pago = datetime.strptime(registro['fecha_pago'], "%Y-%m-%d")
                if fecha_pago.month == mes_actual and fecha_pago.year == anio_actual:
                    return "Registrado"
            except:
                pass

        # Si no, verificar solicitudes activas (opcional)
        cc = registro['cc']
        solicitud = self.db.obtener_solicitud_reciente(cc)
        if solicitud:
            estado_sol = solicitud['estado']
            if estado_sol == 'cliente_confirmado':
                return "En Proceso"
            elif estado_sol == 'facturado':
                return "Registrado"
        return "Pendiente"
    
    def update_contabilidad_tables(self):
        """Actualiza todas las tablas de contabilidad y calcula los totales"""
        self.update_ingresos_table()
        self.update_egresos_table()
        self.update_novedades_table()
        self.calcular_totales_contabilidad()
    
    def update_ingresos_table(self, fecha=None):
        """Actualiza la tabla de ingresos. Si fecha es None, muestra todos."""
        self.clear_treeview(self.ingresos_tree)

        datos = self.contabilidad_data['ingresos']
        if fecha:
            fecha_str = fecha.strip()
            if fecha_str:
                datos = [reg for reg in datos if reg.get('fecha', '') == fecha_str]

        for registro in datos:
            self.ingresos_tree.insert("", tk.END, values=(
                registro['fecha'],
                registro['cc'],
                registro['nombre'],
                registro['servicio'],
                f"${registro['valor']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                registro['metodo_pago'],
                registro['comprobante']
            ))
            
    def update_egresos_table(self, fecha=None):
        """Actualiza la tabla de egresos. Si fecha es None, muestra todos."""
        self.clear_treeview(self.egresos_tree)

        datos = self.contabilidad_data['egresos']
        if fecha:
            fecha_str = fecha.strip()
            if fecha_str:
                datos = [reg for reg in datos if reg.get('fecha', '') == fecha_str]

        for registro in datos:
            self.egresos_tree.insert("", tk.END, values=(
                registro['fecha'],
                registro['descripcion'],
                f"${registro['valor']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                registro['metodo_pago']
            ))
    
    def update_novedades_table(self):
        """Actualiza la tabla de novedades"""
        self.clear_treeview(self.novedades_tree)
        
        for registro in self.contabilidad_data['novedades']:
            self.novedades_tree.insert("", tk.END, values=(
                registro['fecha'],
                registro['cc'],
                registro['nombre'],
                registro['novedad']
            ))
    
    def calcular_totales_contabilidad(self):
        """Calcula los totales de ingresos, egresos y saldo"""
        total_ingresos = sum(ingreso['valor'] for ingreso in self.contabilidad_data['ingresos'])
        total_egresos = sum(egreso['valor'] for egreso in self.contabilidad_data['egresos'])
        saldo = total_ingresos - total_egresos
        
        # Actualizar variables de control
        self.total_ingresos_var.set(f"${total_ingresos:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        self.total_egresos_var.set(f"${total_egresos:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        self.saldo_var.set(f"${saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    def clear_treeview(self, treeview):
        """Limpia todos los elementos de un treeview"""
        for item in treeview.get_children():
            treeview.delete(item)
    
    def limpiar_formulario(self):
        """Limpia todos los campos del formulario"""
        self.cc_var.set("")
        self.nombre_var.set("")
        self.celular_var.set("")
        self.direccion_var.set("")
        self.correo_var.set("")
        self.fecha_ingreso_var.set("")
        self.eps_var.set("-/-")
        self.arl_var.set("-/-")
        self.pension_var.set("-/-")
        self.caja_var.set("-/-")
        #self.mes_pago_var.set("")
        self.valor_pagado_var.set("")
        self.metodo_pago_var.set("")
        self.fecha_pago_var.set(datetime.now().strftime("%Y-%m-%d"))
    
    def _formatear_valor_detalle(self, valor):
        """Devuelve '-/-' si el valor es None, cadena vacía o solo espacios; de lo contrario, devuelve el valor original."""
        if valor is None or (isinstance(valor, str) and valor.strip() == ""):
            return "-/-"
        return valor

    def mostrar_detalles_afiliado(self, event):
        selected_item = self.tree.selection()
        if not selected_item:
            return

        cc = selected_item[0]  # El iid es la cédula
        registro = None
        for a in self.data:
            if a['cc'] == cc:
                registro = a
                break
        if not registro:
            messagebox.showerror("Error", "Afiliado no encontrado")
            return

        # Ventana principal
        detalles_window = Toplevel(self.root)
        detalles_window.title(f"Detalles del Afiliado - {registro['nombre']}")
        detalles_window.geometry("1050x550")
        self.centrar_ventana(detalles_window, 1050, 550)
        detalles_window.resizable(False, False)
        
        # PanedWindow para dos paneles
        paned = ttk.PanedWindow(detalles_window, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # ======================== PANEL IZQUIERDO ========================
        left_frame = ttk.Frame(paned, padding=8)
        paned.add(left_frame, weight=1)
        
        # Título
        ttk.Label(left_frame, text=f"Información detallada de {registro['nombre']}", 
                style='Title.TLabel').pack(pady=(0, 8))
        
        # ---- Datos Personales ----
        personal_frame = ttk.LabelFrame(left_frame, text="Datos Personales", padding=6)
        personal_frame.pack(fill=tk.X, pady=4)
        
        campos_personales = [
            ("Cédula:", self._formatear_valor_detalle(registro['cc'])),
            ("Nombre:", self._formatear_valor_detalle(registro['nombre'])),
            ("Celular:", self._formatear_valor_detalle(registro['celular'])),
            ("Dirección:", self._formatear_valor_detalle(registro['direccion'])),
            ("Correo:", self._formatear_valor_detalle(registro['correo']))
        ]
        for i, (label, valor) in enumerate(campos_personales):
            ttk.Label(personal_frame, text=label, font=('Arial', 9, 'bold')).grid(
                row=i, column=0, sticky=tk.W, pady=1, padx=2)
            ttk.Label(personal_frame, text=valor, font=('Arial', 9)).grid(
                row=i, column=1, sticky=tk.W, pady=1, padx=2)
        personal_frame.columnconfigure(1, weight=1)
        
        # ---- Seguridad Social ----
        social_frame = ttk.LabelFrame(left_frame, text="Seguridad Social", padding=6)
        social_frame.pack(fill=tk.X, pady=4)
        
        campos_social = [
            ("Fecha de Ingreso:", self._formatear_valor_detalle(registro['fecha_ingreso'])),
            ("EPS:", self._formatear_valor_detalle(registro['eps'])),
            ("ARL:", self._formatear_valor_detalle(registro['arl'])),
            ("Fondo de Pensiones:", self._formatear_valor_detalle(registro['pension'])),
            ("Caja de Compensación:", self._formatear_valor_detalle(registro['caja_compensacion']))
        ]
        for i, (label, valor) in enumerate(campos_social):
            ttk.Label(social_frame, text=label, font=('Arial', 9, 'bold')).grid(
                row=i, column=0, sticky=tk.W, pady=1, padx=2)
            ttk.Label(social_frame, text=valor, font=('Arial', 9)).grid(
                row=i, column=1, sticky=tk.W, pady=1, padx=2)
        social_frame.columnconfigure(1, weight=1)
        
        # ---- Información de Pago (con estado) ----
        payment_frame = ttk.LabelFrame(left_frame, text="Información de Pago", padding=6)
        payment_frame.pack(fill=tk.X, pady=4)
        
        payment_inner = ttk.Frame(payment_frame)
        payment_inner.pack(fill=tk.X, pady=2)
        
        # Izquierda: Mes y Valor
        left_pay = ttk.Frame(payment_inner)
        left_pay.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(left_pay, text="Mes de Pago:", font=('Arial', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=2, pady=1)
        ttk.Label(left_pay, text=self._formatear_valor_detalle(registro['mes_pago']), font=('Arial', 9)).grid(row=0, column=1, sticky=tk.W, padx=2, pady=1)
        ttk.Label(left_pay, text="Valor Pagado:", font=('Arial', 9, 'bold')).grid(row=1, column=0, sticky=tk.W, padx=2, pady=1)
        valor_str = f"${float(registro['valor_pagado'] or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        ttk.Label(left_pay, text=valor_str, font=('Arial', 9)).grid(row=1, column=1, sticky=tk.W, padx=2, pady=1)
        left_pay.columnconfigure(1, weight=1)
        
        # Derecha: Método, Fecha y Estado
        right_pay = ttk.Frame(payment_inner)
        right_pay.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)
        ttk.Label(right_pay, text="Método de Pago:", font=('Arial', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=2, pady=1)
        ttk.Label(right_pay, text=self._formatear_valor_detalle(registro.get('metodo_pago', '')), font=('Arial', 9)).grid(row=0, column=1, sticky=tk.W, padx=2, pady=1)
        ttk.Label(right_pay, text="Fecha de Pago:", font=('Arial', 9, 'bold')).grid(row=1, column=0, sticky=tk.W, padx=2, pady=1)
        ttk.Label(right_pay, text=self._formatear_valor_detalle(registro['fecha_pago']), font=('Arial', 9)).grid(row=1, column=1, sticky=tk.W, padx=2, pady=1)
        right_pay.columnconfigure(1, weight=1)
        
        # ---- Nueva etiqueta de estado del pago (debajo de la información de pago) ----
        estado_pago_frame = ttk.Frame(payment_frame)
        estado_pago_frame.pack(fill=tk.X, pady=(5, 0))

        # Verificar si el pago está registrado para el mes actual
        hoy = datetime.now()
        mes_actual = hoy.month
        año_actual = hoy.year
        mes_nombre = self.meses[mes_actual - 1]
        mes_pago_registrado = registro.get('mes_pago', '')
        fecha_pago_registrada = registro.get('fecha_pago', '')
        pago_registrado = False
        if mes_pago_registrado and fecha_pago_registrada:
            try:
                fecha_pago_dt = datetime.strptime(fecha_pago_registrada, "%Y-%m-%d")
                if mes_pago_registrado == mes_nombre and fecha_pago_dt.year == año_actual:
                    pago_registrado = True
            except:
                pass

        if pago_registrado:
            estado_texto = "✅ Pago registrado para este mes"
            estado_color = "green"
        else:
            estado_texto = "⏳ Pago pendiente"
            estado_color = "orange"

        ttk.Label(estado_pago_frame, text=estado_texto, font=('Arial', 9, 'bold'),
                foreground=estado_color).pack(anchor=tk.CENTER)
        
        # ---- Botones de acción ----
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(pady=(8, 2))

        ttk.Button(button_frame, text="📄 Certificado", 
        command=lambda: self.generar_certificado_desde_registro(registro, "afiliacion")).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="✏️ Editar", 
                command=lambda: [self.editar_afiliado(), detalles_window.destroy()]).pack(side=tk.LEFT, padx=5)
        if self.user_role == "Administrativo":
            ttk.Button(button_frame, text="➖ Retirar", 
                    command=lambda: [self.retirar_afiliados([registro['cc']]), detalles_window.destroy()]).pack(side=tk.LEFT, padx=5)
        # NUEVO BOTÓN GENERAR PAGO
        ttk.Button(button_frame, text="💳 Generar Pago", 
                command=lambda: [self.mostrar_formulario_pago_para_afiliados([registro]), detalles_window.destroy()]).pack(side=tk.LEFT, padx=5)

        #ttk.Button(button_frame, text="📱 Generar QR",
        #        command=lambda: self.generar_ventana_qr(registro['cc'], registro['nombre'])).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="↩️ Cerrar", command=detalles_window.destroy).pack(side=tk.RIGHT, padx=5)
        
        # ======================== PANEL DERECHO ========================
        right_frame = ttk.Frame(paned, padding=8)
        paned.add(right_frame, weight=1)
        
        ttk.Label(right_frame, text="📂 Documentos del Afiliado", style='Title.TLabel').pack(pady=(0, 8))
        
        tree_docs = ttk.Treeview(right_frame, columns=("Archivo",), show="headings", height=6)
        tree_docs.heading("Archivo", text="Nombre del archivo")
        tree_docs.column("Archivo", width=250, anchor=tk.W)
        tree_docs.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scroll_docs = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=tree_docs.yview)
        tree_docs.configure(yscrollcommand=scroll_docs.set)
        scroll_docs.pack(side=tk.RIGHT, fill=tk.Y)
        
        doc_btn_frame = ttk.Frame(right_frame)
        doc_btn_frame.pack(fill=tk.X, pady=5)
        
        cedula = registro['cc']
        
        ttk.Button(doc_btn_frame, text="📤 Subir Documento",
                command=lambda: self._subir_documento_afiliado(cedula, tree_docs)).pack(side=tk.LEFT, padx=2)
        ttk.Button(doc_btn_frame, text="🔄 Refrescar",
                command=lambda: self._actualizar_lista_documentos_afiliado(cedula, tree_docs)).pack(side=tk.LEFT, padx=2)
        ttk.Button(doc_btn_frame, text="📂 Abrir Carpeta",
                command=lambda: self._abrir_carpeta_afiliado(cedula)).pack(side=tk.LEFT, padx=2)
        
        tree_docs.bind("<Double-1>", lambda e: self._abrir_archivo_seleccionado(cedula, tree_docs))
        tree_docs.drop_target_register(DND_FILES)
        tree_docs.dnd_bind('<<Drop>>', lambda e: self.on_drop_documentos_afiliado(e, cedula, tree_docs))
        
        self._actualizar_lista_documentos_afiliado(cedula, tree_docs)
        
        detalles_window.tree_docs = tree_docs
        detalles_window.cedula = cedula
            
    def _actualizar_lista_documentos_afiliado(self, cedula, treeview):
        """Actualiza el Treeview con los archivos de la carpeta Documentos/{cedula}"""
        for item in treeview.get_children():
            treeview.delete(item)
        
        carpeta = os.path.join(BASE_PATH, "Documentos", cedula)
        if not os.path.exists(carpeta):
            return
        
        try:
            archivos = os.listdir(carpeta)
            for archivo in sorted(archivos):
                treeview.insert("", tk.END, values=(archivo,))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer la carpeta:\n{str(e)}")

    def _subir_documento_afiliado(self, cedula, treeview):
        """Abre diálogo para seleccionar archivos y los copia a Documentos/{cedula}"""
        carpeta = os.path.join(BASE_PATH, "Documentos", cedula)
        os.makedirs(carpeta, exist_ok=True)
        
        archivos = filedialog.askopenfilenames(
            title="Seleccionar documentos para el afiliado",
            filetypes=[("Todos los archivos", "*.*"), ("PDF", "*.pdf"), ("Imágenes", "*.jpg *.png *.jpeg")]
        )
        if not archivos:
            return
        
        import shutil
        for ruta in archivos:
            try:
                nombre = os.path.basename(ruta)
                destino = os.path.join(carpeta, nombre)
                shutil.copy2(ruta, destino)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo copiar {nombre}:\n{str(e)}")
                return
        
        messagebox.showinfo("Éxito", f"Se subieron {len(archivos)} archivo(s).")
        self._actualizar_lista_documentos_afiliado(cedula, treeview)

    def _abrir_carpeta_afiliado(self, cedula):
        """Abre la carpeta Documentos/{cedula} en el explorador de archivos"""
        carpeta = os.path.join(BASE_PATH, "Documentos", cedula)
        if not os.path.exists(carpeta):
            try:
                os.makedirs(carpeta, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear la carpeta:\n{str(e)}")
                return
        try:
            if sys.platform == "win32":
                os.startfile(carpeta)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", carpeta])
            else:
                subprocess.Popen(["xdg-open", carpeta])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta:\n{str(e)}")

    def _abrir_archivo_seleccionado(self, cedula, treeview):
        """Abre el archivo seleccionado en el Treeview con el programa predeterminado"""
        seleccion = treeview.selection()
        if not seleccion:
            return
        nombre = treeview.item(seleccion[0], 'values')[0]
        carpeta = os.path.join(BASE_PATH, "Documentos", cedula)
        ruta_completa = os.path.join(carpeta, nombre)
        if not os.path.exists(ruta_completa):
            messagebox.showerror("Error", "El archivo no existe en el sistema.")
            return
        try:
            if sys.platform == "win32":
                os.startfile(ruta_completa)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", ruta_completa])
            else:
                subprocess.Popen(["xdg-open", ruta_completa])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el archivo:\n{str(e)}")

    def generar_certificado_desde_registro(self, registro, tipo="afiliacion"):
        """
        Genera certificado (afiliación o retiro) para un afiliado dado.
        Guarda automáticamente en Documentos/{cc}/Certificado/
        tipo: 'afiliacion' o 'retiro'
        """
        if not registro:
            return

        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        import os, subprocess, sys

        cc = registro['cc']
        carpeta_docs = os.path.join(BASE_PATH, "Documentos", cc, "Certificado")
        os.makedirs(carpeta_docs, exist_ok=True)

        if tipo == "afiliacion":
            nombre_archivo = f"Certificado_Afiliacion_{cc}.pdf"
        else:
            nombre_archivo = f"Certificado_Retiro_{cc}.pdf"
        file_path = os.path.join(carpeta_docs, nombre_archivo)

        doc = SimpleDocTemplate(file_path, pagesize=letter,
                                leftMargin=1.5*cm, rightMargin=1.5*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        elements = []
        styles = getSampleStyleSheet()

        # Estilos (con tamaños ligeramente mayores para aprovechar el espacio)
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Title'],
            fontSize=22,
            textColor=colors.HexColor('#0d47a1'),
            alignment=TA_CENTER,
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )
        subtitle_style = ParagraphStyle(
            'SubtitleStyle',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#333333'),
            alignment=TA_CENTER,
            spaceAfter=12,
            fontName='Helvetica'
        )
        body_style = ParagraphStyle(
            'BodyStyle',
            parent=styles['Normal'],
            fontSize=12,
            leading=18,
            alignment=TA_LEFT,
            fontName='Helvetica'
        )
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#555555'),
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        signature_style = ParagraphStyle(
            'SignatureStyle',
            parent=styles['Normal'],
            fontSize=12,
            alignment=TA_CENTER,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )

        # Logo
        logo_path = os.path.join(IMG_PATH, "LogoSaluPago.png")
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=3.5*cm, height=3.5*cm)
                logo.hAlign = 'CENTER'
                elements.append(logo)
                elements.append(Spacer(1, 0.3*cm))
            except:
                pass

        # Título
        if tipo == "afiliacion":
            titulo = "CERTIFICADO DE AFILIACIÓN"
            subtitulo = "La empresa CERTIFICA QUE:"
        else:
            titulo = "CERTIFICADO DE RETIRO"
            subtitulo = "La empresa CERTIFICA QUE el siguiente afiliado ha sido retirado:"

        elements.append(Paragraph(titulo, title_style))
        elements.append(Spacer(1, 0.3*cm))

        empresa = self.config.get('empresa.nombre', 'SaluPago')
        elements.append(Paragraph(empresa.upper(), subtitle_style))
        elements.append(Spacer(1, 0.6*cm))  # Espacio extra

        af = registro
        nombre_completo = af['nombre']
        cedula = af['cc']
        eps = af.get('eps', 'No registrada')

        # Cuerpo - Subtítulo "CERTIFICA QUE"
        elements.append(Paragraph(f"<b>{subtitulo}</b>", body_style))
        elements.append(Spacer(1, 0.4*cm))

        if tipo == "afiliacion":
            elementos_cuerpo = [
                f"El(La) Señor(a) <b>{nombre_completo}</b> identificado(a) con CC <b>{cedula}</b> se encuentra afiliado a la EPS <b>{eps}</b> en condición de <b>1° COTIZANTE</b>.",
                "Fecha de Activación de Servicios: " + af.get('fecha_ingreso', 'No registrada'),
                "Estado de la Afiliación: ACTIVO",
                "IPS: ASIGNADA POR LA EPS",
                "Categoría: A"
            ]
        else:
            fecha_retiro = af.get('fecha_retiro', 'No registrada')
            motivo_retiro = af.get('motivo_retiro', 'No especificado')
            elementos_cuerpo = [
                f"El(La) Señor(a) <b>{nombre_completo}</b> identificado(a) con CC <b>{cedula}</b> se encontraba afiliado a la EPS <b>{eps}</b> en condición de <b>1° COTIZANTE</b>.",
                f"Fecha de Retiro: {fecha_retiro}",
                f"Motivo de Retiro: {motivo_retiro}",
                "Estado de la Afiliación: RETIRADO"
            ]

        for parrafo in elementos_cuerpo:
            elements.append(Paragraph(parrafo, body_style))
            elements.append(Spacer(1, 0.2*cm))
        elements.append(Spacer(1, 0.4*cm))  # Espacio extra después del cuerpo

        # ---- Beneficiarios (si existen) ----
        beneficiarios = self.db.get_beneficiarios(cc)
        if beneficiarios:
            elements.append(Paragraph("<b>Beneficiarios registrados:</b>", body_style))
            for b in beneficiarios:
                texto_benef = f"• {b['nombre']} ({b['tipo']})"
                if b.get('documento_identidad'):
                    texto_benef += f" - CC: {b['documento_identidad']}"
                elements.append(Paragraph(texto_benef, body_style))
            elements.append(Spacer(1, 0.5*cm))  # Espacio después de beneficiarios

        # Observaciones
        observaciones = "ESTA CERTIFICACIÓN NO APLICA PARA SERVICIOS MÉDICOS. NO VÁLIDO PARA TRASLADO A OTRA EPS."
        elements.append(Paragraph(f"<b>Observaciones:</b><br/>{observaciones}", body_style))
        elements.append(Spacer(1, 0.5*cm))

        # Fecha y validez
        fecha_actual = datetime.now()
        elements.append(Paragraph(
            f"La presente certificación se expide a solicitud del(de la) interesado(a) en Bogotá para QUIEN INTERESE, a los {fecha_actual.day} días del mes de {fecha_actual.strftime('%B')} del año {fecha_actual.year}.",
            body_style
        ))
        #if tipo == "afiliacion":
        #    fecha_validez = fecha_actual + timedelta(days=30)
        #    elements.append(Spacer(1, 0.3*cm))
        #    elements.append(Paragraph(
        #        f"La certificación tiene validez de un mes con respecto a la fecha de generación (hasta {fecha_validez.strftime('%d/%m/%Y')}).",
        #        footer_style
        #    ))

        elements.append(Spacer(1, 0.5*cm))

        # Firma profesional
        elements.append(Paragraph("Cordialmente,", body_style))
        elements.append(Spacer(1, 0.3*cm))
        elements.append(Paragraph("_________________________", signature_style))
        elements.append(Paragraph("<b>SaluPago Andrés Renteria (CEO)</b>", signature_style))
        elements.append(Paragraph(empresa.upper(), signature_style))
        elements.append(Spacer(1, 0.2*cm))

        elements.append(Paragraph(f"Certificado generado el {fecha_actual.strftime('%d/%m/%Y %H:%M')}", footer_style))
        #elements.append(Paragraph("Este documento es una constancia y no tiene validez como factura.", footer_style))

        doc.build(elements)
        messagebox.showinfo("Certificado generado", f"Certificado guardado en:\n{file_path}")

        # Abrir automáticamente
        try:
            if sys.platform == 'win32':
                os.startfile(file_path)
            elif sys.platform == 'darwin':
                subprocess.call(('open', file_path))
            else:
                subprocess.call(('xdg-open', file_path))
        except:
            pass
            
    def mostrar_opciones_documentos(self, cedula, ventana_padre=None):
        if ventana_padre:
            ventana_padre.withdraw()
        doc_window = Toplevel(self.root)
        doc_window.title(f"Documentos - Cédula {cedula}")
        doc_window.geometry("400x150")
        self.centrar_ventana(doc_window, 400, 150) 
        
        ttk.Label(doc_window, text=f"Gestión de Documentos\nCédula: {cedula}", 
                style='Title.TLabel').pack(pady=10)
        
        btn_frame = ttk.Frame(doc_window)
        btn_frame.pack(pady=10)
        
        # Botones en horizontal usando grid o pack con side=LEFT
        ttk.Button(btn_frame, text="📂Subir Documentos", 
                command=lambda: [self.subir_documentos(cedula), doc_window.destroy()])\
                .pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Button(btn_frame, text="👁️Ver Documentos", 
                command=lambda: [self.ver_documentos(cedula), doc_window.destroy()])\
                .pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Button(btn_frame, text="↩️Cerrar", 
                command=doc_window.destroy)\
                .pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

    def subir_documentos(self, cedula):
        """Permite subir documentos para un afiliado"""
        import os
        from tkinter import filedialog, messagebox
        
        docs_folder = os.path.join(BASE_PATH, "Documentos", cedula)
        os.makedirs(docs_folder, exist_ok=True)
        
        filepaths = filedialog.askopenfilenames(
            title="Seleccionar documentos",
            filetypes=[("Todos los archivos", "*.*"), 
                    ("PDF", "*.pdf"), 
                    ("Imágenes", "*.jpg *.png *.jpeg"),
                    ("Documentos", "*.doc *.docx *.xls *.xlsx")])
        
        if not filepaths:
            return
        
        for filepath in filepaths:
            filename = os.path.basename(filepath)
            dest_path = os.path.join(docs_folder, filename)
            
            try:
                with open(filepath, 'rb') as src, open(dest_path, 'wb') as dst:
                    dst.write(src.read())
                messagebox.showinfo("Éxito", f"Documento {filename} subido correctamente")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo subir {filename}: {str(e)}")
                
    def ver_documentos(self, cedula):
        """Abre el explorador de archivos en la carpeta de documentos del afiliado"""
        docs_folder = os.path.join(BASE_PATH, "Documentos", cedula)
        
        if not os.path.exists(docs_folder):
            messagebox.showinfo("Información", "No hay documentos subidos para este afiliado")
            return
        
        try:
            # EN WINDOWS: Usar os.startfile directamente
            os.startfile(docs_folder)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta:\n{str(e)}")
                                
    def mostrar_detalles_retirado(self, event):
        selected_item = self.retiros_tree.selection()
        if not selected_item:
            return

        cc = selected_item[0]  # El iid es la cédula
        registro = None
        for r in self.retiros_data:
            if r['cc'] == cc:
                registro = r
                break
        if not registro:
            messagebox.showerror("Error", "Retirado no encontrado")
            return

        detalles_window = Toplevel(self.root)
        detalles_window.title(f"Detalles del Retirado - {registro['nombre']}")
        detalles_window.geometry("600x450")
        self.centrar_ventana(detalles_window, 600, 450)
        detalles_window.resizable(False, False)

        main_frame = ttk.Frame(detalles_window, padding=8)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=f"Información detallada de {registro['nombre']}",
                style='Title.TLabel').pack(pady=(0, 5))

        # --- Dos columnas: Datos Personales y Seguridad Social ---
        columns_frame = ttk.Frame(main_frame)
        columns_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.LabelFrame(columns_frame, text="Datos Personales", padding=5)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 3))

        right_frame = ttk.LabelFrame(columns_frame, text="Seguridad Social", padding=5)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(3, 0))

        # Izquierda: datos personales
        campos_izq = [
            ("Cédula:", self._formatear_valor_detalle(registro['cc'])),
            ("Nombre:", self._formatear_valor_detalle(registro['nombre'])),
            ("Celular:", self._formatear_valor_detalle(registro['celular'])),
            ("Dirección:", self._formatear_valor_detalle(registro['direccion'])),
            ("Correo:", self._formatear_valor_detalle(registro['correo']))
        ]
        for i, (label, valor) in enumerate(campos_izq):
            ttk.Label(left_frame, text=label, font=('Arial', 9, 'bold')).grid(
                row=i, column=0, sticky=tk.W, pady=1, padx=2)
            ttk.Label(left_frame, text=valor, font=('Arial', 9)).grid(
                row=i, column=1, sticky=tk.W, pady=1, padx=2)
        left_frame.columnconfigure(1, weight=1)

        # Derecha: seguridad social
        campos_der = [
            ("Fecha de Ingreso:", self._formatear_valor_detalle(registro['fecha_ingreso'])),
            ("EPS:", self._formatear_valor_detalle(registro['eps'])),
            ("ARL:", self._formatear_valor_detalle(registro['arl'])),
            ("Fondo de Pensiones:", self._formatear_valor_detalle(registro['pension'])),
            ("Caja de Compensación:", self._formatear_valor_detalle(registro['caja_compensacion']))
        ]
        for i, (label, valor) in enumerate(campos_der):
            ttk.Label(right_frame, text=label, font=('Arial', 9, 'bold')).grid(
                row=i, column=0, sticky=tk.W, pady=1, padx=2)
            ttk.Label(right_frame, text=valor, font=('Arial', 9)).grid(
                row=i, column=1, sticky=tk.W, pady=1, padx=2)
        right_frame.columnconfigure(1, weight=1)

        # --- Sección de Pago y Retiro (con cálculo del mes a partir de fecha_pago) ---
        payment_frame = ttk.LabelFrame(main_frame, text="Información de Pago y Retiro", padding=5)
        payment_frame.pack(fill=tk.X, pady=(5, 0))

        payment_inner = ttk.Frame(payment_frame)
        payment_inner.pack(fill=tk.X, pady=2)

        # Columna izquierda: Mes de Pago (derivado de fecha_pago) y Valor Pagado
        left_pay = ttk.Frame(payment_inner)
        left_pay.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        ttk.Label(left_pay, text="Mes de Pago:", font=('Arial', 9, 'bold')).grid(
            row=0, column=0, sticky=tk.W, padx=2, pady=1)
        # ---- CÁLCULO DEL MES A PARTIR DE LA FECHA DE PAGO ----
        fecha_pago = registro.get('fecha_pago')
        if fecha_pago:
            try:
                mes_pago = datetime.strptime(fecha_pago, "%Y-%m-%d").strftime("%B")
            except:
                mes_pago = "-/-"
        else:
            mes_pago = "-/-"
        # -------------------------------------------------------
        ttk.Label(left_pay, text=mes_pago, font=('Arial', 9)).grid(
            row=0, column=1, sticky=tk.W, padx=2, pady=1)

        ttk.Label(left_pay, text="Valor Pagado:", font=('Arial', 9, 'bold')).grid(
            row=1, column=0, sticky=tk.W, padx=2, pady=1)
        valor_str = f"${float(registro['valor_pagado'] or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        ttk.Label(left_pay, text=valor_str, font=('Arial', 9)).grid(
            row=1, column=1, sticky=tk.W, padx=2, pady=1)
        left_pay.columnconfigure(1, weight=1)

        # Columna derecha: Método de Pago, Fecha de Pago, Fecha de Retiro y Motivo
        right_pay = ttk.Frame(payment_inner)
        right_pay.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)

        ttk.Label(right_pay, text="Método de Pago:", font=('Arial', 9, 'bold')).grid(
            row=0, column=0, sticky=tk.W, padx=2, pady=1)
        ttk.Label(right_pay, text=self._formatear_valor_detalle(registro.get('metodo_pago', '')), font=('Arial', 9)).grid(
            row=0, column=1, sticky=tk.W, padx=2, pady=1)

        ttk.Label(right_pay, text="Fecha de Pago:", font=('Arial', 9, 'bold')).grid(
            row=1, column=0, sticky=tk.W, padx=2, pady=1)
        ttk.Label(right_pay, text=self._formatear_valor_detalle(registro['fecha_pago']), font=('Arial', 9)).grid(
            row=1, column=1, sticky=tk.W, padx=2, pady=1)

        ttk.Label(right_pay, text="Fecha de Retiro:", font=('Arial', 9, 'bold')).grid(
            row=2, column=0, sticky=tk.W, padx=2, pady=1)
        ttk.Label(right_pay, text=self._formatear_valor_detalle(registro.get('fecha_retiro', '')), font=('Arial', 9)).grid(
            row=2, column=1, sticky=tk.W, padx=2, pady=1)

        ttk.Label(right_pay, text="Motivo de retiro:", font=('Arial', 9, 'bold')).grid(
            row=3, column=0, sticky=tk.W, padx=2, pady=1)
        ttk.Label(right_pay, text=self._formatear_valor_detalle(registro.get('motivo_retiro', '')), font=('Arial', 9)).grid(
            row=3, column=1, sticky=tk.W, padx=2, pady=1)

        right_pay.columnconfigure(1, weight=1)

        # --- Botones de acción ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(8, 2))

        ttk.Button(button_frame, text="↩️ Cerrar", command=detalles_window.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="📄 Certificado",
                command=lambda: self.generar_certificado_desde_registro(registro, "retiro")).pack(side=tk.LEFT, padx=5)

        if self.user_role == "Administrativo":
            ttk.Button(button_frame, text="♻️ Reactivar",
                    command=lambda: [self.reactivar_afiliados([cc]), detalles_window.destroy()]).pack(side=tk.RIGHT, padx=5)
                                        
    def mostrar_detalles_contabilidad(self, tipo):
        """Muestra los detalles completos de un movimiento contable.
        Para Ingresos usa dos paneles (datos + archivos de factura).
        Para Egresos y Novedades usa el diseño clásico con scroll.
        """
        # Determinar qué datos mostrar según el tipo
        if tipo == 'ingresos':
            tree = self.ingresos_tree
            data = self.contabilidad_data['ingresos']
            titulo = "Detalles de Ingreso"
        elif tipo == 'egresos':
            tree = self.egresos_tree
            data = self.contabilidad_data['egresos']
            titulo = "Detalles de Egreso"
        elif tipo == 'novedades':
            tree = self.novedades_tree
            data = self.contabilidad_data['novedades']
            titulo = "Detalles de Novedad"
        else:
            return

        selected_item = tree.selection()
        if not selected_item:
            return

        index = tree.index(selected_item[0])
        registro = data[index]

        # ============================================================
        # CASO INGRESOS: diseño con dos paneles (similar a incapacidades)
        # ============================================================
        if tipo == 'ingresos':
            detalles_window = Toplevel(self.root)
            detalles_window.title(titulo)
            detalles_window.geometry("800x400")
            self.centrar_ventana(detalles_window, 800, 400)
            detalles_window.resizable(False, False)

            paned = ttk.PanedWindow(detalles_window, orient=tk.HORIZONTAL)
            paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # ---- Panel izquierdo: Datos ----
            left_frame = ttk.Frame(paned, padding=10)
            paned.add(left_frame, weight=1)

            ttk.Label(left_frame, text="Detalles de Ingreso", style='Title.TLabel').pack(pady=(0, 10))

            campos = [
                ("Fecha:", registro.get('fecha', '')),
                ("Documento:", registro.get('cc', '')),
                ("Afiliado:", registro.get('nombre', '')),
                ("Servicio:", registro.get('servicio', '')),
                ("Valor:", f"${float(registro.get('valor', 0)):,.2f}"),
                ("Método de Pago:", registro.get('metodo_pago', '')),
                ("Comprobante:", registro.get('comprobante', ''))
            ]
            for campo, valor in campos:
                row = ttk.Frame(left_frame)
                row.pack(fill=tk.X, pady=2)
                ttk.Label(row, text=campo, font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=5)
                ttk.Label(row, text=valor, font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=5)

            # ---- Panel derecho: Archivos ----
            right_frame = ttk.Frame(paned, padding=10)
            paned.add(right_frame, weight=1)

            ttk.Label(right_frame, text="📁 Factura Asociada", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0,5))

            tree_archivos = ttk.Treeview(right_frame, columns=("Archivo",), show="headings", height=6)
            tree_archivos.heading("Archivo", text="Nombre del archivo")
            tree_archivos.column("Archivo", width=250, anchor=tk.W)
            tree_archivos.pack(fill=tk.BOTH, expand=True, pady=5)

            scroll_arch = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=tree_archivos.yview)
            tree_archivos.configure(yscrollcommand=scroll_arch.set)
            scroll_arch.pack(side=tk.RIGHT, fill=tk.Y)

            # ========== CORRECCIÓN: Obtener la cédula del registro ==========
            cc = registro.get('cc', '')

            def actualizar_lista_archivos():
                for item in tree_archivos.get_children():
                    tree_archivos.delete(item)

                comprobante = registro.get('comprobante', '')
                num_factura = comprobante.replace("Factura ", "").strip()
                if not num_factura or not cc:
                    return

                # Ruta corregida: facturas/ (raíz)
                facturas_dir = os.path.join(BASE_PATH, "facturas")
                if not os.path.exists(facturas_dir):
                    return

                for f in os.listdir(facturas_dir):
                    if f.endswith('.pdf') and num_factura in f:
                        tree_archivos.insert("", tk.END, values=(f,))

            def abrir_archivo_interno():
                seleccion = tree_archivos.selection()
                if not seleccion:
                    messagebox.showinfo("Selección", "Seleccione un archivo para ver.")
                    return
                nombre = tree_archivos.item(seleccion[0], 'values')[0]
                ruta = os.path.join(BASE_PATH, "facturas", nombre)   # ruta corregida
                if os.path.exists(ruta):
                    self.mostrar_pdf_interno(ruta, detalles_window)
                else:
                    messagebox.showerror("Error", "El archivo no existe en el sistema.")

            # Botones del panel derecho
            btn_archivos = ttk.Frame(right_frame)
            btn_archivos.pack(fill=tk.X, pady=5)

            ttk.Button(btn_archivos, text="👁️ Ver Archivo", command=abrir_archivo_interno).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_archivos, text="📤 Compartir",
                    command=lambda: self.compartir_factura_ingreso(registro, detalles_window)).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_archivos, text="🔄 Refrescar", command=actualizar_lista_archivos).pack(side=tk.LEFT, padx=5)

            # Doble clic para abrir internamente
            tree_archivos.bind("<Double-1>", lambda e: abrir_archivo_interno())

            # Botón Cerrar (inferior)
            btn_frame = ttk.Frame(detalles_window)
            btn_frame.pack(fill=tk.X, pady=10, padx=10)
            ttk.Button(btn_frame, text="↩️ Cerrar", command=detalles_window.destroy).pack(side=tk.RIGHT, padx=5)

            actualizar_lista_archivos()
            return  # Finaliza el caso ingresos

        # ============================================================
        # CASOS EGRESOS Y NOVEDADES: diseño con scroll (clásico)
        # ============================================================
        # Crear ventana emergente (con scroll)
        detalles_window = Toplevel(self.root)
        detalles_window.title(titulo)

        main_frame = ttk.Frame(detalles_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas = tk.Canvas(main_frame, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ttk.Label(scrollable_frame, text=titulo, style='Title.TLabel').pack(pady=(0, 10))

        detalles_frame = ttk.Frame(scrollable_frame)
        detalles_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        # Construir campos según el tipo
        if tipo == 'egresos':
            campos = [
                ("Fecha:", registro.get('fecha', '')),
                ("Descripción:", registro.get('descripcion', '')),
                ("Valor:", f"${float(registro.get('valor', 0)):,.2f}"),
                ("Método de Pago:", registro.get('metodo_pago', ''))
            ]
        else:  # novedades
            campos = [
                ("Fecha:", registro.get('fecha', '')),
                ("Documento:", registro.get('cc', '')),
                ("Afiliado:", registro.get('nombre', '')),
                ("Novedad:", registro.get('novedad', ''))
            ]

        for campo, valor in campos:
            row_frame = ttk.Frame(detalles_frame)
            row_frame.pack(fill=tk.X, pady=2)
            label = ttk.Label(row_frame, text=campo, style='TLabel', width=15, anchor='e')
            label.pack(side=tk.LEFT, padx=5)
            value_label = ttk.Label(row_frame, text=valor)
            value_label.pack(side=tk.LEFT, padx=5)

        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill=tk.X, pady=10)

        # Frame para botones
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(pady=(10, 0))

        # Botón Cerrar
        btn_cerrar = ttk.Button(button_frame, text="↩️Cerrar", command=detalles_window.destroy)
        btn_cerrar.pack(side=tk.RIGHT, padx=5)

        # Botones adicionales para Administrativos
        if self.user_role == "Administrativo":
            if tipo == 'novedades':
                btn_editar = ttk.Button(button_frame, text="✏️Editar",
                                        command=lambda: [self.editar_novedad(), detalles_window.destroy()])
                btn_editar.pack(side=tk.RIGHT, padx=5)

        # Ajustar tamaño de la ventana (autoajuste)
        detalles_window.update_idletasks()
        ancho = min(detalles_window.winfo_reqwidth() + 50, 800)
        alto = min(detalles_window.winfo_reqheight() + 100, 600)
        detalles_window.geometry(f"{ancho}x{alto}")
        self.centrar_ventana(detalles_window, ancho, alto)
        detalles_window.minsize(400, 200)

    def mostrar_pdf_interno(self, ruta_pdf, ventana_padre):
        """
        Abre un visor de PDF interno usando PyMuPDF.
        Oculta la ventana_padre y la restaura al cerrar el visor.
        """
        # Intentar importar fitz, si no está instalado, ofrecer instalación
        try:
            import fitz
        except ImportError:
            if messagebox.askyesno("Dependencia faltante",
                                "El visor de PDF necesita la librería 'PyMuPDF'.\n"
                                "¿Desea instalarla ahora?"):
                import subprocess, sys
                subprocess.check_call([sys.executable, "-m", "pip", "install", "PyMuPDF"])
                import fitz
            else:
                messagebox.showwarning("Visor no disponible",
                                    "No se puede visualizar el PDF sin PyMuPDF.\n"
                                    "Puede abrir el archivo manualmente desde la carpeta.")
                return

        if not os.path.exists(ruta_pdf):
            messagebox.showerror("Error", f"El archivo no existe:\n{ruta_pdf}")
            return

        ventana_padre.withdraw()

        visor = Toplevel(ventana_padre)
        visor.title(f"Visor de PDF - {os.path.basename(ruta_pdf)}")
        visor.geometry("900x500")
        self.centrar_ventana(visor, 900, 500)   # <--- NUEVO: centrar ventana
        visor.protocol("WM_DELETE_WINDOW", lambda: self.cerrar_visor(visor, ventana_padre))

        # Frame para el canvas y scrollbar
        frame = ttk.Frame(visor)
        frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(frame, bg='white')
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Cargar el PDF y renderizar todas las páginas
        try:
            doc = fitz.open(ruta_pdf)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el PDF:\n{str(e)}")
            ventana_padre.deiconify()
            visor.destroy()
            return

        # Contenedor interno para las imágenes (dentro del canvas)
        inner_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner_frame, anchor='nw')

        # Renderizar cada página y mostrarla como imagen
        images = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # Escala 1.5 para mejor resolución
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            tk_img = ImageTk.PhotoImage(img)
            images.append(tk_img)  # mantener referencia

            label = ttk.Label(inner_frame, image=tk_img)
            label.pack(pady=5)

        # Configurar el scroll del canvas
        def on_configure(event):
            canvas.configure(scrollregion=canvas.bbox('all'))

        inner_frame.bind("<Configure>", on_configure)

        # Botón Cerrar en la parte inferior
        btn_frame = ttk.Frame(visor)
        btn_frame.pack(fill=tk.X, pady=10)
        ttk.Button(btn_frame, text="Cerrar", command=lambda: self.cerrar_visor(visor, ventana_padre)).pack()

        # Guardar referencias para evitar garbage collection
        visor.images = images
        visor.doc = doc

    def cerrar_visor(self, visor, ventana_padre):
        """Cierra el visor y restaura la ventana padre."""
        visor.destroy()
        ventana_padre.deiconify()
        ventana_padre.lift()
        ventana_padre.focus_force()

    def compartir_factura_ingreso(self, registro, ventana_padre=None):
        try:
            afiliado = None
            for a in self.data:
                if a['cc'] == registro['cc']:
                    afiliado = a
                    break
            if not afiliado:
                messagebox.showerror("Error", "No se encontró al afiliado en los registros activos")
                return

            num_factura = registro['comprobante'].replace("Factura ", "").strip()
            factura_path = os.path.join(BASE_PATH, "facturas", f"Factura_{num_factura}.pdf")
            if not os.path.exists(factura_path):
                messagebox.showerror("Error", f"No se encontró el archivo de factura:\n{factura_path}")
                return

            # Ocultar la ventana padre (detalles de ingreso)
            if ventana_padre:
                ventana_padre.withdraw()

            share_window = Toplevel(self.root)
            share_window.title("Compartir Factura")
            share_window.geometry("400x250")
            self.centrar_ventana(share_window, 400, 250)
            share_window.resizable(False, False)

            # Función para cerrar la ventana de compartir y restaurar la padre
            def on_share_close():
                if ventana_padre:
                    ventana_padre.deiconify()
                share_window.destroy()

            share_window.protocol("WM_DELETE_WINDOW", on_share_close)

            ttk.Label(share_window, text="Opciones para compartir la factura:",
                    style='Title.TLabel').pack(pady=10)

            button_frame = ttk.Frame(share_window)
            button_frame.pack(pady=10, fill=tk.X, padx=20)

            # Wrapper que ejecuta la acción, restaura la padre y cierra la ventana de compartir
            def accion_con_restauracion(func):
                def wrapper():
                    try:
                        func()
                    except Exception as e:
                        messagebox.showerror("Error", str(e))
                    finally:
                        if ventana_padre:
                            ventana_padre.deiconify()
                        share_window.destroy()
                return wrapper

            if afiliado.get('celular'):
                ttk.Button(
                    button_frame,
                    text="WhatsApp al Cliente",
                    command=accion_con_restauracion(
                        lambda: self.compartir_por_whatsapp_cliente(factura_path, afiliado, share_window)
                    )
                ).pack(pady=5, fill=tk.X)

            if afiliado.get('correo'):
                ttk.Button(
                    button_frame,
                    text="Gmail al Cliente",
                    command=accion_con_restauracion(
                        lambda: self.compartir_por_gmail_cliente(factura_path, afiliado, share_window)
                    )
                ).pack(pady=5, fill=tk.X)

            ttk.Button(
                button_frame,
                text="📂 Abrir Ubicación del Archivo",
                command=accion_con_restauracion(
                    lambda: self.abrir_ubicacion_archivo(factura_path, share_window)
                )
            ).pack(pady=5, fill=tk.X)

            ttk.Button(
                share_window,
                text="Cancelar",
                command=on_share_close
            ).pack(pady=10)

        except Exception as e:
            if ventana_padre:
                ventana_padre.deiconify()
            messagebox.showerror("Error", f"Ocurrió un error al compartir: {str(e)}")

    def preparar_factura(self):
        """Muestra formulario de búsqueda para facturar"""
        # Crear ventana de búsqueda
        factura_window = Toplevel(self.root)
        factura_window.title("Buscar Afiliado para Facturar")
        factura_window.geometry("800x450")
        self.centrar_ventana(factura_window, 800, 450)   
        factura_window.resizable(False, False)  
        
        # Variables
        busqueda_var = tk.StringVar()
        resultado_var = tk.StringVar(value="Resultados: 0 afiliados encontrados")
        afiliados_seleccionados = []
        
        # Frame principal con configuración para tamaño fijo
        main_frame = ttk.Frame(factura_window)
        main_frame.pack(fill=tk.BOTH, expand=False, padx=15, pady=15)
        
        # Título
        ttk.Label(main_frame, text="Buscar Afiliado para Facturar", 
                style='Title.TLabel').pack(pady=(0, 15))
        
        # Controles de búsqueda - Frame superior
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(search_frame, text="Buscar:").pack(side=tk.LEFT, padx=5)
        busqueda_entry = ttk.Entry(search_frame, textvariable=busqueda_var, width=50)  # Barra más ancha
        busqueda_entry.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)  # Ahora se expande
        
        ttk.Button(search_frame, text="🧠Buscar", 
                command=lambda: self.buscar_para_factura(busqueda_var.get(), tree, resultado_var),
                width=10).pack(side=tk.LEFT, padx=5)
        
        # Resultados de búsqueda
        ttk.Label(main_frame, textvariable=resultado_var).pack()
        
        # Tabla de resultados - Frame sin scroll
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Tabla sin scrollbar
        columns = ("CC", "Nombre", "EPS", "Último Pago")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended", height=8)  # Altura aumentada
        
        # Configurar columnas con anchos proporcionales
        tree.column("CC", width=120, anchor=tk.CENTER)
        tree.column("Nombre", width=220, anchor=tk.W)
        tree.column("EPS", width=180, anchor=tk.W)
        tree.column("Último Pago", width=110, anchor=tk.CENTER)
        
        for col in columns:
            tree.heading(col, text=col)
        
        tree.pack(fill=tk.BOTH, expand=True)
        
        # Frame inferior para botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="➕Añadir Pago", 
                command=lambda: self.anadir_pago(tree, factura_window, afiliados_seleccionados),
                width=15).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="➗Facturar", 
                command=lambda: self.generar_factura_final(afiliados_seleccionados, factura_window),
                width=15).pack(side=tk.RIGHT, padx=5)
        
        # Actualizar lista de seleccionados cuando cambia la selección
        tree.bind("<<TreeviewSelect>>", lambda e: self.actualizar_seleccionados(tree, afiliados_seleccionados, resultado_var))

    def buscar_para_factura(self, texto_busqueda, tree, resultado_var):
        """Busca afiliados para facturar"""
        self.clear_treeview(tree)
        resultados = []
        
        texto_busqueda = texto_busqueda.lower()
        
        if not texto_busqueda:
            resultados = self.data.copy()
        else:
            for afiliado in self.data:
                if (texto_busqueda in afiliado['cc'].lower() or 
                    texto_busqueda in afiliado['nombre'].lower()):
                    resultados.append(afiliado)
        
        for afiliado in resultados:
            tree.insert("", tk.END, values=(
                afiliado['cc'],
                afiliado['nombre'],
                afiliado['eps'],
                afiliado.get('fecha_pago', '-/-')
            ))
        
        resultado_var.set(f"Resultados: {len(resultados)} afiliados encontrados")

    def actualizar_seleccionados(self, tree, afiliados_seleccionados, resultado_var):
        """Actualiza la lista de afiliados seleccionados"""
        selected_items = tree.selection()
        afiliados_seleccionados.clear()
        
        for item in selected_items:
            cc = tree.item(item, 'values')[0]
            for afiliado in self.data:
                if afiliado['cc'] == cc:
                    afiliados_seleccionados.append(afiliado)
                    break
        
        resultado_var.set(f"Seleccionados: {len(afiliados_seleccionados)} afiliados")

    def mostrar_formulario_pago_para_afiliados(self, afiliados, solicitud=None):
        if not afiliados:
            messagebox.showerror("Error", "No se ha seleccionado ningún afiliado.")
            return

        if len(afiliados) == 1 and solicitud is None:
            solicitud = self.db.obtener_solicitud_activa(afiliados[0]['cc'])

        hoy = datetime.now()
        mes_actual = hoy.month
        año_actual = hoy.year
        mes_nombre = self.meses[mes_actual - 1]
        afiliado = afiliados[0]

        mes_pago_registrado = afiliado.get('mes_pago', '')
        fecha_pago_registrada = afiliado.get('fecha_pago', '')
        pago_registrado = False
        fecha_inicial = hoy.strftime("%Y-%m-%d")
        if mes_pago_registrado and fecha_pago_registrada:
            try:
                fecha_pago_dt = datetime.strptime(fecha_pago_registrada, "%Y-%m-%d")
                if mes_pago_registrado == mes_nombre and fecha_pago_dt.year == año_actual:
                    pago_registrado = True
                    fecha_inicial = fecha_pago_registrada
            except:
                pass

        valor_por_defecto = self.calcular_valor_afiliado(afiliado)

        pago_window = Toplevel(self.root)
        pago_window.title("Añadir Pago")
        pago_window.geometry("650x400")
        self.centrar_ventana(pago_window, 650, 400)
        pago_window.resizable(False, False)
        self.deshabilitar_botones_ventana(pago_window)

        mes_pago_var = tk.StringVar(value=mes_nombre)
        valor_pagado_var = tk.StringVar(value=str(valor_por_defecto))
        metodo_pago_var = tk.StringVar(value=self.metodos_pago[0] if self.metodos_pago else "")
        fecha_pago_var = tk.StringVar(value=fecha_inicial)

        main_frame = ttk.Frame(pago_window, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=f"Añadir Pago - {mes_nombre.upper()}", style='Title.TLabel', font=('Arial', 12, 'bold')).grid(row=0, column=0, columnspan=2, pady=(0, 15))

        left_frame = ttk.LabelFrame(main_frame, text="👤 Datos del Afiliado", padding=12)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8))

        campos_izquierda = [
            ("CC:", afiliado['cc']),
            ("EPS:", afiliado.get('eps', 'No aplica')),
            ("ARL:", afiliado.get('arl', 'No aplica')),
            ("Pensión:", afiliado.get('pension', 'No aplica')),
            ("Caja Comp.:", afiliado.get('caja_compensacion', 'No aplica'))
        ]
        for i, (label, valor) in enumerate(campos_izquierda):
            ttk.Label(left_frame, text=label, font=('Arial', 9, 'bold')).grid(row=i, column=0, sticky=tk.W, padx=2, pady=3)
            ttk.Label(left_frame, text=valor, font=('Arial', 9)).grid(row=i, column=1, sticky=tk.W, padx=2, pady=3)
        if len(afiliados) > 1:
            ttk.Label(left_frame, text=f"(+ {len(afiliados)-1} afiliados más)", foreground="#666", font=('Arial', 8, 'italic')).grid(row=len(campos_izquierda), column=0, columnspan=2, sticky=tk.W, pady=8)
        left_frame.columnconfigure(1, weight=1)

        right_frame = ttk.LabelFrame(main_frame, text="💳 Información de Pago", padding=12)
        right_frame.grid(row=1, column=1, sticky="nsew", padx=(8, 0))

        ttk.Label(right_frame, text="Mes:", font=('Arial', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=2, pady=4)
        cb_mes = ttk.Combobox(right_frame, textvariable=mes_pago_var, values=self.meses, state="readonly", width=18)
        cb_mes.grid(row=0, column=1, sticky=tk.EW, padx=2, pady=4)

        ttk.Label(right_frame, text="Valor*:", font=('Arial', 9, 'bold')).grid(row=1, column=0, sticky=tk.W, padx=2, pady=4)
        entry_valor = ttk.Entry(right_frame, textvariable=valor_pagado_var, width=18)
        entry_valor.grid(row=1, column=1, sticky=tk.EW, padx=2, pady=4)

        ttk.Label(right_frame, text="Método*:", font=('Arial', 9, 'bold')).grid(row=2, column=0, sticky=tk.W, padx=2, pady=4)
        cb_metodo = ttk.Combobox(right_frame, textvariable=metodo_pago_var, values=self.metodos_pago, state="readonly", width=18)
        cb_metodo.grid(row=2, column=1, sticky=tk.EW, padx=2, pady=4)

        ttk.Label(right_frame, text="Fecha (automática):", font=('Arial', 9, 'bold')).grid(row=3, column=0, sticky=tk.W, padx=2, pady=4)
        # Mostrar la fecha actual sin posibilidad de edición
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        ttk.Label(right_frame, text=fecha_actual, font=('Arial', 9), relief='sunken', padding=(5,2), anchor='w', width=18).grid(row=3, column=1, sticky=tk.EW, padx=2, pady=4)

        estado_frame = ttk.Frame(right_frame)
        estado_frame.grid(row=4, column=0, columnspan=2, pady=(10,0), sticky="ew")
        if pago_registrado:
            estado_texto = "✅ Pago registrado para este mes"
            estado_color = "green"
        else:
            estado_texto = "⏳ Pago pendiente"
            estado_color = "orange"
        ttk.Label(estado_frame, text=estado_texto, font=('Arial', 9, 'bold'), foreground=estado_color).pack()

        barra_frame = ttk.Frame(right_frame)
        barra_frame.grid(row=5, column=0, columnspan=2, pady=(10,0), sticky="ew")
        if solicitud:
            self._mostrar_barra_progreso_solicitud(barra_frame, solicitud)
        else:
            ttk.Label(barra_frame, text="No hay solicitud activa. Use 'Generar' para crear una.", font=('Arial', 9), foreground='gray').pack()

        # ========== BOTONES DE ACCIÓN ==========
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(20,5))

        style = ttk.Style()
        style.configure("Big.TButton", padding=8, font=('Arial', 9))

        ttk.Button(button_frame, text="✖️ Cancelar", style="Big.TButton", command=pago_window.destroy).pack(side=tk.LEFT, padx=8)

        btn_generar = ttk.Button(button_frame, text="💬 Generar", style="Big.TButton",
                                command=lambda: self.generar_solicitud_y_whatsapp(
                                    afiliados, mes_pago_var.get(), valor_pagado_var.get(),
                                    metodo_pago_var.get(), pago_window))
        btn_generar.pack(side=tk.LEFT, padx=8)

        btn_facturar = ttk.Button(button_frame, text="📄 Facturar", style="Big.TButton",
                                command=lambda: self.mostrar_dialogo_facturar(
                                    afiliados, solicitud, mes_pago_var.get(),
                                    valor_pagado_var.get(), metodo_pago_var.get(),
                                    fecha_pago_var.get(), pago_window))
        btn_facturar.pack(side=tk.LEFT, padx=8)

        # ==== NUEVO: Botón para cambiar método de pago (visible si hay solicitud activa) ====
        if solicitud and solicitud['estado'] in ('enviada', 'cliente_confirmado'):
            btn_cambiar = ttk.Button(
                button_frame,
                text="💵 Cambiar Pago",
                style="Big.TButton",
                command=lambda: self.mostrar_opciones_cambio_pago(
                    solicitud, afiliados, pago_window
                )
            )
            btn_cambiar.pack(side=tk.LEFT, padx=8)

        # Habilitar/deshabilitar Facturar según estado de la solicitud
        if solicitud and solicitud['estado'] == 'cliente_confirmado':
            btn_facturar.config(state="normal")
        else:
            btn_facturar.config(state="disabled")

        # Guardar referencias en la ventana para actualizar después
        pago_window.solicitud = solicitud
        pago_window.barra_frame = barra_frame
        pago_window.btn_facturar = btn_facturar
        pago_window.afiliados = afiliados

        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        entry_valor.focus_set()

    def mostrar_opciones_cambio_pago(self, solicitud, afiliados, ventana_padre):
        """
        Muestra una ventana para que el empleado elija el nuevo método de pago.
        """
        if not solicitud:
            return

        metodo_actual = solicitud.get('metodo_pago', '')
        opciones = ["Efectivo", "Transferencia"]
        # Filtrar para que no aparezca la opción ya seleccionada (opcional)
        # opciones_disponibles = [m for m in opciones if m != metodo_actual]

        ventana = Toplevel(self.root)
        ventana.title("Cambiar método de pago")
        ventana.geometry("400x200")
        self.centrar_ventana(ventana, 400, 230)
        ventana.resizable(False, False)
        ventana.transient(ventana_padre)
        ventana.grab_set()

        ttk.Label(ventana, text="Seleccione el nuevo método de pago", 
                font=('Arial', 12, 'bold')).pack(pady=15)

        frame = ttk.Frame(ventana)
        frame.pack(pady=10)

        ttk.Button(frame, text="💵 Efectivo", width=20,
                command=lambda: self.cambiar_metodo_pago(
                    solicitud, afiliados, ventana_padre, "Efectivo", ventana
                )).pack(pady=5)

        ttk.Button(frame, text="💳 Transferencia", width=20,
                command=lambda: self.cambiar_metodo_pago(
                    solicitud, afiliados, ventana_padre, "Transferencia", ventana
                )).pack(pady=5)

        ttk.Button(ventana, text="Cancelar", command=ventana.destroy).pack(pady=10)

    def cambiar_metodo_pago(self, solicitud, afiliados, ventana_padre, nuevo_metodo, ventana_seleccion):
        """
        Cambia el método de pago de una solicitud y actualiza su estado.
        """
        if not solicitud:
            return

        # Confirmar con el empleado
        if not messagebox.askyesno(
            "Confirmar cambio",
            f"¿Está seguro de cambiar el método de pago a **{nuevo_metodo}**?\n"
            f"Afiliado: {afiliados[0]['nombre']}\n"
            f"Método actual: {solicitud.get('metodo_pago', 'No especificado')}"
        ):
            return

        # Determinar nuevo estado según el método
        if nuevo_metodo == "Efectivo":
            nuevo_estado = "cliente_confirmado"
        else:  # Transferencia
            nuevo_estado = "enviada"

        # Actualizar en la base de datos
        self.db.actualizar_solicitud(
            solicitud['id'],
            estado=nuevo_estado,
            metodo_pago=nuevo_metodo
        )

        # Refrescar la solicitud en memoria
        nueva_solicitud = self.db.obtener_solicitud_activa(afiliados[0]['cc'])
        ventana_padre.solicitud = nueva_solicitud

        # Actualizar la interfaz de la ventana de pago
        if hasattr(ventana_padre, 'barra_frame'):
            self._mostrar_barra_progreso_solicitud(ventana_padre.barra_frame, nueva_solicitud)

        if hasattr(ventana_padre, 'btn_facturar'):
            if nueva_solicitud and nueva_solicitud['estado'] == 'cliente_confirmado':
                ventana_padre.btn_facturar.config(state="normal")
            else:
                ventana_padre.btn_facturar.config(state="disabled")

        # Cerrar la ventana de selección
        ventana_seleccion.destroy()

        # Registrar en novedades
        novedad_data = {
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "cc": afiliados[0]['cc'],
            "nombre": afiliados[0]['nombre'],
            "novedad": f"Cambio manual de método de pago: {solicitud.get('metodo_pago', '')} -> {nuevo_metodo}. Estado: {nuevo_estado}"
        }
        new_id = self.db.add_novedad(novedad_data)
        novedad_data['id'] = new_id
        self.contabilidad_data['novedades'].append(novedad_data)
        self.update_novedades_table()

        messagebox.showinfo(
            "Cambio realizado",
            f"El método de pago ha sido cambiado a **{nuevo_metodo}**.\n"
            f"Estado actual: {nuevo_estado}"
        )

        # Refrescar la tabla de novedades (ya se hizo)
        # Opcional: refrescar otras tablas si es necesario
        self.refrescar_sistema(silent=True)

    def _mostrar_barra_progreso_solicitud(self, parent, solicitud):
        """Muestra una barra de progreso y etiquetas en el frame padre."""
        for widget in parent.winfo_children():
            widget.destroy()

        estado = solicitud['estado']
        pasos = ["Solicitud enviada", "Cliente confirma pago", "Factura generada"]
        if estado == 'enviada':
            progreso = 0
        elif estado == 'cliente_confirmado':
            progreso = 1
        elif estado == 'facturado':
            progreso = 2
        else:
            progreso = 1

        progress = ttk.Progressbar(parent, orient='horizontal', length=250, mode='determinate', maximum=2, value=progreso)
        progress.pack(fill=tk.X, pady=5)

        labels_frame = ttk.Frame(parent)
        labels_frame.pack(fill=tk.X)
        for i, paso in enumerate(pasos):
            lbl = ttk.Label(labels_frame, text=paso, font=('Arial', 8))
            lbl.config(foreground='green' if i <= progreso else 'gray')
            lbl.pack(side=tk.LEFT, expand=True, padx=2)

        estado_texto = {
            'enviada': '⏳ Esperando confirmación del cliente',
            'cliente_confirmado': '✅ Cliente confirmó el pago. Listo para facturar.',
            'facturado': '📄 Factura generada',
            'rechazado': '❌ Rechazado por el empleado',
            'pendiente': '🔄 Pendiente de revisión'
        }.get(estado, estado)
        ttk.Label(parent, text=estado_texto, font=('Arial', 9, 'italic'), foreground='#555').pack(pady=2)

    def generar_solicitud_y_whatsapp(self, afiliados, mes, valor, metodo, ventana):
        if not afiliados:
            return
        afiliado = afiliados[0]
        try:
            monto = float(valor)
        except ValueError:
            messagebox.showerror("Error", "Valor inválido")
            return

        mensaje = self._generar_mensaje_pago(afiliados, monto)
        if afiliado.get('celular'):
            self._enviar_whatsapp_texto(afiliado['celular'], mensaje)
            messagebox.showinfo("WhatsApp", "Mensaje enviado al cliente.")
        else:
            messagebox.showwarning("Sin celular", "El afiliado no tiene número de celular. No se pudo enviar WhatsApp.")

        solicitud_id = self.db.crear_solicitud(
            cc=afiliado['cc'],
            monto=monto,
            mes=mes,
            metodo_pago=metodo,
            mensaje=mensaje
        )
        solicitud = self.db.obtener_solicitud_activa(afiliado['cc'])

        if hasattr(ventana, 'barra_frame') and solicitud:
            self._mostrar_barra_progreso_solicitud(ventana.barra_frame, solicitud)
        if hasattr(ventana, 'btn_facturar'):
            ventana.btn_facturar.config(state="disabled")

        ventana.solicitud = solicitud
        self.mostrar_toast("Solicitud de pago generada. El cliente podrá confirmar.", duracion=4000)
        
    def mostrar_dialogo_facturar(self, afiliados, solicitud, mes, valor, metodo, fecha, ventana):
        """
        Muestra el diálogo de confirmación de facturación.
        Al seleccionar 'Confirmado', se usa la fecha actual del sistema.
        """
        if not solicitud or solicitud['estado'] != 'cliente_confirmado':
            messagebox.showerror("Error", "El cliente aún no ha confirmado el pago.")
            return

        dialog = Toplevel(ventana)
        dialog.title("Confirmar facturación")
        dialog.geometry("400x200")
        self.centrar_ventana(dialog, 400, 200)
        dialog.resizable(False, False)
        dialog.transient(ventana)
        dialog.grab_set()

        ttk.Label(dialog, text="Estado del pago", style='Title.TLabel', font=('Arial', 12)).pack(pady=10)
        ttk.Label(dialog, text=f"Afiliado: {afiliados[0]['nombre']}", font=('Arial', 10)).pack()
        ttk.Label(dialog, text=f"Monto: ${float(valor):,.2f}", font=('Arial', 10)).pack(pady=5)

        def seleccionar_estado(estado_seleccionado):
            if estado_seleccionado == 'confirmado':
                # ========== CAMBIO CLAVE ==========
                # Usamos la fecha actual del sistema en lugar de la fecha del formulario
                fecha_actual = datetime.now().strftime("%Y-%m-%d")
                # ==================================
                self.guardar_pagos_y_facturar(afiliados, mes, valor, metodo, fecha_actual, ventana)
                self.db.actualizar_solicitud(solicitud['id'], 'facturado')
                dialog.destroy()
                ventana.destroy()
            else:
                self.db.actualizar_solicitud(solicitud['id'], estado_seleccionado)
                dialog.destroy()
                if hasattr(ventana, 'barra_frame'):
                    sol_act = self.db.obtener_solicitud_activa(afiliados[0]['cc'])
                    if sol_act:
                        self._mostrar_barra_progreso_solicitud(ventana.barra_frame, sol_act)
                    else:
                        for w in ventana.barra_frame.winfo_children():
                            w.destroy()
                        ttk.Label(ventana.barra_frame, text="Solicitud finalizada (Rechazada/Pendiente)", font=('Arial', 9), foreground='gray').pack()
                    ventana.btn_facturar.config(state="disabled")
                messagebox.showinfo("Actualizado", f"Estado de la solicitud: {estado_seleccionado}")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="Rechazado", command=lambda: seleccionar_estado('rechazado')).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Pendiente", command=lambda: seleccionar_estado('pendiente')).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Confirmado", command=lambda: seleccionar_estado('confirmado'), style='Accent.TButton').pack(side=tk.LEFT, padx=10)
            
    def anadir_pago(self, tree, ventana, afiliados_seleccionados):
        """Muestra formulario para añadir pago con diseño mejorado y más ancho"""
        if not afiliados_seleccionados:
            messagebox.showerror("Error", "Por favor seleccione al menos un afiliado")
            return

        # Cerrar la ventana de búsqueda y abrir el formulario de pago
        ventana.destroy()
        self.mostrar_formulario_pago_para_afiliados(afiliados_seleccionados)
        
    def _generar_mensaje_pago(self, afiliados, monto):
        """
        Genera un mensaje de texto con los datos de pago para compartir por WhatsApp.
        El mensaje incluye el número de Nequi, el monto exacto y una referencia.
        """
        nombres = [a['nombre'] for a in afiliados]
        lista_nombres = ", ".join(nombres)
        
        # Número de Nequi de la empresa (cambiar por el real)
        numero_nequi = "3022386236"   # Reemplaza con tu número de Nequi
        
        fecha_hoy = datetime.now().strftime("%d/%m/%Y")
        referencia = datetime.now().strftime("%Y%m%d%H%M%S")
        
        mensaje = (
            f"*PAGO DE SERVICIOS DE SEGURIDAD SOCIAL*\n\n"
            f"Afiliado(s): {lista_nombres}\n"
            f"Monto a pagar: ${monto:,.2f}\n\n"
            f"Realice el pago a través de Nequi al número:\n"
            f"*{numero_nequi}\n\n*"
            f"Referencia: {referencia}\n"
            f"Concepto: Pago de seguridad social {fecha_hoy}\n\n"
            f"*Importante: El monto debe ser exacto.*"
        )
        return mensaje
    
    def guardar_pagos_y_generar_link(self, afiliados_seleccionados, mes_pago, valor_pagado, metodo_pago, fecha_pago, ventana):
        # Validar campos (igual que antes)
        if not mes_pago or not valor_pagado or not metodo_pago:
            messagebox.showerror("Error", "Todos los campos son obligatorios")
            return
        try:
            valor = float(valor_pagado)
        except ValueError:
            messagebox.showerror("Error", "El valor debe ser un número")
            return

        # Generar mensaje para WhatsApp
        monto = float(valor_pagado)
        mensaje = self._generar_mensaje_pago(afiliados_seleccionados, monto)

        # Enviar por WhatsApp si hay celular, o mostrar el mensaje
        if afiliados_seleccionados and afiliados_seleccionados[0].get('celular'):
            numero = afiliados_seleccionados[0]['celular']
            self._enviar_whatsapp_texto(numero, mensaje)
        else:
            messagebox.showinfo("Mensaje de pago", mensaje)

        ventana.destroy()
        # Mensaje informativo (no se guardó nada)
        messagebox.showinfo("Éxito", "Mensaje enviado por WhatsApp. El pago NO ha sido registrado en el sistema. Use 'Facturar' para registrar.")

    def calcular_valor_afiliado(self, afiliado):
        """Calcula el valor total para un afiliado según sus servicios"""
        total = 0
        
        # EPS base
        if afiliado.get('eps'):
            total += self.precios['eps']
        
        # ARL
        if afiliado.get('arl'):
            total += self.precios['arl'].get(afiliado['arl'], 0)
        
        # Pensión
        if afiliado.get('pension'):
            total += self.precios['pension']
        
        # Caja de compensación
        if afiliado.get('caja_compensacion'):
            total += self.precios['caja']
        
        return int(total)  # Asegurar que devuelve un entero

    def guardar_pagos_y_facturar(self, afiliados_seleccionados, mes_pago, valor_pagado, metodo_pago, fecha_pago, ventana):
        """Guarda el pago, actualiza la base de datos y genera la factura. Reactiva al afiliado si estaba retirado."""
        if not valor_pagado or not metodo_pago:
            messagebox.showerror("Error", "Valor y método de pago son obligatorios")
            self.reproducir_sonido("alerta")
            return

        try:
            valor = float(valor_pagado)
        except ValueError:
            messagebox.showerror("Error", "El valor debe ser un número válido")
            self.reproducir_sonido("alerta")
            return

        try:
            datetime.strptime(fecha_pago, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Formato de fecha inválido. Use AAAA-MM-DD")
            self.reproducir_sonido("alerta")
            return

        for afiliado in afiliados_seleccionados:
            cc = afiliado['cc']

            if afiliado.get('fecha_retiro'):
                self.db.reactivar_afiliado(cc)
                for i, r in enumerate(self.retiros_data):
                    if r['cc'] == cc:
                        r.pop('fecha_retiro', None)
                        r.pop('motivo_retiro', None)
                        self.data.append(r)
                        del self.retiros_data[i]
                        break
                for a in self.data:
                    if a['cc'] == cc:
                        afiliado = a
                        break

            for i, reg in enumerate(self.data):
                if reg['cc'] == cc:
                    self.data[i]['mes_pago'] = mes_pago
                    self.data[i]['valor_pagado'] = valor
                    self.data[i]['metodo_pago'] = metodo_pago
                    self.data[i]['fecha_pago'] = fecha_pago
                    self.db.update_afiliado(cc, self.data[i])
                    self.actualizar_monitoreo_afiliado(cc)
                    self._registrar_auditoria("Registró pago", "Pagos", "Éxito",
                                            f"Afiliado {afiliado['nombre']} - ${valor}")
                    break

        self.update_afiliados_table()
        self.update_retiros_table()
        self.update_monitoreo_table()
        self.update_ingresos_table()
        self.calcular_totales_contabilidad()
        self.hacer_caja()

        factura_path = self.generar_factura(afiliados_seleccionados)

        # ===== SONIDO CONFIRMAR (pago exitoso) =====
        self.reproducir_sonido("confirmar")

        ventana.destroy()
        self.refrescar_sistema(silent=True)
                    
    def mostrar_opciones_compartir_factura(self, factura_path, afiliado=None):
        """Muestra opciones para compartir la factura generada"""
        share_window = Toplevel(self.root)
        share_window.title("Compartir Factura")
        share_window.geometry("400x250")
        self.centrar_ventana(share_window, 400, 250)   # <--- NUEVO
        share_window.resizable(False, False)
        
        # Centrar la ventana
        window_width = 400
        window_height = 250
        screen_width = share_window.winfo_screenwidth()
        screen_height = share_window.winfo_screenheight()
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        share_window.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        
        ttk.Label(share_window, text="Opciones para compartir la factura:", 
                style='Title.TLabel').pack(pady=10)
        
        # Frame para botones
        button_frame = ttk.Frame(share_window)
        button_frame.pack(pady=10, fill=tk.X, padx=20)
        
        # Botón para WhatsApp (solo si hay afiliado con celular)
        if afiliado and afiliado.get('celular'):
            whatsapp_btn = ttk.Button(button_frame, text="WhatsApp al Cliente", 
                                    command=lambda: self.compartir_por_whatsapp_cliente(
                                        factura_path, afiliado, share_window))
            whatsapp_btn.pack(pady=5, fill=tk.X)
        
        # Botón para Gmail (solo si hay afiliado con correo)
        if afiliado and afiliado.get('correo'):
            gmail_btn = ttk.Button(button_frame, text="Gmail al Cliente", 
                                command=lambda: self.compartir_por_gmail_cliente(
                                    factura_path, afiliado, share_window))
            gmail_btn.pack(pady=5, fill=tk.X)
        
        # Botón para abrir ubicación del archivo
        ttk.Button(button_frame, text="📂 Abrir Ubicación del Archivo", 
                command=lambda: self.abrir_ubicacion_archivo(factura_path, share_window)).pack(pady=5, fill=tk.X)
        
        # Botón Cancelar
        ttk.Button(share_window, text="Cancelar", 
                command=share_window.destroy).pack(pady=10)
        
    def compartir_por_whatsapp_cliente(self, factura_path, afiliado, ventana):
        try:
            numero = afiliado['celular']
            numero_limpio = ''.join(filter(str.isdigit, numero))
            mensaje = (
                f"Estimado/a {afiliado['nombre']},\n\n"
                f"Adjunto encontrará la factura por los servicios de:\n"
                f"- EPS: {afiliado.get('eps', 'No especificado')}\n"
                f"- ARL: {afiliado.get('arl', 'No especificado')}\n"
                f"- Pensión: {afiliado.get('pension', 'No especificado')}\n"
                f"- Caja: {afiliado.get('caja_compensacion', 'No especificado')}\n\n"
                f"Valor pagado: ${float(afiliado.get('valor_pagado', 0)):,.2f}\n"
                f"Fecha de pago: {afiliado.get('fecha_pago', 'No especificada')}\n\n"
                f"Gracias por su preferencia.\n"
                f"Atentamente,\n"
                f"SaluPago"
            )
            mensaje_codificado = urllib.parse.quote(mensaje)
            url_whatsapp = f"https://wa.me/{numero_limpio}?text={mensaje_codificado}"
            webbrowser.open_new_tab(url_whatsapp)
            # Ya no se destruye ventana aquí
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir WhatsApp: {str(e)}")

    def compartir_por_gmail_cliente(self, factura_path, afiliado, ventana):
        try:
            correo_destino = afiliado['correo']
            asunto = f"Factura de servicios - {afiliado['nombre']}"
            mensaje = (
                f"Estimado/a {afiliado['nombre']},\n\n"
                f"Adjunto encontrará la factura por los servicios de:\n"
                f"- EPS: {afiliado.get('eps', 'No especificado')}\n"
                f"- ARL: {afiliado.get('arl', 'No especificado')}\n"
                f"- Pensión: {afiliado.get('pension', 'No especificado')}\n"
                f"- Caja: {afiliado.get('caja_compensacion', 'No especificado')}\n\n"
                f"Valor pagado: ${float(afiliado.get('valor_pagado', 0)):,.2f}\n"
                f"Fecha de pago: {afiliado.get('fecha_pago', 'No especificada')}\n\n"
                f"Gracias por su preferencia.\n\n"
                f"Atentamente,\n"
                f"SaluPago"
            )
            url_gmail = (
                f"https://mail.google.com/mail/?view=cm&fs=1"
                f"&to={correo_destino}"
                f"&su={urllib.parse.quote(asunto)}"
                f"&body={urllib.parse.quote(mensaje)}"
            )
            webbrowser.open_new_tab(url_gmail)
            # Ya no se destruye ventana aquí
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir Gmail: {str(e)}")

    def abrir_ubicacion_archivo(self, filepath, ventana=None):
        try:
            if not os.path.exists(filepath):
                messagebox.showerror("Error", f"El archivo no existe:\n{filepath}")
                return
            directorio = os.path.dirname(filepath)
            if not os.path.exists(directorio):
                messagebox.showerror("Error", f"El directorio no existe:\n{directorio}")
                return
            os.startfile(directorio)
            # Ya no se destruye ventana aquí
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la ubicación:\n{str(e)}")

    def abrir_en_explorador(self, ruta):
        """
        Abre una ruta en el explorador de archivos de Windows.
        """
        try:
            if not os.path.exists(ruta):
                messagebox.showerror("Error", f"La ruta no existe:\n{ruta}")
                return False
            
            # EN WINDOWS: Usar os.startfile
            os.startfile(ruta)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir:\n{str(e)}")
            return False

    def guardar_pagos(self, afiliados_seleccionados, mes_pago, valor_pagado, metodo_pago, fecha_pago, ventana, cerrar_ventana=True):
        """
        Guarda el pago en el sistema. Si cerrar_ventana es True, cierra la ventana y muestra mensaje.
        """
        if not mes_pago or not valor_pagado or not metodo_pago:
            messagebox.showerror("Error", "Todos los campos son obligatorios")
            return
        try:
            valor = float(valor_pagado)
        except ValueError:
            messagebox.showerror("Error", "El valor debe ser un número")
            return

        for afiliado in afiliados_seleccionados:
            for i, registro in enumerate(self.data):
                if registro['cc'] == afiliado['cc']:
                    self.data[i]['mes_pago'] = mes_pago
                    self.data[i]['valor_pagado'] = valor_pagado
                    self.data[i]['metodo_pago'] = metodo_pago
                    self.data[i]['fecha_pago'] = fecha_pago
                    self.db.update_afiliado(registro['cc'], self.data[i])
                    break

        self.update_afiliados_table()

        if cerrar_ventana:
            ventana.destroy()
            messagebox.showinfo("Éxito", f"Pago añadido a {len(afiliados_seleccionados)} afiliados")

    def generar_factura_final(self, afiliados_seleccionados, ventana):
        """Genera la factura final para los afiliados seleccionados"""
        if not afiliados_seleccionados:
            messagebox.showerror("Error", "Por favor seleccione al menos un afiliado")
            return
        
        # Verificar que todos tengan pago registrado
        for afiliado in afiliados_seleccionados:
            if not afiliado.get('valor_pagado'):
                messagebox.showerror("Error", f"El afiliado {afiliado['nombre']} no tiene pago registrado")
                return
        
        if len(afiliados_seleccionados) == 1:
            factura_path = self.generar_factura(afiliados_seleccionados)
        else:
            confirmar = messagebox.askyesno("Facturación múltiple", 
                                        f"¿Desea generar una factura conjunta para {len(afiliados_seleccionados)} afiliados?")
            if confirmar:
                factura_path = self.generar_factura(afiliados_seleccionados)
        
        # Cerrar ventana
        ventana.destroy()
                
    def obtener_numero_factura(self, cc_cliente):
        """Obtiene el número de factura en formato CC{cedula}-{mes}{año}"""
        fecha_actual = datetime.now()
        mes = fecha_actual.strftime("%m")  # Mes con dos dígitos (01-12)
        año = fecha_actual.strftime("%Y")  # Año con cuatro dígitos
        
        # Eliminar cualquier caracter no numérico de la cédula
        cc_limpio = ''.join(filter(str.isdigit, cc_cliente))
        
        return f"CC{cc_limpio}-{mes}{año}"
    
    def generar_factura(self, registros):
        """
        Genera un PDF con la factura en un formato profesional usando plantillas.
        """
        if not registros:
            return None

        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch, cm
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

        # Crear directorio de facturas
        directorio_facturas = os.path.join(BASE_PATH, "facturas")
        os.makedirs(directorio_facturas, exist_ok=True)

        numero_factura = self.obtener_numero_factura(registros[0]['cc'])
        filename = os.path.join(directorio_facturas, f"Factura_{numero_factura}.pdf")

        # Configurar documento
        doc = SimpleDocTemplate(filename, pagesize=letter,
                                leftMargin=1.5*cm, rightMargin=1.5*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        elements = []
        styles = getSampleStyleSheet()

        # Estilos para títulos y cabeceras
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Title'],
            fontSize=18,
            textColor=colors.HexColor('#1a237e'),
            alignment=TA_CENTER,
            spaceAfter=12
        )
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
            alignment=TA_CENTER
        )
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            fontSize=9,
            alignment=TA_CENTER
        )
        total_style = ParagraphStyle(
            'TotalStyle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#1a237e'),
            alignment=TA_RIGHT
        )

        # ========== ENCABEZADO CON LOGO Y DATOS DE EMPRESA ==========
        # Crear tabla de 2 columnas: logo (izquierda) y datos empresa (derecha)
        header_data = []

        # Logo (si existe)
        logo_path = os.path.join(IMG_PATH, "LogoSaluPago.png")
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=3*cm, height=3*cm)  # <--- Aumentado a 3 cm
                logo_cell = [logo]
            except:
                logo_cell = [""]
        else:
            logo_cell = [""]

        # Datos de la empresa en una celda
        # Datos de la empresa desde configuración
        empresa = self.config.get('empresa', {})
        nombre_emp = empresa.get('nombre', 'SaluPago')
        nit_emp = empresa.get('nit', 'NIT no definido')
        direc_emp = empresa.get('direccion', 'Dirección no definida')
        tel_emp = empresa.get('telefono', 'Teléfono no definido')
        correo_emp = empresa.get('correo', 'correo@empresa.com')

        empresa_text = [
            nombre_emp,
            direc_emp,
            correo_emp,
            f"NIT: {nit_emp}",
            f"Teléfono: {tel_emp}",
            f"www.{nombre_emp.lower().replace(' ', '')}.com"   # opcional, o puedes agregar un campo web en config
        ]
        empresa_paragraphs = [Paragraph(line, header_style) for line in empresa_text]
        # Agrupar en un párrafo con saltos de línea
        empresa_block = Paragraph("<br/>".join(empresa_text), header_style)

        # Construir tabla del encabezado: [Logo | Datos empresa]
        header_table = Table([[logo_cell[0], empresa_block]], colWidths=[3*cm, 10*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,0), 'CENTER'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.3*cm))

        # Línea separadora
        elements.append(Paragraph("<hr/>", styles['Normal']))
        elements.append(Spacer(1, 0.3*cm))

        # ========== TÍTULO DE FACTURA ==========
        elements.append(Paragraph("FACTURA", title_style))
        elements.append(Spacer(1, 0.3*cm))

        # ========== DATOS DEL CLIENTE ==========
        cliente = registros[0]
        cliente_data = [
            ["Cliente:", cliente['nombre']],
            ["Cédula:", cliente['cc']],
            ["Dirección:", cliente.get('direccion', '---')],
            ["Fecha:", datetime.now().strftime('%d/%m/%Y')],
            ["Factura N°:", numero_factura.replace('CC', '').replace('FAC', '')]
        ]
        # Aumentar el ancho de la segunda columna para mejor visibilidad
        cliente_table = Table(cliente_data, colWidths=[2.5*cm, 8.5*cm])
        cliente_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#1a237e')),
            ('TEXTCOLOR', (1,0), (1,-1), colors.HexColor('#333333')),
            ('ALIGN', (0,0), (0,-1), 'RIGHT'),
            ('ALIGN', (1,0), (1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 2),
            ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ]))
        elements.append(cliente_table)
        elements.append(Spacer(1, 0.5*cm))

        # ========== DETALLE DE SERVICIOS ==========
        # Preparar datos de servicios
        servicios = []
        total = 0.0
        for reg in registros:
            if reg['eps']:
                servicios.append(["EPS", reg['eps'], f"${self.precios['eps']:,.2f}"])
                total += self.precios['eps']
            if reg['arl']:
                arl_valor = self.precios['arl'].get(reg['arl'], 0)
                servicios.append(["ARL", reg['arl'], f"${arl_valor:,.2f}"])
                total += arl_valor
            if reg['pension']:
                servicios.append(["Pensión", reg['pension'], f"${self.precios['pension']:,.2f}"])
                total += self.precios['pension']
            if reg['caja_compensacion']:
                servicios.append(["Caja Comp.", reg['caja_compensacion'], f"${self.precios['caja']:,.2f}"])
                total += self.precios['caja']

        if not servicios:
            servicios.append(["Sin servicios", "", "$0"])

        # Tabla de servicios con anchos ajustados
        tabla_servicios = Table([["Artículo", "Descripción", "Subtotal"]] + servicios,
                                colWidths=[2.5*cm, 6*cm, 3*cm])
        tabla_servicios.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a237e')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 9),
            ('BACKGROUND', (0,1), (-1,-2), colors.whitesmoke),
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e3f2fd')),
            ('TEXTCOLOR', (-1,1), (-1,-1), colors.HexColor('#1a237e')),
            ('FONTNAME', (-1,-1), (-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (-1,-1), (-1,-1), 11),
        ]))
        elements.append(tabla_servicios)
        elements.append(Spacer(1, 0.3*cm))

        # ========== TOTAL ==========
        total_str = f"${total:,.2f}"
        total_paragraph = Paragraph(f"<b>TOTAL: {total_str}</b>", total_style)
        elements.append(total_paragraph)
        elements.append(Spacer(1, 0.5*cm))

        # ========== PIE DE PÁGINA ==========
        footer_text = "Gracias por su preferencia. Este documento es un comprobante de pago."
        footer = Paragraph(footer_text, styles['Normal'])
        elements.append(footer)
        elements.append(Spacer(1, 0.2*cm))
        fecha_gen = datetime.now().strftime('%d/%m/%Y %H:%M')
        footer_fecha = Paragraph(f"Generado el {fecha_gen}", styles['Italic'])
        elements.append(footer_fecha)

        # Construir PDF
        doc.build(elements)

        # Abrir automáticamente usando sys.platform (corregido)
        try:
            import sys
            if sys.platform == 'win32':
                os.startfile(filename)
            elif sys.platform == 'darwin':
                subprocess.call(('open', filename))
            else:
                subprocess.call(('xdg-open', filename))
        except Exception as e:
            # Si no se puede abrir, al menos mostrar la ubicación
            messagebox.showinfo("Factura generada", f"Factura guardada en:\n{filename}")

        # Registrar en contabilidad si es Administrativo
        if self.user_role == "Administrativo":
            self.registrar_factura_en_contabilidad(registros, total)

        # ===== SONIDO DE FACTURA GENERADA =====
        self.reproducir_sonido("confirmar")

        return filename
    
    def generar_factura_reactivacion(self, registro):
        """
        Genera una factura para una reactivación mostrando los servicios reales del afiliado.
        Registra el ingreso automáticamente en contabilidad.
        """
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch, cm
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

        # Crear directorio de facturas
        directorio_facturas = os.path.join(BASE_PATH, "facturas")
        os.makedirs(directorio_facturas, exist_ok=True)

        cc = registro['cc']
        numero_factura = self.obtener_numero_factura(cc)
        filename = os.path.join(directorio_facturas, f"Factura_{numero_factura}.pdf")

        # Configurar documento
        doc = SimpleDocTemplate(filename, pagesize=letter,
                                leftMargin=1.5*cm, rightMargin=1.5*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        elements = []
        styles = getSampleStyleSheet()

        # Estilos
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Title'],
            fontSize=18,
            textColor=colors.HexColor('#1a237e'),
            alignment=TA_CENTER,
            spaceAfter=12
        )
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
            alignment=TA_CENTER
        )
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            fontSize=9,
            alignment=TA_CENTER
        )
        total_style = ParagraphStyle(
            'TotalStyle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#1a237e'),
            alignment=TA_RIGHT
        )

        # Encabezado con logo y datos de empresa
        logo_path = os.path.join(IMG_PATH, "LogoSaluPago.png")
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=3*cm, height=3*cm)
                logo_cell = [logo]
            except:
                logo_cell = [""]
        else:
            logo_cell = [""]

        empresa = self.config.get('empresa', {})
        nombre_emp = empresa.get('nombre', 'SaluPago')
        nit_emp = empresa.get('nit', 'NIT no definido')
        direc_emp = empresa.get('direccion', 'Dirección no definida')
        tel_emp = empresa.get('telefono', 'Teléfono no definido')
        correo_emp = empresa.get('correo', 'correo@empresa.com')

        empresa_text = [
            nombre_emp,
            direc_emp,
            correo_emp,
            f"NIT: {nit_emp}",
            f"Teléfono: {tel_emp}",
            f"www.{nombre_emp.lower().replace(' ', '')}.com"
        ]
        empresa_block = Paragraph("<br/>".join(empresa_text), header_style)

        header_table = Table([[logo_cell[0], empresa_block]], colWidths=[3*cm, 10*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,0), 'CENTER'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.3*cm))
        elements.append(Paragraph("<hr/>", styles['Normal']))
        elements.append(Spacer(1, 0.3*cm))

        # Título
        elements.append(Paragraph("FACTURA", title_style))
        elements.append(Spacer(1, 0.3*cm))

        # Datos del cliente
        cliente_data = [
            ["Cliente:", registro['nombre']],
            ["Cédula:", registro['cc']],
            ["Dirección:", registro.get('direccion', '---')],
            ["Fecha:", datetime.now().strftime('%d/%m/%Y')],
            ["Factura N°:", numero_factura.replace('CC', '').replace('FAC', '')]
        ]
        cliente_table = Table(cliente_data, colWidths=[2.5*cm, 8.5*cm])
        cliente_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#1a237e')),
            ('TEXTCOLOR', (1,0), (1,-1), colors.HexColor('#333333')),
            ('ALIGN', (0,0), (0,-1), 'RIGHT'),
            ('ALIGN', (1,0), (1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 2),
            ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ]))
        elements.append(cliente_table)
        elements.append(Spacer(1, 0.5*cm))

        # ========== CONSTRUIR SERVICIOS DINÁMICAMENTE ==========
        servicios = []
        total = 0.0

        if registro.get('eps'):
            servicios.append(["EPS", registro['eps'], f"${self.precios['eps']:,.2f}"])
            total += self.precios['eps']
        if registro.get('arl'):
            arl_valor = self.precios['arl'].get(registro['arl'], 0)
            servicios.append(["ARL", registro['arl'], f"${arl_valor:,.2f}"])
            total += arl_valor
        if registro.get('pension'):
            servicios.append(["Pensión", registro['pension'], f"${self.precios['pension']:,.2f}"])
            total += self.precios['pension']
        if registro.get('caja_compensacion'):
            servicios.append(["Caja Comp.", registro['caja_compensacion'], f"${self.precios['caja']:,.2f}"])
            total += self.precios['caja']

        if not servicios:
            servicios.append(["Sin servicios", "", "$0"])

        tabla_servicios = Table([["Artículo", "Descripción", "Subtotal"]] + servicios,
                                colWidths=[2.5*cm, 6*cm, 3*cm])
        tabla_servicios.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a237e')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 9),
            ('BACKGROUND', (0,1), (-1,-2), colors.whitesmoke),
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e3f2fd')),
            ('TEXTCOLOR', (-1,1), (-1,-1), colors.HexColor('#1a237e')),
            ('FONTNAME', (-1,-1), (-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (-1,-1), (-1,-1), 11),
        ]))
        elements.append(tabla_servicios)
        elements.append(Spacer(1, 0.3*cm))

        # Total
        total_str = f"${total:,.2f}"
        total_paragraph = Paragraph(f"<b>TOTAL: {total_str}</b>", total_style)
        elements.append(total_paragraph)
        elements.append(Spacer(1, 0.5*cm))

        # Pie de página
        footer_text = "Gracias por su preferencia. Este documento es un comprobante de pago."
        footer = Paragraph(footer_text, styles['Normal'])
        elements.append(footer)
        elements.append(Spacer(1, 0.2*cm))
        fecha_gen = datetime.now().strftime('%d/%m/%Y %H:%M')
        footer_fecha = Paragraph(f"Generado el {fecha_gen}", styles['Italic'])
        elements.append(footer_fecha)

        doc.build(elements)

        # Abrir automáticamente
        try:
            if sys.platform == 'win32':
                os.startfile(filename)
            elif sys.platform == 'darwin':
                subprocess.call(('open', filename))
            else:
                subprocess.call(('xdg-open', filename))
        except Exception as e:
            messagebox.showinfo("Factura generada", f"Factura guardada en:\n{filename}")

        # Registrar ingreso en contabilidad (si es Administrativo)
        if self.user_role == "Administrativo":
            ingreso_data = {
                "fecha": registro.get('fecha_pago', datetime.now().strftime("%Y-%m-%d")),
                "cc": registro['cc'],
                "nombre": registro['nombre'],
                "servicio": "Reactivación",
                "valor": total,
                "metodo_pago": registro.get('metodo_pago', 'No especificado'),
                "comprobante": f"Factura {numero_factura}"
            }
            new_id = self.db.add_ingreso(ingreso_data)
            ingreso_data['id'] = new_id
            self.contabilidad_data['ingresos'].append(ingreso_data)
            self.update_ingresos_table()
            self.calcular_totales_contabilidad()
            self.hacer_caja()

        return filename

    def registrar_factura_en_contabilidad(self, registros, total):
        for registro in registros:
            numero_factura = self.obtener_numero_factura(registro['cc'])
            data = {
                "fecha": registro['fecha_pago'],
                "cc": registro['cc'],
                "nombre": registro['nombre'],
                "servicio": registro['eps'] or registro['arl'],
                "valor": float(registro['valor_pagado'] or 0),
                "metodo_pago": registro.get('metodo_pago', 'No especificado'),
                "comprobante": f"Factura {numero_factura}"
            }
            new_id = self.db.add_ingreso(data)
            data['id'] = new_id
            self.contabilidad_data['ingresos'].append(data)
        self.update_contabilidad_tables()
    
    def registrar_ingreso(self):
        """Muestra el formulario para registrar un ingreso manual con diseño dividido (imagen + formulario)"""
        if self.user_role == "Auxiliar":
            if not self.validar_password():
                return
        
        ventana = Toplevel(self.root)
        ventana.title("Registrar Ingreso Manual")
        ventana.geometry("750x420")  
        self.centrar_ventana(ventana, 750, 420)
        ventana.resizable(False, False)
        
        # Variables
        fecha_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        cc_var = tk.StringVar()
        nombre_var = tk.StringVar()
        servicio_var = tk.StringVar()
        valor_var = tk.StringVar()
        metodo_pago_var = tk.StringVar()
        comprobante_var = tk.StringVar()
        
        # ====== FRAME PRINCIPAL (Dividido en 2 columnas) ======
        main_frame = ttk.Frame(ventana, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Columna Izquierda: Imagen LogoSaluPago.png
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 20))
        
        try:
            avatar_path = os.path.join(IMG_PATH, "LogoSaluPago.png")
            if os.path.exists(avatar_path):
                img = Image.open(avatar_path)
                # Redimensionar la imagen a un tamaño adecuado (ej. 300x300)
                img = img.resize((300, 300), Image.LANCZOS)
                img_tk = ImageTk.PhotoImage(img)
                
                img_label = ttk.Label(left_frame, image=img_tk)
                img_label.image = img_tk  # Mantener referencia para evitar garbage collection
                img_label.pack(expand=True, pady=20)
            else:
                ttk.Label(left_frame, text="LogoSaluPago.png no encontrado", 
                         font=('Segoe UI', 11), foreground='gray').pack(expand=True)
        except Exception as e:
            ttk.Label(left_frame, text=f"Error al cargar imagen:\n{str(e)}", 
                     font=('Segoe UI', 10), foreground='red').pack(expand=True)
            
        # Columna Derecha: Formulario
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Título
        ttk.Label(right_frame, text="Registrar Ingreso Manual", 
                 style='Title.TLabel', font=('Segoe UI', 16, 'bold')).pack(pady=(0, 15))
        
        # Frame para los campos del formulario
        form_frame = ttk.LabelFrame(right_frame, text="Detalles del Ingreso", padding=15)
        form_frame.pack(fill=tk.X, pady=10)
        
        # Campos del formulario (ajustamos los anchos para que encajen bien en la columna derecha)
        self.create_form_field(form_frame, "Fecha:", fecha_var, 0, width=25)
        self.create_form_field(form_frame, "CC:", cc_var, 1, width=25)
        self.create_form_field(form_frame, "Nombre:", nombre_var, 2, width=25)
        self.create_combobox_field(form_frame, "Servicio:", servicio_var, 
                                ["EPS", "ARL", "Pensión", "Caja de Compensación"], 3, width=23)
        self.create_form_field(form_frame, "Valor:", valor_var, 4, width=25)
        self.create_combobox_field(form_frame, "Método de Pago:", metodo_pago_var, 
                                self.metodos_pago, 5, width=23)
        self.create_form_field(form_frame, "Comprobante:", comprobante_var, 6, width=25)
        
        # Frame para los botones
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Botones alineados a la derecha
        ttk.Button(button_frame, text="Cancelar", command=ventana.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Guardar", 
                command=lambda: self.guardar_ingreso(
                    fecha_var.get(), cc_var.get(), nombre_var.get(), 
                    servicio_var.get(), valor_var.get(), 
                    metodo_pago_var.get(), comprobante_var.get(), ventana)).pack(side=tk.RIGHT, padx=5)
               
    def guardar_ingreso(self, fecha, cc, nombre, servicio, valor, metodo_pago, comprobante, ventana):
        if not servicio or not valor or not metodo_pago:
            messagebox.showerror("Error", "Servicio, valor y método de pago son obligatorios")
            return
        try:
            valor_float = float(valor)
        except ValueError:
            messagebox.showerror("Error", "El valor debe ser un número válido")
            return
        data = {
            "fecha": fecha,
            "cc": cc,
            "nombre": nombre,
            "servicio": servicio,
            "valor": valor_float,
            "metodo_pago": metodo_pago,
            "comprobante": comprobante
        }
        new_id = self.db.add_ingreso(data)
        data['id'] = new_id
        self.contabilidad_data['ingresos'].append(data)
        self.update_ingresos_table()
        self.calcular_totales_contabilidad()
        ventana.destroy()
        # === AUDITORÍA ===
        self._registrar_auditoria("Registró ingreso", "Contabilidad", "Éxito", f"Servicio: {servicio}")
        self.mostrar_toast("Ingreso registrado correctamente")
        self.refrescar_sistema(silent=True)
        
    def registrar_egreso(self):
        """Muestra el formulario para registrar un egreso con un diseño dividido (imagen + formulario)"""
        if self.user_role == "Auxiliar":
            if not self.validar_password():
                return
        
        ventana = Toplevel(self.root)
        ventana.title("Registrar Egreso")
        ventana.geometry("750x350")
        self.centrar_ventana(ventana, 750, 350)
        ventana.resizable(False, False)
        
        # Variables
        fecha_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        descripcion_var = tk.StringVar()
        valor_var = tk.StringVar()
        metodo_pago_var = tk.StringVar()
        
        # ====== FRAME PRINCIPAL (Dividido en 2 columnas) ======
        main_frame = ttk.Frame(ventana, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Columna Izquierda: Imagen LogoSaluPago.png
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 20))
        
        try:
            avatar_path = os.path.join(IMG_PATH, "LogoSaluPago.png")
            if os.path.exists(avatar_path):
                img = Image.open(avatar_path)
                # Redimensionar la imagen a un tamaño adecuado (ej. 280x280)
                img = img.resize((280, 280), Image.LANCZOS)
                img_tk = ImageTk.PhotoImage(img)
                
                img_label = ttk.Label(left_frame, image=img_tk)
                img_label.image = img_tk  # Mantener referencia
                img_label.pack(expand=True, pady=20)
            else:
                ttk.Label(left_frame, text="LogoSaluPago.png no encontrado", 
                         font=('Segoe UI', 11), foreground='gray').pack(expand=True)
        except Exception as e:
            ttk.Label(left_frame, text=f"Error al cargar imagen:\n{str(e)}", 
                     font=('Segoe UI', 10), foreground='red').pack(expand=True)
            
        # Columna Derecha: Formulario
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Título
        ttk.Label(right_frame, text="Registrar Egreso", 
                 style='Title.TLabel', font=('Segoe UI', 16, 'bold')).pack(pady=(0, 15))
        
        # Frame para los campos del formulario
        form_frame = ttk.LabelFrame(right_frame, text="Detalles del Egreso", padding=15)
        form_frame.pack(fill=tk.X, pady=10)
        
        # Campos del formulario (ajustamos los anchos para que encajen bien en la columna derecha)
        self.create_form_field(form_frame, "Fecha:", fecha_var, 0, width=25)
        self.create_form_field(form_frame, "Descripción*:", descripcion_var, 1, width=25, required=True)
        self.create_form_field(form_frame, "Valor*:", valor_var, 2, width=25, required=True)
        self.create_combobox_field(form_frame, "Método de Pago*:", metodo_pago_var, 
                                 self.metodos_pago, 3, width=23, required=True)
        
        # Frame para los botones
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Botones alineados a la derecha
        ttk.Button(button_frame, text="Cancelar", command=ventana.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Guardar", 
                command=lambda: self.guardar_egreso(
                    fecha_var.get(), descripcion_var.get(), 
                    valor_var.get(), metodo_pago_var.get(), ventana)).pack(side=tk.RIGHT, padx=5)

    def guardar_egreso(self, fecha, descripcion, valor, metodo_pago, ventana):
        if not descripcion or not valor or not metodo_pago:
            messagebox.showerror("Error", "Descripción, valor y método de pago son obligatorios")
            return
        try:
            valor_float = float(valor)
        except ValueError:
            messagebox.showerror("Error", "El valor debe ser un número válido")
            return
        data = {
            "fecha": fecha,
            "descripcion": descripcion,
            "valor": valor_float,
            "metodo_pago": metodo_pago
        }
        new_id = self.db.add_egreso(data)
        data['id'] = new_id
        self.contabilidad_data['egresos'].append(data)
        self.update_egresos_table()
        self.calcular_totales_contabilidad()
        ventana.destroy()
        # === AUDITORÍA ===
        self._registrar_auditoria("Registró egreso", "Contabilidad", "Éxito", f"Descripción: {descripcion}")
        self.mostrar_toast("Egreso registrado correctamente")
        self.refrescar_sistema(silent=True)
        
    def registrar_novedad(self):
        """Muestra el formulario para registrar una novedad con búsqueda de afiliado"""
        ventana = Toplevel(self.root)
        ventana.title("Registrar Novedad")
        ventana.geometry("600x500")
        self.centrar_ventana(ventana, 600, 500)
        
        # Variables
        fecha_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        cc_var = tk.StringVar()
        nombre_var = tk.StringVar()
        estado_var = tk.StringVar(value="Estado: No identificado")
        novedad_var = tk.StringVar()
        busqueda_var = tk.StringVar()
        
        # Función para buscar afiliado
        def buscar_afiliado():
            texto_busqueda = busqueda_var.get().lower()
            if not texto_busqueda:
                messagebox.showwarning("Advertencia", "Ingrese un número de cédula o nombre para buscar")
                return
            
            encontrado = False
            
            # Buscar en afiliados activos
            for afiliado in self.data:
                if (texto_busqueda in afiliado['cc'].lower() or 
                    texto_busqueda in afiliado['nombre'].lower()):
                    cc_var.set(afiliado['cc'])
                    nombre_var.set(afiliado['nombre'])
                    estado_var.set("Estado: Activo")
                    encontrado = True
                    break
            
            # Si no se encontró en activos, buscar en retirados
            if not encontrado:
                for retirado in self.retiros_data:
                    if (texto_busqueda in retirado['cc'].lower() or 
                        texto_busqueda in retirado['nombre'].lower()):
                        cc_var.set(retirado['cc'])
                        nombre_var.set(retirado['nombre'])
                        estado_var.set("Estado: Retirado")
                        encontrado = True
                        break
            
            if not encontrado:
                messagebox.showinfo("Información", "No se encontró ningún afiliado con ese nombre o cédula")
        
        # Frame de búsqueda
        busqueda_frame = ttk.Frame(ventana)
        busqueda_frame.pack(pady=10, padx=20, fill=tk.X)
        
        ttk.Label(busqueda_frame, text="Buscar Afiliado:").pack(side=tk.LEFT, padx=5)
        busqueda_entry = ttk.Entry(busqueda_frame, textvariable=busqueda_var, width=30)
        busqueda_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(busqueda_frame, text="🧠Buscar por CC/Nombre", 
                command=buscar_afiliado).pack(side=tk.LEFT, padx=5)
        
        # Frame de datos del afiliado
        datos_frame = ttk.LabelFrame(ventana, text="Datos del Afiliado", padding=10)
        datos_frame.pack(pady=10, padx=20, fill=tk.X)
        
        ttk.Label(datos_frame, text="Fecha:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(datos_frame, textvariable=fecha_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(datos_frame, text="CC:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(datos_frame, textvariable=cc_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(datos_frame, text="Nombre:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(datos_frame, textvariable=nombre_var).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(datos_frame, textvariable=estado_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        # Frame de novedad
        novedad_frame = ttk.LabelFrame(ventana, text="Novedad", padding=10)
        novedad_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        ttk.Label(novedad_frame, text="Descripción de la novedad*:").pack(anchor=tk.W, padx=5, pady=2)
        novedad_text = tk.Text(novedad_frame, height=5, width=60)
        novedad_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Botones
        button_frame = ttk.Frame(ventana)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Cancelar", command=ventana.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Guardar", 
                command=lambda: self.guardar_novedad(
                    fecha_var.get(), cc_var.get(), 
                    nombre_var.get(), novedad_text.get("1.0", tk.END).strip(), 
                    ventana)).pack(side=tk.LEFT, padx=5)

    def guardar_novedad(self, fecha, cc, nombre, novedad, ventana):
        if not novedad:
            messagebox.showerror("Error", "La descripción de la novedad es obligatoria")
            return
        if not cc or not nombre:
            messagebox.showerror("Error", "Debe buscar y seleccionar un afiliado primero")
            return
        data = {
            "fecha": fecha,
            "cc": cc,
            "nombre": nombre,
            "novedad": novedad
        }
        new_id = self.db.add_novedad(data)
        data['id'] = new_id
        self.contabilidad_data['novedades'].append(data)
        self.update_novedades_table()
        ventana.destroy()
        # === AUDITORÍA ===
        self._registrar_auditoria("Registró novedad", "Contabilidad", "Éxito", f"Afiliado: {nombre}")
        self.mostrar_toast("Novedad registrada correctamente")
        self.refrescar_sistema(silent=True)
        
    def editar_novedad(self):
        """Permite editar una novedad seleccionada"""
        selected_item = self.novedades_tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Por favor seleccione una novedad para editar")
            return
            
        # Obtener datos del registro seleccionado
        index = self.novedades_tree.index(selected_item[0])
        registro = self.contabilidad_data['novedades'][index]
        
        # Crear ventana de edición
        ventana = Toplevel(self.root)
        ventana.title("Editar Novedad")
        ventana.geometry("500x300")
        self.centrar_ventana(ventana, 500, 300) 
        
        # Variables
        fecha_var = tk.StringVar(value=registro['fecha'])
        cc_var = tk.StringVar(value=registro['cc'])
        nombre_var = tk.StringVar(value=registro['nombre'])
        novedad_var = tk.StringVar(value=registro['novedad'])
        
        # Formulario
        ttk.Label(ventana, text="Editar Novedad", style='Title.TLabel').pack(pady=10)
        
        frame = ttk.Frame(ventana)
        frame.pack(pady=10, padx=20, fill=tk.X)
        
        self.create_form_field(frame, "Fecha:", fecha_var, 0)
        self.create_form_field(frame, "CC:", cc_var, 1)
        self.create_form_field(frame, "Nombre:", nombre_var, 2, width=30)
        self.create_form_field(frame, "Novedad*:", novedad_var, 3, width=40, required=True)
        
        # Botones
        button_frame = ttk.Frame(ventana)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Cancelar", command=ventana.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Guardar", 
                  command=lambda: self.actualizar_novedad(
                      index, fecha_var.get(), cc_var.get(), 
                      nombre_var.get(), novedad_var.get(), ventana)).pack(side=tk.LEFT, padx=5)
    
    def actualizar_novedad(self, index, fecha, cc, nombre, novedad, ventana):
        if not novedad:
            messagebox.showerror("Error", "La descripción de la novedad es obligatoria")
            return
        data = {
            "fecha": fecha,
            "cc": cc,
            "nombre": nombre,
            "novedad": novedad
        }
        # Obtener id del registro
        registro_id = self.contabilidad_data['novedades'][index]['id']
        self.db.update_novedad(registro_id, data)
        self.contabilidad_data['novedades'][index] = data
        self.update_novedades_table()
        ventana.destroy()
        messagebox.showinfo("Éxito", "Novedad actualizada correctamente")
        self.refrescar_sistema(silent=True)   

    def eliminar_registro_contable(self, tipo):
        if tipo == 'ingresos':
            tree = self.ingresos_tree
            data_list = self.contabilidad_data['ingresos']
            delete_func = self.db.delete_ingreso
        elif tipo == 'egresos':
            tree = self.egresos_tree
            data_list = self.contabilidad_data['egresos']
            delete_func = self.db.delete_egreso
        elif tipo == 'novedades':
            tree = self.novedades_tree
            data_list = self.contabilidad_data['novedades']
            delete_func = self.db.delete_novedad
        else:
            return

        selected_item = tree.selection()
        if not selected_item:
            messagebox.showerror("Error", f"Por favor seleccione un registro de {tipo} para eliminar")
            self.reproducir_sonido("alerta")
            return

        if not self.validar_password():
            self.reproducir_sonido("alerta")
            return

        index = tree.index(selected_item[0])
        registro = data_list[index]
        registro_id = registro.get('id')

        archivos_eliminados = 0

        if tipo == 'ingresos':
            comprobante = registro.get('comprobante', '')
            if comprobante:
                if not messagebox.askyesno("Confirmar eliminación",
                                        f"¿Está seguro de eliminar este ingreso?\n\n"
                                        f"Comprobante: {comprobante}\n"
                                        f"¿Desea eliminar también el archivo PDF de la factura asociada?",
                                        icon=messagebox.WARNING):
                    if registro_id:
                        delete_func(registro_id)
                    del data_list[index]
                    if tipo in ['ingresos', 'egresos']:
                        self.calcular_totales_contabilidad()
                    self.update_contabilidad_tables()
                    self._registrar_auditoria(
                        f"Eliminó {tipo}", "Contabilidad", "Éxito",
                        f"ID {registro_id}, comprobante: {comprobante} (archivo conservado)"
                    )
                    self.mostrar_toast(f"Registro de {tipo} eliminado correctamente")
                    self.reproducir_sonido("eliminar")
                    return

                directorio_facturas = os.path.join(BASE_PATH, "facturas")
                if os.path.exists(directorio_facturas):
                    num_comprobante = comprobante.replace("Factura ", "").strip()
                    for archivo in os.listdir(directorio_facturas):
                        if (num_comprobante.lower() in archivo.lower() or
                            archivo.lower().startswith(f"factura_{num_comprobante.lower()}") or
                            archivo.lower().endswith(f"{num_comprobante.lower()}.pdf")):
                            try:
                                os.remove(os.path.join(directorio_facturas, archivo))
                                archivos_eliminados += 1
                            except:
                                pass

        if registro_id:
            delete_func(registro_id)
        del data_list[index]

        if tipo in ['ingresos', 'egresos']:
            self.calcular_totales_contabilidad()
        self.update_contabilidad_tables()

        if tipo == 'ingresos':
            comprobante = registro.get('comprobante', '')
            detalles = f"ID {registro_id}, comprobante: {comprobante}"
            if archivos_eliminados > 0:
                detalles += f" (se eliminaron {archivos_eliminados} archivo(s) PDF)"
            self._registrar_auditoria("Eliminó ingreso", "Contabilidad", "Éxito", detalles)
        elif tipo == 'egresos':
            descripcion = registro.get('descripcion', '')
            self._registrar_auditoria(
                "Eliminó egreso", "Contabilidad", "Éxito",
                f"ID {registro_id}, descripción: {descripcion}"
            )
        elif tipo == 'novedades':
            nombre = registro.get('nombre', '')
            cc = registro.get('cc', '')
            self._registrar_auditoria(
                "Eliminó novedad", "Contabilidad", "Éxito",
                f"ID {registro_id}, afiliado: {nombre} (CC: {cc})"
            )

        if tipo == 'ingresos' and archivos_eliminados > 0:
            messagebox.showinfo("Éxito", f"Registro de {tipo} y {archivos_eliminados} archivo(s) de factura eliminados correctamente")
        else:
            self.mostrar_toast(f"Registro de {tipo} eliminado correctamente")

        self.reproducir_sonido("eliminar")   # <-- SONIDO ELIMINAR
                
    def exportar_a_excel(self):
        """Exporta los datos de retiros a un archivo Excel en la carpeta BaseRetiros"""
        try:
            # Verificar e instalar openpyxl si no está disponible
            try:
                import openpyxl
            except ImportError:
                if messagebox.askyesno("Dependencia faltante", 
                                    "El módulo 'openpyxl' es requerido pero no está instalado. ¿Instalarlo ahora?"):
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl"])
                    import openpyxl
                else:
                    return

            if not self.retiros_data:
                messagebox.showerror("Error", "No hay datos para exportar")
                return

            # Crear directorio BaseRetiros si no existe
            base_retiros_path = os.path.join(BASE_PATH, "BaseRetiros")
            os.makedirs(base_retiros_path, exist_ok=True)

            # Definir ruta completa del archivo Excel
            file_path = os.path.join(base_retiros_path, f"Retiros{datetime.now().strftime('%m-%Y')}.xlsx")

            # Exportar usando openpyxl como motor
            df = pd.DataFrame(self.retiros_data)
            
            # Reordenar columnas para que fecha_retiro aparezca al final
            if 'fecha_retiro' in df.columns:
                columnas = [col for col in df.columns if col != 'fecha_retiro'] + ['fecha_retiro']
                df = df[columnas]
            
            df.to_excel(file_path, index=False, engine='openpyxl')

            # Confirmación
            if messagebox.askyesno("Éxito", f"Archivo guardado en:\n{file_path}\n\n¿Abrir carpeta?"):
                os.startfile(base_retiros_path)

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar:\n{str(e)}")
            
        # ======================
        # Gestión de Usuarios
        # ======================
    def gestion_usuarios(self):
        if self.user_role not in ("Administrativo", "Auxiliar"):
            messagebox.showerror("Error", "No tiene permisos para importar afiliados.")
            return

        ventana = Toplevel(self.root)
        ventana.title("Administrar Usuarios")
        ventana.geometry("600x450")
        self.centrar_ventana(ventana, 600, 450) 
        ventana.resizable(False, False)

        # Frame principal con padding
        main_frame = ttk.Frame(ventana, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Título
        ttk.Label(main_frame, text="Gestión de Usuarios", style='Title.TLabel').pack(pady=(0, 10))

        # Frame para la tabla (ocupa la mayor parte)
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview
        columns = ("Usuario", "Rol")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        tree.column("Usuario", width=250, anchor=tk.W)
        tree.column("Rol", width=250, anchor=tk.W)
        tree.heading("Usuario", text="Usuario")
        tree.heading("Rol", text="Rol")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Cargar lista de usuarios
        self.cargar_lista_usuarios(tree)

        # --- Frame para los botones (abajo) ---
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))   # separación superior

        # Botones alineados a la izquierda
        ttk.Button(btn_frame, text="➕ Agregar", 
                command=lambda: self.agregar_usuario(ventana, tree)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="✏️ Editar", 
                command=lambda: self.editar_usuario(ventana, tree)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="❌ Eliminar", 
                command=lambda: self.eliminar_usuario(ventana, tree)).pack(side=tk.LEFT, padx=5)

        # Botón Cerrar alineado a la derecha
        ttk.Button(btn_frame, text="Cerrar", command=ventana.destroy).pack(side=tk.RIGHT, padx=5)

    def cargar_lista_usuarios(self, tree):
        """Carga todos los usuarios en el Treeview."""
        for item in tree.get_children():
            tree.delete(item)
        usuarios = self.db.get_all_users()
        for u in usuarios:
            tree.insert("", tk.END, values=(u['username'], u['role']))

    def agregar_usuario(self, parent, tree):
        """Muestra un diálogo para agregar un nuevo usuario."""
        parent.withdraw()
        dialogo = Toplevel(parent)
        dialogo.title("Agregar Usuario")
        dialogo.geometry("350x250")
        self.centrar_ventana(dialogo, 350, 250)
        dialogo.resizable(False, False)

        ttk.Label(dialogo, text="Nuevo Usuario", style='Title.TLabel').pack(pady=10)

        frame = ttk.Frame(dialogo, padding=10)
        frame.pack(fill=tk.X)

        # Campos
        ttk.Label(frame, text="Usuario:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        username_var = tk.StringVar()
        ttk.Entry(frame, textvariable=username_var).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(frame, text="Contraseña:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        password_var = tk.StringVar()
        ttk.Entry(frame, textvariable=password_var, show="*").grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(frame, text="Rol:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        role_var = tk.StringVar(value="Auxiliar")
        ttk.Combobox(frame, textvariable=role_var, values=["Administrativo", "Auxiliar"], 
                     state="readonly").grid(row=2, column=1, padx=5, pady=5)

        def guardar():
            username = username_var.get().strip()
            password = password_var.get().strip()
            role = role_var.get()
            if not username or not password:
                messagebox.showerror("Error", "Usuario y contraseña son obligatorios")
                return
            try:
                self.db.add_user(username, password, role)
                self.cargar_lista_usuarios(tree)
                self._registrar_auditoria("Agregó usuario", "Usuarios", "Éxito",
                                        f"Usuario {username}")
                dialogo.destroy()
                self.mostrar_toast("Usuario agregado correctamente")
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "El nombre de usuario ya existe")

        btn_frame = ttk.Frame(dialogo)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Cancelar", command=dialogo.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Guardar", command=guardar).pack(side=tk.LEFT, padx=5)

    def editar_usuario(self, parent, tree):
        """Muestra un diálogo para editar la contraseña y rol de un usuario seleccionado."""
        selected = tree.selection()
        if not selected:
            messagebox.showerror("Error", "Seleccione un usuario para editar")
            return
        item = tree.item(selected[0])
        username_actual = item['values'][0]
        rol_actual = item['values'][1]

        parent.withdraw()
        dialogo = Toplevel(parent)
        dialogo.title("Editar Usuario")
        dialogo.geometry("350x250")
        self.centrar_ventana(dialogo, 350, 250) 
        dialogo.resizable(False, False)

        ttk.Label(dialogo, text=f"Editar: {username_actual}", style='Title.TLabel').pack(pady=10)

        frame = ttk.Frame(dialogo, padding=10)
        frame.pack(fill=tk.X)

        ttk.Label(frame, text="Usuario:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Label(frame, text=username_actual).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Label(frame, text="Nueva Contraseña:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        password_var = tk.StringVar()
        ttk.Entry(frame, textvariable=password_var, show="*").grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(frame, text="Nuevo Rol:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        role_var = tk.StringVar(value=rol_actual)
        ttk.Combobox(frame, textvariable=role_var, values=["Administrativo", "Auxiliar"], 
                     state="readonly").grid(row=2, column=1, padx=5, pady=5)

        def guardar():
            nueva_password = password_var.get().strip()
            nuevo_rol = role_var.get()
            # Si no se proporciona contraseña, mantenemos la anterior (requerimos consultar)
            if not nueva_password:
                # Obtener la contraseña actual de la base de datos
                usuarios = self.db.get_all_users()
                for u in usuarios:
                    if u['username'] == username_actual:
                        nueva_password = u['password']
                        break
            try:
                self.db.update_user(username_actual, nueva_password, nuevo_rol)
                self.cargar_lista_usuarios(tree)
                self._registrar_auditoria("Editó usuario", "Usuarios", "Éxito",
                                        f"Usuario {username_actual}")
                dialogo.destroy()
                self.mostrar_toast("Usuario actualizado correctamente")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo actualizar: {str(e)}")

        btn_frame = ttk.Frame(dialogo)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Cancelar", command=dialogo.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Guardar", command=guardar).pack(side=tk.LEFT, padx=5)

    def eliminar_usuario(self, parent, tree):
        """Elimina el usuario seleccionado (con confirmación)."""
        selected = tree.selection()
        if not selected:
            messagebox.showerror("Error", "Seleccione un usuario para eliminar")
            return
        item = tree.item(selected[0])
        username = item['values'][0]

        # No permitir eliminar al usuario actual
        if username == self.db.get_user(self.root.winfo_toplevel().title().split("-")[1].strip()):  # truco para obtener usuario actual
            # Mejor obtenemos el usuario actual de la sesión. Lo guardamos en self.current_user al iniciar sesión.
            # Como no lo tenemos, usamos un método más seguro: no eliminar "admin" por defecto.
            if username == "MyAdmin":
                messagebox.showerror("Error", "No se puede eliminar al usuario administrador principal")
                return

        if messagebox.askyesno("Confirmar", f"¿Está seguro de eliminar al usuario '{username}'?"):
            try:
                self.db.delete_user(username)
                self.cargar_lista_usuarios(tree)
                self._registrar_auditoria("Eliminó usuario", "Usuarios", "Éxito",
                                        f"Usuario {username}")
                self.mostrar_toast("Usuario eliminado correctamente")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar: {str(e)}")
                
    def centrar_ventana(self, window, width, height):
        """Centra una ventana en la pantalla (tamaño fijo)"""
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        window.geometry(f'{width}x{height}+{x}+{y}')
        
    def deshabilitar_botones_ventana(self, window):
        """
        Deshabilita (pone en gris) los botones de minimizar y maximizar 
        en Windows, manteniéndolos visibles pero inactivos.
        """
        try:
            import ctypes
            from ctypes import wintypes
            
            # Obtener el HWND (identificador de ventana de Windows)
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            if not hwnd:
                hwnd = window.winfo_id()
                
            # Estilos de ventana de Windows
            GWL_STYLE = -16
            WS_MINIMIZEBOX = 0x00020000
            WS_MAXIMIZEBOX = 0x00010000
            
            # Obtener el estilo actual
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
            
            # Quitar (desactivar) los estilos de minimizar y maximizar
            style &= ~WS_MINIMIZEBOX
            style &= ~WS_MAXIMIZEBOX
            
            # Aplicar el nuevo estilo
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)
            
            # Forzar el redibujado del marco de la ventana para que los cambios se vean
            SWP_FRAMECHANGED = 0x0020
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                            SWP_NOMOVE | SWP_NOSIZE | SWP_FRAMECHANGED)
        except Exception as e:
            # Si falla (ej: no está en Windows), simplemente se ignora
            # y la ventana solo tendrá deshabilitado el botón de maximizar (por el resizable)
            pass
        
    def actualizar_monitoreo_afiliado(self, cc):
        # Buscar el afiliado en activos o retirados
        afiliado = None
        for a in self.data:
            if a['cc'] == cc:
                afiliado = a
                break
        if not afiliado:
            for a in self.retiros_data:
                if a['cc'] == cc:
                    afiliado = a
                    break
        if not afiliado:
            return

        hoy = datetime.now().date()
        fecha_pago_str = afiliado.get('fecha_pago')
        if not fecha_pago_str:
            return

        try:
            fecha_pago = datetime.strptime(fecha_pago_str, "%Y-%m-%d").date()
            fecha_vencimiento = fecha_pago + timedelta(days=30)
            dias_mora = (hoy - fecha_vencimiento).days
            dias_mora = max(0, dias_mora)

            umbrales = self.config.get('monitoreo_umbrales', {})
            activo_hasta = umbrales.get('activo_hasta_dias', 3)
            proximo_suspender = umbrales.get('proximo_suspender_dias', 5)
            suspendido = umbrales.get('suspendido_dias', 7)

            if hoy < fecha_vencimiento:
                estado = 'Activo'
            elif 0 < dias_mora <= activo_hasta:
                estado = 'Activo (Próximo a vencer)'
            elif activo_hasta < dias_mora <= proximo_suspender:
                estado = 'Próximo a Suspender'
            elif proximo_suspender < dias_mora <= suspendido:
                estado = 'Suspendido'
            else:
                estado = 'Retirado'
        except:
            return

        # Buscar o crear registro de monitoreo
        monitoreo = None
        for m in self.contabilidad_data['monitoreo']:
            if m['cc'] == cc:
                monitoreo = m
                break
        if not monitoreo:
            monitoreo = {
                'cc': cc,
                'nombre': afiliado['nombre'],
                'eps': afiliado.get('eps', ''),
                'descripcion': 'Pago de servicios de salud',
                'dias_mora': dias_mora,
                'estado': estado,
                'fecha_ultimo_pago': fecha_pago_str,
                'fecha_registro_estado': hoy.strftime("%Y-%m-%d")
            }
            self.db.add_monitoreo(monitoreo)
            self.contabilidad_data['monitoreo'].append(monitoreo)
        else:
            monitoreo['dias_mora'] = dias_mora
            monitoreo['estado'] = estado
            monitoreo['fecha_ultimo_pago'] = fecha_pago_str
            monitoreo['fecha_registro_estado'] = hoy.strftime("%Y-%m-%d")
            self.db.update_monitoreo(cc, monitoreo)

    def registrar_pago_completo(self, afiliados, mes_pago, valor, metodo, fecha):
        """
        Registra el pago para una lista de afiliados:
        - Actualiza datos del afiliado
        - Crea ingreso contable
        - Actualiza monitoreo
        - Refresca tablas
        """
        if not afiliados:
            return

        # Generar número de factura base (se usa para cada afiliado)
        num_factura_base = self.obtener_numero_factura(afiliados[0]['cc'])

        for idx, afiliado in enumerate(afiliados):
            cc = afiliado['cc']

            # Actualizar datos del afiliado en memoria y BD
            for i, reg in enumerate(self.data):
                if reg['cc'] == cc:
                    self.data[i]['mes_pago'] = mes_pago
                    self.data[i]['valor_pagado'] = float(valor)
                    self.data[i]['metodo_pago'] = metodo
                    self.data[i]['fecha_pago'] = fecha
                    self.db.update_afiliado(cc, self.data[i])
                    break

            # Registrar ingreso en contabilidad
            num_factura = f"{num_factura_base}-{idx+1}" if len(afiliados) > 1 else num_factura_base
            ingreso_data = {
                "fecha": fecha,
                "cc": cc,
                "nombre": afiliado['nombre'],
                "servicio": "Pago de servicios de salud",
                "valor": float(valor),
                "metodo_pago": metodo,
                "comprobante": f"Factura {num_factura}"
            }
            new_id = self.db.add_ingreso(ingreso_data)
            ingreso_data['id'] = new_id
            self.contabilidad_data['ingresos'].append(ingreso_data)

            # Actualizar monitoreo para este afiliado
            self.actualizar_monitoreo_afiliado(cc)

        # Refrescar todas las tablas afectadas
        self.update_afiliados_table()
        self.update_ingresos_table()
        self.update_monitoreo_table()
        self.calcular_totales_contabilidad()
        self.hacer_caja()   # para que la caja muestre el movimiento del día
            
    def mostrar_ventana_seleccion_masiva(self, tipo):
        """
        Muestra una ventana con tabla para seleccionar múltiples afiliados.
        tipo: 'retirar', 'eliminar' (usa self.data) o 'reactivar' (usa self.retiros_data)
        Retorna: lista de índices seleccionados, o None si se cancela.
        """
        # Determinar la lista de origen y el título
        if tipo in ('retirar', 'eliminar'):
            lista_origen = self.data
            titulo = f"Seleccionar afiliados para {tipo.capitalize()}"
            columnas = ("Selección", "CC", "Nombre", "Mes Pago", "Valor", "Medio Pago", "Fecha Pago")
            mostrar_retiro = False
        elif tipo == 'reactivar':
            lista_origen = self.retiros_data
            titulo = "Seleccionar afiliados para Reactivar"
            columnas = ("Selección", "CC", "Nombre", "Mes Pago", "Valor", "Medio Pago", "Fecha Pago", "Fecha Retiro")
            mostrar_retiro = True
        else:
            return None

        if not lista_origen:
            messagebox.showinfo("Información", f"No hay afiliados para {tipo}.")
            return None

        ventana = Toplevel(self.root)
        ventana.title(titulo)
        ventana.geometry("1100x500")
        self.centrar_ventana(ventana, 1100, 500)
        ventana.resizable(True, True)

        # Frame principal
        main_frame = ttk.Frame(ventana, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Título
        ttk.Label(main_frame, text=titulo, style='Title.TLabel').pack(pady=(0, 10))

        # Barra de búsqueda
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(search_frame, text="Buscar (CC o Nombre):").pack(side=tk.LEFT, padx=5)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=50)
        search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Frame para la tabla
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        # Crear Treeview con scrollbar
        tree = ttk.Treeview(table_frame, columns=columnas, show="headings", height=12)
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        # Configurar columnas
        anchos = {
            "Selección": 70,
            "CC": 100,
            "Nombre": 180,
            "Mes Pago": 90,
            "Valor": 100,
            "Medio Pago": 100,
            "Fecha Pago": 100,
            "Fecha Retiro": 100
        }
        for col in columnas:
            tree.heading(col, text=col)
            tree.column(col, width=anchos.get(col, 120), anchor=tk.CENTER)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Diccionario para almacenar el estado de selección (por CC)
        seleccion_estado = {}  # {cc: bool}

        # Función para actualizar la tabla según el filtro
        def actualizar_tabla(filtro=""):
            # Limpiar treeview
            for item in tree.get_children():
                tree.delete(item)

            filtro_lower = filtro.lower().strip()
            for idx, reg in enumerate(lista_origen):
                cc = reg['cc']
                nombre = reg['nombre']
                # Aplicar filtro
                if filtro_lower and filtro_lower not in cc.lower() and filtro_lower not in nombre.lower():
                    continue

                # Asegurar que el CC esté en el diccionario de selección
                if cc not in seleccion_estado:
                    seleccion_estado[cc] = False

                # Determinar el símbolo de selección
                seleccionado = "✔" if seleccion_estado[cc] else ""

                # Formatear valor
                valor = float(reg.get('valor_pagado', 0))
                valor_str = f"${valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

                # Construir fila según el tipo, aplicando formateo a cada campo
                if mostrar_retiro:
                    fila = (
                        seleccionado,
                        self._formatear_valor_tabla(cc),
                        self._formatear_valor_tabla(nombre),
                        self._formatear_valor_tabla(reg.get('mes_pago', '')),
                        valor_str,  # ya formateado con moneda
                        self._formatear_valor_tabla(reg.get('metodo_pago', '')),
                        self._formatear_valor_tabla(reg.get('fecha_pago', '')),
                        self._formatear_valor_tabla(reg.get('fecha_retiro', ''))
                    )
                else:
                    fila = (
                        seleccionado,
                        self._formatear_valor_tabla(cc),
                        self._formatear_valor_tabla(nombre),
                        self._formatear_valor_tabla(reg.get('mes_pago', '')),
                        valor_str,
                        self._formatear_valor_tabla(reg.get('metodo_pago', '')),
                        self._formatear_valor_tabla(reg.get('fecha_pago', ''))
                    )

                # Insertar fila, guardando el índice original en la etiqueta (iid)
                tree.insert("", tk.END, iid=str(idx), values=fila)

        # Función para alternar selección de una fila al hacer clic en la columna "Selección"
        def on_tree_click(event):
            region = tree.identify_region(event.x, event.y)
            if region != "cell":
                return
            col = tree.identify_column(event.x)
            if col != "#1":  # Columna "Selección" es la primera
                return
            item = tree.identify_row(event.y)
            if not item:
                return
            idx = int(item)
            if idx < len(lista_origen):
                cc = lista_origen[idx]['cc']
                # Alternar estado
                seleccion_estado[cc] = not seleccion_estado[cc]
                # Actualizar la celda de selección en el treeview
                nuevo_valor = "✔" if seleccion_estado[cc] else ""
                tree.set(item, column="Selección", value=nuevo_valor)

        tree.bind("<Button-1>", on_tree_click)

        # Función para actualizar la tabla al cambiar la búsqueda
        def on_search_change(*args):
            actualizar_tabla(search_var.get())

        search_var.trace("w", on_search_change)

        # Inicializar tabla sin filtro
        actualizar_tabla("")

        # Botones de selección masiva
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        def seleccionar_todos_visibles():
            # Obtener los items actuales (visibles)
            items = tree.get_children()
            for item in items:
                idx = int(item)
                if idx < len(lista_origen):
                    cc = lista_origen[idx]['cc']
                    seleccion_estado[cc] = True
                    tree.set(item, column="Selección", value="✔")

        def deseleccionar_todos_visibles():
            items = tree.get_children()
            for item in items:
                idx = int(item)
                if idx < len(lista_origen):
                    cc = lista_origen[idx]['cc']
                    seleccion_estado[cc] = False
                    tree.set(item, column="Selección", value="")

        ttk.Button(btn_frame, text="Seleccionar todos", command=seleccionar_todos_visibles).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Deseleccionar todos", command=deseleccionar_todos_visibles).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=ventana.destroy).pack(side=tk.RIGHT, padx=5)

        resultado = []

        def aceptar():
            # Recorrer todos los registros y obtener los índices seleccionados
            indices_seleccionados = []
            for idx, reg in enumerate(lista_origen):
                cc = reg['cc']
                if seleccion_estado.get(cc, False):
                    indices_seleccionados.append(idx)
            if not indices_seleccionados:
                messagebox.showwarning("Selección vacía", "No ha seleccionado ningún afiliado.")
                return
            resultado.extend(indices_seleccionados)
            ventana.destroy()

        ttk.Button(btn_frame, text="Aceptar", command=aceptar).pack(side=tk.RIGHT, padx=5)

        # Esperar a que la ventana se cierre
        ventana.wait_window()
        return resultado if resultado else None

    def get_active_toplevel(self):
        """Devuelve la ventana Toplevel que tiene el foco, o None si es la principal."""
        focused = self.root.focus_get()
        if focused is None:
            return None
        top = focused.winfo_toplevel()
        if top == self.root:
            return None
        return top

    def is_main_window_focused(self):
        """Retorna True si la ventana principal está enfocada (sin Toplevel hijo activo)."""
        return self.get_active_toplevel() is None

    def setup_shortcuts(self):
        """Configura todos los atajos de teclado."""
        root = self.root

        # ESC: cierra ventana emergente o doble clic para salir
        root.bind_all('<Escape>', self.shortcut_escape)

        # Ctrl+N: nuevo afiliado
        root.bind_all('<Control-n>', self.shortcut_nuevo_afiliado)
        root.bind_all('<Control-N>', self.shortcut_nuevo_afiliado)

        # Ctrl+E: editar afiliado seleccionado
        root.bind_all('<Control-e>', self.shortcut_editar_afiliado)
        root.bind_all('<Control-E>', self.shortcut_editar_afiliado)

        # Ctrl+R: retirar afiliado seleccionado
        root.bind_all('<Control-r>', self.shortcut_retirar_afiliado)
        root.bind_all('<Control-R>', self.shortcut_retirar_afiliado)

        # Ctrl+D: eliminar afiliado seleccionado
        root.bind_all('<Control-d>', self.shortcut_eliminar_afiliado)
        root.bind_all('<Control-D>', self.shortcut_eliminar_afiliado)

        # Ctrl+F: enfocar búsqueda de afiliados
        root.bind_all('<Control-f>', self.shortcut_buscar_afiliado)
        root.bind_all('<Control-F>', self.shortcut_buscar_afiliado)

        # Ctrl+B: búsqueda global
        root.bind_all('<Control-b>', self.shortcut_buscar_global)
        root.bind_all('<Control-B>', self.shortcut_buscar_global)

        # Ctrl+C: copiar cédula
        root.bind_all('<Control-c>', self.shortcut_copiar)
        root.bind_all('<Control-C>', self.shortcut_copiar)

        # Ctrl+Q: cerrar sesión
        root.bind_all('<Control-q>', self.shortcut_cerrar_sesion)
        root.bind_all('<Control-Q>', self.shortcut_cerrar_sesion)

        # Ctrl+S: copia de seguridad
        root.bind_all('<Control-s>', self.shortcut_copia_seguridad)
        root.bind_all('<Control-S>', self.shortcut_copia_seguridad)
        
        # F1: abrir ayuda
        root.bind_all('<F1>', self.shortcut_ayuda)

        # F5: Refrescar el sistema
        root.bind_all('<F5>', self.shortcut_refrescar)

        # Ctrl+Shift+P: Botón de pánico (silencioso)
        root.bind_all('<Control-Shift-P>', self.shortcut_panico)
        root.bind_all('<Control-Shift-p>', self.shortcut_panico)

        # Ctrl+Shift+W: WIPE TOTAL (destructivo)
        root.bind_all('<Control-Shift-W>', self.shortcut_panico_wipe)
        root.bind_all('<Control-Shift-w>', self.shortcut_panico_wipe)
        
    def shortcut_escape(self, event):

        toplevel = self.get_active_toplevel()
        if toplevel:
            # Cerrar la ventana emergente sin confirmación
            toplevel.destroy()
            # Reiniciamos el contador para no interferir con el doble clic
            self.last_escape_time = 0
            self.escape_pending = False
            return

        # No hay ventana emergente: manejar doble clic para salir
        import time
        now = time.time()
        if self.escape_pending and (now - self.last_escape_time) <= 0.3:
            # Doble clic detectado: preguntar si salir
            if messagebox.askyesno("Salir", "¿Desea salir del programa?"):
                self.root.quit()
            # Reiniciar estado
            self.escape_pending = False
            self.last_escape_time = 0
        else:
            # Primera pulsación o ha pasado el tiempo: activar pendiente
            self.escape_pending = True
            self.last_escape_time = now

    def shortcut_refrescar(self, event):
        if self.is_main_window_focused():
            self.refrescar_sistema()

    def shortcut_nuevo_afiliado(self, event):
        if self.is_main_window_focused():
            self.show_afiliado_form()

    def shortcut_editar_afiliado(self, event):
        if not self.is_main_window_focused():
            return
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Editar", "Seleccione un afiliado en la tabla de activos.")
            return
        # Verificar que la pestaña de afiliados esté activa (comparando por texto, no por índice)
        tab_actual = self.notebook.tab(self.notebook.select(), "text")
        if "Afiliados Activos" not in tab_actual:
            messagebox.showinfo("Editar", "Cambie a la pestaña 'Afiliados Activos'.")
            return
        index = self.tree.index(selected[0])
        self.show_afiliado_form(edit_mode=True, index=index)

    def shortcut_retirar_afiliado(self, event):
        if not self.is_main_window_focused():
            return
        if self.user_role != "Administrativo":
            messagebox.showerror("Permiso denegado", "Solo el administrador puede retirar.")
            return
        tab_actual = self.notebook.tab(self.notebook.select(), "text")
        if "Afiliados Activos" not in tab_actual:
            messagebox.showinfo("Retirar", "Cambie a la pestaña 'Afiliados Activos'.")
            return
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Retirar", "Seleccione uno o más afiliados.")
            return
        indices = [self.tree.index(item) for item in selected]
        self.retirar_afiliados(indices)

    def shortcut_eliminar_afiliado(self, event):
        if not self.is_main_window_focused():
            return
        if self.user_role != "Administrativo":
            messagebox.showerror("Permiso denegado", "Solo el administrador puede eliminar.")
            return
        tab_actual = self.notebook.tab(self.notebook.select(), "text")
        if "Afiliados Activos" not in tab_actual:
            messagebox.showinfo("Eliminar", "Cambie a la pestaña 'Afiliados Activos'.")
            return
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Eliminar", "Seleccione uno o más afiliados.")
            return
        indices = [self.tree.index(item) for item in selected]
        self.eliminar_afiliados_seleccionados(indices)

    def shortcut_buscar_afiliado(self, event):
        if not self.is_main_window_focused():
            return

        for child in self.root.winfo_children():
            if isinstance(child, ttk.Frame):
                # Recorremos recursivamente
                entry = self.find_entry_by_variable(child, self.busqueda_var)
                if entry:
                    entry.focus_set()
                    entry.select_range(0, tk.END)
                    return
        # Si no se encuentra, intentamos en la pestaña actual
        current_tab = self.notebook.select()
        if current_tab:
            tab = self.notebook.nametowidget(current_tab)
            entry = self.find_entry_by_variable(tab, self.busqueda_var)
            if entry:
                entry.focus_set()
                entry.select_range(0, tk.END)

    def find_entry_by_variable(self, widget, variable):
        """Busca recursivamente un Entry cuyo textvariable sea variable."""
        if isinstance(widget, ttk.Entry) and widget['textvariable'] == variable:
            return widget
        for child in widget.winfo_children():
            result = self.find_entry_by_variable(child, variable)
            if result:
                return result
        return None

    def shortcut_buscar_global(self, event):
        if not self.is_main_window_focused():
            return
        self.abrir_busqueda_global()

    def shortcut_copiar(self, event):
        focused = self.root.focus_get()
        if isinstance(focused, ttk.Treeview):
            selected = focused.selection()
            if selected:
                # Asumimos que la primera columna es la cédula
                cc = focused.item(selected[0], 'values')[0]
                self.root.clipboard_clear()
                self.root.clipboard_append(cc)
                self.root.update()

    def shortcut_copia_seguridad(self, event):
        if not self.is_main_window_focused():
            return
        if self.user_role != "Administrativo":
            messagebox.showerror("Permiso denegado", "Solo el administrador puede crear copias de seguridad.")
            return
        self.crear_copia_seguridad()

    def shortcut_cerrar_sesion(self, event):
        if self.is_main_window_focused():
            self.cerrar_sesion()

    def shortcut_ayuda(self, event):
        self.mostrar_ayuda()

    def shortcut_panico(self, event):
        """Activa el botón de pánico sin feedback visible."""
        self.activar_boton_panico()
        return "break"   # Evita que se propague
    
    def shortcut_panico_wipe(self, event):
        self.activar_panico_wipe()
        return "break"

    def eliminar_afiliados_seleccionados(self, indices):
        """Elimina los afiliados en los índices dados (de self.data)."""
        if self.user_role != "Administrativo":
            messagebox.showerror("Error", "No tiene permisos para eliminar afiliados")
            return

        if not indices:
            return

        if not self.validar_password():
            return

        if not messagebox.askyesno("Confirmar eliminación masiva",
                                    f"¿Está seguro de eliminar permanentemente a {len(indices)} afiliados?\n\n"
                                    "Esta acción también eliminará sus registros de monitoreo y no se puede deshacer.",
                                    icon=messagebox.WARNING):
            return

        for index in sorted(indices, reverse=True):
            if index < len(self.data):
                registro = self.data[index]
                cc_afiliado = registro['cc']
                self.db.delete_afiliado(cc_afiliado)
                self.db.delete_monitoreo(cc_afiliado)
                del self.data[index]
                self.contabilidad_data['monitoreo'] = [
                    m for m in self.contabilidad_data['monitoreo']
                    if m['cc'] != cc_afiliado
                ]

        self.update_afiliados_table()
        self.update_monitoreo_table()
        messagebox.showinfo("Éxito", f"{len(indices)} afiliados eliminados permanentemente")

    def abrir_busqueda_global(self):
        """Abre una ventana con todos los afiliados para búsqueda y acceso rápido."""
        ventana = Toplevel(self.root)
        ventana.title("Búsqueda Global")
        ventana.geometry("920x550")
        self.centrar_ventana(ventana, 920, 550)
        ventana.resizable(True, True)

        main_frame = ttk.Frame(ventana, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Búsqueda Global - Todos los afiliados", style='Title.TLabel').pack(pady=(0,10))

        # ----- Campo de búsqueda (sin el botón QR) -----
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0,10))
        ttk.Label(search_frame, text="Buscar:").pack(side=tk.LEFT, padx=5)
        search_var = tk.StringVar()
        entry = ttk.Entry(search_frame, textvariable=search_var, width=50)
        entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        entry.focus_set()

        # ----- Treeview con scroll -----
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("CC", "Nombre", "Celular", "EPS", "ARL", "Pensión", "Caja", "Estado", "Fecha Pago")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor=tk.W if col=="Nombre" else tk.CENTER)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ----- Cargar datos (sin cambios) -----
        todos = self.data + self.retiros_data
        if hasattr(self, 'archivados_data'):
            todos += self.archivados_data
        else:
            self.archivados_data = self.db.get_archivados()
            todos += self.archivados_data

        ventana.tree = tree
        ventana.todos = todos

        def actualizar(filtro=""):
            for item in tree.get_children():
                tree.delete(item)
            filtro_lower = filtro.lower().strip()
            for reg in todos:
                if filtro_lower:
                    if (filtro_lower not in reg['cc'].lower() and
                        filtro_lower not in reg['nombre'].lower() and
                        filtro_lower not in reg.get('eps', '').lower() and
                        filtro_lower not in reg.get('arl', '').lower()):
                        continue
                if reg.get('fecha_retiro') is None:
                    estado = "Activo"
                else:
                    estado = "Retirado"
                if 'fecha_archivo' in reg and reg.get('fecha_archivo'):
                    estado = "Archivado"

                tree.insert("", tk.END, values=(
                    reg['cc'],
                    reg['nombre'],
                    reg.get('celular', ''),
                    reg.get('eps', ''),
                    reg.get('arl', ''),
                    reg.get('pension', ''),
                    reg.get('caja_compensacion', ''),
                    estado,
                    reg.get('fecha_pago', '')
                ))

        search_var.trace("w", lambda *args: actualizar(search_var.get()))
        actualizar("")

        def on_double_click(event):
            selected = tree.selection()
            if not selected:
                return
            item = selected[0]
            cc = tree.item(item, 'values')[0]   # La cédula está en la primera columna
            # Reutilizamos la función que ya busca y abre los detalles
            self._buscar_y_mostrar_detalles_global(cc, ventana, tree)
 
        tree.bind("<Double-1>", on_double_click)

        # ===== NUEVO BOTÓN QR EN LA PARTE INFERIOR CENTRADO =====
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

        btn_qr = ttk.Button(bottom_frame, text="📷 Escanear QR",
                            command=lambda: self.escanear_qr_global(ventana, tree))
        btn_qr.pack(anchor='center')   # centrado horizontalmente

        # Botón Cerrar (opcional: también se puede mover aquí, pero se mantiene abajo)
        ttk.Button(main_frame, text="Cerrar", command=ventana.destroy).pack(pady=5)
        
    def escanear_qr_global(self, ventana_global, tree_global):
        """Abre el escáner QR para buscar un afiliado en la búsqueda global usando la cámara del teléfono."""
        try:
            import cv2
            from pyzbar.pyzbar import decode
            from PIL import Image, ImageTk
        except ImportError as e:
            messagebox.showerror("Error", f"Falta dependencia: {str(e)}\nInstale opencv-python y pyzbar")
            return

        # Obtener la URL de la cámara desde la configuración
        camera_url = self.config.get('camera_ip_url', 'http://192.168.0.3:8080/video')

        # Verificar cámara IP
        cap = cv2.VideoCapture(camera_url)
        if not cap.isOpened():
            messagebox.showerror("Error", 
                f"No se pudo acceder a la cámara IP en:\n{camera_url}\n\n"
                "Verifique que el teléfono esté transmitiendo y ambos estén en la misma red.")
            return
        cap.release()

        # Crear ventana de escaneo
        scan_win = Toplevel(self.root)
        scan_win.title("Escanear QR - Búsqueda Global")
        scan_win.geometry("500x500")
        scan_win.resizable(False, False)
        self.centrar_ventana(scan_win, 500, 500)

        canvas = tk.Canvas(scan_win, width=480, height=360, bg='black')
        canvas.pack(pady=10)

        estado_label = ttk.Label(scan_win, text="Buscando código QR...", font=('Segoe UI', 11))
        estado_label.pack(pady=5)

        # Botón cancelar
        ttk.Button(scan_win, text="Cancelar", command=scan_win.destroy).pack(pady=10)

        # Conectar a la cámara IP
        cap = cv2.VideoCapture(camera_url)
        scanning = True

        def actualizar_frame():
            nonlocal scanning
            if not scanning:
                return
            ret, frame = cap.read()
            if not ret:
                estado_label.config(text="Error al leer la cámara", foreground='red')
                scan_win.after(500, actualizar_frame)
                return

            # Convertir a RGB para pyzbar
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            codigos = decode(pil_img)

            if codigos:
                cedula = codigos[0].data.decode('utf-8').strip()
                estado_label.config(text=f"✅ QR detectado: {cedula}", foreground='green')
                scan_win.update()

                # Detener escaneo
                scanning = False
                cap.release()
                scan_win.destroy()

                # Buscar el afiliado en todas las listas y mostrar detalles
                self._buscar_y_mostrar_detalles_global(cedula, ventana_global, tree_global)
                return

            # Mostrar frame
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            imgtk = ImageTk.PhotoImage(image=img)
            canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
            canvas.imgtk = imgtk

            scan_win.after(30, actualizar_frame)

        # Iniciar loop
        actualizar_frame()

        # Cerrar cámara al cerrar ventana
        def cerrar_scan():
            nonlocal scanning
            scanning = False
            cap.release()
            scan_win.destroy()
        scan_win.protocol("WM_DELETE_WINDOW", cerrar_scan)
        
    def _buscar_y_mostrar_detalles_global(self, cedula, ventana_global, tree_global):
        """Busca la cédula en todas las listas y abre los detalles del afiliado."""
        # Buscar en activos
        for i, af in enumerate(self.data):
            if af['cc'] == cedula:
                # Seleccionar en el treeview de activos y mostrar detalles
                for child in self.tree.get_children():
                    if self.tree.item(child, 'values')[0] == cedula:
                        self.tree.selection_set(child)
                        break
                ventana_global.destroy()
                self.mostrar_detalles_afiliado(None)
                return

        # Buscar en retirados
        for i, af in enumerate(self.retiros_data):
            if af['cc'] == cedula:
                for child in self.retiros_tree.get_children():
                    if self.retiros_tree.item(child, 'values')[0] == cedula:
                        self.retiros_tree.selection_set(child)
                        break
                ventana_global.destroy()
                self.mostrar_detalles_retirado(None)
                return

        # Buscar en archivados
        if hasattr(self, 'archivados_data'):
            for reg in self.archivados_data:
                if reg['cc'] == cedula:
                    # Usar el método que muestra detalles de archivado directamente
                    ventana_global.destroy()
                    self._mostrar_detalles_archivado_desde_datos(reg)
                    return

        # Si no se encuentra
        messagebox.showinfo("No encontrado", f"No se encontró ningún afiliado con la cédula {cedula}")

    def mostrar_detalles_archivado_global(self, cc):
        """Muestra los detalles de un afiliado archivado desde la búsqueda global."""
        # Obtener los datos del archivado
        if not hasattr(self, 'archivados_data'):
            self.archivados_data = self.db.get_archivados()
        
        registro = None
        for reg in self.archivados_data:
            if reg['cc'] == cc:
                registro = reg
                break
        
        if not registro:
            messagebox.showerror("Error", "No se encontraron datos del archivado.")
            return

        # Reutilizar la función existente para mostrar detalles
        # Pero necesitamos simular la selección en el treeview de archivados
        # Para que la función existente funcione, podemos seleccionar el elemento correspondiente
        
        # Buscar el elemento en el treeview de archivados
        if hasattr(self, 'archivados_tree'):
            for child in self.archivados_tree.get_children():
                if self.archivados_tree.item(child, 'values')[0] == cc:
                    self.archivados_tree.selection_set(child)
                    # Llamar al método existente
                    self.mostrar_detalles_archivado()
                    return
        
        # Si no se encontró en el treeview (porque no está cargado), usar el método alternativo
        self._mostrar_detalles_archivado_desde_datos(registro)

    def _mostrar_detalles_archivado_desde_datos(self, registro):
        """Muestra detalles de un archivado directamente desde los datos sin depender del treeview."""
        # Crear ventana de detalles
        ventana = Toplevel(self.root)
        ventana.title(f"Detalles del Archivado - {registro['nombre']}")
        ventana.geometry("750x450")
        self.centrar_ventana(ventana, 750, 450)
        ventana.resizable(False, False)
        ventana.transient(self.root)
        ventana.grab_set()

        # Frame principal con padding
        main_frame = ttk.Frame(ventana, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Título
        ttk.Label(main_frame, text=f"Información detallada de {registro['nombre']}",
                font=('Segoe UI', 14, 'bold')).pack(pady=(0, 15))

        # Contenedor de 2 columnas
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.BOTH, expand=True)
        top_frame.columnconfigure(0, weight=1)
        top_frame.columnconfigure(1, weight=1)

        # ====== GRUPO 1: DATOS (fila 0, columna 0) ======
        datos_frame = ttk.LabelFrame(top_frame, text="📋 Datos", padding=10)
        datos_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self._agregar_campo(datos_frame, "CC:", registro['cc'], 0)
        self._agregar_campo(datos_frame, "Nombre:", registro['nombre'], 1)
        self._agregar_campo(datos_frame, "Celular:", registro.get('celular', '-/-'), 2)

        # ====== GRUPO 2: SERVICIOS (fila 0, columna 1) ======
        servicios_frame = ttk.LabelFrame(top_frame, text="🛡️ Servicios", padding=10)
        servicios_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self._agregar_campo(servicios_frame, "EPS:", registro.get('eps', '-/-'), 0)
        self._agregar_campo(servicios_frame, "ARL:", registro.get('arl', '-/-'), 1)
        self._agregar_campo(servicios_frame, "Pensión:", registro.get('pension', '-/-'), 2)
        self._agregar_campo(servicios_frame, "Caja Comp.:", registro.get('caja_compensacion', '-/-'), 3)

        # ====== GRUPO 3: PAGOS (fila 1, columna 0) ======
        pagos_frame = ttk.LabelFrame(top_frame, text="💰 Pagos", padding=10)
        pagos_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self._agregar_campo(pagos_frame, "Mes Pago:", registro.get('mes_pago', '-/-'), 0)
        valor_str = f"${float(registro.get('valor_pagado', 0)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        self._agregar_campo(pagos_frame, "Valor:", valor_str, 1)
        self._agregar_campo(pagos_frame, "Método:", registro.get('metodo_pago', '-/-'), 2)
        self._agregar_campo(pagos_frame, "Fecha Pago:", registro.get('fecha_pago', '-/-'), 3)

        # ====== GRUPO 4: ESTADOS (fila 1, columna 1) ======
        estados_frame = ttk.LabelFrame(top_frame, text="📌 Estados", padding=10)
        estados_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        self._agregar_campo(estados_frame, "Fecha Retiro:", registro.get('fecha_retiro', '-/-'), 0)
        self._agregar_campo(estados_frame, "Motivo Retiro:", registro.get('motivo_retiro', '-/-'), 1)
        self._agregar_campo(estados_frame, "Fecha Archivo:", registro.get('fecha_archivo', '-/-'), 2)
        self._agregar_campo(estados_frame, "Usuario:", registro.get('usuario_archivo', '-/-'), 3)

        # ====== BOTONES ======
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        # Función para cerrar la ventana de detalles y ejecutar una acción
        def accion_y_cerrar(func):
            def wrapper():
                func()
                ventana.destroy()
            return wrapper

        ttk.Button(btn_frame, text="↩️ Restaurar",
                command=accion_y_cerrar(lambda: self.restaurar_archivado_individual(registro['cc']))).pack(side=tk.LEFT, padx=5)

        if self.user_role == "Administrativo":
            ttk.Button(btn_frame, text="❌ Eliminar Definitivamente",
                    command=accion_y_cerrar(lambda: self.eliminar_definitivo_archivado_individual(registro['cc']))).pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="Cerrar", command=ventana.destroy).pack(side=tk.RIGHT, padx=5)
                
    def crear_menu_contextual(self, tree, tipo):
        """
        Crea un menú emergente para el Treeview.
        tipo: 'activos' o 'retiros'
        """
        menu = tk.Menu(self.root, tearoff=0)
        
        # Opción Copiar (solo copia la cédula al portapapeles del sistema)
        menu.add_command(label="📋 Copiar", 
                        command=lambda: self.copiar_cedula(tree))
        
        if tipo == 'activos':

            menu.add_command(label="❌ Eliminar", 
                            command=lambda: self.eliminar_desde_menu_retiro(tree))
        
            menu.add_command(label="📋 Ver detalles", 
                            command=lambda: self.ver_detalles_desde_menu(tree, tipo))
        
        return menu

    def copiar_cedula(self, tree):
        """
        Copia la cédula del elemento seleccionado al portapapeles.
        No muestra ningún mensaje emergente.
        """
        selected = tree.selection()
        if not selected:
            return
        item = selected[0]
        cc = tree.item(item, 'values')[0]
        self.root.clipboard_clear()
        self.root.clipboard_append(cc)
        self.root.update()  # Mantener el contenido en el portapapeles

    def editar_afiliado_desde_menu(self, tree):
        """Abre edición del afiliado seleccionado."""
        selected = tree.selection()
        if not selected:
            return
        index = tree.index(selected[0])
        self.show_afiliado_form(edit_mode=True, index=index)

    def retirar_desde_menu(self, tree):
        """Retira el afiliado seleccionado."""
        selected = tree.selection()
        if not selected:
            return
        indices = [tree.index(item) for item in selected]
        self.retirar_afiliados(indices)

    def eliminar_desde_menu(self, tree):
        """Elimina el afiliado seleccionado."""
        selected = tree.selection()
        if not selected:
            return
        indices = [tree.index(item) for item in selected]
        self.eliminar_afiliados_seleccionados(indices)

    def reactivar_desde_menu(self, tree):
        """Reactivar afiliado desde la tabla de retiros."""
        selected = tree.selection()
        if not selected:
            return
        indices = [tree.index(item) for item in selected]
        self.reactivar_afiliados_desde_lista(indices)  # Necesitas este método o adaptar

    def eliminar_desde_menu_retiro(self, tree):
        """Eliminar afiliado desde la tabla de retiros."""
        selected = tree.selection()
        if not selected:
            return
        indices = [tree.index(item) for item in selected]
        # Reutilizamos la función de eliminar, pero usando la lista de retiros
        self.eliminar_retirados_seleccionados(indices)

    def ver_detalles_desde_menu(self, tree, tipo):
        """Muestra los detalles del afiliado seleccionado."""
        selected = tree.selection()
        if not selected:
            return
        item = selected[0]
        # Simulamos un doble clic en el ítem
        if tipo == 'activos':
            self.mostrar_detalles_afiliado(None)
        else:
            self.mostrar_detalles_retirado(None)

    def eliminar_retirados_seleccionados(self, indices):
        """Elimina permanentemente afiliados retirados seleccionados."""
        if not indices:
            return
        if not self.validar_password():
            return
        if not messagebox.askyesno("Confirmar eliminación", 
                                f"¿Eliminar definitivamente {len(indices)} retirados?"):
            return
        for index in sorted(indices, reverse=True):
            if index < len(self.retiros_data):
                reg = self.retiros_data[index]
                self.db.delete_afiliado(reg['cc'])
                self.db.delete_monitoreo(reg['cc'])
                del self.retiros_data[index]
        self.update_retiros_table()
        messagebox.showinfo("Éxito", f"{len(indices)} retirados eliminados.")

    def reactivar_afiliados_desde_lista(self, indices):
        if not indices:
            return
        if self.user_role != "Administrativo":
            messagebox.showerror("Error", "No tiene permisos para reactivar afiliados")
            return
        self.mostrar_formulario_reactivacion(indices)

    def mostrar_menu_contextual(self, event, tree, tipo):
        """Muestra el menú contextual en la posición del clic."""
        item = tree.identify_row(event.y)
        if item:
            tree.selection_set(item)
        else:
            return

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="📋 Copiar", command=lambda: self.copiar_cedula(tree))

        if tipo == 'activos':
            menu.add_command(label="✏️ Editar", command=lambda: self.editar_afiliado())
            menu.add_command(label="📦 Archivar", command=lambda: self.archivar_afiliado())
            if self.user_role == "Administrativo":
                menu.add_command(label="➖ Retirar", command=lambda: self.retirar_afiliados())
                menu.add_command(label="❌ Eliminar", command=lambda: self.eliminar_afiliado())
            menu.add_command(label="📋 Ver detalles", command=lambda: self.mostrar_detalles_afiliado(None))

        elif tipo == 'retiros':
            if self.user_role == "Administrativo":
                menu.add_command(label="♻️ Reactivar", command=lambda: self.reactivar_afiliados())
                menu.add_command(label="📦 Archivar", command=lambda: self.archivar_retirados())
                menu.add_command(label="❌ Eliminar Definitivamente", command=lambda: self.eliminar_definitivo_retirado())
            menu.add_command(label="📋 Ver detalles", command=lambda: self.mostrar_detalles_retirado(None))

        menu.post(event.x_root, event.y_root)
        
    def autocompletar_por_cedula(self):
        """
        Busca un afiliado por la cédula ingresada en el campo CC del formulario
        y si existe, carga todos sus datos en el formulario.
        """
        cc = self.cc_var.get().strip()
        if not cc:
            return
        cc_limpio = re.sub(r'[^0-9]', '', cc)
        if not cc_limpio:
            return
        afiliado = None
        for a in self.data:
            if a['cc'] == cc_limpio:
                afiliado = a
                break
        if not afiliado:
            for a in self.retiros_data:
                if a['cc'] == cc_limpio:
                    afiliado = a
                    break
        if afiliado:
            self.nombre_var.set(afiliado['nombre'])
            self.celular_var.set(afiliado.get('celular', ''))
            self.direccion_var.set(afiliado.get('direccion', ''))
            self.correo_var.set(afiliado.get('correo', ''))
            self.fecha_ingreso_var.set(afiliado.get('fecha_ingreso', ''))
            self.eps_var.set(afiliado.get('eps', '-/-') if afiliado.get('eps') else "-/-")
            self.arl_var.set(afiliado.get('arl', '-/-') if afiliado.get('arl') else "-/-")
            self.pension_var.set(afiliado.get('pension', '-/-') if afiliado.get('pension') else "-/-")
            self.caja_var.set(afiliado.get('caja_compensacion', '-/-') if afiliado.get('caja_compensacion') else "-/-")
            self.mes_pago_var.set(afiliado.get('mes_pago', ''))
            self.valor_pagado_var.set(afiliado.get('valor_pagado', ''))
            self.metodo_pago_var.set(afiliado.get('metodo_pago', ''))
            self.fecha_pago_var.set(afiliado.get('fecha_pago', ''))
            self.calcular_precio()
            # Actualizar beneficiarios si la pestaña está disponible
            if hasattr(self, 'beneficiarios_list'):
                self.beneficiarios_list = self.db.get_beneficiarios(cc_limpio)
                self.actualizar_tabla_beneficiarios()

    def activar_boton_panico(self):
        """Dispara la alerta de pánico de forma discreta."""
        if not self.config.get_panico_activo():
            return  # El pánico está desactivado, ignorar

        # --- Registrar en auditoría (queda silencioso) ---
        self._registrar_auditoria(
            "BOTÓN DE PÁNICO ACTIVADO",
            "Seguridad",
            "CRÍTICO",
            f"Usuario: {self.username} | Equipo: {os.environ.get('COMPUTERNAME', 'Desconocido')}"
        )

        # --- Recopilar info del contexto ---
        from datetime import datetime
        ahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        equipo = os.environ.get('COMPUTERNAME', 'Desconocido')
        usuario = self.username

        # Última ventana o tab activa
        try:
            tab_actual = self.notebook.tab(self.notebook.select(), "text")
        except:
            tab_actual = "Desconocido"

        # Último afiliado en pantalla (si aplica)
        ultimo_contexto = f"Sección: {tab_actual}"

        mensaje = (
            f"🚨 ALERTA DE PÁNICO — SaluPago\n\n"
            f"Usuario: {usuario}\n"
            f"Equipo: {equipo}\n"
            f"Fecha/Hora: {ahora}\n"
            f"Contexto: {ultimo_contexto}\n\n"
            f"⚠️ Requiere verificación inmediata."
        )

        # --- Enviar correo silencioso ---
        correo_destino = self.config.get_panico_correo()
        if correo_destino:
            try:
                self._enviar_gmail_texto(correo_destino, mensaje)
            except Exception as e:
                print(f"Error enviando correo de pánico: {e}")

        # --- Enviar WhatsApp silencioso ---
        whatsapp_destino = self.config.get_panico_whatsapp()
        if whatsapp_destino:
            try:
                self._enviar_whatsapp_texto(whatsapp_destino, mensaje)
            except Exception as e:
                print(f"Error enviando WhatsApp de pánico: {e}")

        # --- Pantalla falsa (opcional) ---
        if self.config.get_panico_pantalla_falsa():
            self._mostrar_pantalla_falsa()

        # --- Sonido discreto solo para el usuario (opcional) ---
        # self.reproducir_sonido("pop", volumen=0.2)

    def _mostrar_pantalla_falsa(self):
        """Muestra una pantalla tipo 'error de conexión' por 3 segundos."""
        falsa = Toplevel(self.root)
        falsa.title("Error de conexión")
        falsa.geometry("500x300")
        falsa.resizable(False, False)
        falsa.transient(self.root)
        falsa.grab_set()

        # Centrar
        falsa.update_idletasks()
        x = (falsa.winfo_screenwidth() // 2) - 250
        y = (falsa.winfo_screenheight() // 2) - 150
        falsa.geometry(f"500x300+{x}+{y}")

        frame = ttk.Frame(falsa, padding=30)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="⚠️", font=('Segoe UI', 48)).pack(pady=10)
        ttk.Label(frame, text="Error de conexión",
                font=('Segoe UI', 16, 'bold')).pack(pady=5)
        ttk.Label(frame, text="No se pudo contactar al servidor.\nPor favor, espere...",
                font=('Segoe UI', 11), justify=tk.CENTER).pack(pady=10)

        # Cerrar automáticamente después de 10 segundos
        falsa.after(10000, falsa.destroy)

    def _capturar_evidencia_panico(self):
        """Toma una foto con la webcam y la guarda localmente."""
        try:
            import cv2
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # cámara web local
            ret, frame = cap.read()
            cap.release()
            if ret:
                carpeta = os.path.join(BASE_PATH, "Panico")
                os.makedirs(carpeta, exist_ok=True)
                nombre = f"panico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                cv2.imwrite(os.path.join(carpeta, nombre), frame)
        except Exception as e:
            print(f"No se pudo capturar imagen de pánico: {e}")

    def borrado_seguro_archivo(self, ruta, pasadas=3):
        """Sobrescribe un archivo con datos aleatorios N veces y luego lo elimina."""
        import secrets
        if not os.path.exists(ruta):
            return
        try:
            tamaño = os.path.getsize(ruta)
            if tamaño == 0:
                os.remove(ruta)
                return
            with open(ruta, "r+b") as f:
                for _ in range(pasadas):
                    f.seek(0)
                    f.write(secrets.token_bytes(tamaño))
                    f.flush()
                    os.fsync(f.fileno())
        except Exception as e:
            print(f"⚠️ Error sobrescribiendo {ruta}: {e}")
        finally:
            try:
                os.remove(ruta)
            except Exception as e:
                print(f"⚠️ No se pudo eliminar {ruta}: {e}")

    def reiniciar_aplicacion(self):
        """
        Reinicia la aplicación lanzando un nuevo proceso y cerrando el actual.
        - En modo script (Python): relanza el script con el mismo intérprete.
        - En modo congelado (PyInstaller): relanza el .exe.
        """
        try:
            # Pequeña espera para que el SO libere handles antes de relanzar
            time.sleep(0.5)

            if getattr(sys, 'frozen', False):
                # Aplicación empaquetada (.exe)
                subprocess.Popen([sys.executable] + sys.argv[1:],
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            else:
                # Script de Python normal
                script_path = os.path.abspath(sys.argv[0])
                subprocess.Popen([sys.executable, script_path] + sys.argv[1:],
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            print("🔁 Nueva instancia de SaluPago lanzada.")
        except Exception as e:
            print(f"⚠️ No se pudo reiniciar la aplicación: {e}")

        # Cerrar la instancia actual después de un pequeño delay
        self.root.after(300, lambda: self.root.destroy())

    def activar_panico_wipe(self):
        r"""
        Wipe total: BORRA las carpetas .BT, Backup, Documentos, facturas,
        Incapacidades, BaseRetiros y Caja de la raíz del proyecto.
        No deja rastro en la raíz.
        Los usuarios se guardan en %APPDATA%\.salupago_cache\users.dat
        y se restauran automáticamente al volver a abrir la app.
        """
        # --- 1) Confirmación disfrazada ---
        respuesta = simpledialog.askstring(
            "Reiniciar aplicación",
            "Escriba 'REINICIAR' para reiniciar el sistema:",
            show='*'
        )
        if respuesta != "REINICIAR":
            return

        # --- 2) Respaldar usuarios en ubicación OCULTA ---
        try:
            usuarios_backup = self.db.get_all_users()
            with open(_get_user_backup_path(), 'w', encoding='utf-8') as f:
                json.dump(usuarios_backup, f, ensure_ascii=False, indent=2)
            print(f"✅ {len(usuarios_backup)} usuarios respaldados en {_get_user_backup_path()}")
        except Exception as e:
            print(f"⚠️ No se pudieron respaldar usuarios: {e}")

        # --- 3) Enviar alerta ANTES de borrar ---
        try:
            ahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            equipo = os.environ.get('COMPUTERNAME', 'Desconocido')
            mensaje = (
                f"🚨 WIPE TOTAL EJECUTADO — SaluPago\n\n"
                f"Usuario: {self.username}\n"
                f"Equipo: {equipo}\n"
                f"Fecha/Hora: {ahora}\n\n"
                f"⚠️ Todas las carpetas han sido eliminadas.\n"
                f"Los usuarios se restaurarán en el próximo inicio."
            )
            correo = self.config.get_panico_correo()
            if correo:
                self._enviar_gmail_texto(correo, mensaje)
            whatsapp = self.config.get_panico_whatsapp()
            if whatsapp:
                self._enviar_whatsapp_texto(whatsapp, mensaje)
        except Exception as e:
            print(f"No se pudo enviar alerta: {e}")

        # --- 4) Auditoría ---
        try:
            self._registrar_auditoria(
                "WIPE TOTAL EJECUTADO", "Seguridad", "CRÍTICO",
                f"Usuario: {self.username} | Carpetas eliminadas por completo"
            )
        except Exception:
            pass

        # --- 5) Cerrar la conexión con la BD + forzar liberación de archivos ---
        try:
            self.db = None
        except Exception:
            pass
        # Forzar recolección de basura para que SQLite libere el .db
        import gc
        gc.collect()
        time.sleep(0.8)  # dar tiempo al SO para liberar los handles

        # --- 5.5) Cerrar visores que puedan tener locks en PDFs/imágenes ---
        if sys.platform == 'win32':
            for proc in ['AcroRd32.exe', 'Acrobat.exe', 'msedge.exe', 'chrome.exe']:
                try:
                    subprocess.run(['taskkill', '/F', '/IM', proc],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                creationflags=subprocess.CREATE_NO_WINDOW)
                except Exception:
                    pass
            time.sleep(0.5)

        # --- 6) Borrar las CARPETAS completas de la raíz ---
        carpetas_a_borrar = [
            os.path.join(BASE_PATH, ".BT"),
            os.path.join(BASE_PATH, "Backup"),
            os.path.join(BASE_PATH, "Documentos"),
            os.path.join(BASE_PATH, "facturas"),
            os.path.join(BASE_PATH, "Incapacidades"),
            os.path.join(BASE_PATH, "BaseRetiros"),
            os.path.join(BASE_PATH, "Caja"),
        ]

        def _forzar_borrado_windows(carpeta):
            """En Windows usa rmdir /s /q que es más agresivo con archivos bloqueados."""
            if sys.platform == 'win32':
                try:
                    subprocess.run(
                        ['cmd', '/c', 'rmdir', '/s', '/q', carpeta],
                        check=False,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    return not os.path.exists(carpeta)
                except Exception as e:
                    print(f"⚠️ rmdir falló en {carpeta}: {e}")
            return False

        for carpeta in carpetas_a_borrar:
            if not os.path.exists(carpeta):
                continue

            borrado_ok = False

            # Intento 0: en Windows, usar rmdir /s /q (más potente contra locks)
            if sys.platform == 'win32':
                borrado_ok = _forzar_borrado_windows(carpeta)
                if borrado_ok:
                    print(f"🗑️  Carpeta eliminada (rmdir): {carpeta}")
                    continue

            # Intento 1: borrado normal
            try:
                shutil.rmtree(carpeta)
                print(f"🗑️  Carpeta eliminada: {carpeta}")
                borrado_ok = True
            except Exception as e:
                print(f"⚠️ Fallo intento 1 con {carpeta}: {e}")

            # Intento 2: quitar solo-lectura y reintentar
            if not borrado_ok:
                try:
                    for raiz, dirs, archivos in os.walk(carpeta):
                        for arch in archivos:
                            ruta = os.path.join(raiz, arch)
                            try:
                                os.chmod(ruta, 0o777)
                            except Exception:
                                pass
                    time.sleep(0.5)
                    shutil.rmtree(carpeta)
                    print(f"🗑️  Carpeta eliminada (intento 2): {carpeta}")
                    borrado_ok = True
                except Exception as e:
                    print(f"⚠️ Fallo intento 2 con {carpeta}: {e}")

            # Intento 3: borrado tolerante
            if not borrado_ok:
                try:
                    shutil.rmtree(carpeta, ignore_errors=True)
                    print(f"🗑️  Carpeta eliminada parcialmente: {carpeta}")
                except Exception as e:
                    print(f"⚠️ No se pudo borrar {carpeta}: {e}")

            for carpeta in carpetas_a_borrar:
                if not os.path.exists(carpeta):
                    continue
                borrado_ok = False
                # Intento 1: borrado normal
                try:
                    shutil.rmtree(carpeta)
                    print(f"🗑️  Carpeta eliminada: {carpeta}")
                    borrado_ok = True
                except Exception as e:
                    print(f"⚠️ Fallo intento 1 con {carpeta}: {e}")

                # Intento 2: marcar archivos como no-solo-lectura y reintentar
                if not borrado_ok:
                    try:
                        for raiz, dirs, archivos in os.walk(carpeta):
                            for arch in archivos:
                                ruta = os.path.join(raiz, arch)
                                try:
                                    os.chmod(ruta, 0o777)
                                except Exception:
                                    pass
                        time.sleep(0.5)
                        shutil.rmtree(carpeta)
                        print(f"🗑️  Carpeta eliminada (intento 2): {carpeta}")
                        borrado_ok = True
                    except Exception as e:
                        print(f"⚠️ Fallo intento 2 con {carpeta}: {e}")

                # Intento 3: dejar la carpeta vacía si no se puede borrar del todo
                if not borrado_ok:
                    try:
                        shutil.rmtree(carpeta, ignore_errors=True)
                        print(f"🗑️  Carpeta eliminada parcialmente: {carpeta}")
                    except Exception as e:
                        print(f"⚠️ No se pudo borrar {carpeta}: {e}")

        # --- 7) Pantalla falsa mientras se reinicia ---
        self._mostrar_pantalla_falsa()

        # --- 8) Reiniciar la aplicación (no cerrarla definitivamente) ---
        # La pantalla falsa se autocierra a los 10s; reiniciamos ~10.3s después.
        self.root.after(10300, self.reiniciar_aplicacion)
                       
    def vaciar_tablas_datos(self):
        tablas_a_vaciar = [
            "afiliados",
            "archivados",
            "beneficiarios",
            "ingresos",
            "egresos",
            "novedades",
            "incapacidades",
            "monitoreo",
            "notificaciones",
            "plantillas_notificaciones",
            "solicitudes_pago",
            "backups",
            "auditoria",
        ]

        try:
            with self.db._get_connection() as conn:
                c = conn.cursor()

                # Deshabilitar foreign keys temporalmente (por si acaso)
                c.execute("PRAGMA foreign_keys = OFF")

                for tabla in tablas_a_vaciar:
                    try:
                        # Borra todos los registros
                        c.execute(f"DELETE FROM {tabla}")

                        # Reiniciar el autoincremento (si existe la tabla sqlite_sequence)
                        try:
                            c.execute(
                                "DELETE FROM sqlite_sequence WHERE name = ?",
                                (tabla,)
                            )
                        except sqlite3.OperationalError:
                            pass  # La tabla no tiene AUTOINCREMENT
                    except sqlite3.OperationalError as e:
                        print(f"⚠️ No se pudo vaciar {tabla}: {e}")

                # Volver a habilitar foreign keys
                c.execute("PRAGMA foreign_keys = ON")
                conn.commit()

            print("✅ Tablas de datos vaciadas. Usuarios conservados.")
        except Exception as e:
            print(f"⚠️ Error vaciando tablas: {e}")
                
if __name__ == "__main__":
    root = TkinterDnD.Tk() 

    ruta_icono_ico = os.path.join(IMG_PATH, "mi_icono.ico")   # Opcional (Windows)
    ruta_icono_png = os.path.join(IMG_PATH, "mi_icono.png")   # Fallback (PNG)

    try:
        if sys.platform == 'win32' and os.path.exists(ruta_icono_ico):
            # En Windows, la forma más fiable es usar .ico
            root.iconbitmap(ruta_icono_ico)
            print(f"✅ Icono .ico cargado desde: {ruta_icono_ico}")
        elif os.path.exists(ruta_icono_png):
            # En otros sistemas (o si no hay .ico), usar .png
            icono = tk.PhotoImage(file=ruta_icono_png)
            root.iconphoto(True, icono)
            # Guardamos referencia para evitar que el garbage collector lo borre
            root._icono_ref = icono
            print(f"✅ Icono .png cargado desde: {ruta_icono_png}")
        else:
            print("⚠️ No se encontró el archivo de icono.")
            print(f"   Buscado en: {IMG_PATH}")
            print("   Se usará el icono predeterminado de Tkinter.")
    except Exception as e:
        print(f"❌ No se pudo cargar el icono: {e}")

    menu = MenuPrincipal(root)
    root.mainloop()