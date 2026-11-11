#!/usr/bin/env python3
"""从 Roboto 派生一款水印专用字体 P9 Sans：
- 整体压窄 6%（DIN 式的瘦长感）
- 点状符号（. : i j ; !）改成方点，去掉圆润感
- 重命名字体，保留 Apache 2.0 许可
"""
import os
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib.woff2 import compress as woff2_compress

SCALE_X = 0.94
DOT_GLYPHS = {'.', ':', 'i', 'j', ';', '!'}
FAMILY = 'P9 Sans'

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, '..', 'fonts')
SRC = {
    'Regular': ('Roboto-Regular.ttf', 400, 'P9Sans-Regular'),
    'Bold': ('Roboto-Bold.ttf', 700, 'P9Sans-Bold'),
}


def contours_of(rec):
    """把 recording pen 的扁平指令切成一条条轮廓"""
    out, cur = [], None
    for op, args in rec.value:
        if op == 'moveTo':
            if cur:
                out.append(cur)
            cur = [(op, args)]
        elif cur is not None:
            cur.append((op, args))
    if cur:
        out.append(cur)
    return out


def bbox_of(contour):
    xs, ys = [], []
    for op, args in contour:
        for pt in args:
            if isinstance(pt, tuple) and len(pt) == 2:
                xs.append(pt[0])
                ys.append(pt[1])
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def is_dot(contour):
    bb = bbox_of(contour)
    if not bb:
        return False
    x0, y0, x1, y1 = bb
    w, h = x1 - x0, y1 - y0
    return 0 < w < 130 and 0 < h < 130 and abs(w - h) < 45


def square_contour(bb, k=0.92):
    x0, y0, x1, y1 = bb
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hw, hh = (x1 - x0) / 2 * k, (y1 - y0) / 2 * k
    pts = [(cx - hw, cy - hh), (cx + hw, cy - hh), (cx + hw, cy + hh), (cx - hw, cy + hh)]
    return [('moveTo', (pts[0],)), ('lineTo', (pts[1],)), ('lineTo', (pts[2],)),
            ('lineTo', (pts[3],)), ('closePath', ())]


def build(style):
    src_name, weight, psname = SRC[style]
    path = os.path.join(FONT_DIR, src_name)
    font = TTFont(path)
    glyph_set = font.getGlyphSet()
    glyf = font['glyf']
    hmtx = font['hmtx']

    new_glyphs = {}
    for name in font.getGlyphOrder():
        rec = DecomposingRecordingPen(glyph_set)
        glyph_set[name].draw(rec)

        pen = TTGlyphPen(None)
        for contour in contours_of(rec):
            bb = bbox_of(contour)
            if name in DOT_GLYPHS and is_dot(contour):
                for op, args in square_contour(bb):
                    getattr(pen, op)(*args) if op != 'closePath' else pen.closePath()
                continue
            for op, args in contour:
                if op == 'closePath':
                    pen.closePath()
                    continue
                moved = []
                for pt in args:
                    if isinstance(pt, tuple) and len(pt) == 2:
                        moved.append((pt[0] * SCALE_X, pt[1]))
                    else:
                        moved.append(pt)
                getattr(pen, op)(*moved)

        try:
            new_glyphs[name] = pen.glyph()
        except Exception:
            new_glyphs[name] = glyf[name]

        aw, lsb = hmtx[name]
        hmtx[name] = (int(round(aw * SCALE_X)), int(round(lsb * SCALE_X)))

    glyf.glyphs = new_glyphs
    for name in new_glyphs:
        glyf[name] = new_glyphs[name]

    # 改名
    nt = font['name']
    for rec in list(nt.names):
        if rec.nameID in (1, 16):
            rec.string = FAMILY
        elif rec.nameID in (2, 17):
            rec.string = style
        elif rec.nameID == 4:
            rec.string = FAMILY + (' ' + style if style != 'Regular' else '')
        elif rec.nameID == 6:
            rec.string = psname
        elif rec.nameID == 3:
            rec.string = psname + ';P9'
    font['OS/2'].usWeightClass = weight

    out_ttf = os.path.join(FONT_DIR, psname + '.ttf')
    font.save(out_ttf)

    woff = TTFont(out_ttf)
    woff2_path = os.path.join(FONT_DIR, psname + '.woff2')
    woff.flavor = 'woff2'
    woff.save(woff2_path)
    return out_ttf, woff2_path


if __name__ == '__main__':
    for style in SRC:
        ttf, w2 = build(style)
        print(style, os.path.basename(ttf), os.path.getsize(ttf) // 1024, 'KB ->',
              os.path.basename(w2), os.path.getsize(w2) // 1024, 'KB')
