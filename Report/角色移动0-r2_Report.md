# 角色移动0-r2 执行报告

| 项目 | 内容 |
| --- | --- |
| 任务标识 | 角色移动0-r2 |
| 任务书 | `Dsh/Task/M系列任务/角色移动0.md`（工作区 `D:\myspace\Git\mygame`） |
| 目标节点 | 角色行为 / 角色移动 / 0 / 制作元对象和相关组件约定 |
| 执行日期 | 2026-10-18（Asia/Shanghai） |
| 任务状态 | Completed（完成且已验证） |
| 报告版本 | v4（多对象角色存为预制体撤下，场景改用单一占位角色；纹理留空待赋值） |

## 变更记录

| 版本 | 日期 | 变更 | 原因 |
| --- | --- | --- | --- |
| v1 | 2026-10-18 | 初版：元对象内核、两个组件、Player 预置接线与 Play Mode 验证 | 节点实现完成 |
| v2 | 2026-10-18 | `MetaObjectPreset` 增加序列化字段变化监听，`Cell` 属性改为可写；补充“运行时改 cell”验证与报告内容 | 验收反馈“运行时修改 cell 变量，角色位置没有移动”：直接改序列化字段绕过了 `SetCell` |
| v3 | 2026-10-18 | 移除字段监听与预置上的 `cell` 字段；坐标与纹理改为组件私有状态，只经 `SetCell` / `SetTexture` / `SetTexturePath` 改动；增加 Debug Panel 元对象验收面板 | 用户要求不用字段监听，关键变量私有、改动必须经过方法，并留出可在 Play Mode 操作的验收入口 |
| v4 | 2026-10-19 | 原多对象角色整体保存为 `Player_Layered.prefab` 并撤出场景；场景改用单一空对象 Player（SpriteRenderer + MetaObjectPreset）；纹理配置清空，相机引用重接 | 多对象角色不适合当前单 SpriteRenderer 的渲染逻辑；纹理引用由用户自行赋值 |

## 1 任务目标

实现网络图节点“角色行为 / 角色移动 / 0 / 制作元对象和相关组件约定”。节点正文：通过场景纹理组件与场景坐标组件将预置元对象显示在指定地图格子，渲染位置与其坐标一致。节点声明的对象为“元对象-场景纹理组件”（保存角色渲染在场景上的纹理；取脚本挂载物体上的 SpriteRenderer，把纹理路径对应的纹理赋给它）与“元对象-场景坐标组件”（确认对象渲染位置，把对象锚点渲染在地图网格的格子中心）。

该节点没有直接前置：数据库中 `v_edge` 指向它的边为 0。它的下游边是 `角色移动0 → 角色移动1`（同路线链式）与 `角色移动0 → 战斗进入与布置1`（显式），两者不在本节点范围内，未实现、未验证。

## 2 任务书摘要与适用规范

任务书授权：在 Unity 工程中完成本节点所需的脚本、场景、Prefab、配置与相关测试；允许修复本节点引出的兼容与接线问题；任务记录可写入资料库 `Output/`、`Report/`；`Rules/`、系统设计文档、架构设计文档与 `Tool/` 本轮只读；不启动其他节点、不修改网络数据库；默认不提交或推送 git。

用户当次补充指令：执行前先仔细确认当前构建情况，在已构建工程的基础上实现目标节点内容，不另做一套。

v3 补充指令：不要用增加字段变化监听的方法实现；为组件中的关键变量（如坐标组件的坐标、渲染组件的纹理）设置方法并把这些变量设为私有，改动必须经过这些方法，效果应用逻辑可以在改动方法中一并调用；同时留下验收入口，能在 Play Mode 中测试效果，可利用 Debug Panel。

v4 补充指令：当前角色由多 object 构成，不适合现在的渲染逻辑；把当前角色整个保存为预制体暂时从场景里撤下，换一个单一的空 object 加上必要组件来充当角色；具体引用什么纹理暂时留空，由用户赋值。

适用规范清单：

| 规范 | 触发依据与执行情况 |
| --- | --- |
| NR-01 规范总则 | 全部任务必读；遵守目录边界、冲突优先级与禁止行为 |
| NR-02 任务执行规范 | 全部任务必读；任务状态、目录与文件、报告十一节、异常登记、自检清单按本规范执行 |

未触发 NR-03、NR-05、NR-06、NR-07、NR-08 的正文编写条件：本节点没有编写或修订系统设计稿、架构设计案、代码设计案或交互规格；`Code_Design/01-通用系统/30_元对象与组件代码设计案.md` 只作为只读设计输入。过程记录按 NR-02 的目录与命名要求落点。未修改 `Rules/`、三个设计库、`Tool/` 或网络数据库。

## 3 执行环境

| 项目 | 内容 |
| --- | --- |
| 工作区 | `D:\myspace\Git\mygame` |
| 资料库 | `D:\myspace\Git\this` |
| git 基线 | 分支 `dsh-move-1`，`HEAD=14bb652`（与 `main` 同一提交）；开工时 `git status --porcelain` 仅有 3 个未跟踪的 `Logs/*.log` |
| Unity | 2022.3.62f3c1（`D:\Unity\2022.3.62f3c1`），编辑器已打开本工程 |
| 程序集 | 工程无自定义 asmdef；运行脚本进入 `Assembly-CSharp`，编辑器工具进入 `Assembly-CSharp-Editor` |
| 已加载场景 | `PersistanceScene`（活动）、`01.Field`、`UI`、`Template` |
| 角色构成 | 场景中为单一 `Player`：`Transform` + `SpriteRenderer`（`Instance/0`，sprite 为空）+ `MetaObjectPreset`；原多对象角色保存在 `Assets/Prefabs/Player_Layered.prefab`（`SortingGroup`、`BoxCollider2D`、`Rigidbody2D`、`Player`、`TriggerItemFader`、`ItemPickup` 与四个分层 `SpriteRenderer`） |
| 地图 | `01.Field/Grid`：`cellSize=(1,1,0)`、`cellLayout=Rectangle` |
| 工程工具 | Unity 编辑器 + 本地 Unity MCP 服务（`http://127.0.0.1:8080/mcp`，仅回环）；`query.py` 只读查询；git |

开工前确认的构建情况：当前工作区没有任何元对象相关脚本或资产；仓库中存在一个更早的实现备份（分支 `dsh-move-0`，提交 `a10b16e`，提交信息为 “backup working state before move (MetaObjects WIP)”），它不在当前分支，也没有被本次执行复用。本次在当前分支上重新实现。

## 4 使用工具

- `Tool/项目网络图/query.py`：显式指定 `N01_完整依赖清理新图_v2.sqlite` 只读查询节点正文、对象声明、依赖边与全图路线；未写入数据库。
- Unity MCP（`http://127.0.0.1:8080/mcp`）：编辑器状态查询、资产刷新与编译、`execute_code` 执行 C#（建定义资产、接场景、运行时探针与行为用例）、`execute_menu_item` 执行自检菜单、`read_console` 读取编译与运行日志、`manage_editor` 进出 Play Mode。
- Unity 编辑器：编译、Play Mode 场景表现与实际截图（`ScreenCapture.CaptureScreenshot`）。
- git：状态与差异核对。
- 未使用外部网络、未调用收费服务、未向第三方发送工程或任务数据。

## 5 执行过程

1. 读任务书、`Rules/README.md`、NR-01、NR-02、`Tool/项目网络图/读库说明.md`；用 `query.py --node n9` 与 `v_edge` 只读核对目标节点与依赖。
2. 核对构建情况：git 状态、分支、提交历史与 `reflog`；确认 `dsh-move-0` 是更早的实现备份、当前分支没有元对象代码；检查 Unity 版本、程序集、场景、`Player` 层级、`01.Field` 的 Grid 与 Build Settings。
3. 读只读设计输入：`Code_Design/01-通用系统/30_元对象与组件代码设计案.md`（定义/实例分离、组件登记与挂载口径）与 `Report/角色移动0_Report.md`（更早一次执行记录，用于识别本工程已有约定与已知限制）。本次不复制旧实现，只沿用“定义 + 实例 + 组件”的既定口径。
4. 实现运行时约定：`MetaObjectComponent`、`MetaObjectComponentDefinition`、`MetaObjectDefinition`、`MetaObjectInstance`、`MetaObjectPreset`，以及两个组件 `SceneTextureComponent`、`SceneCoordinateComponent`。格子归预置、锚点偏移归坐标组件、纹理归纹理组件。
5. 编辑器内编译：`refresh_unity`（force/all/compile）通过，控制台无 error / warning。
6. 建定义资产 `Assets/GameData/MetaObjects/Player.asset`（`CHAR_PLAYER`，两项组件配置），并用 `SerializedObject` 写入 `[SerializeReference]` 清单。
7. 在 `PersistanceScene/Player` 上挂 `MetaObjectPreset` 并接线：`cell=(7,-4)`、`gridSceneName=01.Field`、`spriteRenderer=BodyWalkDown_0`；把 `Player`（WASD）组件停用，避免与格子定位形成两个位置来源。保存场景。
8. 增加编辑器自检工具 `Assets/Editor/MetaObjectVerification.cs`（菜单 `Tools/Meta Object/Verify Play Mode Wiring`）。
9. 进 Play Mode：自检 `PASS`；读取预置状态（格子、Grid、实例组件、期望/实际锚点、纹理、四个渲染器）；相机确认 Player 在视口中心；截图。
10. 在同一 Play Mode 内执行 10 条行为用例（正反路径、失败保留、缺 Grid 挂起、空 Grid 拒绝、同类型替换、换格与还原、Rebuild），全部通过；临时对象与临时定义用后销毁。
11. 退出 Play Mode，恢复场景中的 `bagSturcture_SO` 字段行，保持与基线一致的最小 diff；核对最终 `git status` 与场景 diff。
12. 归档：`Output/角色移动0-r2/` 与 `Report/角色移动0-r2_Report.md`。
13. 收到验收反馈“运行时修改 Player 的 `cell` 变量，角色没有移动”。在 Play Mode 内复现：把序列化字段 `cell` 改为 `(7,-2)` 后，字段与坐标组件都不更新，位置仍是 `(7.5,-3.5,0)`，而新格子中心应为 `(7.5,-1.5,0)`。确认原因是字段写入绕过了 `SetCell`。
14. 修正：`MetaObjectPreset` 记录 `appliedCell`，在 `Update` 中比较字段值与已应用值，不一致时补一次应用；`Cell` 属性改为可写（`set => SetCell(value)`）；`SetCell`、`BindGrid`、`TryBind` 统一经 `ApplyCell()`。重新编译并在 Play Mode 复验：字段改 `(7,-2)` 后下一帧位置 `(7.5,-1.5,0)`，属性赋值 `(5,-3)` 立即到 `(5.5,-2.5,0)`，改回 `(7,-4)` 回到 `(7.5,-3.5,0)`；自检与 10 条行为用例全部通过。归档 `_v2` 验证结果与实现记录。
15. 收到 v3 验收要求：不要用字段变化监听；组件关键变量私有、改动必须经过方法；留 Play Mode 验收入口。移除 `MetaObjectPreset.Update`、`appliedCell` 与预置 `cell` 字段；格子与纹理分别收进 `SceneCoordinateComponent.cell` 与 `SceneTextureComponent.texture` / `texturePath`（均私有），对外只留 `SetCell` / `SetTexture` / `SetTexturePath`，方法内部调用 `ApplyToScene()` 完成效果应用。
16. 初始格子改为按 Player 在场景中的摆放位置换算；重新保存 `PersistanceScene`，移除 `cell` 与 `adoptCurrentCellOnAwake` 序列化项，并恢复被 Unity 自动改名的 `bagSturcture_SO` 字段行。
17. 在 `DebugPanel` 增加“元对象”面板（格子输入 + 应用、方向键逐格、切换纹理、回到初始格子）；重新编译并在 Play Mode 复验 14 条行为用例、自检菜单与面板显示，归档 `_v3` 验证结果、实现记录与面板截图。
18. 收到 v4 要求：多对象角色不适合当前渲染逻辑，整体存预制体撤下，换单一空对象，纹理留空。用 `PrefabUtility.SaveAsPrefabAsset` 把当前 `Player` 整棵树（根节点 + 四个子对象 + 原组件）保存为 `Assets/Prefabs/Player_Layered.prefab`。
19. 在 `(7.5,-3.5)` 新建单一 `Player`（`SpriteRenderer` + `MetaObjectPreset`），把 `Virtual Camera` 的 `m_Follow`、`m_LookAt` 转到新对象，再删除旧 `Player`；清空 `Player.asset` 的纹理配置（`texturePath` 为空、`sprite` 为空）。
20. 调整 `SceneTextureComponent` 与自检：纹理未配置时静默、不报错；重新编译并在 Play Mode 验证格子、位置、相机跟随、自检菜单与 Debug Panel，归档 `_v4` 验证结果、实现记录与截图。

## 6 文件变更列表

新增运行时代码（`Assets/Script/MetaObjects/`，含 `.meta`）：

- `MetaObjectComponent.cs`：组件基类与四段生命周期约定；
- `MetaObjectComponentDefinition.cs`：组件配置项基类；
- `MetaObjectDefinition.cs`：元对象定义资产（ScriptableObject）与 `CreateInstance()`；
- `MetaObjectInstance.cs`：运行时实例与组件构成；
- `MetaObjectPreset.cs`：预置元对象的场景承载、Grid 解析、绑定与重建、把格子改动转发给坐标组件；不保存格子字段、不做字段监听；
- `SceneTextureComponent.cs`：场景纹理组件及其配置项；纹理与来源路径私有，只经 `SetTexture` / `SetTexturePath` 改动并在方法内应用；
- `SceneCoordinateComponent.cs`：场景坐标组件及其配置项；格子私有，只经 `SetCell` 改动并在方法内应用。

新增编辑器工具（`Assets/Editor/`，含 `.meta`）：

- `MetaObjectVerification.cs`：Play Mode 接线自检菜单。

新增资产与接线：

- `Assets/GameData/MetaObjects/Player.asset`（含 `.meta`）：`CHAR_PLAYER` 定义，两项组件配置；纹理项为空（`texturePath` 与 `sprite` 均未赋值），坐标项 `anchorOffset=(0,0)`；
- `Assets/Prefabs/Player_Layered.prefab`（含 `.meta`、`Assets/Prefabs.meta`）：原多对象角色完整备份（根节点 + 四个分层 SpriteRenderer + 原组件），已从场景撤下；
- `Assets/Script/MetaObjects.meta`、`Assets/GameData/MetaObjects.meta`：目录元文件。

修改的既有文件：

- `Assets/Scenes/PersistanceScene.unity`：删除原多对象 `Player` 及其四个子对象；新建单一 `Player`（`(7.5,-3.5)`，`SpriteRenderer`（Instance/0，sprite 为空）+ `MetaObjectPreset`，`definition=Player.asset`、`gridSceneName=01.Field`、`spriteRenderer=自身渲染器`）；`Virtual Camera` 的 `m_Follow`、`m_LookAt` 指向新 `Player`；
- `Assets/Script/MetaObjects/SceneTextureComponent.cs`：纹理未配置（路径与 Sprite 都为空）时静默，不清空渲染器；只有配置了路径却解析失败才报错；
- `Assets/Editor/MetaObjectVerification.cs`：允许空纹理配置，只有配置了路径却解析失败才判失败；
- `Assets/Script/Debug/DebugPanel.cs`：增加“元对象”验收面板，按组件方法改动格子与纹理；
- `Assembly-CSharp.csproj`、`Assembly-CSharp-Editor.csproj`：Unity 自动生成，纳入新增脚本的编译项。

未修改：`Player.cs` 与其他既有脚本、`01.Field`、`UI`、`Template` 场景、`ProjectSettings`、`Packages`、`UserSettings`。未提交或推送 git。

## 7 权限操作记录

未执行 `sudo`/root 操作，未修改系统配置、环境变量、用户权限或网络配置，未安装或卸载软件，未启动对外服务，未提交或推送 git。使用已存在的本地 Unity 编辑器与 Unity MCP 服务（仅监听回环地址 `127.0.0.1:8080`）完成刷新、编译、执行与截图；未修改该服务配置。未向第三方发送工程或任务数据。

## 8 异常情况

| 等级 | 情况 | 处置与遗留 |
| --- | --- | --- |
| Level 1 | 开工时发现更早一次实现保存在分支 `dsh-move-0`（提交 `a10b16e`），当前分支没有该实现 | 按用户“在当前基础上实现”的指令，在当前分支重新实现；未合并、未复制旧文件。旧分支保留，供用户对比 |
| Level 1 | Unity 保存 `PersistanceScene` 时把既有字段行 `bagSturcture_SO` 自动改写成新字段名 `bagStructure_SO` | 手工把该行恢复为 `bagSturcture_SO`；源码有 `[FormerlySerializedAs("bagSturcture_SO")]`，两种写法都能反序列化。该字段值为 `{fileID: 0}`，无行为影响 |
| Level 1 | 截图时临时隐藏 `MainCanvas`，恢复调用因 `GameObject.Find` 找不到未激活对象而返回 false | 退出 Play Mode 后运行时状态整体丢弃；`MainCanvas` 在工程场景中未被修改，截图后编辑器场景保持原状 |
| Level 1 | 进入 Play Mode 前控制台出现过一条 MCP 插件自身的 WebSocket 警告（`Unexpected receive error: WebSocket is not initialised`） | 属于 MCP 插件通信，与本节点代码无关；后续刷新与编译正常，无遗留 |
| Level 1 | 用例 B1/C1 会在 Play Mode 控制台留下两条预期错误日志（纹理解析失败、两个 Grid 无法确定） | 只用例期间存在，临时对象与临时定义已销毁；真实 Player 预置无错误或警告。已在该验证记录中注明为预期失败路径 |
| Level 1 | 验收反馈：运行时直接修改 `cell` 序列化字段，角色位置不变。v1 只提供 `SetCell`，字段写入绕过它 | v2 曾用 `Update` 比较字段与 `appliedCell` 修正；该做法已在 v3 按要求移除 |
| Level 1 | v3 验收要求：不要用字段变化监听，组件关键变量私有、改动必须经过方法，并留 Play Mode 验收入口 | 已移除 `MetaObjectPreset.Update`、`appliedCell` 与预置 `cell` 字段；格子与纹理收进组件私有状态，`SetCell` / `SetTexture` / `SetTexturePath` 内完成应用；新增 Debug Panel 元对象面板。14 条用例、自检菜单与面板显示复验通过 |
| Level 1 | v4 验收要求：多对象角色不适合当前渲染逻辑，整体存预制体撤下，换单一空对象，纹理留空 | 已保存 `Assets/Prefabs/Player_Layered.prefab` 并从场景删除旧角色；新建单一 `Player`（`SpriteRenderer` + `MetaObjectPreset`）；相机 `Follow`/`LookAt` 重接；`Player.asset` 纹理配置清空。Play Mode 验证格子、位置、相机与自检通过 |

未出现 Level 2 或 Level 3 异常。

## 9 输出文件列表

| 文件 | 用途 |
| --- | --- |
| `Report/角色移动0-r2_Report.md` | 本报告（v4） |
| `Output/角色移动0-r2/角色移动0-r2_实现与验证记录_v4.md` | 单一占位角色、预制体备份、纹理留空入口与当前接线（v4） |
| `Output/角色移动0-r2/角色移动0-r2_验证结果_v4.txt` | 预制体内容、新场景角色、相机重接与 Play Mode 验证（v4） |
| `Output/角色移动0-r2/角色移动0-r2_运行截图_v3.png` | Play Mode 下多对象角色已撤下、Debug Panel 显示“纹理 <无>” |
| `Output/角色移动0-r2/角色移动0-r2_实现与验证记录_v3.md` | 组件私有状态与方法约定、Debug Panel 入口、下游入口与限制（v3） |
| `Output/角色移动0-r2/角色移动0-r2_验证结果_v3.txt` | 14 条行为用例、自检菜单、面板状态与场景收敛输出（v3） |
| `Output/角色移动0-r2/角色移动0-r2_运行截图_v2.png` | Play Mode 下 Debug Panel 的元对象验收面板 |
| `Output/角色移动0-r2/角色移动0-r2_实现与验证记录_v2.md` | v2 实现记录（保留，字段监听做法已移除） |
| `Output/角色移动0-r2/角色移动0-r2_验证结果_v2.txt` | v2 验证输出（保留） |
| `Output/角色移动0-r2/角色移动0-r2_实现与验证记录_v1.md` | 初版实现记录（保留） |
| `Output/角色移动0-r2/角色移动0-r2_验证结果_v1.txt` | 初版验证输出（保留） |
| `Output/角色移动0-r2/角色移动0-r2_运行截图_v1.png` | Play Mode 中 Player 位于格子 `(7,-4)` 中心的实际画面 |

## 10 完成状态

按 NR-02 §三.3 的三项标准核对：

| 标准 | 结果 |
| --- | --- |
| 任务目标达成 | 场景中的角色已换成单一空对象：`Transform` + `SpriteRenderer`（Instance/0，sprite 为空）+ `MetaObjectPreset`；预置初始格子由摆放位置换算为 `(7,-4)`，Play Mode 锚点位于格子中心 `(7.5,-3.5,0)`，差值 0；相机 `Follow`/`LookAt` 已指向新对象；原多对象角色完整保存在 `Assets/Prefabs/Player_Layered.prefab`；纹理配置留空，赋值后由 `SceneTextureComponent` 写到该渲染器 |
| 输出文件完整 | 运行时脚本、定义资产、预制体、场景接线、编辑器自检工具、Debug Panel 验收面板均已落盘；v1/v2/v3/v4 验证结果、实现记录与截图已归档 |
| 任务报告完成 | 本报告按 NR-02 十一节完成，并附 v1→v4 变更记录 |

结论：本节点为“完成且已验证”。验证覆盖 Unity 编译、编辑器自检菜单、Play Mode 运行时状态查询、14 条行为用例（含拒绝与生命周期边界、组件级改动入口、纹理设置与非法值拒绝）、Debug Panel 面板显示，以及 v4 的预制体保存、场景角色替换与相机重接；未把“代码存在”当作验收完成。

限制：只在编辑器 Play Mode 验证，未做打包运行；`01.Field` 不在 Build Settings；非 Resources 纹理路径在打包运行不可解析；纹理尚未赋值时角色不可见（本版预期）；占位角色没有碰撞体、刚体与输入组件；注册表、实体类型登记、组件能力类别、挂载契约与存档未实现。

## 11 后续建议

1. **下一节点可直接使用的入口**：`MetaObjectPreset.Instance`、`MetaObjectPreset.Cell`（只读）、`MetaObjectPreset.SetCell(Vector2Int)`、`MetaObjectPreset.TryBind()`、`MetaObjectPreset.BindGrid(Grid)`、`MetaObjectPreset.TryGetCellWorldPosition(out Vector3)`；组件侧 `SceneCoordinateComponent.Cell`（只读）/ `SetCell` / `ApplyToScene`、`SceneTextureComponent.Texture`（只读）/ `SetTexture` / `SetTexturePath` / `LoadSprite(string)`。点击地格移动节点可把“点到格子 → `SetCell`”接在这些入口上。
2. **关键状态只经方法改动**：预置没有格子字段，也不监听字段变化；坐标与纹理是组件私有状态，`SetCell` / `SetTexture` / `SetTexturePath` 内会立即应用效果。初始格子由物体摆放位置换算；若生成流程要先指定格子，先调用 `SetCell` 再让预置绑定，绑定前会暂存。Debug Panel 的“元对象”面板是 Play Mode 验收入口，按钮走同一批方法。
3. **占位角色与原角色预制体**：场景 `Player` 只有 `SpriteRenderer` 与 `MetaObjectPreset`，不含碰撞体、刚体、WASD、拾取与淡出；这些能力保留在 `Assets/Prefabs/Player_Layered.prefab`。后续需要碰撞或拾取时，在新 `Player` 上按需添加；不要把原角色的四个子渲染器直接拖回场景，否则会破坏“一个元对象对应一个 SpriteRenderer”的显示约定。
4. **纹理赋值入口**：`Assets/GameData/MetaObjects/Player.asset` → `SceneTextureComponentDefinition` 的 `sprite`（或 `texturePath`）。赋值后进入 Play Mode 即显示；纹理未赋值时组件静默、不报错。当前 `SpriteRenderer.sprite` 为空是预期状态。
5. **地图场景加载**：`01.Field` 未加入 Build Settings。建议在战斗进入与布置或地图服务节点把地图场景纳入构建与加载流程，并用 `BindGrid(Grid)` 显式交给预置，替代当前按场景名 `01.Field` 的过渡解析。
6. **资源加载**：`SceneTextureComponent` 目前支持直接 Sprite 与 Resources 路径，并在编辑器内按工程路径解析。后续接入资源服务 / Addressables 时，只需替换 `LoadSprite` 实现，保留 `TexturePath` 契约与“解析失败保留原显示”的口径。
7. **注册表与登记校验**：`Code_Design/01-通用系统/30_元对象与组件代码设计案.md` 的 `CLS-OBJ-001` 至 `CLS-OBJ-009`、`API-OBJ-001` 至 `API-OBJ-005` 仍是缺口（设计案本身也登记了 `REQ-OBJ-01`）。建议在增加第二类组件族之前落地对象与组件注册表、实体类型登记与能力类别，避免组件名与能力口径漂移。
8. **存档**：`MetaObjectInstance` 的组件字典不参与 Unity 序列化，也没有存档形态。需要入档时按架构案的判别字段式多态序列化接入，不要把当前字典当成存档结构。
9. **旧实现对比**：更早一次实现保存在 `dsh-move-0`（`a10b16e`）。本次实现没有复用它的文件；若需要保留其中的部分做法（例如 `MetaObjectPreset.Bind(MetaObjectInstance)`），可在对比后单独移植。
10. **测试固化**：当前自检通过编辑器菜单与 Play Mode 执行。若需要进入 CI，建议增加 EditMode 测试程序集与批处理入口，把“预置数量、格子中心、纹理赋值”固定为回归断言。
