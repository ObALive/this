from pathlib import Path
import re
ROOT=Path(r"D:\myspace\Git\this\代码说明文档")
PROJECT="D:/myspace/Git/mygame/"
BASELINE="65c2ff5e40cec060988b74091e189e09fdaa9e13"
def doc(name,title,intro,scope,entry,body,sources,related=None):
    path=ROOT/name
    if related is None and path.exists():
        match=re.search(r"^\| 关联设计 \| (.*?) \|$",path.read_text(encoding="utf-8-sig"),re.M)
        related=match.group(1) if match else None
    related=related or "[架构设计案](../架构设计文档/架构设计案.md)；业务背景与职责约束以设计文档为准，实现行为以本文源码依据为准"
    text=f"# {title}\n\n{intro.strip()}\n\n| 项目 | 内容 |\n| --- | --- |\n| 解释范围 | Assembly-CSharp，全局命名空间；{scope} |\n| 源码依据 | {entry}；文件入口见文末实现定位 |\n| 核对基线 | 工程提交 `{BASELINE}`；2026-10-29 核对时工程工作区干净 |\n| 关联设计 | {related} |\n| 状态 | 已核对：源码声明、调用链与静态资产绑定 |\n| 更新日期 | 2026-10-29 |\n\n{body.strip()}\n\n## 实现定位\n\n| 源码或资产 | 主要定位 |\n| --- | --- |\n"
    for file,symbol in sources:
        target=PROJECT+file
        if " " in target: target="<"+target+">"
        text+=f"| [{Path(file).name}]({target}) | {symbol} |\n"
    text+="\n核对依据为上述提交的源码、工程配置与静态资产。文档状态表示所述实现已完成对照；编译、播放、画面与交互的运行验证属于独立验证范围。\n"
    path.write_text(text,encoding="utf-8",newline="\n")
    print(name)
