#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
if [[ -f bootable/recovery/orangefox.mk ]]; then
    export FOX_BUILD_DEVICE=sheng
    export FOX_BUILD_TYPE=Unofficial
    export FOX_VARIANT=peiyuesheng_sheng
    export OF_USE_LZ4_COMPRESSION=0
    export OF_USE_ZSTD_COMPRESSION=0
    export FOX_AB_DEVICE=1
    export FOX_VIRTUAL_AB_DEVICE=1
    export FOX_RECOVERY_INSTALL_PARTITION=recovery
    export OF_MAINTAINER=peiyuesheng
    export FOX_DELETE_MAGISK_ADDON=0
    export FOX_MOVE_MAGISK_INSTALLER_TO_RAMDISK=1
    export FOX_USE_SPECIFIC_MAGISK_ZIP="$PWD/device/xiaomi/sheng/assets/Magisk-v30.7-sheng-recovery.zip"
    export OF_DONT_PATCH_ENCRYPTED_DEVICE=1
fi
