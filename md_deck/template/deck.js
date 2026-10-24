(() => {
  const MIN_SCALE = 0.8;
  const STEP = 0.02;
  const GUTTER = 22;
  const PARALLEL_GAP = 18;
  const LABEL_GAP = 10;
  const HIT_PAD = 4;
  const EPS = 0.75;

  function ensureMarkers(svg) {
    let defs = svg.querySelector("defs");
    if (!defs) {
      defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
      svg.appendChild(defs);
    }
    if (!svg.querySelector("#flow-arrowhead")) {
      const marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
      marker.setAttribute("id", "flow-arrowhead");
      marker.setAttribute("markerWidth", "10");
      marker.setAttribute("markerHeight", "7");
      marker.setAttribute("refX", "9");
      marker.setAttribute("refY", "3.5");
      marker.setAttribute("orient", "auto");
      const poly = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
      poly.setAttribute("points", "0 0, 10 3.5, 0 7");
      poly.setAttribute("fill", "currentColor");
      marker.appendChild(poly);
      defs.appendChild(marker);
    }
  }

  function nodeByKey(flow, key) {
    return flow.querySelector(`.flow-node[data-node="${CSS.escape(key)}"]`);
  }

  function slideScale(flow) {
    const slide = flow.closest(".slide");
    const raw = slide && slide.dataset ? slide.dataset.scale : "1";
    const scale = Number(raw);
    return Number.isFinite(scale) && scale > 0 ? scale : 1;
  }

  function relBox(el, flowBox, scale) {
    const r = el.getBoundingClientRect();
    const s = scale || 1;
    const left = (r.left - flowBox.left) / s;
    const top = (r.top - flowBox.top) / s;
    const width = r.width / s;
    const height = r.height / s;
    return {
      left,
      right: left + width,
      top,
      bottom: top + height,
      width,
      height,
      cx: left + width / 2,
      cy: top + height / 2,
    };
  }

  function unionBox(boxes) {
    if (!boxes.length) return null;
    const left = Math.min(...boxes.map((b) => b.left));
    const right = Math.max(...boxes.map((b) => b.right));
    const top = Math.min(...boxes.map((b) => b.top));
    const bottom = Math.max(...boxes.map((b) => b.bottom));
    return {
      left,
      right,
      top,
      bottom,
      width: right - left,
      height: bottom - top,
      cx: (left + right) / 2,
      cy: (top + bottom) / 2,
    };
  }

  function attachBox(flow, key, attach, flowBox, scale) {
    const el = nodeByKey(flow, key);
    if (!el) return null;
    if (attach === "stack") {
      const stack = el.closest(".flow-stack");
      if (stack) return relBox(stack, flowBox, scale);
    }
    return relBox(el, flowBox, scale);
  }

  function collectObstacles(flow, flowBox, scale, skipKeys) {
    const skip = new Set(skipKeys || []);
    const out = [];
    Array.from(flow.querySelectorAll(".flow-node")).forEach((el) => {
      const key = el.getAttribute("data-node");
      out.push({
        key,
        kind: "node",
        box: relBox(el, flowBox, scale),
        skip: skip.has(key),
      });
    });
    Array.from(flow.querySelectorAll("div.flow-callout")).forEach((el, index) => {
      out.push({
        key: `callout:${index}`,
        kind: "callout",
        box: relBox(el, flowBox, scale),
        skip: false,
      });
    });
    Array.from(flow.querySelectorAll(".flow-node-badge")).forEach((el, index) => {
      out.push({
        key: `badge:${index}`,
        kind: "badge",
        box: relBox(el, flowBox, scale),
        skip: false,
      });
    });
    return out;
  }

  function sidePoint(box, side) {
    switch (side) {
      case "top":
        return { x: box.cx, y: box.top };
      case "bottom":
        return { x: box.cx, y: box.bottom };
      case "left":
        return { x: box.left, y: box.cy };
      case "right":
        return { x: box.right, y: box.cy };
      default:
        return { x: box.cx, y: box.cy };
    }
  }

  function segmentHitsBox(p, q, box, pad) {
    const padBox = {
      left: box.left - pad,
      right: box.right + pad,
      top: box.top - pad,
      bottom: box.bottom + pad,
    };
    const minX = Math.min(p.x, q.x);
    const maxX = Math.max(p.x, q.x);
    const minY = Math.min(p.y, q.y);
    const maxY = Math.max(p.y, q.y);
    if (maxX < padBox.left || minX > padBox.right || maxY < padBox.top || minY > padBox.bottom) {
      return false;
    }
    // Orthogonal segments only.
    if (Math.abs(p.x - q.x) < EPS) {
      return p.x >= padBox.left && p.x <= padBox.right && maxY >= padBox.top && minY <= padBox.bottom;
    }
    if (Math.abs(p.y - q.y) < EPS) {
      return p.y >= padBox.top && p.y <= padBox.bottom && maxX >= padBox.left && minX <= padBox.right;
    }
    return true;
  }

  function pathHitsObstacles(pts, obstacles, pad) {
    let hits = 0;
    for (let i = 1; i < pts.length; i += 1) {
      obstacles.forEach((o) => {
        if (o.skip) return;
        if (segmentHitsBox(pts[i - 1], pts[i], o.box, pad)) hits += 1;
      });
    }
    return hits;
  }

  function segmentsCross(a1, a2, b1, b2) {
    // Proper orthogonal crossing (not shared endpoint / overlap).
    const aVert = Math.abs(a1.x - a2.x) < EPS;
    const bVert = Math.abs(b1.x - b2.x) < EPS;
    if (aVert === bVert) return false;
    const vert = aVert ? [a1, a2] : [b1, b2];
    const horz = aVert ? [b1, b2] : [a1, a2];
    const x = vert[0].x;
    const y = horz[0].y;
    const yLo = Math.min(vert[0].y, vert[1].y) + EPS;
    const yHi = Math.max(vert[0].y, vert[1].y) - EPS;
    const xLo = Math.min(horz[0].x, horz[1].x) + EPS;
    const xHi = Math.max(horz[0].x, horz[1].x) - EPS;
    return x > xLo && x < xHi && y > yLo && y < yHi;
  }

  function nearPoint(p, q, tol) {
    return Math.hypot(p.x - q.x, p.y - q.y) <= tol;
  }

  function pathCrossings(pts, drawn) {
    // Ignore crossings near shared endpoints (fan-in / fan-out stubs).
    const ends = [pts[0], pts[pts.length - 1]];
    let count = 0;
    for (let i = 1; i < pts.length; i += 1) {
      drawn.forEach((other) => {
        const otherEnds = [other[0], other[other.length - 1]];
        const sharedEnds = [];
        ends.forEach((e) => {
          otherEnds.forEach((o) => {
            if (nearPoint(e, o, 10)) sharedEnds.push(e);
          });
        });
        for (let j = 1; j < other.length; j += 1) {
          if (!segmentsCross(pts[i - 1], pts[i], other[j - 1], other[j])) continue;
          const cross =
            Math.abs(pts[i - 1].x - pts[i].x) < EPS
              ? { x: pts[i - 1].x, y: other[j - 1].y }
              : { x: other[j - 1].x, y: pts[i - 1].y };
          const nearShared = sharedEnds.some((e) => nearPoint(cross, e, 48));
          if (!nearShared) count += 1;
        }
      });
    }
    return count;
  }

  function pathLength(pts) {
    let total = 0;
    for (let i = 1; i < pts.length; i += 1) {
      total += Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
    }
    return total;
  }

  function clamp(value, lo, hi) {
    if (hi < lo) return value;
    return Math.max(lo, Math.min(hi, value));
  }

  function obstaclesInBand(obstacles, band) {
    // Only obstacles that intersect the rows / columns a route actually crosses.
    return obstacles.filter((o) => {
      if (o.skip) return false;
      if (band.kind === "y") {
        return o.box.bottom >= band.lo - HIT_PAD && o.box.top <= band.hi + HIT_PAD;
      }
      return o.box.right >= band.lo - HIT_PAD && o.box.left <= band.hi + HIT_PAD;
    });
  }

  function corridorY(obstacles, a, b, preferDown, flowBox, band) {
    const loX = Math.min(a.left, b.left) - 4;
    const hiX = Math.max(a.right, b.right) + 4;
    const pool = band ? obstaclesInBand(obstacles, band) : obstacles;
    const relevant = pool.filter(
      (o) => !o.skip && o.box.right >= loX && o.box.left <= hiX
    );
    const minY = (flowBox && flowBox.top != null ? flowBox.top : 0) + 8;
    const maxY = (flowBox && flowBox.bottom != null ? flowBox.bottom : 1e9) - 8;
    if (preferDown) {
      let y = Math.max(a.bottom, b.bottom) + GUTTER;
      relevant.forEach((o) => {
        y = Math.max(y, o.box.bottom + GUTTER);
      });
      return clamp(y + 8, minY, maxY);
    }
    let y = Math.min(a.top, b.top) - GUTTER;
    relevant.forEach((o) => {
      y = Math.min(y, o.box.top - GUTTER);
    });
    return clamp(y - 8, minY, maxY);
  }

  function corridorX(obstacles, a, b, preferRight, flowBox, band) {
    const loY = Math.min(a.top, b.top) - 4;
    const hiY = Math.max(a.bottom, b.bottom) + 4;
    const pool = band ? obstaclesInBand(obstacles, band) : obstacles;
    const relevant = pool.filter(
      (o) => !o.skip && o.box.bottom >= loY && o.box.top <= hiY
    );
    const minX = (flowBox && flowBox.left != null ? flowBox.left : 0) + 8;
    const maxX = (flowBox && flowBox.right != null ? flowBox.right : 1e9) - 8;
    if (preferRight) {
      let x = Math.max(a.right, b.right) + GUTTER;
      relevant.forEach((o) => {
        x = Math.max(x, o.box.right + GUTTER);
      });
      return clamp(x + 8, minX, maxX);
    }
    let x = Math.min(a.left, b.left) - GUTTER;
    relevant.forEach((o) => {
      x = Math.min(x, o.box.left - GUTTER);
    });
    return clamp(x - 8, minX, maxX);
  }

  function gapCorridorY(a, b, obstacles, flowBox) {
    // Horizontal run in the gap between a lower edge and an upper edge.
    const upper = a.bottom <= b.top ? a : b;
    const lower = a.bottom <= b.top ? b : a;
    const gapTop = upper.bottom;
    const gapBottom = lower.top;
    const band = { kind: "y", lo: Math.min(a.top, b.top), hi: Math.max(a.bottom, b.bottom) };
    const loX = Math.min(a.left, b.left) - 4;
    const hiX = Math.max(a.right, b.right) + 4;
    const relevant = obstaclesInBand(obstacles, band).filter(
      (o) => !o.skip && o.box.right >= loX && o.box.left <= hiX
    );
    if (gapBottom - gapTop >= GUTTER) {
      let y = (gapTop + gapBottom) / 2;
      // Nudge away from anything sitting in the gap.
      relevant.forEach((o) => {
        if (o.box.bottom < gapTop || o.box.top > gapBottom) return;
        if (Math.abs(o.box.cy - y) < o.box.height / 2 + 8) {
          y = o.box.bottom + 10 < gapBottom ? o.box.bottom + 10 : o.box.top - 10;
        }
      });
      return clamp(y, gapTop + 6, gapBottom - 6);
    }
    // No usable gap: fall back below both within the crossed rows.
    return corridorY(obstacles, a, b, true, flowBox, band);
  }

  function buildUPath(p1, p2, midY) {
    return simplify([p1, { x: p1.x, y: midY }, { x: p2.x, y: midY }, p2]);
  }

  function buildCPath(p1, p2, midX) {
    return simplify([p1, { x: midX, y: p1.y }, { x: midX, y: p2.y }, p2]);
  }

  function candidatePaths(a, b, route, obstacles, flowBox) {
    const bandY = {
      kind: "y",
      lo: Math.min(a.top, b.top),
      hi: Math.max(a.bottom, b.bottom),
    };
    const bandX = {
      kind: "x",
      lo: Math.min(a.left, b.left),
      hi: Math.max(a.right, b.right),
    };
    const out = [];

    function add(name, pts) {
      if (pts && pts.length >= 2) out.push({ name, pts });
    }

    const betweenDown = () => {
      const p1 = sidePoint(a, "bottom");
      const p2 = sidePoint(b, "top");
      add("between", buildUPath(p1, p2, gapCorridorY(a, b, obstacles, flowBox)));
    };
    const betweenUp = () => {
      const p1 = sidePoint(a, "top");
      const p2 = sidePoint(b, "bottom");
      add("between-up", buildUPath(p1, p2, gapCorridorY(a, b, obstacles, flowBox)));
    };
    const aroundDown = () => {
      const p1 = sidePoint(a, "bottom");
      const p2 = sidePoint(b, "bottom");
      add(
        "around-down",
        buildUPath(p1, p2, corridorY(obstacles, a, b, true, flowBox, bandY))
      );
    };
    const aroundUp = () => {
      const p1 = sidePoint(a, "top");
      const p2 = sidePoint(b, "top");
      add(
        "around-up",
        buildUPath(p1, p2, corridorY(obstacles, a, b, false, flowBox, bandY))
      );
    };
    const aroundRight = () => {
      const p1 = sidePoint(a, "right");
      const p2 = sidePoint(b, "right");
      add(
        "around-right",
        buildCPath(p1, p2, corridorX(obstacles, a, b, true, flowBox, bandX))
      );
    };
    const aroundLeft = () => {
      const p1 = sidePoint(a, "left");
      const p2 = sidePoint(b, "left");
      add(
        "around-left",
        buildCPath(p1, p2, corridorX(obstacles, a, b, false, flowBox, bandX))
      );
    };
    const sideHV = () => {
      const fromSide = a.cx <= b.cx ? "right" : "left";
      const toSide = a.cx <= b.cx ? "left" : "right";
      const p1 = sidePoint(a, fromSide);
      const p2 = sidePoint(b, toSide);
      const mid = { x: p2.x, y: p1.y };
      add("hv", simplify([p1, mid, p2]));
      const mid2 = { x: p1.x, y: p2.y };
      add("vh", simplify([p1, mid2, p2]));
    };

    if (route === "between") {
      if (b.cy >= a.cy) betweenDown();
      else betweenUp();
      aroundDown();
      aroundUp();
    } else if (route === "down") {
      betweenDown();
      aroundDown();
      aroundRight();
      aroundLeft();
    } else if (route === "up") {
      betweenUp();
      aroundUp();
      aroundRight();
      aroundLeft();
    } else if (route === "right") {
      aroundRight();
      betweenDown();
      betweenUp();
    } else if (route === "left") {
      aroundLeft();
      betweenDown();
      betweenUp();
    } else {
      // auto: prefer gap between lanes first so fan-in stays on top/bottom anchors.
      if (b.cy >= a.cy) betweenDown();
      else betweenUp();
      aroundDown();
      aroundUp();
      aroundRight();
      aroundLeft();
      sideHV();
    }

    // Direct facing when nearly aligned.
    if (Math.abs(a.cx - b.cx) < Math.max(a.width, b.width) * 0.55) {
      const fromSide = a.cy <= b.cy ? "bottom" : "top";
      const toSide = a.cy <= b.cy ? "top" : "bottom";
      add("col", simplify([sidePoint(a, fromSide), sidePoint(b, toSide)]));
    }
    if (Math.abs(a.cy - b.cy) < Math.max(a.height, b.height) * 0.55) {
      const fromSide = a.cx <= b.cx ? "right" : "left";
      const toSide = a.cx <= b.cx ? "left" : "right";
      add("row", simplify([sidePoint(a, fromSide), sidePoint(b, toSide)]));
    }

    return out;
  }

  function scorePath(pts, obstacles, drawn, flowBox, preferName) {
    const hits = pathHitsObstacles(pts, obstacles, HIT_PAD);
    const crosses = pathCrossings(pts, drawn);
    const len = pathLength(pts);
    let oob = 0;
    if (flowBox) {
      pts.forEach((p) => {
        if (
          p.x < flowBox.left - 1 ||
          p.x > flowBox.right + 1 ||
          p.y < flowBox.top - 1 ||
          p.y > flowBox.bottom + 1
        ) {
          oob += 1;
        }
      });
    }
    // Prefer between-lane top/bottom anchors over side detours when both are clear.
    let prefer = 80;
    if (preferName === "between" || preferName === "between-up") prefer = 0;
    else if (preferName === "col" || preferName === "row") prefer = 10;
    else if (preferName === "hv" || preferName === "vh") prefer = 160;
    // Deterministic lexicographic score.
    return hits * 1e6 + crosses * 1e4 + oob * 1e3 + prefer + len;
  }

  function pickPath(a, b, route, obstacles, drawn, flowBox) {
    const candidates = candidatePaths(a, b, route || "auto", obstacles, flowBox);
    if (!candidates.length) {
      return simplify([sidePoint(a, "bottom"), sidePoint(b, "top")]);
    }
    let best = candidates[0];
    let bestScore = scorePath(best.pts, obstacles, drawn, flowBox, best.name);
    for (let i = 1; i < candidates.length; i += 1) {
      const score = scorePath(
        candidates[i].pts,
        obstacles,
        drawn,
        flowBox,
        candidates[i].name
      );
      if (score < bestScore - 1e-6) {
        best = candidates[i];
        bestScore = score;
      }
    }
    return best.pts;
  }

  function orthogonalPoints(a, b, route, obstacles, drawn, flowBox) {
    return pickPath(a, b, route, obstacles, drawn || [], flowBox);
  }

  function simplify(pts) {
    const out = [];
    pts.forEach((p) => {
      if (!out.length) {
        out.push(p);
        return;
      }
      const prev = out[out.length - 1];
      if (Math.abs(prev.x - p.x) < 0.5 && Math.abs(prev.y - p.y) < 0.5) return;
      if (out.length >= 2) {
        const a = out[out.length - 2];
        const colinear =
          (Math.abs(a.x - prev.x) < 0.5 && Math.abs(prev.x - p.x) < 0.5) ||
          (Math.abs(a.y - prev.y) < 0.5 && Math.abs(prev.y - p.y) < 0.5);
        if (colinear) {
          out[out.length - 1] = p;
          return;
        }
      }
      out.push(p);
    });
    return out;
  }

  function pathD(pts) {
    if (!pts.length) return "";
    let d = `M ${pts[0].x} ${pts[0].y}`;
    for (let i = 1; i < pts.length; i += 1) {
      d += ` L ${pts[i].x} ${pts[i].y}`;
    }
    return d;
  }

  function midpoint(pts) {
    if (pts.length < 2) return pts[0] || { x: 0, y: 0 };
    let total = 0;
    const segs = [];
    for (let i = 1; i < pts.length; i += 1) {
      const len = Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
      segs.push(len);
      total += len;
    }
    let at = total / 2;
    for (let i = 1; i < pts.length; i += 1) {
      if (at <= segs[i - 1]) {
        const t = segs[i - 1] ? at / segs[i - 1] : 0;
        return {
          x: pts[i - 1].x + (pts[i].x - pts[i - 1].x) * t,
          y: pts[i - 1].y + (pts[i].y - pts[i - 1].y) * t,
        };
      }
      at -= segs[i - 1];
    }
    return pts[pts.length - 1];
  }

  function parallelOffset(pts, index, count) {
    if (count <= 1) return { pts, labelNudge: 0 };
    const shift = (index - (count - 1) / 2) * PARALLEL_GAP;
    const a = pts[0];
    const b = pts[Math.min(1, pts.length - 1)];
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const len = Math.hypot(dx, dy) || 1;
    const nx = -dy / len;
    const ny = dx / len;
    const moved = pts.map((p) => ({ x: p.x + nx * shift, y: p.y + ny * shift }));
    return { pts: moved, labelNudge: shift };
  }

  function labelLines(label) {
    if (!label) return [];
    return String(label).split(/\n/);
  }

  function measureLabelSize(svg, lines) {
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", "0");
    text.setAttribute("y", "0");
    text.setAttribute("visibility", "hidden");
    text.classList.add("flow-label", "flow-edge-label");
    lines.forEach((line, i) => {
      const tspan = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
      tspan.setAttribute("x", "0");
      tspan.setAttribute("dy", i === 0 ? "0" : "1.15em");
      tspan.textContent = line;
      text.appendChild(tspan);
    });
    svg.appendChild(text);
    const bbox = text.getBBox();
    svg.removeChild(text);
    return { width: bbox.width, height: bbox.height };
  }

  function applyEdgeHooks(el, edge) {
    el.setAttribute("data-from", edge.from);
    el.setAttribute("data-to", edge.to);
    el.setAttribute("data-kind", edge.kind);
    el.classList.add("flow-arrow");
    if (edge.style === "dashed" || edge.kind === "dashed") {
      el.classList.add("flow-arrow-dashed");
    }
    if (edge.kind === "link" || edge.cross) {
      el.classList.add("flow-link");
    }
  }

  function drawPolyline(svg, pts, edge, labelNudge, labelObstacles) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", pathD(pts));
    path.setAttribute("marker-end", "url(#flow-arrowhead)");
    if (edge.style === "dashed") {
      path.setAttribute("stroke-dasharray", "6 4");
    }
    applyEdgeHooks(path, edge);
    svg.appendChild(path);

    const lines = labelLines(edge.label);
    if (!lines.length) return null;

    const mid = midpoint(pts);
    const size = measureLabelSize(svg, lines);
    const placeAbove =
      edge.pairCount <= 1 || edge.pairIndex < edge.pairCount / 2;
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", String(mid.x));
    text.setAttribute("text-anchor", "middle");
    text.classList.add("flow-label", "flow-edge-label");
    applyEdgeHooks(text, edge);

    // Anchor by the label box: keep the whole block off the stroke.
    if (placeAbove) {
      text.setAttribute("y", String(mid.y - LABEL_GAP + labelNudge * 0.15));
      lines.forEach((line, i) => {
        const tspan = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
        tspan.setAttribute("x", String(mid.x));
        if (i === 0) {
          tspan.setAttribute("dy", `${-(lines.length - 1) * 1.15}em`);
        } else {
          tspan.setAttribute("dy", "1.15em");
        }
        tspan.textContent = line;
        text.appendChild(tspan);
      });
    } else {
      text.setAttribute("y", String(mid.y + LABEL_GAP + 8 + labelNudge * 0.15));
      lines.forEach((line, i) => {
        const tspan = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
        tspan.setAttribute("x", String(mid.x));
        tspan.setAttribute("dy", i === 0 ? "0.9em" : "1.15em");
        tspan.textContent = line;
        text.appendChild(tspan);
      });
    }
    svg.appendChild(text);

    // Fine-tune with measured bbox so multi-line text never straddles the stroke.
    const bbox = text.getBBox();
    if (placeAbove && bbox.bottom > mid.y - 6) {
      const shift = bbox.bottom - (mid.y - 6);
      text.setAttribute("y", String(parseFloat(text.getAttribute("y")) - shift));
    } else if (!placeAbove && bbox.top < mid.y + 6) {
      const shift = mid.y + 6 - bbox.top;
      text.setAttribute("y", String(parseFloat(text.getAttribute("y")) + shift));
    }
    const finalBox = text.getBBox();
    if (labelObstacles) {
      labelObstacles.push({
        key: `label:${edge.from}->${edge.to}:${edge.pairIndex}`,
        kind: "label",
        box: {
          left: finalBox.x,
          right: finalBox.x + finalBox.width,
          top: finalBox.y,
          bottom: finalBox.y + finalBox.height,
          width: finalBox.width,
          height: finalBox.height,
          cx: finalBox.x + finalBox.width / 2,
          cy: finalBox.y + finalBox.height / 2,
        },
        skip: false,
      });
    }
    return size;
  }

  function edgeKind(el, cross) {
    const explicit = el.getAttribute("data-kind");
    if (explicit) return explicit;
    if (cross || el.classList.contains("flow-edge-cross")) return "link";
    if (el.getAttribute("data-bidirectional") === "true") return "bidirectional";
    if ((el.getAttribute("data-style") || "solid") === "dashed") return "dashed";
    return "solid";
  }

  function collectEdges(flow) {
    const explicit = Array.from(flow.querySelectorAll(".flow-edge"));
    if (explicit.length) {
      return explicit.map((el) => ({
        from: el.getAttribute("data-from"),
        to: el.getAttribute("data-to"),
        style: el.getAttribute("data-style") || "solid",
        label: el.getAttribute("data-label"),
        bidirectional: el.getAttribute("data-bidirectional") === "true",
        cross: el.classList.contains("flow-edge-cross"),
        route: el.getAttribute("data-route") || "auto",
        kind: edgeKind(el, el.classList.contains("flow-edge-cross")),
        pairIndex: parseInt(el.getAttribute("data-pair-index") || "0", 10),
        pairCount: parseInt(el.getAttribute("data-pair-count") || "1", 10),
        fromAttach: el.getAttribute("data-from-attach") || "node",
        toAttach: el.getAttribute("data-to-attach") || "node",
      }));
    }
    const nodes = Array.from(
      flow.querySelectorAll(".flow-row > .flow-node, :scope > .flow-node")
    );
    const edges = [];
    for (let i = 0; i < nodes.length - 1; i += 1) {
      edges.push({
        from: nodes[i].getAttribute("data-node") || String(i),
        to: nodes[i + 1].getAttribute("data-node") || String(i + 1),
        style: "solid",
        label: null,
        bidirectional: false,
        cross: false,
        route: "auto",
        kind: "solid",
        pairIndex: 0,
        pairCount: 1,
        fromAttach: "node",
        toAttach: "node",
      });
    }
    return edges;
  }

  function ensureLabelGaps(flow, edges, svg, flowBox, scale) {
    flow.querySelectorAll(".flow-node").forEach((n) => {
      n.style.marginInlineEnd = "";
    });
    let changed = false;
    edges.forEach((edge) => {
      if (!edge.label) return;
      const aEl = nodeByKey(flow, edge.from);
      const bEl = nodeByKey(flow, edge.to);
      if (!aEl || !bEl) return;
      const a = attachBox(flow, edge.from, edge.fromAttach, flowBox, scale);
      const b = attachBox(flow, edge.to, edge.toAttach, flowBox, scale);
      if (!a || !b) return;
      if (Math.abs(a.cy - b.cy) > Math.max(a.height, b.height) * 0.7) return;
      if (a.cx >= b.cx) return;
      const size = measureLabelSize(svg, labelLines(edge.label));
      const gap = b.left - a.right;
      const need = size.width + 24;
      if (gap < need) {
        const extra = need - gap;
        aEl.style.marginInlineEnd = `${extra}px`;
        changed = true;
      }
    });
    return changed;
  }

  function placeCallouts(flow, flowBox, scale) {
    const slide = flow.closest(".slide");
    const clampRoot = slide || flow;
    const gap = 12;

    function positionOne(el, box) {
      const pos = el.getAttribute("data-pos") || "below";
      el.style.position = "absolute";
      el.style.zIndex = "2";
      el.style.right = "auto";
      el.style.bottom = "auto";
      if (pos === "below") {
        el.style.left = `${box.cx}px`;
        el.style.top = `${box.bottom + gap}px`;
        el.style.transform = "translateX(-50%)";
      } else if (pos === "below-left") {
        el.style.left = `${box.left}px`;
        el.style.top = `${box.bottom + gap}px`;
        el.style.transform = "translateX(-100%)";
      } else if (pos === "below-right") {
        el.style.left = `${box.right}px`;
        el.style.top = `${box.bottom + gap}px`;
        el.style.transform = "translateX(0)";
      } else if (pos === "above") {
        el.style.left = `${box.cx}px`;
        el.style.top = `${box.top - gap}px`;
        el.style.transform = "translate(-50%, -100%)";
      } else if (pos === "left") {
        el.style.left = `${box.left - gap}px`;
        el.style.top = `${box.cy}px`;
        el.style.transform = "translate(-100%, -50%)";
      } else {
        el.style.left = `${box.right + gap}px`;
        el.style.top = `${box.cy}px`;
        el.style.transform = "translateY(-50%)";
      }
      return pos;
    }

    function clampHorizontal(el) {
      // style.left is flow-relative; measure the transformed box and keep it
      // inside the flow width so shrink-to-fit does not see a horizontal overflow.
      const origin = flow.getBoundingClientRect();
      const placed = relBox(el, origin, scale);
      const flowW = flow.clientWidth;
      let dx = 0;
      if (placed.left < 4) dx = 4 - placed.left;
      if (placed.right > flowW - 4) dx = flowW - 4 - placed.right;
      if (dx) {
        el.style.left = `${(parseFloat(el.style.left) || 0) + dx}px`;
      }
      // Also keep the note inside the slide padding box when the flow is full width.
      const clampRect = clampRoot.getBoundingClientRect();
      const page = el.getBoundingClientRect();
      let sx = 0;
      if (page.left < clampRect.left + 4) sx = clampRect.left + 4 - page.left;
      if (page.right > clampRect.right - 4) sx = clampRect.right - 4 - page.right;
      if (sx) {
        el.style.left = `${(parseFloat(el.style.left) || 0) + sx / scale}px`;
      }
    }

    // Callouts are absolutely positioned and may extend past the flow box;
    // shrink-to-fit counts them via contentExtents. Only clamp horizontally
    // so edge notes stay on-slide without forcing a tall minHeight.
    Array.from(flow.querySelectorAll("div.flow-callout")).forEach((el) => {
      const node = nodeByKey(flow, el.getAttribute("data-anchor"));
      if (!node) return;
      const box = relBox(node, flowBox, scale);
      const pos = positionOne(el, box);
      clampHorizontal(el);
      if (pos === "left" || pos === "right") {
        const clampRect = clampRoot.getBoundingClientRect();
        const placed = el.getBoundingClientRect();
        let sy = 0;
        if (placed.top < clampRect.top + 4) sy = clampRect.top + 4 - placed.top;
        if (placed.bottom > clampRect.bottom - 4) {
          sy = clampRect.bottom - 4 - placed.bottom;
        }
        if (sy) {
          el.style.top = `${(parseFloat(el.style.top) || 0) + sy / scale}px`;
        }
      }
    });
  }

  function drawCalloutConnectors(svg, flow, flowBox, scale) {
    Array.from(flow.querySelectorAll("div.flow-callout")).forEach((el) => {
      const anchorKey = el.getAttribute("data-anchor");
      const pos = el.getAttribute("data-pos") || "below";
      const node = nodeByKey(flow, anchorKey);
      if (!node) return;
      const n = relBox(node, flowBox, scale);
      const c = relBox(el, flowBox, scale);
      let from;
      let to;
      // Path ends at the anchor node so marker-end points at the node.
      if (pos === "below" || pos === "below-left" || pos === "below-right") {
        from = { x: c.cx, y: c.top };
        to = { x: n.cx, y: n.bottom };
      } else if (pos === "above") {
        from = { x: c.cx, y: c.bottom };
        to = { x: n.cx, y: n.top };
      } else if (pos === "left") {
        from = { x: c.right, y: c.cy };
        to = { x: n.left, y: n.cy };
      } else {
        from = { x: c.left, y: c.cy };
        to = { x: n.right, y: n.cy };
      }
      const mid =
        pos === "below" ||
        pos === "below-left" ||
        pos === "below-right" ||
        pos === "above"
          ? [
              from,
              { x: from.x, y: (from.y + to.y) / 2 },
              { x: to.x, y: (from.y + to.y) / 2 },
              to,
            ]
          : [
              from,
              { x: (from.x + to.x) / 2, y: from.y },
              { x: (from.x + to.x) / 2, y: to.y },
              to,
            ];
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", pathD(simplify(mid)));
      path.setAttribute("stroke-dasharray", "5 4");
      path.setAttribute("marker-end", "url(#flow-arrowhead)");
      path.classList.add("flow-arrow", "flow-callout-arrow", "flow-link", "flow-callout");
      path.setAttribute("data-from", anchorKey);
      path.setAttribute("data-to", anchorKey);
      path.setAttribute("data-kind", "link");
      svg.appendChild(path);
    });
  }

  function drawFlow(flow) {
    let svg = flow.querySelector("svg.flow-svg");
    if (!svg) {
      svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.classList.add("flow-svg");
      flow.insertBefore(svg, flow.firstChild);
    }
    while (svg.lastChild) svg.removeChild(svg.lastChild);
    ensureMarkers(svg);
    svg.style.color =
      getComputedStyle(flow).getPropertyValue("--color-flow-arrow").trim() || "#000";

    const scale = slideScale(flow);
    const flowRect = flow.getBoundingClientRect();
    svg.setAttribute("viewBox", `0 0 ${flow.clientWidth} ${flow.clientHeight}`);
    const flowBox = {
      left: flowRect.left,
      top: flowRect.top,
      right: flowRect.right,
      bottom: flowRect.bottom,
      width: flowRect.width,
      height: flowRect.height,
    };
    const layoutBox = {
      left: 0,
      top: 0,
      right: flow.clientWidth,
      bottom: flow.clientHeight,
      width: flow.clientWidth,
      height: flow.clientHeight,
    };

    const edges = collectEdges(flow);
    // Widen same-row gaps so multi-line labels fit between nodes.
    if (ensureLabelGaps(flow, edges, svg, flowBox, scale)) {
      // Reflow changed geometry; refresh the flow box.
      const refreshed = flow.getBoundingClientRect();
      flowBox.left = refreshed.left;
      flowBox.top = refreshed.top;
      flowBox.right = refreshed.right;
      flowBox.bottom = refreshed.bottom;
      flowBox.width = refreshed.width;
      flowBox.height = refreshed.height;
      svg.setAttribute("viewBox", `0 0 ${flow.clientWidth} ${flow.clientHeight}`);
      layoutBox.right = flow.clientWidth;
      layoutBox.bottom = flow.clientHeight;
      layoutBox.width = flow.clientWidth;
      layoutBox.height = flow.clientHeight;
    }

    placeCallouts(flow, flowBox, scale);

    const drawn = [];
    const labelObstacles = [];
    edges.forEach((edge) => {
      const a = attachBox(flow, edge.from, edge.fromAttach, flowBox, scale);
      const b = attachBox(flow, edge.to, edge.toAttach, flowBox, scale);
      if (!a || !b) return;
      const obstacles = collectObstacles(flow, flowBox, scale, [edge.from, edge.to]).concat(
        labelObstacles
      );
      let pts;
      const sameRow = Math.abs(a.cy - b.cy) < Math.max(a.height, b.height) * 0.7;
      const sameCol = Math.abs(a.cx - b.cx) < Math.max(a.width, b.width) * 0.7;
      if (edge.cross || edge.kind === "link") {
        pts = orthogonalPoints(a, b, edge.route || "auto", obstacles, drawn, layoutBox);
      } else if (sameRow) {
        const fromSide = a.cx <= b.cx ? "right" : "left";
        const toSide = a.cx <= b.cx ? "left" : "right";
        pts = [sidePoint(a, fromSide), sidePoint(b, toSide)];
      } else if (sameCol) {
        const fromSide = a.cy <= b.cy ? "bottom" : "top";
        const toSide = a.cy <= b.cy ? "top" : "bottom";
        pts = [sidePoint(a, fromSide), sidePoint(b, toSide)];
      } else {
        pts = orthogonalPoints(a, b, "auto", obstacles, drawn, layoutBox);
      }
      const shifted = parallelOffset(pts, edge.pairIndex, edge.pairCount);
      drawPolyline(svg, shifted.pts, edge, shifted.labelNudge, labelObstacles);
      drawn.push(shifted.pts);
      if (edge.bidirectional) {
        const back = [...shifted.pts].reverse();
        drawPolyline(
          svg,
          back,
          { ...edge, label: null, bidirectional: false },
          0,
          null
        );
      }
    });

    drawCalloutConnectors(svg, flow, flowBox, scale);
  }

  function contentExtents(content) {
    // Include the last child's margin/padding box; scrollHeight alone can miss it.
    let maxBottom = content.scrollHeight;
    let maxRight = content.scrollWidth;
    Array.from(content.children).forEach((ch) => {
      const style = getComputedStyle(ch);
      const mb = parseFloat(style.marginBottom) || 0;
      const mr = parseFloat(style.marginRight) || 0;
      maxBottom = Math.max(maxBottom, ch.offsetTop + ch.offsetHeight + mb);
      maxRight = Math.max(maxRight, ch.offsetLeft + ch.offsetWidth + mr);
    });
    // Absolutely positioned callouts can sit past the flow box.
    const root = content.getBoundingClientRect();
    const slide = content.closest(".slide");
    const scale = Number((slide && slide.dataset.scale) || "1") || 1;
    content.querySelectorAll("div.flow-callout").forEach((el) => {
      const r = el.getBoundingClientRect();
      maxBottom = Math.max(maxBottom, (r.bottom - root.top) / scale + 4);
      maxRight = Math.max(maxRight, (r.right - root.left) / scale + 4);
    });
    return { width: maxRight, height: maxBottom };
  }

  function fits(slideInner, content) {
    const extents = contentExtents(content);
    return (
      extents.height <= slideInner.clientHeight + 0.5 &&
      extents.width <= slideInner.clientWidth + 0.5
    );
  }

  function shrinkToFit(slide) {
    const inner = slide.querySelector(".slide-inner");
    const content = slide.querySelector(".slide-content");
    if (!inner || !content) return true;

    let scale = 1;
    inner.style.transform = "scale(1)";
    inner.style.width = "100%";
    inner.style.height = "100%";
    slide.dataset.scale = "1";
    slide.removeAttribute("data-overflow");

    while (!fits(inner, content) && scale > MIN_SCALE + 1e-9) {
      scale = Math.max(MIN_SCALE, +(scale - STEP).toFixed(2));
      inner.style.transform = `scale(${scale})`;
      inner.style.width = `${100 / scale}%`;
      inner.style.height = `${100 / scale}%`;
      slide.dataset.scale = String(scale);
      document.querySelectorAll(".flow").forEach(drawFlow);
    }

    if (!fits(inner, content)) {
      slide.dataset.overflow = "true";
      return false;
    }
    return true;
  }

  function prepare() {
    document.querySelectorAll(".flow").forEach(drawFlow);
    const overflows = [];
    document.querySelectorAll(".slide").forEach((slide, index) => {
      if (!shrinkToFit(slide)) {
        overflows.push(index + 1);
      }
    });
    document.querySelectorAll(".flow").forEach(drawFlow);
    window.__mdDeckOverflows = overflows;
    window.__mdDeckReady = true;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", prepare);
  } else {
    prepare();
  }
})();
