# Comprobación de OCR, exportación e interfaz

Esta carpeta corresponde a la revisión `0.3.0-ocr-resources.1`. La evidencia
en `next_evidence` y `dictionary_evidence` pertenece a versiones anteriores.

- `tests.xml`: **134 pruebas aprobadas, 4 omitidas**. Incluye OCR real, nueve
  extensiones nativas, recursos RPA 2/3 con prefijos y fragmentos, archivos RPYC
  compilados por el motor, selección individual de RPA/RPY/RPYC, transparencia,
  conservación de secuencias y prevención de cadenas de traducción duplicadas.
- `acceptance.json`: cinco trabajos con Tesseract real, exportación y creación
  de un ZIP compartido, instalación en una segunda copia y originales intactos.
  Se tradujeron 13 imágenes para cada uno de cuatro idiomas: **52 imágenes**.
  El quinto destino coincidía con el idioma de origen y conservó sus 13 imágenes.
- `engine.json`, `engine_spec.json`, `engine.log`: Ren'Py **8.3.7.25031702**
  inició con el paquete instalado, cambió de Original a los cinco idiomas y
  cargó las 13 imágenes en cada estado: **78 cargas correctas**. Se comprobaron
  dimensiones y hashes de los bytes seleccionados por la localización nativa.
- `ui/ui.json`: se abrieron los selectores de origen y destino en la interfaz
  real. En la misma ventana se activaron español, inglés, francés, portugués y
  ruso. Los nombres nativos permanecieron y los subtítulos se actualizaron.
  También se comprobaron los nombres del MOD y sus controles de 44 píxeles.
- `ui/languages_es.png`, `ui/languages_en.png`, `ui/mod_es.png`: capturas del
  resultado, con todos los idiomas dentro de los límites de la ventana.
- `original_ui_warnings.json`: la aplicación recibida también produce avisos
  `implicitWidth` de dos diálogos Material al cambiar de idioma. Se conservan
  en el informe de interfaz; no se detectaron avisos QML adicionales.
- `baseline.json`: comprobación del manifiesto original y de la huella exacta
  del único archivo protegido modificado por la petición de interfaz.
- `change_manifest.json`: archivos añadidos y modificados respecto al ZIP recibido.

Las respuestas de traducción de la prueba de integración fueron **controladas**:
un servidor HTTP local recibió solicitudes del adaptador LibreTranslate real.
Esto comprueba el recorrido OCR → proveedor → imagen → paquete → motor; no
certifica la calidad o disponibilidad de un proveedor comercial. Tesseract,
Pillow, los códecs, OpenCV y Ren'Py sí se ejecutaron realmente. Los registros
conservan rutas temporales del ensayo; no son rutas de instalación requeridas.

La prueba del motor cubre las extensiones PNG, JPG, JPEG, WebP, AVIF, SVG, BMP,
TGA e ICO. Los casos adicionales de secuencias comprueban sus fotogramas y
metadatos, sin afirmar que cualquier Ren'Py reproduzca animaciones GIF/TIFF/APNG.
Las fuentes estimadas, el aplanado de SVG y la recompresión de formatos con
pérdidas siguen siendo limitaciones y constan en los informes de cada imagen.

El motor de prueba se ejecutó en Linux con salida gráfica y audio desactivados.
No se ejecutaron Windows ni el juego del usuario. La prevención de duplicados
es una corrección demostrada de una causa posible de fallo de inicio; para
confirmar el error de un juego concreto hace falta su `traceback.txt`/`log.txt`.

Para repetir las pruebas, desde la raíz del proyecto, instala
`requirements-next-dev.txt` y un SDK oficial de Ren'Py:

```sh
python -m pytest -q tests/next tests/test_qml_integrity.py tests/test_mod_plain_ui_and_selection.py tests/test_mod_ui_language_independence.py
python scripts/verify_ocr_resources.py --workspace /ruta/nueva/de/prueba --renpy /ruta/renpy-sdk/renpy.sh
python scripts/verify_localized_language_ui.py --output /ruta/evidencia-ui
python run_next.py verify
```

La integración requiere Tesseract con `eng`; su carpeta de prueba debe ser
nueva. Las comprobaciones omitidas necesitan RAR/WinRAR o el entorno opcional
de inferencia generativa. El OCR y la reconstrucción clásica no necesitan
ese modelo generativo.
