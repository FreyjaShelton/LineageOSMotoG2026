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

# DEBUG ONLY: build with UTAH_DEBUG_PANIC=1 to add a vendor init rc that panics the kernel
# 150 s after early-init if boot has not completed, so a hung boot leaves a log in pstore.
# See trees/device_motorola_utah/debug/zz-debug-panic.rc and BUILD_PLAN.md.
ifeq ($(UTAH_DEBUG_PANIC),1)
PRODUCT_COPY_FILES += \
    device/motorola/utah/debug/zz-debug-panic.rc:$(TARGET_COPY_OUT_VENDOR)/etc/init/zz-debug-panic.rc
endif
