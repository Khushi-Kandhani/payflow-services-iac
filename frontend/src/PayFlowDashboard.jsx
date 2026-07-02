import { useState, useEffect, useRef, useCallback } from "react";
import { ArrowRight, CircleDot, TrendingUp, Clock3, GitBranch, Server, Zap, Send, WifiOff, RefreshCcw, BellRing } from "lucide-react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const POLL_MS = 2500;

const NODES = [
  { key: "order", label: "Order Service", icon: Server, sub: "FastAPI · Postgres" },
  { key: "payment", label: "Payment Worker", icon: Zap, sub: "Row-lock queue" },
  { key: "notify", label: "Notification", icon: GitBranch, sub: "SQS subscriber" },
];

const statusStyle = {
  PENDING: { color: "var(--pf-gold)", label: "PENDING", dot: "var(--pf-gold)", pulse: true },
  SUCCESS: { color: "var(--pf-teal)", label: "SUCCESS", dot: "var(--pf-teal)", pulse: false },
  FAILED: { color: "var(--pf-coral)", label: "FAILED", dot: "var(--pf-coral)", pulse: false },
};

export default function PayFlowDashboard() {
  const [orders, setOrders] = useState([]);
  const [connected, setConnected] = useState(null);
  const [activeStage, setActiveStage] = useState(null);
  const [flashIds, setFlashIds] = useState({});
  const [form, setForm] = useState({ product_name: "", amount: "" });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const prevOrdersRef = useRef({});

  const fetchOrders = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/orders`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setConnected(true);
      setLastUpdated(new Date());

      const prevMap = prevOrdersRef.current;
      const newFlashes = {};
      let anyPending = false;
      let anyJustResolved = false;

      data.forEach((o) => {
        if (o.status === "PENDING") anyPending = true;
        const prevStatus = prevMap[o.id];
        if (prevStatus === "PENDING" && (o.status === "SUCCESS" || o.status === "FAILED")) {
          newFlashes[o.id] = true;
          anyJustResolved = true;
        }
      });

      if (anyJustResolved) {
        setActiveStage("notify");
        setTimeout(() => setActiveStage(null), 900);
      } else if (anyPending) {
        setActiveStage("payment");
      } else {
        setActiveStage(null);
      }

      if (Object.keys(newFlashes).length) {
        setFlashIds((current) => ({ ...current, ...newFlashes }));
        setTimeout(() => {
          setFlashIds((current) => {
            const copy = { ...current };
            Object.keys(newFlashes).forEach((id) => delete copy[id]);
            return copy;
          });
        }, 1600);
      }

      const nextMap = {};
      data.forEach((o) => { nextMap[o.id] = o.status; });
      prevOrdersRef.current = nextMap;
      setOrders(data);
    } catch (err) {
      setConnected(false);
    }
  }, []);

  useEffect(() => {
    fetchOrders();
    const interval = setInterval(fetchOrders, POLL_MS);
    return () => clearInterval(interval);
  }, [fetchOrders]);

  const submitOrder = async (e) => {
    e.preventDefault();
    setFormError(null);
    const amount = parseFloat(form.amount);
    if (!form.product_name.trim() || Number.isNaN(amount) || amount <= 0) {
      setFormError("Enter a product name and a positive amount.");
      return;
    }

    setSubmitting(true);
    setActiveStage("order");

    try {
      const res = await fetch(`${API_BASE}/orders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_name: form.product_name.trim(), amount }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setForm({ product_name: "", amount: "" });
      await fetchOrders();
    } catch (err) {
      setFormError("Could not reach the Order Service. Is it running?");
    } finally {
      setSubmitting(false);
      setTimeout(() => setActiveStage(null), 500);
    }
  };

  const pendingCount = orders.filter((o) => o.status === "PENDING").length;
  const successCount = orders.filter((o) => o.status === "SUCCESS").length;
  const failedCount = orders.filter((o) => o.status === "FAILED").length;
  const resolved = successCount + failedCount;
  const successRate = resolved > 0 ? ((successCount / resolved) * 100).toFixed(1) : "—";

  return (
    <div
      style={{
        "--pf-bg": "#0B0F14",
        "--pf-panel": "#121821",
        "--pf-panel2": "#161D27",
        "--pf-line": "#1F2733",
        "--pf-text": "#E9EDF1",
        "--pf-muted": "#7C8797",
        "--pf-gold": "#E8B04B",
        "--pf-teal": "#3ECF8E",
        "--pf-coral": "#FF6B5E",
        background: "var(--pf-bg)",
        color: "var(--pf-text)",
        fontFamily: "'Inter', -apple-system, sans-serif",
        minHeight: "100vh",
        padding: "28px",
      }}
    >
      <style>{`
        .pf-mono { font-family: 'JetBrains Mono', monospace; }
        .pf-display { font-family: 'Space Grotesk', sans-serif; }
        .pf-row { animation: pf-slide-in 0.35s ease-out; }
        @keyframes pf-slide-in { from { opacity: 0; transform: translateY(-6px);} to { opacity:1; transform: translateY(0);} }
        .pf-pulse { animation: pf-pulse 1.4s ease-in-out infinite; }
        @keyframes pf-pulse { 0%,100% { opacity:1;} 50% { opacity:0.4;} }
        .pf-flash { animation: pf-flash 1.6s ease-out; }
        @keyframes pf-flash { 0% { background: rgba(232,176,75,0.18); } 100% { background: transparent; } }
        .pf-input {
          background: var(--pf-panel2);
          border: 1px solid var(--pf-line);
          color: var(--pf-text);
          border-radius: 8px;
          padding: 10px 12px;
          font-size: 13px;
          font-family: 'Inter', sans-serif;
          outline: none;
          width: 100%;
        }
        .pf-input:focus { border-color: var(--pf-gold); }
        .pf-btn {
          background: var(--pf-gold);
          color: #0B0F14;
          border: none;
          border-radius: 8px;
          padding: 10px 16px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 6px;
          white-space: nowrap;
        }
        .pf-btn:disabled { opacity: 0.5; cursor: not-allowed; }
      `}</style>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "24px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
            {connected === false ? (
              <>
                <WifiOff size={12} color="var(--pf-coral)" />
                <span className="pf-mono" style={{ fontSize: "11px", color: "var(--pf-coral)", letterSpacing: "0.1em" }}>
                  API UNREACHABLE — start docker compose
                </span>
              </>
            ) : (
              <>
                <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--pf-teal)" }} className="pf-pulse" />
                <span className="pf-mono" style={{ fontSize: "11px", color: "var(--pf-muted)", letterSpacing: "0.12em" }}>
                  {connected === null ? "CONNECTING..." : "LIVE"}
                </span>
              </>
            )}
          </div>
          <h1 className="pf-display" style={{ fontSize: "28px", fontWeight: 700, margin: 0, letterSpacing: "-0.01em" }}>
            PayFlow <span style={{ color: "var(--pf-gold)" }}>Ops</span>
          </h1>
          <p style={{ color: "var(--pf-muted)", fontSize: "13px", margin: "4px 0 0" }}>
            Real-time orchestration dashboard for order ingestion, payment processing, and event notification.
          </p>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: "12px", marginBottom: "22px" }}>
        {[
          { label: "Total Orders", value: orders.length, icon: TrendingUp },
          { label: "Success Rate", value: successRate, unit: successRate !== "—" ? "%" : "", icon: CircleDot, color: successRate !== "—" && Number(successRate) > 80 ? "var(--pf-teal)" : "var(--pf-coral)" },
          { label: "Pending in Queue", value: pendingCount, unit: "", icon: Clock3 },
          { label: "Failed Orders", value: failedCount, unit: "", icon: BellRing, color: "var(--pf-coral)" },
        ].map((m) => (
          <div key={m.label} style={{ background: "var(--pf-panel)", border: "1px solid var(--pf-line)", borderRadius: "14px", padding: "18px 20px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--pf-muted)", fontSize: "12px", marginBottom: "10px" }}>
              <m.icon size={14} />
              {m.label}
            </div>
            <div className="pf-mono" style={{ fontSize: "26px", fontWeight: 700, color: m.color || "var(--pf-text)" }}>
              {m.value}
              <span style={{ fontSize: "13px", color: "var(--pf-muted)", marginLeft: "6px" }}>{m.unit}</span>
            </div>
          </div>
        ))}
      </div>

      <div style={{ background: "var(--pf-panel)", border: "1px solid var(--pf-line)", borderRadius: "14px", padding: "24px", marginBottom: "22px" }}>
        <div style={{ fontSize: "12px", color: "var(--pf-muted)", letterSpacing: "0.08em", marginBottom: "18px" }} className="pf-mono">
          EVENT PIPELINE
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "16px", justifyContent: "space-between" }}>
          {NODES.map((node, i) => (
            <div key={node.key} style={{ display: "flex", alignItems: "center", gap: "12px", flex: "1 1 220px" }}>
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "10px",
                  padding: "18px 16px",
                  borderRadius: "14px",
                  border: `1px solid ${activeStage === node.key ? "var(--pf-gold)" : "var(--pf-line)"}`,
                  background: activeStage === node.key ? "rgba(232,176,75,0.1)" : "var(--pf-panel2)",
                  minWidth: "200px",
                }}
              >
                <node.icon size={20} color={activeStage === node.key ? "var(--pf-gold)" : "var(--pf-muted)"} />
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: "13px", fontWeight: 700 }}>{node.label}</div>
                  <div className="pf-mono" style={{ fontSize: "10.8px", color: "var(--pf-muted)", marginTop: "3px" }}>{node.sub}</div>
                </div>
              </div>
              {i < NODES.length - 1 && <ArrowRight size={18} color="var(--pf-muted)" />}
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: "18px", marginBottom: "22px" }}>
        <form onSubmit={submitOrder} style={{ background: "var(--pf-panel)", border: "1px solid var(--pf-line)", borderRadius: "14px", padding: "22px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "18px", gap: "12px" }}>
            <div>
              <div style={{ fontSize: "12px", color: "var(--pf-muted)", letterSpacing: "0.08em" }} className="pf-mono">
                PLACE NEW ORDER
              </div>
              <h2 style={{ fontSize: "18px", margin: "10px 0 0" }}>Send a test transaction</h2>
            </div>
            <button type="button" onClick={fetchOrders} className="pf-btn" style={{ background: "transparent", color: "var(--pf-text)", border: "1px solid var(--pf-line)" }}>
              <RefreshCcw size={16} /> Refresh
            </button>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1.3fr 0.9fr", gap: "12px", marginBottom: "14px" }}>
            <input
              className="pf-input"
              placeholder="Product name"
              value={form.product_name}
              onChange={(e) => setForm({ ...form, product_name: e.target.value })}
            />
            <input
              className="pf-input"
              placeholder="Amount ($)"
              type="number"
              step="0.01"
              value={form.amount}
              onChange={(e) => setForm({ ...form, amount: e.target.value })}
            />
          </div>
          <button className="pf-btn" type="submit" disabled={submitting}>
            <Send size={14} />
            {submitting ? "Submitting..." : "Submit Order"}
          </button>
          {formError && (
            <div style={{ color: "var(--pf-coral)", fontSize: "13px", marginTop: "12px" }} className="pf-mono">
              {formError}
            </div>
          )}
        </form>

        <div style={{ display: "grid", gap: "14px" }}>
          <div style={{ background: "var(--pf-panel)", border: "1px solid var(--pf-line)", borderRadius: "14px", padding: "18px" }}>
            <div style={{ fontSize: "12px", color: "var(--pf-muted)", letterSpacing: "0.08em", marginBottom: "14px" }} className="pf-mono">
              PERFORMANCE
            </div>
            <div style={{ display: "grid", gap: "12px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
                <span style={{ color: "var(--pf-muted)" }}>Last refresh</span>
                <span className="pf-mono" style={{ color: "var(--pf-text)" }}>{lastUpdated ? lastUpdated.toLocaleTimeString() : "—"}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
                <span style={{ color: "var(--pf-muted)" }}>Resolved order rate</span>
                <span className="pf-mono" style={{ color: "var(--pf-text)" }}>{successRate !== "—" ? `${successRate}%` : "N/A"}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
                <span style={{ color: "var(--pf-muted)" }}>Active queue</span>
                <span className="pf-mono" style={{ color: pendingCount > 0 ? "var(--pf-gold)" : "var(--pf-teal)" }}>
                  {pendingCount > 0 ? `${pendingCount} pending` : "idle"}
                </span>
              </div>
              {orders.length > 0 && (
                <div>
                  <div style={{ display: "flex", height: "6px", borderRadius: "3px", overflow: "hidden", background: "var(--pf-line)" }}>
                    {successCount > 0 && (
                      <div style={{ width: `${(successCount / orders.length) * 100}%`, background: "var(--pf-teal)" }} />
                    )}
                    {failedCount > 0 && (
                      <div style={{ width: `${(failedCount / orders.length) * 100}%`, background: "var(--pf-coral)" }} />
                    )}
                    {pendingCount > 0 && (
                      <div style={{ width: `${(pendingCount / orders.length) * 100}%`, background: "var(--pf-gold)" }} />
                    )}
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: "6px", fontSize: "10.5px" }} className="pf-mono">
                    <span style={{ color: "var(--pf-teal)" }}>{successCount} success</span>
                    <span style={{ color: "var(--pf-coral)" }}>{failedCount} failed</span>
                    <span style={{ color: "var(--pf-gold)" }}>{pendingCount} pending</span>
                  </div>
                </div>
              )}
            </div>
          </div>
          <div style={{ background: "var(--pf-panel)", border: "1px solid var(--pf-line)", borderRadius: "14px", padding: "18px" }}>
            <div style={{ fontSize: "12px", color: "var(--pf-muted)", letterSpacing: "0.08em", marginBottom: "14px" }} className="pf-mono">
              QUICK TIPS
            </div>
            <ul style={{ color: "var(--pf-text)", fontSize: "13px", lineHeight: 1.7, paddingLeft: "18px" }}>
              <li>Submit an order to start the pipeline.</li>
              <li>Order status moves from PENDING → SUCCESS / FAILED.</li>
              <li>Notification service logs are available in the container output.</li>
            </ul>
          </div>
        </div>
      </div>

      <div style={{ background: "var(--pf-panel)", border: "1px solid var(--pf-line)", borderRadius: "14px", overflow: "hidden" }}>
        <div style={{ padding: "18px 22px", borderBottom: "1px solid var(--pf-line)", fontSize: "12px", color: "var(--pf-muted)", letterSpacing: "0.08em" }} className="pf-mono">
          LIVE TRANSACTION LEDGER
        </div>
        <div className="pf-mono" style={{ display: "grid", gridTemplateColumns: "80px 1.1fr 100px 110px 90px", padding: "12px 22px", fontSize: "11px", color: "var(--pf-muted)", borderBottom: "1px solid var(--pf-line)" }}>
          <span>ID</span>
          <span>PRODUCT</span>
          <span>AMOUNT</span>
          <span>STATUS</span>
          <span>AGE</span>
        </div>

        {connected === null && (
          <div>
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                style={{ display: "grid", gridTemplateColumns: "80px 1.1fr 100px 110px 90px", padding: "14px 22px", borderBottom: "1px solid var(--pf-line)", alignItems: "center" }}
              >
                {[40, "70%", 60, 80, 50].map((w, idx) => (
                  <span
                    key={idx}
                    style={{
                      height: "12px",
                      width: typeof w === "number" ? `${w}px` : w,
                      borderRadius: "4px",
                      background: "var(--pf-line)",
                      opacity: 0.5 + (i % 2) * 0.15,
                    }}
                    className="pf-pulse"
                  />
                ))}
              </div>
            ))}
          </div>
        )}

        {orders.length === 0 && connected && (
          <div style={{ padding: "28px 22px", textAlign: "center", color: "var(--pf-muted)", fontSize: "13px" }}>
            No orders yet — submit one above to see it flow through the pipeline.
          </div>
        )}

        {connected === false && (
          <div style={{ padding: "28px 22px", textAlign: "center", color: "var(--pf-coral)", fontSize: "13px" }} className="pf-mono">
            Can't reach {API_BASE}. Run <code style={{ color: "var(--pf-text)", background: "rgba(255,255,255,0.04)", padding: "2px 4px", borderRadius: "4px" }}>docker compose up --build</code> and refresh.
          </div>
        )}

        {orders.map((o) => {
          const s = statusStyle[o.status] || { color: "var(--pf-muted)", label: o.status, dot: "var(--pf-muted)" };
          const age = o.created_at ? Math.max(0, Math.floor((Date.now() - new Date(o.created_at)) / 1000)) : null;
          return (
            <div
              key={o.id}
              className={`pf-row pf-mono ${flashIds[o.id] ? "pf-flash" : ""}`}
              style={{ display: "grid", gridTemplateColumns: "80px 1.1fr 100px 110px 90px", padding: "14px 22px", fontSize: "13px", borderBottom: "1px solid var(--pf-line)", alignItems: "center" }}
            >
              <span style={{ color: "var(--pf-muted)" }}>#{o.id}</span>
              <span style={{ fontFamily: "'Inter', sans-serif" }}>{o.product_name}</span>
              <span>{Number(o.amount).toLocaleString(undefined, { style: "currency", currency: "USD" })}</span>
              <span style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                <span style={{ display: "flex", alignItems: "center", gap: "8px", color: s.color }}>
                  <span className={s.pulse ? "pf-pulse" : ""} style={{ width: "7px", height: "7px", borderRadius: "50%", background: s.dot, display: "inline-block" }} />
                  {s.label}
                </span>
                {o.status === "FAILED" && o.failure_reason && (
                  <span style={{ fontSize: "10.5px", color: "var(--pf-muted)", fontFamily: "'Inter', sans-serif" }}>
                    {o.failure_reason}
                  </span>
                )}
              </span>
              <span className="pf-mono" style={{ color: "var(--pf-muted)" }}>{age !== null ? `${age}s ago` : "—"}</span>
            </div>
          );
        })}
      </div>

      <div style={{ textAlign: "center", marginTop: "18px", fontSize: "11px", color: "var(--pf-muted)" }} className="pf-mono">
        Polling {API_BASE}/orders every {POLL_MS / 1000}s — swap for a WebSocket for true event streaming.
      </div>
    </div>
  );
}
