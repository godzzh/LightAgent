"""文档文本提取。"""
from __future__ import annotations

import re
from pathlib import Path

from app.core.exceptions import ValidationFailedError

SUPPORTED_EXT = {".pdf", ".docx", ".txt", ".md", ".markdown", ".html", ".htm"}
MAX_FILE_SIZE = 50 * 1024 * 1024


def _clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\u00a0]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text(path: str | Path, ext: str | None = None) -> str:
    p = Path(path)
    suffix = (ext or p.suffix).lower()
    if suffix not in SUPPORTED_EXT:
        raise ValidationFailedError(f"不支持的文件类型: {suffix}")

    if suffix == ".pdf":
        from pypdf import PdfReader

        try:
            reader = PdfReader(str(p))
            pages = [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:  # noqa: BLE001
            raise ValidationFailedError(f"PDF 解析失败: {exc}") from exc
        text = "\n\n".join(pages)
    elif suffix == ".docx":
        import docx

        try:
            doc = docx.Document(str(p))
        except Exception as exc:  # noqa: BLE001
            raise ValidationFailedError(f"DOCX 解析失败: {exc}") from exc
        parts: list[str] = [para.text for para in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join(cell.text.strip() for cell in row.cells))
        text = "\n".join(parts)
    elif suffix in (".html", ".htm"):
        from bs4 import BeautifulSoup

        html = p.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text("\n")
    else:  # txt / md
        text = p.read_text(encoding="utf-8", errors="ignore")

    text = _clean(text)
    if not text:
        raise ValidationFailedError("文档内容为空或无法提取文本（可能是扫描件）")
    return text
