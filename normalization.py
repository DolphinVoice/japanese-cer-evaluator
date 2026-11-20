"""Boolean YAML switches for Japanese text normalization."""
import re
import unicodedata
from pathlib import Path
import yaml

KEYS = {'unicode_nfkc', 'lowercase', 'kana_to_hiragana', 'remove_format_characters',
        'remove_whitespace',
        'remove_punctuation', 'remove_symbols', 'preserve_numeric_symbols'}


class Normalizer:
    def __init__(self, path):
        raw = Path(path).read_bytes()
        self.config = yaml.safe_load(raw)
        if not isinstance(self.config, dict) or set(self.config) != KEYS:
            raise ValueError(f'YAML requires exactly these boolean switches: {sorted(KEYS)}')
        if any(type(v) is not bool for v in self.config.values()):
            raise ValueError('All YAML values must be True or False')

    def apply(self, text):
        trace = []
        for op in ['unicode_nfkc', 'lowercase',
                   'kana_to_hiragana', 'remove_format_characters', 'remove_punctuation', 'remove_symbols', 'remove_whitespace']:
            if not self.config[op]:
                continue
            before = text
            if op == 'unicode_nfkc':
                text = unicodedata.normalize('NFKC', text)
            elif op == 'lowercase':
                text = text.lower()
            elif op == 'kana_to_hiragana':
                text = ''.join(chr(ord(c)-96) if 'ァ' <= c <= 'ヶ' else c for c in text)
            elif op == 'remove_format_characters':
                text = ''.join(c for c in text if unicodedata.category(c) != 'Cf')
            elif op in {'remove_punctuation', 'remove_symbols'}:
                protected = set()
                if self.config['preserve_numeric_symbols']:
                    for match in re.finditer(r'[+-]?[0-9]+(?:\.[0-9]+)?%?', text):
                        protected.update(range(match.start(), match.end()))
                category = 'P' if op == 'remove_punctuation' else 'S'
                text = ''.join(c for i, c in enumerate(text) if i in protected or not unicodedata.category(c).startswith(category))
            elif op == 'remove_whitespace':
                text = ''.join(c for c in text if not c.isspace())
            if before != text:
                trace.append({'op': op, 'before': before, 'after': text})
        return text, trace
