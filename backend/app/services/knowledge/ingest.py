"""文档入库流水线：解析 → 清洗 → 切片 → 向量化 → 落库。"""
from __future__ import annotations

import asyncio
from typing import Optional

from loguru import logger
from sqlalchemy import delete, func, select

from app.core.database import SessionLocal
from app.models.knowledge import Dataset, Document, DocumentSegment
from app.services.knowledge.index import embed_texts
from app.services.knowledge.parser import extract_text
from app.services.knowledge.splitter import estimate_tokens, split_text

_running: set[str] = set()


async def process_document(document_id: str) -> None:
    """完整处理一个文档。使用独立 Session，可安全运行在后台任务中。"""
    async with SessionLocal() as db:
        doc: Optional[Document] = await db.get(Document, document_id)
        if not doc:
            logger.warning(f"document {document_id} not found")
            return
        dataset: Optional[Dataset] = await db.get(Dataset, doc.dataset_id)
        if not dataset:
            return

        async def set_status(status: str, progress: int, error: str = "") -> None:
            doc.status = status
            doc.progress = progress
            if error:
                doc.error = error[:2000]
            await db.commit()

        try:
            await set_status("parsing", 10)
            text = await asyncio.to_thread(extract_text, doc.file_path, f".{doc.file_type}")
            doc.char_count = len(text)

            await set_status("splitting", 30)
            chunks = split_text(
                text,
                strategy=dataset.split_strategy,
                chunk_size=dataset.chunk_size,
                chunk_overlap=dataset.chunk_overlap,
                separator=dataset.separator or "\n\n",
                keep_heading=dataset.keep_heading,
                clean_whitespace=dataset.clean_whitespace,
            )
            if not chunks:
                raise ValueError("切片结果为空，请调整切片参数")

            # 清理旧切片，保证重新索引幂等
            await db.execute(delete(DocumentSegment).where(DocumentSegment.document_id == doc.id))
            segments: list[DocumentSegment] = []
            for c in chunks:
                seg = DocumentSegment(
                    dataset_id=dataset.id,
                    document_id=doc.id,
                    position=c.position,
                    content=c.content,
                    tokens=estimate_tokens(c.content),
                    heading=c.heading,
                    extra={"strategy": dataset.split_strategy},
                )
                db.add(seg)
                segments.append(seg)
            doc.chunk_count = len(segments)
            await set_status("indexing", 55)
            await db.commit()

            # 向量化（按批，边算边落库，避免长事务）
            vectors: list[list[float]] = []
            batch_size = 32
            try:
                for i in range(0, len(segments), batch_size):
                    part = [s.content for s in segments[i : i + batch_size]]
                    vectors.extend(await embed_texts(db, dataset, part))
                    progress = 55 + int(40 * min(1.0, (i + batch_size) / max(1, len(segments))))
                    doc.progress = progress
                    await db.commit()
            except Exception as exc:  # noqa: BLE001
                # 向量化失败：保留切片，标记失败，允许重试
                doc.chunk_count = len(segments)
                await db.commit()
                raise ValueError(f"向量化失败: {exc}") from exc

            for seg, vec in zip(segments, vectors):
                seg.embedding = vec
            await db.commit()

            # 更新统计
            seg_count = (
                await db.execute(
                    select(func.count(DocumentSegment.id)).where(DocumentSegment.dataset_id == dataset.id)
                )
            ).scalar_one()
            doc_count = (
                await db.execute(
                    select(func.count(Document.id)).where(
                        Document.dataset_id == dataset.id, Document.status == "completed"
                    )
                )
            ).scalar_one()
            dataset.segment_count = int(seg_count)
            dataset.doc_count = int(doc_count)
            dataset.index_status = "ready"
            doc.status = "completed"
            doc.progress = 100
            doc.error = ""
            await db.commit()
            logger.info(f"document {doc.id} indexed: {len(segments)} chunks")
        except Exception as exc:  # noqa: BLE001
            logger.exception(f"document {document_id} failed")
            doc.status = "failed"
            doc.error = str(exc)[:2000]
            dataset.index_status = "failed" if dataset.index_status != "ready" else "ready"
            await db.commit()
        finally:
            _running.discard(document_id)


def schedule_document(document_id: str) -> bool:
    """在当前事件循环内调度后台处理（Celery 未启用时的轻量方案）。"""
    if document_id in _running:
        return False
    _running.add(document_id)
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(process_document(document_id))
        return True
    except RuntimeError:
        _running.discard(document_id)
        return False
