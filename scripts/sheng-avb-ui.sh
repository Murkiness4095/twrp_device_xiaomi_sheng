#!/system/bin/sh
# SPDX-License-Identifier: Apache-2.0
# The stock terminal action streams output, but does not retain child status.
# Publish it before EOF so the device-local completion page can read it.
exec 2>&1
setprop sys.sheng.avb.result 1 || exit 1
/system/bin/sheng-avb --disable --language "$1"
result=$?
if [ "$result" -eq 0 ]; then
    setprop sys.sheng.avb.result 0 || exit 1
fi
exit "$result"
