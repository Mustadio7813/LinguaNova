# Muestras controladas del creador

Estos son snapshots de evidencia y capas visuales seleccionadas, no cachés ni trabajos reanudables. Proceden de la última ejecución de `scripts/next_demo.py` y del paquete final incluido en `examples/`. Todos los destinos usan un **diccionario controlado**, no un servicio remoto. El OCR es Tesseract real y la reconstrucción es OpenCV/Pillow real.

El contrato conserva `provider_id: google` como motor solicitado para usar la matriz normal. La fábrica de proveedor fue explícitamente `FixtureProvider`; los candidatos textuales identifican `fixture_dictionary` y `controlled-dictionary-v1`. El puente conserva algunos campos `effective_provider: google` del objeto de prueba: este campo aislado no acredita uso real de Google. La procedencia efectiva de TODA esta demostración es el diccionario. No se usaron claves ni llamadas de traducción remotas.

`automated-fixture-test` identifica decisiones de prueba basadas en la geometría, fuente y efectos conocidos por autoría del fixture. No son aprobaciones editoriales humanas. La fuente DejaVuSans y su hash se conservan; los botones tienen borde/sombra y la imagen del teléfono usa otro tamaño y tratamiento, registrados en sus perfiles. No se aprobaron aproximaciones tipográficas en este ejemplo.

Las rutas temporales fueron sustituidas por `<CONTROLLED_DEMO_WORKSPACE>` y `<EXECUTION_WORKSPACE>`. Se preservan identificadores, métricas, razones, candidatos y estados. Los informes anteriores a la prueba del motor mantienen `in_game_visual_review: not_executed`; la carga posterior está documentada por separado en `renpy_engine/`, sin reescribir el historial.

Cada carpeta incluye cuatro originales, máscaras, fondos, capas de texto y candidatas a escala original. El informe de cobertura no convierte una candidata revisada automáticamente en garantía de fidelidad de otro juego. En ruso siguen pendientes dos títulos latinos y en todos los destinos una cadena técnica incierta; véase `unresolved_entries.jsonl`.
