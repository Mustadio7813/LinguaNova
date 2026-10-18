# -*- coding: utf-8 -*-
"""
Pytest global configuration and fixtures.
Ensures deterministic, headless Qt environment execution across CI and local runners.
"""

import os
import sys

# Force Qt offscreen platform plugin in headless environments if not already specified
if "QT_QPA_PLATFORM" not in os.environ and sys.platform != "win32":
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

if sys.platform != "win32":
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    os.environ.setdefault("QSG_RHI_BACKEND", "software")
    os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")

