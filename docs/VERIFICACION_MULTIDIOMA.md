# Verificación de la corrección multidioma

Fecha de esta revisión: 20 de octubre de 2026 (Chile).
Base: `Traductor LinguaNova V2.2.rar`. Versión interna corregida: 1.1.2.
La entrega contiene el código fuente; no exige copiar un parche al juego.

## Resultado y uso

El generador conserva las traducciones instaladas al crear un nuevo idioma.
Reutiliza el selector nativo cuando puede reconocer sus controles, amplía una
opción única Original/English y añade un grupo con los estilos radio del juego
en las Preferencias estándar que todavía no tienen selector. Los archivos
originales del juego se conservan; la integración se escribe en un auxiliar.
Los diseños personalizados no reconocidos disponen del selector de respaldo
con Shift+L. La apariencia final debe comprobarse en la copia real de Eternum.

El traductor genera e instala `game/zzz_linguanova_ocultar_fuentes.rpy` durante
la generación normal y también si se desactiva la integración opcional del menú.
La herramienta de fuentes y el generador MOD lo instalan por sí mismos. Para un
juego ya traducido, la utilidad «Integrar el idioma en el selector del juego»
guarda esta protección sin traducir los diálogos de nuevo. No se necesita copiar
un archivo aparte. Vuelve a abrir el juego después de generar sus archivos.
La protección filtra únicamente los identificadores de recursos propios de
LinguaNova en `renpy.known_languages()`. No elimina fuentes ni fuerza otro
idioma. Si un menú particular contiene un botón de fuentes escrito a mano,
ese botón requiere corregir su pantalla: el filtro actúa sobre la enumeración
automática. Las nuevas fuentes se guardan fuera de `tl/`.

## Causas corregidas

- La regeneración del auxiliar podía conservar únicamente el último idioma.
  Ahora se reconstruye la integración con todos los idiomas instalados.
- Un selector personalizado que no se podía extender terminaba sin auxiliar.
  Ahora se genera el respaldo; se comprueba el guardado y un fallo se informa
  como error. Una escritura fallida conserva el auxiliar anterior.
- El runtime estándar podía usar el idioma del último proceso al seleccionar
  Original, conservar cachés del idioma anterior o interpretar mal el JSON
  actual. Ahora sigue la preferencia activa, limpia los datos al cambiar y
  admite los formatos plano y `translations`/`dynamic` existentes.
- Ren'Py puede registrar las carpetas de recursos bajo `tl/` como idiomas.
  Por eso aparecía `linguanova_fonts`: seleccionarlo no encontraba traducciones
  y mostraba el idioma original. Se filtran esos recursos y las nuevas fuentes
  se sitúan en `game/linguanova_fonts/`, conservando las rutas antiguas.
- Los comentarios sin sangría dentro de una pantalla y los alias de tipos de
  Ren'Py podían romper la copia del menú o la lectura de diccionarios. Se
  corrigieron y se comprobaron también con el motor real.

## Pruebas automatizadas

Python 3.12: **243 pruebas aprobadas, 12 omitidas por las condiciones del
entorno y ninguna fallida**, en 34,85 segundos. Se ejecutaron estos módulos:

```text
tests/test_multilingual_hot_switch.py
tests/test_font_resource_languages.py
tests/test_language_init.py
tests/test_language_activation_tool.py
tests/test_runtime_templates.py
tests/test_toolbox_fixes.py
tests/test_toolbox_tools.py
tests/test_mod_generator.py
tests/test_mod_five_language_bundle.py
tests/test_mod_isolation_contract.py
tests/test_pipeline_e2e.py
tests/test_v283_runtime_perf.py
tests/test_runtime_hook_diagnostics.py
tests/test_clean_tl_and_native_optimization.py
tests/test_mod_language_contract.py
tests/test_mod_five_points.py
```

La cobertura específica comprueba las 20 direcciones entre los cinco idiomas,
los formatos JSON, volver a Original, cachés, archivos ausentes o dañados,
regeneración secuencial, conservación de las pantallas originales, escrituras
fallidas, fuente rusa, ocultación de recursos, listas largas y convivencia con
el MOD. Las pruebas usan datos sintéticos y proveedores simulados.

## Validación con Ren'Py

Se utilizó **Ren'Py 8.3.7.25031702**, con siete juegos de prueba derivados del
ejemplo del SDK. Se ejecutó la acción real `Language()` en las 20 direcciones
posibles entre inglés, español, francés, portugués y ruso. Después de cada par
se volvió a Original y se comprobó el texto obtenido: **140 cambios dirigidos
validados**, además de sus retornos a Original.

| Caso | Comprobación | Resultado |
| --- | --- | --- |
| `native_standard` | Preferencias sin grupo de idiomas | 20/20 |
| `native_original` | Único botón original con estilo radio | 20/20 |
| `native_auto` | Selector que usa `renpy.known_languages()` | 20/20 |
| `native_dynamic` | Lista de pares cargada desde JSON | 20/20 |
| `standard_json` | Diccionario estándar y filtros de texto | 20/20 |
| `automatic_no_menu` | Protección instalada por el traductor con el menú adicional desactivado y fuente cirílica antigua | 20/20 |
| `native_font` | Inyector de fuente rusa y ruta fuera de `tl/` | 20/20 |

Los siete casos pasaron también `renpy.sh <juego> lint` con código de salida 0.
Las pruebas de fuente utilizan un archivo local válido, sin acceder al proveedor
de descargas. Comprueban la carga real y el procesamiento de «Привет» con FreeType,
tanto desde la ruta antigua bajo `tl/` como desde la nueva ruta externa.
Los resultados y la huella de la base recibida están en
`RESULTADOS_MULTIDIOMA.json`.

Estas comprobaciones validan carga, acciones y traducciones en el motor. No
constituyen una prueba visual de Eternum: no se recibió su carpeta `game/` y
el intento de captura en este entorno sin pantalla terminó en un error de
ventana del controlador SDL de prueba. No se ha compilado un EXE de Windows.

## Otras comprobaciones

- Los cinco archivos de interfaz tienen las mismas 1.434 claves; coinciden los
  marcadores de los mensajes modificados.
- La compilación sintáctica revisó 209 archivos Python/spec y la lectura JSON
  revisó siete archivos, incluido este informe de resultados: sin errores
  de sintaxis ni JSON.
- `scripts/check_repository_compliance.py`: aprobado. Conserva su aviso existente
  para comprobar el repositorio de actualizaciones antes de publicar.
- El verificador histórico `scripts/verificar_proyecto.py` informa que faltan
  `locales/de.json`, `fa.json`, `ja.json`, `tr.json` y `zh-CN.json`. Se comprobó
  que esos mismos archivos ya faltan en la base recibida. Su manifiesto corresponde
  a una extracción anterior; se conserva como registro histórico. No se añaden
  idiomas ni se oculta ese resultado para hacer pasar la comprobación.
- No se eliminó ningún archivo de la base recibida. La interfaz QML, los
  motores, las utilidades y la URL de actualizaciones se conservaron.

## Sobre los porcentajes del reporte

El 100 % de la barra indica que el proceso terminó. La proporción de líneas
cambiadas mide otra cosa. En el registro recibido, español termina con
70.665 de 74.460 líneas cambiadas (94,9 %) y portugués con 70.314 (94,4 %).
Permanecen iguales al original 3.795 y 4.146, respectivamente. El reporte
también registra 915 y 601 salidas bloqueadas por protección.

No se puede deducir que todas las líneas sin cambiar sean gemidos, sonidos o
interjecciones. Pueden incluir texto idéntico válido, nombres, contenido técnico
o traducciones rechazadas por caracteres ilegibles y marcadores dañados. Hay
que revisar las líneas y los motivos de rechazo. Esta corrección mejora la
generación y la selección de idiomas; conserva las protecciones de calidad y
no convierte automáticamente esos pendientes en traducciones válidas.

## Archivos principales de la corrección

| Archivo | Cambio |
| --- | --- |
| `src/core/language_menu_template.py` | Selector compartido, grupo nativo y filtro de recursos |
| `src/core/pipeline/saving.py` | Integración acumulativa y guardado verificado |
| `src/core/pipeline/orchestrator.py` | Propagación de errores y una sola generación |
| `src/core/runtime_hook_template.py` | Recarga y limpieza al cambiar de idioma |
| `src/tools/font_injector.py` | Recursos fuera de `tl/` y conservación de otros idiomas |
| `src/ui_mod/generator.py` | Exclusión de carpetas de fuentes del catálogo del MOD |
| `locales/{en,es,fr,pt,ru}.json` | Mensajes del selector y del archivo guardado |
| `src/core/constants.py` | Reconocimiento del auxiliar automático para no extraerlo como texto del juego |
| `src/version.py` | Versión interna 1.1.2 |
| `tests/` | Regresiones del menú, runtime y recursos |

Se conservan el catálogo de cinco idiomas del traductor y las traducciones
preexistentes del juego. El selector puede ofrecer otros idiomas instalados.
Los archivos nuevos deben estar presentes al abrir el juego; después se puede
cambiar de idioma durante la partida sin volver a iniciarlo.
