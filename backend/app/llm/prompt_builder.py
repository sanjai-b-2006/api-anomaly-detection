from typing import Dict, Any

def build_anomaly_prompt(anomaly_data: Dict[str, Any]) -> str:
    """
    Constructs a rich, contextual prompt for the LLM based on API-traffic anomaly data.
    """
    anomaly_type = anomaly_data.get("anomaly_type", "Unknown")
    severity = anomaly_data.get("severity", "Unknown")
    confidence = anomaly_data.get("confidence", 0.0)

    detectors = anomaly_data.get("detectors_triggered", [])
    detector_summary = "\n".join([f"- {d['name']}: {d['detail']} (score: {d['score']:.2f})" for d in detectors])

    context = anomaly_data.get("context", {})
    endpoint = context.get("endpoint", "Unknown")
    method = context.get("method", "GET")
    requests_per_sec = context.get("requests_per_sec", 0.0)
    avg_latency_ms = context.get("avg_latency_ms", 0.0)
    p95_latency_ms = context.get("p95_latency_ms", 0.0)
    error_rate = context.get("error_rate", 0.0)
    total_requests = context.get("total_requests", 0)
    error_count = context.get("error_count", 0)
    bytes_per_sec = context.get("bytes_per_sec", 0.0)
    dataset_label = context.get("dataset_label", "Unknown")

    # Baselines
    baseline_rps = context.get("baseline_requests_per_sec_mean", 0.0)
    baseline_avg_lat = context.get("baseline_avg_latency_ms_mean", 0.0)
    baseline_p95_lat = context.get("baseline_p95_latency_ms_mean", 0.0)
    baseline_err = context.get("baseline_error_rate_mean", 0.0)

    prompt = f"""
API TRAFFIC INCIDENT / ANOMALY REPORT:
- Incident Category: {anomaly_type} (Simulation Label: {dataset_label})
- Severity: {severity.upper()} (confidence: {confidence*100:.1f}%)

Endpoint: {method} {endpoint}

Traffic Metrics:
- Requests/sec: {requests_per_sec:.1f} (Baseline Mean: {baseline_rps:.1f})
- Avg Latency: {avg_latency_ms:.1f} ms (Baseline Mean: {baseline_avg_lat:.1f} ms)
- P95 Latency: {p95_latency_ms:.1f} ms (Baseline Mean: {baseline_p95_lat:.1f} ms)
- Error Rate: {error_rate*100:.1f}% (Baseline Mean: {baseline_err*100:.1f}%)
- Total Requests (window): {total_requests}
- Error Count (window): {error_count}
- Throughput: {bytes_per_sec:.0f} bytes/sec

Detectors Triggered:
{detector_summary}

Based on the traffic signature above, provide:
1. SRE Root Cause Analysis: Explain what kind of incident this pattern matches (e.g. traffic surge / DDoS, latency degradation from a slow dependency or DB, error spike from a bad deploy, full service outage, or credential-stuffing / brute force) and why, based on the metrics.
2. SRE Immediate Mitigation Actions: Provide 2-3 specific actions the on-call SRE team should take right now (e.g. enable rate limiting / autoscaling, roll back the latest deploy, fail over, add caching, block abusive IPs). Keep it extremely concise, clear, and SRE-focused (3-4 sentences total).
"""
    return prompt
