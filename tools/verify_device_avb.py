#!/usr/bin/env python3
"""Compare the port against the real pinned OrangeFox AVB implementation."""
import argparse,json,os,re,shutil,subprocess,tempfile
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--orangefox-source',type=Path,required=True)
parser.add_argument('--report',type=Path)
args=parser.parse_args()
root=Path(__file__).resolve().parent.parent
native=(args.orangefox_source/'partitionmanager.cpp').read_text()
body=native[native.index('#define AVB_MAGIC "AVB0"'):native.index('\nint TWPartitionManager::Process_Fstab(')]
# Only remove GUI reporting; disk operations and native A/B aggregation stay exact.
body=re.sub(r'\tif \(Display_Info\) \{.*?\n\t\}\n\treturn ret;', '\treturn ret;',body,count=1,flags=re.S)
reference=r'''
#include <cstdio>
#include <cstring>
#include <string>
#include <unistd.h>
using namespace std;
static string devices;
struct TWFunc { static bool Path_Exists(const string& p) { return p!="/dev/block/bootdevice/by-name/"; } };
struct TWPartitionManager { bool Disable_AVB2(bool); };
static constexpr char AVB_VBMETA_IMAGE_FLAGS_VERIFICATION_DISABLED=2;
static FILE* mapped_fopen(const char* name,const char* mode) {
 string p=name; const string prefix="/dev/block/by-name/";
 if(p.find(prefix)==0)p=devices+"/"+p.substr(prefix.size());
 return fopen(p.c_str(),mode);
}
#define fopen mapped_fopen
'''+body+r'''
int main(int argc,char** argv) {
 if(argc!=4 || string(argv[1])!="--disable" || string(argv[2])!="--device-dir")return 2;
 devices=argv[3]; TWPartitionManager manager; return manager.Disable_AVB2(false)?0:1;
}
'''
checks={}
with tempfile.TemporaryDirectory(prefix='sheng-orangefox-avb-') as folder:
 temp=Path(folder); port=temp/'port';ref=temp/'reference'
 (temp/'reference.cpp').write_text(reference)
 for source,binary,flags in [(root/'src/sheng_avb.cpp',port,['-DSHENG_AVB_HOST_TEST']),(temp/'reference.cpp',ref,['-DAB_OTA_UPDATER','-Wno-unused-parameter'])]:
  subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',*flags,str(source),'-o',str(binary)],check=True)
 names=['vbmeta_a','vbmeta_system_a','vbmeta_b','vbmeta_system_b']
 cases=['flags-'+str(value) for value in (0,1,2,3,4,255)]+['bad-magic','bad-version','truncated','short-valid','missing','empty']
 for case in cases:
  source=temp/('original-'+case);source.mkdir()
  flag=int(case[6:]) if case.startswith('flags-') else 3
  for name in names:
   data=bytearray(os.urandom(65536));data[:4]=b'AVB0';data[123]=flag
   (source/name).write_bytes(data)
  target=source/names[1]
  if case=='bad-magic':target.write_bytes(b'NOPE'+target.read_bytes()[4:])
  if case=='bad-version':data=bytearray(target.read_bytes());data[4:8]=b'\x00\x00\x00\x09';target.write_bytes(data)
  if case=='truncated':target.write_bytes(target.read_bytes()[:123])
  if case=='short-valid':target.write_bytes(target.read_bytes()[:124])
  if case=='missing':target.unlink()
  if case=='empty':target.write_bytes(b'')
  paths=[];results=[];outputs=[]
  for binary in (ref,port):
   destination=temp/(case+'-'+binary.name);shutil.copytree(source,destination);paths.append(destination)
   process=subprocess.run([str(binary),'--disable','--device-dir',str(destination)],capture_output=True,text=True)
   results.append(process.returncode);outputs.append(process.stdout)
  assert results[0]==results[1],(case,results)
  assert {p.name:p.read_bytes() for p in paths[0].iterdir()}=={p.name:p.read_bytes() for p in paths[1].iterdir()},case
  assert sorted(p.name for p in paths[1].iterdir())==sorted(p.name for p in source.iterdir())
  checks[case+'_matches_upstream']=True
  messages=json.loads((root/'tools/device-avb-messages.json').read_text())['en']
  lines=outputs[1].splitlines()
  assert len(lines)==6 and lines[0]==messages[0] and lines[-1]==messages[3 if results[1]==0 else 4],case
  for name in names:
   success=(paths[1]/name).is_file() and (paths[1]/name).read_bytes().startswith(b'AVB0') and len((paths[1]/name).read_bytes())>=124
   assert messages[1 if success else 2].replace('{1}',name) in lines[1:-1],(case,name)
  checks[case+'_visible_partition_results_and_summary']=True
  if case=='flags-3':
   for name in names:
    original=(source/name).read_bytes();actual=(paths[1]/name).read_bytes()
    assert actual[:123]==original[:123] and actual[123]==2 and actual[124:]==original[124:]
   checks['only_byte_123_set_to_2']=True
  if case=='bad-magic':
   assert (paths[1]/names[0]).read_bytes()[123]==2 and results[1]==1
   checks['native_partial_failure_semantics_preserved']=True
 for language,messages in json.loads((root/'tools/device-avb-messages.json').read_text()).items():
  destination=paths[1]
  process=subprocess.run([str(port),'--disable','--device-dir',str(destination),'--language',language],capture_output=True,text=True)
  assert process.returncode==1
  lines=process.stdout.splitlines()
  assert len(lines)==6 and lines[0]==messages[0] and lines[-1]==messages[4],language
  assert messages[2].replace('{1}',names[1]) in lines and all(messages[1].replace('{1}',name) in lines for name in (names[0],names[2],names[3])),language
  checks[language+'_localized_failure_output']=True
 report={'implementation':'OrangeFox native A/B port','upstream_commit':'6bd902d14f754ab98a7cccc5598f7b9d135cfc38','checks':checks,'all_passed':all(checks.values()),'backup_or_metadata_operations':False,'physical_partition_writes':False}
 print(json.dumps(report,indent=2))
 if args.report:args.report.write_text(json.dumps(report,indent=2)+'\n')
