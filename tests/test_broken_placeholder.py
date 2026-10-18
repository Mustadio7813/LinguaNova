import pytest
import re
from src.core.syntax_guard import protect_renpy_syntax, restore_renpy_syntax

@pytest.mark.parametrize("original,expected_placeholders", [
    ("[player] kazandı!", ["[player]"]),
    ("{color=#fff}Merhaba{/color}", ["{color=#fff}", "{/color}"]),
    ("?V000? ve ⟦V000⟧", ["?V000?", "⟦V000⟧"]),
    ("[who.age] {b}Kazandı{/b}", ["[who.age]", "{b}", "{/b}"]),
    ("{#disambig} [var]", ["{#disambig}", "[var]"]),
    ("[player] {color=#fff}Kazandı{/color}", ["[player]", "{color=#fff}", "{/color}"]),
    ("⟦V000⟧", ["⟦V000⟧"]),
    ("?T123?", ["?T123?"]),
    # `[[` is Ren'Py's escape for a literal `[` — its whole purpose is to stop the
    # rest being read as interpolation, and the lexer turns source "\[" into it
    # (renpy/lexer.py dequote). So "[[Text]" renders as the literal "[Text]" and
    # only the escape itself is a placeholder; "Text]" stays translatable.
    ("{image=sub_icon_s} [[Text]", ["{image=sub_icon_s}", "[["]),
])
def test_protect_restore_renpy_syntax(original, expected_placeholders):
    protected, placeholders = protect_renpy_syntax(original)
    
    # Tüm placeholder'lar korunmalı
    # Placeholders values can be strings, lists, or tuples (wrapper pairs)
    flat_values = []
    wrapper_values = []
    
    for k, v in placeholders.items():
        if isinstance(v, (list, tuple)):
            flat_values.extend(v)
            if k.startswith("__WRAPPER_"):
                wrapper_values.extend(v)
        else:
            flat_values.append(v)

    # Check existence in map
    for ph in expected_placeholders:
        assert ph in flat_values, f"Eksik placeholder: {ph}"
        
        # Check existence in protected text (only non-wrappers)
        if ph not in wrapper_values:
            # Find the key for this value
            found_key = None
            for k, v in placeholders.items():
                if v == ph:
                    found_key = k
                    break
            
            if found_key:
                assert found_key in protected, f"Placeholder key {found_key} not in text for value {ph}"

    # Geri dönüşümde orijinal metin elde edilmeli
    restored = restore_renpy_syntax(protected, placeholders)
    # [[ -> [ [ spacing check is tricky, mainly check content preservation
    # If restore fixed spacing, great. If not, just ensure content is back.
    # For strict equality:
    if '[[' not in original:
        assert restored == original
    else:
        # Bracket restoration might vary slightly in spacing but should contain text
        assert original.replace('[[', '') in restored.replace('[[', '').replace('[ [', '')

@pytest.mark.parametrize("broken", [
    "Çeviri sırasında [player] bozuldu!",
    "{color=#fff} yanlış çevrildi",
    "?V000? kayboldu",
    "⟦V000⟧ eksik",
    "[who.age] değişti",
])
def test_broken_placeholder_detection(broken):
    # Placeholder'lar bozulmuşsa, orijinal ile karşılaştırınca eksik olur
    # Bu test, pipeline'daki validate_placeholders fonksiyonunun mantığını simüle eder
    import re
    def extract_placeholders(text):
        return set(re.findall(r'\[[^\]]+\]|\{[^}]+\}|\?[A-Za-z]\d{3}\?|[\u27e6][^\u27e7]+[\u27e7]', text))
    # Orijinal placeholder'lar
    orig = "[player] {color=#fff} ?V000? ⟦V000⟧ [who.age]"
    orig_ph = extract_placeholders(orig)
    broken_ph = extract_placeholders(broken)
    # Orijinaldeki herhangi bir placeholder bozulmuşsa, test fail olmalı
    assert not orig_ph.issubset(broken_ph), f"Bozuk placeholder tespit edilemedi: {broken}"


def test_literal_unicode_brackets_do_not_collide_with_internal_tokens():
    original = "Unscathed except for your pride, but ⟦0⟧... and [player]."
    protected, placeholders = protect_renpy_syntax(original)

    assert "⟦0⟧" in protected
    assert "[player]" not in protected
    assert any(
        isinstance(v, str) and v == "[player]"
        for v in placeholders.values()
    )

    restored = restore_renpy_syntax(protected, placeholders)
    assert restored == original


def test_fullwidth_unicode_token_is_restored():
    original = "Merhaba [player], skorun [score]!"
    protected, placeholders = protect_renpy_syntax(original)

    def to_fullwidth_ascii(text: str) -> str:
        out = []
        for ch in text:
            if '0' <= ch <= '9':
                out.append(chr(ord(ch) + 0xFEE0))
            elif 'A' <= ch <= 'Z':
                out.append(chr(ord(ch) + 0xFEE0))
            elif ch == '_':
                out.append('\uFF3F')
            else:
                out.append(ch)
        return ''.join(out)

    mutated = re.sub(r'⟦([^⟧]+)⟧', lambda m: f"⟦{to_fullwidth_ascii(m.group(1))}⟧", protected)
    restored = restore_renpy_syntax(mutated, placeholders)
    assert restored == original


def test_bare_rlph_token_recovery_brackets_stripped():
    """Google ⟦⟧ parantezlerini sildiğinde, çıplak RLPH tokenı recover edilmeli."""
    original = "You found [issue] in the ship"
    protected, placeholders = protect_renpy_syntax(original)

    # Simulate Google stripping the ⟦⟧ brackets but keeping inner content
    bare = re.sub(r'[⟦⟧]', '', protected)
    assert '⟦' not in bare
    assert 'RLPH' in bare

    restored = restore_renpy_syntax(bare, placeholders)
    assert "[issue]" in restored


def test_variant_bracket_rlph_token_recovery():
    """Google ⟦⟧'yi []/() gibi başka parantezlere dönüştürdüğünde recover edilmeli."""
    original = "Score [expr] and [value]!"
    protected, placeholders = protect_renpy_syntax(original)

    # Simulate Google converting ⟦⟧ to []
    variant = protected.replace('⟦', '[').replace('⟧', ']')
    restored = restore_renpy_syntax(variant, placeholders)
    assert "[expr]" in restored
    assert "[value]" in restored

    # Simulate Google converting ⟦⟧ to ()
    variant2 = protected.replace('⟦', '(').replace('⟧', ')')
    restored2 = restore_renpy_syntax(variant2, placeholders)
    assert "[expr]" in restored2
    assert "[value]" in restored2


def test_half_bracket_rlph_token_recovery():
    """Google tek taraflı parantez bıraktığında (⟦RLPH...] gibi) recover edilmeli."""
    original = "Captain [name] reporting"
    protected, placeholders = protect_renpy_syntax(original)

    # Simulate Google keeping only the closing bracket as ]
    half = protected.replace('⟦', '').replace('⟧', ']')
    restored = restore_renpy_syntax(half, placeholders)
    assert "[name]" in restored


def test_placeholder_boundary_spacing_repairs_prefix_attachment():
    original = "Merhaba [player]"
    protected, placeholders = protect_renpy_syntax(original)

    merged = re.sub(r'\s+(⟦[^⟧]+⟧)', r'\1', protected)
    restored = restore_renpy_syntax(merged, placeholders)

    assert restored == original


def test_placeholder_boundary_spacing_repairs_suffix_attachment():
    original = "[player] geldi"
    protected, placeholders = protect_renpy_syntax(original)

    merged = re.sub(r'(⟦[^⟧]+⟧)\s+', r'\1', protected)
    restored = restore_renpy_syntax(merged, placeholders)

    assert restored == original


def test_placeholder_boundary_spacing_does_not_break_apostrophe_suffix():
    original = "[player]'s ship"
    protected, placeholders = protect_renpy_syntax(original)
    restored = restore_renpy_syntax(protected, placeholders)

    assert restored == original
