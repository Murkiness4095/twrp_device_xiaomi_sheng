# sheng — 设备树实用功能与 fastbootd 启动优化

- TWRP 原有“高级”页新增“禁用 AVB 2.0 验证”和“安装 Magisk 30.7”。
- TWRP AVB 默认处理 A/B 两槽的 vbmeta/vbmeta_system，滑动确认后才运行；
  按 OrangeFox 原生实现检查 AVB0，将偏移 123 的字节设为 2。
  不新增备份、回滚、metadata 挂载或额外 hashtree 标志。
- OrangeFox 在原生位置开放原生 AVB 选项，运行时默认不勾选；Magisk 原有位置不变。
- TWRP 23 种语言均有新增文字，OrangeFox 32 种语言原生 AVB 文字覆盖齐全。
  设备 init 在界面启动前安装内存语言覆盖，解决 customlanguages 启动被清除的问题。
- fastbootd 硬件初始化不再为 338 个模块反复启动 tr/grep。实机只读循环计时
  从 4.88 秒降至 0.081 秒；电池轮询间隔从 1 秒缩为 0.1 秒，最长等待仍为 10 秒。
- 新功能、主题生成、翻译、编译配置与启动脚本均在设备树内；两套前端源码
  构建前后的 tracked diff 和文件状态一致。本次没有新增前端源码补丁。

两前端构建、最终 IMG/ZIP 审计和资源入口检查通过。AVB 工具与实际 OrangeFox
原生函数在临时文件上进行字节及返回值对照，覆盖标志值、损坏、短文件、缺少目标
及原生部分失败行为，均一致；保留上游版权与 GPL-3.0-or-later 许可。
本轮未执行设备上的 AVB 禁用或 Magisk 安装；新镜像冷启动、界面和完整 USB 枚举
由用户实机测试。模块循环计时不等于完整 fastbootd 端口出现时间。
此前 0110 版本的官方 payload.bin OTA 完整安装已由用户确认成功；本轮未重刷 OTA。

型号 24018RPACC。两套 IMG 内嵌同套 303 内核/DTB/DTBO/338 个模块，使用 Zstd
ramdisk，保持 eng.peiyuesheng.sheng.20261103 和 peiyuesheng_sheng 标识。
TWRP 保持横屏，两前端默认中文且允许切换语言；文件名没有自定义修订号。

Implementation and reproduction details: DEVICE_TOOLS.md.

## 后续 fastbootd 固定等待优化

设备树 BoardConfig 使用 PRODUCT_ENFORCE_VINTF_MANIFEST_OVERRIDE := true，
通过构建系统启用真实的 HIDL VINTF 校验。镜像实际打包的 libhidlbase 已确认
不含旧版未强制校验路径的固定 sleep(1) 分支，消除三个顺序查询约 3 秒的强制等待。
设备 init 在 fs 阶段提前启动原生 BootControl 服务，Health 仍等待真实电池节点。
实际 libvintf 对 BootControl 1.0/1.1/1.2、Health 2.0/2.1、Gatekeeper 及四个
AIDL 加密服务实例的查询通过；未实现的可选 Fastboot HAL 正确返回未声明。
两套镜像检查通过，未修改前端/框架源码。此项不代表所有冷启动、USB 主机环境
都已达到 1 秒；新镜像的实际连接耗时及解密等实机回归仍由用户测试。

## 2026-11-04 电池启动重试与 Fox 插件手动 AVB

用户确认在运行中的 OrangeFox 重启离线 ADSP 后电池节点恢复。
设备树脚本加入最多五次 ADSP 启动尝试；失败间隔 0.2 秒，首次成功没有额外等待。
电池节点未生成时不误报 hardware.ready。四种模拟启动情形检查通过。
OrangeFox 设备树自定义主题在 Fox 插件加入手动禁用 AVB 的滑动确认，直接调用
原生 disableAVB2。原设置页自动开关和全部原生语言保留。
仅修改设备树；两个前端现有 tracked diff / status 与功能开发前记录一致。
新镜像冷启动电池恢复和手动按钮仍待实机确认，不能以主机检查代替。
