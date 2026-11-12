#!/usr/bin/env python3
"""闭运算 + 高分辨率重描，去掉描摹留下的细缝与毛刺，保持字形不变。

只处理字高 >= 300 单位的字符，标点不动。
"""
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

sys.path.insert(0, r"D:\P9徕卡水印工具\开发文件\tools")
import build_full3

F = r"D:\P9徕卡水印工具\开发文件\fonts"
SIZE = 4000
KERNEL = 9           # 闭运算核（像素，4000px 字身上约 2 单位）
MIN_H = 300

TARGETS = {
    "HWLeica-Regular.ttf": "AWX?",
    "HWLeica-Bold.ttf": "AWX?",
    "HWLeicaLight-Regular.ttf": "6tdfv2",
    "HWLeicaLight-Bold.ttf": "6tdfv2",
}


def run(fn, out=None, chars=None):
    src = f"{F}\\{fn}"
    dst = out or src
    font = TTFont(src)
    cmap = font.getBestCmap()
    glyf = font['glyf']
    core = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (KERNEL, KERNEL))
    todo = chars or TARGETS.get(fn, "")

    for ch in todo:
        if ord(ch) not in cmap:
            continue
        name = cmap[ord(ch)]
        g0 = glyf[name]
        g0.recalcBounds(glyf)
        ref_h = float(g0.yMax - g0.yMin)
        ref_x = float(g0.xMin)
        ref_y = float(g0.yMin)
        if ref_h < MIN_H:
            continue

        img = Image.new("L", (SIZE * 2, SIZE * 2), 0)
        ImageDraw.Draw(img).text((SIZE // 2, SIZE // 2), ch,
                                 font=ImageFont.truetype(src, SIZE), fill=255)
        m = (np.array(img) > 127).astype(np.uint8)
        ys, xs = np.where(m)
        if len(ys) == 0:
            continue
        m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        mc = cv2.morphologyEx(m, cv2.MORPH_CLOSE, core)

        cmds, _ = build_full3.vectorize(mc, float(mc.shape[0]), None, ref_h)
        if not cmds:
            continue
        tp = TTGlyphPen(None)
        for c, _x in cmds:
            for cmd in c:
                if cmd[0] == 'M':
                    tp.moveTo(cmd[1])
                elif cmd[0] == 'L':
                    tp.lineTo(cmd[1])
                elif cmd[0] == 'Q':
                    tp.qCurveTo(cmd[1], cmd[2])
                else:
                    tp.closePath()
        g = tp.glyph()
        g.recalcBounds(glyf)

        # 归一到原字形的尺寸与位置
        h = g.yMax - g.yMin
        if h > 1:
            s = ref_h / h
            if abs(s - 1) > 0.002:
                g.coordinates.scale((s, s))
                g.recalcBounds(glyf)
        g.coordinates.translate((ref_x - g.xMin, ref_y - g.yMin))
        g.recalcBounds(glyf)

        glyf[name] = g
        print(' ', ch, end='', flush=True)

    font.save(dst)
    print(f"\n{fn} → {dst}")


if __name__ == '__main__':
    fn = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    run(fn, out)
