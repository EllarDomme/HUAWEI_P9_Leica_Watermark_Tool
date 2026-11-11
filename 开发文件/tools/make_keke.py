#!/usr/bin/env python3
"""用 Barlow Condensed 派生「K刻」水印字体（免费可分发）。

处理：
1. 横向压窄 8%（刻字感）
2. 字高放 2%（更瘦长）
3. 点状符号（. : i j ; !）改成方点
4. M 的中缝尖角压到基线
5. 重命名字体为 K刻 / Keke，保留 Barlow 的 OFL 许可

用法：python make_keke.py
输出：开发文件/fonts/Keke-Regular.woff2、Keke-Bold.woff2
前置：pip install fonttools brotli，并把 Barlow Condensed 的
      BarlowCondensed.ttf / BarlowCondensedBold.ttf 放在同目录（可用
      fontsource 下载后转 ttf）。
"""
import os
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

DOT = {'.', ':', 'i', 'j', ';', '!'}
SX, SY = 0.92, 1.02
FAMILY = 'K刻'

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, '..', 'fonts')
SRC = [
    ('BarlowCondensed.ttf', 'Regular', 'Keke-Regular', 400),
    ('BarlowCondensedBold.ttf', 'Bold', 'Keke-Bold', 700),
]


def contours_of(rec):
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
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


def square_contour(bb, k=0.92):
    x0, y0, x1, y1 = bb
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hw, hh = (x1 - x0) / 2 * k, (y1 - y0) / 2 * k
    return [('moveTo', ((cx - hw, cy - hh),)), ('lineTo', ((cx + hw, cy - hh),)),
            ('lineTo', ((cx + hw, cy + hh),)), ('lineTo', ((cx - hw, cy + hh),)),
            ('closePath', ())]


def build(src_name, style, out_name, weight):
    font = TTFont(os.path.join(FONT_DIR, src_name))
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
            if name in DOT and bb and 0 < bb[2] - bb[0] < 130 and 0 < bb[3] - bb[1] < 130:
                for op, args in square_contour(bb):
                    pen.closePath() if op == 'closePath' else getattr(pen, op)(*args)
                continue
            for op, args in contour:
                if op == 'closePath':
                    pen.closePath()
                    continue
                moved = []
                for pt in args:
                    if isinstance(pt, tuple) and len(pt) == 2:
                        x, y = pt
                        y2 = y * SY
                        if name == 'M' and 0 < y2 <= 16:
                            y2 = 0
                        moved.append((x * SX, y2))
                    else:
                        moved.append(pt)
                getattr(pen, op)(*moved)

        try:
            new_glyphs[name] = pen.glyph()
        except Exception:
            new_glyphs[name] = glyf[name]

        aw, lsb = hmtx[name]
        hmtx[name] = (int(round(aw * SX)), int(round(lsb * SX)))

    for n, g in new_glyphs.items():
        glyf[n] = g

    nt = font['name']
    for rec in list(nt.names):
        if rec.nameID in (1, 16):
            rec.string = FAMILY
        elif rec.nameID in (2, 17):
            rec.string = style
        elif rec.nameID == 4:
            rec.string = FAMILY + (' ' + style if style != 'Regular' else '')
        elif rec.nameID == 6:
            rec.string = out_name
    font['OS/2'].usWeightClass = weight

    ttf_path = os.path.join(FONT_DIR, out_name + '.ttf')
    font.save(ttf_path)

    web = TTFont(ttf_path)
    web.flavor = 'woff2'
    woff2_path = os.path.join(FONT_DIR, out_name + '.woff2')
    web.save(woff2_path)
    return ttf_path, woff2_path


if __name__ == '__main__':
    for src, style, out, weight in SRC:
        ttf, w2 = build(src, style, out, weight)
        print(style, os.path.basename(ttf), os.path.getsize(ttf) // 1024, 'KB ->',
              os.path.basename(w2), os.path.getsize(w2) // 1024, 'KB')
