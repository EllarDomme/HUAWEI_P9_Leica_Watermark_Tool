#!/usr/bin/env python3
"""统一度量：大写/数字 700 高、x 高度 500、基线 0。

粗体与细体都会跑一遍，保证两套字的高度、基线完全一致，
切换字体时文字不会上下跳。
"""
import os

from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

REG = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf"
LIGHT = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Regular.ttf"

CAP = 700.0
XH = 500.0
DESC = set('gjpqy,;()[]{}|')
XH_LETTERS = set('acemnorsuvwxz')
UPPER = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
DIGITS = set('0123456789')
LOWER_ASC = set('bdfhklt')


def rebuild(gs, name, target_h, target_bottom=0.0):
    rec = DecomposingRecordingPen(gs)
    gs[name].draw(rec)
    ys = [p[1] for op, args in rec.value for p in args if isinstance(p, tuple) and len(p) == 2]
    if not ys:
        return None
    y0, y1 = min(ys), max(ys)
    h = y1 - y0
    if h <= 1:
        return None
    sy = target_h / h
    pen = TTGlyphPen(None)
    for op, args in rec.value:
        if op == 'closePath':
            pen.closePath()
            continue
        moved = []
        for p in args:
            if isinstance(p, tuple) and len(p) == 2:
                moved.append((p[0], (p[1] - y0) * sy + target_bottom))
            else:
                moved.append(p)
        getattr(pen, op)(*moved)
    return pen.glyph()


def normalize(path):
    font = TTFont(path)
    cmap = font.getBestCmap()
    glyf = font['glyf']
    gs = font.getGlyphSet()
    n = 0
    for cp, name in cmap.items():
        ch = chr(cp)
        if ch in UPPER or ch in DIGITS:
            g = rebuild(gs, name, CAP)
        elif ch in XH_LETTERS:
            g = rebuild(gs, name, XH)
        elif ch in LOWER_ASC:
            g = rebuild(gs, name, CAP)      # 升部与字高同高
        else:
            continue
        if g is not None:
            glyf[name] = g
            n += 1
    font.save(path)
    print(os.path.basename(path), 'normalized:', n)


def align_descenders(ref_path, path):
    """下伸字母只做平移，让两套字的下伸深度一致"""
    ref = TTFont(ref_path)
    rcmap = ref.getBestCmap()
    rglyf = ref['glyf']
    font = TTFont(path)
    cmap = font.getBestCmap()
    glyf = font['glyf']
    gs = font.getGlyphSet()
    n = 0
    for cp, name in cmap.items():
        ch = chr(cp)
        pass
        rname = rcmap.get(cp)
        if not rname:
            continue
        rg = rglyf[rname]
        g = glyf[name]
        if not hasattr(g, 'yMin') or not hasattr(rg, 'yMin'):
            continue
        dy = rg.yMin - g.yMin
        if abs(dy) < 1:
            continue
        rec = DecomposingRecordingPen(gs)
        gs[name].draw(rec)
        pen = TTGlyphPen(None)
        for op, args in rec.value:
            if op == 'closePath':
                pen.closePath()
                continue
            moved = []
            for q in args:
                if isinstance(q, tuple) and len(q) == 2:
                    moved.append((q[0], q[1] + dy))
                else:
                    moved.append(q)
            getattr(pen, op)(*moved)
        glyf[name] = pen.glyph()
        n += 1
    font.save(path)
    print(os.path.basename(path), 'descenders aligned:', n)


if __name__ == '__main__':
    normalize(REG)
    normalize(LIGHT)
    align_descenders(REG, LIGHT)  # 现在对全部字符生效
