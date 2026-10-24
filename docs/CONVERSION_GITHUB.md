# Conversión al proyecto modular para GitHub

Fecha: 20 de octubre de 2026.

## Resultado

Se recuperó el proyecto contenido en `LinguaNova_traductor(2).py` sin ejecutar el
script recibido. Las asignaciones de texto y datos binarios se leyeron mediante
el árbol de sintaxis de Python y se escribieron en sus rutas originales.

El resultado conserva **269 archivos originales**: **267 de texto y dos imágenes**.
Entre ellos hay **203 archivos Python**. La versión de la aplicación permanece
en **1.1.0**, tal como figuraba en `src/version.py`.

En la conversión inicial no se cambió ningún archivo original. Las funciones
del traductor, el MOD, la interfaz, los idiomas, los motores presentes, las
pruebas y las dependencias declaradas son las del archivo recibido. La
conversión no añade motores que no estuvieran en esa fuente.

## Archivos añadidos

| Archivo | Motivo |
| --- | --- |
| `LEEME_PRIMERO.md` | Inicio rápido en español. |
| `docs/MAPA_DEL_PROYECTO.md` | Relación entre carpetas, módulos y tipos de corrección. |
| `docs/SUBIR_A_GITHUB.md` | Integración segura de cambios en el repositorio existente. |
| `docs/CONVERSION_GITHUB.md` | Este informe de alcance y verificación. |
| `docs/ORIGEN_ARCHIVOS.json` | Huellas SHA-256 de los 269 archivos y del script recibido. |
| `scripts/verificar_proyecto.py` | Revisión de estructura, sintaxis y JSON; comparación opcional con el origen. |
| `verificar.bat` | Acceso a esa revisión desde Windows. |
| `pruebas.bat` | Acceso a la suite pytest original desde Windows. |
| `.editorconfig` | Configuración básica del editor y de finales de línea. |
| `build/.gitignore` | Excluir directorios de compilación generados, conservando `build/linux/`. |
| `installer/.gitignore` | Excluir los instaladores generados en `installer/Output/`. |

Total de la entrega: **280 archivos**, incluidos **204 Python**. No se incluyen
el script contenedor duplicado, entornos virtuales, modelos descargados,
binarios compilados ni un historial Git previo.

## Integridad

La comparación inicial de bytes verificó **269 de 269 archivos idénticos**.
El manifiesto también contiene huellas normalizadas a LF para que la conversión
de saltos de línea de Git en Windows no se confunda con una modificación.

SHA-256 de `LinguaNova_traductor(2).py` recibido:

```text
b1a6c7f53e15177f72341d32d1a7f3251e661d0bc14045ae28aa52bc8fff917d
```

El programa utiliza ahora `run.py` y los módulos de esta carpeta directamente.
El mecanismo del contenedor para extraer el proyecto a una caché y preparar
dependencias privadas no forma parte de este modo de desarrollo: se utilizan
los BAT y el entorno `.venv` originales del proyecto recuperado.

La URL de actualizaciones sigue siendo `Mustadio7813/LinguaNova`, en
`src/utils/update_checker.py`. Se conservaron también las licencias y los
avisos de terceros originales.

## Comprobaciones realizadas

Entorno de comprobación: Linux, Python 3.12.14.

| Comprobación | Resultado |
| --- | --- |
| Archivos originales, comparados byte por byte | 269/269 idénticos. |
| Sintaxis de archivos `.py` y `LinguaNova.spec` | 205 archivos, sin errores de sintaxis. |
| JSON del proyecto | Diez archivos válidos: nueve idiomas y el manifiesto. |
| YAML de `.github/` | Siete archivos con sintaxis válida. |
| Finales de línea de los cinco BAT | CRLF. |
| `scripts/check_repository_compliance.py` original | OK; informa el canal de actualizaciones ya configurado. |
| Tres comprobaciones de aislamiento del MOD | Aprobadas. |
| Dos comprobaciones de la cola de trabajo | Aprobadas. |
| Comprobación estática de textos con apóstrofos | Aprobada. |

Las seis comprobaciones de regresión se ejecutaron directamente desde las
funciones de prueba ya incluidas en tres archivos de `tests/`; no se simula una
ejecución de toda la suite pytest.

## Estado al momento de la conversión inicial

En la conversión inicial no se ejecutaron la GUI con PyQt6, la suite pytest
completa, las traducciones con servicios reales, los BAT en Windows, PyInstaller
ni Inno Setup. Tampoco se ejecutaron los workflows en GitHub. El entorno de
aquella conversión no incluía todas las dependencias de la aplicación.

`pruebas.bat` permite ejecutar las pruebas originales después de preparar el
entorno con `run.bat`. La revisión estática puede ejecutarse sin esas
dependencias mediante `verificar.bat`.

## Alcance de la conversión inicial

La conversión inicial dejó el código accesible por módulos y no modificó los
269 archivos de referencia en ese momento. El informe anterior describe ese
estado de conversión, no las correcciones aplicadas después.

## Correcciones posteriores a la conversión — 2026-10-20

Se actualizó el código fuente para corregir los problemas de falsos aciertos de
caché y archivos de traducción sucios:

- `src/core/translators/manager.py`: no almacena ni devuelve resultados vacíos
  o idénticos al texto fuente. Al cargar una caché antigua descarta las entradas
  idénticas y marca el archivo para limpieza en el siguiente guardado.
- `src/core/pipeline/orchestrator.py`: descarta como traducción aceptada el
  texto sin cambios procedente de la memoria externa, de la caché o del motor;
  un resultado vacío no se trata como éxito y los resultados no traducidos
  quedan reflejados como pendientes.
- `src/core/tl_parser.py`: conserva el fallback al original para que Ren'Py no
  muestre líneas vacías, protege traducciones manuales y elimina `#ignore` al
  reescribir las líneas de traducción compatibles.
- `run.bat`: crea el entorno con `--without-pip` y aprovisiona `pip` desde el
  Python seleccionado, evitando imprimir el error de `ensurepip` durante el
  primer intento de arranque.
- Las pruebas de regresión se ampliaron para cubrir esas situaciones.

### Validación y publicación

- Suite completa en Python 3.14.7: **1945 aprobadas, 6 fallidas y 2 omitidas**.
  Las seis fallas están en pruebas de extracción de diálogos/IDs de Ren'Py y
  deben revisarse antes de afirmar que la suite completa está limpia.
- Pruebas focalizadas de caché: **57 aprobadas**; pruebas focalizadas de parser
  y salida: **120 aprobadas, 1 omitida**.
- La carpeta de trabajo local no contiene `.git`. Estos cambios están
  preparados en el código y en el ZIP de trabajo, pero no se publicaron en
  GitHub. Antes de integrarlos en `Mustadio7813/LinguaNova`, clona la rama
  actual, aplica y revisa los cambios, ejecuta las pruebas y publica un commit
  revisado. No reemplaces la rama remota con el ZIP completo.
