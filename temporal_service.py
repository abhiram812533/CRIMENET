"""
CDR Graph Intelligence Platform - Temporal Analysis Service
Analyzes communication timelines, hourly histograms, burst communication events,
and temporal structure changes.
"""
from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime
import math

def analyze_temporal_patterns(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not records:
        return {
            "daily_trend": [],
            "hourly_distribution": [{"hour": h, "call_count": 0, "total_duration": 0} for h in range(24)],
            "detected_bursts": [],
            "peak_window": "N/A",
            "total_period": "N/A"
        }

    daily_counts = defaultdict(lambda: {"calls": 0, "duration": 0, "unique_callers": set(), "unique_receivers": set()})
    hourly_counts = defaultdict(lambda: {"calls": 0, "duration": 0, "unique_devices": set()})
    
    # 30-minute bucket for micro-burst analysis
    interval_counts = defaultdict(lambda: {"calls": 0, "duration": 0, "pairs": set(), "towers": set()})

    timestamps = []

    for r in records:
        ts_str = r.get("timestamp")
        if not ts_str:
            continue
        try:
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            timestamps.append(dt)
            day = dt.strftime("%Y-%m-%d")
            hour = dt.hour
            dur = int(r.get("duration", 0))
            caller = r.get("caller", "")
            receiver = r.get("receiver", "")
            tower = r.get("tower_id", "")

            # Daily
            d_entry = daily_counts[day]
            d_entry["calls"] += 1
            d_entry["duration"] += dur
            d_entry["unique_callers"].add(caller)
            d_entry["unique_receivers"].add(receiver)

            # Hourly
            h_entry = hourly_counts[hour]
            h_entry["calls"] += 1
            h_entry["duration"] += dur
            h_entry["unique_devices"].add(caller)
            h_entry["unique_devices"].add(receiver)

            # Interval 30m
            minute_bucket = (dt.minute // 30) * 30
            int_key = f"{day} {dt.hour:02d}:{minute_bucket:02d}"
            i_entry = interval_counts[int_key]
            i_entry["calls"] += 1
            i_entry["duration"] += dur
            i_entry["pairs"].add(tuple(sorted([caller, receiver])))
            i_entry["towers"].add(tower)

        except Exception:
            continue

    # Format daily trend
    daily_trend = []
    for day in sorted(daily_counts.keys()):
        d = daily_counts[day]
        unique_nodes = len(d["unique_callers"].union(d["unique_receivers"]))
        daily_trend.append({
            "date": day,
            "calls": d["calls"],
            "total_duration": d["duration"],
            "unique_devices": unique_nodes,
            "avg_duration": round(d["duration"] / max(1, d["calls"]), 1)
        })

    # Format 24-hour distribution
    hourly_distribution = []
    for h in range(24):
        he = hourly_counts[h]
        hourly_distribution.append({
            "hour": f"{h:02d}:00",
            "call_count": he["calls"],
            "total_duration": he["duration"],
            "unique_devices": len(he["unique_devices"]),
            "avg_duration": round(he["duration"] / max(1, he["calls"]), 1) if he["calls"] > 0 else 0
        })

    # Detect Communication Bursts (intervals where call count > mean + 2 * std)
    counts = [v["calls"] for v in interval_counts.values()]
    mean_val = sum(counts) / max(1, len(counts)) if counts else 0
    variance = sum((c - mean_val) ** 2 for c in counts) / max(1, len(counts)) if counts else 0
    std_val = math.sqrt(variance)
    burst_threshold = mean_val + max(10, 2.0 * std_val)

    detected_bursts = []
    for interval_key, iv in interval_counts.items():
        if iv["calls"] >= burst_threshold:
            detected_bursts.append({
                "time_interval": interval_key,
                "call_count": iv["calls"],
                "total_duration": iv["duration"],
                "unique_pairs": len(iv["pairs"]),
                "active_towers": list(iv["towers"]),
                "z_score": round((iv["calls"] - mean_val) / max(1.0, std_val), 2),
                "description": f"Communication surge detected with {iv['calls']} interactions across {len(iv['towers'])} cellular towers."
            })
    detected_bursts.sort(key=lambda x: x["call_count"], reverse=True)

    # Time range
    total_period = "N/A"
    if timestamps:
        min_ts = min(timestamps).strftime("%Y-%m-%d %H:%M")
        max_ts = max(timestamps).strftime("%Y-%m-%d %H:%M")
        total_period = f"{min_ts} to {max_ts}"

    # Peak hour
    peak_hr = max(hourly_distribution, key=lambda x: x["call_count"]) if hourly_distribution else {"hour": "N/A", "call_count": 0}

    return {
        "daily_trend": daily_trend,
        "hourly_distribution": hourly_distribution,
        "detected_bursts": detected_bursts[:10],
        "peak_window": f"{peak_hr['hour']} ({peak_hr['call_count']} calls)",
        "total_period": total_period,
        "baseline_mean_calls_30m": round(mean_val, 1),
        "burst_threshold_30m": round(burst_threshold, 1)
    }
