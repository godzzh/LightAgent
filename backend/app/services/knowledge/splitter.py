"""文本切片策略。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class Chunk:
    content: str
    heading: str = ""
    position: int = 0


def _split_fixed(text: str, size: int, overlap: int) -> list[str]:
    size = max(50, size)
    overlap = max(0, min(overlap, size // 2))
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def _split_by_separator(text: str, separator: str, size: int, overlap: int) -> list[str]:
    parts = [p.strip() for p in text.split(separator) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for part in parts:
        if len(part) > size:
            if buf:
                chunks.append(buf)
                buf = ""
            chunks.extend(_split_fixed(part, size, overlap))
            continue
        if len(buf) + len(part) + len(separator) <= size:
            buf = f"{buf}{separator}{part}" if buf else part
        else:
            if buf:
                chunks.append(buf)
            buf = part
    if buf:
        chunks.append(buf)
    return chunks


def _split_by_heading(text: str, size: int, overlap: int) -> list[tuple[str, str]]:
    """按 Markdown 标题/中文编号标题切分，返回 (标题, 内容) 列表。"""
    pattern = re.compile(r"^(#{1,6}\s+.+|第[一二三四五六七八九十百]+[章节]\s*.*|\d+(\.\d+)*\s+\S.*)$", re.M)
    matches = list(pattern.finditer(text))
    result: list[tuple[str, str]] = []
    if not matches:
        return [("", t) for t in _split_fixed(text, size, overlap)]
    if matches[0].start() > 0:
        head = text[: matches[0].start()].strip()
        if head:
            result.append(("", head))
    for i, m in enumerate(matches):
        heading = m.group(0).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if not body:
            continue
        if len(body) <= size:
            result.append((heading, body))
        else:
            for piece in _split_fixed(body, size, overlap):
                result.append((heading, piece))
    return result


def split_text(
    text: str,
    *,
    strategy: str = "fixed",
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    separator: str = "\n\n",
    keep_heading: bool = True,
    clean_whitespace: bool = True,
) -> list[Chunk]:
    """按策略切片。strategy: fixed / paragraph / heading / separator"""
    if clean_whitespace:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    if not text:
        return []

    chunks: list[Chunk] = []
    pos = 0
    if strategy == "heading":
        for heading, body in _split_by_heading(text, chunk_size, chunk_overlap):
            content = f"{heading}\n{body}" if (keep_heading and heading) else body
            chunks.append(Chunk(content=content.strip(), heading=heading if keep_heading else "", position=pos))
            pos += 1
    elif strategy == "paragraph":
        for body in _split_by_separator(text, "\n\n", chunk_size, chunk_overlap):
            chunks.append(Chunk(content=body, position=pos))
            pos += 1
    elif strategy == "separator":
        for body in _split_by_separator(text, separator or "\n\n", chunk_size, chunk_overlap):
            chunks.append(Chunk(content=body, position=pos))
            pos += 1
    else:  # fixed
        for body in _split_fixed(text, chunk_size, chunk_overlap):
            chunks.append(Chunk(content=body, position=pos))
            pos += 1

    # 过滤过短片段
    return [c for c in chunks if len(c.content.strip()) >= 2]


def estimate_tokens(text: str) -> int:
    """粗略 Token 估算：中文按 1 字 ≈ 1 token，英文按 4 字符 ≈ 1 token。"""
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    other = len(text) - cjk
    return int(cjk + other / 4) + 1
