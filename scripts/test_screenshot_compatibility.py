"""Original screenshot entry points must work without video arguments/dependencies."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import agent_adapter


class ScreenshotCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.images = [self.root / '默认.png', self.root / '展开.png']
        # Prepare reads references/hashes only; image decoding belongs to host vision.
        for i, path in enumerate(self.images):
            path.write_bytes(bytes([i, 10, 20]))

    def tearDown(self):
        self.tmp.cleanup()

    def test_original_prepare_signature_for_every_stack(self):
        for stack in agent_adapter.STACKS:
            with self.subTest(stack=stack), contextlib.redirect_stdout(io.StringIO()):
                output = self.root / f'{stack}.md'
                # This is the original caller contract: no interaction_spec attribute.
                agent_adapter.prepare(argparse.Namespace(image=self.images, stack=stack, out=output))
                brief = output.read_text()
                self.assertIn(agent_adapter.image_prompt(stack), brief)
                self.assertIn(str(self.images[0]), brief)
                self.assertIn(str(self.images[1]), brief)

    def test_source_sequence_is_preserved(self):
        output = self.root / 'ordered.md'
        with contextlib.redirect_stdout(io.StringIO()):
            agent_adapter.prepare(argparse.Namespace(image=[self.images[1], self.images[0], self.images[1]], stack='html_css', out=output))
        refs = [line.split(' (sha256:')[0][2:] for line in output.read_text().splitlines() if ' (sha256:' in line]
        self.assertEqual(refs, [str(self.images[1]), str(self.images[0]), str(self.images[1])])

    def test_screenshot_cli_needs_only_standard_library(self):
        # -S omits site-packages; empty PATH prevents accidental FFmpeg discovery.
        output = self.root / 'minimal.md'
        command = [sys.executable, '-S', str(Path(agent_adapter.__file__).resolve()), 'prepare']
        for path in self.images:
            command.extend(['--image', str(path)])
        command.extend(['--out', str(output)])
        result = subprocess.run(command, env={'PATH': '', 'PYTHONIOENCODING': 'utf-8'}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['images'], 2)
        self.assertTrue(output.is_file())


if __name__ == '__main__':
    unittest.main()
