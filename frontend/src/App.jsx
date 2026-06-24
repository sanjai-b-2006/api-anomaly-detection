import React, { useState, useEffect, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceArea } from 'recharts';
import { Activity, AlertTriangle, ShieldCheck, Clock, ShieldAlert, Terminal, Network, ListFilter } from 'lucide-react';
import './index.css';

export default function App() {
  const [metrics, setMetrics] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [activeTab, setActiveTab] = useState('fwd_packets_s'); // fwd_packets_s, flow_bytes_s, flow_duration, packet_length_mean
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
        
        // Push anomalous metrics to the chart data
        const ctx = anomaly.context;
        const timeStr = new Date(anomaly.timestamp).toLocaleTimeString();
        
        setMetrics(prev => {
          // Check if we already added a metric for this timestamp to avoid duplicates
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
            fwd_packets_s: ctx.fwd_packets_s,
            flow_bytes_s: ctx.flow_bytes_s,
            flow_duration: ctx.flow_duration,
            packet_length_mean: ctx.packet_length_mean,
            label: anomaly.anomaly_type,
            isAnomaly: true
          }].slice(-50);
        });
        
      } else if (payload.type === 'METRIC_UPDATE') {
        const data = payload.data;
        const timeStr = new Date(data.timestamp).toLocaleTimeString();
        
        // Update live metrics chart
        setMetrics(prev => {
          if (prev.length > 0 && prev[prev.length - 1].time === timeStr) {
            return prev; // skip duplicates within same second
          }
          return [...prev, {
            time: timeStr,
            fwd_packets_s: data.fwd_packets_s,
            flow_bytes_s: data.flow_bytes_s,
            flow_duration: data.flow_duration,
            packet_length_mean: data.packet_length_mean,
            label: data.label,
            isAnomaly: data.label !== 'BENIGN'
          }].slice(-50);
        });

        // Add to recent flows list at bottom
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

  // Helper stats calculation
  const totalFlowsProcessed = recentFlows.length + metrics.length;
  const maliciousFlowsCount = anomalies.length;
  const systemHealth = maliciousFlowsCount > 10 ? '75%' : maliciousFlowsCount > 5 ? '88%' : '99.8%';
  const healthColor = maliciousFlowsCount > 10 ? 'var(--accent-coral)' : maliciousFlowsCount > 5 ? 'var(--accent-warning)' : 'var(--accent-success)';

  const getTabLabel = (tab) => {
    switch(tab) {
      case 'fwd_packets_s': return 'Packets Rate (packets/sec)';
      case 'flow_bytes_s': return 'Bandwidth (bytes/sec)';
      case 'flow_duration': return 'Flow Duration (µs)';
      case 'packet_length_mean': return 'Mean Packet Size (bytes)';
      default: return '';
    }
  };

  const getTabColor = (tab) => {
    switch(tab) {
      case 'fwd_packets_s': return 'var(--accent-cyan)';
      case 'flow_bytes_s': return 'var(--accent-purple)';
      case 'flow_duration': return 'var(--accent-warning)';
      case 'packet_length_mean': return '#E0F2FE';
      default: return 'var(--accent-cyan)';
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar / Console Header */}
      <aside className="sidebar glass-panel">
        <div className="sidebar-logo">
          <Network size={28} color="var(--accent-cyan)" />
          <span>NetSOC Guard</span>
        </div>
        
        <nav className="flex-col gap-4" style={{ marginTop: '2rem' }}>
          <div className="flex items-center gap-2" style={{ color: 'var(--accent-cyan)', fontWeight: 600, cursor: 'pointer' }}>
            <Activity size={20} /> Traffic Dashboard
          </div>
          <div className="flex items-center gap-2" style={{ color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <ShieldAlert size={20} /> Intrusion Feeds
          </div>
          <div className="flex items-center gap-2" style={{ color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <Terminal size={20} /> SOC Shell
          </div>
        </nav>

        <div style={{ marginTop: 'auto', position: 'absolute', bottom: '2rem' }}>
          <div className="flex items-center gap-2" style={{ fontSize: '0.85rem', color: wsStatus === 'Connected' ? 'var(--accent-success)' : 'var(--accent-warning)' }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'currentColor' }}></div>
            Link: {wsStatus}
          </div>
          <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            Ingesting: CIC-IDS-2017 Format
          </p>
        </div>
      </aside>

      {/* Main Console Area */}
      <main className="main-content">
        <header className="dashboard-header flex justify-between items-center">
          <div>
            <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ShieldCheck size={28} color="var(--accent-success)" />
              Security Operations Center (SOC) Console
            </h1>
            <h2>CIC-IDS-2017 Intrusion & Anomaly Tracking</h2>
          </div>
          
          <div className="flex gap-4">
            <div className="glass-card" style={{ padding: '0.75rem 1.5rem', textAlign: 'center', minWidth: '110px' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--accent-coral)' }}>{maliciousFlowsCount}</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Intrusions Flagged</div>
            </div>
            <div className="glass-card" style={{ padding: '0.75rem 1.5rem', textAlign: 'center', minWidth: '110px' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>{recentFlows.length}</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Live Flow Count</div>
            </div>
            <div className="glass-card" style={{ padding: '0.75rem 1.5rem', textAlign: 'center', minWidth: '110px' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: healthColor }}>{systemHealth}</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>SOC Integrity</div>
            </div>
          </div>
        </header>

        {/* Dynamic Metric Tabs */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          {['fwd_packets_s', 'flow_bytes_s', 'flow_duration', 'packet_length_mean'].map(tab => (
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
              {tab === 'fwd_packets_s' ? 'Fwd Packets/s' :
               tab === 'flow_bytes_s' ? 'Flow Bytes/s' :
               tab === 'flow_duration' ? 'Flow Duration' : 'Mean Packet Size'}
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
                    <ReferenceArea key={index} x1={index > 0 ? metrics[index-1].time : entry.time} x2={entry.time} fill="rgba(255, 107, 107, 0.08)" /> 
                  : null
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Intrusions alerts Feed */}
        <h3 style={{ marginTop: '2.5rem', marginBottom: '1rem' }}>Active Threat Alerts</h3>
        
        {anomalies.length === 0 ? (
          <div className="glass-card flex-col items-center" style={{ padding: '3rem', color: 'var(--text-secondary)' }}>
            <ShieldCheck size={48} color="var(--accent-success)" style={{ marginBottom: '1rem' }} />
            <p>No active network threat detected. NetSOC firewall reporting normal activity.</p>
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
                  <div>Port: <code>{anomaly.context?.destination_port}</code></div>
                  <div>Packets/s: <code>{anomaly.context?.fwd_packets_s?.toLocaleString()}</code></div>
                  <div>Flow Duration: <code>{anomaly.context?.flow_duration?.toLocaleString()} µs</code></div>
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

        {/* Live Network Stream Logs */}
        <h3 style={{ marginTop: '2.5rem', marginBottom: '1rem' }}>Live Network Flow Logs</h3>
        <div className="glass-card" style={{ padding: '0.5rem 1rem', overflowX: 'auto', maxHeight: '300px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', color: 'var(--text-primary)', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                <th style={{ padding: '0.75rem' }}>Timestamp</th>
                <th style={{ padding: '0.75rem' }}>Port</th>
                <th style={{ padding: '0.75rem' }}>Fwd Packets/s</th>
                <th style={{ padding: '0.75rem' }}>Bytes/s</th>
                <th style={{ padding: '0.75rem' }}>Duration (µs)</th>
                <th style={{ padding: '0.75rem' }}>Mean Size (B)</th>
                <th style={{ padding: '0.75rem' }}>Dataset Classification</th>
              </tr>
            </thead>
            <tbody>
              {recentFlows.length === 0 ? (
                <tr>
                  <td colSpan="7" style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                    No network flows logged yet. Start the mock data generator to stream packets.
                  </td>
                </tr>
              ) : (
                recentFlows.map(flow => (
                  <tr 
                    key={flow.id} 
                    style={{ 
                      borderBottom: '1px solid rgba(255,255,255,0.02)', 
                      backgroundColor: flow.label !== 'BENIGN' ? 'rgba(255, 107, 107, 0.05)' : 'transparent',
                      color: flow.label !== 'BENIGN' ? 'var(--accent-coral)' : 'var(--text-primary)'
                    }}
                  >
                    <td style={{ padding: '0.75rem', fontFamily: 'monospace' }}>{flow.time}</td>
                    <td style={{ padding: '0.75rem', fontFamily: 'monospace' }}>{flow.destination_port}</td>
                    <td style={{ padding: '0.75rem', fontFamily: 'monospace' }}>{flow.fwd_packets_s?.toLocaleString(undefined, {maximumFractionDigits: 1})}</td>
                    <td style={{ padding: '0.75rem', fontFamily: 'monospace' }}>{flow.flow_bytes_s?.toLocaleString(undefined, {maximumFractionDigits: 1})}</td>
                    <td style={{ padding: '0.75rem', fontFamily: 'monospace' }}>{flow.flow_duration?.toLocaleString()}</td>
                    <td style={{ padding: '0.75rem', fontFamily: 'monospace' }}>{flow.packet_length_mean?.toFixed(1)}</td>
                    <td style={{ padding: '0.75rem' }}>
                      <span 
                        className="badge" 
                        style={{
                          background: flow.label === 'BENIGN' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(255, 107, 107, 0.25)',
                          color: flow.label === 'BENIGN' ? 'var(--accent-success)' : 'var(--accent-coral)',
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
