#!/usr/bin/env python3
"""Run the actual frontend input loop under a deterministic clock/backlog."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    text = (a.source/'gui/gui.cpp').read_text()
    loop = text[text.index('static void loopTimer(int input_timeout_ms)'):
                text.index('static int runPages(')]
    harness = r'''
#include <cstdio>
#include <ctime>
#include <cstring>
#define TW_FRAMERATE 120
static long long tick=0;
static int frames=0;
static bool busy=true;
static int pending=-1, consumed=0;
int test_clock(int, timespec *out) {
    out->tv_sec=tick/1000000000; out->tv_nsec=tick%1000000000; return 0;
}
#define clock_gettime test_clock
struct Handler {
    bool processInput(int timeout) {
        tick+=100000+timeout*1000000LL;
        if (!busy || pending==0) return false;
        if (pending>0) --pending;
        ++consumed; return true;
    }
    void handleDrag() { ++frames; }
} input_handler;
namespace TWFunc {
timespec timespec_diff(timespec a, timespec b) {
    timespec d={b.tv_sec-a.tv_sec,b.tv_nsec-a.tv_nsec};
    if (d.tv_nsec<0) { --d.tv_sec; d.tv_nsec+=1000000000; } return d;
}}
'''
    main_code = r'''
int main(int argc, char **argv) {
    const bool backlog=argc>1 && strcmp(argv[1],"backlog")==0;
    busy=argc==1 || backlog;
    loopTimer(0);
    if (backlog) {
        pending=40;
        tick+=50000000; // Previous 50ms render must not starve new input.
        const auto start=tick;
        loopTimer(0);
        printf("{\"processed\":%d,\"remaining\":%d,\"input_ms\":%.3f}\n",
               consumed,pending,(tick-start)/1000000.0);
        return 0;
    }
    long long maximum=0;
    for (int i=0;i<20;++i) {
        auto start=tick; loopTimer(busy?0:9);
        if (tick-start>maximum) maximum=tick-start;
    }
    printf("{\"frames\":%d,\"max_ms\":%.3f}\n",frames,maximum/1000000.0);
}
'''
    with tempfile.TemporaryDirectory(prefix='sheng303-budget-') as tmp:
        src, exe = Path(tmp)/'test.cpp', Path(tmp)/'test'
        src.write_text(harness+loop+main_code)
        subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(src),'-o',str(exe)],check=True)
        active = json.loads(subprocess.check_output([str(exe)]))
        idle = json.loads(subprocess.check_output([str(exe),'idle']))
        backlog = json.loads(subprocess.check_output([str(exe),'backlog']))
    passed = (active['frames']==20 and 8.3<=active['max_ms']<=8.5 and
              idle['frames']==20 and idle['max_ms']<=9.2 and
              backlog['processed']==40 and backlog['remaining']==0 and backlog['input_ms']<=8.5)
    if 'input_timeout_ms = idle_frames > 15 ? (1000 + TW_FRAMERATE - 1) / TW_FRAMERATE : 0;' not in text:
        passed=False
    report={'source':str(a.source),'configured_fps':120,'continuous_input':active,
            'no_input':idle,'after_50ms_render':backlog,'passed':passed,'hardware_fps_measured':False}
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
