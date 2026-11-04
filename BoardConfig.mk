# SPDX-License-Identifier: Apache-2.0
# Device configuration written from the official OS3.0.303.0.WNXCNXM images.
DEVICE_PATH := device/xiaomi/sheng
ALLOW_MISSING_DEPENDENCIES := true
# config.mk derives PRODUCT_ENFORCE_VINTF_MANIFEST from this override. Setting
# the derived variable directly is overwritten for a recovery-only product.
# This removes libhidl's unconditional one-second legacy lookup delay without
# changing the framework source or turning on unrelated Treble requirements.
PRODUCT_ENFORCE_VINTF_MANIFEST_OVERRIDE := true

TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv8-2a
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_VARIANT := generic
TARGET_CPU_VARIANT_RUNTIME := generic
TARGET_USES_64_BIT_BINDER := true
TARGET_BOARD_PLATFORM := kalama
TARGET_BOOTLOADER_BOARD_NAME := kalama
TARGET_BOARD_PLATFORM_GPU := qcom-adreno740
BOARD_VENDOR := xiaomi
BOARD_USES_QCOM_HARDWARE := true
TARGET_NO_BOOTLOADER := true
TARGET_NO_RADIOIMAGE := true

# Standalone recovery. The v2 load-address layout follows map220v's sheng
# implementation (Apache-2.0, AOSP 2023). Kernel/DTB/modules are imported together
# from official images; the installed boot/vendor_boot are not used as payloads.
BOARD_BOOT_HEADER_VERSION := 2
BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE := false
BOARD_USES_RECOVERY_AS_BOOT := false
BOARD_MOVE_RECOVERY_RESOURCES_TO_VENDOR_BOOT := false
TARGET_PREBUILT_KERNEL := $(DEVICE_PATH)/prebuilt/stock303/Image.gz
TARGET_PREBUILT_DTB := $(DEVICE_PATH)/prebuilt/stock303/dtb
BOARD_PREBUILT_DTBOIMAGE := $(DEVICE_PATH)/prebuilt/stock303/dtbo.img
BOARD_INCLUDE_RECOVERY_DTBO := true
TARGET_KERNEL_ARCH := arm64
BOARD_KERNEL_IMAGE_NAME := Image
BOARD_KERNEL_PAGESIZE := 4096
BOARD_KERNEL_BASE := 0x00000000
BOARD_KERNEL_OFFSET := 0x00008000
BOARD_RAMDISK_OFFSET := 0x02000000
BOARD_KERNEL_SECOND_OFFSET := 0x00000000
BOARD_KERNEL_TAGS_OFFSET := 0x01e00000
BOARD_DTB_OFFSET := 0x01f00000
BOARD_KERNEL_CMDLINE := video=vfb:640x400,bpp=32,memsize=3072000 disable_dma32=on printk.devkmsg=on firmware_class.path=/vendor/firmware_mnt/image bootconfig androidboot.hardware=qcom androidboot.memcg=1 androidboot.usbcontroller=a600000.dwc3 loop.max_part=7 androidboot.load_modules_parallel=false mtdoops.mtddev=0 androidboot.selinux=permissive twrpfastboot=1
BOARD_MKBOOTIMG_ARGS := --header_version 2 --pagesize 4096
BOARD_MKBOOTIMG_ARGS += --kernel_offset $(BOARD_KERNEL_OFFSET) --ramdisk_offset $(BOARD_RAMDISK_OFFSET)
BOARD_MKBOOTIMG_ARGS += --tags_offset $(BOARD_KERNEL_TAGS_OFFSET) --second_offset $(BOARD_KERNEL_SECOND_OFFSET)
BOARD_MKBOOTIMG_ARGS += --dtb $(TARGET_PREBUILT_DTB) --dtb_offset $(BOARD_DTB_OFFSET)
BOARD_RAMDISK_USE_LZ4 := false
BOARD_RAMDISK_USE_ZSTD := true

BOARD_FLASH_BLOCK_SIZE := 262144
BOARD_BOOTIMAGE_PARTITION_SIZE := 100663296
BOARD_VENDOR_BOOTIMAGE_PARTITION_SIZE := 100663296
BOARD_RECOVERYIMAGE_PARTITION_SIZE := 104857600
BOARD_SUPER_PARTITION_SIZE := 11811160064
BOARD_SUPER_PARTITION_GROUPS := qti_dynamic_partitions
BOARD_QTI_DYNAMIC_PARTITIONS_SIZE := 11800674304
# Android 12's image-builder knows these names. Runtime fstab includes the other
# real 303 logical partitions too; recovery does not rebuild a super image.
BOARD_QTI_DYNAMIC_PARTITIONS_PARTITION_LIST := system system_ext vendor vendor_dlkm odm product
BOARD_USES_VENDOR_DLKMIMAGE := true
BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE := ext4
TARGET_COPY_OUT_VENDOR := vendor
TARGET_USERIMAGES_USE_EXT4 := true
TARGET_USERIMAGES_USE_F2FS := true
BOARD_USERDATAIMAGE_FILE_SYSTEM_TYPE := f2fs

BOARD_AVB_ENABLE := true
BOARD_AVB_RECOVERY_KEY_PATH := external/avb/test/data/testkey_rsa4096.pem
BOARD_AVB_RECOVERY_ALGORITHM := SHA256_RSA4096
BOARD_AVB_RECOVERY_ROLLBACK_INDEX := 1
BOARD_AVB_RECOVERY_ROLLBACK_INDEX_LOCATION := 1

TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/recovery.fstab
TARGET_RECOVERY_PIXEL_FORMAT := RGBX_8888
TARGET_SYSTEM_PROP += $(DEVICE_PATH)/system.prop
RECOVERY_SDCARD_ON_DATA := true
BOARD_HAS_LARGE_FILESYSTEM := true
TW_INCLUDE_CRYPTO := true
TW_INCLUDE_CRYPTO_FBE := true
TW_INCLUDE_FBE_METADATA_DECRYPT := true
BOARD_USES_METADATA_PARTITION := true
# Fresh init definitions use the upstream prepdecrypt helper without importing
# another device tree or its service definitions.
# Preserve the boot-header compatibility values used by the working r3.
# These are recovery compatibility fields, not the installed ROM's version.
PLATFORM_VERSION := 99.87.36
PLATFORM_SECURITY_PATCH := 2099-12-31
VENDOR_SECURITY_PATCH := $(PLATFORM_SECURITY_PATCH)
PLATFORM_VERSION_LAST_STABLE := $(PLATFORM_VERSION)

TW_THEME := portrait_hdpi
TW_ROTATION := 270
TW_FRAMERATE := 120
TW_DEFAULT_LANGUAGE := zh_CN
TW_MAX_BRIGHTNESS := 4095
TW_DEFAULT_BRIGHTNESS := 200
TW_BRIGHTNESS_PATH := /sys/class/backlight/panel0-backlight/brightness
TW_CUSTOM_BATTERY_PATH := /sys/class/power_supply/battery
TW_CUSTOM_CPU_TEMP_PATH := /sys/class/thermal/thermal_zone95/temp
TW_USE_LEGACY_BATTERY_SERVICES := true
TW_INPUT_BLACKLIST := "NVTCapacitivePen"
TW_NO_HAPTICS := true
TW_INCLUDE_REPACKTOOLS := true
TW_INCLUDE_RESETPROP := true
TW_INCLUDE_LIBRESETPROP := true
TW_INCLUDE_LPDUMP := true
TW_INCLUDE_LPTOOLS := true
TW_INCLUDE_FASTBOOTD := true
TW_EXCLUDE_APEX := true
TW_EXTRA_LANGUAGES := true
TW_USE_NEW_MINADBD := true
TW_EXCLUDE_DEFAULT_USB_INIT := true
TW_NO_LEGACY_PROPS := true
TW_SKIP_ADDITIONAL_FSTAB := true
TWRP_INCLUDE_LOGCAT := true
TARGET_USES_LOGD := true

SHENG_RECOVERY_FLAVOR ?= $(if $(wildcard bootable/recovery/orangefox.mk),orangefox,twrp)
ifeq ($(SHENG_RECOVERY_FLAVOR),orangefox)
TW_CUSTOM_THEME := $(DEVICE_PATH)/generated/orangefox/ui.xml
include $(DEVICE_PATH)/orangefox.mk
else ifeq ($(SHENG_RECOVERY_FLAVOR),twrp)
TW_DEVICE_VERSION := peiyuesheng_sheng
TARGET_RECOVERY_TWRP_LIB := libsheng_twrp_ui
# The panel's native DRM mode is 3048x2032. Use it directly for tablet UI;
# do not apply the portrait frontend's 270-degree rotation to TWRP.
TW_THEME := landscape_hdpi
TW_CUSTOM_THEME := $(DEVICE_PATH)/generated/twrp/ui.xml
TW_ROTATION := 0
RECOVERY_TOUCHSCREEN_SWAP_XY := true
RECOVERY_TOUCHSCREEN_FLIP_Y := true
else
$(error SHENG_RECOVERY_FLAVOR must be orangefox or twrp)
endif
