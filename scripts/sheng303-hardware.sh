#!/system/bin/sh
# SPDX-License-Identifier: Apache-2.0
mkdir -p /tmp/sheng303
exec >> /tmp/sheng303/hardware.log 2>&1
echo "Stock 303 hardware startup: $(date)"
# First-stage init normally loaded these modules already. Cache the kernel's
# names once instead of forking tr and grep for every one of the 338 entries.
loaded_modules=" "
while read -r loaded_name rest; do
    loaded_modules="$loaded_modules$loaded_name "
done < /proc/modules
while read -r module; do
    [ -n "$module" ] || continue
    name=${module%.ko}
    name=${name//-/_}
    case "$loaded_modules" in *" $name "*) continue ;; esac
    if ! insmod "/lib/modules/$module"; then
        echo "module load failed: $module"
    else
        loaded_modules="$loaded_modules$name "
    fi
done < /vendor/etc/sheng303/modules.order
slot=$(getprop ro.boot.slot_suffix)
case "$slot" in _a|_b) ;; *) echo "No valid slot suffix; firmware mount skipped"; exit 1 ;; esac
mkdir -p /firmware
mount -t vfat -o ro "/dev/block/by-name/modem$slot" /firmware || exit 1
# Recovery mounts and unmounts /vendor while enumerating partitions. Firmware
# requests must keep a stable path across that work, including split segments.
echo /firmware/image > /sys/module/firmware_class/parameters/path || exit 1
for firmware in /firmware/image/adsp.mdt /firmware/image/adsp_dtb.mdt /firmware/image/adsp.b01; do
    [ -r "$firmware" ] || { echo "ADSP firmware missing: $firmware"; exit 1; }
done
echo "Firmware mounted read-only for $slot"
# This kernel exposes ADSP through remoteproc, not the older boot_adsp node.
# Its PMIC GLINK services provide battery status, Type-C negotiation and OTG.
for remote in /sys/class/remoteproc/remoteproc*; do
    case "$(cat "$remote/name" 2>/dev/null)" in
        *remoteproc-adsp*)
            state=$(cat "$remote/state")
            # The stock driver can leave a GLINK device registered after a
            # partial boot failure; retrying then fails with EEXIST. Start once
            # only, after exposing all firmware through the stable root mount.
            if [ "$state" = offline ]; then
                echo start > "$remote/state" || echo "ADSP start failed; not retrying partial driver state"
            fi
            echo "ADSP state: $(cat "$remote/state")"
            ;;
    esac
done
# Health scans power_supply during initialization. Let ADSP publish the battery
# first, then start the existing recovery Health HAL through init. Fastbootd
# waits for this HAL before it can open its USB endpoints.
battery_wait=0
while [ ! -r /sys/class/power_supply/battery/capacity ] && [ "$battery_wait" -lt 100 ]; do
    sleep 0.1
    battery_wait=$((battery_wait + 1))
done
if [ ! -r /sys/class/power_supply/battery/capacity ]; then
    echo "Battery node unavailable; hardware is not ready, leaving Health HAL stopped"
    exit 1
fi
setprop sys.sheng303.hardware.ready 1
echo "Hardware ready at uptime $(cat /proc/uptime)"
