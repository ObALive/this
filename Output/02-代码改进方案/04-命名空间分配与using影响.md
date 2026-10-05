# 命名空间分配与 using 影响表（5.2 落地执行底稿）

> 根命名空间：**`Farm`**（推荐占位名，可整体替换；若替换，执行"把每文件 `Farm.` 前缀替换为新根名"即可，其余映射不变）。
> 规则：命名空间按**业务域**分，不按文件当前物理目录分；目录搬迁（P/F 系列）与命名空间（NS 系列）相互独立、可分别取舍。
> 本表给的是"全编号采纳后的最终形态"。若只采纳部分 NS，删除本表对未采纳域的行即可——文件间的引用（using）按本表"反向引用点"列处理。

## 1. 文件 → 命名空间 总表（24 个现有文件 + 新建文件）

| 当前文件 | 当前命名空间 | 最终路径（F/P 采纳后） | 目标命名空间 | 文件最终需要保留/删除的 using |
| --- | --- | --- | --- | --- |
| Script/Utilities/Singleton.cs | （全局） | Script/Utilities/Singleton.cs（保留） | `Farm.Utilities` [NS-02] | 保留 `UnityEngine` |
| Script/Utilities/Settings.cs | （全局） | Utilities 保留 或 Effects（P-06） | `Farm.Utilities`（P-06 采纳则为 `Farm.Effects`）[NS-02/NS-07] | 保留 `System`、`UnityEngine`（TimeSpan/Vector3） |
| Script/Utilities/SwitchBounds.cs | （全局） | Script/Utilities/SwitchBounds.cs（保留） | `Farm.Utilities` [NS-02] | 保留 `Cinemachine`、`UnityEngine` |
| Script/Utilities/DataCollection.cs | （全局） | —（F-11 删除） | — | — |
| Script/Utilities/Enums.cs | （全局） | —（F-09 删除） | — | — |
| Script/Components/ItemComponent.cs | （全局） | Components（保留） | `Farm.Components` [NS-03] | 保留 `System`、`System.Collections.Generic`、`UnityEngine` |
| Script/Components/MeterComponentData_SO.cs | （全局） | Components（保留） | `Farm.Components` [NS-03] | 保留现有 4 个 using（自身类型同域，无需新增） |
| Script/Components/InventoryComponentData_SO.cs | （全局） | Components（保留） | `Farm.Components` [NS-03] | **新增** `using Farm.Inventory.Data;`（`ItemInstance`、`InventoryConfig`）；其余保留 |
| （F-03 新建）Components/SlotType.cs | — | Components | `Farm.Components` | 无外部依赖 |
| （F-03 新建）Components/SlotConfig.cs | — | Components | `Farm.Components` | `System.Collections.Generic`（List<int>） |
| （F-03 新建）Components/BaseInventorySlot.cs | — | Components | `Farm.Components` | **新增** `using Farm.Inventory.Data;`（`ItemInstance` 形参） |
| （F-03 新建）Components/InventoryCell.cs | — | Components | `Farm.Components` | 无 |
| （F-03 新建）Components/EquipmentSlot.cs | — | Components | `Farm.Components` | `using Farm.Inventory.Data;`（ItemInstance，经基类签名引用时无需但建议加） |
| Script/Inventory/Logic/InventoryManager.cs | `Inventory` | Script/Inventory/InventoryManager.cs（F-04 上移） | `Farm.Inventory` [NS-04] | 命名空间 `Inventory`→`Farm.Inventory`；**删除** `using static InventoryComponent;`、`using static ItemDetails;`、`using System.Runtime.CompilerServices;`；保留 `System`、`System.Collections.Generic`、`System.Linq`、`UnityEngine`；**新增** `using Farm.Inventory.Data;`（ItemDetails/ItemInstance/ComponentRef/InventoryConfig/BagStructure_SO）、`using Farm.Utilities;`（Singleton 基类）；`InventoryComponentData_SO`/`InventoryComponent` 来自 `Farm.Components` → 需要时新增 `using Farm.Components;` |
| Script/Inventory/Item/Item.cs | （全局） | Inventory/Item（保留） | `Farm.Inventory` [NS-04] | 现 `using Inventory;` 删除（同域）；**新增** `using Farm.Inventory.Data;`（ItemDetails/ItemInstance） |
| Script/Inventory/Item/ItemPickup.cs | `Inventory` | Inventory/Item（保留） | `Farm.Inventory` [NS-04] | `Inventory`→`Farm.Inventory`；**新增** `using Farm.Inventory.Data;`（ItemDetails） |
| Script/Inventory/Item/ItemFader.cs | （全局） | Script/Effects/（P-04） | `Farm.Effects` [NS-07] | 保留 `UnityEngine`、`DG.Tweening`；**删除** `System.Data`（未用）；`Settings` 若仍在 `Farm.Utilities` 则加 `using Farm.Utilities;`（P-06 采纳后同域免加） |
| Script/Inventory/Item/ItemManager.cs | （全局） | —（F-12A 删除）/ Script/Player/（F-12B） | F-12B 时 `Farm.Player` | F-12B：**删除** `using UnityEditor;`（P0-7）；**新增** `using Farm.Components;`（InventoryComponent）、`using Farm.Inventory.Data;`（ItemInstance）、`using Farm.Utilities;`（Singleton） |
| Script/Player/Player.cs | （全局） | Script/Player/Player.cs（保留） | `Farm.Player` [NS-09] | 保留 `System.Collections`、`System.Collections.Generic`、`UnityEngine`；**新增** `using Farm.Characters;`（CharacterInstance 字段，N-04 后） |
| Script/Player/TriggerItemFader.cs | （全局） | Player（保留）/ Effects（P-05） | `Farm.Player`（P-05 采纳则 `Farm.Effects`）[NS-09/NS-07] | `ItemFader` 在 `Farm.Effects` → **新增** `using Farm.Effects;`（若 P-05 采纳则同域免加） |
| Script/UI/InventoryUI.cs | `Inventory` | UI（保留） | `Farm.UI` [NS-08] | `Inventory`→`Farm.UI`；SlotUI 同域；保留 `UnityEngine` |
| Script/UI/SlotUI.cs | `Inventory` | UI（保留） | `Farm.UI` [NS-08] | `Inventory`→`Farm.UI`；**新增** `using Farm.Inventory.Data;`（ItemDetails）；保留 UnityEngine/UnityEngine.UI/TMPro/UnityEngine.EventSystems |
| （F-07 新建）UI/ContainerType.cs | — | UI | `Farm.UI` | 无 |
| （F-05 新建）Characters/CharacterData.cs | — | Characters | `Farm.Characters` [NS-06] | 无 |
| （F-05 新建）Characters/CharacterInstance.cs | — | Characters | `Farm.Characters` | **新增** `using Farm.Inventory.Data;`（`Baseitem` 字段：ItemInstance） |
| Script/Inventory/dataSO/Char_SO.cs →（F-05 迁改）Characters/Character_SO.cs | （全局） | Characters/Character_SO.cs | `Farm.Characters` | `CharData`/`CharacterData` 同域 |
| Script/Inventory/dataSO/ItemDataList_SO.cs | （全局） | Inventory/Data/（P-02） | `Farm.Inventory.Data` [NS-05] | ItemDetails 同域；保留 `System.Collections.Generic`、`UnityEngine` |
| Script/Inventory/dataSO/BagStructure_SO.cs | （全局） | Inventory/Data/（P-02） | `Farm.Inventory.Data` | InventoryConfig 同域；`SlotConfig`（在其字段类型中）属 `Farm.Components` → **新增** `using Farm.Components;` |
| Script/Inventory/dataSO/InventoryBag_SO.cs | （全局） | X-02A 删除 / X-02B 随迁 Inventory/Data | X-02B 时 `Farm.Inventory.Data` | 无（空类） |
| （F-01 新建）Inventory/Data/ItemDetails.cs | — | Inventory/Data | `Farm.Inventory.Data` | `UnityEngine`、`UnityEngine.AddressableAssets`、`System`、`System.Collections.Generic`；ComponentRef/ItemType 同域 |
| （F-02 新建）Inventory/Data/ItemInstance.cs | — | Inventory/Data | `Farm.Inventory.Data` | `System`、`System.Collections.Generic`；**新增** `using Farm.Components;`（`ItemComponent` 接口）；`UnityEngine`（Dictionary? 不需要；按实际保留） |
| （F-06 新建）Inventory/Data/ItemType.cs | — | Inventory/Data | `Farm.Inventory.Data` | 无 |
| （F-13 新建）Inventory/Data/InventoryConfig.cs | — | Inventory/Data | `Farm.Inventory.Data` | `System.Collections.Generic`；**新增** `using Farm.Components;`（`SlotConfig` 字段类型） |
| Script/Debug/DebugPanel.cs | （全局） | Debug（保留） | `Farm.Debug` [NS-10] | 保留 `UnityEngine`；**删除** `using Inventory;`（代码未引用 Inventory 域类型）与 `using JetBrains.Annotations;`（未用） |
| Script/GameManager.cs | （全局） | 根级保留（K-03） | （建议保持全局；或随未来系统入口规划再加域，本期不设） | 保留现有 using（空壳） |
| Editor/UI Builder/ItemEditor.cs | （全局） | Editor（保留/ X-01 改名） | `Farm.Editor`（或保持全局，二选一）[NS-11] | **新增** `using Farm.Inventory.Data;`（ItemDetails/ItemDataList_SO/ItemType 经反射名或字段类型引用）；其余 Editor using 保留 |

## 2. 反向引用点（"谁要补 using"汇总，按目标域）

| 目标域 | 该域被下列文件引用 → 这些文件在各自 NS 项中需补 using |
| --- | --- |
| `Farm.Inventory.Data` | InventoryManager.cs（ItemDetails/ItemInstance/ComponentRef/InventoryConfig/BagStructure_SO）、Item.cs（ItemDetails/ItemInstance）、ItemPickup.cs（ItemDetails）、SlotUI.cs（ItemDetails）、ItemEditor.cs（ItemDetails/ItemDataList_SO）、InventoryComponentData_SO.cs 的 InventoryComponent（ItemInstance/InventoryConfig）、CharacterInstance.cs（ItemInstance）、BaseInventorySlot.cs/EquipmentSlot.cs（ItemInstance 形参类型） |
| `Farm.Components` | InventoryManager.cs（InventoryComponent/InventoryComponentData_SO）、ItemInstance.cs（ItemComponent）、InventoryConfig.cs（SlotConfig）、BagStructure_SO.cs（经 InventoryConfig 引用 SlotConfig 时——非直接，无强制）、ItemManager.cs（F-12B 时） |
| `Farm.Characters` | Player.cs（CharacterInstance） |
| `Farm.Effects` | TriggerItemFader.cs（ItemFader） |
| `Farm.Utilities` | InventoryManager.cs（Singleton 基类）、ItemManager.cs（F-12B 时）、ItemFader.cs（Settings） |
| `Farm.Inventory` | DebugPanel.cs（当前无真实引用，无需补；未来用 InventoryManager 时补） |
| `Farm.UI` / `Farm.Debug` / `Farm.Player` / `Farm.Editor` | 无外部引用（Editor 域自身引用运行时域见上表） |

## 3. 采纳方式建议

1. **顺序**：先做 P/F 目录与文件重组（无命名空间时全局态可编译）→ 再逐域采纳 NS。域之间按 §2 补 using 后任意顺序均可在每个域采纳后立即编译通过（增量可验证）。
2. **命名冲突注意**：只要 N-06B（UI SlotType→ContainerType）未执行，数据层枚举改名 N-06A 会与全局 `SlotType` 冲突——NS-08 先采纳（把 UI 枚举收进 `Farm.UI`）可解除全局重名，使 N-06A 可独立执行；二选一即可，勿两者皆无。
3. 类名复查：加命名空间后 `Item`、`ItemManager`、`Settings`、`Singleton`、`Player` 等泛名不再裸露在全局，插件/引擎类型冲突风险消除（5.2 收益点 2）。
4. ItemEditor.cs 属 `Assembly-CSharp-Editor`：运行时域类型从 Editor 程序集引用不受 asmdef 影响（当前无 asmdef），加 using 即可；若未来拆 asmdef（报告 P1-7）需 Editor 程序集显式引用运行时程序集。
