"""视觉理解：把「原图 + 可选用户事实信息」交给多模态模型，产出结构化商品分析。"""
from __future__ import annotations

import base64
from pathlib import Path

from ..providers.ai_client import get_client
from ..prompts.loader import render
from ..schemas import schema_json_text, schema_text


def _image_data_url(image_path: str | Path) -> str:
    data = Path(image_path).read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    ext = Path(image_path).suffix.lower().lstrip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext, "jpeg")
    return f"data:image/{mime};base64,{b64}"


def analyze_product(image_path: str | Path, product_name: str = "", description: str = "") -> dict:
    """返回规整后的商品分析 dict（含 source 语义：visual 推断 / user 提供）。"""
    text = render("product_analysis.txt", {
        "product_name": product_name or "（未提供）",
        "description": description or "（未提供）",
        "schema": schema_text("product_analysis"),
        "schema_sample": schema_json_text("product_analysis"),
    })
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": text},
            {"type": "image_url", "image_url": {"url": _image_data_url(image_path), "detail": "high"}},
        ],
    }]
    return get_client().chat_json("product_analysis", messages)
