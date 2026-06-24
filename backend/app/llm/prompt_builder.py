from typing import Dict, Any

def build_anomaly_prompt(anomaly_data: Dict[str, Any]) -> str:
    """
    Constructs a rich, contextual prompt for the LLM based on network flow anomaly data.
    """
    anomaly_type = anomaly_data.get("anomaly_type", "Unknown")
    severity = anomaly_data.get("severity", "Unknown")
    confidence = anomaly_data.get("confidence", 0.0)
    
    detectors = anomaly_data.get("detectors_triggered", [])
    detector_summary = "\n".join([f"- {d['name']}: {d['detail']} (score: {d['score']:.2f})" for d in detectors])
    
    context = anomaly_data.get("context", {})
    dest_port = context.get("destination_port", "Unknown")
    flow_duration = context.get("flow_duration", 0.0)
    total_fwd_packets = context.get("total_fwd_packets", 0)
    total_bwd_packets = context.get("total_bwd_packets", 0)
    fwd_packets_s = context.get("fwd_packets_s", 0.0)
    bwd_packets_s = context.get("bwd_packets_s", 0.0)
    flow_bytes_s = context.get("flow_bytes_s", 0.0)
    packet_length_mean = context.get("packet_length_mean", 0.0)
    dataset_label = context.get("dataset_label", "Unknown")
    
    # Baselines
    baseline_duration = context.get("baseline_flow_duration_mean", 0.0)
    baseline_fwd_packets_s = context.get("baseline_fwd_packets_s_mean", 0.0)
    baseline_bytes_s = context.get("baseline_flow_bytes_s_mean", 0.0)
    baseline_pkt_len = context.get("baseline_packet_length_mean_mean", 0.0)
    
    prompt = f"""
SECURITY INTRUSION / ANOMALY REPORT:
- Classification Category: {anomaly_type} (Simulation Label: {dataset_label})
- Severity: {severity.upper()} (confidence: {confidence*100:.1f}%)

Network Flow Metrics:
- Destination Port: {dest_port}
- Flow Duration: {flow_duration:.2f} microseconds (Baseline Mean: {baseline_duration:.2f})
- Total Forward Packets: {total_fwd_packets}
- Total Backward Packets: {total_bwd_packets}
- Forward Packets/s: {fwd_packets_s:.2f} (Baseline Mean: {baseline_fwd_packets_s:.2f})
- Backward Packets/s: {bwd_packets_s:.2f}
- Flow Bytes/s: {flow_bytes_s:.2f} (Baseline Mean: {baseline_bytes_s:.2f})
- Mean Packet Length: {packet_length_mean:.2f} bytes (Baseline Mean: {baseline_pkt_len:.2f})

Detectors Triggered:
{detector_summary}

Based on the network signature above, provide:
1. SRE Root Cause Analysis: Explain what kind of cyber-attack or anomaly this pattern matches (e.g. DDoS TCP Syn Flood, Port Scanning, Botnet beaconing, or abnormal system load) and why based on the metrics.
2. SRE Immediate Mitigation Actions: Provide 2-3 specific actions the SRE or NetOps team should take right now (e.g. firewall block, rate limiting, traffic scrubbing). Keep it extremely concise, clear, and SRE-focused (3-4 sentences total).
"""
    return prompt
