"""后端冒烟测试：验证示例链路 / 缓存 / Markdown 导出 / 自有图片边界。"""
from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app

ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def assert_eq(a, b, msg):
    if a != b:
        raise AssertionError(f"{msg}: expected {b}, got {a}")


def main():
    # 1. 配置
    r = client.get("/api/config")
    assert_eq(r.status_code, 200, "config status")
    cfg = r.json()
    print("provider:", cfg["provider"])

    # 2. 示例列表
    r = client.get("/api/examples")
    assert_eq(r.status_code, 200, "examples status")
    exs = r.json()["examples"]
    assert len(exs) >= 3, f"expected >=3 examples, got {len(exs)}"
    slug = exs[0]["slug"]
    print("first example:", slug)

    # 3. 示例分析（mock 链路）
    r = client.post("/api/analyze", json={"example_id": slug})
    assert_eq(r.status_code, 200, "analyze example status")
    tid = r.json()["task_id"]
    report = None
    for _ in range(30):
        r = client.get(f"/api/tasks/{tid}")
        report = r.json().get("report")
        if report:
            break
        time.sleep(0.05)
    assert report is not None, "report not generated in time"
    for key in ("product", "persona", "titles", "selling_points", "detail_sections", "video_script", "image_plans"):
        assert key in report, f"report missing {key}"
    rid = r.json()["report_id"]
    print("example report keys:", list(report.keys()), "report_id:", rid)

    # 4. Markdown 导出
    r = client.get(f"/api/reports/{rid}/markdown")
    assert_eq(r.status_code, 200, "markdown status")
    assert "# AI 电商商品运营报告" in r.text, "markdown header missing"
    print("markdown chars:", len(r.text))

    # 5. 同图缓存（第二次请求应 instant）
    r = client.post("/api/analyze", json={"example_id": slug})
    assert_eq(r.status_code, 200, "cached analyze status")
    assert r.json()["instant"] is True, "expected instant cached result"
    print("cache hit works")

    # 6. Mock + 上传但未填商品名 → 明确提示（无法匹配合适模板）
    img = ROOT / "examples" / "images" / f"{slug}.png"
    with open(img, "rb") as f:
        r = client.post("/api/uploads", files={"file": ("demo.png", f, "image/png")})
    assert_eq(r.status_code, 200, "upload status")
    fid = r.json()["file_id"]
    r = client.post("/api/analyze", json={"file_id": fid})
    assert_eq(r.status_code, 400, "expected 400 when no keyword matched in mock mode")
    assert "Mock" in r.json()["detail"] or "API Key" in r.json()["detail"], "expected helpful boundary message"
    print("boundary check ok:", r.json()["detail"][:80])

    # 7. Mock + 上传并填写商品名 → 生成演示报告（匹配最近模板并重命名）
    with open(img, "rb") as f:
        r = client.post("/api/uploads", files={"file": ("headphones.png", f, "image/png")})
    fid2 = r.json()["file_id"]
    r = client.post("/api/analyze", json={"file_id": fid2, "product_name": "降噪耳机", "description": "主动降噪"})
    assert_eq(r.status_code, 200, "mock upload analyze status")
    tid2 = r.json()["task_id"]
    report2 = None
    for _ in range(60):
        r = client.get(f"/api/tasks/{tid2}")
        report2 = r.json().get("report")
        if report2 or r.json().get("status") == "error":
            break
        time.sleep(0.05)
    assert report2 is not None, "mock upload report not generated in time"
    assert report2["product"]["product_name"] == "降噪耳机", "expected renamed product_name"
    assert r.json().get("report_id"), "expected report_id"
    print("mock upload demo ok -> product:", report2["product"]["product_name"],
          "| demo template:", (report2.get("meta") or {}).get("example_slug"))

    print("\nAll smoke tests passed.")


if __name__ == "__main__":
    main()
