# MetaAction 派生类型与动作构造代码设计案

元动作使用定义资产创建独立动作实例。动作实例持有一个效果报文构造器和自己的执行生命周期；构造器保存技能参数并生成报文，角色侧槽位补齐来源与实际目标，场景 Router 调用共享执行器完成效果。移动与待机采用相同的构造和发送路径。

| 项目 | 内容 |
| --- | --- |
| 解释范围 | Assembly-CSharp，全局命名空间；MetaActionDefinition、MetaActionInstance、MetaActionComponent、ActionPacketBuilder 及移动/待机构造器、ActionExecutionContext 与 ActionResult |
| 源码依据 | MetaActionDefinition.CreateRuntime；MetaActionInstance.ValidateDefinition/BuildPacket/TryQueryTargets/ExecutePacket；ActionPacketBuilder.Build/Validate；文件入口见文末实现定位 |
| 核对基线 | 工程提交 `65c2ff5e40cec060988b74091e189e09fdaa9e13`；2026-10-29 核对时工程工作区干净 |
| 关联设计 | [元动作 §4.3、§4.4](../系统设计文档/01-通用系统/70-元动作/70_元动作设计补充说明.md) |
| 状态 | 已核对：源码声明、调用链与静态资产绑定 |
| 更新日期 | 2026-10-29 |

## 派生关系与作用域

```mermaid
classDiagram
  MetaObjectDefinition <|-- MetaActionDefinition
  MetaObjectInstance <|-- MetaActionInstance
  MetaObjectComponent <|-- MetaActionComponent
  MetaActionComponent <|-- ActionPacketBuilder
  ActionPacketBuilder <|-- MovementPacketBuilder
  ActionPacketBuilder <|-- WaitPacketBuilder
  MetaObjectComponentDefinition <|-- MetaActionComponentDefinition
  MetaActionComponentDefinition <|-- ActionPacketBuilderDefinition
  ActionPacketBuilderDefinition <|-- MovementPacketBuilderDefinition
  ActionPacketBuilderDefinition <|-- WaitPacketBuilderDefinition
  MetaActionInstance *-- MetaActionLifecycle : 每动作独占
  MetaActionInstance *-- ActionPacketBuilder : 组件字典
  ActionPacketBuilderDefinition --> BattleBehaviorDefinition : 后摇资产引用
```

类型均属于 Assembly-CSharp，全局命名空间。MetaActionDefinition 继承并使用 MetaObjectDefinition.CreateInstance，重写 CreateRuntime 返回 MetaActionInstance，IsActionDefinition 为 true。MetaActionComponentDefinition 的 IsActionComponent 重写固定为 true，底座据此核对配置侧归属。

MetaActionInstance 是角色动作容器持有的普通 C# 实例；ActionPacketBuilder 是其中的普通 C# 组件。ActionEffectExecutor 则继承 MonoBehaviour，挂在 Router GameObject 上，其主要结构见 [90 Router 专题](90_ActionRouterManager与键值报文执行代码设计案.md)。每个角色每个槽持有自己的构造器和生命周期，场景内同种操作使用唯一匹配的执行器。

## 技能参数与构造器

ActionPacketBuilderDefinition 保存 targetKind 与 timing 引用；创建时传给对应运行构造器。ActionPacketBuilder.Recovery 从 BattleBehaviorDefinition 读取 double 后摇，Build 生成 Ordinal 字符串键字典，包含 operation、targetKind 和 recovery。构造发生在确认执行后的发送阶段；界面查询与目标预览读取动作属性。

| 构造器 | operation | targetKind | 当前配置 |
| --- | --- | --- | --- |
| MovementPacketBuilder | Movement | Cell | MovementAction 引用 MovementTiming，后摇 10 游戏秒 |
| WaitPacketBuilder | Wait | None | WaitAction 引用 WaitTiming，后摇 10 游戏秒 |

Validate 通过 ActionTiming.NextTime 检查后摇配置存在、有限、非负且可计算，并检查指向性枚举有效。具体构造器还要求各自的指向性匹配。目标配置与后摇配置都属于构造器的技能参数，来源和实际目标由槽位补齐。

## 动作实例的查询与校验

`ValidateDefinition` 要求动作有效、恰好一个 ActionPacketBuilder 且 ComponentCount 为 1，再调用构造器 Validate。缺少构造器或组件构成不符时返回错误。CapabilityId 读取构造器 Operation，TargetKind 与 Recovery 读取构造器参数；BuildPacket 先校验再调用 Build。

`TryQueryTargets` 面向地格动作，要求动作有效、定义有效、指向性为 Cell，且移动能力有效，再调用 IMovementCapability.TryGetTargets。能力接口提供 IsValid、TryGetTargets、Validate；其场景实现由 CharacterMovementController 提供，用于目标查询与提交时校验。位置写入发生在 MovementEffectExecutor。

## 上下文、发送与执行结果

ActionExecutionContext 是同步调用使用的普通对象，保存 Actor、OpportunityId、Destination、Movement、Timeline 和 Router 引用。槽位核对 Actor 为自身 Owner，将这些本局引用转换为报文的运行标识与基础值。上下文的场景引用留在调用层与 Router 的来源登记中。

移动容器继承的 TryExecute、基础技能槽的 TryExecute 都调用 ActionPacketOutlet.Send；发送出口调用 BuildPacket 并补齐上下文，然后调用 MetaActionInstance.ExecutePacket。该内部入口读取报文 double recovery，核对动作与行动者有效，并在绑定时间轴时核对当前行动者、执行锁和机会编号，再将发送委托交给自身生命周期。

生命周期仅将 ActionResult.Succeeded 视为效果成功。执行器成功且生命周期完成，动作返回 Succeeded；执行器成功但生命周期因执行期间终止而未完成时，动作返回 Rejected。LastError 从生命周期读取。配置或 Router 缺失等入口问题通过 Reject 登记动作错误，具体字段和日志覆盖见 Router 专题。

| ActionResult | 当前语义 |
| --- | --- |
| None | 默认结果值 |
| Succeeded | 效果成功并由调用链确认完成 |
| NoChange | 目的格等于当前位置 |
| NotReady | 动作、来源、能力、配置或执行器就绪条件缺失 |
| InvalidTarget | 报文指向性、地格格式或地图目标校验失败 |
| OutOfRange | 目标超出当前查询范围 |
| OutOfTurn | 当前行动者、机会编号或执行锁条件不符 |
| Rejected | 受理或完成条件拒绝 |
| Failed | Router 捕获执行异常时写入结果日志的状态；异常向上传播 |

Terminate 调用 Dispose，标记动作终止、终止自身生命周期并释放组件。容器 Prepare 可以根据定义创建新的有效动作实例。生命周期的阶段和异常处理详见 [40 生命周期专题](40_MetaActionLifecycle统一执行入口代码设计案.md)。

## 动作寿命与效果能力范围

Completed 与 Rejected 动作可以在有效条件下再次受理，容器持有构造器和生命周期直到终止、解绑或卸载。设计背景中的一次性即时效果实例、元持续效果的挂载与存续管理，以及技能成本和冷却属于未实现能力；当前动作执行集合为移动与待机。

## 实现定位

| 源码或资产 | 主要定位 |
| --- | --- |
| [MetaActionDefinition.cs](D:/myspace/Git/mygame/Assets/Script/Battle/MetaActionDefinition.cs) | 动作定义与运行工厂重写 |
| [MetaActionInstance.cs](D:/myspace/Git/mygame/Assets/Script/Battle/MetaActionInstance.cs) | 动作组件校验、参数查询、ExecutePacket、Dispose |
| [MetaActionComponents.cs](D:/myspace/Git/mygame/Assets/Script/Battle/MetaActionComponents.cs) | 基类、接口、上下文与枚举 |
| [ActionPacketBuilders.cs](D:/myspace/Git/mygame/Assets/Script/Battle/ActionPacketBuilders.cs) | 构造器配置、Build、Validate |
| [ActionPackets.cs](D:/myspace/Git/mygame/Assets/Script/Battle/ActionPackets.cs) | ActionPacketOutlet.Send 与字段常量 |
| [MovementAction.asset](D:/myspace/Git/mygame/Assets/GameData/Battle/MovementAction.asset) | MovementPacketBuilderDefinition 的单项组件配置 |
| [WaitAction.asset](D:/myspace/Git/mygame/Assets/GameData/Battle/WaitAction.asset) | WaitPacketBuilderDefinition 的单项组件配置 |

核对依据为上述提交的源码、工程配置与静态资产。文档状态表示所述实现已完成对照；编译、播放、画面与交互的运行验证属于独立验证范围。
