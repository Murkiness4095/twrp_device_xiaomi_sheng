#!/usr/bin/env python3
"""Import stock 303 files from the independently unpacked official image set.

Input layout: stock-images/{boot,recovery,vendor_boot}/... and
roots/{vendor,odm,vendor_dlkm,system,system_ext}/..., prepared read-only.
No map220v tree is read by this program. No devices are opened or flashed.
"""
import argparse
import gzip
import hashlib
import json
import re
import shutil
import struct
import subprocess
from pathlib import Path


def needed(path):
    text = subprocess.check_output(['readelf', '-d', str(path)], text=True)
    return re.findall(r'\(NEEDED\).*?\[([^]]+)\]', text)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--stock-work', type=Path, required=True)
    p.add_argument('--images', type=Path, required=True, help='Original official images directory')
    a = p.parse_args()
    tree = Path(__file__).resolve().parent
    dest = tree / 'recovery/root'
    work = a.stock_work.resolve()
    roots = work / 'roots'
    rec = work / 'stock-images/recovery/ramdisk-root'
    vendor_ramdisk = work / 'stock-images/vendor_boot/vendor_ramdisk00-root'
    manifest = []

    def copy(source, relative):
        if not source.is_file():
            raise FileNotFoundError(source)
        target = tree / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        target.chmod(0o755 if '/bin/' in str(relative) else 0o644)
        manifest.append({'source': str(source.relative_to(work)) if source.is_relative_to(work)
                         else 'official-images/' + source.name,
                         'destination': str(relative), 'bytes': source.stat().st_size,
                         'sha256': hashlib.sha256(source.read_bytes()).hexdigest()})

    copy(work/'stock-images/boot/kernel', Path('prebuilt/stock303/Image'))
    copy(work/'stock-images/vendor_boot/dtb', Path('prebuilt/stock303/dtb'))
    copy(a.images/'dtbo.img', Path('prebuilt/stock303/dtbo.img'))
    # The platform ueventd imports this file. QSEE drops to system and needs
    # smcinvoke and qcom DMA heaps with the vendor's original permissions.
    copy(roots/'vendor/etc/ueventd.rc', Path('recovery/root/vendor/etc/ueventd.rc'))
    kernel = (tree/'prebuilt/stock303/Image').read_bytes()
    version = re.search(rb'Linux version 5\.15\.178[^\x00\n]+', kernel)
    if not version:
        raise RuntimeError('Expected the official 303 5.15.178 kernel')
    compressed = tree/'prebuilt/stock303/Image.gz'
    compressed.write_bytes(gzip.compress(kernel, compresslevel=9, mtime=0))
    manifest.append({'source':'stock-images/boot/kernel',
                     'destination':'prebuilt/stock303/Image.gz',
                     'bytes':compressed.stat().st_size,
                     'sha256':hashlib.sha256(compressed.read_bytes()).hexdigest(),
                     'transformation':'deterministic gzip -9; decompressed bytes equal official Image'})

    programs = [(roots/'vendor/bin/qseecomd', Path('vendor/bin/qseecomd')),
                (roots/'vendor/bin/hw/android.hardware.security.keymint-service-qti',
                 Path('vendor/bin/hw/android.hardware.security.keymint-service-qti')),
                (roots/'vendor/bin/hw/android.hardware.gatekeeper@1.0-service-qti',
                 Path('vendor/bin/hw/android.hardware.gatekeeper@1.0-service-qti')),
                (roots/'odm/bin/touch_report_debug', Path('vendor/odm/bin/touch_report_debug'))]
    plugins = [roots/'vendor/lib64/hw/android.hardware.gatekeeper@1.0-impl-qti.so',
               roots/'odm/lib64/libtouchsensor.so', roots/'odm/lib64/libtensorflowlite_touch_c.so']
    search = [roots/'vendor/lib64', roots/'odm/lib64', work/'apex-v33/root/lib64', rec/'system/lib64',
              roots/'system/system/lib64/bootstrap', roots/'system/system/lib64',
              roots/'system/lib64', roots/'system_ext/lib64',
              roots/'system_ext/system_ext/lib64', roots/'vendor/lib64/hw', roots/'odm/lib64/hw']
    # Stable AIDL HALs must register with /dev/binder. The VNDK libbinder default
    # is /dev/vndbinder; use the matching stock recovery's platform variants.
    runtime_overrides={name:rec/'system/lib64'/name for name in ('libbinder.so','libbinder_ndk.so')}
    resolved, queue = {}, []
    # qseecomd's listener plugins are loaded with dlopen, not DT_NEEDED.
    # Resolve its literal plugin names from this same stock image set.
    dlopen_names=sorted(set(re.findall(rb'[A-Za-z0-9_@.+-]+\.so(?=\x00)',programs[0][0].read_bytes())))
    dlopen_roots=[]
    unavailable_optional_plugins=[]
    for encoded in dlopen_names:
        name=encoded.decode()
        source=next((directory/name for directory in search if (directory/name).is_file()),None)
        if source is None:
            if name in ('librpmb.so','libssd.so','libdrmfs.so','libdrmtime.so'):
                raise FileNotFoundError('qseecomd listener plugin: '+name)
            unavailable_optional_plugins.append(name)
            continue
        dlopen_roots.append(name)
        resolved[name]=source
        queue.extend(needed(source))
    for source, relative in programs:
        copy(source, Path('recovery/root')/relative)
        queue.extend(needed(source))
    for source in plugins:
        if not source.is_file():
            raise FileNotFoundError(source)
        resolved[source.name] = source
        queue.extend(needed(source))
    while queue:
        name = queue.pop(0)
        if name in resolved:
            continue
        source = runtime_overrides.get(name) or next((directory/name for directory in search if (directory/name).is_file()), None)
        if source is None:
            raise RuntimeError(f'Cannot resolve stock runtime library: {name}')
        resolved[name] = source
        queue.extend(needed(source))
    for name, source in sorted(resolved.items()):
        copy(source, Path('recovery/root/vendor/lib64/sheng303-runtime')/name)
        if source.is_relative_to(roots/'vendor'):
            copy(source, Path('recovery/root/vendor')/source.relative_to(roots/'vendor'))
        elif source.is_relative_to(roots/'odm'):
            copy(source, Path('recovery/root/vendor/odm')/source.relative_to(roots/'odm'))
    copy(rec/'system/bin/linker64', Path('recovery/root/vendor/bin/sheng303-linker64'))

    for name in ('n81a_nova_thp_config.ini', 'novatek_nt36532_n81a_fw_csot.bin',
                 'film_model.tflite', 'glove_model.tflite', 'water_check.tflite'):
        copy(roots/'odm/firmware'/name, Path('recovery/root/vendor/odm/firmware')/name)
    copy(roots/'odm/firmware/novatek_nt36532_n81a_fw_csot.bin',
         Path('recovery/root/lib/firmware/novatek_nt36532_n81a_fw_csot.bin'))

    # A standalone image cannot borrow the vendor_boot modules. Include all
    # first-stage recovery modules and the matching THP dependency closure.
    module_dirs = [vendor_ramdisk/'lib/modules', roots/'vendor_dlkm/lib/modules']
    deps = {}
    for directory in reversed(module_dirs):
        for line in (directory/'modules.dep').read_text().splitlines():
            name, values = line.split(':', 1)
            deps[Path(name).name] = [Path(x).name for x in values.split()]
    ordered, visiting = [], set()
    selected = {}

    def visit(name):
        if name in ordered:
            return
        if name in visiting:
            raise ValueError('Module dependency cycle: '+name)
        visiting.add(name)
        for dep in deps.get(name, []):
            visit(dep)
        visiting.remove(name)
        source = next((d/name for d in module_dirs if (d/name).is_file()), None)
        if source is None:
            raise FileNotFoundError(name)
        copy(source, Path('recovery/root/lib/modules')/name)
        selected[name] = source
        ordered.append(name)
    boot_modules = module_dirs[0]
    for source in sorted(boot_modules.glob('*.ko')):
        visit(source.name)
    visit('xiaomi_touch.ko')
    visit('nt36532_touch.ko')
    module_root = dest/'lib/modules'
    for name in ('modules.alias','modules.blocklist','modules.softdep'):
        copy(boot_modules/name, Path('recovery/root/lib/modules')/name)
    (module_root/'modules.dep').write_text(''.join(
        '/lib/modules/'+name+':'+''.join(' /lib/modules/'+x for x in deps.get(name,[]))+'\n'
        for name in sorted(selected)))
    loads=[]
    for name in (boot_modules/'modules.load.recovery').read_text().splitlines()+['xiaomi_touch.ko','nt36532_touch.ko']:
        name=Path(name.strip()).name
        if not name or name in loads:
            continue
        if name not in selected:
            raise ValueError('Recovery load list references absent module: '+name)
        loads.append(name)
    # fastboot boot and recovery boot both load this complete list, regardless
    # of the bootloader's androidboot.mode / force_normal_boot additions.
    for name in ('modules.load','modules.load.recovery'):
        (module_root/name).write_text('\n'.join(loads)+'\n')
    config = dest/'vendor/etc/sheng303'
    config.mkdir(parents=True, exist_ok=True)
    (config/'modules.order').write_text('\n'.join(ordered)+'\n')
    (dest/'vendor/etc/vintf').mkdir(parents=True, exist_ok=True)
    shutil.copy2(tree/'manifest.xml', dest/'vendor/etc/vintf/manifest.xml')
    inspection = json.loads((work/'stock-images/inspection.json').read_text())
    report = {'source': 'Official user-provided OS3.0.303.0.WNXCNXM images',
              'blobs_copied_from_another_device_tree': False, 'kernel': version[0].decode(),
              'boot_layout_reference': 'map220v sheng a9a2994997fa3574b6e718561b5d1c884661b89e: legacy v2 addresses and first-stage module layout',
              'model': '24018RPACC', 'boot_layout': 'standalone v2, embedded kernel/DTB/DTBO/modules',
              'requires_installed_303_boot_or_vendor_boot': False,
              'paired_images': {name: data['sha256'] for name, data in inspection['images'].items()},
              'runtime_library_count': len(resolved), 'extra_modules': ordered,
              'qseecomd_dlopen_roots':dlopen_roots,
              'qseecomd_unavailable_optional_plugins':unavailable_optional_plugins,
              'first_stage_load_list': loads, 'embedded_module_count':len(selected),
              'files': manifest, 'hardware_verified': False}
    (tree/'stock303-manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    (tree/'proprietary-files.txt').write_text('\n'.join(sorted(set(x['destination'] for x in manifest)))+'\n')
    # Declare ELF objects as prebuilt modules instead of putting executables
    # into PRODUCT_COPY_FILES (which Android 12 explicitly rejects).
    elf_paths = sorted({x['destination'][len('recovery/root/'):] for x in manifest
                        if x['destination'].startswith('recovery/root/') and
                        (tree/x['destination']).read_bytes()[:4] == b'\x7fELF'})
    module_names = {path: 'sheng303_' + re.sub(r'[^A-Za-z0-9_]', '_', path) for path in elf_paths}
    runtime_names = {Path(path).name: module_names[path] for path in elf_paths
                     if path.startswith('vendor/lib64/sheng303-runtime/')}
    lines = ['# Generated by extract-files.py from official 303 files.', 'LOCAL_PATH := $(call my-dir)', '']
    for path in elf_paths:
        file = tree/'recovery/root'/path
        is_module = struct.unpack_from('<H', file.read_bytes(), 16)[0] == 1
        is_binary = '/bin/' in path
        kind = 'ETC' if is_module else ('EXECUTABLES' if is_binary else 'SHARED_LIBRARIES')
        suffix = '.so' if kind == 'SHARED_LIBRARIES' else ''
        stem = Path(path).name[:-3] if suffix else Path(path).name
        deps = [runtime_names[name] for name in needed(file)] if not is_module else []
        lines += ['include $(CLEAR_VARS)', f'LOCAL_MODULE := {module_names[path]}',
                  'LOCAL_MODULE_TAGS := optional', 'LOCAL_MODULE_OWNER := xiaomi',
                  'LOCAL_NOTICE_FILE := $(LOCAL_PATH)/NOTICE',
                  f'LOCAL_MODULE_CLASS := {kind}', f'LOCAL_MODULE_STEM := {stem}',
                  f'LOCAL_MODULE_SUFFIX := {suffix}', 'LOCAL_MULTILIB := 64',
                  f'LOCAL_SRC_FILES := recovery/root/{path}',
                  f'LOCAL_MODULE_PATH := $(TARGET_RECOVERY_ROOT_OUT)/{Path(path).parent}',
                  'LOCAL_STRIP_MODULE := false', 'LOCAL_SYSTEM_SHARED_LIBRARIES :=',
                  'LOCAL_SHARED_LIBRARIES := ' + ' '.join(deps),
                  'include $(BUILD_PREBUILT)', '']
    lines += ["# Android's module scan stops at this file, so load the device UI library here.",
              'include $(LOCAL_PATH)/twrp-ui/Android.mk', '']
    (tree/'Android.mk').write_text('\n'.join(lines))
    continuation = ' ' + chr(92) + chr(10) + '    '
    modules = continuation.join(module_names[path] for path in elf_paths)
    paths = continuation.join(elf_paths)
    (tree/'proprietary.mk').write_text(
        '# Generated by extract-files.py from official 303 files.\n'
        + 'SHENG303_ELF_RELATIVE_FILES :=' + continuation + paths + '\n'
        + 'SHENG303_PREBUILT_MODULES :=' + continuation + modules + '\n'
        + 'PRODUCT_PACKAGES += $(SHENG303_PREBUILT_MODULES)\n'
        + 'TARGET_RECOVERY_DEVICE_MODULES += $(SHENG303_PREBUILT_MODULES)\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('files','paired_images')}, indent=2))


if __name__ == '__main__':
    main()
