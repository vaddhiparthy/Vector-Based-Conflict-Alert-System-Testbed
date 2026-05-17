(() => {
  const connectBtn = document.getElementById("connectBtn");
  const runBtn = document.getElementById("runBtn");
  const status = document.getElementById("status");
  const runStatus = document.getElementById("runStatus");
  const scenarioInput = document.getElementById("scenarioInput");
  const historyToggle = document.getElementById("historyToggle");
  const historyControls = document.getElementById("historyControls");
  const historySlider = document.getElementById("historySlider");
  const historyIndex = document.getElementById("historyIndex");
  const aircraftDiv = document.getElementById("aircraft");
  const alertsDiv = document.getElementById("alerts");
  const frameSummary = document.getElementById("frameSummary");

  let socket = null;
  let runHistory = [];
  let latestRunSnapshots = [];

  const renderSnapshot = (snapshot) => {
    aircraftDiv.textContent = JSON.stringify(snapshot.aircraft || [], null, 2);
    alertsDiv.textContent = JSON.stringify(snapshot.new_alerts || [], null, 2);
    frameSummary.textContent = `frame ${snapshot.frame_index} — time ${snapshot.timestamp_utc} • candidates ${snapshot.candidate_pairs} • aircraft ${snapshot.aircraft_count} • total alerts ${snapshot.total_alerts}`;
  };

  const renderLatest = (payload) => {
    aircraftDiv.textContent = JSON.stringify(payload.aircraft || [], null, 2);
    alertsDiv.textContent = JSON.stringify(payload.alerts || [], null, 2);
    frameSummary.textContent = "live stream";
  };

  runBtn.addEventListener("click", async () => {
    runStatus.textContent = "running...";
    try {
      const scenario = scenarioInput.value || "scenarios/canonical/head_on.yml";
      const history = historyToggle.checked ? "&with_history=true" : "";
      const response = await fetch(
        `/api/run-synthetic?scenario=${encodeURIComponent(scenario)}${history}`,
      );
      const payload = await response.json();
      runHistory = payload.history || [];
      latestRunSnapshots = runHistory;
      if (!runHistory.length) {
        alertsDiv.textContent = JSON.stringify(payload.alerts || [], null, 2);
        frameSummary.textContent = `total alerts: ${payload.alert_count || 0}`;
        historyControls.style.display = "none";
      } else {
        historyControls.style.display = "block";
        historySlider.max = String(Math.max(0, runHistory.length - 1));
        historySlider.value = String(runHistory.length - 1);
        renderSnapshot(runHistory[runHistory.length - 1]);
      }
      runStatus.textContent = `done (${payload.alert_count || 0} alerts)`;
    } catch (error) {
      runStatus.textContent = `failed: ${error}`;
    }
  });

  historySlider.addEventListener("input", () => {
    if (!latestRunSnapshots.length) {
      return;
    }
    const index = Number(historySlider.value);
    historyIndex.textContent = String(index);
    renderSnapshot(latestRunSnapshots[index]);
  });

  connectBtn.addEventListener("click", () => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.close();
      socket = null;
      status.textContent = "disconnected";
      return;
    }
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${proto}://${window.location.hostname}:8000/ws/surveillance`;
    socket = new WebSocket(wsUrl);
    status.textContent = "connecting";
    socket.addEventListener("open", () => {
      status.textContent = "connected";
      connectBtn.textContent = "Disconnect";
    });
    socket.addEventListener("close", () => {
      status.textContent = "disconnected";
      connectBtn.textContent = "Connect";
      socket = null;
    });
    socket.addEventListener("message", (evt) => {
      try {
        const payload = JSON.parse(evt.data);
        if (payload.type === "snapshot") {
          renderLatest(payload);
        } else {
          aircraftDiv.textContent = JSON.stringify(payload.aircraft || [], null, 2);
          alertsDiv.textContent = JSON.stringify(payload.alerts || [], null, 2);
          frameSummary.textContent = "no data";
        }
      } catch (error) {
        aircraftDiv.textContent = evt.data;
      }
    });
  });
})();
