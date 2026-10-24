# Integración de la ampliación

## Dependencias y autoridad

`run_next.py` → `cli.py` → `bootstrap.Services` → contratos y `TranslationJobRunner`. El coordinador usa una cola acotada y un bloqueo de proceso por ruta real de juego. La extracción, los proveedores, OCR, fuentes y exportación quedan detrás de adaptadores. Los contratos y `baseline.py` no importan Qt, GPU ni clientes remotos.

Cada trabajo persiste idioma base, locale, carpeta RenPy, perfil/versiones, catálogo, reglas, glosario, fuentes, revisión y una identidad calculada. El puente OCR comparte esa autoridad y comprueba correlación, contenido, imagen y cancelación. El proveedor generativo solo restaura fondos; no recibe la autoridad para elegir idioma o dibujar la traducción.

## APIs reutilizadas

- Parser y lector AST de la base para lectura; scanner MOD separado para interfaz.
- `TranslationRequest` y constructores de proveedores compatibles, mediante una configuración nueva de solo lectura.
- Validación de estructura de etiquetas de la base, sin reemplazar sus métodos.
- Descubrimiento acumulativo de idiomas e `install_resource_filter()` recibidos, solo sobre staging.
- `TLParser` para reabrir las cadenas efectivamente escritas y el adaptador de estadísticas originales.

Los generadores antiguos de selector y MOD no se usan para la UI nueva porque mezclan atajos con exportación. El nuevo emisor usa traducciones de cadenas nativas —también aplicables al diálogo sin bloque traducido— y, en modo MOD, un mapa aislado para textos de interfaz. No duplica dos definiciones `old/new`.

La nueva ruta no convierte archivos de datos arbitrarios en scripts funcionales. Compilados o archivos RPA no verificables y recursos visuales no inventariados quedan en diagnóstico. Si existen traducciones compiladas huérfanas en el destino que impidan descartar duplicados, se bloquea su emisión nueva en vez de arriesgar un error al arrancar.

## Preferencias y persistencia

La única receta incluida usa un slot existente dentro de Preferencias. Su fuente se verifica por hash. Los controles nuevos heredan el prefijo de estilos indicado; no añaden teclas, `overlay_screens`, panel flotante ni menú autónomo de idiomas. La elección usa `renpy.change_language()` y `renpy.save_persistent()`, sin asignar `_preferences.language`.

El campo propio de persistencia distingue ausencia de selección y Original confirmado. En el arranque, una elección válida anula el `config.language` inicial compatible y se restaura mediante callbacks del motor. Rutinas personalizadas posteriores pueden imponer otro idioma: esos juegos requieren inspección y una prueba propia. No se certifica ese caso por un test del fixture.

En la UI creadora se carga el QML clásico original con su backend. La tarjeta adicional es un QQuickItem nuevo, añadido al ColumnLayout de Utilidades identificado en esta base congelada. No se cambian funciones, botones previos, orden ni archivos QML. Se usa QApplication para conservar la compatibilidad con los diálogos de herramientas clásicas.

## Exportación y actualización

Se prepara una carpeta nueva, se validan archivos/hashes/duplicados y se publica por cambio de directorio. Un fallo conserva la publicación anterior. `published/output_manifest.json` es la autoridad del resultado; los informes del trabajo son vistas para el creador.

El constructor multidioma comprueba la misma huella de origen y reglas, selecciona una revisión por destino, conserva subcarpetas, combina un único auxiliar de Preferencias y reconstruye un ZIP reproducible. Las constancias de propiedad permiten identificar salidas propias sin atribuirse archivos ajenos. Los cambios de fuentes originales no se realizan para ocultar recursos del menú.

La opción RAR parte de ese contenido validado, comprime mediante RAR/WinRAR local y comprueba de nuevo nombres, tamaños, hashes y bytes de cada miembro. `rarfile` analiza los encabezados; el comando RAR lee miembros sin extraer rutas al disco. No se aceptan enlaces ni paquetes con contraseña. El lector común permite ensayar instalación/actualización también desde RAR. No hay descarga automática ni redistribución del compresor, y no se exige al jugador ningún proceso de creación.

Se conservan los 283 archivos de actualización/construcción recibidos y el repositorio configurado `Mustadio7813/LinguaNova`. El contrato clásico reconoce `LinguaNova_Setup_<versión>.exe` y `SHA256SUMS.txt`. La ampliación tiene versión propia; el instalador experimental fuente mantiene AppId y versión de procedencia 1.1.2. No debe publicarse encima de la versión oficial con ese mismo número. Un release futuro necesita coordinar versión de conjunto, activos, comparador y pruebas Windows. Aquí no se cambió el remoto ni se ejecutó un despliegue.

El workflow nuevo solo tiene disparador manual y crea un artefacto; no publica releases ni responde a los tags `v*` del flujo original.

## Alcance pendiente

No están implementados un adaptador universal de Preferencias sin slot, captura automática de todas las rutas de un juego ajeno, importación editorial automática de datos españoles/MOD heredados ni reconstrucción fiable de lettering con gradientes/texturas o atlas animados. La importación de observaciones por contrato existe; su captura depende de puntos seguros del juego. Los resultados inciertos quedan pendientes y no se usan para fabricar porcentajes completos.
