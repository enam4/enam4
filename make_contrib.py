"""Renders the last year of GitHub contributions as a dithered grid, in the header's two tones.

Reads the public calendar fragment (https://github.com/users/<user>/contributions), so it needs no
token. Each day becomes a square whose dither density follows GitHub's own activity level (0-4).
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
BG, INK = (0x0b, 0x0b, 0x0e), (0xec, 0xe6, 0xd6)
DENSITY = [None, 0.30, 0.52, 0.76, 1.0]   # by GitHub activity level 0..4; level 0 is a single dot
CELL = 4                                  # dither cell, same as the header and charts
W, PITCH, BOX = 1600, 28, 24              # canvas width, day pitch, day square
LEFT, TOP = 72, 128                       # multiples of CELL so squares sit on the dither grid

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

H = TOP + 7 * PITCH + 70
level = np.full((H, W), -1.0)
dot = BOX // 2 - 2


def square(x, y, density):
    if density is None:
        level[y + dot:y + dot + 4, x + dot:x + dot + 4] = 1.0   # quiet empty day
    else:
        level[y:y + BOX, x:x + BOX] = density


for day, lv in days.items():
    off = (day - start).days
    square(LEFT + (off // 7) * PITCH, TOP + (off % 7) * PITCH, DENSITY[lv])

BAYER = np.array([[0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26],
                  [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
                  [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
                  [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]]) / 64 + 1 / 128


lx = LEFT + weeks * PITCH - 5 * PITCH - 64
for i, dens in enumerate(DENSITY):
    square(lx + i * PITCH, TOP + 7 * PITCH + 24, dens)

yy, xx = np.indices(level.shape)
on = (level >= 0) & (level > BAYER[(yy // CELL) % 8, (xx // CELL) % 8])
img = Image.fromarray(np.where(on[..., None], np.array(INK, np.uint8), np.array(BG, np.uint8)).astype(np.uint8))

font_path = None
try:
    import matplotlib
    font_path = os.path.join(matplotlib.get_data_path(), "fonts", "ttf", "DejaVuSansMono.ttf")
except ImportError:
    pass
if not font_path or not os.path.exists(font_path):
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
big = ImageFont.truetype(font_path.replace("Mono.ttf", "Mono-Bold.ttf"), 30)
small = ImageFont.truetype(font_path, 19)
draw = ImageDraw.Draw(img)
draw.text((LEFT, 30), f"> {total} contributions in the last year", font=big, fill=INK)
for c in range(weeks):
    first = start + dt.timedelta(days=7 * c)
    month_start = next((first + dt.timedelta(days=k) for k in range(7)
                        if (first + dt.timedelta(days=k)).day == 1), None)
    if month_start and c < weeks - 2:
        draw.text((LEFT + c * PITCH, TOP - 34), month_start.strftime("%b").lower(), font=small, fill=INK)
for r, name in [(1, "mon"), (3, "wed"), (5, "fri")]:
    draw.text((LEFT - 56, TOP + r * PITCH + 1), name, font=small, fill=INK)
draw.text((lx - 74, TOP + 7 * PITCH + 27), "less", font=small, fill=INK)
draw.text((lx + 5 * PITCH + 8, TOP + 7 * PITCH + 27), "more", font=small, fill=INK)

pal = Image.new("P", (1, 1)); pal.putpalette(list(BG) + list(INK) + [0] * 762)
img.quantize(palette=pal, dither=Image.Dither.NONE).save(OUT, optimize=True)
print("wrote", OUT, img.size, f"{len(days)} days, {weeks} weeks, total {total}")
