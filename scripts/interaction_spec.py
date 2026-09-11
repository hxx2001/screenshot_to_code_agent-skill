#!/usr/bin/env python3
"""Validate evidence references and structure, not visual interpretation."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
from video_frames import load_index

BASIS = {'observed', 'user-described', 'inferred', 'unknown'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def replay_report(path, source_index, start, end):
    """Check replay coverage/provenance, never infer visual acceptance from pixels."""
    path = Path(path).resolve(strict=True)
    report = json.loads(path.read_text())
    require(report.get('version') == 2, 'Passed motion requires a version 2 comparison report')
    require((path.parent / report['reference_index']).resolve() == source_index,
            'Comparison reference must be the motion window source index')
    indices = {side: load_index(path.parent / report[side + '_index']) for side in ('reference', 'render')}
    frames = {side: {f['frame_number']: f for f in index['frames']} for side, index in indices.items()}
    tolerance = report['tolerance']
    require(type(tolerance) in (int, float) and math.isfinite(tolerance) and tolerance >= 0, 'Invalid pairing tolerance')
    for side in ('reference', 'render'):
        origin = report[side + '_start']
        require(type(origin) in (int, float) and math.isfinite(origin) and origin >= 0, 'Invalid replay start')
    numbers = {'reference': [], 'render': []}
    previous_offset = -math.inf
    for pair in report['pairs']:
        offset = pair['offset']
        require(type(offset) in (int, float) and math.isfinite(offset) and offset >= 0 and offset > previous_offset,
                'Replay offsets must be finite, nonnegative and increasing')
        previous_offset = offset
        elapsed = {}
        for side in ('reference', 'render'):
            number = pair[side]['frame_number']
            require(number in frames[side], 'Replay refers to a missing indexed frame')
            actual = frames[side][number]
            require(pair[side]['relative_seconds'] == actual['relative_seconds'], 'Replay timestamp differs from index')
            numbers[side].append(number)
            elapsed[side] = actual['relative_seconds'] - report[side + '_start']
            require(abs(elapsed[side] - offset) <= tolerance + 1e-9, 'Replay frame outside tolerance')
        require(abs(elapsed['reference'] - elapsed['render']) <= tolerance + 1e-9,
                'Reference/render elapsed times differ beyond tolerance')
        for key in ('pair_image', 'overlay_image', 'difference_image'):
            artifact = (path.parent / pair[key]).resolve(strict=True)
            require(path.parent in artifact.parents and artifact.is_file(), 'Missing local comparison image')
    for side, sequence in numbers.items():
        require(len(sequence) >= 3 and all(b > a for a, b in zip(sequence, sequence[1:])),
                'Passed motion needs at least three distinct ordered frames per recording; no reused frames')
        require(all(n in frames[side] for n in range(sequence[0], sequence[-1] + 1)),
                'Passed replay needs dense frame coverage in both recordings')
    require(numbers['reference'][0] == start and numbers['reference'][-1] == end,
            'Comparison must cover motion window endpoints and an intermediate frame')


def validate(path):
    path = Path(path).resolve(strict=True)
    spec = json.loads(path.read_text())
    require(spec['version'] == 1, 'Unsupported specification version')
    for key in ('width', 'height', 'dpr'):
        value = spec['viewport'][key]
        require(type(value) in (int, float) and math.isfinite(value) and value > 0, f'Invalid viewport {key}')
    require(bool(spec['viewport']['normalization']), 'Describe viewport normalization')
    sources = {key: load_index(path.parent / file) for key, file in spec['sources'].items()}
    frames = {key: {f['frame_number']: f for f in index['frames']} for key, index in sources.items()}
    reviewed = {key: set() for key in sources}
    dense_reviewed = {key: set() for key in sources}

    def frame(source, number):
        require(source in frames and number in frames[source], f'Missing frame {source}:{number}')
        return frames[source][number]

    def window(value):
        source, start, end = value['source'], value['start_frame'], value['end_frame']
        a, b = frame(source, start), frame(source, end)
        require(start <= end and a['relative_seconds'] <= b['relative_seconds'], 'Reversed frame window')
        return source, start, end

    for item in spec['reviewed_ranges']:
        source, start, end = window(item)
        require(item['density'] in {'sampled', 'every-frame'}, 'Unknown review density')
        selected = {n for n in frames[source] if start <= n <= end}
        if item['density'] == 'every-frame':
            require(len(selected) == end - start + 1, 'Every-frame review points to missing frames')
            dense_reviewed[source].update(selected)
        reviewed[source].update(selected)

    def evidence(refs):
        for ref in refs:
            f = frame(ref['source'], ref['frame_number'])
            require(f['frame_number'] in reviewed[ref['source']], 'Evidence lies outside reviewed coverage')

    state_ids = set()
    state_images = []
    for state in spec['states']:
        require(state['id'] and state['id'] not in state_ids, 'Duplicate/empty state ID')
        state_ids.add(state['id'])
        require(bool(state['description']), 'State needs description')
        refs = state.get('evidence', [])
        if 'basis' in state:
            require(state['basis'] in BASIS, 'Invalid state basis')
        require(bool(refs) or state.get('basis') in BASIS - {'observed'}, 'State needs evidence or explicit non-observed basis')
        evidence(refs)
        state_images.extend(frame(r['source'], r['frame_number'])['_path'] for r in refs)
    require(bool(state_ids), 'No states')
    transition_ids = set()
    for transition in spec['transitions']:
        require(transition['id'] and transition['id'] not in transition_ids, 'Duplicate/empty transition ID')
        transition_ids.add(transition['id'])
        require(transition['from'] in state_ids and transition['to'] in state_ids, 'Transition references unknown state')
        trigger = transition['trigger']
        require(trigger['basis'] in BASIS and bool(trigger['description']), 'Invalid trigger')
        refs = trigger.get('evidence', [])
        require(trigger['basis'] != 'observed' or bool(refs), 'Observed trigger needs frame evidence')
        evidence(refs)
        motion = transition['motion']
        require(motion['kind'] in {'timed', 'gesture', 'scroll', 'state', 'none'}, 'Unknown motion kind')
        span = motion.get('window')
        if span:
            source, start, end = window(span)
            require(all(n in reviewed[source] for n in frames[source] if start <= n <= end), 'Motion contains unreviewed frames')
        else:
            require(trigger['basis'] != 'observed' and not motion.get('tracks'), 'Unobserved motion cannot have observed trigger/tracks')
        for track in motion.get('tracks', []):
            require(track['basis'] in BASIS and track['element'] and track['property'] and track['unit'], 'Invalid motion track')
            previous = -math.inf
            require(bool(track['samples']), 'Empty motion samples')
            for sample in track['samples']:
                number = sample['frame_number']
                f = frame(source, number)
                require(start <= number <= end and f['relative_seconds'] > previous, 'Motion samples must increase inside window')
                previous = f['relative_seconds']
                value = sample['value']
                require(type(value) in (int, float) and math.isfinite(value), 'Motion sample must be finite numeric value')
        if 'easing' in motion:
            require(motion['easing']['basis'] in BASIS, 'Invalid easing basis')
        verification = transition['verification']
        require(verification['status'] in {'pending', 'partial', 'blocked', 'passed'}, 'Unknown verification status')
        if verification['status'] == 'passed':
            require(bool(span) and bool(verification['evidence']), 'Passed motion needs demonstrated window and replay evidence')
            if motion['kind'] in {'timed', 'gesture', 'scroll'}:
                require(end - start >= 2 and all(n in dense_reviewed[source] for n in range(start, end + 1)),
                        'Passed motion needs every-frame review including intermediate frames')
                reports = verification.get('comparison_reports', [])
                require(isinstance(reports, list) and bool(reports), 'Passed motion needs local comparison_reports')
                review = verification.get('review', {})
                for key in ('motion', 'interaction'):
                    require(isinstance(review.get(key), str) and bool(review[key].strip()),
                            f'Passed motion needs a written {key} review')
                source_index = (path.parent / spec['sources'][source]).resolve()
                for report in reports:
                    require(isinstance(report, str) and bool(report), 'Comparison report must be a local path')
                    replay_report(path.parent / report, source_index, start, end)
            for item in verification['evidence']:
                require(isinstance(item, str) and bool(item), 'Replay evidence must be a path or URL')
                if not item.startswith(('https://', 'http://')):
                    require((path.parent / item).is_file(), f'Missing replay evidence: {item}')
    for control in spec.get('unseen_controls', []):
        require(control['basis'] in BASIS - {'observed'} and control['description'] and control['decision'], 'Unseen control needs non-observed basis and decision')
    return spec, list(dict.fromkeys(state_images))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('spec')
    args = parser.parse_args()
    try:
        spec, images = validate(args.spec)
        print(json.dumps({'valid': True, 'states': len(spec['states']), 'transitions': len(spec['transitions']), 'state_images': images, 'note': 'Structure and references only; not visual verification'}))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
