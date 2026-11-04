#!/usr/bin/env python3
"""Extract one official APEX payload into an isolated Linux task directory."""
import argparse
import json
import subprocess
import zipfile
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--apex', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--stock-recovery-root', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    payload = a.output / 'payload.img'
    with zipfile.ZipFile(a.apex) as archive:
        payload.write_bytes(archive.read('apex_payload.img'))
    data = payload.read_bytes()[:2048]
    root = a.output / 'root'
    if data[1080:1082] == b'\x53\xef':
        root.mkdir()
        result = subprocess.run(['debugfs', '-R', f'rdump / {root}', str(payload)],
                                capture_output=True, text=True, check=True)
        filesystem = 'ext4'
    elif data[1024:1028] == b'\xe2\xe1\xf5\xe0':
        rec = a.stock_recovery_root
        result = subprocess.run(['qemu-aarch64', '-L', str(rec), '-E',
                                 'LD_LIBRARY_PATH=/system/lib64',
                                 str(rec/'system/bin/fsck.erofs'), '--no-preserve-owner',
                                 f'--extract={root}', str(payload)], capture_output=True, text=True, check=True)
        filesystem = 'erofs'
    else:
        raise ValueError('Unknown APEX payload filesystem')
    (a.output/'extract.log').write_text(result.stdout+result.stderr)
    if not (root/'lib64').is_dir():
        raise RuntimeError('No extracted lib64 directory')
    report = {'apex': str(a.apex), 'root': str(root), 'filesystem': filesystem,
              'lib64_count': len(list((root/'lib64').rglob('*.so')))}
    (a.output/'inspection.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
