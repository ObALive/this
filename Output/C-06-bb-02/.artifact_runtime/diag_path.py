# -*- coding: utf-8 -*-
"""诊断：定位 Python 无法打开该文件的真实原因。"""
import os
import unicodedata

BASE = r"D:\myspace\Git\mygame\Dsh\Design"
REL = "05-运营与经济/05_物品系统/05_物品系统设计_v1.md"

full = os.path.join(BASE, *[p for p in REL.split("/") if p])
print("构造路径:", repr(full))
print("exists:", os.path.exists(full), "isfile:", os.path.isfile(full))

# 逐级检查
cur = BASE
for part in [p for p in REL.split("/") if p]:
    nxt = os.path.join(cur, part)
    print("  级:", repr(part), "->", os.path.exists(nxt))
    if not os.path.exists(nxt) and os.path.isdir(cur):
        listing = os.listdir(cur)
        print("     目录内实际条目:")
        for item in listing:
            same = (item == part)
            print("       %r  equal=%s  NFC=%s" % (
                item, same, unicodedata.is_normalized("NFC", item)))
    cur = nxt

# 用目录扫描直接定位
target_dir = os.path.join(BASE, "05-运营与经济", "05_物品系统")
for name in os.listdir(target_dir):
    if name.endswith(".md"):
        p = os.path.join(target_dir, name)
        print("扫描得到:", repr(name), "可读:", os.path.isfile(p),
              "长度:", len(name), "构造长度:", len("05_物品系统设计_v1.md"))
        print("  逐字符比较:",
              [i for i, (a, b) in enumerate(zip(name, "05_物品系统设计_v1.md")) if a != b])
