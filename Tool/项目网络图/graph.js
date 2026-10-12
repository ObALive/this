/* 项目网络图布局：纯函数，不依赖 DOM，可单独用 node 测试。
 * 约定：一条开发路线（章节）一列，条目自上而下顺排；
 * 同路线内相邻条目依次向上依赖（chain 边），跨路线依赖走曲线（explicit 边）。 */
(function (global) {
  const LAYOUT = {
    colWidth: 176,
    gapY: 78,
    colGap: 92,
    padX: 56,
    padTop: 104,
    padBottom: 72,
    bandHeight: 34,
    sameColBulge: 46,
    // 节点高度由概要行数决定：索引行 + 若干概要行 + 下留白，且不低于 minHeight
    minHeight: 52,
    firstLineBase: 39,
    lineStep: 17,
    bottomPad: 9,
    maxSummaryLines: 4,
    summaryFontPx: 13,
    summaryPadX: 30,
    indexFontPx: 10.5,
    indexPadX: 26,
  };

  const ROUTE_COLORS = [
    "#3f7dd8",
    "#2f9e72",
    "#c2703a",
    "#8a63c9",
    "#b8455f",
    "#4a8fa8",
    "#9a8a2f",
    "#6b7280",
  ];

  function routeColor(sectionId, sectionList) {
    // 按根路线分配颜色，二级路线与父级同色系
    let sec = sectionList.find((s) => s.id === sectionId);
    const guard = new Set();
    while (sec && sec.parent_id && !guard.has(sec.id)) {
      guard.add(sec.id);
      sec = sectionList.find((s) => s.id === sec.parent_id);
    }
    const roots = [];
    const seen = new Set();
    for (const s of sectionList) {
      let root = s;
      const g = new Set();
      while (root && root.parent_id && !g.has(root.id)) {
        g.add(root.id);
        root = sectionList.find((x) => x.id === root.parent_id);
      }
      const key = root ? root.id : s.id;
      if (!seen.has(key)) {
        seen.add(key);
        roots.push(key);
      }
    }
    const idx = Math.max(0, roots.indexOf(sec ? sec.id : sectionId));
    return ROUTE_COLORS[idx % ROUTE_COLORS.length];
  }

  function computeLayout(model, options) {
    const opt = Object.assign({}, LAYOUT, options || {});
    const sections = model.sections || [];
    const nodes = model.nodes || [];
    const byId = new Map(nodes.map((n) => [n.id, n]));

    const positions = new Map();
    const columns = [];

    let colIndex = 0;
    for (const section of sections) {
      const ids = (section.node_ids || []).filter((id) => byId.has(id));
      const x = opt.padX + colIndex * (opt.colWidth + opt.colGap);
      const column = { sectionId: section.id, title: section.title, x, index: colIndex, nodeIds: ids };
      columns.push(column);

      // 概要按节点宽度折行，行数决定节点高度；节点自上而下按「前一个高度 + 间距」累积
      const textUnits = (opt.colWidth - opt.summaryPadX) / opt.summaryFontPx;
      let cursorY = opt.padTop;
      ids.forEach((id, i) => {
        const node = byId.get(id);
        const manual = (node && node.manual) || {};
        const summary = node ? node.summary : "";
        const lines = wrapSummary(summary, textUnits, opt.maxSummaryLines);
        const h = nodeHeightFor(lines.length, opt);
        positions.set(id, {
          id,
          sectionId: section.id,
          column: colIndex,
          row: i,
          x: x + (manual.dx || 0),
          y: cursorY + (manual.dy || 0),
          w: opt.colWidth,
          h,
          baseX: x,
          baseY: cursorY,
          lines,
          maxLines: opt.maxSummaryLines,
          firstLineBase: opt.firstLineBase,
          lineStep: opt.lineStep,
          indexChars: (opt.colWidth - opt.indexPadX) / opt.indexFontPx,
          color: routeColor(section.id, sections),
          index_label: node ? node.index_label : "",
          summary,
          has_error: !!(node && (node.refs || []).some((r) => !r.resolved)),
        });
        cursorY += h + opt.gapY;
      });
      column.bottom = Math.max(opt.padTop, cursorY - opt.gapY);
      colIndex += 1;
    }

    // 顶部路线分组带：按根章节把子列圈起来
    const bands = [];
    const rootsInOrder = [];
    const rootOf = new Map();
    for (const section of sections) {
      let root = section;
      const g = new Set();
      while (root && root.parent_id && !g.has(root.id)) {
        g.add(root.id);
        const parent = sections.find((x) => x.id === root.parent_id);
        if (!parent) break;
        root = parent;
      }
      rootOf.set(section.id, root ? root.id : section.id);
      if (!rootsInOrder.includes(rootOf.get(section.id))) rootsInOrder.push(rootOf.get(section.id));
    }
    for (const rootId of rootsInOrder) {
      const cols = columns.filter((c) => rootOf.get(c.sectionId) === rootId);
      if (!cols.length) continue;
      const rootTitle = (sections.find((s) => s.id === rootId) || {}).title || "";
      const left = Math.min(...cols.map((c) => c.x)) - 16;
      const right = Math.max(...cols.map((c) => c.x)) + opt.colWidth + 16;
      bands.push({ id: rootId, title: rootTitle, x: left, y: 40, w: right - left, h: opt.bandHeight, color: routeColor(cols[0].sectionId, sections) });
    }

    // 边
    const edges = [];
    const seen = new Set();
    for (const e of model.edges || []) {
      const key = e.from + "->" + e.to;
      if (seen.has(key)) continue;
      seen.add(key);
      const a = positions.get(e.from);
      const b = positions.get(e.to);
      if (!a || !b) continue;
      edges.push(Object.assign({}, e, { d: edgePath(a, b, opt), aId: e.from, bId: e.to }));
    }

    let width = opt.padX * 2 + Math.max(1, columns.length) * opt.colWidth + Math.max(0, columns.length - 1) * opt.colGap;
    let height = opt.padTop;
    for (const col of columns) {
      height = Math.max(height, (col.bottom || opt.padTop) + opt.padBottom);
    }
    if (!columns.length) height = 220;
    if (!columns.length) width = 520;

    return { positions, columns, bands, edges, width, height, options: opt };
  }

  function edgePath(a, b, opt) {
    const aCx = a.x + a.w / 2;
    const bCx = b.x + b.w / 2;
    const aCy = a.y + a.h / 2;
    const bCy = b.y + b.h / 2;

    if (a.column === b.column) {
      if (Math.abs(a.row - b.row) === 1) {
        // 相邻条目：直线向下
        return `M ${aCx} ${a.y + a.h} L ${bCx} ${b.y}`;
      }
      // 同列跨行：从右侧绕行
      const bx = Math.max(a.x + a.w, b.x + b.w) + opt.sameColBulge;
      return `M ${a.x + a.w} ${aCy} C ${bx} ${aCy} ${bx} ${bCy} ${b.x + b.w} ${bCy}`;
    }

    const dir = b.column > a.column ? 1 : -1;
    const startX = dir > 0 ? a.x + a.w : a.x;
    const endX = dir > 0 ? b.x : b.x + b.w;
    const span = Math.max(40, Math.abs(endX - startX) * 0.45);
    return `M ${startX} ${aCy} C ${startX + dir * span} ${aCy} ${endX - dir * span} ${bCy} ${endX} ${bCy}`;
  }

  function arrowPath(x, y, angle, size) {
    const s = size || 7;
    const a1 = angle + Math.PI * 0.82;
    const a2 = angle - Math.PI * 0.82;
    return `M ${x} ${y} L ${x + s * Math.cos(a1)} ${y + s * Math.sin(a1)} L ${x + s * Math.cos(a2)} ${y + s * Math.sin(a2)} Z`;
  }

  function wrapSummary(text, maxWidth, maxLines) {
    const source = (text || "").trim();
    if (!source) return [];
    const widthOf = (ch) => (/[\x00-\xff]/.test(ch) ? 0.56 : 1);
    const lines = [];
    let line = "";
    let w = 0;
    let truncated = false;
    for (const ch of source) {
      const cw = widthOf(ch);
      if (w + cw > maxWidth && line) {
        lines.push(line);
        line = "";
        w = 0;
        if (lines.length === (maxLines || 2)) {
          truncated = true;
          break;
        }
      }
      line += ch;
      w += cw;
    }
    if (!truncated && line) lines.push(line);
    if (truncated && lines.length) {
      let last = lines[lines.length - 1];
      if (last.length > 1) last = last.slice(0, -1) + "…";
      lines[lines.length - 1] = last;
    }
    return lines;
  }

  // 节点高度随概要行数变化：索引行固定占高，概要每多一行加一个行距
  function nodeHeightFor(lineCount, options) {
    const opt = Object.assign({}, LAYOUT, options || {});
    const lines = Math.max(1, lineCount || 0);
    const content = opt.firstLineBase + (lines - 1) * opt.lineStep + opt.bottomPad;
    return Math.max(opt.minHeight, content);
  }

  // 单行文本超宽时截断并加省略号，宽度按「非 ASCII 记 1 个单位」估算
  function truncateText(text, maxWidth) {
    const source = (text || "").trim();
    if (!source || !(maxWidth > 0)) return source;
    const widthOf = (ch) => (/[\x00-\xff]/.test(ch) ? 0.56 : 1);
    let w = 0;
    let out = "";
    for (const ch of source) {
      const cw = widthOf(ch);
      if (w + cw > maxWidth - 1) return out + "…";
      out += ch;
      w += cw;
    }
    return out;
  }

  global.PNLayout = { computeLayout, edgePath, arrowPath, wrapSummary, truncateText, nodeHeightFor, routeColor, LAYOUT };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = global.PNLayout;
  }
})(typeof window !== "undefined" ? window : globalThis);
