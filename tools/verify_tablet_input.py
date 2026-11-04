#!/usr/bin/env python3
"""Compile real scaling/filter expressions and check the tablet's four corners."""
import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--source',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
text=a.source.read_text()
scaling=text[text.index('static int vk_tp_to_screen('):text.index('/* Translate a virtual key')]
start=text.index('#ifdef RECOVERY_TOUCHSCREEN_SWAP_XY',text.index('static int vk_modify('))
transform=text[start:text.index('#ifdef _EVENT_LOGGING',start)]
condition=re.search(r'if \((strcmp\(e->deviceName, blacklist\).*?)\) \{',text,re.S).group(1)
code=r'''
#include <cstring>
#include <cstdio>
#include <linux/input.h>
#define RECOVERY_TOUCHSCREEN_SWAP_XY
#define RECOVERY_TOUCHSCREEN_FLIP_Y
struct position { int x,y,synced; input_absinfo xi,yi; };
int gr_fb_width() { return 3048; }
int gr_fb_height() { return 2032; }
'''+scaling+r'''
bool filter(const char* name) {
 struct Event { char deviceName[64]; } event;
 auto* e=&event; strcpy(e->deviceName,name);
 const char* blacklist="NVTCapacitivePen";
 return '''+condition+r''';
}
bool corner(int rx,int ry,int expected_x,int expected_y) {
 position p={}; p.x=rx; p.y=ry; p.xi.maximum=20319; p.yi.maximum=30479;
 int x,y; vk_tp_to_screen(&p,&x,&y);
'''+transform+r'''
 return x==expected_x && y==expected_y && x>=0 && x<3048 && y>=0 && y<2032;
}
int main() {
 bool corners=corner(0,0,0,2031) && corner(20319,0,0,0) &&
              corner(0,30479,3047,2031) && corner(20319,30479,3047,0);
 bool pen=filter("NVTCapacitivePenM80p") && filter("NVTCapacitivePenP81c") && filter("NVTCapacitivePen");
 bool preserve=!filter("NVTCapacitiveTouchScreen") && !filter("gpio-keys");
 printf("{\"landscape_corners_in_bounds\":%s,\"actual_pen_names_filtered\":%s,\"touchscreen_and_keys_preserved\":%s}\n",corners?"true":"false",pen?"true":"false",preserve?"true":"false");
 return corners && pen && preserve ? 0 : 1;
}
'''
with tempfile.TemporaryDirectory(prefix='sheng-tablet-input-') as tmp:
    src,exe=Path(tmp)/'test.cpp',Path(tmp)/'test'
    src.write_text(code)
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-unused-function',src,'-o',exe],check=True)
    checks=json.loads(subprocess.check_output([exe]))
report={'source':str(a.source),'checks':checks,'passed':all(checks.values()),'hardware_verified':False}
a.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
