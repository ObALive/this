# 代码说明文档库

本库以现有程序集、类和关键方法为解释对象，说明代码怎样组成、归属、派生和协作，以及这些结构怎样实现对象显示、属性取值、移动动作与共享时间轴。各类型的主要说明位置固定在下表；继承、组件持有、配置引用和方法调用分别标明。

## 阅读入口与覆盖范围

从[程序集与类型关系总览](00_程序集与类型关系总览代码设计案.md)开始，可看到整体派生树与持有关系。理解动作执行时，先读动作派生类型，再读 MetaActionLifecycle，最后读时间轴；追踪鼠标请求从地图与移动适配类型进入。文档范围是现有对象、属性、移动、高亮、动作与时间轴的实现及必要协作者，未覆盖工程所有功能。

| 解释对象 | 程序集及主要类型 | 主要说明位置 | 源码位置 | 核对基线 | 状态 | 更新日期 |
| --- | --- | --- | --- | --- | --- | --- |
| 程序集和整体关系 | Assembly-CSharp；关联 Assembly-CSharp-Editor、Assembly-CSharp-firstpass | [程序集与类型关系总览](00_程序集与类型关系总览代码设计案.md) | 三份同名 `.csproj`、范围内类型声明 | c744a32b59973f9888d69447bbd2775fccf064f4，结合当前工程文件 | 已核对 | 2026-10-24 |
| 对象底座 | Assembly-CSharp：MetaObjectDefinition/Instance、MetaObjectComponentDefinition/Component | [MetaObject 类型与组件底座](10_MetaObject类型与组件底座代码设计案.md) | `Assets/Script/MetaObjects/MetaObject*.cs` | 同上 | 已核对 | 2026-10-24 |
| 场景承载与对象侧组件 | Assembly-CSharp：MetaObjectPreset、SceneCoordinate/SceneTexture/MovementFacing/Attribute 组件及配对配置 | [对象组件与场景承载类型](20_对象组件与场景承载类型代码设计案.md) | `Assets/Script/MetaObjects/` | 同上 | 已核对 | 2026-10-24 |
| 动作派生体系 | Assembly-CSharp：MetaActionDefinition/Instance/Component、ActionHolderComponent、目标/后摇/效果组件 | [MetaAction 派生类型与动作组件](30_MetaAction派生类型与动作组件代码设计案.md) | `Assets/Script/Battle/MetaAction*.cs`、`MetaObjects/MovementActionComponent.cs` | 同上 | 已核对 | 2026-10-24 |
| 统一动作执行入口 | Assembly-CSharp：MetaActionLifecycle、MetaActionPhase | [MetaActionLifecycle 统一执行入口](40_MetaActionLifecycle统一执行入口代码设计案.md) | `Assets/Script/Battle/MetaActionLifecycle.cs` | 同上 | 已核对 | 2026-10-24 |
| 行动顺序与场景装配 | Assembly-CSharp：TimeLineManager、BattleTimelineController、时机配置、GameManager、DebugPanel | [TimeLineManager 与战斗装配类型](50_TimeLineManager与战斗装配类型代码设计案.md) | `Assets/Script/Battle/`、`GameManager.cs`、`Debug/DebugPanel.cs` | 同上 | 已核对 | 2026-10-24 |
| 地图与移动适配 | Assembly-CSharp：TilemapManager、GridClickInput、CharacterMovementController、MovementRange、MovementRangeOverlay | [地图与移动适配类型](60_地图与移动适配类型代码设计案.md) | `Assets/Script/TilemapManager.cs`、`Assets/Script/Player/` | 同上 | 已核对 | 2026-10-24 |

## 源码基线与文档状态

工程根目录为 [mygame](D:/myspace/Git/mygame)，核对提交为 `c744a32b59973f9888d69447bbd2775fccf064f4`，核对日期为 2026-10-24。上述脚本、配置和场景均无相关未提交差异。工程另有 `Assets/M Studio/Art/Trees/Tree_G.prefab`、`Tree_Y.prefab` 及三份导入/着色器日志的未提交改动；本库不把这些改动归入提交身份，也不据此判断树冠遮挡的实际画面。

程序集归属通过当前工程的 AssemblyName、Compile 项与 ProjectReference 核对，不以目录名或架构模块推定；所列类型均在全局命名空间。工程文件是编辑器生成的配置证据，不能作为本轮编译通过的证据。各专题的“已核对”表示声明范围内的结构、源码行为与静态绑定已核对，未执行编译、自动测试、游戏播放或播放器构建。

## 当前能力边界

当前移动以地图现存地格和曼哈顿距离筛选目的格，行动力（术语表 T-036）取非负整数部分；路径连通、阻碍、地格占用和累计地形成本尚未接入。共享时间轴（术语表 T-117）使用固定行为后摇，行动速度已可查询但尚未参与补正。力量已可查询，重物投掷尚未由这些实现承接。

元动作（术语表 T-188）在源码中由 MetaAction 系列类型表达，没有名为 MetaSkill 的单独类型。动作定义和实例分别派生自对象定义和实例。MetaActionLifecycle 是每动作实例持有的同步生命周期执行器，TimeLineManager 是参战者顺序与机会的管理者。动作实例可重复执行，即时性效果生效后销毁、完整技能类别与其他行为仍有实现差距；文档不把当前结构等同于全部设计已落实。
