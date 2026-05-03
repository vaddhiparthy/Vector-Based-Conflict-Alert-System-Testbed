(async () => {
  const APP_PREFIX = window.location.pathname.startsWith("/vcas-demo/") ? "/vcas-demo" : "";
  const apiUrl = (path) => `${APP_PREFIX}${path}`;

  const status = document.getElementById("status");
  const state = document.getElementById("state");
  const summary = document.getElementById("frameSummary");
  const aircraftDiv = document.getElementById("aircraft");
  const alertsDiv = document.getElementById("alerts");

  const scenarioPath = "scenarios/canonical/head_on.yml";
  const scenarioIntervalMs = 45_000;
  let lastRun = "";

  const render = (payload) => {
    if (payload.aircraft) {
      aircraftDiv.textContent = JSON.stringify(payload.aircraft, null, 2);
    }
    if (payload.alerts) {
      alertsDiv.textContent = JSON.stringify(payload.alerts, null, 2);
    }
    state.textContent = `Connected aircraft: ${(payload.aircraft || []).length}`;
  };

  const runScenarioLoop = async () => {
    try {
      const response = await fetch(
        apiUrl(`/api/run-synthetic?scenario=${encodeURIComponent(scenarioPath)}&with_history=false`),
      );
      const payload = await response.json();
      lastRun = `alerts=${payload.alert_count} risk_mode=${payload.risk_mode}`;
      summary.textContent = `${new Date().toISOString()} • ${lastRun}`;
      alertsDiv.textContent = JSON.stringify(payload.alerts || [], null, 2);
      status.textContent = `last run: ${lastRun}`;
    } catch (error) {
      status.textContent = `run failed: ${error}`;
    }
  };

  const connectSocket = () => {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${proto}://${window.location.host}${APP_PREFIX}/ws/surveillance`;
    const socket = new WebSocket(wsUrl);
    socket.addEventListener("open", () => {
      status.textContent = "websocket connected";
    });
    socket.addEventListener("close", () => {
      status.textContent = "websocket disconnected";
    });
    socket.addEventListener("message", (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === "snapshot") {
          render(payload);
        } else if (Array.isArray(payload.aircraft)) {
          render(payload);
        }
      } catch (error) {
        state.textContent = String(event.data).slice(0, 200);
      }
    });
  };

  const loop = () => {
    void runScenarioLoop();
    window.setTimeout(loop, scenarioIntervalMs);
  };

  status.textContent = "public demo running...";
  connectSocket();
  loop();
})();
(function () {
  const APP_PREFIX = window.location.pathname.startsWith("/vcas-demo/") ? "/vcas-demo" : "";
  const apiUrl = (path) => `${APP_PREFIX}${path}`;
