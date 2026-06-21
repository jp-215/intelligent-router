"""Token estimation — a shared, dependency-free helper.

A deliberately rough heuristic (~4 chars/token). Used by prompt analysis and by the
map-reduce runner to size tasks for budget estimation. Kept here, free of any domain
imports, so every layer can use it without creating a dependency cycle.
"""

from __future__ import annotations


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token), minimum 1."""
    return max(1, len(text) // 4)
