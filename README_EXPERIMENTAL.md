# Integración nativa en la aplicación principal

**Abre `run.bat` y usa el botón habitual de Traducción.** OCR, selección de
orígenes RPA/RPY/RPYC, lote de cinco idiomas, resultados y creación de ZIP/RAR
están en la ventana principal. Los iniciadores anteriores son alias del mismo
arranque. No se abre una aplicación OCR separada.

Consulta [LEEME_PRIMERO.txt](LEEME_PRIMERO.txt) y
[native_evidence/README.md](native_evidence/README.md). Se requieren Python 3.10+
para las fuentes; la distribución compilada completa incluye su intérprete y
el motor OCR. El código de imágenes se reutiliza como biblioteca interna.

La documentación siguiente es histórica y conserva pruebas de versiones previas.
Sus instrucciones de usar otra ventana o `.venv-next` quedan sustituidas.

---

# LinguaNova Multidioma Experimental · cinco idiomas

Ampliación **0.3.0-ocr-resources.1**, sobre la base **1.1.2** recibida. Se corrigieron el OCR de recursos sueltos y empaquetados, la exportación de formatos nativos, los desplegables del MOD y los nombres secundarios que siguen el idioma de la interfaz. De los 283 archivos protegidos de la base, solo `Main.qml` contiene el cambio de interfaz solicitado; el verificador comprueba su huella exacta y conserva el manifiesto original.

**Estado actual: [LEEME_PRIMERO.txt](LEEME_PRIMERO.txt) y [ocr_evidence/README.md](ocr_evidence/README.md).** Las secciones técnicas siguientes y las carpetas `next_evidence` y `dictionary_evidence` conservan documentación y pruebas de versiones anteriores. Sus restricciones antiguas de OCR, revisiones manuales obligatorias y conservación absoluta de la interfaz quedan sustituidas por las instrucciones actuales.

**Empieza por `LEEME_PRIMERO.txt` y abre `INICIAR_LINGUANOVA.bat`.** El iniciador prepara las dependencias de la ventana nueva. Incluye Diccionario por proyecto, lote de cinco idiomas, OCR con selección del ejecutable y respaldo independiente ZIP/RAR. El flujo y las pruebas de esta revisión están en [docs/DICCIONARIO_OCR_RESPALDO.md](docs/DICCIONARIO_OCR_RESPALDO.md) y [dictionary_evidence/README.md](dictionary_evidence/README.md). Las secciones siguientes conservan también la documentación técnica de la ampliación anterior; `next_evidence` contiene evidencia histórica.

## Iniciar en Windows desde las fuentes

Se probó Python 3.12 en Linux. Para construir en Windows se propone Python 3.12; Windows, Inno Setup y su EXE están **pendientes de ejecución**. Los fuentes originales contienen APIs AST antiguas; Python 3.15 no está certificado por esta entrega.

Desde la carpeta que contiene `run_next.py`:

```bat
py -3.12 -m venv .venv-next
.venv-next\Scripts\python.exe -m pip install -r requirements-next.txt
.venv-next\Scripts\python.exe run_next.py verify
.venv-next\Scripts\python.exe run_next.py
```

Después puede usarse `run_next.bat`. `run.py` sigue siendo el arranque clásico original. `run_next.py classic` carga el QML original y añade una tarjeta al final de Utilidades mediante APIs normales de Qt. Los botones clásicos mantienen su comportamiento histórico; para el flujo solicitado se utilizan los trabajos nuevos.

En Linux, los mismos comandos usan `python3`, `.venv-next/bin/python` y `python3 -m venv`. Tesseract y sus datos de origen son un componente independiente; el texto funciona sin OCR ni modelos generativos.

## Flujo de uso

1. Abre **Traducción** y elige una **copia** del proyecto, su carpeta raíz o `game/`. El flujo nuevo lee esa copia; prepara las salidas fuera del juego.
2. Elige Español, Francés, Portugués, Ruso o Inglés. Español ofrece LATAM (predeterminado) y España dentro de una sola entrada base. El origen admite `auto` y códigos de los proveedores; no se limita a esos cinco idiomas.
3. Selecciona motor y, si corresponde, modelo/endpoint. Crea el trabajo, revisa su resumen y pulsa Iniciar. El contrato fija el destino para texto e imágenes. Cambiar los controles no cambia un trabajo activo.
4. Revisa la actividad, las métricas y las causas por entrada. En **Revisión textual** puedes corregir o conservar un original con motivo. Reanudar vuelve a validar esas decisiones antes de escribirlas.
5. Para imágenes, elige modelos OCR **del origen**, por ejemplo `eng` o `jpn`, instalados en Tesseract. Una imagen japonesa no se reconoce con español porque el destino sea LATAM.
6. En **Imágenes y OCR**, revisa transcripción, límites y perfil tipográfico. El editor avanzado muestra un JSON completo: debes identificar la fuente y su hash, ajustar efectos y límites, y registrar evidencia o una aproximación expresamente aprobada. Reanuda para componer; después revisa la candidata, apruébala y reanuda para exportarla. Sin estas decisiones, no se publica esa imagen.
7. En **Utilidades**, al final está **Empaquetar y compartir traducción**. Elige resultados de la misma copia/versión, uno por destino/perfil, el formato **ZIP o RAR**, la ruta y revisa archivos, tamaño y pendientes. La acción también está accesible desde la tarjeta añadida a Utilidades clásicas.

Una interfaz desconocida **no recibe un selector alternativo**. La integración de esta entrega usa una receta ligada al SHA-256 de una pantalla que ya ofrece un punto de extensión `use linguanova_preferences_languages`. La receta incluida corresponde únicamente al fixture controlado. La integración de un juego sin ese punto compatible requiere otro adaptador/receta y pruebas; **no está implementada universalmente**. No se pide editar los originales del desarrollador para sortear esta condición.

## Motores y credenciales

Se conservan Google, Bing, DeepL, LibreTranslate, OpenAI, DeepSeek, Gemini y Pseudo. La matriz está en `linguanova_next/data/provider_capabilities.json`; distinguir soporte de código de inferencia real.

Las credenciales nuevas se leen del entorno y no se guardan en trabajos ni ZIP del jugador:

```powershell
$env:LINGUANOVA_NEXT_OPENAI_KEY = "SU_CLAVE"
# Equivalentes: DEEPL, GEMINI, DEEPSEEK y LIBRETRANSLATE.
.venv-next\Scripts\python.exe run_next.py
```

Google/Bing no necesitan clave en las implementaciones recibidas. LibreTranslate requiere una instancia explícita. DeepSeek conserva la ruta API compatible con OpenAI. La nueva ruta Gemini implementa sus instrucciones de perfil sin modificar el cliente antiguo. Los motores MT reciben el código base y los metadatos de perfil; eso **no garantiza** la variante editorial. Las infracciones detectadas se rechazan; el resto mantiene revisión lingüística pendiente. Pseudo se identifica como prueba y nunca certifica traducción real.

No se ejecutaron servicios de traducción reales en esta entrega. Las pruebas de traducción usan un diccionario de fixture, identificado como tal. OCR e integración con el motor RenPy sí tienen pruebas reales separadas.

## Archivos y recuperación

- Configuración nueva: `%LOCALAPPDATA%\LinguaNova\next\settings_next.json` en Windows; `$XDG_DATA_HOME/LinguaNova/next` o `~/.local/share/LinguaNova/next` en Linux.
- Trabajos: `jobs/<id>/`, con contrato, inventarios, resultados, decisiones, eventos y cobertura. `published/` contiene una generación válida; `published.previous/` conserva la anterior. La publicación del directorio incluye su manifiesto autoritativo.
- Texto, MOD, reconocimiento OCR y composición usan namespaces de caché separados. Un rechazo no entra como traducción aceptada. OCR identifica también los hashes de los datos de reconocimiento.
- Reanudar exige la misma base, fuentes/recursos, catálogo, perfiles, reglas y glosario. Si cambian, crea otro trabajo. La elección del jugador no depende del destino del creador.
- No hay importación automática de cachés españolas heredadas ni de correcciones MOD antiguas sin variante. Se preservan y requieren revisión explícita. La API `SettingsStore.import_legacy_copy()` importa una copia compatible; no hay sincronización silenciosa.
- Cancelar conserva los checkpoints aceptados y la última publicación válida. Retirar los archivos nuevos permite volver a `run.py`; nunca hay que restaurar los 283 archivos originales.

## Paquete del jugador

ZIP funciona sin instalar un compresor externo. Para **crear RAR**, LinguaNova utiliza RAR/WinRAR instalado en el equipo del creador: busca `rar` en PATH o `Rar.exe` en la carpeta habitual de WinRAR. También puede configurarse `LINGUANOVA_NEXT_RAR_EXECUTABLE` con la ruta absoluta de `Rar.exe`. El compresor conserva su licencia y no se redistribuye. Si falta, se muestra la causa y puede elegirse ZIP; no se cambia una extensión para fingir un RAR.

Ambos formatos contienen los mismos textos y las imágenes finales, comprobados por rutas y hashes tras comprimir. El destinatario solo necesita poder descomprimir el archivo; no necesita WinRAR para crear archivos, LinguaNova ni dependencias de procesamiento. La reproducibilidad binaria del RAR depende de la versión/plataforma del compresor; los archivos extraídos sí deben coincidir exactamente con el manifiesto.

El ZIP contiene directamente `game/`, `LEEME_INSTALACION.txt` y `manifest.json`. Se cierra el juego, se descomprime y se copia **game/ a la raíz donde está el ejecutable**, combinándola con la existente. **No** se pega dentro de `game/`: eso crearía `game/game/`.

Las rutas completas se conservan: `game/images/capitulo_01/telefono/mensaje.png` pasa, por ejemplo, a `game/tl/spanish_latam/images/capitulo_01/telefono/mensaje.png`. El jugador recibe imágenes terminadas y scripts `.rpy`; no necesita Python externo, LinguaNova, OCR ni modelos. RenPy hace su compilación habitual. No se distribuye bytecode pretendidamente universal.

El paquete incluye una constancia de propiedad bajo `game/linguanova_next_packages/`; es metadato, no un instalador. La copia manual no comprueba hashes ni hace respaldos automáticamente. El creador debe revisar colisiones y conservar su respaldo. La utilidad de ensayo `install_copy()` rechaza archivos ajenos/modificados y puede revertir una escritura fallida. La retirada automática solo elimina archivos listados cuyo hash coincide; los `.rpyc` creados posteriormente por RenPy requieren comprobar su procedencia, como explican las instrucciones del paquete.

Los ejemplos `examples/Paquete_fixture_multidioma_EXPERIMENTAL.zip` y `.rar` se probaron en segundas copias del **fixture incluido**, con rutas acentuadas, cambios en caliente, Original, cierre/reapertura y actualización. **No son paquetes para un juego comercial ni están certificados para otra versión**.

## Pruebas y construcción

```bat
.venv-next\Scripts\python.exe -m pip install -r requirements-next-dev.txt
.venv-next\Scripts\python.exe -m pytest tests\next -q -p no:cacheprovider
.venv-next\Scripts\python.exe scripts\next_ui_smoke.py
build_next.bat
```

`build_next.bat` produce una distribución por carpeta en `dist\LinguaNovaNext`, si el entorno Windows completa la construcción. Hay que conservar toda esa carpeta. El OCR puede suministrarse como componente con ejecutable, DLL, traineddata y avisos de licencia; el importador de componentes está en Utilidades. El worker generativo se construye aparte con `build_next_worker.bat`; no se instala un paquete Python dentro de un EXE congelado.

La construcción Linux se verificó por separado. Su resultado no se presenta como prueba del EXE Windows. Para comprobar una distribución congelada desde otra carpeta:

```text
LinguaNova.exe verify
LinguaNova.exe gui --smoke-output C:\Temporal\LinguaNova_comprobacion
```

La demostración reproducible y la prueba del motor están documentadas en `next_evidence/README.md`. Los resultados finales y los límites concretos se encuentran en `docs/INFORME_FINAL_NEXT.md`.
