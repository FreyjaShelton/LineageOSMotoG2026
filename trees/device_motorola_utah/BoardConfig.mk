#
# SPDX-License-Identifier: Apache-2.0
#
# Utah (moto g 2026, XT2613-1, MT6835). Same board, partitions, device tree
# and vendor build as nevada (XT2615-1); see BUILD_PLAN.md, Phase 3. This tree
# only layers the utah identity on top of device/motorola/nevada.
#

# Use OUR firmware's kernel, DTB and modules (5.15.189), not nevada's (5.15.180).
# Built by scripts/extract-utah-kernel.sh. Needs patches/device_motorola_nevada/0002.
KERNEL_PATH := device/motorola/utah-kernel

include device/motorola/nevada/BoardConfig.mk

# --- utah safety settings for the first flash (see BUILD_PLAN.md, Phase 4, Step C) ---

# Anti-rollback: stock vbmeta and vbmeta_system are both at rollback index 13
# (checked with avbtool on our firmware). nevada's 20 could stop stock from
# booting again. Never set this above the stock value.
BOARD_AVB_ROLLBACK_INDEX := 13
BOARD_AVB_VBMETA_SYSTEM_ROLLBACK_INDEX := 13

# By default the OTA only touches the 9 normal partitions. nevada's vendor
# makefile adds 15 firmware images (lk/bootloader, preloader, tee, md1img/modem...);
# they are identical to what is on the phone, and an interrupted preloader write
# can hard-brick a MediaTek phone. Build with UTAH_FLASH_FIRMWARE=1 to include them.
ifneq ($(UTAH_FLASH_FIRMWARE),1)
AB_OTA_PARTITIONS := \
    boot \
    system \
    system_ext \
    product \
    vendor \
    vendor_dlkm \
    system_dlkm \
    vendor_boot \
    init_boot \
    vbmeta \
    vbmeta_system
endif

# system_dlkm (found 2026-11-17 from the phone's boot log). Stock's super has a
# system_dlkm logical partition and its first-stage fstab and vold REQUIRE it: without
# it init died on "DM_DEV_STATUS failed for system_dlkm_a" and then vold aborted, so the
# phone looped. Stock's copy is an empty placeholder (0.35 MB: only /etc/build.prop, a
# notice file and two empty fs_config files, no kernel modules), so we build an empty
# one. Needs the group list below (group name from our OTA payload: nevada's super group
# is motorola_dynamic_partitions) and the OTA list above. See BUILD_PLAN.md, "Tracked
# issue: partitions our build does not create". The old stopgap, deleting the lines from
# the fstab, is scripts/drop-system-dlkm-from-fstab.sh (no longer needed with this).
BOARD_USES_SYSTEM_DLKMIMAGE := true
BOARD_SYSTEM_DLKMIMAGE_FILE_SYSTEM_TYPE := erofs
TARGET_COPY_OUT_SYSTEM_DLKM := system_dlkm
BOARD_MOTOROLA_DYNAMIC_PARTITIONS_PARTITION_LIST := $(sort $(BOARD_MOTOROLA_DYNAMIC_PARTITIONS_PARTITION_LIST) system_dlkm)

# init_boot (Phase 4, Step C2). Stock has a separate 8 MiB init_boot partition that
# holds the generic ramdisk, and its boot.img has an EMPTY ramdisk. Without this,
# our boot.img carried the ramdisk itself and the phone's stock init_boot would
# still be there beside it. Size is from the stock partition table (PGPT).
BOARD_INIT_BOOT_IMAGE_PARTITION_SIZE := 8388608
# init_boot header version must match boot/vendor_boot (v4, as stock). Make's mkbootimg
# builds init_boot and defaults to v0; BOARD_INIT_BOOT_HEADER_VERSION is not read by this tree.
BOARD_MKBOOTIMG_INIT_ARGS += --header_version 4

# Boot animation: the saved "trop-pink" vaporwave one (bootanimation/keep/ in the repo).
# scripts/install-utah-tree.sh copies the zip here. LineageOS reads this variable
# (vendor/lineage/config/BoardConfigSoong.mk) and installs it as the product
# media/bootanimation.zip instead of generating its own.
TARGET_BOOTANIMATION := device/motorola/utah/bootanimation/bootanimation.zip
