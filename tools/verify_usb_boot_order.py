#!/usr/bin/env python3
"""Check USB setup ordering in the actual core and imported device init files.

This is a limited static init-action replay, not a kernel or USB hardware test.
Core actions precede imported device actions, as in Android init and the logs.
"""
import argparse
import json
import shlex
from pathlib import Path


def actions(path):
    result = []
    current = None
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if not raw[0].isspace():
            current = None
            if line.startswith('on '):
                current = {'condition': line[3:], 'commands': [], 'source': f'{path.name}:{number}'}
                result.append(current)
        elif current is not None:
            current['commands'].append(shlex.split(line))
    return result


def verify(core, usb):
    all_actions = actions(core) + actions(usb)
    props = {'ro.debuggable': '1'}
    functions, mounts, trace, errors = set(), [], [], []
    configfs_mounted = False
    before_fs = None
    for event in ('early-init', 'init', 'early-fs', 'fs'):
        if event == 'fs':
            before_fs = props.get('sys.usb.configfs')
        # Event actions are selected using properties at event dispatch time.
        selected = []
        for action in all_actions:
            conditions = action['condition'].split(' && ')
            if event not in conditions:
                continue
            matches = True
            for condition in conditions:
                if condition.startswith('property:'):
                    key, value = condition[9:].split('=', 1)
                    matches &= key in props if value == '*' else props.get(key) == value
            if matches:
                selected.append(action)
        for action in selected:
            for command in action['commands']:
                if command[:2] == ['setprop', 'sys.usb.configfs']:
                    props[command[1]] = command[2]
                    trace.append(f'{event}: {action["source"]}: configfs={command[2]}')
                elif command[:2] == ['mount', 'configfs']:
                    configfs_mounted = True
                    trace.append(f'{event}: {action["source"]}: mount configfs')
                elif command[0] == 'mkdir' and '/functions/ffs.' in command[1]:
                    name = command[1].rsplit('ffs.', 1)[1]
                    if not configfs_mounted:
                        errors.append('Function created before configfs mount: ' + name)
                    functions.add(name)
                    trace.append(f'{event}: {action["source"]}: create ffs.{name}')
                elif command[:2] == ['mount', 'functionfs']:
                    name = command[2]
                    if name not in functions:
                        errors.append('FunctionFS mount precedes function creation: ' + name)
                    mounts.append(name)
                    trace.append(f'{event}: {action["source"]}: mount FunctionFS {name}')
    if before_fs != '1':
        errors.append('configfs is not enabled before fs event dispatch')
    for name in ('adb', 'fastboot', 'mtp'):
        if mounts.count(name) != 1:
            errors.append('Expected exactly one FunctionFS mount: ' + name)
    return {'kind': 'static init action order replay', 'hardware_verified': False,
            'configfs_before_fs': before_fs, 'functionfs_mounts': mounts,
            'trace': trace, 'errors': errors, 'passed': not errors}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--core', type=Path, required=True)
    parser.add_argument('--usb', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.core, args.usb)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['passed'] else 1)
