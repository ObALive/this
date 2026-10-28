# -*- coding: utf-8 -*-
"""CO06 工程更新 7362b95 静态验收：核对文档覆盖、链接、基线与只读边界。"""
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = r"D:/myspace/Git/this"
GAME = r"D:/myspace/Git/mygame"
OUT = os.path.join(ROOT, "Output", "CO06-工程更新7362b95")
DOCS = os.path.join(ROOT, "代码说明文档")
BASE = os.path.join(OUT, "CO06-工程更新7362b95_基线_v1.json")

results = []


def check(cid, desc, passed, detail=""):
    results.append({"id": cid, "desc": desc, "pass": bool(passed), "detail": detail})
    print(("PASS " if passed else "FAIL ") + cid + " " + desc + ((" | " + str(detail)) if detail else ""))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_digest(path):
    entries = []
    for base, dirs, files in os.walk(path):
        dirs[:] = sorted(d for d in dirs if d not in ("__pycache__", "Library", "Temp", "obj"))
        for f in sorted(files):
            fp = os.path.join(base, f)
            entries.append([os.path.relpath(fp, path).replace("\\", "/"), sha256(fp)])
    return {"kind": "dir", "file_count": len(entries),
            "sha256": hashlib.sha256(json.dumps(entries).encode("utf-8")).hexdigest()}


def main():
    baseline = json.load(open(BASE, encoding="utf-8"))
    docs = {}
    for name in sorted(os.listdir(DOCS)):
        if name.endswith(".md"):
            with open(os.path.join(DOCS, name), encoding="utf-8") as f:
                docs[name] = f.read()
    all_text = "\n".join(docs.values())

    # A1 文档齐全
    expected = ["README.md",
                "00_程序集与类型关系总览代码设计案.md",
                "10_MetaObject类型与组件底座代码设计案.md",
                "20_对象组件与场景承载类型代码设计案.md",
                "30_MetaAction派生类型与动作组件代码设计案.md",
                "40_MetaActionLifecycle统一执行入口代码设计案.md",
                "50_TimeLineManager与战斗装配类型代码设计案.md",
                "60_地图与移动适配类型代码设计案.md",
                "70_UnitDetailsPanel与移动选择界面代码设计案.md",
                "75_量表组件与生命显示代码设计案.md",
                "80_基础技能槽与待机动作代码设计案.md"]
    missing = [n for n in expected if n not in docs]
    extra = [n for n in docs if n not in expected]
    check("A1", "文档库正文与索引齐全", not missing and not extra, {"missing": missing, "extra": extra})

    # A2 元数据
    keys = ["| 解释范围 |", "| 源码依据 |", "| 核对基线 |", "| 关联设计 |", "| 状态 |", "| 更新日期 |"]
    bad = {}
    for n in expected:
        if n == "README.md":
            continue
        lack = [k.strip("| ") for k in keys if k not in docs[n]]
        if lack:
            bad[n] = lack
    check("A2", "各专题具备规范元数据表字段", not bad, bad)

    # A3 基线一致
    bad = {}
    for n in expected:
        body = docs[n]
        if "7362b95addd908be4f96110c2c51ad0300af8e58" not in body:
            bad.setdefault(n, []).append("missing commit")
        if "2026-10-27" not in body:
            bad.setdefault(n, []).append("missing date")
    check("A3", "全部文档登记当前提交与核对日期", not bad, bad)

    # A4 链接
    link_re = re.compile(r"\]\((?:<([^>]+)>|([^)\s]+))\)")
    broken = []
    total = 0
    for n, body in docs.items():
        for m in link_re.finditer(body):
            target = (m.group(1) or m.group(2)).strip()
            if target.startswith("#") or target.startswith("http"):
                continue
            total += 1
            if target.startswith("D:/"):
                path = target
            else:
                path = os.path.normpath(os.path.join(DOCS, target))
            if not os.path.exists(path):
                broken.append({"doc": n, "target": target})
    check("A4", "文档内链接与源码路径可解析", not broken, {"checked": total, "broken": broken})

    # A5 类型覆盖
    types = []
    for s in baseline["sources"]:
        for t in s["declared_types"]:
            types.append(t["type"])
    absent = [t for t in types if not re.search(r"\b" + re.escape(t) + r"\b", all_text)]
    check("A5", "全部范围内声明类型在正文出现", not absent, {"types": len(types), "absent": absent})

    # A6 已实现功能在索引与覆盖记录中登记
    summaries = [n["summary"] for n in baseline["implemented_nodes"]]
    readme = docs["README.md"]
    cover = open(os.path.join(OUT, "CO06-工程更新7362b95_覆盖记录_v1.md"), encoding="utf-8").read()
    miss_readme = [s for s in summaries if re.sub(r"\s+", "", s) not in re.sub(r"\s+", "", readme)]
    miss_cover = [s for s in summaries if re.sub(r"\s+", "", s) not in re.sub(r"\s+", "", cover)]
    check("A6", "九项已实现功能均登记于索引与覆盖记录",
          not miss_readme and not miss_cover, {"readme": miss_readme, "coverage": miss_cover})

    # A7 文档库不含过程引用
    forbidden = {"sqlite": re.compile(r"sqlite", re.I),
                 "N01_": re.compile(r"N01_"),
                 "网络图": re.compile("网络图"),
                 "节点标识": re.compile(r"\bn\d+\b")}
    hits = {}
    for label, rx in forbidden.items():
        found = [n for n, b in docs.items() if rx.search(b)]
        if found:
            hits[label] = found
    check("A7", "正文不含库路径、图名与节点标识", not hits, hits)

    # A8 计数一致
    count_ok = ("31 份脚本" in docs["00_程序集与类型关系总览代码设计案.md"] and
                "67 个" in docs["00_程序集与类型关系总览代码设计案.md"] and
                "31 份脚本" in readme and "67 个" in readme)
    actual = (len(baseline["sources"]), baseline["type_count"])
    check("A8", "文档声明与基线的脚本/类型计数一致",
          count_ok and actual == (31, 67), {"declared_ok": count_ok, "actual": actual})

    # A9 排版
    whitespace = {}
    for n, body in docs.items():
        lines = body.split("\n")
        trail = [i + 1 for i, line in enumerate(lines) if line != line.rstrip()]
        if trail:
            whitespace[n] = {"trailing": trail[:10], "count": len(trail)}
        if not body.endswith("\n") or body.endswith("\n\n"):
            whitespace.setdefault(n, {})["final_newline"] = "bad"
        if "\t" in body:
            whitespace.setdefault(n, {})["tab"] = True
    check("A9", "文档无行尾空白、制表符与结尾换行异常", not whitespace, whitespace)

    # A10 只读资料身份
    changed = {}
    for rel, recorded in baseline["protected"].items():
        if rel.startswith("<SOURCE>"):
            path = GAME + rel.replace("<SOURCE>", "")
        else:
            path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            changed[rel] = "missing"
            continue
        now = tree_digest(path) if os.path.isdir(path) else {"sha256": sha256(path)}
        if now["sha256"] != recorded["sha256"]:
            changed[rel] = {"before": recorded["sha256"][:12], "now": now["sha256"][:12]}
    check("A10", "工程、网络图、规范、旧库与设计库未被改写", not changed, changed)

    # A11 源码与资产身份
    changed = {}
    for s in baseline["sources"]:
        if sha256(os.path.join(GAME, s["path"])) != s["sha256"]:
            changed[s["path"]] = "source changed"
    for rel, meta in baseline["assets"].items():
        if sha256(os.path.join(GAME, rel)) != meta["sha256"]:
            changed[rel] = "asset changed"
    check("A11", "核对基线的源码与资产散列未变", not changed, changed)

    # A12 UI 绑定与正文一致
    body70 = docs["70_UnitDetailsPanel与移动选择界面代码设计案.md"]
    missing_bind = []
    for key, entry in baseline["ui_bindings"].items():
        if entry.get("exists") and entry["fileID"] not in body70:
            missing_bind.append(key)
    fonts = {f for e in baseline["ui_bindings"].values() for f in e.get("fonts", [])}
    font_ok = all(f in body70 for f in fonts)
    calls_ok = all(e.get("persistentCallsEmpty", True) for e in baseline["ui_bindings"].values()
                   if e.get("hasOnClick"))
    check("A12", "UI 字段、字体与空持久化回调描述可追溯",
          not missing_bind and font_ok and calls_ok,
          {"missing": missing_bind, "fonts": sorted(fonts), "font_in_doc": font_ok, "empty_calls": calls_ok})

    # A13 关键行为符号覆盖
    tokens = ["ActionTargetKind", "WaitEffectComponent", "MetaObjectMeterComponent",
              "BasicSkillSlotsComponent", "SkillSelectionController", "RefreshHealth",
              "HP -", "Prepare"]
    absent = [t for t in tokens if t not in all_text]
    check("A13", "新增实现的关键符号进入说明", not absent, absent)

    # A14 覆盖结论显式区分
    partial = ["共享时间轴调度与行动回排", "待机动作", "固定属性", "动态属性血量"]
    cover_ok = "部分实现" in cover and all(s in cover for s in partial)
    check("A14", "部分实现的功能有显式结论", cover_ok, {"partial": partial})

    # A15 git diff --check（已跟踪文档）
    p = subprocess.run(["git", "diff", "--check", "--", "代码说明文档"], cwd=ROOT, capture_output=True)
    msg = (p.stdout + p.stderr).decode("utf-8", "replace").strip()
    check("A15", "已跟踪文档无空白错误", p.returncode == 0, msg[:500])

    summary = {"total": len(results), "passed": sum(1 for r in results if r["pass"]),
               "failed": [r["id"] for r in results if not r["pass"]]}
    payload = {"date": "2026-10-27", "documents": expected, "summary": summary, "checks": results}
    with open(os.path.join(OUT, "CO06-工程更新7362b95_验收结果_v1.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    print("SUMMARY", summary)
    return 0 if not summary["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
