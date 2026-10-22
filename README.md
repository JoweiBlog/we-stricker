# we-stricker

「我的刀盾」表情包项目。

制作及提交前请遵循 [表情包制作基准](docs/sticker-standard.md)。

正式版本：[V1.0 表情清单](releases/v1.0/README.md)（持续收录，目前 1 个已确认表情）。

## 已确认表情

### 001 · 歪头疑问

![歪头疑问](releases/v1.0/stickers/001-歪头疑问.gif)

[下载正式 GIF](releases/v1.0/stickers/001-歪头疑问.gif) · 240 × 240 像素 · 末帧停顿 1 秒。

## 最新制作稿

### 蓄力怒吼 · 直接蓄力版

![蓄力怒吼](assets/sky-roar-sideguard/蓄力怒吼-直接蓄力版.gif)

[下载当前 GIF](assets/sky-roar-sideguard/蓄力怒吼-直接蓄力版.gif) · 从蓄力开始，举刀仰天怒吼，侧面持盾，末帧停顿 1.2 秒。尚未确认纳入正式 V1.0。

## 素材归档

- [首套九宫格概念图](assets/concepts/首套九宫格概念图.png)：生成的表情方向展示，非用户原始多视角原型稿，也非可直接提交的单品。
- [歪头疑问源素材及制作脚本](assets/question-tilt/)。
- [仰天大吼初稿](assets/sky-roar/)。
- [蓄力怒吼前版](assets/sky-roar-charge/)。
- [侧盾修订及当前版本](assets/sky-roar-sideguard/)。

各目录保留关键帧、历史 GIF、制作脚本与版本说明；正式确认文件单独保存于 `releases/v1.0/`，实验修订不会自动覆盖正式文件。

## 本地重新导出

需要 Python、Pillow 和 NumPy。部分旧脚本还需要 FFmpeg（包含 `minterpolate` 滤镜）。

```sh
python -m pip install -r requirements.txt
python assets/sky-roar-sideguard/build_gif.py
```

请在各脚本中核对输出文件名，重新导出会覆盖对应的制作稿文件。制作规格见上方基准文档。
