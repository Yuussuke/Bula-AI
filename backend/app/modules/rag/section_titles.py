"""Comparison keys and existing administrative-section eligibility policy."""

import re
import unicodedata


# Also used by PostgreSQL regexp_replace; keep syntax valid in both engines.
NUMBERED_SECTION_PREFIX_PATTERN = r"^[ \t]*[0-9]+([.][0-9]+)*[.)][ \t]+"
ADMINISTRATIVE_SECTION_PATTERN = (
    r"historico de alterac.*bula|venda sob prescricao|dizeres legais"
)


def normalize_section_title(section_title: str) -> str:
    """Build a comparison key, never a replacement for the source title."""
    title_without_number = re.sub(
        NUMBERED_SECTION_PREFIX_PATTERN, "", section_title.strip()
    )
    decomposed_title = unicodedata.normalize("NFKD", title_without_number.lower())
    title_without_accents = "".join(
        character
        for character in decomposed_title
        if not unicodedata.combining(character)
    )
    return " ".join(title_without_accents.split())


def is_administrative_section(section_title: str) -> bool:
    """Use documentary section identity, not clinical words in the body."""
    return (
        re.search(
            ADMINISTRATIVE_SECTION_PATTERN, normalize_section_title(section_title)
        )
        is not None
    )
