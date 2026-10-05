"""
CDR Graph Intelligence Platform - Data Validation Service
Validates CDR records, identifies anomalies, keeps rejected/review records with exact reasons.
"""
import re
from typing import List, Dict, Any, Tuple
from datetime import datetime

PHONE_REGEX = re.compile(r"^\+?[0-9]{7,15}$")

def parse_flexible_timestamp(val: Any) -> Tuple[bool, str]:
    if not val:
        return False, "Timestamp is missing"
    val_str = str(val).strip()
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d/%m/%Y %H:%M",
        "%Y/%m/%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(val_str, fmt)
            return True, dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    return False, f"Invalid date/time format: '{val_str}'"

def validate_cdr_records(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    valid_records: List[Dict[str, Any]] = []
    rejected_records: List[Dict[str, Any]] = []
    
    duplicate_count = 0
    missing_field_count = 0
    invalid_count = 0
    ocr_uncertain_count = 0
    
    seen_keys = set()

    for idx, raw in enumerate(records):
        rec = dict(raw)
        # Check OCR confidence flag
        conf = float(rec.get("confidence", 1.0) or 1.0)
        is_ocr_uncertain = conf < 0.75
        if is_ocr_uncertain:
            ocr_uncertain_count += 1

        caller = str(rec.get("caller", "") or "").strip()
        receiver = str(rec.get("receiver", "") or "").strip()
        ts_val = rec.get("timestamp")
        duration_val = rec.get("duration")
        tower_id = str(rec.get("tower_id", "") or "").strip()

        # Check missing critical fields
        if not caller or not receiver or ts_val is None or duration_val is None:
            missing_fields = []
            if not caller: missing_fields.append("caller")
            if not receiver: missing_fields.append("receiver")
            if ts_val is None: missing_fields.append("timestamp")
            if duration_val is None: missing_fields.append("duration")
            missing_field_count += 1
            rejected_records.append({
                "record": rec,
                "record_index": idx + 1,
                "category": "missing_field",
                "reason": f"Missing required fields: {', '.join(missing_fields)}"
            })
            continue

        # Check phone format
        clean_caller = caller.replace(" ", "").replace("-", "")
        clean_receiver = receiver.replace(" ", "").replace("-", "")
        if not PHONE_REGEX.match(clean_caller):
            invalid_count += 1
            rejected_records.append({
                "record": rec,
                "record_index": idx + 1,
                "category": "invalid_phone",
                "reason": f"Invalid caller phone number format: '{caller}'"
            })
            continue
        if not PHONE_REGEX.match(clean_receiver):
            invalid_count += 1
            rejected_records.append({
                "record": rec,
                "record_index": idx + 1,
                "category": "invalid_phone",
                "reason": f"Invalid receiver phone number format: '{receiver}'"
            })
            continue

        # Check self-call
        if clean_caller == clean_receiver:
            invalid_count += 1
            rejected_records.append({
                "record": rec,
                "record_index": idx + 1,
                "category": "self_call",
                "reason": f"Self-call detected: Caller and receiver are identical ({clean_caller})"
            })
            continue

        # Parse & check timestamp
        ts_ok, ts_norm_or_err = parse_flexible_timestamp(ts_val)
        if not ts_ok:
            invalid_count += 1
            rejected_records.append({
                "record": rec,
                "record_index": idx + 1,
                "category": "invalid_timestamp",
                "reason": ts_norm_or_err
            })
            continue
        rec["timestamp"] = ts_norm_or_err

        # Check duration
        try:
            dur = int(float(str(duration_val).strip()))
            if dur < 0 or dur > 86400:
                invalid_count += 1
                rejected_records.append({
                    "record": rec,
                    "record_index": idx + 1,
                    "category": "impossible_duration",
                    "reason": f"Impossible duration value: {dur} seconds (must be 0-86400)"
                })
                continue
            rec["duration"] = dur
        except Exception:
            invalid_count += 1
            rejected_records.append({
                "record": rec,
                "record_index": idx + 1,
                "category": "impossible_duration",
                "reason": f"Non-numeric duration format: '{duration_val}'"
            })
            continue

        # Check Tower ID
        if not tower_id:
            invalid_count += 1
            rejected_records.append({
                "record": rec,
                "record_index": idx + 1,
                "category": "invalid_tower",
                "reason": "Missing or blank Tower ID / Cell ID"
            })
            continue

        # Check duplicate
        dedup_key = (clean_caller, clean_receiver, rec["timestamp"])
        if dedup_key in seen_keys:
            duplicate_count += 1
            rejected_records.append({
                "record": rec,
                "record_index": idx + 1,
                "category": "duplicate",
                "reason": f"Exact duplicate record found for {clean_caller} -> {clean_receiver} at {rec['timestamp']}"
            })
            continue
        seen_keys.add(dedup_key)

        rec["caller"] = clean_caller
        rec["receiver"] = clean_receiver
        if not rec.get("id"):
            rec["id"] = f"REC-{idx+1:06d}"

        valid_records.append(rec)

    return {
        "total_records": len(records),
        "valid_records": len(valid_records),
        "invalid_records": len(rejected_records),
        "duplicate_records": duplicate_count,
        "missing_field_records": missing_field_count,
        "ocr_uncertain_records": ocr_uncertain_count,
        "valid_data": valid_records,
        "review_records": rejected_records
    }
