"""HTTP API：上传 / 示例 / 分析任务 / 进度轮询 / 报告导出 / 静态资源。"""
from __future__ import annotations

import hashlib
import re
import threading
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel

from . import config, db, task_state
from .providers import ai_client
from .segmentation import service as segment
from .services import examples as examples_svc
from .services import markdown_report
from .services.pipeline import report_to_cache_snapshot, run_analysis_task

router = APIRouter(prefix="/api")


# ---------------------------------------------------------------- 模型
class AnalyzeRequest(BaseModel):
    file_id: str | None = None
    example_id: str | None = None
    product_name: str = ""
    description: str = ""


# ---------------------------------------------------------------- 工具
def _md5(path: str | Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _save_upload(file: UploadFile) -> tuple[Path, str, str]:
    original = file.filename or "image.jpg"
    ext = Path(original).suffix.lower()
    if ext not in config.ALLOWED_EXT:
        raise HTTPException(400, f"不支持的图片格式 {ext}，仅支持 {sorted(config.ALLOWED_EXT)}")
    safe_name = re.sub(r"[^\w.\u4e00-\u9fa5-]", "", Path(original).stem)[:40] or "image"
    filename = f"{uuid.uuid4().hex}_{safe_name}{ext}"
    dest = config.UPLOAD_DIR / filename
    data = file.file.read()
    if len(data) > int(config.MAX_IMAGE_MB * 1024 * 1024):
        raise HTTPException(400, f"图片超过 {config.MAX_IMAGE_MB:.0f}MB 限制")
    dest.write_bytes(data)
    return dest, filename, f"/api/files/{filename}"


def _resolve_target(body: AnalyzeRequest) -> dict:
    """把 file_id / example_id 解析为 pipeline 输入；并做模式合法性与缓存检查。

    返回: dict(image_path, image_url, image_hash, product_name, description,
               is_example, example_slug, cached_report_row or None)
    """
    real_ok = ai_client.active_name() != "mock"

    if body.example_id:
        meta = examples_svc.meta_by_slug(body.example_id)
        if not meta or not examples_svc.exists(body.example_id):
            raise HTTPException(404, "示例商品不存在")
        image_path = examples_svc.image_path_for(body.example_id)
        info = {
            "image_path": image_path,
            "image_url": examples_svc.image_url_for(body.example_id),
            "image_hash": _md5(image_path),
            "product_name": body.product_name or meta["suggested_name"],
            "description": body.description or meta["description"],
            "is_example": True,
            "example_slug": body.example_id,
        }
    else:
        if not body.file_id:
            raise HTTPException(400, "缺少图片：请上传图片或选择内置示例")
        upload = db.get_upload(body.file_id)
        if not upload:
            raise HTTPException(404, "上传记录不存在，请重新上传")
        image_path = config.UPLOAD_DIR / upload["file_name"]
        if not image_path.exists():
            raise HTTPException(404, "图片文件缺失，请重新上传")
        if not real_ok:
            # Mock 演示模式：无法真正“看懂”图片，
            # 用「商品名+描述+文件名」匹配最近的内置模板做演示报告（不含视觉分析）。
            user_name = body.product_name or upload.get("product_name", "") or ""
            user_desc = body.description or upload.get("description", "") or ""
            probe = " ".join(filter(None, [user_name, user_desc, Path(upload["file_name"]).stem]))
            if not examples_svc.match_slug(probe):
                raise HTTPException(
                    400,
                    "当前为 Mock 演示模式（未配置 API Key），无法直接识别图片内容。"
                    "请在「商品名称」一栏填写商品类型关键词（如：保温杯 / 咖啡杯 / 耳机），"
                    "系统将据此匹配最接近的演示模板生成报告；"
                    "或直接使用下方内置示例；或在 .env 中配置 OPENAI_API_KEY 分析真实图片。",
                )
        info = {
            "image_path": image_path,
            "image_url": upload["url"],
            "image_hash": upload["image_hash"] or _md5(image_path),
            "product_name": body.product_name or upload.get("product_name", ""),
            "description": body.description or upload.get("description", ""),
            "is_example": False,
            "example_slug": None,
        }

    cached = db.find_cached_report(info["image_hash"], info["product_name"], info["description"])
    info["cached"] = cached
    return info


# ---------------------------------------------------------------- 接口
@router.get("/config")
def get_config():
    try:
        seg = segment.status()
    except Exception as e:  # noqa: BLE001
        seg = {"available": False, "ready": False, "message": f"抠图服务状态读取失败：{e}"}
    return {
        "provider": ai_client.active_name(),
        "is_mock": ai_client.active_name() == "mock",
        "has_api_key": bool(config.API_KEY),
        "model_vision": config.VISION_MODEL,
        "model_text": config.TEXT_MODEL,
        "steps": config.STEPS,
        "segment": seg,
    }


@router.get("/examples")
def list_examples():
    return {"examples": examples_svc.list_examples()}


@router.post("/uploads")
async def upload_image(file: UploadFile = File(...),
                       product_name: str = Form(""),
                       description: str = Form("")):
    try:
        path, filename, url = _save_upload(file)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"文件读取失败: {e}") from e
    image_hash = _md5(path)
    file_id = filename.split("_", 1)[0]
    db.save_upload(file_id, filename, image_hash, url, product_name, description)
    return {"ok": True, "file_id": file_id, "url": url, "image_hash": image_hash}


@router.post("/analyze")
def analyze(body: AnalyzeRequest):
    info = _resolve_target(body)

    if info["cached"]:
        # 同图缓存命中：直接返回已完成的报告（秒开）
        cached_row = info["cached"]
        report_row = db.get_report(cached_row["id"])
        task_id = db.create_task(report_id=report_row["id"])
        db.update_task(task_id, status="done", report_id=report_row["id"])
        report = report_to_cache_snapshot(report_row)
        task_state.init_state(task_id)
        task_state.set_report(task_id, report)
        return {"task_id": task_id, "instant": True}

    task_id = db.create_task()
    task_state.init_state(task_id)
    t = threading.Thread(
        target=run_analysis_task,
        kwargs=dict(
            task_id=task_id,
            image_path=info["image_path"],
            image_url=info["image_url"],
            image_hash=info["image_hash"],
            product_name=info["product_name"],
            description=info["description"],
            is_example=info["is_example"],
            example_slug=info["example_slug"],
        ),
        daemon=True,
    )
    t.start()
    return {"task_id": task_id, "instant": False}


@router.get("/tasks/{task_id}")
def task_detail(task_id: str):
    row = db.get_task(task_id)
    if not row:
        raise HTTPException(404, "任务不存在")
    snap = task_state.snapshot(task_id)
    status = row["status"]
    report_id = row.get("report_id")

    steps = snap["steps"] if snap else None
    report = (snap or {}).get("report")
    if status == "done" and (not report or not steps) and report_id:
        # 进程重启等导致内存态丢失：从数据库恢复
        r = db.get_report(report_id)
        if r:
            report = report_to_cache_snapshot(r)
            steps = [
                {"key": s["key"], "label": s["label"], "status": "done"}
                for s in config.STEPS
            ]
    progress = (snap or {}).get("progress", 100 if status == "done" else 0)
    return {
        "task_id": task_id,
        "status": status,
        "progress": progress,
        "steps": steps or [],
        "current": (snap or {}).get("current", status),
        "report": report,
        "report_id": report_id,
        "error": row.get("error") or (snap or {}).get("error"),
    }


@router.get("/reports/{report_id}/markdown")
def report_markdown(report_id: str):
    r = db.get_report(report_id)
    if not r:
        raise HTTPException(404, "报告不存在")
    md = markdown_report.render_markdown(r["payload"])
    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")


@router.get("/files/{filename}")
def serve_file(filename: str):
    # 仅允许本系统生成/上传的两类文件：<uuid>_<stem>.<ext> 或 cutout_<hash>.png
    if re.fullmatch(r"cutout_[0-9a-f]{32}\.png", filename):
        path = config.OUTPUT_DIR / filename
    elif re.fullmatch(r"[0-9a-f]{32}_[\w\u4e00-\u9fa5-]+\.(jpg|jpeg|png|webp)", filename):
        path = config.UPLOAD_DIR / filename
    else:
        raise HTTPException(400, "非法的文件访问")
    if not path.exists():
        raise HTTPException(404, "文件不存在")
    media = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    return FileResponse(path, media_type=media.get(path.suffix.lstrip("."), "application/octet-stream"))


@router.get("/health")
def health():
    return JSONResponse({"ok": True, "provider": ai_client.active_name()})
