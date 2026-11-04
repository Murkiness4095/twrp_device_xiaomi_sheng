#!/usr/bin/env python3
"""Read block aliases and UFS state without modifying any boot metadata."""
import argparse
import json
import re
import subprocess
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--adb',required=True)
p.add_argument('--serial',required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=False)
command='ls -l /dev/block/by-name; getprop ro.boot.bootdevice; getprop ro.boot.slot_suffix; find /sys/devices/platform/soc/1d84000.ufshc -maxdepth 4 -name boot_lun_enabled -print; for p in /sys/devices/platform/soc/1d84000.ufshc/attributes/boot_lun_enabled; do echo $p; cat $p; done'
r=subprocess.run([a.adb,'-s',a.serial,'exec-out',command],capture_output=True,timeout=15)
(a.output/'raw-layout.txt').write_bytes(r.stdout+r.stderr)
mapping={name:device for name,device in re.findall(r'(\S+) -> (/dev/block/sd[a-z]+\d+)\s*$',r.stdout.decode(errors='replace'),re.M)}
pairs={}
for name,device in mapping.items():
    if name.endswith('_a') and name[:-2]+'_b' in mapping:
        prefix=name[:-2]
        pair=[device,mapping[prefix+'_b']]
        disks=[re.sub(r'\d+$','',path) for path in pair]
        pairs[prefix]={'partitions':pair,'disks':disks,'same_disk':disks[0]==disks[1]}
report={'mapping':mapping,'ab_pairs':pairs,'read_only':True}
(a.output/'layout.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'pairs':len(pairs),'split_pairs':{name:pair for name,pair in pairs.items() if not pair['same_disk']}},indent=2))
