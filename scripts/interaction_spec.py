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
