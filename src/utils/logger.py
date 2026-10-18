# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# LinguaNova: modified work based on RenLocalizer 2.8.19; modification notice date 2026-10-16.
# See LICENSE/COPYING, NOTICE.md and MODIFICATIONS_LINGUANOVA.md.
"""
Hassas Veri Maskeleme ve Güvenli Loglama Modülü
===============================================
API anahtarlarını ve hassas verileri loglara yazılmadan önce maskeler.
"""

import logging
import re
import os
import sys
import platform
from typing import Optional

# Maskelenecek desenler
MASKS = [
    (re.compile(r'(sk-[a-zA-Z0-9\-_]{20,})'), r'sk-***MASKED***'),  # OpenAI / Generic
    (re.compile(r'(AIza[0-9A-Za-z\-_]{30,})'), r'AIza***MASKED***'),  # Google API
    (re.compile(r'(ghp_[a-zA-Z0-9]{30,})'), r'ghp_***MASKED***'),  # Github Token
]

def get_log_path(filename: str) -> str:
    """
    İşletim sistemine ve Taşınabilir mod ayarına göre log dizinini belirler.
    Merkezi path_manager kullanılarak yönetilir.
    """
    try:
        from src.utils.path_manager import get_data_path
    except ImportError:
        # Prevent circular or early import issues if called before path_manager exists
        return filename

    log_dir = get_data_path() / 'logs'
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass  # Will be handled gracefully in setup_logger
        
    return str(log_dir / filename)

class SensitiveDataFilter(logging.Filter):
    """Log kayıtlarındaki hassas verileri maskeler."""
    
    def filter(self, record):
        if not isinstance(record.msg, str):
            return True
            
        msg = record.msg
        # Mesajin kendisindeki hassas verileri maskele
        for pattern, replacement in MASKS:
            if pattern.search(msg):
                msg = pattern.sub(replacement, msg)
        
        # Argümanlardaki hassas verileri maskele (örn: log.info("Key: %s", key))
        if record.args:
            new_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    for pattern, replacement in MASKS:
                        if pattern.search(arg):
                            arg = pattern.sub(replacement, arg)
                new_args.append(arg)
            record.args = tuple(new_args)
            
        record.msg = msg
        return True

def setup_logger(name: str = "LinguaNova", log_file: str = "linguanova.log", level=logging.DEBUG):
    """Güvenli logger yapılandırması."""
    # Her zaman merkezi path_manager ile çözülmüş log dosya yolunu kullan
    log_file = get_log_path(log_file)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Mevcut handlerları temizle (tekrar eklememek için)
    if logger.handlers:
        logger.handlers = []

    # Format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # File Handler — OSError-safe (AppImage read-only mount, permission denied, disk full)
    file_handler = None
    try:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
    except OSError:
        # Primary path failed — fallback to OS temp directory
        try:
            import tempfile
            fallback_dir = os.path.join(tempfile.gettempdir(), 'LinguaNova')
            os.makedirs(fallback_dir, exist_ok=True)
            fallback_path = os.path.join(fallback_dir, os.path.basename(log_file))
            file_handler = logging.FileHandler(fallback_path, encoding='utf-8')
        except OSError:
            # All file logging failed — continue with console only
            file_handler = None

    if file_handler is not None:
        file_handler.setFormatter(formatter)
        file_handler.addFilter(SensitiveDataFilter())
        logger.addHandler(file_handler)
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(SensitiveDataFilter())
    logger.addHandler(console_handler)
    
    return logger
