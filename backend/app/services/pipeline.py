"""核心流水线：把一次任务（真实图片 / 内置示例）跑成完整报告。

步骤编排（analysis 与 extraction 并行，其余顺序依赖商品分析结果）：
analyze_product → build_persona → generate_content(标题/卖点/详情) → script → image_plan → assemble
Mock 模式下整条流水线仍完整走一遍（步骤由内置种子数据瞬时喂出），
保证「进度反馈 + 报告展示」的演示一致性；同图缓存命中则跳过重算。
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .. import config, db, task_state
from ..llm import generators
from ..providers import ai_client
from ..providers.mock import MockProvider
from ..schemas import merge_and_normalize
from ..segmentation import service as segment
from ..vision import analyzer
from .examples import load_seed, seed_for_upload

_MOCK_LOCK = threading.Lock()  # 演示模式下同一时间只跑一个任务，避免共享种子互相污染


def _fmt_time() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _step(task_id: str, key: str, status: str, progress: int) -> None:
    task_state.step_status(task_id, key, status, progress)


def run_analysis_task(
    task_id: str,
    image_path: str | Path,
    image_url: str,
    image_hash: str,
    product_name: str = "",
    description: str = "",
    is_example: bool = False,
    example_slug: str | None = None,
) -> None:
    """后台线程入口：负责把任务从 running 推进到 done / error。"""
    mock_mode = config.IS_MOCK or (is_example and ai_client.active_name() == "mock")
    lock = _MOCK_LOCK if mock_mode else _null_lock()
    with lock:
        _execute(task_id, image_path, image_url, image_hash,
                 product_name, description, mock_mode, example_slug)


def _null_lock() -> Any:
    class _NL:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    return _NL()


def _execute(task_id: str, image_path: str | Path, image_url: str, image_hash: str,
             product_name: str, description: str, mock_mode: bool, example_slug: str | None) -> None:
    db.update_task(task_id, status="running")
    demo_source: str | None = example_slug  # 上传场景匹配到的演示模板
    try:
        # ---------- Mock 种子注入 ----------
        client = ai_client.get_client()
        seed: dict | None = None
        if mock_mode:
            if example_slug:
                seed = load_seed(example_slug) or {}
            else:
                # 上传图片演示：按商品名/描述/文件名匹配最近的示例模板，并重命名到用户商品
                stem = Path(image_path).stem
                seed = seed_for_upload(product_name, description, stem)
                if seed:
                    demo_source = seed.pop("_demo_source", None) or None
                else:
                    raise RuntimeError(
                        "当前为 Mock 演示模式（未配置 API Key），且未识别到匹配的商品模板。"
                        "请在商品名称中填写类型关键词（如 保温杯 / 咖啡杯 / 耳机）后重试，"
                        "或配置 OPENAI_API_KEY 分析真实图片。"
                    )
            if seed and isinstance(client, MockProvider):
                client.set_seed(seed)

        # ---------- 1. 视觉分析（并行：提取主体） ----------
        _step(task_id, "start", "done", 2)
        _step(task_id, "analyze_product", "running", 10)
        analysis_result: dict = {}

        def do_analysis() -> None:
            # 后台线程的异常不会自动传播到主线程，必须显式捕获后回抛，
            # 否则视觉失败会静默吞掉、继续用空 product 跑出残缺报告。
            try:
                analysis_result["data"] = analyzer.analyze_product(image_path, product_name, description)
            except Exception as e:  # noqa: BLE001
                analysis_result["error"] = e

        t1 = threading.Thread(target=do_analysis, daemon=True)
        t1.start()

        # ---------- 2. 主体抠图（独立展示链路） ----------
        _step(task_id, "extract_subject", "running", 12)
        cutout_url: str | None = None
        cutout_note: str | None = None
        if segment.available():
            try:
                cutout_url = segment.extract_subject(image_path, image_hash)
            except Exception as e:  # noqa: BLE001
                cutout_url = None
                cutout_note = f"抠图失败：{str(e)[:200]}"
            if not cutout_url and cutout_note is None:
                cutout_note = segment.last_reason() or None
        else:
            cutout_note = segment.status()["message"]

        t1.join()
        if analysis_result.get("error"):
            raise RuntimeError(
                f"商品视觉分析失败（模型未返回可用结果），请稍后重试。原因：{analysis_result['error']}"
            )
        product = analysis_result.get("data") or {}
        if not product:
            raise RuntimeError("商品视觉分析未返回任何结果，请稍后重试或更换图片。")
        _step(task_id, "analyze_product", "done", 30)
        _step(task_id, "extract_subject", "done", 35)

        # ---------- 3. 用户画像 ----------
        _step(task_id, "build_persona", "running", 42)
        persona = generators.build_persona(product, product_name, description)
        _step(task_id, "build_persona", "done", 50)

        # ---------- 4. 标题 / 卖点 / 详情 ----------
        _step(task_id, "generate_content", "running", 56)
        titles = generators.build_titles(product, product_name, description)
        selling_points = generators.build_selling_points(product, product_name, description)
        detail_sections = generators.build_detail_sections(product, product_name, description)
        _step(task_id, "generate_content", "done", 72)

        # ---------- 5. 短视频脚本 ----------
        _step(task_id, "generate_script", "running", 78)
        video_script = generators.build_video_script(product, product_name, description)
        _step(task_id, "generate_script", "done", 85)

        # ---------- 6. 营销图方案 ----------
        _step(task_id, "generate_image_plan", "running", 90)
        image_plans = generators.build_image_plans(product, product_name, description)
        _step(task_id, "generate_image_plan", "done", 94)

        # ---------- 7. 汇总报告 + 缓存 ----------
        _step(task_id, "assemble", "running", 96)
        report = _assemble(
            product=product, persona=persona, titles=titles,
            selling_points=selling_points, detail_sections=detail_sections,
            video_script=video_script, image_plans=image_plans,
            image_url=image_url, cutout_url=cutout_url, cutout_note=cutout_note,
            product_name=product_name, description=description,
            mock_mode=mock_mode, demo_source=demo_source,
        )
        report_id = db.insert_report(image_hash, image_url, product_name, description, report, mock_mode)
        db.update_task(task_id, status="done", report_id=report_id)
        report["meta"]["report_id"] = report_id
        task_state.set_report(task_id, report)
    except Exception as e:  # noqa: BLE001 —— 统一兜底为友好错误
        message = str(e) or e.__class__.__name__
        db.update_task(task_id, status="error", error=message)
        task_state.set_error(task_id, message)


def _assemble(*, product: dict, persona: dict, titles: dict, selling_points: dict,
              detail_sections: dict, video_script: dict, image_plans: dict,
              image_url: str, cutout_url: str | None, cutout_note: str | None = None,
              product_name: str, description: str,
              mock_mode: bool, demo_source: str | None = None) -> dict:
    report = {
        "meta": {
            "generated_at": _fmt_time(),
            "provider": ai_client.active_name(),
            "is_mock": mock_mode,
            "model_vision": config.VISION_MODEL,
            "model_text": config.TEXT_MODEL,
            "image_url": image_url,
            "cutout_url": cutout_url,
            "cutout_note": cutout_note,
            "from_cache": False,
            "example_slug": demo_source,
            "user_input": {"product_name": product_name, "description": description},
        },
        "product": product,
        "persona": persona,
        "titles": titles,
        "selling_points": selling_points,
        "detail_sections": detail_sections,
        "video_script": video_script,
        "image_plans": image_plans,
    }
    return _normalize_report(report)


# 报告各结构模块的 schema key 对应关系
_REPORT_BLOCKS = [
    ("product", "product_analysis"),
    ("persona", "persona"),
    ("titles", "titles"),
    ("selling_points", "selling_points"),
    ("detail_sections", "detail_sections"),
    ("video_script", "video_script"),
    ("image_plans", "image_plans"),
]


def _normalize_report(report: dict) -> dict:
    """字段级兜底（幂等）：数组恒为数组、字符串恒为字符串、缺段补默认段。

    无论来源是真实模型、Mock 种子还是历史缓存，渲染层都不会因缺字段崩溃。
    """
    for field, schema_key in _REPORT_BLOCKS:
        report[field] = merge_and_normalize(schema_key, report.get(field))
    return report


def report_to_cache_snapshot(report_row: dict) -> dict:
    """把缓存行还原为「报告 dict + report_id」，用于同图秒开。"""
    payload = report_row["payload"]
    _normalize_report(payload)  # 历史缓存同样过一遍字段兜底，防止残缺旧数据白屏
    payload.setdefault("meta", {})["from_cache"] = True
    payload["meta"]["report_id"] = report_row["id"]
    return payload
