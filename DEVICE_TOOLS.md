# 设备树内的实用功能 / Device-local tools

本次新增功能不修改 `bootable/recovery` 或 `vendor/twrp` 的源码。
沿用本树此前已有的输入、显示等公共修补；没有为本次功能增加前端源码补丁。

## TWRP

- 在原有“高级”列表增加“禁用 AVB 2.0 验证”和“安装 Magisk 30.7”。
- AVB 默认处理 A/B 两槽的 `vbmeta` 和 `vbmeta_system`，进入滑动确认页后才运行。
  `src/sheng_avb.cpp` 随设备树编译为 recovery 中的 `sheng-avb`。
  处理代码移植自固定版本 OrangeFox 的 `Do_Disable_AVB2` / `Disable_AVB2`：
  检查 `AVB0`，将偏移 123 的一个字节设为 `VERIFICATION_DISABLED=2`；
  四个 A/B 目标都尝试处理，按原生逻辑汇总成功/失败。不增加自动备份、回滚、
  额外的 HASHTREE_DISABLED 标志，也不挂载或写入 metadata。
  仅把原生 GUI 输出依赖换为独立程序的输出及退出码。
- “安装 Magisk 30.7”清空 ZIP 队列，选择内置的官方 ARM64 recovery 组件包，
  打开正常刷入确认页；不会在启动 Recovery 时自动安装。
- 菜单复用现有的安装、槽位和滑动确认翻译；新增文字覆盖全部 23 种语言。

`tools/prepare-device-tools.py` 从固定的 TeamWin 主题生成设备树内的
`generated/twrp/ui.xml` 和 `languages/`，通过原生 `TW_CUSTOM_THEME`
接入界面。设备 init 在 Recovery 启动前将语言资源复制到内存中的 `/twres/languages/`；
这是因为前端启动时会清除 `customlanguages/`，不能把它当作持久的内置资源目录。
不覆盖或修改前端源码目录中的 XML/C++ 文件。
基础主题来自 TeamWin `android_bootable_recovery` 提交
`5c3d206a5eeb3d446bcda8248a405a4b278bab5c`；派生主题与复制的语言资源保留
TeamWin 上游权利及许可，不适用本树新辅助代码的 Apache-2.0 许可替代声明。

## OrangeFox

在 `orangefox.mk` 启用 `OF_SUPPORT_VBMETA_AVB2_PATCHING := 1`。
设备树生成的自定义主题在 Fox 插件列表加入手动禁用入口，滑动确认后直接调用
原生 `disableAVB2` 动作，按原生实现处理 A/B 两槽。保留原生翻译及原来设置/安装
页面的位置。运行时复选框仍默认关闭；
勾选后使用原生流程处理 A/B 两槽。Magisk 继续使用原来的模块页面。
32 种内置语言中，西班牙语和匈牙利语原本缺少 AVB 文字，设备树补齐其翻译。

## fastbootd 启动

第一阶段 init 已加载配套模块。旧硬件脚本逐项执行 tr/grep，338 项产生大量进程；
现只读取一次 `/proc/modules`，使用 shell 内建匹配，仍加载任何缺少的模块。
电池节点等待间隔从 1 秒改为 0.1 秒，最长仍为 10 秒，不伪造电池状态或绕过 Health。
ADSP 因早期固件加载失败而保持 offline 时，最多启动五次，失败之间间隔 0.2 秒；
首次成功不增加等待。电池节点仍不存在时不发布 hardware.ready，避免误报就绪。
实机只读对比为旧循环 4.88 秒、新循环 0.081 秒，均确认没有缺少模块。
这是模块检查的计时，不等于完整 USB 枚举耗时。

后续根据实机日志，增加 `PRODUCT_ENFORCE_VINTF_MANIFEST_OVERRIDE := true`。
Android 12.1 构建系统会重算派生的 `PRODUCT_ENFORCE_VINTF_MANIFEST`，因此必须
使用 BoardConfig 的 override 入口，不能仅在 device.mk 给派生变量赋值。
这使 libhidl 使用已有 VINTF 声明，编译掉未强制校验时每次查询固定 sleep(1)
的分支。fastbootd 的三次顺序查询因此不再强制累计等 3 秒。fs 阶段提前启动
原生 BootControl，电池服务仍按真实硬件就绪启动。
随镜像校验实际的 libhidlbase 和编译选项，并以平台真实 libvintf 查询加密、
电池和槽位服务的声明；不修改 libhidl/fastbootd 或前端源码。

## Build / validation

Use `tools/build.sh` in an initialized Android 12.1 recovery checkout. The build
helper generates the TWRP custom theme inside this device tree before lunch.
OrangeFox retains its original automatic AVB option and adds a manual native
AVB action to Fox plugins through a device-local custom theme.
The TWRP AVB confirmation defaults to both slots. Its disk operation is ported
from the pinned OrangeFox A/B implementation: check AVB0 and set byte 123 to 2.
No backup, metadata mount, rollback or extra hashtree flag is added.
Both entries follow the selected UI language; all 23 bundled TWRP languages
have translations for the additional strings.

`python3 tools/verify_device_avb.py --orangefox-source <pinned-OrangeFox-checkout>
--report <report.json>` compiles both the port and the real upstream functions
against temporary image files. It compares final bytes and return values for
normal, already-disabled, malformed, missing and short targets, including the
upstream partial-failure behavior. Host tests never write physical partitions.
Actual AVB disabling and Magisk installation require separate device testing.

The port preserves the TeamWin / OrangeFox attribution and GPL-3.0-or-later
license. See `src/ORANGEFOX-NOTICE`.
