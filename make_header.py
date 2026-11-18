"""Builds assets/header.png: the five project palettes as dithered bands next to an ASCII title block."""
import io
import numpy as np
from PIL import Image
import figstyle as fs

W, H = 1600, 440
NEUTRAL = dict(bg="#0b0b0e", fg="#ececf1", dim="#a4a4b0")
PROJECTS = ["amber", "cyan", "magenta", "violet", "green", "yellow", "coral", "blue", "silver"]  # experiments first, then tools

# text layer
fs.theme("amber")  # any palette; only rcParams (mono font, no anti-aliasing) are used here
f = fs.plt.figure(figsize=(W / fs.DPI, H / fs.DPI), dpi=fs.DPI, facecolor=NEUTRAL["bg"])
ax = f.add_axes([0, 0, 1, 1]); ax.set_axis_off(); ax.set_xlim(0, W); ax.set_ylim(0, H)
ax.text(64, 380, "enam4", fontsize=40, fontweight="bold", color=NEUTRAL["fg"], va="top")
for k, line in enumerate(["> interpretability experiments on qwen2.5", "> plus tools and agent skills", "> erastnam.com"]):
    ax.text(64, 276 - k * 36, line, fontsize=13, color=NEUTRAL["dim"], va="top")
ax.text(64, 136, "> 5 experiments + 4 tools, 9 palettes", fontsize=13, color=NEUTRAL["fg"], va="top", fontweight="bold")
for i, name in enumerate(PROJECTS):
    ax.text(64 + i * 34, 92, "█", fontsize=16, color=fs.PALETTES[name]["acc"], va="top")
buf = io.BytesIO(); f.savefig(buf, format="png", dpi=fs.DPI, facecolor=NEUTRAL["bg"]); fs.plt.close(f)
base = np.asarray(Image.open(buf).convert("RGB")).copy()

# dithered bands: one per project accent, denser towards the bottom, with a slight wave
x0, bw = 920, 75
rng = np.random.default_rng(7)
for i, name in enumerate(PROJECTS):
    fs.theme(name)
    yy, xx = np.mgrid[0:H, 0:bw] / np.array([H, bw])[:, None, None]
    wave = 0.08 * np.sin(2 * np.pi * (yy * (1.2 + 0.15 * i) + rng.random()))
    level = np.clip(0.14 + 0.72 * yy + wave, 0, 1)
    level[:, :6] = 0  # dark gap between bands
    code = np.zeros((H, bw, 3), dtype=np.uint8)
    code[..., 0] = fs._CODE_R; code[..., 1] = 2; code[..., 2] = (np.round(level * 250) + 2).astype(np.uint8)
    band = np.asarray(fs._dither(Image.fromarray(code)))
    base[:, x0 + i * bw:x0 + (i + 1) * bw] = band
Image.fromarray(base).convert("P", palette=Image.ADAPTIVE, colors=32).save("assets/header.png", optimize=True)
print("wrote assets/header.png", base.shape)
