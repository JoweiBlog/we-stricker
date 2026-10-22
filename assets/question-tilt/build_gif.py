"""Motion-interpolate generated keyframes and export a 20 fps GIF with a held final pose."""
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
from PIL import Image

ROOT = Path(__file__).resolve().parent
sheet = Image.open(ROOT / 'keyframes.png').convert('RGB')
w, h = sheet.size
keys = [sheet.crop((round(c*w/3), round(r*h/2), round((c+1)*w/3), round((r+1)*h/2))).resize((240, 240), Image.Resampling.LANCZOS)
        for r in range(2) for c in range(3)]
# Two seconds: tilt, blink, then hold the questioning pose. No return motion.
order = [0, 1, 2, 3, 3, 4, 5, 5, 5, 5, 5, 5]
with TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    # Extend endpoint poses; do not interpolate the reset between loops.
    padded = [order[0]] * 2 + order + [order[-1]] * 3
    for i, key in enumerate(padded):
        keys[key].save(tmp / f'in-{i:03d}.png')
    subprocess.run(['ffmpeg', '-v', 'error', '-framerate', '6', '-i', str(tmp/'in-%03d.png'),
                    '-vf', 'minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:mb_size=8:search_param=32:scd=none,trim=start_frame=20:end_frame=140,setpts=PTS-STARTPTS,fps=20',
                    str(tmp/'out-%03d.png')], check=True)
    frames = [Image.open(p).convert('RGB') for p in sorted(tmp.glob('out-*.png'))]
    atlas = Image.new('RGB', (240*len(frames), 240), 'white')
    for i, frame in enumerate(frames):
        atlas.paste(frame, (240*i, 0))
    out = ROOT / '歪头疑问-停顿版.gif'
    for colors in (128, 96, 64, 48):
        palette = atlas.quantize(colors=colors)
        indexed = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
        indexed[0].save(out, save_all=True, append_images=indexed[1:], duration=50,
                        loop=0, optimize=True, disposal=1)
        if out.stat().st_size <= 500_000:
            break
with Image.open(out) as gif:
    assert gif.size == (240, 240) and gif.info.get('loop') == 0
    assert gif.n_frames >= 15 and out.stat().st_size <= 500_000
    print(f'{gif.n_frames} frames, {out.stat().st_size} bytes, 20 fps, infinite loop')
