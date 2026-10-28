# ActionRouterManager 与键值报文执行代码设计案

动作报文把技能参数、来源和目标组合为按需填写的键值主体。角色持有的构造器生成技能参数，移动容器和基础技能槽通过共享发送出口补齐上下文；ActionRouterManager 接收基础值快照，按 operation 调用同物体上的效果执行器，并保存请求与执行结果。当前落地操作为移动与待机。

| 项目 | 内容 |
| --- | --- |
| 解释范围 | Assembly-CSharp，全局命名空间；ActionPacket、ActionPacketOutlet、ActionPacketRecord、ActionRouterManager、ActionEffectExecutor 及移动/待机执行器；报文字段、路由、日志与异常边界 |
| 源码依据 | ActionPacket.Snapshot/Read/Cell/ReadCell；ActionPacketOutlet.Send；ActionRouterManager.Send/RegisterActor/ResolveActor；ActionEffectExecutor.Execute；文件入口见文末实现定位 |
| 核对基线 | 工程提交 `65c2ff5e40cec060988b74091e189e09fdaa9e13`；2026-10-29 核对时工程工作区干净 |
| 关联设计 | [架构设计案](../架构设计文档/架构设计案.md)；业务背景与职责约束以设计文档为准，实现行为以本文源码依据为准 |
| 状态 | 已核对：源码声明、调用链与静态资产绑定 |
| 更新日期 | 2026-10-29 |

## 类型归属与持有关系

| 类型 | 直接基类或形态 | 作用域与责任 |
| --- | --- | --- |
| ActionPacket | 静态类 | 字段常量、基础值快照、类型读取和地格编码 |
| ActionPacketOutlet | internal 静态类 | 两类槽位共用发送步骤，组装上下文并调用动作生命周期 |
| ActionPacketRecord | sealed 普通类 | 记录号 Id、只读 Request 与 Result |
| ActionRouterManager | MonoBehaviour | 来源绑定表、记录列表、操作分发和文件写入 |
| ActionEffectExecutor | 抽象 MonoBehaviour | Operation 与 Execute 的共享执行约定 |
| MovementEffectExecutor / WaitEffectExecutor | ActionEffectExecutor | 分别执行地格移动和待机 |

上述类型均属于 Assembly-CSharp，全局命名空间，工程引用 Newtonsoft.Json 支持日志序列化。ActionRouterManager 在 OnEnable 建立静态 Instance；场景已经存在另一实例时禁用自身并报告错误。OnDisable 清空来源绑定并解除自身 Instance。DisallowMultipleComponent 限制同物体组件重复。

PersistanceScene 的 ActionRouter 根物体挂 Manager、MovementEffectExecutor、WaitEffectExecutor，三者启用；BattleTimelineController.actionRouter 引用此 Manager。Manager 每次 Send 查询同 GameObject 上启用的 ActionEffectExecutor，要求 operation 精确匹配的组件恰好一个。请求数据与结果缓冲由每次调用持有，执行器以调用参数处理当次效果。

## 报文主体与字段责任

报文构造阶段使用 `Dictionary<string, object>`；进入 Router 时 Snapshot 复制为只读字典。字段名采用 Ordinal 比较，大小写参与匹配。Snapshot 接受 null、string、bool、int、long、有限 float 与 double；空白键、非有限数值和其他对象类型抛 ArgumentException。场景对象与可变集合通过运行 ID 或基础值表示。

| 键 | 当前写入值类型与含义 | 写入方 |
| --- | --- | --- |
| operation | string：Movement 或 Wait | 构造器 |
| targetKind | string：Cell 或 None | 构造器 |
| recovery | double：非负有限游戏秒 | 构造器，从 timing 读取 |
| source | string：角色 RuntimeId | 槽位发送出口 |
| sourceDefinition | string：角色 MetaObjectId | 槽位发送出口 |
| action | string：所选动作 RuntimeId | 槽位发送出口 |
| actionDefinition | string：动作 MetaObjectId | 槽位发送出口 |
| opportunity | long：当前上下文机会编号 | 槽位发送出口 |
| slot | string：Movement 或基础槽零基索引 0—3 | 槽位发送出口 |
| target | string：以不变区域格式编码的 x,y | Cell 动作由槽位发送出口填写 |
| cause | 已声明的字段常量 | 当前移动和待机入口的自动填充范围以本表其余项为准 |

None 动作省略 target。报文按实际需要带字段，Snapshot 保留所有满足基础值规则的键值；Router 只读取自身路由字段，具体执行器读取各自参数。新增基础值字段可以随请求记录保留。ActionPacket.Read<T> 使用实际装箱类型匹配，例如 double 与 int 各自独立；文件读取后的数值转换需由相应读取流程处理。

ActionExecutionContext 保存本局引用，角色与动作 RuntimeId 由 Guid 生成；MetaObjectId 表示定义。来源绑定表将 source 解析为运行实例，当前 target 的业务含义是地格坐标。记录号 Id 由 Router 分配，处于 ActionPacketRecord 外层。

## 构造、补齐与发送

1. 移动容器或基础槽核对 Owner 与 context.Actor 的实例身份，选择自身动作，并传入 slot 标识调用 ActionPacketOutlet.Send。
2. 出口优先使用 context.Router，否则取 ActionRouterManager.Instance，要求其启用；校验动作定义并调用 BuildPacket。构造器已提供 source 或 target 时，出口以 Rejected 拒绝，保证这两项由槽位上下文提供。
3. 出口补齐来源、动作、定义、机会、槽号，并按 Cell 指向性编码目标；RegisterActor 登记角色与上下文中的移动能力。相同 RuntimeId 再次登记时，非空移动能力更新绑定，空能力保持已有绑定。
4. 出口调用 MetaActionInstance.ExecutePacket。动作检查 double recovery、机会归属和执行锁，再通过自身生命周期 BeginAction；生效委托调用 Router.Send。
5. Router 记录执行结果并返回，生命周期按结果成功与当前运行状态决定 CompleteAction 或拒绝。选择适配器在整体成功后清理选择。

Router 的 Send 是公共入口，其校验范围为请求快照、路由所需字段、执行器唯一匹配和来源解析；机会编号、当前行动者及后摇回排由上述槽位与生命周期链路处理。实际业务入口需要遵循这条调用关系，才能取得完整行动受理与回排行为。

## Router 受理与执行

Send 先拒绝 null 参数，再完成 Request 快照，随后分配递增记录号和结果字典。快照完成后，路由处理进入 try/finally，按以下条件产生结果：

| 路由条件 | 返回状态与记录 |
| --- | --- |
| Router 未启用 | NotReady，error 说明启用条件 |
| operation 或 source 类型/字段缺失，operation 为空白 | Rejected，error 说明缺失字段 |
| 同 operation 有多个启用执行器 | Rejected，error 说明匹配冲突 |
| 匹配执行器缺失 | NotReady，error 说明 operation |
| source 对应实例缺失或 ComponentCount 为 0 | NotReady，error 说明来源失效 |
| 执行器正常返回 | 保留执行器的 ActionResult，finally 写 status |
| 执行器抛异常 | Failed，写 error 和 exception 类型名，记录后重新抛出 |

ResolveActor 要求 source 字符串已登记且实例仍有组件。ResolveMovement 读取相同来源的能力引用，移动能力自行复核承载启用、绑定及实例身份。ClearBindings 在战斗开始、停止和 Manager 禁用时清理来源映射；Records、序号和文件路径由 Router 实例持有。

MovementEffectExecutor 要求 targetKind 为 Cell 且 target 解析成两个整数。来源坐标已绑定、能力有效后，先记录 before，再调用 Validate 检查地图地格、同格和范围。拒绝时同时记录 after；成功则调用 MoveToCell 并复核能力仍有效、最终地格与目标一致；移动提交的 finally 记录 after。坐标通知可驱动朝向；具体校验见 [60 移动专题](60_地图与移动适配类型代码设计案.md)。

WaitEffectExecutor 要求 targetKind 为 None，并确认来源可解析后返回 Succeeded。等待的可观察行动结果由生命周期按 recovery 完成回排；执行器处理范围是该操作的效果判定。

## 结果快照与文件日志

Router 在 finally 给结果写入 status 字符串，生成 ActionPacketRecord，Request 与 Result 均为只读基础值快照，先加入内存 Records。启用 writeLogFile 时，首次记录按工程根目录与 logDirectory 解析目录，创建 UTC 时间加 Guid 命名的 .jsonl 文件，每次以 Newtonsoft.Json 将记录追加一行；LogPath 提供当前文件路径。

结果字段按实际执行情况出现：status 表示路由执行结果；error、exception 表示路由错误或异常；移动的 before、after 保存坐标字符串。发送者在 Send 返回后修改原字典时，已保存 Request 保持快照值。

| 记录边界 | 当前行为及其影响 |
| --- | --- |
| 空参数、Request 快照校验失败 | 在分配记录号和进入记录 finally 以前抛出，Records 保持原集合 |
| 槽位、构造器、机会或后摇在发送前拒绝 | 由动作结果与 LastError 表达，Router 记录范围从实际 Send 受理开始 |
| Router 内部拒绝或执行器返回失败 | 已完成快照的请求及其结果写入 Records，并按配置写文件 |
| 执行器成功后的时间轴完成 | Router 结果先形成，CompleteAction 随后发生；完整动作阶段从生命周期读取 |
| 文件目录创建或追加失败 | 内存记录已经加入，文件异常向上传播，生命周期转 Failed 并停止时间轴 |
| 效果提交期间异常 | 已发生的状态变化保留，记录体现可取得的结果，时间轴停止授予后续机会 |

## 能力范围与后续核验条件

当前记录为“请求 + 执行器结果”，服务于移动、待机的观察和追溯。角色初始化、属性修正、量表 Modify、普通 SetCell 和显示修改具有各自公开入口，记录覆盖以实际进入 Router.Send 的调用为界。全局所有数据写入的强制报文约束属于未实现能力。

伤害结算与类型反应、反伤因果链自动填充、战局快照恢复、日志读取回放、跨局运行 ID 恢复映射、行动撤回和事务回滚均未实现。cause 字段常量提供名称，完整因果关系需要实际生产与消费流程作为依据。回放或撤回的效果应通过相应实现和运行验证确认。

Router 日志写入与异常收束的实际运行核验需要启用场景、发送有效及拒绝报文，并观察内存、文件和动作阶段；本文依据源码说明当前控制流与静态接线。

## 实现定位

| 源码或资产 | 主要定位 |
| --- | --- |
| [ActionPackets.cs](D:/myspace/Git/mygame/Assets/Script/Battle/ActionPackets.cs) | 字段、Snapshot、ReadCell、Record 与发送出口 |
| [ActionPacketBuilders.cs](D:/myspace/Git/mygame/Assets/Script/Battle/ActionPacketBuilders.cs) | Movement/Wait 参数构造及校验 |
| [ActionRouterManager.cs](D:/myspace/Git/mygame/Assets/Script/Battle/ActionRouterManager.cs) | Send、登记解析、记录与 JSONL |
| [ActionEffectExecutor.cs](D:/myspace/Git/mygame/Assets/Script/Battle/ActionEffectExecutor.cs) | Operation、Execute 抽象入口 |
| [MovementEffectExecutor.cs](D:/myspace/Git/mygame/Assets/Script/Battle/MovementEffectExecutor.cs) | 目的格解析、校验、提交、before/after |
| [WaitEffectExecutor.cs](D:/myspace/Git/mygame/Assets/Script/Battle/WaitEffectExecutor.cs) | 待机指向性与来源校验 |
| [MetaActionInstance.cs](D:/myspace/Git/mygame/Assets/Script/Battle/MetaActionInstance.cs) | ExecutePacket 的时间轴前置检查 |
| [MetaActionLifecycle.cs](D:/myspace/Git/mygame/Assets/Script/Battle/MetaActionLifecycle.cs) | 成功回排与异常停止 |
| [MetaObjectInstance.cs](D:/myspace/Git/mygame/Assets/Script/MetaObjects/MetaObjectInstance.cs) | 定义 ID 与 RuntimeId |
| [PersistanceScene.unity](D:/myspace/Git/mygame/Assets/Scenes/PersistanceScene.unity) | ActionRouter 三组件、日志配置与 Controller 引用 |
| [Assembly-CSharp.csproj](D:/myspace/Git/mygame/Assembly-CSharp.csproj) | 类型编译归属与 Newtonsoft.Json 引用 |

核对依据为上述提交的源码、工程配置与静态资产。文档状态表示所述实现已完成对照；编译、播放、画面与交互的运行验证属于独立验证范围。
