#!/usr/bin/env python3
"""Conservative repository-publication checks for LinguaNova."""
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent

REQUIRED = [
    "README.md",
    "LICENSE",
    "COPYING",
    "NOTICE.md",
    "UPSTREAM.md",
    "LICENSE_POLICY.md",
    "MODIFICATIONS_LINGUANOVA.md",
    "SOURCE_DISTRIBUTION.md",
    "THIRD_PARTY_NOTICES.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
]

errors: list[str] = []

for rel in REQUIRED:
    if not (ROOT / rel).is_file():
        errors.append(f"Falta archivo obligatorio: {rel}")

def read(rel: str) -> str:
    try:
        return (ROOT / rel).read_text(encoding="utf-8")
    except Exception:
        return ""

license_text = read("LICENSE")
readme = read("README.md")
notice = read("NOTICE.md")
contrib = read("CONTRIBUTING.md")
conduct = read("CODE_OF_CONDUCT.md")
updater = read("src/utils/update_checker.py")

if "GNU GENERAL PUBLIC LICENSE" not in license_text or "Version 3" not in license_text:
    errors.append("LICENSE no parece contener GNU GPL v3.")

if "https://github.com/Lord0fTurk/RenLocalizer" not in readme:
    errors.append("README no enlaza visiblemente al proyecto original.")

if "GPL-3.0-or-later" not in readme:
    errors.append("README no identifica GPL-3.0-or-later.")

if "Copyright (C) 2025 RenLocalizer V2 Authors" not in notice:
    errors.append("NOTICE no conserva el aviso de copyright upstream esperado.")

# Current public updater must not point to RenLocalizer.
if re.search(r'UPDATE_REPO\s*=\s*["\'][^"\']*RenLocalizer', updater, re.I):
    errors.append("El actualizador apunta a RenLocalizer; LinguaNova debe usar su propio canal.")

# This development snapshot intentionally keeps the public source empty.
match = re.search(r'UPDATE_REPO\s*=\s*["\']([^"\']*)["\']', updater)
if match and match.group(1).strip():
    print(f"AVISO: UPDATE_REPO está configurado como {match.group(1)!r}. Verificar antes de publicar.")

for label, body in [("CONTRIBUTING.md", contrib), ("CODE_OF_CONDUCT.md", conduct)]:
    lowered = body.lower()
    for forbidden in (
        "non-commercial covenant",
        "selling the software is not",
        "shall never be sold",
    ):
        if forbidden in lowered:
            errors.append(f"{label} contiene una restricción problemática: {forbidden!r}")

# High-confidence secret patterns only.
secret_patterns = {
    "OpenAI-style key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}

skip_dirs = {".git", ".venv", "dist", "build", "__pycache__"}
for path in ROOT.rglob("*"):
    if not path.is_file():
        continue
    if any(part in skip_dirs for part in path.parts):
        continue
    try:
        if path.stat().st_size > 5_000_000:
            continue
        content = path.read_text(encoding="utf-8")
    except Exception:
        continue
    for label, pattern in secret_patterns.items():
        if pattern.search(content):
            errors.append(f"Posible secreto ({label}) en {path.relative_to(ROOT)}")

if errors:
    print("COMPLIANCE CHECK: FAIL")
    for item in errors:
        print(f"- {item}")
    raise SystemExit(1)

print("COMPLIANCE CHECK: OK")
print("- Procedencia upstream visible")
print("- GPL-3.0-or-later visible")
print("- Archivos legales requeridos presentes")
print("- Sin restricción no comercial activa en gobernanza")
print("- Sin canal de actualización apuntando a RenLocalizer")
print("- Sin coincidencias de secretos de alta confianza")
