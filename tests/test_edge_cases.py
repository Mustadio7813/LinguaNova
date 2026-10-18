# -*- coding: utf-8 -*-
import pytest
from src.core.syntax_guard import protect_renpy_syntax, restore_renpy_syntax, validate_translation_integrity

class TestSyntaxGuardEdgeCases:

    def test_recursive_nested_brackets(self):
        """Senaryo 1: İç içe geçmiş parantezler (Ren'Py desteklemese bile kod patlamamalı)"""
        text = "Hello [[v1]] world [v2 [v3]] end"
        # Beklenen: [[v1]] escape kabul edilir, [v2 [v3]] bir bütün olarak veya parça parça işlenir ama CRASH etmez.
        protected, placeholders = protect_renpy_syntax(text)
        print(f"DEBUG: Protected='{protected}', Placeholders={placeholders}")
        assert isinstance(protected, str)
        assert len(placeholders) > 0

    def test_empty_and_none_input(self):
        """Senaryo 2: Boş ve None girdiler"""
        # Boş string
        p, ph = protect_renpy_syntax("")
        assert p == ""
        assert ph == {}
        
        # None girişi (Type hatası fırlatmalı veya handle etmeli - şu anki kod str bekliyor)
        with pytest.raises(TypeError):
             protect_renpy_syntax(None)

    def test_unclosed_brackets_integrity_check(self):
        """Senaryo 3: Kapanmamış parantezlerin tespiti"""
        bad_text = "Welcome to [variable"
        # Bu durumda validate fonksiyonu hata listesi dönmeli
        missing = validate_translation_integrity(bad_text, {"[[v0]]": "[variable]"})
        assert len(missing) > 0 # Hata tespit edilmeli

    def test_similarity_confusion(self):
        """Senaryo 4: Benzer değişkenlerin (0 vs O) karışması"""
        original = "Hello [v0]"
        # AI "Hello [vO]" olarak çevirdi diyelim (sıfır yerine O harfi)
        corrupted_translation = "Hello [vO]"
        
        # protect
        _, ph = protect_renpy_syntax(original)
        print(f"DEBUG: PH={ph}")
        
        # restore
        restored = restore_renpy_syntax(corrupted_translation, ph)
        print(f"DEBUG: Restored='{restored}'")
        
        # integrity check
        missing = validate_translation_integrity(restored, ph)
        print(f"DEBUG: Missing={missing}")
        
        # Ya düzeltmiş olmalı (missing=[]) ya da hatayı fark etmeli (missing=['[v0]'])
        # NOT: 'missing' listesinde original tag stringi tam olarak olmalı.
        assert (original in restored) or ("[v0]" in missing)

    def test_massive_string_performance(self):
        """Senaryo 5: Büyük metin bloğu (Performance/Crash test)"""
        # 100 bin karakterlik metin, içinde binlerce tag
        huge_text = "Start " + ("[test] " * 5000) + " End"
        
        try:
            protected, placeholders = protect_renpy_syntax(huge_text)
            assert len(placeholders) == 5000
            
            restored = restore_renpy_syntax(protected, placeholders)
            # Whitespace toleranslı karşılaştırma (Padding nedeniyle)
            assert restored.replace(" ", "") == huge_text.replace(" ", "")
        except RecursionError:
            pytest.fail("Recursion limit hit on huge string")
        except Exception as e:
            pytest.fail(f"Crashed on huge string: {e}")

if __name__ == "__main__":
    # Elle çalıştırma için
    t = TestSyntaxGuardEdgeCases()
    print("Running test_recursive_nested_brackets...")
    t.test_recursive_nested_brackets()
    print("PASS")
    
    print("Running test_empty_and_none_input...")
    t.test_empty_and_none_input()
    print("PASS")
    
    print("Running test_unclosed_brackets_integrity_check...")
    t.test_unclosed_brackets_integrity_check()
    print("PASS")
    
    print("Running test_similarity_confusion...")
    t.test_similarity_confusion()
    print("PASS")
    
    print("Running test_massive_string_performance...")
    t.test_massive_string_performance()
    print("PASS")
    
    print("All edge case tests passed manually!")
