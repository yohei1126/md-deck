(() => {
  const MIN_SCALE = 0.8;
  const STEP = 0.02;

  function ensureArrowMarker(svg) {
    let defs = svg.querySelector("defs");
    if (!defs) {
      defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
      svg.appendChild(defs);
    }
    if (svg.querySelector("#flow-arrowhead")) return;
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

  function drawFlow(flow) {
    const nodes = Array.from(flow.querySelectorAll(".flow-node"));
    if (nodes.length < 2) return;

    let svg = flow.querySelector("svg.flow-svg");
    if (!svg) {
      svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.classList.add("flow-svg");
      flow.insertBefore(svg, flow.firstChild);
    }
    while (svg.lastChild) svg.removeChild(svg.lastChild);
    ensureArrowMarker(svg);
    svg.style.color = getComputedStyle(flow).getPropertyValue("--color-flow-arrow").trim() || "#000";

    const flowBox = flow.getBoundingClientRect();
    svg.setAttribute("viewBox", `0 0 ${flow.clientWidth} ${flow.clientHeight}`);

    for (let i = 0; i < nodes.length - 1; i += 1) {
      const a = nodes[i].getBoundingClientRect();
      const b = nodes[i + 1].getBoundingClientRect();
      const x1 = a.right - flowBox.left;
      const y1 = a.top + a.height / 2 - flowBox.top;
      const x2 = b.left - flowBox.left;
      const y2 = b.top + b.height / 2 - flowBox.top;
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      const mid = (x1 + x2) / 2;
      path.setAttribute("d", `M ${x1} ${y1} C ${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}`);
      svg.appendChild(path);
    }
  }

  function fits(slideInner, content) {
    return content.scrollHeight <= slideInner.clientHeight + 0.5
      && content.scrollWidth <= slideInner.clientWidth + 0.5;
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
      // Keep layout box so scale does not spill into the next slide.
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
