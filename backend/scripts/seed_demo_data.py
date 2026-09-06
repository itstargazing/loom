"""Fill a local database with a realistic pipeline run, so the dashboard has data.

Runs the same persist -> classify -> route path the worker uses, but calls it
directly instead of going through Redis, so only Postgres needs to be up:

    python -m scripts.seed_demo_data

Safe to re-run. Event ids are derived from their content, so a second run
exercises the deduplication path rather than doubling the data.
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.core.database import async_session_factory
from app.schemas.capture import CaptureEventIn
from app.services.capture_ingest import persist_capture_events
from app.worker.classification_worker import classify_and_route

#  Stable per-content ids, so re-running seeds the same events rather than new
#  ones. Any fixed namespace works; this one is arbitrary.
NAMESPACE = uuid.UUID("6f1d6f6a-1b3f-4a2e-9c1d-000000000001")

NOW = datetime.now(UTC)


def event(
    event_type: str,
    source_url: str,
    page_title: str,
    payload: dict,
    *,
    minutes_ago: int,
) -> CaptureEventIn:
    return CaptureEventIn.model_validate(
        {
            "id": str(uuid.uuid5(NAMESPACE, f"{event_type}|{source_url}|{page_title}")),
            "type": event_type,
            "sourceUrl": source_url,
            "pageTitle": page_title,
            "timestamp": (NOW - timedelta(minutes=minutes_ago)).isoformat(),
            "payload": payload,
        }
    )


SAMPLES = [
    event(
        "highlight_selected",
        "https://arxiv.org/abs/1706.03762",
        "Attention Is All You Need",
        {
            "text": "positional encoding",
            "context": (
                "Since our model contains no recurrence and no convolution, we add "
                "positional encodings to the input embeddings."
            ),
        },
        minutes_ago=4,
    ),
    event(
        "highlight_selected",
        "https://en.wikipedia.org/wiki/Amortized_analysis",
        "Amortized analysis",
        {
            "text": "amortized analysis",
            "context": (
                "Amortized analysis averages the running time of an operation over "
                "a worst-case sequence of operations."
            ),
        },
        minutes_ago=51,
    ),
    event(
        "text_copied",
        "https://www.nature.com/articles/s41586-024-00001",
        "Global temperature trends",
        {
            "text": (
                "According to Hansen et al, global average temperatures rose by 1.2 "
                "degrees Celsius relative to the pre-industrial baseline in 2024."
            )
        },
        minutes_ago=12,
    ),
    event(
        "text_copied",
        "https://pubmed.ncbi.nlm.nih.gov/38000001/",
        "Sleep duration and cognitive performance",
        {
            "text": (
                "Participants sleeping fewer than six hours per night showed a 14 "
                "percent decline in working memory scores across the trial."
            )
        },
        minutes_ago=90,
    ),
    #  Conflicting figures on the same topics — feed for the contradiction watcher.
    event(
        "text_copied",
        "https://www.climate.org/reports/warming-2024",
        "Warming reassessment 2024",
        {
            "text": (
                "According to the reassessment, global average temperatures rose by "
                "0.8 degrees Celsius relative to the pre-industrial baseline in 2024."
            )
        },
        minutes_ago=10,
    ),
    event(
        "text_copied",
        "https://www.sleepfoundation.org/research/working-memory",
        "Working memory and sleep hours",
        {
            "text": (
                "Participants sleeping fewer than six hours per night showed a 6 "
                "percent decline in working memory scores across the trial."
            )
        },
        minutes_ago=85,
    ),
    event(
        "page_opened",
        "https://university.edu/cs101/syllabus",
        "CS101 Syllabus",
        {
            "contentType": "html",
            "fullText": (
                "Problem Set 3 is due 2026-09-15 and must be submitted through the "
                "course portal no later than 5pm. Midterm exam is on October 20, 2026. "
                "RSVP for the review session by 2026-10-18."
            ),
        },
        minutes_ago=30,
    ),
    event(
        "page_opened",
        "https://grants.example.org/fellowship",
        "Research Fellowship 2027",
        {
            "contentType": "html",
            "fullText": (
                "Applications for the 2027 cohort close on 2026-11-01. The last day "
                "to submit references is 2026-11-08."
            ),
        },
        minutes_ago=200,
    ),
    event(
        "page_opened",
        "https://jobs.example.com/postings/staff-engineer",
        "Staff Engineer, Platform",
        {
            "contentType": "html",
            "fullText": (
                "We are hiring a Staff Engineer for the Platform team. "
                "Responsibilities include owning the ingestion pipeline. Salary "
                "range $180,000 - $220,000. Full-time, remote within the EU."
            ),
        },
        minutes_ago=75,
    ),
    event(
        "page_opened",
        "https://shop.example.com/keyboards/hhkb",
        "HHKB Professional Hybrid Type-S",
        {
            "contentType": "html",
            "fullText": (
                "Price $385.00. In stock, free shipping. 60 percent layout, "
                "Bluetooth and USB-C, silenced Topre switches."
            ),
        },
        minutes_ago=140,
    ),
    event(
        "page_opened",
        "https://shop.example.com/keyboards/keychron-q1-max",
        "Keychron Q1 Max",
        {
            "contentType": "html",
            "fullText": (
                "Price $199.00. In stock, paid shipping. 75 percent layout, "
                "Bluetooth and USB-C, Gateron Jupiter switches."
            ),
        },
        minutes_ago=138,
    ),
    event(
        "page_opened",
        "https://app.example.com/terms",
        "Terms of Service",
        {
            "contentType": "html",
            "fullText": (
                "You hereby agree that the Company shall not be liable for any "
                "indirect damages, and you indemnify the Company against all "
                "claims. Any dispute shall be resolved by binding arbitration. "
                "Governing law is the State of Delaware."
            ),
        },
        minutes_ago=320,
    ),
    event(
        "scroll_dwell",
        "https://example.com/essays/on-attention",
        "On Attention",
        {
            "sections": [
                {"heading": "Intro", "excerpt": "A brief opening.", "dwellMs": 1_200},
                {
                    "heading": "The core argument",
                    "excerpt": (
                        "Attention is a scarce resource, and its scarcity is what "
                        "gives it economic value."
                    ),
                    "dwellMs": 42_000,
                },
            ]
        },
        minutes_ago=8,
    ),
    event(
        "scroll_dwell",
        "https://example.com/essays/deep-work",
        "Notes on deep work",
        {
            "sections": [
                {
                    "heading": "Context switching",
                    "excerpt": (
                        "Every unfinished task leaves a residue that taxes the next "
                        "block of focus."
                    ),
                    "dwellMs": 18_000,
                },
                {
                    "heading": "Protecting mornings",
                    "excerpt": (
                        "The first uninterrupted hours of the day are the highest "
                        "leverage for cognitively demanding work."
                    ),
                    "dwellMs": 27_000,
                },
            ]
        },
        minutes_ago=6,
    ),
    #  Expected to be classified as 'none' and routed nowhere. Present so the
    #  seeded data includes the skip path, not only successes.
    event(
        "text_copied",
        "https://bank.example.com/login",
        "Sign in",
        {"text": "my password is hunter2"},
        minutes_ago=60,
    ),
]


async def main() -> None:
    user_id = settings.stub_user_id
    print(f"database={settings.database_url.split('@')[-1]}")
    print(f"user={user_id} events={len(SAMPLES)}\n")

    from app.models.account import UserAccount

    async with async_session_factory() as session:
        account = await session.get(UserAccount, user_id)
        if account is None:
            session.add(
                UserAccount(
                    user_id=user_id,
                    display_name="Dev user",
                    email="dev@localhost",
                    auth_mode="stub",
                )
            )
            await session.commit()
            print("created stub account profile")
        else:
            print(f"account already exists ({account.display_name})")

    async with async_session_factory() as session:
        inserted = await persist_capture_events(
            session, [(user_id, sample) for sample in SAMPLES]
        )

    print(f"persisted {len(inserted)} new event(s), "
          f"{len(SAMPLES) - len(inserted)} already stored")

    #  Already-stored events are re-run too: routing is idempotent, and this
    #  makes a repeat run refresh the stores rather than do nothing.
    for sample in SAMPLES:
        await classify_and_route(sample.id, user_id)

    #  Listings routed before spec extraction existed stay empty. Re-extract
    #  from the capture payload so comparison has aligned attributes without
    #  deleting classifications.
    from sqlalchemy import delete, select

    from app.models.capture_event import CaptureEvent
    from app.models.skill_stores import ProductListing
    from app.services.product_extract import extract_product_price, extract_product_specs

    async with async_session_factory() as session:
        rows = (
            await session.execute(
                select(ProductListing, CaptureEvent).join(
                    CaptureEvent, CaptureEvent.id == ProductListing.capture_event_id
                ).where(ProductListing.user_id == user_id)
            )
        ).all()
        refreshed = 0
        for listing, event in rows:
            text = str((event.payload or {}).get("fullText") or "")
            if not text:
                continue
            specs = extract_product_specs(text)
            price = extract_product_price(text)
            changed = False
            if specs and listing.specs != specs:
                listing.specs = specs
                changed = True
            if price and listing.price != price:
                listing.price = price
                changed = True
            if changed:
                refreshed += 1
        await session.commit()
    print(f"refreshed {refreshed} product listing(s)")

    #  Events classified before contradiction_candidate existed stay "handled"
    #  forever. Clear those outcomes so a seed refresh picks up the new category.
    from app.ai import get_ai_client
    from app.models.event_classification import EventClassification
    from app.models.skill_stores import ContradictionClaim
    from app.services.contradiction_watcher import flag_conflicts_for_user

    async with async_session_factory() as session:
        claimed_events = {
            event_id
            for event_id in (
                await session.execute(
                    select(ContradictionClaim.capture_event_id).where(
                        ContradictionClaim.user_id == user_id,
                        ContradictionClaim.capture_event_id.is_not(None),
                    )
                )
            ).scalars()
        }

    needs_claim = [
        sample.id
        for sample in SAMPLES
        if sample.type == "text_copied"
        and "password" not in str(sample.payload.get("text", "")).casefold()
        and sample.id not in claimed_events
    ]
    if needs_claim:
        async with async_session_factory() as session:
            await session.execute(
                delete(EventClassification).where(
                    EventClassification.capture_event_id.in_(needs_claim)
                )
            )
            await session.commit()
        print(f"reclassifying {len(needs_claim)} text_copied event(s) for claims")
        for sample_id in needs_claim:
            await classify_and_route(sample_id, user_id)

    async with async_session_factory() as session:
        flagged = await flag_conflicts_for_user(
            session, get_ai_client(), user_id=user_id
        )
    print(f"contradiction watcher flagged {flagged} pair(s)")

    #  Phase 12 demo: two assignment drafts that diverge on deadline wording.
    from app.models.live_doc_diff import WatchedDocument, WatchedSet
    from app.services.live_doc_diff import add_snapshot, scan_watched_set

    async with async_session_factory() as session:
        existing = (
            await session.execute(
                select(WatchedSet).where(
                    WatchedSet.user_id == user_id,
                    WatchedSet.name == "Assignment drafts",
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            watched = WatchedSet(user_id=user_id, name="Assignment drafts")
            session.add(watched)
            await session.flush()
            alice = WatchedDocument(
                set_id=watched.id,
                user_id=user_id,
                label="Alice draft",
                source_url="https://docs.example.com/assignment/alice",
            )
            bob = WatchedDocument(
                set_id=watched.id,
                user_id=user_id,
                label="Bob draft",
                source_url="https://docs.example.com/assignment/bob",
            )
            session.add_all([alice, bob])
            await session.flush()
            await add_snapshot(
                session,
                alice,
                (
                    "Group project outline.\n"
                    "The deadline is Friday.\n"
                    "Include the literature review section."
                ),
            )
            await add_snapshot(
                session,
                bob,
                (
                    "Group project outline.\n"
                    "The deadline is Monday.\n"
                    "Include the literature review section.\n"
                    "Add the evaluation rubric appendix."
                ),
            )
            events = await scan_watched_set(session, watched)
            await session.commit()
            print(f"seeded live doc diff set with {len(events)} event(s)")
        else:
            print("live doc diff demo set already present")

    #  Phase 13: seed a small recent-document index for auto-attach demos.
    from app.models.auto_attach import RecentDocument
    from app.models.form_filler import FormDocument
    from app.services.auto_attach_index import index_form_document, upsert_recent_document

    async with async_session_factory() as session:
        existing_docs = (
            await session.execute(
                select(RecentDocument).where(RecentDocument.user_id == user_id)
            )
        ).scalars().all()
        if not existing_docs:
            await upsert_recent_document(
                session,
                user_id=user_id,
                filename="jane-doe-resume.pdf",
                source_url="https://files.example.com/jane-doe-resume.pdf",
                doc_type="resume",
                summary=(
                    "Jane Doe. Software engineer. Experience building data pipelines "
                    "and browser tooling. Curriculum vitae."
                ),
                mime_type="application/pdf",
            )
            await upsert_recent_document(
                session,
                user_id=user_id,
                filename="passport-scan.png",
                source_url="https://files.example.com/passport-scan.png",
                doc_type="id_scan",
                summary="Government ID / passport photo scan for identity verification.",
                mime_type="image/png",
            )
            form_docs = (
                await session.execute(
                    select(FormDocument).where(FormDocument.user_id == user_id)
                )
            ).scalars().all()
            for form_doc in form_docs:
                await index_form_document(
                    session,
                    user_id=user_id,
                    filename=form_doc.filename,
                    source_url=form_doc.source_url,
                    storage_path=form_doc.storage_path,
                )
            await session.commit()
            print(f"seeded auto-attach index ({2 + len(form_docs)} document(s))")
        else:
            print(f"auto-attach index already has {len(existing_docs)} document(s)")

    print("\nDone. Start the API and open the dashboard to see the result.")


if __name__ == "__main__":
    asyncio.run(main())
