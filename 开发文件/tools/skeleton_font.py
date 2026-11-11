#!/usr/bin/env python3
"""骨架描边法：把字形位图变成等宽单线轮廓。

1. 细化出骨架（中线）
2. 骨架转折线、简化
3. 用统一宽度描边（圆角接头），得到干净的轮廓
"""
import numpy as np
import cv2
import pathops


def skeleton(mask):
    return cv2.ximgproc.thinning(mask, thinningType=cv2.ximgproc.THINNING_ZHANGSUEN)


def stroke_width(mask):
    d = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    d = d[d > 0]
    if not len(d):
        return 6.0
    return float(np.median(d)) * 2.0


def neighbours(p, pts):
    x, y = p
    out = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            q = (x + dx, y + dy)
            if q in pts:
                out.append(q)
    return out


def trace_skeleton(sk):
    """骨架像素 -> 若干折线（端点/分叉之间）"""
    ys, xs = np.where(sk > 0)
    pts = set(zip(xs.tolist(), ys.tolist()))
    if not pts:
        return []

    deg = {p: len(neighbours(p, pts)) for p in pts}
    nodes = [p for p in pts if deg[p] != 2] or list(pts)[:1]
    ends = [p for p in pts if deg[p] == 1]

    lines = []
    visited = set()

    def walk(start, first):
        line = [start, first]
        prev, cur = start, first
        visited.add((start, first))
        visited.add((first, start))
        while cur not in nodes:
            nxt = [q for q in neighbours(cur, pts) if q != prev]
            if not nxt:
                break
            # 优先非对角
            nxt.sort(key=lambda q: abs(q[0] - cur[0]) + abs(q[1] - cur[1]))
            prev, cur = cur, nxt[0]
            if (prev, cur) in visited:
                break
            visited.add((prev, cur))
            visited.add((cur, prev))
            line.append(cur)
        return line

    for n in nodes:
        for nb in neighbours(n, pts):
            if (n, nb) in visited:
                continue
            line = walk(n, nb)
            if len(line) >= 4:
                lines.append(line)
    return lines


def vectorize(mask):
    sk = skeleton(mask)
    w = stroke_width(mask)
    lines = trace_skeleton(sk)

    path = pathops.Path()
    path.fillType = pathops.FillType.WINDING
    for line in lines:
        arr = np.array(line, dtype=np.float32).reshape(-1, 1, 2)
        approx = cv2.approxPolyDP(arr, 1.2, False).reshape(-1, 2)
        if len(approx) < 2:
            continue
        sub = pathops.Path()
        sub.moveTo(float(approx[0][0]), float(approx[0][1]))
        for p in approx[1:]:
            sub.lineTo(float(p[0]), float(p[1]))
        sub.stroke(w, pathops.LineCap.ROUND_CAP, pathops.LineJoin.ROUND_JOIN, 4.0)
        sub.convertConicsToQuads()
        path.addPath(sub)

    path.simplify()
    path.convertConicsToQuads()
    return path, w


if __name__ == '__main__':
    import sys
    img = cv2.imread(sys.argv[1], 0)
    _, m = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY)
    p, w = vectorize(m)
    print('stroke', w, 'segments', len(list(p.segments)))
