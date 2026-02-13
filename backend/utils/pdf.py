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
except Exception:
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
        except Exception:
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
        fontName=bold_font,
        alignment=1  # Center
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
    arabic_title_style = ParagraphStyle(
        'ArabicTitleStyle', 
        parent=title_style, 
        fontSize=14,
        alignment=1  # Center
    )
    
    elements = []
    integrity_id = str(uuid.uuid4())[:12].upper()

    # Title - bilingual
    elements.append(Paragraph("DAR AL CODE ENGINEERING CONSULTANCY", title_style))
    elements.append(Paragraph(safe_arabic("شركة دار الكود للاستشارات الهندسية"), arabic_title_style))
    elements.append(Paragraph(f"HR Transaction Record / {safe_arabic('سجل معاملة الموارد البشرية')}", heading_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    elements.append(Spacer(1, 10))

    # Translation maps for labels
    label_translations = {
        'leave_type': safe_arabic('نوع الإجازة'),
        'start_date': safe_arabic('تاريخ البداية'),
        'end_date': safe_arabic('تاريخ النهاية'),
        'adjusted_end_date': safe_arabic('تاريخ النهاية المعدل'),
        'working_days': safe_arabic('أيام العمل'),
        'reason': safe_arabic('السبب'),
        'employee_name': safe_arabic('اسم الموظف'),
        'employee_name_ar': safe_arabic('اسم الموظف'),
        'balance_before': safe_arabic('الرصيد قبل'),
        'balance_after': safe_arabic('الرصيد بعد'),
        'amount': safe_arabic('المبلغ'),
        'description': safe_arabic('الوصف'),
    }

    leave_type_translations = {
        'annual': safe_arabic('سنوية'),
        'sick': safe_arabic('مرضية'),
        'emergency': safe_arabic('طارئة'),
    }

    status_translations = {
        'pending_supervisor': safe_arabic('بانتظار المشرف'),
        'pending_ops': safe_arabic('بانتظار العمليات'),
        'pending_finance': safe_arabic('بانتظار المالية'),
        'pending_ceo': safe_arabic('بانتظار الرئيس'),
        'pending_stas': safe_arabic('بانتظار ستاس'),
        'executed': safe_arabic('منفذة'),
        'rejected': safe_arabic('مرفوضة'),
    }

    type_translations = {
        'leave_request': safe_arabic('طلب إجازة'),
        'finance_60': safe_arabic('معاملة مالية'),
        'settlement': safe_arabic('تسوية'),
        'contract': safe_arabic('عقد'),
    }

    # Get translated type and status
    tx_type = transaction.get('type', 'N/A')
    tx_type_ar = type_translations.get(tx_type, tx_type.replace('_', ' ').title())
    tx_type_display = f"{tx_type.replace('_', ' ').title()} / {tx_type_ar}"

    tx_status = transaction.get('status', 'N/A')
    tx_status_ar = status_translations.get(tx_status, tx_status.replace('_', ' ').title())
    tx_status_display = f"{tx_status.replace('_', ' ').title()} / {tx_status_ar}"

    # Basic info
    info_data = [
        [f"Reference No / {safe_arabic('رقم المرجع')}:", transaction.get('ref_no', 'N/A')],
        [f"Type / {safe_arabic('النوع')}:", tx_type_display],
        [f"Status / {safe_arabic('الحالة')}:", tx_status_display],
        [f"Integrity ID / {safe_arabic('معرف السلامة')}:", integrity_id],
        [f"Generated / {safe_arabic('تاريخ الإنشاء')}:", datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')],
    ]
    if employee:
        emp_name = employee.get('full_name', 'N/A')
        emp_name_ar = employee.get('full_name_ar', '')
        name_display = f"{emp_name}"
        if emp_name_ar:
            name_display += f" / {safe_arabic(emp_name_ar)}"
        info_data.insert(1, [f"Employee / {safe_arabic('الموظف')}:", name_display])
        info_data.insert(2, [f"Employee No / {safe_arabic('رقم الموظف')}:", employee.get('employee_number', 'N/A')])

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
    elements.append(Paragraph(f"Transaction Details / {safe_arabic('تفاصيل المعاملة')}", heading_style))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    elements.append(Spacer(1, 8))
    
    tx_data = transaction.get('data', {})
    for key, value in tx_data.items():
        label_en = key.replace('_', ' ').title()
        label_ar = label_translations.get(key, '')
        label = f"{label_en} / {label_ar}" if label_ar else label_en
        
        val_str = str(value) if value is not None else '-'
        
        # Translate specific values
        if key == 'leave_type' and val_str in leave_type_translations:
            val_str = f"{val_str.title()} / {leave_type_translations[val_str]}"
        elif any('\u0600' <= char <= '\u06FF' for char in val_str):
            val_str = safe_arabic(val_str)
        
        elements.append(Paragraph(f"<b>{label}:</b> {val_str}", normal_style))
    elements.append(Spacer(1, 15))

    # Timeline
    if transaction.get('timeline'):
        elements.append(Paragraph(f"Transaction Timeline / {safe_arabic('الجدول الزمني')}", heading_style))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        elements.append(Spacer(1, 8))
        
        event_translations = {
            'created': safe_arabic('تم الإنشاء'),
            'approved': safe_arabic('تمت الموافقة'),
            'rejected': safe_arabic('تم الرفض'),
            'executed': safe_arabic('تم التنفيذ'),
        }
        
        timeline_data = [[f"Date / {safe_arabic('التاريخ')}", f"Event / {safe_arabic('الحدث')}", f"Actor / {safe_arabic('المنفذ')}", f"Note / {safe_arabic('ملاحظة')}"]]
        for event in transaction['timeline']:
            actor_name = event.get('actor_name', '')
            event_name = event.get('event', '')
            event_ar = event_translations.get(event_name, event_name)
            timeline_data.append([
                str(event.get('timestamp', ''))[:19],
                f"{event_name} / {event_ar}",
                safe_arabic(actor_name) if any('\u0600' <= c <= '\u06FF' for c in actor_name) else actor_name,
                safe_arabic(event.get('note', '')) if event.get('note') else ''
            ])
        t = Table(timeline_data, colWidths=[90, 120, 130, 130])
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
        elements.append(Paragraph(f"Approval Chain / {safe_arabic('سلسلة الموافقات')}", heading_style))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        elements.append(Spacer(1, 8))
        
        stage_translations = {
            'supervisor': safe_arabic('المشرف'),
            'ops': safe_arabic('العمليات'),
            'finance': safe_arabic('المالية'),
            'ceo': safe_arabic('الرئيس'),
            'stas': safe_arabic('ستاس'),
        }
        
        approval_status_translations = {
            'approve': safe_arabic('موافق'),
            'reject': safe_arabic('مرفوض'),
            'pending': safe_arabic('معلق'),
        }
        
        approval_data = [[f"Stage / {safe_arabic('المرحلة')}", f"Approver / {safe_arabic('المعتمد')}", f"Status / {safe_arabic('الحالة')}", f"Date / {safe_arabic('التاريخ')}"]]
        for a in transaction['approval_chain']:
            stage = a.get('stage', '')
            stage_ar = stage_translations.get(stage, stage)
            status = a.get('status', '')
            status_ar = approval_status_translations.get(status, status)
            approver = a.get('approver_name', '')
            
            approval_data.append([
                f"{stage} / {stage_ar}", 
                safe_arabic(approver) if any('\u0600' <= c <= '\u06FF' for c in approver) else approver,
                f"{status} / {status_ar}", 
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
