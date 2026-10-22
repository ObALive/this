# 本机验收操作记录

时间：2026-10-22（Asia/Shanghai）

执行命令：`D:\Unity\2022.3.62f3c1\Editor\Unity.exe -batchmode -projectPath D:\myspace\Git\mygame -executeMethod RoleMove0Acceptance20261022.Run -logFile D:\myspace\Git\this\Output\角色移动0-验收20261022\角色移动0-验收20261022_Unity.log`（Start-Process，WindowStyle Hidden）。

执行目的：编译当前工作区，进入真实 Play Mode，验证任务效果及公开 API 边界，保存行为输出与相机渲染图。

影响范围：本机 Unity 进程 80184，工程缓存、自动生成工程文件、日志与布局；临时探针位于 Assets/Editor，验证完成后已移除。无对外服务配置修改。

执行结果：Play Mode 帧数 1→11，22 条断言完成，截图 2 张。16 PASS、6 FAIL；其中一条“禁用即解绑”的断言未得到契约支持，报告归为观察项。编译无 error CS。EditorApplication.Exit(1) 后进程停留于退出阶段，核对 PID 和命令行后使用 `Stop-Process -Id 80184 -Force` 清理。

恢复方案与实际清理：移除本轮临时脚本和 .meta；恢复本轮前干净的自动生成工程文件；将两个 Unity 自动改名的 -prev 导入日志移回原名；比对 15 个业务文件 SHA-256，均无变化。没有使用 git reset、未覆盖已有业务修改。Unity 清除的旧 shader worker 日志缺少启动前副本，保留实际删除状态并在报告披露，未用提交内容冒充原有未提交日志。
