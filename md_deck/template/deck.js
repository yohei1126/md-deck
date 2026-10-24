(() => {
  const MIN_SCALE = 0.8;
  const STEP = 0.02;
  const GUTTER = 22;
  const PARALLEL_GAP = 18;
  const LABEL_GAP = 12;

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

  function relBox(el, flowBox) {
    const r = el.getBoundingClientRect();
    return {
      left: r.left - flowBox.left,
      right: r.right - flowBox.left,
      top: r.top - flowBox.top,
      bottom: r.bottom - flowBox.top,
      width: r.width,
      height: r.height,
      cx: r.left + r.width / 2 - flowBox.left,
      cy: r.top + r.height / 2 - flowBox.top,
    };
  }

  function collectObstacles(flow, flowBox, skipKeys) {
    const skip = new Set(skipKeys || []);
    return Array.from(flow.querySelectorAll(".flow-node")).map((el) => {
      const key = el.getAttribute("data-node");
      const box = relBox(el, flowBox);
      return { key, box, skip: skip.has(key) };
    });
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

  function chooseSides(a, b, route) {
    if (route === "down") return ["bottom", "bottom"];
    if (route === "up") return ["top", "top"];
    if (route === "left") return ["left", "left"];
    if (route === "right") return ["right", "right"];
    const dx = b.cx - a.cx;
    const dy = b.cy - a.cy;
    if (Math.abs(dx) >= Math.abs(dy) * 1.2) {
      return dx >= 0 ? ["right", "left"] : ["left", "right"];
    }
    return dy >= 0 ? ["bottom", "top"] : ["top", "bottom"];
  }

  function corridorY(obstacles, a, b, preferDown) {
    const loX = Math.min(a.left, b.left) - 4;
    const hiX = Math.max(a.right, b.right) + 4;
    const relevant = obstacles.filter(
      (o) => !o.skip && o.box.right >= loX && o.box.left <= hiX
    );
    if (preferDown) {
      let y = Math.max(a.bottom, b.bottom) + GUTTER;
      relevant.forEach((o) => {
        y = Math.max(y, o.box.bottom + GUTTER);
      });
      // Also clear in-lane arrow labels sitting under nodes in this span.
      return y + 8;
    }
    let y = Math.min(a.top, b.top) - GUTTER;
    relevant.forEach((o) => {
      y = Math.min(y, o.box.top - GUTTER);
    });
    return y - 8;
  }

  function corridorX(obstacles, a, b, preferRight) {
    const loY = Math.min(a.top, b.top) - 4;
    const hiY = Math.max(a.bottom, b.bottom) + 4;
    const relevant = obstacles.filter(
      (o) => !o.skip && o.box.bottom >= loY && o.box.top <= hiY
    );
    if (preferRight) {
      let x = Math.max(a.right, b.right) + GUTTER;
      relevant.forEach((o) => {
        x = Math.max(x, o.box.right + GUTTER);
      });
      return x + 8;
    }
    let x = Math.min(a.left, b.left) - GUTTER;
    relevant.forEach((o) => {
      x = Math.min(x, o.box.left - GUTTER);
    });
    return x - 8;
  }

  function orthogonalPoints(a, b, route, obstacles) {
    const [fromSide, toSide] = chooseSides(a, b, route);
    const p1 = sidePoint(a, fromSide);
    const p2 = sidePoint(b, toSide);
    const pts = [p1];

    const sameRow = Math.abs(a.cy - b.cy) < Math.max(a.height, b.height) * 0.55;
    const sameCol = Math.abs(a.cx - b.cx) < Math.max(a.width, b.width) * 0.55;

    if (route === "down" || (route === "auto" && fromSide === "bottom" && !sameRow)) {
      const y = corridorY(obstacles, a, b, true);
      pts.push({ x: p1.x, y });
      pts.push({ x: p2.x, y });
    } else if (route === "up" || (route === "auto" && fromSide === "top" && !sameRow)) {
      const y = corridorY(obstacles, a, b, false);
      pts.push({ x: p1.x, y });
      pts.push({ x: p2.x, y });
    } else if (route === "right" || (route === "auto" && fromSide === "right" && !sameCol)) {
      const x = corridorX(obstacles, a, b, true);
      pts.push({ x, y: p1.y });
      pts.push({ x, y: p2.y });
    } else if (route === "left" || (route === "auto" && fromSide === "left" && !sameCol)) {
      const x = corridorX(obstacles, a, b, false);
      pts.push({ x, y: p1.y });
      pts.push({ x, y: p2.y });
    } else if (sameRow) {
      // Horizontal elbow via mid-x only when clear; else nudge below.
      const midX = (p1.x + p2.x) / 2;
      const blocked = obstacles.some(
        (o) =>
          !o.skip &&
          o.box.left < midX + 6 &&
          o.box.right > midX - 6 &&
          o.box.top < Math.max(p1.y, p2.y) + 4 &&
          o.box.bottom > Math.min(p1.y, p2.y) - 4
      );
      if (blocked || Math.abs(p1.y - p2.y) > 2) {
        const y = corridorY(obstacles, a, b, true);
        pts.push({ x: p1.x, y });
        pts.push({ x: p2.x, y });
      }
    } else if (sameCol) {
      const midY = (p1.y + p2.y) / 2;
      const blocked = obstacles.some(
        (o) =>
          !o.skip &&
          o.box.top < midY + 6 &&
          o.box.bottom > midY - 6 &&
          o.box.left < Math.max(p1.x, p2.x) + 4 &&
          o.box.right > Math.min(p1.x, p2.x) - 4
      );
      if (blocked || Math.abs(p1.x - p2.x) > 2) {
        const x = corridorX(obstacles, a, b, true);
        pts.push({ x, y: p1.y });
        pts.push({ x, y: p2.y });
      }
    } else {
      // Default orthogonal: horizontal then vertical (HV).
      const mid = { x: p2.x, y: p1.y };
      const hits = obstacles.some(
        (o) =>
          !o.skip &&
          o.box.left < mid.x + 4 &&
          o.box.right > mid.x - 4 &&
          o.box.top < Math.max(p1.y, p2.y) + 4 &&
          o.box.bottom > Math.min(p1.y, p2.y) - 4
      );
      if (hits) {
        const y = corridorY(obstacles, a, b, b.cy >= a.cy);
        pts.push({ x: p1.x, y });
        pts.push({ x: p2.x, y });
      } else {
        pts.push(mid);
      }
    }

    pts.push(p2);
    return simplify(pts);
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
    // Perpendicular to first segment
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

  function drawPolyline(svg, pts, edge, labelNudge) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", pathD(pts));
    path.setAttribute("marker-end", "url(#flow-arrowhead)");
    if (edge.style === "dashed") {
      path.setAttribute("stroke-dasharray", "6 4");
    }
    applyEdgeHooks(path, edge);
    svg.appendChild(path);

    const lines = labelLines(edge.label);
    if (!lines.length) return;

    const mid = midpoint(pts);
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", String(mid.x));
    // Solid/first above, later/dashed below when parallel.
    const baseNudge =
      edge.pairCount > 1
        ? (edge.pairIndex >= edge.pairCount / 2 ? LABEL_GAP + 4 : -(LABEL_GAP + 2))
        : -6;
    text.setAttribute("y", String(mid.y + baseNudge + labelNudge * 0.15));
    text.setAttribute("text-anchor", "middle");
    text.classList.add("flow-label", "flow-edge-label");
    applyEdgeHooks(text, edge);
    lines.forEach((line, i) => {
      const tspan = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
      tspan.setAttribute("x", String(mid.x));
      if (i === 0) {
        tspan.setAttribute("dy", "0");
      } else {
        tspan.setAttribute("dy", "1.15em");
      }
      tspan.textContent = line;
      text.appendChild(tspan);
    });
    svg.appendChild(text);
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
      }));
    }
    const nodes = Array.from(flow.querySelectorAll(":scope > .flow-node"));
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
      });
    }
    return edges;
  }

  function placeCallouts(flow, flowBox) {
    Array.from(flow.querySelectorAll(".flow-callout")).forEach((el) => {
      const anchorKey = el.getAttribute("data-anchor");
      const pos = el.getAttribute("data-pos") || "below";
      const node = nodeByKey(flow, anchorKey);
      if (!node) return;
      const box = relBox(node, flowBox);
      el.style.position = "absolute";
      el.style.zIndex = "2";
      const gap = 12;
      if (pos === "below") {
        el.style.left = `${box.cx}px`;
        el.style.top = `${box.bottom + gap}px`;
        el.style.transform = "translateX(-50%)";
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
    });
  }

  function drawCalloutConnectors(svg, flow, flowBox) {
    Array.from(flow.querySelectorAll(".flow-callout")).forEach((el) => {
      const anchorKey = el.getAttribute("data-anchor");
      const pos = el.getAttribute("data-pos") || "below";
      const node = nodeByKey(flow, anchorKey);
      if (!node) return;
      const n = relBox(node, flowBox);
      const c = relBox(el, flowBox);
      let p1;
      let p2;
      if (pos === "below") {
        p1 = { x: n.cx, y: n.bottom };
        p2 = { x: c.cx, y: c.top };
      } else if (pos === "above") {
        p1 = { x: n.cx, y: n.top };
        p2 = { x: c.cx, y: c.bottom };
      } else if (pos === "left") {
        p1 = { x: n.left, y: n.cy };
        p2 = { x: c.right, y: c.cy };
      } else {
        p1 = { x: n.right, y: n.cy };
        p2 = { x: c.left, y: c.cy };
      }
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      const mid =
        pos === "below" || pos === "above"
          ? [
              p1,
              { x: p1.x, y: (p1.y + p2.y) / 2 },
              { x: p2.x, y: (p1.y + p2.y) / 2 },
              p2,
            ]
          : [
              p1,
              { x: (p1.x + p2.x) / 2, y: p1.y },
              { x: (p1.x + p2.x) / 2, y: p2.y },
              p2,
            ];
      path.setAttribute("d", pathD(simplify(mid)));
      path.setAttribute("stroke-dasharray", "5 4");
      path.setAttribute("marker-end", "url(#flow-arrowhead)");
      path.classList.add("flow-arrow", "flow-callout-arrow");
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

    const flowBox = flow.getBoundingClientRect();
    svg.setAttribute("viewBox", `0 0 ${flow.clientWidth} ${flow.clientHeight}`);

    placeCallouts(flow, flowBox);

    const edges = collectEdges(flow);
    edges.forEach((edge) => {
      const aEl = nodeByKey(flow, edge.from);
      const bEl = nodeByKey(flow, edge.to);
      if (!aEl || !bEl) return;
      const a = relBox(aEl, flowBox);
      const b = relBox(bEl, flowBox);
      const obstacles = collectObstacles(flow, flowBox, [edge.from, edge.to]);
      let pts;
      const sameRow = Math.abs(a.cy - b.cy) < Math.max(a.height, b.height) * 0.7;
      const sameCol = Math.abs(a.cx - b.cx) < Math.max(a.width, b.width) * 0.7;
      if (edge.cross || edge.kind === "link") {
        pts = orthogonalPoints(a, b, edge.route || "auto", obstacles);
      } else if (sameRow) {
        // In-lane neighbours: straight facing-side segment (parallel offset applies).
        const fromSide = a.cx <= b.cx ? "right" : "left";
        const toSide = a.cx <= b.cx ? "left" : "right";
        pts = [sidePoint(a, fromSide), sidePoint(b, toSide)];
      } else if (sameCol) {
        const fromSide = a.cy <= b.cy ? "bottom" : "top";
        const toSide = a.cy <= b.cy ? "top" : "bottom";
        pts = [sidePoint(a, fromSide), sidePoint(b, toSide)];
      } else {
        pts = orthogonalPoints(a, b, "auto", obstacles);
      }
      const shifted = parallelOffset(pts, edge.pairIndex, edge.pairCount);
      drawPolyline(svg, shifted.pts, edge, shifted.labelNudge);
      if (edge.bidirectional) {
        const back = [...shifted.pts].reverse();
        drawPolyline(
          svg,
          back,
          { ...edge, label: null, bidirectional: false },
          0
        );
      }
    });

    drawCalloutConnectors(svg, flow, flowBox);
  }

  function fits(slideInner, content) {
    return (
      content.scrollHeight <= slideInner.clientHeight + 0.5 &&
      content.scrollWidth <= slideInner.clientWidth + 0.5
    );
  }

  function shrinkToFit(slide) {
    const inner = slide.querySelector(".slide-inner");
    const content = slide.querySelector(".slide-content");
    if (!inner || !content) return true;

    let scale = 1;
    inner.style.transform = "scale(1)";
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
