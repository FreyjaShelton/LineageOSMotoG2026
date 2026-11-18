#!/system/bin/sh
# DEBUG ONLY (installed to /system/bin with UTAH_DEBUG_PANIC=1, started by zz-debug-log.rc).
# Writes the phone's own logs into /metadata/dbg every 20 s for 15 minutes. /metadata is not
# encrypted, init mounts it in first stage, and our recovery can mount and read it after ANY
# restart, even a forced power-off. No panic, no timing, no key held.
# Read it from our recovery:  adb shell mount -t f2fs -o ro /dev/block/by-name/metadata /mnt/md
#                             adb pull /mnt/md/dbg   (the previous boot's copy is dbg.prev)
D=/metadata/dbg
rm -rf "$D.prev"
[ -d "$D" ] && mv "$D" "$D.prev"
mkdir -p "$D"
chmod 0777 "$D"

snap() {  # snap NAME COMMAND...  : run the command, write its output atomically
    name=$1; shift
    "$@" > "$D/$name.tmp" 2>&1
    mv "$D/$name.tmp" "$D/$name"
}

n=0
while [ "$n" -lt 45 ]; do
    {
        echo "snapshot $n at uptime $(cat /proc/uptime)"
        echo "sys.boot_completed=$(getprop sys.boot_completed) init.svc.zygote=$(getprop init.svc.zygote) init.svc.surfaceflinger=$(getprop init.svc.surfaceflinger) init.svc.bootanim=$(getprop init.svc.bootanim) vold.decrypt=$(getprop vold.decrypt) ro.crypto.state=$(getprop ro.crypto.state)"
    } > "$D/status.tmp" 2>&1
    mv "$D/status.tmp" "$D/status.txt"
    snap dmesg.txt dmesg
    snap logcat.txt logcat -b all -d
    snap ps.txt ps -A -o PID,PPID,STAT,WCHAN,ARGS
    snap getprop.txt getprop
    snap mounts.txt cat /proc/mounts
    snap bootprof.txt cat /proc/bootprof
    snap cmdline.txt cat /proc/cmdline
    sync
    n=$((n + 1))
    sleep 20
done
