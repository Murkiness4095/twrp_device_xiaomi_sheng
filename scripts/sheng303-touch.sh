#!/system/bin/sh
# SPDX-License-Identifier: Apache-2.0
mkdir -p /tmp/sheng303
exec >> /tmp/sheng303/touch.log 2>&1
i=0
while [ ! -c /dev/xiaomi-touch ] && [ "$i" -lt 100 ]; do
    sleep 0.1
    i=$((i+1))
done
[ -c /dev/xiaomi-touch ] || { echo "No /dev/xiaomi-touch after 10 seconds"; exit 1; }
exec /system/bin/sh /system/bin/sheng303-run /odm/bin/touch_report_debug
