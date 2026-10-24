"""Conservative contextual checks; accepted is not a dialect certification."""
import re
from collections import Counter
from ..contracts.result import ValidationResult

TOKEN = re.compile(r'(?<!\[)\[(?!\[)[^\]\n]+\]|(?<!\{)\{(?!\{)[^}\n]+\}|%(?:\([^)]+\))?[#0+\- ]*\d*(?:\.\d+)?[sdifgeouxXcr%]')


def visible_text(text):
    return TOKEN.sub('', text).strip()


def validate(job, original, candidate, context='', allow_preserve=False,proper_name=False):
    reasons, warnings = [], []
    if not candidate or not candidate.strip():
        reasons.append('empty_or_missing')
    if Counter(TOKEN.findall(original)) != Counter(TOKEN.findall(candidate)):
        reasons.append('renpy_syntax_mismatch')
    from src.core.tag_structure import tag_structure_regression, introduces_replacement_char
    if tag_structure_regression(original,candidate):
        reasons.append('renpy_tag_structure_regression')
    if introduces_replacement_char(original,candidate):
        reasons.append('replacement_character_introduced')
    if re.search(r'__PH_\d+__|⟦[^⟧]+⟧|</?(?:item|translations)>|```', candidate):
        reasons.append('provider_protocol_leak')
    if candidate.strip() == original.strip() and not allow_preserve:
        reasons.append('source_copy_unresolved')
    text = visible_text(candidate)
    from ..dictionary.term_protection import contains_term
    for source, required in __import__('json').loads(job.glossary_json).items():
        if contains_term(original,source) and required not in candidate:
            reasons.append('glossary_term_missing:'+source)
    if proper_name and allow_preserve and candidate==original:
        return ValidationResult(not reasons,tuple(reasons),('declared_name_preserved_separately',))
    # Quotations and proper names are not rewritten. Signals are contextual,
    # restricted to grammatical constructions rather than shared word lists.
    if job.target_locale == 'es-419':
        if re.search(r'\bvosotr[oa]s\s+(?:sois|estáis|tenéis|podéis|queréis|vais|debéis)\b', text, re.I):
            reasons.append('spain_construction_in_latam')
        elif re.search(r'\b(?:vosotr[oa]s|habéis|tenéis|podéis)\b', text, re.I):
            warnings.append('regional_signal_needs_context')
    elif job.target_locale == 'es-ES':
        if re.search(r'\bvos\s+(?:sos|tenés|podés|querés|sabés)\b', text, re.I):
            reasons.append('voseo_in_spain')
    letters = ''.join(c for c in text if c.isalpha())
    if job.target_language_id == 'ru' and len(letters) >= 12 and not any('\u0400' <= c <= '\u052f' for c in letters):
        reasons.append('target_script_mismatch')
    if len(letters) >= 30:
        try:
            import py3langid
            lang, score = py3langid.classify(text)
            # classify's raw score is not a probability. Require a second,
            # normalized prediction before rejecting a foreign language.
            from py3langid.langid import LanguageIdentifier, MODEL_FILE
            global _identifier
            if '_identifier' not in globals():
                _identifier = LanguageIdentifier.from_model_file(MODEL_FILE, norm_probs=True)
            lang, confidence = _identifier.classify(text)
            if confidence >= .96 and lang != job.target_language_id:
                reasons.append('detected_language_mismatch:'+lang)
            elif confidence < .96:
                warnings.append('language_uncertain')
        except (ImportError, AttributeError):
            warnings.append('language_detector_unavailable')
    else:
        warnings.append('short_text_requires_context')
    if job.target_language_id == 'es':
        warnings.append('dialect_requires_editorial_review')
    return ValidationResult(not reasons, tuple(reasons), tuple(warnings))
