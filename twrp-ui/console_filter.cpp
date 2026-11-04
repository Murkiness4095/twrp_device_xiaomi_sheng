// SPDX-License-Identifier: GPL-3.0-or-later
#include <cstdarg>
#include <cstdio>
#include <cstring>

#ifndef SHENG_UI_HOST_TEST
// Preserve the default TeamWin partition factory behind its device-library hook.
#include "BasePartition.cpp"
#endif

extern "C" void __real_gui_print(const char* format, ...);

extern "C" void __wrap_gui_print(const char* format, ...) {
    va_list args;
    va_start(args, format);
    bool avb_echo = false;
    if (strcmp(format, "%s # %s\n") == 0) {
        va_list probe;
        va_copy(probe, args);
        const char* location = va_arg(probe, const char*);
        const char* command = va_arg(probe, const char*);
        constexpr char prefix[] = "/system/bin/sh /system/bin/sheng-avb-ui ";
        avb_echo = location && command && strcmp(location, "/") == 0
                && strncmp(command, prefix, sizeof(prefix) - 1) == 0;
        va_end(probe);
    }
    if (avb_echo) {
        // Retain the diagnostic command in recovery.log, outside the GUI console.
        vfprintf(stdout, format, args);
    } else {
        // Match the upstream gui_print buffer size and formatting behavior.
        char buffer[512];
        vsnprintf(buffer, sizeof(buffer), format, args);
        __real_gui_print("%s", buffer);
    }
    va_end(args);
}
