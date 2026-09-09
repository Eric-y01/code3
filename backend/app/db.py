"""SQLite 存储：uploads / reports / tasks。

- reports 表即“结果缓存”：按 image_hash 命中，同图二次上传秒开。
- 所有连接使用 WAL 与每次新建连接，兼容多线程后台任务。
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from typing import Any, Optional

from . import config

_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(config.DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with _lock, _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS uploads (
                id TEXT PRIMARY KEY,
                file_name TEXT NOT NULL,
                image_hash TEXT,
                url TEXT NOT NULL,
                product_name TEXT DEFAULT '',
                description TEXT DEFAULT '',
                created REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                image_hash TEXT,
                image_url TEXT,
                product_name TEXT DEFAULT '',
                description TEXT DEFAULT '',
                payload TEXT NOT NULL,
                is_mock INTEGER DEFAULT 0,
                created REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_reports_hash ON reports(image_hash);
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                report_id TEXT,
                status TEXT NOT NULL,           -- pending|running|done|error
                error TEXT,
                created REAL NOT NULL,
                updated REAL NOT NULL
            );
            """
        )


def now() -> float:
    return time.time()


# ---------------- uploads ----------------
def save_upload(upload_id: str, file_name: str, image_hash: str, url: str,
                product_name: str = "", description: str = "") -> None:
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO uploads(id,file_name,image_hash,url,product_name,description,created) VALUES(?,?,?,?,?,?,?)",
            (upload_id, file_name, image_hash, url, product_name, description, now()),
        )


def get_upload(upload_id: str) -> Optional[dict]:
    with _conn() as c:
        row = c.execute("SELECT * FROM uploads WHERE id=?", (upload_id,)).fetchone()
    return dict(row) if row else None


# ---------------- reports（缓存） ----------------
def find_cached_report(image_hash: Optional[str], product_name: str = "", description: str = "") -> Optional[dict]:
    if not image_hash:
        return None
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM reports WHERE image_hash=? ORDER BY created DESC LIMIT 3",
            (image_hash,),
        ).fetchall()
    for r in rows:
        d = dict(r)
        # 仅当用户补充信息基本一致时才命中（补充信息不同则重算）
        if d["product_name"].strip() == product_name.strip() and d["description"].strip() == description.strip():
            return d
    return None


def insert_report(image_hash: str, image_url: str, product_name: str, description: str,
                  payload: dict, is_mock: bool) -> str:
    rid = uuid.uuid4().hex
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO reports(id,image_hash,image_url,product_name,description,payload,is_mock,created) VALUES(?,?,?,?,?,?,?,?)",
            (rid, image_hash, image_url, product_name, description,
             json.dumps(payload, ensure_ascii=False), int(is_mock), now()),
        )
    return rid


def get_report(report_id: str) -> Optional[dict]:
    with _conn() as c:
        row = c.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["payload"] = json.loads(d["payload"])
    return d


# ---------------- tasks ----------------
def create_task(report_id: Optional[str] = None) -> str:
    tid = uuid.uuid4().hex
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO tasks(id,report_id,status,error,created,updated) VALUES(?,?,?,?,?,?)",
            (tid, report_id, "pending", None, now(), now()),
        )
    return tid


def update_task(task_id: str, **fields: Any) -> None:
    if not fields:
        return
    fields["updated"] = now()
    cols = ", ".join(f"{k}=?" for k in fields)
    with _lock, _conn() as c:
        c.execute(f"UPDATE tasks SET {cols} WHERE id=?", (*fields.values(), task_id))


def get_task(task_id: str) -> Optional[dict]:
    with _conn() as c:
        row = c.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    return dict(row) if row else None
