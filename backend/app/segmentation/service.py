"""商品主体抠图服务（展示链路，独立于视觉分析）。

- 抠图引擎：rembg（本地 ONNX 推理）。默认模型 u2net，可用环境变量 SEGMENT_MODEL 切换
  （如 isnet-general-use，人像/商品边缘更精细，需额外下载对应权重）。
- 模型目录固定为项目 models/（通过 U2NET_HOME 指向，避免散落到用户主目录）。
  首次使用 rembg 会自动下载权重（u2net 约 170MB）；也可用 warm_up() 预热/预下载。
- rembg 未安装 / 模型下载失败 / 处理异常 → 返回 None 并给出可读原因，上层用原图占位。
- 抠图结果按图片 hash 缓存（outputs/cutout_<hash>.png），二次访问不重复计算。
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from PIL import Image

from .. import config

# 抠图引擎可用性（rembg import）缓存
_ENGINE_OK: Optional[bool] = None
_ENGINE_DETAIL = ""
_LAST_REASON = ""  # 最近一次失败原因；成功时为 ""（避免把过期信息带进报告）

# 模型会话（惰性加载；多任务下仅初始化一次，避免并发重复下载模型）
_SESSION = None
_SESSION_LOCK = threading.Lock()
_AVAILABLE_LOCK = threading.Lock()


# ---------------------------------------------------------------- 状态查询
def available() -> bool:
    """rembg 是否已安装（不触发模型下载）。"""
    global _ENGINE_OK, _ENGINE_DETAIL
    if _ENGINE_OK is None:
        with _AVAILABLE_LOCK:
            if _ENGINE_OK is None:
                try:
                    import rembg  # noqa: F401
                    _ENGINE_OK = True
                except Exception as e:  # noqa: BLE001
                    _ENGINE_OK = False
                    _ENGINE_DETAIL = str(e)[:200]
    return bool(_ENGINE_OK)


def model_name() -> str:
    return config.SEGMENT_MODEL or "u2net"


def model_path() -> Path:
    """rembg 下载模型的实际路径。

    rembg 2.0.50+ 布局为 <U2NET_HOME>/models/<name>/<name>.onnx；
    早期版本平铺在 <U2NET_HOME>/<name>.onnx。这里返回 rembg 实际会使用的路径。
    """
    name = model_name()
    return config.MODELS_DIR / "models" / name / f"{name}.onnx"


def model_candidates() -> list[Path]:
    """不同 rembg 版本可能落盘的模型文件位置，任一存在即视为已下载。"""
    name = model_name()
    return [
        config.MODELS_DIR / "models" / name / f"{name}.onnx",
        config.MODELS_DIR / f"{name}.onnx",
    ]


def model_ready() -> bool:
    return any(p.exists() and p.stat().st_size > 0 for p in model_candidates())


def status() -> dict:
    """返回当前抠图能力状态（供前端/报告 meta 展示可读原因）。"""
    if not available():
        return {
            "available": False,
            "ready": False,
            "model_downloaded": False,
            "message": "抠图引擎未启用：未安装 rembg。请在后端环境执行 "
                       f"pip install -r requirements-segmentation.txt（首次约 200MB）。{_ENGINE_DETAIL}",
        }
    if not model_ready():
        return {
            "available": True,
            "ready": False,
            "model_downloaded": False,
            "message": f"抠图模型 {model_name()} 尚未下载：首次使用将自动下载约 170MB（存于 models/），"
                       "下载完成后即可生成透明抠图；若网络受限可手动将模型放入 models/ 目录。",
        }
    return {
        "available": True,
        "ready": True,
        "model_downloaded": True,
        "message": f"抠图服务就绪（rembg · {model_name()}）。",
    }


def last_reason() -> str:
    """最近一次抠图失败的原因（供上层写入报告提示）。"""
    return _LAST_REASON


def _set_reason(msg: str) -> None:
    global _LAST_REASON
    _LAST_REASON = msg


# ---------------------------------------------------------------- 引擎
def _session():
    """创建（或复用）rembg 会话。模型缺失时会触发一次自动下载。"""
    global _SESSION
    if _SESSION is None:
        with _SESSION_LOCK:
            if _SESSION is None:
                import rembg
                _SESSION = rembg.new_session(model_name())
    return _SESSION


def warm_up() -> bool:
    """预热：确保 rembg 可用且模型就绪（可放在服务启动时后台调用）。

    返回是否已就绪；失败原因可通过 last_reason() / status() 查看。
    """
    if not available():
        _set_reason("rembg 未安装，抠图不可用。")
        return False
    try:
        if _session() is not None:
            _set_reason("")
            return True
    except Exception as e:  # noqa: BLE001
        _set_reason(f"抠图模型加载失败：{e}")
    return False


# ---------------------------------------------------------------- 抠图主入口
def extract_subject(image_path: str | Path, image_hash: str) -> str | None:
    """返回抠图后 PNG 的访问 URL（/api/files/cutout_<hash>.png）；失败返回 None。

    说明：图片 hash 由上层传入，文件名以此为准实现缓存。
    """
    out = config.OUTPUT_DIR / f"cutout_{image_hash}.png"
    if out.exists() and out.stat().st_size > 0:
        _set_reason("")  # 缓存命中同样视为成功
        return f"/api/files/{out.name}"

    if not available():
        _set_reason("rembg 未安装，抠图不可用（已降级为原图展示）。")
        return None

    try:
        with Image.open(image_path) as img:
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            cut = _cutout(img)
        if cut is None:
            _set_reason("抠图失败：模型未输出有效结果（已降级为原图展示）。")
            return None
        cut.save(out, "PNG")
        _set_reason("")
        return f"/api/files/{out.name}"
    except Exception as e:  # noqa: BLE001
        _set_reason(f"抠图失败：{str(e)[:200]}（已降级为原图展示）。")
        return None


def _cutout(img: Image.Image):
    """rembg 实现；如需替换 SAM / U²-Net 仅改动本函数。"""
    try:
        return _session().remove(img)
    except Exception:
        # 个别 rembg 版本的调用形态差异，用标准 API 再试一次
        import rembg
        return rembg.remove(img, session=_session())
