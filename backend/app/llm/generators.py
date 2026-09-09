"""文本内容生成器：画像 / 标题 / 卖点 / 详情 / 脚本 / 营销图方案。

所有方法签名一致：输入「商品上下文」dict，走统一 chat_json(schema_key)，输出与 Mock 同构。
"""
from __future__ import annotations

import json

from ..providers.ai_client import get_client
from ..prompts.loader import render
from ..schemas import schema_json_text, schema_text


def _product_context(product: dict, product_name: str = "", description: str = "") -> dict:
    """构造给下游 Prompt 的商品信息 JSON（合并视觉分析 + 用户输入 + 运营备注）。"""
    return {
        "analysis": product,
        "user_input": {"product_name": product_name, "description": description},
        "note": "以下字段中 source=visual 来自图片视觉推断，source=user 由用户文字提供，均视为可用事实依据。",
    }


def _run(schema_key: str, template: str, context: dict) -> dict:
    product_json = json.dumps(context, ensure_ascii=False, indent=1)
    text = render(template, {
        "product_json": product_json,
        "schema": schema_text(schema_key),
        "schema_sample": schema_json_text(schema_key),
    })
    return get_client().chat_json(schema_key, [{"role": "user", "content": text}])


def build_persona(product: dict, product_name: str = "", description: str = "") -> dict:
    return _run("persona", "persona.txt", _product_context(product, product_name, description))


def build_titles(product: dict, product_name: str = "", description: str = "") -> dict:
    return _run("titles", "titles.txt", _product_context(product, product_name, description))


def build_selling_points(product: dict, product_name: str = "", description: str = "") -> dict:
    return _run("selling_points", "selling_points.txt", _product_context(product, product_name, description))


def build_detail_sections(product: dict, product_name: str = "", description: str = "") -> dict:
    return _run("detail_sections", "detail_sections.txt", _product_context(product, product_name, description))


def build_video_script(product: dict, product_name: str = "", description: str = "") -> dict:
    return _run("video_script", "video_script.txt", _product_context(product, product_name, description))


def build_image_plans(product: dict, product_name: str = "", description: str = "") -> dict:
    return _run("image_plans", "image_plans.txt", _product_context(product, product_name, description))
