"""生成内置示例商品示意图（PIL 程序绘制，风格统一、离线可复现）。

产物：examples/images/<slug>.png，对应 examples/reports/<slug>.json 的预写 Mock 报告。
用法：python scripts/make_example_images.py
说明：本脚本仅为“无网络环境的演示兜底”而存在；
真实使用时上传自有商品照片，效果最佳。
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "images"
SS = 2  # 超采样抗锯齿
W = H = 1200


# ---------------- 基础工具 ----------------
def canvas(top: tuple, bottom: tuple) -> Image.Image:
    img = Image.new("RGBA", (W * SS, H * SS), top)
    d = ImageDraw.Draw(img)
    for y in range(H * SS):
        t = y / (H * SS)
        d.line([(0, y), (W * SS, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    return img


def shadow(img: Image.Image, cx: int, cy: int, rx: int, ry: int, alpha: int = 70):
    layer = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(layer)
    d2.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(20, 25, 35, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(18 * SS))
    img.alpha_composite(layer, (0, 0))


def hgrad_region(bbox, left: tuple, right: tuple) -> Image.Image:
    """在 bbox 内画横向渐变（返回含 bbox 的 RGBA，超出 bbox 部分透明）。"""
    x0, y0, x1, y1 = bbox
    layer = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x in range(x1 - x0):
        t = x / max(1, (x1 - x0 - 1))
        d.line([(x, 0), (x, y1 - y0)], fill=tuple(int(a + (b - a) * t) for a, b in zip(left, right)))
    return layer


def paste_gradient(canvas_img: Image.Image, bbox, left, right, mask: Image.Image | None = None):
    layer = hgrad_region(bbox, left, right)
    if mask:
        layer = Image.composite(layer, Image.new("RGBA", layer.size, (0, 0, 0, 0)), mask)
    canvas_img.alpha_composite(layer, (bbox[0], bbox[1]))


def rounded_mask(bbox, radius) -> Image.Image:
    m = Image.new("L", (bbox[2] - bbox[0], bbox[3] - bbox[1]), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, m.width - 1, m.height - 1], radius, fill=255)
    return m


def save(img: Image.Image, name: str):
    img = img.resize((W, H), Image.LANCZOS).convert("RGB")
    img.save(OUT / name, "PNG")
    print("saved", OUT / name)


def load_font(size: int):
    for path in (r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf",
                 "/System/Library/Fonts/Helvetica.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


from PIL import ImageFont  # noqa: E402


# ---------------- 1. 智能保温杯 ----------------
def tumbler():
    img = canvas((244, 246, 249), (226, 230, 235))
    d = ImageDraw.Draw(img)
    cx, top, bot = 600, 300, 1010
    shadow(img, cx, bot + 6, 260 * SS, 30 * SS)

    body = [cx - 165 * SS, top, cx + 165 * SS, bot]
    mask = rounded_mask(body, 60 * SS)
    paste_gradient(img, body, (238, 241, 244), (96, 106, 118), mask)
    # 金属高光条（偏左）
    hl = [cx - 95 * SS, top + 8 * SS, cx - 25 * SS, bot - 8 * SS]
    hmask = rounded_mask(hl, 46 * SS)
    paste_gradient(img, hl, (255, 255, 255), (186, 195, 205), hmask)
    # 两侧轮廓暗线
    for x, w in ((cx - 165 * SS, 8 * SS), (cx + 165 * SS - 8 * SS, 8 * SS)):
        e = [x, top + 10 * SS, x + w, bot - 10 * SS]
        paste_gradient(img, e, (70, 78, 90), (150, 158, 170), rounded_mask(e, 5 * SS))

    # 杯盖（深灰石墨）
    lid_top, lid_bot = top - 34 * SS, top + 26 * SS
    lid = [cx - 172 * SS, lid_top, cx + 172 * SS, lid_bot]
    paste_gradient(img, lid, (128, 134, 142), (54, 60, 68), rounded_mask(lid, 44 * SS))
    lip = [cx - 176 * SS, lid_bot - 6 * SS, cx + 176 * SS, lid_bot + 22 * SS]
    paste_gradient(img, lip, (88, 95, 104), (158, 166, 176), rounded_mask(lip, 26 * SS))

    # LED 圆形屏幕
    scr_c, scr_r = (cx, lid_top + (lid_bot - lid_top) // 2 - 12 * SS), 66 * SS
    d.ellipse([scr_c[0] - scr_r, scr_c[1] - scr_r, scr_c[0] + scr_r, scr_c[1] + scr_r], fill=(16, 20, 26))
    d.ellipse([scr_c[0] - scr_r * 0.86, scr_c[1] - scr_r * 0.86, scr_c[0] + scr_r * 0.86, scr_c[1] + scr_r * 0.86],
              outline=(125, 211, 252), width=8 * SS, fill=(22, 34, 46))
    # 温度数字
    f = load_font(int(58 * SS))
    text = "65°"
    tb = d.textbbox((0, 0), text, font=f)
    tw = tb[2] - tb[0]
    d.text((scr_c[0] - tw / 2 - tb[0], scr_c[1] - (tb[3] - tb[1]) / 2 - tb[1] - 10 * SS),
           text, fill=(240, 250, 255), font=f)
    # 杯身下方一抹淡环境光
    floor = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(floor).ellipse([cx - 190 * SS, bot - 30 * SS, cx + 190 * SS, bot + 90 * SS],
                                  fill=(210, 218, 228, 120))
    floor = floor.filter(ImageFilter.GaussianBlur(20 * SS))
    img.alpha_composite(floor)
    save(img, "insulated_tumbler.png")


# ---------------- 2. 北欧陶瓷杯 ----------------
def mug():
    img = canvas((250, 247, 240), (238, 230, 218))
    d = ImageDraw.Draw(img)
    cx, top, bot = 600, 330, 980
    shadow(img, cx, bot + 8, 250 * SS, 26 * SS)

    body = [cx - 210 * SS, top, cx + 210 * SS, bot]
    bm = rounded_mask(body, 46 * SS)
    paste_gradient(img, body, (177, 196, 176), (133, 158, 138), bm)  # 鼠尾草绿
    # 哑光漫反射
    hl = [cx - 60 * SS, top + 22 * SS, cx - 8 * SS, bot - 30 * SS]
    paste_gradient(img, hl, (226, 236, 222), (196, 212, 194), rounded_mask(hl, 26 * SS))

    # 杯口内圈 + 咖啡液面
    rim_c, rx, ry = (cx, top + 2 * SS), 224 * SS, 62 * SS
    d.ellipse([rim_c[0] - rx, rim_c[1] - ry, rim_c[0] + rx, rim_c[1] + ry],
              outline=(118, 142, 122), width=16 * SS, fill=(58, 42, 30))
    # 宽把（右侧，双层：外深内浅模拟把厚）
    hc, hr = (cx + 300 * SS, (top + bot) // 2 + 10 * SS), 120 * SS
    for off, col, wd in ((0, (96, 120, 100), 76 * SS), (14 * SS, (168, 190, 168), 30 * SS)):
        b = [hc[0] - hr - off, hc[1] - hr - off, hc[0] + hr + off, hc[1] + hr + off]
        d.arc(b, start=285, end=105, fill=col, width=wd)  # 右侧大半圆
    # 杯身小高光点
    save(img, "ceramic_coffee_mug.png")


# ---------------- 3. 头戴式耳机 ----------------
def headphones():
    img = canvas((240, 244, 250), (218, 226, 238))
    d = ImageDraw.Draw(img)
    shadow(img, 600, 1030, 300 * SS, 34 * SS)

    # 头梁主弧（从两侧耳罩顶部绕过头顶）
    arc_b = [600 - 372 * SS, 460 - 372 * SS, 600 + 372 * SS, 460 + 372 * SS]
    d.arc(arc_b, start=40, end=140, fill=(46, 50, 56), width=96 * SS)
    d.arc([a + 22 * SS for a in arc_b], start=44, end=136, fill=(96, 102, 112), width=30 * SS)

    cup = [
        {"c": (355, 700), "r": 168, "rot": 150, "top": 20},
        {"c": (845, 700), "r": 168, "rot": 150, "top": 160},
    ]
    for item in cup:
        c, r = item["c"], item["r"]
        cx, cy = c[0] * SS, c[1] * SS
        rr = r * SS
        # 耳罩外壳（深灰），旋转倾斜的感觉用椭圆近似
        d.ellipse([cx - rr, cy - rr * 0.94, cx + rr, cy + rr * 0.94], fill=(40, 44, 50))
        # 蛋白皮衬圈
        d.ellipse([cx - rr * 0.86, cy - rr * 0.8, cx + rr * 0.86, cy + rr * 0.8], fill=(74, 80, 90))
        d.ellipse([cx - rr * 0.76, cy - rr * 0.7, cx + rr * 0.76, cy + rr * 0.7], fill=(30, 33, 39))
        # 内侧扬声器格栅亮区
        d.ellipse([cx - rr * 0.55, cy - rr * 0.5, cx + rr * 0.55, cy + rr * 0.5], fill=(58, 63, 71))
        d.ellipse([cx - rr * 0.42, cy - rr * 0.38, cx + rr * 0.42, cy + rr * 0.38], fill=(20, 22, 27))
        # 顶部高光
        d.arc([cx - rr * 0.8, cy - rr * 1.15, cx + rr * 0.8, cy + rr * 0.55], start=210, end=330,
              fill=(120, 128, 140), width=14 * SS)
    save(img, "wireless_headphones.png")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    tumbler()
    mug()
    headphones()
    print("done")
