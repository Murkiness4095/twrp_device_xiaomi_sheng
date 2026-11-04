#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -eo pipefail
source_root="${1:-$PWD}"
tree_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$source_root"
if [[ ! -f build/envsetup.sh ]]; then
    echo "Pass an initialized Android 12.1 recovery checkout" >&2
    exit 1
fi
if [[ -f bootable/recovery/orangefox.mk ]]; then
    flavor=orangefox
    unset NOT_ORANGEFOX
else
    flavor=twrp
    export NOT_ORANGEFOX=1
fi
export SHENG_RECOVERY_FLAVOR="$flavor"
export BUILD_USERNAME=peiyuesheng
export BUILD_NUMBER="${SHENG_BUILD_NUMBER:-eng.peiyuesheng.sheng.20261103}"
export OUT_DIR="${OUT_DIR:-out-sheng-standalone-$flavor}"
export ALLOW_MISSING_DEPENDENCIES=true
unset FOX_MAINTAINER_PATCH_VERSION
python3 "$tree_root/tools/apply-platform-fixes.py" --source "$PWD"
python3 "$tree_root/tools/prepare-device-tools.py" --source "$PWD"
set +e
source build/envsetup.sh
set -e
lunch twrp_sheng-eng
mka -j"${JOBS:-8}" recoveryimage
