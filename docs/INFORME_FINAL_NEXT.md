# Informe de la entrega experimental

Este informe conserva el alcance de la revisión anterior 0.1. El estado actual 0.2, su Diccionario y sus pruebas conectadas se describen en `DICCIONARIO_OCR_RESPALDO.md` y `../dictionary_evidence/README.md`.

La ampliación anterior es ejecutable y revisable desde `run_next.py`. Conserva la base **1.1.2** y añade la versión propia **0.1.0-experimental.1**. La integración comprobada corresponde a un **fixture sintético con un slot explícito de Preferencias**, ejecutado con RenPy 8.3.7.25031702. No se adjuntó un juego comercial y no se certifica compatibilidad universal.

## 1. Implementado

- Arranque nuevo, CLI, panel Qt/QML del creador y acceso al modo clásico. Tarjeta «Empaquetar y compartir traducción» añadida al final de Utilidades mediante composición Qt, sin editar `Main.qml` ni sustituir métodos.
- Cinco destinos base: español, francés, portugués, ruso e inglés. Español LATAM predeterminado y España como perfiles separados, con locale, carpeta RenPy, reglas y cachés propios. Catálogo externo y prueba estructural sintética de 139 registros, sin habilitar 134 destinos adicionales.
- Contrato inmutable, identidad de revisión, cola acotada, bloqueo entre procesos, checkpoints, cancelación y reanudación condicionada a fuentes, reglas, perfiles y glosario.
- Adaptadores para los motores recibidos, instrucciones obligatorias para los perfiles cuando el proveedor admite prompts, validación contextual, sintaxis y contenido. Un resultado automático aceptado sigue sujeto a revisión editorial.
- Extracción y clasificación, revisión explícita de conservaciones, auditoría de solo lectura y reconciliación con lo realmente escrito. Se separan tareas, cambio textual, traducción validada, resolución del inventario, imágenes y rutas observadas.
- OCR real por Tesseract, idioma de reconocimiento de origen separado del destino, regiones y confianza, incertidumbre y segunda detección. Puente exclusivo de procesamiento que rechaza correlaciones o revisiones incompatibles y respuestas tardías.
- Inventario visual y de fuentes, perfiles tipográficos versionados y medidos, máscaras, restauración clásica OpenCV, composición Pillow, cobertura de glifos, dimensiones/transparencia y conservación exacta fuera de la máscara. Aprobación de región/estilo y de candidata como decisiones independientes.
- Worker generativo concreto de Diffusers SDXL inpainting, manifiesto con revisión y hashes, instalación/importación explícita, ejecución local offline, protocolo con cancelación y alternativa clásica. Los pesos son opcionales y no están incluidos.
- Exportación nativa y MOD aislado, staging, hashes y propiedad. Preferencias nuevas sin atajos, filtro original de fuentes reutilizado sin cambios, cambio de idioma y persistencia mediante APIs del motor. Juegos sin receta compatible quedan bloqueados con causa.
- ZIP compartible reproducible y opción RAR genuina con compresor externo del creador. Raíz directa `game/`, destinos separados, recursos finales, un único auxiliar de Preferencias, manifiesto e instrucciones. RAR se verifica por contenido contra el ZIP validado. Ensayo de copia, colisiones, actualización, respaldo, recuperación y retirada de archivos propios.
- Archivos nuevos para construir la aplicación y un worker independiente en Windows, importador de componentes OCR/inferencia y workflow manual de artefactos. El contrato de actualización clásico y sus archivos permanecen intactos; no se publicó una versión.

## 2. Probado y evidencia

| Comprobación | Resultado y alcance | Evidencia |
| --- | --- | --- |
| Base recibida | ZIP SHA-256 `d702b683002f7cebccb92fb582c4b7ac2021b2ab0100cac41106470aaa558747`; 283 archivos, versión 1.1.2; cero modificaciones, eliminaciones o renombrados | `next_evidence/baseline_manifest.json`, `final_integrity.json`, ZIP original en `next_reference/` |
| Pruebas históricas iniciales | 2020 aprobadas, 14 fallidas y 5 omitidas; 13 fallos desaparecen al instalar `socksio` | `historical_initial.log` y XML |
| Base con entorno corregido y repetición final | **2033 aprobadas, 1 fallida y 5 omitidas**; 9 subtests aprobados. Mismo fallo previo: `test_no_second_picker_when_the_game_has_its_own`, resultado `fallback_picker` frente a `not_found` esperado | `historical_environment_fixed.*`, `historical_final.*` |
| Pruebas nuevas finales | **45 aprobadas, 1 omitida**; omisión de inferencia por ausencia del modelo. Contratos, cinco destinos, perfiles, cachés, auditoría, OCR, imágenes, cancelación, exportación ZIP/RAR, copias, actualización y retirada | `next_tests_final.log` y XML; fuentes en `tests/next/` |
| UI fuente | QML nuevo y clásico cargados; tarjeta nueva como último elemento de Utilidades y selector ZIP/RAR renderizado | `qml_smoke_final.log`, `creator_ui.png`, `classic_utilities_added_card.png`, `share_rar_option.png` |
| Compilación Linux | PyInstaller completó; ejecutable invocado desde `/tmp`, fuera del árbol del proyecto. Cargó QML y cinco destinos, comprobó la base y guardó captura. Exportó RAR real desde resultados revisados, con 24 imágenes y hashes comprobados | `linux_build.log`, `frozen_verify.log`, `frozen/smoke.json`, `frozen/creator.png`, `frozen_rar_share.log`. No certifica OCR/traducción/inferencia completos dentro del binario |
| Flujo completo controlado | Seis trabajos, proveedor diccionario explícito, OCR Tesseract real y composición clásica. 4 imágenes por destino/perfil; **24 candidatas** revisadas mediante decisiones automatizadas del fixture | `controlled_demo.log`, `samples/`, `examples/Paquete_fixture_multidioma_EXPERIMENTAL.zip` |
| Motor real y copia del paquete final | **15 procesos nuevos por formato (ZIP y RAR)**, selección/reapertura para 6 destinos/perfiles y Original; en cada formato: 20 direcciones entre los 5 idiomas base, 10 adicionales entre perfiles y 6 retornos a Original; 72 pasos de aplicación | `renpy_engine/acceptance.json`, `renpy_engine_rar/acceptance.json`, JSON de cada proceso, capturas y `renpy_acceptance_zip.log` / `renpy_acceptance_rar.log` |
| Imágenes y persistencia del motor | Los 4 recursos localizados cargaron por hash en cada destino. Perfil y elección sobrevivieron al cierre completo, incluso con `config.language` inicial diferente. La actualización conservó el archivo persistent | Mismos informes del motor; datos del jugador excluidos de la entrega |

Los cambios de idioma se invocaron desde el harness de prueba usando la misma acción del auxiliar; no constituyen pruebas completas de ratón, teclado o mando. Las capturas muestran las Preferencias renderizadas. El harness añade una vista de estados visuales a la copia de prueba; **esa vista no viaja en el ZIP del jugador**.

### Cobertura sin ocultar pendientes

En el fixture hay 11 entradas inventariadas por trabajo. LATAM, España, francés, portugués e inglés procesan 11/11; tienen 7/7 traducciones automáticamente válidas y 10/11 entradas resueltas, incluidas tres conservaciones explícitas del fixture. Ruso conserva 7/7 traducciones válidas y 8/11 entradas resueltas: dos títulos latinos conservados se rechazan por `target_script_mismatch`. En los seis trabajos permanece una omisión incierta de `config.save_directory`; no se publica como texto traducible.

Esos resultados se conservan tal como los informa el código. No se ajusta el denominador para convertir la resolución en 100 %. Las aprobaciones `automated-fixture-test` verifican el circuito y no equivalen a revisión editorial humana. Cada trabajo informa 4/4 imágenes revisadas dentro del inventario controlado; las rutas de un juego ajeno siguen sin comprobar. La prueba posterior del motor aporta evidencia separada y no reescribe retroactivamente los informes del trabajo.

Los campos de motor solicitado de algunos artefactos del fixture dicen `google` porque el contrato usa la matriz normal; el `provider_factory` de la demostración fue sustituido explícitamente por **FixtureProvider**, que devuelve candidatos `fixture_dictionary`. Ningún dato de estas muestras demuestra una llamada real a Google u otro servicio. `samples/PROVENIENCIA.md` documenta esta diferencia.

## 3. No ejecutado o pendiente de verificar

- Proveedores reales Google, Bing, DeepL, LibreTranslate, OpenAI, DeepSeek y Gemini. No se usaron credenciales ni llamadas de traducción remotas. La matriz los marca **no verificados**; tener código no acredita disponibilidad del servicio/modelo ni calidad de variante.
- Inferencia del modelo SDXL elegido, rendimiento, aceleradores, consumo de RAM/VRAM y calidad de restauración. No se descargaron los 6.941.218.469 bytes de pesos. La prueba opcional quedó omitida con causa.
- Construcción, instalación y ejecución **Windows**, OCR/worker congelados y actualización real del instalador. Se entregan archivos de construcción; el binario Linux no se incluye como supuesto EXE Windows.
- Juego real del usuario, otras versiones RenPy, menús personalizados, precargas particulares, navegación de mando y todas las rutas narrativas. No había una copia de juego adjunta.
- Certificación lingüística humana y revisión tipográfica humana de cada recurso final. Se inspeccionaron capturas representativas; las decisiones de lote del fixture son automáticas y están identificadas.
- Descarga completa/importación/activación de los pesos reales y rollback entre revisiones distintas. La implementación solo admite la revisión fijada; las pruebas de instalación de componentes usan archivos controlados pequeños.
- Pipeline completo dentro del ejecutable Linux congelado; se ejecutaron el smoke de arranque, QML, catálogo/base y la exportación RAR desde resultados ya procesados. OCR/composición completos sí se ejecutaron desde fuentes.

## 4. Incompleto o bloqueado

| Función | Causa y efecto actual |
| --- | --- |
| Integración nativa general sin slot | Solo existe la receta del fixture ligada a SHA-256. Un juego desconocido necesita un adaptador verificable que preserve sus archivos; no recibe un selector alternativo. Puede procesarse el trabajo independiente, pero no anunciar un paquete listo para ese juego |
| Captura automática de todas las rutas en ejecución | Hay contratos para importar observaciones, pero no un capturador universal. Las rutas no observadas quedan explícitas |
| Lettering con gradientes/texturas, atlas y animaciones | No hay reconstrucción/composición fiel general. Se registran límites y se exige revisión; no se publican como recursos visuales validados |
| Identificación automática exacta de fuentes | El estimador no acredita identidad. Hace falta identificar la fuente con evidencia o aprobar una aproximación explícita; la fuente exacta del fixture era conocida por autoría |
| Importación editorial automática de datos heredados | No se deduce LATAM/España de `es`/`spanish`, ni se mezclan correcciones MOD inciertas. Se preserva procedencia y se requiere revisión |
| Validación infalible de variantes | Los controles detectan señales contextuales, pero no todos los regionalismos. La obligación editorial permanece y exige revisión |
| Producto Windows listo para distribuir | No hubo sistema Windows de ejecución. Las fuentes y estrategia están entregadas; EXE, instalador y worker requieren construir y probar allí |

La recuperación se realiza retirando componentes nuevos o volviendo a `run.py`; no se restaura código protegido porque no se modificó. Para salidas y datos del creador, conservar `published.previous/` y respaldos. La retirada del paquete solo puede afectar rutas propias cuyo hash coincida; los `.rpyc` creados posteriormente por RenPy requieren revisar procedencia. La copia manual no ejecuta por sí misma comprobaciones ni respaldos.

Esta entrega permite revisar y ejecutar el alcance experimental implementado. No declara cumplidas las verificaciones y funciones enumeradas como pendientes o incompletas.
