#!/usr/bin/env python3
"""生成 App 图标资源：相纸 + P9 字标 + 水印条

设计要点（针对 OPPO / vivo 等会"放大裁切"的启动器）：
  · 背景层铺满 108dp 的米白，任何遮罩/裁切露出的都是米白，不会露出黑角
  · 所有内容（照片块 + 字标 + 水印条）都控制在中心 66dp 安全圆内
  · 前景层透明，只画内容

产物（android/res/）：
  mipmap-*/ic_launcher.png               传统图标（API 25 及以下）
  mipmap-*/ic_launcher_foreground.png    自适应前景（108dp 画布）
  mipmap-anydpi-v26/ic_launcher.xml / ic_launcher_round.xml
  values/colors.xml                      背景色
"""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = r"D:\P9徕卡水印工具\android"
RES = os.path.join(ROOT, "res")
FONT = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf"

CREAM = (247, 244, 238)
PAPER = (255, 253, 249)
INK = (24, 23, 21)
RED = (208, 2, 27)
GRAY = (126, 122, 116)
BG = (247, 244, 238)

CANVAS = 432          # 108dp @4x
# 内容整体占可见区（72dp=288px）约 60%，四周留白，避免被启动器放大后显得挤
# 目标：裁切到 72dp 可见区后，照片块约占 46%，与 P9（传统图标、不裁切）观感一致
PHOTO_W = 200         # 基准按传统图标定：占图标宽度 46%（P9 上看到的效果）
PHOTO_H = 196
PHOTO_R = 30
GAP = 14
STRIP_H = 34
LIFT = 4              # 整体上移，抵消底部水印条带来的下坠感

def _content(img, cx, cy, k=1.0):
    """在透明画布上画：照片块 + P9 + 水印条（整体以 cx,cy 为中心）"""
    d = ImageDraw.Draw(img)
    pw_, ph_ = int(PHOTO_W * k), int(PHOTO_H * k)
    gap_, strip_ = int(GAP * k), int(STRIP_H * k)
    rad_ = max(2, int(PHOTO_R * k))
    total_h = ph_ + gap_ + strip_
    top = cy - total_h // 2 - LIFT
    px0, py0 = cx - pw_ // 2, top
    px1, py1 = px0 + pw_, py0 + ph_

    # 照片块：竖向渐变（天光 → 地面），读起来像照片
    grad = Image.new("RGB", (pw_, ph_))
    gd = ImageDraw.Draw(grad)
    a, b = (62, 70, 84), (20, 21, 25)
    for i in range(ph_):
        t = i / (ph_ - 1)
        gd.line([(0, i), (pw_, i)],
                fill=(int(a[0] + (b[0] - a[0]) * t),
                      int(a[1] + (b[1] - a[1]) * t),
                      int(a[2] + (b[2] - a[2]) * t)))
    mask = Image.new("L", grad.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw_ - 1, ph_ - 1], radius=rad_, fill=255)
    img.paste(grad, (px0, py0), mask)

    # P9：画到独立图层，按真实墨迹居中
    target_w = pw_ * 0.82
    fsize = int(ph_ * 1.02)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((px0, py0), "P9",
                               font=ImageFont.truetype(FONT, fsize),
                               fill=CREAM + (255,), anchor="lt")
    ink = layer.crop(layer.getbbox())
    if ink.width > target_w:
        kk = target_w / ink.width
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((px0, py0), "P9",
                                   font=ImageFont.truetype(FONT, int(fsize * kk)),
                                   fill=CREAM + (255,), anchor="lt")
        ink = layer.crop(layer.getbbox())
    img.alpha_composite(ink, ((px0 + px1) // 2 - ink.width // 2,
                              (py0 + py1) // 2 - ink.height // 2))

    # 水印条：两行文字示意 + 红点
    strip_cy = py1 + gap_ + strip_ // 2
    bar_w = int(pw_ * 0.44)
    d.rounded_rectangle([px0, strip_cy - int(8 * k) - 1, px0 + bar_w, strip_cy - int(2 * k)],
                        radius=max(2, int(5 * k)), fill=INK + (255,))
    d.rounded_rectangle([px0, strip_cy + int(2 * k) + 1, px0 + int(bar_w * 0.66), strip_cy + int(7 * k) + 1],
                        radius=max(1, int(3 * k)), fill=GRAY + (255,))
    r = max(6, int(15 * k))
    dx = px1 - r
    d.ellipse([dx - r, strip_cy - r, dx + r, strip_cy + r], fill=RED + (255,))


def foreground(size, k=0.66):
    """自适应前景：内容按 0.66 缩放，裁到 72dp 可见区后与 P9 观感一致"""
    img = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    _content(img, CANVAS // 2, CANVAS // 2, k)
    if size != CANVAS:
        img = img.resize((size, size), Image.LANCZOS)
    return img


def legacy(size):
    ss = 4
    big = Image.new("RGBA", (CANVAS * ss, CANVAS * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    d.rounded_rectangle([0, 0, CANVAS * ss - 1, CANVAS * ss - 1],
                        radius=int(CANVAS * ss * 0.22), fill=BG + (255,))
    fg = foreground(CANVAS, 1.0).resize((CANVAS * ss, CANVAS * ss), Image.LANCZOS)
    big.alpha_composite(fg)
    return big.resize((size, size), Image.LANCZOS)


DPI = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}

for dpi, scale in DPI.items():
    path = os.path.join(RES, "mipmap-" + dpi)
    os.makedirs(path, exist_ok=True)
    fgs = int(108 * scale)
    foreground(fgs).save(os.path.join(path, "ic_launcher_foreground.png"))
    legacy(int(48 * scale)).save(os.path.join(path, "ic_launcher.png"))

anydpi = os.path.join(RES, "mipmap-anydpi-v26")
os.makedirs(anydpi, exist_ok=True)
xml = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background" />
    <foreground android:drawable="@mipmap/ic_launcher_foreground" />
</adaptive-icon>
"""
for name in ("ic_launcher.xml", "ic_launcher_round.xml"):
    with open(os.path.join(anydpi, name), "w", encoding="utf-8") as f:
        f.write(xml)

values = os.path.join(RES, "values")
os.makedirs(values, exist_ok=True)
with open(os.path.join(values, "colors.xml"), "w", encoding="utf-8") as f:
    f.write("""<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="ic_launcher_background">#F7F4EE</color>
</resources>
""")

print("图标资源已生成到", RES)
