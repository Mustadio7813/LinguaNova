# LinguaNova 🌠

[English](README.md) · **Español**

> [!WARNING]
> **LinguaNova está en fase beta y en desarrollo activo.** Modifica archivos de traducción dentro de la carpeta del juego: **haz una copia de seguridad del juego antes de traducir** y revisa el resultado antes de compartirlo. Informa los problemas en [Issues](../../issues), incluyendo el registro y la versión de Ren'Py del juego.

> [!IMPORTANT]
> **LinguaNova es un proyecto modificado e independiente en su identidad y mantenimiento, basado en parte en RenLocalizer 2.8.19.**
> No es una versión oficial de RenLocalizer, no está mantenido por sus autores originales y no implica afiliación, aprobación ni soporte por parte de ellos.
>
> **Proyecto original:** https://github.com/Lord0fTurk/RenLocalizer  
> **Aviso de copyright original conservado:** Copyright (C) 2025 RenLocalizer V2 Authors  
> **Licencia del trabajo modificado:** GNU General Public License v3.0 o posterior (**GPL-3.0-or-later**)  
> **Fecha relevante del aviso de modificación:** 2026-10-16  
>
> Consulta [`NOTICE.md`](NOTICE.md), [`UPSTREAM.md`](UPSTREAM.md), [`LICENSE_POLICY.md`](LICENSE_POLICY.md) y [`MODIFICATIONS_LINGUANOVA.md`](MODIFICATIONS_LINGUANOVA.md).

**LinguaNova está diseñado para localizar juegos de Ren'Py preservando su estructura de scripts, variables, etiquetas y archivos de traducción.**

![Plataformas](https://img.shields.io/badge/Plataforma-Windows%20%7C%20Linux%20%7C%20macOS-ff7a59?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white)
![GUI](https://img.shields.io/badge/GUI-PyQt6%20%2B%20QML-41cd52?style=flat-square)
![Ren'Py](https://img.shields.io/badge/Ren'Py-7%20%26%208-ffb86b?style=flat-square)
![Licencia](https://img.shields.io/badge/Licencia-GPL--3.0--or--later-111827?style=flat-square)

## Relación con RenLocalizer

LinguaNova **no oculta su procedencia**:

- deriva en parte de RenLocalizer;
- conserva la atribución y los avisos de licencia correspondientes;
- mantiene un registro explícito de las modificaciones realizadas;
- usa un nombre, identidad visual y mantenimiento propios;
- los errores, cambios o decisiones de LinguaNova no deben atribuirse a los autores de RenLocalizer;
- la existencia de este repositorio separado no cambia el hecho de que LinguaNova es un trabajo modificado sujeto a GPL-3.0-or-later.

El archivo [`UPSTREAM.md`](UPSTREAM.md) documenta la relación con el proyecto de origen.

## ⚡ Uso rápido

1. **Selecciona el juego:** carpeta principal, carpeta `game` o ejecutable admitido.
2. **Elige idioma y motor de traducción.**
3. **Inicia la traducción** y revisa el resultado antes de distribuirlo.

## Funciones principales

- Traducción y generación de archivos de idioma para Ren'Py.
- Protección de variables, etiquetas y marcadores.
- Análisis de `.rpy`, `.rpyc` y contenido empaquetado cuando las herramientas disponibles lo permiten.
- Editor de traducciones.
- Herramientas de fuentes, glosario y diagnóstico.
- MOD de traducción de interfaz separado del sistema normal de traducción.
- Cola de trabajos que no cancela automáticamente la operación activa.
- Interfaz en nueve idiomas, más los idiomas que añadas tú (Utilidades → *Crear un idioma de la interfaz*).
- Instalador de Windows con actualizaciones automáticas verificadas.

## 💾 Instalación

| Sistema | Archivo en cada [versión publicada](https://github.com/Mustadio7813/LinguaNova/releases) | Notas |
| --- | --- | --- |
| Windows 10/11 (64 bits) | `LinguaNova_Setup_<versión>.exe` | Instalador. Eliges uno de los discos internos del PC y LinguaNova se instala en `<disco>:\LinguaNova`. Sin permisos de administrador; acceso directo en el escritorio y en el menú Inicio. Se actualiza solo. |
| Windows (portable) | `LinguaNova-Windows-x64.zip` | Descomprime y ejecuta `LinguaNova.exe`. Crea un archivo vacío `.portable` en la carpeta para guardar la configuración dentro de ella. |
| Linux (x64) | `LinguaNova-Linux-x64.AppImage` | Compilado y probado al arrancar por GitHub Actions. |
| macOS (Apple silicon) | `LinguaNova-macOS-arm64.dmg` | **Experimental:** compilado y probado al arrancar por GitHub Actions, aún sin probar en un Mac real por el mantenedor. Se agradecen los reportes. |

El instalador y el programa usan automáticamente el idioma de Windows (inglés si no es uno de los nueve); se puede cambiar en Ajustes. Windows no permite que los instaladores anclen programas a la barra de tareas: abre LinguaNova, haz clic derecho en su icono de la barra y elige **Anclar a la barra de tareas**.

## 🛠️ Ejecutar desde el código

Requiere Python 3.10+.

```bash
python -m venv .venv
```

Windows:

```bat
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Linux/macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

La CLI puede iniciarse con:

```bash
python run_cli.py --interactive
```

## 📦 Compilación y distribución

Los scripts de compilación incluidos forman parte del código fuente correspondiente de LinguaNova.

Antes de publicar un binario:

1. crea el binario desde un commit/tag concreto;
2. conserva el código fuente exacto usado para ese binario;
3. publica el código fuente correspondiente junto con el binario o mediante un método permitido por GPLv3;
4. incluye los avisos y licencias de terceros que realmente formen parte de esa compilación;
5. genera y publica sumas SHA-256 de los artefactos.

Consulta [`SOURCE_DISTRIBUTION.md`](SOURCE_DISTRIBUTION.md) y [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md).

En Windows, `build_windows.bat` genera `dist\LinguaNova\` y `build_installer.bat` lo convierte en el instalador (necesita [Inno Setup](https://jrsoftware.org/isdl.php) 6.5 o superior), el ZIP portable y `SHA256SUMS.txt`. Al subir una etiqueta `v*`, GitHub Actions (`release.yml`) compila todo esto para Windows, Linux y macOS y lo publica como versión.

## 🔄 Actualizaciones de LinguaNova

LinguaNova comprueba si hay una versión nueva en las publicaciones de este repositorio (`Mustadio7813/LinguaNova`) al iniciar (se puede desactivar) y desde **Utilidades → Actualizaciones → Buscar actualizaciones**.

- **Versión instalada de Windows:** el aviso ofrece **Actualizar ahora**. LinguaNova descarga `LinguaNova_Setup_<versión>.exe` de la publicación, lo comprueba con el `SHA256SUMS.txt` de esa publicación (un archivo que no coincide se borra y nunca se ejecuta), lo instala en la misma carpeta y se vuelve a abrir. No se instala nada sin tu clic.
- **Portable, Linux y macOS:** el aviso abre la página de la publicación para descargar la versión nueva.
- Si la comprobación falla (sin conexión, sin versiones publicadas…), LinguaNova lo dice en lugar de indicar que estás al día.

El canal de actualización nunca apunta a RenLocalizer. Esto se refiere a **actualizaciones del programa LinguaNova**, no a modelos de IA ni a componentes externos, que se gestionan por separado.

## 📄 Licencia

LinguaNova se distribuye bajo **GNU GPL v3 o posterior (GPL-3.0-or-later)**.

- Texto completo: [`LICENSE`](LICENSE) y [`COPYING`](COPYING).
- Procedencia y atribución: [`NOTICE.md`](NOTICE.md).
- Política de licencia: [`LICENSE_POLICY.md`](LICENSE_POLICY.md).
- Cambios respecto del trabajo base: [`MODIFICATIONS_LINGUANOVA.md`](MODIFICATIONS_LINGUANOVA.md).
- Distribución de código fuente: [`SOURCE_DISTRIBUTION.md`](SOURCE_DISTRIBUTION.md).
- Terceros: [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

**No se añade una restricción “no comercial”.** Los derechos concedidos por GPL-3.0-or-later, incluido el derecho a redistribuir conforme a la licencia, no se limitan mediante `README`, `CONTRIBUTING`, código de conducta ni otros documentos del proyecto.

## Sin garantía

LinguaNova se proporciona sin garantía en los términos de GNU GPL. Revisa las traducciones y conserva copias de seguridad antes de modificar proyectos de terceros.

---

### English provenance notice

**LinguaNova is a separately maintained modified work based in part on RenLocalizer 2.8.19. It is not an official RenLocalizer release and is not endorsed or supported by the original RenLocalizer authors.**

Original project: https://github.com/Lord0fTurk/RenLocalizer  
Upstream copyright notice preserved by this project: Copyright (C) 2025 RenLocalizer V2 Authors  
License: GNU General Public License v3.0 or later (GPL-3.0-or-later)  
Relevant modification-notice date: 2026-10-16
