"""运行时任务状态机（内存态，仅用于前端轮询展示进度）。

状态与报告数据在 sqlite；进度（steps 完成情况/当前步骤/百分比）存内存字典。
后端重启后未完成任务视为已失败，前端会提示重新开始 —— 对演示足够可靠。
"""
from __future__ import annotations

import threading
from typing import Any, Optional

from . import config

# {task_id: {"steps": {key: "pending"|"running"|"done"|"error"}, "current": key, "report": dict|None, "error": str|None}}
_STATE: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()


def init_state(task_id: str) -> None:
    with _LOCK:
        _STATE[task_id] = {
            "steps": {k: "pending" for k in config.STEP_KEYS},
            "current": "start",
            "progress": 0,
            "report": None,
            "error": None,
        }


def step_status(task_id: str, key: str, status: str, progress: Optional[int] = None) -> None:
    with _LOCK:
        st = _STATE.get(task_id)
        if not st:
            return
        st["steps"][key] = status
        st["current"] = key
        if progress is not None:
            st["progress"] = progress


def set_report(task_id: str, report: dict, progress: int = 100) -> None:
    with _LOCK:
        st = _STATE.get(task_id)
        if not st:
            return
        st["report"] = report
        st["progress"] = progress
        st["steps"] = {k: "done" for k in config.STEP_KEYS}


def set_error(task_id: str, message: str) -> None:
    with _LOCK:
        st = _STATE.get(task_id)
        if not st:
            return
        st["error"] = message
        st["current"] = "error"


def snapshot(task_id: str) -> Optional[dict]:
    with _LOCK:
        st = _STATE.get(task_id)
        if st is None:
            return None
        return {
            "steps": [{"key": k, "label": label, "status": st["steps"].get(k, "pending")}
                      for k, label in [(s["key"], s["label"]) for s in config.STEPS]],
            "current": st["current"],
            "progress": st["progress"],
            "report": st["report"],
            "error": st["error"],
        }
