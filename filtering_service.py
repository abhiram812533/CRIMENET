"""
CDR Graph Intelligence Platform - Filtering & Noise Reduction Engine
Preserves raw data, applies multi-dimensional filters, records precise exclusion reasons,
and provides restore capabilities.
"""
from typing import List, Dict, Any, Tuple
from datetime import datetime
from collections import defaultdict

def apply_filters(
    records: List[Dict[str, Any]],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Filters CDR records based on configurable criteria and logs reasons for every excluded record.
    Returns:
    - filtered_records: List of records that passed
    - excluded_records: List of {record, reason, filter_type}
    - summary_stats: breakdown of exclusions
    """
    date_from = config.get("date_from")
    date_to = config.get("date_to")
    time_start = config.get("time_window_start")  # "HH:MM"
    time_end = config.get("time_window_end")      # "HH:MM"
    min_duration = config.get("min_duration", 0)
    max_duration = config.get("max_duration", 86400)
    min_interactions = config.get("min_interactions", 1)
    min_edge_weight = config.get("min_edge_weight", 1)
    selected_towers = set(config.get("selected_towers") or [])
    selected_numbers = set(config.get("selected_numbers") or [])
    call_types = set(config.get("call_types") or [])
    call_statuses = set(config.get("call_statuses") or [])

    # Step 1: Pre-calculate pair interaction frequencies
    pair_counts = defaultdict(int)
    node_degrees = defaultdict(set)
    for r in records:
        pair = tuple(sorted([r["caller"], r["receiver"]]))
        pair_counts[pair] += 1
        node_degrees[r["caller"]].add(r["receiver"])
        node_degrees[r["receiver"]].add(r["caller"])

    filtered_records: List[Dict[str, Any]] = []
    excluded_records: List[Dict[str, Any]] = []
    exclusion_breakdown = defaultdict(int)

    for r in records:
        ts_str = r.get("timestamp", "")
        duration = int(r.get("duration", 0))
        caller = r.get("caller", "")
        receiver = r.get("receiver", "")
        tower = r.get("tower_id", "")
        status = r.get("call_status", "Answered")
        ctype = r.get("call_type", "Voice")
        pair = tuple(sorted([caller, receiver]))

        reasons = []

        # 1. Duration filter
        if min_duration is not None and duration < min_duration:
            reasons.append(f"Duration ({duration}s) < configured minimum ({min_duration}s)")
        if max_duration is not None and duration > max_duration:
            reasons.append(f"Duration ({duration}s) > configured maximum ({max_duration}s)")

        # 2. Date and Time-window filter
        if ts_str:
            try:
                dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                # Date check
                if date_from:
                    df = datetime.strptime(date_from[:10], "%Y-%m-%d")
                    if dt.date() < df.date():
                        reasons.append(f"Date ({dt.date()}) is before configured start ({df.date()})")
                if date_to:
                    dt_to = datetime.strptime(date_to[:10], "%Y-%m-%d")
                    if dt.date() > dt_to.date():
                        reasons.append(f"Date ({dt.date()}) is after configured end ({dt_to.date()})")

                # Time of day window check (e.g. 10:30 to 11:00)
                if time_start and time_end:
                    t_val = dt.time()
                    t_s = datetime.strptime(time_start, "%H:%M").time()
                    t_e = datetime.strptime(time_end, "%H:%M").time()
                    if not (t_s <= t_val <= t_e):
                        reasons.append(f"Time ({dt.strftime('%H:%M')}) is outside window {time_start} - {time_end}")
            except Exception:
                pass

        # 3. Pair interaction count / min edge weight
        pair_cnt = pair_counts[pair]
        effective_min_weight = max(min_interactions or 1, min_edge_weight or 1)
        if pair_cnt < effective_min_weight:
            reasons.append(f"Pair interaction count ({pair_cnt}) < minimum edge threshold ({effective_min_weight})")

        # 4. Tower filter
        if selected_towers and tower not in selected_towers:
            reasons.append(f"Tower '{tower}' not in selected investigation towers")

        # 5. Selected phone numbers filter (either caller or receiver must match)
        if selected_numbers and (caller not in selected_numbers and receiver not in selected_numbers):
            reasons.append("Neither caller nor receiver matches the selected target numbers")

        # 6. Call Status filter
        if call_statuses and status not in call_statuses:
            reasons.append(f"Call status '{status}' not included in active status filter")

        # 7. Call Type filter
        if call_types and ctype not in call_types:
            reasons.append(f"Call type '{ctype}' not included in active type filter")

        if reasons:
            primary_reason = reasons[0]
            excluded_records.append({
                "record": r,
                "reason": primary_reason,
                "all_reasons": reasons,
                "filter_type": primary_reason.split()[0]
            })
            exclusion_breakdown[primary_reason.split()[0]] += 1
        else:
            filtered_records.append(r)

    return {
        "raw_count": len(records),
        "filtered_count": len(filtered_records),
        "excluded_count": len(excluded_records),
        "filtered_records": filtered_records,
        "excluded_records": excluded_records,
        "exclusion_breakdown": dict(exclusion_breakdown)
    }
