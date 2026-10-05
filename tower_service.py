"""
CDR Graph Intelligence Platform - Tower & Location Analysis Service
Aggregates cellular tower metrics, detects sequential tower transitions (mobility paths),
and provides data for geospatial visualizations.
"""
from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime

def analyze_tower_activity(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes tower metrics:
    - Tower ID, name, lat/lon
    - Unique devices observed
    - Total calls, incoming, outgoing, duration
    - Active hours distribution
    - Top devices active at each tower
    """
    tower_stats = defaultdict(lambda: {
        "tower_id": "",
        "tower_name": "",
        "latitude": None,
        "longitude": None,
        "address": "",
        "unique_devices": set(),
        "total_calls": 0,
        "incoming_calls": 0,
        "outgoing_calls": 0,
        "total_duration": 0,
        "hourly_distribution": defaultdict(int),
        "device_calls": defaultdict(int)
    })

    for r in records:
        t_id = r.get("tower_id") or "UNKNOWN"
        caller = r.get("caller", "")
        receiver = r.get("receiver", "")
        dur = int(r.get("duration", 0))
        ts_str = r.get("timestamp", "")
        t_name = r.get("tower_name") or f"Tower {t_id}"
        lat = r.get("latitude")
        lon = r.get("longitude")
        addr = r.get("tower_address") or ""

        t = tower_stats[t_id]
        t["tower_id"] = t_id
        t["tower_name"] = t_name
        if lat is not None: t["latitude"] = float(lat)
        if lon is not None: t["longitude"] = float(lon)
        if addr: t["address"] = addr

        t["total_calls"] += 1
        t["outgoing_calls"] += 1
        t["incoming_calls"] += 1
        t["total_duration"] += dur
        t["unique_devices"].add(caller)
        t["unique_devices"].add(receiver)
        t["device_calls"][caller] += 1
        t["device_calls"][receiver] += 1

        if ts_str and len(ts_str) >= 13:
            try:
                hr = int(ts_str[11:13])
                t["hourly_distribution"][hr] += 1
            except Exception:
                pass

    towers_list = []
    for t_id, data in tower_stats.items():
        # Top 5 devices
        top_devs = sorted(data["device_calls"].items(), key=lambda x: x[1], reverse=True)[:5]
        hours_active = [data["hourly_distribution"].get(h, 0) for h in range(24)]

        towers_list.append({
            "tower_id": t_id,
            "tower_name": data["tower_name"],
            "latitude": data["latitude"],
            "longitude": data["longitude"],
            "address": data["address"],
            "unique_devices": len(data["unique_devices"]),
            "total_calls": data["total_calls"],
            "incoming_calls": data["incoming_calls"],
            "outgoing_calls": data["outgoing_calls"],
            "total_duration": data["total_duration"],
            "avg_duration": round(data["total_duration"] / max(1, data["total_calls"]), 1),
            "active_hours": hours_active,
            "top_devices": [{"phone": p, "calls": c} for p, c in top_devs]
        })

    towers_list.sort(key=lambda x: x["total_calls"], reverse=True)
    return {
        "towers": towers_list,
        "total_towers": len(towers_list),
        "disclaimer": "Tower association is presented as recorded/observed network data, not guaranteed exact physical GPS location."
    }

def analyze_tower_transitions(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Identifies sequential tower movements per device:
    e.g. Device X at TWR-101 at 10:00 -> TWR-102 at 10:45.
    Constructs a directed transition graph.
    """
    # Group records by device (caller) sorted by timestamp
    device_events = defaultdict(list)
    for r in records:
        ts_str = r.get("timestamp")
        t_id = r.get("tower_id")
        caller = r.get("caller")
        if ts_str and t_id and caller:
            try:
                dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                device_events[caller].append((dt, t_id))
            except Exception:
                pass

    transitions_map = {}
    rapid_device_transitions = []

    for device, events in device_events.items():
        events.sort(key=lambda x: x[0])
        # Find consecutive differing towers
        for i in range(len(events) - 1):
            t1, tower1 = events[i]
            t2, tower2 = events[i + 1]
            if tower1 != tower2:
                gap_sec = (t2 - t1).total_seconds()
                # Ignore transitions across massive time gaps (> 24 hours) for immediate transit
                if gap_sec < 86400:
                    key = (tower1, tower2)
                    if key not in transitions_map:
                        transitions_map[key] = {
                            "source_tower": tower1,
                            "target_tower": tower2,
                            "transition_count": 0,
                            "unique_devices": set(),
                            "gap_sum": 0,
                            "first_observed": t1.strftime("%Y-%m-%d %H:%M:%S"),
                            "last_observed": t2.strftime("%Y-%m-%d %H:%M:%S")
                        }
                    trans = transitions_map[key]
                    trans["transition_count"] += 1
                    trans["unique_devices"].add(device)
                    trans["gap_sum"] += gap_sec
                    if t2.strftime("%Y-%m-%d %H:%M:%S") > trans["last_observed"]:
                        trans["last_observed"] = t2.strftime("%Y-%m-%d %H:%M:%S")

                    # Flag rapid jump (< 30 minutes)
                    if gap_sec < 1800:
                        rapid_device_transitions.append({
                            "device": device,
                            "from_tower": tower1,
                            "to_tower": tower2,
                            "departure": t1.strftime("%Y-%m-%d %H:%M:%S"),
                            "arrival": t2.strftime("%Y-%m-%d %H:%M:%S"),
                            "elapsed_minutes": round(gap_sec / 60, 1)
                        })

    transitions_list = []
    for (src, tgt), data in transitions_map.items():
        cnt = data["transition_count"]
        transitions_list.append({
            "source_tower": src,
            "target_tower": tgt,
            "transition_count": cnt,
            "unique_devices": len(data["unique_devices"]),
            "avg_gap_minutes": round((data["gap_sum"] / max(1, cnt)) / 60, 1),
            "first_observed": data["first_observed"],
            "last_observed": data["last_observed"]
        })

    transitions_list.sort(key=lambda x: x["transition_count"], reverse=True)

    return {
        "transitions": transitions_list,
        "rapid_transitions": rapid_device_transitions[:20],
        "total_transitions_detected": len(transitions_list)
    }
