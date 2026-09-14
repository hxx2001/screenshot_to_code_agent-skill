#!/usr/bin/env python3
"""Local PNG extraction with decoded-frame PTS; no inference or model calls."""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile


def binary(name):
    override = os.environ.get('SCREENSHOT_TO_CODE_' + name.upper())
    candidates = [override] if override else [shutil.which(name), '/opt/homebrew/bin/' + name, '/usr/local/bin/' + name,
        str(Path.home() / '.local/share/video-problem-analysis/bin' / name)]
    for value in candidates:
        if value and Path(value).is_file() and os.access(value, os.X_OK):
            return str(Path(value).resolve())
    raise ValueError(f'{name} unavailable; set SCREENSHOT_TO_CODE_{name.upper()} or install FFmpeg/FFprobe')


def run(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=600)
    if result.returncode:
        raise ValueError(f'{Path(args[0]).name} failed with exit {result.returncode}; check media and output space')
    return result.stdout


def doctor():
    return {name: {'path': binary(name), 'version': run([binary(name), '-version']).splitlines()[0]}
            for name in ('ffmpeg', 'ffprobe')}


def nonnegative(value):
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError('Expected a finite nonnegative number')
    return value


def choose(times, start, end, interval, every_frame):
    if not times or any(not math.isfinite(t) for t in times):
        raise ValueError('Missing frame timestamps')
    if any(b < a for a, b in zip(times, times[1:])):
        raise ValueError('Nonmonotonic frame timestamps')
    relative = [t - times[0] for t in times]
    stop = relative[-1] if end is None else end
    if stop < start or (end is not None and stop == start):
        raise ValueError('End must be after start')
    candidates = [i for i, t in enumerate(relative) if start <= t <= stop]
    if not candidates:
        raise ValueError('No frames in requested range')
    if every_frame:
        selected = candidates
    else:
        if not math.isfinite(interval) or interval <= 0:
            raise ValueError('Interval must be positive')
        selected = [candidates[0]]
        for i in candidates[1:]:
            if relative[i] - relative[selected[-1]] >= interval - 1e-9:
                selected.append(i)
        if selected[-1] != candidates[-1]:
            selected.append(candidates[-1])
    if len(selected) > 600:
        raise ValueError('More than 600 frames; split the range into overlapping batches')
    return selected, relative


def png_size(path):
    with path.open('rb') as stream:
        header = stream.read(24)
    if header[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Invalid exported PNG')
    return list(struct.unpack('>II', header[16:24]))


def extract(args):
    source = Path(args.video).expanduser().resolve(strict=True)
    if not source.is_file():
        raise ValueError('Expected a local video file')
    dependencies = doctor()
    probe = [dependencies['ffprobe']['path'], '-v', 'error', '-protocol_whitelist', 'file,pipe', '-select_streams', 'v:0']
    metadata = json.loads(run(probe + ['-show_entries', 'stream=width,height,avg_frame_rate,start_time,duration:format=duration', '-of', 'json', str(source)]))
    raw = run(probe + ['-show_frames', '-show_entries', 'frame=best_effort_timestamp_time', '-of', 'json', str(source)])
    try:
        times = [float(frame['best_effort_timestamp_time']) for frame in json.loads(raw)['frames']]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Video contains frames without valid timestamps') from exc
    selected, relative = choose(times, args.start, args.end, args.interval, args.every_frame)
    if args.max_width is not None and args.max_width < 1:
        raise ValueError('max-width must be positive')
    parent = Path(args.output).expanduser().resolve()
    parent.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix='frames-', dir=parent))
    select = '+'.join(f'eq(n\\,{i})' for i in selected)
    filters = f'select={select}'
    if args.max_width:
        filters += f",scale='min({args.max_width},iw)':-1"
    filters += ',showinfo'
    command = [dependencies['ffmpeg']['path'], '-nostdin', '-hide_banner', '-v', 'info',
        '-protocol_whitelist', 'file,pipe', '-copyts', '-i', str(source), '-map', '0:v:0',
        '-an', '-sn', '-dn', '-vf', filters, '-fps_mode', 'passthrough', '-threads', '1',
        '-frames:v', str(len(selected)), str(output / 'frame-%04d.png')]
    result = subprocess.run(command, capture_output=True, text=True, timeout=600)
    if result.returncode:
        raise ValueError(f'Extraction failed; incomplete output at {output}')
    pts = [float(v) for v in re.findall(r'\bn:\s*\d+.*?\bpts_time:\s*([-+\d.eE]+)', result.stderr)]
    images = sorted(output.glob('frame-*.png'))
    if len(images) != len(selected) or len(pts) != len(selected):
        raise ValueError('Frame count mismatch; no valid index written')
    if any(abs(p - times[i]) > max(0.002, abs(times[i]) * 0.00001) for p, i in zip(pts, selected)):
        raise ValueError('Decoded timestamps differ from probe; no valid index written')
    frames = [{'file': image.name, 'frame_number': i, 'source_pts_seconds': times[i],
               'relative_seconds': relative[i], 'dimensions': png_size(image)} for image, i in zip(images, selected)]
    digest = hashlib.sha256()
    with source.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    index = {'version': 1, 'source': str(source), 'sha256': digest.hexdigest(), 'metadata': metadata,
        'tools': dependencies, 'first_source_pts_seconds': times[0], 'audio_analyzed': False,
        'requested_range': {'start': args.start, 'end': args.end},
        'every_frame': args.every_frame, 'sample_interval_seconds': None if args.every_frame else args.interval,
        'max_width': args.max_width, 'frames': frames}
    (output / 'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n')
    cards = ''.join(f'<figure><a href="{f["file"]}"><img width="320" src="{f["file"]}"></a><figcaption>{f["relative_seconds"]:.6f}s · frame {f["frame_number"]}</figcaption></figure>' for f in frames)
    (output / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Video frames</title><h1>Extracted frames, not proof of review</h1><p>' + html.escape(source.name) + '</p>' + cards)
    return {'index': str(output / 'index.json'), 'frames': len(frames), 'dimensions': frames[0]['dimensions']}


def load_index(path):
    path = Path(path).resolve(strict=True)
    data = json.loads(path.read_text())
    frames = data['frames']
    if not frames:
        raise ValueError('Empty frame index')
    seen = set()
    previous = -math.inf
    for frame in frames:
        number = frame['frame_number']
        if type(number) is not int or number < 0 or number in seen:
            raise ValueError('Invalid/duplicate frame number')
        seen.add(number)
        time = nonnegative(frame['relative_seconds'])
        if time < previous:
            raise ValueError('Nonmonotonic index timestamps')
        previous = time
        file = (path.parent / frame['file']).resolve(strict=True)
        if not file.is_file() or path.parent not in file.parents:
            raise ValueError('Frame file must be inside its index directory')
        frame['_path'] = str(file)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor')
    p = sub.add_parser('extract')
    p.add_argument('video')
    p.add_argument('--start', type=nonnegative, default=0)
    p.add_argument('--end', type=nonnegative)
    group = p.add_mutually_exclusive_group()
    group.add_argument('--interval', type=nonnegative, default=1)
    group.add_argument('--every-frame', action='store_true')
    p.add_argument('--max-width', type=int)
    p.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(doctor() if args.command == 'doctor' else extract(args), ensure_ascii=False))
    except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
