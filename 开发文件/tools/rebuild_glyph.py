#!/usr/bin/env python3
"""用更细的拟合参数重建指定字母（默认 P、X）。

RDP_EPS 1.8 → 0.8，FIT_TOL 1.2 → 0.7，
这样圆角处会有足够多的曲线点，小字号下边缘不再发白、发硬。
"""
import sys

import numpy as np
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen

sys.path.insert(0, r"D:\P9徕卡水印工具\开发文件\tools")
import build_full3
import build_v7

FONTS = [
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf",
    r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Regular.ttf",
]
SRC = r"E:\DeskTop\字符抠图高清版\chars"
TARGETS = [('P', 'upper'), ('X', 'upper')]
CAP = 700.0
DESC = set('gjpqy,;()[]{}|')


def main():
    build_full3.RDP_EPS = 0.8
    build_full3.FIT_TOL = 0.7

    masks = {}
    caps = []
    for ch, folder in TARGETS:
        path = r"%s\%s\%s.png" % (SRC, folder, ch)
        m = build_v7.load_mask(path)
        masks[ch] = m
        caps.append(m.shape[0] - 6)
    cap_px = float(np.median(caps))

    for fp in FONTS:
        font = TTFont(fp)
        cmap = font.getBestCmap()
        glyf = font['glyf']
        hmtx = font['hmtx']
        for ch, _ in TARGETS:
            m = masks[ch]
            h = m.shape[0] - 6
            base = h + 3.0
            cmds_list, ink_w = build_full3.vectorize(m, cap_px, base, CAP)
            if not cmds_list:
                print('  empty', ch)
                continue
            tpen = TTGlyphPen(None)
            for cmds, _ in cmds_list:
                for cmd in cmds:
                    if cmd[0] == 'M':
                        tpen.moveTo(cmd[1])
                    elif cmd[0] == 'L':
                        tpen.lineTo(cmd[1])
                    elif cmd[0] == 'Q':
                        tpen.qCurveTo(cmd[1], cmd[2])
                    else:
                        tpen.closePath()
            gly = tpen.glyph()
            gly.recalcBounds(glyf)
            name = cmap[ord(ch)]
            old_adv = hmtx[name][0]
            glyf[name] = gly
            # 保持原字距，避免整行变宽
            hmtx[name] = (old_adv, hmtx[name][1])
            print('  %s %s  点数=%d 高=%d' % (fp.split('\\')[-1], ch,
                  len(gly.getCoordinates(glyf)[0]), gly.yMax - gly.yMin))
        font.save(fp)


if __name__ == '__main__':
    main()
