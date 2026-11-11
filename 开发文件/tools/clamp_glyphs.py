#!/usr/bin/env python3
"""修正字形里超出基线的杂点（非下伸字母不应低于基线太多）。

P、X 这类字母在拟合时可能产生向下的控制点，小字号下会形成淡影，
看起来像“轮廓颜色不一样”。这里把非下伸字母的 y 坐标压回基线附近。
"""
import os

from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

SRC = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf"
DESC = set('gjpqy,;()[]{}|')

TARGETS = [SRC, r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Regular.ttf"]


def clamp_font(path, floor=-4.0):
    font = TTFont(path)
    cmap = font.getBestCmap()
    glyf = font['glyf']
    gs = font.getGlyphSet()
    fixed = 0
    for cp, name in cmap.items():
        ch = chr(cp)
        if ch in DESC:
            continue
        g = glyf[name]
        if not hasattr(g, 'yMin') or g.yMin >= floor:
            continue
        rec = DecomposingRecordingPen(gs)
        gs[name].draw(rec)
        pen = TTGlyphPen(None)
        for op, args in rec.value:
            if op == 'closePath':
                pen.closePath()
                continue
            moved = []
            for p in args:
                if isinstance(p, tuple) and len(p) == 2:
                    moved.append((p[0], max(p[1], floor)))
                else:
                    moved.append(p)
            getattr(pen, op)(*moved)
        glyf[name] = pen.glyph()
        fixed += 1
    font.save(path)
    print(os.path.basename(path), 'clamped glyphs:', fixed)


if __name__ == '__main__':
    for p in TARGETS:
        if os.path.exists(p):
            clamp_font(p)
