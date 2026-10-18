"""Runtime coverage learning helpers.

Analyzes runtime missed-string diagnostics and scores which entries are
worth promoting into future exact-match aliases.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List


SHORT_NOISE_REASONS = {
    "duplicate_source_conflict",
    "image_only_ui",
    "corruption_driven_miss",
}

PROMOTABLE_REASONS = {
    "screen_bypass_miss",
    "visible_fragment_miss",
    "long_phrase_candidate_miss",
    "exact_lookup_miss",
    "quote_lookup_miss",
    "screen_scope_observed",
}

PROMOTABLE_SOURCE_KINDS = {
    "dialogue",
    "say_or_menu",
    "screen_text",
    "screen_scope",
    "template_text",
}

NOISY_SOURCE_KINDS = {
    "dynamic_ui",
    "pipe_or_composite",
    "unknown",
}

TECHNICAL_FRAGMENT_RE = re.compile(
    r"(?i)(?:^v?\d+(?:\.\d+)+$|^[A-Z0-9_./:-]{1,24}$|^\d+[/%:-]\d+|^(?:fps|hp|mp|xp|ui|bgm|sfx)$)"
)


@dataclass(frozen=True)
class RuntimeMissScore:
    text: str
    score: int
    confidence: str
    suggested_action: str
    risk: str
    reasons: List[str]
    entry: Dict[str, Any]


def _confidence_from_score(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _action_from_score(score: int, promotable_shape: bool) -> str:
    if not promotable_shape:
        return "ignore"
    if score >= 70:
        return "promote_alias"
    if score >= 40:
        return "review_candidate"
    return "ignore"


def _risk_from_score(score: int, promotable_shape: bool) -> str:
    if not promotable_shape:
        return "high"
    if score >= 70:
        return "low"
    if score >= 40:
        return "medium"
    return "high"


def score_runtime_miss_entry(entry: Dict[str, Any]) -> RuntimeMissScore:
    text = str(entry.get("stripped") or entry.get("text") or "").strip()
    reason = str(entry.get("reason") or "")
    source_kind = str(entry.get("source_kind") or "unknown")
    length = int(entry.get("length") or len(text))
    word_count = int(entry.get("word_count") or len([p for p in text.split() if p]))
    sentence_count = int(entry.get("sentence_count") or 0)
    alnum_count = int(entry.get("alnum_count") or sum(1 for ch in text if ch.isalnum()))
    has_digits = bool(entry.get("has_digits"))
    has_pipe = bool(entry.get("has_pipe"))
    has_square_brackets = bool(entry.get("has_square_brackets"))
    has_text_tags = bool(entry.get("has_text_tags"))
    quoted = bool(entry.get("quoted"))
    has_ellipsis = bool(entry.get("has_ellipsis"))
    has_curly_quotes = bool(entry.get("has_curly_quotes"))
    looks_like_hotkey = bool(entry.get("looks_like_hotkey_visible_form"))
    looks_like_placeholder = bool(entry.get("looks_like_placeholder_remnant"))

    score = 0
    notes: List[str] = []
    promotable_shape = True

    if not text:
        promotable_shape = False
        notes.append("empty_text")

    if reason in SHORT_NOISE_REASONS:
        score -= 60
        promotable_shape = False
        notes.append(f"blocked_reason:{reason}")
    elif reason in PROMOTABLE_REASONS:
        score += 18
        notes.append(f"promotable_reason:{reason}")

    if source_kind in PROMOTABLE_SOURCE_KINDS:
        score += 18
        notes.append(f"promotable_source_kind:{source_kind}")
    elif source_kind in NOISY_SOURCE_KINDS:
        score -= 12
        notes.append(f"noisy_source_kind:{source_kind}")

    if length >= 96:
        score += 18
        notes.append("long_text")
    elif length >= 48:
        score += 12
        notes.append("medium_text")
    elif length < 16:
        score -= 28
        promotable_shape = False
        notes.append("too_short")

    if word_count >= 10:
        score += 14
        notes.append("many_words")
    elif word_count >= 5:
        score += 8
        notes.append("enough_words")
    elif word_count <= 2:
        score -= 22
        promotable_shape = False
        notes.append("too_few_words")

    if sentence_count >= 2:
        score += 10
        notes.append("multi_sentence")
    elif sentence_count == 1:
        score += 4
        notes.append("single_sentence")

    if alnum_count >= 24:
        score += 8
        notes.append("high_signal_text")
    elif alnum_count < 8:
        score -= 15
        promotable_shape = False
        notes.append("low_signal_text")

    if quoted:
        score += 3
        notes.append("quoted_visible_form")
    if has_ellipsis or has_curly_quotes:
        score += 4
        notes.append("visible_form_variant")

    if has_square_brackets or has_text_tags or looks_like_placeholder:
        score -= 35
        promotable_shape = False
        notes.append("placeholder_or_tag_risk")

    if looks_like_hotkey:
        score -= 20
        notes.append("hotkey_like_fragment")

    if has_pipe:
        score -= 18
        notes.append("pipe_composite")

    if has_digits and word_count < 5:
        score -= 18
        notes.append("numeric_fragment")

    if text.isupper() and length <= 24:
        score -= 22
        promotable_shape = False
        notes.append("short_all_caps")

    if TECHNICAL_FRAGMENT_RE.match(text):
        score -= 28
        promotable_shape = False
        notes.append("technical_fragment")

    score = max(0, min(100, score))
    confidence = _confidence_from_score(score)
    action = _action_from_score(score, promotable_shape)
    risk = _risk_from_score(score, promotable_shape)

    return RuntimeMissScore(
        text=text,
        score=score,
        confidence=confidence,
        suggested_action=action,
        risk=risk,
        reasons=notes,
        entry=dict(entry),
    )


def score_runtime_miss_entries(entries: Iterable[Dict[str, Any]]) -> List[RuntimeMissScore]:
    scored = [score_runtime_miss_entry(entry) for entry in entries]
    return sorted(scored, key=lambda item: (-item.score, item.text.casefold()))


def load_runtime_miss_log(path: str | Path) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    p = Path(path)
    if not p.is_file():
        return entries
    for line in p.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            entries.append(payload)
    return entries


def summarize_runtime_miss_scores(entries: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    scored = score_runtime_miss_entries(entries)
    summary = {
        "total": len(scored),
        "promote_alias": 0,
        "review_candidate": 0,
        "ignore": 0,
        "high_confidence": 0,
        "medium_confidence": 0,
        "low_confidence": 0,
    }
    for item in scored:
        summary[item.suggested_action] += 1
        summary[f"{item.confidence}_confidence"] += 1
    return summary
