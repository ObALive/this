任务状态：Completed，完成且已验证。

任务详细说明：用户要求可点击地格悬浮、按住时不透明度变化，按下不触发，原格松开触发，按住移出后取消。

已完成：GridClickInput分阶段状态与取消、MovementRangeOverlay三态单格alpha、真实场景28项交互验收、37项属性回归、元对象接线0失败。常态/悬浮/按住系数0.5/0.8/1.0。现有Play模式保持，角色(7,-7)恢复。截图和报告已归档。

未完成：本请求无。独立播放器、跨平台和OS鼠标自动化未验证。

当前环境：Unity2022.3.62f3c1 PID96236，工程D:/myspace/Git/mygame；HEAD e422970858e2fa27b94c8389467300dc01092474。编辑器处于原有Play模式，未保存场景。

已修改文件：GridClickInput.cs、MovementRangeOverlay.cs、MovementRangeVerification.cs；新增GridPointerVerification.cs及.meta。常驻场景文件哈希未变。

执行记录：旧验证入口因已在Play被拒绝；脚本热重载导致普通C#实例丢失，改为live工具准备阶段保留位置和Sprite重绑定；最终28项全部通过。异常审计保留，不把历史准备异常计为最终成功一轮的0错误。无数据库写入、无提交或推送。

下一步：交付用户；Inspector可调整Normal/Hover/Pressed Opacity。无需重新接线。
