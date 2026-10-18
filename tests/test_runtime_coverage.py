# -*- coding: utf-8 -*-

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from src.core.runtime_coverage import (
    load_runtime_miss_log,
    score_runtime_miss_entries,
    score_runtime_miss_entry,
    summarize_runtime_miss_scores,
)
from src.core.translation_pipeline import TranslationPipeline


def test_score_runtime_miss_entry_prefers_long_dialogue_fragment() -> None:
    entry = {
        "reason": "screen_bypass_miss",
        "source_kind": "dialogue",
        "text": "And the continuation of this story is being created right now. So I won't say goodbye.",
        "stripped": "And the continuation of this story is being created right now. So I won't say goodbye.",
        "length": 85,
        "word_count": 14,
        "sentence_count": 2,
        "alnum_count": 67,
        "has_digits": False,
        "has_pipe": False,
        "has_square_brackets": False,
        "has_text_tags": False,
        "quoted": False,
        "has_ellipsis": False,
        "has_curly_quotes": False,
        "looks_like_hotkey_visible_form": False,
        "looks_like_placeholder_remnant": False,
    }

    scored = score_runtime_miss_entry(entry)
    assert scored.score >= 70
    assert scored.confidence == "high"
    assert scored.suggested_action == "promote_alias"
    assert scored.risk == "low"


def test_score_runtime_miss_entry_rejects_noisy_stat_fragment() -> None:
    entry = {
        "reason": "screen_bypass_miss",
        "source_kind": "pipe_or_composite",
        "text": "Swarm Construct | Level: 20 | FP: 0 | Relaxing",
        "stripped": "Swarm Construct | Level: 20 | FP: 0 | Relaxing",
        "length": 47,
        "word_count": 9,
        "sentence_count": 1,
        "alnum_count": 32,
        "has_digits": True,
        "has_pipe": True,
        "has_square_brackets": False,
        "has_text_tags": False,
        "quoted": False,
        "has_ellipsis": False,
        "has_curly_quotes": False,
        "looks_like_hotkey_visible_form": False,
        "looks_like_placeholder_remnant": False,
    }

    scored = score_runtime_miss_entry(entry)
    assert scored.score < 40
    assert scored.suggested_action == "ignore"
    assert scored.risk == "high"


def test_score_runtime_miss_entry_rejects_placeholder_risk() -> None:
    entry = {
        "reason": "template_candidate_miss",
        "source_kind": "template_text",
        "text": "Score: [score]",
        "stripped": "Score: [score]",
        "length": 14,
        "word_count": 2,
        "sentence_count": 1,
        "alnum_count": 10,
        "has_digits": False,
        "has_pipe": False,
        "has_square_brackets": True,
        "has_text_tags": False,
        "quoted": False,
        "has_ellipsis": False,
        "has_curly_quotes": False,
        "looks_like_hotkey_visible_form": False,
        "looks_like_placeholder_remnant": False,
    }

    scored = score_runtime_miss_entry(entry)
    assert scored.suggested_action == "ignore"
    assert "placeholder_or_tag_risk" in scored.reasons


def test_score_runtime_miss_entries_sorts_best_first() -> None:
    scored = score_runtime_miss_entries(
        [
            {
                "reason": "screen_bypass_miss",
                "source_kind": "pipe_or_composite",
                "text": "|  Jumpgate",
                "stripped": "|  Jumpgate",
                "length": 11,
                "word_count": 1,
                "sentence_count": 1,
                "alnum_count": 8,
                "has_digits": False,
                "has_pipe": True,
                "has_square_brackets": False,
                "has_text_tags": False,
                "quoted": False,
                "has_ellipsis": False,
                "has_curly_quotes": False,
                "looks_like_hotkey_visible_form": False,
                "looks_like_placeholder_remnant": False,
            },
            {
                "reason": "screen_bypass_miss",
                "source_kind": "screen_text",
                "text": "And the continuation of this story is being created right now. So I won't say goodbye.",
                "stripped": "And the continuation of this story is being created right now. So I won't say goodbye.",
                "length": 85,
                "word_count": 14,
                "sentence_count": 2,
                "alnum_count": 67,
                "has_digits": False,
                "has_pipe": False,
                "has_square_brackets": False,
                "has_text_tags": False,
                "quoted": False,
                "has_ellipsis": False,
                "has_curly_quotes": False,
                "looks_like_hotkey_visible_form": False,
                "looks_like_placeholder_remnant": False,
            },
        ]
    )

    assert scored[0].text.startswith("And the continuation")
    assert scored[0].score > scored[1].score


def test_load_runtime_miss_log_ignores_invalid_lines(tmp_path: Path) -> None:
    log_path = tmp_path / "runtime_missed_strings.jsonl"
    log_path.write_text(
        "\n".join(
            [
                "not json",
                json.dumps({"text": "Hello", "reason": "screen_bypass_miss"}),
                "",
            ]
        ),
        encoding="utf-8",
    )

    loaded = load_runtime_miss_log(log_path)
    assert loaded == [{"text": "Hello", "reason": "screen_bypass_miss"}]


def test_summarize_runtime_miss_scores_counts_actions() -> None:
    summary = summarize_runtime_miss_scores(
        [
            {
                "reason": "screen_bypass_miss",
                "source_kind": "dialogue",
                "text": "And the continuation of this story is being created right now. So I won't say goodbye.",
                "stripped": "And the continuation of this story is being created right now. So I won't say goodbye.",
                "length": 85,
                "word_count": 14,
                "sentence_count": 2,
                "alnum_count": 67,
                "has_digits": False,
                "has_pipe": False,
                "has_square_brackets": False,
                "has_text_tags": False,
                "quoted": False,
                "has_ellipsis": False,
                "has_curly_quotes": False,
                "looks_like_hotkey_visible_form": False,
                "looks_like_placeholder_remnant": False,
            },
            {
                "reason": "screen_bypass_miss",
                "source_kind": "pipe_or_composite",
                "text": "|  Jumpgate",
                "stripped": "|  Jumpgate",
                "length": 11,
                "word_count": 1,
                "sentence_count": 1,
                "alnum_count": 8,
                "has_digits": False,
                "has_pipe": True,
                "has_square_brackets": False,
                "has_text_tags": False,
                "quoted": False,
                "has_ellipsis": False,
                "has_curly_quotes": False,
                "looks_like_hotkey_visible_form": False,
                "looks_like_placeholder_remnant": False,
            },
        ]
    )

    assert summary["total"] == 2
    assert summary["promote_alias"] == 1
    assert summary["ignore"] == 1
    assert summary["high_confidence"] == 1


def test_pipeline_analyze_runtime_miss_log_returns_ranked_candidates(tmp_path: Path) -> None:
    log_path = tmp_path / "runtime_missed_strings.jsonl"
    log_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "reason": "screen_bypass_miss",
                        "source_kind": "dialogue",
                        "text": "And the continuation of this story is being created right now. So I won't say goodbye.",
                        "stripped": "And the continuation of this story is being created right now. So I won't say goodbye.",
                        "length": 85,
                        "word_count": 14,
                        "sentence_count": 2,
                        "alnum_count": 67,
                    }
                ),
                json.dumps(
                    {
                        "reason": "screen_bypass_miss",
                        "source_kind": "pipe_or_composite",
                        "text": "|  Jumpgate",
                        "stripped": "|  Jumpgate",
                        "length": 11,
                        "word_count": 1,
                        "sentence_count": 1,
                        "alnum_count": 8,
                        "has_pipe": True,
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    config = SimpleNamespace(translation_settings=SimpleNamespace(), get_ui_text=lambda key, default=None, **kwargs: default or key)
    pipeline = TranslationPipeline(cast(Any, config), cast(Any, object()))
    result = pipeline.analyze_runtime_miss_log(str(log_path))

    assert result["summary"]["total"] == 2
    assert result["top_candidates"][0]["text"].startswith("And the continuation")
    assert result["top_candidates"][0]["suggested_action"] == "promote_alias"
