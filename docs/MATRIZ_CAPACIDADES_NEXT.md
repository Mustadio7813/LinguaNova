# Matriz de destinos y proveedores

El catálogo de producción habilita exactamente **cinco idiomas base**. Los perfiles españoles son dos identidades dentro de español.

| Idioma | Locale | Perfil | Carpeta RenPy |
| --- | --- | --- | --- |
| Español LATAM | `es-419` | `latam_neutro_sin_modismos`, v1; predeterminado | `spanish_latam` |
| Español de España | `es-ES` | `espana_estandar_sin_modismos`, v1 | `spanish_spain` |
| Francés | `fr` | Sin cambio regional añadido | `french` |
| Portugués | `pt` | Sin cambio regional añadido | `portuguese` |
| Ruso | `ru` | Sin cambio regional añadido | `russian` |
| Inglés | `en` | Sin cambio regional añadido | `english` |

En la tabla siguiente **NV** significa adaptador/código de destino disponible, **servicio y modelo no verificados por inferencia real**. No equivale a «compatible comprobado». Los códigos API son los base recibidos; el perfil se conserva en el contrato. La matriz autoritativa legible por máquina es `linguanova_next/data/provider_capabilities.json`.

| Proveedor / modelo por defecto | Español | Francés | Portugués | Ruso | Inglés | Instrucción de perfil |
| --- | --- | --- | --- | --- | --- | --- |
| Google / implementación base 1.1.2 | NV `es` | NV `fr` | NV `pt` | NV `ru` | NV `en` | MT sin prompt; validación y revisión regional obligatorias |
| Bing / implementación base 1.1.2 | NV `es` | NV `fr` | NV `pt` | NV `ru` | NV `en` | MT sin prompt; validación y revisión regional obligatorias |
| DeepL / implementación base 1.1.2 | NV `es` | NV `fr` | NV `pt` | NV `ru` | NV `en` | MT sin prompt; clave requerida |
| LibreTranslate / instancia explícita | NV `es` | NV `fr` | NV `pt` | NV `ru` | NV `en` | Depende del catálogo de la instancia; se conserva el fallo si no admite el par |
| OpenAI / `gpt-4o-mini` | NV `es` | NV `fr` | NV `pt` | NV `ru` | NV `en` | Prompt obligatorio, clave requerida |
| DeepSeek / `deepseek-chat` | NV `es` | NV `fr` | NV `pt` | NV `ru` | NV `en` | Prompt obligatorio, API compatible con OpenAI, clave requerida |
| Gemini / `gemini-2.5-flash` | NV `es` | NV `fr` | NV `pt` | NV `ru` | NV `en` | Adaptador nuevo con `system_instruction`, clave requerida |
| Pseudo / prueba | Solo prueba | Solo prueba | Solo prueba | Solo prueba | Solo prueba | Opt-in explícito; no certifica traducción, puede ser rechazado por validación |

Cambiar de modelo o instancia requiere verificar su soporte; los valores por defecto son configuración de código y no una promesa de vigencia comercial. No se cambia silenciosamente a inglés cuando un destino no es compatible. El origen conserva códigos/autodetección de la base cuando el servicio los admite; no se limita a los cinco destinos.

La ejecución controlada cubre seis identidades de salida usando `FixtureProvider`, fuera de la lista de motores de producción. Demuestra propagación del contrato, validación y exportación, no soporte lingüístico de servicios reales. OCR Tesseract usa `eng` en las muestras; otros idiomas de reconocimiento no se probaron. La reconstrucción clásica fue ejecutada; el modelo generativo fijado está integrado pero su inferencia no fue ejecutada.

El catálogo sintético de 139 registros prueba el esquema de resolución sin precalcular pares, activar destinos ni crear carpetas futuras. No acredita cobertura de escrituras, tipografía o proveedores de esos idiomas.
