#!/system/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Isolate the matching stock 303 linker/libc/vendor library closure from the UI.
if [ "$1" = /vendor/bin/hw/android.hardware.security.keymint-service-qti ]; then
    # The AIDL service shares the recovery's Binder runtime and service manager.
    # A private VNDK binder stack selects vndbinder or mismatches its framework.
    export LD_LIBRARY_PATH=/system/lib64:/vendor/lib64/sheng303-runtime
    exec /system/bin/linker64 "$@"
fi
export LD_LIBRARY_PATH=/vendor/lib64/sheng303-runtime
if [ "$1" = /vendor/bin/qseecomd ]; then
    i=0
    while [ ! -r /firmware/image/adsp.mdt ] && [ "$i" -lt 100 ]; do
        sleep 0.1
        i=$((i+1))
    done
    [ -r /firmware/image/adsp.mdt ] || exit 1
    # Stock QSEE libraries still open /vendor/firmware_mnt/image. Keep the
    # modem mounted outside /vendor and expose its legacy path just before
    # starting the listeners, after recovery has restored the ramdisk vendor.
    if [ ! -e /vendor/firmware_mnt ] && [ ! -L /vendor/firmware_mnt ]; then
        ln -s /firmware /vendor/firmware_mnt || exit 1
    fi
    [ -r /vendor/firmware_mnt/image/adsp.mdt ] || exit 1
fi
exec /vendor/bin/sheng303-linker64 "$@"
