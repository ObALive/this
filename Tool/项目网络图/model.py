"""项目网络图模型。

职责：
1. 把任务书 Markdown 解析成「开发路线（章节） + 目标条目（节点）」的网络图数据；
2. 按「同一章节下的编号条目依次向上依赖」生成隐式依赖边；
3. 把条目括号内的「依赖前置 / 需要一并实现的对象 / 设计方式说明」拆开并保留可编辑结构；
4. 支持插入、删除、移动条目，并自动处理后续编号顺位偏移与正文中的引用改写；
5. 输出校验问题（未解析引用、成环、空条目、对象缺实现路径等）。

本模块不依赖任何第三方库，也不做输入输出，便于单独测试。
"""

from __future__ import annotations

import copy
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable

# --------------------------------------------------------------------------
# 常量与正则
# --------------------------------------------------------------------------

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
ITEM_RE = re.compile(r"^(\d+)\s*[.、．]\s*(.*)$")
CONT_RE = re.compile(r"^(?:\s{2,}|\t+)(\S.*)$")

# 正文里显式标注概要的写法：`【概要】概要【说明】说明`
SUMMARY_MARK_RE = re.compile(r"^【概要】\s*(.*?)\s*(?:【说明】\s*(.*))?$", re.S)

# 括号内的依赖写法：`依赖角色移动1`、`依赖元效果`、`依赖地图2、角色技能1`
DEP_PREFIX_RE = re.compile(r"^依赖\s*(.*)$", re.S)
DEP_TOKEN_RE = re.compile(r"^\s*(?P<name>[^0-9，,、；;。：:\s]+?)\s*(?P<num>\d*)\s*$")

OBJECT_PREFIX_RE = re.compile(r"^(元对象|元技能|元效果|元系统|元属性)\s*[-－]")
OBJECT_WORD_RE = re.compile(r"(组件|系统|对象|管理器|Manager)")

# 括号内信息的分段符
SPLIT_RE = re.compile(r"[，,、；;]")

SUMMARY_MAX = 24

PAREN_OPEN = "（("
PAREN_CLOSE = "）)"


# --------------------------------------------------------------------------
# 数据类
# --------------------------------------------------------------------------


@dataclass
class Section:
    """开发路线。一个带编号条目的标题（一级或二级标题）对应一条路线。"""

    id: str
    title: str
    level: int
    parent_id: str | None = None
    start_number: int = 1
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Ref:
    """条目声明的一条依赖引用。"""

    raw: str
    section: str = ""
    number: int | None = None
    target_id: str | None = None
    reason: str = ""

    @property
    def resolved(self) -> bool:
        return self.target_id is not None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["resolved"] = self.resolved
        return d


@dataclass
class ObjectItem:
    """实现本目标需要一并构建并实现的对象。实现路径是可选项。"""

    name: str
    note: str = ""
    path: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Node:
    """网络图节点：一条实现目标。"""

    id: str
    section_id: str
    number: int
    summary: str
    body: str = ""
    refs: list[Ref] = field(default_factory=list)
    objects: list[ObjectItem] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    manual: dict = field(default_factory=dict)

    # -- 派生 ---------------------------------------------------------------
    @property
    def summary_is_auto(self) -> bool:
        return self.summary == auto_summary(self.body)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "section_id": self.section_id,
            "number": self.number,
            "summary": self.summary,
            "summary_is_auto": self.summary_is_auto,
            "body": self.body,
            "refs": [r.to_dict() for r in self.refs],
            "objects": [o.to_dict() for o in self.objects],
            "notes": list(self.notes),
            "manual": dict(self.manual),
        }


@dataclass
class Model:
    title: str = ""
    source: str = ""
    preamble: str = ""
    sections: list[Section] = field(default_factory=list)
    nodes: list[Node] = field(default_factory=list)
    aliases: dict[str, str] = field(default_factory=dict)
    meta: dict = field(default_factory=dict)

    # -- 查询 ---------------------------------------------------------------
    def section(self, section_id: str) -> Section | None:
        for s in self.sections:
            if s.id == section_id:
                return s
        return None

    def node(self, node_id: str) -> Node | None:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def section_nodes(self, section_id: str) -> list[Node]:
        return [n for n in self.nodes if n.section_id == section_id]

    def section_path(self, section: Section) -> list[Section]:
        """从根到自身的标题链。"""
        chain: list[Section] = []
        cur: Section | None = section
        seen: set[str] = set()
        while cur is not None and cur.id not in seen:
            seen.add(cur.id)
            chain.append(cur)
            cur = self.section(cur.parent_id) if cur.parent_id else None
        return list(reversed(chain))

    def index_label(self, node: Node) -> str:
        sec = self.section(node.section_id)
        if sec is None:
            return str(node.number)
        titles = [s.title for s in self.section_path(sec)]
        return f"{'/'.join(titles)} {node.number}"

    def next_id(self, prefix: str) -> str:
        used = {s.id for s in self.sections} | {n.id for n in self.nodes}
        i = 1
        while f"{prefix}{i}" in used:
            i += 1
        return f"{prefix}{i}"


# --------------------------------------------------------------------------
# 文本工具
# --------------------------------------------------------------------------


def auto_summary(body: str) -> str:
    """从实现目标说明里推出实现目标概要：取第一个句读之前的短语。"""
    text = (body or "").strip()
    if not text:
        return ""
    m = re.match(r"^(.{2,%d}?)[，。；：,;:.]" % SUMMARY_MAX, text)
    if m:
        return m.group(1).strip()
    if len(text) <= SUMMARY_MAX:
        return text
    return text[:SUMMARY_MAX].strip()


def scan_parentheticals(text: str) -> list[dict]:
    """扫描文本中的括号段，返回 [{start, end, content}, ...]。支持嵌套括号。"""
    spans: list[dict] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in PAREN_OPEN:
            depth = 1
            j = i + 1
            while j < n and depth:
                if text[j] in PAREN_OPEN:
                    depth += 1
                elif text[j] in PAREN_CLOSE:
                    depth -= 1
                j += 1
            if depth == 0:
                spans.append({"start": i, "end": j, "content": text[i + 1 : j - 1]})
                i = j
                continue
        i += 1
    return spans


def split_parentheticals(text: str) -> tuple[str, list[str]]:
    """把文本按括号拆开，返回（去掉全部括号内容的文本, 括号内容列表）。"""
    spans = scan_parentheticals(text)
    plain = _strip_spans(text, spans) if spans else text
    cleaned = re.sub(r"\s+", " ", plain).strip()
    return cleaned, [s["content"] for s in spans]


def _strip_spans(text: str, spans: list[dict]) -> str:
    out: list[str] = []
    cursor = 0
    for sp in sorted(spans, key=lambda s: s["start"]):
        if sp["start"] < cursor:
            continue
        out.append(text[cursor : sp["start"]])
        cursor = sp["end"]
    out.append(text[cursor:])
    return "".join(out)


def _looks_like_object(seg: str) -> bool:
    seg = seg.strip()
    if not seg or len(seg) > 24:
        return False
    if seg.startswith("依赖"):
        return False
    if OBJECT_PREFIX_RE.match(seg):
        return True
    if seg.endswith("组件") or seg.endswith("管理器") or seg.endswith("系统") or seg.endswith("对象"):
        return True
    return False


def _parse_ref_token(seg: str) -> Ref | None:
    m = DEP_TOKEN_RE.match(seg.strip())
    if not m:
        return None
    name = m.group("name").strip()
    num = m.group("num").strip()
    if not name:
        return None
    return Ref(raw=seg.strip(), section=name, number=int(num) if num else None)


def _dep_remainder(seg: str) -> str:
    m = DEP_PREFIX_RE.match(seg.strip())
    return (m.group(1) if m else seg).strip()


def _parse_object_group(group: str) -> list[ObjectItem]:
    """解析一个括号里的对象声明，支持「对象A、对象B」与「对象，用途说明」。"""
    objects: list[ObjectItem] = []
    for piece in re.split(r"[、；;]", group):
        piece = piece.strip()
        if not piece:
            continue
        head, _, tail = piece.partition("，")
        if not _:
            head, _, tail = piece.partition(",")
        head = head.strip()
        tail = tail.strip()
        if _looks_like_object(head):
            objects.append(ObjectItem(name=head, note=tail))
        elif objects:
            extra = piece
            objects[-1].note = (objects[-1].note + "、" + extra).strip("、")
        else:
            objects.append(ObjectItem(name=piece))
    return objects


def parse_body(body: str) -> tuple[str, str | None, list[Ref], list[ObjectItem], list[str]]:
    """解析条目正文。

    返回（实现目标说明, 显式概要或 None, 依赖引用, 需要实现的对象, 其他说明性括号内容）。
    只有被判为依赖、对象或长段设计说明的括号会被摘出，短的内联括号保留在说明正文里。
    """
    text = body or ""
    spans = scan_parentheticals(text)
    extracted: list[dict] = []
    refs: list[Ref] = []
    objects: list[ObjectItem] = []
    notes: list[str] = []

    for sp in spans:
        g = sp["content"].strip()
        if not g:
            continue
        if g.startswith("依赖"):
            extracted.append(sp)
            segments = [s for s in SPLIT_RE.split(g) if s.strip()]
            for idx, seg in enumerate(segments):
                seg = seg.strip()
                if seg.startswith("依赖"):
                    ref = _parse_ref_token(_dep_remainder(seg))
                    if ref:
                        refs.append(ref)
                    else:
                        notes.append(seg)
                elif _looks_like_object(seg):
                    objects.extend(_parse_object_group(seg))
                elif idx > 0 and _parse_ref_token(seg):
                    ref = _parse_ref_token(seg)
                    if ref:
                        refs.append(ref)
                    else:
                        notes.append(seg)
                else:
                    notes.append(seg)
            continue

        head = re.split(r"[，,]", g, maxsplit=1)[0]
        if _looks_like_object(head):
            extracted.append(sp)
            objects.extend(_parse_object_group(g))
            continue

        if len(g) > 24:
            extracted.append(sp)
            notes.append(g)

    detail = _strip_spans(text, extracted) if extracted else text
    detail = re.sub(r"\s+", " ", detail).strip()
    detail = detail.strip("，,、；;。 ").strip()

    summary_override: str | None = None
    m = SUMMARY_MARK_RE.match(detail)
    if m:
        summary_override = m.group(1).strip()
        detail = (m.group(2) or "").strip()

    return detail, summary_override, refs, objects, notes


# --------------------------------------------------------------------------
# 章节名解析
# --------------------------------------------------------------------------


def _norm(text: str) -> str:
    return re.sub(r"[\s　]", "", text or "")


def find_section_by_hint(model: Model, hint: str) -> tuple[Section | None, str]:
    """按引用里写的章节名找章节。支持全名、路径名、别名与后缀匹配。"""
    hint_n = _norm(hint)
    if not hint_n:
        return None, "引用未写章节名"

    alias = model.aliases.get(hint_n)
    if alias:
        hint_n = _norm(alias)

    for s in model.sections:
        if _norm(s.title) == hint_n:
            return s, ""

    for s in model.sections:
        path = "/".join(x.title for x in model.section_path(s))
        if _norm(path) == hint_n or _norm(path.replace("/", "")) == hint_n:
            return s, ""

    suffix_hits = [
        s
        for s in model.sections
        if len(hint_n) >= 2
        and (_norm(s.title).endswith(hint_n) or hint_n.endswith(_norm(s.title)))
    ]
    if len(suffix_hits) == 1:
        return suffix_hits[0], ""
    if len(suffix_hits) > 1:
        names = "、".join(s.title for s in suffix_hits)
        return None, f"引用「{hint}」匹配到多条开发路线：{names}"
    return None, f"没有名为「{hint}」的开发路线"


def resolve_ref_text(model: Model, raw: str) -> tuple[str | None, str, str, int | None]:
    """解析一段引用文本，返回（目标节点 id, 原因, 章节名, 编号）。"""
    text = DEP_PREFIX_RE.sub("", (raw or "").strip(), count=1).strip()
    m = DEP_TOKEN_RE.match(text)
    if not m:
        return None, f"无法识别的依赖写法「{raw}」", "", None
    name = m.group("name").strip()
    num_text = m.group("num").strip()
    number = int(num_text) if num_text else None

    sec, reason = find_section_by_hint(model, name)
    if sec is None:
        return None, reason, name, number
    if number is None:
        first = model.section_nodes(sec.id)
        if not first:
            return None, f"开发路线「{sec.title}」下还没有条目", sec.title, None
        return first[0].id, "", sec.title, None

    for n in model.section_nodes(sec.id):
        if n.number == number:
            return n.id, "", sec.title, number
    return None, f"开发路线「{sec.title}」下没有编号 {number}", sec.title, number


def resolve_refs(model: Model) -> None:
    """解析所有尚未绑定目标的引用。已手工绑定的引用保持不动。"""
    for node in model.nodes:
        for ref in node.refs:
            if ref.target_id and model.node(ref.target_id):
                ref.reason = ""
                continue
            ref.target_id = None
            target_id, reason, section_title, number = resolve_ref_text(model, ref.raw)
            ref.target_id = target_id
            ref.reason = "" if target_id else reason
            if section_title:
                ref.section = section_title
            ref.number = number


def sync_ref_raw(model: Model, ref: Ref) -> None:
    """编号或章节名变化后，把已绑定引用的文本改写成新的规范写法。"""
    target = model.node(ref.target_id) if ref.target_id else None
    if target is None:
        return
    sec = model.section(target.section_id)
    if sec is None:
        return
    if _norm(ref.section) == _norm(sec.title) and ref.number == target.number:
        return
    target_id, _reason, _s, _n = resolve_ref_text(model, ref.raw)
    if target_id == ref.target_id:
        # 原文写法（例如别名「地图1」）仍能指到同一个目标，保留原写法
        ref.section = sec.title
        ref.number = target.number
        return
    ref.section = sec.title
    ref.number = target.number
    ref.raw = f"{sec.title}{target.number}"


def sync_all_refs(model: Model) -> None:
    for node in model.nodes:
        for ref in node.refs:
            sync_ref_raw(model, ref)


# --------------------------------------------------------------------------
# Markdown 解析
# --------------------------------------------------------------------------


def parse_markdown(text: str, source: str = "", title: str = "") -> Model:
    """把任务书 Markdown 解析成网络图模型。"""
    model = Model(source=source, title=title or Path(source).stem if source else (title or ""))
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    heading_stack: list[Section] = []
    current_section: Section | None = None
    current_node: Node | None = None
    preamble: list[str] = []
    warnings: list[str] = []
    n_seq = 0

    for line in lines:
        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            if level > 3:
                level = 3
            title_text = heading.group(2).strip()
            parent = None
            while heading_stack and heading_stack[-1].level >= level:
                heading_stack.pop()
            if heading_stack:
                parent = heading_stack[-1].id
            section = Section(
                id=f"s{len(model.sections) + 1}",
                title=title_text,
                level=level,
                parent_id=parent,
            )
            model.sections.append(section)
            heading_stack.append(section)
            current_section = section
            current_node = None
            continue

        item = ITEM_RE.match(line)
        if item:
            if current_section is None:
                # 标题出现之前的编号列表属于任务背景说明，不计入网络图
                preamble.append(line.strip())
                current_node = None
                continue
            n_seq += 1
            number = int(item.group(1))
            body = item.group(2).strip()
            detail, summary_override, refs, objects, notes = parse_body(body)
            node = Node(
                id=f"n{n_seq}",
                section_id=current_section.id,
                number=number,
                summary=summary_override if summary_override is not None else auto_summary(detail),
                body=detail,
                refs=refs,
                objects=objects,
                notes=notes,
            )
            model.nodes.append(node)
            current_node = node
            continue

        if current_node is not None:
            cont = CONT_RE.match(line)
            if cont and line.strip():
                extra = cont.group(1).strip()
                current_node.body = (current_node.body + extra).strip()
                current_node.summary = auto_summary(current_node.body)
                continue

        if line.strip():
            if current_section is None:
                preamble.append(line.strip())
            else:
                current_section.note = (current_section.note + "\n" + line.strip()).strip()

    model.preamble = "\n".join(preamble).strip()

    # 编号规范化：同一路线内按出现顺序顺排，起点取该路线第一条的编号
    for section in model.sections:
        nodes = model.section_nodes(section.id)
        if nodes:
            section.start_number = nodes[0].number
        numbers = [n.number for n in nodes]
        if numbers and numbers != list(range(section.start_number, section.start_number + len(numbers))):
            warnings.append(
                f"路线「{section.title}」的编号不是连续顺排（原文：{'、'.join(str(x) for x in numbers)}），已按出现顺序重排"
            )
        for i, node in enumerate(nodes):
            node.number = section.start_number + i

    resolve_refs(model)
    model.meta["warnings"] = warnings
    model.meta.setdefault("aliases_note", "")
    return model


def model_from_dict(data: dict) -> Model:
    """从序列化数据恢复模型（用于撤销与本地存档）。"""
    model = Model(
        title=data.get("title", ""),
        source=data.get("source", ""),
        preamble=data.get("preamble", ""),
        aliases=dict(data.get("aliases", {}) or {}),
        meta=copy.deepcopy(data.get("meta", {}) or {}),
    )
    for s in data.get("sections", []):
        model.sections.append(
            Section(
                id=s["id"],
                title=s.get("title", ""),
                level=int(s.get("level", 2)),
                parent_id=s.get("parent_id"),
                start_number=int(s.get("start_number", 1)),
                note=s.get("note", ""),
            )
        )
    for n in data.get("nodes", []):
        node = Node(
            id=n["id"],
            section_id=n["section_id"],
            number=int(n.get("number", 1)),
            summary=n.get("summary", ""),
            body=n.get("body", ""),
            notes=list(n.get("notes", []) or []),
            manual=dict(n.get("manual", {}) or {}),
        )
        for r in n.get("refs", []) or []:
            node.refs.append(
                Ref(
                    raw=r.get("raw", ""),
                    section=r.get("section", ""),
                    number=r.get("number"),
                    target_id=r.get("target_id"),
                )
            )
        for o in n.get("objects", []) or []:
            node.objects.append(ObjectItem(name=o.get("name", ""), note=o.get("note", ""), path=o.get("path", "")))
        model.nodes.append(node)
    return model


# --------------------------------------------------------------------------
# 依赖边
# --------------------------------------------------------------------------


def build_edges(model: Model) -> tuple[list[dict], list[str]]:
    """生成依赖边。同路线内相邻条目依次向上依赖，另有条目显式声明的跨路线依赖。"""
    edges: list[dict] = []
    index: dict[tuple[str, str], int] = {}
    warnings: list[str] = []

    def add(src: str, dst: str, kind: str, raw: str = "") -> None:
        if src == dst:
            warnings.append(f"条目 {model.index_label(model.node(dst))} 依赖了自身")
            return
        key = (src, dst)
        if key in index:
            i = index[key]
            if kind == "explicit" and edges[i]["kind"] == "chain":
                edges[i]["kind"] = "chain+explicit"
                edges[i]["raw"] = raw
            return
        index[key] = len(edges)
        edges.append({"from": src, "to": dst, "kind": kind, "raw": raw})

    for section in model.sections:
        nodes = model.section_nodes(section.id)
        for prev, cur in zip(nodes, nodes[1:]):
            add(prev.id, cur.id, "chain")

    for node in model.nodes:
        for ref in node.refs:
            if ref.target_id and model.node(ref.target_id):
                add(ref.target_id, node.id, "explicit", ref.raw)

    return edges, warnings


# --------------------------------------------------------------------------
# 校验
# --------------------------------------------------------------------------


def validate(model: Model) -> dict:
    """返回校验结果：问题清单 + 统计。"""
    issues: list[dict] = []
    edges, edge_warnings = build_edges(model)

    for node in model.nodes:
        label = model.index_label(node)
        if not node.body.strip() and not node.summary.strip():
            issues.append({"level": "warning", "kind": "empty_node", "node_id": node.id, "text": f"{label} 没有正文，无法判断实现目标"})
        for ref in node.refs:
            if ref.target_id is None:
                issues.append(
                    {
                        "level": "error",
                        "kind": "unresolved_ref",
                        "node_id": node.id,
                        "text": f"{label} 的依赖「{ref.raw}」未解析：{ref.reason or '未知原因'}",
                    }
                )
        for obj in node.objects:
            if not obj.path.strip():
                issues.append(
                    {
                        "level": "info",
                        "kind": "object_missing_path",
                        "node_id": node.id,
                        "text": f"{label} 的对象「{obj.name}」未写实现路径（可选项）",
                    }
                )

    for w in edge_warnings:
        issues.append({"level": "warning", "kind": "self_ref", "text": w})

    # 成环检测
    adjacency: dict[str, list[str]] = {n.id: [] for n in model.nodes}
    for e in edges:
        adjacency.setdefault(e["from"], []).append(e["to"])

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n.id: WHITE for n in model.nodes}
    stack: list[str] = []
    reported: set[frozenset[str]] = set()

    def dfs(uid: str) -> None:
        color[uid] = GRAY
        stack.append(uid)
        for vid in adjacency.get(uid, []):
            if color.get(vid, WHITE) == WHITE:
                dfs(vid)
            elif color.get(vid) == GRAY:
                cycle = stack[stack.index(vid) :] + [vid]
                key = frozenset(cycle)
                if key not in reported:
                    reported.add(key)
                    labels = [model.index_label(model.node(x)) for x in cycle if model.node(x)]
                    issues.append(
                        {
                            "level": "error",
                            "kind": "cycle",
                            "node_id": vid,
                            "text": "依赖成环：" + " → ".join(labels),
                        }
                    )
        stack.pop()
        color[uid] = BLACK

    for node in model.nodes:
        if color[node.id] == WHITE:
            dfs(node.id)

    for section in model.sections:
        if not model.section_nodes(section.id):
            issues.append(
                {
                    "level": "info",
                    "kind": "empty_section",
                    "section_id": section.id,
                    "text": f"开发路线「{section.title}」下没有条目",
                }
            )

    order = {"error": 0, "warning": 1, "info": 2}
    issues.sort(key=lambda i: order.get(i["level"], 3))

    object_usage: dict[str, list[str]] = {}
    for node in model.nodes:
        for obj in node.objects:
            object_usage.setdefault(obj.name, []).append(node.id)

    stats = {
        "sections": len(model.sections),
        "nodes": len(model.nodes),
        "edges": len(edges),
        "chain_edges": sum(1 for e in edges if e["kind"].startswith("chain")),
        "explicit_edges": sum(1 for e in edges if e["kind"].startswith("explicit") or e["kind"] == "chain+explicit"),
        "errors": sum(1 for i in issues if i["level"] == "error"),
        "warnings": sum(1 for i in issues if i["level"] == "warning"),
        "infos": sum(1 for i in issues if i["level"] == "info"),
        "objects": len(object_usage),
        "objects_with_path": len({o.name for n in model.nodes for o in n.objects if o.path.strip()}),
        "unresolved_refs": sum(1 for n in model.nodes for r in n.refs if not r.resolved),
        "root_nodes": sum(1 for n in model.nodes if not any(e["to"] == n.id for e in edges)),
    }
    return {"issues": issues, "stats": stats, "object_usage": object_usage}


# --------------------------------------------------------------------------
# 序列化
# --------------------------------------------------------------------------


def serialize(model: Model) -> dict:
    """输出给前端使用的完整视图数据。"""
    check = validate(model)
    edges, _ = build_edges(model)

    sections = []
    for s in model.sections:
        nodes = model.section_nodes(s.id)
        path = "/".join(x.title for x in model.section_path(s))
        sections.append(
            {
                "id": s.id,
                "title": s.title,
                "level": s.level,
                "parent_id": s.parent_id,
                "path": path,
                "start_number": s.start_number,
                "note": s.note,
                "node_ids": [n.id for n in nodes],
            }
        )

    nodes = []
    for n in model.nodes:
        d = n.to_dict()
        d["index_label"] = model.index_label(n)
        d["detail"] = n.body
        nodes.append(d)

    return {
        "title": model.title,
        "source": model.source,
        "preamble": model.preamble,
        "aliases": dict(model.aliases),
        "meta": model.meta,
        "sections": sections,
        "nodes": nodes,
        "edges": edges,
        "issues": check["issues"],
        "stats": check["stats"],
        "object_usage": check["object_usage"],
    }


# --------------------------------------------------------------------------
# Markdown 导出
# --------------------------------------------------------------------------


def to_markdown(model: Model) -> str:
    """把模型导出回任务书 Markdown。编号与引用均按当前模型生成。"""
    lines: list[str] = []
    if model.preamble.strip():
        lines.append(model.preamble.strip())
        lines.append("")

    for section in model.sections:
        lines.append("#" * max(1, min(3, section.level)) + " " + section.title)
        if section.note.strip():
            lines.append(section.note.strip())
        for node in model.section_nodes(section.id):
            item = f"{node.number}. {node.body.strip()}"
            if node.summary.strip() and node.summary.strip() != auto_summary(node.body):
                item += f"【概要】{node.summary.strip()}"
            parts: list[str] = []
            if node.refs:
                parts.append("（依赖" + "、".join(r.raw for r in node.refs) + "）")
            if node.objects:
                rendered = []
                for o in node.objects:
                    rendered.append(f"{o.name}，{o.note}" if o.note.strip() else o.name)
                parts.append("（" + "；".join(rendered) + "）")
            for note in node.notes:
                parts.append(f"（{note}）")
            item += "".join(parts)
            lines.append(item)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------
# 编辑操作
# --------------------------------------------------------------------------


def _log(log: list[str], text: str) -> None:
    log.append(text)


def renumber_section(model: Model, section_id: str, log: list[str] | None = None) -> list[dict]:
    """把一条路线下的条目编号顺排，并改写所有相关引用。返回编号变化的记录。"""
    section = model.section(section_id)
    if section is None:
        return []
    nodes = model.section_nodes(section_id)
    changes: list[dict] = []
    for i, node in enumerate(nodes):
        new_number = section.start_number + i
        if node.number != new_number:
            changes.append({"node_id": node.id, "old": node.number, "new": new_number})
            node.number = new_number
    if changes and log is not None:
        detail = "、".join(f"{c['old']}→{c['new']}" for c in changes)
        _log(log, f"路线「{section.title}」后续编号顺位偏移：{detail}")
    sync_all_refs(model)
    return changes


def insert_node(
    model: Model,
    section_id: str,
    after_node_id: str | None = None,
    before_node_id: str | None = None,
    summary: str = "",
    body: str = "",
    refs: Iterable[dict] | None = None,
    objects: Iterable[dict] | None = None,
    notes: Iterable[str] | None = None,
    log: list[str] | None = None,
) -> Node:
    """在指定条目之后（或之前）插入新条目；两者都不给则插入该路线末尾。"""
    section = model.section(section_id)
    if section is None:
        raise ValueError(f"未知的开发路线：{section_id}")
    log = log if log is not None else []

    node = Node(
        id=model.next_id("n"),
        section_id=section_id,
        number=section.start_number,
        summary=summary.strip() or auto_summary(body),
        body=body.strip(),
        notes=[str(x) for x in (notes or [])],
    )
    for r in refs or []:
        node.refs.append(Ref(raw=str(r.get("raw", "")).strip(), target_id=r.get("target_id")))
    for o in objects or []:
        node.objects.append(ObjectItem(name=str(o.get("name", "")).strip(), note=str(o.get("note", "")), path=str(o.get("path", ""))))

    if after_node_id:
        target = model.node(after_node_id)
        if target is None:
            raise ValueError(f"未知的插入位置：{after_node_id}")
        model.nodes.insert(model.nodes.index(target) + 1, node)
        _log(log, f"已在「{model.index_label(target)}」之后插入条目")
    elif before_node_id:
        target = model.node(before_node_id)
        if target is None:
            raise ValueError(f"未知的插入位置：{before_node_id}")
        model.nodes.insert(model.nodes.index(target), node)
        _log(log, f"已在「{model.index_label(target)}」之前插入条目")
    else:
        siblings = model.section_nodes(section_id)
        if siblings:
            model.nodes.insert(model.nodes.index(siblings[-1]) + 1, node)
        else:
            model.nodes.append(node)
        _log(log, f"已在路线「{section.title}」末尾插入条目")

    renumber_section(model, section_id, log)
    resolve_refs(model)
    _log(log, f"新条目编号为 {section.title}{node.number}")
    return node


def delete_node(model: Model, node_id: str, log: list[str] | None = None) -> dict:
    node = model.node(node_id)
    if node is None:
        raise ValueError(f"未知的条目：{node_id}")
    log = log if log is not None else []
    label = model.index_label(node)
    section_id = node.section_id

    # 解除指向它的引用，保留原文并在正文中标注失效
    affected: list[str] = []
    for other in model.nodes:
        for ref in list(other.refs):
            if ref.target_id == node_id:
                ref.target_id = None
                ref.reason = f"原引用的 {label} 已被删除"
                affected.append(model.index_label(other))
    model.nodes.remove(node)
    renumber_section(model, section_id, log)
    _log(log, f"已删除条目「{label}」")
    if affected:
        _log(log, "以下条目的依赖因此失效，需要重新指定：" + "、".join(sorted(set(affected))))
    return {"deleted": label, "affected": sorted(set(affected))}


def move_node(model: Model, node_id: str, direction: str, log: list[str] | None = None) -> None:
    node = model.node(node_id)
    if node is None:
        raise ValueError(f"未知的条目：{node_id}")
    log = log if log is not None else []
    siblings = model.section_nodes(node.section_id)
    idx = siblings.index(node)
    swap = idx - 1 if direction == "up" else idx + 1
    if swap < 0 or swap >= len(siblings):
        return
    other = siblings[swap]
    i, j = model.nodes.index(node), model.nodes.index(other)
    model.nodes[i], model.nodes[j] = model.nodes[j], model.nodes[i]
    renumber_section(model, node.section_id, log)
    _log(log, f"条目「{model.index_label(node)}」已{'上移' if direction == 'up' else '下移'}")


def update_node(model: Model, node_id: str, payload: dict, log: list[str] | None = None) -> Node:
    """更新条目内容。正文被改写时会重新解析括号内容。"""
    node = model.node(node_id)
    if node is None:
        raise ValueError(f"未知的条目：{node_id}")
    log = log if log is not None else []
    before = model.index_label(node)

    if "body" in payload:
        node.body = str(payload["body"]).strip()
        if payload.get("reparse", True):
            detail, summary_override, refs, objects, notes = parse_body(node.body)
            node.body = detail
            node.refs = refs
            node.objects = objects
            node.notes = notes
            if summary_override is not None:
                node.summary = summary_override
            elif "summary" not in payload:
                node.summary = auto_summary(detail)
            _log(log, "正文已重新解析括号内的依赖与对象")

    if "summary" in payload:
        node.summary = str(payload["summary"]).strip() or auto_summary(node.body)

    if "refs" in payload:
        node.refs = []
        for r in payload["refs"] or []:
            node.refs.append(Ref(raw=str(r.get("raw", "")).strip(), target_id=r.get("target_id")))
        _log(log, "依赖列表已更新")

    if "objects" in payload:
        node.objects = []
        for o in payload["objects"] or []:
            name = str(o.get("name", "")).strip()
            if name:
                node.objects.append(ObjectItem(name=name, note=str(o.get("note", "")), path=str(o.get("path", ""))))
        _log(log, "对象列表已更新")

    if "notes" in payload:
        node.notes = [str(x) for x in (payload["notes"] or []) if str(x).strip()]

    if "manual" in payload:
        node.manual = dict(payload["manual"] or {})

    resolve_refs(model)
    sync_all_refs(model)
    if model.index_label(node) != before:
        _log(log, f"条目索引由「{before}」变为「{model.index_label(node)}」")
    return node


def insert_section(
    model: Model,
    title: str,
    level: int = 2,
    parent_id: str | None = None,
    after_section_id: str | None = None,
    start_number: int = 1,
    log: list[str] | None = None,
) -> Section:
    log = log if log is not None else []
    section = Section(
        id=model.next_id("s"),
        title=title.strip() or "未命名路线",
        level=max(1, min(3, int(level))),
        parent_id=parent_id,
        start_number=int(start_number),
    )
    if after_section_id:
        anchor = model.section(after_section_id)
        if anchor is None:
            raise ValueError(f"未知的路线：{after_section_id}")
        model.sections.insert(model.sections.index(anchor) + 1, section)
    else:
        model.sections.append(section)
    _log(log, f"已新增开发路线「{section.title}」")
    return section


def update_section(model: Model, section_id: str, payload: dict, log: list[str] | None = None) -> Section:
    section = model.section(section_id)
    if section is None:
        raise ValueError(f"未知的路线：{section_id}")
    log = log if log is not None else []
    if "title" in payload:
        old = section.title
        section.title = str(payload["title"]).strip() or old
        if section.title != old:
            _log(log, f"路线「{old}」已改名为「{section.title}」")
    if "start_number" in payload:
        section.start_number = int(payload["start_number"])
    if "note" in payload:
        section.note = str(payload["note"])
    if "parent_id" in payload:
        section.parent_id = payload["parent_id"] or None
    if "level" in payload:
        section.level = max(1, min(3, int(payload["level"])))
    renumber_section(model, section.id, log)
    resolve_refs(model)
    sync_all_refs(model)
    return section


def delete_section(model: Model, section_id: str, log: list[str] | None = None) -> dict:
    section = model.section(section_id)
    if section is None:
        raise ValueError(f"未知的路线：{section_id}")
    log = log if log is not None else []
    removed = model.section_nodes(section_id)
    for node in removed:
        model.nodes.remove(node)
    model.sections.remove(section)
    for other in model.sections:
        if other.parent_id == section_id:
            other.parent_id = section.parent_id
    resolve_refs(model)
    _log(log, f"已删除路线「{section.title}」（含 {len(removed)} 个条目）")
    return {"deleted_nodes": [n.id for n in removed]}


def move_section(model: Model, section_id: str, direction: str, log: list[str] | None = None) -> None:
    section = model.section(section_id)
    if section is None:
        raise ValueError(f"未知的路线：{section_id}")
    log = log if log is not None else []
    siblings = [s for s in model.sections if s.parent_id == section.parent_id]
    idx = siblings.index(section)
    swap = idx - 1 if direction == "up" else idx + 1
    if swap < 0 or swap >= len(siblings):
        return
    other = siblings[swap]
    i, j = model.sections.index(section), model.sections.index(other)
    model.sections[i], model.sections[j] = model.sections[j], model.sections[i]
    _log(log, f"路线「{section.title}」已{'前移' if direction == 'up' else '后移'}")


def apply_op(model: Model, op: str, args: dict) -> dict:
    """统一的操作入口，供 HTTP 服务与测试调用。"""
    args = args or {}
    log: list[str] = []
    if op == "insert_node":
        node = insert_node(
            model,
            section_id=args["section_id"],
            after_node_id=args.get("after_node_id"),
            before_node_id=args.get("before_node_id"),
            summary=args.get("summary", ""),
            body=args.get("body", ""),
            refs=args.get("refs"),
            objects=args.get("objects"),
            notes=args.get("notes"),
            log=log,
        )
        return {"node_id": node.id, "log": log}
    if op == "update_node":
        node = update_node(model, args["node_id"], args, log)
        return {"node_id": node.id, "log": log}
    if op == "delete_node":
        result = delete_node(model, args["node_id"], log)
        result["log"] = log
        return result
    if op == "move_node":
        move_node(model, args["node_id"], args.get("direction", "down"), log)
        return {"log": log}
    if op == "insert_section":
        section = insert_section(
            model,
            title=args.get("title", "新开发路线"),
            level=args.get("level", 2),
            parent_id=args.get("parent_id"),
            after_section_id=args.get("after_section_id"),
            start_number=args.get("start_number", 1),
            log=log,
        )
        return {"section_id": section.id, "log": log}
    if op == "update_section":
        section = update_section(model, args["section_id"], args, log)
        return {"section_id": section.id, "log": log}
    if op == "delete_section":
        result = delete_section(model, args["section_id"], log)
        result["log"] = log
        return result
    if op == "move_section":
        move_section(model, args["section_id"], args.get("direction", "down"), log)
        return {"log": log}
    if op == "replace":
        new_model = model_from_dict(args["model"])
        model.title = new_model.title
        model.source = new_model.source
        model.preamble = new_model.preamble
        model.sections = new_model.sections
        model.nodes = new_model.nodes
        model.aliases = new_model.aliases
        model.meta = new_model.meta
        resolve_refs(model)
        _log(log, "已恢复到历史版本")
        return {"log": log}
    raise ValueError(f"未知操作：{op}")


# --------------------------------------------------------------------------
# CLI（便于单独验证解析结果）
# --------------------------------------------------------------------------


def _main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("用法：python model.py <任务书.md> [--json 输出路径] [--markdown 输出路径]")
        return 2
    src = Path(argv[1])
    text = src.read_text(encoding="utf-8")
    model = parse_markdown(text, source=str(src))
    view = serialize(model)
    if "--json" in argv:
        out = Path(argv[argv.index("--json") + 1])
        out.write_text(json.dumps(view, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写出 {out}")
    if "--markdown" in argv:
        out = Path(argv[argv.index("--markdown") + 1])
        out.write_text(to_markdown(model), encoding="utf-8")
        print(f"已写出 {out}")
    print(json.dumps(view["stats"], ensure_ascii=False))
    for node in view["nodes"]:
        refs = "、".join(f"{r['raw']}{'' if r['resolved'] else '(未解析)'}" for r in node["refs"]) or "-"
        objs = "、".join(o["name"] for o in node["objects"]) or "-"
        print(f"[{node['index_label']}] {node['summary']} | 依赖: {refs} | 对象: {objs}")
    for issue in view["issues"]:
        print(f"  {issue['level']}: {issue['text']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
