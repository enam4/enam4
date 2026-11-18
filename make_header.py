"""Builds assets/header.png: a procedurally painted dusk landscape, ordered-dithered into a small
colour ramp, with the name set on top.

The scene is computed as a single brightness field (0 = darkest, 1 = brightest). Each pixel is then
dithered between the two nearest colours of RAMP with an 8x8 Bayer matrix, so every gradient in
the sky, haze and water turns into a dither pattern."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib

W, H = 1600, 520
CELL = 3                       # dither cell in px
SEED = 4
NAME = "enam4"

# dusk ramp, darkest to brightest
RAMP = ["#06050d", "#120c24", "#24143f", "#3d1d5c", "#652a74", "#94357a", "#c74a74",
        "#ee6f63", "#ff9b5e", "#ffc77a", "#fff0c4"]

rng = np.random.default_rng(SEED)
y, x = np.mgrid[0:H, 0:W].astype(float)
X, Y = x / W, y / H


def noise1d(n, octaves=6, persistence=0.55, base=6):
    """Fractal 1-D value noise on [0,1] sampled at n points, range about [-1, 1]."""
    t = np.linspace(0, 1, n)
    out, amp, total = np.zeros(n), 1.0, 0.0
    for o in range(octaves):
        k = base * 2 ** o
        pts = rng.uniform(-1, 1, k + 2)
        xs = np.linspace(0, 1, k + 2)
        out += amp * np.interp(t, xs, pts); total += amp; amp *= persistence
    return out / total


def smooth(a, k):
    return np.convolve(np.pad(a, k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), mode="same")[k:-k]


HORIZON = 0.66                 # where the far haze meets the lake
SUN = (0.70, 0.40, 0.115)      # centre x, centre y, radius (y and r as fractions of H)

# ---------------------------------------------------------------- sky
v = 0.06 + 0.62 * np.clip(Y / HORIZON, 0, 1) ** 1.8
dx, dy = (X - SUN[0]) * W / H, Y - SUN[1]
d = np.sqrt(dx ** 2 + dy ** 2)
v += 0.42 * np.exp(-d / 0.20) + 0.18 * np.exp(-d / 0.55)

# stars in the upper sky, away from the glow
stars = (rng.random((H, W)) < 0.0016) & (Y < 0.38) & (d > 0.35)
v = np.where(stars, np.maximum(v, 0.55 + 0.35 * rng.random((H, W))), v)

# sun disc, cut by thin cloud bands
v = np.where(d < SUN[2], 0.99, v)
for yc, th, half, ph in [(0.355, 0.005, 0.10, 0.0), (0.395, 0.008, 0.15, 1.7), (0.43, 0.010, 0.19, 3.1)]:
    edge = yc + 0.006 * np.sin(X * 31 + ph) + 0.003 * np.sin(X * 97 + ph)
    taper = np.clip(1 - (np.abs(X - SUN[0] - 0.02 * np.sin(ph)) / half) ** 2, 0, 1)
    band = np.abs(Y - edge) < th * taper
    v = np.where(band, v * 0.5, v)

# long wisps of high cloud, lit from below near the sun
for yc, amp, ph in [(0.16, 0.025, 0.4), (0.24, 0.02, 2.2), (0.31, 0.018, 5.0)]:
    curve = yc + amp * np.sin(X * 3.1 + ph) + 0.008 * np.sin(X * 17 + ph * 2)
    thick = 0.012 * (0.5 + 0.5 * np.sin(X * 5 + ph)) ** 2
    wisp = np.exp(-((Y - curve) / (thick + 1e-4)) ** 2)
    v += 0.18 * wisp * (0.5 + 0.8 * np.exp(-np.abs(X - SUN[0]) / 0.25))

# ---------------------------------------------------------------- mountains, far to near
def ridged(n, octaves=8, persistence=0.52, base=3):
    """Ridged noise in [0,1]: sharp peaks, soft valleys."""
    r = 1 - np.abs(noise1d(n, octaves, persistence, base))
    return (r - r.min()) / (r.max() - r.min()) ** 1.0


layers = [  # base height, amplitude, roughness, brightness, haze
    (0.62, 0.30, 0.50, 0.52, 0.14),
    (0.66, 0.28, 0.54, 0.40, 0.14),
    (0.71, 0.26, 0.56, 0.30, 0.12),
    (0.77, 0.20, 0.58, 0.15, 0.08),
]
for base, amp, rough, bright, haze in layers:
    notch = 1 - 0.85 * np.exp(-((X[0] - SUN[0]) / 0.10) ** 2)   # a valley for the sun to set into
    ridge = smooth(base - amp * notch * ridged(W, persistence=rough) ** 1.6, 1)
    below = Y > ridge[None, :]
    depth = np.clip((Y - ridge[None, :]) / 0.12, 0, 1)
    shade = bright + haze * (1 - depth)                     # lit ridgeline, darker below
    rim = np.exp(-np.abs(X - SUN[0]) / 0.18) * np.exp(-((Y - ridge[None, :]) * H / 3.0) ** 2)
    v = np.where(below, shade + 0.18 * rim, v)
    v += 0.10 * haze * np.exp(-((Y - (base + 0.02)) / 0.012) ** 2) * ~below   # valley mist

# ---------------------------------------------------------------- lake with a broken reflection
LAKE = 0.80
water = Y > LAKE
src_y = np.clip((2 * LAKE - Y) * H, 0, H - 1)
wobble = (4 * np.sin(Y * H * 0.9) + 3 * np.sin(Y * H * 0.37 + X * 9)) * np.clip((Y - LAKE) / 0.2, 0, 1)
src_x = np.clip(x + wobble, 0, W - 1)
refl = v[src_y.astype(int), src_x.astype(int)]
row_len = rng.uniform(0.15, 1.0, H)[:, None] * (rng.random(H)[:, None] < 0.45)
row_off = rng.normal(0, 0.012, H)[:, None]
glitter = np.abs(X - SUN[0] - row_off) < (0.015 + 0.30 * (Y - LAKE)) * row_len
v = np.where(water, 0.55 * refl + 0.04 + 0.6 * glitter * np.exp(-(Y - LAKE) / 0.2), v)

# foreground shore and pines, pure silhouette
shore = 0.94 - 0.05 * (0.5 + 0.5 * noise1d(W, octaves=5, base=2)) - 0.07 * np.clip(0.3 - X[0], 0, 1) / 0.3         - 0.05 * np.clip(X[0] - 0.85, 0, 1) / 0.15
fg = Y > shore[None, :]
trees = [(rng.uniform(0, 0.30), rng.uniform(0.16, 0.42)) for _ in range(22)] +         [(rng.uniform(0.87, 1.0), rng.uniform(0.14, 0.34)) for _ in range(10)]
for px, ph in trees:
    pw = ph * rng.uniform(0.16, 0.22)                     # half-width at the base, in units of H
    top = shore[int(px * (W - 1))] - ph
    t = np.clip((Y - top) / ph, 0, 1)
    tiers = 5 + int(ph * 18)
    saw = 0.55 + 0.45 * ((t * tiers) % 1)                 # each tier flares out then steps in
    half = pw * t * saw
    trunk = (np.abs(X - px) * W / H < 0.004) & (t > 0.85)
    fg |= ((np.abs(X - px) * W / H < half) & (Y > top) & (t < 0.9)) | trunk
v = np.where(fg, 0.015, v)
v = np.clip(v, 0, 1)

# ---------------------------------------------------------------- dither into the ramp
BAYER = np.array([[0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26],
                  [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
                  [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
                  [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]]) / 64 + 1 / 128
cols = np.array([[int(c[i:i + 2], 16) for i in (1, 3, 5)] for c in RAMP], dtype=np.uint8)
s = v * (len(RAMP) - 1)
lo = np.floor(s).astype(int)
thr = BAYER[(y.astype(int) // CELL) % 8, (x.astype(int) // CELL) % 8]
idx = np.clip(lo + ((s - lo) > thr), 0, len(RAMP) - 1)
img = Image.fromarray(cols[idx])

# ---------------------------------------------------------------- the name
font_path = os.path.join(matplotlib.get_data_path(), "fonts", "ttf", "DejaVuSansMono-Bold.ttf")
font = ImageFont.truetype(font_path, 124)
draw = ImageDraw.Draw(img)
tx, ty = 92, 60
draw.text((tx + 8, ty + 8), NAME, font=font, fill=RAMP[1])  # hard shadow
draw.text((tx, ty), NAME, font=font, fill=RAMP[-1])
pal = Image.new("P", (1, 1))
pal.putpalette([c for row in cols.tolist() for c in row] + [0] * (768 - 3 * len(RAMP)))
img = img.quantize(palette=pal, dither=Image.Dither.NONE)   # exact ramp colours, no merging
img.save("assets/header.png", optimize=True)
print("wrote assets/header.png", img.size)
