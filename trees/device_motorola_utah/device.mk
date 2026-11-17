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
