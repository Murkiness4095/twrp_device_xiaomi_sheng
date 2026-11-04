# SPDX-License-Identifier: Apache-2.0
# Only OrangeFox reads these; the common hardware files also work with TWRP.
OF_SCREEN_H := 3048
OF_STATUS_H := 80
OF_STATUS_INDENT_LEFT := 24
OF_STATUS_INDENT_RIGHT := 24
OF_CLOCK_POS := 1
OF_ALLOW_DISABLE_NAVBAR := 0
OF_USE_LEGACY_BATTERY_SERVICES := 1
OF_MAINTAINER := peiyuesheng
FOX_DELETE_MAGISK_ADDON := 0
FOX_MOVE_MAGISK_INSTALLER_TO_RAMDISK := 1
FOX_USE_SPECIFIC_MAGISK_ZIP := $(DEVICE_PATH)/assets/Magisk-v30.7-sheng-recovery.zip
FOX_AB_DEVICE := 1
FOX_VIRTUAL_AB_DEVICE := 1
FOX_RECOVERY_INSTALL_PARTITION := recovery
FOX_RECOVERY_VENDOR_BOOT_PARTITION := /dev/block/bootdevice/by-name/vendor_boot
FOX_BUILD_TYPE := Unofficial
OF_DONT_PATCH_ENCRYPTED_DEVICE := 1
OF_SKIP_FBE_DECRYPTION := 0
# Show OrangeFox's own vbmeta/vbmeta_system option in its original locations.
# The runtime option remains opt-in (upstream default is off).
OF_SUPPORT_VBMETA_AVB2_PATCHING := 1
