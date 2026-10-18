[English](CONTRIBUTING.md) · **Español**

# Contribuir a LinguaNova

Gracias por ayudar a mejorar LinguaNova. Son bienvenidos los reportes de errores, las traducciones de la interfaz, las pruebas y el código.

> [!NOTE]
> LinguaNova está en beta y lo mantiene una sola persona. Las revisiones pueden tardar unos días. Los Pull Requests pequeños y enfocados se revisan antes.

## Antes de empezar

- **Errores:** abre un Issue con la plantilla de error. Incluye la versión de LinguaNova, la versión de Ren'Py del juego, el motor que usaste y la parte relevante del log. Nunca pegues claves API.
- **Cambios grandes** (un motor nuevo, un formato de archivo nuevo, cambios en el pipeline o en el MOD): abre primero un Issue para acordar el enfoque antes de dedicarle tiempo.
- **Correcciones pequeñas** (erratas, un texto de locales, un error evidente): puedes abrir un Pull Request directamente.

## Preparar el entorno

Requiere Python 3.10+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Ejecuta las pruebas y la comprobación del repositorio antes de abrir un Pull Request:

```bash
python -m pytest tests/ -q
python scripts/check_repository_compliance.py
```

En Linux sin pantalla, ejecuta las pruebas con `xvfb-run -a python -m pytest tests/ -q`.

## Flujo de trabajo

1. Haz un fork del repositorio y crea una rama desde `main` (por ejemplo `fix/comillas-escapadas`).
2. Mantén cada Pull Request enfocado en un solo cambio.
3. Añade o actualiza pruebas. Una corrección de error debería incluir una prueba que falle sin la corrección.
4. Actualiza la documentación cuando el cambio afecte a los usuarios.
5. Firma cada commit (ver abajo).
6. Abre el Pull Request y completa la plantilla.

## Firma (Developer Certificate of Origin)

LinguaNova usa el [Developer Certificate of Origin 1.1](https://developercertificate.org/) (DCO). Al añadir una línea `Signed-off-by` a un commit, certificas que escribiste el cambio, o que tienes derecho a enviarlo, y que puede distribuirse bajo la licencia del proyecto.

Añade la línea automáticamente con `-s`:

```bash
git commit -s -m "Corrige comillas escapadas en diálogos"
```

Esto genera:

```text
Signed-off-by: Tu Nombre <tu-correo@example.com>
```

Puedes usar tu dirección noreply de GitHub (`usuario@users.noreply.github.com`) si no quieres publicar tu correo. Si olvidaste firmar tu último commit, ejecuta `git commit --amend -s --no-edit` y vuelve a hacer push.

Si editas archivos desde la web de GitHub, añade tú mismo la línea `Signed-off-by:` al final de la descripción del commit.

## Licencia de las contribuciones

LinguaNova es un trabajo modificado de RenLocalizer y se distribuye bajo **GPL-3.0-or-later**.

- Las contribuciones a código cubierto por la GPL se aceptan bajo GPL-3.0-or-later, salvo que un archivo independiente indique de forma válida otra licencia compatible.
- No se exige cesión de copyright. Conservas el copyright de tu aportación.
- Los contribuyentes figuran en el historial de git y, si la aportación es importante, en `MODIFICATIONS_LINGUANOVA.md`.

**Este documento no limita la GPL.** No añade ninguna prohibición de uso comercial, venta o redistribución. Cualquiera, incluidos el mantenedor y los contribuyentes, puede usar, vender y redistribuir LinguaNova según permite la GPL, siempre que entregue también el código fuente y la licencia. Las preferencias de la comunidad no reducen los derechos concedidos por GPL-3.0-or-later.

## Qué no enviar

- Código propietario que no tengas autorización para redistribuir.
- Claves API, tokens, contraseñas, cookies o datos privados, tampoco dentro de logs, capturas o archivos de prueba.
- Gráficos, fuentes, modelos u otros archivos con licencia incompatible.
- Código copiado de otro proyecto sin conservar su licencia y atribución.
- Textos, imágenes o archivos extraídos de juegos comerciales. Usa cadenas de prueba cortas e inventadas.
- Cambios cuyo objetivo sea saltarse los términos, límites o protecciones de un servicio de traducción.

Si incluyes código de terceros, indica en el Pull Request: proyecto de origen, URL, licencia, archivos afectados y por qué la licencia es compatible.

## Cambios que requieren documentación adicional

Actualiza `MODIFICATIONS_LINGUANOVA.md`, `NOTICE.md` o `THIRD_PARTY_NOTICES.md` cuando un cambio afecte de forma relevante a:

- procedencia o licencia;
- distribución, instalador o versión portable;
- dependencias;
- seguridad;
- el actualizador;
- la arquitectura de traducción;
- el formato de los archivos generados.

## Traducir la interfaz

Los textos de la interfaz están en `locales/*.json`. Cuando añadas una clave, añádela a todos los archivos de idioma (el texto en inglés sirve como provisional) para que ningún idioma muestre una clave sin traducir.

## Código de conducta

Toda participación se rige por [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). Para reportar un problema de seguridad, sigue [`SECURITY.md`](SECURITY.md) en lugar de abrir un Issue público.
