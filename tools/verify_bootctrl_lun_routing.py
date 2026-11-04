#!/usr/bin/env python3
"""Compile real QTI slot-selection code with read-only captured topology mocks."""
import argparse
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--boot-control',type=Path,required=True)
p.add_argument('--header',type=Path,required=True)
p.add_argument('--baseline-zip',type=Path,required=True)
p.add_argument('--layout',type=Path,required=True)
p.add_argument('--report',type=Path,required=True)
a=p.parse_args()
source=a.boot_control.read_text()
start=source.index('int set_active_boot_slot(')
end=source.index('\nint set_slot_as_unbootable(',start)
method=source[start:end]
layout=json.loads(a.layout.read_text())
disks={name:re.sub(r'\d+$','',path) for name,path in layout['mapping'].items()}
entries=',\n'.join('{'+json.dumps(name)+','+json.dumps(path)+'}' for name,path in disks.items())
prefix=r'''
#include <cstdint>
#include <limits.h>
#include <cstdio>
#include <cstring>
#include <map>
#include <vector>
#include <string>
using namespace std;
#include "test-gpt.h"
#define ALOGE(...) ((void)0)
struct boot_control_module {};
const char* slot_suffix_arr[]={"_a","_b"};
static int switched_lun=0, updated_shared=0;
static map<string,string> topology={
'''+entries+r'''};
int boot_control_check_slot_sanity(boot_control_module*, unsigned slot) { return slot>=2; }
int gpt_utils_is_ufs_device() { return 1; }
int gpt_utils_get_partition_map(vector<string>& names,map<string,vector<string>>& output) {
 for (const auto& name:names) if(topology.count(name)) output[topology[name]].push_back(name);
 return 0;
}
static int boot_ctl_set_active_slot_for_partitions(vector<string> names,unsigned) {
 for (const auto& name:names) {
  const string other=name.substr(0,name.size()-2)+"_b";
  if(!topology.count(other)) continue;
  // The real per-disk code looks for both entries in this same GPT.
  if(topology[name]!=topology[other]) return -1;
  ++updated_shared;
 }
 return 0;
}
int gpt_utils_set_xbl_boot_partition(enum boot_chain chain) {
 switched_lun=chain==NORMAL_BOOT?1:2; return 0;
}
'''
suffix=r'''
int main() {
 boot_control_module module;
 const int b=set_active_boot_slot(&module,1);
 const int b_lun=switched_lun, b_shared=updated_shared;
 switched_lun=0; updated_shared=0;
 const int a=set_active_boot_slot(&module,0);
 const int a_lun=switched_lun;
 switched_lun=0;
 const int invalid=set_active_boot_slot(&module,2);
 printf("{\"slot_b_result\":%d,\"slot_b_boot_lun\":%d,\"slot_a_result\":%d,\"slot_a_boot_lun\":%d,\"shared_pairs_updated\":%d,\"invalid_slot_rejected\":%s,\"invalid_slot_switched_lun\":%s}\n",b,b_lun,a,a_lun,b_shared,invalid!=0?"true":"false",switched_lun?"true":"false");
}
'''
with zipfile.ZipFile(a.baseline_zip) as archive:
    baseline=archive.read('device_xiaomi_sheng/gpt-utils/gpt-utils.h').decode()
reports={}
with tempfile.TemporaryDirectory(prefix='sheng-bootctrl-routing-') as tmp:
    root=Path(tmp)
    (root/'test.cpp').write_text(prefix+method+suffix)
    for label,header in [('baseline',baseline),('fixed',a.header.read_text())]:
        (root/'test-gpt.h').write_text(header)
        subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-unused-variable',
                        root/'test.cpp','-o',root/'test'],check=True)
        reports[label]=json.loads(subprocess.check_output([root/'test']))
fixed=reports['fixed']
passed=(reports['baseline']['slot_b_result']!=0 and fixed['slot_b_result']==0 and
        fixed['slot_b_boot_lun']==2 and fixed['slot_a_result']==0 and fixed['slot_a_boot_lun']==1 and
        fixed['shared_pairs_updated']>0 and fixed['invalid_slot_rejected'] and not fixed['invalid_slot_switched_lun'])
report={'actual_qti_method_compiled':True,'captured_device_topology':str(a.layout),
        'device_partition_writes':False,'ufs_ioctl_executed':False,'results':reports,
        'passed':passed,'physical_slot_switch_verified':False}
a.report.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
raise SystemExit(0 if passed else 1)
