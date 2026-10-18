# -*- coding: utf-8 -*-
"""
Data Transfer Utilities
=======================

Handles Import/Export operations for Glossary and other data structures.
Supports: JSON, Excel (.xlsx), CSV (.csv)
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

try:
    import pandas as pd
except ImportError:
    pd = None
    logger.debug("pandas not found. Excel/CSV export limited to JSON.")


def export_glossary_to_file(glossary_data: Dict[str, str], filepath: str) -> bool:
    """Export glossary dict to JSON, XLSX, or CSV."""
    try:
        path = Path(filepath)
        ext = path.suffix.lower()

        if ext == ".json":
            with open(path, "w", encoding="utf-8") as f:
                json.dump(glossary_data, f, indent=2, ensure_ascii=False)
            return True

        elif ext in (".xlsx", ".xls", ".csv"):
            if pd is None:
                raise ImportError("pandas required for Excel/CSV export.")
            df = pd.DataFrame(list(glossary_data.items()), columns=["Source", "Target"])
            if ext == ".csv":
                df.to_csv(path, index=False, encoding="utf-8-sig")
            else:
                df.to_excel(path, index=False)
            return True

        raise ValueError(f"Unsupported format: {ext}")
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise


def import_glossary_from_file(filepath: str) -> Dict[str, str]:
    """Import glossary from JSON, XLSX, or CSV file. Returns {source: target} dict."""
    try:
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        ext = path.suffix.lower()
        glossary: Dict[str, str] = {}

        if ext == ".json":
            with open(path, "r", encoding="utf-8") as f:
                glossary = json.load(f)

        elif ext in (".xlsx", ".xls", ".csv"):
            if pd is None:
                raise ImportError("pandas required for Excel/CSV import.")
            df = pd.read_csv(path) if ext == ".csv" else pd.read_excel(path)

            source_col = None
            target_col = None
            for c in df.columns:
                cl = c.lower()
                if cl in ("source", "original", "text", "id", "key") and source_col is None:
                    source_col = c
                if cl in ("target", "translation", "value", "translated", "tr") and target_col is None:
                    target_col = c

            if source_col is None and len(df.columns) >= 1:
                source_col = df.columns[0]
            if target_col is None and len(df.columns) >= 2:
                target_col = df.columns[1]
            if source_col is None:
                raise ValueError("Could not identify source column.")

            for _, row in df.iterrows():
                src = str(row[source_col]).strip() if pd.notna(row[source_col]) else ""
                tgt = str(row[target_col]).strip() if target_col and pd.notna(row[target_col]) else ""
                if src:
                    glossary[src] = tgt

        else:
            raise ValueError(f"Unsupported format: {ext}")

        return glossary
    except Exception as e:
        logger.error(f"Import failed: {e}")
        raise
