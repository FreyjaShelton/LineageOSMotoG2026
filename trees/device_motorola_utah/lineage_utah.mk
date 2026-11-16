#
# SPDX-License-Identifier: Apache-2.0
#
# Utah (moto g 2026, XT2613-1, RETUS). Differs from nevada (moto g play 2026,
# XT2615-1) only by the per-SKU props in /product/etc/motorola/props:
#   hardware.sku.XT2613-1.prop: ro.product.device=utah,
#     ro.product.product.model="moto g - 2026", ro.product.name.canonical=utah,
#     ro.product.product.name.suffix=u
#   carrier.cc.sku.XT2613-1.prop: persist.carrier.media.dir=/product/carrier/cc/utah/media
#

# Inherit from those products. Most specific first.
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base_telephony.mk)

# Inherit from the device makefile (nevada).
$(call inherit-product, device/motorola/utah/device.mk)

# Inherit some common lineageOS stuff.
$(call inherit-product, vendor/lineage/config/common_full_phone.mk)

TARGET_BOOT_ANIMATION_RES := 720

PRODUCT_NAME := lineage_utah
PRODUCT_DEVICE := utah
PRODUCT_MANUFACTURER := Motorola
PRODUCT_BRAND := motorola
PRODUCT_MODEL := moto g - 2026

PRODUCT_GMS_CLIENTID_BASE := android-motorola

# Read from our phone (adb getprop, 2026-11-16).
PRODUCT_BUILD_PROP_OVERRIDES += \
    DeviceName=utah \
    BuildDesc="nevada_g_sysu-user 16 W1WNS36.18-114-3-2-1-1-1 bb91ee-4dbad release-keys" \
    BuildFingerprint=motorola/nevada_g_sysu/utah:16/W1WNS36.18-114-3-2-1-1-1/bb91ee-4dbad:user/release-keys
