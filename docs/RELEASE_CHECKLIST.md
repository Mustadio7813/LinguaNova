# Release checklist — LinguaNova

## Código y procedencia

- [ ] La Release se construye desde un commit/tag concreto.
- [ ] `README.md` mantiene visible la procedencia de RenLocalizer.
- [ ] `NOTICE.md` y `UPSTREAM.md` están presentes.
- [ ] `LICENSE` y `COPYING` conservan el texto GPL.
- [ ] `MODIFICATIONS_LINGUANOVA.md` describe los cambios relevantes.
- [ ] No existe una restricción “no comercial” añadida a la GPL.

## Seguridad

- [ ] No hay claves API, tokens, contraseñas ni secretos en el repositorio.
- [ ] Se revisaron archivos de configuración y logs.
- [ ] El actualizador valida integridad antes de ejecutar/reemplazar archivos.
- [ ] Se probaron descargas interrumpidas y fallos de red.

## Terceros

- [ ] Se resolvieron las versiones exactas usadas para compilar.
- [ ] Se inspeccionó el contenido real del paquete final.
- [ ] Se recopilaron licencias/avisos requeridos de los componentes incluidos.
- [ ] `THIRD_PARTY_NOTICES.md` fue actualizado para la Release.

## Binarios

- [ ] EXE/paquete instalable probado en instalación limpia.
- [ ] Portable probado desde una carpeta nueva.
- [ ] La página de discos del instalador muestra solo los discos internos (sin pendrives, discos USB ni unidades de red).
- [ ] La actualización automática se probó con `LINGUANOVA_UPDATE_REPO` apuntando a un repositorio de prueba (Release con instalador + `SHA256SUMS.txt`).
- [ ] Actualización de una versión anterior probada.
- [ ] Actualización mientras LinguaNova trabaja no interrumpe la tarea activa.
- [ ] Temporales del actualizador se limpian.
- [ ] Configuración, glosarios, modelos y archivos de juegos se conservan según diseño.

## GPL / código fuente

- [ ] El código fuente correspondiente es el mismo usado para generar los binarios.
- [ ] Se incluyen scripts/configuración de compilación necesarios.
- [ ] Se crea `LinguaNova-<version>-source.zip`.
- [ ] El código fuente está disponible conforme al método de distribución GPL elegido.

## Artefactos recomendados

- [ ] `LinguaNova_Setup_<version>.exe`
- [ ] `LinguaNova-Windows-x64.zip` (portable)
- [ ] `LinguaNova-<version>-source.zip`
- [ ] `SHA256SUMS.txt`

## Publicación

- [ ] La descripción de la Release identifica la versión.
- [ ] Se resumen cambios importantes.
- [ ] Se enlaza al código fuente/licencia.
- [ ] Se indican limitaciones conocidas.
- [ ] No se afirma compatibilidad universal no probada.
