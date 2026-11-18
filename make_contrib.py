"""Renders the last year of GitHub contributions as dithered green squares, GitHub's palette in the header's dither.

Reads the public calendar fragment (https://github.com/users/<user>/contributions), so it needs no
token. Each day is a rounded square with a solid base, so its shape stays readable at any size; bright
green is ordered-dithered over the base, denser for higher GitHub activity levels (0-4).
usage: python make_contrib.py [user] [out.png]   (run daily by .github/workflows/contributions.yml)"""
import datetime as dt
import os
import re
import sys
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFont

USER = sys.argv[1] if len(sys.argv) > 1 else "enam4"
OUT = sys.argv[2] if len(sys.argv) > 2 else "contributions.png"

BG = (0x0b, 0x0b, 0x0e)          # same background as the header
INK = (0xec, 0xe6, 0xd6)         # headline, same ink as the header
MUTED = (0x8b, 0x94, 0x9e)       # month, weekday and legend labels
EMPTY = (0x16, 0x1b, 0x22)       # GitHub's dark-theme empty day
BRIGHT = (0x39, 0xd3, 0x53)      # GitHub's busiest-day green, the dither ink
BASE = EMPTY                     # every square sits on the empty grey and gets more green dots as activity rises
DENSITY = [0.0, 0.28, 0.52, 0.76, 1.0]   # by GitHub activity level 0..4

CELL = 4                          # dither cell, same as the header and charts
PITCH, BOX, RADIUS = 28, 24, 5    # day pitch, day square, corner radius
LEFT, TOP, RIGHT = 84, 120, 36    # multiples of CELL so squares sit on the dither grid

req = urllib.request.Request(f"https://github.com/users/{USER}/contributions",
                             headers={"User-Agent": "contribution-graph-renderer"})
html = urllib.request.urlopen(req, timeout=30).read().decode("utf8")
days = {}
for td in re.findall(r"<td[^>]*ContributionCalendar-day[^>]*>", html):
    d, lv = re.search(r'data-date="([\d-]+)"', td), re.search(r'data-level="(\d)"', td)
    if d and lv:
        days[dt.date.fromisoformat(d.group(1))] = int(lv.group(1))
if len(days) < 300:
    sys.exit(f"only parsed {len(days)} days; the page format may have changed")
total = re.search(r"([\d,]+)\s+contributions?\s+in the last year", html)
total = total.group(1) if total else str(len([1 for v in days.values() if v]))

start = min(days)
start -= dt.timedelta(days=(start.weekday() + 1) % 7)       # weeks start on Sunday, like GitHub
weeks = (max(days) - start).days // 7 + 1

W = LEFT + weeks * PITCH + RIGHT
H = TOP + 7 * PITCH + 64

# per-pixel activity level (255 = background), drawn as rounded squares
lvl_img = Image.new("L", (W, H), 255)
lvl_draw = ImageDraw.Draw(lvl_img)


def square(x, y, lv):
    lvl_draw.rounded_rectangle((x, y, x + BOX - 1, y + BOX - 1), radius=RADIUS, fill=lv)


for day, lv in days.items():
    off = (day - start).days
    square(LEFT + (off // 7) * PITCH, TOP + (off % 7) * PITCH, lv)

lx = LEFT + weeks * PITCH - 5 * PITCH - 64      # leaves room for "more" inside the right edge
ly = TOP + 7 * PITCH + 22
for i in range(5):
    square(lx + i * PITCH, ly, i)

BAYER = np.array([[0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26],
                  [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
                  [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
                  [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]]) / 64 + 1 / 128

lvl = np.array(lvl_img)
inside = lvl < 5
safe = np.where(inside, lvl, 0)
yy, xx = np.indices(lvl.shape)
dots = inside & (np.array(DENSITY)[safe] > BAYER[(yy // CELL) % 8, (xx // CELL) % 8])

rgb = np.empty((H, W, 3), np.uint8)
rgb[:] = BG
rgb[inside] = BASE
rgb[dots] = BRIGHT
img = Image.fromarray(rgb)
draw = ImageDraw.Draw(img)


def font(names, size):
    """First available font: matplotlib's DejaVu (CI), then Linux and Windows system paths."""
    dirs = []
    try:
        import matplotlib
        dirs.append(os.path.join(matplotlib.get_data_path(), "fonts", "ttf"))
    except ImportError:
        pass
    dirs += ["/usr/share/fonts/truetype/dejavu", r"C:\Windows\Fonts"]
    for d in dirs:
        for n in names:
            if os.path.exists(os.path.join(d, n)):
                return ImageFont.truetype(os.path.join(d, n), size)
    return ImageFont.load_default(size)


big = font(["DejaVuSansMono-Bold.ttf", "consolab.ttf"], 32)
small = font(["DejaVuSansMono.ttf", "consola.ttf"], 22)

draw.text((LEFT, 28), f"> {total} contributions in the last year", font=big, fill=INK)
for c in range(weeks):
    first = start + dt.timedelta(days=7 * c)
    month_start = next((first + dt.timedelta(days=k) for k in range(7)
                        if (first + dt.timedelta(days=k)).day == 1), None)
    if month_start and c < weeks - 2:
        draw.text((LEFT + c * PITCH, TOP - 32), month_start.strftime("%b").lower(), font=small, fill=MUTED)
for r, name in [(1, "mon"), (3, "wed"), (5, "fri")]:
    draw.text((LEFT - 62, TOP + r * PITCH + 1), name, font=small, fill=MUTED)
draw.text((lx - 62, ly + 1), "less", font=small, fill=MUTED)
draw.text((lx + 5 * PITCH + 4, ly + 1), "more", font=small, fill=MUTED)

img.save(OUT, optimize=True)
print("wrote", OUT, img.size, f"{len(days)} days, {weeks} weeks, total {total}")
