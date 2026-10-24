# LinguaNova 1.2.0: OCR en la aplicación principal

La entrada normal es `run.bat` → `start.py` → `run.py`. Todos los iniciadores
anteriores redirigen a esa aplicación. La ventana es `src/gui/qml/Main.qml`;
el proceso usa `AppBackend`, `TranslationPipeline` y `TranslationManager`.
El código de lectura y composición de imágenes se reutiliza como biblioteca.

## Prueba real desde el botón de la ventana principal

`acceptance.json` se generó con `scripts/verify_native_main.py` y un SDK oficial
de Ren'Py 8.3.7. Se cargó el QML real, se eligió el motor mediante el método
público del programa y se activó el botón real del lote de cinco idiomas.
El idioma de origen y el modelo OCR estaban en **automático**.

- En cada etapa OCR había **una sola ventana visible de LinguaNova**.
- La cola ejecutó cinco trabajos con el mismo motor de traducción.
- Tesseract real leyó cuatro PNG sueltos y nueve extensiones nativas en RPA.
  El archivo RPA también contenía referencias RPYC compiladas por el SDK.
- Se generaron **52 imágenes traducidas** para español, francés, portugués y
  ruso. El destino inglés conservó las **13 imágenes del idioma original**.
  `five_languages.json` contiene el desglose y los modelos de origen usados.
- La acción nativa de Utilidades creó el ZIP con todos los idiomas instalados,
  las imágenes y los archivos auxiliares. Se instaló en otra copia del juego.
- Ren'Py inició, cambió entre Original y los cinco idiomas y comprobó hashes
  y dimensiones de las 13 imágenes en cada estado: **78 cargas correctas**.
  Véanse `engine.json` y `engine.log`.
- Las imágenes del RPA original conservaron sus bytes.
- `native_main.png` muestra el OCR dentro del flujo principal, su resumen,
  el botón habitual y el progreso de la misma ventana.

La traducción del ensayo usó respuestas **controladas** de un servicio HTTP
local a través del cliente LibreTranslate principal. No se sustituyeron el
OCR, los códecs, el guardado, el empaquetado o el motor Ren'Py por simulaciones.
Los textos que esas respuestas controladas dejaron sin resolver figuran como
pendientes: el ensayo no certifica un proveedor comercial ni traducción total.

## Arranque y regresiones

`bootstrap.json` comprueba un entorno virtual real vacío y una instalación de
pip incompleta: se reparó pip sin invocar `ensurepip` dentro del entorno. Se
usaron rutas con espacios y el mismo intérprete destinado a la aplicación.

**192 casos distintos aprobaron y 4 se omitieron**. `test_summary.json` evita
contar dos veces los casos repetidos.

`final_tests.xml`, `native_final.xml` y `main_regressions.xml` contienen las
pruebas de las bibliotecas y del flujo principal: OCR automático, desactivación,
componente ausente, cancelación con reversión de imágenes, lectura RPA/RPYC,
modelos OCR privados, sintaxis Python 3.10, preservación del idioma original,
cola de trabajos, interfaz, idiomas y recuperación del arranque.

La comprobación de duplicados de traducción también se aplica en el generador
principal, antes de crear los bloques. Las pruebas verifican que una cadena ya
traducida dentro de un RPA, en RPY o RPYC, no se vuelva a generar.

`ui/` verifica los selectores de idiomas de origen y destino al cambiar entre
las cinco interfaces sin reiniciar; conserva los nombres nativos y traduce los
textos pequeños. También comprueba los controles legibles del MOD. Los avisos
`implicitWidth` que aparecen en el informe proceden de dos diálogos Material
ya existentes en la aplicación recibida; no aparecieron avisos QML adicionales.

## Alcance y límites

Se ejecutó Python 3.12.14 en Linux y se comprobó la sintaxis de los módulos
nuevos con la gramática de Python 3.10. Se mantiene el requisito **Python 3.10
o superior**. No se ejecutaron Windows, Python 3.10/3.14 ni el juego del usuario.
El ZIP contiene fuentes y scripts de compilación; no contiene un EXE Windows
compilado y probado. `LinguaNova.spec` exige preparar el OCR antes de compilar
en Windows e incluye el intérprete, bibliotecas, fuentes y runtime OCR en la
distribución completa. El destinatario de esa distribución no necesita Python.

La tipografía se estima; los formatos con pérdida pueden recomprimir píxeles
y SVG se aplana a su resolución nativa. Las imágenes no resueltas se informan.
Las pruebas omitidas requieren RAR/WinRAR o inferencia generativa opcional.
Las carpetas de evidencia anteriores se conservan como historial.

Para reproducir:

```sh
python -m pytest -q tests/test_native_images.py tests/test_source_bootstrap.py
python scripts/verify_native_main.py --all-languages --workspace /ruta/nueva --renpy /ruta/renpy-sdk/renpy.sh
python scripts/verify_localized_language_ui.py --output /ruta/evidencia-ui
python run_next.py verify
```

Referencias de los métodos de preparación utilizados:

- [pip: gestionar otro intérprete](https://pip.pypa.io/en/stable/topics/python-option/)
- [PyPA: instalación de pip](https://pip.pypa.io/en/stable/installation/)
- [Tesseract: modelos oficiales](https://github.com/tesseract-ocr/tessdata_fast)
