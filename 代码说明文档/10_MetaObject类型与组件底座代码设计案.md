# MetaObject 类型与组件底座代码设计案

MetaObject 四个核心类型将共享配置、运行对象、组件配置与运行组件分开。它们提供动作派生体系复用的对象构成和生命周期底座，使角色与动作都能从配置建立各自的运行组件，而不把全部能力塞进同一个类。

| 项目 | 内容 |
| --- | --- |
| 解释范围 | Assembly-CSharp，全局命名空间；MetaObjectDefinition、MetaObjectInstance、MetaObjectComponentDefinition、MetaObjectComponent，以及嵌套订阅记录 |
| 源码依据 | `Assets/Script/MetaObjects/MetaObject*.cs`；CreateInstance、AddComponent、Attach/Bind/Detach、Publish、Dispose |
| 核对基线 | c744a32b59973f9888d69447bbd2775fccf064f4；2026-10-24；相关源码无未提交差异 |
| 关联设计 | [元对象与组件 §4.1](../系统设计文档/01-通用系统/30_元对象与组件设计补充说明.md)、[架构设计案 §5、§7.11](../架构设计文档/架构设计案.md) |
| 状态 | 已核对：结构与源码行为 |
| 更新日期 | 2026-10-24 |

## 类层级与组合

| 声明类型 | 直接基类或接口 | 持有内容与主要职责 |
| --- | --- | --- |
| MetaObjectDefinition | UnityEngine.ScriptableObject | 共享静态资产，持有 MetaObjectComponentDefinition 清单和识别信息；派生类为 MetaActionDefinition |
| MetaObjectComponentDefinition | 普通抽象类，隐式 System.Object | 定义 CreateComponent 工厂；对象配置与动作配置均从它派生，不是运行组件 |
| MetaObjectInstance | 普通类，隐式 System.Object | 按具体 Type 持有 MetaObjectComponent 字典，另持有订阅表；派生类为 MetaActionInstance |
| MetaObjectComponent | 普通抽象类，隐式 System.Object | 保存 Owner 和 Preset 引用，提供生命周期钩子与受保护的对象内消息入口 |
| MetaObjectInstance.MessageSubscription | 私有嵌套类 | 由实例订阅表持有，记录订阅组件、委托和有效标记；不是另一个可挂载组件 |

MetaObjectInstance 与 MetaObjectComponent 是组合关系，二者互不继承；组件的 Owner 是归属引用。MetaObjectComponentDefinition.CreateComponent 创建运行组件，两类对象也互不继承。MetaObjectDefinition.CreateInstance 创建 MetaObjectInstance，定义资产不是运行实例本身。组件实际族与场景承载见[对象侧类型](20_对象组件与场景承载类型代码设计案.md)，动作派生见[MetaAction 类型](30_MetaAction派生类型与动作组件代码设计案.md)。

## 创建与方法归属

| 关键方法的声明类 | 调用方与下游 | 行为及结构地位 |
| --- | --- | --- |
| MetaObjectDefinition.CreateInstance | MetaObjectPreset、ActionHolderComponent → CreateRuntime、各配置 CreateComponent、实例 AddComponent | 共享的完整创建入口；派生动作定义继承此方法 |
| MetaObjectDefinition.CreateRuntime | CreateInstance；MetaActionDefinition 重写 | 默认创建普通对象，派生工厂改为动作实例 |
| MetaObjectComponentDefinition.CreateComponent | CreateInstance 调用；各具体配置重写 | 把静态配置变成独立运行组件 |
| MetaObjectInstance.AddComponent / RemoveComponent | 定义创建或运行期调用方 → 组件 Attach/Detach | 按具体类型维护唯一组件；这些方法被动作实例继承 |
| MetaObjectComponent.Attach / Bind / Unbind / Detach | 实例或场景承载 → OnAttached/OnBind/OnUnbind/OnDetached | 非虚内部调度入口调用受保护虚钩子；具体组件重写钩子 |
| MetaObjectInstance.Dispose | 场景承载；MetaActionInstance 重写后调用 base | 整体释放组合组件和订阅 |

CreateInstance 按组件配置逐项创建：空配置或空返回记录后跳过；配置侧别不匹配、创建或挂载抛异常会释放已建实例并抛出。IsActionDefinition 是定义侧虚属性，IsActionComponent 是配置侧判别；运行实例还以 IsAction 和实际组件是否为 MetaActionComponent 检查侧别。双方检查使动作组件与角色对象组件不能混挂。

AddComponent 按实际具体类型替换。同一组件重复添加不触发钩子；替换时先卸载旧组件，挂载新组件失败会移除并清理新组件，旧组件不会自动回滚恢复。拒绝清理中挂载、组件跨对象同时归属和同类型挂载回调重入。查询 GetComponent/TryGetComponent 按具体 T 精确取值，不会自动按抽象基类检索所有派生组件。

## 组件生命周期与场景边界

Attach 先赋 Owner 再调用 OnAttached。Bind 赋 Preset 后调用 OnBind，切换承载时先 Unbind；Unbind 在 finally 清掉 Preset。Detach 在回调前后取消该组件的全部订阅，并保证 Owner 清空。对象整体 Dispose 先清空构成与订阅，再逐项卸载，收集清理异常后统一抛出。

实例的 AddComponent 只挂载，不知道场景承载；运行期新增组件不自动完成 Bind。MetaObjectPreset 在 TryBind 遍历实例当前组件补做场景绑定，详见[场景承载](20_对象组件与场景承载类型代码设计案.md)。因此“组件已在字典中”和“组件已绑定到场景”是不同状态。

## 对象内通信的声明与协作

具体组件调用的 Publish/Subscribe/Unsubscribe 声明在 MetaObjectComponent，随后转发给 Owner 的内部泛型方法。实际订阅表属于 MetaObjectInstance，不属于全局事件总线；未挂载组件无法发布或订阅。

消息按精确类型同步执行订阅快照，不自动向基类或接口分发，也不缓存重放。一次发布期间新增订阅下次才收到，已取消或卸载项立即失效。单个处理器抛错被记录，其他处理器继续；此前的业务修改不回滚。解绑保留对象内订阅，卸载自动清除；依赖场景的处理器须检查绑定状态。

## 源码定位与边界

- [MetaObjectDefinition.cs](D:/myspace/Git/mygame/Assets/Script/MetaObjects/MetaObjectDefinition.cs)：定义资产、创建模板和失败清理。
- [MetaObjectComponentDefinition.cs](D:/myspace/Git/mygame/Assets/Script/MetaObjects/MetaObjectComponentDefinition.cs)：组件配置基类及工厂声明。
- [MetaObjectInstance.cs](D:/myspace/Git/mygame/Assets/Script/MetaObjects/MetaObjectInstance.cs)：组件组合、消息记录、精确类型查询和整体释放。
- [MetaObjectComponent.cs](D:/myspace/Git/mygame/Assets/Script/MetaObjects/MetaObjectComponent.cs)：Owner/Preset 归属与生命周期钩子。

该底座没有提供实例存档、全局组件注册表或跨对象消息寻址。架构要求的强制注册与公共服务不能仅由本地字典机制证明已经落实；说明对当前结构的核对不代表这些设计要求已验收。
