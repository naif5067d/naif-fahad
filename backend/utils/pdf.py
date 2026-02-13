from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display
import hashlib
import uuid
import io
import os
from datetime import datetime, timezone

# Register Arabic fonts
FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')
try:
    pdfmetrics.registerFont(TTFont('NotoArabic', os.path.join(FONTS_DIR, 'NotoSansArabic-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('NotoArabicBold', os.path.join(FONTS_DIR, 'NotoSansArabic-Bold.ttf')))
    ARABIC_FONT_AVAILABLE = True
except:
    ARABIC_FONT_AVAILABLE = False


def process_arabic_text(text):
    """Process Arabic text for proper RTL display in PDF"""
    if not text:
        return ''
    
    text_str = str(text)
    # Check if text contains Arabic characters
    has_arabic = any('\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F' for char in text_str)
    if has_arabic and ARABIC_FONT_AVAILABLE:
        try:
            reshaped = arabic_reshaper.reshape(text_str)
            return get_display(reshaped)
        except:
            return text_str
    return text_str


def safe_arabic(text):
    """Safely process any text that might contain Arabic"""
    if not text:
        return '-'
    return process_arabic_text(str(text))


def generate_transaction_pdf(transaction: dict, employee: dict = None) -> tuple:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm, leftMargin=15*mm, rightMargin=15*mm)
    styles = getSampleStyleSheet()
    
    # Create styles with Arabic font support
    base_font = 'NotoArabic' if ARABIC_FONT_AVAILABLE else 'Helvetica'
    bold_font = 'NotoArabicBold' if ARABIC_FONT_AVAILABLE else 'Helvetica-Bold'
    
    title_style = ParagraphStyle(
        'TitleStyle', 
        parent=styles['Title'], 
        fontSize=16, 
        spaceAfter=12,
        fontName=bold_font
    )
    heading_style = ParagraphStyle(
        'HeadingStyle', 
        parent=styles['Heading2'], 
        fontSize=12, 
        spaceAfter=6,
        fontName=bold_font
    )
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontName=base_font,
        fontSize=10
    )
    bold_style = ParagraphStyle(
        'BoldStyle',
        parent=styles['Normal'],
        fontName=bold_font,
        fontSize=10
    )
    
    elements = []
    integrity_id = str(uuid.uuid4())[:12].upper()

    # Title - bilingual
    elements.append(Paragraph("DAR AL CODE ENGINEERING CONSULTANCY", title_style))
    elements.append(Paragraph(process_arabic_text("شركة دار الكود للاستشارات الهندسية"), ParagraphStyle('ArabicTitle', parent=title_style, fontSize=14)))
    elements.append(Paragraph("HR Transaction Record / سجل معاملة الموارد البشرية", heading_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    elements.append(Spacer(1, 10))

    # Basic info
    info_data = [
        ["Reference No / رقم المرجع:", transaction.get('ref_no', 'N/A')],
        ["Type / النوع:", transaction.get('type', 'N/A').replace('_', ' ').title()],
        ["Status / الحالة:", transaction.get('status', 'N/A').replace('_', ' ').title()],
        ["Integrity ID / معرف السلامة:", integrity_id],
        ["Generated / تاريخ الإنشاء:", datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')],
    ]
    if employee:
        emp_name = employee.get('full_name', 'N/A')
        emp_name_ar = employee.get('full_name_ar', '')
        name_display = f"{emp_name}"
        if emp_name_ar:
            name_display += f" / {process_arabic_text(emp_name_ar)}"
        info_data.insert(1, ["Employee / الموظف:", name_display])
        info_data.insert(2, ["Employee No / رقم الموظف:", employee.get('employee_number', 'N/A')])

    info_table = Table(info_data, colWidths=[150, 320])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), bold_font if ARABIC_FONT_AVAILABLE else 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), base_font if ARABIC_FONT_AVAILABLE else 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 15))

    # Transaction Details
    elements.append(Paragraph("Transaction Details / تفاصيل المعاملة", heading_style))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    elements.append(Spacer(1, 8))
    
    tx_data = transaction.get('data', {})
    for key, value in tx_data.items():
        label = key.replace('_', ' ').title()
        val_str = str(value) if value is not None else '-'
        # Process Arabic text in values
        if any('\u0600' <= char <= '\u06FF' for char in val_str):
            val_str = process_arabic_text(val_str)
        elements.append(Paragraph(f"<b>{label}:</b> {val_str}", normal_style))
    elements.append(Spacer(1, 15))

    # Timeline
    if transaction.get('timeline'):
        elements.append(Paragraph("Transaction Timeline / الجدول الزمني", heading_style))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        elements.append(Spacer(1, 8))
        timeline_data = [["Date / التاريخ", "Event / الحدث", "Actor / المنفذ", "Note / ملاحظة"]]
        for event in transaction['timeline']:
            actor_name = event.get('actor_name', '')
            timeline_data.append([
                str(event.get('timestamp', ''))[:19],
                event.get('event', ''),
                actor_name,
                event.get('note', '')
            ])
        t = Table(timeline_data, colWidths=[100, 100, 130, 140])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.06, 0.09, 0.16)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), bold_font if ARABIC_FONT_AVAILABLE else 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), base_font if ARABIC_FONT_AVAILABLE else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))

    # Approval Chain
    if transaction.get('approval_chain'):
        elements.append(Paragraph("Approval Chain / سلسلة الموافقات", heading_style))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        elements.append(Spacer(1, 8))
        approval_data = [["Stage / المرحلة", "Approver / المعتمد", "Status / الحالة", "Date / التاريخ"]]
        for a in transaction['approval_chain']:
            approval_data.append([
                a.get('stage', ''), 
                a.get('approver_name', ''),
                a.get('status', ''), 
                str(a.get('timestamp', ''))[:19]
            ])
        at = Table(approval_data, colWidths=[100, 140, 100, 130])
        at.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.06, 0.09, 0.16)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), bold_font if ARABIC_FONT_AVAILABLE else 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), base_font if ARABIC_FONT_AVAILABLE else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(at)

    # Footer
    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    elements.append(Spacer(1, 5))
    footer_text = f"Document generated by DAR AL CODE HR OS | Integrity verified | ID: {integrity_id}"
    elements.append(Paragraph(footer_text, ParagraphStyle('Footer', parent=normal_style, fontSize=7, textColor=colors.grey)))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    return pdf_bytes, pdf_hash, integrity_id
