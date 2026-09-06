"""Cluster contradiction claims by topic similarity before pairwise comparison.

Real embeddings can replace the bag-of-tokens vectors later; the interface stays
the same so the watcher does not care how similarity is computed. Clustering
first keeps the comparison step O(cluster size^2) instead of O(n^2).
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeVar

TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "of",
    "in",
    "on",
    "to",
    "for",
    "by",
    "with",
    "from",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "that",
    "this",
    "it",
    "as",
    "at",
}

#  Topics sharing at least this cosine similarity join the same cluster.
SIMILARITY_THRESHOLD = 0.45

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ClaimRef:
    """Minimal claim shape the clusterer needs."""

    id: object
    topic: str
    claim: str
    source_url: str


def normalize_topic(topic: str) -> str:
    tokens = [
        token
        for token in TOKEN_RE.findall(topic.casefold())
        if token not in STOPWORDS and len(token) > 1
    ]
    return " ".join(tokens)


def topic_tokens(topic: str) -> set[str]:
    return set(normalize_topic(topic).split())


def topic_vector(topic: str) -> dict[str, float]:
    """Unit bag-of-tokens vector — a cheap stand-in for an embedding."""
    tokens = topic_tokens(topic)
    if not tokens:
        return {}
    weight = 1.0 / math.sqrt(len(tokens))
    return {token: weight for token in tokens}


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return sum(weight * right.get(token, 0.0) for token, weight in left.items())


def cluster_by_topic(
    claims: Sequence[ClaimRef],
    *,
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[list[ClaimRef]]:
    """Greedy clustering: assign each claim to the first cluster whose centroid is close."""
    clusters: list[list[ClaimRef]] = []
    centroids: list[dict[str, float]] = []

    for claim in claims:
        vector = topic_vector(claim.topic)
        placed = False
        for index, centroid in enumerate(centroids):
            if cosine_similarity(vector, centroid) >= threshold:
                clusters[index].append(claim)
                #  Refresh centroid as the union of member topic tokens.
                tokens: set[str] = set()
                for member in clusters[index]:
                    tokens |= topic_tokens(member.topic)
                weight = 1.0 / math.sqrt(len(tokens)) if tokens else 0.0
                centroids[index] = {token: weight for token in tokens}
                placed = True
                break
        if not placed:
            clusters.append([claim])
            centroids.append(vector)

    return clusters


def group_by_exact_topic(claims: Sequence[ClaimRef]) -> dict[str, list[ClaimRef]]:
    """Fallback when only exact topic labels should be compared."""
    groups: dict[str, list[ClaimRef]] = defaultdict(list)
    for claim in claims:
        key = normalize_topic(claim.topic) or claim.topic.casefold().strip()
        groups[key].append(claim)
    return dict(groups)
