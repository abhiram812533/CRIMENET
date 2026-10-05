"""
CDR Graph Intelligence Platform - Synthetic Realistic Data Generator
Generates 10,000 structured CDR records with clear communities, bridge nodes,
burst time windows, and realistic tower coordinates.
"""
import random
import datetime
from typing import List, Dict, Any

# Realistic tower locations with names and coordinates (Delhi NCR / Urban Metro)
TOWERS = [
    {"tower_id": "TWR-101", "tower_name": "Connaught Place Central", "lat": 28.6315, "lon": 77.2167, "address": "Block B, CP, New Delhi"},
    {"tower_id": "TWR-102", "tower_name": "South Extension Hub", "lat": 28.5729, "lon": 77.2215, "address": "Ring Road, South Ext II"},
    {"tower_id": "TWR-103", "tower_name": "Cyber City Gateway", "lat": 28.4952, "lon": 77.0895, "address": "DLF Cyber City, Sector 24"},
    {"tower_id": "TWR-104", "tower_name": "Noida Sector 18 Commercial", "lat": 28.5708, "lon": 77.3261, "address": "Atta Market, Sector 18"},
    {"tower_id": "TWR-105", "tower_name": "Indira Gandhi Airport T3", "lat": 28.5562, "lon": 77.1000, "address": "Terminal 3 Arrival, Palam"},
    {"tower_id": "TWR-106", "tower_name": "Rohini Sector 10 Hub", "lat": 28.7166, "lon": 77.1126, "address": "Swarn Jayanti Park, Rohini"},
    {"tower_id": "TWR-107", "tower_name": "Nehru Place Tech Center", "lat": 28.5494, "lon": 77.2533, "address": "Kalkaji, Nehru Place"},
    {"tower_id": "TWR-108", "tower_name": "Chandni Chowk North", "lat": 28.6562, "lon": 77.2300, "address": "Old Delhi Main Road"},
    {"tower_id": "TWR-109", "tower_name": "Saket District Centre", "lat": 28.5244, "lon": 77.2167, "address": "Press Enclave Marg, Saket"},
    {"tower_id": "TWR-110", "tower_name": "Dwarka Sector 21 Junction", "lat": 28.5522, "lon": 77.0583, "address": "Pacific D21, Dwarka"},
]

PROVIDERS = ["Airtel", "Jio", "Vodafone-Idea", "BSNL"]
CALL_TYPES = ["Voice", "Voice", "Voice", "SMS"]
CALL_STATUSES = ["Answered", "Answered", "Answered", "Answered", "Missed", "Failed"]

def generate_synthetic_cdr(record_count: int = 10000) -> List[Dict[str, Any]]:
    """
    Creates 10,000 records structured with:
    - 4 distinct dense communication clusters
    - 3 specific 'bridge' nodes connecting clusters (high betweenness)
    - 2 highly connected 'hub' nodes (high degree)
    - A temporal burst window on 2026-01-15 10:30 - 11:00
    - A rapid tower transition sequence for specific devices
    - Realistic phone numbers (MSISDN)
    """
    random.seed(42)  # Deterministic generation for consistency

    # Define communities with phone numbers
    community_nodes = {
        "cluster_1": [f"+9198110{i:04d}" for i in range(101, 131)],  # 30 nodes (Central/CP)
        "cluster_2": [f"+9198220{i:04d}" for i in range(201, 231)],  # 30 nodes (South/Saket)
        "cluster_3": [f"+9198330{i:04d}" for i in range(301, 331)],  # 30 nodes (Cyber City/Airport)
        "cluster_4": [f"+9198440{i:04d}" for i in range(401, 431)],  # 30 nodes (Noida/East)
    }

    # Special designated nodes for graph properties:
    bridge_node_1 = "+919899090001"  # Bridges Cluster 1 & Cluster 2
    bridge_node_2 = "+919899090002"  # Bridges Cluster 2 & Cluster 3
    hub_node_prime = "+919899099999" # Connects widely across all clusters

    all_nodes = []
    for c_nodes in community_nodes.values():
        all_nodes.extend(c_nodes)
    all_nodes.extend([bridge_node_1, bridge_node_2, hub_node_prime])

    records: List[Dict[str, Any]] = []

    start_date = datetime.datetime(2026, 1, 1, 0, 0, 0)
    end_date = datetime.datetime(2026, 1, 31, 23, 59, 59)
    total_seconds = int((end_date - start_date).total_seconds())

    # 1. Generate intra-cluster communication (6,000 records)
    for c_name, nodes in community_nodes.items():
        # Match towers with clusters
        if c_name == "cluster_1":
            pref_towers = ["TWR-101", "TWR-108", "TWR-106"]
        elif c_name == "cluster_2":
            pref_towers = ["TWR-102", "TWR-107", "TWR-109"]
        elif c_name == "cluster_3":
            pref_towers = ["TWR-103", "TWR-105", "TWR-110"]
        else:
            pref_towers = ["TWR-104", "TWR-107", "TWR-101"]

        for _ in range(1500):
            caller = random.choice(nodes)
            receiver = random.choice([n for n in nodes if n != caller])
            
            # Random time across month
            rand_sec = random.randint(0, total_seconds)
            ts = start_date + datetime.timedelta(seconds=rand_sec)
            
            call_type = random.choice(CALL_TYPES)
            call_status = random.choice(CALL_STATUSES)
            duration = 0 if call_status in ["Missed", "Failed"] else (1 if call_type == "SMS" else random.randint(15, 620))
            
            t_id = random.choice(pref_towers)
            tower = next(t for t in TOWERS if t["tower_id"] == t_id)

            records.append({
                "id": f"REC-{len(records)+1:06d}",
                "caller": caller,
                "receiver": receiver,
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "duration": duration,
                "tower_id": t_id,
                "call_type": call_type,
                "call_status": call_status,
                "tower_name": tower["tower_name"],
                "latitude": tower["lat"],
                "longitude": tower["lon"],
                "tower_address": tower["address"],
                "network_provider": random.choice(PROVIDERS),
                "imsi": f"40445{random.randint(1000000000, 9999999999)}",
                "imei": f"86420{random.randint(1000000000, 9999999999)}",
                "cell_id": f"CID-{random.randint(1000, 9999)}",
                "confidence": 1.0
            })

    # 2. Bridge Nodes interactions (1,200 records)
    for _ in range(600):
        # Bridge 1 connects Cluster 1 and Cluster 2
        is_caller = random.random() > 0.5
        c1_target = random.choice(community_nodes["cluster_1"])
        c2_target = random.choice(community_nodes["cluster_2"])
        
        caller = bridge_node_1 if is_caller else random.choice([c1_target, c2_target])
        receiver = random.choice([c1_target, c2_target]) if is_caller else bridge_node_1
        if caller == receiver:
            receiver = c2_target

        ts = start_date + datetime.timedelta(seconds=random.randint(0, total_seconds))
        t_id = random.choice(["TWR-101", "TWR-102"])
        tower = next(t for t in TOWERS if t["tower_id"] == t_id)
        
        records.append({
            "id": f"REC-{len(records)+1:06d}",
            "caller": caller,
            "receiver": receiver,
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": random.randint(30, 750),
            "tower_id": t_id,
            "call_type": "Voice",
            "call_status": "Answered",
            "tower_name": tower["tower_name"],
            "latitude": tower["lat"],
            "longitude": tower["lon"],
            "tower_address": tower["address"],
            "network_provider": "Airtel",
            "imsi": f"404459990011223",
            "imei": f"864209990011223",
            "cell_id": f"CID-8891",
            "confidence": 1.0
        })

    for _ in range(600):
        # Bridge 2 connects Cluster 2 and Cluster 3
        is_caller = random.random() > 0.5
        c2_target = random.choice(community_nodes["cluster_2"])
        c3_target = random.choice(community_nodes["cluster_3"])
        
        caller = bridge_node_2 if is_caller else random.choice([c2_target, c3_target])
        receiver = random.choice([c2_target, c3_target]) if is_caller else bridge_node_2
        if caller == receiver:
            receiver = c3_target

        ts = start_date + datetime.timedelta(seconds=random.randint(0, total_seconds))
        t_id = random.choice(["TWR-102", "TWR-103", "TWR-105"])
        tower = next(t for t in TOWERS if t["tower_id"] == t_id)
        
        records.append({
            "id": f"REC-{len(records)+1:06d}",
            "caller": caller,
            "receiver": receiver,
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": random.randint(45, 900),
            "tower_id": t_id,
            "call_type": "Voice",
            "call_status": "Answered",
            "tower_name": tower["tower_name"],
            "latitude": tower["lat"],
            "longitude": tower["lon"],
            "tower_address": tower["address"],
            "network_provider": "Jio",
            "imsi": f"404459990022334",
            "imei": f"864209990022334",
            "cell_id": f"CID-8892",
            "confidence": 1.0
        })

    # 3. Hub Node Prime interactions (800 records)
    for _ in range(800):
        target = random.choice(all_nodes[:100])
        is_outgoing = random.random() > 0.4
        caller = hub_node_prime if is_outgoing else target
        receiver = target if is_outgoing else hub_node_prime
        
        ts = start_date + datetime.timedelta(seconds=random.randint(0, total_seconds))
        t_id = random.choice([t["tower_id"] for t in TOWERS])
        tower = next(t for t in TOWERS if t["tower_id"] == t_id)
        
        records.append({
            "id": f"REC-{len(records)+1:06d}",
            "caller": caller,
            "receiver": receiver,
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": random.randint(20, 500),
            "tower_id": t_id,
            "call_type": "Voice",
            "call_status": "Answered",
            "tower_name": tower["tower_name"],
            "latitude": tower["lat"],
            "longitude": tower["lon"],
            "tower_address": tower["address"],
            "network_provider": "Vodafone-Idea",
            "imsi": f"404459999999999",
            "imei": f"864209999999999",
            "cell_id": f"CID-9999",
            "confidence": 1.0
        })

    # 4. Concentrated Burst Event: 2026-01-15 10:30 to 11:00 (500 records)
    burst_base = datetime.datetime(2026, 1, 15, 10, 30, 0)
    for _ in range(500):
        sec_offset = random.randint(0, 1799)  # 30-minute window
        ts = burst_base + datetime.timedelta(seconds=sec_offset)
        
        # High activity between Cluster 1 and Cluster 3 nodes
        caller = random.choice(community_nodes["cluster_1"][:10])
        receiver = random.choice(community_nodes["cluster_3"][:10])
        t_id = "TWR-101"  # Concentrated at Connaught Place
        tower = next(t for t in TOWERS if t["tower_id"] == t_id)
        
        records.append({
            "id": f"REC-{len(records)+1:06d}",
            "caller": caller,
            "receiver": receiver,
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": random.randint(15, 180),
            "tower_id": t_id,
            "call_type": "Voice",
            "call_status": "Answered",
            "tower_name": tower["tower_name"],
            "latitude": tower["lat"],
            "longitude": tower["lon"],
            "tower_address": tower["address"],
            "network_provider": "Airtel",
            "imsi": f"40445{random.randint(1000000000, 9999999999)}",
            "imei": f"86420{random.randint(1000000000, 9999999999)}",
            "cell_id": "CID-BURST-01",
            "confidence": 1.0
        })

    # 5. Device Sequential Movement / Tower Transitions (400 records)
    # Target phone moving rapidly across city: TWR-105 (Airport) -> TWR-103 (Cyber City) -> TWR-102 (South Ext) -> TWR-101 (CP)
    traveling_phone = "+919876543210"
    journey_times = [
        datetime.datetime(2026, 1, 10, 9, 0, 0),
        datetime.datetime(2026, 1, 10, 10, 15, 0),
        datetime.datetime(2026, 1, 10, 11, 45, 0),
        datetime.datetime(2026, 1, 10, 13, 0, 0),
    ]
    journey_towers = ["TWR-105", "TWR-103", "TWR-102", "TWR-101"]
    for j in range(len(journey_times)):
        t_id = journey_towers[j]
        tower = next(t for t in TOWERS if t["tower_id"] == t_id)
        for call_idx in range(10):
            ts = journey_times[j] + datetime.timedelta(minutes=call_idx * 3)
            records.append({
                "id": f"REC-{len(records)+1:06d}",
                "caller": traveling_phone,
                "receiver": random.choice(all_nodes[:20]),
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "duration": random.randint(45, 300),
                "tower_id": t_id,
                "call_type": "Voice",
                "call_status": "Answered",
                "tower_name": tower["tower_name"],
                "latitude": tower["lat"],
                "longitude": tower["lon"],
                "tower_address": tower["address"],
                "network_provider": "Jio",
                "imsi": "404457778889990",
                "imei": "864207778889990",
                "cell_id": f"CID-MOV-{j}",
                "confidence": 1.0
            })

    # 6. Fill remaining records up to 10,000 with realistic peripheral / background traffic
    remaining = record_count - len(records)
    for _ in range(max(0, remaining)):
        caller = random.choice(all_nodes)
        receiver = random.choice([n for n in all_nodes if n != caller])
        ts = start_date + datetime.timedelta(seconds=random.randint(0, total_seconds))
        t_id = random.choice([t["tower_id"] for t in TOWERS])
        tower = next(t for t in TOWERS if t["tower_id"] == t_id)
        call_type = random.choice(CALL_TYPES)
        call_status = random.choice(CALL_STATUSES)
        duration = 0 if call_status in ["Missed", "Failed"] else random.randint(10, 480)
        
        records.append({
            "id": f"REC-{len(records)+1:06d}",
            "caller": caller,
            "receiver": receiver,
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": duration,
            "tower_id": t_id,
            "call_type": call_type,
            "call_status": call_status,
            "tower_name": tower["tower_name"],
            "latitude": tower["lat"],
            "longitude": tower["lon"],
            "tower_address": tower["address"],
            "network_provider": random.choice(PROVIDERS),
            "imsi": f"40445{random.randint(1000000000, 9999999999)}",
            "imei": f"86420{random.randint(1000000000, 9999999999)}",
            "cell_id": f"CID-{random.randint(1000, 9999)}",
            "confidence": 1.0
        })

    return records[:record_count]
