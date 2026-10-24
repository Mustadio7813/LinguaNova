# Uso de la ampliación 0.2

Abre `INICIAR_LINGUANOVA.bat` en Windows o `python3 start_next.py` en Linux. El iniciador crea un entorno independiente e instala `requirements-next.txt` la primera vez. `run_next.py` permite utilizar un entorno ya preparado. `run.bat` y los archivos de la aplicación clásica se conservan con su comportamiento anterior.

## Diccionario por proyecto

La vista se inicia vacía en cada proceso. Cambiar el origen o el idioma limpia la selección visible. La información guardada permanece en los datos del creador y nunca se envía al paquete del jugador.

Antes de crear un trabajo se calcula la identidad de la ruta canónica de `game/`, se comprueban los archivos de origen y se prepara el inventario textual. La ruta raíz y su carpeta `game/` identifican el mismo proyecto. Dos carpetas diferentes se tratan como proyectos diferentes, incluso si contienen archivos idénticos.

Se excluyen traducciones instaladas, partidas, cachés y auxiliares propios del análisis neutral. El contrato de cada trabajo también conserva una huella más amplia que incluye los recursos y traducciones instaladas para impedir reanudar sobre un juego modificado.

Si las fuentes coinciden, se reutilizan el inventario y las entidades para otro idioma. Se vuelven a comprobar sus hashes; reutilizar no significa confiar ciegamente en archivos antiguos. Si cambian las fuentes, se actualiza el análisis y las decisiones de otra revisión quedan pendientes de una nueva aprobación. No se borran como si nunca hubieran existido.

| Información | Ámbito |
| --- | --- |
| Inventario y evidencia de nombres | Juego, versión de archivos y modo de extracción |
| Traducción o conservación manual de términos | Juego, versión, idioma y perfil |
| Decisiones incluidas en un trabajo | Snapshot inmutable y huella comprobada |
| Texto que aparece al iniciar la aplicación | Ninguno; la vista empieza vacía |

Las declaraciones `Character("Nombre")` aportan evidencia fuerte. La conservación automática queda limitada a sus ocurrencias declaradas. Una aparición de la misma palabra en diálogo no se considera automáticamente un nombre. Como las cadenas nativas `old/new` tienen una sola traducción por texto original, una colisión entre nombre y homónimo queda pendiente en lugar de extender la decisión a todos sus usos. Los términos de interfaz repetidos se proponen para revisión; una decisión explícita se aplica al idioma seleccionado. Los marcadores de Ren'Py y los límites de palabra se respetan al proteger terminología para el proveedor.

La extracción usa los formatos admitidos por los lectores existentes, incluidos guiones compilados y archivos cuando son compatibles. Los formatos opacos, fallos de lectura y recursos no inventariados aparecen en diagnósticos. Esto no constituye una certificación de cobertura completa de cualquier juego.

## Traducción e imágenes

Selecciona origen, destino, perfil y motor en **Traducción**. Puedes preparar el Diccionario antes para revisar decisiones, o crear el trabajo directamente: la preparación se ejecuta automáticamente antes de enviar textos al proveedor.

Para imágenes activa **Imágenes y OCR** y comprueba Tesseract. Puedes elegir su ejecutable desde la aplicación. Los modelos instalados deben corresponder al texto original: `eng` reconoce inglés; el destino de traducción sigue siendo el idioma del trabajo. La falta del ejecutable o del modelo de reconocimiento bloquea la preparación del trabajo con imágenes.

El OCR inventaría las regiones y su confianza. **Imágenes y OCR** permite corregir la transcripción y los límites, revisar la fuente y efectos y registrar la evidencia del estilo. El editor avanzado recibe un borrador desde el botón de preparación; el perfil debe indicar `identified` o una aproximación aprobada, una fuente presente en el proyecto con su hash y un motivo de revisión. Al reanudar se restaura el fondo y se componen las letras. La imagen candidata necesita aprobación visual; una reanudación posterior exporta su versión final.

El método clásico utiliza Tesseract, OpenCV y Pillow. El modelo generativo es opcional y no se ha ejecutado en esta verificación. Las imágenes sin detección no se dan por carentes de texto. JPEG, animaciones, atlas y formatos no compatibles quedan pendientes con su motivo; no se les atribuye cobertura visual completa.

## Cinco idiomas y un solo archivo

**Traducir los 5 idiomas** crea trabajos separados para español, francés, portugués, ruso e inglés y utiliza el perfil español seleccionado. Si el idioma de origen coincide con un destino y el resultado permanece igual, no se acepta por ello como una traducción nueva: puede necesitar una decisión explícita de conservación. Cada trabajo se revisa desde el selector de **Revisión textual**.

La lectura OCR del mismo original y los mismos modelos se comparte. La traducción de cada región y la composición final se realizan por destino, porque cambian la longitud, el alfabeto y la distribución. No se copia una única imagen traducida a los cinco idiomas.

| Imagen original | Ejemplo de imagen francesa |
| --- | --- |
| `game/gui/boton.png` | `game/tl/french/gui/boton.png` |
| `game/images/telefono/mensaje.png` | `game/tl/french/images/telefono/mensaje.png` |

En **Utilidades**, selecciona los trabajos del mismo proyecto y versión, revisa el contenido y crea ZIP o RAR. El paquete combina las carpetas de idioma y una única integración de Preferencias cuando existe una receta válida. No mezcla versiones de un mismo destino. El destinatario descomprime y copia `game/` sobre una copia compatible; los recursos ya están traducidos y compuestos.

La integración del selector se ha comprobado en el juego sintético suministrado. Un juego desconocido necesita su propia integración comprobada. La ausencia de receta se declara en la vista previa y el manifiesto; no se anuncia como integración universal.

## Respaldo independiente

En **Utilidades > Respaldar traducciones existentes** selecciona un juego con `game/tl` y un destino fuera de `game/`. Este proceso no necesita trabajos previos ni un proveedor de traducción. Comprime todos los idiomas presentes, sus imágenes con las rutas existentes, las fuentes auxiliares y los archivos de integración/propiedad conocidos de LinguaNova. No copia partidas, cachés ni datos del creador. Una imagen reemplazada fuera de `game/tl` por otra herramienta requiere identificación explícita y no se adivina como traducida.

ZIP utiliza la biblioteca estándar. RAR utiliza RAR/WinRAR instalado en el equipo creador o la ruta configurada mediante `LINGUANOVA_NEXT_RAR_EXECUTABLE`. El destinatario solo necesita descomprimir. Antes de publicar se comparan rutas, tamaños y hashes; RAR se compara también con el contenido ZIP validado. Un fallo conserva el archivo anterior.

También puede ejecutarse independientemente desde terminal:

```text
python run_next.py backup "C:\Juegos\Mi juego" "C:\Respaldos\Cinco_idiomas.zip"
python run_next.py backup "C:\Juegos\Mi juego" "C:\Respaldos\Cinco_idiomas.rar"
```

## Cobertura, caché y fallos

El análisis del Diccionario no agrega entradas artificiales ni modifica el denominador del inventario. La cobertura compara las salidas realmente escritas. Procesamiento, texto modificado, traducción validada, conservación y cobertura visual se informan por separado. Que una tarea haya terminado no equivale a que todo esté traducido o revisado.

La caché de texto incluye proyecto, snapshot del Diccionario, fuente, contexto, idioma/perfil, proveedor/modelo y reglas. Se separan texto, MOD, OCR y composición. Las entradas se guardan en un esquema nuevo con identidad y huella; una incoherencia se informa como fallo. Los candidatos textuales se validan antes de guardar y después de leer. El OCR comparte el análisis de origen entre idiomas; la composición mantiene identidad de destino y tipografía.

Los errores observables de la ruta nueva se muestran en la aplicación y se guardan con fase, proyecto/recurso, excepción y traza en `diagnostics/errors.jsonl`. Las credenciales configuradas por variables de entorno se ocultan en esos mensajes. La corrupción del Diccionario y de sus snapshots detiene la operación; no se sustituye por una lista vacía exitosa. Los 283 archivos originales no se reescriben, por lo que su implementación histórica sigue conservada.

## Verificación de esta entrega

Las pruebas actuales y sus límites están en `dictionary_evidence/README.md`. La prueba conectada acciona los controles QML distribuidos y utiliza el adaptador real de LibreTranslate contra un servidor HTTP **de respuestas controladas**. Ejecuta OCR real, composición, revisión, veinte imágenes para cinco destinos, ZIP/RAR, copia receptora y respaldo independiente. Las pruebas del motor Ren'Py se ejecutan aparte sobre ese paquete.

Google se probó con una frase sintética y devolvió un fallo desde este entorno. No se ha ejecutado un proveedor comercial con credenciales, Windows, tu juego concreto ni el modelo generativo. Las evidencias anteriores de la ampliación 0.1 permanecen en `next_evidence`; no deben confundirse con la verificación actual.
