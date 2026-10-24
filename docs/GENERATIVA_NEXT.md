# Reconstrucción generativa local opcional

## Implementación y modelo seleccionado

Se implementó un adaptador concreto de Diffusers `AutoPipelineForInpainting` para `diffusers/stable-diffusion-xl-1.0-inpainting-0.1`, revisión **115134f363124c53c7d878647567d04daf26e41e**. `linguanova_next/data/sdxl_inpainting_manifest.json` fija los 18 archivos necesarios, incluidos cuatro safetensors fp16, con tamaños y SHA-256 obtenidos de la revisión oficial. Total: **6.941.218.469 bytes**, sin runtime ni espacio temporal.

No se descargaron pesos ni se ejecutó inferencia generativa. Esto es código concreto integrado, con inferencia pendiente; no una prueba simulada del modelo. El flujo clásico real funciona sin ellos.

El modelo recibe original, máscara blanca de restauración y parámetros de fondo. La traducción procede del servicio textual; Pillow compone después las letras con un perfil tipográfico controlado. La salida del modelo se mezcla finalmente con el original para preservar los píxeles y la transparencia fuera de la máscara efectiva.

## Runtime y límites

El worker tiene protocolo JSONL versionado, IDs de solicitud, progreso, errores y cancelación mediante terminación del proceso. Se carga fuera del hilo de UI. El binario congelado del creador exige un worker independiente; `sys.executable` no se utiliza como un supuesto intérprete Python de ese EXE.

Runtime propuesto y comprobación de versiones en código:

- Torch 2.8.0.
- Diffusers 0.35.1.
- Transformers 4.56.2.
- Accelerate 1.10.1.
- Safetensors 0.6.2.

CUDA fp16 tiene un umbral experimental de admisión de 8 GiB libres. CPU float32 requiere aceptación experimental expresa; 32 GiB de RAM es una orientación, no una medición ni una garantía. No se habilita inferencia sin ese consentimiento local del creador. Los fallos conservan el original; puede usarse la alternativa clásica, identificada como `classic_fallback` y con su causa.

La carga es local y con `local_files_only=True`; el proceso fija modo offline. Se verifica la presencia/hash de los archivos antes de activar y ejecutar. El código de instalación conserva directorios por revisión y escribe la activación atómicamente. Esta entrega solo admite la revisión fijada; recuperación entre distintas revisiones futuras y equipos GPU/CPU queda sin comprobar. Un modelo incompatible se rechaza y no reemplaza automáticamente la versión aceptada.

## Instalación

En Utilidades, consulta el manifiesto y elige importar una carpeta local con esos archivos o descargar expresamente la revisión fijada (~6,94 GB). No hay descarga de pesos al importar módulos ni al abrir la aplicación. Los modelos permanecen en el directorio de datos del usuario, fuera de los recursos de solo lectura y del ejecutable.

Para un worker fuente usa un entorno separado con `requirements-next-inference.txt`. Para Windows están `LinguaNova_next_worker.spec` y `build_next_worker.bat`; **no se construyó ni probó ese worker Windows**. La carpeta distribuida necesita todas sus bibliotecas y avisos de licencia. `scripts/next_prepare_component.py` genera un manifiesto desde una carpeta probada y requiere indicar ejecutable, versión y avisos. El importador de componentes de Utilidades verifica esos hashes; no basta con copiar bibliotecas Python a un EXE.

Ejemplo de creación del manifiesto tras reunir los avisos reales:

```text
python scripts/next_prepare_component.py dist/LinguaNovaInference --type inference --executable LinguaNovaInference.exe --version worker-1 --license LICENSES.txt
```

El mismo mecanismo admite un componente `tesseract` con su ejecutable, DLL, carpeta `tessdata` y licencias. El manifiesto identifica bytes y dependencias; por sí solo no demuestra la ejecución en Windows.

Prueba real opcional, después de instalar el runtime y los pesos verificados:

```text
LINGUANOVA_NEXT_TEST_MODEL_DIR=/ruta/modelo LINGUANOVA_NEXT_TEST_DEVICE=cuda python -m pytest tests/next/test_generative_and_components.py -q
```

Sin ese directorio, la prueba se omite con causa explícita; no declara una inferencia aprobada.

## Licencias y fuentes oficiales

La ficha del modelo enlaza **CreativeML Open RAIL++-M, 26 de julio de 2023**, con condiciones de uso y distribución. Se conservó su texto de referencia, SHA-256 `19b6998b569b53ac1fc2158a8a3202c8699a9a4605b47075715d9c96be7fb6d0`, en `next_evidence/model_license_reference.txt`. No se distribuyen pesos en este proyecto. Código Diffusers, Torch, dependencias, pesos y recursos del juego tienen licencias distintas; construir un worker exige sus avisos reales. Una imagen derivada no concede permiso automático para compartir recursos de un juego.

Fuentes verificadas durante la implementación:

- https://huggingface.co/diffusers/stable-diffusion-xl-1.0-inpainting-0.1
- https://huggingface.co/api/models/diffusers/stable-diffusion-xl-1.0-inpainting-0.1?blobs=true
- https://huggingface.co/docs/diffusers/en/using-diffusers/inpaint
- https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/d5d78e4/LICENSE.md
- https://tesseract-ocr.github.io/tessdoc/Installation.html
- https://pyinstaller.org/en/stable/spec-files.html
- https://pyinstaller.org/en/stable/runtime-information.html
- https://www.renpy.org/doc/html/translation.html
- https://www.renpy.org/doc/html/persistent.html
