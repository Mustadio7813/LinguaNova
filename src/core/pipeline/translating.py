# -*- coding: utf-8 -*-
"""
Translation-stage functions extracted from TranslationPipeline.
"""

import re
import asyncio
import time
from typing import Optional, List, Dict, Tuple, Any, Union

from .constants import (
    SEPARATOR_REMNANTS, PLACEHOLDER_REMNANT_RE, HTML_LEAK_RE,
    PLACEHOLDER_BRACKET_RE, RENPY_TAG_RE, PRINTF_SPEC_RE, HOTKEY_SOURCE_RE,
    OUTER_COLOR_WRAPPER_RE, SAFE_COLOR_HEX_RE,
)


from src.core.tag_structure import introduces_replacement_char, tag_structure_regression


def reset_translation_diagnostics(diagnostic_report) -> None:
    """Reset diagnostic counters before a new translation run."""
    from src.core.diagnostics import DiagnosticReport
    if diagnostic_report is None:
        return
    diagnostic_report.__init__()


def record_translation_guard_event(
    translation_guard_events: List[Dict],
    translation_guard_counts: Dict[str, int],
    translation_guard_sample_limit: int,
    *,
    category: str,
    file_path: str,
    translation_id: str = '',
    original_text: str = '',
    translated_text: str = '',
    detail: str = '',
    line_number: int = 0,
) -> None:
    if category not in translation_guard_counts:
        translation_guard_counts[category] = 0
    translation_guard_counts[category] += 1
    if len(translation_guard_events) >= translation_guard_sample_limit:
        return
    translation_guard_events.append({
        'category': category,
        'file_path': file_path,
        'translation_id': translation_id,
        'line_number': line_number,
        'detail': detail,
        'original_preview': (original_text or '')[:160],
        'translated_preview': (translated_text or '')[:160],
    })


def extract_validation_placeholders(text: str, source_text: str = '') -> List[str]:
    placeholders = PLACEHOLDER_BRACKET_RE.findall(text or '')
    hotkey_match = HOTKEY_SOURCE_RE.match((source_text or '').strip())
    if hotkey_match and placeholders:
        hotkey_suffix = f"[{hotkey_match.group('hotkey').upper()}]"
        stripped_text = (text or '').strip()
        if stripped_text.endswith(hotkey_suffix):
            for idx in range(len(placeholders) - 1, -1, -1):
                if placeholders[idx].upper() == hotkey_suffix:
                    placeholders.pop(idx)
                    break
    return sorted(re.sub(r'\s+', '', ph) for ph in placeholders)


def validate_placeholders(original: str, translated: str) -> bool:
    """
    Çeviri sonrası değişkenlerin doğruluğunu kontrol eder.
    v2.7.2: Fuzzy matching - boşluklu versiyonları da kabul et.
    """
    orig_vars = PLACEHOLDER_BRACKET_RE.findall(original)
    for var in orig_vars:
        if var not in translated:
            var_content = var[1:-1]
            var_normalized = re.sub(r'\s+', '', var_content)
            found = False
            for trans_var in PLACEHOLDER_BRACKET_RE.findall(translated):
                trans_content = trans_var[1:-1]
                trans_normalized = re.sub(r'\s+', '', trans_content)
                if var_normalized == trans_normalized:
                    found = True
                    break
            if not found:
                return False
    return True


def classify_translation_corruption(original: str, translated: str) -> Optional[str]:
    orig = (original or '').strip()
    trans = (translated or '').strip()
    if not orig or not trans:
        return None
    if any(remnant in trans for remnant in SEPARATOR_REMNANTS):
        return 'separator_remnant'
    if '\u27e6' in trans or '\u27e7' in trans or PLACEHOLDER_REMNANT_RE.search(trans) or '<ph id=' in trans or '</ph>' in trans:
        return 'placeholder_remnant'
    if HTML_LEAK_RE.search(trans):
        return 'html_leakage'
    if introduces_replacement_char(orig, trans):
        return 'replacement_char'
    if len(trans) > max(len(orig) * 4, len(orig) + 80):
        return 'length_inflation'
    if not validate_placeholders(original=orig, translated=trans):
        return 'placeholder_set_mismatch'
    if extract_validation_placeholders(orig) != extract_validation_placeholders(trans, source_text=orig):
        return 'placeholder_set_mismatch'
    if '\u27e6' not in orig and '\u27e7' not in orig:
        if sorted(RENPY_TAG_RE.findall(orig)) != sorted(RENPY_TAG_RE.findall(trans)):
            return 'renpy_tag_set_mismatch'
        # Same tags in an order Ren'Py rejects ("{/i} ... {i}") crash the game
        # at display time; the multiset comparison above cannot see it.
        if tag_structure_regression(orig, trans) is not None:
            return 'renpy_tag_order_invalid'
        # v2.8.13: printf-style format specifiers must survive translation
        # intact — a dropped or mutated %-specifier breaks the game's
        # string formatting at runtime ("%d items" → TypeError). The same
        # token-absence guard as the tag check above applies: when the
        # original still carries ⟦…⟧ tokens its specifier count is
        # distorted by the protect step, so comparison is skipped.
        if sorted(PRINTF_SPEC_RE.findall(orig)) != sorted(PRINTF_SPEC_RE.findall(trans)):
            return 'printf_set_mismatch'
    return None


def normalize_outer_color_wrapper(original: str, translated: str) -> str:
    """
    Pure helper: unwrap exactly one balanced outer
    ``{color=#rgb|#rgba|#rrggbb|#rrggbbaa}...{/color}`` pair.

    Returns the inner text only when every strict boundary holds;
    otherwise returns ``translated`` unchanged. Never mutates inputs,
    never logs, never touches global state, and never weakens
    ``classify_translation_corruption()`` — the unwrapped value must
    pass the same full integrity battery as any other translation.

    Boundaries (all must hold):
      1. ``original`` contains zero Ren'Py tags (``RENPY_TAG_RE``),
         including disambiguation ``{#...}`` tags.
      2. ``translated`` is exactly one wrapper: anchored at both ends,
         no leading/trailing text, strict lowercase tag name, and a
         literal safe hex argument (``SAFE_COLOR_HEX_RE``) — no named
         colors, ``gui.*`` references, expressions, or whitespace.
      3. Inner text is non-empty and contains no tags at all
         (no nesting, no stray closers).
      4. The unwrapped value passes ``classify_translation_corruption``
         (separator/placeholder remnants, HTML leakage, length,
         placeholder set, tag set, printf specifiers).
    """
    orig = (original or '').strip()
    trans = translated or ''
    if RENPY_TAG_RE.search(orig):
        return translated
    match = OUTER_COLOR_WRAPPER_RE.match(trans)
    if match is None or not SAFE_COLOR_HEX_RE.fullmatch(match.group('hex')):
        return translated
    inner = match.group('inner')
    if not inner.strip() or RENPY_TAG_RE.search(inner):
        return translated
    if classify_translation_corruption(orig, inner) is not None:
        return translated
    return inner


def get_guard_reason_text(reason: str, config) -> str:
    reason_key_map = {
        'separator_remnant': ('guard_reason_separator_remnant', 'separator markers leaked into the output'),
        'placeholder_remnant': ('guard_reason_placeholder_remnant', 'placeholder tokens leaked into the output'),
        'html_leakage': ('guard_reason_html_leakage', 'HTML markup leaked into the output'),
        'length_inflation': ('guard_reason_length_inflation', 'translated text expanded far beyond the source'),
        'placeholder_set_mismatch': ('guard_reason_placeholder_set_mismatch', 'placeholder structure changed'),
        'renpy_tag_set_mismatch': ('guard_reason_renpy_tag_set_mismatch', "Ren'Py text tags changed"),
        'printf_set_mismatch': ('guard_reason_printf_set_mismatch', 'printf-style format specifiers changed'),
        'renpy_tag_order_invalid': ('guard_reason_renpy_tag_order_invalid', "Ren'Py text tags were reordered or left unbalanced"),
        'replacement_char': ('guard_reason_replacement_char', 'the output contains unreadable characters (U+FFFD)'),
    }
    key, default = reason_key_map.get(reason, ('guard_reason_unknown', (reason or 'suspicious translator output').replace('_', ' ')))
    return config.get_log_text(key, default)


def sanitize_translation_for_output(
    *,
    original: str,
    translated: str,
    file_path: str,
    translation_id: str,
    diagnostic_report,
    log_emit,
    config,
    record_guard_event_fn,
    line_number: int = 0,
) -> Tuple[str, Optional[str]]:
    reason = classify_translation_corruption(original, translated)
    if reason is None:
        return translated, None

    record_guard_event_fn(
        category='blocked_as_corrupted',
        file_path=file_path,
        translation_id=translation_id,
        original_text=original,
        translated_text=translated,
        detail=reason,
        line_number=line_number,
    )
    try:
        diagnostic_report.mark_blocked(
            file_path,
            translation_id,
            'corrupt_blocked',
            original_text=original,
            translated_text=translated,
        )
    except Exception:
        pass
    return original, reason


def should_retry_unchanged_core_ui(original_text: str) -> bool:
    from .constants import CORE_UI_RETRY_STRINGS
    return (original_text or '').strip() in CORE_UI_RETRY_STRINGS


def is_sentence_shaped_natural_language(text: str) -> bool:
    """
    Deterministic check: returns True if text looks like a natural-language
    sentence (e.g. 'She strokes your cock.'), warranting exactly one translation retry.
    Strictly excludes names, interjections, identifiers, code, and isolated short UI phrases.
    """
    if not text:
        return False
    raw = (text or '').strip()
    # Strip disambiguation tags if any ({#tag})
    raw = re.sub(r'\{#[^}]*\}', '', raw).strip()
    # Strip Ren'Py display tags ({color=...}, {b}, {i}, etc.)
    clean = re.sub(r'\{/?[^}]+\}', '', raw).strip()
    # Strip Ren'Py placeholders [var]
    clean = re.sub(r'\[[^\]]+\]', '', clean).strip()
    if not clean or len(clean) < 6:
        return False

    # Must not contain underscores (identifier/code) or path separators
    if '_' in clean or '/' in clean or '\\' in clean:
        return False

    # Must not look like code, format specs, or variable assignment
    if any(sig in clean for sig in ('%s', '%d', '()', '==', '!=', '+=', '-=', '->', '$')):
        return False

    has_terminal_punct = clean.endswith(('.', '!', '?', '…', '。', '！', '？', '"', "'", '”', '’'))

    # Special handling for unsegmented CJK text (Japanese / Chinese without spaces)
    if re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]', clean):
        return len(clean) >= 4 and has_terminal_punct

    words = clean.split()
    if len(words) < 2:
        return False

    # Two-word sentences must end with terminal punctuation (. ! ? …)
    if len(words) == 2:
        if not clean.endswith(('.', '!', '?', '…')):
            return False
        if not all(any(c.isalpha() for c in w) for w in words):
            return False

    # Must have a high ratio of alphabetic words
    alpha_words = [w for w in words if any(c.isalpha() for c in w)]
    if len(alpha_words) < 2 or (len(alpha_words) / len(words)) < 0.7:
        return False

    # Reject if uppercase and short (likely UI button, menu header, or acronym)
    if clean.isupper() and len(words) <= 4:
        return False

    # Must start with a capital letter, dialogue quotes, or end with sentence punctuation
    starts_capital = clean[0].isupper() or (clean[0] in ('"', "'", '“', '‘') and len(clean) > 1 and clean[1].isupper())
    if not (starts_capital or has_terminal_punct):
        return False

    # Skip if first word is a raw Ren'Py keyword (e.g. "scene bg room", "show eileen happy")
    from .constants import RENPY_KEYWORDS_TO_SKIP
    first_token = words[0].strip('"\';:,.-!?').lower()
    if first_token in RENPY_KEYWORDS_TO_SKIP and not has_terminal_punct:
        return False

    return True


def should_retry_unchanged(original_text: str) -> Tuple[bool, str]:
    """
    Classify whether an unchanged translation output should be retried once.
    Returns (should_retry: bool, retry_kind: str).
    retry_kind is 'core_ui' or 'sentence' or empty ''.
    """
    orig = (original_text or '').strip()
    if not orig:
        return False, ''
    if should_retry_unchanged_core_ui(orig):
        return True, 'core_ui'
    if is_sentence_shaped_natural_language(orig):
        return True, 'sentence'
    return False, ''


def get_requested_translation_batch_size(engine, config) -> int:
    from src.core.translator import TranslationEngine
    if engine in (TranslationEngine.OPENAI, TranslationEngine.GEMINI):
        return getattr(config.translation_settings, 'ai_batch_size', 15)
    return getattr(config.translation_settings, 'max_batch_size', 100)


def get_effective_translation_batch_size(engine, config) -> int:
    from src.core.translator import TranslationEngine
    from src.utils.config import get_effective_batch_size as _get_eff
    requested = get_requested_translation_batch_size(engine, config)
    if engine in (TranslationEngine.OPENAI, TranslationEngine.GEMINI):
        return requested
    return _get_eff(requested, engine)


def emit_batch_size_cap_notice_if_needed(requested: int, effective: int, engine, config, log_emit) -> None:
    if effective == requested:
        return
    from src.utils.config import get_engine_batch_size_cap
    cap = get_engine_batch_size_cap(engine) or effective
    engine_name = getattr(engine, 'value', str(engine))
    log_emit("info", config.get_log_text(
        'log_batch_size_engine_cap_applied',
        'Requested batch size {requested} exceeds the effective limit for {engine}; using {effective} (cap: {cap}).',
        requested=requested, engine=engine_name, effective=effective, cap=cap,
    ))


def execute_single_request_with_retry_mode(loop, translator, request) -> Optional[Any]:
    ts = getattr(translator, '_config_manager', None)
    if ts is None:
        original_flag = getattr(translator, 'aggressive_retry', None)
        try:
            if original_flag is not None:
                translator.aggressive_retry = True
            return loop.run_until_complete(translator.translate_single(request))
        except Exception as exc:
            return None
        finally:
            if original_flag is not None:
                translator.aggressive_retry = original_flag

    ts_settings = getattr(ts, 'translation_settings', None)
    original_config_flag = getattr(ts_settings, 'aggressive_retry_translation', False) if ts_settings else False
    original_translator_flag = getattr(translator, 'aggressive_retry', None)
    try:
        if ts_settings is not None:
            ts_settings.aggressive_retry_translation = True
        if original_translator_flag is not None:
            translator.aggressive_retry = True
        return loop.run_until_complete(translator.translate_single(request))
    except Exception as exc:
        return None
    finally:
        if ts_settings is not None:
            ts_settings.aggressive_retry_translation = original_config_flag
        if original_translator_flag is not None:
            translator.aggressive_retry = original_translator_flag


def retry_unchanged_candidate(
    loop, request, entry, current_text: str, translation_manager, retry_kind: str = 'core_ui'
) -> Tuple[str, bool]:
    if request is None:
        return current_text, False

    orig = (entry.original_text or '').strip()
    if retry_kind == 'core_ui':
        if not should_retry_unchanged_core_ui(orig):
            return current_text, False
    elif retry_kind == 'sentence':
        if not is_sentence_shaped_natural_language(orig):
            return current_text, False
    else:
        should_retry, _ = should_retry_unchanged(orig)
        if not should_retry:
            return current_text, False

    translator = translation_manager.translators.get(request.engine)
    if translator is None:
        return current_text, False

    retry_result = execute_single_request_with_retry_mode(loop, translator, request)
    if retry_result and getattr(retry_result, 'success', False):
        retry_text = (getattr(retry_result, 'translated_text', '') or '').strip()
        if retry_text and retry_text != orig:
            return retry_text, True

    fallback_translator = getattr(translator, 'fallback_translator', None) or getattr(translator, '_fallback', None)
    if (
        fallback_translator is not None
        and getattr(translator, 'fallback_for_unchanged_retry', True)
        and not is_translator_cooling_down(fallback_translator)
    ):
        # AI requests carry XML-protected text; the fallback engine needs the
        # original source text so it can apply its own placeholder scheme.
        build_fb = getattr(translator, '_build_fallback_request', None)
        fallback_request = build_fb(request, fallback_translator) if callable(build_fb) else request
        fallback_result = execute_single_request_with_retry_mode(loop, fallback_translator, fallback_request)
        if fallback_result and getattr(fallback_result, 'success', False):
            fallback_text = (getattr(fallback_result, 'translated_text', '') or '').strip()
            if fallback_text and fallback_text != orig:
                return fallback_text, True

    return current_text, False


def is_translator_cooling_down(translator) -> bool:
    """
    True while a translator is inside its own rate-limit cooldown window
    (GoogleTranslator sets `_global_cooldown_until` after a 429). The unchanged
    second-opinion retry is opportunistic, so it must not stall the run by
    queueing behind a throttled fallback engine (Bing/Gemini -> Google).
    """
    until = getattr(translator, '_global_cooldown_until', 0) or 0
    try:
        return float(until) > time.time()
    except (TypeError, ValueError):
        return False


def retry_unchanged_core_ui(loop, request, entry, current_text: str, translation_manager) -> Tuple[str, bool]:
    return retry_unchanged_candidate(loop, request, entry, current_text, translation_manager, retry_kind='core_ui')


def protect_glossary_terms(text: str, config, xml_mode: bool = False) -> Tuple[str, Dict[str, str]]:
    if not config or not hasattr(config, 'glossary') or not config.glossary:
        return text, {}
    from src.core.glossary_manager import GlossaryManager
    return GlossaryManager.protect_terms(text, config.glossary, xml_mode=xml_mode)


def get_extraction_mode(config) -> str:
    ts = getattr(config, 'translation_settings', None)
    mode = str(getattr(ts, 'extraction_mode', 'balanced') or 'balanced').strip().lower()
    if mode not in ('strict', 'balanced', 'aggressive'):
        return 'balanced'
    return mode


def is_aggressive_extraction_mode(config) -> bool:
    return get_extraction_mode(config) == 'aggressive'
