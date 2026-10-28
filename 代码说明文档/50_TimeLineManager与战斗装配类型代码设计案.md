# TimeLineManager 与战斗装配类型代码设计案

TimeLineManager 是参战单位行动标记与当前机会的权威持有者。BattleTimelineController 把场景角色和配置装配给它，GameManager 负责启动场景加载，DebugPanel 读取调试结果。动作生效与结束由 MetaActionLifecycle 统一执行，时间轴只承接开始、完成或终止的交接，并在成功完成后决定下一行动者。

| 项目 | 内容 |
| --- | --- |
| 解释范围 | Assembly-CSharp，全局命名空间；调度、时机配置、场景控制器、启动与调试相关类及嵌套记录 |
| 源码依据 | TimeLineManager、BattleTimelineController、BattleTimelineConfiguration、BattleBehaviorDefinition、GameManager、DebugPanel |
| 核对基线 | 工程 7362b95addd908be4f96110c2c51ad0300af8e58；2026-10-27；相关脚本与配置无未提交差异 |
| 关联设计 | [时间轴与行动顺序 §3](../系统设计文档/06-战斗/20-时间轴与行动顺序/20_时间轴与行动顺序设计.md)、[架构设计案 §7.12、§9.5](../架构设计文档/架构设计案.md) |
| 状态 | 已核对：结构、源码与静态绑定 |
| 更新日期 | 2026-10-27 |

## 类归属与数据所有权

| 声明类型 | 直接基类或形态 | 持有关系与作用 |
| --- | --- | --- |
| TimeLineManager | 普通 sealed class | 私有 entries 列表持有 Entry，保存 elected、时刻、机会编号及执行锁；无场景生命周期继承 |
| TimeLineManager.Entry | 私有嵌套类 | 保存 TimelineParticipant 引用、配置顺序和当前标记时刻 |
| TimelineParticipant | 普通 sealed class | 初始化输入，引用 UnitId、角色 MetaObjectInstance 和初始时刻；不拥有角色生命周期 |
| TimelineMarker | readonly struct | 返回给表现调用方的标记快照，只有标识、时刻和配置顺序，无对象写入口 |
| BattleTimelineController | MonoBehaviour | 持有 Runtime 时间轴、标识到场景承载的字典、注册时的实例引用和最近动作引用 |
| BattleTimelineController.Binding | 私有嵌套类 | 场景序列化的一条 unitId 与 MetaObjectPreset 引用 |
| BattleTimelineConfiguration | ScriptableObject | 参战单位配置资产，持有 Unit 数组 |
| BattleTimelineConfiguration.Unit | 嵌套 sealed class | 保存 unitId 和 initialTime；GetUnit 返回副本 |
| BattleBehaviorDefinition | ScriptableObject | 行为后摇配置资产，当前移动为 10 游戏秒 |
| ActionTiming | static class | 无实例状态，提供预览与实际受理共用的 NextTime |
| GameManager / DebugPanel | 两个 MonoBehaviour | 前者持有启动场景名和时间轴控制器引用；后者持有角色承载和同一控制器引用，用于显示/调试 |

上述类型均声明于 Assembly-CSharp 全局命名空间，文件在 Battle、Debug 或根目录不改变归属。TimeLineManager 与 MetaActionLifecycle 之间是引用与调用关系，互不继承；控制器持有时间轴，而不是其子类。DebugPanel 的背包/金币等其他调试功能不在本篇覆盖范围。

## 启动及关键方法归属

| 方法实际声明类 | 调用方与下游 | 当前意义 |
| --- | --- | --- |
| GameManager.Start | Unity → SceneManager.LoadSceneAsync → 面板 BindTimeline → TryStartBattle | 加载配置场景、等一帧，注入详情面板的时间轴引用，再开始战斗 |
| BattleTimelineController.TryStartBattle | 启动或外部调用 → 配置 GetUnit、持有组件与技能槽 Prepare、new TimeLineManager、补技能适配器 | 装配校验、建立参战绑定、注入移动与技能选择所需引用 |
| TimeLineManager 构造 / SelectNext / Compare | 构造与成功完成路径 | 校验参战输入，最早时刻优先，同刻按配置顺序 |
| BattleTimelineController.CanControl | 移动控制器、技能适配器 | 把逻辑当前角色、执行锁和场景控制器状态映射成可控判断 |
| TimeLineManager.BeginAction / CompleteAction / AbortAction | MetaActionLifecycle 调用的 internal 方法 | 开始预计算、成功回排或未生效保留机会 |
| TimeLineManager.TryPreview / GetMarkers | 场景控制器 → 调试读取 | 只读预计时刻和当前标记快照 |
| BattleTimelineController.Update / StopBattle / OnDisable | Unity 或外部停止 | 检测对象失效、停止运行并终止登记的移动与技能动作 |
| DebugPanel.DrawTimelineDetails / GetCharacterDetailsText | OnGUI 等显示路径 | 读取控制器文本和角色当前属性；不修改权威标记 |

Start 按 startupScenes 附加加载 01.Field、UI，已加载则跳过，构建清单缺场景时报错并停止后续启动。等待一帧后，它遍历已加载场景中的 UnitDetailsPanel，包括未激活对象，调用 BindTimeline，再尝试启动战斗；面板首次绑定刷新可能仍显示等待机会，运行后的 Update 会读取当前角色。TryStartBattle 要求控制器启用且战斗未在运行，配置与场景绑定数量一致，每个角色活跃、已绑定、有运行实例、移动控制器和有效移动动作；移动持有组件与技能槽组件都会 Prepare，用于已终止动作重建。技能槽不是参战必要条件：没有槽组件的角色仍可只走移动。

装配时，若角色带技能槽组件而场景上还没有 SkillSelectionController，控制器会在该角色 GameObject 上补加这个场景适配器，再把时间轴引用交给移动控制器；移动控制器在绑定时间轴时一并把引用转给技能适配器。因此技能选择适配器属于战斗装配产物，不是常驻场景里的序列化组件，也不改变元对象实例的组件构成。

TimeLineManager 进一步拒绝空列表、空角色、空白/重复标识、重复运行实例，以及非法初始时刻。它把配置顺序保存到 Entry，选取最早标记成为当前行动者（术语表 T-189），写 CurrentTime 并递增 OpportunityId。ElectedObject 是运行角色引用，不由查看、镜头或指针状态改写。

## 一次机会与回排

MetaActionLifecycle.TryExecute 先调用 BeginAction，它校验机会编号，并通过 TryPreview 验证当前角色、执行锁、机会序号上限和后摇，预计算 preparedNext，随后标记 IsExecuting。准备结果尚未写回标记，也未授予下一机会。

生效成功才 CompleteAction：更新 elected 的时刻为 preparedNext，解除执行锁并重新 SelectNext。AbortAction 仅解除执行锁，保留当前角色与机会。Stop 使运行与执行标志失效，ElectedObject 返回空；标记表并不因此清空，只读快照不能当作仍可执行的证明。异常和部分效果的处理见[生命周期执行器](40_MetaActionLifecycle统一执行入口代码设计案.md)。

ActionTiming.NextTime 当前只把非负有限当前时刻与后摇相加，并检查相加溢出。预览和实际开始使用同一方法，不读速度属性、UI、动画或帧时间。等待玩家时不会持续增加时刻。零后摇被接受，同刻优先级可能令同一角色连续获得机会，当前没有自动公平轮换。

## 配置、调试与失效处理

DemoTimeline 的三个标识按 CHAR_PLAYER、CHAR_UNIT_02、CHAR_UNIT_03 排列，初始时刻为 0、1、2。移动或待机成功后当前角色按其动作后摇加时间再重排；两种动作当前都配置 10 游戏秒，例如首个角色从 0 回排至 10，下一个选中时刻 1 的角色。这不是现实等待倒计时，速度属性仍未参与补正。

控制器 Update 检查每个登记承载仍活跃、绑定且运行实例与注册时相同；销毁、禁用、解绑或重建导致停止。StopBattle 调用 Runtime.Stop，终止已登记实例的移动动作与技能槽动作，并清理移动与技能选择。控制器 OnDisable 同样停止。成功完成动作后 NotifyActionFinished 保存最近动作并清理旧选择；这是结果通知，回排已由生命周期交接执行。内部方法仍名为 CancelPointers，但实际调用各角色的 CancelMovementSelection 与技能适配器的 CancelSelection，同时清指针、覆盖层与范围缓存，不只取消鼠标按压。

GetDebugText 显示时刻、机会、行动者、当前标记与移动预览；该预览只按当前行动者移动动作的后摇计算，不反映待机或选中槽位的后摇。GetMarkers 只返回每单位当前标记，不模拟未来多轮。调试按钮调用 TryDebugMoveCurrent，按右、上、左、下寻找一个相邻可选格并走真实移动动作。最近动作只在成功通知后更新，不是全部失败请求的历史。

DebugPanel 在发现启用的 UnitDetailsPanel 时隐藏旧 IMGUI 属性详情，并根据面板高度和 Canvas 缩放调整调试区缩放及点击遮挡范围；未发现启用面板时保留原详情与缩放。面板显示的当前角色属性、移动按钮与技能按钮由[UnitDetailsPanel](70_UnitDetailsPanel与移动选择界面代码设计案.md)负责，调试时间轴仍由 DebugPanel 读取。该适配依赖面板具有 RectTransform 和父级 Canvas，不能理解成任意装配都可安全显示。

## 实现定位与差异

| 类型组 | 源码与配置 |
| --- | --- |
| 调度及记录 | [TimeLineManager.cs](D:/myspace/Git/mygame/Assets/Script/Battle/TimeLineManager.cs) |
| 场景装配 | [BattleTimelineController.cs](D:/myspace/Git/mygame/Assets/Script/Battle/BattleTimelineController.cs)、[PersistanceScene.unity](D:/myspace/Git/mygame/Assets/Scenes/PersistanceScene.unity) |
| 选择适配 | [SkillSelectionController.cs](D:/myspace/Git/mygame/Assets/Script/Player/SkillSelectionController.cs)、[BasicSkillSlotsComponent.cs](D:/myspace/Git/mygame/Assets/Script/MetaObjects/BasicSkillSlotsComponent.cs) |
| 初始配置 | [BattleTimelineConfiguration.cs](D:/myspace/Git/mygame/Assets/Script/Battle/BattleTimelineConfiguration.cs)、[DemoTimeline.asset](D:/myspace/Git/mygame/Assets/GameData/Battle/DemoTimeline.asset) |
| 时机规则 | [BattleBehaviorDefinition.cs](D:/myspace/Git/mygame/Assets/Script/Battle/BattleBehaviorDefinition.cs)、[MovementTiming.asset](D:/myspace/Git/mygame/Assets/GameData/Battle/MovementTiming.asset)、[WaitTiming.asset](D:/myspace/Git/mygame/Assets/GameData/Battle/WaitTiming.asset) |
| 启动与调试 | [GameManager.cs](D:/myspace/Git/mygame/Assets/Script/GameManager.cs)、[DebugPanel.cs](D:/myspace/Git/mygame/Assets/Script/Debug/DebugPanel.cs)、[EditorBuildSettings.asset](D:/myspace/Git/mygame/ProjectSettings/EditorBuildSettings.asset) |

三角色定义和绑定已静态核对，构建清单登记常驻场景、地图和 UI；本轮未播放或构建验证。当前 AI、完整技能后摇与速度补正、增援、失能恢复、战斗轮次存档和世界时间结算尚未由本链实现。待机的后摇虽已接入回排，但“技能后摇 + 行动速度补正”的完整规则仍未成立，两个动作都使用固定值。实际控制器直接装配和交接，不能据此宣称架构全部战斗编排及公共基础设施已经落实。
