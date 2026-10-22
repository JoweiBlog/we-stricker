"""Build a stabilized, side-guard roar GIF from sixteen drawn poses."""
from pathlib import Path
from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parent
sheet = Image.open(ROOT / 'keyframes.png').convert('RGB')
w, h = sheet.size
frames = []
anchors = []
for r in range(4):
    for c in range(4):
        # Row boundaries follow the white gaps, not the uneven generated grid.
        top = [0, 260, 520, 788][r]
        bottom = [260, 520, 788, h][r]
        source = sheet.crop((round(c*w/4), top, round((c+1)*w/4), bottom))
        square = Image.new('RGB', (362, 362), 'white')
        square.paste(source, (0, 362-source.height))
        tile = square.resize((240, 240), Image.Resampling.LANCZOS)
        pixels = np.asarray(tile)
        # Dark toes, rather than the moving head or weapon, anchor the camera.
        dark = (pixels.min(axis=2) < 75) & (pixels.mean(axis=2) < 120)
        dark[:140] = False
        counts = dark.sum(axis=1)
        rows = np.flatnonzero(counts >= 4)
        if not len(rows):
            raise ValueError('No foot baseline detected')
        baseline = int(rows[-1])
        ys, xs = np.where(dark[max(140, baseline-7):baseline+1])
        center = float((np.quantile(xs, .03)+np.quantile(xs, .97))/2)
        anchors.append((center, baseline))
        canvas = Image.new('RGB', (240, 240), 'white')
        canvas.paste(tile, (round(120-center), 221-baseline))
        frames.append(canvas)

# Select a monotonic head-raising sequence; freeze one final pose to avoid redraw jitter.
frames = [frames[i] for i in [3, 4, 5, 6, 8, 7, 9, 10]]
# 50 ms per release pose (20 fps), with deliberate
# charging/final holds. Do not invent occluded limbs via optical flow.
durations = [70, 70, 70, 180, 50, 50, 50, 1200]
atlas = Image.new('RGB', (240*len(frames), 240), 'white')
for i, frame in enumerate(frames):
    atlas.paste(frame, (i*240, 0))
out = ROOT / '蓄力怒吼-直接蓄力版.gif'
for colors in (128, 96, 64, 48, 32):
    palette = atlas.quantize(colors=colors)
    indexed = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    indexed[0].save(out, save_all=True, append_images=indexed[1:], duration=durations,
                    loop=0, optimize=True, disposal=1)
    if out.stat().st_size <= 500_000:
        break
with Image.open(out) as gif:
    assert gif.size == (240, 240) and gif.info.get('loop') == 0
    assert out.stat().st_size <= 500_000
    print(f'{gif.n_frames} frames, {out.stat().st_size} bytes; anchors={anchors}')
review = Image.new('RGB', (240*8, 240*2), 'white')
for i, frame in enumerate(frames):
    review.paste(frame, ((i%8)*240, (i//8)*240))
review.save(ROOT / 'review.png')
