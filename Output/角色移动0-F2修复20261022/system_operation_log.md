# F2 修复运行验证操作记录

时间：2026-10-22（Asia/Shanghai）

执行命令：`D:\Unity\2022.3.62f3c1\Editor\Unity.exe -batchmode -projectPath D:\myspace\Git\mygame -executeMethod RoleMove0F2Regression20261022.Run -logFile D:\myspace\Git\this\Output\角色移动0-F2修复20261022\角色移动0-F2修复20261022_Unity.log`，使用 Start-Process 的 WindowStyle Hidden。

目的与影响：加载原有四场景，在 Play Mode 运行 F2 的针对性验证。临时探针仅用于编辑器编译，不保存场景。Unity 会自动更新工程文件、日志和会话文件，启动前采集 16 个相关文件的内容作为本次会话恢复依据。

结果：编译成功，帧数 1→11，13 项行为检查全部 PASS，最终场景自检 1 个预置 0 失败；结果与退出请求均已落盘。

清理：Unity 进程 91656 在退出阶段停滞，确认 PID、命令行及已写出的退出请求后，执行 Stop-Process -Id 91656 -Force；删除本轮临时脚本与 .meta；恢复启动前采集的 16 个会话文件，移除本轮新生成的 Logs 文件。恢复和删除前均校验绝对路径属于工程预期目录。恢复后逐项比对内容，无差异。

恢复范围：只恢复自动生成和会话文件；未覆盖任何业务源码、场景、Prefab 或用户并发编辑的任务书。实际 F2 修复保留。未启动外部服务、修改系统配置、权限或网络配置，未执行 Git 提交或推送。
