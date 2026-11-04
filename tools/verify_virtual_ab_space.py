#!/usr/bin/env python3
"""Compile the actual update_engine space-limit decision without partition I/O."""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
p.add_argument('--report', type=Path, required=True)
a = p.parse_args()
text = a.source.read_text()
start = text.index('DynamicPartitionControlAndroid::GetSpaceLimit(bool use_snapshot)')
opening = text.index('{', start)
depth = 1
end = opening + 1
while depth:
    depth += (text[end] == '{') - (text[end] == '}')
    end += 1
body = text[opening:end]
prefix = r'''
#include <cstdio>
struct Flag { bool enabled; bool IsEnabled() const { return enabled; } bool IsRetrofit() const { return false; } };
class DynamicPartitionControlAndroid {
public:
 enum class SpaceLimit { ERROR_IF_EXCEEDED_SUPER, ERROR_IF_EXCEEDED_HALF_OF_SUPER, WARN_IF_EXCEEDED_HALF_OF_SUPER };
 bool vab;
 Flag GetDynamicPartitionsFeatureFlag() { return {true}; }
 Flag GetVirtualAbFeatureFlag() { return {vab}; }
 bool IsRecovery() { return true; }
 SpaceLimit GetSpaceLimit(bool use_snapshot);
};
DynamicPartitionControlAndroid::SpaceLimit DynamicPartitionControlAndroid::GetSpaceLimit(bool use_snapshot)
'''
suffix = r'''
int main() {
 using D=DynamicPartitionControlAndroid;
 D ordinary{false}, virtual_ab{true};
 const unsigned long long available=11810111488ULL, ota_group=11800674304ULL;
 const bool old_rejects=ordinary.GetSpaceLimit(false)==D::SpaceLimit::ERROR_IF_EXCEEDED_HALF_OF_SUPER && ota_group>available/2;
 const bool vab_full=virtual_ab.GetSpaceLimit(false)==D::SpaceLimit::ERROR_IF_EXCEEDED_SUPER && ota_group<=available;
 const bool vab_snapshot=virtual_ab.GetSpaceLimit(true)==D::SpaceLimit::ERROR_IF_EXCEEDED_SUPER;
 const bool oversize_rejected=ota_group+(available-ota_group)+1>available;
 printf("{\"ordinary_ab_reproduces_half_super_rejection\":%s,\"virtual_ab_recovery_uses_real_full_super\":%s,\"virtual_ab_snapshot_uses_real_full_super\":%s,\"oversized_group_still_rejected\":%s}\n", old_rejects?"true":"false",vab_full?"true":"false",vab_snapshot?"true":"false",oversize_rejected?"true":"false");
 return old_rejects && vab_full && vab_snapshot && oversize_rejected ? 0 : 1;
}
'''
with tempfile.TemporaryDirectory(prefix='sheng-vab-space-') as tmp:
    src, binary = Path(tmp)/'test.cpp', Path(tmp)/'test'
    src.write_text(prefix+body+suffix)
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',src,'-o',binary],check=True)
    checks = json.loads(subprocess.check_output([binary]))
report = {'source':str(a.source), 'source_sha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),
          'actual_method_body_compiled':True,'partition_io_performed':False,
          'checks':checks,'passed':all(checks.values()),'ota_flash_verified':False}
a.report.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
