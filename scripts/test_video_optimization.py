"""Behavioral checks for review gates, transient detection, and focused comparison."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import unittest
from PIL import Image, ImageDraw
import test_video_workflow
import interaction_spec
import motion_compare
import video_changes
import video_frames


class OptimizationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_video_workflow.WorkflowTests()
        self.fixture.setUp()
        self.root = self.fixture.root

    def tearDown(self):
        self.fixture.tearDown()

    def passed_spec(self):
        render = self.fixture.make_index('replay', [0, .04, .12, .24, .4])
        comparison = motion_compare.compare(self.fixture.compare_args(render))
        spec = self.fixture.spec()
        spec['transitions'][0]['verification'] = {'status': 'passed', 'evidence': [comparison['contact_sheet']],
            'comparison_reports': [comparison['report']],
            'review': {'motion': 'Inspected onset, travel, settling and full-frame appearance.',
                       'interaction': 'Clicked open and close; repeated the cycle and checked final state.'}}
        return spec, Path(comparison['report'])

    def test_dense_replay_passes_and_legacy_sparse_pass_fails(self):
        spec, _ = self.passed_spec()
        interaction_spec.validate(self.fixture.write_spec(spec))
        data = json.loads(self.fixture.index.read_text())
        data['frames'] = [data['frames'][0], data['frames'][-1]]
        self.fixture.index.write_text(json.dumps(data))
        spec['reviewed_ranges'][0]['density'] = 'sampled'
        with self.assertRaisesRegex(ValueError, 'every-frame'):
            interaction_spec.validate(self.fixture.write_spec(spec))
        spec['transitions'][0]['verification']['status'] = 'partial'
        interaction_spec.validate(self.fixture.write_spec(spec))

    def test_replay_requires_intermediate_distinct_frames_and_real_coverage(self):
        spec, report_path = self.passed_spec()
        original = json.loads(report_path.read_text())
        for mutation in ('endpoints', 'reused', 'timestamp', 'artifact', 'window', 'pair_skew', 'missing_report', 'no_review'):
            report = copy.deepcopy(original)
            changed = copy.deepcopy(spec)
            if mutation == 'endpoints': report['pairs'] = [report['pairs'][0], report['pairs'][-1]]
            if mutation == 'reused':
                report['tolerance'] = .1
                report['pairs'][1]['reference'] = report['pairs'][0]['reference']
            if mutation == 'timestamp': report['pairs'][1]['render']['relative_seconds'] = .05
            if mutation == 'artifact': report['pairs'][0]['pair_image'] = 'missing.png'
            if mutation == 'window': report['pairs'] = report['pairs'][1:]
            if mutation == 'pair_skew':
                # Both individual errors can fit tolerance while their mismatch does not.
                report['tolerance'] = .025
                report['pairs'][1]['offset'] = .02
                report['pairs'][1]['render'] = report['pairs'][0]['render']
            if mutation == 'missing_report': changed['transitions'][0]['verification'].pop('comparison_reports')
            if mutation == 'no_review': changed['transitions'][0]['verification']['review']['interaction'] = ' '
            report_path.write_text(json.dumps(report))
            with self.subTest(mutation=mutation), self.assertRaises((ValueError, OSError)):
                interaction_spec.validate(self.fixture.write_spec(changed))

    def test_regions_isolate_background_noise_without_hiding_it(self):
        render = self.fixture.make_index('noise', [0, .04, .12, .24, .4])
        for file in render.parent.glob('*.png'):
            with Image.open(file) as im:
                ImageDraw.Draw(im).rectangle((0, 0, 100, 20), fill='white')
                im.save(file)
        args = self.fixture.compare_args(render)
        args.region = ['drawer:200,0,1000,80', 'status:0,0,100,20']
        result = motion_compare.compare(args)
        pair = json.loads(Path(result['report']).read_text())['pairs'][0]
        self.assertFalse(pair['pixel_identical'])
        self.assertEqual(pair['regions'][0]['changed_fraction'], 0)
        self.assertEqual(pair['regions'][1]['changed_fraction'], 1)
        with Image.open(Path(result['report']).parent / pair['regions'][0]['overlay_image']) as im:
            self.assertEqual(im.size, (800, 80))
        args.region = ['outside:0,0,1500,80']
        with self.assertRaisesRegex(ValueError, 'outside'):
            motion_compare.compare(args)

    def make_video(self, name, transient=False):
        try:
            ffmpeg = video_frames.binary('ffmpeg')
            video_frames.binary('ffprobe')
        except ValueError as exc:
            self.skipTest(str(exc))
        folder = self.root / name
        folder.mkdir()
        for n in range(25):
            im = Image.new('RGB', (640, 360), '#333333')
            if transient and n in (10, 11):
                ImageDraw.Draw(im).rectangle((100, 80, 105, 85), fill='white')
            im.save(folder / f'{n:03d}.png')
        video = folder / 'clip.mkv'
        subprocess.run([ffmpeg, '-v', 'error', '-framerate', '25', '-i', str(folder / '%03d.png'),
            '-c:v', 'ffv1', str(video)], check=True)
        return video

    def scan_args(self, video):
        return argparse.Namespace(video=str(video), output=str(self.root / 'scan'), scan_width=320,
            pixel_threshold=12, changed_fraction=.008, before=.15, after=.25, merge_gap=.15,
            region=['button:90,70,120,100'], extract=True)

    def test_brief_local_change_is_found_between_overview_samples_and_extracted(self):
        video = self.make_video('transient', transient=True)
        overview = video_frames.extract(argparse.Namespace(video=str(video), start=0, end=None,
            interval=1, every_frame=False, max_width=None, output=str(self.root / 'overview')))
        self.assertEqual([f['frame_number'] for f in video_frames.load_index(overview['index'])['frames']], [0, 24])
        result = video_changes.scan(self.scan_args(video))
        report = json.loads(Path(result['report']).read_text())
        self.assertEqual(result['scanned_frames'], 25)
        self.assertEqual(report['scan_dimensions'], [320, 180])
        self.assertEqual([e['frame_number'] for e in report['events']], [10, 12])
        self.assertEqual(report['windows'][0]['regions'], ['button'])
        self.assertEqual(len(result['dense_indices']), 1)
        frames = video_frames.load_index(result['dense_indices'][0])['frames']
        numbers = [f['frame_number'] for f in frames]
        self.assertLess(numbers[0], 10)
        self.assertGreater(numbers[-1], 12)
        self.assertEqual(numbers, list(range(numbers[0], numbers[-1] + 1)))
        self.assertEqual(frames[0]['dimensions'], [640, 360])

    def test_static_video_does_not_create_events(self):
        result = video_changes.scan(self.scan_args(self.make_video('static')))
        self.assertEqual(result['windows'], 0)
        self.assertEqual(result['dense_indices'], [])

    def test_long_candidate_is_split_into_overlapping_bounded_batches(self):
        times = [i / 60 for i in range(1300)]
        events = [{'frame_number': n, 'relative_seconds': times[n], 'regions': {'full-frame': 1}} for n in range(1, 1300)]
        windows = video_changes.group_windows(events, times, .15, .25, .15)
        self.assertEqual(len(windows), 1)
        batches = windows[0]['dense_batches']
        self.assertEqual(len(batches), 3)
        for batch in batches:
            self.assertLessEqual(batch['end_frame'] - batch['start_frame'] + 1, 600)
        self.assertEqual(batches[0]['end_frame'], batches[1]['start_frame'])
        self.assertEqual(batches[-1]['end_frame'], 1299)


if __name__ == '__main__':
    unittest.main()
