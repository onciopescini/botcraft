"""Cover art itch.io 630x500 generata col brand Botcraft (no asset esterni)."""
from PIL import Image, ImageDraw

W, H = 630, 500
BG = (11, 14, 20)
BLU, ROSSO, ORO = (77, 163, 255), (255, 93, 93), (255, 217, 77)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)
# griglia arena
for x in range(40, 591, 23):
    d.line([(x, 60), (x, 440)], fill=(26, 35, 51))
for y in range(60, 441, 23):
    d.line([(40, y), (590, y)], fill=(26, 35, 51))
# alberi/oro decorativi
import random
rng = random.Random(7)
for _ in range(26):
    x, y = rng.randrange(50, 580), rng.randrange(70, 430)
    d.ellipse([x, y, x + 9, y + 9], fill=(63, 174, 90) if rng.random() < 0.7 else ORO)
# i due bot
d.rounded_rectangle([120, 200, 220, 300], 18, fill=BLU)
d.rounded_rectangle([410, 200, 510, 300], 18, fill=ROSSO)
d.ellipse([148, 232, 168, 252], fill="white")
d.ellipse([182, 232, 202, 252], fill="white")
d.ellipse([438, 232, 458, 252], fill="white")
d.ellipse([472, 232, 492, 252], fill="white")
d.ellipse([300, 235, 330, 265], fill=ORO)  # totem
# titolo
d.text((40, 370), "BOTCRAFT", fill=ORO)
d.text((40, 410), "programma il bot. lui va in guerra.", fill=(200, 200, 200))
img.save("site/assets/cover.png")
print("cover: site/assets/cover.png")
