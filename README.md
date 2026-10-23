# SaluPago

Sistema de gestión de afiliaciones, pagos, incapacidades, retiros y contabilidad, desarrollado para la asignatura **Ingeniería Web** bajo la dirección del profesor Miguel Angel Villamil Bustos.

**Autores:** L. A. Renteria Berrio, J. Cuitiva Merchán y K. J. Soto

Repositorio: https://github.com/LeyB-King/SaluPago_A.K.J

El proyecto tiene dos aplicaciones que comparten la misma base de datos SQLite:

| Archivo | Descripción | Tecnología |
|---|---|---|
| `SaluPago_v4_0.py` | Aplicación de escritorio para administrativos y auxiliares | Python + Tkinter |
| `SaluApp.py` | Portal del afiliado (versión móvil/cliente) | Python + Flet |

---

## 1. Requisitos previos

- **Python 3.10 a 3.12** → verifica con `python --version`
- **Git** → verifica con `git --version`
- **Windows 10/11** (recomendado). La aplicación de escritorio usa funciones propias de Windows (ventana maximizada, rutas `%APPDATA%`), por lo que en Linux o macOS puede no funcionar por completo.

Descargas: [Python](https://www.python.org/downloads/) (marca la casilla **Add Python to PATH** al instalar) y [Git](https://git-scm.com/downloads).

---

## 2. Clonar el repositorio

```bash
git clone https://github.com/LeyB-King/SaluPago_A.K.J.git
cd SaluPago_A.K.J
```

Si el repositorio es privado, GitHub pedirá autenticación: usa tu usuario y un **Personal Access Token** en lugar de la contraseña (GitHub → Settings → Developer settings → Personal access tokens).

---

## 3. Crear el entorno virtual e instalar dependencias

```bash
python -m venv venv
```

Activar el entorno:

```powershell
# Windows (PowerShell)
venv\Scripts\Activate.ps1

# Windows (CMD)
venv\Scripts\activate.bat

# Linux / macOS
source venv/bin/activate
```

Instalar las librerías:

```bash
pip install -r requirements.txt
```

> Si PowerShell bloquea la activación, ejecuta una vez: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

> En Linux, `pyzbar` necesita además la librería del sistema: `sudo apt install libzbar0`.

---

## 4. Verificar la carpeta `img`

El repositorio debe incluir la carpeta `img/` con los recursos gráficos y de sonido:

```
img/
├── LogoSaluPago.png
├── LogoSP1.png
├── SaluApp.png
├── mi_icono.ico
├── mi_icono.png
└── sonidos/        (archivos .wav, .ogg o .mp3)
```

Si falta alguno, la aplicación abre igual pero sin logos, icono o sonidos.

---

## 5. Ejecutar la aplicación de escritorio (SaluPago)

```bash
python SaluPago_v4_0.py
```

En el primer arranque se crea automáticamente la carpeta `.BT/` con la base de datos `saluPago.db` y los usuarios iniciales:

| Usuario | Contraseña | Rol |
|---|---|---|
| `MyAdmin` | `admin123` | Administrativo |
| `Auxiliar` | `aux123` | Auxiliar |

**Cambia estas contraseñas desde la gestión de usuarios después del primer ingreso.**

---

## 6. Ejecutar el portal del afiliado (SaluApp)

Primero debe existir la base de datos, es decir, haber ejecutado SaluPago al menos una vez en el mismo equipo (o haber restaurado un backup, ver sección 7).

```bash
python SaluApp.py
```

`SaluApp` busca la base de datos automáticamente en `.BT/saluPago.db`. Si está en otra ubicación, crea un archivo `client_config.json` junto a `SaluApp.py`:

```json
{"db_path": "C:/ruta/a/.BT/saluPago.db"}
```

---

## 7. Llevar los datos a otro equipo

GitHub **solo guarda el código**. Los datos reales (base de datos, facturas, documentos de afiliados, incapacidades, etc.) están excluidos del repositorio por el `.gitignore` para proteger información personal.

Para trasladar la información:

1. En el equipo original, abre SaluPago y usa la opción de **Backup** del sistema. Esto genera un `.zip` con la base de datos y las carpetas de trabajo.
2. Copia ese `.zip` al nuevo equipo (USB, correo, nube privada; **no GitHub**).
3. En el nuevo equipo, con el programa ya instalado, usa la opción de **Restaurar backup** y selecciona el `.zip`.

Si solo quieres probar el sistema con datos vacíos, omite este paso: se creará una base nueva.

---

## 8. Estructura del proyecto

```
SaluPago_A.K.J/
├── SaluPago_v4_0.py     # Aplicación de escritorio (Tkinter)
├── SaluApp.py           # Portal del afiliado (Flet)
├── requirements.txt     # Dependencias de Python
├── .gitignore           # Excluye datos privados
├── README.md
├── img/                 # Logos, iconos y sonidos
│
│  # Se generan al ejecutar (no se suben a GitHub):
├── .BT/                 # Base de datos saluPago.db y configuración
├── facturas/            # Facturas en PDF
├── Documentos/          # Documentos por afiliado
├── Incapacidades/       # Soportes de incapacidades
├── BaseRetiros/  Caja/  Recibos/  Reportes/  Backup/
```

---

## 9. Actualizar el código

Traer los últimos cambios:

```bash
git pull origin main
pip install -r requirements.txt
```

Subir tus cambios:

```bash
git add .
git commit -m "Descripción del cambio"
git push origin main
```

---

## 10. Solución de problemas

| Problema | Solución |
|---|---|
| `python` no se reconoce como comando | Reinstala Python marcando **Add Python to PATH**, o usa `py` en lugar de `python`. |
| `ModuleNotFoundError: No module named ...` | Activa el entorno virtual y ejecuta `pip install -r requirements.txt`. |
| Error al importar `pyzbar` o `ImportError: DLL load failed` | Instala el [Microsoft Visual C++ Redistributable](https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist) y reinicia. |
| `SaluApp` muestra "No se pudo conectar" | No encuentra la base de datos: ejecuta primero SaluPago o crea `client_config.json` (sección 6). |
| No suenan los efectos de sonido | Verifica que `pygame` esté instalado y que `img/sonidos/` tenga archivos. |
| Faltan logos o iconos | Revisa que la carpeta `img/` se haya clonado completa. |
| Errores con `flet` tras actualizar | Instala la versión indicada en `requirements.txt` sin actualizarla. |

---

## 11. Autores

- L. A. Renteria Berrio
- J. Cuitiva Merchán
- K. J. Soto

**Director del proyecto:** Prof. Miguel Angel Villamil Bustos
