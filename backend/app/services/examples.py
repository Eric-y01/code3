"""内置示例商品目录：无 API Key 也能一键演示（Mock 链路）。

examples/images/<slug>.png   —— 示例商品原图
examples/reports/<slug>.json —— 专家预写的完整报告（各环节与真实模型输出同构）
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from .. import config

# slug -> 展示信息（与 images/、reports/ 下的文件名一一对应）
CATALOG: list[dict[str, str]] = [
    {
        "slug": "insulated_tumbler",
        "name": "智能保温杯",
        "tagline": "商务简约 · 可测水温 · 主打办公/通勤人群",
        "suggested_name": "智能保温杯",
        "description": "304不锈钢内胆，智能屏显水温，400ml，密封防漏。",
        # 演示模式下做「用户上传图片 → 最近示例模板」匹配用的关键词（小写）
        "keywords": ["保温杯", "保温", "水温", "水杯", "tumbler", "保温壶", "智能杯"],
    },
    {
        "slug": "ceramic_coffee_mug",
        "name": "北欧极简陶瓷咖啡杯",
        "tagline": "高颜值手冲/办公室马克杯",
        "suggested_name": "北欧极简陶瓷咖啡杯",
        "description": "哑光釉面，350ml，杯身人体工学握把，可进微波炉。",
        "keywords": ["咖啡杯", "马克杯", "咖啡", "陶瓷", "手冲", "mug", "茶杯", "釉"],
    },
    {
        "slug": "wireless_headphones",
        "name": "头戴式降噪耳机",
        "tagline": "主动降噪 · 长续航 · 通勤学习党",
        "suggested_name": "头戴式降噪耳机",
        "description": "混合主动降噪，40小时续航，蛋白皮耳罩，蓝牙5.3。",
        "keywords": ["耳机", "头戴", "降噪", "耳麦", "headphone", "耳罩", "hifi", "hi-fi"],
    },
]


def match_slug(text: str) -> Optional[str]:
    """用「商品名 + 补充说明 + 文件名」在示例模板里找最接近的一个（Mock 上传演示用）。

    命中任一示例的专用关键词（如 保温杯/咖啡杯/耳机）即算匹配；
    完全无信号返回 None，由上层给出友好提示。
    """
    t = (text or "").lower().strip()
    if not t:
        return None
    best_slug, best_score = None, 0
    for item in CATALOG:
        score = 0
        name, desc = item.get("name", ""), item.get("description", "")
        if name and name.lower() in t:
            score += 6
        if desc and desc.lower() in t:
            score += 4
        for kw in item.get("keywords", []):
            if kw in t:
                score += 2
        if score > best_score:
            best_slug, best_score = item["slug"], score
    return best_slug if best_score >= 2 else None


def seed_for_upload(product_name: str, description: str, filename_stem: str = "") -> Optional[dict]:
    """Mock 上传演示：匹配最近的示例模板并重命名到用户商品。

    返回预写报告 dict（不含 meta）；无匹配时返回 None。
    """
    text = " ".join(filter(None, [product_name, description, filename_stem]))
    slug = match_slug(text)
    if not slug:
        return None
    seed = load_seed(slug) or {}
    if not seed:
        return None
    old_name = (seed.get("product_analysis") or {}).get("product_name") or ""
    new_name = (product_name or "").strip()
    if new_name and new_name != old_name:
        seed = _rename_product(seed, old_name, new_name)
    seed.setdefault("_demo_source", slug)
    return seed


def _rename_product(node: Any, old: str, new: str) -> Any:
    """把预写文案中出现的内置示例商品名替换为用户填写的商品名（递归）。"""
    if isinstance(node, dict):
        return {k: _rename_product(v, old, new) for k, v in node.items()}
    if isinstance(node, list):
        return [_rename_product(v, old, new) for v in node]
    if isinstance(node, str) and old:
        return node.replace(old, new)
    return node


def image_path_for(slug: str) -> Path:
    return config.EXAMPLES_IMAGES_DIR / f"{slug}.png"


def image_url_for(slug: str) -> str:
    return f"/examples/images/{slug}.png"


def report_path_for(slug: str) -> Path:
    return config.EXAMPLES_REPORTS_DIR / f"{slug}.json"


def meta_by_slug(slug: str) -> Optional[dict[str, str]]:
    for item in CATALOG:
        if item["slug"] == slug:
            return item
    return None


def exists(slug: str) -> bool:
    return image_path_for(slug).exists() and report_path_for(slug).exists()


def load_seed(slug: str) -> Optional[dict[str, Any]]:
    """加载预写报告片段（Mock 引擎的种子数据）。"""
    try:
        with report_path_for(slug).open(encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def list_examples() -> list[dict]:
    out = []
    for item in CATALOG:
        if not exists(item["slug"]):
            continue
        out.append({
            "slug": item["slug"],
            "name": item["name"],
            "tagline": item["tagline"],
            "suggested_name": item["suggested_name"],
            "description": item["description"],
            "image_url": image_url_for(item["slug"]),
        })
    return out
