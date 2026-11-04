# SPDX-License-Identifier: Apache-2.0
DEVICE_PATH := device/xiaomi/sheng
SHENG_RECOVERY_FLAVOR ?= $(if $(wildcard bootable/recovery/orangefox.mk),orangefox,twrp)
PRODUCT_USE_DYNAMIC_PARTITIONS := true
PRODUCT_VIRTUAL_AB_OTA := true
PRODUCT_PACKAGES += libhidlbase.recovery
PRODUCT_SOONG_NAMESPACES += $(DEVICE_PATH)
PRODUCT_PACKAGES += bootctrl.kalama.recovery android.hardware.boot@1.2-impl-qti.recovery
AB_OTA_UPDATER := true
AB_OTA_PARTITIONS := boot init_boot vendor_boot recovery dtbo vbmeta vbmeta_system \
    system system_ext system_dlkm vendor vendor_dlkm odm product mi_ext

include $(DEVICE_PATH)/proprietary.mk
SHENG303_RAW_COPY_FILES := $(call find-copy-subdir-files,*,$(DEVICE_PATH)/recovery/root,recovery/root)
SHENG303_ELF_COPY_FILES := $(foreach path,$(SHENG303_ELF_RELATIVE_FILES),$(DEVICE_PATH)/recovery/root/$(path):recovery/root/$(path))
PRODUCT_COPY_FILES += $(filter-out $(SHENG303_ELF_COPY_FILES),$(SHENG303_RAW_COPY_FILES))
PRODUCT_COPY_FILES += \
    $(DEVICE_PATH)/assets/Magisk-v30.7-sheng-recovery.zip:recovery/root/FFiles/OF_Magisk/Magisk.zip \
    $(DEVICE_PATH)/scripts/sheng303-hardware.sh:recovery/root/system/bin/sheng303-hardware \
    $(DEVICE_PATH)/scripts/sheng303-touch.sh:recovery/root/system/bin/sheng303-touch \
    $(DEVICE_PATH)/scripts/sheng303-run.sh:recovery/root/system/bin/sheng303-run \
    $(DEVICE_PATH)/scripts/sheng303-logs.sh:recovery/root/system/bin/sheng303-logs

ifeq ($(wildcard device/qcom/twrp-common/crypto/system/bin/prepdecrypt.sh),)
$(error The upstream device/qcom/twrp-common prepdecrypt helper is required)
endif
PRODUCT_COPY_FILES += device/qcom/twrp-common/crypto/system/bin/prepdecrypt.sh:recovery/root/system/bin/prepdecrypt.sh

PRODUCT_PACKAGES += snapuserd.recovery
PRODUCT_COPY_FILES += \
    $(call find-copy-subdir-files,*,$(DEVICE_PATH)/generated/$(SHENG_RECOVERY_FLAVOR)/languages,recovery/root/system/etc/sheng-device-languages) \
    $(DEVICE_PATH)/generated/$(SHENG_RECOVERY_FLAVOR)/init.recovery.sheng-tools.rc:recovery/root/init.recovery.sheng-tools.rc
ifeq ($(SHENG_RECOVERY_FLAVOR),twrp)
PRODUCT_PACKAGES += sheng-avb
TARGET_RECOVERY_DEVICE_MODULES += sheng-avb
RECOVERY_BINARY_SOURCE_FILES += $(TARGET_RECOVERY_ROOT_OUT)/system/bin/sheng-avb
endif
TARGET_RECOVERY_DEVICE_MODULES += snapuserd.recovery
RECOVERY_BINARY_SOURCE_FILES += $(TARGET_RECOVERY_ROOT_OUT)/system/bin/snapuserd
ifneq ($(wildcard external/sheng-p7zip/Android.bp),)
PRODUCT_PACKAGES += sheng_7za
TARGET_RECOVERY_DEVICE_MODULES += sheng_7za
RECOVERY_BINARY_SOURCE_FILES += $(TARGET_RECOVERY_ROOT_OUT)/system/bin/7za
endif
DEVICE_MANIFEST_FILE := $(DEVICE_PATH)/manifest.xml
