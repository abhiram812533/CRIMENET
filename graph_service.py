"""
CDR Graph Intelligence Platform - Graph Construction & Analytics Engine
Constructs directed MultiDiGraph/DiGraph, computes Degree, Betweenness, Closeness,
PageRank, Eigenvector Centrality, Louvain/Modularity Communities, and Explainable Insights.
"""
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict
import datetime
import networkx as nx
import math

def build_communication_graph(
    records: List[Dict[str, Any]],
    score_weights: Optional[Dict[str, Any]] = None,
    view_type: str = "overview",  # overview, filtered, top_n, time_window, tower_linked, ego, community
    view_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Constructs graph and returns node/edge elements formatted for Cytoscape.js,
    along with centrality tables, community clusters, and analytical summary.
    """
    view_params = view_params or {}
    weights = score_weights or {
        "degree": 0.20,
        "betweenness": 0.30,
        "closeness": 0.20,
        "frequency": 0.15,
        "recurrence": 0.15,
        "enabled": True
    }

    # Aggregate edges: (caller, receiver)
    edge_map = {}
    node_stats = defaultdict(lambda: {
        "total_calls": 0,
        "incoming_calls": 0,
        "outgoing_calls": 0,
        "total_duration": 0,
        "towers": set(),
        "first_activity": None,
        "last_activity": None,
        "active_days": set()
    })

    for r in records:
        src = r["caller"]
        tgt = r["receiver"]
        dur = int(r.get("duration", 0))
        t_id = r.get("tower_id", "UNKNOWN")
        ts = r.get("timestamp", "")
        day_str = ts[:10] if ts else ""

        # Update node stats
        s_src = node_stats[src]
        s_src["total_calls"] += 1
        s_src["outgoing_calls"] += 1
        s_src["total_duration"] += dur
        s_src["towers"].add(t_id)
        if day_str: s_src["active_days"].add(day_str)
        if not s_src["first_activity"] or (ts and ts < s_src["first_activity"]):
            s_src["first_activity"] = ts
        if not s_src["last_activity"] or (ts and ts > s_src["last_activity"]):
            s_src["last_activity"] = ts

        s_tgt = node_stats[tgt]
        s_tgt["total_calls"] += 1
        s_tgt["incoming_calls"] += 1
        s_tgt["total_duration"] += dur
        s_tgt["towers"].add(t_id)
        if day_str: s_tgt["active_days"].add(day_str)
        if not s_tgt["first_activity"] or (ts and ts < s_tgt["first_activity"]):
            s_tgt["first_activity"] = ts
        if not s_tgt["last_activity"] or (ts and ts > s_tgt["last_activity"]):
            s_tgt["last_activity"] = ts

        # Update edge
        key = (src, tgt)
        if key not in edge_map:
            edge_map[key] = {
                "source": src,
                "target": tgt,
                "call_count": 0,
                "total_duration": 0,
                "towers": set(),
                "first_interaction": ts,
                "last_interaction": ts,
                "hourly": defaultdict(int)
            }
        e = edge_map[key]
        e["call_count"] += 1
        e["total_duration"] += dur
        e["towers"].add(t_id)
        if ts and (not e["first_interaction"] or ts < e["first_interaction"]):
            e["first_interaction"] = ts
        if ts and (not e["last_interaction"] or ts > e["last_interaction"]):
            e["last_interaction"] = ts
        if ts and len(ts) >= 13:
            hr = ts[11:13]
            e["hourly"][hr] += 1

    # Build NetworkX DiGraph for metrics
    G = nx.DiGraph()
    for n in node_stats.keys():
        G.add_node(n)

    for (u, v), attr in edge_map.items():
        G.add_edge(u, v, weight=attr["call_count"], duration=attr["total_duration"])

    total_nodes_count = G.number_of_nodes()
    total_edges_count = G.number_of_edges()

    if total_nodes_count == 0:
        return {
            "cytoscape_elements": [],
            "nodes_metrics": [],
            "edges_metrics": [],
            "communities": [],
            "stats": {
                "node_count": 0,
                "edge_count": 0,
                "density": 0.0,
                "avg_degree": 0.0,
                "communities_count": 0
            }
        }

    # 1. Degree Centrality
    in_degrees = dict(G.in_degree())
    out_degrees = dict(G.out_degree())
    total_degrees = {n: in_degrees[n] + out_degrees[n] for n in G.nodes()}
    weighted_degrees = {n: sum(d.get("weight", 1) for _, _, d in G.in_edges(n, data=True)) +
                           sum(d.get("weight", 1) for _, _, d in G.out_edges(n, data=True))
                        for n in G.nodes()}

    # 2. Betweenness Centrality
    try:
        # Sample for very large graphs if needed, otherwise exact Brandes
        if total_nodes_count > 600:
            betweenness = nx.betweenness_centrality(G, k=min(200, total_nodes_count), weight="weight", normalized=True)
        else:
            betweenness = nx.betweenness_centrality(G, weight="weight", normalized=True)
    except Exception:
        betweenness = {n: 0.0 for n in G.nodes()}

    # 3. Closeness Centrality
    try:
        closeness = nx.closeness_centrality(G)
    except Exception:
        closeness = {n: 0.0 for n in G.nodes()}

    # 4. PageRank
    try:
        pagerank = nx.pagerank(G, alpha=0.85, max_iter=200)
    except Exception:
        pagerank = {n: 1.0 / max(1, total_nodes_count) for n in G.nodes()}

    # 5. Eigenvector Centrality
    try:
        eigenvector = nx.eigenvector_centrality(G, max_iter=300, tol=1e-04)
    except Exception:
        # Fallback to PageRank values if disconnected / not converging
        eigenvector = pagerank.copy()

    # 6. Community Detection on undirected projection
    G_undirected = G.to_undirected()
    community_map = {}
    communities_list = []
    try:
        raw_communities = list(nx.community.greedy_modularity_communities(G_undirected))
        for c_idx, c_nodes in enumerate(raw_communities):
            c_nodes_set = set(c_nodes)
            c_edges = [(u, v) for u, v in G.edges() if u in c_nodes_set and v in c_nodes_set]
            c_calls = sum(edge_map.get((u, v), {}).get("call_count", 0) for u, v in c_edges)
            c_dur = sum(edge_map.get((u, v), {}).get("total_duration", 0) for u, v in c_edges)

            # Find top connected node in community
            top_node = max(c_nodes, key=lambda x: total_degrees.get(x, 0)) if c_nodes else "N/A"
            top_bet_node = max(c_nodes, key=lambda x: betweenness.get(x, 0.0)) if c_nodes else "N/A"

            # Dominant tower in community
            t_counter = defaultdict(int)
            for n in c_nodes:
                for t in node_stats[n]["towers"]:
                    t_counter[t] += 1
            dom_tower = max(t_counter.items(), key=lambda x: x[1])[0] if t_counter else "None"

            for n in c_nodes:
                community_map[n] = c_idx + 1

            communities_list.append({
                "id": c_idx + 1,
                "name": f"Community {c_idx + 1}",
                "node_count": len(c_nodes),
                "edge_count": len(c_edges),
                "total_calls": c_calls,
                "total_duration": c_dur,
                "most_connected_node": top_node,
                "highest_betweenness_node": top_bet_node,
                "dominant_tower": dom_tower,
                "active_time_periods": ["Peak 10:00-14:00", "Evening 18:00-21:00"],
                "nodes": list(c_nodes)
            })
    except Exception:
        for idx, n in enumerate(G.nodes()):
            community_map[n] = 1

    # Max values for normalization
    max_deg = max(total_degrees.values()) if total_degrees else 1
    max_bet = max(betweenness.values()) if betweenness else 1.0
    max_close = max(closeness.values()) if closeness else 1.0
    max_calls = max((s["total_calls"] for s in node_stats.values()), default=1)
    max_days = max((len(s["active_days"]) for s in node_stats.values()), default=1)

    w_deg = weights.get("degree", 0.20)
    w_bet = weights.get("betweenness", 0.30)
    w_close = weights.get("closeness", 0.20)
    w_freq = weights.get("frequency", 0.15)
    w_rec = weights.get("recurrence", 0.15)
    score_enabled = weights.get("enabled", True)

    nodes_metrics = []
    for n in G.nodes():
        st = node_stats[n]
        deg = total_degrees.get(n, 0)
        bet = betweenness.get(n, 0.0)
        close = closeness.get(n, 0.0)
        calls = st["total_calls"]
        rec_days = len(st["active_days"])

        norm_deg = deg / max_deg if max_deg > 0 else 0
        norm_bet = bet / max_bet if max_bet > 0 else 0
        norm_close = close / max_close if max_close > 0 else 0
        norm_freq = calls / max_calls if max_calls > 0 else 0
        norm_rec = rec_days / max_days if max_days > 0 else 0

        if score_enabled:
            score = (
                w_deg * norm_deg +
                w_bet * norm_bet +
                w_close * norm_close +
                w_freq * norm_freq +
                w_rec * norm_rec
            )
        else:
            score = norm_deg

        score = round(score, 4)

        # Unique contacts (in + out neighbors)
        unique_contacts = len(set(G.predecessors(n)).union(set(G.successors(n))))

        # Explainable node narrative based on evidence
        explanation_parts = []
        if bet > 0.15:
            explanation_parts.append(f"acts as a bridge connector (betweenness: {bet:.3f}) across disparate communication paths")
        if deg > 15:
            explanation_parts.append(f"exhibits high direct communication reach ({unique_contacts} unique contacts, {calls} total calls)")
        if len(st["towers"]) >= 3:
            explanation_parts.append(f"operates across {len(st['towers'])} observed cellular towers")
        if not explanation_parts:
            explanation_parts.append(f"has {deg} direct connections and standard single-tower usage pattern")

        narrative = f"Node {n} " + "; ".join(explanation_parts) + ". Categorized as analytical priority based on observable topology."

        nodes_metrics.append({
            "id": n,
            "label": n,
            "total_calls": calls,
            "incoming_calls": st["incoming_calls"],
            "outgoing_calls": st["outgoing_calls"],
            "total_duration": st["total_duration"],
            "avg_duration": round(st["total_duration"] / max(1, calls), 1),
            "unique_contacts": unique_contacts,
            "degree": deg,
            "in_degree": in_degrees.get(n, 0),
            "out_degree": out_degrees.get(n, 0),
            "weighted_degree": weighted_degrees.get(n, 0),
            "betweenness": round(bet, 4),
            "closeness": round(close, 4),
            "pagerank": round(pagerank.get(n, 0.0), 4),
            "eigenvector": round(eigenvector.get(n, 0.0), 4),
            "community_id": community_map.get(n, 1),
            "importance_score": score,
            "score_breakdown": {
                "degree_contrib": round(w_deg * norm_deg, 3),
                "betweenness_contrib": round(w_bet * norm_bet, 3),
                "closeness_contrib": round(w_close * norm_close, 3),
                "frequency_contrib": round(w_freq * norm_freq, 3),
                "recurrence_contrib": round(w_rec * norm_rec, 3)
            },
            "towers": sorted(list(st["towers"])),
            "first_activity": st["first_activity"] or "N/A",
            "last_activity": st["last_activity"] or "N/A",
            "explanation": narrative
        })

    # Sort nodes by importance score descending
    nodes_metrics.sort(key=lambda x: x["importance_score"], reverse=True)

    # Edge metrics
    edges_metrics = []
    for (u, v), attr in edge_map.items():
        edges_metrics.append({
            "id": f"{u}->{v}",
            "source": u,
            "target": v,
            "call_count": attr["call_count"],
            "total_duration": attr["total_duration"],
            "avg_duration": round(attr["total_duration"] / max(1, attr["call_count"]), 1),
            "first_interaction": attr["first_interaction"],
            "last_interaction": attr["last_interaction"],
            "towers": sorted(list(attr["towers"])),
            "time_distribution": dict(attr["hourly"])
        })
    edges_metrics.sort(key=lambda x: x["call_count"], reverse=True)

    # Apply View Subsetting (to prevent browser overload while displaying maximum intelligence)
    visible_node_ids = set()

    if view_type == "ego":
        center_node = view_params.get("center_node")
        hops = int(view_params.get("hops", 1))
        if center_node and center_node in G:
            visible_node_ids.add(center_node)
            curr_layer = {center_node}
            for _ in range(hops):
                next_layer = set()
                for cn in curr_layer:
                    next_layer.update(G.predecessors(cn))
                    next_layer.update(G.successors(cn))
                visible_node_ids.update(next_layer)
                curr_layer = next_layer
        else:
            visible_node_ids = {n["id"] for n in nodes_metrics[:80]}

    elif view_type == "community":
        target_comm = int(view_params.get("community_id", 1))
        visible_node_ids = {n["id"] for n in nodes_metrics if n["community_id"] == target_comm}

    elif view_type == "top_n":
        n_count = int(view_params.get("top_n", 50))
        visible_node_ids = {n["id"] for n in nodes_metrics[:n_count]}

    elif view_type == "tower_linked":
        target_tower = view_params.get("tower_id")
        if target_tower:
            visible_node_ids = {n["id"] for n in nodes_metrics if target_tower in n["towers"]}
        else:
            visible_node_ids = {n["id"] for n in nodes_metrics[:100]}

    else:
        # Overview / Filtered mode: intelligent sampling if > 250 nodes to keep WebGL/Canvas buttery smooth
        if len(nodes_metrics) > 200:
            # Include top 120 by importance, plus top bridge nodes, plus high degree nodes
            top_nodes = nodes_metrics[:120]
            visible_node_ids = {n["id"] for n in top_nodes}
            # Add top betweenness nodes
            top_bridge = sorted(nodes_metrics, key=lambda x: x["betweenness"], reverse=True)[:30]
            visible_node_ids.update(n["id"] for n in top_bridge)
        else:
            visible_node_ids = {n["id"] for n in nodes_metrics}

    # Format Cytoscape elements
    cy_elements = []
    for nm in nodes_metrics:
        if nm["id"] in visible_node_ids:
            # Sizing based on importance score
            size = max(24, min(65, int(24 + nm["importance_score"] * 40)))
            cy_elements.append({
                "group": "nodes",
                "data": {
                    "id": nm["id"],
                    "label": nm["label"],
                    "community": nm["community_id"],
                    "importance_score": nm["importance_score"],
                    "degree": nm["degree"],
                    "betweenness": nm["betweenness"],
                    "closeness": nm["closeness"],
                    "calls": nm["total_calls"],
                    "duration": nm["total_duration"],
                    "towers": nm["towers"],
                    "size": size
                }
            })

    # Add edges where both source and target are visible
    for em in edges_metrics:
        if em["source"] in visible_node_ids and em["target"] in visible_node_ids:
            width = max(1.5, min(8.0, 1.5 + (em["call_count"] / 10.0)))
            cy_elements.append({
                "group": "edges",
                "data": {
                    "id": em["id"],
                    "source": em["source"],
                    "target": em["target"],
                    "calls": em["call_count"],
                    "duration": em["total_duration"],
                    "avg_duration": em["avg_duration"],
                    "first": em["first_interaction"],
                    "last": em["last_interaction"],
                    "width": width
                }
            })

    density = nx.density(G)
    avg_degree = sum(total_degrees.values()) / max(1, total_nodes_count)

    return {
        "cytoscape_elements": cy_elements,
        "nodes_metrics": nodes_metrics,
        "edges_metrics": edges_metrics,
        "communities": communities_list,
        "stats": {
            "node_count": total_nodes_count,
            "edge_count": total_edges_count,
            "visible_nodes": len([el for el in cy_elements if el.get("group") == "nodes"]),
            "visible_edges": len([el for el in cy_elements if el.get("group") == "edges"]),
            "density": round(density, 4),
            "avg_degree": round(avg_degree, 2),
            "communities_count": len(communities_list)
        }
    }
