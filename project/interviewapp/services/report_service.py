import logging
from io import BytesIO
from typing import Optional
from django.utils import timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    KeepTogether, PageBreak, HRFlowable
)

from ..models import InterviewSession

logger = logging.getLogger(__name__)


def build_session_pdf_report(session: InterviewSession) -> BytesIO:
    """
    Constructs a complete executive PDF performance report for an InterviewSession
    using ReportLab and returns an in-memory BytesIO buffer.
    """
    answers = session.answers.select_related("question").all().order_by("index")
    scores = [a.score for a in answers if a.score is not None]
    avg = (sum(scores) / len(scores)) if scores else 0
    duration = (
        int((session.completed_at - session.started_at).total_seconds() / 60)
        if (session.completed_at and session.started_at)
        else 0
    )
    report_date = session.completed_at or session.started_at or timezone.now()

    total_q = answers.count()
    attempted_answers = answers.exclude(
        answer_text__in=["[Skipped]", "", "[Voice answer could not be transcribed]"]
    )
    attempted_count = attempted_answers.count()
    completion_rate = int((attempted_count / total_q) * 100) if total_q else 0

    attempted_scores = [a.score for a in attempted_answers if a.score is not None]
    content_quality_score = (
        (sum(attempted_scores) / len(attempted_scores)) if attempted_scores else 0
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=40,
        bottomMargin=40,
    )
    styles = getSampleStyleSheet()
    elements = []

    # Palette
    brand_indigo = colors.HexColor("#4F46E5")
    text_dark = colors.HexColor("#1E293B")
    text_light = colors.HexColor("#64748B")
    bg_slate = colors.HexColor("#F8FAFC")
    border_color = colors.HexColor("#E2E8F0")

    # Typography styles
    h1_style = ParagraphStyle(
        "H1", parent=styles["Heading1"], fontSize=22, textColor=text_dark, spaceAfter=2
    )
    h2_style = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=brand_indigo,
        spaceBefore=15,
        spaceAfter=10,
        borderPadding=5,
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"], fontSize=10, textColor=text_dark, leading=14
    )
    label_style = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontSize=8,
        textColor=text_light,
        fontName="Helvetica-Bold",
        leading=10,
    )
    quote_style = ParagraphStyle(
        "Quote",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#475569"),
        fontName="Helvetica-Oblique",
        leftIndent=15,
        leading=14,
    )

    # 1. Header
    header_data = [
        [
            Paragraph("MockInterview<font color='#4F46E5'>.ai</font>", h1_style),
            Paragraph(
                f"REPORT ID: #{session.id}<br/>DATE: {report_date.strftime('%d %b %Y')}",
                label_style,
            ),
        ]
    ]
    header_tab = Table(header_data, colWidths=[350, 150])
    header_tab.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ])
    )
    elements.append(header_tab)
    elements.append(
        HRFlowable(
            width="100%", thickness=1, color=brand_indigo, spaceBefore=5, spaceAfter=20
        )
    )

    # 2. Executive Summary Card
    candidate_name = (
        session.user.get_full_name() or session.user.username
    ).upper()
    elements.append(Paragraph("EXECUTIVE SUMMARY", label_style))
    summary_data = [
        [
            Paragraph("CANDIDATE", label_style),
            Paragraph("TARGET ROLE", label_style),
            Paragraph("ANSWER QUALITY", label_style),
            Paragraph("COMPLETION RATE", label_style),
            Paragraph("OVERALL SCORE", label_style),
        ],
        [
            Paragraph(candidate_name, body_style),
            Paragraph(session.role.upper(), body_style),
            Paragraph(f"<b>{round(content_quality_score, 1)}</b>/100", body_style),
            Paragraph(f"<b>{completion_rate}%</b>", body_style),
            Paragraph(
                f"<font size='12' color='#4F46E5'><b>{round(avg, 1)}</b></font><font size='8' color='#94A3B8'> / 100</font>",
                body_style,
            ),
        ],
    ]
    summary_tab = Table(summary_data, colWidths=[100, 105, 100, 95, 95])
    summary_tab.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg_slate),
            ("BOX", (0, 0), (-1, -1), 0.5, border_color),
            ("PADDING", (0, 0), (-1, -1), 15),
        ])
    )
    elements.append(summary_tab)
    elements.append(Spacer(1, 25))

    # 3. Question-by-Question Analysis
    elements.append(Paragraph("QUESTION-BY-QUESTION ANALYSIS", h2_style))

    for idx, a in enumerate(answers, start=1):
        q_container = []

        score = a.score or 0
        status_color = (
            "#22C55E" if score >= 80 else "#F59E0B" if score >= 60 else "#EF4444"
        )
        status_text = (
            "EXCEPTIONAL" if score >= 80 else "SATISFACTORY" if score >= 60 else "NEEDS FOCUS"
        )

        q_head_data = [[
            Paragraph(f"<font color='#94A3B8'>QUESTION {idx}</font>", label_style),
            Paragraph(f"<font color='{status_color}'>● {status_text}</font>", label_style),
        ]]
        q_head_tab = Table(q_head_data, colWidths=[400, 100])
        q_container.append(q_head_tab)

        q_container.append(Paragraph(f"<b>{a.question.text}</b>", body_style))
        q_container.append(Spacer(1, 10))

        q_container.append(Paragraph("CANDIDATE RESPONSE", label_style))
        q_container.append(
            Paragraph(f"\"{a.answer_text or 'No response recorded.'}\"", quote_style)
        )
        q_container.append(Spacer(1, 10))

        if a.expected_answer:
            q_container.append(Paragraph("EXPECTED ANSWER (MODEL SOLUTION)", label_style))
            q_container.append(
                Paragraph(
                    a.expected_answer,
                    ParagraphStyle(
                        "Expected",
                        parent=body_style,
                        leftIndent=10,
                        textColor=colors.HexColor("#B45309"),
                    ),
                )
            )
            q_container.append(Spacer(1, 10))

        # Resume grounding evidence
        rg = getattr(a, "resume_grounding", None)
        if rg and isinstance(rg, dict):
            c_score = rg.get("consistency_score", 0)
            align = str(rg.get("alignment_level", "partial")).upper()
            q_container.append(
                Paragraph(f"RESUME EVIDENCE & CONSISTENCY: {align} ({c_score}/20)", label_style)
            )

            rg_notes = []
            for supp in rg.get("supported_claims", []):
                rg_notes.append(f"<font color='#059669'>[VERIFIED]</font> {supp}")
            for missed in rg.get("missed_resume_points", []):
                rg_notes.append(f"<font color='#D97706'>[MISSED]</font> {missed}")
            for contra in rg.get("contradictions", []):
                rg_notes.append(f"<font color='#DC2626'>[DISCREPANCY]</font> {contra}")

            if rg_notes:
                for note in rg_notes:
                    q_container.append(
                        Paragraph(
                            note,
                            ParagraphStyle("rg_item", parent=body_style, leftIndent=10, fontSize=9),
                        )
                    )
            q_container.append(Spacer(1, 10))

        q_container.append(Paragraph("AI EVALUATION", label_style))
        q_container.append(Paragraph(a.feedback or "Evaluation pending.", body_style))

        if a.improvement_tips:
            q_container.append(Spacer(1, 5))
            for tip in a.improvement_tips:
                q_container.append(
                    Paragraph(
                        f"<font color='#4F46E5'>•</font> {tip}",
                        ParagraphStyle("tip", parent=body_style, leftIndent=10, fontSize=9),
                    )
                )

        q_container.append(Spacer(1, 15))
        q_container.append(HRFlowable(width="100%", thickness=0.5, color=border_color))
        q_container.append(Spacer(1, 15))

        elements.append(KeepTogether(q_container))

    # 4. Behavioral Intelligence
    v_feedback = getattr(session, "video_feedback_json", None)
    if v_feedback:
        elements.append(PageBreak())
        elements.append(Paragraph("BEHAVIORAL INTELLIGENCE", h2_style))
        elements.append(Paragraph(v_feedback.get("summary", ""), body_style))
        elements.append(Spacer(1, 15))

        b_data = [
            [Paragraph("CORE STRENGTHS", label_style), Paragraph("IMPROVEMENT AREAS", label_style)],
            [
                Paragraph("<br/>".join([f"<b>+</b> {s}" for s in v_feedback.get("strengths", [])]), body_style),
                Paragraph("<br/>".join([f"<b>-</b> {i}" for i in v_feedback.get("improvements", [])]), body_style),
            ],
        ]
        b_tab = Table(b_data, colWidths=[250, 250])
        b_tab.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, 1), colors.HexColor("#F0FDF4")),
                ("BACKGROUND", (1, 0), (1, 1), colors.HexColor("#FFF7ED")),
                ("PADDING", (0, 0), (-1, -1), 12),
                ("GRID", (0, 0), (-1, -1), 0.5, border_color),
            ])
        )
        elements.append(b_tab)

    doc.build(elements)
    buffer.seek(0)
    return buffer

