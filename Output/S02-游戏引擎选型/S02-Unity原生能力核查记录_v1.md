# S02 Unity 原生能力核查记录 v1

| 项目 | 内容 |
| --- | --- |
| 用途 | 核查「现行架构第 7 章的十一项基础设施」与「S02 二十八项缺口的候选方案」中，哪些能力引擎已原生提供、哪些必须项目自建，作为候选方案的证据基础 |
| 核查方式 | 逐项抓取引擎官方手册、脚本参考、官方包文档与官方仓库源码，按目标版本逐一核对 API 是否存在，并对同名页面做跨版本 200/404 探测以确定版本边界 |
| 版本口径 | 目标为引擎 6 与 2022 长期支持版两条线并行核对 |
| 结论去向 | 本文只记录核查结论；候选方案的修订落在缺口分析文档与本任务决策库 |
| 维护人 | 首席主策划 |
| 更新日期 | 2026-10-08 |

---

# 一、与缺口方案有关的关键事实

## 1. 官方对运行时界面方案的定位

引擎官方能力对照表给出的是：**运行时界面推荐传统场景内界面方案，界面工具包为替代方案**；编辑器方向相反。界面工具包的明确短板是场景内编辑、序列化事件、动画剪辑与时间轴集成；世界空间界面要到 6.2 才可用。

**对本项目的影响：** `ENG-GAP-008` 推荐候选 B（传统场景内界面方案）由「工程判断」升级为「有官方定位支撑」。本项目十四个界面以固定版式面板、列表、信息框与窗口为主，且地图点位与战场单位需要与界面叠层交互，两项都落在传统方案的强项上。

## 2. 关闭域重载会改变静态状态的语义

引擎较新版本的新项目**默认只重载场景、不重载域**。此时静态字段与非序列化字段会跨播放会话存活；关闭域重载后，编辑器中「每次播放都回到初始值」这一便利不再成立。这与域重载开启时的行为不同，且构建版本的行为与编辑器不一致。

**对本项目的影响：** 现行架构有大量常驻对象与静态约定（服务容器、数据域、随机序列位置、事件登记表）。若不做显式重置，编辑器中反复播放会把上一次会话的状态带进来。这一条在 `ENG-GAP-013` 与 `ENG-GAP-014` 的裁定中必须一并处理，改写后的架构案应补一条「常驻对象在启动引导的最早阶段显式重建，不依赖引擎的域重载提供初始状态」的约束。

## 3. 异步能力的版本分叉

引擎 6 提供可等待类型与可等待的异步操作；2022 长期支持版完全没有可等待类型，只有协程。此外可等待实例是池化的，同一个方法内不能等待两次；基于任务的续体回到主线程时至少晚一帧；WebGL 平台上线程池路径会导致浏览器不可恢复地挂起。

**对本项目的影响：** `ENG-GAP-021` 的版本基线从「可选项」变为**下游接口写法的前提**——若基线取 2022 长期支持版，则「事件场景与战斗地图按需加载」这类异步流程只能用协程或第三方异步方案，接口写法完全不同。建议在 `ENG-GAP-021` 与 `ENG-GAP-007` 的裁定中一并确定。

## 4. 对象池已有原生能力

引擎自 2021.1 起原生提供对象池类型族（泛型池、链式池、集合池等），构造参数含创建、取出、归还、销毁四个回调与容量上限，并提供活跃数与空闲数查询。缺的是游戏对象专用池、预热与场景归属，以及可寻址资源实例的池化。

**对本项目的影响：** 现行架构 7.11 把「对象池」登记为「本项不单独设立：当前版本无高频对象创建需求；性能验证表明必要时再设立」。核查结论是：**通用池已由引擎提供，无需自建；但游戏对象池的薄封装层可以现在设立**，因为战斗单位、投射物、特效实例与界面列表项都是反复创建销毁的对象。这一条应作为 `ENG-GAP-001` 裁定后第 7 章的一处修订。

## 5. 随机源的可用形态

引擎自带随机是**单一全局流**，其内部状态不透明、只能整块存取，无法按消费点分流，且旧的种子接口已废弃。可用于确定性的替代是一个数学库中的可序列化随机结构（显式状态字段、可指定种子、可由索引派生），但按消费点分流与序列位置入档仍需项目自建。系统基础库的随机不保证跨运行时版本同序列，且不是线程安全的。

**对本项目的影响：** `ENG-GAP-023` 推荐候选 A（生成类走项目自有确定性序列、表现类用引擎随机）成立；同时应在架构案写明**不得使用系统基础库的随机**，这条比现行 7.10 的表述更严。

## 6. 时间手段的限制

引擎的时间全是帧钟、真实钟与固定步，没有逻辑钟、刻度量化与刻度广播。尤其要注意：**时间缩放为零会同时停掉固定步更新与等待真实秒数的等待**，而时间上限会吞掉卡顿造成的时间差。

**对本项目的影响：** 现行架构 7.4 的「暂停只冻结表现与输入，不改变任何数据」在引擎侧**不能靠时间缩放实现**——用时间缩放会连固定步一起停，且与「战斗净时长按秒累计」冲突。这是对现行条款的一处实质性修正，需要在 `ENG-GAP-014` 的裁定里明确「暂停的实现方式与不得使用时间缩放」。

## 7. 存档、配置与序列化的能力边界

| 结论 | 对本项目的影响 |
| --- | --- |
| 引擎内置 JSON 工具不支持字典、不序列化属性、不支持多态、顶层不能是数组或基元；不能直接反序列化到引擎对象子类 | 现行五个数据域含嵌套集合与按标识引用，内置工具不足以直接承载；`ENG-GAP-005` 推荐候选 A（通用 JSON 序列化）成立 |
| 官方发布了一个第三方 JSON 序列化包，能力覆盖字典、属性、多态（多态需配类型白名单）、未知字段原样保留 | 候选 A 的落地有了官方渠道；应在架构案写明「多态反序列化必须配类型白名单」，避免不可信输入风险 |
| 某二进制序列化机制已被明令不得使用，运行时已移除实现，且官方把存档文件点名为攻击面 | 第 7 章应补一条禁止项：存档不得使用该机制 |
| 引擎官方序列化包提供版本标识与迁移接口（在版本不匹配时才调用迁移），但该包在较新版本已被标注弃用 | 版本标识与迁移的**形态**有官方参考，但承接方需要项目自定；`ENG-GAP-005` 的关闭条件里「版本标识与迁移的归属」必须明确写出 |
| 无任何原生「存档」概念：只有持久化数据目录；没有存档位；移动端可能没有优雅退出时点 | 现行 9.4「以最近一次自动保存的提交结果为准」是正确方向，应升级为架构约束：**不得把「退出时保存」当作唯一写路径** |
| CSV 是引擎的原生资源扩展名，自定义导入器**不能**默认接管该扩展名 | `ENG-GAP-004` 与 `ENG-GAP-028` 若采用「编辑器导入」路线，导入器的接管方式必须先解决（复合扩展名或显式指定导入器） |
| 资产文件不能在运行期生成（生成资产的接口属于编辑器） | 静态数据必须在构建期生成；运行期只能读，与现行 7.9「不带热重载」一致 |
| 引擎序列化不支持字典、多维与交错数组、嵌套容器，不序列化属性 | 静态数据的运行期载体若用资产，大表的字段形态受限；这支持「保留设计库表为权威源、运行期用内存形态」的候选 A |

## 8. 资源与场景的能力边界

| 结论 | 对本项目的影响 |
| --- | --- |
| 资源目录的内容永远进包、不能按资产单独卸载、也没有按目录的异步全量加载 | 与现行 6.2「常驻集启动加载、场景集按需释放」不符，不能只用资源目录实现 |
| 可寻址资源体系按句柄计数、按束卸载，**不能部分卸载**；释放后内存不会立刻回收，要等所属束计数归零；没有常驻集、没有按集合释放、没有缓存 | 「常驻集」在引擎侧没有对应概念，做法是**永不释放的句柄集合**；界面级释放要自己记账；同一标识的并发加载去重也要自建 |
| 让对象跨场景存续与隐藏标记，对可寻址资源**官方明确无效**，场景要保住必须显式持有 | 架构案第 7 章与 6.2 需要写明这条，否则实现会踩空 |
| 场景加载有同步与异步两种，同步加载会强制完成已挂起的异步操作；被挂起的操作会阻塞整个异步队列 | 现行 6.2 的「一次性切换」需要写明由异步加载加显式激活时机实现 |
| 场景卸载**不释放资产** | 6.2 的资源释放与场景卸载是两件事，要分开写 |
| 场景加载完成回调的时点在启用之后、开始之前 | 界面与场景的初始化顺序可以据此确定 |
| 跨场景存续只对根对象有效，且会带走整棵子树 | 与 `ENG-GAP-013` 的「承载对象数量以职责为限」呼应 |

## 9. 事件与日志的能力边界

| 结论 | 对本项目的影响 |
| --- | --- |
| 引擎没有跨系统事件总线；序列化事件回调最多四个参数、无返回值、强引用会阻止回收 | `ENG-GAP-006` 推荐候选 A（项目自有通道）是唯一可行路线 |
| 日志只有一个控制台与播放器日志流，没有「内容日志」概念；自定义日志处理器的接入点是替换日志处理器或订阅日志消息回调（回调可能在多线程并行触发）；崩溃报告在部分平台不提供，云端诊断服务已弃用 | `ENG-GAP-024` 推荐候选 A（统一入口加落点策略）成立；架构案应写明**日志回调必须线程安全**，并把崩溃现场的采集口径写为「尽力而为」 |

## 10. 生命周期与初始化顺序的能力边界

| 结论 | 对本项目的影响 |
| --- | --- |
| 启动回调分五个阶段，**同一阶段内的执行顺序官方明确不保证** | 现行 6.3「初始化顺序由依赖拓扑决定，不由硬编码顺序决定」不能改为依赖引擎的启动回调顺序；`ENG-GAP-003` 推荐候选 A（保留服务容器）成立 |
| 执行顺序设定只作用于组件类型、只管生命周期回调、同值即不确定，且不影响启动回调与销毁回调 | 同上；引擎的执行顺序设定不能承担依赖拓扑的职责 |
| 没有依赖图或拓扑初始化；唯一一处拓扑实现位于官方服务的内部命名空间，不可依赖 | 依赖图校验与拓扑创建必须项目自建 |
| 自定义帧循环注入是整体覆盖式的，必须基于当前循环重建并做幂等安装 | `ENG-GAP-014` 若采用「逻辑推进与帧循环分离」，推进入口的安装方式与幂等要求要在架构案写明 |
| 退出回调在强制退出与崩溃时不触发，在部分平台检测不到；编辑器内也会被忽略；进程退出事件在目标运行时下无官方依据 | 9.4 的两条路径（正常退出、异常终止）成立，且要加强「异常终止以最近一次自动保存为准」；不得依赖退出回调做存档 |

## 11. 输入的能力边界

| 结论 | 对本项目的影响 |
| --- | --- |
| 新版输入方案是官方推荐，旧版将移除；旧版无运行期改键能力 | `ENG-GAP-026` 推荐候选 A 成立 |
| 同时启用新旧两套后端会导致输入被处理两遍；新版独占时运行期界面事件收不到输入 | 架构案应写明**只启用一套**，并说明界面输入模块与新方案的配套要求 |
| 改键的覆盖项不会自动持久化，需要另存；改键操作对象必须显式释放，否则泄漏 | 7.4「改键即时生效」的落地方式要写明「覆盖项另存」与「必须释放」两条 |
| 官方不提供成品改键界面 | 改键界面属于项目实现，归设置系统 |
| 通用手柄设备不一定会被识别为标准手柄类型，需要留兼容分支 | 归代码设计案，但架构案可在 7.4 提一句 |

## 12. 表现通道的能力边界

音频、本地化与特效动画模块提供的都是**播放原语**（播放音频、按标识取文案、触发特效与动画状态），没有任何原生能力把「逻辑事件」解析成「剪辑加总线加预制体加动画状态」的组合，也没有全局音量分轨策略。

**对本项目的影响：** `ENG-GAP-025` 推荐候选 A 成立，但要把「解析层必须自建」写明：引擎提供播放原语，架构规定按标识取用，中间的解析与分轨策略是项目实现。

## 13. 与热更新无关的两项否决

- 二进制序列化机制（安全）——第 7 章补禁止项；
- 完整实体组件系统（本项目为回合制战棋，热工作集中在成批计算而非每帧海量实体；且其图形部分不支持内置渲染管线、不支持网页平台）——`ENG-GAP-002` 与 `ENG-GAP-011` 维持现推荐候选，架构案可补一句「不采用完整实体组件系统」的说明。

## 14. 三项需在改写时预登记的结论

| # | 结论 | 落点 |
| --- | --- | --- |
| 1 | 可寻址资源体系**没有缓存层**：同一标识的并发加载不做去重，句柄所有权也无归属约定。项目若不建去重层，容易出现重复加载与重复释放（重复释放会破坏引用计数） | 7.2；`ENG-GAP-007` 候选 A 的关闭条件中「加载失败的处置」应扩展为「并发加载去重与句柄所有权」 |
| 2 | 界面栈与层级**两套界面方案都没有原生实现**：引擎只提供画布排序与界面文档排序值，屏幕栈、弹窗队列、模态阻塞、层级枚举全部要自建 | 2.4 与 3.1 ARC-M08-001；`ENG-GAP-008` 的推荐候选不改变「界面栈由项目自建」这一结论，但正文要写明「引擎不提供界面栈」 |
| 3 | 界面与场景相交处的一条工程约束：界面文档与画布**不能互相嵌套**（连渲染贴图也不传递事件），因此同一界面只应使用一套界面方案 | 第 8 章；`ENG-GAP-008` 若采用候选 C（混合方案）必须一并登记这条限制 |

---

# 二、对缺口候选的修订建议

核查后需要修订的候选集中在四处，其余二十四项的推荐候选经核查成立。

| 缺口 | 修订内容 |
| --- | --- |
| `ENG-GAP-021` 引擎版本基线 | 候选 A 的正文补一条：基线取值决定异步能力的可用形态，因此基线**必须在缺口 007 的候选落地前确定**；基线一经确定，升级属于架构变更 |
| `ENG-GAP-014` 帧循环与程序推进 | 候选 A 的正文补两条：**暂停不得使用时间缩放实现**（时间缩放会连固定步一起停）；推进入口的安装必须幂等，且不依赖引擎的启动回调顺序 |
| `ENG-GAP-013` 常驻对象的跨场景存续 | 候选 A 的正文补一条：**常驻对象在启动引导的最早阶段显式重建**，不依赖引擎的域重载提供初始状态（较新版本的新项目默认只重载场景） |
| `ENG-GAP-023` 确定性与引擎随机源 | 候选 A 的正文补一条：**不得使用系统基础库的随机**（不保证跨运行时版本同序列且非线程安全） |

另有三处属**架构案第 7 章正文层面的修订**，不改变候选，只需在改写时写入：

| # | 修订 | 落点 |
| --- | --- | --- |
| 1 | 「对象池」由「本项不单独设立」改为「通用池由引擎提供，项目只设游戏对象池的薄封装层」 | 7.11 |
| 2 | 补禁止项：存档不得使用已被移除实现的二进制序列化机制 | 7.1 与 8.2 |
| 3 | 补约束：日志订阅回调必须线程安全；崩溃现场采集为尽力而为；不得依赖退出回调做存档 | 7.7 与 9.4 |

---

# 三、官方来源

核查所依据的官方页面按主题归档如下，均为本次实际抓取。

| 主题 | 来源 |
| --- | --- |
| 执行顺序与帧循环 | [执行顺序](https://docs.unity3d.com/6000.0/Documentation/Manual/execution-order.html)、[脚本执行顺序](https://docs.unity3d.com/6000.0/Documentation/Manual/script-execution-order.html)、[自定义帧循环](https://docs.unity3d.com/6000.0/Documentation/Manual/player-loop-customizing.html)、[启动回调](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/RuntimeInitializeOnLoadMethodAttribute.html)、[启动回调阶段](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/RuntimeInitializeLoadType.html) |
| 域重载与静态状态 | [域重载](https://docs.unity3d.com/6000.0/Documentation/Manual/domain-reloading.html)、[可配置进入播放模式](https://docs.unity3d.com/6000.0/Documentation/Manual/configurable-enter-play-mode.html) |
| 异步 | [可等待类型](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Awaitable.html)、[异步等待支持](https://docs.unity3d.com/6000.0/Documentation/Manual/async-await-support.html)、[协程](https://docs.unity3d.com/6000.0/Documentation/Manual/Coroutines.html) |
| 序列化与配置 | [脚本序列化规则](https://docs.unity3d.com/6000.0/Documentation/Manual/script-serialization-rules.html)、[内置 JSON 工具](https://docs.unity3d.com/6000.0/Documentation/Manual/json-serialization.html)、[自定义导入器](https://docs.unity3d.com/6000.0/Documentation/Manual/ScriptedImporters.html)、[导入器扩展名接管](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/AssetImporters.ScriptedImporterAttribute-overrideFileExtensions.html)、[第三方 JSON 序列化包](https://docs.unity3d.com/Packages/com.unity.nuget.newtonsoft-json@3.2/manual/index.html)、[不兼容 API](https://docs.unity3d.com/6000.6/Documentation/Manual/dotnet-incompatible-api.html) |
| 存档落点 | [持久化数据目录](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Application-persistentDataPath.html)、[退出事件](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Application-quitting.html) |
| 资源 | [运行期资源管理](https://docs.unity3d.com/Manual/assets-managing-introduction.html)、[资源目录的代价](https://docs.unity3d.com/2022.3/Documentation/Manual/UnderstandingPerformanceResourcesFolder.html)、[可寻址资源的内存管理](https://docs.unity3d.com/Packages/com.unity.addressables@2.6/manual/MemoryManagement.html) |
| 场景 | [场景管理器](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/SceneManagement.SceneManager.html)、[异步操作激活时机](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/AsyncOperation-allowSceneActivation.html) |
| 随机 | [数学库随机结构](https://docs.unity3d.com/Packages/com.unity.mathematics@1.3/api/Unity.Mathematics.Random.html)、[系统基础库随机的版本差异](https://learn.microsoft.com/en-us/dotnet/api/system.random) |
| 时间 | [时间缩放](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Time-timeScale.html)、[时间上限](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Time-maximumDeltaTime.html) |
| 输入 | [输入总览](https://docs.unity3d.com/6000.0/Documentation/Manual/input-introduction.html)、[旧版输入](https://docs.unity3d.com/6000.0/Documentation/Manual/InputLegacy.html)、[改键覆盖的保存](https://docs.unity3d.com/Packages/com.unity.inputsystem@6.7/manual/save-load-rebinds.html) |
| 日志与崩溃 | [日志处理器](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/ILogHandler.html)、[多线程日志回调](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Application-logMessageReceivedThreaded.html)、[崩溃报告](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/CrashReport.html) |
| 事件与表现 | [序列化事件](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Events.UnityEvent.html)、[音频混音器](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Audio.AudioMixer.html)、[本地化包](https://docs.unity3d.com/Packages/com.unity.localization@1.5/manual/CSV.html)、[特效发送事件](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/VFX.VisualEffect.SendEvent.html) |
| 对象池 | [泛型对象池](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Pool.ObjectPool_1.html)、[可复用代码](https://docs.unity3d.com/6000.0/Documentation/Manual/performance-reusable-code.html) |
| 界面方案定位 | [界面系统对照](https://docs.unity3d.com/6000.3/Documentation/Manual/UI-system-compare.html)、[从旧方案迁移](https://docs.unity3d.com/6000.0/Documentation/Manual/UIE-Transitioning-From-UGUI.html) |
| 依赖注入 | [官方服务核心的内部依赖图](https://docs.unity3d.com/Packages/com.unity.services.core@1.13/api/Unity.Services.Core.Internal.html)、[第三方容器](https://raw.githubusercontent.com/hadashiA/VContainer/master/README.md) |
