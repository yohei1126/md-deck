(() => {
  const MIN_SCALE = 0.8;
  const STEP = 0.02;

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

  function edgePoint(fromRect, toRect, flowBox, fromEnd) {
    // Anchor on the facing sides of the two nodes.
    const fromCx = fromRect.left + fromRect.width / 2 - flowBox.left;
    const fromCy = fromRect.top + fromRect.height / 2 - flowBox.top;
    const toCx = toRect.left + toRect.width / 2 - flowBox.left;
    const toCy = toRect.top + toRect.height / 2 - flowBox.top;
    const dx = toCx - fromCx;
    const dy = toCy - fromCy;
    if (Math.abs(dx) >= Math.abs(dy)) {
      // Horizontal-ish
      if (fromEnd) {
        return {
          x: (dx >= 0 ? fromRect.right : fromRect.left) - flowBox.left,
          y: fromCy,
        };
      }
      return {
        x: (dx >= 0 ? toRect.left : toRect.right) - flowBox.left,
        y: toCy,
      };
    }
    // Vertical-ish
    if (fromEnd) {
      return {
        x: fromCx,
        y: (dy >= 0 ? fromRect.bottom : fromRect.top) - flowBox.top,
      };
    }
    return {
      x: toCx,
      y: (dy >= 0 ? toRect.top : toRect.bottom) - flowBox.top,
    };
  }

  function drawPath(svg, x1, y1, x2, y2, style, label) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    const midX = (x1 + x2) / 2;
    const midY = (y1 + y2) / 2;
    path.setAttribute("d", `M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`);
    path.setAttribute("marker-end", "url(#flow-arrowhead)");
    if (style === "dashed") {
      path.setAttribute("stroke-dasharray", "6 4");
      path.classList.add("flow-arrow-dashed");
    }
    svg.appendChild(path);

    if (label) {
      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x", String(midX));
      text.setAttribute("y", String(midY - 6));
      text.setAttribute("text-anchor", "middle");
      text.classList.add("flow-edge-label");
      text.textContent = label;
      svg.appendChild(text);
    }
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
      }));
    }
    // Legacy: consecutive .flow-node siblings (no edge descriptors)
    const nodes = Array.from(flow.querySelectorAll(":scope > .flow-node"));
    const edges = [];
    for (let i = 0; i < nodes.length - 1; i += 1) {
      edges.push({
        from: nodes[i].getAttribute("data-node") || String(i),
        to: nodes[i + 1].getAttribute("data-node") || String(i + 1),
        style: "solid",
        label: null,
        bidirectional: false,
      });
    }
    return edges;
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

    const edges = collectEdges(flow);
    // Also chain consecutive nodes inside each .flow-row when edges were only
    // emitted as descriptors — descriptors already cover chains.
    edges.forEach((edge) => {
      const a = nodeByKey(flow, edge.from);
      const b = nodeByKey(flow, edge.to);
      if (!a || !b) return;
      const ar = a.getBoundingClientRect();
      const br = b.getBoundingClientRect();
      const p1 = edgePoint(ar, br, flowBox, true);
      const p2 = edgePoint(ar, br, flowBox, false);
      drawPath(svg, p1.x, p1.y, p2.x, p2.y, edge.style, edge.label);
      if (edge.bidirectional) {
        drawPath(svg, p2.x, p2.y, p1.x, p1.y, edge.style, null);
      }
    });
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
