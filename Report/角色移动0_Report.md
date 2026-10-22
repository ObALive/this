# 角色移动 0 执行报告

| 项目 | 内容 |
| --- | --- |
| 任务编号 | 角色移动0 |
| 任务书 | 工作区 `Dsh/Task/M系列任务/角色移动0.md`（资料库同内容副本 `Task/M系列任务/角色移动0.md`）；网络节点 `角色行为 / 角色移动 / 0 / 制作元对象和相关组件约定` |
| 执行日期 | 2026-10-18，Asia/Shanghai |
| 任务状态 | Completed（完成且已验证） |
| 报告版本 | v2（按现有 Player/01.Field 集成，删除 v1 的独立演示场景） |

## 变更记录

| 版本 | 日期 | 变更 | 原因 |
| --- | --- | --- | --- |
| v1 | 2026-10-18 | 初版：独立演示场景验收 | 节点实现与验证完成 |
| v2 | 2026-10-18 | 改为在现有 `PersistanceScene/Player` 与 `01.Field` 上接线；删除独立演示场景/角色；WASD 组件停用 | 用户明确要求必须基于已构建工程实现，不要另做一套；v1 的演示场景容易被误认为推翻原有工作 |

## 1 任务目标

实现网络图中的“角色行为 / 角色移动 / 0 / 制作元对象和相关组件约定”节点：建立元对象与组件的运行时约定，并做出可实际使用的两个组件——场景纹理组件与场景坐标组件；把现有角色显示在其所在地图格子的中心，使渲染位置与格子坐标一致。

本节点没有直接前置。图中的下游边为 `角色移动0 → 角色移动1`（同路线链式）与 `角色移动0 → 战斗进入与布置1`（显式），两者不在本节点范围内，未实现、未验证。

## 2 任务书摘要与适用规范

任务书授权范围：在 Unity 工程中完成本节点所需的脚本、场景、Prefab、配置与相关测试；允许修复本节点引出的兼容与接线问题；可将任务记录写入资料库 `Output/` 与 `Report/`；`Rules/`、系统设计、架构设计、旧 `Code_Design/` 与 `Tool/` 本轮只读；不启动其他节点、不修改网络数据库；默认不提交或推送 git。

用户当次补充指令：必须基于已经构建的工程实现，允许增删改查，但不要全部推翻；随后明确选择“直接把元对象组件接到现有 Player 根节点上”。

适用规范清单：

| 规范 | 触发依据与执行情况 |
| --- | --- |
| NR-01 规范总则 | 全部任务必读；遵守目录边界、冲突优先级与禁止行为 |
| NR-02 任务执行规范 | 全部任务必读；任务状态、报告十一节、文件变更与异常登记按本规范执行 |

未触发 NR-03、NR-05、NR-06、NR-07、NR-08 的正文编写条件：本节点没有编写或修订系统设计稿、架构设计案、代码设计案或交互规格；过程记录按 NR-02 的目录与命名要求落点。未修改 `Rules/`、设计库、旧 `Code_Design/`、`Tool/` 或网络数据库。

## 3 执行环境

| 项目 | 内容 |
| --- | --- |
| 工作区 | `D:\myspace\Git\mygame` |
| 资料库 | `D:\myspace\Git\this` |
| Unity | 2022.3.62f3c1，安装于 `D:\Unity\2022.3.62f3c1` |
| 程序集 | 工程无自定义 asmdef；新脚本进入 `Assembly-CSharp`，编辑器工具进入 `Assembly-CSharp-Editor` |
| 现有场景 | `01.Field.unity`（地图）、`PersistanceScene.unity`（Player）、`UI.unity`、`Template.unity` |
| 现有角色 | `PersistanceScene/Player`：多层 SpriteRenderer（Body/Hair/Arm/Shadow）、SortingGroup、BoxCollider2D、Rigidbody2D、WASD 的 `Player.cs` |
| 工程工具 | 已运行的 Unity 编辑器与本地 Unity MCP 服务（`127.0.0.1:8080`）；`query.py` 只读查询；git 状态检查 |
| 基线 | 开工时 `git status --porcelain` 为空；未覆盖或删除既有未提交修改 |

## 4 使用工具

- `Tool/项目网络图/query.py`：只读读取指定数据库，核对节点正文、对象声明、直接前置与边；
- git：检查工作区状态、核对场景/脚本改动，回退无关的序列化重命名与用户设置变化；
- Unity 编辑器 + `unity-mcp`：资产刷新与编译、在编辑器内执行集成/验证方法、场景装载与 Play Mode 查询、Game View 截图；
- Python 3.11 + Pillow：仅用于生成路径加载测试用的小纹理；未用于替换工程美术；
- 未使用外部网络、未调用收费服务、未上传工程或任务数据。

## 5 执行过程

1. 读取任务书、`Rules/README.md`、NR-01、NR-02 与 `Tool/项目网络图/读库说明.md`；使用 `query.py` 指定 `N01_完整依赖清理新图_v2.sqlite` 只读查询目标节点与边。
2. 核对目标：`角色行为/角色移动 0`，正文为通过场景纹理组件与场景坐标组件显示预置元对象，对象为“元对象-场景纹理组件”与“元对象-场景坐标组件”；无直接前置。
3. 检查工程：Unity 2022.3.62f3c1；无自定义 asmdef；现有 `PersistanceScene/Player` 是多层角色，`01.Field` 有地图 Grid/Tilemap；仓库中未发现同名元对象实现。
4. 先在隔离场景完成组件与原型的局部验证，确认元对象结构、纹理赋值、格子中心定位可行。
5. 按用户要求改为在现有工程上集成：打开 `PersistanceScene`，在 `Player` 根节点新增 `MetaObjectPreset`；用现有 `BodyWalkDown_0` 的 Sprite 创建 `Player.asset` 定义；启用 `useCurrentCellOnAwake`，由 `01.Field` 的 Grid 换算当前格子并吸附到格子中心；停用 WASD 的 `Player` 组件（保留脚本与字段）。
6. 删除 v1 临时生成的独立演示场景、演示 Prefab、演示定义与演示背景；保留 `PlayerDemo.png` 仅作为 `SceneTextureComponent.LoadSprite` 正路径测试夹具。
7. 编译并执行 `MetaObjectVerification.VerifyAll()`，结果为 `PASS`；在 `PersistanceScene + 01.Field` 进入 Play Mode 查询 Player 的格子、位置与 Body Sprite，并截图。
8. 收口：恢复 `UI` 场景，回退由场景切换产生的 `UserSettings/EditorUserSettings.asset` 修改，恢复被 Unity 自动改名的 `bagSturcture_SO` 字段行；未提交或推送 git。

## 6 文件变更列表

新增脚本与编辑器工具：

- `Assets/Script/MetaObjects/IMetaObjectComponent.cs`
- `Assets/Script/MetaObjects/MetaObjectComponent.cs`
- `Assets/Script/MetaObjects/MetaObjectInstance.cs`
- `Assets/Script/MetaObjects/MetaObjectComponentDefinition.cs`
- `Assets/Script/MetaObjects/MetaObjectDefinition.cs`
- `Assets/Script/MetaObjects/SceneTextureComponent.cs`
- `Assets/Script/MetaObjects/SceneCoordinateComponent.cs`
- `Assets/Script/MetaObjects/MetaObjectPreset.cs`
- `Assets/Editor/MetaObjectSetup.cs`
- `Assets/Editor/MetaObjectVerification.cs`

新增资产与接线：

- `Assets/GameData/MetaObjects/Player.asset`：`CHAR_PLAYER` 元对象定义，含场景纹理组件与场景坐标组件；
- `Assets/Resources/MetaObjects/Characters/PlayerDemo.png`：仅用于路径加载正例测试；
- 上述脚本与资产对应的 `.meta`，以及 `Assets/GameData/MetaObjects.meta`、`Assets/Resources/MetaObjects.meta`、`Assets/Script/MetaObjects.meta` 等目录元文件。

修改的既有文件：

- `Assets/Scenes/PersistanceScene.unity`：
  - `Player` 根节点新增 `MetaObjectPreset`（`definition = Player.asset`、`cell = (0,0)`、`grid` 运行时查找、`rebuildOnAwake = 1`、`useCurrentCellOnAwake = 1`）；
  - `Player.cs` 组件 `m_Enabled` 由 1 改为 0（脚本、字段与资产保留）；
  - 其他 Player 组件与层级未改动；
  - Unity 保存时自动改名的 `bagSturcture_SO` 行已恢复为原字段名，避免无关 diff。
- `Assets/Script/Inventory/Data/ItemInstance.cs`：改为继承 `MetaObjectInstance`，组件字典与取用方法上移到基类；`MetaObjectId` 以 `ItemID` 为唯一来源；
- `Assets/Script/Components/ItemComponent.cs`：`ItemComponent` 继承 `IMetaObjectComponent`，使既有物品组件继续作为元对象组件使用；
- `Assembly-CSharp.csproj`、`Assembly-CSharp-Editor.csproj`：Unity 自动生成，纳入新增脚本的编译项。

删除的临时产物（均为本次新增，不是工程原有资产）：

- `Assets/Scenes/00.MetaObjectDemo.unity` 及其 `.meta`；
- `Assets/Prefabs/MetaObjectCharacter.prefab`、`Assets/Prefabs/` 与 `Assets/Prefabs.meta`；
- `Assets/GameData/MetaObjects/CHAR_Demo.asset` 及其 `.meta`；
- `Assets/Resources/MetaObjects/Backgrounds/` 及其 `.meta`。

`UserSettings/EditorUserSettings.asset` 因场景切换产生“最近使用场景”记录，已在收口时回退，不计入最终变更。

## 7 权限操作记录

未执行 `sudo`/root 操作，未修改系统配置、环境变量、用户权限或网络配置，未安装或卸载软件，未启动对外服务，未提交或推送 git。使用已存在的本地 Unity 编辑器与 Unity MCP 服务（仅监听回环地址 `127.0.0.1:8080`）完成编译、执行集成/验证与截图；未修改该服务配置。未向第三方发送工程或任务数据。

## 8 异常情况

| 等级 | 情况 | 处置与遗留 |
| --- | --- | --- |
| Level 1 | v1 为节点验收另建了演示场景/演示角色，用户看到后误以为原有工作被删除 | 按用户要求改为在现有 `PersistanceScene/Player` 与 `01.Field` 上集成；删除仅由本次新增的演示文件，原有场景/美术未删除。已在报告中明确区分 |
| Level 1 | 第一次批处理打开工程时工程已被另一个 Unity 实例打开，进程以 `HandleProjectAlreadyOpenInAnotherInstance` 退出 | 改用已运行编辑器的 Unity MCP 通道完成刷新、编译、验证与截图；未关闭用户编辑器 |
| Level 1 | `MetaObjectSetup` 首次编译报 `TextureImporter.spriteAlignment` 不存在（CS1061） | 改用 `TextureImporterSettings.spriteAlignment` 与 `spritePivot` 后重新编译通过；无遗留 |
| Level 1 | 首次集成时编辑器仍处于 Play Mode，`EditorSceneManager.OpenScene` 报“cannot be used during play mode” | 先停止 Play Mode，再执行集成；集成成功 |
| Level 1 | 删除演示场景后，编辑器仍保留其内存场景且为 dirty | 新建空场景并重新打开 `UI.unity`，不保存已删除的演示场景；未影响用户场景 |
| Level 1 | Unity 保存 `PersistanceScene` 时把 `bagSturcture_SO` 自动写成新字段名 `bagStructure_SO` | 手工恢复原字段行，保持 diff 最小；`[FormerlySerializedAs]` 仍兼容两种写法 |

未出现 Level 2 或 Level 3 异常。

## 9 输出文件列表

| 文件 | 用途 |
| --- | --- |
| `Report/角色移动0_Report.md` | 本报告（v2） |
| `Output/角色移动0/角色移动0_实现与验证记录_v2.md` | 实现结构、现有工程接线、验证结果与后续入口 |
| `Output/角色移动0/角色移动0_验证结果_v1.txt` | 自动化验证结果 `PASS` |
| `Output/角色移动0/角色移动0_运行截图_v1.png` | Play Mode 中现有 Player 位于 `(7,-4)` 格子中心的截图 |

## 10 完成状态

按 NR-02 §三.3 的三项标准核对：

| 标准 | 结果 |
| --- | --- |
| 任务目标达成 | 已在现有 `Player` 上建立元对象实例、场景纹理组件与场景坐标组件；Player 实际位于 `01.Field` 的 `(7,-4)` 格子中心；Body 渲染器使用现有 Body Sprite |
| 输出文件完整 | 脚本、定义资产、场景接线、编辑集成工具与验证工具均已落盘；实现与验证记录、验证结果、运行截图已归档 |
| 任务报告完成 | 本报告按 NR-02 十一节完成，并附 v1→v2 变更记录 |

结论：本节点为“完成且已验证”。验证方式包括 Unity 编译、编辑器内行为验证 `PASS`、Play Mode 运行时格子/位置/Sprite 查询与 Game View 截图。未把“代码存在”当作验收完成。

限制：本次 Play Mode 验证时 `PersistanceScene` 与 `01.Field` 均已打开，未单独构造“先 Player、后地图”的晚加载时序；`SceneManager.sceneLoaded` 的晚绑定路径已实现，`01.Field` 当前不在 Build Settings，运行时按名加载需另行确认。

## 11 后续建议

1. **下一节点可直接使用本节点入口**：`MetaObjectPreset.Instance` 取得当前元对象实例；`MetaObjectPreset.TryBindToGrid` 完成地图加载后的首次绑定；`SceneCoordinateComponent.SetCell` / `MetaObjectPreset.SetCell` 驱动格子位置。点击地格移动节点可在这些入口上接入输入与寻路。
2. **WASD 已停用**：`Player` 组件仍在物体上但 `m_Enabled = 0`，脚本与字段保留；下一节点接入点击移动后可删除或替换该组件。当前 Player 不会自行移动。
3. **完整注册表仍待实现**：`Code_Design/01-通用系统/30_元对象与组件代码设计案.md` 的 `CLS-OBJ-001` 至 `CLS-OBJ-009`、`API-OBJ-001` 至 `API-OBJ-005`、登记校验与判别字段式存档序列化尚未落地。建议在组件族增加前先落注册表与登记校验。
4. **资源加载路径**：`SceneTextureComponent` 同时支持 Resources 路径与直接 `Sprite`；现有 Player 使用直接 Body Sprite，避免复制美术。若后续统一到 Addressables/M01 资源服务，只需替换 `LoadSprite` 加载实现，保留 `TexturePath` 契约。
5. **存档边界**：`MetaObjectInstance` 的组件字典不参与 Unity 默认序列化；后续需要入档时，应按架构案的判别字段式多态序列化接入。
6. **验证固化**：`MetaObjectVerification` 目前通过编辑器调用；若需要进入 CI，建议增加 EditMode 测试程序集或批处理入口，并固定 `PersistanceScene + 01.Field` 的 Play Mode 验证与截图作为回归证据。
