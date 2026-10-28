# UnitDetailsPanel 与移动选择界面代码设计案

UnitDetailsPanel 是战斗底部的信息与操作面板：它展示当前行动者的姓名与三项属性、场上角色的生命摘要，并提供移动按钮与四个技能按钮。面板只把“选择哪个动作”转发给角色身上的场景适配器，把目的格确认留给地图输入；它不保存技能、行动机会或生命，因此查看与选择都不会自行推进战斗。

| 项目 | 内容 |
| --- | --- |
| 解释范围 | Assembly-CSharp，全局命名空间；UnitDetailsPanel 的界面引用、时间轴绑定、属性与生命读取、移动/技能按钮、反馈和清理，以及 UI.unity 静态装配 |
| 源码依据 | UnitDetailsPanel.BindTimeline/Refresh/RefreshHealth/SelectMovement/SelectSkill/OnEnable/OnDisable；GameManager.Start；CharacterMovementController.SelectMovement；SkillSelectionController.SelectSlot |
| 核对基线 | 工程 7362b95addd908be4f96110c2c51ad0300af8e58；2026-10-27；UnitDetailsPanel 的生命摘要、UI.unity 的 HealthSummary/BaseSkills 与面板高度 236 已由该提交收录，相关文件无未提交差异 |
| 关联设计 | [时间轴与行动顺序 §3.6](../系统设计文档/06-战斗/20-时间轴与行动顺序/20_时间轴与行动顺序设计.md)、[架构设计案 §7.12](../架构设计文档/架构设计案.md) |
| 状态 | 已核对：结构、源码与静态绑定；实际画面、字体和交互未运行验证 |
| 更新日期 | 2026-10-27 |

## 类归属与界面对象关系

UnitDetailsPanel 是 sealed MonoBehaviour，位于 `Assets/Script/UI/UnitDetailsPanel.cs`，被 Assembly-CSharp.csproj 的 Compile 项包含，未声明 namespace。它使用 uGUI 的 Button/Image 和 TextMeshPro 的 TMP_Text；这不是 MetaObjectComponent 派生类型，也不在角色运行对象的组件字典中。

| 成员或场景对象 | 归属/关系 | 实际作用 |
| --- | --- | --- |
| details、hint | 面板引用两个 TMP_Text；由 UI 场景创建和持有 | 属性正文与操作提示 |
| healthSummary | 面板引用的 TMP_Text | 全场角色生命摘要，独立于当前行动者 |
| moveLabel、moveButton、moveBackground | 面板引用移动按钮 GameObject 上的文本、Button 和 Image | 移动按钮文字、可交互状态与选中底色 |
| skillButtons、skillLabels | 面板引用四个按钮及各自子文本 | 技能槽选择与名称/后摇显示；长度按场景配置 |
| timeline | GameManager 调用 BindTimeline 注入 BattleTimelineController 引用 | 查询 Runtime 是否运行及 CurrentActor，不拥有时间轴 |
| selectedMovement | 面板记住经移动按钮选择成功的 CharacterMovementController | 行动者切换、重绑或禁用时清理旧选择；真实选择标记仍属于控制器 |
| healthActors、nextHealthScan、healthText | 面板私有的角色清单缓存、重扫时刻与拼接缓冲 | 生命摘要的扫描与格式化，不写回任何角色 |
| UnitDetailsCanvas / UnitDetails / BaseSkills | UI 场景中的父 Canvas、面板 GameObject 与技能按钮容器 | 屏幕覆盖式 uGUI；CanvasScaler/GraphicRaycaster 承接缩放与界面命中 |

关系是场景组合与组件引用，不是面板继承了 Button 或 TMP_Text。`IsMoveHighlighted` 通过记住的控制器查询 IsMovementSelected；`DisplayedDetails`、`DisplayedHealth` 读取文本。三者都是查询属性，不提供动作、属性或生命的写入口。技能选择状态也不在面板中，而由运行时补加的 SkillSelectionController 持有。

## 方法声明、订阅与启动

| 实际声明方法 | 主要调用方与下游 | 结构地位 |
| --- | --- | --- |
| GameManager.Start | Unity → 所有已加载的 UnitDetailsPanel.BindTimeline → 时间轴启动 | 面板依赖注入的启动编排，先绑定再授予首个机会 |
| UnitDetailsPanel.OnEnable / OnDisable | Unity → 按钮 onClick 添加/移除 SelectMovement、SelectSkill | 动态订阅与成对清理；场景按钮没有持久化业务回调 |
| UnitDetailsPanel.BindTimeline | GameManager 或外部绑定 → 取消旧移动与技能选择、Refresh | 清旧引用并接受新时间轴 |
| UnitDetailsPanel.Update / Refresh | Unity 或绑定/按钮后刷新 | 刷新生命摘要，再从当前行动者重取属性、移动与技能状态 |
| UnitDetailsPanel.SelectMovement | Button.onClick → 当前角色控制器 SelectMovement | 移动选择请求入口，不调用 TryMoveToCell |
| UnitDetailsPanel.SelectSkill | Button.onClick → 当前角色 SkillSelectionController.SelectSlot | 技能槽选择请求入口，不直接执行动作 |
| UnitDetailsPanel.RefreshHealth | Refresh 每帧调用 | 扫描、过滤并拼出全场生命摘要 |
| CharacterMovementController.SelectMovement / CancelMovementSelection | 面板、输入和时间轴清理 | 真正持有并清理移动选择，详见[移动适配类型](60_地图与移动适配类型代码设计案.md) |
| SkillSelectionController.SelectSlot / Confirm / CancelSelection | 面板、数字键、场景点击与清理 | 真正持有技能选择与机会校验，详见[技能槽专题](80_基础技能槽与待机动作代码设计案.md) |

BindTimeline 先清理由面板记住的旧控制器选择与旧角色的技能选择，再清空 selectedMovement 与生命清单缓存、保存 timeline 并刷新。绑定发生在 TryStartBattle 之前，首次刷新可以显示等待机会；Update 继续读取启动后的当前行动者。禁用时移除两类按钮监听、取消当前角色的技能选择与面板记住的移动选择，避免留下失去界面的选择状态。

## 详情读取与按钮状态

Refresh 先读取生命摘要，再判断 timeline、Runtime 存在且正在运行，才取得 CurrentActor 并取其移动控制器与 AttributeComponent。已记住的控制器与当前控制器不同，会先取消旧选择。面板显示当前行动者，而不是任意查看对象，也不改变 ElectedObject。

无属性组件时详情显示等待行动机会；正常时读取定义的 DisplayName 和行动力、力量、行动速度当前值。汇总抛出 OverflowException 时显示属性溢出并禁用移动按钮。它不捕获任意异常，当前装配要求 actor.Definition 和所有序列化界面引用有效，缺失时没有通用容错替代。

移动按钮可用需移动控制器存在、CanSelectMovement 成立且有属性组件。可选择检查不等于地图、坐标、范围全部就绪，因此按钮可用仍可能在后续目标查询阶段没有可选格。Refresh 对属性溢出只改变显示和按钮可用性，不主动调用 CancelMovementSelection。

按下移动按钮成功后记录控制器，并显示“移动 · 已选择”；重复选择同一有效动作保持选择。所选背景设为青绿色，未选为深色。具体 RGB 是源码写入 Image 的配置输入，Button 的 Selectable 过渡也会影响最终显示，实际画面未运行验证。

技能按钮的状态与当前角色绑定：没有当前行动者或没有槽组件时，四个按钮显示“空槽”且不可用；有槽时逐个读取动作与定义，可交互要求技能适配器 CanSelect 成立且该槽动作通过定义校验，标签显示“序号 · 显示名”和“后摇 数值”，动作缺失则显示“空槽”。被选中的槽按钮用同一青绿色底。由于待机是无指向动作，当前选中槽时提示为“再次选择该技能或左键空白场景释放 · 右键取消”；若选中的是地格指向槽，则提示改为点选高亮地格。当前三份角色只配置待机，所以地格分支在现有场景中不会出现。

普通鼠标路径随后由移动控制器允许目标查询与高亮，同格按松确认后才进入动作；无指向技能则在未被界面遮挡的位置按松即确认。右键优先取消而不生效；成功、机会改变、实例重建、禁用、重绑或行动者切换会清理相应选择。指针离格/失焦只取消按压，不必然退出选择；完整边界见移动适配与技能槽专题。

## 生命摘要的读取与显示

`RefreshHealth` 每次刷新先取场景中所有 MetaObjectPreset，按定义的 MetaObjectId 排序并缓存 0.5 秒；随后跳过未激活、未绑定或没有量表的承载，只接受用途标识严格等于 `Health` 的量表，把“显示名 当前值 / 上限”拼成一行写入 healthSummary，没有可显示角色时写 `HP -`。它不依赖当前行动者或时间轴，因此战斗开始前也会列出全部符合条件的角色；清单是全场扫描而非参战名单。

这段显示与量表的数值规则分开：面板只读当前值与上限，不调用 Modify、不缓存数值，也不订阅变化事件，靠每帧重读。量表的创建、增减与边界见[量表专题](75_量表组件与生命显示代码设计案.md)。当前三份角色分别显示 100/100、120/150、60/80。

## UI 场景和字体绑定

UI.unity 中 UnitDetailsPanel 的八个序列化字段已落实到本场景：details 1538517151、hint 166982040、healthSummary 488543080、moveLabel 474455404、moveButton 2050392728、moveBackground 2050392729；skillButtons 为 228922413、1967859605、2036563005、775289352，skillLabels 为 1875193678、1949239004、58925814、446884971。移动按钮与其背景同属 Move 对象；四个技能按钮为 Skill1—Skill4，标签分别是各按钮下的 Label 子文本。

父级 UnitDetailsCanvas 是 Screen Space Overlay，CanvasScaler 参考分辨率为 1280×720、宽高匹配 0.5，带 GraphicRaycaster。面板 UnitDetails 贴在底边，当前高度 236 参考像素；HealthSummary 是面板顶部一条横向拉伸文本，锚点约为横向 0.025—0.975、纵向 0.847—1；四个技能按钮放在面板内的 BaseSkills 容器下。所有文本引用同一 `UnitDetails SDF.asset`，其 GUID 为 3e2ea7fb08197d249a0a4dbdff44ac4d；工程同时保存 UnitDetails.ttf，并在技能文案扩展时重新烘焙字形；生命摘要沿用现有字形，未再改动字体资产。

按钮的持久化 OnClick 列表为空，业务监听由 OnEnable 添加、OnDisable 移除，因此场景不保存业务回调。绑定有效仅证明资产来源可定位，不能据此确认字形覆盖、分辨率适配或点击遮挡已经运行通过。

DebugPanel 发现启用的面板后隐藏旧 IMGUI 属性详情，保留时间轴调试并调整调试区缩放；没有启用面板时回退到旧详情。其检测与缩放依赖场景 RectTransform/Canvas 结构，不会替面板补齐缺失引用。

## 实现定位与当前边界

- [UnitDetailsPanel.cs](D:/myspace/Git/mygame/Assets/Script/UI/UnitDetailsPanel.cs)：面板声明、引用、按钮订阅、属性/技能刷新、生命摘要与失败处理。
- [UI.unity](D:/myspace/Git/mygame/Assets/Scenes/UI.unity)：Canvas、面板、BaseSkills、按钮/文本与字段绑定。
- [UnitDetails SDF.asset](<D:/myspace/Git/mygame/Assets/GameData/UI/UnitDetails SDF.asset>)、[UnitDetails.ttf](D:/myspace/Git/mygame/Assets/GameData/UI/UnitDetails.ttf)：字体资源。
- [GameManager.cs](D:/myspace/Git/mygame/Assets/Script/GameManager.cs)、[DebugPanel.cs](D:/myspace/Git/mygame/Assets/Script/Debug/DebugPanel.cs)：启动接线和旧调试显示协作。
- [CharacterMovementController.cs](D:/myspace/Git/mygame/Assets/Script/Player/CharacterMovementController.cs)、[SkillSelectionController.cs](D:/myspace/Git/mygame/Assets/Script/Player/SkillSelectionController.cs)、[GridClickInput.cs](D:/myspace/Git/mygame/Assets/Script/Player/GridClickInput.cs)：选择状态、互斥与地图输入清理。
- [Assembly-CSharp.csproj](D:/myspace/Git/mygame/Assembly-CSharp.csproj)：运行程序集成员和 Unity.TextMeshPro 引用依据。

当前面板除姓名与三项属性外，还提供技能选择与生命摘要，但没有通用多技能菜单、任意查看对象选择、独立目标预览确认页，也没有生命变化的操作入口。四个技能按钮当前都指向同一待机动作，属于槽位验证而非正式构筑。装配上要求技能按钮与标签数量一致、按钮上存在 Image 背景，否则刷新会索引越界或取色失败；这些是当前场景满足、代码未兜底的前提。

接口和场景绑定已静态核对；本轮没有运行编辑器验证脚本或游戏，也不把工程中已有验证脚本的存在当作验证通过。
