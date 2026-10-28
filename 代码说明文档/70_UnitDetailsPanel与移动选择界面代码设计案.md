# UnitDetailsPanel 与移动选择界面代码设计案

UnitDetailsPanel 是战斗底部的信息与操作面板，显示当前行动者的姓名、三项属性以及全场角色的生命摘要，并提供独立移动按钮和四个技能按钮。面板将选择转发给角色场景适配器，地图输入或无目标确认再触发槽位的报文发送。

| 项目 | 内容 |
| --- | --- |
| 解释范围 | Assembly-CSharp，全局命名空间；UnitDetailsPanel 的界面引用、时间轴绑定、属性和生命读取、移动与技能按钮、UI.unity 装配及 DebugPanel 协作 |
| 源码依据 | UnitDetailsPanel.BindTimeline/Refresh/RefreshHealth/SelectMovement/SelectSkill/OnEnable/OnDisable；GameManager.Start；文件入口见文末实现定位 |
| 核对基线 | 工程提交 `65c2ff5e40cec060988b74091e189e09fdaa9e13`；2026-10-29 核对时工程工作区干净 |
| 关联设计 | [时间轴与行动顺序 §3.6](../系统设计文档/06-战斗/20-时间轴与行动顺序/20_时间轴与行动顺序设计.md)、[架构设计案 §7.12](../架构设计文档/架构设计案.md) |
| 状态 | 已核对：源码声明、调用链与静态资产绑定 |
| 更新日期 | 2026-10-29 |

## 类型、引用与状态归属

UnitDetailsPanel 是 Assembly-CSharp 全局命名空间中的 sealed MonoBehaviour，依赖 uGUI Button/Image 和 TextMeshPro TMP_Text。UI.unity 持有 Canvas、面板与按钮物体，面板序列化引用指向这些场景组件。

| 引用或缓存 | 作用 |
| --- | --- |
| details、hint、healthSummary | 当前行动者属性、操作提示、场上角色生命摘要 |
| moveLabel、moveButton、moveBackground | 移动文案、可交互状态和选择底色 |
| skillButtons、skillLabels | 四槽按钮、名称与后摇文本 |
| timeline | GameManager 注入的 BattleTimelineController，用于读取 Runtime 和 CurrentActor |
| selectedMovement | 面板记住的移动适配器，供行动者变化、重绑和禁用时取消选择 |
| healthActors、nextHealthScan、healthText | 角色清单、重扫时刻与文本缓冲 |

角色属性和生命由运行组件持有；移动选择由 CharacterMovementController 持有，技能选择由 SkillSelectionController 持有；时间轴由 Runtime 持有。DisplayedDetails、DisplayedHealth 和 IsMoveHighlighted 提供只读显示查询。

## 绑定、订阅与清理

GameManager.Start 在场景加载完成并等待一帧后，为面板调用 BindTimeline，再启动时间轴。BindTimeline 先取消记住的移动选择和绑定角色的技能选择，清空引用及生命清单缓存，保存时间轴并 Refresh。Update 每帧刷新。

OnEnable 给移动按钮和各技能按钮添加监听，为各槽保存捕获索引的委托；OnDisable 使用相同委托解除监听，取消移动与技能选择并清空缓存。场景按钮的持久化业务回调列表为空，业务订阅由面板生命周期建立。

SelectMovement 查询当前行动者并调用其 SelectMovement，成功后记住控制器；SelectSkill 调用当前角色的 SelectSlot。二者随后刷新显示，动作确认由选择适配器和地图输入继续处理。入口与结果见 [60 移动](60_地图与移动适配类型代码设计案.md) 和 [80 技能槽](80_基础技能槽与待机动作代码设计案.md)。

## 当前行动者与按钮显示

Refresh 先刷新生命摘要，再要求 timeline.Runtime 正在运行，取得 CurrentActor 与属性、移动和技能适配器。行动者对应的移动适配器变化时取消记住的选择。缺少属性时显示等待行动机会；正常时显示定义名称、行动力、力量和行动速度。属性汇总 OverflowException 形成溢出提示并使移动按钮不可交互。

移动按钮要求移动适配器可选择且属性存在。选中时文案为“移动 · 已选择”，背景为青绿色，其余为“移动”和深色。选择资格与范围查询是两道条件，地图或坐标缺失会在目标查询阶段体现。

技能按钮逐槽读取动作和定义，有效动作显示序号、名称和后摇，缺少动作显示“空槽”；交互资格同时要求技能适配器可控制当前角色及动作定义有效。选中槽使用青绿色。当前三份角色四槽均为待机，后摇均为 10。

提示随选择状态显示动作选择、点选高亮地格确认或再次确认无目标技能。无目标技能可再次点击同一按钮、按同一数字键或左键点未被 UI 遮挡的场景位置确认。成功与机会变化触发相应选择清理。

## 全场生命摘要

RefreshHealth 每 0.5 个不受缩放影响的秒重扫 MetaObjectPreset，并按定义 MetaObjectId 的 Ordinal 顺序排列清单。每次 Refresh 都从清单中角色的当前实例读取量表，筛选启用、已绑定且 MeterId 精确等于 Health 的角色，拼为 `HP  名称 当前值 / 上限`；空集合显示 `HP -`。

摘要清单的范围是场景中符合筛选条件的角色，独立于参战登记和当前行动者。数值每帧重读，新增角色最迟随下一次清单重扫进入。量表规则与三名角色测试值见 [75 量表专题](75_量表组件与生命显示代码设计案.md)。

## UI 场景与字体

UnitDetailsCanvas 使用 Screen Space Overlay，排序 20，CanvasScaler 参考分辨率 1280×720，宽高匹配 0.5，带 GraphicRaycaster。UnitDetails 贴屏幕底边，高度为 236 参考像素。HealthSummary 位于面板顶部，四个技能按钮位于 BaseSkills 容器，各自带 Label 子文本。

UnitDetailsPanel 字段接线为 details 1538517151、hint 166982040、healthSummary 488543080、moveLabel 474455404、moveButton 2050392728、moveBackground 2050392729；技能按钮为 228922413、1967859605、2036563005、775289352，标签为 1875193678、1949239004、58925814、446884971。按钮和标签按相同索引配对，按钮具有 Image 背景。

面板文字使用 UnitDetails SDF.asset，GUID 为 3e2ea7fb08197d249a0a4dbdff44ac4d；对应 TTF 也保存在 GameData/UI。字体覆盖与多分辨率布局属于实际运行核验范围。

DebugPanel 检测到启用面板时由底部面板承担属性详情显示，调试面板保留时间轴与调试入口，并依据面板高度和 Canvas 缩放计算自身缩放；底部面板缺席时通过 DrawCharacterDetails 绘制属性。遮挡判断使用同一实际区域计算。

## 装配条件与验证范围

面板要求属性展示时 actor.Definition 有效，移动引用与各文本完成接线，技能按钮与标签数量一致且索引在槽容量内，按钮具备 Image。当前 UI 资产提供四对按钮和标签。可见布局、字形覆盖、分辨率适配和点击观感需要运行场景核验；静态绑定支持本文的组件与数据来源结论。

## 实现定位

| 源码或资产 | 主要定位 |
| --- | --- |
| [UnitDetailsPanel.cs](D:/myspace/Git/mygame/Assets/Script/UI/UnitDetailsPanel.cs) | 绑定、监听、Refresh、生命扫描与按钮 |
| [UI.unity](D:/myspace/Git/mygame/Assets/Scenes/UI.unity) | UnitDetailsCanvas、面板与字段绑定 |
| [UnitDetails SDF.asset](<D:/myspace/Git/mygame/Assets/GameData/UI/UnitDetails SDF.asset>) | TMP 字体资产 |
| [UnitDetails.ttf](D:/myspace/Git/mygame/Assets/GameData/UI/UnitDetails.ttf) | 字体资源 |
| [GameManager.cs](D:/myspace/Git/mygame/Assets/Script/GameManager.cs) | 面板绑定时序 |
| [DebugPanel.cs](D:/myspace/Git/mygame/Assets/Script/Debug/DebugPanel.cs) | 属性详情切换、缩放及遮挡区域 |
| [CharacterMovementController.cs](D:/myspace/Git/mygame/Assets/Script/Player/CharacterMovementController.cs) | 移动选择 |
| [SkillSelectionController.cs](D:/myspace/Git/mygame/Assets/Script/Player/SkillSelectionController.cs) | 技能选择与确认 |

核对依据为上述提交的源码、工程配置与静态资产。文档状态表示所述实现已完成对照；编译、播放、画面与交互的运行验证属于独立验证范围。
