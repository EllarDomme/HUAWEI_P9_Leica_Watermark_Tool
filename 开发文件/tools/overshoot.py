#!/usr/bin/env python3
"""给圆弧字补 overshoot：上下各溢出 1.5%。

平头字（2 5 7 E H）的顶底是满的，圆字（0 O C S）只有弧线顶点接触边界，
视觉上会显小，排版上要故意做高一点，看起来才一样高。
"""
import os

from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

FONTS = [
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf",
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Regular.ttf",
]

# 上下两端都是圆弧的字
ROUND = set('OCGQS0689oces')
OVERSHOOT = 0.03          # 总高度 +3%，上下各 1.5%


def apply(font, name, k):
    gs = font.getGlyphSet()
    rec = DecomposingRecordingPen(gs)
    gs[name].draw(rec)
    ys = [p[1] for op, args in rec.value for p in args if isinstance(p, tuple) and len(p) == 2]
    if not ys:
        return None
    y0, y1 = min(ys), max(ys)
    c = (y0 + y1) / 2.0
    pen = TTGlyphPen(None)
    for op, args in rec.value:
        if op == 'closePath':
            pen.closePath()
            continue
        moved = []
        for p in args:
            if isinstance(p, tuple) and len(p) == 2:
                moved.append((p[0], c + (p[1] - c) * k))
            else:
                moved.append(p)
        getattr(pen, op)(*moved)
    return pen.glyph()


def main():
    for path in FONTS:
        font = TTFont(path)
        cmap = font.getBestCmap()
        glyf = font['glyf']
        n = 0
        for cp, name in cmap.items():
            ch = chr(cp)
            if ch not in ROUND:
                continue
            g = glyf[name]
            if not hasattr(g, 'yMin'):
                continue
            new = apply(font, name, 1.0 + OVERSHOOT)
            if new is not None:
                glyf[name] = new
                n += 1
        font.save(path)
        print(os.path.basename(path), 'overshoot applied:', n)


if __name__ == '__main__':
    main()
