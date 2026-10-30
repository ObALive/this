PRAGMA foreign_keys = ON;

PRAGMA user_version = 2;

CREATE TABLE IF NOT EXISTS "_分类" (table_name TEXT PRIMARY KEY, title TEXT NOT NULL, tier TEXT NOT NULL, extension_mode TEXT NOT NULL, entry_rule TEXT NOT NULL, extension_steps TEXT NOT NULL, limitations TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS "_构建信息" (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS "_源码快照" (path TEXT PRIMARY KEY, sha256 TEXT NOT NULL);

DROP VIEW IF EXISTS "v_待办";

DROP VIEW IF EXISTS "v_全部条目";

DROP VIEW IF EXISTS "v_操作链";

-- v2：按用户要求移除固定的显示朝向分类，保留其他分类数据。

DROP TABLE IF EXISTS "显示朝向";

DELETE FROM "_分类" WHERE table_name='显示朝向';

CREATE TABLE IF NOT EXISTS "元对象组件" (
  "id" TEXT PRIMARY KEY,
  "code_name" TEXT NOT NULL UNIQUE,
  "display_name" TEXT NOT NULL,
  "summary" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK(status IN ('已实现','部分实现','仅声明','待实现','已废弃')),
  "extension_steps" TEXT NOT NULL DEFAULT '',
  "limitations" TEXT NOT NULL DEFAULT '',
  "evidence_json" TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(evidence_json)),
  "reference_doc" TEXT NOT NULL DEFAULT '',
  "baseline_commit" TEXT NOT NULL DEFAULT '',
  "verified_at" TEXT NOT NULL DEFAULT '',
  "managed" INTEGER NOT NULL DEFAULT 0 CHECK(managed IN (0,1)),
  "notes" TEXT NOT NULL DEFAULT '',
  "owner" TEXT NOT NULL DEFAULT '',
  "priority" INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 0 AND 3),
  "created_at" TEXT NOT NULL,
  "updated_at" TEXT NOT NULL,
  "definition_type" TEXT,
  "runtime_base" TEXT,
  "dependencies" TEXT
);

CREATE INDEX IF NOT EXISTS "ix_元对象组件_status" ON "元对象组件"(status);

CREATE TABLE IF NOT EXISTS "动作构造器" (
  "id" TEXT PRIMARY KEY,
  "code_name" TEXT NOT NULL UNIQUE,
  "display_name" TEXT NOT NULL,
  "summary" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK(status IN ('已实现','部分实现','仅声明','待实现','已废弃')),
  "extension_steps" TEXT NOT NULL DEFAULT '',
  "limitations" TEXT NOT NULL DEFAULT '',
  "evidence_json" TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(evidence_json)),
  "reference_doc" TEXT NOT NULL DEFAULT '',
  "baseline_commit" TEXT NOT NULL DEFAULT '',
  "verified_at" TEXT NOT NULL DEFAULT '',
  "managed" INTEGER NOT NULL DEFAULT 0 CHECK(managed IN (0,1)),
  "notes" TEXT NOT NULL DEFAULT '',
  "owner" TEXT NOT NULL DEFAULT '',
  "priority" INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 0 AND 3),
  "created_at" TEXT NOT NULL,
  "updated_at" TEXT NOT NULL,
  "definition_type" TEXT,
  "operation_name" TEXT,
  "default_target" TEXT,
  "timing_source" TEXT
);

CREATE INDEX IF NOT EXISTS "ix_动作构造器_status" ON "动作构造器"(status);

CREATE TABLE IF NOT EXISTS "效果执行器" (
  "id" TEXT PRIMARY KEY,
  "code_name" TEXT NOT NULL UNIQUE,
  "display_name" TEXT NOT NULL,
  "summary" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK(status IN ('已实现','部分实现','仅声明','待实现','已废弃')),
  "extension_steps" TEXT NOT NULL DEFAULT '',
  "limitations" TEXT NOT NULL DEFAULT '',
  "evidence_json" TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(evidence_json)),
  "reference_doc" TEXT NOT NULL DEFAULT '',
  "baseline_commit" TEXT NOT NULL DEFAULT '',
  "verified_at" TEXT NOT NULL DEFAULT '',
  "managed" INTEGER NOT NULL DEFAULT 0 CHECK(managed IN (0,1)),
  "notes" TEXT NOT NULL DEFAULT '',
  "owner" TEXT NOT NULL DEFAULT '',
  "priority" INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 0 AND 3),
  "created_at" TEXT NOT NULL,
  "updated_at" TEXT NOT NULL,
  "operation_name" TEXT,
  "mount_point" TEXT,
  "writes" TEXT
);

CREATE INDEX IF NOT EXISTS "ix_效果执行器_status" ON "效果执行器"(status);

CREATE TABLE IF NOT EXISTS "目标类型" (
  "id" TEXT PRIMARY KEY,
  "code_name" TEXT NOT NULL UNIQUE,
  "display_name" TEXT NOT NULL,
  "summary" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK(status IN ('已实现','部分实现','仅声明','待实现','已废弃')),
  "extension_steps" TEXT NOT NULL DEFAULT '',
  "limitations" TEXT NOT NULL DEFAULT '',
  "evidence_json" TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(evidence_json)),
  "reference_doc" TEXT NOT NULL DEFAULT '',
  "baseline_commit" TEXT NOT NULL DEFAULT '',
  "verified_at" TEXT NOT NULL DEFAULT '',
  "managed" INTEGER NOT NULL DEFAULT 0 CHECK(managed IN (0,1)),
  "notes" TEXT NOT NULL DEFAULT '',
  "owner" TEXT NOT NULL DEFAULT '',
  "priority" INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 0 AND 3),
  "created_at" TEXT NOT NULL,
  "updated_at" TEXT NOT NULL,
  "enum_type" TEXT,
  "numeric_value" INTEGER,
  "encoding" TEXT
);

CREATE INDEX IF NOT EXISTS "ix_目标类型_status" ON "目标类型"(status);

CREATE TABLE IF NOT EXISTS "报文操作" (
  "id" TEXT PRIMARY KEY,
  "code_name" TEXT NOT NULL UNIQUE,
  "display_name" TEXT NOT NULL,
  "summary" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK(status IN ('已实现','部分实现','仅声明','待实现','已废弃')),
  "extension_steps" TEXT NOT NULL DEFAULT '',
  "limitations" TEXT NOT NULL DEFAULT '',
  "evidence_json" TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(evidence_json)),
  "reference_doc" TEXT NOT NULL DEFAULT '',
  "baseline_commit" TEXT NOT NULL DEFAULT '',
  "verified_at" TEXT NOT NULL DEFAULT '',
  "managed" INTEGER NOT NULL DEFAULT 0 CHECK(managed IN (0,1)),
  "notes" TEXT NOT NULL DEFAULT '',
  "owner" TEXT NOT NULL DEFAULT '',
  "priority" INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 0 AND 3),
  "created_at" TEXT NOT NULL,
  "updated_at" TEXT NOT NULL,
  "builder_id" TEXT REFERENCES "动作构造器"(id),
  "executor_id" TEXT REFERENCES "效果执行器"(id),
  "target_kind_id" TEXT REFERENCES "目标类型"(id),
  "required_request" TEXT,
  "result_fields" TEXT
);

CREATE INDEX IF NOT EXISTS "ix_报文操作_status" ON "报文操作"(status);

CREATE TABLE IF NOT EXISTS "请求字段" (
  "id" TEXT PRIMARY KEY,
  "code_name" TEXT NOT NULL UNIQUE,
  "display_name" TEXT NOT NULL,
  "summary" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK(status IN ('已实现','部分实现','仅声明','待实现','已废弃')),
  "extension_steps" TEXT NOT NULL DEFAULT '',
  "limitations" TEXT NOT NULL DEFAULT '',
  "evidence_json" TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(evidence_json)),
  "reference_doc" TEXT NOT NULL DEFAULT '',
  "baseline_commit" TEXT NOT NULL DEFAULT '',
  "verified_at" TEXT NOT NULL DEFAULT '',
  "managed" INTEGER NOT NULL DEFAULT 0 CHECK(managed IN (0,1)),
  "notes" TEXT NOT NULL DEFAULT '',
  "owner" TEXT NOT NULL DEFAULT '',
  "priority" INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 0 AND 3),
  "created_at" TEXT NOT NULL,
  "updated_at" TEXT NOT NULL,
  "constant_name" TEXT,
  "value_type" TEXT,
  "requirement" TEXT,
  "producer" TEXT,
  "consumer" TEXT,
  "encoding" TEXT
);

CREATE INDEX IF NOT EXISTS "ix_请求字段_status" ON "请求字段"(status);

CREATE TABLE IF NOT EXISTS "结果字段" (
  "id" TEXT PRIMARY KEY,
  "code_name" TEXT NOT NULL UNIQUE,
  "display_name" TEXT NOT NULL,
  "summary" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK(status IN ('已实现','部分实现','仅声明','待实现','已废弃')),
  "extension_steps" TEXT NOT NULL DEFAULT '',
  "limitations" TEXT NOT NULL DEFAULT '',
  "evidence_json" TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(evidence_json)),
  "reference_doc" TEXT NOT NULL DEFAULT '',
  "baseline_commit" TEXT NOT NULL DEFAULT '',
  "verified_at" TEXT NOT NULL DEFAULT '',
  "managed" INTEGER NOT NULL DEFAULT 0 CHECK(managed IN (0,1)),
  "notes" TEXT NOT NULL DEFAULT '',
  "owner" TEXT NOT NULL DEFAULT '',
  "priority" INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 0 AND 3),
  "created_at" TEXT NOT NULL,
  "updated_at" TEXT NOT NULL,
  "value_type" TEXT,
  "producer" TEXT,
  "presence_condition" TEXT
);

CREATE INDEX IF NOT EXISTS "ix_结果字段_status" ON "结果字段"(status);

CREATE TABLE IF NOT EXISTS "对象消息" (
  "id" TEXT PRIMARY KEY,
  "code_name" TEXT NOT NULL UNIQUE,
  "display_name" TEXT NOT NULL,
  "summary" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK(status IN ('已实现','部分实现','仅声明','待实现','已废弃')),
  "extension_steps" TEXT NOT NULL DEFAULT '',
  "limitations" TEXT NOT NULL DEFAULT '',
  "evidence_json" TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(evidence_json)),
  "reference_doc" TEXT NOT NULL DEFAULT '',
  "baseline_commit" TEXT NOT NULL DEFAULT '',
  "verified_at" TEXT NOT NULL DEFAULT '',
  "managed" INTEGER NOT NULL DEFAULT 0 CHECK(managed IN (0,1)),
  "notes" TEXT NOT NULL DEFAULT '',
  "owner" TEXT NOT NULL DEFAULT '',
  "priority" INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 0 AND 3),
  "created_at" TEXT NOT NULL,
  "updated_at" TEXT NOT NULL,
  "payload" TEXT,
  "publisher" TEXT,
  "subscriber" TEXT
);

CREATE INDEX IF NOT EXISTS "ix_对象消息_status" ON "对象消息"(status);

CREATE TABLE IF NOT EXISTS "固定属性" (
  "id" TEXT PRIMARY KEY,
  "code_name" TEXT NOT NULL UNIQUE,
  "display_name" TEXT NOT NULL,
  "summary" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK(status IN ('已实现','部分实现','仅声明','待实现','已废弃')),
  "extension_steps" TEXT NOT NULL DEFAULT '',
  "limitations" TEXT NOT NULL DEFAULT '',
  "evidence_json" TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(evidence_json)),
  "reference_doc" TEXT NOT NULL DEFAULT '',
  "baseline_commit" TEXT NOT NULL DEFAULT '',
  "verified_at" TEXT NOT NULL DEFAULT '',
  "managed" INTEGER NOT NULL DEFAULT 0 CHECK(managed IN (0,1)),
  "notes" TEXT NOT NULL DEFAULT '',
  "owner" TEXT NOT NULL DEFAULT '',
  "priority" INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 0 AND 3),
  "created_at" TEXT NOT NULL,
  "updated_at" TEXT NOT NULL,
  "enum_type" TEXT,
  "numeric_value" INTEGER,
  "storage" TEXT,
  "consumer" TEXT
);

CREATE INDEX IF NOT EXISTS "ix_固定属性_status" ON "固定属性"(status);

CREATE TABLE IF NOT EXISTS "标记键" (
  "id" TEXT PRIMARY KEY,
  "code_name" TEXT NOT NULL UNIQUE,
  "display_name" TEXT NOT NULL,
  "summary" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK(status IN ('已实现','部分实现','仅声明','待实现','已废弃')),
  "extension_steps" TEXT NOT NULL DEFAULT '',
  "limitations" TEXT NOT NULL DEFAULT '',
  "evidence_json" TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(evidence_json)),
  "reference_doc" TEXT NOT NULL DEFAULT '',
  "baseline_commit" TEXT NOT NULL DEFAULT '',
  "verified_at" TEXT NOT NULL DEFAULT '',
  "managed" INTEGER NOT NULL DEFAULT 0 CHECK(managed IN (0,1)),
  "notes" TEXT NOT NULL DEFAULT '',
  "owner" TEXT NOT NULL DEFAULT '',
  "priority" INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 0 AND 3),
  "created_at" TEXT NOT NULL,
  "updated_at" TEXT NOT NULL,
  "value_domain" TEXT,
  "consumer" TEXT
);

CREATE INDEX IF NOT EXISTS "ix_标记键_status" ON "标记键"(status);

CREATE TABLE IF NOT EXISTS "标记取值" (
  "id" TEXT PRIMARY KEY,
  "code_name" TEXT NOT NULL UNIQUE,
  "display_name" TEXT NOT NULL,
  "summary" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK(status IN ('已实现','部分实现','仅声明','待实现','已废弃')),
  "extension_steps" TEXT NOT NULL DEFAULT '',
  "limitations" TEXT NOT NULL DEFAULT '',
  "evidence_json" TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(evidence_json)),
  "reference_doc" TEXT NOT NULL DEFAULT '',
  "baseline_commit" TEXT NOT NULL DEFAULT '',
  "verified_at" TEXT NOT NULL DEFAULT '',
  "managed" INTEGER NOT NULL DEFAULT 0 CHECK(managed IN (0,1)),
  "notes" TEXT NOT NULL DEFAULT '',
  "owner" TEXT NOT NULL DEFAULT '',
  "priority" INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 0 AND 3),
  "created_at" TEXT NOT NULL,
  "updated_at" TEXT NOT NULL,
  "tag_key_id" TEXT REFERENCES "标记键"(id),
  "stored_value" TEXT,
  "recognizer" TEXT,
  UNIQUE(tag_key_id,stored_value)
);

CREATE INDEX IF NOT EXISTS "ix_标记取值_status" ON "标记取值"(status);

CREATE TABLE IF NOT EXISTS "量表标识" (
  "id" TEXT PRIMARY KEY,
  "code_name" TEXT NOT NULL UNIQUE,
  "display_name" TEXT NOT NULL,
  "summary" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK(status IN ('已实现','部分实现','仅声明','待实现','已废弃')),
  "extension_steps" TEXT NOT NULL DEFAULT '',
  "limitations" TEXT NOT NULL DEFAULT '',
  "evidence_json" TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(evidence_json)),
  "reference_doc" TEXT NOT NULL DEFAULT '',
  "baseline_commit" TEXT NOT NULL DEFAULT '',
  "verified_at" TEXT NOT NULL DEFAULT '',
  "managed" INTEGER NOT NULL DEFAULT 0 CHECK(managed IN (0,1)),
  "notes" TEXT NOT NULL DEFAULT '',
  "owner" TEXT NOT NULL DEFAULT '',
  "priority" INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 0 AND 3),
  "created_at" TEXT NOT NULL,
  "updated_at" TEXT NOT NULL,
  "component_type" TEXT,
  "value_type" TEXT,
  "consumer" TEXT
);

CREATE INDEX IF NOT EXISTS "ix_量表标识_status" ON "量表标识"(status);

CREATE TABLE IF NOT EXISTS "地形标识" (
  "id" TEXT PRIMARY KEY,
  "code_name" TEXT NOT NULL UNIQUE,
  "display_name" TEXT NOT NULL,
  "summary" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK(status IN ('已实现','部分实现','仅声明','待实现','已废弃')),
  "extension_steps" TEXT NOT NULL DEFAULT '',
  "limitations" TEXT NOT NULL DEFAULT '',
  "evidence_json" TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(evidence_json)),
  "reference_doc" TEXT NOT NULL DEFAULT '',
  "baseline_commit" TEXT NOT NULL DEFAULT '',
  "verified_at" TEXT NOT NULL DEFAULT '',
  "managed" INTEGER NOT NULL DEFAULT 0 CHECK(managed IN (0,1)),
  "notes" TEXT NOT NULL DEFAULT '',
  "owner" TEXT NOT NULL DEFAULT '',
  "priority" INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 0 AND 3),
  "created_at" TEXT NOT NULL,
  "updated_at" TEXT NOT NULL,
  "mapping_source" TEXT,
  "consumer" TEXT
);

CREATE INDEX IF NOT EXISTS "ix_地形标识_status" ON "地形标识"(status);

CREATE TABLE IF NOT EXISTS "物品组件" (
  "id" TEXT PRIMARY KEY,
  "code_name" TEXT NOT NULL UNIQUE,
  "display_name" TEXT NOT NULL,
  "summary" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK(status IN ('已实现','部分实现','仅声明','待实现','已废弃')),
  "extension_steps" TEXT NOT NULL DEFAULT '',
  "limitations" TEXT NOT NULL DEFAULT '',
  "evidence_json" TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(evidence_json)),
  "reference_doc" TEXT NOT NULL DEFAULT '',
  "baseline_commit" TEXT NOT NULL DEFAULT '',
  "verified_at" TEXT NOT NULL DEFAULT '',
  "managed" INTEGER NOT NULL DEFAULT 0 CHECK(managed IN (0,1)),
  "notes" TEXT NOT NULL DEFAULT '',
  "owner" TEXT NOT NULL DEFAULT '',
  "priority" INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 0 AND 3),
  "created_at" TEXT NOT NULL,
  "updated_at" TEXT NOT NULL,
  "definition_type" TEXT,
  "asset_type" TEXT,
  "assembly_path" TEXT
);

CREATE INDEX IF NOT EXISTS "ix_物品组件_status" ON "物品组件"(status);

CREATE TABLE IF NOT EXISTS "背包槽位" (
  "id" TEXT PRIMARY KEY,
  "code_name" TEXT NOT NULL UNIQUE,
  "display_name" TEXT NOT NULL,
  "summary" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK(status IN ('已实现','部分实现','仅声明','待实现','已废弃')),
  "extension_steps" TEXT NOT NULL DEFAULT '',
  "limitations" TEXT NOT NULL DEFAULT '',
  "evidence_json" TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(evidence_json)),
  "reference_doc" TEXT NOT NULL DEFAULT '',
  "baseline_commit" TEXT NOT NULL DEFAULT '',
  "verified_at" TEXT NOT NULL DEFAULT '',
  "managed" INTEGER NOT NULL DEFAULT 0 CHECK(managed IN (0,1)),
  "notes" TEXT NOT NULL DEFAULT '',
  "owner" TEXT NOT NULL DEFAULT '',
  "priority" INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 0 AND 3),
  "created_at" TEXT NOT NULL,
  "updated_at" TEXT NOT NULL,
  "enum_type" TEXT,
  "numeric_value" INTEGER,
  "implementation_type" TEXT,
  "factory_state" TEXT
);

CREATE INDEX IF NOT EXISTS "ix_背包槽位_status" ON "背包槽位"(status);

CREATE TABLE IF NOT EXISTS "物品分类" (
  "id" TEXT PRIMARY KEY,
  "code_name" TEXT NOT NULL UNIQUE,
  "display_name" TEXT NOT NULL,
  "summary" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK(status IN ('已实现','部分实现','仅声明','待实现','已废弃')),
  "extension_steps" TEXT NOT NULL DEFAULT '',
  "limitations" TEXT NOT NULL DEFAULT '',
  "evidence_json" TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(evidence_json)),
  "reference_doc" TEXT NOT NULL DEFAULT '',
  "baseline_commit" TEXT NOT NULL DEFAULT '',
  "verified_at" TEXT NOT NULL DEFAULT '',
  "managed" INTEGER NOT NULL DEFAULT 0 CHECK(managed IN (0,1)),
  "notes" TEXT NOT NULL DEFAULT '',
  "owner" TEXT NOT NULL DEFAULT '',
  "priority" INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 0 AND 3),
  "created_at" TEXT NOT NULL,
  "updated_at" TEXT NOT NULL,
  "enum_type" TEXT,
  "numeric_value" INTEGER,
  "consumer" TEXT
);

CREATE INDEX IF NOT EXISTS "ix_物品分类_status" ON "物品分类"(status);

CREATE TABLE IF NOT EXISTS "容器分类" (
  "id" TEXT PRIMARY KEY,
  "code_name" TEXT NOT NULL UNIQUE,
  "display_name" TEXT NOT NULL,
  "summary" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK(status IN ('已实现','部分实现','仅声明','待实现','已废弃')),
  "extension_steps" TEXT NOT NULL DEFAULT '',
  "limitations" TEXT NOT NULL DEFAULT '',
  "evidence_json" TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(evidence_json)),
  "reference_doc" TEXT NOT NULL DEFAULT '',
  "baseline_commit" TEXT NOT NULL DEFAULT '',
  "verified_at" TEXT NOT NULL DEFAULT '',
  "managed" INTEGER NOT NULL DEFAULT 0 CHECK(managed IN (0,1)),
  "notes" TEXT NOT NULL DEFAULT '',
  "owner" TEXT NOT NULL DEFAULT '',
  "priority" INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 0 AND 3),
  "created_at" TEXT NOT NULL,
  "updated_at" TEXT NOT NULL,
  "enum_type" TEXT,
  "numeric_value" INTEGER,
  "consumer" TEXT
);

CREATE INDEX IF NOT EXISTS "ix_容器分类_status" ON "容器分类"(status);

CREATE TABLE IF NOT EXISTS "动作结果" (
  "id" TEXT PRIMARY KEY,
  "code_name" TEXT NOT NULL UNIQUE,
  "display_name" TEXT NOT NULL,
  "summary" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK(status IN ('已实现','部分实现','仅声明','待实现','已废弃')),
  "extension_steps" TEXT NOT NULL DEFAULT '',
  "limitations" TEXT NOT NULL DEFAULT '',
  "evidence_json" TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(evidence_json)),
  "reference_doc" TEXT NOT NULL DEFAULT '',
  "baseline_commit" TEXT NOT NULL DEFAULT '',
  "verified_at" TEXT NOT NULL DEFAULT '',
  "managed" INTEGER NOT NULL DEFAULT 0 CHECK(managed IN (0,1)),
  "notes" TEXT NOT NULL DEFAULT '',
  "owner" TEXT NOT NULL DEFAULT '',
  "priority" INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 0 AND 3),
  "created_at" TEXT NOT NULL,
  "updated_at" TEXT NOT NULL,
  "enum_type" TEXT,
  "numeric_value" INTEGER,
  "producer" TEXT,
  "adapter_mapping" TEXT
);

CREATE INDEX IF NOT EXISTS "ix_动作结果_status" ON "动作结果"(status);

CREATE TABLE IF NOT EXISTS "动作相态" (
  "id" TEXT PRIMARY KEY,
  "code_name" TEXT NOT NULL UNIQUE,
  "display_name" TEXT NOT NULL,
  "summary" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK(status IN ('已实现','部分实现','仅声明','待实现','已废弃')),
  "extension_steps" TEXT NOT NULL DEFAULT '',
  "limitations" TEXT NOT NULL DEFAULT '',
  "evidence_json" TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(evidence_json)),
  "reference_doc" TEXT NOT NULL DEFAULT '',
  "baseline_commit" TEXT NOT NULL DEFAULT '',
  "verified_at" TEXT NOT NULL DEFAULT '',
  "managed" INTEGER NOT NULL DEFAULT 0 CHECK(managed IN (0,1)),
  "notes" TEXT NOT NULL DEFAULT '',
  "owner" TEXT NOT NULL DEFAULT '',
  "priority" INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 0 AND 3),
  "created_at" TEXT NOT NULL,
  "updated_at" TEXT NOT NULL,
  "enum_type" TEXT,
  "numeric_value" INTEGER,
  "entry_condition" TEXT
);

CREATE INDEX IF NOT EXISTS "ix_动作相态_status" ON "动作相态"(status);

CREATE TABLE IF NOT EXISTS "移动返回值" (
  "id" TEXT PRIMARY KEY,
  "code_name" TEXT NOT NULL UNIQUE,
  "display_name" TEXT NOT NULL,
  "summary" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK(status IN ('已实现','部分实现','仅声明','待实现','已废弃')),
  "extension_steps" TEXT NOT NULL DEFAULT '',
  "limitations" TEXT NOT NULL DEFAULT '',
  "evidence_json" TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(evidence_json)),
  "reference_doc" TEXT NOT NULL DEFAULT '',
  "baseline_commit" TEXT NOT NULL DEFAULT '',
  "verified_at" TEXT NOT NULL DEFAULT '',
  "managed" INTEGER NOT NULL DEFAULT 0 CHECK(managed IN (0,1)),
  "notes" TEXT NOT NULL DEFAULT '',
  "owner" TEXT NOT NULL DEFAULT '',
  "priority" INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 0 AND 3),
  "created_at" TEXT NOT NULL,
  "updated_at" TEXT NOT NULL,
  "enum_type" TEXT,
  "numeric_value" INTEGER,
  "domain_result" TEXT
);

CREATE INDEX IF NOT EXISTS "ix_移动返回值_status" ON "移动返回值"(status);

CREATE VIEW IF NOT EXISTS "v_全部条目" AS SELECT '元对象组件' AS category, id, code_name, display_name, summary, status, owner, priority, notes FROM "元对象组件"
UNION ALL
SELECT '动作构造器' AS category, id, code_name, display_name, summary, status, owner, priority, notes FROM "动作构造器"
UNION ALL
SELECT '效果执行器' AS category, id, code_name, display_name, summary, status, owner, priority, notes FROM "效果执行器"
UNION ALL
SELECT '目标类型' AS category, id, code_name, display_name, summary, status, owner, priority, notes FROM "目标类型"
UNION ALL
SELECT '报文操作' AS category, id, code_name, display_name, summary, status, owner, priority, notes FROM "报文操作"
UNION ALL
SELECT '请求字段' AS category, id, code_name, display_name, summary, status, owner, priority, notes FROM "请求字段"
UNION ALL
SELECT '结果字段' AS category, id, code_name, display_name, summary, status, owner, priority, notes FROM "结果字段"
UNION ALL
SELECT '对象消息' AS category, id, code_name, display_name, summary, status, owner, priority, notes FROM "对象消息"
UNION ALL
SELECT '固定属性' AS category, id, code_name, display_name, summary, status, owner, priority, notes FROM "固定属性"
UNION ALL
SELECT '标记键' AS category, id, code_name, display_name, summary, status, owner, priority, notes FROM "标记键"
UNION ALL
SELECT '标记取值' AS category, id, code_name, display_name, summary, status, owner, priority, notes FROM "标记取值"
UNION ALL
SELECT '量表标识' AS category, id, code_name, display_name, summary, status, owner, priority, notes FROM "量表标识"
UNION ALL
SELECT '地形标识' AS category, id, code_name, display_name, summary, status, owner, priority, notes FROM "地形标识"
UNION ALL
SELECT '物品组件' AS category, id, code_name, display_name, summary, status, owner, priority, notes FROM "物品组件"
UNION ALL
SELECT '背包槽位' AS category, id, code_name, display_name, summary, status, owner, priority, notes FROM "背包槽位"
UNION ALL
SELECT '物品分类' AS category, id, code_name, display_name, summary, status, owner, priority, notes FROM "物品分类"
UNION ALL
SELECT '容器分类' AS category, id, code_name, display_name, summary, status, owner, priority, notes FROM "容器分类"
UNION ALL
SELECT '动作结果' AS category, id, code_name, display_name, summary, status, owner, priority, notes FROM "动作结果"
UNION ALL
SELECT '动作相态' AS category, id, code_name, display_name, summary, status, owner, priority, notes FROM "动作相态"
UNION ALL
SELECT '移动返回值' AS category, id, code_name, display_name, summary, status, owner, priority, notes FROM "移动返回值";

CREATE VIEW IF NOT EXISTS "v_待办" AS SELECT * FROM "v_全部条目" WHERE status IN ('部分实现','仅声明','待实现') ORDER BY priority,category,code_name;

CREATE VIEW IF NOT EXISTS "v_操作链" AS SELECT o.code_name AS operation,o.status,b.code_name AS builder,e.code_name AS executor,o.target_kind_id,o.limitations FROM "报文操作" o JOIN "动作构造器" b ON b.id=o.builder_id JOIN "效果执行器" e ON e.id=o.executor_id;
