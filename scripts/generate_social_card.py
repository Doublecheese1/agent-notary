from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "agentsolis-social-card.png"
FONT = ROOT / "static" / "fonts" / "Manrope-Variable.ttf"

w, h = 1200, 630
image = Image.new("RGB", (w, h))
pixels = image.load()
left = (166, 234, 217)
middle = (112, 207, 224)
right = (61, 123, 215)
for x in range(w):
    t = x / (w - 1)
    if t < 0.48:
        u = t / 0.48
        a, b = left, middle
    else:
        u = (t - 0.48) / 0.52
        a, b = middle, right
    color = tuple(round(a[i] * (1 - u) + b[i] * u) for i in range(3))
    for y in range(h):
        pixels[x, y] = color

draw = ImageDraw.Draw(image, "RGBA")
navy = (11, 25, 48, 255)
cream = (255, 253, 248, 238)
sun = (246, 199, 91, 255)

for radius, alpha in ((250, 35), (180, 48), (105, 70)):
    cx, cy = 1010, 480
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=(255, 255, 255, alpha), width=3)

draw.ellipse((68, 58, 112, 102), outline=navy, width=3)
draw.ellipse((61, 69, 119, 91), outline=navy, width=2)
draw.ellipse((85, 75, 95, 85), fill=sun)

brand = ImageFont.truetype(str(FONT), 30)
title = ImageFont.truetype(str(FONT), 72)
body = ImageFont.truetype(str(FONT), 27)
mono = ImageFont.truetype(str(FONT), 19)
draw.text((135, 59), "AgentSolis Protocol", font=brand, fill=navy)
draw.text((68, 172), "Lock the job.", font=title, fill=navy)
draw.text((68, 255), "Pay when settled.", font=title, fill=navy)
draw.text((72, 373), "Native USDC escrow for agent-to-agent work.", font=body, fill=navy)

pill = (68, 460, 590, 530)
draw.rounded_rectangle(pill, radius=18, fill=cream, outline=(11, 25, 48, 40), width=2)
draw.text((96, 481), "AGREE  →  LOCK  →  DELIVER  →  SETTLE", font=mono, fill=navy)
draw.text((72, 570), "agentsolis.solists.com.tr", font=mono, fill=navy)

image.save(OUT, optimize=True)
print(OUT)
