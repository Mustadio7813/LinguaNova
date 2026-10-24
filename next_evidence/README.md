# Evidencia y reproducción

Esta carpeta conserva las comprobaciones de la ampliación 0.1. Para el Diccionario y el recorrido conectado de la revisión 0.2 consulta `dictionary_evidence/README.md`; los informes anteriores no equivalen a una nueva ejecución sobre esta revisión.

Todos los resultados aquí descritos proceden de ejecuciones de esta implementación. Los documentos históricos de la base se conservan por integridad y no se presentan como nuevas pruebas.

## Entorno y arranque

Usar Python 3.12 y un entorno separado, instalar `requirements-next-dev.txt` y consultar `environment_final.json` para las versiones efectivamente usadas. Tesseract 5.3.4 estaba instalado externamente con `eng` y `osd`. Para otro origen se requieren sus datos de reconocimiento; el destino de traducción no elige el modelo OCR.

Desde la raíz extraída:

```text
python run_next.py verify
python -m pytest tests/next -q -p no:cacheprovider --junitxml=next_evidence/next_tests_reproduced.xml
python scripts/next_ui_smoke.py
```

Suite histórica, sin ejecutar `tests/next` y sin alterar sus pruebas:

```text
python -m pytest tests --ignore=tests/next -q -p no:cacheprovider --junitxml=next_evidence/historical_reproduced.xml
```

El fallo histórico documentado impide afirmar que toda la suite está verde. Los logs inicial, corregido y final permiten separar dependencias faltantes del comportamiento previo. Los logs intermedios de pruebas nuevas se conservan como historial de desarrollo; la autoridad de la entrega es `next_tests_final.*`.

## Demostración completa

Elegir una carpeta nueva **fuera** de la raíz del proyecto para que las operaciones y cachés no se incorporen a sus fuentes:

```text
python scripts/next_demo.py --workspace C:/Temporal/LinguaNova_demo --rar
```

El script usa `FixtureProvider`: un diccionario controlado de `tests/next/support.py`. No requiere claves y no hace traducción remota. OCR y restauración clásica sí son reales. Aprueba automáticamente geometría/estilo/candidatas conocidos por autoría del fixture, con revisor `automated-fixture-test`; esto prueba el flujo y no certifica una aprobación humana. Crea seis trabajos y un ZIP del jugador. No reutilizar directorios de trabajo archivados como si fueran checkpoints portátiles: las identidades están ligadas a las fuentes y reglas originales de la ejecución.

`--rar` añade un RAR genuino y `rar_demo_summary.json`; requiere RAR/WinRAR en el creador y puede omitirse para ejecutar solo ZIP. Las pruebas de RAR se ejecutaron con RAR 7.23 Linux en evaluación, obtenido del repositorio oficial Debian; el compresor no se incluye en la entrega. También se probaron su ausencia, conservación del paquete anterior, rutas con acentos y contenido binario. Para reproducir las tres pruebas RAR reales, instalar el compresor y, si no está en PATH, configurar `LINGUANOVA_NEXT_RAR_EXECUTABLE`. Sin él, las dos pruebas que lo ejecutan se omiten con causa; la prueba de ausencia sigue ejecutándose.

Las muestras de `samples/` son informes y artefactos seleccionados para revisión, **no cachés operativas**. Las rutas temporales se sustituyeron por etiquetas de procedencia legibles; no se modificaron métricas, rechazos ni estados. Sus campos de procedencia originales y la aclaración de `PROVENIENCIA.md` distinguen motor solicitado y proveedor efectivo de prueba.

## Motor RenPy real

Se usó el SDK oficial **8.3.7.25031702**. No está incluido en el ZIP. En un sistema con pantalla disponible:

```text
python scripts/next_fixture_baseline.py --renpy C:/RenPy/renpy.exe --workspace C:/Temporal/LinguaNova_antes
python scripts/next_engine_acceptance.py --renpy C:/RenPy/renpy.exe --demo C:/Temporal/LinguaNova_demo/demo_summary.json --workspace C:/Temporal/LinguaNova_motor
python scripts/next_engine_acceptance.py --renpy C:/RenPy/renpy.exe --demo C:/Temporal/LinguaNova_demo/rar_demo_summary.json --workspace C:/Temporal/LinguaNova_motor_RAR
```

En Linux se invocó `SDK/renpy.sh` con `--display 127.0.0.1:103`, Xvfb, `SDL_VIDEODRIVER=x11`, `SDL_AUDIODRIVER=dummy` y `RENPY_RENDERER=sw`. Los directorios de datos del jugador son separados y se excluyen de esta entrega. La prueba copia el contenido final del paquete en una segunda copia del fixture situada en una ruta con espacios/acentos. El harness de observación es exclusivamente de prueba y no integra el paquete del jugador.

`renpy_engine/acceptance.json` agrega 15 procesos y las verificaciones; `run_*.json` conserva resultados individuales. Las capturas `preferences_*.png` muestran Preferencias y una vista de estados de imágenes añadida por el harness. `preferences_before_fixture.png` muestra la pantalla fuente sin paquete ni grupo de idiomas. Son capturas de un **fixture**, no de un juego comercial.

`renpy_engine_rar/` registra otras 15 ejecuciones instaladas desde el RAR final; su `acceptance.json` identifica la extensión y SHA-256 del archivo realmente usado. El destinatario recibe los mismos archivos finales en los dos formatos.

Las 20 direcciones son cambios entre cinco idiomas ya instalados; no representan traducciones automáticas de todos los pares. Los dos perfiles españoles producen seis opciones concretas, 30 direcciones entre ellas, más 6 regresos a Original. Se comprueban texto/carga de imágenes por hashes y persistencia del perfil tras un proceso nuevo. No se automatizaron clics ni navegación de mando.

## Distribución congelada

Se ejecutó en Linux:

```text
python -m PyInstaller --noconfirm --workpath /ruta/temporal/build --distpath /ruta/temporal/dist LinguaNova_next.spec
```

Luego, desde `/tmp`, se invocó el ejecutable por ruta absoluta:

```text
/ruta/temporal/dist/LinguaNovaNext/LinguaNova verify
/ruta/temporal/dist/LinguaNovaNext/LinguaNova gui --smoke-output /ruta/temporal/comprobacion
```

La segunda ejecución utilizó `QT_QPA_PLATFORM=offscreen`, `QT_QUICK_BACKEND=software`, `QSG_RHI_BACKEND=software`, `QT_QUICK_CONTROLS_STYLE=Material`, `QML_DISABLE_DISK_CACHE=1` y `LINGUANOVA_NEXT_DATA` en otra carpeta temporal. `frozen/smoke.json` identifica `frozen: true`, carga de UI, cinco destinos y verificación de los originales. Además se ejecutó `LinguaNova share salida.rar <ids>` sobre los seis trabajos revisados, con RAR externo configurado y cwd `/tmp`: `frozen_rar_share.log` confirma 33 archivos propios, 24 imágenes finales y verificación del contenido. El binario probado se identifica por hash en `environment_final.json`; no se incluye su carpeta Linux (~694 MB). Esto no acredita Windows ni OCR/inferencia completos dentro del binario.

## Modelos, integridad y entrega

La prueba generativa real se omite al faltar los pesos. `docs/GENERATIVA_NEXT.md` documenta cómo habilitarla y el manifiesto concreto. Los valores de hardware son criterios experimentales, no mediciones de inferencia.

`baseline_manifest.json` conserva la captura original y su identidad fijada en el verificador. `final_integrity.json` compara cada ruta/tamaño/hash antes de empaquetar. `added_files.json` enumera individualmente los archivos nuevos, responsabilidad y hash; su propio hash se omite para evitar una referencia recursiva. El ZIP final también se reabre y contrasta contra los 283 originales. Los informes no incluyen partidas, persistent, pesos ni claves nuevas.
