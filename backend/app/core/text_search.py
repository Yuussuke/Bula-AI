"""Literal, accent-insensitive predicates shared by navigation searches."""

import re

from sqlalchemy import SQLColumnExpression, and_, func, literal
from sqlalchemy.sql.elements import ColumnElement


def text_search_match(
    column: SQLColumnExpression[str | None], query: str, *, word_prefix: bool
) -> ColumnElement[bool]:
    normalized_column = func.lower(func.unaccent(column))
    conditions: list[ColumnElement[bool]] = []
    for term in query.split():
        if word_prefix:
            pattern = literal(r"(^|\W)") + func.lower(func.unaccent(re.escape(term)))
            conditions.append(normalized_column.regexp_match(pattern))
        else:
            escaped = term.replace("/", "//").replace("%", "/%").replace("_", "/_")
            conditions.append(
                normalized_column.contains(
                    func.lower(func.unaccent(escaped)), escape="/"
                )
            )
    return and_(*conditions)
