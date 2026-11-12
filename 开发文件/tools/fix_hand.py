#!/usr/bin/env python3
"""修正两处：
1. 被扭转推宽的字母（尤其 M）压回原字宽
2. 小写 f/g/y 的收笔再收尖一些
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

sys.path.insert(0, r"D:\P9徕卡水印工具\开发文件\tools")
import build_full3

BASE = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Bold.ttf"
HAND = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaHand-Regular.ttf"
SIZE = 4000
SHARP = set()
K_SHARP = 0.30


def render(path, ch):
    f = ImageFont.truetype(path, SIZE)
    im = Image.new("L", (SIZE * 2, SIZE * 2), 0)
    ImageDraw.Draw(im).text((SIZE // 2, SIZE // 2), ch, font=f, fill=255)
    m = (np.array(im) > 127).astype(np.uint8)
    ys, xs = np.where(m)
    if len(ys) == 0:
        return None
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def pressure(mask, k):
    h, w = mask.shape
    out = np.zeros_like(mask)
    for y in range(h):
        t = 1.0 + k * (1.0 - 2.0 * y / max(1, h - 1))
        row = mask[y]
        if not row.any():
            continue
        idx = np.where(row)[0]
        runs = []
        s = idx[0]; prev = idx[0]
        for c in idx[1:]:
            if c - prev > 1:
                runs.append((s, prev)); s = c
            prev = c
        runs.append((s, prev))
        for (a, b) in runs:
            center = (a + b) / 2.0
            half = (b - a + 1) * t / 2.0
            na = max(0, int(round(center - half)))
            nb = min(w - 1, int(round(center + half)))
            if nb >= na:
                out[y, na:nb + 1] = 1
    out = cv2.medianBlur(out * 255, 5)
    return (out > 127).astype(np.uint8)


def main():
    base = TTFont(BASE)
    bc = base.getBestCmap()
    bg = base['glyf']

    font = TTFont(HAND)
    cmap = font.getBestCmap()
    glyf = font['glyf']
    gs = font.getGlyphSet()

    # 1) 宽度收敛
    clamped = 0
    for cp, name in sorted(cmap.items()):
        ch = chr(cp)
        if cp not in bc:
            continue
        g0 = glyf[name]
        g0.recalcBounds(glyf)
        b0 = bg[bc[cp]]
        b0.recalcBounds(bg)
        gw = g0.xMax - g0.xMin
        bw = b0.xMax - b0.xMin
        if bw <= 0 or gw <= bw * 1.03:
            continue
        s = bw / gw
        glyf[name].coordinates.scale((s, 1.0))
        glyf[name].recalcBounds(glyf)
        clamped += 1

    # 2) f/g/y 收尖
    sharpened = 0
    for cp, name in sorted(cmap.items()):
        ch = chr(cp)
        if ch not in SHARP:
            continue
        g0 = glyf[name]
        ref_h = float(g0.yMax - g0.yMin)
        ref_y = float(g0.yMin)
        m = render(HAND, ch)
        if m is None:
            continue
        m2 = pressure(m, K_SHARP)
        cmds, _ = build_full3.vectorize(m2, float(m2.shape[0]), None, ref_h)
        if not cmds:
            continue
        tp = TTGlyphPen(None)
        for c, _ in cmds:
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
        dy = ref_y - g.yMin
        if abs(dy) > 0.5:
            g.coordinates.translate((0, dy))
            g.recalcBounds(glyf)
        glyf[name] = g
        sharpened += 1

    font.save(HAND)
    print('压窄', clamped, '个；收尖', sharpened, '个；', os.path.getsize(HAND) // 1024, 'KB')


if __name__ == '__main__':
    main()
