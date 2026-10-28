# -*- coding: utf-8 -*-
"""CO06 工程更新 7362b95 取证：只读收集本轮核对基线。"""
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys

ROOT = r"D:/myspace/Git/this"
GAME = r"D:/myspace/Git/mygame"
OUT = os.path.join(ROOT, "Output", "CO06-工程更新7362b95")
DB = os.path.join(ROOT, "Tool/项目网络图/数据/N01_完整依赖清理新图_v2.sqlite")

SOURCES = [
    "Assets/Script/MetaObjects/MetaObjectDefinition.cs",
    "Assets/Script/MetaObjects/MetaObjectInstance.cs",
    "Assets/Script/MetaObjects/MetaObjectComponentDefinition.cs",
    "Assets/Script/MetaObjects/MetaObjectComponent.cs",
    "Assets/Script/MetaObjects/MetaObjectPreset.cs",
    "Assets/Script/MetaObjects/SceneCoordinateComponent.cs",
    "Assets/Script/MetaObjects/SceneTextureComponent.cs",
    "Assets/Script/MetaObjects/MovementFacingComponent.cs",
    "Assets/Script/MetaObjects/AttributeComponent.cs",
    "Assets/Script/MetaObjects/MetaObjectMeterComponent.cs",
    "Assets/Script/MetaObjects/BasicSkillSlotsComponent.cs",
    "Assets/Script/MetaObjects/CellChanged.cs",
    "Assets/Script/MetaObjects/MovementCompleted.cs",
    "Assets/Script/Battle/MetaActionDefinition.cs",
    "Assets/Script/Battle/MetaActionInstance.cs",
    "Assets/Script/Battle/MetaActionComponents.cs",
    "Assets/Script/MetaObjects/MovementActionComponent.cs",
    "Assets/Script/Battle/MetaActionLifecycle.cs",
    "Assets/Script/Battle/TimeLineManager.cs",
    "Assets/Script/Battle/BattleTimelineController.cs",
    "Assets/Script/Battle/BattleTimelineConfiguration.cs",
    "Assets/Script/Battle/BattleBehaviorDefinition.cs",
    "Assets/Script/GameManager.cs",
    "Assets/Script/Debug/DebugPanel.cs",
    "Assets/Script/TilemapManager.cs",
    "Assets/Script/Player/GridClickInput.cs",
    "Assets/Script/Player/SkillSelectionController.cs",
    "Assets/Script/Player/CharacterMovementController.cs",
    "Assets/Script/Player/MovementRange.cs",
    "Assets/Script/Player/MovementRangeOverlay.cs",
    "Assets/Script/UI/UnitDetailsPanel.cs",
]

# 被复用但不计入本次声明清单的既有类型来源
REUSED = "Assets/Script/Components/MeterComponentData_SO.cs"

ASSETS = [
    "Assets/GameData/Battle/DemoTimeline.asset",
    "Assets/GameData/Battle/MovementAction.asset",
    "Assets/GameData/Battle/MovementTiming.asset",
    "Assets/GameData/Battle/WaitAction.asset",
    "Assets/GameData/Battle/WaitTiming.asset",
    "Assets/GameData/Battle/Unit_02_Timeline.asset",
    "Assets/GameData/Battle/Unit_03_Timeline.asset",
    "Assets/GameData/MetaObjects/Player.asset",
    "Assets/GameData/UI/UnitDetails SDF.asset",
    "Assets/GameData/UI/UnitDetails.ttf",
    "Assets/Scenes/UI.unity",
    "Assets/Scenes/PersistanceScene.unity",
    "Assets/Editor/BasicSkillVerification.cs",
    "Assets/Editor/MeterVerification.cs",
    "Assets/Editor/UnitDetailsVerification.cs",
]

PROTECTED = [
    "Tool/项目网络图/数据/N01_完整依赖清理新图_v2.sqlite",
    "Tool/项目网络图/db.py",
    "Tool/项目网络图/query.py",
    "Rules",
    "Code_Design",
    "系统设计文档",
    "架构设计文档",
    "Task",
]

# 工程内只读源码树身份（绝对路径）
SOURCE_TREES = [
    GAME + "/Assets/Script",
    GAME + "/Assets/GameData",
    GAME + "/Assets/Scenes",
    GAME + "/Assets/Editor",
    GAME + "/ProjectSettings",
]

TYPE_RE = re.compile(
    r"^[ \t]*(?:(?:public|internal|private|protected|static|abstract|sealed|partial|readonly)\s+)*"
    r"(class|interface|struct|enum)\s+(\w+)",
    re.M,
)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run(args, cwd=GAME):
    p = subprocess.run(args, cwd=cwd, capture_output=True)
    return p.stdout.decode("utf-8", "replace").strip(), p.returncode


def scan_types(text):
    result = []
    for m in TYPE_RE.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        result.append({"kind": m.group(1), "type": m.group(2), "line": line})
    return result


def main():
    os.makedirs(OUT, exist_ok=True)
    data = {
        "date": "2026-10-26",
        "workspace_head": run(["git", "rev-parse", "HEAD"], ROOT)[0],
        "workspace_status": run(["git", "status", "--porcelain"], ROOT)[0].splitlines(),
        "source_head": run(["git", "rev-parse", "HEAD"])[0],
        "source_status": run(["git", "status", "--porcelain"])[0].splitlines(),
        "source_log": run(["git", "log", "--oneline", "-6"])[0].splitlines(),
        "delta_from_doc_baseline": run(["git", "diff", "--name-status", "3911fe3", "HEAD"])[0].splitlines(),
        "delta_uncommitted": run(["git", "diff", "--stat"])[0].splitlines(),
        "sources": [],
        "reused_source": {},
        "type_count": 0,
        "projects": {},
        "assets": {},
        "implemented_nodes": [],
        "node_status_counts": {},
        "ui_bindings": {},
        "assets_config": {},
        "protected": {},
        "editor_entries": {},
    }

    # 源码清单与类型
    for rel in SOURCES:
        path = os.path.join(GAME, rel)
        text = open(path, encoding="utf-8").read()
        types = scan_types(text)
        data["sources"].append({
            "path": rel,
            "sha256": sha256(path),
            "bytes": os.path.getsize(path),
            "declared_types": types,
        })
        data["type_count"] += len(types)

    rp = os.path.join(GAME, REUSED)
    rtext = open(rp, encoding="utf-8").read()
    data["reused_source"] = {
        "path": REUSED,
        "sha256": sha256(rp),
        "declared_types": scan_types(rtext),
        "reason": "MetaObjectMeterComponent 复用的既有量表实现，不计入本次声明清单",
    }

    # 程序集归属
    for proj in ["Assembly-CSharp.csproj", "Assembly-CSharp-Editor.csproj", "Assembly-CSharp-firstpass.csproj"]:
        path = os.path.join(GAME, proj)
        if not os.path.exists(path):
            continue
        text = open(path, encoding="utf-8").read()
        name = re.search(r"<AssemblyName>([^<]+)</AssemblyName>", text)
        compiles = re.findall(r'<Compile Include="([^"]+)"', text)
        data["projects"][proj] = {
            "assembly_name": name.group(1) if name else None,
            "compile_count": len(compiles),
            "in_scope_members": [rel.replace("/", "\\") for rel in SOURCES
                                 if rel.replace("/", "\\") in compiles],
            "reference_hits": sorted(set(re.findall(r'<Reference Include="([^"]+)"', text))),
        }

    # 资产散列
    for rel in ASSETS:
        path = os.path.join(GAME, rel)
        data["assets"][rel] = {"sha256": sha256(path), "bytes": os.path.getsize(path)}

    # 网络图（只读）
    conn = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    for r in conn.execute("SELECT status, COUNT(*) c FROM nodes GROUP BY status"):
        data["node_status_counts"][r["status"]] = r["c"]
    for r in conn.execute("SELECT id, seq, number, status FROM nodes ORDER BY seq"):
        if r["status"] != "已实现":
            continue
        node = {"id": r["id"], "seq": r["seq"], "number": r["number"], "status": r["status"]}
        v = conn.execute("SELECT index_label, summary, section_path FROM v_node WHERE id=?", (r["id"],)).fetchone()
        node.update({"index_label": v["index_label"], "summary": v["summary"], "section_path": v["section_path"]})
        body = conn.execute("SELECT body FROM nodes WHERE id=?", (r["id"],)).fetchone()["body"]
        node["body"] = body
        node["objects"] = [dict(o) for o in conn.execute(
            "SELECT seq, name, note, path FROM node_objects WHERE node_id=? ORDER BY seq", (r["id"],))]
        node["notes"] = [dict(o) for o in conn.execute(
            "SELECT seq, text FROM node_notes WHERE node_id=? ORDER BY seq", (r["id"],))]
        node["refs"] = [dict(o) for o in conn.execute(
            "SELECT seq, raw, target_id FROM node_refs WHERE node_id=? ORDER BY seq", (r["id"],))]
        data["implemented_nodes"].append(node)
    data["db_meta"] = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM meta")}
    conn.close()

    # UI 绑定
    scene = open(os.path.join(GAME, "Assets/Scenes/UI.unity"), encoding="utf-8").read()
    blocks = re.split(r"^--- !u!(\d+) &(\d+).*$", scene, flags=re.M)
    objs = {}
    i = 1
    while i + 2 <= len(blocks):
        objs[blocks[i + 1]] = (blocks[i], blocks[i + 2])
        i += 3

    def field(body, name):
        m = re.search(r"^[ \t]*" + name + r":[ \t]*(.*)$", body, re.M)
        return m.group(1).strip() if m else None

    def go_name(gid):
        b = objs.get(gid)
        return field(b[1], "m_Name") if b else "MISSING"

    fields = {
        "details": "1538517151", "hint": "166982040", "healthSummary": "488543080",
        "moveLabel": "474455404", "moveButton": "2050392728", "moveBackground": "2050392729",
        "skillButtons[0]": "228922413", "skillButtons[1]": "1967859605",
        "skillButtons[2]": "2036563005", "skillButtons[3]": "775289352",
        "skillLabels[0]": "1875193678", "skillLabels[1]": "1949239004",
        "skillLabels[2]": "58925814", "skillLabels[3]": "446884971",
    }
    for key, fid in fields.items():
        entry = {"fileID": fid, "exists": fid in objs}
        if fid in objs:
            body = objs[fid][1]
            go = field(body, "m_GameObject")
            go_id = re.search(r"fileID:\s*(\d+)", go).group(1) if go else None
            entry.update({
                "gameObject": go_id,
                "name": go_name(go_id),
                "class": objs[fid][0],
                "fonts": re.findall(r"m_fontAsset:\s*\{fileID:\s*\d+,\s*guid:\s*(\w+)", body),
                "hasOnClick": "m_OnClick" in body,
                "persistentCallsEmpty": bool(re.search(r"m_Calls: \[\]", body)),
            })
        data["ui_bindings"][key] = entry

    # 面板与血量文本的布局记录
    def rect_of(go_id):
        for fid, (cls, body) in objs.items():
            if cls == "224" and re.search(r"m_GameObject:\s*\{fileID:\s*" + go_id + r"\}", body):
                return {
                    "rectTransform": fid,
                    "father": field(body, "m_Father"),
                    "anchorMin": field(body, "m_AnchorMin"),
                    "anchorMax": field(body, "m_AnchorMax"),
                    "anchoredPosition": field(body, "m_AnchoredPosition"),
                    "sizeDelta": field(body, "m_SizeDelta"),
                }
        return None

    canvas_go = field(objs["1837621939"][1], "m_GameObject")
    data["ui_layout"] = {
        "panelGameObject": "2067759692",
        "panelName": go_name("2067759692"),
        "panelRect": rect_of("2067759692"),
        "healthSummaryGameObject": "488543078",
        "healthSummaryRect": rect_of("488543078"),
        "canvasName": go_name(re.search(r"fileID:\s*(\d+)", canvas_go).group(1)),
    }

    # 资产配置摘要
    for rel in ["Assets/GameData/MetaObjects/Player.asset",
                "Assets/GameData/Battle/Unit_02_Timeline.asset",
                "Assets/GameData/Battle/Unit_03_Timeline.asset"]:
        text = open(os.path.join(GAME, rel), encoding="utf-8").read()
        data["assets_config"][rel] = {
            "metaObjectId": (re.search(r"^\s*metaObjectId:\s*(\S+)", text, re.M) or [None, None])[1],
            "attributes": {
                k: (re.search(r"^\s*" + k + r":\s*([\d.]+)", text, re.M) or [None, None])[1]
                for k in ["actionPoints", "strength", "actionSpeed"]
            },
            "meter": {
                k: (re.search(r"^\s*" + k + r":\s*(\S+)", text, re.M) or [None, None])[1]
                for k in ["meterId", "minimum", "maximum", "initialValue"]
            },
            "slot_guids": re.findall(r"^\s*- \{fileID: 11400000, guid: (\w+), type: 2\}\s*$", text, re.M),
            "has_skill_slots": "BasicSkillSlotsComponentDefinition" in text,
            "has_meter_component": "MetaObjectMeterComponentDefinition" in text,
        }
    for rel in ["Assets/GameData/Battle/WaitAction.asset", "Assets/GameData/Battle/WaitTiming.asset",
                "Assets/GameData/Battle/MovementAction.asset", "Assets/GameData/Battle/MovementTiming.asset"]:
        text = open(os.path.join(GAME, rel), encoding="utf-8").read()
        data["assets_config"][rel] = {
            "metaObjectId": (re.search(r"^\s*metaObjectId:\s*(\S+)", text, re.M) or [None, None])[1],
            "displayName": (re.search(r"^\s*displayName:\s*(.+)$", text, re.M) or [None, None])[1],
            "kind": (re.search(r"^\s*kind:\s*(\d+)", text, re.M) or [None, None])[1],
            "behaviorId": (re.search(r"^\s*behaviorId:\s*(\S+)", text, re.M) or [None, None])[1],
            "recovery": (re.search(r"^\s*recovery:\s*([\d.]+)", text, re.M) or [None, None])[1],
            "component_types": re.findall(r"type: \{class: (\w+), ns: , asm: Assembly-CSharp\}", text),
        }

    # 编辑器入口
    for rel in ["Assets/Editor/BasicSkillVerification.cs", "Assets/Editor/MeterVerification.cs",
                "Assets/Editor/UnitDetailsVerification.cs"]:
        text = open(os.path.join(GAME, rel), encoding="utf-8").read()
        data["editor_entries"][rel] = {
            "sha256": sha256(os.path.join(GAME, rel)),
            "public_methods": re.findall(r"public static [\w<>\[\]]+ (\w+)\(", text),
            "output_dir": (re.search(r'Output\s*=\s*"([^"]+)"', text) or [None, None])[1],
        }

    # 只读资料身份
    def tree_digest(path):
        entries = []
        for base, dirs, files in os.walk(path):
            dirs[:] = sorted(d for d in dirs if d not in ("__pycache__", "Library", "Temp", "obj"))
            for f in sorted(files):
                fp = os.path.join(base, f)
                entries.append([os.path.relpath(fp, path).replace("\\", "/"), sha256(fp)])
        return {"kind": "dir", "file_count": len(entries), "sha256": sha256_text(json.dumps(entries))}

    for rel in PROTECTED:
        path = os.path.join(ROOT, rel)
        if os.path.isdir(path):
            data["protected"][rel] = tree_digest(path)
        elif os.path.exists(path):
            data["protected"][rel] = {"kind": "file", "sha256": sha256(path)}
        else:
            data["protected"][rel] = {"kind": "missing"}

    for path in SOURCE_TREES:
        data["protected"][path.replace(GAME, "<SOURCE>")] = tree_digest(path)

    with open(os.path.join(OUT, "CO06-工程更新7362b95_基线_v1.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")

    print("sources", len(data["sources"]), "types", data["type_count"])
    print("status", data["node_status_counts"])
    print("implemented", [(n["id"], n["summary"]) for n in data["implemented_nodes"]])
    print("reused types", [t["type"] for t in data["reused_source"]["declared_types"]])
    for rel, cfg in data["assets_config"].items():
        print(rel, {k: v for k, v in cfg.items() if k in ("attributes", "meter", "kind", "recovery", "behaviorId")})


if __name__ == "__main__":
    main()
