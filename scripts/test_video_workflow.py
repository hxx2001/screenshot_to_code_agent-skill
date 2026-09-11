"""Regression checks using generated media; no user recordings or model calls."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from PIL import Image
import agent_adapter
import interaction_spec
import motion_compare
import video_frames


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.index = self.make_index('source', [0, .04, .12, .24, .40])

    def tearDown(self):
        self.tmp.cleanup()

    def make_index(self, name, times, altered=False, width=1400):
        folder = self.root / name
        folder.mkdir()
        frames = []
        for i, time in enumerate(times):
            file = f'{i}.png'
            color = 'red' if altered and i == 2 else (i * 40, 100, 100)
            Image.new('RGB', (width, 80), color).save(folder / file)
            frames.append({'file': file, 'frame_number': i, 'relative_seconds': time, 'source_pts_seconds': 5 + time, 'dimensions': [width, 80]})
        path = folder / 'index.json'
        path.write_text(json.dumps({'frames': frames}))
        return path

    def spec(self):
        return {'version': 1, 'viewport': {'width': 1400, 'height': 80, 'dpr': 1, 'normalization': 'native'},
            'sources': {'v': str(self.index)}, 'reviewed_ranges': [{'source': 'v', 'start_frame': 0, 'end_frame': 4, 'density': 'every-frame'}],
            'states': [{'id': 'a', 'description': 'closed', 'evidence': [{'source': 'v', 'frame_number': 0}]}, {'id': 'b', 'description': 'open', 'evidence': [{'source': 'v', 'frame_number': 4}]}],
            'transitions': [{'id': 'open', 'from': 'a', 'to': 'b', 'trigger': {'description': 'click', 'basis': 'inferred', 'evidence': []},
                'motion': {'kind': 'timed', 'window': {'source': 'v', 'start_frame': 0, 'end_frame': 4}, 'tracks': [{'element': 'drawer', 'property': 'top', 'unit': 'px', 'basis': 'observed', 'samples': [{'frame_number': 0, 'value': 80}, {'frame_number': 4, 'value': 20}]}]},
                'verification': {'status': 'pending', 'evidence': []}}], 'unseen_controls': []}

    def write_spec(self, spec):
        path = self.root / 'spec.json'
        path.write_text(json.dumps(spec))
        return path

    def compare_args(self, render):
        return argparse.Namespace(reference=str(self.index), render=str(render), offsets='0,.04,.12,.24,.4', reference_start=0, render_start=0, tolerance=.001, out=str(self.root / 'comparisons'))

    def test_vfr_selection_and_invalid_timestamps(self):
        selected, relative = video_frames.choose([5, 5.04, 5.12, 5.24], 0, None, .1, False)
        self.assertEqual(selected, [0, 2, 3])
        self.assertAlmostEqual(relative[2], .12)
        for times in ([0, float('nan')], [0, -.1]):
            with self.assertRaises(ValueError):
                video_frames.choose(times, 0, None, .1, True)
        with self.assertRaises(ValueError):
            video_frames.choose(list(range(601)), 0, None, 1, True)

    def test_real_native_png_and_nonzero_vfr_pts(self):
        try:
            ffmpeg = video_frames.binary('ffmpeg')
            video_frames.binary('ffprobe')
        except ValueError as exc:
            self.skipTest(str(exc))
        video = self.root / 'vfr.mkv'
        subprocess.run([ffmpeg, '-v', 'error', '-framerate', '25', '-i', str(self.index.parent / '%d.png'), '-vf', 'setpts=(5+N*N/25)/TB', '-fps_mode', 'vfr', '-c:v', 'ffv1', str(video)], check=True)
        result = video_frames.extract(argparse.Namespace(video=str(video), start=0, end=None, interval=1, every_frame=True, max_width=None, output=str(self.root / 'extracted')))
        data = video_frames.load_index(result['index'])
        self.assertEqual(len(data['frames']), 5)
        self.assertEqual(data['frames'][0]['dimensions'], [1400, 80])
        self.assertAlmostEqual(data['first_source_pts_seconds'], 5, places=2)
        gaps = [round(b['relative_seconds'] - a['relative_seconds'], 2) for a, b in zip(data['frames'], data['frames'][1:])]
        self.assertGreater(len(set(gaps)), 1)

    def test_spec_rejects_false_evidence_and_pass(self):
        spec = self.spec()
        interaction_spec.validate(self.write_spec(spec))
        for mutate in ('trigger', 'frame', 'pass', 'review', 'order'):
            changed = copy.deepcopy(spec)
            t = changed['transitions'][0]
            if mutate == 'trigger': t['trigger']['basis'] = 'observed'
            if mutate == 'frame': changed['states'][0]['evidence'][0]['frame_number'] = 999
            if mutate == 'pass': t['verification']['status'] = 'passed'
            if mutate == 'review': changed['reviewed_ranges'][0]['end_frame'] = 0
            if mutate == 'order': t['motion']['tracks'][0]['samples'].reverse()
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                interaction_spec.validate(self.write_spec(changed))

    def test_image_and_video_prepare(self):
        extra = self.root / 'clear-screenshot.png'
        Image.new('RGB', (1400, 80), 'white').save(extra)
        for name, image, spec in [('still', [self.index.parent / '0.png'], None), ('video', None, self.write_spec(self.spec())), ('mixed', [extra], self.write_spec(self.spec()))]:
            out = self.root / f'{name}.md'
            agent_adapter.prepare(argparse.Namespace(image=image, interaction_spec=spec, stack='html_css', out=out))
            self.assertTrue(out.is_file())
            self.assertIn(str((self.index.parent / '0.png').resolve()), out.read_text())
            if spec: self.assertIn('"basis": "inferred"', out.read_text())
            if name == 'mixed':
                refs = [line.split(' (sha256:')[0][2:] for line in out.read_text().splitlines() if ' (sha256:' in line]
                self.assertEqual(refs, [str(path.resolve()) for path in (extra, self.index.parent / '0.png', self.index.parent / '4.png')])

    def test_intermediate_difference_with_matching_endpoints(self):
        render = self.make_index('different', [0, .04, .12, .24, .40], altered=True)
        result = motion_compare.compare(self.compare_args(render))
        pairs = json.loads(Path(result['report']).read_text())['pairs']
        self.assertEqual([p['pixel_identical'] for p in pairs], [True, True, False, True, True])

    def test_pairing_rejects_missing_time_and_wrong_size(self):
        args = self.compare_args(self.index)
        args.offsets = '.08'
        with self.assertRaises(ValueError): motion_compare.compare(args)
        args.offsets = '.5'
        with self.assertRaises(ValueError): motion_compare.compare(args)
        args = self.compare_args(self.make_index('small', [0, .04, .12, .24, .40], width=700))
        with self.assertRaises(ValueError): motion_compare.compare(args)

    def test_reused_frames_are_reported(self):
        args = self.compare_args(self.index)
        args.offsets = '0,.001'
        args.tolerance = .01
        result = motion_compare.compare(args)
        pairs = json.loads(Path(result['report']).read_text())['pairs']
        self.assertTrue(pairs[1]['reused_reference_frame'])

    def test_still_crop_compare_and_finalize(self):
        manifest = self.root / 'assets.json'
        manifest.write_text(json.dumps([{'source': str(self.index.parent / '0.png'), 'name': 'asset.png', 'box': [0, 0, 20, 20]}]))
        agent_adapter.crop(argparse.Namespace(manifest=manifest, out=self.root / 'assets'))
        with Image.open(self.root / 'assets/asset.png') as image:
            self.assertEqual(image.size, (20, 20))
        agent_adapter.compare(argparse.Namespace(reference=self.index.parent / '0.png', render=self.index.parent / '0.png', out=self.root / 'still.png'))
        html = self.root / 'generated.txt'
        html.write_text('```html\n<html><body>OK</body></html>\n```')
        agent_adapter.finalize(argparse.Namespace(input=html, out=self.root / 'site.html'))
        self.assertEqual((self.root / 'site.html').read_text().strip(), '<html><body>OK</body></html>')


if __name__ == '__main__':
    unittest.main()
