"""经过人工归纳的源码目录。新增类型须补充解释；禁止把发现机制当作完整 C# 编译器。"""
import re
from pathlib import Path

S = "Assets/Script/"
M = S + "MetaObjects/"
B = S + "Battle/"
C = S + "Components/"
I = S + "Inventory/Data/"
P = S + "Player/"
U = S + "UI/"
DOC = Path(__file__).resolve().parent.parent.as_posix() + "/"

TABLES = {}
# 用户明确排除：固定两向表现选项，不作为可持续增长的内容维度登记。
EXCLUDED_ENUMS = {"HorizontalFacing"}


def table(name, tier, mode, rule, steps, limitations, columns=None, constraints=None):
    TABLES[name] = dict(title=name, tier=tier, mode=mode, rule=rule, steps=steps,
                       limitations=limitations, columns=columns or {}, constraints=constraints or [])


table("元对象组件", "核心扩展点", "派生类型 + 配置工厂 + 组合装配",
      "一行代表一对对象侧组件定义与运行组件。抽象基类、场景 MonoBehaviour、动作侧组件不重复列入。",
      "新增 MetaObjectComponent 与 MetaObjectComponentDefinition 派生类型，实现 CreateComponent；通过 SerializeReference 配入定义资产；依赖场景时实现绑定/解绑/卸载。",
      "字典使用具体 Type 作键；同类型重复添加替换旧组件。普通对象与动作组件不能混挂；继承关系不意味着可用基类 GetComponent 查询。",
      {"definition_type": "TEXT", "runtime_base": "TEXT", "dependencies": "TEXT"})
table("动作构造器", "核心扩展点", "动作组件派生 + 报文协议",
      "一行代表一个具体 ActionPacketBuilder 及其定义工厂，属于动作侧组件家族。",
      "新增构造器/定义对，明确 Operation、目标与业务参数；实现匹配执行器，创建动作资产并接入槽位。",
      "MetaActionInstance 只取首个 ActionPacketBuilder；Cell 查询使用 IMovementCapability，Object 通过 TargetRange 与 ObjectTargeting 查询，不是完整通用范围策略。",
      {"definition_type": "TEXT", "operation_name": "TEXT", "default_target": "TEXT", "timing_source": "TEXT"})
table("效果执行器", "核心扩展点", "ActionEffectExecutor 派生组件",
      "一行代表一种 Router 可选择的同步执行实现，不按每个技能资产重复。",
      "继承 ActionEffectExecutor，实现 Operation/Execute；挂到 Router 同一 GameObject 并启用，保持操作名与构造器一致。",
      "Router 选取同物体首个启用且字符串完全匹配的执行器；无匹配会异常。同操作多个实现不是显式优先级策略。",
      {"operation_name": "TEXT", "mount_point": "TEXT", "writes": "TEXT"})
table("目标类型", "核心扩展点", "枚举 + 目标编码 + 输入/查询分支",
      "一行代表 ActionTargetKind 的协议选项。",
      "追加枚举值，更新 Outlet 目标编码、MetaActionInstance 目标查询、选择控制器、执行器解析和 UI。",
      "当前为 Cell、None、Object；Object 已接入敌对对象选取，方向或区域选取尚未实现。",
      {"enum_type": "TEXT", "numeric_value": "INTEGER", "encoding": "TEXT"})
table("报文操作", "核心扩展点", "操作名注册契约",
      "一行代表一条构造器→操作字符串→执行器的实现链。表间用外键维护引用。",
      "同步登记构造器与执行器，操作名保持 Ordinal 大小写一致，配置目标与后摇并完成场景接线。",
      "这里是开发目录，游戏运行时不读取该表；运行匹配仍使用源码 Operation 属性。",
      {"builder_id": 'TEXT REFERENCES "动作构造器"(id)', "executor_id": 'TEXT REFERENCES "效果执行器"(id)',
       "target_kind_id": 'TEXT REFERENCES "目标类型"(id)', "required_request": "TEXT", "result_fields": "TEXT"})
table("请求字段", "核心扩展点", "Dictionary<string, object> 字段契约",
      "一行代表一个请求报文字段键；区分声明、生成、读取和只随日志保存。",
      "确认唯一键、值类型、写入者与读取者；业务字段通常在构造器生成，由执行器读取；公共上下文由 Outlet 补齐。",
      "当前无强类型 Schema 或集中校验；Get<T> 为直接强转，缺键或类型不符可抛异常；Cause 只有常量声明。",
      {"constant_name": "TEXT", "value_type": "TEXT", "requirement": "TEXT", "producer": "TEXT", "consumer": "TEXT", "encoding": "TEXT"})
table("结果字段", "核心扩展点", "执行结果字典字段契约",
      "一行代表 Router 或执行器写入结果日志的字段键。",
      "执行器向 result 写入有明确类型与条件的字段；Router 保留快照并写日志。",
      "结果字段目前为字符串字面量，无公共常量表；日志形成在时间轴 CompleteAction 之前，不是完整状态回放。",
      {"value_type": "TEXT", "producer": "TEXT", "presence_condition": "TEXT"})
table("对象消息", "核心扩展点", "类型化 Owner 内部消息",
      "一行代表一个已声明并发布的对象内部消息类型，不包括普通事件委托。",
      "定义消息载荷；组件调用 Publish<T>/Subscribe<T>；按挂载与卸载生命周期管理订阅。",
      "只在同一 Owner 内同步传播，按精确消息类型匹配；不是跨对象全局事件总线。",
      {"payload": "TEXT", "publisher": "TEXT", "subscriber": "TEXT"})
table("固定属性", "核心扩展点", "枚举索引 + 固定字段/数组",
      "一行代表 CharacterAttribute 的索引契约，而不是某个角色的属性值。",
      "在枚举末尾追加属性，补配置字段、构造参数与 baseValues；修正 SetModifier 的硬编码归零判断，更新消费者与 UI。",
      "当前数组长度为 3，归零检测直接访问 values[0..2]。只加枚举会越界或留下错误状态；不要重排已序列化枚举。",
      {"enum_type": "TEXT", "numeric_value": "INTEGER", "storage": "TEXT", "consumer": "TEXT"})
table("标记键", "核心扩展点", "按名称配置的字符串键",
      "一行代表有源码/资产依据的通用标记键，不枚举任意可能的字符串。",
      "定义稳定的大小写敏感键，配置初值，明确消费端与允许值；需要关系规则时另行实现。",
      "字典可以保存任意字符串；已有 FactionTag 业务帮助类仅承认 Ally 与 Enemy。",
      {"value_domain": "TEXT", "consumer": "TEXT"})
table("标记取值", "核心扩展点", "标记键下的命名值",
      "一行代表指定键下已使用的具体技术取值。",
      "登记所属键与取值，同步扩展业务校验、关系查询和显示；通用 SetTag 本身不校验值域。",
      "FactionTag 的 TryGetFaction 有显式白名单，不能仅写入新字符串就视为有效阵营。",
      {"tag_key_id": 'TEXT REFERENCES "标记键"(id)', "stored_value": "TEXT", "recognizer": "TEXT"},
      ['UNIQUE(tag_key_id,stored_value)'])
table("量表标识", "核心扩展点", "字符串用途标识 + 消费约定",
      "一行代表已配置并被代码识别的 MeterId，不记录角色的具体血量。",
      "约定新 MeterId 与增减/显示入口；若要求同一对象同时有多个量表，先调整容器结构或类型区分。",
      "MetaObjectMeterComponent 按具体 Type 存储，一个对象只能保留一个；Health 显示硬编码筛选名称，已接固定伤害，治疗/死亡入口未实现。",
      {"component_type": "TEXT", "value_type": "TEXT", "consumer": "TEXT"})
table("地形标识", "核心扩展点", "TileBase→TerrainId 映射",
      "一行代表有当前源码或场景配置依据的 TerrainId，不逐个记录地图格子或贴图。",
      "在 TilemapManager 的 terrainMappings 配置 TileBase/字符串，或调整默认值；结算差异需新增消费者。",
      "当前所有存在的目的格同等可用；MovementRange 不读取 TerrainId 做阻挡、寻路或成本结算。场景映射为空。",
      {"mapping_source": "TEXT", "consumer": "TEXT"})
table("物品组件", "旧体系扩展点", "ItemComponent 接口 + 泛型配置工厂",
      "一行代表旧物品系统的具体数据组件及其配置类型，不与 MetaObjectComponent 混为同一体系。",
      "实现 ItemComponent、ItemComponentData<T> 工厂与配置库 SO；更新 ComponentRef 解析和装配调用。",
      "ItemInstance 使用 typeof(T) 作为键；InventoryManager 当前只识别 InventoryComponentData_SO，不是通用配置工厂注册表。",
      {"definition_type": "TEXT", "asset_type": "TEXT", "assembly_path": "TEXT"})
table("背包槽位", "旧体系扩展点", "SlotType + BaseInventorySlot 派生 + switch 工厂",
      "一行同时表达槽位枚举判别与对应实现，避免把枚举声明当成可用功能。",
      "追加 SlotType，实现 BaseInventorySlot 两个操作，补 InventoryComponent.CreateSlots 分支与 settings 解释。",
      "Grid/Secure 构造被注释；EquipmentSlot 能创建但放置判断固定 false，快速放置抛 NotImplementedException。",
      {"enum_type": "TEXT", "numeric_value": "INTEGER", "implementation_type": "TEXT", "factory_state": "TEXT"})
table("物品分类", "旧体系扩展点", "ItemType 枚举判别值",
      "一行代表 ItemDetails/ItemInstance 使用的序列化分类值，管理代码索引而非物品内容。",
      "在枚举末尾追加并核对资产数字值与各消费端；具体行为仍要在组件/执行入口实现。",
      "当前多数只有分类声明，不能推导出工具、武器或护甲行为已实现；Player 中旧工具分支在块注释里。",
      {"enum_type": "TEXT", "numeric_value": "INTEGER", "consumer": "TEXT"})
table("容器分类", "旧体系扩展点", "ContainerType 枚举语义",
      "一行代表 SlotUI 的容器语义字段选项。",
      "追加枚举值并补相应容器 UI 与交互逻辑，核对序列化兼容。",
      "当前 SlotUI 声明 containerType 字段，没有按 Bag/Box/Shop 实现不同交互分支。",
      {"enum_type": "TEXT", "numeric_value": "INTEGER", "consumer": "TEXT"})
table("动作结果", "辅助契约（有限结果集）", "动作领域返回码",
      "一行代表 ActionResult 值；这是可演化的协议结果集，不是随开发自然增量的玩法内容。",
      "新增返回码需更新生命周期成功条件、调用者处理、移动返回值映射与日志解释。",
      "只有 Succeeded 被生命周期视为生效成功；适配层默认映射 ActionRejected，不能只追加枚举。",
      {"enum_type": "TEXT", "numeric_value": "INTEGER", "producer": "TEXT", "adapter_mapping": "TEXT"})
table("动作相态", "辅助契约（有限状态机）", "MetaActionPhase 状态机",
      "一行代表动作生命周期状态。状态不是技能类型或内容变体。",
      "修改状态集时同时更新所有状态迁移、重复执行/终止判断和选择器就绪条件。",
      "相态由 MetaActionLifecycle 统一写入；Idle 是默认枚举初值，终止后需要重建实例才能重用。",
      {"enum_type": "TEXT", "numeric_value": "INTEGER", "entry_condition": "TEXT"})
table("移动返回值", "辅助契约（输入兼容结果）", "CellMoveResult 适配返回码",
      "一行代表输入/场景移动适配层的兼容结果，不与 ActionResult 混合。",
      "更新 CharacterMovementController 的结果映射方法及消费端提示，保持领域码与适配码语义一致。",
      "该集合服务场景输入兼容，不建议作为独立内容增长目标。",
      {"enum_type": "TEXT", "numeric_value": "INTEGER", "domain_result": "TEXT"})


def declaration(symbol):
    return r"\b(?:class|struct|interface)\s+" + re.escape(symbol) + r"\b"


def enum(index, path, name):
    match = re.search(r"\benum\s+" + name + r"\s*\{([^}]*)\}", index[path], re.S)
    if not match:
        raise ValueError(f"枚举缺失: {path}/{name}")
    value = -1
    result = []
    for token in match[1].split(','):
        token = token.strip()
        if not token:
            continue
        member, *explicit = token.split('=')
        member = member.strip()
        value = int(explicit[0].strip(), 0) if explicit else value + 1
        result.append((member, value))
    return result


def records(root, index):
    out = []

    def add(category, code, label, summary, path, pattern=None, status="已实现", limits="", extra=None, refs=(), doc=""):
        spec = TABLES[category]
        row = dict(id=code, code_name=code, display_name=label, summary=summary, status=status,
                   extension_steps=spec["steps"], limitations=limits or spec["limitations"],
                   evidence=[(path, pattern or declaration(code)), *refs], reference_doc=DOC + doc if doc else "")
        row.update(extra or {})
        out.append((category, row))

    components = [
        ("SceneCoordinateComponent", "逻辑坐标组件", "持有格子坐标；SetCell 定位，MoveToCell 追加主动移动通知；已绑定时同步场景位置。", "MetaObjectComponent", "MetaObjectPreset/Grid"),
        ("SceneTextureComponent", "纹理与动画承载组件", "按动画预制体、Sprite、纹理路径优先级绑定显示，持有左右朝向并管理实例释放。", "MetaObjectComponent", "MetaObjectPreset/SpriteRenderer/Animator"),
        ("AttributeComponent", "固定属性组件", "保存三项基础值与按来源排序汇总的修正，不承担属性对应的业务公式。", "MetaObjectComponent", "CharacterAttribute"),
        ("MovementFacingComponent", "主动移动转向组件", "订阅 Owner 的 MovementCompleted，根据水平位移调用纹理组件调整朝向。", "MetaObjectComponent", "MovementCompleted/SceneTextureComponent"),
        ("MovementActionComponent", "独立移动动作持有组件", "通过 ActionHolderComponent 持有独占动作实例；执行出口固定使用 Movement 槽位标识。", "ActionHolderComponent", "MetaActionDefinition/ActionPacketOutlet"),
        ("BasicSkillSlotsComponent", "四槽动作持有组件", "每角色每槽创建独占动作实例，定义共享；发送时使用 0..3 的槽序号字符串。", "MetaObjectComponent", "MetaActionDefinition[4]/ActionPacketOutlet"),
        ("MetaObjectMeterComponent", "通用量表组件", "包装 MeterComponent 提供上下限、增减钳位与变化通知，MeterId 用于用途识别。", "MetaObjectComponent", "MeterComponent"),
        ("MetaObjectTagComponent", "通用标记组件", "使用 Ordinal 字符串字典持有键值标记，支持查询、设置、移除与只读视图。", "MetaObjectComponent", "无场景依赖"),
    ]
    for code, label, summary, base, deps in components:
        path = M + ("MovementActionComponent" if code == "MovementActionComponent" else code) + ".cs"
        refs = [(path, declaration(code + "Definition")), (M + "MetaObjectInstance.cs", r"public bool AddComponent\(")]
        limits = TABLES["元对象组件"]["limitations"]
        if code == "BasicSkillSlotsComponent": limits += " Capacity=4；扩槽还需调整数组、输入数字键与按钮构建。"
        if code == "MetaObjectMeterComponent": limits += " 多个用途量表不能以同类型并列挂载。"
        if code == "AttributeComponent": limits += " 三元素数组与归零检查硬编码。"
        add("元对象组件", code, label, summary, path, limits=limits,
            extra=dict(definition_type=code+"Definition", runtime_base=base, dependencies=deps), refs=refs,
            doc="20_对象组件与场景承载类型代码设计案.md" if code not in ("BasicSkillSlotsComponent", "MetaObjectMeterComponent", "MetaObjectTagComponent") else ("75_量表组件与生命显示代码设计案.md" if code == "MetaObjectMeterComponent" else "10_MetaObject类型与组件底座代码设计案.md"))

    for prefix, target, label, writes in [("Movement", "Cell", "地格移动", "SceneCoordinateComponent.MoveToCell；before/after"), ("Wait", "None", "无目标待机", "无对象状态写入；成功后生命周期完成时间轴回排")]:
        builder = prefix + "PacketBuilder"
        executor = prefix + "EffectExecutor"
        add("动作构造器", builder, label+"报文构造器", "继承通用 Build，只提供 Operation 字符串；目标与后摇配置由定义工厂传入。", B+"ActionPacketBuilders.cs",
            extra=dict(definition_type=builder+"Definition", operation_name=prefix, default_target=target, timing_source="BattleBehaviorDefinition.Recovery"),
            refs=[(B+"ActionPacketBuilders.cs", declaration(builder+"Definition"))], doc="30_MetaAction派生类型与动作组件代码设计案.md")
        add("效果执行器", executor, label+"共享执行器", "解析目的格并校验移动能力，成功后修改坐标。" if prefix == "Movement" else "直接返回 Succeeded；不在执行器内手动推进时间轴。", B+executor+".cs",
            extra=dict(operation_name=prefix, mount_point="ActionRouterManager 同物体的启用组件", writes=writes), doc="90_ActionRouterManager与键值报文执行代码设计案.md")

    for member, value in enum(index, B+"MetaActionComponents.cs", "ActionTargetKind"):
        descriptions = {"Cell": ("地格目标", "Outlet 写入 x,y 字符串，构造器查询与选择分支使用 IMovementCapability。", "target: string，InvariantCulture 十进制 x,y"), "None": ("无目标", "Outlet 移除 target；SkillSelectionController 走无目标确认路径。", "不存在 target 键"), "Object": ("对象目标", "Outline 表示整片射程，仅高亮合法敌方对象格；按同一对象按下松开确认。", "target: MetaObjectInstance.RuntimeId 字符串")}
        if member not in descriptions: raise ValueError("待补目标类型解释: " + member)
        label, summary, encoding = descriptions[member]
        add("目标类型", member, label, summary, B+"MetaActionComponents.cs", r"\benum ActionTargetKind\b", extra=dict(enum_type="ActionTargetKind", numeric_value=value, encoding=encoding), refs=[(B+"ActionPackets.cs", r"if \(action.TargetKind == ActionTargetKind.Cell\)")])
    for prefix, target in [("Movement", "Cell"), ("Wait", "None")]:
        add("报文操作", prefix, prefix+"操作契约", "将动作构造器与共享执行器通过操作名关联；目标类型为当前默认配置。", B+"ActionPacketBuilders.cs", r'Operation => "'+prefix+r'"',
            extra=dict(builder_id=prefix+"PacketBuilder", executor_id=prefix+"EffectExecutor", target_kind_id=target,
                       required_request="operation,targetKind,recovery；标准出口另补 source,sourceDefinition,action,actionDefinition,opportunity,slot" + (",target" if target == "Cell" else ""),
                       result_fields="status,before,after；异常可含 error,exception" if prefix == "Movement" else "status；异常可含 error,exception"),
            refs=[(B+prefix+"EffectExecutor.cs", r'Operation => "'+prefix+r'"'), ("Assets/Scenes/PersistanceScene.unity", "m_Name: ActionRouter")], doc="90_ActionRouterManager与键值报文执行代码设计案.md")

    fields = [
        ("Operation", "operation", "操作标识", "string", "通用构造器生成；Router 必需", "ActionPacketBuilder.Build", "ActionRouterManager.Send", "Ordinal 操作字符串", "已实现"),
        ("TargetKind", "targetKind", "目标指向性", "string", "通用构造器生成", "ActionPacketBuilder.Build", "当前随日志保存；选择分支读取动作属性而非该字段", "ActionTargetKind.ToString()", "已实现"),
        ("Recovery", "recovery", "动作后摇", "double", "生命周期执行必需", "ActionPacketBuilder.Build", "MetaActionInstance.ExecutePacket", "游戏秒；BattleBehaviorDefinition.Recovery", "已实现"),
        ("SourceDefinition", "sourceDefinition", "来源定义标识", "string", "标准 Outlet 补齐", "ActionPacketOutlet.Send", "当前随日志保存", "owner.MetaObjectId", "已实现"),
        ("Source", "source", "来源运行标识", "string", "标准 Outlet 补齐；来源解析必需", "ActionPacketOutlet.Send", "ActionRouterManager.ResolveActor/ResolveMovement", "owner.RuntimeId", "已实现"),
        ("Target", "target", "实际目标", "string", "Cell/Object 目标存在；None 目标移除", "ActionPacketOutlet.Send", "Cell: ActionPacket.GetCell；Object: ActionRouterManager.ResolveTarget", "Cell: InvariantCulture x,y；Object: RuntimeId", "已实现"),
        ("Action", "action", "动作运行标识", "string", "标准 Outlet 补齐", "ActionPacketOutlet.Send", "当前随日志保存", "action.RuntimeId", "已实现"),
        ("ActionDefinition", "actionDefinition", "动作定义标识", "string", "标准 Outlet 补齐", "ActionPacketOutlet.Send", "当前随日志保存", "action.MetaObjectId", "已实现"),
        ("Opportunity", "opportunity", "行动机会标识", "long", "标准 Outlet 补齐", "ActionPacketOutlet.Send", "当前随日志保存；时间轴校验直接使用 context.OpportunityId", "ActionExecutionContext.OpportunityId", "已实现"),
        ("Cause", "cause", "因果来源预留键", "未约定", "只有常量声明", "当前无写入者", "当前无读取者", "尚无值类型与因果链规则", "仅声明"),
        ("Slot", "slot", "发送槽位标识", "string", "标准 Outlet 补齐", "ActionHolderComponent/BasicSkillSlotsComponent → ActionPacketOutlet.Send", "当前随日志保存", "独立移动用 Movement；技能槽用 0..3", "已实现"),
    ]
    for constant, key, label, value_type, required, producer, consumer, encoding, status in fields:
        add("请求字段", key, label, "公共键值请求的技术字段；" + required + "。", B+"ActionPackets.cs", r'\b'+constant+r'\s*=\s*"'+key+r'"', status=status,
            extra=dict(constant_name="ActionPacket."+constant, value_type=value_type, requirement=required, producer=producer, consumer=consumer, encoding=encoding),
            doc="90_ActionRouterManager与键值报文执行代码设计案.md")
    results = [
        ("status", "处理状态", "string", "ActionRouterManager.Send/finally", "进入 Send 并完成请求快照复制后，由 finally 写入 ActionResult.ToString()", "ActionRouterManager.cs"),
        ("error", "异常消息", "string", "ActionRouterManager.Send/catch", "捕获到执行阶段异常", "ActionRouterManager.cs"),
        ("exception", "异常类型", "string", "ActionRouterManager.Send/catch", "捕获到执行阶段异常，保存异常类型名称", "ActionRouterManager.cs"),
        ("before", "移动前坐标", "string", "MovementEffectExecutor.Execute", "通过移动校验后、提交坐标前", "MovementEffectExecutor.cs"),
        ("after", "移动后坐标", "string", "MovementEffectExecutor.Execute/finally", "进入坐标提交 try 后，即使提交或消息处理异常也尝试读取坐标", "MovementEffectExecutor.cs"),
    ]
    for key, label, value_type, producer, condition, file in results:
        add("结果字段", key, label, condition+"；结果保存为只读容器快照。", B+file, r'result\["'+key+r'"\]', extra=dict(value_type=value_type, producer=producer, presence_condition=condition), doc="90_ActionRouterManager与键值报文执行代码设计案.md")

    add("动作构造器", "FixedDamagePacketBuilder", "固定伤害报文构造器", "提供 Object 指向性与 TargetRange，Build 写入独立的固定 damage 和 range 参数，不读取角色属性。", B+"FixedDamagePacketBuilder.cs",
        extra=dict(definition_type="FixedDamagePacketBuilderDefinition", operation_name="FixedDamage", default_target="Object", timing_source="BattleBehaviorDefinition.Recovery"),
        refs=[(B+"FixedDamagePacketBuilder.cs", declaration("FixedDamagePacketBuilderDefinition"))], doc="95_对象指向与固定伤害代码设计案.md")
    add("效果执行器", "FixedDamageEffectExecutor", "对象固定伤害执行器", "复用 ObjectTargeting 的敌我、量表与射程判定，调用 Health.Modify(-damage) 并记录生命变化。", B+"FixedDamageEffectExecutor.cs",
        extra=dict(operation_name="FixedDamage", mount_point="ActionRouterManager 同物体的启用组件", writes="MetaObjectMeterComponent.Modify；healthBefore/healthAfter/appliedDamage"), doc="95_对象指向与固定伤害代码设计案.md")
    add("报文操作", "FixedDamage", "固定伤害操作契约", "构造器、对象目标与执行器共同组成固定伤害链，成功后由既有生命周期完成后摇回排。", B+"FixedDamagePacketBuilder.cs", r'Operation => "FixedDamage"',
        extra=dict(builder_id="FixedDamagePacketBuilder", executor_id="FixedDamageEffectExecutor", target_kind_id="Object", required_request="operation,targetKind,recovery,damage,range,source,target；标准出口补动作与机会身份", result_fields="status,healthBefore,healthAfter,appliedDamage；异常可含 error,exception"),
        refs=[(B+"FixedDamageEffectExecutor.cs", r'Operation => "FixedDamage"'), ("Assets/Scenes/PersistanceScene.unity", "m_Name: ActionRouter")], doc="95_对象指向与固定伤害代码设计案.md")
    for key, label, value_type in [("damage", "固定伤害量", "float"), ("range", "对象目标射程", "int")]:
        add("请求字段", key, label, "FixedDamage 的业务参数；由对应构造器和执行器约定。", B+"FixedDamagePacketBuilder.cs", r'packet\["'+key+r'"\]',
            extra=dict(constant_name="", value_type=value_type, requirement="FixedDamage 必需", producer="FixedDamagePacketBuilder.Build", consumer="FixedDamageEffectExecutor.Execute", encoding="固定值；射程采用曼哈顿距离"), doc="95_对象指向与固定伤害代码设计案.md")
    for key, label in [("healthBefore", "伤害前生命"), ("healthAfter", "伤害后生命"), ("appliedDamage", "实际扣减量")]:
        add("结果字段", key, label, "固定伤害通过目标判定后，记录量表提交结果。", B+"FixedDamageEffectExecutor.cs", r'result\["'+key+r'"\]',
            extra=dict(value_type="float", producer="FixedDamageEffectExecutor.Execute", presence_condition="对象目标合法且完成伤害提交"), doc="95_对象指向与固定伤害代码设计案.md")

    for code, label, summary, publisher, subscriber in [
        ("CellChanged", "坐标变化通知", "任意实际坐标变化均可发布，包括初始化和被动定位；不等价于主动移动。", "SceneCoordinateComponent.SetCell", "当前运行源码无 Subscribe<CellChanged>；可供后续 Owner 内组件订阅"),
        ("MovementCompleted", "主动移动完成通知", "已绑定且有 Owner 时，由显式 MoveToCell 在实际发生位移后发布；朝向据此响应水平变化。", "SceneCoordinateComponent.MoveToCell", "MovementFacingComponent.OnMovementCompleted"),
    ]:
        add("对象消息", code, label, summary, M+code+".cs", extra=dict(payload="Vector2Int OldCell; Vector2Int NewCell", publisher=publisher, subscriber=subscriber), refs=[(M+"SceneCoordinateComponent.cs", r'Publish\(new '+code+r'\(')], doc="10_MetaObject类型与组件底座代码设计案.md")

    attributes = {
        "ActionPoints": ("行动力索引", "配置字段 actionPoints；baseValues[0]", "MovementRange.Refresh；UnitDetailsPanel", "移动范围读取非负整数部分，查询不消耗属性。"),
        "Strength": ("力量索引", "配置字段 strength；baseValues[1]", "UnitDetailsPanel；当前没有投掷/伤害计算消费者", "基础值与修正可查询，力量业务公式尚未接入。"),
        "ActionSpeed": ("行动速度索引", "配置字段 actionSpeed；baseValues[2]", "UnitDetailsPanel；TimeLineManager 尚不使用它修正延迟", "属性可查询，行动后摇仍直接使用配置值。"),
    }
    for member, value in enum(index, M+"AttributeComponent.cs", "CharacterAttribute"):
        if member not in attributes: raise ValueError("待补固定属性解释: " + member)
        label, storage, consumer, summary = attributes[member]
        add("固定属性", member, label, summary, M+"AttributeComponent.cs", r'\b'+member+r'\s*[,\n]', extra=dict(enum_type="CharacterAttribute", numeric_value=value, storage=storage, consumer=consumer), doc="20_对象组件与场景承载类型代码设计案.md")
    add("标记键", "Faction", "阵营技术标记键", "配置存储使用 Faction 键；业务帮助类负责有效值、关系与可读名称。", M+"MetaObjectTagComponent.cs", r'Key = "Faction"', extra=dict(value_domain="Ally | Enemy（当前白名单）", consumer="FactionTag/SceneFactionLabel/UnitDetailsPanel"))
    for value, label in [("Ally", "我方技术标记值"), ("Enemy", "敌方技术标记值")]:
        add("标记取值", "Faction."+value, label, "FactionTag 认可的字符串值；相同有效值视为友方，不同有效值视为敌方。", M+"MetaObjectTagComponent.cs", r'\b'+value+r' = "'+value+r'"', extra=dict(tag_key_id="Faction", stored_value=value, recognizer="FactionTag.TryGetFaction/AreAllies/AreEnemies"))
    add("量表标识", "Health", "生命用途标识契约", "三个角色定义资产使用该标识；UI 按 Ordinal 精确匹配读取当前值与上限；固定伤害通过 Modify 扣减。", U+"UnitDetailsPanel.cs", r'health.MeterId, "Health"', extra=dict(component_type="MetaObjectMeterComponent", value_type="float", consumer="UnitDetailsPanel.RefreshHealth/ObjectTargeting/FixedDamageEffectExecutor"), refs=[("Assets/GameData/MetaObjects/Player.asset", "meterId: Health")], doc="75_量表组件与生命显示代码设计案.md")
    add("地形标识", "ground", "默认地形标识", "未命中 TileBase 映射的已绘制格子使用 ground；当前 Field 场景没有专门映射。", S+"TilemapManager.cs", r'defaultTerrainId = "ground"', extra=dict(mapping_source="TilemapManager.defaultTerrainId/terrainMappings", consumer="MapCellData.TerrainId 查询；无玩法结算消费者"), refs=[("Assets/Scenes/01.Field.unity", "defaultTerrainId: ground")], doc="60_地图与移动适配类型代码设计案.md")

    for code, label, summary, file, assembly, status, limits in [
        ("InventoryComponent", "旧容器数据组件", "按槽位配置创建 BaseInventorySlot 列表，并提供遍历放置入口。", "InventoryComponentData_SO.cs", "InventoryManager.CreatInventory → InventoryComponentData.CreateComponent → ItemInstance.AddComponent", "部分实现", TABLES["背包槽位"]["limitations"]),
        ("MeterComponent", "旧量表数据组件", "提供值钳位、数值委托与检查点通知；也被新 MetaObjectMeterComponent 作为内部数值实现复用。", "MeterComponentData_SO.cs", "MeterComponentData.CreateComponent；MetaObjectMeterComponent 直接 new MeterComponent", "已实现", "旧工厂用 minValue 作初值而未使用 initvalue；检查点经旧工厂复制，新量表包装路径未配置检查点。"),
    ]:
        add("物品组件", code, label, summary, C+file, status=status, limits=limits,
            extra=dict(definition_type=code+"Data", asset_type=code+"Data_SO", assembly_path=assembly), refs=[(C+file, declaration(code+"Data"))])
    slot_info = {
        "Grid": ("网格槽判别值", None, "case 存在，new GridSlot 被注释，最终不产生槽位", "仅声明"),
        "Equipment": ("装备槽判别值", "EquipmentSlot", "new EquipmentSlot；行为仍为桩实现", "部分实现"),
        "Secure": ("安全槽判别值", None, "case 存在，new SecureSlot 被注释，最终不产生槽位", "仅声明"),
    }
    for member, value in enum(index, C+"SlotType.cs", "SlotType"):
        if member not in slot_info: raise ValueError("待补槽位解释: " + member)
        label, impl, factory_state, status = slot_info[member]
        refs = [(C+"InventoryComponentData_SO.cs", r'case SlotType\.'+member+r':')]
        if impl: refs.append((C+"EquipmentSlot.cs", r'throw new NotImplementedException'))
        add("背包槽位", member, label, factory_state+"。", C+"SlotType.cs", r'\b'+member+r'\s*[,\n]', status=status, extra=dict(enum_type="SlotType", numeric_value=value, implementation_type=impl, factory_state=factory_state), refs=refs)

    labels = {"Seed":"种子", "Commodity":"商品", "Furniture":"家具", "HoeTool":"锄地工具", "ChopTool":"砍伐工具", "BreakTool":"破坏工具", "ReapTool":"割草工具", "WaterTool":"浇水工具", "CollectTool":"采集工具", "ReapableScenery":"可收割场景物", "Weapon":"武器", "Inventory":"容器", "Artifact":"神器", "Armors":"护甲"}
    for member, value in enum(index, I+"ItemType.cs", "ItemType"):
        if member not in labels: raise ValueError("待补物品分类解释: " + member)
        add("物品分类", member, labels[member]+"分类判别值", "旧物品数据中的分类枚举成员，登记其序列化数字值；不代表对应玩法行为已完成。", I+"ItemType.cs", r'\b'+member+r'\s*[,\n]', status="仅声明", extra=dict(enum_type="ItemType", numeric_value=value, consumer="ItemDetails.ItemType/ItemInstance.ItemType；当前没有按该成员分派的有效行为代码"))
    for member, value in enum(index, U+"ContainerType.cs", "ContainerType"):
        labels = {"Bag":"背包", "Box":"箱子", "Shop":"商店"}
        if member not in labels: raise ValueError("待补容器分类解释: " + member)
        add("容器分类", member, labels[member]+"容器语义", "SlotUI.containerType 的可配置枚举值；当前无对应分类行为分支。", U+"ContainerType.cs", r'\b'+member+r'\s*[,\n]', status="仅声明", extra=dict(enum_type="ContainerType", numeric_value=value, consumer="Inventory.SlotUI.containerType"), refs=[(U+"SlotUI.cs", r'public ContainerType containerType')])

    results = {
        "None": ("无执行结果", "默认值/局部执行前哨兵", "default → ActionRejected"),
        "Succeeded": ("执行成功", "WaitEffectExecutor/MovementEffectExecutor/TimeLineManager/MetaActionLifecycle", "Moved"),
        "NoChange": ("状态无变化", "MovementCapability.Validate：目的格等于当前格", "AlreadyThere"),
        "NotReady": ("尚未就绪", "动作、组件、地图、来源身份等就绪校验", "NotReady"),
        "InvalidTarget": ("无效目标", "MovementCapability.Validate：目的格不在地图", "OutsideMap"),
        "OutOfRange": ("超出范围", "MovementCapability.Validate：不在当前范围", "OutOfRange"),
        "OutOfTurn": ("无当前机会", "TimeLineManager.BeginAction：身份/机会不匹配", "OutOfTurn"),
        "Rejected": ("执行被拒绝", "生命周期生效失败或执行期间终止等", "default → ActionRejected"),
        "Failed": ("执行异常", "Router 默认失败/异常，生命周期异常路径", "default → ActionRejected"),
    }
    for member, value in enum(index, B+"MetaActionComponents.cs", "ActionResult"):
        if member not in results: raise ValueError("待补动作结果解释: " + member)
        label, producer, mapping = results[member]
        add("动作结果", member, label, "动作执行领域返回值；当前生产路径："+producer+"。", B+"MetaActionComponents.cs", r'\benum ActionResult\b', extra=dict(enum_type="ActionResult", numeric_value=value, producer=producer, adapter_mapping=mapping), refs=[(P+"CharacterMovementController.cs", r'case ActionResult.Succeeded:')])
    phases = {"Idle":("初始", "默认零值，尚未执行"), "Executing":("执行中", "时间轴受理后，调用生效委托前"), "Completed":("已完成", "生效成功且 CompleteAction 完成"), "Rejected":("已拒绝", "时间轴拒绝或生效委托返回 false"), "Failed":("已失败", "生效/完成过程中抛异常，停止时间轴并重抛"), "Terminated":("已终止", "显式 Terminate，或执行期间动作/时间轴终止")}
    for member, value in enum(index, B+"MetaActionLifecycle.cs", "MetaActionPhase"):
        if member not in phases: raise ValueError("待补动作相态解释: " + member)
        label, condition = phases[member]
        add("动作相态", member, label, condition+"。", B+"MetaActionLifecycle.cs", r'\benum MetaActionPhase\b', extra=dict(enum_type="MetaActionPhase", numeric_value=value, entry_condition=condition), doc="40_MetaActionLifecycle统一执行入口代码设计案.md")
    move = {"None":("无结果", "默认值"), "Moved":("已经移动", "Succeeded"), "AlreadyThere":("已在目的格", "NoChange"), "NotReady":("未就绪", "NotReady"), "OutsideMap":("地图外", "InvalidTarget"), "OutOfRange":("超出范围", "OutOfRange"), "OutOfTurn":("非当前机会", "OutOfTurn"), "ActionRejected":("动作拒绝", "其他 ActionResult → default")}
    for member, value in enum(index, P+"CharacterMovementController.cs", "CellMoveResult"):
        if member not in move: raise ValueError("待补移动返回值解释: " + member)
        label, domain = move[member]
        add("移动返回值", member, label, "移动输入适配返回值；对应领域结果："+domain+"。", P+"CharacterMovementController.cs", r'\benum CellMoveResult\b', extra=dict(enum_type="CellMoveResult", numeric_value=value, domain_result=domain))

    # 覆盖核对：增量源码出现新成员时必须先解释，再重新构建。抽象扩展基类不是条目。
    reviewed = {row["code_name"] for category, row in out if category in ("元对象组件", "动作构造器", "效果执行器", "物品组件")}
    reviewed |= {row["definition_type"] for _, row in out if row.get("definition_type")}
    reviewed |= {row["implementation_type"] for category, row in out if category == "背包槽位" and row.get("implementation_type")}
    bases = {"MetaObjectComponent", "MetaObjectComponentDefinition", "ActionEffectExecutor", "ItemComponent", "BaseInventorySlot"}
    declarations = {}
    for text in index.values():
        for match in re.finditer(r'\bclass\s+(\w+)\s*:\s*(\w+)\b', text):
            declarations[match[1]] = match[2]
    discovered = set()
    changed = True
    while changed:
        changed = False
        for name, base in declarations.items():
            if base in bases | discovered and name not in discovered:
                discovered.add(name)
                changed = True
    abstract = {"MetaActionComponent", "ActionHolderComponent", "MetaActionComponentDefinition", "ActionPacketBuilder", "ActionPacketBuilderDefinition"}
    if discovered - reviewed - abstract:
        raise ValueError("新组件/执行器需要归纳: " + ', '.join(sorted(discovered-reviewed-abstract)))
    known_enums = {row.get("enum_type") for _, row in out if row.get("enum_type")}
    found_enums = {m[1] for text in index.values() for m in re.finditer(r'\benum\s+(\w+)\b', text)}
    if found_enums - EXCLUDED_ENUMS != known_enums:
        raise ValueError("枚举覆盖需复核: " + str((found_enums - EXCLUDED_ENUMS) ^ known_enums))
    declared_fields = {m[1] for m in re.finditer(r'\b\w+\s*=\s*"(\w+)"', index[B+"ActionPackets.cs"].split("public static T Get")[0])}
    catalog_fields = {row["code_name"] for category, row in out if category == "请求字段" and row.get("constant_name", "").startswith("ActionPacket.")}
    if declared_fields != catalog_fields:
        raise ValueError("公共报文字段覆盖需复核: " + str(declared_fields ^ catalog_fields))
    return out
