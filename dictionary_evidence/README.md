# Verificación de la revisión 0.2

Esta carpeta corresponde al Diccionario por proyecto y al recorrido conectado de OCR, cinco idiomas, compresión y respaldo. `next_evidence` conserva la evidencia histórica de la ampliación anterior. No se ha ejecutado un juego comercial suministrado por el usuario.

| Comprobación | Resultado y alcance |
| --- | --- |
| Suite inicial | 45 correctas, 1 omitida; `before.log` |
| Suite final | 62 correctas, 1 omitida; `after.log` y `after.xml` |
| Motivo de omisión | Modelo generativo opcional sin pesos/runtime de inferencia ejecutados |
| Aviso de la suite | Deprecación de `enable_cleanup_closed` del cliente aiohttp original en Python 3.12; no fallo de traducción |
| Interfaz conectada | Acciones `clicked`/`toggled` de los controles QML distribuidos y slots del backend, sin reemplazar métodos de producto |
| Proveedor de la prueba conectada | Adaptador LibreTranslate real contra servidor HTTP local de respuestas controladas; **no demuestra traducción comercial ni calidad editorial** |
| Lote | Cinco idiomas base, español LATAM seleccionado; 85 solicitudes HTTP controladas |
| Reconocimiento | Tesseract real, cuatro originales y cuatro entradas de caché OCR reutilizadas entre destinos |
| Imágenes | Veinte exportaciones por idioma, OpenCV Telea y Pillow reales, revisiones de fixture automatizadas y píxeles fuera de máscara comprobados |
| Compresión | ZIP y RAR genuinos, rutas y contenido verificados; respaldo independiente ZIP/RAR después de la copia receptora |
| Ren'Py | SDK 8.3.7.25031702; 13 procesos nuevos por formato, 26 en total, cinco idiomas, Original, 20 direcciones base y persistencia tras cerrar/abrir |
| Aplicación empaquetada | PyInstaller 6.22.3 en Linux; 111 recursos de código/datos coinciden, verificación, carga QML y OCR real de cuatro imágenes con proveedor Pseudo explícito |
| Interfaz clásica | Carga de la ventana original y tarjeta adicional de Utilidades; archivos originales intactos |
| Google externo | Se envió una frase sintética; el proveedor devolvió un fallo en este entorno. No se contabiliza como traducción real verificada |
| Originales | 283 archivos protegidos conservados byte por byte |

`connected_ui/acceptance.json` contiene los cinco trabajos, sus coberturas separadas, las comprobaciones de rutas y los paquetes producidos. Las revisiones visuales proceden de datos conocidos del fixture, no de una aprobación humana de un juego comercial. Los paths absolutos registrados son los del entorno de prueba: no son rutas que el usuario deba introducir.

`renpy_zip` y `renpy_rar` contienen informes, logs y capturas del motor. Ambos se refieren a los hashes exactos de `examples/Cinco_idiomas_UI.zip` y `.rar`. La prueba inicial de RAR del motor no tenía configurada la ruta del compresor del laboratorio; se corrigió el entorno y se repitió únicamente RAR. `renpy_engine.log` conserva ese incidente y `renpy_rar_retry.log` muestra la ejecución corregida. El paquete no cambió entre ambos intentos.

`frozen_checks.json` comprueba el arranque compilado en Linux y que las cuatro imágenes tienen regiones reconocidas realmente. Esas imágenes permanecen pendientes de revisión en ese ensayo Pseudo, tal como corresponde; la cobertura completa de composición se comprueba en el ensayo QML controlado. No se entrega ese binario Linux como si fuera un ejecutable Windows.

La prueba inicial con Google detectó un método público de configuración ausente en el adaptador nuevo. Se implementaron `get_ui_text` y `get_log_text`, se agregó una prueba de contrato y se volvió a intentar. `live_google_initial.json` registra el defecto inicial; `live_google.json` registra el fallo del proveedor después de corregirlo. No se ocultaron ni convirtieron esos fallos en resultados válidos.

Los casos nuevos cubren reutilización entre idiomas, aislamiento de perfil y proyecto, cambios en las fuentes, decisiones obsoletas, corrupción del Diccionario/snapshot/caché, errores de codificación, cancelación, nombres frente a homónimos, nombres largos en ruso, protección de términos y tokens, modelo OCR faltante y respaldo de rutas/bytes de cinco idiomas.

## Reproducir

Con el entorno nuevo preparado:

```text
python -m pytest tests/next -q -p no:cacheprovider
python scripts/next_connected_acceptance.py --workspace RUTA_NUEVA_DE_PRUEBA --rar
python scripts/next_live_provider_probe.py --output resultado_google.json
```

RAR requiere el compresor instalado y Tesseract requiere modelos del origen. La prueba conectada no contacta proveedores externos: sirve sus respuestas controladas en localhost. El probe Google es independiente y sí envía una frase sintética al motor externo.

Las pruebas Ren'Py requieren el SDK y un servidor de pantalla del equipo de pruebas; sus utilidades están en `scripts/next_engine_acceptance.py`. Las pruebas Windows, el instalador Windows, la inferencia generativa y la compatibilidad con el juego concreto del usuario siguen sin ejecutarse. Esta verificación no permite afirmar ausencia universal de errores.
