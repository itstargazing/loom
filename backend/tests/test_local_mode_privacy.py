"""Local-only mode must never call the cloud AI client."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.classification import ClassificationResult, ExtractedFields, ClassificationItem
from app.services.classification import ClassificationOutcome
from app.services.local_mode import matches_local_domain


def test_matches_local_domain_for_subdomains():
    assert matches_local_domain("https://secure.bank.example.com/a", ["bank.example.com"])
    assert not matches_local_domain("https://example.com", ["bank.example.com"])


@pytest.mark.asyncio
async def test_classify_and_route_uses_local_client_for_local_domains(monkeypatch):
    from app.worker import classification_worker as worker

    event_id = uuid4()
    user_id = "dev-user"
    event = SimpleNamespace(
        id=event_id,
        user_id=user_id,
        event_type="highlight_selected",
        source_url="https://portal.bank.example.com/statements",
        page_title="Statements",
        payload={"text": "account balance", "context": "Your balance is $12."},
        occurred_at=datetime.now(UTC),
    )

    cloud_calls = {"count": 0}
    local_calls = {"count": 0}

    class FakeCloud:
        provider = "claude"
        model = "should-not-run"

        async def complete_structured(self, *args, **kwargs):
            cloud_calls["count"] += 1
            raise AssertionError("cloud AI must not run in local-only mode")

    class FakeLocal:
        provider = "stub"
        model = "local-heuristics"

        async def complete_structured(self, *args, **kwargs):
            local_calls["count"] += 1
            return None

    async def fake_already_handled(_session, _id):
        return False

    async def fake_load(_session, _id):
        return user_id, event

    class FakePrivacy:
        local_only_domains = ["bank.example.com"]

    class FakeScalars:
        def scalar_one_or_none(self):
            return FakePrivacy()

    class FakeResult:
        def scalar_one_or_none(self):
            return FakePrivacy()

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def execute(self, *_args, **_kwargs):
            return FakeResult()

        async def commit(self):
            return None

    async def fake_classify_event(event_arg, client):
        assert client is local_client
        cloud_calls["seen_event"] = event_arg
        result = ClassificationResult(
            classifications=[
                ClassificationItem(
                    category="none",
                    confidence=0.2,
                    reason="local",
                    fields=ExtractedFields.of(),
                )
            ]
        )
        return ClassificationOutcome(
            result=result,
            attempts=1,
            provider=client.provider,
            model=client.model,
            latency_ms=1,
            error=None,
            raw_text="{}",
            cached=False,
        )

    async def fake_record_outcome(*_args, **_kwargs):
        return SimpleNamespace(id=uuid4(), categories=["none"])

    async def fake_route(*_args, **_kwargs):
        return SimpleNamespace(entries=[], skipped=[], created_count=0, merged_count=0)

    async def fake_upsert(*_args, **_kwargs):
        return None

    async def fake_mark(*_args, **_kwargs):
        return None

    local_client = FakeLocal()
    monkeypatch.setattr(worker, "async_session_factory", FakeSession)
    monkeypatch.setattr(worker, "already_handled", fake_already_handled)
    monkeypatch.setattr(worker, "load_classifiable_event", fake_load)
    monkeypatch.setattr(worker, "get_ai_client", lambda: FakeCloud())
    monkeypatch.setattr(worker, "get_local_ai_client", lambda: local_client)
    monkeypatch.setattr(worker, "get_cached_result", lambda *_a, **_k: None)
    monkeypatch.setattr(worker, "classify_event", fake_classify_event)
    monkeypatch.setattr(worker, "record_outcome", fake_record_outcome)
    monkeypatch.setattr(worker, "route_classification", fake_route)
    monkeypatch.setattr(worker, "upsert_embedding", fake_upsert)
    monkeypatch.setattr(worker, "mark_routed", fake_mark)
    monkeypatch.setattr(worker, "matches_local_domain", lambda *_a, **_k: True)

    ok = await worker.classify_and_route(event_id, user_id)
    assert ok is True
    assert cloud_calls["count"] == 0
