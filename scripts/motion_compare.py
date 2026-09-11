#!/usr/bin/env python3
"""Pair frames by elapsed time without rescaling images or warping time."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import tempfile
from PIL import Image, ImageChops, ImageDraw
from video_frames import load_index, nonnegative
from image_regions import parse_regions, difference_metrics


def nearest(frames, target, tolerance):
    if target < frames[0]['relative_seconds'] - 1e-9 or target > frames[-1]['relative_seconds'] + 1e-9:
        raise ValueError(f'Requested time {target:.6f} is outside extracted coverage')
    frame = min(frames, key=lambda f: abs(f['relative_seconds'] - target))
    error = frame['relative_seconds'] - target
    if abs(error) > tolerance + 1e-9:
        raise ValueError(f'No frame within tolerance at {target:.6f}; nearest error {error:.6f}')
    return frame, error


def compare(args):
    reference = load_index(args.reference)['frames']
    render = load_index(args.render)['frames']
    offsets = [nonnegative(value) for value in args.offsets.split(',')]
    if not offsets or any(b <= a for a, b in zip(offsets, offsets[1:])):
        raise ValueError('Offsets must be unique and increasing')
    if len(offsets) > 120:
        raise ValueError('Split comparisons exceeding 120 pairs')
    pairs = []
    regions = None
    for offset in offsets:
        a, ae = nearest(reference, args.reference_start + offset, args.tolerance)
        b, be = nearest(render, args.render_start + offset, args.tolerance)
        with Image.open(a['_path']) as ai, Image.open(b['_path']) as bi:
            if ai.size != bi.size:
                raise ValueError(f'Dimensions differ: {ai.size} vs {bi.size}; normalize explicitly')
            current_regions = parse_regions(getattr(args, 'region', []), ai.size)
            if regions is None:
                regions = current_regions
        pairs.append({'offset': offset, 'reference': dict(a), 'render': dict(b),
            'reference_time_error': ae, 'render_time_error': be,
            'elapsed_time_mismatch': (b['relative_seconds'] - args.render_start) - (a['relative_seconds'] - args.reference_start)})
    parent = Path(args.out).resolve()
    parent.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix='comparison-', dir=parent))
    thumbnails = []
    used_reference, used_render = set(), set()
    for i, pair in enumerate(pairs):
        with Image.open(pair['reference']['_path']) as im:
            a = im.convert('RGB')
        with Image.open(pair['render']['_path']) as im:
            b = im.convert('RGB')
        canvas = Image.new('RGB', (a.width * 2 + 16, a.height + 36), '#eeeeee')
        canvas.paste(a, (0, 36)); canvas.paste(b, (a.width + 16, 36))
        label = f'+{pair["offset"]:.3f}s | reference {pair["reference"]["relative_seconds"]:.6f}s | render {pair["render"]["relative_seconds"]:.6f}s'
        ImageDraw.Draw(canvas).text((8, 10), label, fill='black')
        name = f'pair-{i:03d}.png'
        canvas.save(output / name)
        Image.blend(a, b, 0.5).save(output / f'overlay-{i:03d}.png')
        pair['pair_image'] = name
        pair['overlay_image'] = f'overlay-{i:03d}.png'
        difference, pair['full_frame_metrics'] = difference_metrics(a, b)
        pair['difference_image'] = f'difference-{i:03d}.png'
        difference.save(output / pair['difference_image'])
        pair['regions'] = []
        for j, region in enumerate(regions):
            ra, rb = a.crop(region['box']), b.crop(region['box'])
            diff, metrics = difference_metrics(ra, rb)
            prefix = f'region-{j:02d}-pair-{i:03d}'
            focused = Image.new('RGB', (ra.width * 2 + 16, ra.height), '#eeeeee')
            focused.paste(ra, (0, 0)); focused.paste(rb, (ra.width + 16, 0))
            focused.save(output / f'{prefix}.png')
            Image.blend(ra, rb, .5).save(output / f'{prefix}-overlay.png')
            diff.save(output / f'{prefix}-difference.png')
            pair['regions'].append({**region, **metrics, 'pair_image': f'{prefix}.png',
                'overlay_image': f'{prefix}-overlay.png', 'difference_image': f'{prefix}-difference.png'})
        pair['pixel_identical'] = ImageChops.difference(a, b).getbbox() is None
        pair['reused_reference_frame'] = pair['reference']['frame_number'] in used_reference
        pair['reused_render_frame'] = pair['render']['frame_number'] in used_render
        used_reference.add(pair['reference']['frame_number']); used_render.add(pair['render']['frame_number'])
        canvas.thumbnail((800, 500))
        thumbnails.append(canvas)
    sheet = Image.new('RGB', (max(im.width for im in thumbnails), sum(im.height for im in thumbnails)), 'white')
    y = 0
    for im in thumbnails:
        sheet.paste(im, (0, y)); y += im.height
    sheet.save(output / 'contact-sheet.png')
    report = {'version': 2, 'reference_index': str(Path(args.reference).resolve()), 'render_index': str(Path(args.render).resolve()),
        'reference_start': args.reference_start, 'render_start': args.render_start, 'tolerance': args.tolerance,
        'regions': regions,
        'note': 'Pairing evidence only; inspect motion and actual interaction. No fidelity score or automatic acceptance.', 'pairs': pairs}
    (output / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    return {'report': str(output / 'comparison.json'), 'contact_sheet': str(output / 'contact-sheet.png'), 'pairs': len(pairs)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('reference', 'render', 'offsets', 'out'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--reference-start', required=True, type=nonnegative)
    parser.add_argument('--render-start', required=True, type=nonnegative)
    parser.add_argument('--tolerance', type=nonnegative, default=0.025)
    parser.add_argument('--region', action='append', help='Repeatable name:left,top,right,bottom in normalized image pixels; keeps full-frame comparisons')
    args = parser.parse_args()
    try:
        print(json.dumps(compare(args)))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
