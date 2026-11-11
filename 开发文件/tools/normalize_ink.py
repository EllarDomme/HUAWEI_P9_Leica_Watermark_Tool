#!/usr/bin/env python3
"""按“实际渲染高度”归一化，而不是按控制点包围盒。

曲线控制点可能比真实笔画高出很多，用 bbox 会误判。
这里把二次曲线采样成折线，得到真实的上下边界再缩放。
"""
import os

from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

FONTS = [
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf",
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Regular.ttf",
]

CAP = 700.0
XH = 500.0
DESC = set('gjpqy,;()[]{}|')
XH_LETTERS = set('acemnorsuvwxz')
UPPER = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
DIGITS = set('0123456789')
LOWER_ASC = set('bdfhklt')
ROUND = set('OCGQS0689oces')

SAMPLES = 24


def sample_contour(ops):
    """把一段轮廓的指令采样成点序列"""
    pts = []
    cur = None
    start = None
    for op, args in ops:
        if op == 'moveTo':
            cur = args[0]
            start = cur
            pts.append(cur)
        elif op == 'lineTo':
            cur = args[0]
            pts.append(cur)
        elif op == 'qCurveTo':
            control = args[0]
            for i in range(1, len(args)):
                end = args[i]
                for k in range(1, SAMPLES + 1):
                    t = k / float(SAMPLES)
                    mt = 1 - t
                    pts.append((
                        mt * mt * cur[0] + 2 * mt * t * control[0] + t * t * end[0],
                        mt * mt * cur[1] + 2 * mt * t * control[1] + t * t * end[1],
                    ))
                cur = end
                control = end
        elif op == 'curveTo':
            for i in range(SAMPLES):
                t = (i + 1) / float(SAMPLES)
                mt = 1 - t
                p = args[-1]
                c1, c2 = args[0], args[1]
                pts.append((
                    mt**3 * cur[0] + 3 * mt * mt * t * c1[0] + 3 * mt * t * t * c2[0] + t**3 * p[0],
                    mt**3 * cur[1] + 3 * mt * mt * t * c1[1] + 3 * mt * t * t * c2[1] + t**3 * p[1],
                ))
            cur = args[-1]
        elif op == 'closePath':
            if start:
                pts.append(start)
    return pts


def tight_bounds(font, name):
    gs = font.getGlyphSet()
    rec = DecomposingRecordingPen(gs)
    gs[name].draw(rec)
    groups, cur = [], []
    for op, args in rec.value:
        if op == 'moveTo' and cur:
            groups.append(cur)
            cur = []
        cur.append((op, args))
    if cur:
        groups.append(cur)

    ys = []
    for g in groups:
        ys.extend(p[1] for p in sample_contour(g))
    if not ys:
        return None
    return min(ys), max(ys)


def transform(font, name, target_bottom, target_top):
    gs = font.getGlyphSet()
    rec = DecomposingRecordingPen(gs)
    gs[name].draw(rec)
    b = tight_bounds(font, name)
    if not b:
        return None
    y0, y1 = b
    h = y1 - y0
    if h <= 1:
        return None
    k = (target_top - target_bottom) / h
    pen = TTGlyphPen(None)
    for op, args in rec.value:
        if op == 'closePath':
            pen.closePath()
            continue
        moved = []
        for p in args:
            if isinstance(p, tuple) and len(p) == 2:
                moved.append((p[0], target_bottom + (p[1] - y0) * k))
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
            if ch in ROUND:
                target = (-10.0, 710.0)          # 圆字上下各溢出 1.5%
            elif ch in UPPER or ch in DIGITS or ch in LOWER_ASC:
                target = (0.0, 700.0)
            elif ch in XH_LETTERS:
                target = (0.0, 500.0)
            else:
                continue
            g = transform(font, name, target[0], target[1])
            if g is not None:
                glyf[name] = g
                n += 1
        font.save(path)
        print(os.path.basename(path), 'normalized by ink:', n)


if __name__ == '__main__':
    main()
