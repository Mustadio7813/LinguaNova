"""Read-only shadow inventory. Omissions require an explicit review decision."""
import re
from ..contracts.entry import Occurrence


def omitted_occurrences(path, content, source_hash, known):
    from src.ui_mod.parser import renpy_statement_string
    pattern = re.compile(r'^\s*(?:(?:text|textbutton|tooltip|[A-Za-z_]\w*)\s+)?(?P<q>"|\')(?P<body>(?:\\.|(?!(?P=q)).)*)(?P=q)')
    out=[]
    for line_no,line in enumerate(content.splitlines(),1):
        if line.lstrip().startswith('#'):
            continue
        match=pattern.match(line)
        if not match:
            continue
        if re.match(r'^\s*(?:font|color|hover_color|selected_color|background|style_prefix|id|add|image)\b',line):
            continue
        text=renpy_statement_string(match['q'],match['body'])
        if not any(c.isalpha() for c in text) or (line_no,text) in known:
            continue
        # Names, assets and Python strings remain uncertain. This scanner does
        # not widen the base parser's technical-text acceptance filters.
        out.append(Occurrence.create(path,line_no,text,line.strip(),'extraction_omission',source_hash,
                                     provenance='shadow_inventory',publishable=False))
    return out
