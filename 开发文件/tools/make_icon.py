#!/usr/bin/env python3
"""生成 App 图标资源：拍立得 + P9 字标 + 水印条

产物（android/res/）：
  mipmap-{m,h,xh,xxh,xxxh}dpi/ic_launcher.png          传统图标（API 25 及以下）
  mipmap-{...}/ic_launcher_foreground.png              自适应前景（108dp 画布）
  mipmap-anydpi-v26/ic_launcher.xml                    自适应图标声明
  mipmap-anydpi-v26/ic_launcher_round.xml
  values/colors.xml                                    背景色
"""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = r"D:\P9徕卡水印工具\android"
RES = os.path.join(ROOT, "res")
FONT = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf"

CREAM = (247, 244, 238)
CARD = (252, 250, 246)
INK = (22, 21, 19)
RED = (208, 2, 27)
BG = (23, 23, 26)

# 108dp 画布，4x = 432px；可见区 72dp=288px，安全圆 66dp=264px
CANVAS = 432
CARD_W, CARD_H = 252, 292
PHOTO_H = 196
CORNER = 14


def draw_card(img, cx, cy):
    """在透明画布上画拍立得卡片"""
    d = ImageDraw.Draw(img)
    x0, y0 = cx - CARD_W // 2, cy - CARD_H // 2
    x1, y1 = x0 + CARD_W, y0 + CARD_H
    d.rounded_rectangle([x0, y0, x1, y1], radius=CORNER, fill=CARD + (255,))
    # 照片区
    px0, py0 = x0 + 12, y0 + 12
    px1, py1 = x1 - 12, y0 + 12 + PHOTO_H
    d.rounded_rectangle([px0, py0, px1, py1], radius=5, fill=INK + (255,))
    # P9
    f = ImageFont.truetype(FONT, int(PHOTO_H * 0.82))
    d.text(((px0 + px1) // 2, (py0 + py1) // 2 + 2), "P9", font=f, fill=CREAM + (255,), anchor="mm")
    # 底部水印条
    strip_cy = (py1 + y1) // 2
    bar_h = 20
    d.rounded_rectangle([x0 + 20, strip_cy - bar_h // 2,
                         x0 + 20 + 104, strip_cy + bar_h // 2],
                        radius=bar_h // 2, fill=INK + (255,))
    r = 12
    dx = x1 - 34
    d.ellipse([dx - r, strip_cy - r, dx + r, strip_cy + r], fill=RED + (255,))


def foreground(size):
    img = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    draw_card(img, CANVAS // 2, CANVAS // 2)
    if size != CANVAS:
        img = img.resize((size, size), Image.LANCZOS)
    return img


def legacy(size):
    """带圆角方形背景的传统图标"""
    ss = 4
    big = Image.new("RGBA", (CANVAS * ss, CANVAS * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    d.rounded_rectangle([0, 0, CANVAS * ss - 1, CANVAS * ss - 1],
                        radius=int(CANVAS * ss * 0.22), fill=BG + (255,))
    fg = foreground(CANVAS).resize((CANVAS * ss, CANVAS * ss), Image.LANCZOS)
    big.alpha_composite(fg)
    return big.resize((size, size), Image.LANCZOS)


DPI = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}

for dpi, scale in DPI.items():
    path = os.path.join(RES, "mipmap-" + dpi)
    os.makedirs(path, exist_ok=True)
    fg_size = int(108 * scale)
    foreground(fg_size).save(os.path.join(path, "ic_launcher_foreground.png"))
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
    <color name="ic_launcher_background">#17171A</color>
</resources>
""")

print("图标资源已生成到", RES)
