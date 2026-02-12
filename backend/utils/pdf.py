from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
import hashlib
import uuid
import io
from datetime import datetime, timezone


def generate_transaction_pdf(transaction: dict, employee: dict = None) -> tuple:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm, leftMargin=15*mm, rightMargin=15*mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Title'], fontSize=16, spaceAfter=12)
    heading_style = ParagraphStyle('HeadingStyle', parent=styles['Heading2'], fontSize=12, spaceAfter=6)
    normal_style = styles['Normal']
    elements = []

    integrity_id = str(uuid.uuid4())[:12].upper()

    elements.append(Paragraph("DAR AL CODE ENGINEERING CONSULTANCY", title_style))
    elements.append(Paragraph("HR Transaction Record", heading_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    elements.append(Spacer(1, 10))

    info_data = [
        ["Reference No:", transaction.get('ref_no', 'N/A')],
        ["Type:", transaction.get('type', 'N/A').replace('_', ' ').title()],
        ["Status:", transaction.get('status', 'N/A').replace('_', ' ').title()],
        ["Integrity ID:", integrity_id],
        ["Generated:", datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')],
    ]
    if employee:
        info_data.insert(1, ["Employee:", employee.get('full_name', 'N/A')])
        info_data.insert(2, ["Employee No:", employee.get('employee_number', 'N/A')])

    info_table = Table(info_data, colWidths=[120, 350])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 15))

    elements.append(Paragraph("Transaction Details", heading_style))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    elements.append(Spacer(1, 8))
    tx_data = transaction.get('data', {})
    for key, value in tx_data.items():
        elements.append(Paragraph(f"<b>{key.replace('_', ' ').title()}:</b> {value}", normal_style))
    elements.append(Spacer(1, 15))

    if transaction.get('timeline'):
        elements.append(Paragraph("Transaction Timeline", heading_style))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        elements.append(Spacer(1, 8))
        timeline_data = [["Date", "Event", "Actor", "Note"]]
        for event in transaction['timeline']:
            timeline_data.append([
                str(event.get('timestamp', ''))[:19],
                event.get('event', ''),
                event.get('actor_name', ''),
                event.get('note', '')
            ])
        t = Table(timeline_data, colWidths=[100, 120, 100, 150])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.06, 0.09, 0.16)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))

    if transaction.get('approval_chain'):
        elements.append(Paragraph("Approval Chain", heading_style))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        elements.append(Spacer(1, 8))
        approval_data = [["Stage", "Approver", "Status", "Date"]]
        for a in transaction['approval_chain']:
            approval_data.append([
                a.get('stage', ''), a.get('approver_name', ''),
                a.get('status', ''), str(a.get('timestamp', ''))[:19]
            ])
        at = Table(approval_data, colWidths=[120, 120, 100, 130])
        at.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.06, 0.09, 0.16)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(at)

    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    elements.append(Spacer(1, 5))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    return pdf_bytes, pdf_hash, integrity_id
