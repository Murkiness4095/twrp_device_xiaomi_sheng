# SPDX-License-Identifier: Apache-2.0
# Fresh device configuration for the user-provided official 303 package.
DEVICE_PATH := device/xiaomi/sheng
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/base.mk)
$(call inherit-product, vendor/twrp/config/common.mk)
$(call inherit-product, $(DEVICE_PATH)/device.mk)

PRODUCT_DEVICE := sheng
PRODUCT_NAME := twrp_sheng
PRODUCT_BRAND := Xiaomi
PRODUCT_MANUFACTURER := Xiaomi
PRODUCT_MODEL := 24018RPACC
PRODUCT_RELEASE_NAME := sheng
TARGET_OTA_ASSERT_DEVICE := sheng
PRODUCT_LOCALES := zh_CN en_US
