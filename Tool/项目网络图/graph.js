/* 项目网络图布局：纯函数，不依赖 DOM，可单独用 node 测试。
 * 约定：一条开发路线（章节）一列，节点按依赖关系自上而下排布；
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
    edgePortOffset: 8, // 侧边指入点上移、指出点下移，分开两类连接
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

    // 先建立父子关系：纯分组用的路线（自己没有条目、但有子路线）不单独占一列，
    // 它的标题由顶部带承担；空的叶子路线要占一列，好让人看到它建在了哪里。
    const childrenOf = new Map();
    for (const s of sections) {
      const key = s.parent_id || null;
      if (!childrenOf.has(key)) childrenOf.set(key, []);
      childrenOf.get(key).push(s);
    }

    let colIndex = 0;
    for (const section of sections) {
      const ids = (section.node_ids || []).filter((id) => byId.has(id));
      if (!ids.length && (childrenOf.get(section.id) || []).length) continue;
      const x = opt.padX + colIndex * (opt.colWidth + opt.colGap);
      const column = {
        sectionId: section.id,
        title: section.title,
        path: section.path || section.title,
        level: section.level || 1,
        x,
        index: colIndex,
        nodeIds: ids,
        color: routeColor(section.id, sections),
      };
      columns.push(column);

      // 先确定列、文字与节点尺寸，再统一按依赖安排纵坐标。
      const textUnits = (opt.colWidth - opt.summaryPadX) / opt.summaryFontPx;
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
          y: opt.padTop,
          w: opt.colWidth,
          h,
          baseX: x,
          baseY: opt.padTop,
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
      });
      colIndex += 1;
    }

    const constraints = arrangeByDependencies(positions, columns, model.edges || [], byId, opt);

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

    // 列头：只有自己带条目、或没有子路线的叶子路线才画列头；
    // 纯分组用的父路线（例如「角色行为」）由顶部带承担标题，不重复画。
    const heads = [];
    for (const col of columns) {
      const hasChildren = (childrenOf.get(col.sectionId) || []).length > 0;
      if (!col.nodeIds.length && hasChildren) continue;
      heads.push({
        sectionId: col.sectionId,
        title: col.title,
        path: col.path,
        level: col.level,
        x: col.x,
        width: opt.colWidth,
        empty: col.nodeIds.length === 0,
        color: col.color,
        y: opt.padTop - 22,
        chars: Math.max(4, Math.floor((opt.colWidth - 4) / 12)),
      });
    }

    return { positions, columns, bands, heads, edges, constraints, width, height, options: opt };
  }

  function arrangeByDependencies(positions, columns, edges, byId, opt) {
    const incoming = new Map([...positions.keys()].map((id) => [id, new Map()]));
    const constraints = [];
    const add = (from, to) => {
      if (!positions.has(from) || !positions.has(to) || incoming.get(to).has(from)) return;
      const constraint = { from, to, cyclic: false };
      incoming.get(to).set(from, constraint);
      constraints.push(constraint);
    };
    // 即使调用方未提供 chain 边，同列条目也保持顺序且不重叠。
    for (const column of columns) {
      for (let i = 1; i < column.nodeIds.length; i += 1) add(column.nodeIds[i - 1], column.nodeIds[i]);
    }
    for (const edge of edges) add(edge.from, edge.to);

    // 显式栈先处理前置节点，避免长路线递归溢出。
    // 成环时忽略返回当前访问路径的边，保留可绘制布局；环由模型校验报告。
    const visits = new Map();
    const order = [];
    for (const id of positions.keys()) {
      if (visits.has(id)) continue;
      visits.set(id, 1);
      const stack = [{ id, dependencies: [...incoming.get(id).values()], next: 0 }];
      while (stack.length) {
        const frame = stack[stack.length - 1];
        if (frame.next < frame.dependencies.length) {
          const constraint = frame.dependencies[frame.next++];
          const visit = visits.get(constraint.from);
          if (visit === 1) {
            constraint.cyclic = true;
          } else if (!visit) {
            visits.set(constraint.from, 1);
            stack.push({ id: constraint.from, dependencies: [...incoming.get(constraint.from).values()], next: 0 });
          }
        } else {
          visits.set(frame.id, 2);
          order.push(frame.id);
          stack.pop();
        }
      }
    }
    for (const id of order) {
      const position = positions.get(id);
      let minimumY = opt.padTop;
      for (const constraint of incoming.get(id).values()) {
        if (constraint.cyclic) continue;
        const dependency = positions.get(constraint.from);
        minimumY = Math.max(minimumY, dependency.y + dependency.h + opt.gapY);
      }
      position.baseY = minimumY;
      const dy = (byId.get(id).manual || {}).dy || 0;
      position.y = Math.max(minimumY, minimumY + dy);
    }
    for (const column of columns) {
      column.bottom = opt.padTop;
      for (const id of column.nodeIds) {
        const position = positions.get(id);
        column.bottom = Math.max(column.bottom, position.y + position.h);
      }
    }
    return constraints;
  }

  // 拖动只在现有前置与后续节点之间微调，始终保持依赖顺序。
  function constrainNodeY(layout, nodeId, requestedY) {
    const position = layout.positions.get(nodeId);
    if (!position) return requestedY;
    let minimumY = layout.options.padTop;
    let maximumY = Infinity;
    for (const constraint of layout.constraints) {
      if (constraint.cyclic) continue;
      if (constraint.to === nodeId) {
        const dependency = layout.positions.get(constraint.from);
        minimumY = Math.max(minimumY, dependency.y + dependency.h + layout.options.gapY);
      }
      if (constraint.from === nodeId) {
        const dependent = layout.positions.get(constraint.to);
        maximumY = Math.min(maximumY, dependent.y - position.h - layout.options.gapY);
      }
    }
    return Math.max(minimumY, Math.min(maximumY, requestedY));
  }

  function edgePath(a, b, opt) {
    const aCx = a.x + a.w / 2;
    const bCx = b.x + b.w / 2;
    const portOffset = opt.edgePortOffset ?? LAYOUT.edgePortOffset;
    const aOutY = a.y + a.h / 2 + Math.min(portOffset, a.h / 4);
    const bInY = b.y + b.h / 2 - Math.min(portOffset, b.h / 4);

    if (a.column === b.column) {
      if (Math.abs(a.row - b.row) === 1) {
        // 相邻条目：直线向下
        return `M ${aCx} ${a.y + a.h} L ${bCx} ${b.y}`;
      }
      // 同列跨行：从右侧绕行
      const bx = Math.max(a.x + a.w, b.x + b.w) + opt.sameColBulge;
      return `M ${a.x + a.w} ${aOutY} C ${bx} ${aOutY} ${bx} ${bInY} ${b.x + b.w} ${bInY}`;
    }

    const dir = b.column > a.column ? 1 : -1;
    const startX = dir > 0 ? a.x + a.w : a.x;
    const endX = dir > 0 ? b.x : b.x + b.w;
    const span = Math.max(40, Math.abs(endX - startX) * 0.45);
    return `M ${startX} ${aOutY} C ${startX + dir * span} ${aOutY} ${endX - dir * span} ${bInY} ${endX} ${bInY}`;
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

  global.PNLayout = { computeLayout, constrainNodeY, edgePath, arrowPath, wrapSummary, truncateText, nodeHeightFor, routeColor, LAYOUT };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = global.PNLayout;
  }
})(typeof window !== "undefined" ? window : globalThis);
