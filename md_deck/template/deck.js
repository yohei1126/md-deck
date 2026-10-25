(() => {
  const MIN_SCALE = 0.8;
  const STEP = 0.02;
  const GUTTER = 22;
  const PARALLEL_GAP = 18;
  const LABEL_GAP = 10;
  const HIT_PAD = 4;
  const EPS = 0.75;
  const DEFAULT_PORT_GAP = 12;
  const DEFAULT_CALLOUT_GAP = 12;
  const CALLOUT_MIN_SHAFT = 16;
  // Boxes that overlap by at least this much horizontally get one straight
  // vertical stroke instead of a Z between their centres.
  const STRAIGHT_OVERLAP_MIN = 24;
  // Arrowhead marker is 10x7 at strokeWidth units with stroke-width 2 ≈ 18×13 px.
  const ARROWHEAD_LEN = 18;
  const ARROWHEAD_WIDTH = 13;
  // Same-row U detours need ports wider than the head plus a visible gap.
  const DETOUR_PORT_MIN = ARROWHEAD_WIDTH + 5;

  function cssPxVar(el, name, fallback) {
    const raw = getComputedStyle(el).getPropertyValue(name).trim();
    const n = parseFloat(raw);
    return Number.isFinite(n) ? n : fallback;
  }

  function cssTokenVar(el, name, fallback) {
    const raw = getComputedStyle(el).getPropertyValue(name).trim();
    return raw || fallback;
  }

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

  function stackMemberKeys(flow, key) {
    const el = nodeByKey(flow, key);
    if (!el) return key ? [key] : [];
    const stack = el.closest(".flow-stack");
    if (!stack) return [key];
    return Array.from(stack.querySelectorAll(".flow-node"))
      .map((n) => n.getAttribute("data-node"))
      .filter(Boolean);
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
    return sidePointAt(box, side, 0);
  }

  function sidePointAt(box, side, offset) {
    const off = offset || 0;
    switch (side) {
      case "top":
        return { x: box.cx + off, y: box.top };
      case "bottom":
        return { x: box.cx + off, y: box.bottom };
      case "left":
        return { x: box.left, y: box.cy + off };
      case "right":
        return { x: box.right, y: box.cy + off };
      default:
        return { x: box.cx + off, y: box.cy };
    }
  }

  function clampPortOffset(box, side, offset) {
    const span =
      side === "top" || side === "bottom" ? box.width : box.height;
    const half = Math.max(0, span / 2 - 6);
    return clamp(offset, -half, half);
  }

  function inferSide(box, point) {
    const dist = {
      top: Math.abs(point.y - box.top) + Math.abs(point.x - box.cx) * 0.15,
      bottom: Math.abs(point.y - box.bottom) + Math.abs(point.x - box.cx) * 0.15,
      left: Math.abs(point.x - box.left) + Math.abs(point.y - box.cy) * 0.15,
      right: Math.abs(point.x - box.right) + Math.abs(point.y - box.cy) * 0.15,
    };
    let best = "bottom";
    let bestV = dist.bottom;
    Object.keys(dist).forEach((side) => {
      if (dist[side] < bestV) {
        best = side;
        bestV = dist[side];
      }
    });
    return best;
  }

  function portSlotOffset(index, count, gap) {
    if (count <= 1) return 0;
    return (index - (count - 1) / 2) * gap;
  }

  function detourNestGap(portGap) {
    return Math.max(portGap, DETOUR_PORT_MIN);
  }

  function detourBaseClear(portGap) {
    return Math.max(portGap, ARROWHEAD_LEN);
  }

  function isSameSideUD(plan) {
    return (
      plan.fromSide === plan.toSide &&
      (plan.toSide === "top" || plan.toSide === "bottom")
    );
  }

  function nestClearancePx(count, portGap) {
    if (count <= 0) return 0;
    const nestGap = detourNestGap(portGap);
    const baseClear = detourBaseClear(portGap);
    // Outermost trunk sits baseClear + nestGap*(count-1) from the node edge;
    // keep a small margin so the stroke stays inside the flow box.
    return baseClear + nestGap * Math.max(0, count - 1) + 4;
  }

  function lineHitsRect(p, q, r) {
    // Liang-Barsky clip: true when the segment touches the rect.
    let t0 = 0;
    let t1 = 1;
    const dx = q.x - p.x;
    const dy = q.y - p.y;
    const clips = [
      [-dx, p.x - r.left],
      [dx, r.right - p.x],
      [-dy, p.y - r.top],
      [dy, r.bottom - p.y],
    ];
    for (let i = 0; i < clips.length; i += 1) {
      const a = clips[i][0];
      const b = clips[i][1];
      if (Math.abs(a) < 1e-9) {
        if (b < 0) return false;
        continue;
      }
      const t = b / a;
      if (a < 0) {
        if (t > t1) return false;
        if (t > t0) t0 = t;
      } else {
        if (t < t0) return false;
        if (t < t1) t1 = t;
      }
    }
    return t1 >= t0;
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
    if (Math.abs(p.x - q.x) < EPS) {
      return p.x >= padBox.left && p.x <= padBox.right && maxY >= padBox.top && minY <= padBox.bottom;
    }
    if (Math.abs(p.y - q.y) < EPS) {
      return p.y >= padBox.top && p.y <= padBox.bottom && maxX >= padBox.left && minX <= padBox.right;
    }
    return lineHitsRect(p, q, padBox);
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

  function segmentOverlapLen(a1, a2, b1, b2) {
    // Collinear overlapping length for orthogonal segments (shared trunks).
    const aVert = Math.abs(a1.x - a2.x) < EPS;
    const bVert = Math.abs(b1.x - b2.x) < EPS;
    if (aVert !== bVert) return 0;
    if (aVert) {
      if (Math.abs(a1.x - b1.x) > EPS) return 0;
      const aLo = Math.min(a1.y, a2.y);
      const aHi = Math.max(a1.y, a2.y);
      const bLo = Math.min(b1.y, b2.y);
      const bHi = Math.max(b1.y, b2.y);
      return Math.max(0, Math.min(aHi, bHi) - Math.max(aLo, bLo));
    }
    if (Math.abs(a1.y - b1.y) > EPS) return 0;
    const aLo = Math.min(a1.x, a2.x);
    const aHi = Math.max(a1.x, a2.x);
    const bLo = Math.min(b1.x, b2.x);
    const bHi = Math.max(b1.x, b2.x);
    return Math.max(0, Math.min(aHi, bHi) - Math.max(aLo, bLo));
  }

  function pathOverlaps(pts, drawn) {
    const ends = [pts[0], pts[pts.length - 1]];
    let total = 0;
    for (let i = 1; i < pts.length; i += 1) {
      drawn.forEach((other) => {
        const otherEnds = [other[0], other[other.length - 1]];
        for (let j = 1; j < other.length; j += 1) {
          const overlap = segmentOverlapLen(
            pts[i - 1],
            pts[i],
            other[j - 1],
            other[j]
          );
          if (overlap <= 8) continue;
          // Ignore stub overlap that meets at a shared port.
          const mid = {
            x: (pts[i - 1].x + pts[i].x) / 2,
            y: (pts[i - 1].y + pts[i].y) / 2,
          };
          const nearShared = ends.some((e) =>
            otherEnds.some((o) => nearPoint(e, o, 14) && nearPoint(mid, e, 40))
          );
          if (!nearShared) total += overlap;
        }
      });
    }
    return total;
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

    // Direct facing only when truly aligned (keeps segments orthogonal).
    // Skip for explicit between: that route must leave bottom / enter top via a U.
    if (route !== "between") {
      if (Math.abs(a.cx - b.cx) < EPS) {
        const fromSide = a.cy <= b.cy ? "bottom" : "top";
        const toSide = a.cy <= b.cy ? "top" : "bottom";
        add("col", simplify([sidePoint(a, fromSide), sidePoint(b, toSide)]));
      }
      if (Math.abs(a.cy - b.cy) < EPS) {
        const fromSide = a.cx <= b.cx ? "right" : "left";
        const toSide = a.cx <= b.cx ? "left" : "right";
        add("row", simplify([sidePoint(a, fromSide), sidePoint(b, toSide)]));
      }
    }

    return out;
  }

  function scorePath(pts, obstacles, drawn, flowBox, preferName) {
    const hits = pathHitsObstacles(pts, obstacles, HIT_PAD);
    const crosses = pathCrossings(pts, drawn);
    const overlaps = pathOverlaps(pts, drawn);
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
    else if (preferName === "around-up" || preferName === "around-down") prefer = 40;
    else if (preferName === "hv" || preferName === "vh") prefer = 160;
    // Deterministic lexicographic score.
    return (
      hits * 1e6 + crosses * 1e4 + overlaps * 20 + oob * 1e3 + prefer + len
    );
  }

  function pickPath(a, b, route, obstacles, drawn, flowBox) {
    const routeName = route || "auto";
    let candidates = candidatePaths(a, b, routeName, obstacles, flowBox);
    if (!candidates.length) {
      return simplify([sidePoint(a, "bottom"), sidePoint(b, "top")]);
    }
    // Explicit between must keep the U through the lane gap when it is clear.
    if (routeName === "between") {
      const betweenOnly = candidates.filter(
        (c) => c.name === "between" || c.name === "between-up"
      );
      const clear = betweenOnly.filter(
        (c) => pathHitsObstacles(c.pts, obstacles, HIT_PAD) === 0
      );
      if (clear.length) candidates = clear;
      else if (betweenOnly.length) candidates = betweenOnly;
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

  function preferredSides(a, b, route) {
    const routeName = route || "auto";
    if (routeName === "between") {
      return b.cy >= a.cy ? ["bottom", "top"] : ["top", "bottom"];
    }
    if (routeName === "down") return ["bottom", "top"];
    if (routeName === "up") return ["top", "bottom"];
    if (routeName === "left") return ["left", "left"];
    if (routeName === "right") return ["right", "right"];
    const sameRow =
      Math.abs(a.cy - b.cy) < Math.max(a.height, b.height) * 0.7;
    const sameCol =
      Math.abs(a.cx - b.cx) < Math.max(a.width, b.width) * 0.7;
    if (sameRow) {
      return a.cx <= b.cx ? ["right", "left"] : ["left", "right"];
    }
    if (sameCol) {
      return a.cy <= b.cy ? ["bottom", "top"] : ["top", "bottom"];
    }
    // Prefer top/bottom anchors for lane-style fan-in.
    return b.cy >= a.cy ? ["bottom", "top"] : ["top", "bottom"];
  }

  function candidatePathsForPorts(a, b, route, obstacles, flowBox, p1, p2, fromSide, toSide) {
    // Same family of routes as candidatePaths, but pinned to allocated ports.
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
    const gapY = gapCorridorY(a, b, obstacles, flowBox);
    const downY = corridorY(obstacles, a, b, true, flowBox, bandY);
    const upY = corridorY(obstacles, a, b, false, flowBox, bandY);
    const rightX = corridorX(obstacles, a, b, true, flowBox, bandX);
    const leftX = corridorX(obstacles, a, b, false, flowBox, bandX);

    if (fromSide === "bottom" && toSide === "top") {
      add("between", buildUPath(p1, p2, gapY));
      add("around-down", buildUPath(p1, p2, downY));
    } else if (fromSide === "top" && toSide === "bottom") {
      add("between-up", buildUPath(p1, p2, gapY));
      add("around-up", buildUPath(p1, p2, upY));
    } else if (fromSide === "bottom" && toSide === "bottom") {
      add("around-down", buildUPath(p1, p2, downY));
    } else if (fromSide === "top" && toSide === "top") {
      add("around-up", buildUPath(p1, p2, upY));
    } else if (fromSide === "right" && toSide === "right") {
      add("around-right", buildCPath(p1, p2, rightX));
    } else if (fromSide === "left" && toSide === "left") {
      add("around-left", buildCPath(p1, p2, leftX));
    }

    // Generic orthogonal connectors between the two ports.
    if (Math.abs(p1.x - p2.x) < EPS || Math.abs(p1.y - p2.y) < EPS) {
      add("direct", simplify([p1, p2]));
    } else {
      add("hv", simplify([p1, { x: p2.x, y: p1.y }, p2]));
      add("vh", simplify([p1, { x: p1.x, y: p2.y }, p2]));
      add("u-down", buildUPath(p1, p2, Math.max(p1.y, p2.y, downY)));
      add("u-up", buildUPath(p1, p2, Math.min(p1.y, p2.y, upY)));
    }

    if (route === "between") {
      const betweenOnly = out.filter(
        (c) => c.name === "between" || c.name === "between-up"
      );
      if (betweenOnly.length) return betweenOnly;
    }
    return out;
  }

  function pickPathForPorts(a, b, route, obstacles, drawn, flowBox, p1, p2, fromSide, toSide) {
    const candidates = candidatePathsForPorts(
      a,
      b,
      route || "auto",
      obstacles,
      flowBox,
      p1,
      p2,
      fromSide,
      toSide
    );
    if (!candidates.length) {
      return rebuildOrthogonalWithPorts(null, p1, p2, 0);
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

  function midSegmentIsVertical(pts) {
    if (pts.length < 2) return false;
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
        return (
          Math.abs(pts[i].x - pts[i - 1].x) < EPS &&
          Math.abs(pts[i].y - pts[i - 1].y) >= EPS
        );
      }
      at -= segs[i - 1];
    }
    return false;
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

  function isOrthogonalPath(pts) {
    for (let i = 1; i < pts.length; i += 1) {
      const dx = Math.abs(pts[i].x - pts[i - 1].x);
      const dy = Math.abs(pts[i].y - pts[i - 1].y);
      if (dx >= EPS && dy >= EPS) return false;
    }
    return true;
  }

  function rebuildOrthogonalWithPorts(oldPts, p1, p2, corridorShift) {
    const shift = corridorShift || 0;
    if (!oldPts || oldPts.length < 2) {
      return simplify([p1, p2]);
    }
    if (oldPts.length === 2) {
      if (Math.abs(p1.x - p2.x) < EPS || Math.abs(p1.y - p2.y) < EPS) {
        return simplify([p1, p2]);
      }
      // Keep orthogonal: prefer the bend of the original facing.
      return simplify([p1, { x: p2.x, y: p1.y }, p2]);
    }
    if (oldPts.length >= 4) {
      const mid1 = oldPts[1];
      const mid2 = oldPts[oldPts.length - 2];
      if (Math.abs(mid1.y - mid2.y) < EPS) {
        const midY = mid1.y + shift;
        return simplify([
          p1,
          { x: p1.x, y: midY },
          { x: p2.x, y: midY },
          p2,
        ]);
      }
      if (Math.abs(mid1.x - mid2.x) < EPS) {
        const midX = mid1.x + shift;
        return simplify([
          p1,
          { x: midX, y: p1.y },
          { x: midX, y: p2.y },
          p2,
        ]);
      }
    }
    // Generic: replace ends and force orthogonality on adjacent segments.
    const pts = oldPts.map((p) => ({ x: p.x, y: p.y }));
    pts[0] = p1;
    pts[pts.length - 1] = p2;
    if (pts.length >= 3) {
      if (Math.abs(pts[1].x - pts[0].x) >= EPS && Math.abs(pts[1].y - pts[0].y) >= EPS) {
        pts[1] = { x: pts[0].x, y: pts[1].y };
      }
      const last = pts.length - 1;
      if (
        Math.abs(pts[last].x - pts[last - 1].x) >= EPS &&
        Math.abs(pts[last].y - pts[last - 1].y) >= EPS
      ) {
        pts[last - 1] = { x: pts[last].x, y: pts[last - 1].y };
      }
    }
    return simplify(pts);
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
    if (edge.shape) {
      el.setAttribute("data-shape", edge.shape);
    }
    el.classList.add("flow-arrow");
    if (edge.style === "dashed" || edge.kind === "dashed") {
      el.classList.add("flow-arrow-dashed");
    }
    if (edge.kind === "link" || edge.cross) {
      el.classList.add("flow-link");
    }
  }

  function labelBoxOf(text) {
    const b = text.getBBox();
    return {
      left: b.x,
      right: b.x + b.width,
      top: b.y,
      bottom: b.y + b.height,
      width: b.width,
      height: b.height,
      cx: b.x + b.width / 2,
      cy: b.y + b.height / 2,
    };
  }

  function flowNodeBoxes(flow) {
    if (!flow) return [];
    const origin = flow.getBoundingClientRect();
    const scale = slideScale(flow);
    return Array.from(flow.querySelectorAll(".flow-node")).map((el) =>
      relBox(el, origin, scale)
    );
  }

  function labelOverlapArea(a, b) {
    const w = Math.min(a.right, b.right) - Math.max(a.left, b.left);
    const h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
    if (w <= 1 || h <= 1) return 0;
    return w * h;
  }

  // The SVG sits under the nodes, so a label painted inside a box disappears.
  // A label past the flow is clipped by the slide. A vertical stroke keeps the
  // label beside the line, on the side that has room. A horizontal stroke keeps
  // the label above or below the line — never centred on the shaft — and prefers
  // the side that misses other links. On a short same-row shaft the arrowhead
  // sits on that shaft, so the label stays at mid-shaft instead of sliding
  // into the source box to dodge the head.
  function segmentHitsBox(p, q, box, pad) {
    const left = box.left - pad;
    const right = box.right + pad;
    const top = box.top - pad;
    const bottom = box.bottom + pad;
    const minX = Math.min(p.x, q.x);
    const maxX = Math.max(p.x, q.x);
    const minY = Math.min(p.y, q.y);
    const maxY = Math.max(p.y, q.y);
    if (maxX < left || minX > right || maxY < top || minY > bottom) return false;
    if (Math.abs(p.y - q.y) < EPS) return p.y >= top && p.y <= bottom;
    if (Math.abs(p.x - q.x) < EPS) return p.x >= left && p.x <= right;
    const steps = Math.max(2, Math.ceil(Math.hypot(q.x - p.x, q.y - p.y) / 6));
    for (let s = 0; s <= steps; s += 1) {
      const t = s / steps;
      const x = p.x + (q.x - p.x) * t;
      const y = p.y + (q.y - p.y) * t;
      if (x >= left && x <= right && y >= top && y <= bottom) return true;
    }
    return false;
  }

  function pathHitsBox(pts, box, pad) {
    if (!pts || pts.length < 2) return false;
    for (let i = 1; i < pts.length; i += 1) {
      if (segmentHitsBox(pts[i - 1], pts[i], box, pad)) return true;
    }
    return false;
  }

  function arrowheadBox(pts) {
    if (!pts || pts.length < 2) return null;
    const end = pts[pts.length - 1];
    const prev = pts[pts.length - 2];
    const dx = end.x - prev.x;
    const dy = end.y - prev.y;
    const len = Math.hypot(dx, dy) || 1;
    const back = Math.min(ARROWHEAD_LEN + 4, len);
    const hx = end.x - (dx / len) * back;
    const hy = end.y - (dy / len) * back;
    const half = ARROWHEAD_WIDTH / 2 + 2;
    return {
      left: Math.min(end.x, hx) - half,
      right: Math.max(end.x, hx) + half,
      top: Math.min(end.y, hy) - half,
      bottom: Math.max(end.y, hy) + half,
    };
  }

  function pointBlocked(x, y, nodes) {
    return nodes.some(
      (node) =>
        x >= node.left - 3 &&
        x <= node.right + 3 &&
        y >= node.top - 3 &&
        y <= node.bottom + 3
    );
  }

  // Path-length midpoint can land inside a box the stroke crosses, which hides
  // the label under that box. Prefer the longest run that stays in open space.
  function openLabelPoint(pts, nodes) {
    let best = null;
    for (let i = 1; i < pts.length; i += 1) {
      const p = pts[i - 1];
      const q = pts[i];
      const len = Math.hypot(q.x - p.x, q.y - p.y);
      if (len < 8) continue;
      const steps = Math.max(2, Math.ceil(len / 8));
      let run = null;
      const runs = [];
      for (let s = 0; s <= steps; s += 1) {
        const t = s / steps;
        const x = p.x + (q.x - p.x) * t;
        const y = p.y + (q.y - p.y) * t;
        if (!pointBlocked(x, y, nodes)) {
          if (!run) run = { start: t, end: t };
          else run.end = t;
        } else if (run) {
          runs.push(run);
          run = null;
        }
      }
      if (run) runs.push(run);
      const vertical = Math.abs(q.x - p.x) < EPS && Math.abs(q.y - p.y) >= EPS;
      runs.forEach((span) => {
        const along = (span.end - span.start) * len;
        if (along < 14) return;
        const t0 = span.start;
        const t1 = span.end;
        const t = (t0 + t1) / 2;
        const candidate = {
          x: p.x + (q.x - p.x) * t,
          y: p.y + (q.y - p.y) * t,
          along,
          vertical,
          x0: p.x + (q.x - p.x) * t0,
          y0: p.y + (q.y - p.y) * t0,
          x1: p.x + (q.x - p.x) * t1,
          y1: p.y + (q.y - p.y) * t1,
        };
        if (!best || candidate.along > best.along) best = candidate;
      });
    }
    return best;
  }

  function mountEdgeLabel(svg, pts, edge, lines, labelNudge, flow, otherPaths, labelObstacles) {
    const nodes = flowNodeBoxes(flow);
    const open = openLabelPoint(pts, nodes);
    const mid = open || midpoint(pts);
    const verticalMid = open ? open.vertical : midSegmentIsVertical(pts);
    const size = measureLabelSize(svg, lines);
    const flowW = (flow && flow.clientWidth) || svg.clientWidth || size.width;
    const flowH = (flow && flow.clientHeight) || svg.clientHeight || size.height;
    const pad = 8;
    const nudge = (labelNudge || 0) * 0.15;
    const half = size.width / 2;
    const verticalDy = `${0.35 - ((lines.length - 1) * 1.15) / 2}em`;
    // Same-row chain: the head is the end of this horizontal shaft. Its box is
    // padded off the line, so a centred label that already clears the stroke
    // still "hits" it. Sliding toward x0 then tucks the first glyphs under the
    // source box. Keep mid-shaft in that case.
    const end = pts.length >= 2 ? pts[pts.length - 1] : null;
    const beforeEnd = pts.length >= 2 ? pts[pts.length - 2] : null;
    const headOnShaft =
      !verticalMid &&
      end &&
      beforeEnd &&
      Math.abs(end.y - beforeEnd.y) < EPS &&
      Math.abs(end.x - beforeEnd.x) > 8 &&
      Math.abs(end.y - mid.y) < 2;

    // Do not slide a beside-the-line label back across the stroke to make it
    // fit. A side that cannot hold the text loses on the overflow score, and
    // the other side is used instead.
    const candidates = [];
    if (verticalMid) {
      candidates.push({
        name: "right",
        anchor: "start",
        x: mid.x + LABEL_GAP,
        y: mid.y,
        dy: verticalDy,
        prefer: 0,
        beside: true,
      });
      candidates.push({
        name: "left",
        anchor: "end",
        x: mid.x - LABEL_GAP,
        y: mid.y,
        dy: verticalDy,
        prefer: 4,
        beside: true,
      });
    } else {
      const placeAbove = edge.pairCount <= 1 || edge.pairIndex < edge.pairCount / 2;
      // Above or below only. A beside-the-shaft candidate sits on the stroke
      // and wins whenever the gap is tight enough for the box to kiss a node.
      // Slide along the open run so the label can miss another stroke, but keep
      // its centre over that run — parking it past the elbow reads as detached.
      const centerX = open ? open.x : mid.x;
      const xs = [centerX];
      let spanLo = pad + half;
      let spanHi = Math.max(spanLo, flowW - pad - half);
      if (open && !open.vertical) {
        const x0 = Math.min(open.x0, open.x1);
        const x1 = Math.max(open.x0, open.x1);
        spanLo = Math.max(spanLo, x0);
        spanHi = Math.min(spanHi, Math.max(spanLo, x1));
        if (x1 - x0 > 24) {
          for (let s = 0; s <= 4; s += 1) xs.push(x0 + ((x1 - x0) * s) / 4);
        }
      }
      const seen = [];
      xs.forEach((raw) => {
        const x = clamp(raw, spanLo, spanHi);
        if (seen.some((u) => Math.abs(u - x) < 1)) return;
        seen.push(x);
        const drift = Math.abs(x - centerX);
        candidates.push({
          name: "above",
          anchor: "middle",
          x,
          y: mid.y - LABEL_GAP + nudge,
          dy: `${-(lines.length - 1) * 1.15}em`,
          prefer: (placeAbove ? 0 : 12) + drift * 1.5,
          side: "above",
        });
        candidates.push({
          name: "below",
          anchor: "middle",
          x,
          y: mid.y + LABEL_GAP + 8 + nudge,
          dy: "0.9em",
          prefer: (placeAbove ? 12 : 0) + drift * 1.5,
          side: "below",
        });
      });
    }

    function paint(c) {
      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x", String(c.x));
      text.setAttribute("y", String(c.y));
      text.setAttribute("text-anchor", c.anchor);
      text.classList.add("flow-label", "flow-edge-label");
      applyEdgeHooks(text, edge);
      lines.forEach((line, i) => {
        const tspan = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
        tspan.setAttribute("x", String(c.x));
        tspan.setAttribute("dy", i === 0 ? c.dy : "1.15em");
        tspan.textContent = line;
        text.appendChild(tspan);
      });
      svg.appendChild(text);
      if (c.side === "above" || c.side === "below") {
        // Sit just off the shaft. The initial offset can leave a below-label
        // inside the next node when the lane gap is only a few dozen pixels.
        const bbox = text.getBBox();
        const shift =
          c.side === "above"
            ? bbox.y + bbox.height - (mid.y - 6)
            : bbox.y - (mid.y + 6);
        if (Math.abs(shift) > 0.5) {
          text.setAttribute("y", String(parseFloat(text.getAttribute("y")) - shift));
        }
      }
      return text;
    }

    function score(box, c) {
      let penalty = 0;
      if (box.left < pad) penalty += 10000 + (pad - box.left) * 40;
      if (box.right > flowW - pad) penalty += 10000 + (box.right - (flowW - pad)) * 40;
      if (box.top < 0) penalty += 400 + -box.top * 10;
      if (box.bottom > flowH) penalty += 400 + (box.bottom - flowH) * 10;
      nodes.forEach((node) => {
        if (!c.beside) {
          const area = labelOverlapArea(box, node);
          if (area <= 0) return;
          const overlapH =
            Math.min(box.bottom, node.bottom) - Math.max(box.top, node.top);
          // A hairline kiss of a box in the next lane stays cheap. Text that
          // actually enters an endpoint box (even by a pixel of width) does not.
          if (overlapH > 3) penalty += 6000 + area * 4;
          else penalty += area * 4;
          return;
        }
        // Vertical labels: ignore a one-pixel kiss of the border.
        const inner = {
          left: node.left + 3,
          right: node.right - 3,
          top: node.top + 3,
          bottom: node.bottom - 3,
        };
        if (inner.right <= inner.left || inner.bottom <= inner.top) return;
        penalty += labelOverlapArea(box, inner) * 4;
      });
      // A horizontal label that still straddles the shaft is on the stroke.
      if (!c.beside && box.top < mid.y - 1 && box.bottom > mid.y + 1) penalty += 20000;
      // A beside-the-line label that still covers the stroke x is on the line.
      if (c.beside && box.left < mid.x - 1 && box.right > mid.x + 1) penalty += 8000;
      const head = arrowheadBox(pts);
      if (!headOnShaft && head && labelOverlapArea(box, head) > 0) penalty += 4500;
      (otherPaths || []).forEach((other) => {
        if (pathHitsBox(other, box, 1)) penalty += 7000;
      });
      (labelObstacles || []).forEach((obstacle) => {
        const other = obstacle && obstacle.box;
        if (other && labelOverlapArea(box, other) > 0) penalty += 5000;
      });
      return penalty;
    }

    let bestText = null;
    let bestScore = Infinity;
    candidates.forEach((c) => {
      const text = paint(c);
      const box = labelBoxOf(text);
      const total = score(box, c) + c.prefer;
      if (total < bestScore - 1e-6) {
        if (bestText) svg.removeChild(bestText);
        bestText = text;
        bestScore = total;
      } else {
        svg.removeChild(text);
      }
    });
    return bestText ? labelBoxOf(bestText) : null;
  }

  function drawPolyline(svg, pts, edge, labelNudge, labelObstacles, flow, otherPaths) {
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

    const finalBox = mountEdgeLabel(
      svg,
      pts,
      edge,
      lines,
      labelNudge,
      flow,
      otherPaths,
      labelObstacles
    );
    if (!finalBox) return null;
    if (labelObstacles) {
      labelObstacles.push({
        key: `label:${edge.from}->${edge.to}:${edge.pairIndex}`,
        kind: "label",
        box: finalBox,
        skip: false,
      });
    }
    return { width: finalBox.width, height: finalBox.height };
  }

  function edgeKind(el, cross) {
    const explicit = el.getAttribute("data-kind");
    if (explicit) return explicit;
    if (cross || el.classList.contains("flow-edge-cross")) return "link";
    if (el.getAttribute("data-bidirectional") === "true") return "bidirectional";
    if ((el.getAttribute("data-style") || "solid") === "dashed") return "dashed";
    return "solid";
  }

  function defaultFlowEdgeShape(flow) {
    if (flow.classList.contains("flow-straight")) return "straight";
    const token = cssTokenVar(flow, "--flow-edge-shape", "orthogonal")
      .replace(/^["']|["']$/g, "")
      .toLowerCase();
    return token === "straight" ? "straight" : "orthogonal";
  }

  function collectEdges(flow) {
    const flowShape = defaultFlowEdgeShape(flow);
    const explicit = Array.from(flow.querySelectorAll(".flow-edge"));
    if (explicit.length) {
      return explicit.map((el) => {
        const rawShape = (el.getAttribute("data-shape") || "").toLowerCase();
        const shape =
          rawShape === "straight" || rawShape === "orthogonal"
            ? rawShape
            : flowShape;
        return {
          from: el.getAttribute("data-from"),
          to: el.getAttribute("data-to"),
          style: el.getAttribute("data-style") || "solid",
          label: el.getAttribute("data-label"),
          bidirectional: el.getAttribute("data-bidirectional") === "true",
          cross: el.classList.contains("flow-edge-cross"),
          route: el.getAttribute("data-route") || "auto",
          shape,
          kind: edgeKind(el, el.classList.contains("flow-edge-cross")),
          pairIndex: parseInt(el.getAttribute("data-pair-index") || "0", 10),
          pairCount: parseInt(el.getAttribute("data-pair-count") || "1", 10),
          fromAttach: el.getAttribute("data-from-attach") || "node",
          toAttach: el.getAttribute("data-to-attach") || "node",
        };
      });
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
        shape: flowShape,
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
    // Above/below facing stubs need room for a full arrowhead on the final segment.
    // ARROWHEAD_LEN alone leaves no shaft: the connector reads as a lone
    // triangle. Keep a visible stroke before the head.
    const gap = Math.max(
      cssPxVar(flow, "--flow-callout-gap", DEFAULT_CALLOUT_GAP),
      ARROWHEAD_LEN + CALLOUT_MIN_SHAFT
    );

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

  function calloutExitPoint(c, pos, side) {
    if (side === "top") return { x: c.cx, y: c.top };
    if (side === "bottom") return { x: c.cx, y: c.bottom };
    if (side === "left") return { x: c.left, y: c.cy };
    if (side === "right") return { x: c.right, y: c.cy };
    if (pos === "below" || pos === "below-left" || pos === "below-right") {
      return { x: c.cx, y: c.top };
    }
    if (pos === "above") return { x: c.cx, y: c.bottom };
    if (pos === "left") return { x: c.right, y: c.cy };
    return { x: c.left, y: c.cy };
  }

  function calloutExitSide(pos, side) {
    if (side === "top" || side === "bottom" || side === "left" || side === "right") {
      return side;
    }
    if (pos === "below" || pos === "below-left" || pos === "below-right") return "top";
    if (pos === "above") return "bottom";
    if (pos === "left") return "right";
    return "left";
  }

  function calloutEnterEdge(pos) {
    if (pos === "below" || pos === "below-left" || pos === "below-right") return "bottom";
    if (pos === "above") return "top";
    if (pos === "left") return "left";
    return "right";
  }

  function calloutFacingExit(pos) {
    // Nearest exit that faces the anchor (never runs back through the box).
    if (pos === "above") return "bottom";
    if (pos === "below" || pos === "below-left" || pos === "below-right") return "top";
    if (pos === "left") return "right";
    return "left";
  }

  function calloutPathHitsBox(pts, box) {
    // Inset so a stub that only leaves the exit edge is allowed; interior crossings fail.
    const inset = 2;
    const inner = {
      left: box.left + inset,
      right: box.right - inset,
      top: box.top + inset,
      bottom: box.bottom - inset,
      width: Math.max(0, box.width - inset * 2),
      height: Math.max(0, box.height - inset * 2),
    };
    if (inner.width < 1 || inner.height < 1) return false;
    return pathHitsObstacles(pts, [{ box: inner }], 0) > 0;
  }

  function calloutFinalPerpendicular(pts, enter) {
    // Last segment must meet the anchor edge at a right angle (not run along it).
    if (!pts || pts.length < 2) return false;
    const a = pts[pts.length - 2];
    const b = pts[pts.length - 1];
    const dx = Math.abs(a.x - b.x);
    const dy = Math.abs(a.y - b.y);
    if (enter === "top" || enter === "bottom") {
      return dx < EPS && dy > 2;
    }
    return dy < EPS && dx > 2;
  }

  function calloutFinalLength(pts) {
    if (!pts || pts.length < 2) return 0;
    const a = pts[pts.length - 2];
    const b = pts[pts.length - 1];
    return Math.hypot(a.x - b.x, a.y - b.y);
  }

  function calloutFinalOk(pts, enter) {
    return (
      calloutFinalPerpendicular(pts, enter) &&
      calloutFinalLength(pts) >= ARROWHEAD_LEN - 0.5
    );
  }

  function calloutOutsidePolyline(from, to, exit, enter, callout) {
    // Leave the requested side, step clear of the box, then enter perpendicular.
    // Final stub must be at least ARROWHEAD_LEN so the marker does not swallow the corner.
    const pad = 8;
    const finalMin = ARROWHEAD_LEN;
    if (exit === "left" || exit === "right") {
      const x = exit === "left" ? callout.left - pad : callout.right + pad;
      if (enter === "top" || enter === "bottom") {
        let midY =
          enter === "top" ? callout.bottom + pad : callout.top - pad;
        if (enter === "top") {
          midY = Math.min(midY, to.y - finalMin);
        } else {
          midY = Math.max(midY, to.y + finalMin);
        }
        if (enter === "top" && midY >= to.y - 2) return null;
        if (enter === "bottom" && midY <= to.y + 2) return null;
        return simplify([
          from,
          { x, y: from.y },
          { x, y: midY },
          { x: to.x, y: midY },
          to,
        ]);
      }
      // Side-to-side: keep a long enough final horizontal stub.
      let approachX = x;
      if (enter === "left") approachX = Math.min(approachX, to.x - finalMin);
      if (enter === "right") approachX = Math.max(approachX, to.x + finalMin);
      return simplify([from, { x: approachX, y: from.y }, { x: approachX, y: to.y }, to]);
    }
    if (exit === "top" || exit === "bottom") {
      const y = exit === "top" ? callout.top - pad : callout.bottom + pad;
      if (enter === "left" || enter === "right") {
        let midX =
          enter === "left" ? callout.right + pad : callout.left - pad;
        if (enter === "left") {
          midX = Math.min(midX, to.x - finalMin);
        } else {
          midX = Math.max(midX, to.x + finalMin);
        }
        if (enter === "left" && midX >= to.x - 2) return null;
        if (enter === "right" && midX <= to.x + 2) return null;
        return simplify([
          from,
          { x: from.x, y },
          { x: midX, y },
          { x: midX, y: to.y },
          to,
        ]);
      }
      let approachY = y;
      if (enter === "top") approachY = Math.min(approachY, to.y - finalMin);
      if (enter === "bottom") approachY = Math.max(approachY, to.y + finalMin);
      return simplify([from, { x: from.x, y: approachY }, { x: to.x, y: approachY }, to]);
    }
    return null;
  }

  function calloutConnectorRaw(from, to, exit, enter) {
    // When the exit side is perpendicular to the edge the path enters, use an
    // L (leave sideways, run to the entry x/y, then enter perpendicular).
    // Same-axis exits keep a mid corridor (H-V-H or V-H-V).
    const exitHorizontal = exit === "left" || exit === "right";
    const enterVertical = enter === "top" || enter === "bottom";
    if (exitHorizontal && enterVertical) {
      return simplify([from, { x: to.x, y: from.y }, to]);
    }
    if (!exitHorizontal && !enterVertical) {
      return simplify([from, { x: from.x, y: to.y }, to]);
    }
    if (enterVertical) {
      const midY = (from.y + to.y) / 2;
      return simplify([
        from,
        { x: from.x, y: midY },
        { x: to.x, y: midY },
        to,
      ]);
    }
    const midX = (from.x + to.x) / 2;
    return simplify([
      from,
      { x: midX, y: from.y },
      { x: midX, y: to.y },
      to,
    ]);
  }

  function calloutConnectorPoints(from, to, pos, side, calloutBox) {
    const requested = calloutExitSide(pos, side);
    const enter = calloutEnterEdge(pos);
    let pts = calloutConnectorRaw(from, to, requested, enter);
    if (
      (!calloutBox || !calloutPathHitsBox(pts, calloutBox)) &&
      calloutFinalOk(pts, enter)
    ) {
      return pts;
    }
    // Keep the requested side: route outside the callout box.
    const outside = calloutBox
      ? calloutOutsidePolyline(from, to, requested, enter, calloutBox)
      : null;
    if (
      outside &&
      !calloutPathHitsBox(outside, calloutBox) &&
      calloutFinalOk(outside, enter)
    ) {
      return outside;
    }
    // Fall back to the facing side (e.g. pos=above → bottom).
    const fallback = calloutFacingExit(pos);
    if (fallback === requested) {
      if (outside && calloutFinalOk(outside, enter)) return outside;
      if (calloutFinalOk(pts, enter)) return pts;
      // Prefer a long-enough outside stub even if it grazes the box edge.
      if (outside && calloutFinalPerpendicular(outside, enter)) return outside;
      if (calloutFinalPerpendicular(pts, enter)) return pts;
      return outside || pts;
    }
    const altFrom = calloutExitPoint(calloutBox, pos, fallback);
    const alt = calloutConnectorRaw(altFrom, to, fallback, enter);
    if (calloutFinalOk(alt, enter)) return alt;
    // Stretch the facing stub so the arrowhead does not cover the corner.
    if (calloutBox && (enter === "top" || enter === "bottom")) {
      const midY =
        enter === "top" ? to.y - ARROWHEAD_LEN : to.y + ARROWHEAD_LEN;
      const stretched = simplify([
        altFrom,
        { x: altFrom.x, y: midY },
        { x: to.x, y: midY },
        to,
      ]);
      if (
        !calloutPathHitsBox(stretched, calloutBox) &&
        calloutFinalOk(stretched, enter)
      ) {
        return stretched;
      }
    }
    return alt;
  }

  function drawCalloutConnectors(svg, flow, flowBox, scale) {
    Array.from(flow.querySelectorAll("div.flow-callout")).forEach((el) => {
      const anchorKey = el.getAttribute("data-anchor");
      const pos = el.getAttribute("data-pos") || "below";
      const side = el.getAttribute("data-side");
      const node = nodeByKey(flow, anchorKey);
      if (!node) return;
      const n = relBox(node, flowBox, scale);
      const c = relBox(el, flowBox, scale);
      // Path ends at the anchor node so marker-end points at the node.
      const from = calloutExitPoint(c, pos, side);
      let to;
      if (pos === "below" || pos === "below-left" || pos === "below-right") {
        to = { x: n.cx, y: n.bottom };
      } else if (pos === "above") {
        to = { x: n.cx, y: n.top };
      } else if (pos === "left") {
        to = { x: n.left, y: n.cy };
      } else {
        to = { x: n.right, y: n.cy };
      }
      const pts = calloutConnectorPoints(from, to, pos, side, c);
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", pathD(pts));
      path.setAttribute("stroke-dasharray", "5 4");
      path.setAttribute("marker-end", "url(#flow-arrowhead)");
      path.classList.add("flow-arrow", "flow-callout-arrow", "flow-link", "flow-callout");
      path.setAttribute("data-from", anchorKey);
      path.setAttribute("data-to", anchorKey);
      path.setAttribute("data-kind", "link");
      path.setAttribute("data-enter-edge", calloutEnterEdge(pos));
      svg.appendChild(path);
    });
  }

  const STACK_FAN_GAP = 72;

  function ensureStackFanGaps(flow) {
    // Keep a readable gap beside a stack even if deck CSS sets gap: 0 or flex: 1.
    let changed = false;
    flow.querySelectorAll(".flow-row").forEach((row) => {
      const kids = Array.from(row.children).filter(
        (el) =>
          el.classList.contains("flow-node") || el.classList.contains("flow-stack")
      );
      for (let i = 0; i < kids.length - 1; i += 1) {
        const a = kids[i];
        const b = kids[i + 1];
        if (!a.classList.contains("flow-stack") && !b.classList.contains("flow-stack")) {
          continue;
        }
        const measured = b.getBoundingClientRect().left - a.getBoundingClientRect().right;
        if (measured + 0.5 < STACK_FAN_GAP) {
          const current = parseFloat(a.style.marginInlineEnd) || 0;
          a.style.marginInlineEnd = `${current + (STACK_FAN_GAP - measured)}px`;
          changed = true;
        }
      }
    });
    return changed;
  }

  function forkTrunks(flow, plans) {
    // Two or more edges from one node into the same stack share a trunk,
    // then a horizontal run into each box long enough for the arrowhead.
    const groups = new Map();
    const stacks = Array.from(flow.querySelectorAll(".flow-stack"));
    plans.forEach((plan, idx) => {
      if (plan.edge.shape === "straight") return;
      if (plan.edge.toAttach === "stack" || plan.edge.fromAttach === "stack") return;
      const target = nodeByKey(flow, plan.edge.to);
      const source = nodeByKey(flow, plan.edge.from);
      if (!target || !source) return;
      const stack = target.closest(".flow-stack");
      if (!stack || stack.contains(source)) return;
      const key = `${plan.edge.from}#${stacks.indexOf(stack)}`;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(idx);
    });
    const paths = new Map();
    groups.forEach((idxs) => {
      if (idxs.length < 2) return;
      const sample = plans[idxs[0]];
      const targets = idxs.map((i) => plans[i].b);
      const avgX = targets.reduce((sum, box) => sum + box.cx, 0) / targets.length;
      const goingRight = sample.a.cx <= avgX;
      const srcX = goingRight ? sample.a.right : sample.a.left;
      const edgeX = goingRight
        ? Math.min(...targets.map((box) => box.left))
        : Math.max(...targets.map((box) => box.right));
      const gap = goingRight ? edgeX - srcX : srcX - edgeX;
      const minLast = ARROWHEAD_LEN + 8;
      let junction = goingRight
        ? srcX + Math.max(16, gap - minLast)
        : srcX - Math.max(16, gap - minLast);
      if (goingRight) junction = Math.min(junction, edgeX - minLast);
      else junction = Math.max(junction, edgeX + minLast);
      const srcY = sample.a.cy;
      idxs.forEach((idx) => {
        const box = plans[idx].b;
        const endX = goingRight ? box.left : box.right;
        const y = box.cy;
        const pts =
          Math.abs(y - srcY) < 0.75
            ? [
                { x: srcX, y: srcY },
                { x: endX, y: srcY },
              ]
            : [
                { x: srcX, y: srcY },
                { x: junction, y: srcY },
                { x: junction, y },
                { x: endX, y },
              ];
        paths.set(idx, pts);
      });
    });
    return paths;
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
    function refreshFlowBox() {
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
    // Widen same-row gaps so multi-line labels fit between nodes.
    if (ensureLabelGaps(flow, edges, svg, flowBox, scale)) {
      refreshFlowBox();
    }
    // After label margins, keep a fork beside a stack from collapsing.
    if (ensureStackFanGaps(flow)) {
      refreshFlowBox();
    }

    placeCallouts(flow, flowBox, scale);

    const portGap = cssPxVar(flow, "--flow-port-gap", DEFAULT_PORT_GAP);
    const drawn = [];
    const labelObstacles = [];

    // Pass 1: choose attach sides (before ports) and count fan-in / fan-out.
    const plans = [];
    edges.forEach((edge) => {
      const a = attachBox(flow, edge.from, edge.fromAttach, flowBox, scale);
      const b = attachBox(flow, edge.to, edge.toAttach, flowBox, scale);
      if (!a || !b) return;
      const skip = new Set([edge.from, edge.to]);
      if (edge.fromAttach === "stack") {
        stackMemberKeys(flow, edge.from).forEach((k) => skip.add(k));
      }
      if (edge.toAttach === "stack") {
        stackMemberKeys(flow, edge.to).forEach((k) => skip.add(k));
      }
      const obstacles = collectObstacles(
        flow,
        flowBox,
        scale,
        Array.from(skip)
      ).concat(labelObstacles);
      let fromSide;
      let toSide;
      const route = edge.route || "auto";
      if (edge.cross || edge.kind === "link") {
        [fromSide, toSide] = preferredSides(a, b, route);
      } else {
        const sameRow =
          Math.abs(a.cy - b.cy) < Math.max(a.height, b.height) * 0.7;
        const sameCol =
          Math.abs(a.cx - b.cx) < Math.max(a.width, b.width) * 0.7;
        if (sameRow) {
          fromSide = a.cx <= b.cx ? "right" : "left";
          toSide = a.cx <= b.cx ? "left" : "right";
          const direct = [sidePoint(a, fromSide), sidePoint(b, toSide)];
          // Non-neighbouring same-row edges detour above/below intermediates.
          if (pathHitsObstacles(direct, obstacles, HIT_PAD) > 0) {
            fromSide = "bottom";
            toSide = "bottom";
            // Prefer the side with more clearance.
            const upClear =
              pathHitsObstacles(
                buildUPath(
                  sidePoint(a, "top"),
                  sidePoint(b, "top"),
                  corridorY(obstacles, a, b, false, layoutBox, {
                    kind: "y",
                    lo: Math.min(a.top, b.top),
                    hi: Math.max(a.bottom, b.bottom),
                  })
                ),
                obstacles,
                HIT_PAD
              ) === 0;
            if (upClear) {
              fromSide = "top";
              toSide = "top";
            }
          }
        } else if (sameCol) {
          fromSide = a.cy <= b.cy ? "bottom" : "top";
          toSide = a.cy <= b.cy ? "top" : "bottom";
        } else {
          [fromSide, toSide] = preferredSides(a, b, "auto");
        }
      }
      plans.push({ edge, a, b, fromSide, toSide, obstacles, route });
    });

    // Grow the flow box so nested same-row trunks stay inside it (never through
    // the slide title). Padding pushes nodes down/up inside the SVG viewBox.
    function maxSameSideNestCount(side) {
      let maxCount = 0;
      const toMap = new Map();
      const fromMap = new Map();
      plans.forEach((plan) => {
        if (!isSameSideUD(plan) || plan.toSide !== side) return;
        const tk = `${plan.edge.to}:${plan.toSide}`;
        const fk = `${plan.edge.from}:${plan.fromSide}`;
        toMap.set(tk, (toMap.get(tk) || 0) + 1);
        fromMap.set(fk, (fromMap.get(fk) || 0) + 1);
      });
      toMap.forEach((n) => {
        maxCount = Math.max(maxCount, n);
      });
      fromMap.forEach((n) => {
        maxCount = Math.max(maxCount, n);
      });
      return maxCount;
    }
    function refreshFlowMetrics() {
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
    const needTop = nestClearancePx(maxSameSideNestCount("top"), portGap);
    const needBottom = nestClearancePx(maxSameSideNestCount("bottom"), portGap);
    // Reset inline padding so CSS card-padding is the baseline each redraw.
    flow.style.paddingTop = "";
    flow.style.paddingBottom = "";
    const basePadTop = parseFloat(getComputedStyle(flow).paddingTop) || 0;
    const basePadBottom = parseFloat(getComputedStyle(flow).paddingBottom) || 0;
    let grew = false;
    if (needTop > basePadTop + 0.5) {
      flow.style.paddingTop = `${needTop}px`;
      grew = true;
    }
    if (needBottom > basePadBottom + 0.5) {
      flow.style.paddingBottom = `${needBottom}px`;
      grew = true;
    }
    if (grew) {
      refreshFlowMetrics();
      plans.forEach((plan) => {
        plan.a = attachBox(flow, plan.edge.from, plan.edge.fromAttach, flowBox, scale);
        plan.b = attachBox(flow, plan.edge.to, plan.edge.toAttach, flowBox, scale);
        const skip = new Set([plan.edge.from, plan.edge.to]);
        if (plan.edge.fromAttach === "stack") {
          stackMemberKeys(flow, plan.edge.from).forEach((k) => skip.add(k));
        }
        if (plan.edge.toAttach === "stack") {
          stackMemberKeys(flow, plan.edge.to).forEach((k) => skip.add(k));
        }
        plan.obstacles = collectObstacles(
          flow,
          flowBox,
          scale,
          Array.from(skip)
        ).concat(labelObstacles);
      });
      // Callouts sit relative to nodes; re-place after padding shifts them.
      placeCallouts(flow, flowBox, scale);
    }

    const portCounts = new Map();
    plans.forEach((plan) => {
      const fk = `${plan.edge.from}:${plan.fromSide}`;
      const tk = `${plan.edge.to}:${plan.toSide}`;
      portCounts.set(fk, (portCounts.get(fk) || 0) + 1);
      portCounts.set(tk, (portCounts.get(tk) || 0) + 1);
    });

    // Same-row U detours use a wider gap so arrowheads do not merge; cross-row
    // / diagonal fan-in keeps flow_port_gap (default 12).
    function gapForSide(plan, count) {
      if (isSameSideUD(plan) && count > 1) return detourNestGap(portGap);
      return portGap;
    }

    // Pre-assign port slots. Same-side U/C fan-in reverses target slots so the
    // farther source gets the farther port and nested trunks do not cross.
    // Fan-out mirrors that on the source side (farther target = outer port).
    const fromSlotOf = new Array(plans.length);
    const toSlotOf = new Array(plans.length);
    const fromGroups = new Map();
    plans.forEach((plan, idx) => {
      const key = `${plan.edge.from}:${plan.fromSide}`;
      if (!fromGroups.has(key)) fromGroups.set(key, []);
      fromGroups.get(key).push(idx);
    });
    fromGroups.forEach((idxs) => {
      const sample = plans[idxs[0]];
      const side = sample.fromSide;
      const allNest = idxs.every((i) => isSameSideUD(plans[i]));
      if (
        allNest &&
        (side === "top" || side === "bottom") &&
        idxs.length > 1
      ) {
        idxs.sort((i, j) => plans[i].b.cx - plans[j].b.cx);
        const avgDst =
          idxs.reduce((s, i) => s + plans[i].b.cx, 0) / idxs.length;
        const toRight = sample.a.cx <= avgDst;
        idxs.forEach((planIdx, order) => {
          // Farther target gets the outer (higher-rank) source port.
          fromSlotOf[planIdx] = toRight ? order : idxs.length - 1 - order;
        });
      } else if (
        allNest &&
        (side === "left" || side === "right") &&
        idxs.length > 1
      ) {
        idxs.sort((i, j) => plans[i].b.cy - plans[j].b.cy);
        const avgDst =
          idxs.reduce((s, i) => s + plans[i].b.cy, 0) / idxs.length;
        const toBelow = sample.a.cy <= avgDst;
        idxs.forEach((planIdx, order) => {
          fromSlotOf[planIdx] = toBelow ? order : idxs.length - 1 - order;
        });
      } else {
        idxs.forEach((planIdx, order) => {
          fromSlotOf[planIdx] = order;
        });
      }
    });
    const toGroups = new Map();
    plans.forEach((plan, idx) => {
      const key = `${plan.edge.to}:${plan.toSide}`;
      if (!toGroups.has(key)) toGroups.set(key, []);
      toGroups.get(key).push(idx);
    });
    toGroups.forEach((idxs) => {
      const sample = plans[idxs[0]];
      const side = sample.toSide;
      const allNest = idxs.every((i) => plans[i].fromSide === plans[i].toSide);
      if (
        allNest &&
        (side === "top" || side === "bottom") &&
        idxs.length > 1
      ) {
        idxs.sort((i, j) => plans[i].a.cx - plans[j].a.cx);
        const avgSrc =
          idxs.reduce((s, i) => s + plans[i].a.cx, 0) / idxs.length;
        const fromLeft = sample.b.cx >= avgSrc;
        idxs.forEach((planIdx, order) => {
          toSlotOf[planIdx] = fromLeft
            ? idxs.length - 1 - order
            : order;
        });
      } else if (
        allNest &&
        (side === "left" || side === "right") &&
        idxs.length > 1
      ) {
        idxs.sort((i, j) => plans[i].a.cy - plans[j].a.cy);
        const avgSrc =
          idxs.reduce((s, i) => s + plans[i].a.cy, 0) / idxs.length;
        const fromAbove = sample.b.cy >= avgSrc;
        idxs.forEach((planIdx, order) => {
          toSlotOf[planIdx] = fromAbove
            ? idxs.length - 1 - order
            : order;
        });
      } else {
        idxs.forEach((planIdx, order) => {
          toSlotOf[planIdx] = order;
        });
      }
    });

    function portAt(box, side, slot, count, gap) {
      const offset = clampPortOffset(
        box,
        side,
        portSlotOffset(slot, count, gap)
      );
      return {
        point: sidePointAt(box, side, offset),
        index: slot,
        count,
        gap,
      };
    }

    const forkPaths = forkTrunks(flow, plans);

    // Pass 2: route between allocated ports (orthogonal by default; straight opt-in).
    // Paths are chosen first so a label can see every other stroke, including
    // links drawn later. Routing still sees earlier paths via `drawn`.
    const routed = [];
    plans.forEach((plan, planIdx) => {
      const fromCount =
        portCounts.get(`${plan.edge.from}:${plan.fromSide}`) || 1;
      const toCount = portCounts.get(`${plan.edge.to}:${plan.toSide}`) || 1;
      const fromGap = gapForSide(plan, fromCount);
      const toGap = gapForSide(plan, toCount);
      const fromPort = portAt(
        plan.a,
        plan.fromSide,
        fromSlotOf[planIdx],
        fromCount,
        fromGap
      );
      const toPort = portAt(
        plan.b,
        plan.toSide,
        toSlotOf[planIdx],
        toCount,
        toGap
      );
      // One edge between boxes stacked over each other (bottom -> top or
      // top -> bottom) whose x-ranges overlap: share one x so the stroke is a
      // single vertical line instead of a Z through the lane gap.
      if (
        fromCount === 1 &&
        toCount === 1 &&
        !forkPaths.has(planIdx) &&
        ((plan.fromSide === "bottom" && plan.toSide === "top") ||
          (plan.fromSide === "top" && plan.toSide === "bottom"))
      ) {
        const lo = Math.max(plan.a.left, plan.b.left);
        const hi = Math.min(plan.a.right, plan.b.right);
        if (hi - lo >= STRAIGHT_OVERLAP_MIN) {
          const pad = Math.min(plan.a.width, plan.b.width) * 0.15;
          const want = (plan.a.cx + plan.b.cx) / 2;
          const x = clamp(want, lo + Math.min(pad, (hi - lo) / 2), hi - Math.min(pad, (hi - lo) / 2));
          const p1 = { x, y: fromPort.point.y };
          const p2 = { x, y: toPort.point.y };
          if (pathHitsObstacles([p1, p2], plan.obstacles, HIT_PAD) === 0) {
            fromPort.point = p1;
            toPort.point = p2;
          }
        }
      }
      const corridorShift = portSlotOffset(
        toPort.index,
        toPort.count,
        toGap
      );
      const shape = plan.edge.shape === "straight" ? "straight" : "orthogonal";
      let pts = forkPaths.has(planIdx) ? forkPaths.get(planIdx) : null;
      const direct = simplify([fromPort.point, toPort.point]);
      const directClear =
        pathHitsObstacles(direct, plan.obstacles, HIT_PAD) === 0;
      if (pts) {
        // Fork trunk already includes the arrowhead stub.
      } else if (shape === "straight" && directClear) {
        // Straight / diagonal only when the segment clears other nodes
        // (including not running along their borders).
        pts = direct;
      } else {
        // Orthogonal (default), or straight falling back when blocked.
        pts = pickPathForPorts(
          plan.a,
          plan.b,
          plan.route,
          plan.obstacles,
          drawn,
          layoutBox,
          fromPort.point,
          toPort.point,
          plan.fromSide,
          plan.toSide
        );
        // Same-side U detours: nest trunks (fan-in and fan-out) with arrowhead-
        // aware spacing so heads stay clear and trunks do not share a y.
        if (isSameSideUD(plan) && Math.max(fromPort.count, toPort.count) > 1) {
          const nestGap = detourNestGap(portGap);
          const baseClear = detourBaseClear(portGap);
          // Fan-in ranks by target port; fan-out ranks by source port.
          const rank =
            toPort.count > 1 ? toPort.index : fromPort.index;
          const midY =
            plan.toSide === "top"
              ? Math.min(fromPort.point.y, toPort.point.y) -
                baseClear -
                nestGap * rank
              : Math.max(fromPort.point.y, toPort.point.y) +
                baseClear +
                nestGap * rank;
          pts = buildUPath(fromPort.point, toPort.point, midY);
        } else if (
          (plan.fromSide === "bottom" && plan.toSide === "top") ||
          (plan.fromSide === "top" && plan.toSide === "bottom")
        ) {
          pts = rebuildOrthogonalWithPorts(
            pts,
            fromPort.point,
            toPort.point,
            corridorShift * 0.5
          );
        }
        if (!isOrthogonalPath(pts)) {
          pts = rebuildOrthogonalWithPorts(
            null,
            fromPort.point,
            toPort.point,
            0
          );
        }
      }
      const shifted = parallelOffset(
        pts,
        plan.edge.pairIndex,
        plan.edge.pairCount
      );
      routed.push({
        pts: shifted.pts,
        edge: { ...plan.edge, shape },
        labelNudge: shifted.labelNudge,
        bidirectional: plan.edge.bidirectional,
      });
      drawn.push(shifted.pts);
    });

    routed.forEach((item, index) => {
      const others = [];
      routed.forEach((other, otherIndex) => {
        if (otherIndex !== index) others.push(other.pts);
      });
      drawPolyline(
        svg,
        item.pts,
        item.edge,
        item.labelNudge,
        labelObstacles,
        flow,
        others
      );
      if (item.bidirectional) {
        drawPolyline(
          svg,
          [...item.pts].reverse(),
          { ...item.edge, label: null, bidirectional: false },
          0,
          null,
          flow,
          others
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
