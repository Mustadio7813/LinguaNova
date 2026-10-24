#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Comprueba la entrega modular sin ejecutar la aplicación ni instalar paquetes."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "docs" / "ORIGEN_ARCHIVOS.json"
SKIP_DIRS = {".git", ".venv", "venv", "env", "dist", "__pycache__", ".pytest_cache", ".tox", "node_modules", "Output"}
RUNTIME_IMPORTS = (
    "PyQt6", "aiohttp", "requests", "charset_normalizer", "orjson",
    "py3langid", "openai", "google.genai", "unrpa", "rpycdec", "rich",
    "yaml", "fontTools", "httpx",
)


def project_files():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            yield Path(base) / name


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparar-origen", action="store_true", help="Detectar cambios frente a la extracción inicial; tolera diferencias LF/CRLF.")
    parser.add_argument("--dependencias", action="store_true", help="Comprobar además que están disponibles los módulos externos requeridos.")
    args = parser.parse_args(argv)
    errors = []
    if sys.version_info < (3, 10):
        print("[ERROR] Se necesita Python 3.10 o superior.")
        return 1
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        original = manifest["files"]
    except (OSError, ValueError, KeyError) as exc:
        print(f"[ERROR] No se pudo leer {MANIFEST.name}: {exc}")
        return 1

    unchanged = 0
    for rel, expected in original.items():
        path = ROOT / rel
        if not path.is_file():
            errors.append(f"Falta el archivo original: {rel}")
            continue
        if args.comparar_origen:
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            same = digest == expected["sha256"]
            if not same and expected.get("text"):
                same = hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest() == expected["sha256_lf"]
            if same:
                unchanged += 1
            else:
                errors.append(f"Modificado respecto del origen: {rel}")

    python_count = json_count = 0
    for path in project_files():
        rel = path.relative_to(ROOT)
        try:
            if path.suffix in {".py", ".spec"}:
                # compile() valida sintaxis; no ejecuta el código ni escribe .pyc.
                compile(path.read_bytes(), str(path), "exec", dont_inherit=True)
                python_count += 1
            elif path.suffix == ".json":
                json.loads(path.read_text(encoding="utf-8-sig"))
                json_count += 1
        except (OSError, SyntaxError, ValueError) as exc:
            errors.append(f"{rel}: {exc}")

    if args.dependencias:
        for name in RUNTIME_IMPORTS:
            try:
                found = importlib.util.find_spec(name) is not None
            except (ImportError, ValueError, AttributeError):
                found = False
            if not found:
                errors.append(f"Dependencia no disponible: {name}")
        print("Dependencias: se comprueba disponibilidad, no compatibilidad de versiones.")

    print(f"Estructura: {len(original)} archivos originales requeridos.")
    print(f"Sintaxis: {python_count} archivos Python/spec revisados.")
    print(f"JSON: {json_count} archivos revisados.")
    if args.comparar_origen:
        print(f"Integridad frente al origen: {unchanged}/{len(original)} archivos iguales (LF/CRLF permitido en textos).")
    for message in errors:
        print(f"[ERROR] {message}")
    print("VERIFICACION: ERROR" if errors else "VERIFICACION: OK")
    print("Esta comprobacion no ejecuta la GUI, las traducciones ni la suite pytest.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
