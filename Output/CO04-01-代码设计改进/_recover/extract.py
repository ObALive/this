#!/usr/bin/env python3
"""CO04-01 事故恢复：从会话转录中抽取 write/edit 工具的完整文件内容。"""
import json, os, sys, glob

REC = "/home/typhoeus/this/Output/CO04-01-代码设计改进/_recover"
OUT = os.path.join(REC, "files")
os.makedirs(OUT, exist_ok=True)


def walk(o, path=""):
    """递归遍历任意 JSON 结构，产出 (键路径, 值)。"""
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, path + "/" + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, path + "/" + str(i))
    else:
        yield path, o


def main():
    stats = {}
    for p in sorted(glob.glob(os.path.join(REC, "*.jsonl"))):
        tag = os.path.basename(p)[:-6]
        n_write = n_edit = 0
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                # 收集本行中所有含 file_path 的字典
                for kp, v in walk(d):
                    if kp.endswith("/file_path") and isinstance(v, str):
                        # 找同级的 content / old_string / new_string
                        base = kp[: -len("/file_path")]
                        d2 = d
                        cur = d2
                        ok = True
                        for part in [x for x in base.split("/") if x]:
                            try:
                                cur = cur[int(part)] if isinstance(cur, list) else cur[part]
                            except Exception:
                                ok = False
                                break
                        if not ok or not isinstance(cur, dict):
                            continue
                        content = cur.get("content")
                        if isinstance(content, str) and content:
                            rel = v.replace("/home/typhoeus/this/", "")
                            dest = os.path.join(OUT, rel)
                            os.makedirs(os.path.dirname(dest), exist_ok=True)
                            with open(dest, "w", encoding="utf-8") as w:
                                w.write(content)
                            n_write += 1
                            stats.setdefault(tag, {}).setdefault(rel, []).append(
                                ("write", len(content))
                            )
                        if cur.get("old_string") is not None and cur.get("new_string") is not None:
                            n_edit += 1
        print(f"{tag}: write 载荷 {n_write} 次，edit 载荷 {n_edit} 次")
    print("\n== 抽取出的文件 ==")
    for tag, files in stats.items():
        print(f"--- {tag}")
        for rel, ops in sorted(files.items()):
            print(f"    {rel}  ({', '.join(str(o[1]) for o in ops)} 字符)")


if __name__ == "__main__":
    main()
