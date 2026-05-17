/* Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
 *
 * All rights reserved.
 *
 * Non-commercial use is permitted for review and research only.
 */

/* global Cesium */

const els = {
  scenario: document.getElementById("scenario"),
  run: document.getElementById("run"),
  reset: document.getElementById("reset"),
  save: document.getElementById("save"),
  status: document.getElementById("status"),
  pillToken: document.getElementById("pillToken"),
  pillAircraft: document.getElementById("pillAircraft"),
  pillAlerts: document.getElementById("pillAlerts"),
};

function setPill(pillEl, text, klass) {
  pillEl.classList.remove("ok", "warn", "danger");
  if (klass) pillEl.classList.add(klass);
  pillEl.innerHTML = text;
}

function setStatus(text) {
  els.status.textContent = text;
}

function toColor(bucket) {
  if (bucket === "high") return Cesium.Color.RED.withAlpha(0.9);
  if (bucket === "medium") return Cesium.Color.ORANGE.withAlpha(0.9);
  return Cesium.Color.YELLOW.withAlpha(0.9);
}

function safeNum(x, fallback) {
  const n = Number(x);
  return Number.isFinite(n) ? n : fallback;
}

function formatIso(iso) {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return String(iso);
  }
}

function formatAltM(altM) {
  const m = Number(altM);
  if (!Number.isFinite(m)) return "";
  const ft = Math.round(m * 3.28084);
  return `${ft}ft`;
}

let appConfig = null;
let viewer = null;
let aircraftEntities = new Map();
let lastHistory = null;
let anim = { handle: null, idx: 0, startedAtMs: 0 };
const DEFAULT_AERODROME = { lat: 42.2343889, lon: -85.5515556, alt_m: 100.0 }; // KAZO
const APP_PREFIX = window.location.pathname.startsWith("/vcas-demo/") ? "/vcas-demo" : "";
const apiUrl = (path) => `${APP_PREFIX}${path}`;

function ensureViewer() {
  if (viewer) return viewer;

  const options = {
    animation: false,
    baseLayerPicker: false,
    fullscreenButton: false,
    geocoder: false,
    homeButton: false,
    infoBox: false,
    navigationHelpButton: false,
    sceneModePicker: false,
    selectionIndicator: false,
    timeline: false,
    shouldAnimate: true,
    contextOptions: { webgl: { preserveDrawingBuffer: true } },
  };
  viewer = new Cesium.Viewer("cesiumContainer", options);

  // Default to a "no external imagery" globe until a Cesium ion token is supplied.
  // This avoids violating third-party tile server usage policies (OSM volunteers, etc).
  viewer.imageryLayers.removeAll(true);
  viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString("#0b1220");

  viewer.scene.globe.depthTestAgainstTerrain = false;
  viewer.scene.globe.enableLighting = false;
  return viewer;
}

function resetView() {
  if (!viewer) return;
  // Always snap Reset View to KAZO unless the API is explicitly configured nearby.
  const cfg = appConfig && appConfig.aerodrome ? appConfig.aerodrome : DEFAULT_AERODROME;
  const lat = safeNum(cfg.lat, DEFAULT_AERODROME.lat);
  const lon = safeNum(cfg.lon, DEFAULT_AERODROME.lon);
  const alt_m = safeNum(cfg.alt_m, DEFAULT_AERODROME.alt_m);
  const far =
    Math.abs(lat - DEFAULT_AERODROME.lat) > 1.0 || Math.abs(lon - DEFAULT_AERODROME.lon) > 1.0;
  const targetLat = far ? DEFAULT_AERODROME.lat : lat;
  const targetLon = far ? DEFAULT_AERODROME.lon : lon;
  const targetAlt = far ? DEFAULT_AERODROME.alt_m : alt_m;

  const center = Cesium.Cartesian3.fromDegrees(targetLon, targetLat, Math.max(targetAlt, 50));
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(targetLon, targetLat, 25000),
    orientation: { heading: 0.0, pitch: -1.15, roll: 0.0 },
    duration: 0.8,
  });
  void center; // keep in case we want a tighter local offset later
}

function stopAnimation() {
  if (anim.handle) cancelAnimationFrame(anim.handle);
  anim.handle = null;
  anim.idx = 0;
}

function upsertAircraft(frameAircraft) {
  const v = ensureViewer();
  for (const ac of frameAircraft) {
    const key = `${ac.icao24 || ac.callsign || "ac"}:${ac.callsign || ""}`;
    const lon = safeNum(ac.lon, null);
    const lat = safeNum(ac.lat, null);
    const alt = safeNum(ac.alt_m, 0);
    if (lon === null || lat === null) continue;

    const pos = Cesium.Cartesian3.fromDegrees(lon, lat, alt);
    let entity = aircraftEntities.get(key);
    if (!entity) {
      entity = v.entities.add({
        id: key,
        name: ac.callsign || ac.icao24 || key,
        position: pos,
        point: {
          pixelSize: 7,
          color: Cesium.Color.CYAN.withAlpha(0.92),
          outlineColor: Cesium.Color.BLACK.withAlpha(0.6),
          outlineWidth: 1,
          heightReference: Cesium.HeightReference.NONE,
        },
        label: {
          text: `${ac.callsign || ac.icao24 || ""} ${formatAltM(alt)}`.trim(),
          font: "12px sans-serif",
          fillColor: Cesium.Color.WHITE.withAlpha(0.9),
          outlineColor: Cesium.Color.BLACK.withAlpha(0.75),
          outlineWidth: 3,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          pixelOffset: new Cesium.Cartesian2(10, -12),
          showBackground: true,
          backgroundColor: Cesium.Color.BLACK.withAlpha(0.35),
          horizontalOrigin: Cesium.HorizontalOrigin.LEFT,
          distanceDisplayCondition: new Cesium.DistanceDisplayCondition(
            0.0,
            250000.0,
          ),
        },
      });
      aircraftEntities.set(key, entity);
    } else {
      entity.position = pos;
      if (entity.label && typeof entity.label.text !== "undefined") {
        entity.label.text = `${ac.callsign || ac.icao24 || ""} ${formatAltM(alt)}`.trim();
      }
    }
  }
}

function drawAlertRings(alerts) {
  const v = ensureViewer();
  // Remove previous rings.
  const toRemove = [];
  v.entities.values.forEach((e) => {
    if (String(e.id || "").startsWith("alert-ring:")) toRemove.push(e);
  });
  toRemove.forEach((e) => v.entities.remove(e));

  if (!alerts || !Array.isArray(alerts)) return;
  // Use the latest alert per pair to avoid clutter.
  const seen = new Set();
  for (let i = alerts.length - 1; i >= 0; i -= 1) {
    const a = alerts[i];
    const pair = Array.isArray(a.pair) ? a.pair.join("|") : String(a.alert_id);
    if (seen.has(pair)) continue;
    seen.add(pair);

    // We don't have precise CPA coords without extra computation; draw rings at current aircraft positions.
    const cs0 = Array.isArray(a.pair) ? a.pair[0] : null;
    const cs1 = Array.isArray(a.pair) ? a.pair[1] : null;
    const ac0 = cs0 ? [...aircraftEntities.values()].find((e) => e.name === cs0) : null;
    const ac1 = cs1 ? [...aircraftEntities.values()].find((e) => e.name === cs1) : null;
    const color = toColor(a.bucket);
    const radius = Math.max(250, safeNum(a.d_min_m, 0) * 2.0);

    for (const target of [ac0, ac1]) {
      if (!target || !target.position) continue;
      const targetId = String(target.id || "");
      const posCb = new Cesium.CallbackProperty(() => {
        const live = viewer && aircraftEntities.get(targetId);
        const prop = live ? live.position : null;
        if (!prop) return undefined;
        if (typeof prop.getValue === "function") return prop.getValue(viewer.clock.currentTime);
        return prop;
      }, false);
      const heightCb = new Cesium.CallbackProperty(() => {
        const live = viewer && aircraftEntities.get(targetId);
        const prop = live ? live.position : null;
        if (!prop) return 0;
        const pos = typeof prop.getValue === "function" ? prop.getValue(viewer.clock.currentTime) : prop;
        if (!pos) return 0;
        try {
          const carto = Cesium.Cartographic.fromCartesian(pos);
          return safeNum(carto.height, 0);
        } catch {
          return 0;
        }
      }, false);
      v.entities.add({
        id: `alert-ring:${pair}:${target.id}`,
        position: posCb,
        ellipse: {
          semiMajorAxis: radius,
          semiMinorAxis: radius,
          material: color.withAlpha(0.18),
          outline: true,
          outlineColor: color.withAlpha(0.75),
          heightReference: Cesium.HeightReference.NONE,
          height: heightCb,
        },
      });
    }
  }
}

function renderFrame(historyItem, allAlerts) {
  if (!historyItem) return;
  upsertAircraft(historyItem.aircraft || []);

  const totalAlerts = safeNum(historyItem.total_alerts, 0);
  const aircraftCount = safeNum(historyItem.aircraft_count, 0);
  setPill(els.pillAircraft, `Aircraft: <strong>${aircraftCount}</strong>`, aircraftCount > 0 ? "ok" : "warn");
  setPill(
    els.pillAlerts,
    `Alerts: <strong>${totalAlerts}</strong>`,
    totalAlerts > 0 ? "danger" : "ok",
  );

  const ts = historyItem.timestamp_utc ? formatIso(historyItem.timestamp_utc) : "n/a";
  setStatus(`Frame ${historyItem.frame_index} @ ${ts}`);

  drawAlertRings(allAlerts || []);
}

function startHistoryAnimation(history, allAlerts) {
  stopAnimation();
  if (!Array.isArray(history) || history.length === 0) {
    setStatus("No history returned for scenario.");
    return;
  }
  lastHistory = { history, allAlerts };
  anim.idx = 0;
  anim.startedAtMs = performance.now();

  const tick = (now) => {
    const elapsed = now - anim.startedAtMs;
    // Run at ~10 fps, mapping time to frame index.
    const fps = 10;
    const nextIdx = Math.min(history.length - 1, Math.floor((elapsed / 1000) * fps));
    if (nextIdx !== anim.idx) anim.idx = nextIdx;
    renderFrame(history[anim.idx], allAlerts);
    if (anim.idx >= history.length - 1) {
      anim.handle = null;
      return;
    }
    anim.handle = requestAnimationFrame(tick);
  };
  anim.handle = requestAnimationFrame(tick);
}

async function loadClientConfig() {
  const resp = await fetch(apiUrl("/api/client-config"), { cache: "no-store" });
  if (!resp.ok) throw new Error(`client-config failed: ${resp.status}`);
  appConfig = await resp.json();

  const token = (appConfig.cesium_token || "").trim();
  if (token) {
    Cesium.Ion.defaultAccessToken = token;
    // If a token is present, add a proper imagery layer through Cesium ion defaults.
    // This keeps map usage within Cesium's intended distribution path.
    try {
      const v = ensureViewer();
      v.imageryLayers.removeAll(true);
      const imagery = await Cesium.createWorldImageryAsync();
      v.imageryLayers.addImageryProvider(imagery);
    } catch {
      // Keep no-imagery fallback if Cesium ion imagery fails.
    }
    setPill(els.pillToken, `Cesium token: <strong>loaded</strong>`, "ok");
  } else {
    setPill(els.pillToken, `Cesium token: <strong>not set</strong>`, "warn");
  }

  ensureViewer();
  resetView();
  setStatus("Ready. Click Run Scenario + Animate.");
}

async function runScenario() {
  const scenario = els.scenario.value;
  const isSimulator = scenario.includes("scenarios/bluesky/");
  const sourceMode = isSimulator ? "simulator" : "synthetic";
  setStatus(`Running ${sourceMode} scenario: ${scenario} …`);
  const url = apiUrl(`/api/run?source_mode=${encodeURIComponent(sourceMode)}&scenario=${encodeURIComponent(
    scenario,
  )}&with_history=true`);
  const resp = await fetch(url, { cache: "no-store" });
  if (!resp.ok) throw new Error(`run failed: ${resp.status}`);
  const payload = await resp.json();
  const history = payload.history || [];
  const alerts = payload.alerts || [];
  startHistoryAnimation(history, alerts);
}

async function saveScreenshot() {
  const v = ensureViewer();
  if (!v || !v.canvas) throw new Error("Viewer not ready");
  if (els.save) els.save.disabled = true;
  setStatus("Saving screenshot…");
  try {
    // Force a render so the drawing buffer has the latest frame.
    v.render();
    const dataUrl = v.canvas.toDataURL("image/png");
    const resp = await fetch(apiUrl("/api/save-screenshot"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "globe", png_base64: dataUrl }),
    });
    if (!resp.ok) throw new Error(`save failed: ${resp.status}`);
    const payload = await resp.json();
    setStatus(`Saved: ${payload.saved_to}`);
  } finally {
    if (els.save) els.save.disabled = false;
  }
}

els.run.addEventListener("click", () => {
  runScenario().catch((e) => {
    setStatus(String(e && e.message ? e.message : e));
  });
});
els.reset.addEventListener("click", () => resetView());
if (els.save) {
  els.save.addEventListener("click", () => {
    saveScreenshot().catch((e) => {
      setStatus(String(e && e.message ? e.message : e));
    });
  });
}

loadClientConfig().catch((e) => {
  setStatus(String(e && e.message ? e.message : e));
});
