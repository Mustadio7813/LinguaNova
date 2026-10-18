# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# MOD
# #MOD — LinguaNova Interface MOD subsystem.
#
# ISOLATION CONTRACT:
# - This package must NOT import src.core.runtime_hook_template.
# - This package must NOT patch the normal TranslationPipeline.
# - This package must NOT modify parser.py, rpyc_reader.py or saving.py.
# - Original game .rpy/.rpyc/.rpa content is read-only input.

MOD_FEATURE_NAME = "MOD"
MOD_HOOK_MODULE = "src.ui_mod.ui_mod_hook_template"
MOD_IMPLEMENTATION_STATUS = "functional_isolated"
