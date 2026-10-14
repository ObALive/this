"""从 v1 清理图继续执行不限层数的依赖传递化简，并生成独立 v2 交付。"""
from pathlib import Path
from collections import defaultdict, deque
from datetime import datetime
import hashlib
import json
import sqlite3
import sys
import threading
import urllib.request

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT / "Tool/项目网络图"))
import db
import model as M
import server
import store

SOURCE = OUT / "N01_依赖清理新图_v1.sqlite"
NEWLIB = OUT / "N01_完整依赖清理新图_v2.sqlite"
EXPORT = OUT / "N01_完整依赖清理新图_v2.md"
FULL_MODEL = OUT / "N01_完整依赖清理模型_v2.json"
MAPPING = OUT / "N01_完整依赖清理功能映射_v2.json"
VERIFY = OUT / "N01_完整依赖清理核验_v2.json"
ENTRY = OUT / "N01_完整依赖清理交付入口_v2.md"
AUDIT = OUT / "N01_完整依赖清理系统操作_v2.md"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def persist(path, value):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8")


def parent_map(graph):
    result = defaultdict(set)
    for edge in M.build_edges(graph)[0]:
        result[edge["to"]].add(edge["from"])
    return result


def closure(graph):
    parents = parent_map(graph)
    result = {}
    for node in graph.nodes:
        seen = set()
        queue = list(parents[node.id])
        while queue:
            current = queue.pop()
            if current in seen:
                continue
            seen.add(current)
            queue.extend(parents[current])
        assert node.id not in seen, "依赖环"
        result[node.id] = seen
    return result


def alternate_path(graph, node_id, target_id):
    """当前引用已经临时移除；返回经其余边到目标的最短上游路径。"""
    parents = parent_map(graph)
    queue = deque([(node_id, [node_id])])
    seen = {node_id}
    while queue:
        current, path = queue.popleft()
        for upstream in parents[current]:
            next_path = path + [upstream]
            if upstream == target_id:
                return next_path
            if upstream not in seen:
                seen.add(upstream)
                queue.append((upstream, next_path))
    return None


assert SOURCE.exists(), "缺少 v1 清理图"
for path in (NEWLIB, EXPORT, FULL_MODEL, MAPPING, VERIFY, ENTRY, AUDIT):
    assert not path.exists(), f"为遵守文件隔离，不覆盖已有文件：{path.name}"

before = db.load_model(SOURCE)
assert not M.validate(before)["stats"]["errors"]
before_stats = M.serialize(before)["stats"]
before_closure = closure(before)
after = M.model_from_dict(db.model_payload(before))


def label(graph, node_id):
    return graph.index_label(graph.node(node_id))


removed = []
passes = 0
while True:
    removed_this_pass = 0
    passes += 1
    for node in after.nodes:
        for ref in list(node.refs):
            index = node.refs.index(ref)
            node.refs.pop(index)
            witness = alternate_path(after, node.id, ref.target_id)
            if witness:
                removed.append({
                    "node": label(after, node.id),
                    "dependency": label(after, ref.target_id),
                    "raw": ref.raw,
                    "reason": "该依赖已由其他上游路径传递，显式重复",
                    "witness": [label(after, item) for item in witness],
                    "path_edges": len(witness) - 1,
                })
                removed_this_pass += 1
            else:
                node.refs.insert(index, ref)
    if not removed_this_pass:
        break

after_closure = closure(after)
assert before_closure == after_closure, "完整清理改变了任一节点的上游可达集合"
assert not M.validate(after)["stats"]["errors"]

# 终态强校验：逐条临时删去剩余显式引用，不允许再存在任何替代路径。
remaining_redundant = []
for node in after.nodes:
    for ref in list(node.refs):
        index = node.refs.index(ref)
        node.refs.pop(index)
        witness = alternate_path(after, node.id, ref.target_id)
        node.refs.insert(index, ref)
        if witness:
            remaining_redundant.append({
                "node": label(after, node.id),
                "dependency": label(after, ref.target_id),
                "witness": [label(after, item) for item in witness],
            })
assert not remaining_redundant, remaining_redundant

# 用户要求同一节点在同一其他路线只留最末项；v1 已执行，v2 再独立验证。
rank = {node.id: index for section in after.sections for index, node in enumerate(after.section_nodes(section.id))}
same_route_groups = []
for node in after.nodes:
    groups = defaultdict(list)
    for ref in node.refs:
        groups[after.node(ref.target_id).section_id].append(ref)
    for section_id, refs in groups.items():
        if len(refs) > 1:
            same_route_groups.append({
                "node": label(after, node.id),
                "route": after.section(section_id).title,
                "dependencies": [label(after, ref.target_id) for ref in refs],
                "latest": label(after, max(refs, key=lambda item: rank[item.target_id]).target_id),
            })
assert not same_route_groups, same_route_groups

changed_nodes = sum(
    [(ref.raw, ref.target_id) for ref in node.refs]
    != [(ref.raw, ref.target_id) for ref in after.node(node.id).refs]
    for node in before.nodes
)
source_hash = sha(SOURCE)
preserved = [
    ROOT / "Tool/项目网络图/数据/项目网络图.sqlite",
    OUT / "N01_原图一致性备份_v1.sqlite",
    OUT / "N01_战斗玩家功能新图_v1.sqlite",
    SOURCE,
    OUT / "N01_依赖清理新图_v1.md",
    OUT / "N01_依赖清理完整模型_v1.json",
    OUT / "N01_依赖清理功能映射_v1.json",
    OUT / "N01_依赖清理交付入口_v1.md",
]
preserved_hashes = {str(path): sha(path) for path in preserved}

with db.connect(SOURCE, readonly=True) as src, sqlite3.connect(NEWLIB) as dst:
    src.backup(dst)

store.DB_FILE = NEWLIB
store.DATA_DIR = OUT
store.BACKUP_DIR = OUT
store.EXPORT_DIR = OUT


class Quiet(server.Handler):
    def log_message(self, *args):
        pass


http = server.ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
thread = threading.Thread(target=http.serve_forever, daemon=True)
thread.start()


def api(path, payload):
    request = urllib.request.Request(
        f"http://127.0.0.1:{http.server_port}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read())
    assert result["ok"]
    return result


api_log = []
try:
    for node in after.nodes:
        old_refs = [(ref.raw, ref.target_id) for ref in before.node(node.id).refs]
        new_refs = [(ref.raw, ref.target_id) for ref in node.refs]
        if old_refs == new_refs:
            continue
        payload = {
            "node_id": node.id,
            "refs": [{"raw": ref.raw, "target_id": ref.target_id} for ref in node.refs],
            "reparse": False,
        }
        response = api("/api/op", {"op": "update_node", "args": payload})
        api_log.append({"node": label(after, node.id), "args": payload, "log": response.get("log", [])})
    exported = api("/api/export", {"path": "Output/N01-战斗玩家功能补图/" + EXPORT.name})
    current = db.load_model(NEWLIB)
    current_stats = M.serialize(current)["stats"]
    assert closure(current) == before_closure
    assert not M.validate(current)["stats"]["errors"]
    assert exported["markdown"] == M.to_markdown(current)
    for old in before.nodes:
        new = current.node(old.id)
        assert old.summary == new.summary
        assert old.body == new.body
        assert old.objects == new.objects
        assert old.notes == new.notes
        assert old.manual == new.manual
        assert old.number == new.number
        assert [(ref.raw, ref.target_id) for ref in new.refs] == [
            (ref.raw, ref.target_id) for ref in after.node(old.id).refs
        ]
    assert all(sha(Path(path)) == value for path, value in preserved_hashes.items())

    persist(FULL_MODEL, db.model_payload(current))
    data = json.loads((OUT / "N01_依赖清理功能映射_v1.json").read_text(encoding="utf-8"))
    keys = {item["new_location"]: item["key"] for item in data}
    nodes = {current.index_label(node): node for node in current.nodes}
    for item in data:
        item["refs"] = [keys[label(current, ref.target_id)] for ref in nodes[item["new_location"]].refs]
    persist(MAPPING, data)

    timeline_check = []
    for node in current.nodes:
        node_label = current.index_label(node)
        if node_label in ("时间轴 3", "时间轴 6"):
            timeline_check.append({
                "node": node_label,
                "explicit_dependencies": [label(current, ref.target_id) for ref in node.refs],
                "all_upstream_contains_角色技能1": any(
                    label(current, item) == "角色行为/角色技能 1" for item in closure(current)[node.id]
                ),
            })

    result = {
        "checked_at": datetime.now().astimezone().isoformat(),
        "source_database": str(SOURCE),
        "source_sha256": source_hash,
        "delivery_database": str(NEWLIB),
        "delivery_sha256": sha(NEWLIB),
        "before": before_stats,
        "after": current_stats,
        "additional_removed_refs": len(removed),
        "additional_changed_nodes": changed_nodes,
        "passes": passes,
        "removed": removed,
        "remaining_redundant_explicit_refs": remaining_redundant,
        "same_target_route_multiple_refs": same_route_groups,
        "all_145_ancestor_sets_equal": True,
        "all_node_content_and_number_unchanged": True,
        "export_matches_model": True,
        "timeline_3_and_6_check": timeline_check,
        "existing_files_unchanged": preserved_hashes,
        "sqlite": db.verify(NEWLIB),
        "api_operations": api_log,
        "upstream_gaps_unchanged": 14,
        "full_coverage_achieved": False,
    }
    persist(VERIFY, result)

    lines = [
        "# N01 完整依赖清理交付 v2",
        "",
        "已修正 v1 的三层检查上限，现按任意长度的完整上游路径清理。删除一条显式引用后，只要仍可经其他边到达同一依赖，该引用即删除。",
        "",
        f"在 v1 基础上继续删除 {len(removed)} 条显式引用，涉及 {changed_nodes} 个节点；显式引用 {before_stats['explicit_edges']} → {current_stats['explicit_edges']}，不同依赖边 {before_stats['edges']} → {current_stats['edges']}。145 个节点的完整上游可达集合逐项不变。",
        "",
        "终态已逐条反证检查：临时删去每一条剩余显式引用后，均不存在其他路径到达相同依赖；同一节点也不存在指向同一其他路线的多条显式引用。",
        "",
        "| 产物 | 文件 |",
        "| --- | --- |",
        f"| 可编辑图库 | `{NEWLIB.name}` |",
        f"| Markdown | `{EXPORT.name}` |",
        f"| 全字段模型 | `{FULL_MODEL.name}` |",
        f"| 功能映射 | `{MAPPING.name}` |",
        f"| 完整核验 | `{VERIFY.name}` |",
        "",
        "打开命令：",
        "",
        "```powershell",
        "python -B -X utf8 'Output/N01-战斗玩家功能补图/N01_打开完整依赖清理图_v2.py' --no-browser --port 8793",
        "```",
        "",
        "访问 http://127.0.0.1:8793/，Ctrl+C 停止。",
        "",
        "## v1 遗漏删除明细",
        "",
        "| 节点 | 删除引用 | 替代路径 | 路径边数 |",
        "| --- | --- | --- | ---: |",
    ]
    for item in removed:
        lines.append(
            "| " + item["node"] + " | " + item["dependency"] + " | "
            + " → ".join(item["witness"]) + " | " + str(item["path_edges"]) + " |"
        )
    lines.extend([
        "",
        "v1 图及此前产物均未覆盖；v2 为新的独立交付。14 项上游未决及完整覆盖状态不受此次依赖书写清理影响。",
        "",
    ])
    persist(ENTRY, "\n".join(lines))
    print(json.dumps({
        "before": before_stats,
        "after": current_stats,
        "additional_removed_refs": len(removed),
        "additional_changed_nodes": changed_nodes,
        "passes": passes,
        "remaining_redundant_explicit_refs": len(remaining_redundant),
        "same_target_route_multiple_refs": len(same_route_groups),
        "delivery_sha256": sha(NEWLIB),
        "timeline_check": timeline_check,
    }, ensure_ascii=False, indent=2))
finally:
    http.shutdown()
    http.server_close()
    thread.join(timeout=5)
    persist(AUDIT, "\n".join([
        "# N01 完整依赖清理系统操作 v2",
        "",
        f"时间：{datetime.now().astimezone().isoformat()}",
        "执行命令：`python -B -X utf8 Output/N01-战斗玩家功能补图/N01_完整依赖清理交付_v2.py`",
        "执行目的：修正 v1 的三层检查上限，按任意长度的其他上游路径完成依赖传递化简。",
        f"影响范围：仅创建本任务 v2 新产物；临时服务监听 127.0.0.1:{http.server_port}。",
        "执行结果：服务已停止；详情见 `N01_完整依赖清理核验_v2.json`。",
        "恢复方案：v1 清理图及此前所有产物均保留，可直接改用旧入口。",
        "",
    ]))
