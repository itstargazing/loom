"""Pure tests for topic clustering and local claim comparison."""

from app.services.contradiction_cluster import ClaimRef, cluster_by_topic, cosine_similarity, topic_vector
from app.services.contradiction_compare import ComparisonInput, compare_locally


def test_similar_topics_land_in_one_cluster():
    claims = [
        ClaimRef(id="a", topic="global average temperatures", claim="1.2", source_url="https://a.example"),
        ClaimRef(id="b", topic="global average temperature", claim="0.8", source_url="https://b.example"),
        ClaimRef(id="c", topic="working memory scores", claim="14%", source_url="https://c.example"),
    ]
    clusters = cluster_by_topic(claims)
    sizes = sorted(len(cluster) for cluster in clusters)
    assert sizes == [1, 2]
    paired = next(cluster for cluster in clusters if len(cluster) == 2)
    assert {claim.id for claim in paired} == {"a", "b"}


def test_cosine_is_one_for_identical_topics():
    vector = topic_vector("global average temperatures")
    assert abs(cosine_similarity(vector, vector) - 1.0) < 1e-9


def test_different_figures_conflict():
    result = compare_locally(
        ComparisonInput(
            topic="global average temperatures",
            claim_a="Global average temperatures rose by 1.2 degrees Celsius.",
            claim_b="Global average temperatures rose by 0.8 degrees Celsius.",
            source_a_url="https://a.example",
            source_b_url="https://b.example",
        )
    )
    assert result.conflicts is True
    assert "1.2" in result.explanation and "0.8" in result.explanation


def test_identical_claims_do_not_conflict():
    claim = "Global average temperatures rose by 1.2 degrees Celsius."
    result = compare_locally(
        ComparisonInput(
            topic="temperatures",
            claim_a=claim,
            claim_b=claim,
            source_a_url="https://a.example",
            source_b_url="https://b.example",
        )
    )
    assert result.conflicts is False


def test_unrelated_wording_without_figures_does_not_conflict():
    result = compare_locally(
        ComparisonInput(
            topic="attention",
            claim_a="Attention is a scarce resource in modern economies.",
            claim_b="Readers allocate attention unevenly across a page.",
            source_a_url="https://a.example",
            source_b_url="https://b.example",
        )
    )
    assert result.conflicts is False
