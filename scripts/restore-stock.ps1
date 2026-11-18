# Put the phone back to Motorola stock (done 2026-11-17 and 2026-11-18). Run on the Windows PC with the
# phone in the BOOTLOADER (fastboot screen; from our recovery: adb reboot bootloader):
#     powershell -File scripts/restore-stock.ps1
# Writes only what flashfile.xml's own list says, from D:/LineageOS/firmware: stock vbmeta first (images with an
# AVB footer are checked against the current slot's vbmeta), then dtbo, init_boot, boot, vendor_boot on BOTH
# slots, the 27 super chunks (about 3 min), erases userdata and metadata, sets slot a. NEVER touches the GPT,
# preloader, lk, tee, modem or nvdata. Afterwards run: fastboot reboot. A leftover "No command" recovery screen
# on the first boot: hold Power, press Volume Up, Reboot system now. Verify the MD5s against flashfile.xml first
# (see BUILD_PLAN.md, "Getting back to stock"). Fallback: Motorola Software Fix.
$ErrorActionPreference = "Continue"   # fastboot writes its progress to stderr; judge by the exit code instead
$pt = "$env:USERPROFILE\platform-tools-extract\platform-tools\fastboot.exe"
$d  = (Get-ChildItem "D:\LineageOS\firmware" -Directory | Select-Object -First 1).FullName
function Fb {
    param([string[]]$a)
    $out = & $pt @a 2>&1 | ForEach-Object { "$_" }
    $code = $LASTEXITCODE
    $out | Where-Object { $_ -match "OKAY|FAILED|rror" } | ForEach-Object { "   $_" }
    if ($code -ne 0) { throw "fastboot $($a -join ' ') failed (exit $code)" }
}
function Flash($part, $file) { "flash $part  <-  $file"; Fb @("flash", $part, "$d\$file") }

"== 1. stock vbmeta first, both slots (images with an AVB footer are checked against the current slot's vbmeta)"
foreach ($s in "a", "b") { Flash "vbmeta_$s" "vbmeta.img"; Flash "vbmeta_system_$s" "vbmeta_system.img" }
"== 2. stock dtbo, init_boot, boot, vendor_boot on both slots"
foreach ($s in "a", "b") {
    Flash "dtbo_$s" "dtbo.img"
    Flash "init_boot_$s" "init_boot.img"
    Flash "boot_$s" "boot.img"
    Flash "vendor_boot_$s" "vendor_boot.img"
}
"== 3. stock super (27 sparse chunks)"
$t = Get-Date
0..26 | ForEach-Object { Flash "super" "super.img_sparsechunk.$_" }
"   super done in $([int]((Get-Date) - $t).TotalSeconds) s"
"== 4. erase userdata and metadata (both are blank already; nothing of yours is on them)"
Fb @("erase", "userdata")
Fb @("erase", "metadata")
"== 5. slot a active"
Fb @("set_active", "a")
"RESTORE FINISHED, no errors"
