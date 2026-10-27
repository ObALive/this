# MetaAction 派生类型与动作组件代码设计案

源码用 MetaAction 系列类型承载元动作（术语表 T-188）、移动与待机。动作不是与元对象平行的孤立系统：动作定义和动作实例分别派生自对象定义和对象实例，组件也复用同一底座，并进一步分成角色对象侧的“持有动作”与动作内部的“目标、后摇和效果”。本轮给动作补上了指向性维度与待机效果，移动与待机因此共用一条受理和执行协议。

| 项目 | 内容 |
| --- | --- |
| 解释范围 | Assembly-CSharp，全局命名空间；动作定义、实例、组件派生与配置、两种持有组件、执行上下文及能力接口 |
| 源码依据 | MetaActionDefinition、MetaActionInstance、MetaActionComponents、MovementActionComponent、BasicSkillSlotsComponent 的声明及调用 |
| 核对基线 | 工程 8468fb91c225447ff0a329a020d7fcd7fe5e7857；2026-10-26；相关脚本与动作资产无未提交差异 |
| 关联设计 | [元动作 §4.3、§4.4](../系统设计文档/01-通用系统/70-元动作/70_元动作设计补充说明.md) |
| 状态 | 已核对：类型关系、源码与静态配置 |
| 更新日期 | 2026-10-26 |

## 动作与对象的三组派生

| 声明类型 | 直接基类 | 结构职责 |
| --- | --- | --- |
| MetaActionDefinition | MetaObjectDefinition | 复用组件配置清单与 CreateInstance，重写 CreateRuntime 创建动作实例 |
| MetaActionInstance | MetaObjectInstance | 复用组合字典、精确类型查询和释放，增添动作受理与生命周期执行器 |
| MetaActionComponentDefinition | MetaObjectComponentDefinition | 动作侧配置抽象基类，将 IsActionComponent 密封重写为 true |
| MetaActionComponent | MetaObjectComponent | 动作内部运行组件的共同抽象基类，仍使用 Owner/生命周期机制 |

这里的“元技能”在当前代码中没有另一个 MetaSkill 基类。移动作为动作配置和效果体现，不能凭业务称谓另画一个源码中不存在的继承节点。MetaActionInstance 构造把 IsAction 设为 true，配合底座的侧别校验，禁止把对象侧组件挂进动作实例或反向混挂。

## 对象侧持有与动作内部组合

```mermaid
classDiagram
  MetaObjectComponent <|-- ActionHolderComponent
  MetaObjectComponent <|-- BasicSkillSlotsComponent
  ActionHolderComponent <|-- MovementActionComponent
  ActionHolderComponent --> MetaActionDefinition : 共享配置引用
  ActionHolderComponent *-- MetaActionInstance : 独立运行实例
  BasicSkillSlotsComponent *-- MetaActionInstance : 四槽各自独立实例
  MetaActionInstance *-- MetaActionLifecycle : 每实例一个执行器
  MetaActionInstance *-- MetaActionComponent : 组件字典持有
  MetaActionComponent <|-- ActionTargetComponent
  MetaActionComponent <|-- ActionRecoveryComponent
  MetaActionComponent <|-- ActionEffectComponent
  ActionEffectComponent <|-- MovementEffectComponent
  ActionEffectComponent <|-- WaitEffectComponent
```

ActionHolderComponent 直接继承 MetaObjectComponent，是普通对象侧抽象类；MovementActionComponent 派生于它，本身只提供构造。MovementActionComponentDefinition 也直接继承 MetaObjectComponentDefinition，创建的是对象侧持有组件。这两者不是动作内部组件。角色对象持有 MovementActionComponent，后者引用共享动作定义并拥有独立动作运行实例。BasicSkillSlotsComponent 是并列的另一种对象侧持有组件，它不属于 ActionHolderComponent 的派生，而是自己按槽保存四个动作实例，细节见[技能槽专题](80_基础技能槽与待机动作代码设计案.md)。

ActionHolderComponent.OnAttached 创建动作；OnUnbind/OnDetached 终止并清空，OnBind 在缺失时重建。Prepare 仅在仍挂载、当前动作已 Terminated 且有定义时重建，战斗启动调用它。多个角色可以共享定义资产，但动作实例与其阶段各自独立。

| 动作内部运行类 | 直接基类 | 配对配置类及其直接基类 |
| --- | --- | --- |
| ActionTargetComponent | MetaActionComponent | ActionTargetComponentDefinition : MetaActionComponentDefinition |
| ActionRecoveryComponent | MetaActionComponent | ActionRecoveryComponentDefinition : MetaActionComponentDefinition |
| ActionEffectComponent | MetaActionComponent，抽象类 | 只有效果共同协议，没有单独的具体配对配置 |
| MovementEffectComponent | ActionEffectComponent | MovementEffectComponentDefinition : MetaActionComponentDefinition |
| WaitEffectComponent | ActionEffectComponent | WaitEffectComponentDefinition : MetaActionComponentDefinition |

各配置类重写 CreateComponent，返回相应运行组件。运行组件由 MetaActionInstance 继承来的字典持有；配置对象属于定义清单。ActionRecoveryComponent 保存 BattleBehaviorDefinition 资产引用并读取 Recovery，尚未把它当成可变动作状态。

## 上下文、接口和数据类型

ActionExecutionContext 是普通 sealed class，保存角色运行实例、机会编号、目的格、IMovementCapability 与可选 TimeLineManager 引用，供一次受理使用；它不创建或拥有这些角色和时间轴。无指向动作的目的格为空、移动能力为空，动作侧不得据此查询地格。IMovementCapability 是接口，声明有效性、目标查询、校验和实际移动，具体实现为 CharacterMovementController 的私有嵌套类 MovementCapability，详见[移动适配](60_地图与移动适配类型代码设计案.md)。

ActionResult 枚举表示 Succeeded、NoChange、NotReady、InvalidTarget、OutOfRange、OutOfTurn、Rejected、Failed 等受理结果，ActionTargetKind 枚举当前有 Cell 与 None：前者要求目的格并通过移动能力校验，后者不需要目标。CapabilityId 是从唯一效果组件推得的字符串，当前为 Movement 或 Wait；它只是效果能力的名称，不构成完整技能分类系统。

## 关键方法归属与入口

| 关键成员的实际声明类 | 继承/重写及主要调用关系 | 当前作用 |
| --- | --- | --- |
| MetaObjectDefinition.CreateInstance | MetaActionDefinition 继承，内部虚调用后者 CreateRuntime | 统一创建配置组件；不能误记为动作定义重新声明 |
| MetaActionDefinition.CreateRuntime | 重写对象定义基类 | 返回 MetaActionInstance |
| ActionHolderComponent.TryExecute | MovementActionComponent 继承；移动控制器调用 → Action.TryExecute | 检查上下文角色确为持有方 Owner，再交动作 |
| BasicSkillSlotsComponent.TryExecute | 技能适配器调用 → 槽内 Action.TryExecute | 同上检查 Owner，并取指定槽的实例 |
| MetaActionInstance.ValidateDefinition | 控制器、查询与执行路径调用 | 要求一个目标、一个后摇和唯一效果组件，检查后摇合法及效果与指向性匹配 |
| MetaActionInstance.TryQueryTargets | 控制器 → 目标组件 Query → 能力接口 | 只对 Cell 动作返回当前目标集合和版本 |
| MetaActionInstance.TryExecute | 持有方 → 目标 Validate → lifecycle.TryExecute | 动作对外统一受理，先验证定义、能力（仅 Cell）、当前角色与机会 |
| ActionTargetComponent.Validate / Query | 动作实例 → IMovementCapability | None 直接成功；Cell 才转交能力校验/查询 |
| MovementEffectComponent.Apply | 重写 ActionEffectComponent.Apply；生效委托调用 → TryMove | 具体移动效果入口 |
| WaitEffectComponent.Apply | 重写 ActionEffectComponent.Apply；生效委托调用 | 不做领域修改，直接返回成功，表示结束行动 |
| MetaActionInstance.Dispose | 重写 MetaObjectInstance.Dispose | 标记终止、调用生命周期 Terminate，再清理组件；Terminate 转到本重写入口 |

验证后的生效及结束交接由独占 MetaActionLifecycle.TryExecute 承担，其统一执行地位见[独立专题](40_MetaActionLifecycle统一执行入口代码设计案.md)。动作实例自身 Phase 从该执行器读取，受理前拒绝会调用生命周期 Reject；LastError 由动作实例保存受理错误或复制执行器结果。

普通鼠标提交还经过场景侧的选择门槛：移动由 CharacterMovementController 的选择状态把关，技能槽由 SkillSelectionController 把关，两者都属于适配层，不属于 ActionExecutionContext、动作实例或生命周期阶段。UnitDetailsPanel 的按钮只负责选择，右键只取消选择，二者不直接执行效果；直接调用 TryMoveToCell 的调试路径仍可在未选择按钮时进入相同动作受理与能力校验。选择与确认的完整流程见[技能槽专题](80_基础技能槽与待机动作代码设计案.md)。

## 当前资产与边界

MovementAction 定义配置地格目标、后摇组件和一个移动效果；其目标配置未写指向性字段，取枚举默认值 Cell。WaitAction 定义配置无指向目标、后摇组件和待机效果，指向性显式写为 None。两份动作的后摇分别引用 MovementTiming 与 WaitTiming，当前值都是 10 游戏秒。三角色的移动持有组件引用同一移动资产；四槽技能配置引用同一待机资产。有效动作的直接目标/类别/后摇属性依赖组件存在，正常调用链先 ValidateDefinition；任意外部直接读取无效动作不保证安全。

当前只有移动与待机两种效果、Cell 与 None 两种指向性。未实现全部技能族、复杂目标、成本/产出串与其他行为接入；待机之外没有第二份可配置的地格技能。动作成功后仍由持有方保存并可重复执行，未建立设计所述“即时性效果实例生效后销毁”的独立一次性实例层。统一入口存在也不能证明全部角色行为已经接入。

## 实现定位

- [MetaActionDefinition.cs](D:/myspace/Git/mygame/Assets/Script/Battle/MetaActionDefinition.cs)：动作定义派生及工厂重写。
- [MetaActionInstance.cs](D:/myspace/Git/mygame/Assets/Script/Battle/MetaActionInstance.cs)：动作实例派生、受理、执行器持有和 Dispose 重写。
- [MetaActionComponents.cs](D:/myspace/Git/mygame/Assets/Script/Battle/MetaActionComponents.cs)：动作组件树、指向性、上下文、接口和结果枚举。
- [MovementActionComponent.cs](D:/myspace/Git/mygame/Assets/Script/MetaObjects/MovementActionComponent.cs)：对象侧单动作持有组件及其配置、继承方法。
- [BasicSkillSlotsComponent.cs](D:/myspace/Git/mygame/Assets/Script/MetaObjects/BasicSkillSlotsComponent.cs)：对象侧四槽持有组件，结构见技能槽专题。
- [MovementAction.asset](D:/myspace/Git/mygame/Assets/GameData/Battle/MovementAction.asset)、[MovementTiming.asset](D:/myspace/Git/mygame/Assets/GameData/Battle/MovementTiming.asset)、[WaitAction.asset](D:/myspace/Git/mygame/Assets/GameData/Battle/WaitAction.asset)、[WaitTiming.asset](D:/myspace/Git/mygame/Assets/GameData/Battle/WaitTiming.asset)：两种动作组合与各自后摇引用。
