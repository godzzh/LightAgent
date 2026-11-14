"""知识库接口：数据集、文档、切片、检索测试。"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import Pagination, get_current_user, paginate
from app.core.exceptions import NotFoundError, ValidationFailedError
from app.core.response import EnvelopeRoute
from app.models.knowledge import Dataset, Document, DocumentSegment
from app.models.user import User
from app.models.model_provider import ModelConfig
from app.schemas.knowledge import (
    DatasetCreate,
    DatasetUpdate,
    RetrieveRequest,
    SegmentUpdate,
)
from app.services.knowledge.index import embed_texts, keyword_search, retrieve_segments
from app.services.knowledge.ingest import process_document, schedule_document
from app.services.knowledge.parser import SUPPORTED_EXT, extract_text
from app.services.knowledge.splitter import estimate_tokens, split_text
from app.services.workspace_service import get_user_workspace

router = APIRouter(route_class=EnvelopeRoute, prefix="/knowledge", tags=["知识库"])


def _dataset_out(d: Dataset) -> dict:
    return {
        "id": d.id,
        "name": d.name,
        "description": d.description,
        "embedding_model_id": d.embedding_model_id,
        "chunk_size": d.chunk_size,
        "chunk_overlap": d.chunk_overlap,
        "split_strategy": d.split_strategy,
        "separator": d.separator,
        "keep_heading": d.keep_heading,
        "clean_whitespace": d.clean_whitespace,
        "index_status": d.index_status,
        "doc_count": d.doc_count,
        "segment_count": d.segment_count,
        "created_at": d.created_at,
        "updated_at": d.updated_at,
    }


def _doc_out(d: Document) -> dict:
    return {
        "id": d.id,
        "dataset_id": d.dataset_id,
        "name": d.name,
        "filename": d.filename,
        "file_type": d.file_type,
        "file_size": d.file_size,
        "status": d.status,
        "progress": d.progress,
        "error": d.error,
        "char_count": d.char_count,
        "chunk_count": d.chunk_count,
        "created_at": d.created_at,
        "updated_at": d.updated_at,
    }


async def _get_dataset(db: AsyncSession, dataset_id: str) -> Dataset:
    ds = await db.get(Dataset, dataset_id)
    if not ds:
        raise NotFoundError("知识库不存在")
    return ds


# ------------------------------------------------------------------ datasets
@router.get("/datasets", summary="知识库列表")
async def list_datasets(
    keyword: str = "",
    p: Pagination = Depends(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await get_user_workspace(db, user)
    stmt = select(Dataset).where(Dataset.workspace_id == ws.id)
    count_stmt = select(func.count(Dataset.id)).where(Dataset.workspace_id == ws.id)
    if keyword:
        stmt = stmt.where(Dataset.name.contains(keyword))
        count_stmt = count_stmt.where(Dataset.name.contains(keyword))
    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(stmt.order_by(Dataset.updated_at.desc()).offset(p.offset).limit(p.page_size))
    ).scalars().all()
    return paginate([_dataset_out(d) for d in rows], int(total), p)


@router.post("/datasets", summary="创建知识库")
async def create_dataset(
    payload: DatasetCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = await get_user_workspace(db, user)
    if payload.embedding_model_id:
        cfg = await db.get(ModelConfig, payload.embedding_model_id)
        if not cfg or cfg.model_type != "embedding":
            raise ValidationFailedError("Embedding 模型不存在或类型不正确")
    ds = Dataset(
        workspace_id=ws.id,
        name=payload.name,
        description=payload.description,
        embedding_model_id=payload.embedding_model_id,
        chunk_size=payload.chunk_size,
        chunk_overlap=payload.chunk_overlap,
        split_strategy=payload.split_strategy,
        separator=payload.separator,
        keep_heading=payload.keep_heading,
        clean_whitespace=payload.clean_whitespace,
    )
    db.add(ds)
    await db.commit()
    await db.refresh(ds)
    return _dataset_out(ds)


@router.get("/datasets/{dataset_id}", summary="知识库详情")
async def get_dataset(
    dataset_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return _dataset_out(await _get_dataset(db, dataset_id))


@router.patch("/datasets/{dataset_id}", summary="更新知识库")
async def update_dataset(
    dataset_id: str,
    payload: DatasetUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ds = await _get_dataset(db, dataset_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(ds, k, v)
    await db.commit()
    await db.refresh(ds)
    return _dataset_out(ds)


@router.delete("/datasets/{dataset_id}", summary="删除知识库")
async def delete_dataset(
    dataset_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    ds = await _get_dataset(db, dataset_id)
    await db.delete(ds)
    await db.commit()
    return {"ok": True}


# ----------------------------------------------------------------- documents
@router.get("/datasets/{dataset_id}/documents", summary="文档列表")
async def list_documents(
    dataset_id: str,
    p: Pagination = Depends(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_dataset(db, dataset_id)
    total = (
        await db.execute(select(func.count(Document.id)).where(Document.dataset_id == dataset_id))
    ).scalar_one()
    rows = (
        await db.execute(
            select(Document)
            .where(Document.dataset_id == dataset_id)
            .order_by(Document.created_at.desc())
            .offset(p.offset)
            .limit(p.page_size)
        )
    ).scalars().all()
    return paginate([_doc_out(d) for d in rows], int(total), p)


@router.post("/datasets/{dataset_id}/documents", summary="上传文档")
async def upload_document(
    dataset_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ds = await _get_dataset(db, dataset_id)
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXT:
        raise ValidationFailedError(f"仅支持 {', '.join(sorted(SUPPORTED_EXT))} 格式")

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise ValidationFailedError(f"文件大小超过限制({settings.MAX_UPLOAD_MB}MB)")
    if not content:
        raise ValidationFailedError("文件内容为空")

    target_dir = settings.storage_path / "datasets" / dataset_id
    target_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    target = target_dir / stored_name
    target.write_bytes(content)

    doc = Document(
        dataset_id=ds.id,
        name=file.filename or stored_name,
        filename=stored_name,
        file_path=str(target),
        file_type=suffix.lstrip("."),
        file_size=len(content),
        status="waiting",
    )
    db.add(doc)
    ds.index_status = "indexing"
    await db.commit()
    await db.refresh(doc)

    scheduled = schedule_document(doc.id)
    if not scheduled:
        # 无法调度时同步处理，保证功能可用
        await process_document(doc.id)
        await db.refresh(doc)

    return {"document": _doc_out(doc), "queued": scheduled}


@router.delete("/documents/{document_id}", summary="删除文档")
async def delete_document(
    document_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    doc = await db.get(Document, document_id)
    if not doc:
        raise NotFoundError("文档不存在")
    try:
        Path(doc.file_path).unlink(missing_ok=True)
    except OSError:
        pass
    ds = await db.get(Dataset, doc.dataset_id)
    await db.delete(doc)
    await db.commit()
    if ds:
        ds.doc_count = max(0, ds.doc_count - 1)
        await db.commit()
    return {"ok": True}


@router.post("/documents/{document_id}/reindex", summary="重新索引")
async def reindex_document(
    document_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    doc = await db.get(Document, document_id)
    if not doc:
        raise NotFoundError("文档不存在")
    doc.status = "waiting"
    doc.progress = 0
    doc.error = ""
    await db.commit()
    scheduled = schedule_document(doc.id)
    if not scheduled:
        await process_document(doc.id)
    return {"ok": True, "queued": scheduled}


# ------------------------------------------------------------------ segments
@router.get("/documents/{document_id}/segments", summary="切片列表")
async def list_segments(
    document_id: str,
    p: Pagination = Depends(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total = (
        await db.execute(
            select(func.count(DocumentSegment.id)).where(DocumentSegment.document_id == document_id)
        )
    ).scalar_one()
    rows = (
        await db.execute(
            select(DocumentSegment)
            .where(DocumentSegment.document_id == document_id)
            .order_by(DocumentSegment.position.asc())
            .offset(p.offset)
            .limit(p.page_size)
        )
    ).scalars().all()
    return paginate(
        [
            {
                "id": s.id,
                "position": s.position,
                "content": s.content,
                "tokens": s.tokens,
                "heading": s.heading,
                "has_embedding": bool(s.embedding),
            }
            for s in rows
        ],
        int(total),
        p,
    )


@router.patch("/segments/{segment_id}", summary="修改切片内容（会重新向量化）")
async def update_segment(
    segment_id: str,
    payload: SegmentUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    seg = await db.get(DocumentSegment, segment_id)
    if not seg:
        raise NotFoundError("切片不存在")
    ds = await db.get(Dataset, seg.dataset_id)
    seg.content = payload.content
    seg.tokens = estimate_tokens(payload.content)
    try:
        vec = (await embed_texts(db, ds, [payload.content]))[0]
        seg.embedding = vec
    except Exception as exc:  # noqa: BLE001
        raise ValidationFailedError(f"重新向量化失败: {exc}") from exc
    await db.commit()
    return {"id": seg.id, "content": seg.content, "tokens": seg.tokens, "reindexed": True}


# ------------------------------------------------------------------ retrieve
@router.post("/retrieve", summary="检索测试")
async def retrieve(
    payload: RetrieveRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ids = payload.dataset_ids or []
    if not ids:
        ws = await get_user_workspace(db, user)
        ids = [
            d.id
            for d in (
                await db.execute(select(Dataset).where(Dataset.workspace_id == ws.id))
            ).scalars().all()
        ]
    if not ids:
        return {"results": [], "fallback": False}
    try:
        results = await retrieve_segments(db, ids, payload.query, payload.top_k, payload.threshold)
        return {"results": results, "fallback": False}
    except Exception as exc:  # noqa: BLE001
        # Embedding 不可用时降级为关键词检索
        results = await keyword_search(db, ids, payload.query, payload.top_k)
        return {"results": results, "fallback": True, "message": f"向量检索不可用，已降级为关键词检索: {exc}"}


@router.post("/datasets/{dataset_id}/preview-chunks", summary="切片预览（不入库）")
async def preview_chunks(
    dataset_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ds = await _get_dataset(db, dataset_id)
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXT:
        raise ValidationFailedError("不支持的文件格式")
    tmp_dir = settings.storage_path / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_file = tmp_dir / f"{uuid.uuid4().hex}{suffix}"
    tmp_file.write_bytes(await file.read())
    try:
        text = extract_text(tmp_file, suffix)
        chunks = split_text(
            text,
            strategy=ds.split_strategy,
            chunk_size=ds.chunk_size,
            chunk_overlap=ds.chunk_overlap,
            separator=ds.separator or "\n\n",
            keep_heading=ds.keep_heading,
            clean_whitespace=ds.clean_whitespace,
        )
        return {
            "total": len(chunks),
            "chunks": [
                {"position": c.position, "content": c.content, "tokens": estimate_tokens(c.content)}
                for c in chunks[:100]
            ],
        }
    finally:
        tmp_file.unlink(missing_ok=True)
