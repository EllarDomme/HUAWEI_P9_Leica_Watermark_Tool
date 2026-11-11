#!/usr/bin/env python3
"""把字体导出为矢量文件。

输出：
  glyphs/<char>.svg   每字一个 SVG（viewBox 按字宽与字高）
  all-glyphs.svg      一张总览，全部字形按网格排列
"""
import os
import re
import html

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

FONT = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Smooth.ttf"
OUT = r"D:\P9徕卡水印工具\开发文件\vector"

GROUPS = [
    ("ABCDEFGHIJKLMNOPQRSTUVWXYZ", 13),
    ("abcdefghijklmnopqrstuvwxyz", 13),
    ("0123456789", 10),
    ("?!/.:-+=\"'\\ ", 12),
]


def glyph_svg(font, ch):
    cmap = font.getBestCmap()
    name = cmap.get(ord(ch))
    if not name:
        return None
    gs = font.getGlyphSet()
    pen = SVGPathPen(gs)
    gs[name].draw(pen)
    d = pen.getCommands()
    if not d:
        return None
    adv = font['hmtx'][name][0]
    upm = font['head'].unitsPerEm
    # 字体坐标 y 向上，SVG y 向下：翻转
    return dict(d=d, adv=adv, upm=upm)


def single(font, ch, path):
    info = glyph_svg(font, ch)
    if not info:
        return False
    upm = info['upm']
    y_top = int(upm * 0.8)
    y_bot = -int(upm * 0.3)
    h = y_top - y_bot
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 {y_bot} {info["adv"]} {h}" '
        f'width="{info["adv"]}" height="{h}">\n'
        f'  <g transform="translate(0,0) scale(1,-1)">\n'
        f'    <path d="{info["d"]}" fill="#000"/>\n'
        f'  </g>\n</svg>\n'
    )
    with open(path, 'w', encoding='utf-8') as f:
        f.write(svg)
    return True


def main():
    os.makedirs(os.path.join(OUT, 'glyphs'), exist_ok=True)
    font = TTFont(FONT)
    upm = font['head'].unitsPerEm

    count = 0
    for text, _ in GROUPS:
        for ch in text:
            if ch.isspace():
                continue
            fn = ch if ch.isalnum() else 'sym%02x' % ord(ch)
            if single(font, ch, os.path.join(OUT, 'glyphs', fn + '.svg')):
                count += 1
    print('single svg:', count)

    # 总览
    cell_w, cell_h = 250, 340
    pad = 30
    label_h = 44
    rows = []
    for text, cols in GROUPS:
        rows.append((text, cols))

    width = pad * 2 + max(cols for _, cols in rows) * cell_w
    height = pad * 2 + len(rows) * (cell_h + label_h)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="#faf9f6"/>',
    ]

    y = pad
    for text, cols in rows:
        for i, ch in enumerate(text):
            r, c = divmod(i, cols)
            info = glyph_svg(font, ch)
            if not info:
                continue
            x = pad + c * cell_w
            yy = y + r * (cell_h + label_h)
            # 把字形缩放到 cell 内：以字高 700 计
            scale = min((cell_h - 110) / 700.0, (cell_w - 46) / float(info['adv']))
            tx = x + (cell_w - info['adv'] * scale) / 2
            ty = yy + cell_h - 30
            parts.append(
                f'<g transform="translate({tx:.1f},{ty:.1f}) scale({scale:.4f},{-scale:.4f})">'
                f'<path d="{info["d"]}" fill="#17150f"/></g>'
            )
            label = 'sp' if ch == ' ' else ch
            parts.append(
                f'<text x="{x + cell_w/2:.1f}" y="{yy + cell_h + 30}" font-family="monospace" '
                f'font-size="22" fill="#9a978f" text-anchor="middle">{html.escape(label)}</text>'
            )
        y += ((len(text) + cols - 1) // cols) * (cell_h + label_h)

    parts.append('</svg>')
    out = os.path.join(OUT, 'all-glyphs.svg')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(parts))
    print('overview:', out, os.path.getsize(out) // 1024, 'KB')


if __name__ == '__main__':
    main()
