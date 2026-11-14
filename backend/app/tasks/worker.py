"""轻量后台工作进程：轮询待处理文档并完成解析 / 切片 / 向量化。

不引入 Celery 即可满足单机部署；有多实例需求时可替换为 Celery 任务，
业务函数 process_document 保持不变。
"""
from __future__ import annotations

import asyncio
import signal

from loguru import logger
from sqlalchemy import select

from app.core.database import SessionLocal, engine, init_db
from app.core.logging import setup_logging
from app.models.knowledge import Document
from app.services.knowledge.ingest import process_document

_running = True
POLL_INTERVAL = 3.0


def _stop(*_: object) -> None:
    global _running
    _running = False
    logger.info("worker 收到停止信号，等待当前任务结束…")


async def fetch_pending(limit: int = 3) -> list[str]:
    async with SessionLocal() as db:
        rows = (
            await db.execute(
                select(Document.id)
                .where(Document.status == "waiting")
                .order_by(Document.created_at.asc())
                .limit(limit)
            )
        ).scalars().all()
        return list(rows)


async def main() -> None:
    setup_logging()
    await init_db()
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    logger.info("文档处理 worker 已启动")
    while _running:
        try:
            ids = await fetch_pending()
            if ids:
                await asyncio.gather(*(process_document(i) for i in ids), return_exceptions=True)
                continue
        except Exception as exc:  # noqa: BLE001
            logger.exception(f"worker 循环异常: {exc}")
        await asyncio.sleep(POLL_INTERVAL)
    await engine.dispose()
    logger.info("worker 已退出")


if __name__ == "__main__":
    asyncio.run(main())
