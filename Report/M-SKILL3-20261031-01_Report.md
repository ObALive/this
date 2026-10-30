# 角色技能 3：指定敌对目标固定伤害

| 项目 | 内容 |
| --- | --- |
| 任务标识 | M-SKILL3-20261031-01 |
| 任务说明 | 用户本次指令；`D:/myspace/Git/mygame/Dsh/Task/M系列任务/模板.md` |
| 执行日期 | 2026-10-31（Asia/Shanghai） |
| 完成状态 | Completed：完成且已验证本节点核心路径 |
| 报告版本 | v1 |

## 1. 任务目标

实现网络图“角色行为/角色技能 3 / 指定敌对目标固定伤害”。本次库中标识为 n8，概要、路线、序号与正文已一并核对。对象声明要求区分地格指向与对象指向：整片射程沿外围描线，只高亮范围内存在合法目标的格子。

## 2. 任务书摘要

按用户指定模板完成实际功能，不另行等待完整代码设计案。首要约束为职责解耦、增量可局部接入、最少必要判定与验证。只读 Rules、系统设计、架构设计、旧 Code_Design 与网络图 Tool；没有改写网络图数据库、正文或状态。未提交或推送 Git。

适用规则：NR-01、NR-02 为必读；NR-05 §六用于过程与报告归档；NR-06 用于同步实际代码解释。记录不另行定义游戏规则，不预建校验框架或新增测试脚本。模板的直接实施与默认不提交要求优先于任务书另存、先提交未跟踪文件等通用过程要求。

采用的系统设计依据：技能系统 §7–8 的使用侧、即时效果边界；元动作 §4.3–4.4 的生命周期与一次性效果归属。架构对照采用 §1.6 的职责/通信边界、M05 战斗职责及 §7.4 的语义输入要求。保留当前 Assembly-CSharp 装配，不借机实施全局程序集拆分。

## 3. 执行环境

Unity 工程 `D:/myspace/Git/mygame`；Unity 2022.3.62f3c1。基线提交 `bf1b4d8caf90a8d6e10de503f1e682b96bb3b936`，本次为工作区增量。原有未提交输出与日志保持不动。

加载场景为 PersistanceScene、01.Field、UI、Template；编辑前均无未保存场景修改。原项目使用旧输入后端、uGUI/TMP、Tilemap、Cinemachine。编辑与验证结束后退出播放模式，回到原编辑状态。

## 4. 使用工具

只读 `query.py --db N01_完整依赖清理新图_v2.sqlite` 查询节点和 v_edge。工程已有 Unity MCP 正常连接，使用其 execute_code、refresh_unity、manage_editor、read_console；没有安装 CLI 或为任务增加 Pipeline 包。

使用 Unity 编辑器创建动作/后摇资产、更新槽引用并添加场景组件，保留原资产身份。使用现有 FontTools 对字体子集补字，并经 TMP 原位重新烘焙。验证通过编辑器内临时语义调用和真实场景截图完成，没有新增 Assets/Editor 测试脚本。

## 5. 执行过程

### 直接前置核查

v_edge 同时读出了显式与链式依赖：

| 前置 | 来源 | 工程事实与使用方式 |
| --- | --- | --- |
| 角色行为/角色属性 2：动态属性血量 | explicit，n20 → n8 | MetaObjectMeterComponent 保存 Health；Modify 钳位并返回实际变化；UnitDetailsPanel 每帧读取生命摘要 |
| 角色行为/角色技能 2：待机动作 | chain，n7 → n8 | BasicSkillSlotsComponent 四槽持有独占动作，选择→Outlet→生命周期→Router 的路径完整可复用 |

前置已有实现，本次通过最终扣血、待机、移动的运行证据确认协作可用，没有仅凭图状态判定。

### 复用、适配与新增

- 复用：元对象/动作定义、四技能槽、动作生命周期、后摇时间轴、键值路由、量表与生命摘要。状态继续由原权威对象保存。
- 适配：ActionTargetKind 在末尾增加 Object；执行上下文携带目标实例，Outlet 按目标类型编码 target；Router 增加目标解析；现有统一输入入口接入对象按压意图。
- 新增：FixedDamagePacketBuilder 定义/运行对、FixedDamageEffectExecutor、ObjectTargeting、ObjectTargetOverlay。参数生成、业务判定、效果提交、范围绘制分别归属。
- 资产接线：三个角色第一个技能槽配置固定伤害，其余三槽保持待机；Router 同物体挂固定伤害执行器，三个角色挂对象范围显示组件。
- 实际结构不需要重做已有移动或待机系统，没有引入独立扣血旁路或重复的生命状态。

当前演示资产配置固定伤害 25、曼哈顿射程 4、后摇 12 游戏秒。射程与资格分别形成：地图上存在且在几何射程内的格子决定外框；敌对关系与 Health 量表决定对象资格，查询和提交共用 ObjectTargeting.Validate。

外围网格只生成并集边界，没有逐格画内部框线。选择、取消与机会交接不直接改变生命；效果执行器调用原量表 Modify，成功后由生命周期回排时间轴。

### 实际验证

| 验证 | 实际结果 |
| --- | --- |
| Unity 导入和编译 | 新类型可在编辑器反射/执行中使用，最终控制台 error 为 0 |
| 场景持续运行 | 不同执行点 Time.frameCount 为 3802、10020、13241，场景在推进 |
| 选择与预览 | 玩家选择第一个技能，41 个射程格、36 段外围边、1 个合法敌方目标；画面没有内部逐格边框 |
| 友方点击 | 使用 GridClickInput.SubmitScreenPoint 点击我方角色，无动作提交、机会号不变 |
| 取消 | ProcessCancel 清选择，不消耗机会，重新选择可继续提交 |
| 指定敌人伤害 | 同一目标地格按下并松开后返回 true；敌方角色3 的生命从 60/80 变为 35/80；其他角色生命保持 100、120 |
| 统一提交与结果 | 请求 operation=FixedDamage、targetKind=Object、damage=25f、range=4、target=目标 RuntimeId；结果 healthBefore=60、healthAfter=35、appliedDamage=25、status=Succeeded |
| 后摇 | 动作相态 Completed；玩家标记从本次时刻 0 回排到 12，机会号从 1 增到 2 |
| 生命显示 | 面板实际显示角色3 35/80，保留其余角色摘要 |
| 待机回归 | 选择并再次选择原第二槽，正常完成一次机会交接 |
| 移动回归 | 原移动入口从 (11,-4) 移至有效范围格 (11,-11)，返回 Moved；机会号到 4；对象高亮已清除 |
| 字形修正后复验 | 保留旧字形，新增所需 10 个静态 SDF 字符；HasCharacters 返回 true；复验点击仍扣至 35，画面文字正常 |

截图位于本任务 Output 目录。上述指针验证调用现有语义输入方法完成，没有声称逐项人工按键测试或全场景测试。

## 6. 文件变更列表

| 文件或范围 | 变更 |
| --- | --- |
| Assets/Script/Battle/FixedDamagePacketBuilder.cs（及 .meta） | 新增固定伤害定义工厂与运行构造器 |
| Assets/Script/Battle/FixedDamageEffectExecutor.cs（及 .meta） | 新增同步量表扣减 |
| Assets/Script/Battle/ObjectTargeting.cs（及 .meta） | 新增对象资格与射程规则 |
| Assets/Script/Player/ObjectTargetOverlay.cs（及 .meta） | 新增外围轮廓、目标填色和资源清理 |
| Battle/MetaActionComponents.cs、ActionPacketBuilders.cs、MetaActionInstance.cs | Object 枚举、上下文目标、TargetRange 读取 |
| Battle/ActionPackets.cs、ActionRouterManager.cs、BattleTimelineController.cs | 对象目标编码/登记/解析，公开参战查询枚举 |
| Player/SkillSelectionController.cs、GridClickInput.cs | 对象选择与语义指针路径、相机读取、失焦清理 |
| UI/UnitDetailsPanel.cs | 对象指向技能提示；保留已有按钮层级与生命显示 |
| GameData/Battle/FixedDamageAction.asset、FixedDamageTiming.asset（及 .meta） | 伤害、射程、后摇配置 |
| GameData/MetaObjects/Player.asset、Battle/Unit_02_Timeline.asset、Unit_03_Timeline.asset | 仅替换第一个技能引用 |
| Scenes/PersistanceScene.unity | 添加执行器与三角色范围显示组件；RequireComponent 保证选择适配器接线 |
| GameData/UI/UnitDetails.ttf、UnitDetails SDF.asset | 保留已有字符与资产引用，补足新增中文文案并重烘焙静态图集 |
| Assembly-CSharp.csproj | Unity 自动将四个新增运行脚本列入现有程序集 |
| 代码说明文档 95、README、30、75、80、90 与横向扩展内容库 | 同步源码事实、目标协议与量表调用，保留现有表结构 |

## 7. 权限操作记录

未安装软件、未修改系统环境/网络设置、未启动外部服务、未提交 Git、未推送远程。Unity 编辑、播放与文件修改均在当前节点授权范围内。只读查询网络图，未修改 Rules、系统设计、架构设计、旧 Code_Design 或 Tool。

## 8. 异常情况

首次仅请求脚本编译时，新建脚本尚未全部被 AssetDatabase 导入，出现新类型未找到。随后执行全资产刷新与编译，恢复连接后编译成功，最终错误计数为 0。

首次画面检查发现新增中文显示方框。原字体 TTF 本身是子集，直接往静态图集补字失败；确认缺少源字形后保留原 205 个源字符并补充所需字符，原位重烘焙已有 164 字形与新增文案，最终静态图集含 174 字符，旧字形全部保留。

字体修正后的首次复验调用遇到选择已因失焦取消，未提交伤害。确认 SelectedIndex=-1 后重新选择并完成同一路径，提交成功；未为该既有取消行为增加防御机制或改变规则。

截图接口为异步请求，一次结果截图在退出播放后才成图，读图发现已是编辑态。随后在播放中重新完成有效点击，使用现有截图工具请求并等待文件落盘，读图确认生命35/80后归档，才退出播放。正式交付图片已替换为实际运行结果。

现有 Router 的日志目录仍指向其历史配置。本次播放产生的三个新日志已按精确文件名及 FixedDamage 内容确认后移至本任务 Output，原有历史日志不动；未为单次验收更改运行日志基础配置。

## 9. 输出文件列表

- `Output/M-SKILL3-20261031-01/M-SKILL3-20261031-01_对象目标预览.png`
- `Output/M-SKILL3-20261031-01/M-SKILL3-20261031-01_固定伤害结果.png`
- `Output/M-SKILL3-20261031-01/M-SKILL3-20261031-01_运行日志01.jsonl` 至 `运行日志03.jsonl`
- `Output/M-SKILL3-20261031-01/checkpoint_001.md`
- 本报告。

## 10. 完成状态

任务目标、资产接线、核心运行证据、配套解释与本报告均已完成。状态为“完成且已验证本节点核心路径”。

横向扩展内容库沿用 20 张内容表，由 87 条增至 96 条，已完成完整性、外键和 75 个源码文件/146 处证据核验。没有创建新内容表。没有为本节点新增专门的测试/验收脚本。

## 11. 后续建议

后续对象指向技能可以复用 Object 目标编码、参与者查询、ObjectTargeting 的当前规则与 ObjectTargetOverlay；固定伤害参数从动作资产调整，后摇仍由 BattleBehaviorDefinition 提供。按后续节点的真实需求再局部扩展规则，不提前加入通用技能框架。

本节点未验收属性伤害公式、治疗、死亡/击倒、持续效果、射线阻挡、叠格多目标切换或广泛技能范围形状。生命到达下限仍由量表钳位，不自动移除角色。网络图中后续技能范围预览节点的通用化要求保持其独立验收范围，本次仅满足当前对象声明要求。
