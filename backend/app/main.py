"""FastAPI 应用入口。

运行：cd backend && uvicorn app.main:app --reload --port 8000
若 frontend/dist 已构建，本服务同时托管前端（单进程即可完整演示）。
"""
from __future__ import annotations

import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config, db
from .api import router as api_router
from .providers import ai_client

app = FastAPI(title="AI 电商运营助手", version="0.1.0",
              description="上传商品图 → 结构化分析 → 三平台运营内容 → 运营报告")

# 本地开发（Vite 5173）与任意来源演示均放开 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init_db()

# 探测并兜底初始化供应商（真实 key 缺失时自动落到 Mock）
try:
    ai_client.get_client()
except Exception as e:  # noqa: BLE001
    print(f"[startup] AI provider init warn: {e}")

app.include_router(api_router)

# 后台预热抠图模型：不阻塞启动；rembg 已装但模型缺失时自动下载（u2net 约 170MB）。
# 预热完成后，用户首次分析即可直接产出透明抠图。
try:
    from .segmentation import service as _seg
    if _seg.available() and not _seg.model_ready():
        threading.Thread(target=_seg.warm_up, daemon=True).start()
        print(f"[startup] segmentation warm-up started → {_seg.model_path()}")
    elif _seg.available():
        print("[startup] segmentation ready (rembg).")
    else:
        print(f"[startup] rembg not installed: {_seg.last_reason()}")
except Exception as e:  # noqa: BLE001
    print(f"[startup] segmentation warm-up skipped: {e}")

# 内置示例商品静态资源（/examples/images/...）
app.mount("/examples", StaticFiles(directory=str(config.EXAMPLES_DIR)), name="examples")


@app.get("/")
def index_fallback():
    if config.FRONTEND_DIST.exists():
        from fastapi.responses import FileResponse
        return FileResponse(config.FRONTEND_DIST / "index.html")
    return JSONResponse({
        "service": "AI 电商运营助手 API",
        "provider": ai_client.active_name(),
        "hint": "前端未构建。请进入 frontend 执行 npm install && npm run build；"
                "或开发模式分别启动：npm run dev（5173）+ 本 API（8000）。"
    })


if config.FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(config.FRONTEND_DIST), html=True), name="frontend")
