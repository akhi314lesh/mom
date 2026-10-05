"""backend/app/artifacts/pdf_generator.py — Clean PDF generator for Minutes of Meeting."""
from pathlib import Path
from typing import Dict, Any

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)


class PdfGenerator:
    """Generates professional, printable PDF Minutes of Meeting reports."""

    @staticmethod
    def generate(output_path: Path, meeting_data: Dict[str, Any]) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=20,
            leading=24,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            'DocSub',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=12,
        )
        h2_style = ParagraphStyle(
            'Heading2',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            textColor=colors.HexColor('#1e293b'),
            spaceBefore=14,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            textColor=colors.HexColor('#334155'),
        )
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#94a3b8'),
            alignment=1,  # Center
            spaceBefore=20,
        )

        story = []

        # Title & Metadata
        title = meeting_data.get('title', 'Minutes of Meeting')
        date_str = meeting_data.get('date', '')
        story.append(Paragraph(f"Minutes of Meeting: {title}", title_style))
        story.append(Paragraph(f"Date: {date_str}  •  Status: {meeting_data.get('lifecycle_status', 'FINALIZED')}", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceAfter=14))

        # Executive Summary
        story.append(Paragraph("Executive Summary", h2_style))
        summary_text = meeting_data.get('summary', 'Evidence-grounded canonical meeting record.')
        story.append(Paragraph(summary_text, body_style))
        story.append(Spacer(1, 10))

        # Participants
        participants = meeting_data.get('participants', [])
        if participants:
            story.append(Paragraph("Participants", h2_style))
            part_data = [["Name", "Role"]]
            for p in participants:
                part_data.append([p.get('name', 'Unknown'), p.get('role', 'Team Member')])
            t_part = Table(part_data, colWidths=[200, 300])
            t_part.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ]))
            story.append(t_part)
            story.append(Spacer(1, 10))

        # Decisions
        decisions = meeting_data.get('decisions', [])
        if decisions:
            story.append(Paragraph("Key Decisions", h2_style))
            dec_data = [["Decision", "Status"]]
            for d in decisions:
                dec_data.append([Paragraph(d.get('text', ''), body_style), d.get('status', 'CONFIRMED')])
            t_dec = Table(dec_data, colWidths=[400, 100])
            t_dec.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ecfdf5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#065f46')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ]))
            story.append(t_dec)
            story.append(Spacer(1, 10))

        # Action Items
        actions = meeting_data.get('action_items', [])
        if actions:
            story.append(Paragraph("Action Items", h2_style))
            act_data = [["Task", "Owner", "Deadline", "Priority"]]
            for a in actions:
                act_data.append([
                    Paragraph(a.get('task', ''), body_style),
                    a.get('owner', 'Unassigned'),
                    str(a.get('deadline', 'TBD'))[:10],
                    str(a.get('priority', 'MED')),
                ])
            t_act = Table(act_data, colWidths=[250, 100, 80, 70])
            t_act.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eff6ff')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ]))
            story.append(t_act)
            story.append(Spacer(1, 10))

        # Footer
        story.append(Spacer(1, 14))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e2e8f0'), spaceAfter=8))
        story.append(Paragraph("— Generated by MOM for meetings • Evidence-Grounded Canonical Record —", footer_style))

        doc.build(story)
        return output_path
