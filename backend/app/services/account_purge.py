"""Delete all rows owned by a user_id (account deletion)."""

from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import UserAccount
from app.models.auto_attach import RecentDocument
from app.models.capture_event import CaptureEvent
from app.models.collection import Collection
from app.models.event_classification import EventClassification
from app.models.form_filler import FormDocument, FormProfile
from app.models.live_doc_diff import (
    DocumentDiffEvent,
    DocumentSnapshot,
    WatchedDocument,
    WatchedSet,
)
from app.models.privacy import UserPrivacySettings
from app.models.skill_stores import (
    Citation,
    ContractFlag,
    Contradiction,
    ContradictionClaim,
    Deadline,
    GlossaryTerm,
    JobListing,
    ProductListing,
    ReadingCompilerEntry,
)


async def purge_user_data(session: AsyncSession, user_id: str) -> dict[str, int]:
    """Erase skill stores, captures, and account rows for one user."""
    counts: dict[str, int] = {}

    async def _wipe(model, label: str) -> None:
        result = await session.execute(delete(model).where(model.user_id == user_id))
        counts[label] = int(result.rowcount or 0)

    #  Children before parents where FK order matters.
    await _wipe(DocumentDiffEvent, "document_diff_events")
    await _wipe(DocumentSnapshot, "document_snapshots")
    await _wipe(WatchedDocument, "watched_documents")
    await _wipe(WatchedSet, "watched_sets")
    await _wipe(RecentDocument, "recent_documents")
    await _wipe(FormDocument, "form_documents")
    await _wipe(FormProfile, "form_profiles")
    await _wipe(Contradiction, "contradictions")
    await _wipe(ContradictionClaim, "contradiction_claims")
    await _wipe(GlossaryTerm, "glossary_terms")
    await _wipe(Citation, "citations")
    await _wipe(Deadline, "deadlines")
    await _wipe(ReadingCompilerEntry, "reading_compiler_entries")
    await _wipe(ProductListing, "product_listings")
    await _wipe(JobListing, "job_listings")
    await _wipe(ContractFlag, "contract_flags")
    await _wipe(Collection, "collections")
    await _wipe(EventClassification, "event_classifications")
    await _wipe(CaptureEvent, "capture_events")
    await _wipe(UserPrivacySettings, "user_privacy_settings")
    await _wipe(UserAccount, "user_accounts")
    await session.commit()
    return counts
