"""Builds failures.jpg: four frames with the model's own words for that window."""
from PIL import Image, ImageDraw, ImageFont
F = lambda n: Image.open(f'frames/f_{n+1:03d}.jpg')
items = [(117, '1:57  camera bumped', 'Qwen: "Rinsing a plate under running water."'),
         (139, '2:19  camera bumped again', 'Gemma: "The person is rinsing glasses under the faucet."'),
         (172, '2:52  my head blocks the view', 'Qwen: "Rinsing the glass under running water." (I was scrubbing)'),
         (24, '0:24  nobody at the sink', 'Gemma: "The person is scrubbing the dirty plate with a sponge."')]
W, pad = 330, 16
fb = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 19); fr = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 17)
tiles = []
for n, a, b in items:
    im = F(n); im = im.resize((W, int(im.height * W / im.width)))
    t = Image.new('RGB', (W, im.height + 100), 'white'); t.paste(im, (0, 0)); d = ImageDraw.Draw(t)
    d.text((6, im.height + 8), a, fill='#171717', font=fb)
    line, y = '', im.height + 36
    for w in b.split():
        if line and d.textlength(line + ' ' + w, font=fr) > W - 12:
            d.text((6, y), line, fill='#b42318', font=fr); y += 20; line = w
        else:
            line = (line + ' ' + w).strip()
    d.text((6, y), line, fill='#b42318', font=fr)
    tiles.append(t)
out = Image.new('RGB', (len(tiles) * W + (len(tiles) + 1) * pad, max(t.height for t in tiles) + 2 * pad), '#f4f4f4')
for i, t in enumerate(tiles): out.paste(t, (pad + i * (W + pad), pad))
out.save('failures.jpg', quality=88)
n3 = 3
x3 = Image.new('RGB', (n3 * W + (n3 + 1) * pad, max(t.height for t in tiles[:n3]) + 2 * pad), '#f4f4f4')
for i, t in enumerate(tiles[:n3]): x3.paste(t, (pad + i * (W + pad), pad))
x3.save('failures_3.jpg', quality=88)
