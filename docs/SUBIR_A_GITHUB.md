# Integrar este proyecto en GitHub

El repositorio público existente es
[Mustadio7813/LinguaNova](https://github.com/Mustadio7813/LinguaNova). La carpeta
de trabajo y el ZIP de esta entrega no contienen historial `.git`; la rama
principal consultada fue `main`, en el commit
[`5106c67`](https://github.com/Mustadio7813/LinguaNova/commit/5106c67e6645cdd5cd923c4a93b0ee42722d317f).

## Flujo seguro para actualizar el repositorio existente

Clona la rama actual en una carpeta nueva y copia **solo los archivos que
cambiaron** desde esta entrega, sin copiar `.venv`, cachés, `build/`, `dist/` ni
el ZIP dentro del repositorio clonado. En la raíz deben quedar `run.py`, `src/`,
`tests/` y `.github/`.

Revisa el diff antes de preparar un commit:

```bash
git clone https://github.com/Mustadio7813/LinguaNova.git
cd LinguaNova
git status
git diff --check
```

Después de copiar los cambios revisados desde el ZIP, ejecuta `git status`,
`git diff --check` y `python -m pytest tests -q`. La suite completa ya presentó
seis fallas en pruebas de extracción Ren'Py; revisa si siguen presentes y no
las declares corregidas sin evidencia. No uses `git init`, no sobrescribas la
rama remota con una carga completa y no hagas push si el diff incluye cambios
ajenos o las pruebas pendientes no están explicadas.

Cuando el diff y la validación sean aceptables, crea una rama, confirma los
cambios y abre una pull request o publica siguiendo las reglas de tu repositorio.
Las herramientas usadas para esta revisión permitieron leer GitHub, pero no
crear commits ni hacer push al repositorio.

## Archivos y compilación

El `.gitignore` excluye `.venv/`, `dist/`, registros y datos de uso. El proyecto
conserva sus avisos GPL, dependencias y scripts de compilación.

`run.bat` y `build_windows.bat` utilizan archivos del proyecto directamente. Ya
no dependen del script grande que los contenía.

## Configuración que se conserva

- `.github/workflows/tests.yml`: pruebas y comprobaciones de inicio.
- `.github/workflows/compliance.yml`: comprobaciones del repositorio.
- `.github/workflows/release.yml`: compilación de las distribuciones.
- `src/utils/update_checker.py`: `UPDATE_REPO = "Mustadio7813/LinguaNova"`.

Los workflows se ejecutan en GitHub según sus eventos y la configuración del
repositorio. La lectura del repositorio no ejecuta ni cambia esos workflows.
El workflow de publicación responde a etiquetas `v*`; su ejecución manual
prepara compilaciones.

Si utilizas otro repositorio para distribuir actualizaciones, esa URL debe
ajustarse en una corrección posterior. Esta conversión no cambia el canal.

También se conserva la documentación anterior en
[GITHUB_FIRST_UPLOAD.md](GITHUB_FIRST_UPLOAD.md); sus indicaciones para crear un
repositorio nuevo son históricas y no se deben seguir para actualizar el
repositorio público existente.
