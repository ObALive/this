#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把各文档的缺口条目装配成《CO01 上层设计补充需求申报 v1》。"""
import os, re, sys
from collections import defaultdict

ROOT = "/home/ob-alive/策划书"
OUT = os.path.join(ROOT, "Output/CO01-初步构建代码设计文档/CO01_上层设计补充需求申报_v1.md")
HEAD = os.path.join(ROOT, "Output/CO01-初步构建代码设计文档/req_head.md")
FIELDS = ["编号", "提出单元", "缺口内容", "影响", "为何不能自行决定", "建议承接方", "建议补充产出", "优先级"]
FIELD_RE = re.compile(r"^\s*[-*\s]*(" + "|".join(FIELDS) + r")\s*[:：]\s*(.*)$")

def docs():
    base = os.path.join(ROOT, "Code_Design")
    for dp, _d, fs in os.walk(base):
        for n in sorted(fs):
            if n.endswith(".md") and n != "README.md":
                yield os.path.join(dp, n)

def parse(path):
    recs, cur = [], None
    for line in open(path, encoding="utf-8"):
        m = FIELD_RE.match(line.rstrip())
        if not m:
            continue
        k, v = m.group(1), m.group(2).strip()
        if k == "编号":
            if cur: recs.append(cur)
            cur = {f: "" for f in FIELDS}; cur["编号"] = v
            cur["_file"] = os.path.relpath(path, ROOT)
        elif cur is not None:
            cur[k] = v
    if cur: recs.append(cur)
    return recs

recs = []
for p in docs():
    recs.extend(parse(p))

def group(r):
    o = r.get("建议承接方", "")
    if "架构" in o and "系统设计" not in o: return "架构设计案"
    if "系统设计" in o: return "系统设计文档"
    return "待判定承接方"

groups = defaultdict(list)
for r in recs:
    groups[group(r)].append(r)

def prio_key(r):
    p = r.get("优先级", "")
    return (0 if p.startswith("高") else 1 if p.startswith("中") else 2, r.get("编号", ""))

out = [open(HEAD, encoding="utf-8").read().rstrip(), "", "---", ""]
out.append("## 二、条目汇总")
out.append("")
out.append("本轮共回收缺口条目 **%d** 条，涉及 **%d** 份代码设计案。" % (len(recs), len({r["_file"] for r in recs})))
out.append("")
for key in ["系统设计文档", "架构设计案", "待判定承接方"]:
    rows = sorted(groups.get(key, []), key=prio_key)
    if not rows:
        continue
    n_high = sum(1 for r in rows if r.get("优先级", "").startswith("高"))
    out.append("### %s（%d 条，其中高优先级 %d 条）" % (key, len(rows), n_high))
    out.append("")
    for r in rows:
        out.append("**%s ｜ %s**" % (r.get("编号", ""), r.get("提出单元", "") or r["_file"]))
        out.append("")
        out.append("- 缺口内容：%s" % r.get("缺口内容", ""))
        out.append("- 影响：%s" % r.get("影响", ""))
        out.append("- 为何不能自行决定：%s" % (r.get("为何不能自行决定", "") or "依 NR-06 §三.2 第 3 项与架构案相关条文，代码设计层不得改写游戏规则或自行裁定未登记的结构"))
        out.append("- 建议承接方：%s" % r.get("建议承接方", ""))
        out.append("- 建议补充产出：%s" % r.get("建议补充产出", ""))
        out.append("- 优先级：%s" % r.get("优先级", ""))
        out.append("")
    out.append("")

# 未结构化但正文标注了「待上游补充」的文档
loose = []
for p in docs():
    t = open(p, encoding="utf-8").read()
    n = len(re.findall(r"待上游补充", t))
    if n:
        loose.append((os.path.relpath(p, ROOT), n))
out.append("### 附：正文标注「待上游补充」但未展开为条目的位置")
out.append("")
out.append("下列位置在正文中以「待上游补充」标注，其内容已并入上表对应条目或属同一缺口的落点说明，供承接方定位。")
out.append("")
out.append("| 文档 | 处数 |")
out.append("| --- | --- |")
for rel, n in sorted(loose):
    out.append("| `%s` | %d |" % (rel, n))
out.append("")
out.append("---")
out.append("")
out.append("## 三、闭合登记")
out.append("")
out.append("本轮无已闭合条目。承接方补齐上游设计后，在此逐条登记编号、补齐日期与回填的代码设计案。")
out.append("")

open(OUT, "w", encoding="utf-8").write("\n".join(out))
print("需求申报已写入 %s（%d 条）" % (OUT, len(recs)))
