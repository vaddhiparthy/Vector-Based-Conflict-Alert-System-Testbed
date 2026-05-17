(() => {
  const NM_IN_M = 1852.0;
  const MAX_TRAIL = 45;
  const APP_PREFIX = window.location.pathname.startsWith("/vcas-demo/") ? "/vcas-demo" : "";
  const apiUrl = (path) => `${APP_PREFIX}${path}`;

  const statusBar = document.getElementById("statusBar");
  const tokenHint = document.getElementById("tokenHint");
  const tokenCard = document.getElementById("tokenCard");
  const tokenName = document.getElementById("tokenName");
  const tokenExamples = document.getElementById("tokenExamples");

  const scenarioInput = document.getElementById("scenarioInput");
  const modeSelect = document.getElementById("modeSelect");
  const refreshMs = document.getElementById("refreshMs");
  const maxHistoryInput = document.getElementById("maxHistory");
  const rangeNm = document.getElementById("rangeNm");
  const runReplayBtn = document.getElementById("runReplayBtn");
  const connectLiveBtn = document.getElementById("connectLiveBtn");
  const pauseBtn = document.getElementById("pauseBtn");
  const frameSlider = document.getElementById("frameSlider");
  const frameLabel = document.getElementById("frameLabel");
  const frameInfo = document.getElementById("frameInfo");
  const saveShotBtn = document.getElementById("saveShotBtn");
  const saveShotStatus = document.getElementById("saveShotStatus");
  const genBtn = document.getElementById("genBtn");
  const genSeed = document.getElementById("genSeed");
  const genBgCount = document.getElementById("genBgCount");
  const genDuration = document.getElementById("genDuration");
  const genStatus = document.getElementById("genStatus");
  const eventsPanel = document.getElementById("events");
  const canvas = document.getElementById("radarCanvas");
  const ctx = canvas.getContext("2d");

  const kpiAircraft = document.getElementById("kpiAircraft");
  const kpiAlerts = document.getElementById("kpiAlerts");
  const kpiPairCount = document.getElementById("kpiPairCount");
  const kpiMode = document.getElementById("kpiMode");

  let appConfig = {
    display: { default_range_nm: 8, default_refresh_ms: 120 },
    tokens: {
      cesium_env_name: "VCAS_CESIUM_TOKEN",
      opensky_username_env_name: "VCAS_OPENSKY_USERNAME",
      opensky_password_env_name: "VCAS_OPENSKY_PASSWORD",
      telegram_env_name: "TELEGRAM_BOT_TOKEN",
      openweather_env_name: "OPENWEATHER_API_KEY",
    },
    cesium_token: "",
    aerodrome: { lat: 38.944, lon: -77.455, alt_m: 100 },
  };
  const state = {
    snapshots: [],
    frameIndex: 0,
    replayPlaying: false,
    replayTimer: null,
    liveSocket: null,
    trails: new Map(),
    liveMode: false,
    latestAlerts: [],
    // Replay alert accumulation: avoid O(n^2) rescans that can freeze the UI.
    replayAlerts: [],
    replayAlertsBuiltUntil: -1,
  };

  const setStatus = (message, muted = false) => {
    statusBar.textContent = message;
    statusBar.style.color = muted ? "#93a4b8" : "#e2e8f0";
  };

  const resizeCanvas = () => {
    const ratio = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = Math.max(1, Math.floor(rect.width * ratio));
    canvas.height = Math.max(1, Math.floor(rect.height * ratio));
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    if (state.snapshots.length) {
      const frame = state.liveMode ? state.snapshots[state.frameIndex] : state.snapshots[state.frameIndex];
      if (frame) {
        renderSnapshot(frame);
      }
    }
  };

  const stopReplay = () => {
    if (state.replayTimer !== null) {
      clearInterval(state.replayTimer);
      state.replayTimer = null;
    }
    state.replayPlaying = false;
  };

  const stopLive = () => {
    if (state.liveSocket && state.liveSocket.readyState === WebSocket.OPEN) {
      state.liveSocket.close();
    }
    state.liveSocket = null;
    state.liveMode = false;
    connectLiveBtn.textContent = "Connect live websocket";
    if (runReplayBtn) {
      runReplayBtn.disabled = false;
      runReplayBtn.title = "";
    }
  };

  const showTokenInfo = () => {
    const hasToken = Boolean(appConfig.cesium_token && appConfig.cesium_token.trim());
    const tokenLabel = hasToken ? "connected from env" : "not set";
    tokenHint.textContent = hasToken
      ? "Environment token loaded."
      : "Token not set. Radar demo runs without it.";
    tokenCard.innerHTML = `Cesium token status: <strong>${tokenLabel}</strong>`;
    tokenName.textContent = appConfig.tokens.cesium_env_name;
    tokenExamples.textContent = [
      appConfig.tokens.cesium_env_name,
      appConfig.tokens.opensky_username_env_name,
      appConfig.tokens.opensky_password_env_name,
      appConfig.tokens.telegram_env_name,
      appConfig.tokens.openweather_env_name,
    ]
      .map((name) => `${name}=...`)
      .join(", ");
  };

  const refreshTokenUI = () => showTokenInfo();

  const toScreen = (east, north, rangeNm, width, height) => {
    const rangeMeters = Math.max(0.5, rangeNm * NM_IN_M);
    const cx = width / 2;
    const cy = height / 2;
    const p = Math.min(cx, cy) * 0.88;
    const x = cx + (east / rangeMeters) * p;
    const y = cy - (north / rangeMeters) * p;
    return { x, y, inside: Math.hypot(east, north) <= rangeMeters };
  };

  const drawGrid = (ctx2d, width, height, rangeNm) => {
    const cx = width / 2;
    const cy = height / 2;
    const radius = Math.min(cx, cy) * 0.88;

    ctx2d.strokeStyle = "#263247";
    ctx2d.lineWidth = 1;
    ctx2d.fillStyle = "#93a4b8";
    ctx2d.beginPath();
    ctx2d.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx2d.stroke();

    [0.25, 0.5, 0.75, 1].forEach((factor, idx) => {
      const r = radius * factor;
      ctx2d.beginPath();
      ctx2d.arc(cx, cy, r, 0, Math.PI * 2);
      ctx2d.stroke();
      const nm = Math.round(factor * rangeNm);
      ctx2d.fillText(`${nm}nm`, cx + 4, cy - r + 14 - (idx === 3 ? 2 : 0));
    });

    ctx2d.beginPath();
    ctx2d.moveTo(cx - radius, cy);
    ctx2d.lineTo(cx + radius, cy);
    ctx2d.moveTo(cx, cy - radius);
    ctx2d.lineTo(cx, cy + radius);
    ctx2d.stroke();

    const labels = [
      ["N", 0, -radius - 8],
      ["E", radius - 8, 4],
      ["S", 0, radius + 12],
      ["W", -radius - 14, 4],
    ];
    ctx2d.fillStyle = "#94a3b8";
    labels.forEach(([label, dx, dy]) => {
      const x = cx + dx;
      const y = cy + dy;
      if (label === "N") {
        ctx2d.fillText(label, x - 2, y + 10);
      } else if (label === "S") {
        ctx2d.fillText(label, x - 2, y + 10);
      } else if (label === "W") {
        ctx2d.fillText(label, x - 2, y + 10);
      } else {
        ctx2d.fillText(label, x + 2, y);
      }
    });
  };

  const altitudeColor = (altM) => {
    if (altM < 900) return "#4ade80";
    if (altM < 2000) return "#f59e0b";
    return "#f87171";
  };

  const formatAlt = (altM) => {
    const m = Number(altM);
    if (!Number.isFinite(m)) return "ALT ?";
    const ft = Math.round(m * 3.28084);
    return `ALT ${ft}ft`;
  };

  const pairKey = (a, b) => [a, b].sort().join("|");

  const parseAlertPairs = (alertList) => {
    const pairs = new Map();
    (alertList || []).forEach((item) => {
      const pair = Array.isArray(item.pair) && item.pair.length === 2 ? item.pair : [];
      if (pair.length === 2) {
        pairs.set(pairKey(pair[0], pair[1]), {
          key: pairKey(pair[0], pair[1]),
          risk: Number(item.risk_total ?? 0),
          bucket: item.bucket || "medium",
          pair: [...pair].sort(),
        });
      }
    });
    return pairs;
  };

  const renderAlertsPanel = (alertsNewestFirst) => {
    const latest = Array.isArray(alertsNewestFirst) ? alertsNewestFirst.slice(0, 30) : [];
    state.latestAlerts = latest;

    eventsPanel.textContent = "";
    latest.forEach((alert) => {
      const line = document.createElement("div");
      line.className = "event";
      const bucket = (alert.bucket || "medium").toLowerCase();
      const riskText = typeof alert.risk_total === "number" ? ` • risk ${(alert.risk_total * 100).toFixed(0)}%` : "";
      const frameText = alert.frame_index != null ? `frame ${alert.frame_index}` : "";
      const pair = Array.isArray(alert.pair) ? alert.pair.join(" ↔ ") : "unknown pair";
      const created = alert.created_utc ? new Date(alert.created_utc).toLocaleTimeString() : "";
      line.innerHTML = `<span class="badge ${bucket}">${bucket}</span><strong>${frameText}</strong> ${pair}${riskText} <span class="small">${created}</span>`;
      eventsPanel.appendChild(line);
    });

    kpiAlerts.textContent = String(latest.length);
    kpiPairCount.textContent = String(new Set(latest.map((item) => pairKey(item.pair?.[0], item.pair?.[1]))).size);
  };

  const rebuildReplayAlertsUpTo = (frameIndex) => {
    const target = Math.min(Math.max(0, frameIndex), state.snapshots.length - 1);
    if (target < state.replayAlertsBuiltUntil) {
      state.replayAlerts = [];
      state.replayAlertsBuiltUntil = -1;
    }

    for (let i = state.replayAlertsBuiltUntil + 1; i <= target; i += 1) {
      const frame = state.snapshots[i];
      const additions = frame && frame.new_alerts ? frame.new_alerts : [];
      additions.forEach((item) => {
        state.replayAlerts.push({ ...item, frame_index: i });
      });
    }
    state.replayAlertsBuiltUntil = target;

    // Show newest first (frame order is deterministic for replay).
    renderAlertsPanel(state.replayAlerts.slice(-30).reverse());
  };

  const renderSnapshot = (snapshot) => {
    if (!snapshot) {
      frameInfo.textContent = "No frame to render.";
      return;
    }
    const currentRange = Number(rangeNm.value || 8);
    const aircraft = snapshot.aircraft || [];
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;

    ctx.clearRect(0, 0, width, height);
    drawGrid(ctx, width, height, currentRange);

    const index = snapshot.frame_index != null ? Number(snapshot.frame_index) : state.frameIndex;
    if (!state.liveMode) {
      rebuildReplayAlertsUpTo(index);
    }

    const activePairs = parseAlertPairs(state.latestAlerts);

    const pointsByCallsign = new Map();
    aircraft.forEach((aircraftItem) => {
      const posArr = Array.isArray(aircraftItem.position)
        ? aircraftItem.position
        : Array.isArray(aircraftItem.position_m)
          ? aircraftItem.position_m
          : null;
      if (!posArr || posArr.length < 2) {
        return;
      }
      const [eastM, northM, upM] = posArr;
      const point = toScreen(eastM, northM, currentRange, width, height);
      pointsByCallsign.set(aircraftItem.callsign, point);
      const trail = state.trails.get(aircraftItem.callsign) || [];
      trail.push(point);
      while (trail.length > MAX_TRAIL) trail.shift();
      state.trails.set(aircraftItem.callsign, trail);

      ctx.strokeStyle = "rgba(96, 165, 250, 0.35)";
      ctx.lineWidth = 1.2;
      if (trail.length > 1) {
        ctx.beginPath();
        trail.forEach((pt, idx2) => {
          if (idx2 === 0) ctx.moveTo(pt.x, pt.y);
          else ctx.lineTo(pt.x, pt.y);
        });
        ctx.stroke();
      }
    });

    aircraft.forEach((aircraftItem) => {
      const posArr = Array.isArray(aircraftItem.position)
        ? aircraftItem.position
        : Array.isArray(aircraftItem.position_m)
          ? aircraftItem.position_m
          : [];
      const [eastM, northM] = posArr || [];
      if (!Number.isFinite(eastM) || !Number.isFinite(northM)) {
        return;
      }
      const point = toScreen(eastM, northM, currentRange, width, height);
      if (!point.inside) return;

      const color = altitudeColor(aircraftItem.alt_m || 0);
      const call = aircraftItem.callsign || "N/A";
      const altLabel = formatAlt(aircraftItem.alt_m || 0);

      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(point.x, point.y, 4.6, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = "rgba(226, 232, 240, 0.95)";
      ctx.lineWidth = 1;
      ctx.strokeText(call, point.x + 6, point.y - 2);
      ctx.strokeStyle = "rgba(148, 163, 184, 0.95)";
      ctx.lineWidth = 1;
      ctx.strokeText(altLabel, point.x + 6, point.y + 12);

      const velocity = Array.isArray(aircraftItem.velocity)
        ? aircraftItem.velocity
        : Array.isArray(aircraftItem.velocity_mps)
          ? aircraftItem.velocity_mps
          : [0, 0];
      const vx = velocity[0] || 0;
      const vy = velocity[1] || 0;
      const speed = Math.sqrt(vx * vx + vy * vy);
      if (speed > 1e-6) {
        ctx.strokeStyle = color;
        ctx.beginPath();
        ctx.moveTo(point.x, point.y);
        const scale = Math.min(30, speed * 0.4);
        const v = toScreen(eastM + vx * scale, northM + vy * scale, currentRange, width, height);
        ctx.lineTo(v.x, v.y);
        ctx.stroke();
      }
    });

    activePairs.forEach((entry) => {
      const [a, b] = entry.pair;
      if (!pointsByCallsign.has(a) || !pointsByCallsign.has(b)) {
        return;
      }
      const pA = pointsByCallsign.get(a);
      const pB = pointsByCallsign.get(b);
      const stroke = entry.bucket === "high" ? "#f87171" : entry.bucket === "medium" ? "#f59e0b" : "#4ade80";
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 1.6;
      ctx.beginPath();
      ctx.moveTo(pA.x, pA.y);
      ctx.lineTo(pB.x, pB.y);
      ctx.stroke();

      // Moving highlight rings that follow the aircraft.
      ctx.lineWidth = 2.0;
      ctx.globalAlpha = 0.9;
      [pA, pB].forEach((pt) => {
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, 18, 0, Math.PI * 2);
        ctx.stroke();
        ctx.globalAlpha = 0.45;
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, 28, 0, Math.PI * 2);
        ctx.stroke();
        ctx.globalAlpha = 0.9;
      });
      ctx.globalAlpha = 1.0;
      ctx.lineWidth = 1.6;
      ctx.strokeStyle = stroke;
      ctx.fillStyle = "#f9fafb";
      const mid = {
        x: (pA.x + pB.x) / 2,
        y: (pA.y + pB.y) / 2,
      };
      ctx.fillText(entry.bucket.toUpperCase(), mid.x + 3, mid.y - 2);
    });

    const safeInfo = [];
    if (Array.isArray(aircraft)) {
      safeInfo.push(`aircraft ${aircraft.length}`);
    }
    if (snapshot.timestamp_utc) {
      safeInfo.push(`time ${snapshot.timestamp_utc}`);
    }
    if (snapshot.frame_index != null) {
      safeInfo.push(`frame ${snapshot.frame_index}`);
    }
    if (snapshot.candidate_pairs != null) {
      safeInfo.push(`pairs ${snapshot.candidate_pairs}`);
    }
    if (snapshot.total_alerts != null) {
      safeInfo.push(`alerts_so_far ${snapshot.total_alerts}`);
    }
    frameInfo.textContent = `${safeInfo.join(" • ")}`;
    kpiAircraft.textContent = String(aircraft.length);
    kpiMode.textContent = state.liveMode ? "live ws" : "replay";
  };

  async function saveScreenshot() {
    if (!saveShotBtn) return;
    saveShotBtn.disabled = true;
    if (saveShotStatus) saveShotStatus.textContent = "Saving...";
    try {
      const canvas = document.getElementById("radarCanvas");
      if (!canvas) throw new Error("Canvas not found");
      const dataUrl = canvas.toDataURL("image/png");
      const resp = await fetch(apiUrl("/api/save-screenshot"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: "radar", png_base64: dataUrl }),
      });
      if (!resp.ok) throw new Error(`save failed: ${resp.status}`);
      const payload = await resp.json();
      if (saveShotStatus) saveShotStatus.textContent = `Saved: ${payload.saved_to}`;
    } catch (e) {
      if (saveShotStatus) saveShotStatus.textContent = String(e && e.message ? e.message : e);
    } finally {
      saveShotBtn.disabled = false;
    }
  }

  if (saveShotBtn) {
    saveShotBtn.addEventListener("click", () => void saveScreenshot());
  }

  const generateScenario = async () => {
    if (!genBtn) return;
    genBtn.disabled = true;
    if (genStatus) genStatus.textContent = "Generating…";
    try {
      const seedRaw = (genSeed && genSeed.value ? genSeed.value.trim() : "") || "";
      const body = {
        seed: seedRaw ? Number(seedRaw) : null,
        bg_count: Number(genBgCount && genBgCount.value ? genBgCount.value : 18),
        duration_s: Number(genDuration && genDuration.value ? genDuration.value : 600),
        dt_s: 1.0,
      };
      const resp = await fetch(apiUrl("/api/generate-scenario"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.ok) throw new Error(`generate failed: ${resp.status}`);
      const payload = await resp.json();
      if (payload && payload.scenario_path) {
        scenarioInput.value = payload.scenario_path;
      }
      if (genSeed && payload && payload.seed != null) {
        genSeed.value = String(payload.seed);
      }
      if (genStatus) {
        genStatus.textContent = `Generated: ${payload.scenario_path} (seed=${payload.seed})`;
      }
      // Auto-run after generating.
      await runReplay();
    } catch (e) {
      if (genStatus) genStatus.textContent = String(e && e.message ? e.message : e);
    } finally {
      genBtn.disabled = false;
    }
  };

  if (genBtn) {
    genBtn.addEventListener("click", () => void generateScenario());
  }

  const normalizeSnapshot = (payload, fromReplay = false) => {
    if (payload.type === "snapshot") {
      const rawAircraft = Array.isArray(payload.aircraft) ? payload.aircraft : [];
      const aircraft = rawAircraft.map((item) => {
        const position = Array.isArray(item.position)
          ? item.position
          : Array.isArray(item.position_m)
            ? item.position_m
            : null;
        const velocity = Array.isArray(item.velocity)
          ? item.velocity
          : Array.isArray(item.velocity_mps)
            ? item.velocity_mps
            : null;
        return { ...item, position, velocity };
      });
      return {
        frame_index: Number(state.frameIndex),
        timestamp_utc: payload.timestamp_utc || new Date().toISOString(),
        candidate_pairs: null,
        aircraft_count: aircraft.length,
        aircraft,
        new_alerts: fromReplay ? (payload.new_alerts || []) : (payload.alerts || []).map((item) => ({
          ...item,
          frame_index: state.frameIndex,
        })),
        total_alerts: fromReplay ? payload.total_alerts || 0 : Array.isArray(payload.alerts) ? payload.alerts.length : 0,
      };
    }
    return payload;
  };

  const renderFrameIndex = (index) => {
    if (!state.snapshots.length) {
      frameLabel.textContent = "No frames";
      return;
    }
    state.frameIndex = Math.max(0, Math.min(index, state.snapshots.length - 1));
    const frame = state.snapshots[state.frameIndex];
    frameSlider.value = String(state.frameIndex);
    frameLabel.textContent = `Frame ${state.frameIndex + 1} / ${state.snapshots.length}`;
    const modeLabel = state.liveMode ? `live frame ${state.frameIndex}` : "replay";
    frameInfo.textContent = `mode ${modeLabel}`;
    renderSnapshot(frame);
  };

  const runReplay = async () => {
    stopReplay();
    if (state.liveSocket && state.liveSocket.readyState === WebSocket.OPEN) {
      setStatus("Live websocket is connected. Disconnect live websocket before running a scenario replay.");
      return;
    }
    state.liveMode = false;
    state.trails = new Map();
    setStatus("Running scenario and building radar frames...");
    state.snapshots = [];
    state.frameIndex = 0;
    frameSlider.max = "0";
    frameLabel.textContent = "No frames yet";

    try {
      const scenario = scenarioInput.value || "scenarios/canonical/head_on.yml";
      const mode = modeSelect ? modeSelect.value : "synthetic";
      const maxHistory = Math.max(60, Number(maxHistoryInput?.value || 360));
      const url =
        mode === "simulator"
          ? apiUrl(
              `/api/run?source_mode=simulator&scenario=${encodeURIComponent(scenario)}&with_history=true&max_history=${maxHistory}`,
            )
          : apiUrl(
              `/api/run-synthetic?scenario=${encodeURIComponent(scenario)}&with_history=true&max_history=${maxHistory}`,
            );
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`run failed: ${response.status}`);
      }
      const payload = await response.json();
      state.snapshots = (payload.history || []).map((item) => ({
        ...item,
        aircraft: Array.isArray(item.aircraft) ? item.aircraft : [],
      }));
      if (!state.snapshots.length) {
        setStatus("Scenario ran but returned no frames.");
        return;
      }

      frameSlider.max = String(state.snapshots.length - 1);
      frameSlider.value = "0";
      state.frameIndex = 0;
      renderFrameIndex(0);
      const maxCandidates = Math.max(
        0,
        ...state.snapshots.map((snapshot) => Number(snapshot.candidate_pairs || 0)),
      );
      const maxFrameAlerts = Math.max(
        0,
        ...state.snapshots.map((snapshot) => Number((snapshot.new_alerts || []).length || 0)),
      );
      const totalAlerts = state.snapshots.reduce(
        (total, snapshot) => total + Number(snapshot.new_alerts?.length || 0),
        0,
      );
      if (maxCandidates === 0) {
        setStatus(
          "Loaded. No candidate pairs reached Thread-1 screening threshold. Use the default head_on scenario or increase VCAS_THREAD1_T_TC_S.",
        );
      } else if (maxFrameAlerts === 0) {
        setStatus(`Loaded ${state.snapshots.length} frames. ${maxCandidates} pair candidate(s), no alerts emitted (check risk thresholds).`);
      } else {
        setStatus(
          `Loaded ${state.snapshots.length} frames. Candidate pairs seen: ${maxCandidates}, alerts total: ${totalAlerts}. Animation playing.`,
        );
      }
      runReplayBtn.textContent = "Re-run scenario";
      state.replayPlaying = true;
      const ms = Number(refreshMs.value || appConfig.display.default_refresh_ms);
      state.replayTimer = window.setInterval(() => {
        if (!state.replayPlaying) {
          return;
        }
        const next = (state.frameIndex + 1) % state.snapshots.length;
        renderFrameIndex(next);
      }, ms);
      pauseBtn.textContent = "Pause replay";
    } catch (error) {
      setStatus(`Replay failed: ${error.message}`);
    }
  };

  const connectLive = () => {
    if (state.liveSocket && state.liveSocket.readyState === WebSocket.OPEN) {
      stopLive();
      setStatus("Live websocket disconnected.");
      return;
    }
    stopReplay();
    setStatus("Connecting to websocket...");
    state.liveMode = true;
    if (runReplayBtn) {
      runReplayBtn.disabled = true;
      runReplayBtn.title = "Disconnect live websocket to run a scenario replay.";
    }
    state.trails = new Map();
    state.snapshots = [];
    state.frameIndex = 0;
    renderAlertsPanel([]);
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${proto}://${window.location.host}${APP_PREFIX}/ws/surveillance`;
    const socket = new WebSocket(wsUrl);
    state.liveSocket = socket;
    connectLiveBtn.textContent = "Disconnect live websocket";

    socket.addEventListener("open", () => {
      setStatus("Live websocket connected.");
    });

    socket.addEventListener("close", () => {
      setStatus("Live websocket closed.");
      state.liveMode = false;
      connectLiveBtn.textContent = "Connect live websocket";
      if (runReplayBtn) {
        runReplayBtn.disabled = false;
        runReplayBtn.title = "";
      }
    });

    socket.addEventListener("message", (event) => {
      try {
        const payload = JSON.parse(event.data);
        const snapshot = normalizeSnapshot(payload, false);
        // For live mode the backend sends the full audit history each tick; show the newest 30.
        const allAlerts = Array.isArray(snapshot.new_alerts) ? snapshot.new_alerts : [];
        renderAlertsPanel(allAlerts.slice(-30).reverse());
        state.snapshots = [snapshot];
        renderSnapshot(snapshot);
        state.snapshots = [snapshot];
      } catch (error) {
        // ignore malformed payload
      }
    });
  };

  const loadConfig = async () => {
    try {
      const response = await fetch(apiUrl("/api/client-config"), { cache: "no-store" });
      if (response.ok) {
        appConfig = await response.json();
      }
      refreshTokenUI();
      refreshMs.value = String(appConfig.display.default_refresh_ms);
      rangeNm.value = String(appConfig.display.default_range_nm);
      tokenHint.textContent += ` | Aerodrome: lat ${appConfig.aerodrome.lat.toFixed(
        4,
      )}, lon ${appConfig.aerodrome.lon.toFixed(4)}`;
      setStatus("Ready. Use Run scenario + animate or Connect live websocket.");
    } catch (error) {
      setStatus(`Config load failed: ${error}`, true);
      refreshTokenUI();
    }
  };

  runReplayBtn.addEventListener("click", runReplay);
  connectLiveBtn.addEventListener("click", connectLive);
  frameSlider.addEventListener("input", () => {
    stopReplay();
    state.liveMode = false;
    renderFrameIndex(Number(frameSlider.value));
    pauseBtn.textContent = "Resume replay";
  });
  pauseBtn.addEventListener("click", () => {
    if (!state.snapshots.length || state.liveMode) {
      return;
    }
    state.replayPlaying = !state.replayPlaying;
    if (state.replayPlaying) {
      pauseBtn.textContent = "Pause replay";
      const ms = Number(refreshMs.value || appConfig.display.default_refresh_ms);
      if (!state.replayTimer) {
        state.replayTimer = window.setInterval(() => {
          const next = (state.frameIndex + 1) % state.snapshots.length;
          renderFrameIndex(next);
        }, ms);
      }
      setStatus("Replay resumed.");
    } else {
      stopReplay();
      pauseBtn.textContent = "Resume replay";
      setStatus("Replay paused.");
    }
  });

  window.addEventListener("resize", resizeCanvas);

  loadConfig();
  resizeCanvas();
})();
