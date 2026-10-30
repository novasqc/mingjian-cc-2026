"""Reviewed assets survive normal builds and failed explicit rasterization."""
import builtins
import contextlib
import io
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'build'))
import gen_site
try:
    from PIL import Image
except ImportError:
    Image = None


class ImageBuild(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'assets').mkdir()
        self.names = ('apple-touch-icon.png', 'og-image.png')
        for name in self.names:
            shutil.copy2(ROOT / 'assets' / name, self.root / 'assets' / name)
        self.original = self.contents()
        root_patch = patch.object(gen_site, 'ROOT', str(self.root))
        root_patch.start()
        self.addCleanup(root_patch.stop)

    def contents(self):
        return {name: (self.root / 'assets' / name).read_bytes() for name in self.names}

    def test_normal_build_preserves_bytes_without_image_dependencies(self):
        original_import = builtins.__import__
        def without_pillow(name, *args, **kwargs):
            if name == 'PIL' or name.startswith('PIL.'):
                raise ImportError('Pillow deliberately unavailable')
            return original_import(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=without_pillow), \
             patch.object(gen_site, '_rasterize_emblem', side_effect=AssertionError('No renderer allowed')), \
             contextlib.redirect_stdout(io.StringIO()):
            gen_site.build_images()
        self.assertEqual(self.original, self.contents())

    def test_missing_or_empty_asset_blocks_before_any_page_generation(self):
        for mode in ('missing', 'empty'):
            with self.subTest(mode=mode):
                target = self.root / 'assets' / self.names[0]
                if mode == 'missing': target.unlink()
                else: target.write_bytes(b'')
                with patch.object(gen_site, 'PageLastmods') as page_work:
                    with self.assertRaisesRegex(RuntimeError, 'Missing reviewed PNG'):
                        gen_site.main()
                    page_work.assert_not_called()
                self.assertEqual(self.original[self.names[1]],
                                 (self.root / 'assets' / self.names[1]).read_bytes())

    @unittest.skipIf(Image is None, 'Pillow required only for regeneration tests')
    def test_renderer_failure_keeps_both_reviewed_images(self):
        with patch('PIL.ImageFont.truetype'), \
             patch.object(gen_site, '_rasterize_emblem', side_effect=RuntimeError('Quick Look unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'Quick Look unavailable'):
                gen_site.build_images(regenerate=True)
        self.assertEqual(self.original, self.contents())

    @unittest.skipIf(Image is None, 'Pillow required only for regeneration tests')
    def test_second_encoding_failure_does_not_install_first_replacement(self):
        original_save = Image.Image.save
        def save_or_fail(image, path, *args, **kwargs):
            if Path(path).name == 'og-image.png':
                raise OSError('encoding failure')
            return original_save(image, path, *args, **kwargs)
        with patch('PIL.ImageFont.truetype'), patch('PIL.ImageDraw.Draw'), \
             patch.object(gen_site, '_rasterize_emblem', return_value=Image.new('RGB', (512, 512))), \
             patch.object(Image.Image, 'save', new=save_or_fail):
            with self.assertRaisesRegex(OSError, 'encoding failure'):
                gen_site.build_images(regenerate=True)
        self.assertEqual(self.original, self.contents())
        self.assertEqual(set(self.names), {p.name for p in (self.root / 'assets').iterdir()})

    @unittest.skipIf(Image is None, 'Pillow required only for regeneration tests')
    def test_explicit_regeneration_prepares_valid_expected_sizes(self):
        with patch('PIL.ImageFont.truetype'), patch('PIL.ImageDraw.Draw'), \
             patch.object(gen_site, '_rasterize_emblem', return_value=Image.new('RGB', (512, 512))), \
             contextlib.redirect_stdout(io.StringIO()):
            gen_site.build_images(regenerate=True)
        for name, size in zip(self.names, ((180, 180), (1200, 630))):
            with Image.open(self.root / 'assets' / name) as image:
                self.assertEqual(image.size, size)
            self.assertNotEqual(self.original[name], self.contents()[name])


if __name__ == '__main__':
    unittest.main()
