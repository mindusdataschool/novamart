"""
NovaMart - PDF Report Generator
=================================
Generates beautiful monthly PDF reports using ReportLab + Matplotlib.
Features: cover page, KPIs, charts, top sellers table, professional styling.
"""

import io
import os
import calendar
from datetime import datetime
from decimal import Decimal

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics import renderPDF

from database import query, query_one

# ======================== COLOR PALETTE ========================

COLORS = {
    "primary": colors.HexColor("#6C3CE1"),
    "primary_dark": colors.HexColor("#5228B5"),
    "accent": colors.HexColor("#FF6B35"),
    "bg_dark": colors.HexColor("#0F0B1E"),
    "bg_card": colors.HexColor("#1A1530"),
    "text_white": colors.HexColor("#FFFFFF"),
    "text_light": colors.HexColor("#E8E4F0"),
    "text_muted": colors.HexColor("#9B95A8"),
    "green": colors.HexColor("#10B981"),
    "red": colors.HexColor("#EF4444"),
    "blue": colors.HexColor("#3B82F6"),
    "yellow": colors.HexColor("#F9C74F"),
}

CHART_COLORS = ["#6C3CE1", "#FF6B35", "#10B981", "#3B82F6", "#F9C74F",
                "#EC4899", "#8B5CF6", "#06B6D4", "#F472B6", "#34D399"]

MONTH_NAMES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


# ======================== STYLES ========================

def get_styles():
    """Create custom paragraph styles for the PDF."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="CoverTitle",
        fontName="Helvetica-Bold",
        fontSize=36,
        textColor=COLORS["text_white"],
        alignment=TA_CENTER,
        spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        name="CoverSubtitle",
        fontName="Helvetica",
        fontSize=16,
        textColor=COLORS["text_muted"],
        alignment=TA_CENTER,
        spaceAfter=4,
    ))

    styles.add(ParagraphStyle(
        name="SectionTitle",
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=COLORS["primary"],
        spaceBefore=20,
        spaceAfter=12,
    ))

    styles.add(ParagraphStyle(
        name="SubSectionTitle",
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=COLORS["text_light"],
        spaceBefore=12,
        spaceAfter=8,
    ))

    styles.add(ParagraphStyle(
        name="BodyText_Custom",
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#444444"),
        spaceBefore=4,
        spaceAfter=4,
        leading=14,
    ))

    styles.add(ParagraphStyle(
        name="KPIValue",
        fontName="Helvetica-Bold",
        fontSize=24,
        textColor=COLORS["primary"],
        alignment=TA_CENTER,
    ))

    styles.add(ParagraphStyle(
        name="KPILabel",
        fontName="Helvetica",
        fontSize=9,
        textColor=colors.HexColor("#666666"),
        alignment=TA_CENTER,
    ))

    styles.add(ParagraphStyle(
        name="FooterStyle",
        fontName="Helvetica",
        fontSize=8,
        textColor=colors.HexColor("#999999"),
        alignment=TA_CENTER,
    ))

    return styles


# ======================== PAGE BACKGROUNDS ========================

def cover_page_bg(canvas, doc):
    """Draw cover page background with gradient-like effect and branding."""
    w, h = A4
    # Dark gradient background
    canvas.setFillColor(COLORS["bg_dark"])
    canvas.rect(0, 0, w, h, fill=1, stroke=0)

    # Decorative gradient overlay
    canvas.setFillColor(COLORS["primary_dark"])
    canvas.setFillAlpha(0.3)
    canvas.rect(0, h * 0.55, w, h * 0.45, fill=1, stroke=0)

    canvas.setFillAlpha(1)

    # Accent stripe at top
    canvas.setFillColor(COLORS["accent"])
    canvas.rect(0, h - 8, w, 8, fill=1, stroke=0)

    # Bottom decorative bar
    canvas.setFillColor(COLORS["primary"])
    canvas.rect(0, 0, w, 3, fill=1, stroke=0)

    # Side accent
    canvas.setFillColor(COLORS["primary"])
    canvas.setFillAlpha(0.15)
    canvas.rect(0, 0, 4, h, fill=1, stroke=0)
    canvas.setFillAlpha(1)

    # Logo "N" circle
    cx, cy = w / 2, h * 0.72
    canvas.setFillColor(COLORS["primary"])
    canvas.circle(cx, cy, 40, fill=1, stroke=0)
    canvas.setFillColor(COLORS["text_white"])
    canvas.setFont("Helvetica-Bold", 36)
    canvas.drawCentredString(cx, cy - 13, "N")

    # Footer on cover
    canvas.setFillColor(COLORS["text_muted"])
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(w / 2, 25, "NovaMart Analytics • Relatório Confidencial • Gerado automaticamente")


def standard_page_bg(canvas, doc):
    """Standard page header/footer for content pages."""
    w, h = A4

    # Top bar
    canvas.setFillColor(COLORS["primary"])
    canvas.rect(0, h - 4, w, 4, fill=1, stroke=0)

    # Header
    canvas.setFillColor(colors.HexColor("#F8F7FC"))
    canvas.rect(0, h - 50, w, 46, fill=1, stroke=0)

    canvas.setFillColor(COLORS["primary"])
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(2 * cm, h - 35, "NovaMart")

    canvas.setFillColor(COLORS["accent"])
    canvas.setFont("Helvetica", 11)
    canvas.drawString(2 * cm + canvas.stringWidth("NovaMart", "Helvetica-Bold", 11), h - 35, " Analytics")

    # Header line
    canvas.setStrokeColor(COLORS["primary"])
    canvas.setLineWidth(0.5)
    canvas.line(0, h - 50, w, h - 50)

    # Footer
    canvas.setStrokeColor(colors.HexColor("#E0E0E0"))
    canvas.line(2 * cm, 1.5 * cm, w - 2 * cm, 1.5 * cm)

    canvas.setFillColor(colors.HexColor("#999999"))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(2 * cm, 1 * cm, f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    canvas.drawRightString(w - 2 * cm, 1 * cm, f"Página {doc.page}")


# ======================== CHART GENERATORS ========================

def create_bar_chart(categories, values, title, xlabel="", ylabel="Receita (R$)", figsize=(7, 3.5)):
    """Create a styled horizontal bar chart."""
    fig, ax = plt.subplots(figsize=figsize)

    bars = ax.barh(range(len(categories)), values, color=CHART_COLORS[:len(categories)],
                   height=0.6, edgecolor="white", linewidth=0.5)

    ax.set_yticks(range(len(categories)))
    ax.set_yticklabels(categories, fontsize=8)
    ax.set_xlabel(xlabel, fontsize=9, color="#666")
    ax.set_title(title, fontsize=12, fontweight="bold", color="#333", pad=15)

    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f"R$ {x:,.0f}"))
    ax.tick_params(axis="x", labelsize=7, colors="#666")

    # Add value labels
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + max(values) * 0.02, bar.get_y() + bar.get_height() / 2,
                f"R$ {val:,.2f}", va="center", fontsize=7, color="#333")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color("#DDD")
    ax.invert_yaxis()

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf


def create_line_chart(dates, values, title, ylabel="Receita (R$)", figsize=(7, 3)):
    """Create a styled line chart for daily trends."""
    fig, ax = plt.subplots(figsize=figsize)

    ax.plot(range(len(dates)), values, color=CHART_COLORS[0], linewidth=2, marker="o",
            markersize=3, markerfacecolor=CHART_COLORS[1])
    ax.fill_between(range(len(dates)), values, alpha=0.1, color=CHART_COLORS[0])

    ax.set_xticks(range(len(dates)))
    ax.set_xticklabels([d.split("-")[-1] for d in dates], fontsize=7, rotation=45)
    ax.set_xlabel("Dia", fontsize=9, color="#666")
    ax.set_title(title, fontsize=12, fontweight="bold", color="#333", pad=15)

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f"R$ {x:,.0f}"))
    ax.tick_params(axis="y", labelsize=7, colors="#666")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#DDD")
    ax.spines["bottom"].set_color("#DDD")
    ax.grid(axis="y", alpha=0.3, linestyle="--")

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf


def create_pie_chart(labels, values, title, figsize=(5, 3.5)):
    """Create a styled pie/donut chart."""
    fig, ax = plt.subplots(figsize=figsize)

    wedges, texts, autotexts = ax.pie(
        values, labels=None, autopct="%1.1f%%",
        colors=CHART_COLORS[:len(labels)],
        startangle=90, pctdistance=0.78,
        wedgeprops=dict(width=0.45, edgecolor="white", linewidth=2),
    )

    for t in autotexts:
        t.set_fontsize(7)
        t.set_color("white")
        t.set_fontweight("bold")

    ax.legend(labels, loc="center left", bbox_to_anchor=(1, 0.5),
              fontsize=7, frameon=False)
    ax.set_title(title, fontsize=12, fontweight="bold", color="#333", pad=10)

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf


# ======================== KPI CARD ========================

def create_kpi_table(kpis, styles):
    """Create a row of KPI cards as a table."""
    header_cells = []
    value_cells = []
    detail_cells = []

    for kpi in kpis:
        header_cells.append(Paragraph(kpi["label"], styles["KPILabel"]))
        value_cells.append(Paragraph(kpi["value"], styles["KPIValue"]))
        detail_cells.append(Paragraph(kpi.get("detail", ""), styles["KPILabel"]))

    data = [header_cells, value_cells, detail_cells]

    col_width = (A4[0] - 4 * cm) / len(kpis)
    t = Table(data, colWidths=[col_width] * len(kpis))

    t.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8F7FC")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E8E4F0")),
        ("LINEAFTER", (0, 0), (-2, -1), 0.5, colors.HexColor("#E8E4F0")),
        ("TOPPADDING", (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 12),
        ("TOPPADDING", (0, 1), (-1, 1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 4),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))

    return t


# ======================== MAIN GENERATOR ========================

def fetch_report_data(month, year):
    """Fetch all data needed for the report."""
    data = {}

    # Revenue & orders
    row = query_one("""
        SELECT COALESCE(SUM(valor_total), 0) AS revenue,
               COUNT(*) AS orders,
               COALESCE(AVG(valor_total), 0) AS avg_ticket
        FROM app.orders
        WHERE EXTRACT(YEAR FROM data_pedido) = %s
          AND EXTRACT(MONTH FROM data_pedido) = %s
          AND id_status NOT IN (6, 7)
    """, (year, month))
    data["revenue"] = float(row["revenue"])
    data["total_orders"] = row["orders"]
    data["avg_ticket"] = float(row["avg_ticket"])

    # Previous month
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    prev = query_one("""
        SELECT COALESCE(SUM(valor_total), 0) AS revenue, COUNT(*) AS orders
        FROM app.orders
        WHERE EXTRACT(YEAR FROM data_pedido) = %s
          AND EXTRACT(MONTH FROM data_pedido) = %s
          AND id_status NOT IN (6, 7)
    """, (prev_year, prev_month))
    data["prev_revenue"] = float(prev["revenue"])
    data["prev_orders"] = prev["orders"]

    # Top categories
    data["top_categories"] = query("""
        SELECT pc.nome AS category, SUM(oi.preco_total) AS total
        FROM app.order_items oi
        JOIN app.products p ON p.id = oi.id_produto
        JOIN app.product_categories pc ON pc.id = p.id_categoria
        JOIN app.orders o ON o.id = oi.id_pedido
        WHERE EXTRACT(YEAR FROM o.data_pedido) = %s
          AND EXTRACT(MONTH FROM o.data_pedido) = %s
          AND o.id_status NOT IN (6, 7)
        GROUP BY pc.nome
        ORDER BY total DESC
        LIMIT 8
    """, (year, month))

    # Top sellers
    data["top_sellers"] = query("""
        SELECT s.nome_empresa, SUM(oi.preco_total) AS total,
               COUNT(DISTINCT oi.id_pedido) AS orders,
               ROUND(AVG(r.avaliacao), 1) AS avg_rating
        FROM app.order_items oi
        JOIN app.sellers s ON s.id = oi.id_vendedor
        JOIN app.orders o ON o.id = oi.id_pedido
        LEFT JOIN app.reviews r ON r.id_vendedor = s.id
        WHERE EXTRACT(YEAR FROM o.data_pedido) = %s
          AND EXTRACT(MONTH FROM o.data_pedido) = %s
          AND o.id_status NOT IN (6, 7)
        GROUP BY s.nome_empresa
        ORDER BY total DESC
        LIMIT 10
    """, (year, month))

    # Payment methods
    data["payment_methods"] = query("""
        SELECT pm.nome AS method, COUNT(*) AS count, SUM(p.valor) AS total
        FROM app.payments p
        JOIN app.payment_methods pm ON pm.id = p.id_metodo_pagamento
        JOIN app.orders o ON o.id = p.id_pedido
        WHERE EXTRACT(YEAR FROM o.data_pedido) = %s
          AND EXTRACT(MONTH FROM o.data_pedido) = %s
          AND p.status = 'approved'
        GROUP BY pm.nome
        ORDER BY total DESC
    """, (year, month))

    # Daily revenue
    data["daily_revenue"] = query("""
        SELECT data_pedido::date AS day, SUM(valor_total) AS revenue
        FROM app.orders
        WHERE EXTRACT(YEAR FROM data_pedido) = %s
          AND EXTRACT(MONTH FROM data_pedido) = %s
          AND id_status NOT IN (6, 7)
        GROUP BY data_pedido::date
        ORDER BY day
    """, (year, month))

    # New customers
    row = query_one("""
        SELECT COUNT(*) AS total FROM app.customers
        WHERE EXTRACT(YEAR FROM criado_em) = %s
          AND EXTRACT(MONTH FROM criado_em) = %s
    """, (year, month))
    data["new_customers"] = row["total"]

    # Reviews
    row = query_one("""
        SELECT ROUND(AVG(avaliacao), 2) AS avg, COUNT(*) AS total
        FROM app.reviews
        WHERE EXTRACT(YEAR FROM criado_em) = %s
          AND EXTRACT(MONTH FROM criado_em) = %s
    """, (year, month))
    data["avg_rating"] = float(row["avg"]) if row and row["avg"] else 0
    data["total_reviews"] = row["total"] if row else 0

    # Order status distribution
    data["status_dist"] = query("""
        SELECT os.nome AS status, COUNT(*) AS count
        FROM app.orders o
        JOIN app.order_statuses os ON os.id = o.id_status
        WHERE EXTRACT(YEAR FROM o.data_pedido) = %s
          AND EXTRACT(MONTH FROM o.data_pedido) = %s
        GROUP BY os.nome, os.ordem_exibicao
        ORDER BY os.ordem_exibicao
    """, (year, month))

    return data


def generate_monthly_report(month, year):
    """
    Generate a complete monthly PDF report.
    Returns: bytes of the PDF file.
    """
    data = fetch_report_data(month, year)
    styles = get_styles()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
    )

    story = []

    # ==================== COVER PAGE ====================
    story.append(Spacer(1, 6 * cm))
    story.append(Paragraph("NovaMart", styles["CoverTitle"]))
    story.append(Paragraph("Relatório Mensal", styles["CoverSubtitle"]))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(
        f"{MONTH_NAMES[month]} {year}",
        ParagraphStyle("CoverDate", parent=styles["CoverSubtitle"],
                       fontSize=22, textColor=COLORS["accent"])
    ))
    story.append(Spacer(1, 2 * cm))
    story.append(Paragraph(
        "Relatório gerado automaticamente com os indicadores<br/>de performance do marketplace NovaMart.",
        ParagraphStyle("CoverBody", parent=styles["CoverSubtitle"],
                       fontSize=11, leading=16)
    ))
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph(
        f"Data de geração: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        ParagraphStyle("CoverFooter", parent=styles["CoverSubtitle"],
                       fontSize=9, textColor=COLORS["text_muted"])
    ))

    story.append(PageBreak())

    # ==================== KPIs PAGE ====================
    story.append(Paragraph("Indicadores Chave", styles["SectionTitle"]))
    story.append(Spacer(1, 0.3 * cm))

    # Revenue change
    rev_change = 0
    if data["prev_revenue"] > 0:
        rev_change = ((data["revenue"] - data["prev_revenue"]) / data["prev_revenue"]) * 100
    rev_arrow = "▲" if rev_change >= 0 else "▼"
    rev_color = "#10B981" if rev_change >= 0 else "#EF4444"

    kpis = [
        {
            "label": "RECEITA TOTAL",
            "value": f"R$ {data['revenue']:,.2f}",
            "detail": f'<font color="{rev_color}">{rev_arrow} {abs(rev_change):.1f}% vs mês anterior</font>',
        },
        {
            "label": "TOTAL DE PEDIDOS",
            "value": f"{data['total_orders']:,}",
            "detail": f"Mês anterior: {data['prev_orders']:,}",
        },
        {
            "label": "TICKET MÉDIO",
            "value": f"R$ {data['avg_ticket']:,.2f}",
            "detail": "",
        },
    ]

    story.append(create_kpi_table(kpis, styles))
    story.append(Spacer(1, 0.8 * cm))

    kpis2 = [
        {
            "label": "NOVOS CLIENTES",
            "value": f"{data['new_customers']:,}",
            "detail": "",
        },
        {
            "label": "AVALIAÇÃO MÉDIA",
            "value": f"{'★' * int(data['avg_rating'])} {data['avg_rating']}",
            "detail": f"{data['total_reviews']} avaliações",
        },
        {
            "label": "COMISSÃO ESTIMADA",
            "value": f"R$ {data['revenue'] * 0.15:,.2f}",
            "detail": "Taxa padrão: 15%",
        },
    ]

    story.append(create_kpi_table(kpis2, styles))

    # Summary text
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("Resumo Executivo", styles["SubSectionTitle"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E8E4F0")))
    story.append(Spacer(1, 0.3 * cm))

    summary = (
        f"No mês de <b>{MONTH_NAMES[month]} de {year}</b>, o marketplace NovaMart registrou "
        f"uma receita total de <b>R$ {data['revenue']:,.2f}</b> com <b>{data['total_orders']:,}</b> pedidos "
        f"processados. O ticket médio ficou em <b>R$ {data['avg_ticket']:,.2f}</b>. "
        f"Foram registrados <b>{data['new_customers']:,}</b> novos clientes e "
        f"<b>{data['total_reviews']:,}</b> avaliações, com nota média de <b>{data['avg_rating']:.1f}</b>."
    )
    if rev_change >= 0:
        summary += (
            f" A receita apresentou crescimento de <font color='#10B981'><b>{rev_change:.1f}%</b></font> "
            f"em relação ao mês anterior."
        )
    else:
        summary += (
            f" A receita teve uma redução de <font color='#EF4444'><b>{abs(rev_change):.1f}%</b></font> "
            f"em relação ao mês anterior."
        )

    story.append(Paragraph(summary, styles["BodyText_Custom"]))

    story.append(PageBreak())

    # ==================== CHARTS PAGE 1: Categories + Trend ====================
    story.append(Paragraph("Receita por Categoria", styles["SectionTitle"]))

    if data["top_categories"]:
        cats = [r["category"] for r in data["top_categories"]]
        vals = [float(r["total"]) for r in data["top_categories"]]

        chart_buf = create_bar_chart(
            cats, vals,
            f"Top Categorias - {MONTH_NAMES[month]} {year}",
        )
        story.append(Image(chart_buf, width=16 * cm, height=8 * cm))
    else:
        story.append(Paragraph("Sem dados de categorias para este período.", styles["BodyText_Custom"]))

    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("Tendência Diária de Receita", styles["SectionTitle"]))

    if data["daily_revenue"]:
        days = [r["day"].strftime("%Y-%m-%d") for r in data["daily_revenue"]]
        revenues = [float(r["revenue"]) for r in data["daily_revenue"]]

        chart_buf = create_line_chart(
            days, revenues,
            f"Receita Diária - {MONTH_NAMES[month]} {year}",
        )
        story.append(Image(chart_buf, width=16 * cm, height=7 * cm))

    story.append(PageBreak())

    # ==================== CHARTS PAGE 2: Payment Methods + Status ====================
    story.append(Paragraph("Métodos de Pagamento", styles["SectionTitle"]))

    if data["payment_methods"]:
        pm_labels = [r["method"] for r in data["payment_methods"]]
        pm_values = [float(r["total"]) for r in data["payment_methods"]]

        chart_buf = create_pie_chart(
            pm_labels, pm_values,
            f"Distribuição por Método de Pagamento",
        )
        story.append(Image(chart_buf, width=14 * cm, height=8 * cm))

    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph("Status dos Pedidos", styles["SectionTitle"]))

    if data["status_dist"]:
        st_labels = [r["status"] for r in data["status_dist"]]
        st_values = [r["count"] for r in data["status_dist"]]

        chart_buf = create_pie_chart(
            st_labels, st_values,
            f"Distribuição de Status",
        )
        story.append(Image(chart_buf, width=14 * cm, height=8 * cm))

    story.append(PageBreak())

    # ==================== TOP SELLERS TABLE ====================
    story.append(Paragraph("Top Sellers", styles["SectionTitle"]))
    story.append(Spacer(1, 0.3 * cm))

    if data["top_sellers"]:
        table_data = [
            [
                Paragraph("<b>#</b>", styles["KPILabel"]),
                Paragraph("<b>Seller</b>", styles["KPILabel"]),
                Paragraph("<b>Receita</b>", styles["KPILabel"]),
                Paragraph("<b>Pedidos</b>", styles["KPILabel"]),
                Paragraph("<b>Rating</b>", styles["KPILabel"]),
            ]
        ]

        for i, seller in enumerate(data["top_sellers"], 1):
            rating = float(seller["avg_rating"]) if seller["avg_rating"] else 0
            rating_str = f"{'★' * int(rating)} {rating:.1f}" if rating > 0 else "N/A"

            table_data.append([
                Paragraph(str(i), styles["BodyText_Custom"]),
                Paragraph(seller["nome_empresa"][:35], styles["BodyText_Custom"]),
                Paragraph(f"R$ {float(seller['total']):,.2f}", styles["BodyText_Custom"]),
                Paragraph(str(seller["orders"]), styles["BodyText_Custom"]),
                Paragraph(rating_str, styles["BodyText_Custom"]),
            ])

        seller_table = Table(
            table_data,
            colWidths=[1.2 * cm, 6.5 * cm, 3.5 * cm, 2.5 * cm, 3 * cm],
        )

        seller_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F0EDFA")),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLORS["primary"]),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("ALIGN", (2, 0), (4, -1), "CENTER"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E8E4F0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAFA")]),
            ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ]))

        story.append(seller_table)

    # ==================== FOOTER NOTE ====================
    story.append(Spacer(1, 2 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E8E4F0")))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "Este relatório foi gerado automaticamente pelo sistema NovaMart Analytics. "
        "Os dados apresentados são referentes ao período selecionado e podem sofrer "
        "pequenas variações após o fechamento mensal.",
        styles["FooterStyle"]
    ))

    # ==================== BUILD PDF ====================
    doc.build(
        story,
        onFirstPage=cover_page_bg,
        onLaterPages=standard_page_bg,
    )

    return buffer.getvalue()


if __name__ == "__main__":
    # Test: generate a report for a sample month
    pdf_bytes = generate_monthly_report(10, 2025)
    with open("test_report.pdf", "wb") as f:
        f.write(pdf_bytes)
    print(f"Report generated: test_report.pdf ({len(pdf_bytes)} bytes)")
