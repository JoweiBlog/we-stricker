"""Validate configured WeChat albums and generate upload bundles (no publishing)."""
from pathlib import Path
from PIL import Image
from zipfile import ZipFile, ZIP_DEFLATED
import argparse
import csv
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ['角色、画风统一且各表情动作差异足够', '布局留白适量、无裁切或拉伸',
          '动态节奏流畅不卡顿', '横幅无文字、非白底、色彩明朗、有故事性',
          '封面为正面半身或全身、无多余文字装饰', '图标为清晰简洁正面头部、无方框',
          '透明图边缘无白描边、锯齿或生硬直角',
          '赞赏两图与表情风格一致、内容相关，引导语自然且无错误']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_image(path, role='sticker'):
    with Image.open(path) as im:
        animated = bool(getattr(im, 'is_animated', False))
        alpha = im.convert('RGBA').getchannel('A')
        transparent = alpha.getextrema()[0] < 255
        return {'format': im.format, 'size': list(im.size), 'animated': animated,
                'loop': im.info.get('loop'), 'transparent': transparent,
                'empty': alpha.getextrema()[1] == 0,
                'bytes': path.stat().st_size, 'sha256': digest(path)}


def validate_stickers(paths):
    errors, warnings, entries = [], [], []
    if not 8 <= len(paths) <= 24:
        errors.append(f'表情数量为 {len(paths)}，须为 8–24。')
    for p in paths:
        try:
            x = inspect_image(p)
        except (OSError, ValueError) as exc:
            errors.append(f'{p.name} 无法读取：{exc}')
            continue
        entries.append(x)
        if x['format'] not in ('JPEG', 'PNG', 'GIF') or x['size'] != [240, 240] or x['empty']:
            errors.append(f'{p.name} 格式、240×240 尺寸或非空要求不符。')
        if x['animated'] and (x['format'] != 'GIF' or x['loop'] != 0):
            errors.append(f'{p.name} 动态须为无限循环 GIF。')
        if x['bytes'] > 500000:
            warnings.append(f'{p.name} 超过保守 500 KB 阈值，平台可能压缩。')
    types = {x['animated'] for x in entries}
    if len(types) > 1:
        errors.append('同一专辑不可混用动态与静态表情。')
    if len({x['sha256'] for x in entries}) != len(entries):
        errors.append('存在内容完全相同的重复表情，请替换。')
    return errors, warnings, entries


def validate_asset(path, role):
    x = inspect_image(path)
    appreciation = role in ('appreciation_guide', 'appreciation_thanks')
    size = {'banner': [750, 400], 'cover': [240, 240], 'icon': [50, 50],
            'appreciation_guide': [750, 560], 'appreciation_thanks': [750, 750]}[role]
    formats = ('JPEG', 'PNG', 'GIF') if appreciation else (('JPEG', 'PNG') if role == 'banner' else ('PNG',))
    errors, warnings = [], []
    if x['size'] != size or x['format'] not in formats or (x['animated'] and not appreciation) or x['empty']:
        errors.append(f'{role} 的格式、尺寸或有效图像要求不符。')
    if not appreciation and x['transparent'] != (role != 'banner'):
        errors.append(f'{role} 背景透明性不符合规范。')
    if x['bytes'] > (100000 if role == 'icon' else 500000):
        warnings.append(f'{role} 超出平台压缩提示阈值。')
    return errors, warnings, x


def resolve(relative, base=None):
    base = ROOT if base is None else base
    p = (base / relative).resolve()
    p.relative_to(ROOT.resolve())
    return p


def prepare(config_path, registry):
    config = json.loads(config_path.read_text())
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', config['id']):
        raise ValueError('配置 id 仅允许字母、数字、下划线和短横线。')
    album_id = config['album_id']
    intro = config.get('introduction', '').strip()
    errors, warnings = [], []
    if not intro or len(intro) > 80:
        errors.append('表情介绍须为 1–80 字符。')
    appreciation_prompt = str(config.get('appreciation_prompt') or '').strip()
    appreciation_count = len(re.findall(r'[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0002fa1f]', appreciation_prompt))
    if not 5 <= appreciation_count <= 15:
        errors.append('赞赏引导语须为 5–15 个汉字，须单独填写，标点不计入汉字数。')
    mp = resolve(config['stickers_manifest'])
    items = json.loads(mp.read_text())['stickers']
    paths = [resolve(item['file'], mp.parent) for item in items]
    e, w, entries = validate_stickers(paths)
    errors += e
    warnings += w
    assets = {}
    for role in ('banner', 'cover', 'icon', 'appreciation_guide', 'appreciation_thanks'):
        value = config.get(role)
        if not value:
            errors.append(f'缺少 {role} 素材，待制作并确认。')
            continue
        try:
            p = resolve(value)
            e, w, meta = validate_asset(p, role)
        except (OSError, ValueError) as exc:
            errors.append(f'{role} 无法读取：{exc}')
            continue
        errors += e
        warnings += w
        if role in ('cover', 'icon'):
            key = (role, meta['sha256'])
            owner = registry.get(key)
            if owner and owner != album_id:
                errors.append(f'{role} 与另一专辑 {owner} 完全相同，请另行制作。')
            registry[key] = album_id
        assets[role] = (p, meta)
    return {'config': config, 'intro': intro, 'items': items, 'paths': paths,
            'entries': entries, 'assets': assets, 'errors': errors, 'warnings': warnings,
            'appreciation_prompt': appreciation_prompt, 'appreciation_count': appreciation_count}


def write_album(data, destination):
    cfg = data['config']
    destination.mkdir(parents=True, exist_ok=True)
    (destination / '表情').mkdir()
    (destination / '表情介绍.txt').write_text(data['intro'] + '\n')
    (destination / '赞赏').mkdir()
    (destination / '赞赏' / '赞赏引导语.txt').write_text(data['appreciation_prompt'] + '\n')
    copied = []
    with (destination / '上传信息.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['编号', '图片', '含义词', '标签'])
        for n, (item, source) in enumerate(zip(data['items'], data['paths']), 1):
            if not source.is_file():
                continue  # Missing source is already recorded as a blocking error.
            name = f'{n:02d}{source.suffix.lower()}'
            target = destination / '表情' / name
            shutil.copy2(source, target)
            copied.append(target)
            writer.writerow([f'{n:02d}', name, item.get('meaning', item['name']), '、'.join(item.get('tags', []))])
    with ZipFile(destination / '表情合计.zip', 'w', compression=ZIP_DEFLATED) as z:
        for p in copied:
            z.write(p, p.name)
    labels = {'banner': '横幅', 'cover': '封面', 'icon': '图标',
              'appreciation_guide': '赞赏/引导图', 'appreciation_thanks': '赞赏/致谢图'}
    for role, (source, _) in data['assets'].items():
        d = destination / labels[role]
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, d / source.name)
    report = {'album_id': cfg['album_id'], 'title': cfg['title'],
              'automatic_status': 'blocked' if data['errors'] else 'passed',
              'ready_for_upload': False,
              'manual_review_status': 'pending', 'manual_review_items': MANUAL,
              'errors': data['errors'], 'warnings': data['warnings'],
              'introduction_length': len(data['intro']), 'stickers': data['entries'],
              'appreciation_prompt': data['appreciation_prompt'],
              'appreciation_prompt_chinese_count': data['appreciation_count'],
              'assets': {k: x[1] for k, x in data['assets'].items()}}
    (destination / '发布检查.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    text = [f"# {cfg['title']} · 发布清单", '', f"自动检查：{report['automatic_status']}；人工检查待确认。", '',
            '## 表情介绍', '', data['intro'], '', '## 赞赏引导语', '', data['appreciation_prompt'], '', '## 待补／错误', '']
    text += [f'- {s}' for s in data['errors']] or ['无自动错误；仍需人工检查。']
    text += ['', '## 压缩提示', ''] + ([f'- {s}' for s in data['warnings']] or ['无。'])
    text += ['', '## 人工确认', ''] + [f'- [ ] {s}' for s in MANUAL]
    text += ['', '表情合计.zip 仅含单品图片；完整发布素材在当前目录中。脚本未上传或发布至微信。']
    (destination / '发布清单.md').write_text('\n'.join(text) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('configs', nargs='+')
    parser.add_argument('--output', default='dist/publication')
    args = parser.parse_args()
    output = resolve(args.output)
    registry, prepared = {}, []
    for value in args.configs:
        prepared.append(prepare(resolve(value), registry))
    if len({x['config']['id'] for x in prepared}) != len(prepared):
        raise ValueError('配置 id 重复。')
    # Never overwrite an unrelated or previous output directory.
    output.mkdir(parents=True, exist_ok=False)
    summary = []
    for data in prepared:
        report = write_album(data, output / data['config']['id'])
        summary.append({'id': data['config']['id'], 'automatic_status': report['automatic_status'], 'errors': report['errors']})
    (output / '汇总.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    zip_path = output / '我的刀盾-已确认静态表情合集.zip'
    with ZipFile(zip_path, 'w', compression=ZIP_DEFLATED) as z:
        for p in sorted(output.rglob('*')):
            if p.is_file() and p != zip_path and p.suffix != '.zip':
                z.write(p, p.relative_to(output))
    print(json.dumps(summary, ensure_ascii=False))
    print(zip_path)
    return 2 if any(x['errors'] for x in summary) else 0


if __name__ == '__main__':
    raise SystemExit(main())
