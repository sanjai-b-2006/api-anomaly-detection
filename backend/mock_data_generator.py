import asyncio
import httpx
import random
import math
import argparse
import sys
import os
from datetime import datetime, timezone
import pandas as pd

API_URL = "http://localhost:8000/api/v1/metrics/"

def parse_args():
    parser = argparse.ArgumentParser(description="Network Intrusion Mock Data & CSV Replay Generator")
    parser.add_argument("--csv", type=str, default="", help="Path to a Kaggle Network Intrusion dataset CSV to replay")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between sent flows in seconds")
    return parser.parse_args()

async def send_flow(client, flow_data):
    try:
        response = await client.post(API_URL, json=flow_data)
        label = flow_data.get("label", "BENIGN")
        status_marker = "[ATTACK]" if label != "BENIGN" else "[BENIGN]"
        print(f"{status_marker} Sent flow | Port: {flow_data['destination_port']} | Packets/s: {flow_data['fwd_packets_s']:.1f} | Label: {label} | API: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Error sending flow: {e}")

def normalize_csv_columns(df):
    """
    Cleans up column names and matches them to our database fields.
    """
    col_mapping = {}
    for col in df.columns:
        clean = col.strip().lower()
        if "destination port" in clean or "dest port" in clean or clean == "destination_port":
            col_mapping[col] = "destination_port"
        elif "flow duration" in clean or clean == "flow_duration":
            col_mapping[col] = "flow_duration"
        elif "total fwd packets" in clean or "total forward" in clean or clean == "total_fwd_packets":
            col_mapping[col] = "total_fwd_packets"
        elif "total bwd packets" in clean or "total backward" in clean or clean == "total_bwd_packets":
            col_mapping[col] = "total_bwd_packets"
        elif "fwd packets/s" in clean or "fwd packet rate" in clean or clean == "fwd_packets_s":
            col_mapping[col] = "fwd_packets_s"
        elif "bwd packets/s" in clean or "bwd packet rate" in clean or clean == "bwd_packets_s":
            col_mapping[col] = "bwd_packets_s"
        elif "flow bytes/s" in clean or "flow byte rate" in clean or clean == "flow_bytes_s":
            col_mapping[col] = "flow_bytes_s"
        elif "packet length mean" in clean or "avg packet size" in clean or clean == "packet_length_mean":
            col_mapping[col] = "packet_length_mean"
        elif "label" in clean:
            col_mapping[col] = "label"
            
    df.rename(columns=col_mapping, inplace=True)
    return df

async def replay_csv(csv_path, delay):
    print(f"[REPLAY] Starting CSV Replay mode from: {csv_path}")
    if not os.path.exists(csv_path):
        print(f"[ERROR] CSV file not found at {csv_path}")
        return
        
    try:
        # Load the CSV file in chunks to save memory
        chunk_size = 1000
        reader = pd.read_csv(csv_path, chunksize=chunk_size)
        
        async with httpx.AsyncClient() as client:
            for chunk in reader:
                chunk = normalize_csv_columns(chunk)
                # Filter out columns we don't care about
                required_cols = [
                    "destination_port", "flow_duration", "total_fwd_packets", 
                    "total_bwd_packets", "fwd_packets_s", "bwd_packets_s", 
                    "flow_bytes_s", "packet_length_mean"
                ]
                
                # Check if all required columns are present
                missing = [c for c in required_cols if c not in chunk.columns]
                if missing:
                    print(f"[ERROR] CSV is missing columns: {missing}. Available columns: {list(chunk.columns)}")
                    return
                
                for idx, row in chunk.iterrows():
                    # Handle NaN / Inf values
                    fwd_s = row["fwd_packets_s"]
                    bwd_s = row["bwd_packets_s"]
                    bytes_s = row["flow_bytes_s"]
                    
                    if math.isnan(fwd_s) or math.isinf(fwd_s): fwd_s = 0.0
                    if math.isnan(bwd_s) or math.isinf(bwd_s): bwd_s = 0.0
                    if math.isnan(bytes_s) or math.isinf(bytes_s): bytes_s = 0.0
                    
                    flow_payload = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "destination_port": int(row["destination_port"]),
                        "flow_duration": float(row["flow_duration"]),
                        "total_fwd_packets": int(row["total_fwd_packets"]),
                        "total_bwd_packets": int(row["total_bwd_packets"]),
                        "fwd_packets_s": float(fwd_s),
                        "bwd_packets_s": float(bwd_s),
                        "flow_bytes_s": float(bytes_s),
                        "packet_length_mean": float(row["packet_length_mean"]),
                        "label": str(row.get("label", "BENIGN")).strip(),
                        "tags": {"mode": "csv_replay", "filename": os.path.basename(csv_path)},
                        "source": "csv_replay"
                    }
                    await send_flow(client, flow_payload)
                    await asyncio.sleep(delay)
    except Exception as e:
        print(f"[ERROR] Error during CSV processing: {e}")

async def generate_synthetic_traffic(delay):
    print("[START] Starting Synthetic Security Traffic Generator mode...")
    async with httpx.AsyncClient() as client:
        step = 0
        scan_ports = [21, 22, 23, 25, 53, 80, 110, 135, 139, 443, 445, 1433, 3306, 3389, 8080]
        
        while True:
            # Determine state: normal or attack
            # Every 20 steps, let's inject a cyber security threat
            is_attack = False
            attack_type = "BENIGN"
            
            if step > 0 and step % 20 == 0:
                is_attack = True
                attack_type = random.choice(["DDoS", "PortScan", "DoS Hulk", "Infiltration"])
                print(f"\n[WARN] >>> INJECTING ATTACK: {attack_type.upper()} <<<\n")
            
            if not is_attack:
                # BENIGN TRAFFIC
                flow_payload = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "destination_port": random.choice([80, 443, 53, 22]),
                    "flow_duration": float(random.randint(15000, 1500000)), # microseconds
                    "total_fwd_packets": random.randint(2, 15),
                    "total_bwd_packets": random.randint(1, 15),
                    "fwd_packets_s": float(random.uniform(5.0, 150.0)),
                    "bwd_packets_s": float(random.uniform(5.0, 150.0)),
                    "flow_bytes_s": float(random.uniform(500.0, 25000.0)),
                    "packet_length_mean": float(random.uniform(64.0, 320.0)),
                    "label": "BENIGN",
                    "tags": {"environment": "production"},
                    "source": "synthetic_generator"
                }
                await send_flow(client, flow_payload)
                await asyncio.sleep(delay)
                
            elif attack_type == "DDoS":
                # Simulate a massive HTTP GET / TCP Syn Flood (DDoS)
                # Send 8 back-to-back fast requests representing the flood
                for _ in range(8):
                    flow_payload = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "destination_port": 80,
                        "flow_duration": float(random.randint(100, 1000)), # very short flows
                        "total_fwd_packets": random.randint(500, 3000), # massive fwd packet count
                        "total_bwd_packets": random.randint(0, 2), # little to no response
                        "fwd_packets_s": float(random.uniform(50000.0, 250000.0)), # massive rates
                        "bwd_packets_s": float(random.uniform(0, 10.0)),
                        "flow_bytes_s": float(random.uniform(10000000.0, 50000000.0)), # massive bandwidth
                        "packet_length_mean": float(random.uniform(40.0, 64.0)), # small flood packets
                        "label": "DDoS",
                        "tags": {"attack_category": "DDoS_Flood"},
                        "source": "synthetic_generator"
                    }
                    await send_flow(client, flow_payload)
                    await asyncio.sleep(0.4) # very fast burst
                    
            elif attack_type == "PortScan":
                # Simulate scanning all standard open ports on the target machine
                for scan_port in scan_ports[:8]:
                    flow_payload = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "destination_port": scan_port,
                        "flow_duration": float(random.randint(50, 800)),
                        "total_fwd_packets": 1, # single probing packet
                        "total_bwd_packets": 0,
                        "fwd_packets_s": float(random.uniform(10000.0, 20000.0)), # high rate due to short time
                        "bwd_packets_s": 0.0,
                        "flow_bytes_s": 40.0, # tiny payload
                        "packet_length_mean": 40.0,
                        "label": "PortScan",
                        "tags": {"attack_category": "Port_Scanning"},
                        "source": "synthetic_generator"
                    }
                    await send_flow(client, flow_payload)
                    await asyncio.sleep(0.3)
                    
            elif attack_type == "DoS Hulk":
                # DoS Hulk exhausting web server resources with large packets
                for _ in range(4):
                    flow_payload = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "destination_port": 443,
                        "flow_duration": float(random.randint(100000, 800000)),
                        "total_fwd_packets": random.randint(80, 250),
                        "total_bwd_packets": random.randint(80, 250),
                        "fwd_packets_s": float(random.uniform(1200.0, 4500.0)),
                        "bwd_packets_s": float(random.uniform(1200.0, 4500.0)),
                        "flow_bytes_s": float(random.uniform(1500000.0, 4000000.0)), # heavy data transfer
                        "packet_length_mean": float(random.uniform(800.0, 1400.0)), # large HTTP get headers
                        "label": "DoS Hulk",
                        "tags": {"attack_category": "DoS_Hulk"},
                        "source": "synthetic_generator"
                    }
                    await send_flow(client, flow_payload)
                    await asyncio.sleep(0.5)
                    
            elif attack_type == "Infiltration":
                # Slow backdoor control / beaconing (Infiltration)
                flow_payload = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "destination_port": 4444, # Metasploit payload default
                    "flow_duration": 9000000.0, # 9 seconds persistent connection
                    "total_fwd_packets": 6,
                    "total_bwd_packets": 4,
                    "fwd_packets_s": 0.66, # extremely slow rate
                    "bwd_packets_s": 0.44,
                    "flow_bytes_s": 120.0, # tiny keep-alive command bytes
                    "packet_length_mean": 60.0,
                    "label": "Infiltration",
                    "tags": {"attack_category": "Remote_Access_Backdoor"},
                    "source": "synthetic_generator"
                }
                await send_flow(client, flow_payload)
                await asyncio.sleep(delay)
                
            step += 1
            print(f"Waiting {delay}s for next step...")
            await asyncio.sleep(delay)

if __name__ == "__main__":
    args = parse_args()
    print("====================================================")
    print("NETSOC SECURITY INTRUSION FLOW GENERATOR")
    print(f"Target API: {API_URL}")
    print("====================================================")
    
    try:
        if args.csv:
            asyncio.run(replay_csv(args.csv, args.delay))
        else:
            asyncio.run(generate_synthetic_traffic(args.delay))
    except KeyboardInterrupt:
        print("\nStopped generator.")
        sys.exit(0)
