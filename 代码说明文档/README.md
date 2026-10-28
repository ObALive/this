# 代码说明文档库

本库解释工程中的元对象、角色组件、元动作、键值报文、场景执行器、时间轴、移动输入与底部 UI。说明以实际程序集、类型和关键方法为定位单位，分别表达继承、组件持有、资产引用和调用关系；功能行为以源码及静态资产为依据。

| 项目 | 内容 |
| --- | --- |
| 本任务区 | D:/myspace/Git/this/ |
| 工程目录 | [D:/myspace/Git/mygame/](D:/myspace/Git/mygame) |
| 核对基线 | 工程提交 `65c2ff5e40cec060988b74091e189e09fdaa9e13`；核对时工程工作区干净 |
| 核对方式 | 源码声明、工程 Compile/Reference、关键调用链与场景/资产序列化接线 |
| 状态 | 已核对：各专题声明的源码与静态资产范围 |
| 更新日期 | 2026-10-29 |

## 阅读入口

先读 [00 程序集与类型关系总览](00_程序集与类型关系总览代码设计案.md) 了解类型和持有结构。角色数据沿“对象底座 → 场景组件 → 量表”阅读；动作执行沿“动作构造 → 槽位发送 → 报文路由 → 生命周期 → 时间轴”阅读；玩家操作沿“面板选择 → 地图输入与范围 → 槽位执行”追踪。

## 文档索引

表中运行类型均属于 Assembly-CSharp、全局命名空间；程序集依据由 00 专题说明。各行基线 `65c2ff5` 对应上表完整提交，状态“已核对”涵盖文内声明范围。关键入口的完整源码链接集中在各专题实现定位表。

| 编号与说明文件 | 主要类与解释功能 | 关键源码位置与入口 | 核对基线 | 状态 | 更新日期 |
| --- | --- | --- | --- | --- | --- |
| [00 程序集与类型关系总览](00_程序集与类型关系总览代码设计案.md) | 实际程序集、继承、组合与统一入口作用域 | [Assembly-CSharp.csproj](D:/myspace/Git/mygame/Assembly-CSharp.csproj)：Compile/Reference | 65c2ff5 | 已核对 | 2026-10-29 |
| [10 MetaObject 类型与组件底座](10_MetaObject类型与组件底座代码设计案.md) | MetaObjectDefinition、MetaObjectInstance、MetaObjectComponent：工厂、归属、生命周期与对象内部消息 | [MetaObjectInstance.cs](D:/myspace/Git/mygame/Assets/Script/MetaObjects/MetaObjectInstance.cs)：AddComponent、Publish、Dispose | 65c2ff5 | 已核对 | 2026-10-29 |
| [20 对象组件与场景承载](20_对象组件与场景承载类型代码设计案.md) | MetaObjectPreset、坐标、纹理、朝向、属性：绑定与状态来源 | [MetaObjectPreset.cs](D:/myspace/Git/mygame/Assets/Script/MetaObjects/MetaObjectPreset.cs)：TryBind、Rebuild；AttributeComponent.GetValue | 65c2ff5 | 已核对 | 2026-10-29 |
| [30 MetaAction 派生与动作构造](30_MetaAction派生类型与动作组件代码设计案.md) | MetaActionDefinition/Instance、ActionPacketBuilder：动作实例、技能参数、指向性与后摇 | [ActionPacketBuilders.cs](D:/myspace/Git/mygame/Assets/Script/Battle/ActionPacketBuilders.cs)：Build、Validate；MetaActionInstance.ExecutePacket | 65c2ff5 | 已核对 | 2026-10-29 |
| [40 MetaActionLifecycle 统一执行入口](40_MetaActionLifecycle统一执行入口代码设计案.md) | 每动作的开始、成功、拒绝、终止与异常 | [MetaActionLifecycle.cs](D:/myspace/Git/mygame/Assets/Script/Battle/MetaActionLifecycle.cs)：TryExecute、Terminate | 65c2ff5 | 已核对 | 2026-10-29 |
| [50 TimeLineManager 与战斗装配](50_TimeLineManager与战斗装配类型代码设计案.md) | 标记、机会、回排、配置、启动、调试及相机跟随 | [BattleTimelineController.cs](D:/myspace/Git/mygame/Assets/Script/Battle/BattleTimelineController.cs)：TryStartBattle、StopBattle；TimeLineManager.CompleteAction | 65c2ff5 | 已核对 | 2026-10-29 |
| [60 地图与移动适配](60_地图与移动适配类型代码设计案.md) | TilemapManager、MovementRange、GridClickInput、CharacterMovementController、覆盖层：范围与输入 | [CharacterMovementController.cs](D:/myspace/Git/mygame/Assets/Script/Player/CharacterMovementController.cs)：TryMoveToCell；MovementEffectExecutor.Execute | 65c2ff5 | 已核对 | 2026-10-29 |
| [70 UnitDetailsPanel 与选择界面](70_UnitDetailsPanel与移动选择界面代码设计案.md) | 当前行动者、属性、按钮、生命摘要和静态 UI 接线 | [UnitDetailsPanel.cs](D:/myspace/Git/mygame/Assets/Script/UI/UnitDetailsPanel.cs)：BindTimeline、Refresh、RefreshHealth | 65c2ff5 | 已核对 | 2026-10-29 |
| [75 量表与生命显示](75_量表组件与生命显示代码设计案.md) | MetaObjectMeterComponent、MeterComponent：通用区间数值与 Health 应用 | [MetaObjectMeterComponent.cs](D:/myspace/Git/mygame/Assets/Script/MetaObjects/MetaObjectMeterComponent.cs)：Modify、ValueChanged | 65c2ff5 | 已核对 | 2026-10-29 |
| [80 基础技能槽与待机](80_基础技能槽与待机动作代码设计案.md) | BasicSkillSlotsComponent、ActionHolderComponent、SkillSelectionController：独占动作、选择与确认 | [BasicSkillSlotsComponent.cs](D:/myspace/Git/mygame/Assets/Script/MetaObjects/BasicSkillSlotsComponent.cs)：Prepare、TryExecute、Terminate | 65c2ff5 | 已核对 | 2026-10-29 |
| [90 ActionRouterManager 与键值报文](90_ActionRouterManager与键值报文执行代码设计案.md) | ActionPacket、ActionPacketOutlet、Router、共享执行器与日志 | [ActionPackets.cs](D:/myspace/Git/mygame/Assets/Script/Battle/ActionPackets.cs)：Snapshot、Send；ActionRouterManager.Send | 65c2ff5 | 已核对 | 2026-10-29 |

## 功能覆盖与实际配置

| 功能 | 当前实现与主要说明 |
| --- | --- |
| 元对象与组件 | 定义创建独立实例，按具体类型挂载组件，统一处理场景绑定与清理，对象内部同步消息见 10、20 |
| 固定属性 | 行动力、力量、行动速度的基础值与按来源修正见 20；行动力供移动范围查询 |
| 通用量表与生命应用 | 上下限、可变值、增减钳位、变化通知见 75；三角色 Health 分别为 100/100、120/150、60/80 |
| 元动作与技能参数 | 每动作一个报文构造器，保存目标指向性与后摇，动作实例持有独立生命周期，见 30、40 |
| 四槽技能与待机 | 三角色四槽均引用待机定义，各槽独占运行实例；移动使用独立容器和按钮，见 80 |
| 键值报文与效果执行 | 构造器生成参数，槽位补来源与目标，Router 按操作选择同物体执行器并记录请求和结果，见 90 |
| 共享时间轴 | 初始时刻 0、1、2，成功后按行为固定后摇回排，同刻按配置顺序；移动和待机后摇均为 10 游戏秒，见 50 |
| 点击地格移动 | 查询现存地格，以行动力非负整数部分限定曼哈顿距离；同格有效按松确认，经报文提交坐标，见 60 |
| 范围高亮与反馈 | 独立 Tilemap 绘制可选格，按普通、悬停和按压反馈，取消或失效时清理，见 60 |
| 底部详情与选择 | 当前行动者三项属性、独立移动和四技能按钮、全场生命摘要与提示，见 70 |
| 相机跟随 | 虚拟相机跟随当前行动者，平面位移统一阻尼，表现读取时间轴结果，见 50 |

## 实现与验证边界

行为调度以配置后摇计算回排时刻，行动速度的延迟补正属于未实现能力。移动范围依据地格存在性与曼哈顿距离，路径、阻挡、占用和累计地形成本结算属于算法范围以外的能力。地格技能槽具备查询和发送代码路径，当前静态槽配置为待机；该分支的实际交互核验需要对应槽配置与场景运行。

量表提供通用数值与显示，伤害、治疗、生命状态和死亡规则属于未实现能力。Router 日志覆盖实际进入 Send 且通过请求快照阶段的路由处理，记录在时间轴完成之前形成；配置或机会在发送前被拒绝时由动作结果和 LastError 表达。战局回放、撤回、因果链自动构建和所有游戏数据写入的强制路由均未实现，日志范围见 90。

“已核对”表示解释与所列源码和静态资产一致。编译、测试、游戏播放、字体显示、多分辨率布局和实际交互属于独立运行验证范围。正文中的设计链接提供业务背景，具体实现以源码入口及其当前调用关系为准。
