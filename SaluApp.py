import flet as ft
import sqlite3
import os
import sys
import json
import base64
import asyncio
import tempfile
from datetime import datetime, timedelta


# ═══════════════════════════════════════════════════════════════════
# COMPATIBILIDAD FLET
# ═══════════════════════════════════════════════════════════════════
def _border_all(w, c):
    return (ft.Border if hasattr(ft, "Border") else ft.border).all(w, c)

def _border_only(**kw):
    return (ft.Border if hasattr(ft, "Border") else ft.border).only(**kw)

def _padding_only(**kw):
    return (ft.Padding if hasattr(ft, "Padding") else ft.padding).only(**kw)

def _padding_sym(**kw):
    return (ft.Padding if hasattr(ft, "Padding") else ft.padding).symmetric(**kw)

def _margin_sym(**kw):
    return (ft.Margin if hasattr(ft, "Margin") else ft.margin).symmetric(**kw)

def _align(name):
    if hasattr(ft, "Alignment"):
        return getattr(ft.Alignment, name.upper())
    return getattr(ft.alignment, name)

def _image_fit(name="contain"):
    if hasattr(ft, "BoxFit"):
        return getattr(ft.BoxFit, name.upper())
    return getattr(ft.ImageFit, name.upper())

def _clip(name="hard_edge"):
    if hasattr(ft, "ClipBehavior"):
        return getattr(ft.ClipBehavior, name.upper())
    return getattr(ft.clip, name)

def _radius(**kw):
    if hasattr(ft, "BorderRadius"):
        return ft.BorderRadius(**kw)
    return ft.border_radius.only(**kw)


# ═══════════════════════════════════════════════════════════════════
# LOCALIZAR BASE DE DATOS
# ═══════════════════════════════════════════════════════════════════
def find_db_path():
    app_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_file = os.path.join(app_dir, "client_config.json")
    if os.path.exists(cfg_file):
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                p = json.load(f).get("db_path")
                if p:
                    p = os.path.abspath(os.path.expanduser(p))
                    if os.path.exists(p):
                        return p
        except Exception:
            pass
    candidatos = [
        os.path.join(app_dir, ".BT", "saluPago.db"),
        os.path.join(os.path.dirname(app_dir), ".BT", "saluPago.db"),
        os.path.join(app_dir, "..", ".BT", "saluPago.db"),
        os.path.join(os.path.dirname(app_dir), "..", ".BT", "saluPago.db"),
    ]
    for c in candidatos:
        c = os.path.abspath(c)
        if os.path.exists(c):
            return c
    return None


def find_img_path(filename):
    app_dir = os.path.dirname(os.path.abspath(__file__))
    candidatos = [
        os.path.join(app_dir, "img", filename),
        os.path.join(os.path.dirname(app_dir), "img", filename),
        os.path.join(app_dir, "..", "img", filename),
        os.path.join(app_dir, filename),
        os.path.join(os.path.dirname(app_dir), filename),
    ]
    for c in candidatos:
        c = os.path.abspath(c)
        if os.path.exists(c):
            return c
    return None


# ═══════════════════════════════════════════════════════════════════
# CONECTOR DB  (ahora con auto-migración de tablas SaluApp)
# ═══════════════════════════════════════════════════════════════════
class SaluPagoDB:
    def __init__(self, db_path):
        self.db_path = db_path
        self._ensure_tables()

    def _conn(self):
        c = sqlite3.connect(self.db_path, timeout=10)
        c.row_factory = sqlite3.Row
        return c

    # ─── Auto-migración robusta (crea tablas y añade columnas faltantes) ───
    def _ensure_tables(self):
        """Crea las tablas SaluApp y añade columnas faltantes si el esquema
        ya existía de una versión anterior."""
        tablas = {
            "chat_mensajes": [
                ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
                ("cc_afiliado", "TEXT"),
                ("emisor", "TEXT"),
                ("mensaje", "TEXT"),
                ("fecha", "TEXT"),
                ("leido", "INTEGER DEFAULT 0"),
            ],
            "pqr": [
                ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
                ("cc_afiliado", "TEXT"),
                ("tipo", "TEXT"),
                ("asunto", "TEXT"),
                ("descripcion", "TEXT"),
                ("estado", "TEXT DEFAULT 'Recibida'"),
                ("respuesta", "TEXT"),
                ("prioridad", "TEXT DEFAULT 'Normal'"),
                ("fecha_creacion", "TEXT"),
                ("fecha_actualizacion", "TEXT"),
            ],
        }
        try:
            with self._conn() as conn:
                cur = conn.cursor()
                for tabla, cols in tablas.items():
                    # 1. Crear tabla base si no existe
                    cur.execute(
                        f"CREATE TABLE IF NOT EXISTS {tabla} "
                        f"(id INTEGER PRIMARY KEY AUTOINCREMENT)"
                    )
                    # 2. Ver qué columnas tiene AHORA
                    cur.execute(f"PRAGMA table_info({tabla})")
                    existentes = {row[1] for row in cur.fetchall()}
                    # 3. Añadir columnas faltantes
                    for nombre, tipo in cols:
                        if nombre == "id":
                            continue
                        if nombre not in existentes:
                            try:
                                cur.execute(
                                    f"ALTER TABLE {tabla} "
                                    f"ADD COLUMN {nombre} {tipo}"
                                )
                                print(f"🔧 Columna añadida: {tabla}.{nombre}")
                            except Exception as e:
                                print(f"⚠️ No se pudo añadir {tabla}.{nombre}: {e}")
                conn.commit()
        except Exception as e:
            print(f"⚠️ Error en _ensure_tables: {e}")

    # ─── Helper seguro: nunca deja caer la app por un error de esquema ──
    def _safe(self, fn, default=None):
        """Ejecuta fn() y captura cualquier error de esquema, devolviendo default."""
        try:
            return fn()
        except sqlite3.OperationalError as e:
            print(f"⚠️ Error SQL (ignorado): {e}")
            return default if default is not None else []
        except Exception as e:
            print(f"⚠️ Error inesperado (ignorado): {e}")
            return default if default is not None else []
    # ─── Afiliado ─────────────────────────────────────────────────
    def get_afiliado(self, cc):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM afiliados WHERE cc = ?", (cc,))
            r = cur.fetchone()
            if r:
                d = dict(r)
                d["archivado"] = False
                d["retirado"] = bool(d.get("fecha_retiro"))
                return d
            cur.execute("SELECT * FROM archivados WHERE cc = ?", (cc,))
            r = cur.fetchone()
            if r:
                d = dict(r)
                d["archivado"] = True
                d["retirado"] = True
                return d
            return None

    def get_beneficiarios(self, cc):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM beneficiarios WHERE cotizante_cc = ? ORDER BY tipo, nombre", (cc,))
            return [dict(r) for r in cur.fetchall()]

    def get_pagos(self, cc):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM ingresos WHERE cc = ? ORDER BY fecha DESC", (cc,))
            return [dict(r) for r in cur.fetchall()]

    def get_notificaciones(self, cc):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM notificaciones WHERE cc = ? ORDER BY fecha DESC", (cc,))
            return [dict(r) for r in cur.fetchall()]

    def get_monitoreo(self, cc):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM monitoreo WHERE cc = ?", (cc,))
            r = cur.fetchone()
            return dict(r) if r else None

    def get_incapacidades(self, nombre):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM incapacidades WHERE nombre = ? ORDER BY fecha_inicio DESC", (nombre,))
            return [dict(r) for r in cur.fetchall()]

    def get_solicitud_activa(self, cc):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("""SELECT * FROM solicitudes_pago
                           WHERE cc_afiliado = ? AND estado IN ('enviada','cliente_confirmado')
                           ORDER BY fecha_creacion DESC LIMIT 1""", (cc,))
            r = cur.fetchone()
            return dict(r) if r else None

    def update_datos_cliente(self, cc, celular, correo, direccion):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("""UPDATE afiliados SET celular = ?, correo = ?, direccion = ? WHERE cc = ?""",
                        (celular, correo, direccion, cc))
            conn.commit()

    def confirmar_solicitud(self, id_solicitud):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("""UPDATE solicitudes_pago
                           SET estado = 'cliente_confirmado', fecha_actualizacion = ?
                           WHERE id = ?""",
                        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), id_solicitud))
            conn.commit()

    def get_empresa(self):
        app_dir = os.path.dirname(self.db_path)
        cfg_path = os.path.join(app_dir, "config.json")
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    return json.load(f).get("empresa", {})
            except Exception:
                pass
        return {"nombre": "SaluPago", "telefono": "", "correo": ""}

    # ══════════════════════════════════════════════════════════════
    # CHAT CON ADMINISTRACIÓN  (con defensa de esquema)
    # ══════════════════════════════════════════════════════════════
    def get_chat_mensajes(self, cc, since_id=0):
        def _q():
            with self._conn() as conn:
                cur = conn.cursor()
                cur.execute("""SELECT * FROM chat_mensajes
                               WHERE cc_afiliado = ? AND id > ?
                               ORDER BY id ASC""", (cc, since_id))
                return [dict(r) for r in cur.fetchall()]
        return self._safe(_q, [])

    def send_chat_mensaje(self, cc, emisor, mensaje):
        def _q():
            with self._conn() as conn:
                cur = conn.cursor()
                cur.execute("""INSERT INTO chat_mensajes
                               (cc_afiliado, emisor, mensaje, fecha, leido)
                               VALUES (?, ?, ?, ?, 0)""",
                            (cc, emisor, mensaje,
                             datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                return cur.lastrowid
        return self._safe(_q, None)

    def marcar_chat_leidos(self, cc, emisor):
        def _q():
            with self._conn() as conn:
                cur = conn.cursor()
                cur.execute("""UPDATE chat_mensajes SET leido = 1
                               WHERE cc_afiliado = ? AND emisor = ?""",
                            (cc, emisor))
                conn.commit()
        self._safe(_q, None)

    def count_chat_no_leidos(self, cc):
        def _q():
            with self._conn() as conn:
                cur = conn.cursor()
                cur.execute("""SELECT COUNT(*) FROM chat_mensajes
                               WHERE cc_afiliado = ?
                               AND emisor = 'admin' AND leido = 0""", (cc,))
                return cur.fetchone()[0]
        return self._safe(_q, 0)

    # ══════════════════════════════════════════════════════════════
    # PQR  (con defensa de esquema)
    # ══════════════════════════════════════════════════════════════
    def get_pqr(self, cc):
        def _q():
            with self._conn() as conn:
                cur = conn.cursor()
                cur.execute("""SELECT * FROM pqr WHERE cc_afiliado = ?
                               ORDER BY fecha_creacion DESC""", (cc,))
                return [dict(r) for r in cur.fetchall()]
        return self._safe(_q, [])

    def create_pqr(self, cc, tipo, asunto, descripcion, prioridad="Normal"):
        def _q():
            with self._conn() as conn:
                cur = conn.cursor()
                cur.execute("""INSERT INTO pqr
                               (cc_afiliado, tipo, asunto, descripcion, estado,
                                prioridad, fecha_creacion, fecha_actualizacion)
                               VALUES (?, ?, ?, ?, 'Recibida', ?, ?, ?)""",
                            (cc, tipo, asunto, descripcion, prioridad,
                             datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                             datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                return cur.lastrowid
        return self._safe(_q, None)

    def count_pqr_abiertos(self, cc):
        def _q():
            with self._conn() as conn:
                cur = conn.cursor()
                cur.execute("""SELECT COUNT(*) FROM pqr
                               WHERE cc_afiliado = ?
                               AND estado IN ('Recibida','En Proceso')""", (cc,))
                return cur.fetchone()[0]
        return self._safe(_q, 0)

    # ══════════════════════════════════════════════════════════════
    # FACTURAS
    # ══════════════════════════════════════════════════════════════
    def find_facturas_dir(self):
        """Busca la carpeta 'facturas' del proyecto SaluPago."""
        candidatos = []
        db_dir = os.path.dirname(self.db_path)        # .BT
        base = os.path.dirname(db_dir)                # raíz proyecto
        candidatos.append(os.path.join(base, "facturas"))
        candidatos.append(os.path.join(db_dir, "facturas"))
        app_dir = os.path.dirname(os.path.abspath(__file__))
        candidatos.append(os.path.join(app_dir, "facturas"))
        candidatos.append(os.path.join(os.path.dirname(app_dir), "facturas"))
        for c in candidatos:
            c = os.path.abspath(c)
            if os.path.isdir(c):
                return c
        return None

    def get_facturas_cliente(self, cc):
        """Devuelve lista de facturas PDF del cliente ordenadas por fecha desc."""
        fd = self.find_facturas_dir()
        if not fd:
            return []
        cc_limpio = ''.join(filter(str.isdigit, str(cc)))
        resultado = []
        try:
            for f in os.listdir(fd):
                if not f.lower().endswith(".pdf"):
                    continue
                if cc_limpio not in f:
                    continue
                ruta = os.path.join(fd, f)
                try:
                    stat = os.stat(ruta)
                    resultado.append({
                        "nombre": f,
                        "ruta": ruta,
                        "fecha_mod": datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M"),
                        "tamano_kb": round(stat.st_size / 1024, 1),
                    })
                except Exception:
                    continue
        except Exception:
            pass
        resultado.sort(key=lambda x: x["fecha_mod"], reverse=True)
        return resultado


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════
def fmt_money(v):
    try:
        return f"$ {float(v):,.0f}".replace(",", ".")
    except Exception:
        return "$ 0"


def fmt_fecha(f):
    if not f:
        return "—"
    try:
        return datetime.strptime(str(f)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return str(f)


def dias_prox_pago(fecha_pago_str):
    if not fecha_pago_str:
        return None
    try:
        f = datetime.strptime(str(fecha_pago_str)[:10], "%Y-%m-%d")
        venc = f + timedelta(days=30)
        return (venc - datetime.now()).days, venc
    except Exception:
        return None


def generar_qr_base64(data, color_dark="#1E1E38", color_light="white"):
    """Genera un QR en base64 listo para ft.Image()."""
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=3,
        )
        qr.add_data(str(data))
        qr.make(fit=True)
        img = qr.make_image(fill_color=color_dark, back_color=color_light).convert("RGB")
        buf = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        buf.close()
        img.save(buf.name)
        with open(buf.name, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        try:
            os.remove(buf.name)
        except Exception:
            pass
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        print(f"⚠️ Error generando QR: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════
# APP
# ═══════════════════════════════════════════════════════════════════
def main(page: ft.Page):
    page.title = "SaluApp · Mi Portal"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.spacing = 0

    DARK_BG        = "#0F0F1E"
    DARK_BG_2      = "#1A1035"
    DARK_SURFACE   = "#1E1E38"
    DARK_SURFACE_2 = "#252547"
    DARK_BORDER    = "#2E2E52"

    PURPLE         = "#8B5CF6"
    PURPLE_DARK    = "#6D28D9"
    PURPLE_LIGHT   = "#A855F7"

    TEXT           = "#FFFFFF"
    TEXT_DIM       = "#B0B0C8"
    TEXT_MUTED     = "#6B6B8A"

    GREEN          = "#4ADE80"
    RED            = "#F87171"
    ORANGE         = "#FB923C"
    BLUE_ACC       = "#60A5FA"

    page.bgcolor = DARK_BG

    WIN_W, WIN_H = 390, 700
    MARGEN_DERECHO = 20

    def _screen_size():
        try:
            import tkinter as tk
            r = tk.Tk()
            r.withdraw()
            w, h = r.winfo_screenwidth(), r.winfo_screenheight()
            r.destroy()
            return w, h
        except Exception:
            return 1920, 1080

    sw, sh = _screen_size()
    win_left = max(0, sw - WIN_W - MARGEN_DERECHO)
    win_top  = max(0, (sh - WIN_H) // 2)

    try:
        page.window.width  = WIN_W
        page.window.height = WIN_H
        page.window.left   = win_left
        page.window.top    = win_top
    except AttributeError:
        page.window_width  = WIN_W
        page.window_height = WIN_H
        page.window_left   = win_left
        page.window_top    = win_top

    db_path = find_db_path()
    img_saluapp = find_img_path("SaluApp.png")

    if not db_path:
        page.add(
            ft.Container(
                expand=True, bgcolor=DARK_BG, padding=30,
                content=ft.Column(
                    controls=[
                        ft.Container(expand=True),
                        ft.Icon(ft.Icons.ERROR_OUTLINE, size=80, color=RED),
                        ft.Container(height=20),
                        ft.Text("No se pudo conectar", size=22,
                                weight=ft.FontWeight.BOLD,
                                text_align=ft.TextAlign.CENTER, color=TEXT),
                        ft.Text(
                            "No se encontró la base de datos de SaluApp.\n\n"
                            'Crea un archivo client_config.json con:\n'
                            '{"db_path": "C:/ruta/a/.BT/saluPago.db"}',
                            size=13, text_align=ft.TextAlign.CENTER, color=TEXT_DIM,
                        ),
                        ft.Container(expand=True),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
        )
        return

    db = SaluPagoDB(db_path)
    empresa = db.get_empresa()

    state = {
        "app_abierta": None,
        "afiliado": None,
        "tab": "inicio",
        "sub": None,
        "splash": False,
        "welcome": False,
        "goodbye": False,
        "history": [],
        "beneficiarios": [],
        "pagos": [],
        "notificaciones": [],
        "incapacidades": [],
        "monitoreo": None,
        "solicitud": None,
        "chat": [],
        "pqr": [],
        "facturas": [],
        "chat_unread": 0,
        "pqr_abiertos": 0,
        "chat_poll_token": 0,
    }

    def cargar_datos():
        af = state["afiliado"]
        if not af:
            return
        cc = af["cc"]

        # Cada llamada va en su propio try/except para que un error
        # en una tabla no tumbe todo el resto.
        try:
            state["afiliado"] = db.get_afiliado(cc) or af
        except Exception as e:
            print(f"⚠️ get_afiliado: {e}")

        for clave, fn in [
            ("beneficiarios",  lambda: db.get_beneficiarios(cc)),
            ("pagos",          lambda: db.get_pagos(cc)),
            ("notificaciones", lambda: db.get_notificaciones(cc)),
            ("monitoreo",      lambda: db.get_monitoreo(cc)),
            ("solicitud",      lambda: db.get_solicitud_activa(cc)),
            ("incapacidades",  lambda: db.get_incapacidades(
                                    state["afiliado"].get("nombre", ""))),
            ("chat",           lambda: db.get_chat_mensajes(cc)),
            ("pqr",            lambda: db.get_pqr(cc)),
            ("facturas",       lambda: db.get_facturas_cliente(cc)),
            ("chat_unread",    lambda: db.count_chat_no_leidos(cc)),
            ("pqr_abiertos",   lambda: db.count_pqr_abiertos(cc)),
        ]:
            try:
                state[clave] = fn()
            except Exception as e:
                print(f"⚠️ Error cargando '{clave}': {e}")
                state.setdefault(
                    clave,
                    [] if clave not in ("monitoreo", "solicitud",
                                        "chat_unread", "pqr_abiertos")
                    else (None if clave in ("monitoreo", "solicitud") else 0)
                )
    # ═══════════════════════════════════════════════════════════════
    # SISTEMA DE ALERTAS (SnackBar flotante)
    # ═══════════════════════════════════════════════════════════════
    def _icono_alerta(tipo):
        if tipo == "error":
            return ft.Icons.ERROR_OUTLINE_ROUNDED, RED
        if tipo == "warning":
            return ft.Icons.WARNING_AMBER_ROUNDED, ORANGE
        if tipo == "info":
            return ft.Icons.INFO_OUTLINE_ROUNDED, BLUE_ACC
        return ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED, GREEN

    def mostrar_alerta(mensaje, tipo="error", duracion=3500):
        icono, color = _icono_alerta(tipo)
        try:
            page.snack_bar = ft.SnackBar(
                content=ft.Row(
                    controls=[
                        ft.Icon(icono, color="white", size=20),
                        ft.Text(mensaje, color="white", size=13,
                                weight=ft.FontWeight.W_600, expand=True),
                    ],
                    spacing=10,
                ),
                bgcolor=color,
                behavior=ft.SnackBarBehavior.FLOATING,
                margin=_margin_sym(horizontal=15, vertical=12),
                shape=ft.RoundedRectangleBorder(radius=14),
                duration=duracion,
            )
            page.snack_bar.open = True
            page.update()
        except Exception:
            pass

    # ─── Historial navegación ─────────────────────────────────────
    def _snapshot_actual():
        return {
            "app_abierta": state["app_abierta"],
            "tab": state["tab"],
            "sub": state["sub"],
        }

    def _restaurar(snap):
        state["app_abierta"] = snap["app_abierta"]
        state["tab"] = snap["tab"]
        state["sub"] = snap["sub"]
        state["splash"] = False
        state["welcome"] = False
        state["goodbye"] = False
        state.pop("_auth_refs", None)
        state.pop("_welcome_refs", None)
        state.pop("_goodbye_refs", None)
        state["chat_poll_token"] = state.get("chat_poll_token", 0) + 1

    def _navegar(**cambios):
        state["history"].append(_snapshot_actual())
        for k, v in cambios.items():
            state[k] = v
        render()

    # ─── Barra de estado ──────────────────────────────────────────
    def status_bar(fg_color):
        return ft.Container(
            bgcolor="transparent",
            padding=_padding_only(left=20, right=20, top=4, bottom=4),
            content=ft.Row(
                controls=[
                    ft.Text(datetime.now().strftime("%H:%M"), size=10,
                            weight=ft.FontWeight.BOLD, color=fg_color),
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.SIGNAL_CELLULAR_4_BAR, size=11, color=fg_color),
                            ft.Icon(ft.Icons.WIFI, size=11, color=fg_color),
                            ft.Icon(ft.Icons.BATTERY_FULL, size=13, color=fg_color),
                        ],
                        spacing=3,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
        )

    # ─── Barra Android (transparente) ─────────────────────────────
    def nav_buttons_bar():
        def go_recent(e):
            pass

        def go_home(e):
            state["history"] = []
            state["app_abierta"] = None
            state["sub"] = None
            state["splash"] = False
            state["welcome"] = False
            state["goodbye"] = False
            state["chat_poll_token"] = state.get("chat_poll_token", 0) + 1
            state.pop("_auth_refs", None)
            state.pop("_welcome_refs", None)
            state.pop("_goodbye_refs", None)
            render()

        def go_back(e):
            if state["history"]:
                snap = state["history"].pop()
                _restaurar(snap)
                render()
                return
            if state["app_abierta"] is None:
                return
            state["app_abierta"] = None
            state["sub"] = None
            state["splash"] = False
            state["welcome"] = False
            state["goodbye"] = False
            state["chat_poll_token"] = state.get("chat_poll_token", 0) + 1
            state.pop("_auth_refs", None)
            state.pop("_welcome_refs", None)
            state.pop("_goodbye_refs", None)
            render()

        en_launcher = state.get("app_abierta") is None
        fg = "#3C4043" if en_launcher else TEXT

        def nav_btn(icon_name, handler):
            return ft.Container(
                alignment=_align("center"),
                on_click=handler,
                ink=True,
                border_radius=50,
                padding=_padding_sym(vertical=6, horizontal=18),
                content=ft.Icon(icon_name, size=20, color=fg),
            )

        return ft.Container(
            bgcolor="transparent",
            padding=_padding_sym(vertical=2, horizontal=20),
            content=ft.Row(
                controls=[
                    nav_btn(ft.Icons.CROP_SQUARE_ROUNDED, go_recent),
                    nav_btn(ft.Icons.CIRCLE_OUTLINED, go_home),
                    nav_btn(ft.Icons.CHANGE_HISTORY, go_back),
                ],
                alignment=ft.MainAxisAlignment.SPACE_EVENLY,
            ),
        )

    # ═══════════════════════════════════════════════════════════════
    # AUTH VIEW (splash + login unificados)
    # ═══════════════════════════════════════════════════════════════
    def auth_view():
        is_splash = state.get("splash", False)

        if img_saluapp:
            logo_content = ft.Image(src=img_saluapp, fit=_image_fit("contain"))
            logo = ft.Container(
                width=120, height=120, border_radius=30,
                clip_behavior=_clip("hard_edge"),
                alignment=_align("center"),
                shadow=ft.BoxShadow(
                    blur_radius=70, spread_radius=0,
                    color="#8B5CF6CC", offset=ft.Offset(0, 0),
                ),
                scale=1.7 if is_splash else 1.0,
                animate_scale=ft.Animation(850, ft.AnimationCurve.EASE_OUT_CUBIC),
                content=logo_content,
            )
        else:
            logo = ft.Container(
                width=120, height=120, border_radius=30,
                gradient=ft.LinearGradient(
                    colors=[PURPLE_DARK, PURPLE, PURPLE_LIGHT],
                    begin=_align("top_left"), end=_align("bottom_right"),
                ),
                alignment=_align("center"),
                shadow=ft.BoxShadow(
                    blur_radius=70, spread_radius=0,
                    color="#8B5CF6CC", offset=ft.Offset(0, 0),
                ),
                scale=1.7 if is_splash else 1.0,
                animate_scale=ft.Animation(850, ft.AnimationCurve.EASE_OUT_CUBIC),
                content=ft.Icon(ft.Icons.FAVORITE_ROUNDED, size=60, color="white"),
            )

        brand = ft.Column(
            controls=[
                ft.Text("SaluApp", color=TEXT, size=32, weight=ft.FontWeight.BOLD),
                ft.Container(height=4),
                ft.Text("Mi Portal del Afiliado", color=TEXT_DIM, size=14),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
            opacity=0 if is_splash else 1,
            animate_opacity=ft.Animation(800, ft.AnimationCurve.EASE_OUT),
        )

        logo_group = ft.Container(
            alignment=_align("center"),
            offset=ft.Offset(0, 0.9) if is_splash else ft.Offset(0, 0),
            animate_offset=ft.Animation(900, ft.AnimationCurve.EASE_IN_OUT_CUBIC),
            content=ft.Column(
                controls=[
                    logo,
                    ft.Container(height=22),
                    brand,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
            ),
        )

        login_card = ft.Container(
            bgcolor=DARK_SURFACE, border_radius=22, padding=25,
            border=_border_all(1, DARK_BORDER),
            opacity=0 if is_splash else 1,
            animate_opacity=ft.Animation(800, ft.AnimationCurve.EASE_OUT),
            content=ft.Column(
                controls=[
                    ft.Text("Ingresa con tu documento", size=16,
                            weight=ft.FontWeight.BOLD, color=TEXT),
                    ft.Container(height=4),
                    ft.Text("Consulta tu estado, pagos y afiliación",
                            size=12, color=TEXT_MUTED),
                    ft.Container(height=18),
                    cedula_input,
                    ft.Container(height=10),
                    ft.Container(
                        border_radius=14, padding=16,
                        gradient=ft.LinearGradient(
                            colors=[PURPLE_DARK, PURPLE, PURPLE_LIGHT],
                            begin=_align("top_left"),
                            end=_align("bottom_right"),
                        ),
                        alignment=_align("center"),
                        on_click=login, ink=True,
                        shadow=ft.BoxShadow(
                            blur_radius=35, spread_radius=0,
                            color="#8B5CF6CC", offset=ft.Offset(0, 0),
                        ),
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.LOGIN_ROUNDED,
                                        color="white", size=20),
                                ft.Text("Ingresar", color="white", size=16,
                                        weight=ft.FontWeight.BOLD),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=10,
                        ),
                    ),
                ],
                spacing=6,
            ),
        )

        state["_auth_refs"] = {
            "group": logo_group,
            "logo": logo,
            "brand": brand,
            "card": login_card,
        }

        return ft.Container(
            expand=True,
            gradient=ft.LinearGradient(
                colors=[DARK_BG_2, DARK_BG, DARK_BG],
                begin=_align("top_left"), end=_align("bottom_right"),
            ),
            content=ft.Column(
                controls=[
                    status_bar(TEXT),
                    ft.Container(
                        padding=_padding_only(left=8, top=0),
                        alignment=_align("center_left"),
                        content=ft.IconButton(
                            icon=ft.Icons.ARROW_BACK_ROUNDED,
                            icon_color=TEXT,
                            on_click=volver_launcher,
                        ),
                    ),
                    ft.Container(height=10),
                    logo_group,
                    ft.Container(height=35),
                    ft.Container(
                        margin=_margin_sym(horizontal=20),
                        content=login_card,
                    ),
                    ft.Container(expand=True),
                    ft.Container(
                        padding=_padding_only(bottom=10),
                        alignment=_align("center"),
                        content=ft.Text(
                            f"© {datetime.now().year} {empresa.get('nombre', 'SaluApp')}",
                            color=TEXT_MUTED, size=11,
                        ),
                    ),
                ],
                spacing=0,
            ),
        )

    # ═══════════════════════════════════════════════════════════════
    # WELCOME VIEW
    # ═══════════════════════════════════════════════════════════════
    def welcome_view():
        af = state["afiliado"]
        primer_nombre = (af.get("nombre") or "Afiliado").split()[0]

        check_ring = ft.Container(
            width=110, height=110, border_radius=55,
            gradient=ft.LinearGradient(
                colors=[GREEN, "#22C55E"],
                begin=_align("top_left"),
                end=_align("bottom_right"),
            ),
            alignment=_align("center"),
            shadow=ft.BoxShadow(
                blur_radius=70, spread_radius=2,
                color=f"{GREEN}CC",
                offset=ft.Offset(0, 0),
            ),
            scale=0.2, opacity=0,
            animate_scale=ft.Animation(750, ft.AnimationCurve.EASE_OUT_BACK),
            animate_opacity=ft.Animation(450, ft.AnimationCurve.EASE_OUT),
            content=ft.Icon(ft.Icons.CHECK_ROUNDED, size=64, color="white"),
        )

        saludo = ft.Column(
            controls=[
                ft.Text("¡Bienvenido!", size=30,
                        weight=ft.FontWeight.BOLD, color=TEXT,
                        text_align=ft.TextAlign.CENTER),
                ft.Container(height=6),
                ft.Text(primer_nombre, size=22,
                        weight=ft.FontWeight.W_600, color=PURPLE_LIGHT,
                        text_align=ft.TextAlign.CENTER),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0, opacity=0,
            offset=ft.Offset(0, 0.35),
            animate_opacity=ft.Animation(600, ft.AnimationCurve.EASE_OUT),
            animate_offset=ft.Animation(700, ft.AnimationCurve.EASE_OUT_CUBIC),
        )

        subtitulo = ft.Container(
            opacity=0,
            animate_opacity=ft.Animation(500, ft.AnimationCurve.EASE_OUT),
            content=ft.Row(
                controls=[
                    ft.ProgressRing(width=16, height=16,
                                    stroke_width=2, color=PURPLE_LIGHT),
                    ft.Text("Preparando tu información…",
                            size=12, color=TEXT_DIM),
                ],
                spacing=10,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        )

        state["_welcome_refs"] = {
            "check": check_ring,
            "saludo": saludo,
            "subtitulo": subtitulo,
        }

        return ft.Container(
            expand=True,
            gradient=ft.LinearGradient(
                colors=[DARK_BG_2, DARK_BG, DARK_BG],
                begin=_align("top_left"), end=_align("bottom_right"),
            ),
            content=ft.Column(
                controls=[
                    status_bar(TEXT),
                    ft.Container(expand=True),
                    ft.Container(
                        alignment=_align("center"),
                        content=ft.Column(
                            controls=[
                                check_ring,
                                ft.Container(height=30),
                                saludo,
                                ft.Container(height=40),
                                subtitulo,
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=0,
                        ),
                    ),
                    ft.Container(expand=True),
                    ft.Container(
                        padding=_padding_only(bottom=10),
                        alignment=_align("center"),
                        content=ft.Text(
                            f"© {datetime.now().year} {empresa.get('nombre', 'SaluApp')}",
                            color=TEXT_MUTED, size=11,
                        ),
                    ),
                ],
                spacing=0,
            ),
        )

    async def _run_welcome_anim():
        await asyncio.sleep(0.12)

        def _get(n):
            refs = state.get("_welcome_refs") or {}
            return refs.get(n)

        def _u(n):
            c = _get(n)
            if c is not None:
                try:
                    c.update()
                except Exception:
                    pass

        c = _get("check")
        if c is None or not state.get("welcome"):
            return
        c.scale = 1.0
        c.opacity = 1
        _u("check")
        await asyncio.sleep(0.55)

        if not state.get("welcome"):
            return
        s = _get("saludo")
        if s is not None:
            s.opacity = 1
            s.offset = ft.Offset(0, 0)
            _u("saludo")
        await asyncio.sleep(0.65)

        if not state.get("welcome"):
            return
        sub = _get("subtitulo")
        if sub is not None:
            sub.opacity = 1
            _u("subtitulo")
        await asyncio.sleep(1.05)

        if not state.get("welcome"):
            return
        state["welcome"] = False
        state.pop("_welcome_refs", None)
        render()

    # ═══════════════════════════════════════════════════════════════
    # GOODBYE VIEW
    # ═══════════════════════════════════════════════════════════════
    def goodbye_view():
        af = state.get("afiliado") or {}
        primer_nombre = (af.get("nombre") or "Afiliado").split()[0]

        wave_ring = ft.Container(
            width=110, height=110, border_radius=55,
            gradient=ft.LinearGradient(
                colors=[PURPLE, PURPLE_LIGHT],
                begin=_align("top_left"),
                end=_align("bottom_right"),
            ),
            alignment=_align("center"),
            shadow=ft.BoxShadow(
                blur_radius=70, spread_radius=2,
                color=f"{PURPLE}CC",
                offset=ft.Offset(0, 0),
            ),
            scale=0.2, opacity=0,
            animate_scale=ft.Animation(750, ft.AnimationCurve.EASE_OUT_BACK),
            animate_opacity=ft.Animation(450, ft.AnimationCurve.EASE_OUT),
            content=ft.Text("👋", size=58),
        )

        despedida = ft.Column(
            controls=[
                ft.Text("¡Hasta pronto!", size=30,
                        weight=ft.FontWeight.BOLD, color=TEXT,
                        text_align=ft.TextAlign.CENTER),
                ft.Container(height=6),
                ft.Text(primer_nombre, size=22,
                        weight=ft.FontWeight.W_600, color=PURPLE_LIGHT,
                        text_align=ft.TextAlign.CENTER),
                ft.Container(height=10),
                ft.Text("Gracias por usar SaluApp 💜",
                        size=13, color=TEXT_DIM,
                        text_align=ft.TextAlign.CENTER),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0, opacity=0,
            offset=ft.Offset(0, 0.35),
            animate_opacity=ft.Animation(600, ft.AnimationCurve.EASE_OUT),
            animate_offset=ft.Animation(700, ft.AnimationCurve.EASE_OUT_CUBIC),
        )

        subtitulo = ft.Container(
            opacity=0,
            animate_opacity=ft.Animation(500, ft.AnimationCurve.EASE_OUT),
            content=ft.Row(
                controls=[
                    ft.ProgressRing(width=16, height=16,
                                    stroke_width=2, color=PURPLE_LIGHT),
                    ft.Text("Cerrando sesión de forma segura…",
                            size=12, color=TEXT_DIM),
                ],
                spacing=10,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        )

        state["_goodbye_refs"] = {
            "wave": wave_ring,
            "despedida": despedida,
            "subtitulo": subtitulo,
        }

        return ft.Container(
            expand=True,
            gradient=ft.LinearGradient(
                colors=[DARK_BG_2, DARK_BG, DARK_BG],
                begin=_align("top_left"), end=_align("bottom_right"),
            ),
            content=ft.Column(
                controls=[
                    status_bar(TEXT),
                    ft.Container(expand=True),
                    ft.Container(
                        alignment=_align("center"),
                        content=ft.Column(
                            controls=[
                                wave_ring,
                                ft.Container(height=30),
                                despedida,
                                ft.Container(height=40),
                                subtitulo,
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=0,
                        ),
                    ),
                    ft.Container(expand=True),
                    ft.Container(
                        padding=_padding_only(bottom=10),
                        alignment=_align("center"),
                        content=ft.Text(
                            f"© {datetime.now().year} {empresa.get('nombre', 'SaluApp')}",
                            color=TEXT_MUTED, size=11,
                        ),
                    ),
                ],
                spacing=0,
            ),
        )

    async def _run_goodbye_anim():
        await asyncio.sleep(0.12)

        def _get(n):
            refs = state.get("_goodbye_refs") or {}
            return refs.get(n)

        def _u(n):
            c = _get(n)
            if c is not None:
                try:
                    c.update()
                except Exception:
                    pass

        w = _get("wave")
        if w is None or not state.get("goodbye"):
            return
        w.scale = 1.0
        w.opacity = 1
        _u("wave")
        await asyncio.sleep(0.55)

        if not state.get("goodbye"):
            return
        d = _get("despedida")
        if d is not None:
            d.opacity = 1
            d.offset = ft.Offset(0, 0)
            _u("despedida")
        await asyncio.sleep(0.70)

        if not state.get("goodbye"):
            return
        sub = _get("subtitulo")
        if sub is not None:
            sub.opacity = 1
            _u("subtitulo")
        await asyncio.sleep(1.00)

        if not state.get("goodbye"):
            return
        state["afiliado"] = None
        state["sub"] = None
        state["splash"] = False
        state["welcome"] = False
        state["goodbye"] = False
        state["history"] = []
        state["tab"] = "inicio"
        state.pop("_auth_refs", None)
        state.pop("_welcome_refs", None)
        state.pop("_goodbye_refs", None)
        try:
            cedula_input.value = ""
        except Exception:
            pass
        render()

    async def _run_splash_anim():
        await asyncio.sleep(0.15)

        def _get(nombre):
            refs = state.get("_auth_refs") or {}
            return refs.get(nombre)

        def _u(nombre):
            c = _get(nombre)
            if c is not None:
                try:
                    c.update()
                except Exception:
                    pass

        b = _get("brand")
        if b is not None:
            b.opacity = 1
            _u("brand")
        await asyncio.sleep(0.35)

        for _ in range(2):
            if not state.get("_auth_refs"):
                return
            lg = _get("logo")
            if lg is None:
                return
            lg.scale = 1.85
            _u("logo")
            await asyncio.sleep(0.30)
            if not state.get("_auth_refs"):
                return
            lg = _get("logo")
            if lg is None:
                return
            lg.scale = 1.70
            _u("logo")
            await asyncio.sleep(0.30)

        await asyncio.sleep(0.45)

        if not state.get("splash"):
            return
        if not state.get("_auth_refs"):
            return

        state["splash"] = False

        g = _get("group")
        if g is not None:
            g.offset = ft.Offset(0, 0)
            _u("group")

        lg = _get("logo")
        if lg is not None:
            lg.scale = 1.0
            _u("logo")

        await asyncio.sleep(0.35)

        c = _get("card")
        if c is not None:
            c.opacity = 1
            _u("card")

    # ─── Render con transición animada ────────────────────────────
    def render():
        if state.get("app_abierta") is None:
            content = launcher_view()
            view_key = "launcher"
        elif state.get("goodbye") and state.get("afiliado") is not None:
            content = goodbye_view()
            view_key = "goodbye"
        elif state.get("afiliado") is None:
            content = auth_view()
            view_key = "auth"
        elif state.get("welcome"):
            content = welcome_view()
            view_key = "welcome"
        else:
            content = main_view()
            view_key = f"main_{state['tab']}_{state['sub']}"

        wrapper = ft.Column(
            key=view_key,
            controls=[
                ft.Container(content=content, expand=True),
                nav_buttons_bar(),
            ],
            spacing=0,
            expand=True,
        )

        if not hasattr(page, "_switcher") or page._switcher is None:
            page._switcher = ft.AnimatedSwitcher(
                content=wrapper,
                duration=350,
                reverse_duration=250,
                switch_in_curve=ft.AnimationCurve.EASE_OUT_CUBIC,
                switch_out_curve=ft.AnimationCurve.EASE_IN,
                transition=ft.AnimatedSwitcherTransition.FADE,
                expand=True,
            )
            page.controls.clear()
            page.add(page._switcher)
        else:
            page._switcher.content = wrapper

        page.update()

        mostrar_splash = (
            state.get("splash", False)
            and state.get("app_abierta") is not None
            and state.get("afiliado") is None
        )
        if mostrar_splash and not state.get("_splash_anim_scheduled"):
            state["_splash_anim_scheduled"] = True
            try:
                page.run_task(_run_splash_anim)
            except Exception:
                import threading
                threading.Timer(
                    0.1, lambda: asyncio.run(_run_splash_anim())
                ).start()
        elif not mostrar_splash:
            state["_splash_anim_scheduled"] = False

        mostrar_welcome = (
            state.get("welcome", False)
            and state.get("afiliado") is not None
            and state.get("app_abierta") is not None
        )
        if mostrar_welcome and not state.get("_welcome_anim_scheduled"):
            state["_welcome_anim_scheduled"] = True
            try:
                page.run_task(_run_welcome_anim)
            except Exception:
                import threading
                threading.Timer(
                    0.1, lambda: asyncio.run(_run_welcome_anim())
                ).start()
        elif not mostrar_welcome:
            state["_welcome_anim_scheduled"] = False

        mostrar_goodbye = (
            state.get("goodbye", False)
            and state.get("afiliado") is not None
            and state.get("app_abierta") is not None
        )
        if mostrar_goodbye and not state.get("_goodbye_anim_scheduled"):
            state["_goodbye_anim_scheduled"] = True
            try:
                page.run_task(_run_goodbye_anim)
            except Exception:
                import threading
                threading.Timer(
                    0.1, lambda: asyncio.run(_run_goodbye_anim())
                ).start()
        elif not mostrar_goodbye:
            state["_goodbye_anim_scheduled"] = False

    def volver_launcher(e=None):
        state["history"] = []
        state["app_abierta"] = None
        state["sub"] = None
        state["splash"] = False
        state["welcome"] = False
        state["goodbye"] = False
        state["chat_poll_token"] = state.get("chat_poll_token", 0) + 1
        state.pop("_auth_refs", None)
        state.pop("_welcome_refs", None)
        state.pop("_goodbye_refs", None)
        render()

    # ═══════════════════════════════════════════════════════════════
    # CAMPO DE ENTRADA + VALIDACIONES
    # ═══════════════════════════════════════════════════════════════
    cedula_input = ft.TextField(
        label="Número de documento",
        hint_text="Ej: 1234567890",
        keyboard_type=ft.KeyboardType.NUMBER,
        border=ft.InputBorder.OUTLINE,
        border_color=DARK_BORDER,
        focused_border_color=PURPLE,
        border_radius=14,
        filled=True,
        bgcolor=DARK_SURFACE_2,
        label_style=ft.TextStyle(color=TEXT_DIM, size=12),
        text_style=ft.TextStyle(color=TEXT, size=16),
        cursor_color=PURPLE,
        prefix_icon=ft.Icons.BADGE_ROUNDED,
        text_size=16,
        max_length=15,
    )

    def _set_error(msg):
        if hasattr(cedula_input, "error"):
            cedula_input.error = msg
        else:
            cedula_input.error_text = msg
        cedula_input.border_color = RED if msg else DARK_BORDER
        page.update()

    def limpiar_error(e=None):
        _set_error(None)

    def solo_numeros(e=None):
        valor = cedula_input.value or ""
        limpio = "".join(filter(str.isdigit, valor))
        if limpio != valor:
            cedula_input.value = limpio
            _set_error("Solo se permiten números (0-9)")
        else:
            if hasattr(cedula_input, "error") and cedula_input.error:
                _set_error(None)
            elif hasattr(cedula_input, "error_text") and cedula_input.error_text:
                _set_error(None)

    cedula_input.on_change = solo_numeros

    def login(e=None):
        raw = (cedula_input.value or "").strip()

        if not raw:
            _set_error("El campo no puede estar vacío")
            mostrar_alerta(
                "Por favor, ingresa tu número de documento para continuar.",
                tipo="warning",
            )
            return

        if len(raw) < 5:
            _set_error("Mínimo 5 dígitos")
            mostrar_alerta(
                f"El número de documento es demasiado corto ({len(raw)} dígitos). "
                "Debe tener al menos 5.",
                tipo="warning",
            )
            return

        if len(raw) > 12:
            _set_error("Máximo 12 dígitos")
            mostrar_alerta(
                f"El número de documento es demasiado largo ({len(raw)} dígitos). "
                "Verifica la información.",
                tipo="warning",
            )
            return

        limpio = "".join(filter(str.isdigit, raw))
        if limpio != raw:
            _set_error("Solo se permiten números")
            mostrar_alerta(
                "El documento solo debe contener números, sin letras ni símbolos.",
                tipo="error",
            )
            return

        if len(set(limpio)) == 1:
            _set_error("Documento inválido")
            mostrar_alerta(
                "Ese número de documento no parece válido. Verifícalo por favor.",
                tipo="warning",
            )
            return

        af = db.get_afiliado(limpio)
        if not af:
            _set_error("Documento no registrado")
            mostrar_alerta(
                f"No existe ningún afiliado con el documento {limpio}. "
                "Verifica o contacta a soporte.",
                tipo="error",
                duracion=4500,
            )
            return

        _set_error(None)
        mostrar_alerta(
            f"¡Bienvenido, {(af.get('nombre') or '').split()[0]}!",
            tipo="success",
            duracion=2000,
        )
        state["afiliado"] = af
        state["tab"] = "inicio"
        state["sub"] = None
        state["splash"] = False
        state["welcome"] = True
        state["goodbye"] = False
        state["history"] = []
        state.pop("_auth_refs", None)
        state.pop("_goodbye_refs", None)
        cargar_datos()
        render()

    cedula_input.on_submit = login

    def logout(e=None):
        if state.get("afiliado") is None:
            return
        state["goodbye"] = True
        state["welcome"] = False
        state["splash"] = False
        state["history"] = []
        state["chat_poll_token"] = state.get("chat_poll_token", 0) + 1
        state.pop("_auth_refs", None)
        state.pop("_welcome_refs", None)
        state.pop("_goodbye_refs", None)
        render()

    # ═══════════════════════════════════════════════════════════════
    # LAUNCHER
    # ═══════════════════════════════════════════════════════════════
    def launcher_view():
        def abrir(key):
            def h(e):
                _navegar(app_abierta=key, splash=(key == "salupago"))
            return h

        def tile(nombre, icono=None, color=None, on_click=None, image_path=None):
            if image_path:
                contenedor_icono = ft.Container(
                    width=54, height=54, border_radius=17,
                    bgcolor="white", alignment=_align("center"),
                    shadow=ft.BoxShadow(
                        blur_radius=10, spread_radius=0,
                        color="#00000015", offset=ft.Offset(0, 3),
                    ),
                    clip_behavior=_clip("hard_edge"),
                    padding=3,
                    content=ft.Image(src=image_path, fit=_image_fit("contain")),
                )
            else:
                contenedor_icono = ft.Container(
                    width=54, height=54, border_radius=17,
                    bgcolor="white", alignment=_align("center"),
                    shadow=ft.BoxShadow(
                        blur_radius=10, spread_radius=0,
                        color="#00000015", offset=ft.Offset(0, 3),
                    ),
                    content=ft.Icon(icono, color=color, size=27),
                )
            columna = ft.Column(
                controls=[
                    contenedor_icono,
                    ft.Container(height=2),
                    ft.Text(nombre, size=10, color="#3C4043",
                            text_align=ft.TextAlign.CENTER),
                ],
                spacing=3,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
            return ft.Container(
                width=70,
                content=columna,
                on_click=on_click,
                ink=on_click is not None,
                border_radius=12,
            )

        otros = [
            ("Correo",      ft.Icons.MAIL_ROUNDED,           "#EA4335", None, None),
            ("Fotos",       ft.Icons.PHOTO_LIBRARY_ROUNDED,  "#FBBC04", None, None),
            ("Archivos",    ft.Icons.FOLDER_ROUNDED,         "#4285F4", None, None),
            ("Ajustes",     ft.Icons.SETTINGS_ROUNDED,       "#5F6368", None, None),
            ("Calendario",  ft.Icons.CALENDAR_MONTH_ROUNDED, "#34A853", None, None),
            ("Notas",       ft.Icons.STICKY_NOTE_2_ROUNDED,  "#F9AB00", None, None),
            ("Música",      ft.Icons.MUSIC_NOTE_ROUNDED,     "#E91E63", None, None),
            ("SaluApp",     None,                            None,     abrir("salupago"), img_saluapp),
        ]

        filas = []
        for i in range(0, len(otros), 4):
            chunk = otros[i:i + 4]
            filas.append(
                ft.Row(
                    controls=[tile(n, ic, c, cb, img) for n, ic, c, cb, img in chunk],
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                    spacing=0,
                )
            )

        clock = ft.Container(
            alignment=_align("center"),
            content=ft.Column(
                controls=[
                    ft.Text(datetime.now().strftime("%H:%M"), size=48,
                            weight=getattr(ft.FontWeight, "W_300",
                                           ft.FontWeight.NORMAL),
                            color="#202124"),
                    ft.Text(
                        datetime.now().strftime("%A, %d %b").capitalize(),
                        size=11, color="#5F6368",
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
            ),
        )

        dock = ft.Container(
            margin=_margin_sym(horizontal=18),
            padding=_padding_sym(vertical=12, horizontal=16),
            bgcolor="#FFFFFFCC",
            border_radius=26,
            shadow=ft.BoxShadow(
                blur_radius=16, spread_radius=0,
                color="#00000018", offset=ft.Offset(0, 4),
            ),
            content=ft.Row(
                controls=[
                    ft.Container(width=42, height=42, border_radius=13,
                                 bgcolor="#E3F2FD", alignment=_align("center"),
                                 content=ft.Icon(ft.Icons.PHONE_ROUNDED,
                                                 color="#1E88E5", size=20)),
                    ft.Container(width=42, height=42, border_radius=13,
                                 bgcolor="#E8F5E9", alignment=_align("center"),
                                 content=ft.Icon(ft.Icons.CHAT_ROUNDED,
                                                 color="#43A047", size=20)),
                    ft.Container(width=42, height=42, border_radius=13,
                                 bgcolor="#FCE4EC", alignment=_align("center"),
                                 content=ft.Icon(ft.Icons.CAMERA_ALT_ROUNDED,
                                                 color="#E91E63", size=20)),
                    ft.Container(width=42, height=42, border_radius=13,
                                 bgcolor="#FFF3E0", alignment=_align("center"),
                                 content=ft.Icon(ft.Icons.MAIL_ROUNDED,
                                                 color="#EF6C00", size=20)),
                ],
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
            ),
        )

        return ft.Container(
            expand=True,
            gradient=ft.LinearGradient(
                colors=["#F8FAFD", "#EDF2F8", "#E3EAF2"],
                begin=_align("top_left"), end=_align("bottom_right"),
            ),
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    status_bar("#3C4043"),
                    ft.Container(height=8),
                    clock,
                    ft.Container(expand=True),
                    ft.Container(
                        padding=_padding_sym(horizontal=10),
                        content=ft.Column(controls=filas, spacing=16),
                    ),
                    ft.Container(height=20),
                    dock,
                    ft.Container(height=8),
                ],
            ),
        )

    # ═══════════════════════════════════════════════════════════════
    # HELPERS PARA LA VISTA INICIO
    # ═══════════════════════════════════════════════════════════════
    def _saludo_dinamico():
        h = datetime.now().hour
        if h < 12:
            return "Buenos días"
        if h < 19:
            return "Buenas tardes"
        return "Buenas noches"

    def _greeting_row(af, nombre_corto):
        return ft.Container(
            padding=_padding_only(left=20, right=20, top=8),
            content=ft.Row(
                controls=[
                    ft.Container(
                        width=44, height=44, border_radius=50,
                        gradient=ft.LinearGradient(
                            colors=[PURPLE_DARK, PURPLE, PURPLE_LIGHT],
                            begin=_align("top_left"),
                            end=_align("bottom_right"),
                        ),
                        alignment=_align("center"),
                        shadow=ft.BoxShadow(
                            blur_radius=20, spread_radius=0,
                            color=f"{PURPLE}66",
                            offset=ft.Offset(0, 0),
                        ),
                        content=ft.Text(
                            nombre_corto[0].upper(),
                            color="white", size=18,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ),
                    ft.Container(width=12),
                    ft.Column(
                        controls=[
                            ft.Text(
                                f"{_saludo_dinamico()}, {nombre_corto} 👋",
                                color=TEXT, size=16,
                                weight=ft.FontWeight.BOLD,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(f"CC: {af['cc']}",
                                    color=TEXT_DIM, size=12),
                        ],
                        spacing=2, expand=True,
                    ),
                    ft.Container(
                        bgcolor=DARK_SURFACE_2,
                        border=_border_all(1, DARK_BORDER),
                        border_radius=12,
                        padding=_padding_sym(vertical=9, horizontal=14),
                        on_click=logout,
                        ink=True,
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.LOGOUT_ROUNDED,
                                        color=PURPLE_LIGHT, size=16),
                                ft.Text("Salir", color=PURPLE_LIGHT,
                                        size=12,
                                        weight=ft.FontWeight.W_600),
                            ],
                            spacing=6,
                            tight=True,
                        ),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
            ),
        )

    def _tab_header(titulo):
        def volver_inicio(e):
            state["tab"] = "inicio"
            state["sub"] = None
            render()

        return ft.Container(
            bgcolor=DARK_SURFACE,
            border=_border_only(bottom=ft.BorderSide(1, DARK_BORDER)),
            padding=_padding_only(left=0, right=0, top=0, bottom=10),
            content=ft.Column(
                controls=[
                    status_bar(TEXT),
                    ft.Container(
                        padding=_padding_only(left=8, right=15, top=0),
                        content=ft.Row(
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.ARROW_BACK_ROUNDED,
                                    icon_color=TEXT,
                                    on_click=volver_inicio,
                                ),
                                ft.Text(titulo, size=18,
                                        weight=ft.FontWeight.BOLD, color=TEXT),
                            ],
                        ),
                    ),
                ],
                spacing=0,
            ),
        )

    def _badge_count(n, color=RED):
        if n <= 0:
            return ft.Container(width=0, height=0)
        return ft.Container(
            bgcolor=color,
            border_radius=50,
            padding=_padding_sym(vertical=2, horizontal=8),
            alignment=_align("center"),
            content=ft.Text(str(n), color="white", size=10,
                            weight=ft.FontWeight.BOLD),
        )

    def _donut_dias(res):
        if not res:
            return ft.Container(width=0, height=0)

        dias, _ = res

        if dias > 5:
            color = GREEN
            label = "días"
        elif dias > 0:
            color = ORANGE
            label = "días"
        elif dias > -5:
            color = RED
            label = "vencido"
        else:
            color = "#DC2626"
            label = "en mora"

        texto_dias = str(abs(dias)) if dias < 0 else str(dias)

        return ft.Container(
            width=68, height=68, border_radius=34,
            bgcolor=color,
            alignment=_align("center"),
            content=ft.Container(
                width=58, height=58, border_radius=29,
                bgcolor=DARK_SURFACE,
                alignment=_align("center"),
                content=ft.Column(
                    controls=[
                        ft.Text(texto_dias, size=19,
                                weight=ft.FontWeight.BOLD, color=color),
                        ft.Text(label, size=8, color=TEXT_MUTED),
                    ],
                    spacing=0,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ),
        )

    def _progreso_mes(res):
        if not res:
            return ft.Container(width=0, height=0)

        dias, _ = res

        if dias <= 0:
            progreso = 1.0
            color = RED
            label = "100%"
        else:
            transcurridos = max(0, min(30, 30 - dias))
            progreso = transcurridos / 30
            label = f"{int(progreso * 100)}%"
            if dias > 5:
                color = GREEN
            elif dias > 0:
                color = ORANGE
            else:
                color = RED

        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Ciclo de pago actual", size=11,
                                color=TEXT_MUTED),
                        ft.Text(label, size=11, color=color,
                                weight=ft.FontWeight.BOLD),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(height=4),
                ft.ProgressBar(
                    value=progreso,
                    color=color,
                    bgcolor=DARK_SURFACE_2,
                    border_radius=3,
                    height=6,
                ),
            ],
            spacing=0,
        )

    def _chips_servicios():
        af = state["afiliado"]
        servicios = [
            ("EPS", af.get("eps")),
            ("ARL", af.get("arl")),
            ("Pensión", af.get("pension")),
            ("Caja", af.get("caja_compensacion")),
        ]

        chips = []
        for label, valor in servicios:
            activo = bool(valor)
            color = GREEN if activo else TEXT_MUTED
            icon = ft.Icons.CHECK_ROUNDED if activo else ft.Icons.CLOSE_ROUNDED
            chips.append(
                ft.Container(
                    bgcolor=f"{color}20",
                    border=_border_all(1, f"{color}55"),
                    border_radius=50,
                    padding=_padding_sym(vertical=5, horizontal=10),
                    content=ft.Row(
                        controls=[
                            ft.Icon(icon, color=color, size=12),
                            ft.Text(label, color=color, size=11,
                                    weight=ft.FontWeight.W_600),
                        ],
                        spacing=4,
                        tight=True,
                    ),
                )
            )

        return ft.Container(
            bgcolor=DARK_SURFACE,
            border_radius=16,
            padding=12,
            border=_border_all(1, DARK_BORDER),
            on_click=lambda e: go_tab("servicios"),
            ink=True,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.SHIELD_ROUNDED, size=16,
                                    color=PURPLE),
                            ft.Text("Servicios activos", size=13,
                                    weight=ft.FontWeight.BOLD, color=TEXT),
                            ft.Container(expand=True),
                            ft.Text("Ver →", size=11, color=PURPLE_LIGHT,
                                    weight=ft.FontWeight.W_600),
                        ],
                        spacing=8,
                    ),
                    ft.Container(height=8),
                    ft.Row(controls=chips, spacing=6,
                           scroll=ft.ScrollMode.AUTO),
                ],
                spacing=0,
            ),
        )

    def _mini_beneficiarios():
        bens = state.get("beneficiarios", [])
        if not bens:
            return None

        items = []
        for b in bens[:3]:
            nombre = (b.get("nombre") or "?").split()[0]
            inicial = nombre[0].upper() if nombre else "?"
            items.append(
                ft.Container(
                    width=62,
                    content=ft.Column(
                        controls=[
                            ft.Container(
                                width=44, height=44, border_radius=50,
                                gradient=ft.LinearGradient(
                                    colors=[PURPLE_DARK, PURPLE_LIGHT],
                                    begin=_align("top_left"),
                                    end=_align("bottom_right"),
                                ),
                                alignment=_align("center"),
                                content=ft.Text(
                                    inicial, color="white", size=18,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ),
                            ft.Text(nombre, size=10, color=TEXT_DIM,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    text_align=ft.TextAlign.CENTER),
                        ],
                        spacing=4,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )

        extras = len(bens) - 3
        if extras > 0:
            items.append(
                ft.Container(
                    width=62,
                    content=ft.Column(
                        controls=[
                            ft.Container(
                                width=44, height=44, border_radius=50,
                                bgcolor=DARK_SURFACE_2,
                                border=_border_all(1, DARK_BORDER),
                                alignment=_align("center"),
                                content=ft.Text(f"+{extras}", color=TEXT_DIM,
                                                size=14,
                                                weight=ft.FontWeight.BOLD),
                            ),
                            ft.Text("más", size=10, color=TEXT_MUTED),
                        ],
                        spacing=4,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )

        return ft.Container(
            bgcolor=DARK_SURFACE, border_radius=16, padding=15,
            border=_border_all(1, DARK_BORDER),
            on_click=lambda e: _navegar(sub="beneficiarios"),
            ink=True,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.PEOPLE_ROUNDED, size=18,
                                    color=PURPLE),
                            ft.Text("Tus beneficiarios", size=14,
                                    weight=ft.FontWeight.BOLD, color=TEXT),
                            ft.Container(expand=True),
                            ft.Text("Ver todos →", size=11,
                                    color=PURPLE_LIGHT,
                                    weight=ft.FontWeight.W_600),
                        ],
                        spacing=8,
                    ),
                    ft.Container(height=10),
                    ft.Row(controls=items, spacing=14),
                ],
                spacing=0,
            ),
        )

    # ═══════════════════════════════════════════════════════════════
    # MAIN VIEW (dark)
    # ═══════════════════════════════════════════════════════════════
    def main_view():
        af = state["afiliado"]
        nombre_corto = (af.get("nombre") or "Afiliado").split()[0]

        if state["sub"]:
            return sub_view()

        contenidos = {
            "inicio": view_inicio,
            "datos": view_datos,
            "servicios": view_servicios,
            "pagos": view_pagos,
            "mas": view_mas,
        }
        contenido = contenidos.get(state["tab"], view_inicio)()

        titulos_tabs = {
            "datos": "Mis Datos",
            "servicios": "Mis Servicios",
            "pagos": "Mis Pagos",
            "mas": "Más Opciones",
        }

        if state["tab"] == "inicio":
            header = ft.Container(
                bgcolor=DARK_SURFACE,
                border=_border_only(bottom=ft.BorderSide(1, DARK_BORDER)),
                padding=_padding_only(left=0, right=0, top=0, bottom=14),
                content=ft.Column(
                    controls=[status_bar(TEXT),
                              _greeting_row(af, nombre_corto)],
                    spacing=0,
                ),
            )
        else:
            header = _tab_header(titulos_tabs.get(state["tab"], ""))

        return ft.Column(
            controls=[
                header,
                ft.Container(expand=True, content=contenido, bgcolor=DARK_BG),
                bottom_nav(),
            ],
            spacing=0, expand=True,
        )

    def bottom_nav():
        chat_unread = state.get("chat_unread", 0)
        pqr_abiertos = state.get("pqr_abiertos", 0)
        # Badge combinado para la pestaña "Más"
        mas_badge = chat_unread + pqr_abiertos

        items = [
            ("inicio", ft.Icons.HOME_ROUNDED, "Inicio", 0),
            ("datos", ft.Icons.PERSON_ROUNDED, "Datos", 0),
            ("servicios", ft.Icons.SHIELD_ROUNDED, "Servicios", 0),
            ("pagos", ft.Icons.PAYMENTS_ROUNDED, "Pagos", 0),
            ("mas", ft.Icons.MORE_HORIZ_ROUNDED, "Más", mas_badge),
        ]

        def mk_handler(key):
            def h(e):
                if state["tab"] == key and state["sub"] is None:
                    return
                _navegar(tab=key, sub=None)
            return h

        def nav_item(key, icon, label, badge):
            activo = state["tab"] == key
            icon_ctrl = ft.Stack(
                controls=[
                    ft.Icon(icon, size=22,
                            color=PURPLE if activo else TEXT_MUTED),
                    ft.Container(
                        right=-8, top=-4,
                        content=_badge_count(badge, color=RED),
                    ),
                ],
            ) if badge > 0 else ft.Icon(
                icon, size=22, color=PURPLE if activo else TEXT_MUTED
            )

            return ft.Container(
                expand=True, on_click=mk_handler(key), ink=True,
                border_radius=12,
                padding=_padding_sym(vertical=6),
                content=ft.Column(
                    controls=[
                        icon_ctrl,
                        ft.Text(label, size=10,
                                color=PURPLE if activo else TEXT_MUTED,
                                weight=ft.FontWeight.BOLD if activo
                                else ft.FontWeight.NORMAL),
                    ],
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )

        return ft.Container(
            bgcolor=DARK_SURFACE,
            padding=_padding_sym(vertical=6, horizontal=4),
            border=_border_only(top=ft.BorderSide(1, DARK_BORDER)),
            content=ft.Row(
                controls=[nav_item(k, i, l, b) for k, i, l, b in items],
                spacing=0,
            ),
        )

    def card(content, padding=15):
        return ft.Container(
            bgcolor=DARK_SURFACE, border_radius=16, padding=padding,
            border=_border_all(1, DARK_BORDER),
            content=content,
        )

    def section_title(text, icon=None):
        ctrls = []
        if icon:
            ctrls.append(ft.Icon(icon, size=18, color=PURPLE))
        ctrls.append(ft.Text(text, size=14, weight=ft.FontWeight.BOLD, color=TEXT))
        return ft.Row(controls=ctrls, spacing=8)

    def info_row(label, value):
        return ft.Row(
            controls=[
                ft.Text(label, size=12, color=TEXT_MUTED, width=120),
                ft.Text(value or "—", size=13, color=TEXT,
                        expand=True, text_align=ft.TextAlign.RIGHT),
            ]
        )

    def go_tab(key):
        if state["tab"] == key and state["sub"] is None:
            return
        _navegar(tab=key, sub=None)

    # ═══════════════════════════════════════════════════════════════
    # VISTA: INICIO
    # ═══════════════════════════════════════════════════════════════
    def view_inicio():
        af = state["afiliado"]
        solicitud = state.get("solicitud")
        notifs = state.get("notificaciones", [])[:3]
        total_notifs = len(state.get("notificaciones", []))
        resultado = dias_prox_pago(af.get("fecha_pago"))

        controls = []

        if af.get("archivado"):
            estado_txt, color, icono = "Archivado", TEXT_MUTED, ft.Icons.ARCHIVE_ROUNDED
        elif af.get("retirado"):
            estado_txt, color, icono = "Retirado", RED, ft.Icons.CANCEL_ROUNDED
        else:
            estado_txt, color, icono = "Activo", GREEN, ft.Icons.CHECK_CIRCLE_ROUNDED

        controls.append(
            card(
                ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(icono, color=color, size=30),
                                ft.Column(
                                    controls=[
                                        ft.Text("Estado de afiliación",
                                                size=11, color=TEXT_MUTED),
                                        ft.Text(estado_txt, size=18,
                                                weight=ft.FontWeight.BOLD,
                                                color=color),
                                    ],
                                    spacing=0, expand=True,
                                ),
                                _donut_dias(resultado),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Divider(height=1, color=DARK_BORDER),
                        ft.Row(
                            controls=[
                                ft.Column(
                                    controls=[
                                        ft.Text("Último pago", size=11,
                                                color=TEXT_MUTED),
                                        ft.Text(fmt_fecha(af.get("fecha_pago")),
                                                size=14,
                                                weight=ft.FontWeight.BOLD,
                                                color=TEXT),
                                    ],
                                    spacing=2, expand=True,
                                ),
                                ft.Column(
                                    controls=[
                                        ft.Text("Próximo vencimiento",
                                                size=11, color=TEXT_MUTED),
                                        ft.Text(
                                            resultado[1].strftime("%d/%m/%Y") if resultado else "—",
                                            size=14,
                                            weight=ft.FontWeight.BOLD,
                                            color=RED if resultado and resultado[0] < 0 else TEXT,
                                        ),
                                    ],
                                    spacing=2, expand=True,
                                    horizontal_alignment=ft.CrossAxisAlignment.END,
                                ),
                            ]
                        ),
                        ft.Container(height=4),
                        _barra_dias(resultado),
                        ft.Container(height=10),
                        _progreso_mes(resultado),
                    ],
                    spacing=12,
                )
            )
        )

        if solicitud:
            controls.append(
                ft.Container(
                    bgcolor=f"{ORANGE}15",
                    border=_border_all(1, f"{ORANGE}55"),
                    border_radius=16, padding=15,
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_ROUNDED,
                                            color=ORANGE, size=22),
                                    ft.Text("Tienes una solicitud de pago pendiente",
                                            size=13, weight=ft.FontWeight.BOLD,
                                            color=ORANGE, expand=True),
                                ]
                            ),
                            ft.Text(
                                f"Estado: {solicitud['estado'].replace('_', ' ').title()}",
                                size=12, color=TEXT_DIM,
                            ),
                            ft.Text(f"Monto: {fmt_money(solicitud.get('monto'))}",
                                    size=13, weight=ft.FontWeight.BOLD,
                                    color=ORANGE),
                            ft.Container(height=6),
                            ft.Container(
                                bgcolor=ORANGE, border_radius=10, padding=12,
                                alignment=_align("center"),
                                on_click=lambda e: go_tab("pagos"), ink=True,
                                content=ft.Text("Ver detalles", color="#0F0F1E",
                                                weight=ft.FontWeight.BOLD, size=13),
                            ),
                        ],
                        spacing=6,
                    ),
                )
            )

        total_pagos = sum(float(p.get("valor", 0) or 0) for p in state.get("pagos", []))
        num_pagos = len(state.get("pagos", []))

        controls.append(
            card(
                ft.Row(
                    controls=[
                        _stat_box(str(num_pagos), "Pagos registrados",
                                  ft.Icons.RECEIPT_LONG_ROUNDED, PURPLE,
                                  f"{PURPLE}20"),
                        _stat_box(fmt_money(total_pagos), "Total pagado",
                                  ft.Icons.ATTACH_MONEY_ROUNDED, GREEN,
                                  f"{GREEN}20"),
                        _stat_box(str(len(state.get("beneficiarios", []))),
                                  "Beneficiarios",
                                  ft.Icons.PEOPLE_ROUNDED, PURPLE_LIGHT,
                                  f"{PURPLE_LIGHT}20"),
                    ],
                )
            )
        )

        controls.append(_chips_servicios())

        mini_bens = _mini_beneficiarios()
        if mini_bens:
            controls.append(mini_bens)

        if notifs:
            filas = []
            for n in notifs:
                tipo = n.get("tipo", "")
                es_alerta = ("Mora" in tipo or "Suspensión" in tipo
                             or "Alerta" in tipo)
                c = ORANGE if es_alerta else BLUE_ACC
                ic = (ft.Icons.WARNING_ROUNDED if es_alerta
                      else ft.Icons.INFO_ROUNDED)
                filas.append(
                    ft.Container(
                        padding=_padding_sym(vertical=10),
                        border=_border_only(bottom=ft.BorderSide(1, DARK_BORDER)),
                        content=ft.Row(
                            controls=[
                                ft.Icon(ic, color=c, size=18),
                                ft.Column(
                                    controls=[
                                        ft.Text(tipo, size=11, color=TEXT_MUTED),
                                        ft.Text((n.get("mensaje", "") or "")[:110],
                                                size=12, color=TEXT_DIM),
                                    ],
                                    spacing=2, expand=True,
                                ),
                            ]
                        ),
                    )
                )
            controls.append(
                card(
                    ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.NOTIFICATIONS_ROUNDED,
                                            size=18, color=PURPLE),
                                    ft.Text("Notificaciones recientes",
                                            size=14,
                                            weight=ft.FontWeight.BOLD,
                                            color=TEXT),
                                    _badge_count(total_notifs),
                                ],
                                spacing=8,
                            ),
                            ft.Container(height=4),
                            *filas,
                        ],
                        spacing=5,
                    )
                )
            )

        return ft.Container(
            padding=15,
            content=ft.Column(controls=controls, spacing=12,
                              scroll=ft.ScrollMode.AUTO),
            expand=True,
        )

    def _stat_box(valor, label, icono, color, bg):
        return ft.Column(
            controls=[
                ft.Container(
                    width=42, height=42, border_radius=12, bgcolor=bg,
                    alignment=_align("center"),
                    content=ft.Icon(icono, color=color, size=22),
                ),
                ft.Text(valor, size=16, weight=ft.FontWeight.BOLD, color=TEXT),
                ft.Text(label, size=10, color=TEXT_MUTED,
                        text_align=ft.TextAlign.CENTER),
            ],
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )

    def _barra_dias(res):
        if not res:
            return ft.Text("Sin registro de pagos", size=11, color=TEXT_MUTED,
                           text_align=ft.TextAlign.CENTER)
        dias, _ = res
        if dias > 5:
            color, ic, msg = GREEN, ft.Icons.CHECK_CIRCLE_ROUNDED, f"Al día · {dias} días para el próximo pago"
        elif dias > 0:
            color, ic, msg = ORANGE, ft.Icons.SCHEDULE_ROUNDED, f"Próximo a vencer · {dias} días"
        elif dias > -5:
            color, ic, msg = RED, ft.Icons.WARNING_ROUNDED, f"Vencido hace {abs(dias)} días"
        else:
            color, ic, msg = "#DC2626", ft.Icons.ERROR_ROUNDED, f"En mora · {abs(dias)} días"

        return ft.Container(
            bgcolor=f"{color}20", border_radius=10, padding=10,
            content=ft.Row(
                controls=[
                    ft.Icon(ic, color=color, size=18),
                    ft.Text(msg, size=12, color=color,
                            weight=ft.FontWeight.BOLD, expand=True),
                ],
                spacing=8,
            ),
        )

    # ═══════════════════════════════════════════════════════════════
    # VISTA: DATOS
    # ═══════════════════════════════════════════════════════════════
    def view_datos():
        af = state["afiliado"]

        def tf(label, value, icon, kb=None):
            return ft.TextField(
                label=label, value=value or "",
                keyboard_type=kb,
                border=ft.InputBorder.OUTLINE,
                border_color=DARK_BORDER,
                focused_border_color=PURPLE,
                border_radius=12, filled=True, bgcolor=DARK_SURFACE_2,
                label_style=ft.TextStyle(color=TEXT_DIM),
                text_style=ft.TextStyle(color=TEXT),
                cursor_color=PURPLE,
                prefix_icon=icon,
            )

        celular_tf = tf("Celular", af.get("celular"), ft.Icons.PHONE_ROUNDED,
                        ft.KeyboardType.PHONE)
        correo_tf = tf("Correo electrónico", af.get("correo"),
                       ft.Icons.EMAIL_ROUNDED, ft.KeyboardType.EMAIL)
        direccion_tf = tf("Dirección", af.get("direccion"),
                          ft.Icons.HOME_ROUNDED)

        def guardar(e):
            if correo_tf.value and "@" not in correo_tf.value:
                if hasattr(correo_tf, "error"):
                    correo_tf.error = "Correo no válido"
                else:
                    correo_tf.error_text = "Correo no válido"
                mostrar_alerta("El correo electrónico no es válido (falta @).",
                               "warning")
                page.update()
                return
            if hasattr(correo_tf, "error"):
                correo_tf.error = None
            else:
                correo_tf.error_text = None
            try:
                db.update_datos_cliente(
                    af["cc"],
                    celular_tf.value or "",
                    correo_tf.value or "",
                    direccion_tf.value or "",
                )
                cargar_datos()
                mostrar_alerta("Datos actualizados correctamente", "success")
                render()
            except Exception as ex:
                mostrar_alerta(f"Error: {ex}", "error")

        return ft.Container(
            padding=15,
            content=ft.Column(
                controls=[
                    card(
                        ft.Column(
                            controls=[
                                section_title("Información personal",
                                              ft.Icons.BADGE_ROUNDED),
                                ft.Container(height=8),
                                info_row("Cédula", af.get("cc", "")),
                                info_row("Nombre", af.get("nombre", "")),
                                info_row("Fecha ingreso",
                                         fmt_fecha(af.get("fecha_ingreso"))),
                            ],
                            spacing=8,
                        )
                    ),
                    card(
                        ft.Column(
                            controls=[
                                section_title("Datos de contacto",
                                              ft.Icons.CONTACT_PHONE_ROUNDED),
                                ft.Text("Puedes actualizar tus datos de contacto",
                                        size=11, color=TEXT_MUTED),
                                ft.Container(height=8),
                                celular_tf, correo_tf, direccion_tf,
                                ft.Container(height=5),
                                ft.Container(
                                    border_radius=12, padding=14,
                                    gradient=ft.LinearGradient(
                                        colors=[PURPLE_DARK, PURPLE],
                                        begin=_align("top_left"),
                                        end=_align("bottom_right"),
                                    ),
                                    alignment=_align("center"),
                                    on_click=guardar, ink=True,
                                    shadow=ft.BoxShadow(
                                        blur_radius=35, spread_radius=0,
                                        color="#8B5CF6CC",
                                        offset=ft.Offset(0, 0),
                                    ),
                                    content=ft.Row(
                                        controls=[
                                            ft.Icon(ft.Icons.SAVE_ROUNDED,
                                                    color="white", size=18),
                                            ft.Text("Guardar cambios",
                                                    color="white",
                                                    weight=ft.FontWeight.BOLD,
                                                    size=14),
                                        ],
                                        alignment=ft.MainAxisAlignment.CENTER,
                                        spacing=8,
                                    ),
                                ),
                            ],
                            spacing=8,
                        )
                    ),
                ],
                spacing=12, scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
        )

    # ═══════════════════════════════════════════════════════════════
    # VISTA: SERVICIOS
    # ═══════════════════════════════════════════════════════════════
    def view_servicios():
        af = state["afiliado"]
        servicios = [
            ("EPS", af.get("eps"), ft.Icons.LOCAL_HOSPITAL_ROUNDED, PURPLE),
            ("ARL", af.get("arl"), ft.Icons.HEALTH_AND_SAFETY_ROUNDED, ORANGE),
            ("Pensión", af.get("pension"), ft.Icons.SAVINGS_ROUNDED, GREEN),
            ("Caja de Compensación", af.get("caja_compensacion"),
             ft.Icons.FAMILY_RESTROOM_ROUNDED, PURPLE_LIGHT),
        ]

        cards = []
        for label, valor, icono, color in servicios:
            activo = bool(valor)
            cards.append(
                ft.Container(
                    bgcolor=DARK_SURFACE, border_radius=14, padding=15,
                    border=_border_all(1, DARK_BORDER),
                    content=ft.Row(
                        controls=[
                            ft.Container(
                                width=48, height=48, border_radius=12,
                                bgcolor=f"{color}25" if activo else DARK_SURFACE_2,
                                alignment=_align("center"),
                                content=ft.Icon(icono,
                                                color=color if activo else TEXT_MUTED,
                                                size=26),
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text(label, size=12, color=TEXT_MUTED),
                                    ft.Text(valor or "No afiliado", size=14,
                                            weight=ft.FontWeight.BOLD,
                                            color=TEXT if activo else TEXT_MUTED),
                                ],
                                spacing=2, expand=True,
                            ),
                            ft.Icon(
                                ft.Icons.CHECK_CIRCLE_ROUNDED if activo
                                else ft.Icons.REMOVE_CIRCLE_OUTLINE,
                                color=color if activo else TEXT_MUTED, size=22,
                            ),
                        ]
                    ),
                )
            )

        return ft.Container(
            padding=15,
            content=ft.Column(
                controls=[
                    card(
                        ft.Column(
                            controls=[
                                section_title("Mis servicios",
                                              ft.Icons.SHIELD_ROUNDED),
                                ft.Text("Estos son los servicios a los que estás afiliado",
                                        size=11, color=TEXT_MUTED),
                            ],
                            spacing=5,
                        )
                    ),
                    *cards,
                ],
                spacing=10, scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
        )

    # ═══════════════════════════════════════════════════════════════
    # VISTA: PAGOS
    # ═══════════════════════════════════════════════════════════════
    def view_pagos():
        pagos = state.get("pagos", [])
        solicitud = state.get("solicitud")
        total = sum(float(p.get("valor", 0) or 0) for p in pagos)
        controls = []

        if solicitud:
            controls.append(
                ft.Container(
                    bgcolor=f"{BLUE_ACC}15",
                    border=_border_all(1, f"{BLUE_ACC}55"),
                    border_radius=14, padding=15,
                    content=ft.Column(
                        controls=[
                            section_title("Solicitud de pago activa",
                                          ft.Icons.REQUEST_QUOTE_ROUNDED),
                            ft.Container(height=4),
                            info_row("Estado",
                                     solicitud.get("estado", "").replace("_", " ").title()),
                            info_row("Monto", fmt_money(solicitud.get("monto"))),
                            info_row("Mes", solicitud.get("mes", "")),
                            info_row("Método", solicitud.get("metodo_pago", "")),
                            ft.Container(height=6),
                            ft.Container(
                                border_radius=10, padding=12,
                                gradient=ft.LinearGradient(
                                    colors=[PURPLE_DARK, PURPLE],
                                    begin=_align("top_left"),
                                    end=_align("bottom_right"),
                                ),
                                alignment=_align("center"),
                                on_click=lambda e: confirmar_solicitud(solicitud),
                                ink=True,
                                shadow=ft.BoxShadow(
                                    blur_radius=30, spread_radius=0,
                                    color="#8B5CF6BB", offset=ft.Offset(0, 0),
                                ),
                                content=ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.CHECK_ROUNDED,
                                                color="white", size=18),
                                        ft.Text("Confirmar que ya pagué",
                                                color="white",
                                                weight=ft.FontWeight.BOLD,
                                                size=13),
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=8,
                                ),
                            ),
                        ],
                        spacing=6,
                    ),
                )
            )

        controls.append(
            card(
                ft.Row(
                    controls=[
                        ft.Column(
                            controls=[
                                ft.Text("Total pagado", size=11,
                                        color=TEXT_MUTED),
                                ft.Text(fmt_money(total), size=22,
                                        weight=ft.FontWeight.BOLD, color=GREEN),
                            ],
                            spacing=2, expand=True,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text("Nº de pagos", size=11,
                                        color=TEXT_MUTED),
                                ft.Text(str(len(pagos)), size=22,
                                        weight=ft.FontWeight.BOLD, color=TEXT),
                            ],
                            spacing=2,
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                        ),
                    ]
                )
            )
        )

        if not pagos:
            controls.append(
                card(
                    ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.INBOX_ROUNDED, size=60,
                                    color=TEXT_MUTED),
                            ft.Text("No tienes pagos registrados", size=14,
                                    color=TEXT_MUTED,
                                    text_align=ft.TextAlign.CENTER),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    )
                )
            )
        else:
            filas = []
            for p in pagos:
                filas.append(
                    ft.Container(
                        padding=_padding_sym(vertical=10),
                        border=_border_only(bottom=ft.BorderSide(1, DARK_BORDER)),
                        content=ft.Row(
                            controls=[
                                ft.Container(
                                    width=40, height=40, border_radius=10,
                                    bgcolor=f"{GREEN}20",
                                    alignment=_align("center"),
                                    content=ft.Icon(ft.Icons.ATTACH_MONEY_ROUNDED,
                                                    color=GREEN, size=20),
                                ),
                                ft.Column(
                                    controls=[
                                        ft.Text(p.get("servicio", "Pago"), size=13,
                                                weight=ft.FontWeight.BOLD,
                                                color=TEXT),
                                        ft.Text(
                                            f"{fmt_fecha(p.get('fecha'))} · "
                                            f"{p.get('metodo_pago', '')}",
                                            size=11, color=TEXT_MUTED,
                                        ),
                                    ],
                                    spacing=2, expand=True,
                                ),
                                ft.Text(fmt_money(p.get("valor")), size=14,
                                        weight=ft.FontWeight.BOLD, color=GREEN),
                            ]
                        ),
                    )
                )
            controls.append(
                card(
                    ft.Column(
                        controls=[
                            section_title("Historial de pagos",
                                          ft.Icons.HISTORY_ROUNDED),
                            ft.Container(height=4),
                            *filas,
                        ],
                        spacing=5,
                    )
                )
            )

        return ft.Container(
            padding=15,
            content=ft.Column(controls=controls, spacing=12,
                              scroll=ft.ScrollMode.AUTO),
            expand=True,
        )

    def confirmar_solicitud(sol):
        def yes(e):
            page.close(dlg)
            try:
                db.confirmar_solicitud(sol["id"])
                cargar_datos()
                mostrar_alerta("¡Listo! Tu pago ha sido confirmado", "success")
                render()
            except Exception as ex:
                mostrar_alerta(f"Error: {ex}", "error")

        def no(e):
            page.close(dlg)

        dlg = ft.AlertDialog(
            title=ft.Text("Confirmar pago"),
            content=ft.Text(
                f"¿Confirmas que ya realizaste el pago de "
                f"{fmt_money(sol.get('monto'))} para el mes {sol.get('mes', '')}?"
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=no),
                ft.FilledButton("Sí, confirmar", on_click=yes),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    # ═══════════════════════════════════════════════════════════════
    # VISTA: MÁS  (con nuevos módulos)
    # ═══════════════════════════════════════════════════════════════
    def view_mas():
        chat_unread = state.get("chat_unread", 0)
        pqr_abiertos = state.get("pqr_abiertos", 0)
        num_facturas = len(state.get("facturas", []))

        items = [
            ("Chat con Administración",
             f"{chat_unread} mensajes sin leer" if chat_unread else "En línea",
             ft.Icons.CHAT_ROUNDED, PURPLE, "chat", chat_unread),
            ("PQR",
             f"{pqr_abiertos} abiertos" if pqr_abiertos else "Sin pendientes",
             ft.Icons.FORUM_ROUNDED, ORANGE, "pqr", pqr_abiertos),
            ("Mi código QR",
             "Comparte tu identificación",
             ft.Icons.QR_CODE_ROUNDED, GREEN, "qr", 0),
            ("Mis Facturas",
             f"{num_facturas} disponibles" if num_facturas else "Sin facturas",
             ft.Icons.RECEIPT_ROUNDED, BLUE_ACC, "facturas", 0),
            ("Beneficiarios",
             f"{len(state.get('beneficiarios', []))} registrados",
             ft.Icons.PEOPLE_ROUNDED, PURPLE_LIGHT, "beneficiarios", 0),
            ("Notificaciones",
             f"{len(state.get('notificaciones', []))} mensajes",
             ft.Icons.NOTIFICATIONS_ROUNDED, ORANGE, "notificaciones", 0),
            ("Incapacidades",
             f"{len(state.get('incapacidades', []))} registradas",
             ft.Icons.MEDICAL_SERVICES_ROUNDED, BLUE_ACC, "incapacidades", 0),
            ("Certificados",
             "Descargar PDF",
             ft.Icons.DESCRIPTION_ROUNDED, GREEN, "certificados", 0),
        ]

        cards = []

        def mk(key):
            def h(e):
                _navegar(sub=key)
            return h

        for titulo, sub, icono, color, key, badge in items:
            card_content = ft.Row(
                controls=[
                    ft.Container(
                        width=44, height=44, border_radius=12,
                        bgcolor=f"{color}25",
                        alignment=_align("center"),
                        content=ft.Icon(icono, color=color, size=22),
                    ),
                    ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(titulo, size=14,
                                            weight=ft.FontWeight.BOLD,
                                            color=TEXT),
                                    _badge_count(badge, color=color),
                                ],
                                spacing=8,
                            ),
                            ft.Text(sub, size=11, color=TEXT_MUTED),
                        ],
                        spacing=2, expand=True,
                    ),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED,
                            color=TEXT_MUTED),
                ]
            )
            cards.append(
                ft.Container(
                    bgcolor=DARK_SURFACE, border_radius=14, padding=15,
                    border=_border_all(1, DARK_BORDER),
                    on_click=mk(key), ink=True,
                    content=card_content,
                )
            )

        emp = db.get_empresa()
        cards.append(
            card(
                ft.Column(
                    controls=[
                        section_title("Contacto",
                                      ft.Icons.SUPPORT_AGENT_ROUNDED),
                        ft.Container(height=6),
                        info_row("Empresa", emp.get("nombre", "SaluApp")),
                        info_row("Teléfono", emp.get("telefono", "")),
                        info_row("Correo", emp.get("correo", "")),
                        info_row("Dirección", emp.get("direccion", "")),
                    ],
                    spacing=8,
                )
            )
        )

        return ft.Container(
            padding=15,
            content=ft.Column(
                controls=[
                    card(
                        ft.Column(
                            controls=[
                                section_title("Más opciones",
                                              ft.Icons.APPS_ROUNDED),
                                ft.Text("Accede a toda tu información",
                                        size=11, color=TEXT_MUTED),
                            ],
                            spacing=5,
                        )
                    ),
                    *cards,
                    ft.Container(
                        alignment=_align("center"), padding=15,
                        content=ft.Text("SaluApp · Portal del Cliente v2.0",
                                        size=11, color=TEXT_MUTED),
                    ),
                ],
                spacing=10, scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
        )

    # ═══════════════════════════════════════════════════════════════
    # SUB-VISTAS
    # ═══════════════════════════════════════════════════════════════
    def sub_view():
        key = state["sub"]
        handlers = {
            "beneficiarios": sub_beneficiarios,
            "notificaciones": sub_notificaciones,
            "incapacidades": sub_incapacidades,
            "certificados": sub_certificados,
            "chat": sub_chat,
            "pqr": sub_pqr,
            "qr": sub_qr,
            "facturas": sub_facturas,
        }
        contenido, titulo = handlers.get(key, (None, "Más"))()

        def volver(e):
            state["chat_poll_token"] = state.get("chat_poll_token", 0) + 1
            if state["history"]:
                snap = state["history"].pop()
                _restaurar(snap)
            else:
                state["sub"] = None
            render()

        return ft.Column(
            controls=[
                ft.Container(
                    bgcolor=DARK_SURFACE,
                    padding=_padding_only(left=0, right=0, top=0, bottom=10),
                    border=_border_only(bottom=ft.BorderSide(1, DARK_BORDER)),
                    content=ft.Column(
                        controls=[
                            status_bar(TEXT),
                            ft.Container(
                                padding=_padding_only(left=8, right=15, top=0),
                                content=ft.Row(
                                    controls=[
                                        ft.IconButton(
                                            icon=ft.Icons.ARROW_BACK_ROUNDED,
                                            icon_color=TEXT,
                                            on_click=volver,
                                        ),
                                        ft.Text(titulo, size=18,
                                                weight=ft.FontWeight.BOLD,
                                                color=TEXT),
                                    ],
                                ),
                            ),
                        ],
                        spacing=0,
                    ),
                ),
                ft.Container(expand=True, content=contenido, bgcolor=DARK_BG),
            ],
            spacing=0, expand=True,
        )

    def sub_beneficiarios():
        bens = state.get("beneficiarios", [])
        if not bens:
            contenido = card(
                ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.PEOPLE_OUTLINE_ROUNDED, size=60,
                                color=TEXT_MUTED),
                        ft.Text("No tienes beneficiarios registrados", size=14,
                                color=TEXT_MUTED,
                                text_align=ft.TextAlign.CENTER),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                )
            )
        else:
            items = []
            for b in bens:
                items.append(
                    card(
                        ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Container(
                                            width=40, height=40, border_radius=50,
                                            bgcolor=f"{PURPLE_LIGHT}25",
                                            alignment=_align("center"),
                                            content=ft.Icon(ft.Icons.PERSON_ROUNDED,
                                                            color=PURPLE_LIGHT,
                                                            size=20),
                                        ),
                                        ft.Column(
                                            controls=[
                                                ft.Text(b.get("nombre", ""), size=14,
                                                        weight=ft.FontWeight.BOLD,
                                                        color=TEXT),
                                                ft.Text(b.get("tipo", ""), size=11,
                                                        color=TEXT_MUTED),
                                            ],
                                            spacing=2, expand=True,
                                        ),
                                    ]
                                ),
                                ft.Divider(height=1, color=DARK_BORDER),
                                info_row("Documento",
                                         b.get("documento_identidad", "")),
                                info_row("Fecha nac.",
                                         fmt_fecha(b.get("fecha_nacimiento"))),
                                info_row("Teléfono", b.get("telefono", "")),
                            ],
                            spacing=6,
                        )
                    )
                )
            contenido = ft.Column(controls=items, spacing=10,
                                  scroll=ft.ScrollMode.AUTO)
        return ft.Container(padding=15, content=contenido,
                            expand=True), "Beneficiarios"

    def sub_notificaciones():
        notifs = state.get("notificaciones", [])
        if not notifs:
            contenido = card(
                ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.NOTIFICATIONS_OFF_ROUNDED, size=60,
                                color=TEXT_MUTED),
                        ft.Text("No tienes notificaciones", size=14,
                                color=TEXT_MUTED,
                                text_align=ft.TextAlign.CENTER),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                )
            )
        else:
            items = []
            for n in notifs:
                tipo = n.get("tipo", "")
                es_alerta = ("Mora" in tipo or "Suspensión" in tipo)
                color = RED if es_alerta else BLUE_ACC
                items.append(
                    card(
                        ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.NOTIFICATIONS_ROUNDED,
                                                color=color, size=20),
                                        ft.Column(
                                            controls=[
                                                ft.Text(tipo, size=13,
                                                        weight=ft.FontWeight.BOLD,
                                                        color=color),
                                                ft.Text(fmt_fecha(n.get("fecha")),
                                                        size=11, color=TEXT_MUTED),
                                            ],
                                            spacing=2, expand=True,
                                        ),
                                        ft.Container(
                                            bgcolor=f"{GREEN}25" if n.get("estado") == "Enviada"
                                            else f"{ORANGE}25",
                                            border_radius=8,
                                            padding=_padding_sym(horizontal=8,
                                                                 vertical=3),
                                            content=ft.Text(n.get("estado", ""),
                                                            size=10,
                                                            color=GREEN
                                                            if n.get("estado") == "Enviada"
                                                            else ORANGE),
                                        ),
                                    ]
                                ),
                                ft.Text(n.get("mensaje", ""), size=12,
                                        color=TEXT_DIM),
                            ],
                            spacing=8,
                        )
                    )
                )
            contenido = ft.Column(controls=items, spacing=10,
                                  scroll=ft.ScrollMode.AUTO)
        return ft.Container(padding=15, content=contenido,
                            expand=True), "Notificaciones"

    def sub_incapacidades():
        incs = state.get("incapacidades", [])
        if not incs:
            contenido = card(
                ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.MEDICAL_SERVICES_OUTLINED, size=60,
                                color=TEXT_MUTED),
                        ft.Text("No tienes incapacidades registradas", size=14,
                                color=TEXT_MUTED,
                                text_align=ft.TextAlign.CENTER),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                )
            )
        else:
            items = []
            for inc in incs:
                estado = inc.get("estado", "Recibida")
                if estado == "Pagada":
                    color, icono = GREEN, ft.Icons.CHECK_CIRCLE_ROUNDED
                elif estado == "En Revisión":
                    color, icono = ORANGE, ft.Icons.SCHEDULE_ROUNDED
                else:
                    color, icono = BLUE_ACC, ft.Icons.INFO_ROUNDED

                items.append(
                    card(
                        ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Icon(icono, color=color, size=20),
                                        ft.Column(
                                            controls=[
                                                ft.Text(inc.get("tipo", ""), size=13,
                                                        weight=ft.FontWeight.BOLD,
                                                        color=TEXT),
                                                ft.Text(estado, size=11,
                                                        color=color),
                                            ],
                                            spacing=2, expand=True,
                                        ),
                                    ]
                                ),
                                ft.Divider(height=1, color=DARK_BORDER),
                                info_row("Inicio",
                                         fmt_fecha(inc.get("fecha_inicio"))),
                                info_row("Final",
                                         fmt_fecha(inc.get("fecha_final"))),
                                info_row("Días", str(inc.get("dias", 0))),
                                info_row("Valor", fmt_money(inc.get("valor"))),
                            ],
                            spacing=6,
                        )
                    )
                )
            contenido = ft.Column(controls=items, spacing=10,
                                  scroll=ft.ScrollMode.AUTO)
        return ft.Container(padding=15, content=contenido,
                            expand=True), "Incapacidades"

    def sub_certificados():
        af = state["afiliado"]

        def generar(tipo):
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer)
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib import colors
                from reportlab.lib.units import cm
                from reportlab.lib.enums import TA_CENTER

                carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "certificados")
                os.makedirs(carpeta, exist_ok=True)

                fname = f"Certificado_{tipo}_{af['cc']}.pdf"
                fpath = os.path.join(carpeta, fname)

                doc = SimpleDocTemplate(
                    fpath, pagesize=letter,
                    leftMargin=2 * cm, rightMargin=2 * cm,
                    topMargin=2 * cm, bottomMargin=2 * cm,
                )
                st = getSampleStyleSheet()
                title = ParagraphStyle("T", parent=st["Title"], fontSize=20,
                                       textColor=colors.HexColor("#1a237e"),
                                       alignment=TA_CENTER)
                body = ParagraphStyle("B", parent=st["Normal"], fontSize=12,
                                      leading=18)

                titulo = ("CERTIFICADO DE AFILIACIÓN" if tipo == "afiliacion"
                          else "CERTIFICADO DE RETIRO")

                elems = [
                    Paragraph(titulo, title),
                    Spacer(1, 0.6 * cm),
                    Paragraph(f"<b>{empresa.get('nombre', 'SaluApp')}</b>", body),
                    Spacer(1, 0.5 * cm),
                    Paragraph(
                        f"El(La) Señor(a) <b>{af['nombre']}</b> identificado(a) con CC "
                        f"<b>{af['cc']}</b> se encuentra "
                        f"{'afiliado(a)' if tipo == 'afiliacion' else 'retirado(a)'} "
                        f"a la EPS <b>{af.get('eps', 'No registrada')}</b>.",
                        body,
                    ),
                    Spacer(1, 0.3 * cm),
                    Paragraph(f"Fecha de ingreso: {fmt_fecha(af.get('fecha_ingreso'))}",
                              body),
                ]
                if tipo == "retiro":
                    elems.append(Spacer(1, 0.2 * cm))
                    elems.append(Paragraph(
                        f"Fecha de retiro: {fmt_fecha(af.get('fecha_retiro'))}",
                        body))
                    elems.append(Paragraph(
                        f"Motivo: {af.get('motivo_retiro', 'No especificado')}",
                        body))

                elems.append(Spacer(1, 1 * cm))
                elems.append(Paragraph(
                    f"Expedido el {datetime.now().strftime('%d/%m/%Y')}", body))
                doc.build(elems)

                mostrar_alerta(f"Guardado en: {fpath}", "success", duracion=5000)

                try:
                    if sys.platform == "win32":
                        os.startfile(fpath)
                    elif sys.platform == "darwin":
                        os.system(f"open '{fpath}'")
                    else:
                        os.system(f"xdg-open '{fpath}'")
                except Exception:
                    pass
            except Exception as ex:
                mostrar_alerta(f"Error: {ex}", "error")

        es_activo = not af.get("retirado") and not af.get("archivado")
        if es_activo:
            btn = ft.Container(
                border_radius=12, padding=16,
                gradient=ft.LinearGradient(
                    colors=[PURPLE_DARK, PURPLE, PURPLE_LIGHT],
                    begin=_align("top_left"), end=_align("bottom_right"),
                ),
                alignment=_align("center"), ink=True,
                shadow=ft.BoxShadow(
                    blur_radius=35, spread_radius=0,
                    color="#8B5CF6CC", offset=ft.Offset(0, 0),
                ),
                on_click=lambda e: generar("afiliacion"),
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.DESCRIPTION_ROUNDED, color="white",
                                size=20),
                        ft.Text("Certificado de Afiliación", color="white",
                                weight=ft.FontWeight.BOLD, size=14),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER, spacing=10,
                ),
            )
        else:
            btn = ft.Container(
                bgcolor=RED, border_radius=12, padding=16,
                alignment=_align("center"), ink=True,
                on_click=lambda e: generar("retiro"),
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.DESCRIPTION_ROUNDED, color="white",
                                size=20),
                        ft.Text("Certificado de Retiro", color="white",
                                weight=ft.FontWeight.BOLD, size=14),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER, spacing=10,
                ),
            )

        contenido = ft.Column(
            controls=[
                card(
                    ft.Column(
                        controls=[
                            section_title("Certificados disponibles",
                                          ft.Icons.DESCRIPTION_ROUNDED),
                            ft.Text("Descarga el certificado según tu estado actual",
                                    size=11, color=TEXT_MUTED),
                        ],
                        spacing=5,
                    )
                ),
                btn,
            ],
            spacing=12,
        )
        return ft.Container(padding=15, content=contenido,
                            expand=True), "Certificados"

    # ═══════════════════════════════════════════════════════════════
    # SUB-VISTA: CHAT CON ADMINISTRACIÓN
    # ═══════════════════════════════════════════════════════════════
    def sub_chat():
        af = state["afiliado"]
        cc = af["cc"]

        msg_container = ft.Column(
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            auto_scroll=True,
        )

        ultimo_id = {"valor": 0}

        def _burbuja(m, es_cliente):
            hora = ""
            try:
                hora = datetime.strptime(m.get("fecha", "")[:19],
                                         "%Y-%m-%d %H:%M:%S").strftime("%H:%M")
            except Exception:
                hora = str(m.get("fecha", ""))[11:16]

            return ft.Row(
                controls=[
                    ft.Container(
                        bgcolor=PURPLE if es_cliente else DARK_SURFACE_2,
                        border_radius=_radius(
                            top_left=16, top_right=16,
                            bottom_left=4 if es_cliente else 16,
                            bottom_right=16 if es_cliente else 4,
                        ),
                        padding=_padding_sym(vertical=8, horizontal=12),
                        margin=_margin_sym(horizontal=0),
                        border=_border_all(1, f"{PURPLE}55" if es_cliente else DARK_BORDER),
                        content=ft.Column(
                            controls=[
                                ft.Text(m.get("mensaje", ""), size=13,
                                        color="white" if es_cliente else TEXT,
                                        selectable=True),
                                ft.Text(hora, size=9,
                                        color="#FFFFFFAA" if es_cliente else TEXT_MUTED),
                            ],
                            spacing=2,
                            tight=True,
                            horizontal_alignment=ft.CrossAxisAlignment.END
                            if es_cliente else ft.CrossAxisAlignment.START,
                        ),
                    ),
                ],
                alignment=ft.MainAxisAlignment.END if es_cliente
                else ft.MainAxisAlignment.START,
            )

        def _render_mensajes():
            mensajes = db.get_chat_mensajes(cc)
            msg_container.controls.clear()

            if not mensajes:
                msg_container.controls.append(
                    ft.Container(
                        alignment=_align("center"),
                        padding=40,
                        content=ft.Column(
                            controls=[
                                ft.Icon(ft.Icons.CHAT_BUBBLE_OUTLINE_ROUNDED,
                                        size=60, color=TEXT_MUTED),
                                ft.Text("Aún no hay mensajes",
                                        size=14, color=TEXT_DIM,
                                        text_align=ft.TextAlign.CENTER),
                                ft.Text("Envía tu primer mensaje a la administración",
                                        size=11, color=TEXT_MUTED,
                                        text_align=ft.TextAlign.CENTER),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=6,
                        ),
                    )
                )
            else:
                for m in mensajes:
                    es_cliente = m.get("emisor") == "cliente"
                    msg_container.controls.append(_burbuja(m, es_cliente))
                ultimo_id["valor"] = mensajes[-1]["id"]

            # Marcar como leídos los del admin
            try:
                db.marcar_chat_leidos(cc, "admin")
                state["chat_unread"] = 0
            except Exception:
                pass

        _render_mensajes()

        # Input de envío
        msg_input = ft.TextField(
            hint_text="Escribe un mensaje…",
            expand=True,
            border=ft.InputBorder.OUTLINE,
            border_color=DARK_BORDER,
            focused_border_color=PURPLE,
            border_radius=22,
            filled=True,
            bgcolor=DARK_SURFACE_2,
            text_style=ft.TextStyle(color=TEXT),
            hint_style=ft.TextStyle(color=TEXT_MUTED),
            cursor_color=PURPLE,
            multiline=False,
        )

        def _enviar(e=None):
            texto = (msg_input.value or "").strip()
            if not texto:
                return
            try:
                db.send_chat_mensaje(cc, "cliente", texto)
            except Exception as ex:
                mostrar_alerta(f"Error al enviar: {ex}", "error")
                return
            msg_input.value = ""
            _render_mensajes()
            try:
                page.update()
            except Exception:
                pass

        msg_input.on_submit = _enviar

        send_btn = ft.Container(
            width=46, height=46, border_radius=23,
            gradient=ft.LinearGradient(
                colors=[PURPLE_DARK, PURPLE, PURPLE_LIGHT],
                begin=_align("top_left"), end=_align("bottom_right"),
            ),
            alignment=_align("center"),
            on_click=_enviar,
            ink=True,
            shadow=ft.BoxShadow(
                blur_radius=20, spread_radius=0,
                color="#8B5CF6AA", offset=ft.Offset(0, 0),
            ),
            content=ft.Icon(ft.Icons.SEND_ROUNDED, color="white", size=20),
        )

        input_row = ft.Container(
            padding=_padding_only(left=10, right=10, top=6, bottom=10),
            bgcolor=DARK_SURFACE,
            border=_border_only(top=ft.BorderSide(1, DARK_BORDER)),
            content=ft.Row(controls=[msg_input, send_btn], spacing=8),
        )

        # Polling del chat (solo mientras esté abierto)
        token_actual = state.get("chat_poll_token", 0) + 1
        state["chat_poll_token"] = token_actual

        async def _poll():
            while state.get("sub") == "chat" and state.get("chat_poll_token") == token_actual:
                await asyncio.sleep(4)
                if state.get("sub") != "chat" or state.get("chat_poll_token") != token_actual:
                    break
                try:
                    nuevos = db.get_chat_mensajes(cc, since_id=ultimo_id["valor"])
                    if nuevos:
                        _render_mensajes()
                        try:
                            page.update()
                        except Exception:
                            pass
                except Exception:
                    pass

        try:
            page.run_task(_poll)
        except Exception:
            import threading
            threading.Timer(0.2, lambda: asyncio.run(_poll())).start()

        contenido = ft.Column(
            controls=[
                ft.Container(expand=True, content=msg_container,
                             padding=_padding_sym(horizontal=12, vertical=8)),
                input_row,
            ],
            spacing=0, expand=True,
        )
        return contenido, "Chat con Administración"

    # ═══════════════════════════════════════════════════════════════
    # SUB-VISTA: PQR  (diseño profesional)
    # ═══════════════════════════════════════════════════════════════
    def sub_pqr():
        af = state["afiliado"]
        cc = af["cc"]

        # ── Estado interno del formulario ──
        form_state = {"tipo": "Petición", "prioridad": "Normal"}

        # ── Catálogos visuales ──
        TIPOS = [
            ("Petición",   ft.Icons.HELP_OUTLINE_ROUNDED,           BLUE_ACC, "Solicitar información"),
            ("Queja",      ft.Icons.SENTIMENT_DISSATISFIED_ROUNDED, ORANGE,   "Reportar inconformidad"),
            ("Reclamo",    ft.Icons.REPORT_PROBLEM_ROUNDED,         RED,      "Reportar problema grave"),
            ("Sugerencia", ft.Icons.LIGHTBULB_OUTLINE_ROUNDED,      GREEN,    "Proponer una mejora"),
        ]
        PRIORIDADES = [
            ("Baja",   GREEN),
            ("Normal", BLUE_ACC),
            ("Alta",   ORANGE),
            ("Urgente", RED),
        ]

        # ── Contenedores reactivos ──
        tipos_grid = ft.Row(spacing=8)
        prioridad_row = ft.Row(spacing=6)

        def _render_tipos():
            tipos_grid.controls.clear()
            for nombre, icono, color, _desc in TIPOS:
                activo = form_state["tipo"] == nombre
                tipos_grid.controls.append(
                    ft.Container(
                        expand=True,
                        bgcolor=f"{color}22" if activo else DARK_SURFACE_2,
                        border=_border_all(
                            2 if activo else 1,
                            color if activo else DARK_BORDER,
                        ),
                        border_radius=14,
                        padding=_padding_sym(vertical=12, horizontal=6),
                        alignment=_align("center"),
                        ink=True,
                        on_click=lambda e, n=nombre: _set_tipo(n),
                        content=ft.Column(
                            controls=[
                                ft.Icon(icono,
                                        color=color if activo else TEXT_MUTED,
                                        size=22),
                                ft.Container(height=6),
                                ft.Text(nombre, size=10,
                                        weight=ft.FontWeight.BOLD if activo
                                        else ft.FontWeight.W_500,
                                        color=color if activo else TEXT_DIM,
                                        text_align=ft.TextAlign.CENTER),
                            ],
                            spacing=0,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    )
                )
            try:
                tipos_grid.update()
            except Exception:
                pass

        def _set_tipo(nombre):
            form_state["tipo"] = nombre
            _render_tipos()

        def _render_prioridades():
            prioridad_row.controls.clear()
            for nombre, color in PRIORIDADES:
                activo = form_state["prioridad"] == nombre
                prioridad_row.controls.append(
                    ft.Container(
                        expand=True,
                        bgcolor=color if activo else f"{color}15",
                        border=_border_all(1, color if activo else f"{color}55"),
                        border_radius=50,
                        padding=_padding_sym(vertical=8),
                        alignment=_align("center"),
                        ink=True,
                        on_click=lambda e, n=nombre: _set_prioridad(n),
                        content=ft.Row(
                            controls=[
                                ft.Container(
                                    width=8, height=8, border_radius=4,
                                    bgcolor="white" if activo else color,
                                ),
                                ft.Text(nombre, size=11,
                                        weight=ft.FontWeight.BOLD,
                                        color="white" if activo else color),
                            ],
                            spacing=6,
                            alignment=ft.MainAxisAlignment.CENTER,
                            tight=True,
                        ),
                    )
                )
            try:
                prioridad_row.update()
            except Exception:
                pass

        def _set_prioridad(nombre):
            form_state["prioridad"] = nombre
            _render_prioridades()

        _render_tipos()
        _render_prioridades()

        # ── Campos del formulario ──
        asunto_tf = ft.TextField(
            label="Asunto",
            hint_text="Ej: Problema con el cobro del mes de octubre",
            border=ft.InputBorder.OUTLINE,
            border_color=DARK_BORDER,
            focused_border_color=PURPLE,
            border_radius=14,
            filled=True,
            bgcolor=DARK_SURFACE_2,
            label_style=ft.TextStyle(color=TEXT_DIM, size=12),
            text_style=ft.TextStyle(color=TEXT, size=14),
            cursor_color=PURPLE,
            prefix_icon=ft.Icons.EDIT_NOTE_ROUNDED,
            max_length=120,
        )

        descripcion_tf = ft.TextField(
            label="Descripción",
            hint_text="Describe tu caso con el mayor detalle posible…",
            multiline=True,
            min_lines=4,
            max_lines=6,
            border=ft.InputBorder.OUTLINE,
            border_color=DARK_BORDER,
            focused_border_color=PURPLE,
            border_radius=14,
            filled=True,
            bgcolor=DARK_SURFACE_2,
            label_style=ft.TextStyle(color=TEXT_DIM, size=12),
            text_style=ft.TextStyle(color=TEXT, size=13),
            cursor_color=PURPLE,
            max_length=500,
        )

        # ── Feedback en vivo ──
        char_counter = ft.Text("0/500", size=10, color=TEXT_MUTED)
        asunto_hint = ft.Text("Mínimo 4 caracteres", size=10, color=TEXT_MUTED)
        desc_hint = ft.Text("Mínimo 10 caracteres", size=10, color=TEXT_MUTED)

        def _on_desc_change(e=None):
            val = descripcion_tf.value or ""
            n = len(val)
            char_counter.value = f"{n}/500"
            char_counter.color = GREEN if n >= 10 else TEXT_MUTED
            desc_hint.color = GREEN if n >= 10 else TEXT_MUTED
            try:
                char_counter.update()
                desc_hint.update()
            except Exception:
                pass

        def _on_asunto_change(e=None):
            val = (asunto_tf.value or "").strip()
            asunto_hint.color = GREEN if len(val) >= 4 else TEXT_MUTED
            try:
                asunto_hint.update()
            except Exception:
                pass

        descripcion_tf.on_change = _on_desc_change
        asunto_tf.on_change = _on_asunto_change

        # ── Header del formulario ──
        header_icon = ft.Container(
            width=52, height=52, border_radius=16,
            gradient=ft.LinearGradient(
                colors=[PURPLE_DARK, PURPLE, PURPLE_LIGHT],
                begin=_align("top_left"),
                end=_align("bottom_right"),
            ),
            alignment=_align("center"),
            shadow=ft.BoxShadow(
                blur_radius=25, spread_radius=0,
                color=f"{PURPLE}88", offset=ft.Offset(0, 0),
            ),
            content=ft.Icon(ft.Icons.FORUM_ROUNDED, color="white", size=26),
        )

        header = ft.Row(
            controls=[
                header_icon,
                ft.Column(
                    controls=[
                        ft.Text("Nueva PQR", size=18,
                                weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Text("Peticiones · Quejas · Reclamos · Sugerencias",
                                size=11, color=TEXT_MUTED),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # ── SLA / tiempo de respuesta ──
        sla_card = ft.Container(
            bgcolor=f"{BLUE_ACC}12",
            border=_border_all(1, f"{BLUE_ACC}44"),
            border_radius=12,
            padding=_padding_sym(vertical=10, horizontal=12),
            content=ft.Row(
                controls=[
                    ft.Container(
                        width=32, height=32, border_radius=10,
                        bgcolor=f"{BLUE_ACC}25",
                        alignment=_align("center"),
                        content=ft.Icon(ft.Icons.SCHEDULE_ROUNDED,
                                        color=BLUE_ACC, size=18),
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("Tiempo de respuesta", size=10,
                                    color=BLUE_ACC, weight=ft.FontWeight.BOLD),
                            ft.Text("24-48 horas hábiles", size=12,
                                    color=TEXT_DIM),
                        ],
                        spacing=0,
                        expand=True,
                    ),
                ],
                spacing=10,
            ),
        )

        # ── Enviar ──
        def enviar_pqr(e):
            tipo = form_state["tipo"]
            asunto = (asunto_tf.value or "").strip()
            desc = (descripcion_tf.value or "").strip()
            prio = form_state["prioridad"]

            if not asunto:
                mostrar_alerta("El asunto es obligatorio", "warning")
                return
            if len(asunto) < 4:
                mostrar_alerta("El asunto es demasiado corto (mínimo 4 caracteres)",
                               "warning")
                return
            if not desc or len(desc) < 10:
                mostrar_alerta("La descripción debe tener al menos 10 caracteres",
                               "warning")
                return

            try:
                db.create_pqr(cc, tipo, asunto, desc, prio)
                asunto_tf.value = ""
                descripcion_tf.value = ""
                form_state["tipo"] = "Petición"
                form_state["prioridad"] = "Normal"
                cargar_datos()
                mostrar_alerta("PQR enviada correctamente", "success")
                render()
            except Exception as ex:
                mostrar_alerta(f"Error al enviar: {ex}", "error")

        btn_enviar = ft.Container(
            border_radius=14,
            padding=_padding_sym(vertical=16),
            gradient=ft.LinearGradient(
                colors=[PURPLE_DARK, PURPLE, PURPLE_LIGHT],
                begin=_align("top_left"),
                end=_align("bottom_right"),
            ),
            alignment=_align("center"),
            on_click=enviar_pqr,
            ink=True,
            shadow=ft.BoxShadow(
                blur_radius=35, spread_radius=0,
                color="#8B5CF6CC", offset=ft.Offset(0, 0),
            ),
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.SEND_ROUNDED, color="white", size=20),
                    ft.Text("Enviar PQR", color="white",
                            weight=ft.FontWeight.BOLD, size=15),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10,
            ),
        )

        # ── Helper: separador con barra morada ──
        def _seccion_label(texto):
            return ft.Row(
                controls=[
                    ft.Container(width=4, height=14, border_radius=2,
                                 bgcolor=PURPLE),
                    ft.Text(texto, size=10,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_DIM),
                ],
                spacing=8,
            )

        # ── Tarjeta del formulario ──
        form_card = card(
            ft.Column(
                controls=[
                    header,
                    ft.Container(height=18),

                    _seccion_label("TIPO DE SOLICITUD"),
                    ft.Container(height=8),
                    tipos_grid,
                    ft.Container(height=20),

                    _seccion_label("PRIORIDAD"),
                    ft.Container(height=8),
                    prioridad_row,
                    ft.Container(height=20),

                    _seccion_label("DETALLES"),
                    ft.Container(height=8),
                    asunto_tf,
                    asunto_hint,
                    ft.Container(height=10),
                    descripcion_tf,
                    ft.Row(
                        controls=[
                            desc_hint,
                            ft.Container(expand=True),
                            char_counter,
                        ],
                    ),
                    ft.Container(height=14),
                    sla_card,
                    ft.Container(height=16),
                    btn_enviar,
                ],
                spacing=0,
            ),
            padding=20,
        )

        # ── Historial + estadísticas ──
        pqr_list = state.get("pqr", [])
        total_pqr = len(pqr_list)
        abiertos = sum(1 for p in pqr_list
                       if p.get("estado") in ("Recibida", "En Proceso"))
        resueltos = sum(1 for p in pqr_list
                        if p.get("estado") == "Resuelta")

        def _stat_mini(valor, label, icono, color):
            return ft.Container(
                expand=True,
                bgcolor=DARK_SURFACE,
                border=_border_all(1, DARK_BORDER),
                border_radius=12,
                padding=12,
                content=ft.Column(
                    controls=[
                        ft.Icon(icono, color=color, size=20),
                        ft.Container(height=4),
                        ft.Text(str(valor), size=18,
                                weight=ft.FontWeight.BOLD, color=TEXT),
                        ft.Text(label, size=10, color=TEXT_MUTED),
                    ],
                    spacing=0,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )

        stats_row = ft.Row(
            controls=[
                _stat_mini(total_pqr, "Total",
                           ft.Icons.INBOX_ROUNDED, PURPLE),
                _stat_mini(abiertos, "Abiertos",
                           ft.Icons.HOURGLASS_EMPTY_ROUNDED, ORANGE),
                _stat_mini(resueltos, "Resueltos",
                           ft.Icons.CHECK_CIRCLE_ROUNDED, GREEN),
            ],
            spacing=8,
        )

        if not pqr_list:
            historial = card(
                ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.FORUM_OUTLINED, size=60,
                                color=TEXT_MUTED),
                        ft.Text("No has enviado PQRs aún", size=14,
                                color=TEXT_MUTED,
                                text_align=ft.TextAlign.CENTER),
                        ft.Text("Tus solicitudes aparecerán aquí",
                                size=11, color=TEXT_MUTED,
                                text_align=ft.TextAlign.CENTER),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                )
            )
        else:
            tipo_icon_map = {
                "Petición":   ft.Icons.HELP_OUTLINE_ROUNDED,
                "Queja":      ft.Icons.SENTIMENT_DISSATISFIED_ROUNDED,
                "Reclamo":    ft.Icons.REPORT_PROBLEM_ROUNDED,
                "Sugerencia": ft.Icons.LIGHTBULB_OUTLINE_ROUNDED,
            }
            tipo_color_map = {
                "Petición":   BLUE_ACC,
                "Queja":      ORANGE,
                "Reclamo":    RED,
                "Sugerencia": GREEN,
            }
            prio_color_map = {
                "Baja":   GREEN,
                "Normal": BLUE_ACC,
                "Alta":   ORANGE,
                "Urgente": RED,
            }

            filas = []
            for p in pqr_list:
                estado = p.get("estado", "Recibida")
                tipo = p.get("tipo", "Petición")

                if estado == "Resuelta":
                    color_est = GREEN
                    icono_est = ft.Icons.CHECK_CIRCLE_ROUNDED
                elif estado == "En Proceso":
                    color_est = ORANGE
                    icono_est = ft.Icons.SCHEDULE_ROUNDED
                elif estado == "Cerrada":
                    color_est = TEXT_MUTED
                    icono_est = ft.Icons.ARCHIVE_ROUNDED
                else:
                    color_est = BLUE_ACC
                    icono_est = ft.Icons.INFO_ROUNDED

                tipo_icono = tipo_icon_map.get(tipo, ft.Icons.FORUM_ROUNDED)
                tipo_color = tipo_color_map.get(tipo, PURPLE)

                prio = p.get("prioridad", "Normal")
                prio_color = prio_color_map.get(prio, BLUE_ACC)

                respuesta_block = []
                if p.get("respuesta"):
                    respuesta_block.append(ft.Container(height=10))
                    respuesta_block.append(
                        ft.Container(
                            bgcolor=f"{GREEN}12",
                            border=_border_all(1, f"{GREEN}44"),
                            border_radius=12,
                            padding=12,
                            content=ft.Column(
                                controls=[
                                    ft.Row(
                                        controls=[
                                            ft.Icon(ft.Icons.REPLY_ROUNDED,
                                                    color=GREEN, size=14),
                                            ft.Text("Respuesta del administrador",
                                                    size=10, color=GREEN,
                                                    weight=ft.FontWeight.BOLD),
                                        ],
                                        spacing=6,
                                    ),
                                    ft.Container(height=4),
                                    ft.Text(p["respuesta"], size=12,
                                            color=TEXT_DIM),
                                ],
                                spacing=0,
                            ),
                        )
                    )

                filas.append(
                    card(
                        ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Container(
                                            width=40, height=40,
                                            border_radius=12,
                                            bgcolor=f"{tipo_color}22",
                                            alignment=_align("center"),
                                            content=ft.Icon(tipo_icono,
                                                            color=tipo_color,
                                                            size=20),
                                        ),
                                        ft.Column(
                                            controls=[
                                                ft.Row(
                                                    controls=[
                                                        ft.Text(f"#{p.get('id', '')}",
                                                                size=10,
                                                                color=TEXT_MUTED),
                                                        ft.Container(
                                                            width=4, height=4,
                                                            border_radius=2,
                                                            bgcolor=TEXT_MUTED,
                                                        ),
                                                        ft.Text(tipo, size=10,
                                                                color=tipo_color,
                                                                weight=ft.FontWeight.BOLD),
                                                    ],
                                                    spacing=6,
                                                ),
                                                ft.Text(p.get("asunto", ""),
                                                        size=13,
                                                        weight=ft.FontWeight.BOLD,
                                                        color=TEXT,
                                                        max_lines=1,
                                                        overflow=ft.TextOverflow.ELLIPSIS),
                                            ],
                                            spacing=2,
                                            expand=True,
                                        ),
                                        ft.Container(
                                            bgcolor=f"{color_est}22",
                                            border=_border_all(1, f"{color_est}55"),
                                            border_radius=50,
                                            padding=_padding_sym(
                                                horizontal=10, vertical=4),
                                            content=ft.Row(
                                                controls=[
                                                    ft.Icon(icono_est,
                                                            color=color_est,
                                                            size=10),
                                                    ft.Text(estado, size=10,
                                                            color=color_est,
                                                            weight=ft.FontWeight.BOLD),
                                                ],
                                                spacing=4,
                                                tight=True,
                                            ),
                                        ),
                                    ],
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                ft.Container(height=10),
                                ft.Text(p.get("descripcion", ""),
                                        size=12, color=TEXT_DIM,
                                        max_lines=3,
                                        overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Container(height=10),
                                ft.Row(
                                    controls=[
                                        ft.Row(
                                            controls=[
                                                ft.Icon(ft.Icons.SCHEDULE_ROUNDED,
                                                        color=TEXT_MUTED, size=11),
                                                ft.Text(
                                                    str(p.get('fecha_creacion', ''))[:16],
                                                    size=10, color=TEXT_MUTED),
                                            ],
                                            spacing=4,
                                            tight=True,
                                        ),
                                        ft.Container(expand=True),
                                        ft.Container(
                                            bgcolor=f"{prio_color}22",
                                            border_radius=50,
                                            padding=_padding_sym(
                                                horizontal=8, vertical=3),
                                            content=ft.Text(prio, size=9,
                                                            color=prio_color,
                                                            weight=ft.FontWeight.BOLD),
                                        ),
                                    ],
                                ),
                                *respuesta_block,
                            ],
                            spacing=0,
                        )
                    )
                )

            historial = ft.Column(
                controls=[
                    ft.Container(height=4),
                    section_title("Historial de PQRs",
                                  ft.Icons.HISTORY_ROUNDED),
                    ft.Container(height=4),
                    *filas,
                ],
                spacing=10,
            )

        contenido = ft.Container(
            padding=15,
            content=ft.Column(
                controls=[
                    form_card,
                    ft.Container(height=4),
                    stats_row,
                    historial,
                ],
                spacing=12,
                scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
        )
        return contenido, "PQR"
    # ═══════════════════════════════════════════════════════════════
    # SUB-VISTA: MI QR
    # ═══════════════════════════════════════════════════════════════
    def sub_qr():
        af = state["afiliado"]
        cc = af["cc"]

        qr_src = generar_qr_base64(cc)

        if qr_src:
            qr_widget = ft.Container(
                width=250, height=250,
                bgcolor="white",
                border_radius=20,
                padding=15,
                alignment=_align("center"),
                shadow=ft.BoxShadow(
                    blur_radius=40, spread_radius=0,
                    color="#8B5CF6AA", offset=ft.Offset(0, 0),
                ),
                content=ft.Image(
                    src=qr_src,
                    fit=_image_fit("contain"),
                    width=220, height=220,
                ),
            )
        else:
            qr_widget = ft.Container(
                width=250, height=250,
                bgcolor=DARK_SURFACE_2,
                border_radius=20,
                alignment=_align("center"),
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.QR_CODE_2_ROUNDED, size=80,
                                color=TEXT_MUTED),
                        ft.Text("No se pudo generar el QR", size=12,
                                color=TEXT_MUTED),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
            )

        def copiar_cedula(e):
            try:
                page.set_clipboard(cc)
                mostrar_alerta("Cédula copiada al portapapeles", "success")
            except Exception as ex:
                mostrar_alerta(f"No se pudo copiar: {ex}", "error")

        return ft.Container(
            padding=15,
            content=ft.Column(
                controls=[
                    card(
                        ft.Column(
                            controls=[
                                section_title("Mi código QR",
                                              ft.Icons.QR_CODE_ROUNDED),
                                ft.Text("Presenta este código en recepción para "
                                        "identificarte rápido",
                                        size=11, color=TEXT_MUTED),
                                ft.Container(height=15),
                                ft.Row(
                                    controls=[qr_widget],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                                ft.Container(height=15),
                                ft.Column(
                                    controls=[
                                        ft.Text(af.get("nombre", ""),
                                                size=16,
                                                weight=ft.FontWeight.BOLD,
                                                color=TEXT,
                                                text_align=ft.TextAlign.CENTER),
                                        ft.Text(f"CC: {cc}", size=13,
                                                color=PURPLE_LIGHT,
                                                weight=ft.FontWeight.W_600,
                                                text_align=ft.TextAlign.CENTER),
                                    ],
                                    spacing=4,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                ft.Container(height=15),
                                ft.Container(
                                    border_radius=12, padding=14,
                                    bgcolor=DARK_SURFACE_2,
                                    border=_border_all(1, DARK_BORDER),
                                    on_click=copiar_cedula,
                                    ink=True,
                                    content=ft.Row(
                                        controls=[
                                            ft.Icon(ft.Icons.COPY_ROUNDED,
                                                    color=PURPLE_LIGHT, size=18),
                                            ft.Text("Copiar cédula",
                                                    color=TEXT,
                                                    weight=ft.FontWeight.BOLD,
                                                    size=13),
                                        ],
                                        alignment=ft.MainAxisAlignment.CENTER,
                                        spacing=8,
                                    ),
                                ),
                                ft.Container(height=10),
                                ft.Container(
                                    bgcolor=f"{BLUE_ACC}15",
                                    border=_border_all(1, f"{BLUE_ACC}44"),
                                    border_radius=10, padding=10,
                                    content=ft.Row(
                                        controls=[
                                            ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED,
                                                    color=BLUE_ACC, size=16),
                                            ft.Text(
                                                "Compatible con el escáner de SaluPago. "
                                                "Muestra la pantalla completa al recepcionista.",
                                                size=11, color=TEXT_DIM, expand=True),
                                        ],
                                        spacing=8,
                                    ),
                                ),
                            ],
                            spacing=6,
                        )
                    ),
                ],
                spacing=12, scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
        ), "Mi código QR"

    # ═══════════════════════════════════════════════════════════════
    # SUB-VISTA: MIS FACTURAS
    # ═══════════════════════════════════════════════════════════════
    def sub_facturas():
        af = state["afiliado"]

        def refrescar():
            try:
                state["facturas"] = db.get_facturas_cliente(af["cc"])
                render()
                mostrar_alerta("Facturas actualizadas", "info", duracion=1500)
            except Exception as ex:
                mostrar_alerta(f"Error: {ex}", "error")

        def abrir_factura(ruta):
            try:
                if not os.path.exists(ruta):
                    mostrar_alerta("El archivo ya no existe", "error")
                    return
                if sys.platform == "win32":
                    os.startfile(ruta)
                elif sys.platform == "darwin":
                    os.system(f"open '{ruta}'")
                else:
                    os.system(f"xdg-open '{ruta}'")
            except Exception as ex:
                mostrar_alerta(f"No se pudo abrir: {ex}", "error")

        def abrir_carpeta(e=None):
            try:
                fd = db.find_facturas_dir()
                if not fd:
                    mostrar_alerta("No se encontró la carpeta de facturas", "warning")
                    return
                if sys.platform == "win32":
                    os.startfile(fd)
                elif sys.platform == "darwin":
                    os.system(f"open '{fd}'")
                else:
                    os.system(f"xdg-open '{fd}'")
            except Exception as ex:
                mostrar_alerta(f"No se pudo abrir la carpeta: {ex}", "error")

        facturas = state.get("facturas", [])

        header_row = card(
            ft.Row(
                controls=[
                    ft.Icon(ft.Icons.RECEIPT_LONG_ROUNDED, color=PURPLE_LIGHT,
                            size=22),
                    ft.Column(
                        controls=[
                            ft.Text("Mis facturas", size=14,
                                    weight=ft.FontWeight.BOLD, color=TEXT),
                            ft.Text(
                                f"{len(facturas)} documento(s) encontrado(s)",
                                size=11, color=TEXT_MUTED),
                        ],
                        spacing=2, expand=True,
                    ),
                    ft.Container(
                        bgcolor=DARK_SURFACE_2,
                        border=_border_all(1, DARK_BORDER),
                        border_radius=10,
                        padding=_padding_sym(vertical=8, horizontal=12),
                        on_click=lambda e: refrescar(),
                        ink=True,
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.REFRESH_ROUNDED,
                                        color=PURPLE_LIGHT, size=16),
                                ft.Text("Refrescar", color=PURPLE_LIGHT,
                                        size=11, weight=ft.FontWeight.W_600),
                            ],
                            spacing=6, tight=True,
                        ),
                    ),
                ]
            )
        )

        if not facturas:
            contenido_lista = card(
                ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.RECEIPT_OUTLINED, size=60,
                                color=TEXT_MUTED),
                        ft.Text("No hay facturas disponibles",
                                size=14, color=TEXT_DIM,
                                text_align=ft.TextAlign.CENTER),
                        ft.Text(
                            "Las facturas generadas por la administración aparecerán aquí",
                            size=11, color=TEXT_MUTED,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                )
            )
        else:
            filas = []
            for f in facturas:
                def mk_open(path):
                    def h(e):
                        abrir_factura(path)
                    return h

                filas.append(
                    ft.Container(
                        bgcolor=DARK_SURFACE,
                        border=_border_all(1, DARK_BORDER),
                        border_radius=12,
                        padding=12,
                        on_click=mk_open(f["ruta"]),
                        ink=True,
                        content=ft.Row(
                            controls=[
                                ft.Container(
                                    width=42, height=42, border_radius=10,
                                    bgcolor=f"{RED}25",
                                    alignment=_align("center"),
                                    content=ft.Icon(ft.Icons.PICTURE_AS_PDF_ROUNDED,
                                                    color=RED, size=22),
                                ),
                                ft.Column(
                                    controls=[
                                        ft.Text(f["nombre"], size=12,
                                                weight=ft.FontWeight.BOLD,
                                                color=TEXT,
                                                max_lines=1,
                                                overflow=ft.TextOverflow.ELLIPSIS),
                                        ft.Text(
                                            f"{f['fecha_mod']} · {f['tamano_kb']} KB",
                                            size=10, color=TEXT_MUTED,
                                        ),
                                    ],
                                    spacing=2, expand=True,
                                ),
                                ft.Icon(ft.Icons.OPEN_IN_NEW_ROUNDED,
                                        color=TEXT_MUTED, size=18),
                            ]
                        ),
                    )
                )
            contenido_lista = ft.Column(controls=filas, spacing=8)

        return ft.Container(
            padding=15,
            content=ft.Column(
                controls=[
                    header_row,
                    ft.Container(
                        border_radius=12, padding=12,
                        bgcolor=DARK_SURFACE_2,
                        border=_border_all(1, DARK_BORDER),
                        on_click=abrir_carpeta,
                        ink=True,
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.FOLDER_OPEN_ROUNDED,
                                        color=PURPLE_LIGHT, size=18),
                                ft.Text("Abrir carpeta de facturas",
                                        color=TEXT, size=12,
                                        weight=ft.FontWeight.W_600, expand=True),
                                ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED,
                                        color=TEXT_MUTED, size=18),
                            ],
                            spacing=8,
                        ),
                    ),
                    contenido_lista,
                ],
                spacing=12, scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
        ), "Mis Facturas"

    # ─── Arranque ─────────────────────────────────────────────────
    render()


if __name__ == "__main__":
    ft.app(target=main)