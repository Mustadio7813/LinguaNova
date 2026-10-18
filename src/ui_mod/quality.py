# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# MOD
# #MOD — acceptance rules for MOD translations (one policy for every target).
"""Decide whether an engine answer is a real translation into the target language.

Root-cause note (2026-10-17): the previous MOD accepted every non-empty answer whose
placeholders matched. In the Portuguese→Polish case 865 of 3,493 stored pairs kept
most of the Portuguese words, 236 only changed capitalisation and 213 were still
Portuguese ("( ...são as duas. As DUAS. )" → "( ... São as Duas. Jako DUAS. )").
This module rejects such answers so they stay pending instead of being published
and cached.

Statuses:
  accepted   — translated into the target language, structure preserved
  invariant  — identical/case-only answer; nothing to replace (not a translation)
  rejected   — reason in ``QualityVerdict.reason``
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import logging
import re
import threading
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .languages import ModLanguage, char_script, resolve_language, script_matches
from .protect import extract_tokens, is_junk, structure_problem

logger = logging.getLogger("LinguaNova")

VALIDATION_VERSION = 2

_MARKUP_RE = re.compile(
    r"\{[^{}]*\}|\[[^\[\]]*\]|%\([A-Za-z_]\w*\)[#0\- +]?\d*(?:\.\d+)?[a-zA-Z%]|%[#0\- +]?\d*(?:\.\d+)?[a-zA-Z%]"
)
_WS_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*")
_SEGMENT_SPLIT_RE = re.compile(r"(?<=[.!?…;:])\s+|\.{3,}|\n+")

# Minimum normalised probability for a language-identification verdict.
LID_REJECT_PROB = 0.80
LID_SEGMENT_PROB = 0.90
LID_CONFIRM_PROB = 0.70
# Copied fragments: calibrated on pt→es ("para editar" pt=0.85, a legitimate
# shared phrase) vs pt→pl ("Valeu mesmo" pt=1.00, an untranslated fragment).
LID_RUN_PROB = 0.97
RETENTION_REJECT_RATIO = 0.60

# py3langid labels that differ from LinguaNova catalogue codes.
_LID_ALIASES = {"zh-cn": "zh", "zh-tw": "zh", "no": "nb", "tl": "tl", "he": "he", "jv": "jv"}


@dataclass(frozen=True)
class QualityVerdict:
    status: str                  # accepted | invariant | rejected
    reason: str = ""
    detected: str = ""           # language the check attributed to the answer, if any
    level: str = "full"          # full (with language identification) | basic

    @property
    def accepted(self) -> bool:
        return self.status == "accepted"


class _LangId:
    """Private py3langid instance (never mutates the shared detector's language set)."""

    def __init__(self) -> None:
        self._identifier = None
        self._labels: frozenset = frozenset()
        self._failed = False
        self._lock = threading.Lock()

    def _get(self):
        if self._identifier is not None or self._failed:
            return self._identifier
        with self._lock:
            if self._identifier is None and not self._failed:
                try:
                    from py3langid.langid import LanguageIdentifier, MODEL_FILE
                    ident = LanguageIdentifier.from_model_file(MODEL_FILE, norm_probs=True)
                    labels = frozenset(lang for lang, _ in ident.rank("text"))
                    self._identifier, self._labels = ident, labels
                except Exception as exc:  # missing package or model data in a frozen build
                    self._failed = True
                    logger.warning("[#MOD] py3langid unavailable; MOD validation runs in basic mode: %s", exc)
        return self._identifier

    @property
    def available(self) -> bool:
        return self._get() is not None

    def label(self, lang: Optional[ModLanguage]) -> Optional[str]:
        if lang is None or self._get() is None:
            return None
        code = lang.api.lower()
        for candidate in (_LID_ALIASES.get(code), code, code.split("-", 1)[0]):
            if candidate and candidate in self._labels:
                return candidate
        return None

    def rank_among(self, text: str, labels: Iterable[str]) -> List[Tuple[str, float]]:
        ident = self._get()
        wanted = {label for label in labels if label}
        if ident is None or not wanted:
            return []
        try:
            scores = [(lang, float(p)) for lang, p in ident.rank(text) if lang in wanted]
        except Exception as exc:
            logger.debug("[#MOD] py3langid rank failed: %s", exc)
            return []
        total = sum(p for _, p in scores)
        if total <= 0:
            return []
        return sorted(((lang, p / total) for lang, p in scores), key=lambda item: -item[1])

    def classify(self, text: str) -> Optional[Tuple[str, float]]:
        ident = self._get()
        if ident is None:
            return None
        try:
            lang, prob = ident.classify(text)
            return str(lang), float(prob)
        except Exception:
            return None


_LID = _LangId()


def language_identification_available() -> bool:
    return _LID.available


def clean_for_language(text: str) -> str:
    return _WS_RE.sub(" ", _MARKUP_RE.sub(" ", text or "")).strip()


def _normalise(text: str) -> str:
    return _WS_RE.sub(" ", (text or "").strip()).casefold()


def _letters_by_script(text: str) -> Counter:
    counts: Counter = Counter()
    for char in text:
        script = char_script(char)
        if script:
            counts[script] += 1
    return counts


def _content_words(text: str, unspaced: bool) -> List[str]:
    if unspaced:
        return []
    out = []
    for index, word in enumerate(_WORD_RE.findall(text)):
        # Capitalised words after the first are likely names that legitimately stay.
        if len(word) < 4 or (index > 0 and word[:1].isupper()):
            continue
        out.append(word.casefold())
    return out


def _copied_runs(clean_src: str, clean_out: str) -> List[List[str]]:
    """Maximal runs of consecutive output words that also occur consecutively in the source.

    Kept: runs of >= 3 words, or 2 words of >= 4 letters. Runs made only of
    capitalised words (names, titles) are ignored.
    """
    src = [w.casefold() for w in _WORD_RE.findall(clean_src)]
    out_raw = _WORD_RE.findall(clean_out)
    out = [w.casefold() for w in out_raw]
    if len(src) < 2 or len(out) < 2:
        return []
    src_bigrams = {(src[i], src[i + 1]) for i in range(len(src) - 1)}
    runs: List[List[str]] = []
    i = 0
    while i < len(out) - 1:
        if (out[i], out[i + 1]) not in src_bigrams:
            i += 1
            continue
        j = i + 1
        while j < len(out) - 1 and (out[j], out[j + 1]) in src_bigrams:
            j += 1
        run_raw = out_raw[i:j + 1]
        long_words = [w for w in run_raw if len(w) >= 4]
        all_capitalised = all(w[:1].isupper() for w in run_raw)
        if not all_capitalised and (len(run_raw) >= 3 or len(long_words) >= 2):
            runs.append(run_raw)
        i = j + 1
    return runs


def _enough_text(clean: str, lang: Optional[ModLanguage]) -> bool:
    if lang is not None and lang.unspaced:
        return sum(1 for ch in clean if ch.isalpha()) >= 6
    return len(_WORD_RE.findall(clean)) >= 3 and len(clean) >= 12


def _lid_candidates(source: Optional[ModLanguage], target: ModLanguage) -> List[str]:
    labels = [_LID.label(target), _LID.label(source)]
    english = resolve_language("en")
    labels.append(_LID.label(english))
    return [label for label in dict.fromkeys(labels) if label]


def validate_translation(
    source_text: str,
    translated: str,
    target: ModLanguage,
    source: Optional[ModLanguage] = None,
) -> QualityVerdict:
    """Apply the MOD acceptance policy; never raises for odd input."""
    level = "full" if (_LID.available and _LID.label(target)) else "basic"
    if not isinstance(translated, str) or not translated.strip():
        return QualityVerdict("rejected", "empty", level=level)
    if is_junk(source_text) or is_junk(translated):
        return QualityVerdict("rejected", "junk", level=level)
    problem = structure_problem(source_text, translated)
    if problem:
        return QualityVerdict("rejected", problem, level=level)
    if "__LNMOD_TOKEN_" in translated or "⟦" in translated:
        return QualityVerdict("rejected", "placeholder_leak", level=level)
    if _normalise(source_text) == _normalise(translated):
        return QualityVerdict("invariant", "unchanged", level=level)

    clean_src = clean_for_language(source_text)
    clean_out = clean_for_language(translated)
    out_scripts = _letters_by_script(clean_out)
    letters = sum(out_scripts.values())
    if letters == 0:
        return QualityVerdict("accepted", "no_letters", level=level)

    # 1) Writing system of the target language.
    expected = target.script
    in_script = sum(n for s, n in out_scripts.items() if script_matches(expected, s))
    source_words = {w.casefold() for w in _WORD_RE.findall(clean_src)}
    foreign_words = [w for w in _WORD_RE.findall(clean_out)
                     if not any(script_matches(expected, char_script(c)) for c in w if c.isalpha())]
    copied_foreign = [w for w in foreign_words if w.casefold() in source_words]
    if expected != "LATIN":
        if in_script == 0:
            if foreign_words and len(copied_foreign) == len(foreign_words):
                # Only names/brands copied from the source: nothing was translated.
                return QualityVerdict("invariant", "names_only", level=level)
            return QualityVerdict("rejected", "wrong_script", detected=out_scripts.most_common(1)[0][0], level=level)
        foreign_letters = sum(len(w) for w in foreign_words if w.casefold() not in source_words)
        if foreign_letters > in_script:
            return QualityVerdict("rejected", "wrong_script", detected=out_scripts.most_common(1)[0][0], level=level)
        if len(copied_foreign) >= 3 and sum(len(w) for w in copied_foreign) > in_script:
            return QualityVerdict("rejected", "untranslated_residue", level=level)
    elif in_script * 2 < letters:
        return QualityVerdict("rejected", "wrong_script", detected=out_scripts.most_common(1)[0][0], level=level)

    # 2) Language identification (whole answer, then each sentence).
    confirmed = False
    target_label = _LID.label(target)
    if target_label and _enough_text(clean_out, target):
        candidates = _lid_candidates(source, target)
        ranking = _LID.rank_among(clean_out, candidates)
        if ranking:
            top, prob = ranking[0]
            if top != target_label and prob >= LID_REJECT_PROB:
                return QualityVerdict("rejected", "wrong_language", detected=top, level=level)
            confirmed = top == target_label and prob >= LID_CONFIRM_PROB
        source_label = _LID.label(source)
        for segment in _SEGMENT_SPLIT_RE.split(clean_out):
            segment = (segment or "").strip()
            if not segment or not _enough_text(segment, target) or len(_WORD_RE.findall(segment)) < 4:
                continue
            seg_rank = _LID.rank_among(segment, candidates)
            if seg_rank and seg_rank[0][0] != target_label and seg_rank[0][1] >= LID_SEGMENT_PROB \
                    and (seg_rank[0][0] == source_label or source_label is None):
                return QualityVerdict("rejected", "mixed_language", detected=seg_rank[0][0], level=level)

    # 2b) Fragments copied verbatim from the source ("... quando tá brava.",
    #      "Valeu mesmo! Do tego ...") inside an otherwise translated answer.
    if not target.unspaced and (source is None or source.api != target.api):
        for run in _copied_runs(clean_src, clean_out):
            if _LID.label(source) and _LID.label(target):
                ranking = _LID.rank_among(" ".join(run), [_LID.label(target), _LID.label(source)])
                if ranking and ranking[0][0] == _LID.label(source) and ranking[0][1] >= LID_RUN_PROB:
                    return QualityVerdict("rejected", "mixed_language", detected=ranking[0][0], level=level)
            elif len(run) >= 3 and level == "basic":
                return QualityVerdict("rejected", "untranslated_residue", level=level)

    # 3) Source words left in place (language independent; decisive when the
    #    identifier could not confirm the target, e.g. short or unsupported text).
    if not confirmed and not target.unspaced:
        src_words = _content_words(clean_src, unspaced=False)
        if len(src_words) >= 3:
            out_words = {w.casefold() for w in _WORD_RE.findall(clean_out)}
            kept = sum(1 for w in src_words if w in out_words)
            if kept / len(src_words) >= RETENTION_REJECT_RATIO:
                return QualityVerdict("rejected", "untranslated_residue", level=level)
    return QualityVerdict("accepted", "", level=level)


def detect_text_language(texts: Sequence[str]) -> Optional[Tuple[str, float]]:
    """Joined-sample classification used for reports (not for acceptance)."""
    sample = " ".join(clean_for_language(t) for t in texts if t)[:4000]
    if not sample:
        return None
    return _LID.classify(sample)


def summarise(verdicts: Iterable[QualityVerdict]) -> Dict[str, int]:
    counts: Counter = Counter()
    for verdict in verdicts:
        counts[verdict.status if verdict.status != "rejected" else f"rejected:{verdict.reason}"] += 1
    return dict(sorted(counts.items()))
