"""知识库文本处理测试：解析、切片策略、Token 估算。"""
from __future__ import annotations

from pathlib import Path

from app.services.knowledge.parser import extract_text
from app.services.knowledge.splitter import estimate_tokens, split_text

SAMPLE = """# 产品手册

## 退换货政策
自签收之日起 7 天内可无理由退货，商品需保持完好。

## 支付方式
支持微信支付、支付宝与企业转账。

## 发货时间
工作日 16:00 前下单当日发出，其余次日发出。
"""


def test_extract_markdown(tmp_path: Path):
    p = tmp_path / "manual.md"
    p.write_text(SAMPLE, encoding="utf-8")
    text = extract_text(p)
    assert "退换货政策" in text
    assert "\r" not in text


def test_fixed_split_respects_size():
    chunks = split_text(SAMPLE, strategy="fixed", chunk_size=80, chunk_overlap=10)
    assert len(chunks) >= 2
    assert all(len(c.content) <= 90 for c in chunks)


def test_heading_split_keeps_heading():
    chunks = split_text(SAMPLE, strategy="heading", chunk_size=200, chunk_overlap=0, keep_heading=True)
    assert any("退换货政策" in c.content for c in chunks)
    assert any(c.heading for c in chunks)


def test_paragraph_split():
    chunks = split_text(SAMPLE, strategy="paragraph", chunk_size=40, chunk_overlap=0)
    assert len(chunks) >= 2


def test_empty_text_returns_no_chunks():
    assert split_text("   ", strategy="fixed") == []


def test_estimate_tokens_positive():
    assert estimate_tokens("你好 world") > 0
