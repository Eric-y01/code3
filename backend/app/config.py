"""全局配置：路径、目录、AI 供应商设置（全部由环境变量/.env 控制）。"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# 仓库根目录 = backend/app/config.py -> 上两级
ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"

load_dotenv(ROOT_DIR / ".env", override=True)  # .env 优先于系统环境变量，确保项目配置可控

# ---------- 目录 ----------
DATA_DIR = ROOT_DIR / "data"
UPLOAD_DIR = ROOT_DIR / "uploads"
OUTPUT_DIR = ROOT_DIR / "outputs"
EXAMPLES_DIR = ROOT_DIR / "examples"
EXAMPLES_IMAGES_DIR = EXAMPLES_DIR / "images"
EXAMPLES_REPORTS_DIR = EXAMPLES_DIR / "reports"
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
PROMPTS_DIR = BACKEND_DIR / "app" / "prompts"
MODELS_DIR = ROOT_DIR / "models"  # rembg 等本地模型权重缓存

for _d in (DATA_DIR, UPLOAD_DIR, OUTPUT_DIR, EXAMPLES_IMAGES_DIR, EXAMPLES_REPORTS_DIR, MODELS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# rembg 模型目录固定到项目内（避免散落到用户主目录 ~/.u2net）。
# 注意 rembg 内部会再拼一层 models/<模型名>/ 子目录：
# 默认权重落在 <ROOT>/models/models/u2net/u2net.onnx，均已 gitignore。
# 允许在 .env 用 U2NET_HOME 覆盖（若自定义请填绝对路径）。
os.environ.setdefault("U2NET_HOME", str(MODELS_DIR))

# 抠图模型：u2net（通用）| isnet-general-use（精细人像/商品更准，需额外下载）
SEGMENT_MODEL = os.getenv("SEGMENT_MODEL", "u2net").strip() or "u2net"

DB_PATH = DATA_DIR / "app.db"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------- 上传限制 ----------
MAX_IMAGE_MB = float(os.getenv("MAX_IMAGE_MB", "8"))
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}

# ---------- AI 供应商 ----------
def _effective_provider() -> str:
    mode = os.getenv("AI_PROVIDER", "auto").strip().lower()
    if mode in ("mock", "openai_compatible"):
        return mode
    # auto：有 key 走真实模型，否则 Mock
    if os.getenv("OPENAI_API_KEY") or os.getenv("AI_API_KEY"):
        return "openai_compatible"
    return "mock"

API_KEY = os.getenv("AI_API_KEY") or os.getenv("OPENAI_API_KEY", "").strip()
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
VISION_MODEL = os.getenv("VISION_MODEL", "gpt-4o-mini").strip()
TEXT_MODEL = os.getenv("TEXT_MODEL", "gpt-4o-mini").strip()

# 实际激活的供应商名（供 /api/config 与前端徽标展示）
PROVIDER = _effective_provider()
IS_MOCK = PROVIDER == "mock"
HTTP_TIMEOUT = 120

# ---------- 进度步骤定义（前端据此渲染） ----------
STEPS = [
    {"key": "start", "label": "创建任务"},
    {"key": "analyze_product", "label": "视觉分析商品"},
    {"key": "extract_subject", "label": "提取商品主体"},
    {"key": "build_persona", "label": "构建用户画像"},
    {"key": "generate_content", "label": "生成标题/卖点/详情页"},
    {"key": "generate_script", "label": "生成短视频脚本"},
    {"key": "generate_image_plan", "label": "生成营销图方案"},
    {"key": "assemble", "label": "汇总运营报告"},
]
STEP_KEYS = [s["key"] for s in STEPS]
