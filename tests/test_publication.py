import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import json
from PIL import Image

spec = importlib.util.spec_from_file_location('publication', Path(__file__).resolve().parents[1] / 'scripts/build_publication.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.paths = []
        for i in range(8):
            p = self.root / f'{i}.png'
            Image.new('RGB', (240, 240), (30*i, 90, 100)).save(p)
            self.paths.append(p)

    def tearDown(self):
        self.tmp.cleanup()

    def gif(self, loop):
        p = self.root / 'dynamic.gif'
        frames = [Image.new('RGB', (240, 240), c) for c in ['red', 'blue']]
        frames[0].save(p, save_all=True, append_images=frames[1:], duration=80, loop=loop)
        return p

    def test_eight_unique_static_files_pass(self):
        errors, warnings, _ = module.validate_stickers(self.paths)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_count_and_duplicates_are_blocking(self):
        self.assertTrue(module.validate_stickers(self.paths[:7])[0])
        self.assertTrue(module.validate_stickers([self.paths[0]]*8)[0])

    def test_static_gif_is_static_and_mixed_motion_is_blocked(self):
        p = self.root / 'still.gif'
        Image.new('RGB', (240, 240), 'yellow').save(p)
        self.assertFalse(module.inspect_image(p)['animated'])
        errors = module.validate_stickers(self.paths[:7]+[self.gif(0)])[0]
        self.assertTrue(any('混用' in e for e in errors))

    def test_nonlooping_animation_is_blocked(self):
        errors = module.validate_stickers(self.paths[:7]+[self.gif(1)])[0]
        self.assertTrue(any('无限循环' in e for e in errors))

    def test_cover_requires_real_transparency(self):
        self.assertTrue(module.validate_asset(self.paths[0], 'cover')[0])
        p = self.root / 'cover.png'
        im = Image.new('RGBA', (240, 240), (0,0,0,0))
        im.paste((120,80,40,255), (20,20,220,220))
        im.save(p)
        self.assertEqual(module.validate_asset(p, 'cover')[0], [])

    def test_banner_rejects_transparency_and_icon_wrong_size(self):
        p = self.root / 'banner.png'
        im = Image.new('RGBA', (750,400), (100,100,100,255))
        im.putpixel((0,0), (0,0,0,0)); im.save(p)
        self.assertTrue(module.validate_asset(p,'banner')[0])
        self.assertTrue(module.validate_asset(self.paths[0],'icon')[0])

    def test_introduction_length_and_cross_album_reuse(self):
        previous = module.ROOT
        module.ROOT = self.root
        try:
            manifest = {'stickers': [{'file': p.name, 'name': str(i)} for i,p in enumerate(self.paths)]}
            (self.root/'manifest.json').write_text(json.dumps(manifest))
            Image.new('RGB',(750,400),'green').save(self.root/'banner.jpg')
            cover = Image.new('RGBA',(240,240),(0,0,0,0))
            cover.paste((120,80,40,255),(20,20,220,220))
            cover.save(self.root/'cover.png')
            cover.resize((50,50)).save(self.root/'icon.png')
            cfg = {'id':'a', 'album_id':'album-a','title':'A','introduction':'介绍',
                   'stickers_manifest':'manifest.json','banner':'banner.jpg','cover':'cover.png','icon':'icon.png'}
            path = self.root/'config.json'
            path.write_text(json.dumps(cfg))
            registry = {}
            self.assertEqual(module.prepare(path,registry)['errors'],[])
            # Alternative export of the same album may share its artwork.
            self.assertEqual(module.prepare(path,registry)['errors'],[])
            cfg['album_id']='album-b'
            cfg['introduction']='字'*81
            path.write_text(json.dumps(cfg))
            errors = module.prepare(path,registry)['errors']
            self.assertTrue(any('介绍' in e for e in errors))
            self.assertEqual(sum('另一专辑' in e for e in errors),2)
        finally:
            module.ROOT = previous


if __name__ == '__main__':
    unittest.main()
