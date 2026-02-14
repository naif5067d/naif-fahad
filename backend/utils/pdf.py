"""
Professional PDF Generator for DAR AL CODE HR OS
Single A4 Page - Clean Layout - QR/Barcode Signatures
"""
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import code128
from reportlab.graphics.shapes import Drawing
import hashlib
import uuid
import io
import os
from datetime import datetime, timezone

# Register Arabic fonts
FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')
ARABIC_FONT = False
try:
    pdfmetrics.registerFont(TTFont('Arabic', os.path.join(FONTS_DIR, 'NotoSansArabic-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('ArabicBold', os.path.join(FONTS_DIR, 'NotoSansArabic-Bold.ttf')))
    ARABIC_FONT = True
except:
    pass

# Colors
NAVY = colors.Color(0.12, 0.23, 0.37)
GRAY_BG = colors.Color(0.97, 0.97, 0.98)
GRAY_BORDER = colors.Color(0.85, 0.85, 0.87)


def format_time(ts):
    """Format timestamp to Saudi time"""
    if not ts:
        return '-'
    try:
        from datetime import timedelta
        if isinstance(ts, str):
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        else:
            dt = ts
        saudi = dt + timedelta(hours=3)
        return saudi.strftime('%Y-%m-%d %H:%M')
    except:
        return str(ts)[:16]


def create_barcode(code, width=50, height=15):
    """Create barcode drawing"""
    try:
        barcode = code128.Code128(code, barWidth=0.5*mm, barHeight=height*mm)
        d = Drawing(width*mm, height*mm)
        d.add(barcode)
        return d
    except:
        return Paragraph(f"[{code}]", ParagraphStyle('bc', fontSize=6))


def generate_transaction_pdf(transaction: dict, employee: dict = None, lang: str = 'ar') -> tuple:
    """Generate single-page professional PDF"""
    buffer = io.BytesIO()
    
    # Smaller margins to fit content
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=10*mm, bottomMargin=10*mm,
        leftMargin=12*mm, rightMargin=12*mm
    )
    
    # Font selection
    if lang == 'ar' and ARABIC_FONT:
        font = 'Arabic'
        font_bold = 'ArabicBold'
    else:
        font = 'Helvetica'
        font_bold = 'Helvetica-Bold'
    
    # Compact styles
    styles = {
        'title': ParagraphStyle('t', fontSize=14, fontName=font_bold, textColor=NAVY, alignment=TA_CENTER, spaceAfter=2*mm),
        'subtitle': ParagraphStyle('st', fontSize=10, fontName=font_bold, textColor=NAVY, alignment=TA_CENTER, spaceAfter=3*mm),
        'section': ParagraphStyle('s', fontSize=9, fontName=font_bold, textColor=NAVY, spaceBefore=4*mm, spaceAfter=2*mm),
        'label': ParagraphStyle('l', fontSize=7, fontName=font, textColor=colors.gray),
        'value': ParagraphStyle('v', fontSize=8, fontName=font_bold, textColor=colors.black),
        'small': ParagraphStyle('sm', fontSize=6, fontName=font, textColor=colors.gray, alignment=TA_CENTER),
    }
    
    elements = []
    integrity_id = str(uuid.uuid4())[:12].upper()
    
    # === HEADER ===
    if lang == 'ar':
        company = "شركة دار الكود للاستشارات الهندسية"
    else:
        company = "DAR AL CODE ENGINEERING CONSULTANCY"
    
    elements.append(Paragraph(company, styles['title']))
    
    # Line
    elements.append(Table([['']], colWidths=[186*mm], rowHeights=[1]))
    elements[-1].setStyle(TableStyle([('LINEABOVE', (0,0), (-1,0), 2, NAVY)]))
    elements.append(Spacer(1, 2*mm))
    
    # === DOCUMENT TYPE ===
    tx_type = transaction.get('type', '')
    type_labels = {
        'ar': {'leave_request': 'طلب إجازة', 'finance_60': 'عهدة مالية', 'tangible_custody': 'عهدة ملموسة', 'settlement': 'تسوية', 'contract': 'عقد'},
        'en': {'leave_request': 'Leave Request', 'finance_60': 'Financial Custody', 'tangible_custody': 'Tangible Custody', 'settlement': 'Settlement', 'contract': 'Contract'}
    }
    doc_type = type_labels.get(lang, type_labels['en']).get(tx_type, tx_type)
    elements.append(Paragraph(doc_type, styles['subtitle']))
    
    # === REF & STATUS BOX ===
    status = transaction.get('status', '')
    status_labels = {
        'ar': {'executed': 'منفذة', 'rejected': 'مرفوضة', 'cancelled': 'ملغاة', 'stas': 'STAS', 'pending_supervisor': 'بانتظار المشرف', 'pending_ops': 'بانتظار العمليات', 'pending_ceo': 'بانتظار CEO'},
        'en': {'executed': 'Executed', 'rejected': 'Rejected', 'cancelled': 'Cancelled', 'stas': 'STAS', 'pending_supervisor': 'Pending Supervisor', 'pending_ops': 'Pending Ops', 'pending_ceo': 'Pending CEO'}
    }
    status_text = status_labels.get(lang, status_labels['en']).get(status, status)
    
    ref_label = 'رقم المرجع' if lang == 'ar' else 'Ref No'
    status_label = 'الحالة' if lang == 'ar' else 'Status'
    date_label = 'التاريخ' if lang == 'ar' else 'Date'
    id_label = 'المعرف' if lang == 'ar' else 'ID'
    
    info_data = [
        [ref_label, transaction.get('ref_no', '-'), status_label, status_text],
        [date_label, format_time(transaction.get('created_at')), id_label, integrity_id],
    ]
    
    info_table = Table(info_data, colWidths=[30*mm, 55*mm, 30*mm, 55*mm], rowHeights=[7*mm, 7*mm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), GRAY_BG),
        ('BOX', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
        ('FONTNAME', (0, 0), (-1, -1), font),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('FONTNAME', (0, 0), (0, -1), font_bold),
        ('FONTNAME', (2, 0), (2, -1), font_bold),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.gray),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.gray),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(info_table)
    
    # === EMPLOYEE INFO ===
    if employee:
        emp_label = 'معلومات الموظف' if lang == 'ar' else 'Employee'
        elements.append(Paragraph(emp_label, styles['section']))
        
        name_label = 'الاسم' if lang == 'ar' else 'Name'
        num_label = 'الرقم' if lang == 'ar' else 'No'
        
        emp_name = employee.get('full_name_ar' if lang == 'ar' else 'full_name', employee.get('full_name', '-'))
        emp_num = employee.get('employee_number', '-')
        
        emp_data = [[name_label, emp_name, num_label, str(emp_num)]]
        emp_table = Table(emp_data, colWidths=[25*mm, 75*mm, 25*mm, 45*mm], rowHeights=[6*mm])
        emp_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('FONTNAME', (0, 0), (0, 0), font_bold),
            ('FONTNAME', (2, 0), (2, 0), font_bold),
            ('TEXTCOLOR', (0, 0), (0, 0), colors.gray),
            ('TEXTCOLOR', (2, 0), (2, 0), colors.gray),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(emp_table)
    
    # === TRANSACTION DETAILS ===
    details_label = 'تفاصيل المعاملة' if lang == 'ar' else 'Details'
    elements.append(Paragraph(details_label, styles['section']))
    
    tx_data = transaction.get('data', {})
    
    # Field labels
    field_labels = {
        'ar': {'leave_type': 'نوع الإجازة', 'start_date': 'من', 'end_date': 'إلى', 'working_days': 'الأيام', 'reason': 'السبب', 'amount': 'المبلغ', 'description': 'الوصف', 'itemname': 'العنصر', 'employee_name': 'الموظف'},
        'en': {'leave_type': 'Type', 'start_date': 'From', 'end_date': 'To', 'working_days': 'Days', 'reason': 'Reason', 'amount': 'Amount', 'description': 'Desc', 'itemname': 'Item', 'employee_name': 'Employee'}
    }
    
    leave_types = {
        'ar': {'annual': 'سنوية', 'sick': 'مرضية', 'emergency': 'طارئة'},
        'en': {'annual': 'Annual', 'sick': 'Sick', 'emergency': 'Emergency'}
    }
    
    details_rows = []
    skip_keys = ['employee_name_ar', 'balance_before', 'balance_after', 'adjusted_end_date', 'sick_tier_info']
    
    for key, value in tx_data.items():
        if key in skip_keys:
            continue
        if key == 'employee_name' and lang == 'ar' and 'employee_name_ar' in tx_data:
            value = tx_data['employee_name_ar']
        
        label = field_labels.get(lang, field_labels['en']).get(key, key)
        
        # Format value
        if value is None:
            val = '-'
        elif key == 'leave_type':
            val = leave_types.get(lang, leave_types['en']).get(str(value), str(value))
        elif key in ('amount', 'estimatedvalue'):
            val = f"{value} SAR"
        else:
            val = str(value)
        
        details_rows.append([label, val])
    
    if details_rows:
        # Split into 2 columns if more than 3 rows
        if len(details_rows) > 3:
            mid = (len(details_rows) + 1) // 2
            col1 = details_rows[:mid]
            col2 = details_rows[mid:] + [['', '']] * (mid - len(details_rows[mid:]))
            combined = []
            for i in range(mid):
                combined.append([col1[i][0], col1[i][1], col2[i][0] if i < len(col2) else '', col2[i][1] if i < len(col2) else ''])
            details_table = Table(combined, colWidths=[25*mm, 55*mm, 25*mm, 55*mm], rowHeights=[6*mm] * len(combined))
        else:
            details_table = Table(details_rows, colWidths=[35*mm, 135*mm], rowHeights=[6*mm] * len(details_rows))
        
        details_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.gray),
            ('TEXTCOLOR', (2, 0), (2, -1), colors.gray) if len(details_rows) > 3 else ('TEXTCOLOR', (0, 0), (0, -1), colors.gray),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBELOW', (0, 0), (-1, -2), 0.3, GRAY_BORDER),
        ]))
        elements.append(details_table)
    
    # === APPROVAL CHAIN WITH SIGNATURES ===
    if transaction.get('approval_chain'):
        approval_label = 'سلسلة الموافقات' if lang == 'ar' else 'Approvals'
        elements.append(Paragraph(approval_label, styles['section']))
        
        stage_labels = {
            'ar': {'supervisor': 'المشرف', 'ops': 'العمليات', 'finance': 'المالية', 'ceo': 'CEO', 'stas': 'STAS', 'employee_accept': 'الموظف'},
            'en': {'supervisor': 'Supervisor', 'ops': 'Operations', 'finance': 'Finance', 'ceo': 'CEO', 'stas': 'STAS', 'employee_accept': 'Employee'}
        }
        
        action_labels = {
            'ar': {'approve': 'موافق', 'reject': 'رافض', 'escalate': 'تصعيد'},
            'en': {'approve': 'Approved', 'reject': 'Rejected', 'escalate': 'Escalated'}
        }
        
        # Headers
        h_stage = 'المرحلة' if lang == 'ar' else 'Stage'
        h_by = 'بواسطة' if lang == 'ar' else 'By'
        h_action = 'القرار' if lang == 'ar' else 'Action'
        h_date = 'التاريخ' if lang == 'ar' else 'Date'
        h_sig = 'التوقيع' if lang == 'ar' else 'Signature'
        
        approval_data = [[h_stage, h_by, h_action, h_date, h_sig]]
        
        for a in transaction['approval_chain']:
            stage = a.get('stage', '')
            stage_text = stage_labels.get(lang, stage_labels['en']).get(stage, stage.upper())
            
            approver = a.get('approver_name', '-')
            action = a.get('status', '')
            action_text = action_labels.get(lang, action_labels['en']).get(action, action)
            date = format_time(a.get('timestamp'))
            
            # Signature: STAS = Barcode, others = short code
            if stage == 'stas':
                sig = create_barcode(f"STAS-{integrity_id[:6]}", width=30, height=8)
            else:
                sig = f"[{a.get('approver_id', '')[:6]}]"
            
            approval_data.append([stage_text, approver, action_text, date, sig])
        
        approval_table = Table(approval_data, colWidths=[28*mm, 40*mm, 25*mm, 35*mm, 42*mm], rowHeights=[8*mm] * len(approval_data))
        approval_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), font_bold),
            ('FONTNAME', (0, 1), (-1, -1), font),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
            ('LINEBELOW', (0, 0), (-1, -2), 0.3, GRAY_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(approval_table)
    
    # === EXECUTION STAMP (if executed) ===
    if transaction.get('status') == 'executed':
        elements.append(Spacer(1, 3*mm))
        
        stamp_label = 'تم التنفيذ بواسطة STAS' if lang == 'ar' else 'EXECUTED BY STAS'
        stamp_date = format_time(transaction.get('updated_at'))
        
        stamp_data = [
            [stamp_label],
            [create_barcode(f"EXEC-{transaction.get('ref_no')}-{integrity_id}", width=60, height=12)],
            [stamp_date]
        ]
        
        stamp_table = Table(stamp_data, colWidths=[70*mm], rowHeights=[6*mm, 15*mm, 5*mm])
        stamp_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), font_bold),
            ('FONTSIZE', (0, 0), (0, 0), 9),
            ('FONTSIZE', (0, 2), (0, 2), 6),
            ('TEXTCOLOR', (0, 0), (0, 0), NAVY),
            ('TEXTCOLOR', (0, 2), (0, 2), colors.gray),
            ('BOX', (0, 0), (-1, -1), 1, NAVY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        # Center the stamp
        outer = Table([[stamp_table]], colWidths=[186*mm])
        outer.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
        elements.append(outer)
    
    # === FOOTER ===
    elements.append(Spacer(1, 3*mm))
    elements.append(Table([['']], colWidths=[186*mm], rowHeights=[1]))
    elements[-1].setStyle(TableStyle([('LINEABOVE', (0,0), (-1,0), 0.5, GRAY_BORDER)]))
    
    footer_text = f"DAR AL CODE HR OS | {integrity_id} | {format_time(datetime.now(timezone.utc).isoformat())}"
    elements.append(Paragraph(footer_text, styles['small']))
    
    # Build
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    return pdf_bytes, pdf_hash, integrity_id
