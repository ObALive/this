任务状态：Running
任务详细说明：实现角色行为 / 角色移动 / 2 / 高亮渲染可移动的地格（n11），直接前置 n10 已在当前工程实现。
已完成：只读查询节点和直接前置，工作区起点校验；范围计算、覆盖层、移动受理限制、DebugPanel 反馈、32px 框形 Tile 已完成。用户最终修正规则为曼哈顿距离，取行动力非负整数部分，当前位置不算目的地；无行动力消耗。已编译成功。当前 Player 已接线并保存，保留用户当前 Barrel 场景 sprite 与渲染器绑定；UI 脏场景未保存或重载。
未完成：实际 Play Mode 验证、截图检查、最终报告。
当前环境：Unity 2022.3.62f3c1，已有编辑器 PID 96236；工程 D:/myspace/Git/mygame；HEAD e422970858e2fa27b94c8389467300dc01092474。unity-cli 不可用，采用项目 Editor 验证请求入口。
已修改文件：新增 MovementRange.cs、MovementRangeOverlay.cs、MovementRangeVerification.cs、GameData/Movement；修改 TilemapManager.cs、CharacterMovementController.cs、DebugPanel.cs、PersistanceScene.unity；不修改数据库、Rules、设计稿，不提交或推送。
执行记录：原切比雪夫选择已被用户明确更正为曼哈顿。节点后续路径与地形能力未实现，本轮只按存在地格与距离筛选；不会宣称路径可达性验收。已有前置未提交文件保留，不为规则中的版本核验条款擅自提交。
下一步：通过 Temp/MovementRangeVerification.request 的 verify 操作运行现有加载场景，结果归档到本目录；修复失败并保留异常记录，不使用旧验证入口重载脏场景。
