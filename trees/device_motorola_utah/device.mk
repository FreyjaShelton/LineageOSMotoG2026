#
# SPDX-License-Identifier: Apache-2.0
#

$(call inherit-product, device/motorola/nevada/device.mk)

# HIDL service manager and the HIDL ashmem allocator service (found 2026-11-17).
# Our vendor is Android 13 with HIDL HALs (composer, USB gadget, ...). They register through
# hwservicemanager. Stock's Android 16 system_ext ships it (/bin/hwservicemanager plus
# /etc/init/hwservicemanager.rc) and the allocator (/bin/hw/android.hidl.allocator@1.0-service,
# its rc and its VINTF fragment). The nevada tree's build had NEITHER: /system/bin/hwservicemanager
# was a dangling symlink, init logged "service hwservicemanager not found", and the phone sat at
# the Hello Moto logo with no USB device. Both are plain AOSP modules; the build generates the rc
# and the VINTF fragment. See BUILD_PLAN.md ("Boot log findings").
PRODUCT_PACKAGES += \
    hwservicemanager \
    android.hidl.allocator@1.0-service

# VENDOR = STOCK'S OWN IMAGE (2026-11-18). BoardConfig.mk sets BOARD_PREBUILT_VENDORIMAGE, so nothing
# installed into the vendor directory by the build ends up on the phone: the vendor partition is
# Motorola's, unchanged. History: the nevada tree rebuilt the vendor from a blob list plus HALs built from
# source; composer, thermal, audio, their libraries and their effects configuration were each an Android 13
# stock blob running against an Android 16 build of a same-named library, and every fix uncovered the next
# (BUILD_PLAN.md, "Flash day"). Patch 0004 (removes the source-built composer, thermal and audio packages
# from nevada's device.mk) is kept: it only affects what is compiled, not what is flashed.

# DEBUG ONLY: build with UTAH_DEBUG_PANIC=1 to add a logger that writes dmesg, logcat, ps and getprop into
# /metadata/dbg every 20 s (our recovery can read it after any restart). It lives in /system, not in the
# vendor, because the vendor image is prebuilt. See debug/zz-debug-log.rc and BUILD_PLAN.md.
ifeq ($(UTAH_DEBUG_PANIC),1)
PRODUCT_COPY_FILES +=     device/motorola/utah/debug/zz-debug-log.rc:$(TARGET_COPY_OUT_SYSTEM)/etc/init/zz-debug-log.rc     device/motorola/utah/debug/zz-debug-log.sh:$(TARGET_COPY_OUT_SYSTEM)/bin/zz-debug-log.sh
endif
