// Turns every `div.osm-map` that the `osm_map` component emits into an
// OpenStreetMap embed. Until this runs the container holds only a plain
// link, so a browser without JavaScript -- or one that cannot reach the
// OSM API -- keeps that link and nothing else changes.
(() => {
  if (globalThis.osmMap) return;

  const API = "https://www.openstreetmap.org/api/0.6/node/";
  const EMBED = "https://www.openstreetmap.org/export/embed.html";
  const LAYERS = ["mapnik", "cyclosm", "cyclemap", "transportmap", "hot", "shortbread"];

  // The embed takes a bounding box, not a zoom, and fits it to the iframe
  // with MapLibre's `fitBounds`. Because that fit happens in Web Mercator,
  // the latitude half-span carries a cos(lat) factor; without it the map
  // zooms out by log2(1/cos(lat)) -- almost half a level in Toronto.
  const bbox = (lat, lon, zoom, width, height) => {
    const degPerPx = 360 / (256 * 2 ** zoom);
    const halfLon = (width * degPerPx) / 2;
    const halfLat = (height * degPerPx * Math.cos((lat * Math.PI) / 180)) / 2;
    return [lon - halfLon, lat - halfLat, lon + halfLon, lat + halfLat]
      .map((degrees) => degrees.toFixed(7))
      .join(",");
  };

  // The name comes from OSM, where anyone can edit it, so it goes in
  // through `textContent` and never through `innerHTML`.
  const render = (el, lat, lon, zoom, name, nodeId) => {
    const width = Number(el.dataset.width);
    const height = Number(el.dataset.height);
    const layer = LAYERS.includes(el.dataset.layer) ? el.dataset.layer : "mapnik";

    const frame = document.createElement("iframe");
    frame.src = `${EMBED}?bbox=${bbox(lat, lon, zoom, width, height)}&layer=${layer}&marker=${lat},${lon}`;
    frame.width = width;
    frame.height = height;
    frame.title = name || "OpenStreetMap map";
    frame.loading = "lazy";
    frame.style.border = "1px solid var(--text-color)";
    frame.style.maxWidth = "100%";

    const link = el.querySelector("a");
    if (nodeId) link.href = `https://www.openstreetmap.org/node/${nodeId}#map=${zoom}/${lat}/${lon}`;
    if (name) link.textContent = name;

    el.insertBefore(document.createElement("br"), el.firstChild);
    el.insertBefore(frame, el.firstChild);
  };

  // A node id gives us the place's own coordinates and its name, which the
  // pasted `#map=` fragment cannot: that fragment is wherever the viewport
  // happened to be. Any failure leaves the fallback link untouched.
  const upgrade = async (el) => {
    const zoom = Number(el.dataset.zoom);
    const nodeId = el.dataset.node;
    let lat = Number(el.dataset.lat);
    let lon = Number(el.dataset.lon);
    let name = el.dataset.name;

    if (nodeId) {
      try {
        const response = await fetch(API + encodeURIComponent(nodeId), { credentials: "omit" });
        if (!response.ok) throw new Error(`OSM API answered ${response.status}`);
        const doc = new DOMParser().parseFromString(await response.text(), "application/xml");
        if (doc.querySelector("parsererror")) throw new Error("OSM API sent malformed XML");
        const node = doc.querySelector("node");
        if (!node) throw new Error("no node in the OSM API response");
        lat = Number(node.getAttribute("lat"));
        lon = Number(node.getAttribute("lon"));
        if (!name) name = doc.querySelector('tag[k="name"]')?.getAttribute("v") ?? "";
      } catch {
        return;
      }
    }

    render(el, lat, lon, zoom, name, nodeId);
  };

  globalThis.osmMap = { bbox, render, upgrade };

  if (typeof document !== "undefined") {
    const start = () => document.querySelectorAll("div.osm-map").forEach(upgrade);
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", start);
    } else {
      start();
    }
  }
})();
