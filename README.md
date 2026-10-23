# SaluPago

Sistema de gestión de afiliaciones, pagos, incapacidades, retiros y contabilidad, desarrollado para la asignatura **Ingeniería Web**

**Autores:** L. A. Renteria Berrio
Repositorio: https://github.com/LeyB-King/SaluPago_A.K.J

El proyecto tiene dos aplicaciones que comparten la misma base de datos SQLite:

| Archivo | Descripción | Tecnología |
|---|---|---|
| `SaluPago_v4_0.py` | Aplicación de escritorio para administrativos y auxiliares | Python + Tkinter |

Hay **tres formas de usarlo**. Elige según tu caso:

| Soy... | Voy a... | Ir a la sección |
|---|---|---|
| Usuario final | Descargar el programa ya compilado y abrirlo | [1](#1-usar-el-ejecutable-usuario-final) |
| Desarrollador | Ejecutar el código fuente desde GitHub | [2](#2-ejecutar-desde-el-código-fuente) |
| Desarrollador | Generar yo mismo el ejecutable | [3](#3-generar-el-ejecutable-con-pyinstaller) |

---

## 1. Usar el ejecutable (usuario final)

No necesitas instalar Python ni Git.

1. Entra a la sección **Releases** del repositorio: https://github.com/LeyB-King/SaluPago_A.K.J/releases
2. Descarga el archivo `SaluPago.zip` de la última versión.
3. **Descomprime todo el contenido** del `.zip` en una carpeta de tu equipo (por ejemplo `C:\SaluPago`). No ejecutes el programa desde dentro del `.zip`.
4. Abre la carpeta y haz doble clic en `SaluPago.exe`.

Usuarios iniciales (cámbialos después del primer ingreso):

| Usuario | Contraseña | Rol |
|---|---|---|
| `MyAdmin` | `admin123` | Administrativo |
| `Auxiliar` | `aux123` | Auxiliar |

Notas importantes:

- **No muevas ni borres archivos** dentro de la carpeta del programa: el `.exe` necesita la carpeta `_internal` que está junto a él. Si quieres un acceso directo, haz clic derecho sobre `SaluPago.exe` → *Enviar a → Escritorio*.
- **Windows puede mostrar una advertencia** ("Windows protegió su PC") porque el programa no tiene firma digital. Pulsa **Más información → Ejecutar de todas formas**.
- **Tus datos** (base de datos, facturas, documentos) se guardan dentro de la carpeta del programa. Antes de actualizar a una versión nueva, haz un backup desde el sistema (sección 5).

---

## 2. Ejecutar desde el código fuente

### 2.1 Requisitos

- **Python 3.10 a 3.12** (`python --version`). Con Python 3.13 algunas librerías pueden fallar.
- **Git** (`git --version`).
- **Windows 10/11** (recomendado). La aplicación de escritorio usa funciones propias de Windows.

Descargas: [Python](https://www.python.org/downloads/) (marca **Add Python to PATH** al instalar) y [Git](https://git-scm.com/downloads).

### 2.2 Clonar el repositorio

```bash
git clone https://github.com/LeyB-King/SaluPago_A.K.J.git
cd SaluPago_A.K.J
```

Si el repositorio es privado, GitHub pedirá autenticación: usa tu usuario y un **Personal Access Token** en lugar de la contraseña.

### 2.3 Entorno virtual y dependencias

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Si PowerShell bloquea la activación, ejecuta una vez: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### 2.4 Ejecutar

```bash
python SaluPago_v4_0.py
```

En el primer arranque se crea la carpeta `.BT/` con la base de datos `saluPago.db` y los usuarios iniciales de la sección 1.

Para el portal del afiliado (necesita que la base de datos ya exista):

```bash
python SaluApp.py
```

`SaluApp` busca la base en `.BT/saluPago.db`. Si está en otra ubicación, crea un archivo `client_config.json` junto a `SaluApp.py`:

```json
{"db_path": "C:/ruta/a/.BT/saluPago.db"}
```

### 2.5 Carpeta `img`

El repositorio debe incluir `img/` con `LogoSaluPago.png`, `LogoSP1.png`, `SaluApp.png`, `mi_icono.ico`, `mi_icono.png` y la subcarpeta `sonidos/`. Si falta alguno, el programa abre pero sin logos, icono o sonidos.

---

## 3. Generar el ejecutable con PyInstaller

Hazlo desde Windows, con el entorno virtual activado (sección 2.3) y dentro de la carpeta del proyecto, donde está `img\`.

```powershell
pip install pyinstaller
python -m PyInstaller --noconfirm --clean --onedir --windowed --name SaluPago --icon img\mi_icono.ico --add-data "img;img" --collect-all tkinterdnd2 --collect-all pyzbar SaluPago_v4_0.py
```

Qué hace cada opción:

| Opción | Función |
|---|---|
| `python -m PyInstaller` | Evita el error "pyinstaller no se reconoce como comando". |
| `--onedir` | Genera una carpeta. **No uses `--onefile`**: guardaría la base de datos en una ubicación temporal y se perderían los datos al cerrar. |
| `--windowed` | Abre sin ventana de consola. |
| `--icon img\mi_icono.ico` | Icono del `.exe`. Debe ser un `.ico` verdadero. |
| `--add-data "img;img"` | Incluye toda la carpeta `img` (logos, iconos y sonidos) dentro del programa. |
| `--collect-all ...` | Incluye archivos que PyInstaller no detecta solo (arrastrar y soltar, lector QR). |
| `--clean` | Limpia la caché de compilaciones anteriores. |

### 3.1 Dónde queda el resultado

PyInstaller crea dos carpetas nuevas:

```
build\   → archivos temporales. NO ejecutar nada de aquí.
dist\
└── SaluPago\
    ├── SaluPago.exe   ← este es el programa
    └── _internal\     ← librerías, imágenes y datos (debe ir junto al .exe)
```

El programa está en **`dist\SaluPago\SaluPago.exe`**. Ábrelo desde ahí.

### 3.2 Probar antes de entregar

Lo ideal es probar en otro equipo sin Python instalado:

- Abre con logos e icono visibles.
- Se crea la base de datos y el login funciona.
- Se genera una factura en PDF.
- El escáner QR no da error.

Si falta una librería, agrega otra opción `--collect-all nombre_libreria` al comando y vuelve a compilar.

### 3.3 Publicar el ejecutable en GitHub

El ejecutable **no se sube al código** del repositorio (por eso `dist/` y `build/` están en el `.gitignore`). Se publica como *Release*:

1. Comprime la carpeta `dist\SaluPago` completa en `SaluPago.zip`.
2. En GitHub: **Releases → Draft a new release**.
3. Escribe una etiqueta de versión (por ejemplo `v4.0`), arrastra `SaluPago.zip` y pulsa **Publish release**.

Cualquier usuario podrá descargarlo desde la sección 1.

### 3.4 SaluApp como ejecutable (opcional)

```powershell
flet pack SaluApp.py --name SaluApp --icon img\mi_icono.ico --add-data "img;img"
```

Las opciones de `flet pack` cambian entre versiones de Flet. Este ejecutable también necesita encontrar la base de datos: junto a `SaluApp.exe` crea un `client_config.json` con la ruta a `saluPago.db` de la instalación de SaluPago.

---

## 4. Estructura del proyecto

```
SaluPago_A.K.J/
├── SaluPago_v4_0.py     # Aplicación de escritorio (Tkinter)
├── SaluApp.py           # Portal del afiliado (Flet)
├── requirements.txt     # Dependencias de Python
├── .gitignore           # Excluye datos privados y carpetas de compilación
├── README.md
├── img/                 # Logos, iconos y sonidos
│
│  # Se generan al ejecutar o compilar (no se suben a GitHub):
├── .BT/                 # Base de datos saluPago.db y configuración
├── facturas/  Documentos/  Incapacidades/  BaseRetiros/
├── Caja/  Recibos/  Reportes/  Backup/
├── build/  dist/        # Resultado de PyInstaller
```

---

## 5. Llevar los datos a otro equipo

GitHub **solo guarda el código**. Los datos reales (base de datos, facturas, documentos de afiliados, incapacidades) están excluidos del repositorio para proteger información personal.

1. En el equipo original, abre SaluPago y usa la opción de **Backup**. Se genera un `.zip` con la base de datos y las carpetas de trabajo.
2. Copia el `.zip` al nuevo equipo (USB, correo o nube privada; **no GitHub**).
3. En el nuevo equipo, con el programa abierto, usa la opción de **Restaurar backup** y selecciona el `.zip`.

Haz este proceso también **antes de recompilar o reemplazar el ejecutable**, porque en la versión compilada los datos viven dentro de `dist\SaluPago\_internal\`.

---

## 6. Actualizar el código

```bash
git pull origin main
pip install -r requirements.txt
```

Subir cambios:

```bash
git add .
git commit -m "Descripción del cambio"
git push origin main
```

---

## 7. Solución de problemas

| Problema | Solución |
|---|---|
| `Failed to load Python DLL ... python313.dll` al abrir el `.exe` | Estás abriendo el `.exe` de la carpeta `build\` o lo sacaste de su carpeta. Usa `dist\SaluPago\SaluPago.exe` y conserva la carpeta `_internal` junto a él. |
| El mismo error dentro de `dist\` | Cierra el programa, borra `build` y `dist` y compila de nuevo con `--clean`. Si el proyecto está en OneDrive, mueve la carpeta fuera de OneDrive (por ejemplo `C:\Proyectos`) o marca *Mantener siempre en este dispositivo*. |
| `pyinstaller` no se reconoce como comando | Usa `python -m PyInstaller ...`. |
| Windows o el antivirus bloquean el `.exe` | Es una falsa alarma frecuente en programas sin firma. Usa *Más información → Ejecutar de todas formas* o agrega la carpeta a las excepciones. |
| El `.exe` abre sin logos ni icono | Compila de nuevo verificando que la opción `--add-data "img;img"` esté y que `img\` exista. |
| `python` no se reconoce como comando | Reinstala Python marcando **Add Python to PATH**, o usa `py`. |
| `ModuleNotFoundError` al ejecutar el código | Activa el entorno virtual y ejecuta `pip install -r requirements.txt`. |
| Error con `pyzbar` o `DLL load failed` | Instala el [Microsoft Visual C++ Redistributable](https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist) y reinicia. |
| `SaluApp` muestra "No se pudo conectar" | No encuentra la base de datos: ejecuta primero SaluPago o crea `client_config.json` (sección 2.4). |
| No suenan los efectos | Verifica que `pygame` esté instalado y que `img/sonidos/` tenga archivos. |

---

## 8. Autores

- L. A. Renteria Berrio

**Director del proyecto:** 
