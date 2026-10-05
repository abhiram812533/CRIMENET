"""
CDR Graph Intelligence Platform - Data Models
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class CDRRecord(BaseModel):
    id: Optional[str] = None
    caller: str
    receiver: str
    timestamp: str  # ISO string or YYYY-MM-DD HH:MM:SS
    duration: int   # seconds
    tower_id: str
    call_type: Optional[str] = "Voice"
    imsi: Optional[str] = None
    imei: Optional[str] = None
    cell_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tower_name: Optional[str] = None
    tower_address: Optional[str] = None
    network_provider: Optional[str] = None
    call_status: Optional[str] = "Answered"
    confidence: Optional[float] = 1.0
    ocr_flags: Optional[Dict[str, Any]] = None

class ValidationItem(BaseModel):
    record: Dict[str, Any]
    reason: str
    category: str  # invalid_phone, missing_field, invalid_timestamp, impossible_duration, duplicate, self_call, invalid_tower

class ValidationReport(BaseModel):
    total_records: int
    valid_records: int
    invalid_records: int
    duplicate_records: int
    missing_field_records: int
    ocr_uncertain_records: int
    review_records: List[ValidationItem]

class FilterConfig(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    time_window_start: Optional[str] = None  # "HH:MM" e.g. "10:30"
    time_window_end: Optional[str] = None    # "HH:MM" e.g. "11:00"
    min_duration: Optional[int] = 0
    max_duration: Optional[int] = 86400
    min_interactions: Optional[int] = 1
    min_edge_weight: Optional[int] = 1
    min_node_degree: Optional[int] = 1
    top_n_percent: Optional[int] = 100
    repeated_interaction_threshold: Optional[int] = 1
    selected_towers: Optional[List[str]] = None
    selected_numbers: Optional[List[str]] = None
    call_types: Optional[List[str]] = None
    call_statuses: Optional[List[str]] = None

class ScoreWeights(BaseModel):
    degree: float = 0.20
    betweenness: float = 0.30
    closeness: float = 0.20
    frequency: float = 0.15
    recurrence: float = 0.15
    enabled: bool = True

class NodeMetrics(BaseModel):
    id: str
    label: str
    total_calls: int
    incoming_calls: int
    outgoing_calls: int
    total_duration: int
    avg_duration: float
    unique_contacts: int
    degree: int
    in_degree: int
    out_degree: int
    weighted_degree: int
    betweenness: float
    closeness: float
    pagerank: float
    eigenvector: float
    community_id: int
    importance_score: float
    score_breakdown: Dict[str, float]
    towers: List[str]
    first_activity: str
    last_activity: str
    explanation: str

class EdgeMetrics(BaseModel):
    id: str
    source: str
    target: str
    call_count: int
    total_duration: int
    avg_duration: float
    first_interaction: str
    last_interaction: str
    towers: List[str]
    time_distribution: Dict[str, int]

class GraphViewData(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    stats: Dict[str, Any]

class CommunityDetail(BaseModel):
    id: int
    name: str
    node_count: int
    edge_count: int
    total_calls: int
    total_duration: int
    most_connected_node: str
    highest_betweenness_node: str
    dominant_tower: str
    active_time_periods: List[str]
    nodes: List[str]

class TowerMetricItem(BaseModel):
    tower_id: str
    tower_name: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    unique_devices: int
    total_calls: int
    incoming_calls: int
    outgoing_calls: int
    total_duration: int
    active_hours: List[int]
    top_devices: List[Dict[str, Any]]

class TowerTransition(BaseModel):
    source_tower: str
    target_tower: str
    transition_count: int
    unique_devices: int
    avg_gap_seconds: float
    first_observed: str
    last_observed: str

class PatternFinding(BaseModel):
    id: str
    pattern_type: str
    title: str
    what: str
    why: str
    when: str
    where: str
    evidence: Dict[str, Any]
    metrics: Dict[str, Any]
    confidence: float
    confidence_label: str  # High, Moderate, Notable
    related_nodes: List[str]
    related_towers: List[str]
    flag_reason: str

class CaseRecord(BaseModel):
    case_id: str
    case_name: str
    created_date: str
    analyst: str
    selected_nodes: List[str]
    selected_towers: List[str]
    selected_time_range: Optional[Dict[str, str]] = None
    notes: str
    saved_filters: Optional[Dict[str, Any]] = None
    saved_graph_meta: Optional[Dict[str, Any]] = None
    generated_findings: Optional[List[Dict[str, Any]]] = None
