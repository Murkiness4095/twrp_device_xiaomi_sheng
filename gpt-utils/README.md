# GPT / UFS 支持代码来源

本目录的 GPT/UFS 源码来自 map220v/android_device_xiaomi_sheng 的固定提交
`a9a2994997fa3574b6e718561b5d1c884661b89e`，原文件包含 Linux Foundation /
Qualcomm 的版权与许可，均保留。Android.bp 中的本设备构建模块改名为
`libgptutils.sheng`；不声称这些通用底层源码是本工程原创。

上游：https://github.com/map220v/android_device_xiaomi_sheng/tree/a9a2994997fa3574b6e718561b5d1c884661b89e/gpt-utils

它为平台 `hardware/qcom-caf/bootctrl` 的 QTI BootControl 实现提供 GPT/UFS
辅助函数。当前源码平台该仓库提交为 `9ed7376299a15399624ebff4fcf8b8a162cd6c34`。
设备的 checkpoint 检查依赖 BootControl 查询当前槽位；缺少实现会一直等待服务，
导致元数据密钥已解开后仍卡 Logo。该支持代码由源码重新编译，不打入旧 r3 的二进制。

2026-11-04 的 OTA 实机测试暴露了切槽适配缺口：payload 写入和哈希校验通过，
但 QTI 的逐盘切槽算法把 multiimgoem_a/b 当作同一 GPT 内的一对；实际它们和
multiimgqti_a/b、xbl_a/b、xbl_config_a/b 都跨 UFS Boot LUN 1/2。
本设备的 `AB_PTN_LIST` 现仅选择共享 LUN 中的分区，保留原始 `PTN_SWAP_LIST`，
也保留 QTI 在最后调用 `gpt_utils_set_xbl_boot_partition()` 切换整个 Boot LUN 的路径。
这是一项本地硬件适配改动；不是忽略失败、跳过 UFS 切换或伪造成功。
以真实 QTI 方法和本机只读拓扑作的主机模拟回归通过；实际物理切槽仍需单独验证。
