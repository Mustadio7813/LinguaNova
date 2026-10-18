"""Test character_define_re regex matching."""
import re

_QS = r'(?:[rRuUbBfF]{,2})?(?P<quote>"(?:[^"\\]|\\.)*"|\'(?:[^\\\']|\\.)*\')'

pattern = re.compile(
    r'^\s*define\s+'
    r'(?P<var_name>\w+)\s*'
    r'=\s*'
    r'(?:Dynamic|NVL|ADV)?Character\s*\(\s*'
    r'(?:_\s*\(\s*)?'
    rf'{_QS}'
    r'(?:\s*\))?',
    re.MULTILINE | re.DOTALL
)

test = 'define frank = Character(\n    "Frank",\n    color="#ABCDEF"\n)'
m = pattern.search(test)
print(f"Match: {m is not None}")
if m:
    print(f"var_name: {m.group('var_name')}")
    print(f"quote: {m.group('quote')}")
else:
    print("FAIL - no match")
