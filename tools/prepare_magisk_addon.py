#!/usr/bin/env python3
"""Package unmodified official Magisk recovery components for this ARM64 device."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--apk', type=Path, required=True)
p.add_argument('--tree', type=Path, required=True)
a = p.parse_args()
expected = 'e0d32d2123532860f97123d927b1bb86c4e08e6fd8a48bfc6b5bee0afae9ebd5'
if hashlib.sha256(a.apk.read_bytes()).hexdigest() != expected:
    raise ValueError('APK differs from the official GitHub v30.7 release asset digest')
output = a.tree/'assets/Magisk-v30.7-sheng-recovery.zip'
entries = []
with zipfile.ZipFile(a.apk) as source, zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as target:
    if source.testzip():
        raise ValueError('Official APK CRC failure')
    for name in sorted(source.namelist()):
        if name.endswith('/') or not (name.startswith(('assets/', 'META-INF/com/google/', 'lib/arm64-v8a/'))
                                      or name == 'lib/armeabi-v7a/libmagisk.so'):
            continue
        data = source.read(name)
        info = zipfile.ZipInfo(name, (2026, 11, 3, 0, 0, 0))
        info.create_system = 3
        info.external_attr = 0o100644 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        target.writestr(info, data)
        entries.append({'path': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
with zipfile.ZipFile(output) as target, zipfile.ZipFile(a.apk) as source:
    if target.testzip():
        raise ValueError('Recovery ZIP CRC failure')
    for entry in entries:
        if target.read(entry['path']) != source.read(entry['path']):
            raise ValueError('Official component bytes changed')
report = {'version': '30.7', 'version_code': 30700,
          'official_release': 'https://github.com/topjohnwu/Magisk/releases/tag/v30.7',
          'official_apk_url': 'https://github.com/topjohnwu/Magisk/releases/download/v30.7/Magisk-v30.7.apk',
          'official_apk_sha256': expected, 'recovery_zip_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
          'recovery_zip_bytes': output.stat().st_size, 'component_bytes_unmodified': True,
          'selection': 'All official assets and recovery scripts, ARM64 libraries, optional ARM32 magisk binary',
          'entries': entries}
(a.tree/'assets/magisk-v30.7-provenance.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({k: v for k, v in report.items() if k != 'entries'}, indent=2))
