"""Batch PDF form filler: profiles, uploads, match preview, and zip fill."""

from __future__ import annotations

import io
import uuid
import zipfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import CurrentUserId
from app.models.form_filler import FormDocument, FormProfile
from app.schemas.form_filler import (
    DocumentMatchOut,
    FieldMatchOut,
    FillRequest,
    FormDocumentOut,
    FormProfileIn,
    FormProfileOut,
    FormProfilePatch,
    MatchRequest,
)
from app.services.auto_attach_index import index_form_document
from app.services.form_match import FieldMatch, match_document_fields
from app.services.form_pdf import (
    PASSWORD_PROTECTED,
    extract_fields,
    fill_fields,
    looks_like_pdf,
    normalize_pdf_bytes,
    resolve_stored_path,
    storage_root,
)

router = APIRouter(prefix="/api", tags=["form-filler"])

SAFE_NAME_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._- ")


def _safe_filename(name: str) -> str:
    cleaned = "".join(ch if ch in SAFE_NAME_CHARS else "_" for ch in Path(name).name)
    cleaned = cleaned.strip(" ._") or "document.pdf"
    if not cleaned.lower().endswith(".pdf"):
        cleaned = f"{cleaned}.pdf"
    return cleaned[:180]


def _stored_relpath(user_id: str, doc_id: uuid.UUID) -> str:
    return f"{user_id}/{doc_id}.pdf"


async def _owned_profile(
    db: AsyncSession, profile_id: uuid.UUID, user_id: str
) -> FormProfile:
    result = await db.execute(
        select(FormProfile).where(
            FormProfile.id == profile_id, FormProfile.user_id == user_id
        )
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    return profile


async def _owned_document(
    db: AsyncSession, document_id: uuid.UUID, user_id: str
) -> FormDocument:
    result = await db.execute(
        select(FormDocument).where(
            FormDocument.id == document_id, FormDocument.user_id == user_id
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    return document


def _read_pdf(document: FormDocument) -> bytes:
    path = resolve_stored_path(settings.form_storage_dir, document.storage_path)
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=f"Stored PDF for {document.filename!r} is missing",
        )
    return path.read_bytes()


def _match_out(document: FormDocument, profile_values: dict) -> DocumentMatchOut:
    matches = match_document_fields(document.fields, profile_values)
    return DocumentMatchOut(
        document_id=document.id,
        filename=document.filename,
        matches=[FieldMatchOut.model_validate(match, from_attributes=True) for match in matches],
        auto_filled=sum(1 for match in matches if not match.needs_manual),
        needs_manual=sum(1 for match in matches if match.needs_manual),
    )


def _fill_values(
    matches: list[FieldMatch], overrides: dict[str, str]
) -> dict[str, str]:
    values: dict[str, str] = {}
    for match in matches:
        if match.value:
            values[match.field_name] = match.value
    values.update(overrides)
    return {key: value for key, value in values.items() if value != ""}


@router.get(
    "/skills/form-filler/profiles",
    response_model=list[FormProfileOut],
    summary="List form-fill profiles",
)
async def list_profiles(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[FormProfile]:
    result = await db.execute(
        select(FormProfile)
        .where(FormProfile.user_id == user_id)
        .order_by(FormProfile.name)
    )
    return list(result.scalars().all())


@router.post(
    "/skills/form-filler/profiles",
    response_model=FormProfileOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a form-fill profile",
)
async def create_profile(
    payload: FormProfileIn,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FormProfile:
    name = payload.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Profile name cannot be empty",
        )
    profile = FormProfile(user_id=user_id, name=name, values=payload.values or {})
    db.add(profile)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A profile named {name!r} already exists",
        ) from None
    await db.refresh(profile)
    return profile


@router.patch(
    "/skills/form-filler/profiles/{profile_id}",
    response_model=FormProfileOut,
    summary="Update a form-fill profile",
)
async def update_profile(
    profile_id: uuid.UUID,
    payload: FormProfilePatch,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FormProfile:
    profile = await _owned_profile(db, profile_id, user_id)
    if "name" in payload.model_fields_set:
        name = (payload.name or "").strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Profile name cannot be empty",
            )
        profile.name = name
    if "values" in payload.model_fields_set:
        profile.values = payload.values or {}
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A profile with that name already exists",
        ) from None
    await db.refresh(profile)
    return profile


@router.delete(
    "/skills/form-filler/profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete a form-fill profile",
)
async def delete_profile(
    profile_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    profile = await _owned_profile(db, profile_id, user_id)
    await db.delete(profile)
    await db.commit()


@router.get(
    "/skills/form-filler/documents",
    response_model=list[FormDocumentOut],
    summary="List uploaded fillable PDFs",
)
async def list_documents(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[FormDocument]:
    result = await db.execute(
        select(FormDocument)
        .where(FormDocument.user_id == user_id)
        .order_by(FormDocument.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


@router.post(
    "/skills/form-filler/documents",
    response_model=FormDocumentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a fillable PDF (bytes over HTTP, not the extension bus)",
)
async def upload_document(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    source_url: Annotated[str, Form()] = "",
) -> FormDocument:
    filename = _safe_filename(file.filename or "document.pdf")
    payload = normalize_pdf_bytes(await file.read())
    if len(payload) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty",
        )
    if len(payload) > settings.form_upload_max_bytes:
        raise HTTPException(
            status_code=413,
            detail="PDF is larger than the 20 MB upload limit",
        )
    if not looks_like_pdf(payload):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File is not a PDF",
        )

    try:
        fields = extract_fields(payload)
    except ValueError as exc:
        if str(exc) == PASSWORD_PROTECTED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="This PDF is password-protected. Unlock it, then upload again.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not read this PDF",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not read this PDF",
        ) from exc

    doc_id = uuid.uuid4()
    relative = _stored_relpath(user_id, doc_id)
    dest = storage_root(settings.form_storage_dir) / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(payload)

    document = FormDocument(
        id=doc_id,
        user_id=user_id,
        filename=filename,
        storage_path=relative,
        source_url=(source_url or "").strip(),
        fields=fields,
        field_count=len(fields),
    )
    db.add(document)
    await index_form_document(
        db,
        user_id=user_id,
        filename=filename,
        source_url=(source_url or "").strip(),
        storage_path=relative,
    )
    await db.commit()
    await db.refresh(document)
    return document


@router.delete(
    "/skills/form-filler/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete an uploaded PDF",
)
async def delete_document(
    document_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    document = await _owned_document(db, document_id, user_id)
    path = resolve_stored_path(settings.form_storage_dir, document.storage_path)
    await db.delete(document)
    await db.commit()
    if path.is_file():
        path.unlink()


@router.post(
    "/skills/form-filler/match",
    response_model=list[DocumentMatchOut],
    summary="Preview profile-to-field matches; low confidence stays blank",
)
async def match_documents(
    payload: MatchRequest,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DocumentMatchOut]:
    if not payload.document_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Select at least one document",
        )
    profile = await _owned_profile(db, payload.profile_id, user_id)
    previews: list[DocumentMatchOut] = []
    for document_id in payload.document_ids:
        document = await _owned_document(db, document_id, user_id)
        previews.append(_match_out(document, profile.values))
    return previews


@router.post(
    "/skills/form-filler/fill",
    summary="Fill selected PDFs and download a zip",
    response_class=Response,
)
async def fill_documents(
    payload: FillRequest,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    if not payload.document_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Select at least one document",
        )
    profile = await _owned_profile(db, payload.profile_id, user_id)
    override_by_doc = {
        item.document_id: {row.field_name: row.value for row in item.overrides}
        for item in payload.documents
    }

    archive = io.BytesIO()
    used_names: dict[str, int] = {}
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        for document_id in payload.document_ids:
            document = await _owned_document(db, document_id, user_id)
            matches = match_document_fields(document.fields, profile.values)
            values = _fill_values(matches, override_by_doc.get(document.id, {}))
            filled = fill_fields(_read_pdf(document), values)
            zip_name = _safe_filename(document.filename)
            count = used_names.get(zip_name, 0)
            used_names[zip_name] = count + 1
            if count:
                stem = zip_name[:-4]
                zip_name = f"{stem}-{count + 1}.pdf"
            zipped.writestr(zip_name, filled)

    return Response(
        content=archive.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="filled-forms.zip"'},
    )
