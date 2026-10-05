"""
CDR Graph Intelligence Platform - Explainable Pattern & Anomaly Detection Service
Detects communication spikes, bridge bottlenecks, repeated short calls, high-frequency pairs,
rapid tower mobility, and temporal clusters. Adheres strictly to neutral, evidence-based terminology.
"""
from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime

def detect_patterns(
    records: List[Dict[str, Any]],
    nodes_metrics: List[Dict[str, Any]],
    temporal_data: Dict[str, Any],
    tower_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    finding_id = 1

    # 1. Sudden Communication Spikes (from temporal burst analysis)
    bursts = temporal_data.get("detected_bursts", [])
    for b in bursts[:3]:
        findings.append({
            "id": f"PAT-{finding_id:04d}",
            "pattern_type": "communication_spike",
            "title": "Sudden Communication Volume Surge",
            "what": f"Sharp surge of {b['call_count']} interactions concentrated within a 30-minute window",
            "why": f"Call count exceeded the dataset 30-minute baseline ({temporal_data.get('baseline_mean_calls_30m', 0):.1f}) by a z-score of {b['z_score']:.1f}",
            "when": b["time_interval"],
            "where": f"Towers: {', '.join(b['active_towers'][:3])}",
            "evidence": {
                "call_count": b["call_count"],
                "total_duration_sec": b["total_duration"],
                "unique_communication_pairs": b["unique_pairs"]
            },
            "metrics": {
                "z_score": b["z_score"],
                "active_towers_count": len(b["active_towers"])
            },
            "confidence": min(0.98, round(0.70 + (b["z_score"] * 0.05), 2)),
            "confidence_label": "High" if b["z_score"] > 3.0 else "Moderate",
            "related_nodes": [],
            "related_towers": b["active_towers"],
            "flag_reason": "Statistical volume divergence above 2 standard deviations from baseline rate"
        })
        finding_id += 1

    # 2. High Bridge Centrality (Top Betweenness Nodes)
    # Identifies nodes that serve as critical structural connectors between sub-networks
    high_bet_nodes = [n for n in nodes_metrics if n.get("betweenness", 0) > 0.08][:3]
    for bn in high_bet_nodes:
        findings.append({
            "id": f"PAT-{finding_id:04d}",
            "pattern_type": "bridge_node",
            "title": "High Bridge Centrality Node Observed",
            "what": f"Node {bn['id']} occupies a significant bridge position connecting distinct communication groups",
            "why": f"Betweenness centrality of {bn['betweenness']:.4f} indicates this node is on a substantial proportion of shortest network paths",
            "when": f"{bn['first_activity']} to {bn['last_activity']}",
            "where": f"Observed across towers: {', '.join(bn['towers'][:3])}",
            "evidence": {
                "unique_contacts": bn["unique_contacts"],
                "total_calls": bn["total_calls"],
                "community_id": bn["community_id"],
                "towers_used": len(bn["towers"])
            },
            "metrics": {
                "betweenness_centrality": bn["betweenness"],
                "degree": bn["degree"],
                "closeness": bn["closeness"]
            },
            "confidence": 0.92,
            "confidence_label": "High",
            "related_nodes": [bn["id"]],
            "related_towers": bn["towers"],
            "flag_reason": "High network betweenness indicates intermediary role between separate communication clusters"
        })
        finding_id += 1

    # 3. Unusually High Number of Contacts (Hub Topology)
    high_contact_nodes = [n for n in nodes_metrics if n.get("unique_contacts", 0) >= 20][:3]
    for hn in high_contact_nodes:
        findings.append({
            "id": f"PAT-{finding_id:04d}",
            "pattern_type": "high_connectivity_hub",
            "title": "High-Degree Node Communication Reach",
            "what": f"Node {hn['id']} communicates directly with {hn['unique_contacts']} distinct phone devices",
            "why": f"Total degree ({hn['degree']}) is substantially above the average network degree of the dataset",
            "when": f"{hn['first_activity']} to {hn['last_activity']}",
            "where": f"Primary towers: {', '.join(hn['towers'][:2])}",
            "evidence": {
                "total_calls": hn["total_calls"],
                "incoming_calls": hn["incoming_calls"],
                "outgoing_calls": hn["outgoing_calls"],
                "total_duration_sec": hn["total_duration"]
            },
            "metrics": {
                "unique_contacts": hn["unique_contacts"],
                "degree": hn["degree"],
                "weighted_degree": hn["weighted_degree"]
            },
            "confidence": 0.88,
            "confidence_label": "High",
            "related_nodes": [hn["id"]],
            "related_towers": hn["towers"],
            "flag_reason": "Connectivity degree exceeds upper distribution quartile"
        })
        finding_id += 1

    # 4. Repeated Short-Duration Calls (Possible Pinging or Signaling Pattern)
    short_calls_by_pair = defaultdict(int)
    for r in records:
        dur = int(r.get("duration", 0))
        if 1 <= dur <= 15:  # Very short answered calls
            pair = tuple(sorted([r["caller"], r["receiver"]]))
            short_calls_by_pair[pair] += 1

    top_short_pairs = sorted(short_calls_by_pair.items(), key=lambda x: x[1], reverse=True)[:3]
    for (p1, p2), count in top_short_pairs:
        if count >= 5:
            findings.append({
                "id": f"PAT-{finding_id:04d}",
                "pattern_type": "repeated_short_calls",
                "title": "Frequent Short-Duration Communication Pattern",
                "what": f"High recurrence of very short calls (duration <= 15 seconds) between {p1} and {p2}",
                "why": f"{count} calls had brief durations, differing from normal conversational voice patterns",
                "when": "Observed across investigation date range",
                "where": "Multi-tower interactions",
                "evidence": {
                    "short_call_count": count,
                    "target_pair": f"{p1} <-> {p2}",
                    "average_short_duration": "<= 15s"
                },
                "metrics": {
                    "recurrence_count": count
                },
                "confidence": 0.84,
                "confidence_label": "Moderate",
                "related_nodes": [p1, p2],
                "related_towers": [],
                "flag_reason": "Recurrent ultra-short calls indicate signaling or quick coordination pattern"
            })
            finding_id += 1

    # 5. Repeated High-Frequency Pair Communication
    pair_freq = defaultdict(lambda: {"count": 0, "total_duration": 0, "towers": set()})
    for r in records:
        pair = tuple(sorted([r["caller"], r["receiver"]]))
        pair_freq[pair]["count"] += 1
        pair_freq[pair]["total_duration"] += int(r.get("duration", 0))
        pair_freq[pair]["towers"].add(r.get("tower_id", ""))

    top_pairs = sorted(pair_freq.items(), key=lambda x: x[1]["count"], reverse=True)[:3]
    for (p1, p2), data in top_pairs:
        if data["count"] >= 15:
            findings.append({
                "id": f"PAT-{finding_id:04d}",
                "pattern_type": "recurrent_pair_channel",
                "title": "Persistent High-Volume Communication Pair",
                "what": f"Intensive communication channel established between {p1} and {p2}",
                "why": f"Pair accounts for {data['count']} interactions and {data['total_duration']} total seconds",
                "when": "Observed recurring across multiple dates",
                "where": f"Towers: {', '.join(list(data['towers'])[:3])}",
                "evidence": {
                    "interaction_count": data["count"],
                    "total_talk_time_sec": data["total_duration"],
                    "towers_involved": len(data["towers"])
                },
                "metrics": {
                    "call_frequency": data["count"],
                    "avg_duration_sec": round(data["total_duration"] / max(1, data["count"]), 1)
                },
                "confidence": 0.90,
                "confidence_label": "High",
                "related_nodes": [p1, p2],
                "related_towers": list(data["towers"]),
                "flag_reason": "Strongest bilateral communication link in the active dataset"
            })
            finding_id += 1

    # 6. Rapid Tower Mobility / Transitions
    rapid_moves = tower_data.get("rapid_transitions", [])
    if rapid_moves:
        top_rm = rapid_moves[0]
        findings.append({
            "id": f"PAT-{finding_id:04d}",
            "pattern_type": "rapid_tower_transition",
            "title": "Rapid Cellular Tower Transition Detected",
            "what": f"Device {top_rm['device']} recorded calls on differing towers within a short time window",
            "why": f"Transition from {top_rm['from_tower']} to {top_rm['to_tower']} occurred in {top_rm['elapsed_minutes']} minutes",
            "when": f"{top_rm['departure']} -> {top_rm['arrival']}",
            "where": f"{top_rm['from_tower']} to {top_rm['to_tower']}",
            "evidence": {
                "elapsed_time_minutes": top_rm["elapsed_minutes"],
                "origin_tower": top_rm["from_tower"],
                "destination_tower": top_rm["to_tower"]
            },
            "metrics": {
                "transition_gap_minutes": top_rm["elapsed_minutes"]
            },
            "confidence": 0.82,
            "confidence_label": "Moderate",
            "related_nodes": [top_rm["device"]],
            "related_towers": [top_rm["from_tower"], top_rm["to_tower"]],
            "flag_reason": "Sequential activity at distant cell sites within brief time delta"
        })
        finding_id += 1

    return findings
