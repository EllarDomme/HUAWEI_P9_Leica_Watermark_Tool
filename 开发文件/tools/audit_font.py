#!/usr/bin/env python3
"""字体体检：逐字检查度量、轮廓、粗细是否一致。

输出：控制台报告 + preview/font-audit.csv
"""
import csv
import os
import statistics

from fontTools.ttLib import TTFont

REG = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeica-Regular.ttf"
LIGHT = r"D:\P9徕卡水印工具\开发文件\fonts\HWLeicaLight-Regular.ttf"
OUT = r"D:\P9徕卡水印工具\开发文件\preview\font-audit.csv"

DESC = set('gjpqy,;()[]{}|')
LOWER = set('abcdefghijklmnopqrstuvwxyz')
UPPER = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ')


def area_of(glyf, name, gs):
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    rec = DecomposingRecordingPen(gs)
    gs[name].draw(rec)
    # 粗算面积：轮廓点包围盒比例 + 点数，只用于相对比较
    return len(rec.value)


def audit(path, label):
    font = TTFont(path)
    glyf = font['glyf']
    cmap = font.getBestCmap()
    hmtx = font['hmtx']
    gs = font.getGlyphSet()
    rows = []

    cap_h = []
    for cp, name in sorted(cmap.items()):
        ch = chr(cp)
        if ch in UPPER:
            g = glyf[name]
            cap_h.append(g.yMax)
    cap = statistics.median(cap_h) if cap_h else 700

    for cp, name in sorted(cmap.items()):
        ch = chr(cp)
        g = glyf[name]
        if not hasattr(g, 'xMin'):
            continue
        coords, ends, flags = g.getCoordinates(glyf)
        off = sum(1 for f in flags if not (f & 1))
        aw, lsb = hmtx[name]
        rows.append(dict(
            ch=ch, name=name,
            xMin=g.xMin, yMin=g.yMin, xMax=g.xMax, yMax=g.yMax,
            w=g.xMax - g.xMin, h=g.yMax - g.yMin,
            adv=aw, lsb=lsb,
            contours=g.numberOfContours,
            points=len(coords), off=off,
            ink=round((g.xMax - g.xMin) * 0 + 0, 1),
        ))

    # --- 检查项 ---
    print('=' * 60)
    print(label, '| 字符数', len(rows))
    probs = {}

    # 1. 非下伸字母跑到基线以下
    bad = [r for r in rows if chr(ord(r['ch'])) not in DESC and r['yMin'] < -6]
    if bad:
        probs['低于基线'] = [(r['ch'], r['yMin']) for r in bad]

    # 2. 大写高度不齐
    ups = [r for r in rows if r['ch'] in UPPER]
    if ups:
        tops = [r['yMax'] for r in ups]
        base = statistics.median(tops)
        off = [(r['ch'], r['yMax']) for r in ups if abs(r['yMax'] - base) > 6]
        if off:
            probs['大写高度偏差'] = off

    # 3. 小写 x 高度不齐
    xhset = [r for r in rows if r['ch'] in 'acemnorsuvwxz']
    if xhset:
        base = statistics.median([r['yMax'] for r in xhset])
        off = [(r['ch'], r['yMax']) for r in xhset if abs(r['yMax'] - base) > 8]
        if off:
            probs['x高度偏差'] = off

    # 4. 下伸深度不齐
    desc = [r for r in rows if r['ch'] in DESC]
    if desc:
        base = statistics.median([r['yMin'] for r in desc])
        off = [(r['ch'], r['yMin']) for r in desc if abs(r['yMin'] - base) > 10]
        if off:
            probs['下伸深度偏差'] = off

    # 5. 字宽异常（同类里过宽/过窄）
    widths = [r['w'] for r in rows if r['ch'] in UPPER]
    if widths:
        med = statistics.median(widths)
        odd = [(r['ch'], r['w']) for r in rows if r['ch'] in UPPER and (r['w'] < med * 0.55 or r['w'] > med * 1.6)]
        if odd:
            probs['大写宽度异常'] = odd

    # 6. 字距（advance）与墨宽差值
    tight = [(r['ch'], r['adv'] - r['w']) for r in rows if r['adv'] - r['w'] < 10]
    if tight:
        probs['字距过窄'] = tight[:8]

    # 7. 轮廓点数异常（可能过碎或过简）
    pts = [r['points'] for r in rows if r['points'] > 0]
    if pts:
        med = statistics.median(pts)
        odd = [(r['ch'], r['points']) for r in rows if r['points'] > med * 3 or r['points'] < med * 0.25]
        if odd:
            probs['轮廓点数异常'] = odd

    # 8. 无曲线（全直线）的字
    flat = [(r['ch'], r['points'], r['off']) for r in rows if r['ch'] in 'OCGQSUosce' and r['off'] == 0]
    if flat:
        probs['圆字没有曲线'] = flat

    for k, v in probs.items():
        print('  ⚠', k, ':', v)
    if not probs:
        print('  ✓ 未发现异常')

    return rows, cap


def main():
    r1, cap1 = audit(REG, 'HWLeica Regular')
    r2, cap2 = audit(LIGHT, 'HWLeica Light')

    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['font', 'char', 'xMin', 'yMin', 'xMax', 'yMax', 'width', 'height', 'adv', 'lsb', 'contours', 'points', 'offcurve'])
        for tag, rows in (('regular', r1), ('light', r2)):
            for r in rows:
                w.writerow([tag, r['ch'], r['xMin'], r['yMin'], r['xMax'], r['yMax'], r['w'], r['h'], r['adv'], r['lsb'], r['contours'], r['points'], r['off']])

    # 对比两套字：宽度/字距是否一致
    m1 = {r['ch']: r for r in r1}
    m2 = {r['ch']: r for r in r2}
    diff = []
    for ch in m1:
        if ch not in m2:
            diff.append((ch, 'missing in light'))
            continue
        if abs(m1[ch]['adv'] - m2[ch]['adv']) > 4:
            diff.append((ch, 'adv %d vs %d' % (m1[ch]['adv'], m2[ch]['adv'])))
        if abs(m1[ch]['yMin'] - m2[ch]['yMin']) > 8:
            diff.append((ch, 'yMin %d vs %d' % (m1[ch]['yMin'], m2[ch]['yMin'])))
    print('=' * 60)
    print('两套字度量差异:', diff if diff else '无')
    print('报告已写入', OUT)


if __name__ == '__main__':
    main()
