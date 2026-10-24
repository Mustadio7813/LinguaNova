> Corrección multidioma sobre la base V2.2 (versión interna 1.1.2): consulta
> [LEEME_MULTIDIOMA.txt](LEEME_MULTIDIOMA.txt). El traductor instala automáticamente
> la protección del selector sin eliminar la fuente rusa. No requiere un parche manual.

# LinguaNova: proyecto para GitHub

Este proyecto se recuperó inicialmente de `LinguaNova_traductor(2).py`. El
archivo recibido contenía un proyecto modular guardado como textos y dos
imágenes dentro de un solo script. Los archivos están disponibles como archivos
normales y se pueden editar directamente.

La conversión inicial conservó los **269 archivos originales**. Desde entonces
se han aplicado correcciones al pipeline de caché y traducción, al parser de
salida Ren'Py y al lanzador de Windows. El registro y el alcance de esas
correcciones están en [CONVERSION_GITHUB.md](docs/CONVERSION_GITHUB.md) y
[CHANGELOG.md](CHANGELOG.md).

## Abrir y ejecutar en Windows

1. Extrae el ZIP completo a una carpeta normal, por ejemplo `D:\LinguaNova`.
2. Abre esa carpeta con tu editor. `run.py` es la entrada de la aplicación.
3. Ejecuta `run.bat`. Crea `.venv`, instala o repara las dependencias e inicia
   la interfaz. La instalación de dependencias necesita conexión a Internet.
   Si falla el bootstrap de `pip`, el lanzador intenta crear el entorno sin
   `pip` y provisionarlo desde el Python seleccionado.

Se requiere Python 3.10 o superior; se recomienda Python 3.12 de 64 bits.
Instala Python desde python.org con los componentes `pip` y `venv`.

## Archivos de uso frecuente

| Archivo | Función |
| --- | --- |
| `run.bat` | Preparar el entorno y abrir la interfaz. |
| `run.py` | Iniciar la aplicación desde Python. |
| `run_cli.py` | Iniciar la versión de consola. |
| `verificar.bat` | Revisar estructura, sintaxis Python y archivos JSON sin abrir la aplicación. |
| `verificar.bat --comparar-origen` | Además, comprobar los archivos contra la copia inicial. Los cambios deliberados también se detectan. |
| `pruebas.bat` | Ejecutar la suite original con pytest usando el entorno del proyecto. |
| `build_windows.bat` | Compilar con PyInstaller a `dist\LinguaNova\`. |
| `build_installer.bat` | Crear el instalador con Inno Setup y el ZIP portable. |
| `LinguaNova.spec` | Configuración original de PyInstaller. |

La salida de `build_windows.bat` es una **carpeta completa**, con el ejecutable y
sus recursos. Para distribuir esa compilación, conserva toda `dist\LinguaNova\`.

## Localizar qué corregir

Consulta el [mapa del proyecto](docs/MAPA_DEL_PROYECTO.md). Cada módulo puede
editarse directamente; al iniciar con `run.bat` se utiliza el código de esta
carpeta. Ya no tienes que editar cadenas de texto dentro del script contenedor.

## Actualizar el repositorio de GitHub

El repositorio público ya existe en
[Mustadio7813/LinguaNova](https://github.com/Mustadio7813/LinguaNova). Este ZIP
de trabajo no incluye `.git`; no ejecutes `git init` ni reemplaces la rama
publicada con una carga ciega. Sigue la guía para clonar el repositorio,
integrar los cambios y revisar el diff:
[docs/SUBIR_A_GITHUB.md](docs/SUBIR_A_GITHUB.md).

La URL de actualizaciones que contiene el código se conserva:
`Mustadio7813/LinguaNova`, en `src/utils/update_checker.py`. Crear otro repositorio
no cambia automáticamente esa constante.

## Alcance de la verificación

La conversión y las correcciones posteriores, además de sus comprobaciones y
limitaciones, se documentan en
[CONVERSION_GITHUB.md](docs/CONVERSION_GITHUB.md). No implica una garantía de
que todos los errores de traducción estén corregidos.

Consulta [README.es.md](README.es.md) para la documentación original y
[LICENSE](LICENSE) para la licencia GPL-3.0-or-later.
