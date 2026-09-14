#!/usr/bin/env python3
"""Scan every decoded frame at reduced size; propose dense windows, not interactions."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import subprocess
import tempfile
import threading
from PIL import Image
from image_regions import parse_regions, difference_metrics
from video_frames import doctor, run, extract, nonnegative, png_size


def group_windows(events, times, before, after, merge_gap):
    windows = []
    for event in events:
        # Include the previous frame: it bounds where this observed change began.
        start = max(0, times[max(0, event['frame_number'] - 1)] - before)
        end = min(times[-1], event['relative_seconds'] + after)
        if windows and start <= windows[-1]['end'] + merge_gap:
            windows[-1]['end'] = max(end, windows[-1]['end'])
            windows[-1]['regions'] = sorted(set(windows[-1]['regions']) | set(event['regions']))
        else:
            windows.append({'start': start, 'end': end, 'regions': sorted(event['regions'])})
    for window in windows:
        # Round outward to actual frames, so onset and settling are not trimmed.
        first = max(i for i, t in enumerate(times) if t <= window['start'])
        last = next(i for i, t in enumerate(times) if t >= window['end'])
        window['start'], window['end'] = times[first], times[last]
        window['dense_batches'] = []
        while first < last:
            stop = min(first + 599, last)
            window['dense_batches'].append({'start': times[first], 'end': times[stop],
                'start_frame': first, 'end_frame': stop})
            first = stop  # one shared frame at batch boundaries
    return windows


def scan(args):
    source = Path(args.video).expanduser().resolve(strict=True)
    if not source.is_file():
        raise ValueError('Expected a local video file')
    if args.scan_width < 16 or args.scan_width > 1920:
        raise ValueError('scan-width must be between 16 and 1920')
    if not 1 <= args.pixel_threshold <= 255 or not 0 < args.changed_fraction <= 1:
        raise ValueError('Invalid pixel threshold or changed fraction')
    dependencies = doctor()
    probe = json.loads(run([dependencies['ffprobe']['path'], '-v', 'error', '-protocol_whitelist', 'file,pipe',
        '-select_streams', 'v:0', '-show_frames', '-show_entries', 'frame=best_effort_timestamp_time', '-of', 'json', str(source)]))
    times = [float(f['best_effort_timestamp_time']) for f in probe['frames']]
    # Validate timestamps without the export-only 600-frame bound.
    if not times or any(not math.isfinite(t) for t in times) or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError('Change scan needs strictly increasing decoded timestamps')
    relative = [t - times[0] for t in times]
    parent = Path(args.output).expanduser().resolve()
    parent.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix='changes-', dir=parent))
    base = [dependencies['ffmpeg']['path'], '-nostdin', '-hide_banner', '-v', 'error',
        '-protocol_whitelist', 'file,pipe', '-copyts', '-i', str(source), '-map', '0:v:0', '-an', '-sn', '-dn']
    # Read decoded orientation rather than assuming coded stream width/height.
    first_png = output / 'overview.png'
    run(base + ['-frames:v', '1', '-threads', '1', str(first_png)])
    native = png_size(first_png)
    width = min(args.scan_width, native[0])
    height = max(1, round(native[1] * width / native[0]))
    regions = parse_regions(args.region, native)
    scan_regions = [{'name': 'full-frame', 'box': [0, 0, width, height]}]
    if any(r['name'] == 'full-frame' for r in regions):
        raise ValueError('full-frame is a reserved region name')
    for region in regions:
        l, t, r, b = region['box']
        scan_regions.append({'name': region['name'], 'box': [math.floor(l * width / native[0]),
            math.floor(t * height / native[1]), math.ceil(r * width / native[0]), math.ceil(b * height / native[1])]})
    events, previous, frame_number = [], None, 0
    command = base + ['-vf', f'scale={width}:{height}', '-pix_fmt', 'rgb24', '-fps_mode', 'passthrough',
        '-threads', '1', '-f', 'rawvideo', 'pipe:1']
    with (output / 'scan-errors.log').open('wb') as errors:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors)
        timeout = threading.Event()
        def kill_timeout():
            timeout.set()
            process.kill()
        timer = threading.Timer(600, kill_timeout)
        timer.start()
        try:
            while True:
                data = process.stdout.read(width * height * 3)
                if not data:
                    break
                if len(data) != width * height * 3 or frame_number >= len(relative):
                    raise ValueError('Decoded scan frame count mismatch')
                current = Image.frombytes('RGB', (width, height), data)
                if previous is not None:
                    scores = {}
                    for region in scan_regions:
                        _, metrics = difference_metrics(previous.crop(region['box']), current.crop(region['box']), args.pixel_threshold)
                        if metrics['changed_fraction'] >= args.changed_fraction:
                            scores[region['name']] = metrics['changed_fraction']
                    if scores:
                        events.append({'frame_number': frame_number, 'relative_seconds': relative[frame_number], 'regions': scores})
                previous = current
                frame_number += 1
            code = process.wait()
            if timeout.is_set():
                raise ValueError('Change scan exceeded 600 seconds; use a shorter source recording')
            if code or frame_number != len(times):
                raise ValueError(f'Change scan incomplete; inspect {output / "scan-errors.log"}')
        finally:
            timer.cancel()
            if process.poll() is None:
                process.kill()
            process.wait()
            process.stdout.close()
    windows = group_windows(events, relative, args.before, args.after, args.merge_gap)
    for window in windows:
        for batch in window['dense_batches']:
            batch['command'] = ['python3', str(Path(__file__).with_name('video_frames.py')), 'extract', str(source),
                '--start', str(batch['start']), '--end', str(batch['end']), '--every-frame', '--output', str(output / 'dense')]
    report = {'version': 1, 'source': str(source), 'dimensions': native, 'scan_dimensions': [width, height],
        'scanned_frames': frame_number, 'scanned_range': [0, relative[-1]], 'regions': regions,
        'pixel_threshold': args.pixel_threshold, 'changed_fraction': args.changed_fraction,
        'before': args.before, 'after': args.after, 'merge_gap': args.merge_gap,
        'note': 'Candidate visual changes only. No-change output does not prove no interaction; inspect playback and tune thresholds/regions for subtle changes.',
        'events': events, 'windows': windows}
    report_path = output / 'changes.json'
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    if args.extract:
        batches = [b for w in windows for b in w['dense_batches']]
        if len(batches) > 40:
            raise ValueError(f'More than 40 dense batches; review {report_path} and extract selected windows')
        for batch in batches:
            batch['extraction'] = extract(argparse.Namespace(video=str(source), start=batch['start'], end=batch['end'],
                every_frame=True, interval=1, max_width=None, output=str(output / 'dense')))
            report_path.write_text(json.dumps(report, indent=2) + '\n')
    return {'report': str(report_path), 'windows': len(windows), 'scanned_frames': frame_number,
        'dense_indices': [b['extraction']['index'] for w in windows for b in w['dense_batches'] if 'extraction' in b]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video')
    parser.add_argument('--output', required=True)
    parser.add_argument('--scan-width', type=int, default=320)
    parser.add_argument('--pixel-threshold', type=int, default=12)
    parser.add_argument('--changed-fraction', type=nonnegative, default=.008)
    parser.add_argument('--before', type=nonnegative, default=.15)
    parser.add_argument('--after', type=nonnegative, default=.25)
    parser.add_argument('--merge-gap', type=nonnegative, default=.15)
    parser.add_argument('--region', action='append', help='Repeatable name:left,top,right,bottom in original decoded image pixels')
    parser.add_argument('--extract', action='store_true', help='Also export native-resolution dense candidate batches (at most 40)')
    try:
        print(json.dumps(scan(parser.parse_args())))
    except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
