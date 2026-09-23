import re


class BM25QueryNormalizer:
    """Restore known leaflet vocabulary before PostgreSQL Portuguese stemming.

    This is a deliberately closed vocabulary, not spelling correction or a
    general accent-restoration algorithm. Medication names and unknown words
    are left alone. The database still owns stemming and accent folding.
    """

    _word_pattern = re.compile(r"\b[^\W\d_]+\b")
    _accented_terms = {
        "advertencia": "advertência",
        "advertencias": "advertências",
        "composicao": "composição",
        "composicoes": "composições",
        "contraindicacao": "contraindicação",
        "contraindicacoes": "contraindicações",
        "indicacao": "indicação",
        "indicacoes": "indicações",
        "informacao": "informação",
        "informacoes": "informações",
        "interacao": "interação",
        "interacoes": "interações",
        "precaucao": "precaução",
        "precaucoes": "precauções",
        "reacao": "reação",
        "reacoes": "reações",
    }

    def normalize(self, query: str) -> str:
        return self._word_pattern.sub(self._restore_known_accent, query)

    def _restore_known_accent(self, match: re.Match[str]) -> str:
        word = match.group(0)
        return self._accented_terms.get(word.casefold(), word)
