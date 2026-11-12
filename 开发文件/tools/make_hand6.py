#!/usr/bin/env python3
"""给手写体加「运笔收放」：笔画沿纵向由粗变细，末端收尖。

在 4000px 上做行内宽度渐变，再做一次中值滤波去掉锯齿，最后重新描摹。
只处理较高的字形（数字/字母），标点保持原样。
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

SRC = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaHand-Regular.ttf"
DST = SRC
SIZE = 4000
K = 0.15          # 上端 +15%，下端 −15%
MIN_H = 300


def render(path, ch):
    f = ImageFont.truetype(path, SIZE)
    im = Image.new("L", (SIZE * 2, SIZE * 2), 0)
    ImageDraw.Draw(im).text((SIZE // 2, SIZE // 2), ch, font=f, fill=255)
    m = (np.array(im) > 127).astype(np.uint8)
    ys, xs = np.where(m)
    if len(ys) == 0:
        return None
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def pressure(mask):
    h, w = mask.shape
    out = np.zeros_like(mask)
    for y in range(h):
        t = 1.0 + K * (1.0 - 2.0 * y / max(1, h - 1))
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
    font = TTFont(SRC)
    cmap = font.getBestCmap()
    glyf = font['glyf']
    done = 0
    for cp, name in sorted(cmap.items()):
        ch = chr(cp)
        if ch == ' ':
            continue
        g0 = glyf[name]
        if not hasattr(g0, 'yMax'):
            continue
        ref_h = float(g0.yMax - g0.yMin)
        ref_y = float(g0.yMin)
        if ref_h < MIN_H:
            continue
        m = render(SRC, ch)
        if m is None:
            continue
        m2 = pressure(m)
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
        done += 1
        print(' ', ch, end='', flush=True)
    font.save(DST)
    print('\n处理', done, '个；', os.path.getsize(DST) // 1024, 'KB')


if __name__ == '__main__':
    main()
