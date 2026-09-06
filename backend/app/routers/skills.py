"""Read endpoints for the typed skill stores.

The eight list endpoints are generated from ``SKILL_RESOURCES`` rather than
written out, so each one keeps its own response model in the OpenAPI schema
while the query logic exists once. Adding a skill means adding a registry entry.
"""

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUserId
from app.models.collection import Collection
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
from app.schemas.skills import (
    CitationOut,
    CitationPatch,
    CollectionIn,
    CollectionOut,
    ContractFlagOut,
    ContradictionClaimOut,
    ContradictionOut,
    ContradictionPatch,
    DeadlineOut,
    DeadlinePatch,
    GlossaryTermOut,
    GlossaryTermPatch,
    JobListingOut,
    ProductCompareColumnOut,
    ProductCompareOut,
    ProductListingOut,
    ProductListingPatch,
    NormalizedPriceOut,
    ReadingCompileOut,
    ReadingCompilePassageOut,
    ReadingCompilerEntryOut,
    ReadingCompilerEntryPatch,
)
from app.services.citation_format import (
    CitationMeta,
    bibliography_filename,
    format_styles,
    render_bibliography,
)
from app.services.deadline_extract import document_identity
from app.services.deadline_parse import date_identity, parse_due
from app.services.dedup import dedup_key
from app.services.product_compare import compare_products, render_csv
from app.services.reading_compile import (
    CompiledPassage,
    compilation_filename,
    order_passages,
    render_markdown,
    render_plain_text,
)
from app.services.reading_pdf import render_pdf

router = APIRouter(prefix="/api", tags=["skills"])


class SkillResource:
    def __init__(
        self,
        slug: str,
        label: str,
        model: Any,
        schema: type[BaseModel],
        *,
        title_column: str,
        detail_column: str,
        search_columns: tuple[str, ...] | None = None,
    ):
        self.slug = slug
        self.label = label
        self.model = model
        self.schema = schema
        #  Which columns stand in for "title" and "detail" when entries from
        #  different stores are listed together in the overview feed.
        self.title_column = title_column
        self.detail_column = detail_column
        self.search_columns = search_columns or (title_column, detail_column)

    @property
    def title(self) -> Any:
        return getattr(self.model, self.title_column)

    @property
    def detail(self) -> Any:
        return getattr(self.model, self.detail_column)


SKILL_RESOURCES: list[SkillResource] = [
    SkillResource(
        "glossary",
        "Glossary",
        GlossaryTerm,
        GlossaryTermOut,
        title_column="term",
        detail_column="definition",
    ),
    SkillResource(
        "citations",
        "Citations",
        Citation,
        CitationOut,
        title_column="quote",
        detail_column="author",
        search_columns=("quote", "author", "work_title", "publisher"),
    ),
    SkillResource(
        "deadlines",
        "Deadlines",
        Deadline,
        DeadlineOut,
        title_column="title",
        detail_column="due_text",
        search_columns=("title", "due_text", "kind", "context_snippet", "page_title"),
    ),
    SkillResource(
        "contradiction-claims",
        "Claims",
        ContradictionClaim,
        ContradictionClaimOut,
        title_column="claim",
        detail_column="topic",
    ),
    SkillResource(
        "reading",
        "Reading Compiler",
        ReadingCompilerEntry,
        ReadingCompilerEntryOut,
        title_column="passage",
        detail_column="heading",
    ),
    SkillResource(
        "products",
        "Product Comparisons",
        ProductListing,
        ProductListingOut,
        title_column="name",
        detail_column="price",
    ),
    SkillResource(
        "jobs",
        "Job Listings",
        JobListing,
        JobListingOut,
        title_column="title",
        detail_column="company",
    ),
    SkillResource(
        "contract-flags",
        "Contract Flags",
        ContractFlag,
        ContractFlagOut,
        title_column="clause_text",
        detail_column="flag_reason",
    ),
]

SKILLS_BY_SLUG = {resource.slug: resource for resource in SKILL_RESOURCES}


def _ilike_pattern(query: str) -> str:
    """Substring match that treats user-supplied % and _ as literals."""
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _make_list_endpoint(resource: SkillResource):
    model = resource.model

    async def list_entries(
        user_id: CurrentUserId,
        db: Annotated[AsyncSession, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        collection_id: Annotated[uuid.UUID | None, Query()] = None,
        q: Annotated[str | None, Query(max_length=200)] = None,
        sort: Annotated[Literal["recent", "alpha"], Query()] = "recent",
    ) -> Any:
        query = select(model).where(model.user_id == user_id)

        if collection_id is not None:
            query = query.where(model.collection_id == collection_id)

        needle = (q or "").strip()
        if needle:
            pattern = _ilike_pattern(needle)
            query = query.where(
                or_(
                    *[
                        getattr(model, column).ilike(pattern, escape="\\")
                        for column in resource.search_columns
                    ]
                )
            )

        if sort == "alpha":
            query = query.order_by(func.lower(resource.title), model.last_seen_at.desc())
        else:
            query = query.order_by(model.last_seen_at.desc())

        result = await db.execute(query.limit(limit).offset(offset))
        return list(result.scalars().all())

    list_entries.__name__ = f"list_{resource.slug.replace('-', '_')}"
    return list_entries


for _resource in SKILL_RESOURCES:
    router.add_api_route(
        f"/skills/{_resource.slug}",
        _make_list_endpoint(_resource),
        methods=["GET"],
        response_model=list[_resource.schema],
        summary=f"List {_resource.label} entries",
        name=f"list_{_resource.slug}",
    )


async def _owned_glossary(
    db: AsyncSession, entry_id: uuid.UUID, user_id: str
) -> GlossaryTerm:
    result = await db.execute(
        select(GlossaryTerm).where(
            GlossaryTerm.id == entry_id, GlossaryTerm.user_id == user_id
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Glossary entry not found"
        )
    return entry


async def _owned_collection(
    db: AsyncSession, collection_id: uuid.UUID, user_id: str
) -> Collection:
    result = await db.execute(
        select(Collection).where(
            Collection.id == collection_id, Collection.user_id == user_id
        )
    )
    collection = result.scalar_one_or_none()
    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found"
        )
    return collection


@router.patch(
    "/skills/glossary/{entry_id}",
    response_model=GlossaryTermOut,
    summary="Update a glossary term",
)
async def update_glossary_term(
    entry_id: uuid.UUID,
    payload: GlossaryTermPatch,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GlossaryTerm:
    entry = await _owned_glossary(db, entry_id, user_id)

    if "term" in payload.model_fields_set:
        term = (payload.term or "").strip()
        if not term:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Term cannot be empty",
            )
        entry.term = term
        entry.dedup_key = dedup_key(term)

    if "definition" in payload.model_fields_set:
        definition = (payload.definition or "").strip()
        if not definition:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Definition cannot be empty",
            )
        entry.definition = definition

    if "collection_id" in payload.model_fields_set:
        if payload.collection_id is not None:
            await _owned_collection(db, payload.collection_id, user_id)
        entry.collection_id = payload.collection_id

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A glossary entry with that term already exists",
        ) from None

    await db.refresh(entry)
    return entry


@router.delete(
    "/skills/glossary/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a glossary term",
)
async def delete_glossary_term(
    entry_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    entry = await _owned_glossary(db, entry_id, user_id)
    await db.delete(entry)
    await db.commit()


async def _owned_citation(
    db: AsyncSession, entry_id: uuid.UUID, user_id: str
) -> Citation:
    result = await db.execute(
        select(Citation).where(Citation.id == entry_id, Citation.user_id == user_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Citation not found"
        )
    return entry


def _refresh_citation_format(entry: Citation) -> None:
    entry.formatted = format_styles(
        CitationMeta(
            author=entry.author,
            work_title=entry.work_title,
            publisher=entry.publisher,
            published_date=entry.published_date,
            source_url=entry.source_url,
            page_title=entry.page_title,
        )
    )


@router.get(
    "/skills/citations/export",
    summary="Download a bibliography",
    response_class=Response,
)
async def export_citations(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
    style: Annotated[Literal["apa", "mla"], Query()] = "apa",
    format: Annotated[Literal["txt", "md"], Query()] = "txt",
    collection_id: Annotated[uuid.UUID | None, Query()] = None,
    unfiled: Annotated[bool, Query()] = False,
) -> Response:
    query = select(Citation).where(Citation.user_id == user_id)
    heading = "Citations"
    collection_name: str | None = None

    if collection_id is not None:
        collection = await _owned_collection(db, collection_id, user_id)
        heading = collection.name
        collection_name = collection.name
        query = query.where(Citation.collection_id == collection_id)
    elif unfiled:
        heading = "Unfiled"
        collection_name = "unfiled"
        query = query.where(Citation.collection_id.is_(None))

    result = await db.execute(query)
    rendered: list[str] = []
    for entry in result.scalars().all():
        text = (entry.formatted or {}).get(style)
        if not text:
            text = format_styles(
                CitationMeta(
                    author=entry.author,
                    work_title=entry.work_title,
                    publisher=entry.publisher,
                    published_date=entry.published_date,
                    source_url=entry.source_url,
                    page_title=entry.page_title,
                )
            )[style]
        rendered.append(text)
    rendered.sort(key=str.casefold)

    body = render_bibliography(
        rendered, style=style, format=format, heading=heading
    )
    filename = bibliography_filename(collection_name, style, format)
    media_type = (
        "text/markdown; charset=utf-8" if format == "md" else "text/plain; charset=utf-8"
    )
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch(
    "/skills/citations/{entry_id}",
    response_model=CitationOut,
    summary="Correct citation metadata",
)
async def update_citation(
    entry_id: uuid.UUID,
    payload: CitationPatch,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Citation:
    entry = await _owned_citation(db, entry_id, user_id)

    if "author" in payload.model_fields_set:
        author = (payload.author or "").strip()
        entry.author = author or None
    if "work_title" in payload.model_fields_set:
        title = (payload.work_title or "").strip()
        entry.work_title = title or None
    if "publisher" in payload.model_fields_set:
        publisher = (payload.publisher or "").strip()
        entry.publisher = publisher or None
    if "published_date" in payload.model_fields_set:
        published = (payload.published_date or "").strip()
        entry.published_date = published or None
    if "collection_id" in payload.model_fields_set:
        if payload.collection_id is not None:
            await _owned_collection(db, payload.collection_id, user_id)
        entry.collection_id = payload.collection_id

    _refresh_citation_format(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete(
    "/skills/citations/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a citation",
)
async def delete_citation(
    entry_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    entry = await _owned_citation(db, entry_id, user_id)
    await db.delete(entry)
    await db.commit()


async def _owned_deadline(
    db: AsyncSession, entry_id: uuid.UUID, user_id: str
) -> Deadline:
    result = await db.execute(
        select(Deadline).where(Deadline.id == entry_id, Deadline.user_id == user_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Deadline not found"
        )
    return entry


@router.patch(
    "/skills/deadlines/{entry_id}",
    response_model=DeadlineOut,
    summary="Confirm or correct a deadline",
)
async def update_deadline(
    entry_id: uuid.UUID,
    payload: DeadlinePatch,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Deadline:
    entry = await _owned_deadline(db, entry_id, user_id)

    if "title" in payload.model_fields_set:
        title = (payload.title or "").strip()
        if not title:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Title cannot be empty",
            )
        entry.title = title

    if "due_text" in payload.model_fields_set:
        due_text = (payload.due_text or "").strip()
        if not due_text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Due date cannot be empty",
            )
        entry.due_text = due_text
        entry.due_date = parse_due(due_text)

    if "kind" in payload.model_fields_set:
        kind = (payload.kind or "").strip()
        entry.kind = kind or None

    if "confirmed" in payload.model_fields_set:
        entry.confirmed = bool(payload.confirmed)

    if "collection_id" in payload.model_fields_set:
        if payload.collection_id is not None:
            await _owned_collection(db, payload.collection_id, user_id)
        entry.collection_id = payload.collection_id

    entry.dedup_key = dedup_key(
        entry.title,
        date_identity(entry.due_text),
        document_identity(entry.source_url),
    )

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A deadline with that title and date already exists",
        ) from None

    await db.refresh(entry)
    return entry


@router.delete(
    "/skills/deadlines/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a deadline",
)
async def delete_deadline(
    entry_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    entry = await _owned_deadline(db, entry_id, user_id)
    await db.delete(entry)
    await db.commit()


async def _owned_reading(
    db: AsyncSession, entry_id: uuid.UUID, user_id: str
) -> ReadingCompilerEntry:
    result = await db.execute(
        select(ReadingCompilerEntry).where(
            ReadingCompilerEntry.id == entry_id,
            ReadingCompilerEntry.user_id == user_id,
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reading entry not found"
        )
    return entry


async def _load_reading_passages(
    db: AsyncSession,
    user_id: str,
    *,
    collection_id: uuid.UUID | None,
    unfiled: bool,
    since: datetime | None,
    until: datetime | None,
    source_url: str | None,
) -> list[ReadingCompilerEntry]:
    query = select(ReadingCompilerEntry).where(ReadingCompilerEntry.user_id == user_id)
    if collection_id is not None:
        await _owned_collection(db, collection_id, user_id)
        query = query.where(ReadingCompilerEntry.collection_id == collection_id)
    elif unfiled:
        query = query.where(ReadingCompilerEntry.collection_id.is_(None))
    if since is not None:
        query = query.where(ReadingCompilerEntry.last_seen_at >= since)
    if until is not None:
        query = query.where(ReadingCompilerEntry.last_seen_at <= until)
    if source_url:
        query = query.where(ReadingCompilerEntry.source_url == source_url)
    query = query.order_by(
        ReadingCompilerEntry.source_url, ReadingCompilerEntry.created_at
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def _compile_reading_document(
    db: AsyncSession,
    user_id: str,
    *,
    collection_id: uuid.UUID | None,
    unfiled: bool,
    since: datetime | None,
    until: datetime | None,
    source_url: str | None,
    order: Literal["source", "recent"],
    entry_ids: list[uuid.UUID] | None,
    title: str,
) -> tuple[str, list[CompiledPassage], str]:
    rows = await _load_reading_passages(
        db,
        user_id,
        collection_id=collection_id,
        unfiled=unfiled,
        since=since,
        until=until,
        source_url=source_url,
    )
    compiled = [
        CompiledPassage(
            id=str(row.id),
            passage=row.passage,
            heading=row.heading,
            source_url=row.source_url,
            page_title=row.page_title,
            dwell_ms=row.dwell_ms,
            last_seen_at=row.last_seen_at,
        )
        for row in rows
    ]
    ordered = order_passages(
        compiled,
        order=order,
        entry_ids=[str(item) for item in entry_ids] if entry_ids else None,
    )
    doc_title = title.strip() or "Reading compilation"
    return doc_title, ordered, render_markdown(ordered, title=doc_title)


@router.get(
    "/skills/reading/compile",
    response_model=ReadingCompileOut,
    summary="Preview a merged reading document",
)
async def compile_reading(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
    collection_id: Annotated[uuid.UUID | None, Query()] = None,
    unfiled: Annotated[bool, Query()] = False,
    since: Annotated[datetime | None, Query()] = None,
    until: Annotated[datetime | None, Query()] = None,
    source_url: Annotated[str | None, Query()] = None,
    order: Annotated[Literal["source", "recent"], Query()] = "source",
    entry_id: Annotated[list[uuid.UUID] | None, Query()] = None,
    title: Annotated[str, Query()] = "Reading compilation",
) -> ReadingCompileOut:
    doc_title, ordered, markdown = await _compile_reading_document(
        db,
        user_id,
        collection_id=collection_id,
        unfiled=unfiled,
        since=since,
        until=until,
        source_url=source_url,
        order=order,
        entry_ids=entry_id,
        title=title,
    )
    return ReadingCompileOut(
        title=doc_title,
        markdown=markdown,
        passages=[
            ReadingCompilePassageOut(
                id=uuid.UUID(item.id),
                passage=item.passage,
                heading=item.heading,
                source_url=item.source_url,
                page_title=item.page_title,
                dwell_ms=item.dwell_ms,
                last_seen_at=item.last_seen_at,
            )
            for item in ordered
        ],
    )


@router.get(
    "/skills/reading/export",
    summary="Download a compiled reading document",
    response_class=Response,
)
async def export_reading(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
    format: Annotated[Literal["md", "txt", "pdf"], Query()] = "md",
    collection_id: Annotated[uuid.UUID | None, Query()] = None,
    unfiled: Annotated[bool, Query()] = False,
    since: Annotated[datetime | None, Query()] = None,
    until: Annotated[datetime | None, Query()] = None,
    source_url: Annotated[str | None, Query()] = None,
    order: Annotated[Literal["source", "recent"], Query()] = "source",
    entry_id: Annotated[list[uuid.UUID] | None, Query()] = None,
    title: Annotated[str, Query()] = "Reading compilation",
) -> Response:
    doc_title, passages, markdown = await _compile_reading_document(
        db,
        user_id,
        collection_id=collection_id,
        unfiled=unfiled,
        since=since,
        until=until,
        source_url=source_url,
        order=order,
        entry_ids=entry_id,
        title=title,
    )
    filename = compilation_filename(doc_title, format)
    if format == "md":
        body = markdown.encode("utf-8")
        media = "text/markdown; charset=utf-8"
    elif format == "txt":
        body = render_plain_text(passages, title=doc_title).encode("utf-8")
        media = "text/plain; charset=utf-8"
    else:
        plain = render_plain_text(passages, title=doc_title)
        body = render_pdf(doc_title, plain)
        media = "application/pdf"

    return Response(
        content=body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch(
    "/skills/reading/{entry_id}",
    response_model=ReadingCompilerEntryOut,
    summary="Update a reading passage",
)
async def update_reading(
    entry_id: uuid.UUID,
    payload: ReadingCompilerEntryPatch,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReadingCompilerEntry:
    entry = await _owned_reading(db, entry_id, user_id)
    if "heading" in payload.model_fields_set:
        heading = (payload.heading or "").strip()
        entry.heading = heading or None
    if "collection_id" in payload.model_fields_set:
        if payload.collection_id is not None:
            await _owned_collection(db, payload.collection_id, user_id)
        entry.collection_id = payload.collection_id
    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete(
    "/skills/reading/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a reading passage",
)
async def delete_reading(
    entry_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    entry = await _owned_reading(db, entry_id, user_id)
    await db.delete(entry)
    await db.commit()


async def _owned_product(
    db: AsyncSession, entry_id: uuid.UUID, user_id: str
) -> ProductListing:
    result = await db.execute(
        select(ProductListing).where(
            ProductListing.id == entry_id, ProductListing.user_id == user_id
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product listing not found"
        )
    return entry


async def _load_products_for_compare(
    db: AsyncSession,
    user_id: str,
    entry_ids: list[uuid.UUID] | None,
) -> list[ProductListing]:
    query = select(ProductListing).where(ProductListing.user_id == user_id)
    if entry_ids:
        query = query.where(ProductListing.id.in_(entry_ids))
    query = query.order_by(ProductListing.last_seen_at.desc()).limit(12)
    result = await db.execute(query)
    rows = list(result.scalars().all())
    if entry_ids:
        by_id = {row.id: row for row in rows}
        missing = [item for item in entry_ids if item not in by_id]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more product listings were not found",
            )
        return [by_id[item] for item in entry_ids]
    return rows


def _product_comparison(rows: list[ProductListing]):
    return compare_products(
        [
            (
                row.id,
                row.name,
                row.source_url,
                row.page_title,
                row.price,
                row.specs or {},
            )
            for row in rows
        ]
    )


def _product_compare_out(comparison) -> ProductCompareOut:
    return ProductCompareOut(
        columns=[
            ProductCompareColumnOut(
                id=column.id,
                name=column.name,
                source_url=column.source_url,
                page_title=column.page_title,
                price=NormalizedPriceOut(
                    raw=column.price.raw,
                    amount=(
                        float(column.price.amount)
                        if column.price.amount is not None
                        else None
                    ),
                    currency=column.price.currency,
                    comparable=column.price.comparable,
                ),
                specs=column.specs,
            )
            for column in comparison.columns
        ],
        spec_keys=comparison.spec_keys,
        lowest_price_ids=comparison.lowest_price_ids,
        price_note=comparison.price_note,
    )


@router.get(
    "/skills/products/compare",
    response_model=ProductCompareOut,
    summary="Compare product listings side by side",
)
async def compare_product_listings(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
    entry_id: Annotated[list[uuid.UUID] | None, Query()] = None,
) -> ProductCompareOut:
    rows = await _load_products_for_compare(db, user_id, entry_id)
    return _product_compare_out(_product_comparison(rows))


@router.get(
    "/skills/products/export",
    summary="Download a product comparison spreadsheet",
    response_class=Response,
)
async def export_product_listings(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
    entry_id: Annotated[list[uuid.UUID] | None, Query()] = None,
) -> Response:
    rows = await _load_products_for_compare(db, user_id, entry_id)
    body = render_csv(_product_comparison(rows))
    return Response(
        content=body.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="product-comparison.csv"'
        },
    )


@router.patch(
    "/skills/products/{entry_id}",
    response_model=ProductListingOut,
    summary="Correct a product listing",
)
async def update_product(
    entry_id: uuid.UUID,
    payload: ProductListingPatch,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProductListing:
    entry = await _owned_product(db, entry_id, user_id)
    if "name" in payload.model_fields_set:
        name = (payload.name or "").strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Name cannot be empty",
            )
        entry.name = name
    if "price" in payload.model_fields_set:
        price = (payload.price or "").strip()
        entry.price = price or None
    if "specs" in payload.model_fields_set:
        entry.specs = payload.specs or {}
    if "collection_id" in payload.model_fields_set:
        if payload.collection_id is not None:
            await _owned_collection(db, payload.collection_id, user_id)
        entry.collection_id = payload.collection_id
    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete(
    "/skills/products/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete a product listing",
)
async def delete_product(
    entry_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    entry = await _owned_product(db, entry_id, user_id)
    await db.delete(entry)
    await db.commit()


async def _owned_job(
    db: AsyncSession, entry_id: uuid.UUID, user_id: str
) -> JobListing:
    result = await db.execute(
        select(JobListing).where(
            JobListing.id == entry_id, JobListing.user_id == user_id
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job listing not found"
        )
    return entry


@router.delete(
    "/skills/jobs/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete a job listing",
)
async def delete_job(
    entry_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    entry = await _owned_job(db, entry_id, user_id)
    await db.delete(entry)
    await db.commit()


async def _owned_contract_flag(
    db: AsyncSession, entry_id: uuid.UUID, user_id: str
) -> ContractFlag:
    result = await db.execute(
        select(ContractFlag).where(
            ContractFlag.id == entry_id, ContractFlag.user_id == user_id
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contract flag not found"
        )
    return entry


@router.delete(
    "/skills/contract-flags/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete a contract flag",
)
async def delete_contract_flag(
    entry_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    entry = await _owned_contract_flag(db, entry_id, user_id)
    await db.delete(entry)
    await db.commit()


async def _owned_contradiction(
    db: AsyncSession, entry_id: uuid.UUID, user_id: str
) -> Contradiction:
    result = await db.execute(
        select(Contradiction).where(
            Contradiction.id == entry_id, Contradiction.user_id == user_id
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contradiction not found"
        )
    return entry


@router.get(
    "/skills/contradictions",
    response_model=list[ContradictionOut],
    summary="List flagged contradiction pairs",
)
async def list_contradictions(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    include_dismissed: Annotated[bool, Query()] = False,
) -> list[Contradiction]:
    stmt = select(Contradiction).where(Contradiction.user_id == user_id)
    if not include_dismissed:
        stmt = stmt.where(Contradiction.dismissed.is_(False))
    stmt = (
        stmt.order_by(Contradiction.created_at.desc()).offset(offset).limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.patch(
    "/skills/contradictions/{entry_id}",
    response_model=ContradictionOut,
    summary="Dismiss or restore a contradiction",
)
async def update_contradiction(
    entry_id: uuid.UUID,
    payload: ContradictionPatch,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Contradiction:
    entry = await _owned_contradiction(db, entry_id, user_id)
    entry.dismissed = bool(payload.dismissed)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete(
    "/skills/contradictions/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a flagged contradiction",
)
async def delete_contradiction(
    entry_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    entry = await _owned_contradiction(db, entry_id, user_id)
    await db.delete(entry)
    await db.commit()


@router.get(
    "/collections", response_model=list[CollectionOut], summary="List collections"
)
async def list_collections(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Collection]:
    result = await db.execute(
        select(Collection)
        .where(Collection.user_id == user_id)
        .order_by(Collection.name)
    )
    return list(result.scalars().all())


@router.post(
    "/collections",
    response_model=CollectionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a collection",
)
async def create_collection(
    payload: CollectionIn,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Collection:
    name = payload.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Collection name cannot be empty",
        )

    existing = await db.execute(
        select(Collection).where(
            Collection.user_id == user_id, Collection.name == name
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A collection named {name!r} already exists",
        )

    collection = Collection(
        user_id=user_id, name=name, description=payload.description
    )
    db.add(collection)
    await db.commit()
    await db.refresh(collection)

    return collection


@router.delete(
    "/collections/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a collection",
)
async def delete_collection(
    collection_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(
        select(Collection).where(
            Collection.id == collection_id, Collection.user_id == user_id
        )
    )
    collection = result.scalar_one_or_none()
    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found"
        )

    # Entries keep their data and become unfiled, via ON DELETE SET NULL.
    await db.delete(collection)
    await db.commit()
