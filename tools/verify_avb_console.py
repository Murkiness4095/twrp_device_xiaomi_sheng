#!/usr/bin/env python3
"""Run the real TWRP terminal action with the AVB wrapper on temporary files."""
import argparse
import json
import os
import shlex
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--twrp-source', type=Path, required=True)
parser.add_argument('--root', type=Path)
parser.add_argument('--report', type=Path, required=True)
args = parser.parse_args()
tree = Path(__file__).resolve().parent.parent
action_source = (args.twrp_source/'gui/action.cpp').read_text()
start = action_source.index('int GUIAction::terminalcommand(')
end = action_source.index('\nint GUIAction::', start+1)
native = action_source[start:end]
harness = r'''
#include <cstdio>
#include <cerrno>
#include <cstring>
#include <cstdarg>
#include <string>
#include <sys/select.h>
#include <unistd.h>
using std::string;
static string location;
static string wrapper_command;
FILE* gui_output;
struct DataManager {
 static void GetValue(const char*, string& value) { value=location; }
 static void GetValue(const char*, int& value) { value=1; }
 static void SetValue(const char* key,int value) {
  if(string(key)=="tw_operation_status") fprintf(stderr,"NATIVE_STATUS=%d\n",value);
 }
};
extern "C" void gui_print(const char* format,...);
static FILE* mapped_popen(const char* command,const char* mode) {
 string actual=command;
 const string prefix="/system/bin/sh /system/bin/sheng-avb-ui";
 const auto at=actual.find(prefix);
 if(at!=string::npos)actual.replace(at,prefix.size(),wrapper_command);
 return popen(actual.c_str(),mode);
}
#define popen mapped_popen
#define LOGINFO(...) ((void)0)
#define LOGERR(...) fprintf(stderr,__VA_ARGS__)
#define TW_ACTION_BUSY "tw_action_busy"
struct GUIAction {
 bool simulate=false;
 void operation_start(const char*) {}
 void operation_end(int) {}
 void simulate_progress_bar() {}
 void page(const char*) {}
 int terminalcommand(string arg);
};
'''+native+r'''
int main(int argc,char** argv) {
 if(argc!=5)return 2;
 location=argv[1];gui_output=fopen(argv[3],"w");wrapper_command=argv[4];
 if(!gui_output)return 2;
 GUIAction action;int result=action.terminalcommand(argv[2]);
 fclose(gui_output);return result;
}
'''
checks = {}
ui_path = args.root/'twres/ui.xml' if args.root else tree/'generated/twrp/ui.xml'
ui = ET.parse(ui_path).getroot()
done = ui.find("pages/page[@name='sheng_avb_action']/action/condition[@var1='tw_operation_state']/../actions")
checks['real_result_read_before_shared_completion_page'] = [
    (item.get('function'), item.text) for item in done] == [
    ('set','tw_operation_status=%property.sys.sheng.avb.result%'), ('page','action_complete')]
wrapper_path = args.root/'system/bin/sheng-avb-ui' if args.root else tree/'scripts/sheng-avb-ui.sh'
if args.root:
    checks['packaged_wrapper_matches_source'] = wrapper_path.read_bytes() == (tree/'scripts/sheng-avb-ui.sh').read_bytes()
messages = json.loads((tree/'tools/device-avb-messages.json').read_text())['zh_CN']
with tempfile.TemporaryDirectory(prefix='sheng-avb-gui-') as folder:
    temp = Path(folder)
    (temp/'terminal.cpp').write_text(harness)
    (temp/'console.cpp').write_text('''#include <cstdio>
#include <cstdarg>
extern FILE* gui_output;
extern "C" void gui_print(const char* format,...) {
 va_list args; va_start(args,format); vfprintf(gui_output,format,args); va_end(args);
}
''')
    subprocess.run(['g++','-std=c++17','-DSHENG_UI_HOST_TEST',str(temp/'terminal.cpp'),
                    str(temp/'console.cpp'),str(tree/'twrp-ui/console_filter.cpp'),
                    '-Wl,--wrap=gui_print','-o',str(temp/'terminal')],check=True)
    subprocess.run(['g++','-std=c++17','-DSHENG_AVB_HOST_TEST',str(tree/'src/sheng_avb.cpp'),'-o',str(temp/'avb')],check=True)
    devices = temp/'devices'
    devices.mkdir()
    names = ('vbmeta_a','vbmeta_system_a','vbmeta_b','vbmeta_system_b')
    for name in names:
        data = bytearray(4096)
        data[:4] = b'AVB0'
        (devices/name).write_bytes(data)
    wrapper = wrapper_path.read_text().replace('/system/bin/sheng-avb --disable',
              shlex.quote(str(temp/'avb'))+' --disable --device-dir '+shlex.quote(str(devices)))
    (temp/'wrapper.sh').write_text(wrapper)
    (temp/'setprop').write_text('#!/bin/sh\nprintf "%s" "$2" > "$MOCK_RESULT_FILE"\n')
    (temp/'setprop').chmod(0o755)
    result_file = temp/'result'
    environment = {**os.environ,'PATH':str(temp)+':'+os.environ['PATH'], 'MOCK_RESULT_FILE':str(result_file)}
    samples = {}
    for case in ('success','partial_failure','missing_tool'):
        if case == 'partial_failure':
            (devices/names[1]).write_bytes(b'NOPE')
        if case == 'missing_tool':
            (temp/'avb').rename(temp/'avb-hidden')
        result_file.write_text('0')  # A stale success must not leak into failure.
        gui_file=temp/'gui-output'
        result = subprocess.run([str(temp/'terminal'),'/',
                 '/system/bin/sh /system/bin/sheng-avb-ui zh_CN',str(gui_file),
                 'bash '+shlex.quote(str(temp/'wrapper.sh'))],env=environment,capture_output=True,text=True,timeout=10)
        visible=gui_file.read_text()
        checks[case+'_native_action_completed'] = result.returncode == 0
        checks[case+'_real_result_preserved'] = result_file.read_text() == ('0' if case == 'success' else '1')
        checks[case+'_no_avb_command_echo_in_gui'] = ' # ' not in visible and 'sheng-avb-ui zh_CN' not in visible
        checks[case+'_command_retained_in_diagnostic_log'] = '/ # /system/bin/sh /system/bin/sheng-avb-ui zh_CN' in result.stdout
        if case != 'missing_tool':
            lines = visible.splitlines()
            checks[case+'_start_and_summary_visible'] = messages[0] in lines and messages[3 if case=='success' else 4] in lines
            checks[case+'_exactly_six_gui_lines'] = len(lines)==6 and lines[0]==messages[0]
            checks[case+'_all_partition_results_visible'] = all(
                messages[2 if case=='partial_failure' and name==names[1] else 1].replace('{1}',name) in lines for name in names)
            samples[case] = lines
        else:
            checks['missing_tool_error_visible'] = 'No such file or directory' in visible
    ordinary="printf 'ordinary terminal output\\n'"
    result=subprocess.run([str(temp/'terminal'),'/',ordinary,str(gui_file),'unused'],
                          env=environment,capture_output=True,text=True,timeout=10)
    checks['ordinary_terminal_echo_and_output_preserved'] = gui_file.read_text()==('/ # '+ordinary+'\nordinary terminal output\n')
report = {'checks':checks,'passed':all(checks.values()),'real_twrp_terminal_action':True,
          'physical_partition_writes':False,'device_gui_tested':False,'samples':samples}
args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
assert report['passed'],checks
