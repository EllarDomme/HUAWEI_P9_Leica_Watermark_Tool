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
CARD_W, CARD_H = 254, 300
PHOTO_H = 208
CORNER = 5   # 接近相纸直角，避免像游戏机


def draw_card(img, cx, cy, k=1.0):
    """在透明画布上画拍立得卡片；k<1 时整体缩小（给自适应图标留裁切余量）"""
    d = ImageDraw.Draw(img)
    cw, ch, ph = int(CARD_W * k), int(CARD_H * k), int(PHOTO_H * k)
    pad = max(3, int(12 * k))
    x0, y0 = cx - cw // 2, cy - ch // 2
    x1, y1 = x0 + cw, y0 + ch
    d.rounded_rectangle([x0, y0, x1, y1], radius=max(2, int(CORNER * k)), fill=CARD + (255,))
    # 照片区
    px0, py0 = x0 + pad, y0 + pad
    px1, py1 = x1 - pad, y0 + pad + ph
    grad = Image.new("RGB", (max(1, px1 - px0), max(1, py1 - py0)))
    gd = ImageDraw.Draw(grad)
    top, bot = (58, 64, 76), (21, 22, 26)
    for i in range(grad.height):
        t = i / max(1, grad.height - 1)
        gd.line([(0, i), (grad.width, i)],
                fill=(int(top[0] + (bot[0] - top[0]) * t),
                      int(top[1] + (bot[1] - top[1]) * t),
                      int(top[2] + (bot[2] - top[2]) * t)))
    mask = Image.new("L", grad.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, grad.width - 1, grad.height - 1], radius=3, fill=255)
    img.paste(grad, (px0, py0), mask)
    # P9：先画到独立图层，按真实墨迹包围盒居中（字体侧边距/上下留白都不对称）
    # 字号控制在墨迹宽度约为照片区 86%，留出呼吸感又不显小
    target_w = (px1 - px0) * 0.86
    fsize = int(ph * 1.05)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((px0, py0), "P9",
                               font=ImageFont.truetype(FONT, fsize),
                               fill=CREAM + (255,), anchor="lt")
    box = layer.getbbox()
    ink = layer.crop(box)
    if ink.width > target_w:                      # 按宽度回收
        kk = target_w / ink.width                 # 注意：不要覆盖外层 k（那是整体缩放）
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((px0, py0), "P9",
                                   font=ImageFont.truetype(FONT, int(fsize * kk)),
                                   fill=CREAM + (255,), anchor="lt")
        ink = layer.crop(layer.getbbox())
    img.alpha_composite(ink, ((px0 + px1) // 2 - ink.width // 2,
                              (py0 + py1) // 2 - ink.height // 2))
    # 底部水印条：所有尺寸都随 k 缩放，否则缩小后红点会顶到文字行上
    strip_cy = (py1 + y1) // 2
    sx = x0 + int(24 * k)              # 文字行左边距
    l1 = int(96 * k)                   # 第一行长度
    l2 = int(64 * k)                   # 第二行长度
    t1a, t1b = int(15 * k), int(5 * k)
    t2a, t2b = int(3 * k), int(11 * k)
    d.rounded_rectangle([sx, strip_cy - t1a, sx + l1, strip_cy - t1b],
                        radius=max(2, int(5 * k)), fill=INK + (255,))
    d.rounded_rectangle([sx, strip_cy + t2a, sx + l2, strip_cy + t2b],
                        radius=max(1, int(4 * k)), fill=(126, 122, 116, 255))
    r = max(5, int(15 * k))
    dx = x1 - int(38 * k)
    d.ellipse([dx - r, strip_cy - r, dx + r, strip_cy + r], fill=RED + (255,))


# 自适应前景缩放：裁切窗口只有 288px（72dp），要让卡片四周留出与 P9 相同的白边
# （P9 传统图标上卡片占宽 59%，即两侧各留 20.6%），换算到 288 窗口即 k≈0.66
ADAPTIVE_K = 0.66


def foreground(size, k=ADAPTIVE_K):
    img = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    draw_card(img, CANVAS // 2, CANVAS // 2, k)
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
    fg = foreground(CANVAS, 1.0).resize((CANVAS * ss, CANVAS * ss), Image.LANCZOS)
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
