# 2026-11-04 20:45 修正版验证范围

TWRP 禁用 AVB2.0 原先通过 cmd 执行，stdout 仅进入 recovery.log，屏幕无逐分区日志。
现通过原生 terminalcommand 将开始、四个分区各自结果、最终汇总送入屏幕日志。
原生 terminalcommand 不保留子进程退出码，设备树包装器将真实结果在输出结束前发布，
专用确认/动作页在进入原生完成页前读回结果，失败不会误报成功。
23 种语言均有日志文字。实际 TWRP terminalcommand 方法与包装器在临时文件上
验证成功、部分失败和工具缺失；对照 OrangeFox 原生分区操作仍一致。
未在物理分区执行本次 AVB 测试，新镜像屏幕显示仍待用户验证。
用户提供的 2020 实机照片已确认六行操作日志显示，但仍有终端命令路径回显。
本次树内 GUI 输出适配仅隐藏 AVB 包装器的命令行；保留完整操作结果及普通终端回显。
使用默认 BasePartition 工厂和设备库接口，无前端源码编辑；最终 recovery 链接符号、
专用链接参数及真实 terminalcommand 的成功/失败/工具缺失输出回归均检查。

1915 OrangeFox 已撤回：将 advanced 页内联到 ui.xml 导致页面先于字体、资源、
样式和模板加载，Recovery 循环 SIGSEGV，Logo 闪烁。改为保持原 include 顺序，
独立加载树内 sheng-advanced.xml。当前设备 RAM 替换后用户确认进入界面，
Fox 插件首项可见。按钮最终名称按用户要求为“禁用 AVB2.0”。

电池启动日志显示固件片段加载失败，随后重试留下重复 GLINK 注册 -17。
删除重复启动，将只读 modem 固件挂到 /firmware，内核搜索路径设为
/firmware/image，避免 /vendor 挂卸影响。电池节点未就绪时不伪报 ready。
1940 实机冷启动已确认 ADSP running、电池 capacity=100、Health HAL 运行。
该镜像因 QSEE 启动脚本仍等待旧路径而卡在解密初始化 Logo。
RAM 中将 /vendor/firmware_mnt 链接到 /firmware 并启动 QSEE 后，
密钥服务恢复、data 挂载继续，用户确认进入界面。
现已修正启动器：等待独立挂载的真实固件文件，在执行 QSEE 前创建旧路径兼容链接。
以上实机结果来自 1940 加 RAM 修正；本目录新镜像仍待用户独立冷启动测试。

两前端编译与最终镜像完整审计、主题 include 顺序、插件首项/语言、
真实电池节点条件、单次 ADSP 启动、QSEE 固件路径兼容、fastbootd VINTF 检查均通过。
本次仅设备树新增修改，未修改前端源码；未自动刷写或启动新镜像。
此前 OTA 完整安装成功的用户确认不扩大为本次重新刷入验证。
