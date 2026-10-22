"""Assemble twelve drawn action poses without optical-flow ghosting."""
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
from PIL import Image

ROOT = Path(__file__).resolve().parent
sheet = Image.open(ROOT / 'keyframes.png').convert('RGB')
w, h = sheet.size
keys = [sheet.crop((round(c*w/4), round(r*h/3), round((c+1)*w/4), round((r+1)*h/3))).resize((240, 240), Image.Resampling.LANCZOS)
        for r in range(3) for c in range(4)]
# Ready pose, anticipation, release, roar, and a held final pose.
order = [0, 0, 0, 1, 2, 3, 4, 4, 5, 6, 7, 8, 9, 10, 11] + [11] * 15
# Use the twelve drawn poses for the large equipment movement; optical-flow
# synthesis introduces doubled blades and faces at these occlusions.
frames = [keys[i] for i in order for _ in range(2)]
if frames:
    atlas = Image.new('RGB', (240*len(frames), 240), 'white')
    for i, frame in enumerate(frames):
        atlas.paste(frame, (240*i, 0))
    out = ROOT / '蓄力仰天大吼.gif'
    for colors in (128, 96, 64, 48, 32):
        palette = atlas.quantize(colors=colors)
        indexed = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
        indexed[0].save(out, save_all=True, append_images=indexed[1:], duration=50,
                        loop=0, optimize=True, disposal=1)
        if out.stat().st_size <= 500_000:
            break
with Image.open(out) as gif:
    assert gif.size == (240, 240) and gif.info.get('loop') == 0
    assert gif.n_frames >= 12 and out.stat().st_size <= 500_000
    print(f'{gif.n_frames} frames, {out.stat().st_size} bytes, 50 ms timebase, drawn keyframes, infinite loop')
