"""
Professional PDF Generator for DAR AL CODE HR OS
Single A4 Page - Arabic/English Support - QR/Barcode Signatures
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import code128
from reportlab.graphics.shapes import Drawing
import qrcode
import hashlib
import uuid
import io
import os
from datetime import datetime, timezone, timedelta

# Constants
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 15 * mm
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)

# Colors
NAVY = colors.Color(0.12, 0.23, 0.37)
LIGHT_GRAY = colors.Color(0.96, 0.96, 0.97)
BORDER_GRAY = colors.Color(0.85, 0.85, 0.87)
TEXT_GRAY = colors.Color(0.4, 0.4, 0.45)

# Font Registration
FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')

# Try multiple Arabic fonts in order of preference
ARABIC_FONT_AVAILABLE = False
FONT_REGULAR = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'

# Try Noto Naskh Arabic first (better for traditional Arabic text)
for font_name, regular_file, bold_file in [
    ('NotoNaskh', 'NotoNaskhArabic-Regular.ttf', 'NotoNaskhArabic-Bold.ttf'),
    ('NotoSans', 'NotoSansArabic-Regular.ttf', 'NotoSansArabic-Bold.ttf'),
]:
    try:
        regular_path = os.path.join(FONTS_DIR, regular_file)
        bold_path = os.path.join(FONTS_DIR, bold_file)
        if os.path.exists(regular_path) and os.path.getsize(regular_path) > 1000:
            pdfmetrics.registerFont(TTFont(f'{font_name}Arabic', regular_path))
            if os.path.exists(bold_path) and os.path.getsize(bold_path) > 1000:
                pdfmetrics.registerFont(TTFont(f'{font_name}ArabicBold', bold_path))
            else:
                pdfmetrics.registerFont(TTFont(f'{font_name}ArabicBold', regular_path))
            FONT_REGULAR = f'{font_name}Arabic'
            FONT_BOLD = f'{font_name}ArabicBold'
            ARABIC_FONT_AVAILABLE = True
            break
    except Exception as e:
        continue


def format_saudi_time(ts):
    """Format timestamp to Saudi Arabia time (UTC+3)"""
    if not ts:
        return '-'
    try:
        if isinstance(ts, str):
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        else:
            dt = ts
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        saudi_time = dt + timedelta(hours=3)
        return saudi_time.strftime('%Y-%m-%d %H:%M')
    except:
        return str(ts)[:16] if ts else '-'


def create_qr_code(data: str, size: int = 25) -> Image:
    """Create QR code image for signatures"""
    try:
        qr = qrcode.QRCode(version=1, box_size=3, border=1)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return Image(buffer, width=size*mm, height=size*mm)
    except:
        return None


def create_barcode_drawing(code: str, width: int = 50, height: int = 12):
    """Create barcode drawing for STAS signature"""
    try:
        barcode = code128.Code128(code, barWidth=0.4*mm, barHeight=height*mm)
        d = Drawing(width*mm, (height+3)*mm)
        d.add(barcode)
        return d
    except:
        return None


def get_styles(lang: str):
    """Get paragraph styles based on language"""
    font = FONT_REGULAR if lang == 'ar' and ARABIC_FONT_AVAILABLE else 'Helvetica'
    font_bold = FONT_BOLD if lang == 'ar' and ARABIC_FONT_AVAILABLE else 'Helvetica-Bold'
    align = TA_RIGHT if lang == 'ar' else TA_LEFT
    
    return {
        'title': ParagraphStyle('title', fontSize=14, fontName=font_bold, textColor=NAVY, alignment=TA_CENTER, spaceAfter=2*mm),
        'subtitle': ParagraphStyle('subtitle', fontSize=11, fontName=font_bold, textColor=NAVY, alignment=TA_CENTER, spaceAfter=4*mm),
        'section': ParagraphStyle('section', fontSize=9, fontName=font_bold, textColor=NAVY, spaceBefore=4*mm, spaceAfter=2*mm, alignment=align),
        'normal': ParagraphStyle('normal', fontSize=8, fontName=font, textColor=colors.black, alignment=align),
        'small': ParagraphStyle('small', fontSize=6, fontName=font, textColor=TEXT_GRAY, alignment=TA_CENTER),
        'label': ParagraphStyle('label', fontSize=7, fontName=font, textColor=TEXT_GRAY, alignment=align),
        'value': ParagraphStyle('value', fontSize=8, fontName=font_bold, textColor=colors.black, alignment=align),
    }


def get_labels(lang: str):
    """Get all labels based on language"""
    if lang == 'ar':
        return {
            'company': 'شركة دار الكود للاستشارات الهندسية',
            'slogan': 'التميز الهندسي',
            'ref_no': 'رقم المرجع',
            'status': 'الحالة',
            'date': 'التاريخ',
            'integrity_id': 'معرف السلامة',
            'employee_info': 'معلومات الموظف',
            'name': 'الاسم',
            'emp_no': 'الرقم الوظيفي',
            'details': 'تفاصيل المعاملة',
            'approvals': 'سلسلة الموافقات',
            'stage': 'المرحلة',
            'approver': 'المعتمد',
            'action': 'الإجراء',
            'time': 'الوقت',
            'signature': 'التوقيع',
            'executed_by': 'تم التنفيذ بواسطة STAS',
            # Transaction types
            'leave_request': 'طلب إجازة',
            'finance_60': 'عهدة مالية',
            'tangible_custody': 'عهدة ملموسة',
            'settlement': 'تسوية',
            'contract': 'عقد',
            'salary_advance': 'سلفة راتب',
            # Statuses
            'executed': 'منفذة',
            'rejected': 'مرفوضة',
            'cancelled': 'ملغاة',
            'stas': 'STAS',
            'pending_supervisor': 'بانتظار المشرف',
            'pending_ops': 'بانتظار العمليات',
            'pending_finance': 'بانتظار المالية',
            'pending_ceo': 'بانتظار CEO',
            'pending_employee_accept': 'بانتظار الموظف',
            # Stages
            'supervisor': 'المشرف',
            'ops': 'العمليات',
            'finance': 'المالية',
            'ceo': 'CEO',
            'employee_accept': 'الموظف',
            # Actions
            'approve': 'موافقة',
            'reject': 'رفض',
            'escalate': 'تصعيد',
            # Data fields
            'leave_type': 'نوع الإجازة',
            'start_date': 'من تاريخ',
            'end_date': 'إلى تاريخ',
            'working_days': 'أيام العمل',
            'reason': 'السبب',
            'amount': 'المبلغ',
            'description': 'الوصف',
            'itemname': 'اسم العنصر',
            'estimatedvalue': 'القيمة التقديرية',
            # Leave types
            'annual': 'سنوية',
            'sick': 'مرضية',
            'emergency': 'طارئة',
        }
    else:
        return {
            'company': 'DAR AL CODE ENGINEERING CONSULTANCY',
            'slogan': 'Engineering Excellence',
            'ref_no': 'Reference No',
            'status': 'Status',
            'date': 'Date',
            'integrity_id': 'Integrity ID',
            'employee_info': 'Employee Information',
            'name': 'Name',
            'emp_no': 'Employee No',
            'details': 'Transaction Details',
            'approvals': 'Approval Chain',
            'stage': 'Stage',
            'approver': 'Approver',
            'action': 'Action',
            'time': 'Time',
            'signature': 'Signature',
            'executed_by': 'Executed by STAS',
            # Transaction types
            'leave_request': 'Leave Request',
            'finance_60': 'Financial Custody',
            'tangible_custody': 'Tangible Custody',
            'settlement': 'Settlement',
            'contract': 'Contract',
            'salary_advance': 'Salary Advance',
            # Statuses
            'executed': 'Executed',
            'rejected': 'Rejected',
            'cancelled': 'Cancelled',
            'stas': 'STAS',
            'pending_supervisor': 'Pending Supervisor',
            'pending_ops': 'Pending Operations',
            'pending_finance': 'Pending Finance',
            'pending_ceo': 'Pending CEO',
            'pending_employee_accept': 'Pending Employee',
            # Stages
            'supervisor': 'Supervisor',
            'ops': 'Operations',
            'finance': 'Finance',
            'ceo': 'CEO',
            'employee_accept': 'Employee',
            # Actions
            'approve': 'Approved',
            'reject': 'Rejected',
            'escalate': 'Escalated',
            # Data fields
            'leave_type': 'Leave Type',
            'start_date': 'Start Date',
            'end_date': 'End Date',
            'working_days': 'Working Days',
            'reason': 'Reason',
            'amount': 'Amount',
            'description': 'Description',
            'itemname': 'Item Name',
            'estimatedvalue': 'Estimated Value',
            # Leave types
            'annual': 'Annual',
            'sick': 'Sick',
            'emergency': 'Emergency',
        }


def generate_transaction_pdf(transaction: dict, employee: dict = None, lang: str = 'ar') -> tuple:
    """Generate professional single-page PDF for transaction"""
    buffer = io.BytesIO()
    
    # Create document with tight margins
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=12*mm,
        bottomMargin=10*mm,
        leftMargin=MARGIN,
        rightMargin=MARGIN
    )
    
    styles = get_styles(lang)
    labels = get_labels(lang)
    font = FONT_REGULAR if lang == 'ar' and ARABIC_FONT_AVAILABLE else 'Helvetica'
    font_bold = FONT_BOLD if lang == 'ar' and ARABIC_FONT_AVAILABLE else 'Helvetica-Bold'
    
    elements = []
    integrity_id = str(uuid.uuid4())[:12].upper()
    
    # ============ HEADER ============
    elements.append(Paragraph(labels['company'], styles['title']))
    
    # Decorative line
    line_table = Table([['']], colWidths=[CONTENT_WIDTH], rowHeights=[1.5])
    line_table.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, 0), 2, NAVY)]))
    elements.append(line_table)
    elements.append(Spacer(1, 3*mm))
    
    # ============ DOCUMENT TYPE ============
    tx_type = transaction.get('type', '')
    doc_type = labels.get(tx_type, tx_type.replace('_', ' ').title())
    elements.append(Paragraph(doc_type, styles['subtitle']))
    
    # ============ INFO BOX (Ref, Status, Date, ID) ============
    status_raw = transaction.get('status', '')
    status_text = labels.get(status_raw, status_raw.replace('_', ' ').title())
    
    info_data = [
        [labels['ref_no'], transaction.get('ref_no', '-'), labels['status'], status_text],
        [labels['date'], format_saudi_time(transaction.get('created_at')), labels['integrity_id'], integrity_id],
    ]
    
    col_widths = [28*mm, 60*mm, 28*mm, 54*mm]
    info_table = Table(info_data, colWidths=col_widths, rowHeights=[7*mm, 7*mm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('FONTNAME', (0, 0), (-1, -1), font),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('FONTNAME', (0, 0), (0, -1), font_bold),
        ('FONTNAME', (2, 0), (2, -1), font_bold),
        ('TEXTCOLOR', (0, 0), (0, -1), TEXT_GRAY),
        ('TEXTCOLOR', (2, 0), (2, -1), TEXT_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    
    # ============ EMPLOYEE INFO ============
    if employee:
        elements.append(Paragraph(labels['employee_info'], styles['section']))
        
        emp_name = employee.get('full_name_ar' if lang == 'ar' else 'full_name', employee.get('full_name', '-'))
        emp_no = employee.get('employee_number', '-')
        
        emp_data = [[labels['name'], emp_name, labels['emp_no'], str(emp_no)]]
        emp_table = Table(emp_data, colWidths=[25*mm, 80*mm, 25*mm, 40*mm], rowHeights=[6*mm])
        emp_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('FONTNAME', (0, 0), (0, 0), font_bold),
            ('FONTNAME', (2, 0), (2, 0), font_bold),
            ('TEXTCOLOR', (0, 0), (0, 0), TEXT_GRAY),
            ('TEXTCOLOR', (2, 0), (2, 0), TEXT_GRAY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(emp_table)
    
    # ============ TRANSACTION DETAILS ============
    elements.append(Paragraph(labels['details'], styles['section']))
    
    tx_data = transaction.get('data', {})
    skip_fields = ['employee_name_ar', 'balance_before', 'balance_after', 'adjusted_end_date', 'sick_tier_info']
    
    details_rows = []
    for key, value in tx_data.items():
        if key in skip_fields:
            continue
        if key == 'employee_name' and lang == 'ar' and 'employee_name_ar' in tx_data:
            value = tx_data['employee_name_ar']
        
        # Get label
        field_label = labels.get(key, key.replace('_', ' ').title())
        
        # Format value
        if value is None:
            formatted_val = '-'
        elif key == 'leave_type':
            formatted_val = labels.get(str(value), str(value))
        elif key in ('amount', 'estimatedvalue', 'estimated_value'):
            formatted_val = f"{value} SAR"
        else:
            formatted_val = str(value)
        
        details_rows.append([field_label, formatted_val])
    
    if details_rows:
        # Arrange in 2 columns if more than 3 items
        if len(details_rows) > 3:
            mid = (len(details_rows) + 1) // 2
            col1 = details_rows[:mid]
            col2 = details_rows[mid:]
            # Pad shorter column
            while len(col2) < len(col1):
                col2.append(['', ''])
            
            combined = []
            for i in range(len(col1)):
                combined.append([col1[i][0], col1[i][1], col2[i][0] if i < len(col2) else '', col2[i][1] if i < len(col2) else ''])
            
            details_table = Table(combined, colWidths=[28*mm, 55*mm, 28*mm, 55*mm], rowHeights=[6*mm] * len(combined))
            details_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), font),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('TEXTCOLOR', (0, 0), (0, -1), TEXT_GRAY),
                ('TEXTCOLOR', (2, 0), (2, -1), TEXT_GRAY),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LINEBELOW', (0, 0), (-1, -2), 0.3, BORDER_GRAY),
            ]))
        else:
            details_table = Table(details_rows, colWidths=[40*mm, 130*mm], rowHeights=[6*mm] * len(details_rows))
            details_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), font),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('TEXTCOLOR', (0, 0), (0, -1), TEXT_GRAY),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LINEBELOW', (0, 0), (-1, -2), 0.3, BORDER_GRAY),
            ]))
        
        elements.append(details_table)
    
    # ============ APPROVAL CHAIN ============
    approval_chain = transaction.get('approval_chain', [])
    if approval_chain:
        elements.append(Paragraph(labels['approvals'], styles['section']))
        
        # Table headers
        headers = [labels['stage'], labels['approver'], labels['action'], labels['time'], labels['signature']]
        approval_data = [headers]
        
        for approval in approval_chain:
            stage = approval.get('stage', '')
            stage_label = labels.get(stage, stage.upper())
            if stage in ('stas', 'ceo'):
                stage_label = stage.upper()
            
            approver = approval.get('approver_name', '-')
            action = approval.get('status', '')
            action_label = labels.get(action, action.title())
            timestamp = format_saudi_time(approval.get('timestamp'))
            
            # Signature: STAS gets barcode, others get QR code reference
            if stage == 'stas':
                sig = f"[BAR:{integrity_id[:6]}]"
            else:
                sig = f"[QR:{approval.get('approver_id', '')[:6]}]"
            
            approval_data.append([stage_label, approver, action_label, timestamp, sig])
        
        # Create table with better proportions
        approval_table = Table(
            approval_data, 
            colWidths=[30*mm, 45*mm, 28*mm, 38*mm, 29*mm], 
            rowHeights=[7*mm] * len(approval_data)
        )
        approval_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), font_bold),
            ('FONTNAME', (0, 1), (-1, -1), font),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
            ('LINEBELOW', (0, 0), (-1, -1), 0.3, BORDER_GRAY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(approval_table)
    
    # ============ EXECUTION STAMP (if executed) ============
    if transaction.get('status') == 'executed':
        elements.append(Spacer(1, 4*mm))
        
        stamp_text = labels['executed_by']
        stamp_date = format_saudi_time(transaction.get('updated_at'))
        barcode_code = f"EXEC-{transaction.get('ref_no', 'NA')[-8:]}-{integrity_id[:4]}"
        
        # Create barcode
        barcode_drawing = create_barcode_drawing(barcode_code, width=55, height=10)
        
        stamp_data = [[Paragraph(stamp_text, styles['section'])]]
        if barcode_drawing:
            stamp_data.append([barcode_drawing])
        else:
            stamp_data.append([Paragraph(f"[{barcode_code}]", styles['small'])])
        stamp_data.append([Paragraph(stamp_date, styles['small'])])
        
        stamp_table = Table(stamp_data, colWidths=[65*mm], rowHeights=[6*mm, 14*mm, 5*mm])
        stamp_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, NAVY),
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ]))
        
        # Center the stamp
        outer = Table([[stamp_table]], colWidths=[CONTENT_WIDTH])
        outer.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
        elements.append(outer)
    
    # ============ FOOTER ============
    elements.append(Spacer(1, 4*mm))
    footer_line = Table([['']], colWidths=[CONTENT_WIDTH], rowHeights=[0.5])
    footer_line.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, 0), 0.5, BORDER_GRAY)]))
    elements.append(footer_line)
    
    footer_text = f"DAR AL CODE HR OS | {integrity_id} | {format_saudi_time(datetime.now(timezone.utc).isoformat())}"
    elements.append(Spacer(1, 1*mm))
    elements.append(Paragraph(footer_text, styles['small']))
    
    # Build document
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    return pdf_bytes, pdf_hash, integrity_id
