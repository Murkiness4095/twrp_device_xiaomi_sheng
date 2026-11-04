// SPDX-License-Identifier: GPL-3.0-or-later
/*
 * Copyright 2014 to 2021 TeamWin
 * Copyright (C) 2018-2026 OrangeFox Recovery Project
 *
 * Ported from partitionmanager.cpp, commit
 * 6bd902d14f754ab98a7cccc5598f7b9d135cfc38 (fox_12.1).
 * This program is free software under GNU GPL version 3 or later.
 * See ORANGEFOX-NOTICE for the original notice and full license.
 *
 * Only the recovery GUI dependencies are replaced with standalone stdio/CLI
 * glue. Partition selection, AVB0 check, byte offset, flag value, per-target
 * writes and all-four-result aggregation follow the upstream A/B implementation.
 */
#include <cstdio>
#include <cstring>
#include <string>
#include <unistd.h>
using std::string;

#define AVB_MAGIC "AVB0"
#define AVB_MAGIC_LEN 4
#define AVB_VBMETA_FLAGS_OFFSET 123
// AOSP libavb: AVB_VBMETA_IMAGE_FLAGS_VERIFICATION_DISABLED = (1 << 1).
static constexpr char AVB_VBMETA_IMAGE_FLAGS_VERIFICATION_DISABLED = 2;
#ifdef SHENG_AVB_HOST_TEST
static string test_directory;
#endif
static string block_directory() {
#ifdef SHENG_AVB_HOST_TEST
    return test_directory + "/";
#else
    string dev = "/dev/block/bootdevice/by-name/";
    if (access(dev.c_str(), F_OK) != 0) dev = "/dev/block/by-name/";
    return dev;
#endif
}

static bool Do_Disable_AVB2(string File_Name, char Disable_Flags, bool Display_Info) {
    char AVB_MAGIC_BUF[AVB_MAGIC_LEN + 1] = {0}, flags_buf[1] = {0};
    int _ret;
    bool ret = false;
    string dev = block_directory();
    FILE* vbmetaFile = fopen((dev + File_Name).c_str(), "rb+");
    if (vbmetaFile != NULL) {
        fread(&AVB_MAGIC_BUF, AVB_MAGIC_LEN, 1, vbmetaFile);
        if (strncmp(AVB_MAGIC, AVB_MAGIC_BUF, AVB_MAGIC_LEN) != 0) goto exit;
        fseek(vbmetaFile, AVB_VBMETA_FLAGS_OFFSET, SEEK_SET);
        _ret = fread(&flags_buf, 1, 1, vbmetaFile);
        if (!_ret) goto exit;
        if (flags_buf[0] != Disable_Flags) {
            fseek(vbmetaFile, AVB_VBMETA_FLAGS_OFFSET, SEEK_SET);
            _ret = fwrite(&Disable_Flags, 1, 1, vbmetaFile);
            if (!_ret) goto exit;
        }
        ret = true;
    }
exit:
    if (vbmetaFile) {
        fclose(vbmetaFile);
        vbmetaFile = nullptr;
    }
    if (Display_Info)
        fprintf(ret ? stdout : stderr, "Disable vbmeta AVB2.0: %s: %s\n",
                File_Name.c_str(), ret ? "success" : "failed");
    return ret;
}

static bool Disable_AVB2(bool Display_Info) {
    char disable_flags = AVB_VBMETA_IMAGE_FLAGS_VERIFICATION_DISABLED;
    return Do_Disable_AVB2("vbmeta_a", disable_flags, Display_Info)
         & Do_Disable_AVB2("vbmeta_system_a", disable_flags, Display_Info)
         & Do_Disable_AVB2("vbmeta_b", disable_flags, Display_Info)
         & Do_Disable_AVB2("vbmeta_system_b", disable_flags, Display_Info);
}

int main(int argc, char** argv) {
#ifdef SHENG_AVB_HOST_TEST
    if (argc != 4 || strcmp(argv[1], "--disable") || strcmp(argv[2], "--device-dir")) return 2;
    test_directory = argv[3];
#else
    if (argc != 2 || strcmp(argv[1], "--disable")) {
        fprintf(stderr, "usage: sheng-avb --disable\n");
        return 2;
    }
#endif
    return Disable_AVB2(true) ? 0 : 1;
}
