"""Normalização e mapeamentos de nomes de tipos/strings."""
import unicodedata


def normalize(value: object) -> str:
    """Normaliza removendo acentos e reduzindo para lower-case.

    Retorna string vazia para None/NaN.
    """
    if value is None:
        return ''
    s = str(value)
    s = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    return s.lower()


def canonical_type(normalized: str) -> str:
    """Mapeia tipo normalizado para nome canônico usado no app."""
    n = normalized
    if n in {normalize('História'), normalize('Historia'), normalize('Story')}:
        return 'História'
    if n in {normalize('Débito Técnico'), normalize('Debito Tecnico'), normalize('Technical Debt')}:
        return 'Débito Técnico'
    if n in {normalize('Spike')}:
        return 'Spike'
    return normalized


