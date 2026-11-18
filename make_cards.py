"""Builds assets/cards/<repo>.png: dithered cards for the tool repos, one palette each.
(The five experiment repos make their own banner in their own make_figures.py.)"""
import numpy as np
import figstyle as fs

yy, xx = np.mgrid[0:100, 0:400] / np.array([100, 400])[:, None, None]
rng = np.random.default_rng(21)


def feed():
    """iweb: many thin streams on the left merging into one bright band on the right."""
    f = np.zeros_like(xx)
    for k in range(9):
        y0 = 0.08 + k * 0.105
        y = y0 + (0.5 - y0) * np.clip((xx - 0.3) / 0.6, 0, 1) ** 1.5
        f += np.exp(-((yy - y) / 0.018) ** 2) * (0.35 + 0.65 * xx)
    return np.clip(f, 0, 1) * 0.95 + 0.04


def tree():
    """FileTree: a branching tree drawn as dithered strokes."""
    f = np.zeros_like(xx)
    def branch(x, y, ang, length, depth):
        if depth == 0:
            return
        n = 40
        for t in np.linspace(0, 1, n):
            px, py = x + t * length * np.cos(ang) / 4, y + t * length * np.sin(ang)
            d = ((xx - px) * 4) ** 2 + (yy - py) ** 2
            f[:] = np.maximum(f, np.exp(-d / (2 * (0.004 + 0.003 * depth) ** 2 * 4)))
        x2, y2 = x + length * np.cos(ang) / 4, y + length * np.sin(ang)
        branch(x2, y2, ang - 0.45, length * 0.72, depth - 1)
        branch(x2, y2, ang + 0.45, length * 0.72, depth - 1)
    branch(0.86, 1.02, -np.pi / 2, 0.36, 6)
    return np.clip(f * 0.95 + 0.05 + 0.1 * yy, 0, 1)


def sparks():
    """Ideation-Skills: scattered sparks drawn in towards one point."""
    f = 0.05 + np.zeros_like(xx)
    cx, cy = 0.83, 0.5
    for _ in range(260):
        r = rng.random() ** 0.6 * 0.6
        a = rng.random() * 2 * np.pi
        px, py = cx + r * np.cos(a) / 2.2, cy + r * np.sin(a) * 1.4
        f += 0.9 * np.exp(-(((xx - px) * 4) ** 2 + (yy - py) ** 2) / (2 * 0.012 ** 2)) * (1 - r)
    f += 0.9 * np.exp(-(((xx - cx) * 4) ** 2 + (yy - cy) ** 2) / (2 * 0.06 ** 2))
    return np.clip(f, 0, 1)


def search():
    """KBsearch: concentric rings around a query point, like a ranked search radius."""
    d = np.sqrt(((xx - 0.82) * 4) ** 2 + (yy - 0.5) ** 2)
    rings = 0.5 + 0.5 * np.cos(2 * np.pi * d * 7)
    return np.clip(0.08 + rings * np.exp(-d * 1.2) * 0.9 + 0.5 * np.exp(-(d / 0.07) ** 2), 0, 1)


CARDS = [
    ("iweb", "coral", "one feed from everything you follow, ranked the way you choose.",
     "> javascript · self-hosted · github.com/enam4", feed),
    ("FileTree", "blue", "a file browser that is an actual tree.", "> rust · github.com/enam4", tree),
    ("Ideation-Skills", "yellow", "ai skills that turn vague motivation into buildable project ideas.",
     "> agent skills · github.com/enam4", sparks),
    ("KBsearch", "silver", "a /kb claude skill that answers support questions from a knowledge base.",
     "> python · claude agent skill · github.com/enam4", search),
]
for repo, pal, tag, meta, fn in CARDS:
    fs.theme(pal)
    fs.banner(f"{repo}.png", repo, tag, fn(), out="assets/cards", meta=meta)
