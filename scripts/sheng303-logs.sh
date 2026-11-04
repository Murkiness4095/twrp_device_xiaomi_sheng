#!/system/bin/sh
# SPDX-License-Identifier: Apache-2.0
dest=${1:-/tmp/sheng303-diagnostics}
mkdir -p "$dest" || exit 1
cp /tmp/recovery.log "$dest/" 2>/dev/null
cp -R /tmp/sheng303 "$dest/hardware" 2>/dev/null
dmesg > "$dest/dmesg.txt"
getprop > "$dest/properties.txt"
cat /proc/modules > "$dest/modules.txt"
cat /proc/bus/input/devices > "$dest/input-devices.txt"
cat /proc/mounts > "$dest/mounts.txt"
cat /sys/class/drm/card0-DSI-1/modes > "$dest/display-modes.txt"
echo "$dest"
