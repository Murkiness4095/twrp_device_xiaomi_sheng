# SPDX-License-Identifier: GPL-3.0-or-later
LOCAL_PATH := $(call my-dir)
ifeq ($(SHENG_RECOVERY_FLAVOR),twrp)
include $(CLEAR_VARS)
LOCAL_MODULE := libsheng_twrp_ui
LOCAL_SRC_FILES := console_filter.cpp
LOCAL_C_INCLUDES := \
    bootable/recovery \
    bootable/recovery/twrpinstall/include \
    system/libbase/include \
    system/libziparchive/include
LOCAL_CFLAGS := -Wall -Wextra -Werror
LOCAL_MULTILIB := 64
LOCAL_NOTICE_FILE := $(LOCAL_PATH)/../src/ORANGEFOX-NOTICE
include $(BUILD_STATIC_LIBRARY)

# The recovery module has already been declared by bootable/recovery/Android.mk.
# Wrap only its GUI printing; no global linker flags or frontend source edits.
sheng_twrp_linked := $(call intermediates-dir-for,EXECUTABLES,recovery)/LINKED/recovery
$(sheng_twrp_linked): PRIVATE_LDFLAGS += -Wl,--wrap=gui_print
endif
