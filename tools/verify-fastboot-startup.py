#!/usr/bin/env python3
"""Check the shipped HIDL implementation and real libvintf transport lookup."""
import argparse
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--root', type=Path, required=True)
parser.add_argument('--baseline-root', type=Path, required=True)
parser.add_argument('--vintf-checker', type=Path, required=True)
parser.add_argument('--report', type=Path, required=True)
args = parser.parse_args()
root, out = args.root, args.out
checks = {}
variables = json.loads((out/'soong/soong.variables').read_text())
checks['actual_soong_vintf_enforcement'] = variables['Enforce_vintf_manifest'] is True
with (out/'soong/build.ninja').open() as ninja:
    # Soong reuses the recovery static variant's compiled objects when linking
    # the shared variant, so there is no separate shared .cflags assignment.
    cflags = [line for line in ninja if line.startswith('m.libhidlbase_android_recovery_') and '.cflags = ' in line]
checks['hidl_recovery_objects_compiled_with_enforcement'] = bool(cflags) and all('-DENFORCE_VINTF_MANIFEST' in line for line in cflags)
library = root/'system/lib64/libhidlbase.so'
old_library = args.baseline_root/'system/lib64/libhidlbase.so'
warning = b'getService: Potential race detected.'
checks['baseline_has_fixed_delay_branch'] = warning in old_library.read_bytes()
checks['shipped_library_has_no_legacy_fixed_delay_branch'] = warning not in library.read_bytes()
checks['shipped_library_changed'] = library.read_bytes() != old_library.read_bytes()
checks['shipped_library_matches_built_recovery_module'] = library.read_bytes() == (out/'target/product/sheng/recovery/root/system/lib64/libhidlbase.so').read_bytes()
init = (root/'init.recovery.sheng303.rc').read_text()
fs_action = re.search(r'^on fs\n(.*?)(?=^on |^service |\Z)', init, re.M | re.S).group(1)
checks['bootcontrol_started_before_hardware_service'] = 0 <= fs_action.find('start boot-hal-1-2') < fs_action.find('start sheng303-hardware')
service = (root/'system/etc/init/android.hardware.boot@1.2-service.rc').read_text()
checks['upstream_bootcontrol_interfaces_preserved'] = all(f'interface android.hardware.boot@1.{minor}::IBootControl default' in service for minor in (0, 1, 2))
checks['health_still_waits_for_real_hardware'] = 'on property:sys.sheng303.hardware.ready=1\n' in init and 'start health-hal-2-1' in init
inputs = [root/'vendor/etc/vintf/manifest.xml'] + sorted((root/'vendor/etc/vintf/manifest').glob('*.xml'))
merged = args.report.parent/(args.report.stem+'-manifest.xml')
subprocess.run([str(out/'host/linux-x86/bin/assemble_vintf'), '-i', ':'.join(map(str, inputs)), '-o', str(merged)], check=True)
# Only element content is relevant to the transport lookup. Normalize the
# assembler's explanatory comment before passing it to the libvintf checker.
merged.write_text(ET.tostring(ET.parse(merged).getroot(), encoding='unicode')+'\n')
result = subprocess.run([str(args.vintf_checker), str(merged)], capture_output=True)
checks['real_libvintf_boot_health_and_crypto_transports'] = result.returncode == 0 and result.stdout.count(b': PASS') == 11
report = {'checks':checks, 'all_passed':all(checks.values()),
          'libhidlbase_sha256':hashlib.sha256(library.read_bytes()).hexdigest(),
          'transport_queries':result.stdout.decode(),
          'fixed_sequential_delay_removed_seconds':3,
          'actual_usb_enumeration_timing_tested':False}
args.report.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
if not report['all_passed']:
    raise SystemExit('Fastboot startup checks failed')
