# TimeLineManager 与战斗装配类型代码设计案

TimeLineManager 保存全体参战者的行动标记，选取最早标记授予行动机会；动作生命周期成功完成后，将行动者标记按固定后摇回排。BattleTimelineController 负责把配置、场景角色、Router 和输入适配器装配到这份权威运行状态上，GameManager 负责加载地图与界面并启动战斗。

| 项目 | 内容 |
| --- | --- |
| 解释范围 | Assembly-CSharp，全局命名空间；TimeLineManager、TimelineParticipant/Marker、BattleTimelineConfiguration、BattleBehaviorDefinition、ActionTiming、BattleTimelineController、GameManager 与相机跟随 |
| 源码依据 | TimeLineManager 构造、BeginAction/CompleteAction/TryPreview；BattleTimelineController.TryStartBattle/StopBattle；GameManager.Start；CurrentActorCameraFollow.LateUpdate；文件入口见文末实现定位 |
| 核对基线 | 工程提交 `bf1b4d8caf90a8d6e10de503f1e682b96bb3b936`；2026-10-30 核对源码与静态资产 |
| 关联设计 | [时间轴与行动顺序 §3](../系统设计文档/06-战斗/20-时间轴与行动顺序/20_时间轴与行动顺序设计.md)、[架构设计案 §7.12、§9.5](../架构设计文档/架构设计案.md) |
| 状态 | 已核对：源码声明、调用链与静态资产绑定 |
| 更新日期 | 2026-10-30 |

## 归属、数据与配置

TimeLineManager 是普通 C# sealed 类，BattleTimelineController 是持有 Runtime 的 MonoBehaviour，GameManager 是启动协程的场景组件，均归 Assembly-CSharp。BattleTimelineConfiguration 与 BattleBehaviorDefinition 继承 ScriptableObject，分别提供参战初值和行为后摇。ActionTiming 是静态计算类。

TimelineParticipant 保存参战 ID、MetaObjectInstance 和初始时刻；Manager 私有 Entry 另存配置顺序与当前标记时刻。TimelineMarker 是只读表现快照，GetMarkers 生成按时刻及配置顺序排序的只读集合。

DemoTimeline 配置 CHAR_PLAYER、CHAR_UNIT_02、CHAR_UNIT_03，初始时刻分别为 0、1、2。MovementTiming 与 WaitTiming 的后摇均为 10 游戏秒。构造器将 timing.Recovery 写入报文，生命周期将该值交给时间轴。

## 排序、预览与回排

TimeLineManager 构造时按配置顺序登记参战实例与初始时刻。SelectNext 选取最早标记，将 CurrentTime 定为该时刻，OpportunityId 增加一次。同刻按初始化配置顺序确定优先级。

TryPreview 通过 CanAct 判断当前角色及执行占用，使用 ActionTiming.NextTime 计算“CurrentTime + recovery”。预览与实际回排共用相加公式。0 后摇对应当前时刻；同刻优先级保持配置顺序，因此同一单位可能连续取得机会。

BeginAction 核对机会编号及 CanAct，受理时计算 preparedNext、设置 IsExecuting 并返回 Succeeded；机会不符返回 OutOfTurn。CompleteAction 将行动者标记提交为 preparedNext，解锁后重新 SelectNext。AbortAction 释放执行锁，当前标记和机会保持。Stop 将 IsRunning、IsExecuting 置 false，内部标记可供快照读取。固定后摇计算以行为配置为输入，属性中的行动速度由属性与显示链路读取。

## 战斗启动与场景接线

GameManager.Start 顺序读取 startupScenes：已加载则继续，其余以 Additive 方式等待加载。加载完成后等待一帧，给全部 UnitDetailsPanel 调用 BindTimeline，再调用 TryStartBattle。EditorBuildSettings 启用 PersistanceScene、01.Field 和 UI。

BattleTimelineController.TryStartBattle 在自身启用、Runtime 尚未运行时启动。它按 Binding 建立角色映射，依参战配置取得场景角色，调用移动容器及技能槽 Prepare，创建 TimelineParticipant 清单并建立 TimeLineManager。

装配成功后保存场景角色和登记实例映射，清空 Router 的来源绑定；对带基础槽的角色按需添加 SkillSelectionController，再通过 CharacterMovementController.BindTimeline 绑定移动与技能适配器。来源运行实例及其移动能力在槽位确认发送时由 ActionPacketOutlet.Send 调用 ActionRouterManager.RegisterActor 登记到 Router。最后清理指针和选择并返回成功。装配中的配置访问和创建异常沿调用栈传播。

PersistanceScene 中 BattleTimelineController.actionRouter 引用 ActionRouter 上的 Manager；同物体有启用的移动和待机执行器。此配置提供按 operation 分发的实际落点，字段与结果见 [90 Router 专题](90_ActionRouterManager与键值报文执行代码设计案.md)。

## 执行结束、停止与失效

CanControl 同时要求 Controller 启用、Runtime 运行且解锁、传入角色为当前行动者。NotifyActionFinished 保存最近动作及其错误信息，动作 Completed 时清理全部角色的移动和技能选择；时间轴回排已经由动作生命周期完成。

Update 检查每个参战承载继续启用、已绑定、实例有效，并与启动登记的实例相同。承载失效或实例重建会 StopBattle。StopBattle 停止 Runtime，终止登记实例持有的移动动作和四槽动作，清空 Router 来源绑定并取消选择。OnDisable 调用相同停止入口。Router 的记录序列与文件路径按其自身实例生命周期保存。

调试移动按右、上、左、下顺序寻找范围内邻格，然后调用角色的真实 TryMoveToCell。TryPreviewMovement 读取当前角色移动动作后摇形成预览。DebugPanel 展示调试文字与该移动入口，业务推进仍由完整动作链路完成。

## 当前行动者的相机表现

CurrentActorCameraFollow 继承 MonoBehaviour，在 LateUpdate 读取 timeline.CurrentActor，将同一虚拟相机的 Follow 与 LookAt 指向行动者 Transform。它保持虚拟相机实例和既有取景约束，执行顺序为 -100。

CinemachinePlanarFollow 继承 CinemachineExtension。播放态接管 FramingTransposer 的 XY 阻尼与死区，保存其配置并将原项置零；Finalize 阶段在构图和 Confiner 得到目标位置后，对整个位移向量使用统一阻尼，再写入 PositionCorrection。启用时初始化平滑状态，禁用或销毁时恢复保存的 Framing 设置。相机状态属于表现数据，行动者身份和标记时刻由 Runtime 提供。

## 实现定位

| 源码或资产 | 主要定位 |
| --- | --- |
| [TimeLineManager.cs](D:/myspace/Git/mygame/Assets/Script/Battle/TimeLineManager.cs) | Participant、Marker、权威标记与调度入口 |
| [BattleTimelineController.cs](D:/myspace/Git/mygame/Assets/Script/Battle/BattleTimelineController.cs) | TryStartBattle、CanControl、停止与失效检查 |
| [BattleTimelineConfiguration.cs](D:/myspace/Git/mygame/Assets/Script/Battle/BattleTimelineConfiguration.cs) | 参战配置与复制读取 |
| [BattleBehaviorDefinition.cs](D:/myspace/Git/mygame/Assets/Script/Battle/BattleBehaviorDefinition.cs) | 行为配置与 ActionTiming.NextTime |
| [GameManager.cs](D:/myspace/Git/mygame/Assets/Script/GameManager.cs) | Start 场景加载与启动编排 |
| [CurrentActorCameraFollow.cs](D:/myspace/Git/mygame/Assets/Script/Battle/CurrentActorCameraFollow.cs) | 当前行动者跟随目标 |
| [CinemachinePlanarFollow.cs](D:/myspace/Git/mygame/Assets/Script/Battle/CinemachinePlanarFollow.cs) | 相机位置缓动与设置恢复 |
| [DebugPanel.cs](D:/myspace/Git/mygame/Assets/Script/Debug/DebugPanel.cs) | 时间轴文字与调试移动入口 |
| [DemoTimeline.asset](D:/myspace/Git/mygame/Assets/GameData/Battle/DemoTimeline.asset) | 三名参战者与初始时刻 |
| [MovementTiming.asset](D:/myspace/Git/mygame/Assets/GameData/Battle/MovementTiming.asset) | 移动后摇 |
| [WaitTiming.asset](D:/myspace/Git/mygame/Assets/GameData/Battle/WaitTiming.asset) | 待机后摇 |
| [PersistanceScene.unity](D:/myspace/Git/mygame/Assets/Scenes/PersistanceScene.unity) | Controller、角色、Router 与相机引用 |
| [EditorBuildSettings.asset](D:/myspace/Git/mygame/ProjectSettings/EditorBuildSettings.asset) | 启动场景清单 |

核对依据为上述提交的源码、工程配置与静态资产。文档状态表示所述实现已完成对照；编译、播放、画面与交互的运行验证属于独立验证范围。
