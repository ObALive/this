# MetaObject 类型与组件底座代码设计案

元对象底座将共享配置与个体状态分开：定义资产描述组件清单，运行实例持有各自组件与对象内部消息订阅。它统一处理挂载、场景绑定、卸载和释放，让坐标、属性、量表与动作容器按相同生命周期协作。

| 项目 | 内容 |
| --- | --- |
| 解释范围 | Assembly-CSharp，全局命名空间；MetaObjectDefinition、MetaObjectInstance、MetaObjectComponentDefinition、MetaObjectComponent 的工厂、组件归属与同步消息 |
| 源码依据 | MetaObjectDefinition.CreateInstance；MetaObjectInstance.AddComponent/RemoveComponent/Publish/Dispose；MetaObjectComponent.Attach/Bind/Unbind/Detach；文件入口见文末实现定位 |
| 核对基线 | 工程提交 `bf1b4d8caf90a8d6e10de503f1e682b96bb3b936`；2026-10-30 核对源码与静态资产 |
| 关联设计 | [元对象与组件 §4.1](../系统设计文档/01-通用系统/30_元对象与组件设计补充说明.md)、[架构设计案 §5、§7.11](../架构设计文档/架构设计案.md) |
| 状态 | 已核对：源码声明、调用链与静态资产绑定 |
| 更新日期 | 2026-10-30 |

## 类型归属与持有关系

这些类型均由 `Assembly-CSharp.csproj` 收入运行程序集。`MetaObjectDefinition` 继承 ScriptableObject，保存标识、显示名与 SerializeReference 组件定义清单。`MetaObjectComponentDefinition` 是可序列化抽象配置类，通过抽象方法 `CreateComponent` 创建组件。

`MetaObjectInstance` 是普通 C# 类，持有“具体 Type → MetaObjectComponent”的字典和私有消息订阅。`MetaObjectComponent` 是普通 C# 抽象基类，保存 Owner 与 Preset 引用。配置资产共享；每次工厂调用建立独立运行实例与组件。

`MetaObjectId` 表示定义标识；`RuntimeId` 在运行实例创建时生成 Guid 的 N 格式字符串，区分使用相同定义的多个角色或动作。Router 报文以 RuntimeId 引用运行个体，并携带定义标识供读取。

## 定义创建与组件挂载

`MetaObjectDefinition.CreateInstance` 先调用可重写的 `CreateRuntime`，再按配置清单创建并挂载组件。普通定义产生 MetaObjectInstance，动作定义通过派生工厂产生 MetaActionInstance。对象侧与动作侧的组件归属限制由 AddComponent 按实际组件类型与实例 IsAction 统一判断。

组件配置负责提供创建输入，定义工厂直接调用 CreateComponent 与 AddComponent。创建及挂载中的异常沿调用栈传播；清单为空时形成空实例。

`AddComponent` 使用实际具体类型作为键。相同组件实例重复添加时返回 false 并保持生命周期；相同具体类型的另一实例进入时先移出并 Detach 前一组件，再挂载新组件，返回 false；新增类型返回 true。挂载入口设置 Owner 并调用 OnAttached，回调异常向调用者传播。

查询 `GetComponent<T>`、`TryGetComponent<T>` 和 `HasComponent<T>` 按 typeof(T) 精确匹配。动作实例在读取构造器时另行使用类型筛选，构造器读取见 [30 动作专题](30_MetaAction派生类型与动作组件代码设计案.md)。

## 生命周期与资源清理

| 底座入口 | 回调与可用状态 | 责任 |
| --- | --- | --- |
| Attach | 先设置 Owner，再 OnAttached | 建立组件归属与对象内部订阅 |
| Bind | 必要时先 Unbind，再设置 Preset 并 OnBind | 将运行组件连接到场景承载 |
| Unbind | OnUnbind，finally 清空 Preset | 释放场景关联，保留组件归属 |
| Detach | 停用该组件的全部订阅，Unbind、OnDetached，finally 清空 Owner | 解除场景与对象归属，处理派生资源 |

`RemoveComponent<T>` 先从字典移出组件，再执行 Detach。`UnbindAll` 使用组件快照，逐项解除场景绑定。`Dispose` 先清空组件字典并停用全部订阅，再遍历快照执行 Detach；组件清理中的异常沿调用栈传播。

组件的状态保留策略取决于各自回调：属性在解绑时保留来源修正、卸载时清空；量表在解绑时保留值、卸载时清空外部监听；动作容器在解绑时终止所持动作；纹理组件解绑时释放显示实例。场景承载的创建与重建责任见 [20 场景专题](20_对象组件与场景承载类型代码设计案.md)。

## 对象内部消息

组件通过受保护的 Publish、Subscribe、Unsubscribe 调用 Owner 的内部方法，通信操作在组件挂载期间使用。同一组件的同一委托重复注册返回 false。

发布按消息泛型 T 精确匹配，按订阅顺序同步执行当前订阅快照。新增订阅从下一次发布参与；取消或卸载使快照中的订阅立即失效。嵌套发布使用各自快照。处理器异常沿调用栈传播，已经发生的业务修改保留。

`CellChanged` 与 `MovementCompleted` 是对象内部通知；前者说明坐标改变，后者说明主动移动完成。`MovementFacingComponent` 订阅主动移动通知并更新显示朝向。消息通道的寻址范围是当前 Owner；跨动作执行使用 [90 报文路由专题](90_ActionRouterManager与键值报文执行代码设计案.md) 的 Router 入口。

## 数据范围

底座的字典、组件实例、运行 ID 和订阅属于运行状态。共享定义保存创建输入，场景承载持有运行实例；持久化流程需要以实际保存入口为依据。本专题覆盖工厂、组件归属、同步通知和清理。

## 实现定位

| 源码或资产 | 主要定位 |
| --- | --- |
| [MetaObjectDefinition.cs](D:/myspace/Git/mygame/Assets/Script/MetaObjects/MetaObjectDefinition.cs) | CreateInstance、CreateRuntime |
| [MetaObjectInstance.cs](D:/myspace/Git/mygame/Assets/Script/MetaObjects/MetaObjectInstance.cs) | RuntimeId、组件字典、消息分发与 Dispose |
| [MetaObjectComponentDefinition.cs](D:/myspace/Git/mygame/Assets/Script/MetaObjects/MetaObjectComponentDefinition.cs) | CreateComponent 工厂约定 |
| [MetaObjectComponent.cs](D:/myspace/Git/mygame/Assets/Script/MetaObjects/MetaObjectComponent.cs) | 生命周期入口与通信封装 |
| [CellChanged.cs](D:/myspace/Git/mygame/Assets/Script/MetaObjects/CellChanged.cs) | 坐标变化载荷 |
| [MovementCompleted.cs](D:/myspace/Git/mygame/Assets/Script/MetaObjects/MovementCompleted.cs) | 主动移动载荷 |
| [Assembly-CSharp.csproj](D:/myspace/Git/mygame/Assembly-CSharp.csproj) | 程序集 Compile 依据 |

核对依据为上述提交的源码、工程配置与静态资产。文档状态表示所述实现已完成对照；编译、播放、画面与交互的运行验证属于独立验证范围。
