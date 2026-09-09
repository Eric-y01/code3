# -*- coding: utf-8 -*-
"""临时验证脚本（用完即删）：
1) 真实/示例链路跑通并验证新字段
2) 直接验证抠图能力
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.segmentation import service as seg  # noqa: E402

client = TestClient(app)

print("== 1) segmentation direct check ==")
print("status:", seg.status())
img = Path(__file__).resolve().parents[1] / "examples" / "images" / "insulated_tumbler.png"
import hashlib  # noqa: E402

h = hashlib.md5(img.read_bytes()).hexdigest()
url = seg.extract_subject(img, h)
print("cutout url:", url)
if url:
    out = Path(__file__).resolve().parents[1] / "outputs" / f"cutout_{h}.png"
    from PIL import Image  # noqa: E402
    im = Image.open(out)
    print("cutout size:", im.size, "mode:", im.mode)
    assert im.mode == "RGBA", "expected RGBA transparent output"

print("\n== 2) example analyze flow ==")
r = client.post("/api/analyze", json={"example_id": "insulated_tumbler"})
tid = r.json()["task_id"]
report = None
for _ in range(180):
    r = client.get(f"/api/tasks/{tid}")
    d = r.json()
    if d.get("report"):
        report = d["report"]
        break
    if d.get("status") == "error":
        print("task error:", d)
        break
    time.sleep(1)
assert report is not None, "report not generated in 180s"

plans = report["image_plans"]["plans"]
print("plans count:", len(plans))
for f in ("subject", "scene", "lighting", "composition", "style", "prompt", "negative_prompt"):
    vals = [p.get(f) for p in plans]
    print(f"  {f}: present={all(bool(v) for v in vals)} len_min={min(len(v) for v in vals)}")
p0 = plans[0]
print("prompt char len:", len(p0["prompt"]))
assert len(p0["prompt"]) >= 120, "prompt should be rich"
print("meta cutout_note:", report["meta"].get("cutout_note"))

print("\n== 3) markdown export ==")
rid = r.json()["report_id"]
md = client.get(f"/api/reports/{rid}/markdown")
assert md.status_code == 200
assert "完整正向 Prompt" in md.text or "正向 Prompt" in md.text
assert "商品主体" in md.text
print("markdown ok, chars:", len(md.text))

print("\nAll checks passed.")
