"""向量化与检索。

说明：向量统一持久化在 document_segments.embedding（JSON 浮点数组），
保证 SQLite / PostgreSQL 行为一致；PostgreSQL 部署（docker-compose 已启用 pgvector）
可直接在迁移后用 pgvector 的 `<=>` 运算符替换 `_cosine` 全表计算以获得 HNSW 加速，
接口保持不变，业务层无需改动。
"""
from __future__ import annotations

import math
from typing import Any, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.knowledge import Dataset, Document, DocumentSegment
from app.models.model_provider import ModelConfig
from app.providers.registry import build_provider_for_config, get_model_config


async def resolve_embedding_model(db: AsyncSession, dataset: Dataset) -> ModelConfig:
    if dataset.embedding_model_id:
        cfg = await db.get(ModelConfig, dataset.embedding_model_id)
        if cfg:
            return cfg
    # 回退：任意可用的 embedding 模型
    stmt = (
        select(ModelConfig)
        .where(ModelConfig.model_type == "embedding", ModelConfig.enabled.is_(True))
        .order_by(ModelConfig.is_default.desc())
        .limit(1)
    )
    cfg = (await db.execute(stmt)).scalar_one_or_none()
    if not cfg:
        raise AppError("尚未配置 Embedding 模型，请先到「模型管理」添加 embedding 类型模型")
    return cfg


async def embed_texts(db: AsyncSession, dataset: Dataset, texts: Sequence[str]) -> list[list[float]]:
    cfg = await resolve_embedding_model(db, dataset)
    provider = await build_provider_for_config(db, cfg)
    vectors: list[list[float]] = []
    batch = 16
    for i in range(0, len(texts), batch):
        vectors.extend(await provider.embed(cfg.model_name, list(texts[i : i + batch])))
    return vectors


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


async def retrieve_segments(
    db: AsyncSession,
    dataset_ids: list[str],
    query: str,
    top_k: int = 4,
    threshold: float = 0.3,
    *,
    keyword: Optional[str] = None,
) -> list[dict[str, Any]]:
    """向量检索（附带轻量关键词加权），返回带相似度分数的片段。"""
    if not dataset_ids or not query.strip():
        return []

    datasets = (await db.execute(select(Dataset).where(Dataset.id.in_(dataset_ids)))).scalars().all()
    if not datasets:
        return []

    query_vec = (await embed_texts(db, datasets[0], [query]))[0]

    stmt = (
        select(DocumentSegment, Document.name)
        .join(Document, Document.id == DocumentSegment.document_id, isouter=True)
        .where(
            DocumentSegment.dataset_id.in_(dataset_ids),
            DocumentSegment.embedding.is_not(None),
        )
        .limit(5000)
    )
    rows = (await db.execute(stmt)).all()

    kw = (keyword or query).strip().lower()
    scored: list[dict[str, Any]] = []
    for seg, doc_name in rows:
        emb = seg.embedding or []
        sim = _cosine(query_vec, emb)
        # 混合检索：关键词命中做小幅加权
        bonus = 0.0
        if kw and len(kw) <= 60:
            terms = [t for t in kw.replace("，", " ").replace(",", " ").split() if t]
            if terms:
                hit = sum(1 for t in terms if t in (seg.content or "").lower())
                bonus = min(0.05, 0.02 * hit)
        score = round(sim + bonus, 4)
        if score < threshold:
            continue
        scored.append(
            {
                "segment_id": seg.id,
                "document_id": seg.document_id,
                "document_name": doc_name or "",
                "content": seg.content,
                "score": score,
                "position": seg.position,
                "heading": seg.heading or "",
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[: max(1, top_k)]


async def keyword_search(
    db: AsyncSession, dataset_ids: list[str], query: str, top_k: int = 5
) -> list[dict[str, Any]]:
    """简单关键词检索（无 Embedding 模型时的降级能力）。"""
    stmt = (
        select(DocumentSegment, Document.name)
        .join(Document, Document.id == DocumentSegment.document_id, isouter=True)
        .where(DocumentSegment.dataset_id.in_(dataset_ids))
        .limit(2000)
    )
    rows = (await db.execute(stmt)).all()
    q = query.strip().lower()
    hits = [
        {
            "segment_id": seg.id,
            "document_id": seg.document_id,
            "document_name": doc_name or "",
            "content": seg.content,
            "score": 1.0 if q in (seg.content or "").lower() else 0.0,
            "position": seg.position,
            "heading": seg.heading or "",
        }
        for seg, doc_name in rows
    ]
    hits = [h for h in hits if h["score"] > 0]
    return hits[:top_k]
