# 维护者头像

`maintainer-original.png` 是用户在本聊天提供的第二张图片
`IMG_20260924_210346.png`，4096×4096，保留原始 PNG 字节，未重绘或覆盖原文件。

SHA-256：`a642035eb41948031bf494c2b15849593ca3bad746fda6771851740715464d67`

OrangeFox 公共修补助手将其复制为主题 `Default/About/maintainer.png`，
资源 XML 使用 `width="192"`，仅在加载到内存时等比缩放到头像尺寸。
沿用关于页卡片的圆孔遮罩。头像以卡片为锚点，offsetx/offsety 与卡片图片使用
相同的最小缩放比例，避免宽屏布局只把头像坐标横向拉伸、导致图片偏出圆框。

这项界面变更仅用于 OrangeFox；没有给 TWRP 注入 OrangeFox 的主题代码。
r3 已重新编译并检查启动载荷，OrangeFox 为 98889728 字节，小于 96 MiB；
原图在最终镜像中的 SHA-256 一致。实机关于页布局仍待测试。

## Magisk recovery 组件

`Magisk-v30.7-sheng-recovery.zip` 从 [官方 v30.7 APK](https://github.com/topjohnwu/Magisk/releases/tag/v30.7)
中选择所有 assets、recovery 脚本、ARM64 程序以及可选 ARM32 magisk 程序，
保留每个组件的原始字节。此 ZIP 不是完整 Android APK。
原包校验值、选择范围和逐文件哈希见 `magisk-v30.7-provenance.json`。
Magisk 为第三方项目，其源代码和许可见 [官方 v30.7 源码](https://github.com/topjohnwu/Magisk/tree/v30.7)。
可用树内 `tools/prepare_magisk_addon.py` 和指定版本的官方 APK 重建。
最终镜像内的 ZIP、脚本和入口已检查，实际安装/卸载尚未实测。
