#!/usr/bin/env python3
"""Read official boot-family images and safely inspect their ramdisks in Linux."""
import argparse
import gzip
import hashlib
import json
import subprocess
from pathlib import Path
from newc import unpack_cpio


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--images', required=True, type=Path)
    p.add_argument('--platform', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    unpacker = a.platform / 'system/tools/mkbootimg/unpack_bootimg.py'
    report = {'source_images': str(a.images), 'images': {}, 'read_only_source': True}
    for name in ('boot', 'init_boot', 'recovery', 'vendor_boot'):
        source, dest = a.images / (name + '.img'), a.output / name
        result = subprocess.run(['python3', str(unpacker), '--boot_img', str(source),
                                 '--out', str(dest)], text=True, capture_output=True, check=True)
        (dest / 'header.txt').write_text(result.stdout)
        metadata = {'bytes': source.stat().st_size,
                    'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                    'header': result.stdout, 'ramdisks': {}}
        ramdisks = ([dest / 'vendor_ramdisk00'] if name == 'vendor_boot' else [dest / 'ramdisk'])
        for ramdisk in ramdisks:
            if not ramdisk.is_file() or not ramdisk.stat().st_size:
                continue
            content = ramdisk.read_bytes()
            if content.startswith(b'\x1f\x8b'):
                cpio = gzip.decompress(content)
                compression = 'gzip'
            elif content[:4] in (b'\x02\x21\x4c\x18', b'\x04\x22\x4d\x18'):
                cpio = subprocess.check_output(['lz4', '-d', '-c', str(ramdisk)])
                compression = 'lz4'
            else:
                raise ValueError(f'Unknown ramdisk compression: {ramdisk}')
            root = dest / (ramdisk.name + '-root')
            entries = unpack_cpio(cpio, root)
            files = sorted(str(x.relative_to(root)) for x in root.rglob('*')
                           if x.is_file() and not x.is_symlink())
            (dest / (ramdisk.name + '-files.json')).write_text(json.dumps(files, indent=2)+'\n')
            metadata['ramdisks'][ramdisk.name] = {
                'compression': compression, 'cpio_entries': entries,
                'root': str(root), 'regular_file_count': len(files)}
        report['images'][name] = metadata
    (a.output / 'inspection.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
