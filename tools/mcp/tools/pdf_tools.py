"""PDF visualization tools for the unified MCP server."""

import os
import time
import tempfile
from typing import List, Dict, Optional
from dataclasses import dataclass

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

# Import reportlab after matplotlib to avoid conflicts
from reportlab.lib import colors as rl_colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, TableStyle, Table, Image


OUTPUT_DIR = os.environ.get("PDF_OUTPUT_DIR", os.path.join(os.getcwd(), "output", "reports"))
os.makedirs(OUTPUT_DIR, exist_ok=True)


@dataclass
class ChartSpec:
    x_key: str
    y_key: str
    top_n: int = 10
    title: str = "Chart"


def _make_chart_png(df: pd.DataFrame, spec: ChartSpec) -> Optional[str]:
    """
    Create a bar chart from the DataFrame and save it as a PNG file.
    Returns the file path of the saved PNG or None if creation failed.
    """
    try:
        if spec.x_key not in df.columns or spec.y_key not in df.columns:
            return None

        data = df[[spec.x_key, spec.y_key]].dropna().sort_values(by=spec.y_key, ascending=False).head(spec.top_n)

        if data.empty:
            return None

        # Create figure with explicit color specification
        fig, ax = plt.subplots(figsize=(8, 6))
        bars = ax.bar(
            data[spec.x_key].astype(str), 
            data[spec.y_key], 
            color='steelblue',  # Use named color to avoid conflicts
            edgecolor='black',
            linewidth=0.5
        )
        ax.set_title(spec.title)
        ax.set_xlabel(spec.x_key)
        ax.set_ylabel(spec.y_key)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        # Save to tmp
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        plt.savefig(tmp.name, dpi=100, bbox_inches='tight')
        plt.close(fig)

        return tmp.name
    except Exception as e:
        print(f"Chart creation failed: {e}")
        return None


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in s).lower()[:50]


def generate_pdf(
    title: str,
    question: str,
    insight: str,
    rows: List[Dict],
    chart_x_key: Optional[str] = None,
    chart_y_key: Optional[str] = None,
    chart_top_n: int = 10,
    chart_title: Optional[str] = None
) -> Dict:
    """
    Generate a PDF report from the provided data and insights.
    """

    # Normalize rows to dataframe
    df = pd.DataFrame(rows) if rows else pd.DataFrame()

    # prepare chart if requested
    chart_path = None

    # Temporarily disable chart generation to debug
    # if chart_x_key and chart_y_key and not df.empty:
    #     chart_path = _make_chart_png(df, ChartSpec(
    #         x_key=chart_x_key,
    #         y_key=chart_y_key,
    #         top_n=chart_top_n,
    #         title=chart_title or f"Top {chart_top_n} {chart_y_key} by {chart_x_key}"
    #     ))

    ts = time.strftime("%Y%m%d_%H%M%S")
    fname = f"{_slug(title)}_{ts}.pdf"
    fpath = os.path.join(OUTPUT_DIR, fname)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    print(f"Creating PDF at: {fpath}")
    print(f"Directory exists: {os.path.exists(os.path.dirname(fpath))}")

    # build pdf
    doc = SimpleDocTemplate(fpath, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(title, styles['Title']))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Question: {question}", styles['Heading2']))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Insight:", styles['Heading2']))
    story.append(Paragraph(insight, styles['BodyText']))
    story.append(Spacer(1, 12))

    # Chart
    if chart_path and os.path.exists(chart_path):
        story.append(Paragraph("Chart:", styles['Heading2']))
        img = Image(chart_path, width=400, height=300)
        story.append(img)
        story.append(Spacer(1, 12))

    # Preview of table
    if not df.empty:
        df_preview = df.iloc[:25, :8].copy()

        story.append(Paragraph("Data Preview (first 25 rows):", styles['Heading2']))
        table_data = [df_preview.columns.tolist()] + df_preview.values.tolist()
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), rl_colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), rl_colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, rl_colors.black),
        ]))
        story.append(table)
        story.append(Spacer(1, 12))

    doc.build(story)

    return {"ok": True, "path": fpath}
