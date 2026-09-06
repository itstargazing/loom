"""Stub classifier emits contradiction candidates for checkable figures."""

from app.ai.stub_client import classify_locally


def test_stub_emits_contradiction_candidate_for_statistical_claim():
    result = classify_locally(
        {
            "eventType": "text_copied",
            "sourceUrl": "https://www.nature.com/articles/demo",
            "pageTitle": "Warming",
            "payload": {
                "text": (
                    "According to Hansen et al, global average temperatures rose by "
                    "1.2 degrees Celsius relative to the pre-industrial baseline."
                )
            },
        }
    )
    categories = {item.category for item in result.classifications}
    assert "contradiction_candidate" in categories
    claim = next(
        item for item in result.classifications if item.category == "contradiction_candidate"
    )
    assert "1.2" in claim.fields.claim
    assert "temperature" in claim.fields.topic
