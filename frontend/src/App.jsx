import React, { useState, useEffect, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceArea } from 'recharts';
import { Activity, AlertTriangle, ShieldCheck, Gauge, ServerCrash, Terminal, Globe } from 'lucide-react';
import './index.css';

export default function App() {
  const [metrics, setMetrics] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [activeTab, setActiveTab] = useState('requests_per_sec');
  const [wsStatus, setWsStatus] = useState('Connecting...');
  const [recentFlows, setRecentFlows] = useState([]);
  const ws = useRef(null);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (ws.current) ws.current.close();
    };
  }, []);

  const connectWebSocket = () => {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws.current = new WebSocket(`${proto}//${window.location.host}/api/v1/ws/alerts`);

    ws.current.onopen = () => setWsStatus('Connected');
    ws.current.onclose = () => {
      setWsStatus('Disconnected - Reconnecting...');
      setTimeout(connectWebSocket, 3000);
    };

    ws.current.onmessage = (event) => {
      const payload = JSON.parse(event.data);

      if (payload.type === 'NEW_ANOMALY') {
        const anomaly = payload.data;
        setAnomalies(prev => [anomaly, ...prev].slice(0, 50));

        const ctx = anomaly.context;
        const timeStr = new Date(anomaly.timestamp).toLocaleTimeString();

        setMetrics(prev => {
          if (prev.length > 0 && prev[prev.length - 1].time === timeStr) {
            const updated = [...prev];
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              isAnomaly: true,
              anomalyType: anomaly.anomaly_type
            };
            return updated;
          }
          return [...prev, {
            time: timeStr,
            requests_per_sec: ctx.requests_per_sec,
            avg_latency_ms: ctx.avg_latency_ms,
            p95_latency_ms: ctx.p95_latency_ms,
            error_rate: ctx.error_rate,
            label: anomaly.anomaly_type,
            isAnomaly: true
          }].slice(-50);
        });

      } else if (payload.type === 'METRIC_UPDATE') {
        const data = payload.data;
        const timeStr = new Date(data.timestamp).toLocaleTimeString();

        setMetrics(prev => {
          if (prev.length > 0 && prev[prev.length - 1].time === timeStr) {
            return prev;
          }
          return [...prev, {
            time: timeStr,
            requests_per_sec: data.requests_per_sec,
            avg_latency_ms: data.avg_latency_ms,
            p95_latency_ms: data.p95_latency_ms,
            error_rate: data.error_rate,
            label: data.label,
            isAnomaly: data.label !== 'NORMAL'
          }].slice(-50);
        });

        setRecentFlows(prev => [
          {
            id: Math.random().toString(),
            time: timeStr,
            ...data
          },
          ...prev
        ].slice(0, 30));
      }
    };
  };

  const incidentsCount = anomalies.length;
  const uptime = incidentsCount > 10 ? '97.5%' : incidentsCount > 5 ? '99.0%' : '99.9%';
  const uptimeColor = incidentsCount > 10 ? 'var(--accent-coral)' : incidentsCount > 5 ? 'var(--accent-warning)' : 'var(--accent-success)';

  const getTabLabel = (tab) => {
    switch (tab) {
      case 'requests_per_sec': return 'Throughput (requests/sec)';
      case 'avg_latency_ms': return 'Average Latency (ms)';
      case 'p95_latency_ms': return 'P95 Latency (ms)';
      case 'error_rate': return 'Error Rate (fraction)';
      default: return '';
    }
  };

  const getTabColor = (tab) => {
    switch (tab) {
      case 'requests_per_sec': return 'var(--accent-cyan)';
      case 'avg_latency_ms': return 'var(--accent-purple)';
      case 'p95_latency_ms': return 'var(--accent-warning)';
      case 'error_rate': return 'var(--accent-coral)';
      default: return 'var(--accent-cyan)';
    }
  };

  const getTabShort = (tab) => {
    switch (tab) {
      case 'requests_per_sec': return 'Req/s';
      case 'avg_latency_ms': return 'Avg Latency';
      case 'p95_latency_ms': return 'P95 Latency';
      case 'error_rate': return 'Error Rate';
      default: return tab;
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar glass-panel">
        <div className="sidebar-logo">
          <Globe size={28} color="var(--accent-cyan)" />
          <span>API Watch</span>
        </div>

        <nav className="flex-col gap-4" style={{ marginTop: '2rem' }}>
          <div className="flex items-center gap-2" style={{ color: 'var(--accent-cyan)', fontWeight: 600, cursor: 'pointer' }}>
            <Activity size={20} /> Traffic Dashboard
          </div>
          <div className="flex items-center gap-2" style={{ color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <ServerCrash size={20} /> Incident Feed
          </div>
          <div className="flex items-center gap-2" style={{ color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <Terminal size={20} /> Ops Shell
          </div>
        </nav>

        <div style={{ marginTop: 'auto', position: 'absolute', bottom: '2rem' }}>
          <div className="flex items-center gap-2" style={{ fontSize: '0.85rem', color: wsStatus === 'Connected' ? 'var(--accent-success)' : 'var(--accent-warning)' }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'currentColor' }}></div>
            Link: {wsStatus}
          </div>
          <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            Monitoring: REST / API Endpoints
          </p>
        </div>
      </aside>

      {/* Main Console */}
      <main className="main-content">
        <header className="dashboard-header flex justify-between items-center">
          <div>
            <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Gauge size={28} color="var(--accent-success)" />
              API Traffic Observability Console
            </h1>
            <h2>Real-time Latency, Throughput & Error-rate Anomaly Tracking</h2>
          </div>

          <div className="flex gap-4">
            <div className="glass-card" style={{ padding: '0.75rem 1.5rem', textAlign: 'center', minWidth: '110px' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--accent-coral)' }}>{incidentsCount}</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Incidents Flagged</div>
            </div>
            <div className="glass-card" style={{ padding: '0.75rem 1.5rem', textAlign: 'center', minWidth: '110px' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>{recentFlows.length}</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Live Samples</div>
            </div>
            <div className="glass-card" style={{ padding: '0.75rem 1.5rem', textAlign: 'center', minWidth: '110px' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: uptimeColor }}>{uptime}</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Service Uptime</div>
            </div>
          </div>
        </header>

        {/* Metric Tabs */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          {['requests_per_sec', 'avg_latency_ms', 'p95_latency_ms', 'error_rate'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className="badge"
              style={{
                background: activeTab === tab ? getTabColor(tab) : 'var(--bg-tertiary)',
                color: activeTab === tab ? '#0b0f19' : 'var(--text-secondary)',
                border: activeTab === tab ? '1px solid currentColor' : '1px solid var(--border-color)',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                padding: '0.5rem 1rem',
                fontSize: '0.8rem'
              }}
            >
              {getTabShort(tab)}
            </button>
          ))}
        </div>

        {/* Real-time Line Chart */}
        <div className="glass-card">
          <div className="flex justify-between items-center" style={{ marginBottom: '1rem' }}>
            <h3>{getTabLabel(activeTab)}</h3>
            <span className="badge badge-low" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <Activity size={12} /> Streaming live
            </span>
          </div>

          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={metrics}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis
                  dataKey="time"
                  stroke="var(--text-secondary)"
                  tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                  tickLine={false}
                />
                <YAxis
                  stroke="var(--text-secondary)"
                  tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  domain={['auto', 'auto']}
                />
                <Tooltip
                  contentStyle={{ backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: '8px' }}
                  itemStyle={{ color: 'var(--text-primary)' }}
                />
                <Line
                  type="monotone"
                  dataKey={activeTab}
                  stroke={getTabColor(activeTab)}
                  strokeWidth={2.5}
                  dot={(props) => {
                    if (props.payload.isAnomaly) {
                      return <circle cx={props.cx} cy={props.cy} r={5} fill="var(--accent-coral)" stroke="var(--bg-primary)" strokeWidth={2} />;
                    }
                    return <circle cx={props.cx} cy={props.cy} r={0} />;
                  }}
                  activeDot={{ r: 6, fill: getTabColor(activeTab) }}
                />
                {metrics.map((entry, index) => (
                  entry.isAnomaly ?
                    <ReferenceArea key={index} x1={index > 0 ? metrics[index - 1].time : entry.time} x2={entry.time} fill="rgba(255, 107, 107, 0.08)" />
                    : null
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Incident Feed */}
        <h3 style={{ marginTop: '2.5rem', marginBottom: '1rem' }}>Active Incident Alerts</h3>

        {anomalies.length === 0 ? (
          <div className="glass-card flex-col items-center" style={{ padding: '3rem', color: 'var(--text-secondary)' }}>
            <ShieldCheck size={48} color="var(--accent-success)" style={{ marginBottom: '1rem' }} />
            <p>All endpoints healthy. Latency, throughput and error rates within SLO.</p>
          </div>
        ) : (
          <div className="alerts-grid">
            {anomalies.map(anomaly => (
              <div key={anomaly.id} className={`glass-card alert-card ${anomaly.severity}`}>
                <div className="alert-header">
                  <span className="alert-metric" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: 'var(--accent-coral)' }}>
                    <AlertTriangle size={18} />
                    {anomaly.anomaly_type}
                  </span>
                  <span className={`badge badge-${anomaly.severity}`}>{anomaly.severity}</span>
                </div>

                <div className="flex-col gap-1" style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                  <div>Endpoint: <code>{anomaly.context?.method} {anomaly.context?.endpoint}</code></div>
                  <div>Requests/s: <code>{anomaly.context?.requests_per_sec?.toLocaleString()}</code></div>
                  <div>P95 Latency: <code>{anomaly.context?.p95_latency_ms?.toLocaleString()} ms</code></div>
                  <div>Error Rate: <code>{((anomaly.context?.error_rate || 0) * 100).toFixed(1)}%</code></div>
                </div>

                <div className="alert-explanation">
                  <strong style={{ color: 'var(--accent-cyan)' }}>SRE Root Cause & Mitigations:</strong>
                  <p style={{ marginTop: '0.5rem', whiteSpace: 'pre-line', fontSize: '0.85rem' }}>
                    {anomaly.llm_explanation || "Generating root cause analysis..."}
                  </p>
                </div>

                <div style={{ marginTop: '1.25rem', fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'flex', justifyContent: 'space-between' }}>
                  <span>Confidence: {(anomaly.confidence * 100).toFixed(0)}%</span>
                  <span>Detectors: {anomaly.detectors_triggered?.length || 0} active</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Live Traffic Logs */}
        <h3 style={{ marginTop: '2.5rem', marginBottom: '1rem' }}>Live API Traffic Logs</h3>
        <div className="glass-card" style={{ padding: '0.5rem 1rem', overflowX: 'auto', maxHeight: '300px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', color: 'var(--text-primary)', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                <th style={{ padding: '0.75rem' }}>Timestamp</th>
                <th style={{ padding: '0.75rem' }}>Endpoint</th>
                <th style={{ padding: '0.75rem' }}>Req/s</th>
                <th style={{ padding: '0.75rem' }}>Avg (ms)</th>
                <th style={{ padding: '0.75rem' }}>P95 (ms)</th>
                <th style={{ padding: '0.75rem' }}>Error %</th>
                <th style={{ padding: '0.75rem' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {recentFlows.length === 0 ? (
                <tr>
                  <td colSpan="7" style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                    No traffic logged yet. Start the generator to stream samples.
                  </td>
                </tr>
              ) : (
                recentFlows.map(flow => (
                  <tr
                    key={flow.id}
                    style={{
                      borderBottom: '1px solid rgba(255,255,255,0.02)',
                      backgroundColor: flow.label !== 'NORMAL' ? 'rgba(255, 107, 107, 0.05)' : 'transparent',
                      color: flow.label !== 'NORMAL' ? 'var(--accent-coral)' : 'var(--text-primary)'
                    }}
                  >
                    <td style={{ padding: '0.75rem', fontFamily: 'monospace' }}>{flow.time}</td>
                    <td style={{ padding: '0.75rem', fontFamily: 'monospace' }}>{flow.method} {flow.endpoint}</td>
                    <td style={{ padding: '0.75rem', fontFamily: 'monospace' }}>{flow.requests_per_sec?.toLocaleString(undefined, { maximumFractionDigits: 1 })}</td>
                    <td style={{ padding: '0.75rem', fontFamily: 'monospace' }}>{flow.avg_latency_ms?.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                    <td style={{ padding: '0.75rem', fontFamily: 'monospace' }}>{flow.p95_latency_ms?.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                    <td style={{ padding: '0.75rem', fontFamily: 'monospace' }}>{((flow.error_rate || 0) * 100).toFixed(1)}%</td>
                    <td style={{ padding: '0.75rem' }}>
                      <span
                        className="badge"
                        style={{
                          background: flow.label === 'NORMAL' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(255, 107, 107, 0.25)',
                          color: flow.label === 'NORMAL' ? 'var(--accent-success)' : 'var(--accent-coral)',
                          border: 'none',
                          padding: '0.15rem 0.5rem',
                          fontSize: '0.75rem'
                        }}
                      >
                        {flow.label}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
