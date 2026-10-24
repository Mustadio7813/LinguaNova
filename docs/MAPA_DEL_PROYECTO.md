# Mapa del proyecto LinguaNova

## Carpetas

| Ruta | Contenido |
| --- | --- |
| `src/backend/` | Conexión entre los botones y propiedades QML y las operaciones de Python. |
| `src/core/` | Análisis de Ren'Py, traducción, exportación, validaciones y cola de trabajos. |
| `src/core/pipeline/` | Etapas del traductor principal: extracción, traducción, validación y guardado. |
| `src/core/translators/` | Motores de traducción, selección de servicios, caché y solicitudes. |
| `src/core/editor/` | Carga, comprobación y almacenamiento de traducciones en el editor. |
| `src/ui_mod/` | Generación independiente del MOD, con su propio análisis y hook. |
| `src/gui/qml/` | Ventana principal y componentes visuales. |
| `src/utils/` | Configuración, registros, codificaciones, rutas y actualizaciones. |
| `src/tools/` | Herramientas de fuentes, glosarios, memorias y revisión de Ren'Py. |
| `locales/` | Nueve archivos JSON de idioma de la interfaz. |
| `tests/` | Pruebas que ya estaban en el archivo recibido. |
| `scripts/` | Utilidades de desarrollo y verificación del repositorio. |
| `installer/` | Instalador de Windows y sus traducciones. |
| `build/linux/` | Archivos auxiliares de la distribución Linux. |
| `.github/` | Pruebas y compilaciones automáticas, plantillas y Dependabot. |
| `docs/` | Guías de publicación, distribución y desarrollo. |

## Dónde hacer cada corrección

| Problema o cambio | Archivos principales |
| --- | --- |
| Distribución visual, menús y botones | `src/gui/qml/Main.qml`, `src/gui/qml/components/` |
| Acción que ejecuta un botón, estado y progreso | `src/backend/app_backend.py` |
| Preferencias de la interfaz | `src/backend/settings_backend.py`, `src/utils/config.py` |
| Textos de la interfaz | `locales/es.json` y los otros ocho JSON |
| Secuencia de traducción principal | `src/core/pipeline/orchestrator.py` |
| Extraer texto o generar bloques de traducción | `src/core/pipeline/extraction.py`, `src/core/parser.py`, `src/core/renpy_lexer.py` |
| Traducir, validar y guardar | `src/core/pipeline/translating.py`, `validating.py`, `saving.py` |
| Formato de salida | `src/core/output_formatter.py`, `src/core/tl_parser.py` |
| Archivos `.rpyc` y archivos `.rpa` | `src/core/rpyc_reader.py`, `src/utils/rpa_parser.py`, `src/utils/unrpyc_adapter.py`, `src/utils/unrpa_adapter.py` |
| Google | `src/core/translators/google.py`, `router.py` |
| DeepL, LibreTranslate, Bing y traductor de prueba | `src/core/translators/services.py` |
| Motor seleccionado y caché | `src/core/translators/manager.py`, `base.py` |
| Servicios de IA | `src/core/ai_translator.py` |
| Cola y orden de tareas | `src/core/work_queue.py`, `src/backend/app_backend.py` |
| Generación del MOD | `src/ui_mod/generator.py` |
| Idiomas y compatibilidad de los motores del MOD | `src/ui_mod/languages.py`, `src/ui_mod/engine_support.py` |
| Texto que detecta el MOD | `src/ui_mod/scanner.py`, `parser.py`, `filters.py` |
| Protección de marcadores y calidad del MOD | `src/ui_mod/protect.py`, `quality.py` |
| Hook del MOD | `src/ui_mod/ui_mod_hook_template.py`, `src/ui_mod/hook_check.py` |
| Hook del traductor principal | `src/core/runtime_hook_template.py` |
| Editor de traducciones | `src/backend/editor_backend.py`, `src/core/editor/`, `src/gui/qml/components/EditorPage.qml` |
| Registros y diagnósticos | `src/utils/logger.py`, `src/core/diagnostics.py` |
| Ruta del programa y recursos | `src/utils/path_manager.py`, `run.py` |
| Inicio de Qt y modos gráficos | `run.py`, `src/utils/qt_runtime.py` |
| URL de actualizaciones | `src/utils/update_checker.py`: `UPDATE_REPO` |
| Descarga y comprobación del instalador | `src/utils/auto_updater.py` |
| Versión del programa | `src/version.py` |
| Inclusión de módulos y recursos en el EXE | `LinguaNova.spec` |

Las rutas abreviadas en una celda comparten la carpeta del primer archivo de
esa celda, salvo que se indique una ruta completa.

## Flujo de trabajo

La interfaz se inicia en `run.py`, carga los backends y después
`src/gui/qml/Main.qml`. Las acciones llegan a `AppBackend`, que utiliza la cola y
deriva la operación al traductor principal o al generador del MOD.

`src/core/translation_pipeline.py` es una capa de compatibilidad que vuelve a
exportar las clases de `src/core/pipeline/`. Para modificar el comportamiento
del proceso, abre los archivos de esa carpeta. Algo similar ocurre con
`src/core/translator.py`, que expone las clases de `src/core/translators/`.

## Corregir y comprobar

1. Identifica el módulo y busca pruebas relacionadas en `tests/`.
2. Crea una rama para el cambio, por ejemplo `git switch -c corregir-mod`.
3. Edita los archivos normales del proyecto.
4. Ejecuta `verificar.bat`.
5. Ejecuta una prueba concreta, por ejemplo `pruebas.bat tests/test_mod_isolation_contract.py`.
6. Prueba el comportamiento real con `run.bat` antes de recompilar.

`--comparar-origen` sirve para revisar qué cambió frente a la entrega inicial.
No es un requisito para aprobar una corrección: un archivo corregido tendrá
una huella diferente, como corresponde. Git conserva el historial posterior.
