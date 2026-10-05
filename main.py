"""
CDR Graph Intelligence Platform - FastAPI Backend
Core analytical API server providing graph construction, centrality analytics,
temporal burst detection, tower mobility tracking, OCR pipeline, and explainable intelligence.
"""
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Body, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from typing import List, Dict, Any, Optional
import json
import uuid
from datetime import datetime

from backend.models import FilterConfig, ScoreWeights, CaseRecord
from backend.synthetic_data import generate_synthetic_cdr
from backend.validation_service import validate_cdr_records
from backend.filtering_service import apply_filters
from backend.graph_service import build_communication_graph
from backend.temporal_service import analyze_temporal_patterns
from backend.tower_service import analyze_tower_activity, analyze_tower_transitions
from backend.pattern_service import detect_patterns
from backend.ocr_service import parse_csv_or_excel, process_pdf_document, process_scanned_cdr_image
from backend.export_service import generate_pdf_report, generate_csv_export

app = FastAPI(
    title="CDR Graph Intelligence Platform API",
    description="From Raw Call Records to Meaningful Communication Patterns",
    version="1.0.0"
)

# Enable CORS for local Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-Memory Session / State Store
STATE: Dict[str, Any] = {
    "raw_records": [],
    "valid_records": [],
    "filtered_records": [],
    "rejected_records": [],
    "excluded_records": [],
    "validation_report": None,
    "current_filter_config": {},
    "current_weights": {
        "degree": 0.20,
        "betweenness": 0.30,
        "closeness": 0.20,
        "frequency": 0.15,
        "recurrence": 0.15,
        "enabled": True
    },
    "graph_cache": None,
    "temporal_cache": None,
    "tower_cache": None,
    "pattern_cache": [],
    "cases": []
}

def recompute_all():
    """Recomputes graph, centrality, temporal, towers, and patterns on filtered_records."""
    records = STATE["filtered_records"]
    weights = STATE["current_weights"]
    
    # 1. Graph
    graph_res = build_communication_graph(records, weights, view_type="overview")
    STATE["graph_cache"] = graph_res

    # 2. Temporal
    temporal_res = analyze_temporal_patterns(records)
    STATE["temporal_cache"] = temporal_res

    # 3. Towers
    tower_res = analyze_tower_activity(records)
    STATE["tower_cache"] = tower_res

    # 4. Patterns
    patterns = detect_patterns(records, graph_res["nodes_metrics"], temporal_res, tower_res)
    STATE["pattern_cache"] = patterns

# Initialize automatically with 10,000 synthetic demo records on startup so platform is immediately usable
@app.on_event("startup")
def startup_init():
    load_demo_dataset()

@app.post("/api/demo/load")
def load_demo_dataset():
    """Generates and loads 10,000 synthetic realistic CDR records."""
    raw = generate_synthetic_cdr(10000)
    STATE["raw_records"] = raw
    
    # Validate
    val_res = validate_cdr_records(raw)
    STATE["valid_records"] = val_res["valid_data"]
    STATE["rejected_records"] = val_res["review_records"]
    STATE["validation_report"] = {
        "total_records": val_res["total_records"],
        "valid_records": val_res["valid_records"],
        "invalid_records": val_res["invalid_records"],
        "duplicate_records": val_res["duplicate_records"],
        "missing_field_records": val_res["missing_field_records"],
        "ocr_uncertain_records": val_res["ocr_uncertain_records"],
    }
    
    # Default filter: include all valid initially
    STATE["current_filter_config"] = {
        "min_duration": 0,
        "max_duration": 86400,
        "min_interactions": 1,
        "min_edge_weight": 1
    }
    filt_res = apply_filters(STATE["valid_records"], STATE["current_filter_config"])
    STATE["filtered_records"] = filt_res["filtered_records"]
    STATE["excluded_records"] = filt_res["excluded_records"]

    # Recompute analytics
    recompute_all()

    return {
        "status": "success",
        "message": "Demo dataset loaded successfully with 10,000 synthetic CDR records.",
        "stats": {
            "total_records": len(STATE["raw_records"]),
            "valid_records": len(STATE["valid_records"]),
            "filtered_records": len(STATE["filtered_records"]),
            "unique_nodes": STATE["graph_cache"]["stats"]["node_count"],
            "unique_edges": STATE["graph_cache"]["stats"]["edge_count"],
            "communities": STATE["graph_cache"]["stats"]["communities_count"],
            "patterns_detected": len(STATE["pattern_cache"])
        }
    }

@app.get("/api/dashboard/stats")
def get_dashboard_stats():
    """Top KPI metrics for dashboard."""
    g_stats = STATE["graph_cache"]["stats"] if STATE["graph_cache"] else {}
    t_stats = STATE["tower_cache"] if STATE["tower_cache"] else {}
    return {
        "total_records": len(STATE["raw_records"]),
        "valid_records": len(STATE["valid_records"]),
        "filtered_records": len(STATE["filtered_records"]),
        "rejected_records": len(STATE["rejected_records"]),
        "excluded_records": len(STATE["excluded_records"]),
        "unique_numbers": g_stats.get("node_count", 0),
        "active_towers": t_stats.get("total_towers", 0),
        "graph_nodes": g_stats.get("visible_nodes", 0),
        "graph_edges": g_stats.get("visible_edges", 0),
        "communities": g_stats.get("communities_count", 0),
        "patterns_count": len(STATE["pattern_cache"])
    }

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Uploads CSV, Excel, PDF, or Image CDR files."""
    contents = await file.read()
    fname = file.filename.lower()

    if fname.endswith((".csv", ".xlsx", ".xls")):
        records, cols, mapping = parse_csv_or_excel(contents, fname)
        return {
            "file_type": "tabular",
            "filename": file.filename,
            "detected_columns": cols,
            "suggested_mapping": mapping,
            "total_extracted": len(records),
            "sample_rows": records[:10]
        }
    elif fname.endswith(".pdf"):
        res = process_pdf_document(contents)
        res["filename"] = file.filename
        return res
    elif fname.endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp")):
        res = process_scanned_cdr_image(contents, is_pdf=False)
        res["filename"] = file.filename
        return res
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload CSV, XLSX, PDF, PNG, or JPG.")

@app.post("/api/confirm-import")
def confirm_import(payload: Dict[str, Any] = Body(...)):
    """Applies column mapping and saves imported records to active state."""
    raw_rows = payload.get("records", [])
    mapping = payload.get("mapping", {})

    if not raw_rows:
        raise HTTPException(status_code=400, detail="No records provided for import.")

    standardized_records = []
    for idx, r in enumerate(raw_rows):
        rec = {
            "id": f"IMP-{idx+1:06d}",
            "caller": str(r.get(mapping.get("caller") or "caller", "")),
            "receiver": str(r.get(mapping.get("receiver") or "receiver", "")),
            "timestamp": str(r.get(mapping.get("timestamp") or "timestamp", "")),
            "duration": r.get(mapping.get("duration") or "duration", 0),
            "tower_id": str(r.get(mapping.get("tower_id") or "tower_id", "TWR-MAIN")),
            "call_type": str(r.get(mapping.get("call_type") or "call_type", "Voice")),
            "call_status": str(r.get(mapping.get("call_status") or "call_status", "Answered")),
            "confidence": float(r.get("_confidence", 1.0) or 1.0)
        }
        standardized_records.append(rec)

    STATE["raw_records"] = standardized_records
    val_res = validate_cdr_records(standardized_records)
    STATE["valid_records"] = val_res["valid_data"]
    STATE["rejected_records"] = val_res["review_records"]
    STATE["validation_report"] = {
        "total_records": val_res["total_records"],
        "valid_records": val_res["valid_records"],
        "invalid_records": val_res["invalid_records"],
        "duplicate_records": val_res["duplicate_records"],
        "missing_field_records": val_res["missing_field_records"],
        "ocr_uncertain_records": val_res["ocr_uncertain_records"],
    }
    
    # Filter
    filt_res = apply_filters(STATE["valid_records"], STATE["current_filter_config"])
    STATE["filtered_records"] = filt_res["filtered_records"]
    STATE["excluded_records"] = filt_res["excluded_records"]

    recompute_all()

    return {
        "status": "success",
        "imported_count": len(standardized_records),
        "valid_count": len(STATE["valid_records"]),
        "rejected_count": len(STATE["rejected_records"])
    }

@app.get("/api/validation")
def get_validation_report():
    """Returns validation statistics and rejected records."""
    return {
        "report": STATE["validation_report"],
        "rejected_records": STATE["rejected_records"][:100],
        "total_rejected": len(STATE["rejected_records"])
    }

@app.post("/api/filter")
def set_filters(payload: FilterConfig):
    """Updates filter parameters and executes transparent noise-reduction."""
    cfg = payload.dict(exclude_unset=True)
    STATE["current_filter_config"].update(cfg)

    filt_res = apply_filters(STATE["valid_records"], STATE["current_filter_config"])
    STATE["filtered_records"] = filt_res["filtered_records"]
    STATE["excluded_records"] = filt_res["excluded_records"]

    recompute_all()

    return {
        "status": "success",
        "raw_count": filt_res["raw_count"],
        "filtered_count": filt_res["filtered_count"],
        "excluded_count": filt_res["excluded_count"],
        "exclusion_breakdown": filt_res["exclusion_breakdown"],
        "excluded_samples": filt_res["excluded_records"][:50]
    }

@app.get("/api/filtered-records")
def get_filtered_records(page: int = 1, page_size: int = 50):
    """Returns excluded records with explanation of why each record was filtered."""
    ex = STATE["excluded_records"]
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "total_excluded": len(ex),
        "page": page,
        "page_size": page_size,
        "records": ex[start:end]
    }

@app.post("/api/restore-records")
def restore_records(payload: Dict[str, Any] = Body(...)):
    """Restores selected or all excluded records back into analytical set."""
    record_ids = payload.get("record_ids", [])
    restore_all = payload.get("restore_all", False)

    if restore_all:
        STATE["filtered_records"] = list(STATE["valid_records"])
        STATE["excluded_records"] = []
    elif record_ids:
        ids_set = set(record_ids)
        restored = []
        remaining_excluded = []
        for item in STATE["excluded_records"]:
            rec = item["record"]
            if rec.get("id") in ids_set:
                restored.append(rec)
            else:
                remaining_excluded.append(item)
        STATE["filtered_records"].extend(restored)
        STATE["excluded_records"] = remaining_excluded

    recompute_all()
    return {
        "status": "success",
        "active_filtered_count": len(STATE["filtered_records"]),
        "remaining_excluded_count": len(STATE["excluded_records"])
    }

@app.post("/api/weights")
def update_score_weights(weights: ScoreWeights):
    """Updates importance score weights and recalculates."""
    STATE["current_weights"] = weights.dict()
    recompute_all()
    return {"status": "success", "weights": STATE["current_weights"]}

@app.get("/api/graph")
def get_graph(
    view_type: str = Query("overview"),
    center_node: Optional[str] = Query(None),
    hops: int = Query(1),
    community_id: Optional[int] = Query(None),
    top_n: int = Query(50),
    tower_id: Optional[str] = Query(None)
):
    """
    Returns graph elements for Cytoscape.js supporting:
    - overview, filtered, top_n, time_window, tower_linked, ego, community
    """
    view_params = {
        "center_node": center_node,
        "hops": hops,
        "community_id": community_id,
        "top_n": top_n,
        "tower_id": tower_id
    }
    graph_data = build_communication_graph(
        STATE["filtered_records"],
        STATE["current_weights"],
        view_type=view_type,
        view_params=view_params
    )
    return graph_data

@app.get("/api/nodes/{node_id}")
def get_node_details(node_id: str):
    """Returns comprehensive details and evidence for a specific node."""
    if not STATE["graph_cache"]:
        raise HTTPException(status_code=404, detail="Graph not initialized")

    matched = next((n for n in STATE["graph_cache"]["nodes_metrics"] if n["id"] == node_id), None)
    if not matched:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found in active graph.")

    # Find node's direct edges
    incident_edges = [
        e for e in STATE["graph_cache"]["edges_metrics"]
        if e["source"] == node_id or e["target"] == node_id
    ]

    return {
        "node": matched,
        "incident_edges": incident_edges,
        "incident_edge_count": len(incident_edges)
    }

@app.get("/api/centrality")
def get_centrality_table(page: int = 1, page_size: int = 50, sort_by: str = "importance_score"):
    """Returns centrality comparison table for all nodes."""
    if not STATE["graph_cache"]:
        return {"nodes": [], "total": 0}
    nodes = list(STATE["graph_cache"]["nodes_metrics"])
    
    reverse = True
    if sort_by in nodes[0]:
        nodes.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)

    start = (page - 1) * page_size
    end = start + page_size
    return {
        "total": len(nodes),
        "page": page,
        "page_size": page_size,
        "nodes": nodes[start:end]
    }

@app.get("/api/communities")
def get_communities():
    """Returns communication clusters / communities."""
    if not STATE["graph_cache"]:
        return {"communities": []}
    return {"communities": STATE["graph_cache"]["communities"]}

@app.get("/api/timeline")
def get_timeline():
    """Returns daily/hourly timelines, burst events, and peaks."""
    if not STATE["temporal_cache"]:
        return {"daily_trend": [], "hourly_distribution": [], "detected_bursts": []}
    return STATE["temporal_cache"]

@app.get("/api/towers")
def get_towers():
    """Returns cellular tower metrics and geographical data."""
    if not STATE["tower_cache"]:
        return {"towers": []}
    return STATE["tower_cache"]

@app.get("/api/towers/transitions")
def get_tower_transitions():
    """Returns sequential tower mobility transitions."""
    return analyze_tower_transitions(STATE["filtered_records"])

@app.get("/api/patterns")
def get_patterns():
    """Returns detected patterns with explainable evidence."""
    return {"patterns": STATE["pattern_cache"]}

# Case Workspace Management
@app.post("/api/cases")
def create_case(payload: CaseRecord):
    """Creates a new case investigation record."""
    c_dict = payload.dict()
    if not c_dict.get("case_id"):
        c_dict["case_id"] = f"CASE-{len(STATE['cases'])+1:04d}"
    c_dict["created_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    STATE["cases"].append(c_dict)
    return {"status": "success", "case": c_dict}

@app.get("/api/cases")
def list_cases():
    """Lists saved investigation cases."""
    return {"cases": STATE["cases"]}

@app.get("/api/cases/{case_id}")
def get_case(case_id: str):
    """Retrieves case details."""
    c = next((item for item in STATE["cases"] if item["case_id"] == case_id), None)
    if not c:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"case": c}

# Report & Export Generation
@app.post("/api/reports/pdf")
def download_pdf_report(payload: Optional[Dict[str, Any]] = Body(None)):
    """Generates and downloads formal PDF report."""
    g_stats = STATE["graph_cache"]["stats"] if STATE["graph_cache"] else {}
    t_stats = STATE["tower_cache"] if STATE["tower_cache"] else {}
    
    report_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stats": {
            "total_records": len(STATE["raw_records"]),
            "valid_records": len(STATE["valid_records"]),
            "filtered_count": len(STATE["excluded_records"]),
            "node_count": g_stats.get("node_count", 0),
            "edge_count": g_stats.get("edge_count", 0),
            "tower_count": t_stats.get("total_towers", 0),
            "communities_count": g_stats.get("communities_count", 0)
        },
        "top_nodes": STATE["graph_cache"]["nodes_metrics"][:10] if STATE["graph_cache"] else [],
        "patterns": STATE["pattern_cache"]
    }
    
    pdf_bytes = generate_pdf_report(report_data)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=CDR_Graph_Intelligence_Report.pdf"}
    )

@app.get("/api/export/csv")
def download_csv_export():
    """Exports active filtered dataset as CSV."""
    csv_str = generate_csv_export(STATE["filtered_records"][:5000])
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=filtered_cdr_dataset.csv"}
    )
