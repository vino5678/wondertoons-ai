"""Character similarity-check interface.

The bundled checker compares TEXT only (word overlap). It cannot prove two
characters look different. Swap in an image-embedding checker later by
implementing SimilarityChecker.
"""
from __future__ import annotations

import string
from abc import ABC, abstractmethod
from dataclasses import dataclass

_STRIP = string.punctuation + "।“”‘’"


@dataclass
class SimilarityMatch:
    character_id: str
    name: str
    score: float


class SimilarityChecker(ABC):
    method: str = "base"
    guarantees_visual_uniqueness: bool = False

    @abstractmethod
    def compare(self, candidate: dict, existing: list[dict]) -> list[SimilarityMatch]:
        """Return matches sorted by descending score (0..1)."""


def _tokens(text: str) -> set:
    # Whitespace split keeps Tamil combining marks intact (regex \w would split them).
    return {t.strip(_STRIP) for t in text.lower().split() if t.strip(_STRIP)}


class TextOverlapSimilarityChecker(SimilarityChecker):
    method = "text_overlap"
    guarantees_visual_uniqueness = False

    def compare(self, candidate: dict, existing: list[dict]) -> list[SimilarityMatch]:
        a = _tokens(f"{candidate.get('name', '')} {candidate.get('appearance', '')}")
        out = []
        for ch in existing:
            b = _tokens(f"{ch.get('name', '')} {ch.get('appearance', '')}")
            union = a | b
            score = (len(a & b) / len(union)) if union else 0.0
            out.append(SimilarityMatch(ch["id"], ch.get("name", ""), round(score, 4)))
        out.sort(key=lambda m: (-m.score, m.character_id))
        return out
