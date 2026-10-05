"""
CDR Graph Intelligence Platform - Report & Export Service
Generates professional analytical PDF reports, CSV, and tabular exports.
Adheres to strict analytical standards and transparent evidence documentation.
"""
import io
import csv
from typing import Dict, Any, List
from datetime import datetime

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

def generate_pdf_report(report_data: Dict[str, Any]) -> bytes:
    """Generates comprehensive analytical intelligence PDF report."""
    if not HAS_REPORTLAB:
        # Fallback to plain text if reportlab is absent
        summary = f"CDR Graph Intelligence Platform - Report\nDate: {datetime.now()}\n"
        return summary.encode("utf-8")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#2563EB'),
        spaceAfter=15
    )
    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#DC2626')
    )

    story = []

    # Title & Header
    story.append(Paragraph("CDR GRAPH INTELLIGENCE REPORT", title_style))
    story.append(Paragraph("Analytical Communication Pattern & Network Centrality Assessment", subtitle_style))
    story.append(Paragraph(
        "<b>CONFIDENTIALITY NOTICE:</b> This analytical decision-support dossier contains processed telecommunication "
        "graph metrics. Findings represent topological associations and communication statistics, not legal determination of guilt.",
        disclaimer_style
    ))
    story.append(Spacer(1, 10))

    # Executive Summary
    story.append(Paragraph("1. Executive Summary", h2_style))
    stats = report_data.get("stats", {})
    summary_text = (
        f"Analysis performed on {report_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}. "
        f"The active dataset comprises <b>{stats.get('valid_records', 0)}</b> validated CDR records involving "
        f"<b>{stats.get('node_count', 0)}</b> distinct phone nodes and <b>{stats.get('edge_count', 0)}</b> directed interaction edges. "
        f"Algorithm detected <b>{stats.get('communities_count', 0)}</b> distinct communication clusters and "
        f"<b>{len(report_data.get('patterns', []))}</b> explainable topological patterns."
    )
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 8))

    # KPI Table
    kpi_data = [
        ["Total Records", "Valid Records", "Filtered Out", "Unique Nodes", "Unique Edges", "Active Towers"],
        [
            str(stats.get("total_records", 0)),
            str(stats.get("valid_records", 0)),
            str(stats.get("filtered_count", 0)),
            str(stats.get("node_count", 0)),
            str(stats.get("edge_count", 0)),
            str(stats.get("tower_count", 0)),
        ]
    ]
    t_kpi = Table(kpi_data, colWidths=[90, 90, 90, 90, 90, 90])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 12))

    # Top Centrality Nodes Table
    story.append(Paragraph("2. Top Priority Communication Nodes (Centrality Metrics)", h2_style))
    nodes = report_data.get("top_nodes", [])[:8]
    node_rows = [["Node ID", "Degree", "Betweenness", "Closeness", "Calls", "Score", "Dominant Towers"]]
    for n in nodes:
        node_rows.append([
            n.get("id", "N/A"),
            str(n.get("degree", 0)),
            f"{n.get('betweenness', 0):.3f}",
            f"{n.get('closeness', 0):.3f}",
            str(n.get("total_calls", 0)),
            f"{n.get('importance_score', 0):.3f}",
            ", ".join(n.get("towers", [])[:2])
        ])
    t_nodes = Table(node_rows, colWidths=[95, 45, 60, 60, 45, 55, 180])
    t_nodes.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_nodes)
    story.append(Spacer(1, 12))

    # Detected Patterns & Explainable Findings
    story.append(Paragraph("3. Detected Communication Patterns & Evidence", h2_style))
    patterns = report_data.get("patterns", [])
    if patterns:
        for p in patterns[:4]:
            p_box = [
                [Paragraph(f"<b>Pattern:</b> {p.get('title')} ({p.get('pattern_type')})", body_style)],
                [Paragraph(f"<b>WHAT:</b> {p.get('what')}", body_style)],
                [Paragraph(f"<b>WHY:</b> {p.get('why')}", body_style)],
                [Paragraph(f"<b>WHEN:</b> {p.get('when')} | <b>WHERE:</b> {p.get('where')}", body_style)],
                [Paragraph(f"<b>EVIDENCE:</b> {str(p.get('evidence'))}", body_style)],
                [Paragraph(f"<b>REASON FOR FLAGGING:</b> {p.get('flag_reason')}", body_style)]
            ]
            t_pat = Table(p_box, colWidths=[540])
            t_pat.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
                ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#3B82F6')),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(t_pat)
            story.append(Spacer(1, 6))
    else:
        story.append(Paragraph("No anomalous patterns detected under current filter thresholds.", body_style))

    # Limitations & Legal Framework
    story.append(Spacer(1, 8))
    story.append(Paragraph("4. Analytical Limitations & Evidence Integrity", h2_style))
    limits = (
        "1. Tower site data indicates antenna coverage sectors, not guaranteed exact physical user locations.<br/>"
        "2. Centrality metrics are mathematically derived from observed CDR records and can be influenced by incomplete provider extracts.<br/>"
        "3. High centrality indicates structural connectedness, not criminal propensity."
    )
    story.append(Paragraph(limits, body_style))

    doc.build(story)
    return buffer.getvalue()

def generate_csv_export(records: List[Dict[str, Any]]) -> str:
    """Exports dataset to CSV string."""
    output = io.StringIO()
    if not records:
        return ""
    fieldnames = list(records[0].keys())
    # Remove internal prefixes
    fieldnames = [f for f in fieldnames if not f.startswith("_")]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    for r in records:
        writer.writerow(r)
    return output.getvalue()
