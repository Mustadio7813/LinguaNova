"""Explicit approved terminology, with word boundaries and protected syntax."""
import re
from ..linguistic.profile_validator import TOKEN
from ..util import digest


def term_pattern(source):
    return re.compile((r'(?<!\w)' if source[:1].isalnum() else '') + re.escape(source) +
                      (r'(?!\w)' if source[-1:].isalnum() else ''))


def contains_term(text, source):
    return any(term_pattern(source).search(part) for part in TOKEN.split(text)) if source else False


def protect_terms(text, glossary):
    matches = []
    syntax = [(m.start(), m.end()) for m in TOKEN.finditer(text)]
    for source, required in sorted(glossary.items(), key=lambda item: (-len(item[0]), item[0])):
        if not source or not required:
            raise ValueError('El Diccionario solo admite términos y traducciones no vacíos')
        for match in term_pattern(source).finditer(text):
            a, b = match.span()
            if any(a < y and b > x for x, y in syntax + [(x, y) for x, y, _ in matches]):
                continue
            matches.append((a, b, required))
    replacements = {}
    for index, (a, b, required) in enumerate(sorted(matches, reverse=True)):
        token = '[LNTERM_' + digest([text, glossary])[:16] + '_' + str(index) + ']'
        if token in text:
            raise ValueError('El texto original colisiona con un marcador del Diccionario')
        replacements[token] = required
        text = text[:a] + token + text[b:]
    return text, replacements


def restore_terms(text, replacements):
    for token, required in replacements.items():
        if text.count(token) != 1:
            raise ValueError('El proveedor alteró o duplicó un término protegido del Diccionario')
        text = text.replace(token, required)
    return text
