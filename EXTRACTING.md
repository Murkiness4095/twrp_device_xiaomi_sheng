# 从官方 303 重新提取

构建所需的文件已经随树提供。只有更新或重建 blobs 时才需要下面的步骤。
请使用 Linux/WSL 的 Linux 文件系统保存工作目录，以保留符号链接；原始 images
可以位于 Windows 盘。输入固定为本次 `OS3.0.303.0.WNXCNXM`，不能混用其他版本。

依赖 Python 3、binutils/readelf、lz4、simg2img、debugfs、qemu-aarch64，以及
Android 构建环境编出的 lpunpack。以下命令对应本次提取流程；不调用刷机脚本。

```sh
tree="$PWD/device/xiaomi/sheng"
images="/path/to/sheng_images_OS3.0.303.0.WNXCNXM_16.0/images"
work="/path/to/new-empty-linux-work"
hosttools="/path/to/android-out/host/linux-x86/bin"

python3 "$tree/tools/inspect_stock303.py" --images "$images" \
    --platform "$PWD" --output "$work/stock-images"
mkdir -p "$work/super" "$work/partitions" "$work/roots"
simg2img "$images/super.img" "$work/super/super.raw.img"
"$hosttools/lpunpack" -p vendor_a -p odm_a -p vendor_dlkm_a \
    -p system_a -p system_ext_a -p system_dlkm_a \
    "$work/super/super.raw.img" "$work/partitions"

# 使用本次官方 recovery 的新 fsck.erofs，避免宿主旧版本不支持 --extract。
rec="$work/stock-images/recovery/ramdisk-root"
for part in vendor odm vendor_dlkm system system_ext system_dlkm; do
    qemu-aarch64 -L "$rec" -E LD_LIBRARY_PATH=/system/lib64 \
        "$rec/system/bin/fsck.erofs" --no-preserve-owner \
        --extract="$work/roots/$part" "$work/partitions/${part}_a.img"
done

python3 "$tree/tools/extract_stock_apex.py" \
    --apex "$work/roots/system_ext/apex/com.android.vndk.v33.apex" \
    --stock-recovery-root "$rec" --output "$work/apex-v33"
python3 "$tree/extract-files.py" --stock-work "$work" --images "$images"
```

提取器根据 ELF 的 DT_NEEDED 递归解析私有用户态依赖，并按 modules.dep 生成额外
触摸模块加载顺序。它同时生成 `Android.mk`、`proprietary.mk` 和来源哈希清单。
没有使用 ELF 检查豁免；镜像构建会检查这些预编译模块。

提取不会证明驱动、解密或触摸已经在设备上通过；应另外进行实机回归。
