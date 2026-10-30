# ActionRouterManager 与键值报文执行代码设计案

动作报文把技能参数、来源和目标组合为按需填写的键值主体。角色持有的构造器生成技能参数，移动容器和基础技能槽通过共享发送出口补齐上下文；ActionRouterManager 接收请求容器副本，按 operation 调用同物体上的效果执行器，并保存请求与执行结果。当前落地操作为移动与待机。

| 项目 | 内容 |
| --- | --- |
| 解释范围 | Assembly-CSharp，全局命名空间；ActionPacket、ActionPacketOutlet、ActionPacketRecord、ActionRouterManager、ActionEffectExecutor 及移动/待机执行器；报文字段、路由、日志与异常边界 |
| 源码依据 | ActionPacket.Snapshot/Get/Cell/GetCell；ActionPacketOutlet.Send；ActionRouterManager.Send/RegisterActor/ResolveActor；ActionEffectExecutor.Execute；文件入口见文末实现定位 |
| 核对基线 | 工程提交 `bf1b4d8caf90a8d6e10de503f1e682b96bb3b936`；2026-10-30 核对源码与静态资产 |
| 关联设计 | [架构设计案](../架构设计文档/架构设计案.md)；业务背景与职责约束以设计文档为准，实现行为以本文源码依据为准 |
| 状态 | 已核对：源码声明、调用链与静态资产绑定 |
| 更新日期 | 2026-10-30 |

## 类型归属与持有关系

| 类型 | 直接基类或形态 | 作用域与责任 |
| --- | --- | --- |
| ActionPacket | 静态类 | 字段常量、容器复制、字段读取和地格编码 |
| ActionPacketOutlet | internal 静态类 | 两类槽位共用发送步骤，组装上下文并调用动作生命周期 |
| ActionPacketRecord | sealed 普通类 | 记录号 Id、只读 Request 与 Result |
| ActionRouterManager | MonoBehaviour | 来源绑定表、记录列表、操作分发和文件写入 |
| ActionEffectExecutor | 抽象 MonoBehaviour | Operation 与 Execute 的共享执行约定 |
| MovementEffectExecutor / WaitEffectExecutor / FixedDamageEffectExecutor | ActionEffectExecutor | 分别执行地格移动、待机与固定伤害 |

上述类型均属于 Assembly-CSharp，全局命名空间，工程引用 Newtonsoft.Json 支持日志序列化。ActionRouterManager 在 OnEnable 将自身登记为静态 Instance。OnDisable 清空来源绑定并解除自身 Instance。DisallowMultipleComponent 限制同物体组件重复。

PersistanceScene 的 ActionRouter 根物体挂 Manager、MovementEffectExecutor、WaitEffectExecutor、FixedDamageEffectExecutor，四者启用；BattleTimelineController.actionRouter 引用此 Manager。Manager 每次 Send 查询同 GameObject 上启用的 ActionEffectExecutor，选取首个 operation 精确匹配的组件。请求数据与结果缓冲由每次调用持有，执行器以调用参数处理当次效果。

## 报文主体与字段责任

报文构造阶段使用 `Dictionary<string, object>`；进入 Router 时 Snapshot 将键值复制到 Ordinal 字符串键的只读字典。字段值的构造与所有权归发送方，复制范围是字典容器。当前 Movement、Wait 与 FixedDamage 构造链写入文本、整数与 double 等基础值。

| 键 | 当前写入值类型与含义 | 写入方 |
| --- | --- | --- |
| operation | string：Movement、Wait 或 FixedDamage | 构造器 |
| targetKind | string：Cell、None 或 Object | 构造器 |
| recovery | double：后摇游戏秒 | 构造器，从 timing 读取 |
| source | string：角色 RuntimeId | 槽位发送出口 |
| sourceDefinition | string：角色 MetaObjectId | 槽位发送出口 |
| action | string：所选动作 RuntimeId | 槽位发送出口 |
| actionDefinition | string：动作 MetaObjectId | 槽位发送出口 |
| opportunity | long：当前上下文机会编号 | 槽位发送出口 |
| slot | string：Movement 或基础槽零基索引 0—3 | 槽位发送出口 |
| target | string：Cell 为不变区域 x,y；Object 为目标 RuntimeId | 槽位发送出口填写并登记对象目标 |
| cause | 已声明的字段常量 | 当前移动和待机入口的自动填充范围以本表其余项为准 |

None 动作省略 target。报文按实际需要携带字段，Snapshot 保留输入键值；Router 读取 operation，具体执行器读取各自参数。`ActionPacket.Get<T>` 通过字典索引与类型转换取得必填字段，装箱值按调用约定使用，例如 recovery 使用 double。`GetCell` 按逗号分隔 target，再通过 int.Parse 取得地格坐标。

ActionExecutionContext 保存本局引用，角色与动作 RuntimeId 由 Guid 生成；MetaObjectId 表示定义。来源绑定表将 source 解析为运行实例，当前 target 的业务含义是地格坐标。记录号 Id 由 Router 分配，处于 ActionPacketRecord 外层。

## 构造、补齐与发送

1. 移动容器或基础槽选择自身动作，传入 slot 标识调用 ActionPacketOutlet.Send。共享出口核对 Owner 与 context.Actor 的实例身份，不匹配时返回 NotReady。
2. 出口优先使用 context.Router，否则取 ActionRouterManager.Instance，调用 BuildPacket 取得技能参数。
3. 出口按上下文写入来源、动作、定义、机会和槽号；Cell 动作编码地格，Object 动作写入并登记目标 RuntimeId，None 动作省略 target。RegisterActor 登记角色与移动能力，非空能力更新绑定，空能力保持已有绑定。
4. MetaActionInstance.ExecutePacket 读取 double recovery，通过生命周期调用时间轴 BeginAction，受理后由生效委托调用 Router.Send。
5. Router 记录执行结果并返回；生命周期根据执行结果和当前相态完成回排或保留机会，选择适配器在整体成功后清理选择。

Router 的 Send 负责请求复制、操作分发和执行结果记录。机会编号、当前行动者与执行占用由 TimeLineManager 判断，动作实例与生命周期负责受理结果和完成交接。实际业务调用沿上述链路取得行动受理与回排行为。

## Router 受理与执行

Send 先完成 Request 容器复制，分配递增记录号和结果字典。在 try 中读取 operation，查询同 GameObject 的启用执行器，以 Ordinal 比较操作名并取首个匹配项，直接调用 Execute。调用约定为每种操作配置对应执行器。字段访问、类型转换和路由查询的开发错误通过实际操作的异常暴露。

执行器正常返回时，Router 保留其 ActionResult；try 内出现异常时，将 status 置 Failed，写入 error 与 exception 类型名，并在记录后重新抛出。

ResolveActor 和 ResolveMovement 使用 source 取得绑定表中的角色及移动能力。ClearBindings 在战斗开始、停止和 Manager 禁用时清理来源映射；Records、序号和文件路径由 Router 实例持有。移动能力负责当前角色绑定和实例身份的业务就绪判定。

MovementEffectExecutor 通过 GetCell 取得目的格，再调用已登记移动能力的 Validate。业务拒绝直接返回对应结果；成功受理后取得坐标组件并记录 before，调用 MoveToCell，在提交的 finally 中记录实际 after。主动移动通知驱动朝向，范围与目标规则见 [60 移动专题](60_地图与移动适配类型代码设计案.md)。

WaitEffectExecutor 接收 Router 分发的 Wait 操作并返回 Succeeded。生命周期按 recovery 完成行动和回排。

## 结果快照与文件日志

Router 在 finally 给结果写入 status 字符串，生成 ActionPacketRecord，Request 与 Result 均为只读字典容器副本，先加入内存 Records。启用 writeLogFile 时，首次记录按工程根目录与 logDirectory 解析目录，创建 UTC 时间加 Guid 命名的 .jsonl 文件，每次以 Newtonsoft.Json 将记录追加一行；LogPath 提供当前文件路径。

结果字段按实际执行情况出现：status 表示路由执行结果；error、exception 表示路由错误或异常；移动的 before、after 保存坐标字符串。发送者在 Send 返回后增删或替换输入字典的条目时，已保存 Request 保持复制时的条目值；引用类型字段的内容与所有权由发送方管理。

| 记录边界 | 当前行为及其影响 |
| --- | --- |
| Request 容器复制过程中抛异常 | 发生在记录号分配与记录 finally 以前，Records 保持当前集合 |
| 槽位身份、动作相态或机会在 Send 前拒绝 | 由对应动作结果表达，Router 从实际 Send 开始记录 |
| 路由操作异常或执行器返回业务拒绝 | try 内异常记为 Failed 并重新抛出；业务拒绝按执行器结果记入 Records，文件写入受 writeLogFile 配置控制 |
| 执行器成功后的时间轴完成 | Router 结果先形成，CompleteAction 随后发生；完整动作阶段从生命周期读取 |
| 文件目录创建或追加失败 | 内存记录已经加入，文件异常向上传播，生命周期转 Failed 并停止时间轴 |
| 效果提交期间异常 | 已发生的状态变化保留，记录体现可取得的结果，时间轴停止授予后续机会 |

## 能力范围与后续核验条件

当前记录为“请求 + 执行器结果”，服务于移动、待机和固定伤害的观察和追溯。角色初始化、属性修正、量表 Modify、普通 SetCell 和显示修改具有各自公开入口，记录覆盖以实际进入 Router.Send 的调用为界。全局所有数据写入的强制报文约束属于未实现能力。

伤害结算与类型反应、反伤因果链自动填充、战局快照恢复、日志读取回放、跨局运行 ID 恢复映射、行动撤回和事务回滚均未实现。cause 字段常量提供名称，完整因果关系需要实际生产与消费流程作为依据。回放或撤回的效果应通过相应实现和运行验证确认。

Router 日志写入与异常收束的实际运行核验需要启用场景、发送有效及拒绝报文，并观察内存、文件和动作阶段；本文依据源码说明当前控制流与静态接线。

## 实现定位

| 源码或资产 | 主要定位 |
| --- | --- |
| [ActionPackets.cs](D:/myspace/Git/mygame/Assets/Script/Battle/ActionPackets.cs) | 字段、Snapshot、Get/GetCell、Record 与发送出口 |
| [ActionPacketBuilders.cs](D:/myspace/Git/mygame/Assets/Script/Battle/ActionPacketBuilders.cs) | Movement/Wait 参数构造 |
| [ActionRouterManager.cs](D:/myspace/Git/mygame/Assets/Script/Battle/ActionRouterManager.cs) | Send、登记解析、记录与 JSONL |
| [ActionEffectExecutor.cs](D:/myspace/Git/mygame/Assets/Script/Battle/ActionEffectExecutor.cs) | Operation、Execute 抽象入口 |
| [MovementEffectExecutor.cs](D:/myspace/Git/mygame/Assets/Script/Battle/MovementEffectExecutor.cs) | 目的格解析、校验、提交、before/after |
| [WaitEffectExecutor.cs](D:/myspace/Git/mygame/Assets/Script/Battle/WaitEffectExecutor.cs) | 待机成功结果 |
| [MetaActionInstance.cs](D:/myspace/Git/mygame/Assets/Script/Battle/MetaActionInstance.cs) | ExecutePacket 的后摇读取与生命周期调用 |
| [MetaActionLifecycle.cs](D:/myspace/Git/mygame/Assets/Script/Battle/MetaActionLifecycle.cs) | 成功回排与异常停止 |
| [MetaObjectInstance.cs](D:/myspace/Git/mygame/Assets/Script/MetaObjects/MetaObjectInstance.cs) | 定义 ID 与 RuntimeId |
| [PersistanceScene.unity](D:/myspace/Git/mygame/Assets/Scenes/PersistanceScene.unity) | ActionRouter 三组件、日志配置与 Controller 引用 |
| [Assembly-CSharp.csproj](D:/myspace/Git/mygame/Assembly-CSharp.csproj) | 类型编译归属与 Newtonsoft.Json 引用 |

核对依据为上述提交的源码、工程配置与静态资产。文档状态表示所述实现已完成对照；编译、播放、画面与交互的运行验证属于独立验证范围。


对象目标的 ResolveTarget、damage/range 业务参数及 healthBefore/healthAfter/appliedDamage 结果字段见 [95 对象指向与固定伤害](95_对象指向与固定伤害代码设计案.md)。
