"""
Professional PDF Generator for DAR AL CODE HR OS
FIXED VERSION - Uses Paragraph with RTL wordWrap for all Arabic text
Single A4 Page - Arabic/English Support - QR/Barcode Signatures
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image as RLImage
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import code128
from reportlab.graphics.shapes import Drawing
import arabic_reshaper
from bidi.algorithm import get_display
import qrcode
import hashlib
import uuid
import io
import os
import base64
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
ARABIC_FONT = 'NotoNaskhArabic'
ARABIC_FONT_BOLD = 'NotoNaskhArabicBold'
ENGLISH_FONT = 'Helvetica'
ENGLISH_FONT_BOLD = 'Helvetica-Bold'


def register_arabic_fonts():
    """Register Arabic fonts"""
    global ARABIC_FONT, ARABIC_FONT_BOLD
    
    font_pairs = [
        ('NotoNaskhArabic', 'NotoNaskhArabic-Regular.ttf', 'NotoNaskhArabic-Bold.ttf'),
        ('NotoSansArabic', 'NotoSansArabic-Regular.ttf', 'NotoSansArabic-Bold.ttf'),
    ]
    
    registered_any = False
    for font_name, regular_file, bold_file in font_pairs:
        try:
            regular_path = os.path.join(FONTS_DIR, regular_file)
            bold_path = os.path.join(FONTS_DIR, bold_file)
            
            if os.path.exists(regular_path) and os.path.getsize(regular_path) > 1000:
                pdfmetrics.registerFont(TTFont(font_name, regular_path))
                
                if os.path.exists(bold_path) and os.path.getsize(bold_path) > 1000:
                    pdfmetrics.registerFont(TTFont(f'{font_name}Bold', bold_path))
                else:
                    pdfmetrics.registerFont(TTFont(f'{font_name}Bold', regular_path))
                
                pdfmetrics.registerFontFamily(
                    font_name,
                    normal=font_name,
                    bold=f'{font_name}Bold',
                )
                
                if not registered_any:
                    ARABIC_FONT = font_name
                    ARABIC_FONT_BOLD = f'{font_name}Bold'
                    registered_any = True
                    
        except Exception as e:
            continue
    
    return registered_any


_fonts_registered = register_arabic_fonts()


def has_arabic(text):
    """Check if text contains Arabic characters"""
    if not text:
        return False
    return any('\u0600' <= c <= '\u06FF' for c in str(text))


def reshape_arabic(text):
    """Reshape Arabic text for proper RTL display"""
    if not text:
        return ''
    try:
        text_str = str(text)
        reshaped = arabic_reshaper.reshape(text_str)
        return get_display(reshaped)
    except Exception:
        return str(text)


def format_saudi_time(ts):
    """Format timestamp to Saudi Arabia time (UTC+3)"""
    if not ts:
        return '-'
    try:
        if isinstance(ts, str):
            ts_clean = ts.replace('Z', '+00:00')
            if 'T' in ts_clean:
                dt = datetime.fromisoformat(ts_clean)
            else:
                dt = datetime.strptime(ts_clean[:19], '%Y-%m-%d %H:%M:%S')
        else:
            dt = ts
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        saudi_time = dt + timedelta(hours=3)
        return saudi_time.strftime('%Y-%m-%d %H:%M')
    except Exception:
        ts_str = str(ts)
        if len(ts_str) >= 8 and ts_str[:8].isdigit():
            return f"{ts_str[:4]}-{ts_str[4:6]}-{ts_str[6:8]}"
        return str(ts)[:16] if ts else '-'


def format_date_only(date_str):
    """Format date with separators: YYYY-MM-DD"""
    if not date_str:
        return '-'
    try:
        date_str = str(date_str).strip()
        if '-' in date_str and len(date_str.split('-')[0]) == 4:
            return date_str.split('T')[0] if 'T' in date_str else date_str
        if len(date_str) >= 8 and date_str[:8].isdigit():
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return date_str
    except Exception:
        return str(date_str)


def create_qr_image(data: str, size: int = 18, fill_color="black"):
    """Create QR code image for PDF"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=2,
            border=1,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color=fill_color, back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return RLImage(buffer, width=size*mm, height=size*mm)
    except:
        return None


def create_barcode_image(code: str, width: int = 40, height: int = 10):
    """Create Code128 barcode for STAS signature"""
    try:
        barcode = code128.Code128(code, barWidth=0.35*mm, barHeight=height*mm)
        d = Drawing(width*mm, (height+3)*mm)
        d.add(barcode)
        return d
    except:
        return None


def create_logo_image(logo_data: str, max_width: int = 25, max_height: int = 15):
    """Create image from base64 logo data"""
    if not logo_data:
        return None
    try:
        if ',' in logo_data:
            logo_data = logo_data.split(',')[1]
        img_bytes = base64.b64decode(logo_data)
        buffer = io.BytesIO(img_bytes)
        return RLImage(buffer, width=max_width*mm, height=max_height*mm)
    except:
        return None


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
            'comments': 'التعليقات',
            'executed_by': 'تم التنفيذ بواسطة STAS',
            'transaction_id': 'رقم المعاملة',
            'leave_request': 'طلب إجازة',
            'finance_60': 'عهدة مالية',
            'tangible_custody': 'عهدة ملموسة',
            'settlement': 'تسوية',
            'contract': 'عقد',
            'salary_advance': 'سلفة راتب',
            'executed': 'منفذة',
            'rejected': 'مرفوضة',
            'cancelled': 'ملغاة',
            'stas': 'بانتظار التنفيذ',
            'pending_supervisor': 'بانتظار المشرف',
            'pending_ops': 'بانتظار العمليات',
            'pending_finance': 'بانتظار المالية',
            'pending_ceo': 'لدى سلطان',
            'pending_employee_accept': 'بانتظار الموظف',
            'returned': 'معادة',
            'supervisor': 'المشرف',
            'ops': 'العمليات',
            'finance': 'المالية',
            'ceo': 'CEO',
            'employee_accept': 'الموظف',
            'approve': 'موافقة',
            'approved': 'موافقة',
            'reject': 'رفض',
            'reject_action': 'مرفوض',
            'escalate': 'تصعيد',
            'escalated': 'تم التصعيد',
            'leave_type': 'نوع الإجازة',
            'start_date': 'من تاريخ',
            'end_date': 'إلى تاريخ',
            'working_days': 'أيام العمل',
            'reason': 'السبب',
            'amount': 'المبلغ',
            'description': 'الوصف',
            'itemname': 'اسم العنصر',
            'estimatedvalue': 'القيمة التقديرية',
            'annual': 'سنوية',
            'sick': 'مرضية',
            'emergency': 'طارئة',
            'employee_name': 'اسم الموظف',
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
            'comments': 'Comments',
            'executed_by': 'Executed by STAS',
            'transaction_id': 'Transaction ID',
            'leave_request': 'Leave Request',
            'finance_60': 'Financial Custody',
            'tangible_custody': 'Tangible Custody',
            'settlement': 'Settlement',
            'contract': 'Contract',
            'salary_advance': 'Salary Advance',
            'executed': 'Executed',
            'rejected': 'Rejected',
            'cancelled': 'Cancelled',
            'stas': 'STAS',
            'pending_supervisor': 'Pending Supervisor',
            'pending_ops': 'Pending Operations',
            'pending_finance': 'Pending Finance',
            'pending_ceo': 'Pending CEO',
            'pending_employee_accept': 'Pending Employee',
            'supervisor': 'Supervisor',
            'ops': 'Operations',
            'finance': 'Finance',
            'ceo': 'CEO',
            'employee_accept': 'Employee',
            'approve': 'Approved',
            'approved': 'Approved',
            'reject': 'Rejected',
            'reject_action': 'Rejected',
            'escalate': 'Escalated',
            'escalated': 'Escalated',
            'leave_type': 'Leave Type',
            'start_date': 'Start Date',
            'end_date': 'End Date',
            'working_days': 'Working Days',
            'reason': 'Reason',
            'amount': 'Amount',
            'description': 'Description',
            'itemname': 'Item Name',
            'estimatedvalue': 'Estimated Value',
            'annual': 'Annual',
            'sick': 'Sick',
            'emergency': 'Emergency',
            'employee_name': 'Employee Name',
        }


def make_para(text, style, force_ltr=False):
    """Create a Paragraph from text, reshaping Arabic if needed.
    
    Args:
        text: The text to display
        style: ParagraphStyle to use
        force_ltr: If True, use LTR style for this text
    """
    text_str = str(text)
    
    if has_arabic(text_str):
        # Arabic text needs reshaping
        text_str = reshape_arabic(text_str)
    
    return Paragraph(text_str, style)


def make_ltr_para(text, style):
    """Create a Paragraph for LTR text (numbers, dates, English).
    Uses Helvetica font to ensure proper LTR rendering."""
    # Create a copy of style with Helvetica font and no RTL
    ltr_style = ParagraphStyle(
        f'{style.name}_ltr',
        parent=style,
        fontName='Helvetica',
        wordWrap='LTR',
        alignment=TA_LEFT,
    )
    return Paragraph(str(text), ltr_style)


def generate_transaction_pdf(transaction: dict, employee: dict = None, lang: str = 'ar', branding: dict = None) -> tuple:
    """Generate professional single-page PDF with PROPER Arabic support using Paragraphs"""
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=12*mm,
        bottomMargin=10*mm,
        leftMargin=MARGIN,
        rightMargin=MARGIN
    )
    
    labels = get_labels(lang)
    
    if branding is None:
        branding = {
            "company_name_en": "DAR AL CODE ENGINEERING CONSULTANCY",
            "company_name_ar": "شركة دار الكود للاستشارات الهندسية",
            "slogan_en": "Engineering Excellence",
            "slogan_ar": "التميز الهندسي",
            "logo_data": None
        }
    
    # Font selection
    main_font = ARABIC_FONT if ARABIC_FONT else ENGLISH_FONT
    bold_font = ARABIC_FONT_BOLD if ARABIC_FONT_BOLD else ENGLISH_FONT_BOLD
    
    # ===== STYLES =====
    # Use different base styles for Arabic vs English
    if lang == 'ar':
        base_style = ParagraphStyle(
            'base',
            fontName=main_font,
            fontSize=8,
            alignment=TA_RIGHT,
            wordWrap='RTL',
            leading=12,
        )
    else:
        # English uses Helvetica with LTR
        base_style = ParagraphStyle(
            'base',
            fontName='Helvetica',
            fontSize=8,
            alignment=TA_LEFT,
            wordWrap='LTR',
            leading=12,
        )
    
    styles = {
        'title': ParagraphStyle('title', parent=base_style, fontSize=14, fontName='Helvetica-Bold' if lang == 'en' else bold_font, textColor=NAVY, alignment=TA_CENTER),
        'subtitle': ParagraphStyle('subtitle', parent=base_style, fontSize=11, fontName='Helvetica-Bold' if lang == 'en' else bold_font, textColor=NAVY, alignment=TA_CENTER, spaceAfter=4*mm),
        'section': ParagraphStyle('section', parent=base_style, fontSize=9, fontName='Helvetica-Bold' if lang == 'en' else bold_font, textColor=NAVY, spaceBefore=4*mm, spaceAfter=2*mm),
        'small': ParagraphStyle('small', parent=base_style, fontSize=6, textColor=TEXT_GRAY, alignment=TA_CENTER),
        'small_bold': ParagraphStyle('small_bold', parent=base_style, fontSize=7, fontName='Helvetica-Bold' if lang == 'en' else bold_font, textColor=TEXT_GRAY, alignment=TA_CENTER),
        'cell': ParagraphStyle('cell', parent=base_style, fontSize=7),
        'cell_label': ParagraphStyle('cell_label', parent=base_style, fontSize=7, textColor=TEXT_GRAY),
        'cell_center': ParagraphStyle('cell_center', parent=base_style, fontSize=6, alignment=TA_CENTER),
        'header_cell': ParagraphStyle('header_cell', parent=base_style, fontSize=6, fontName='Helvetica-Bold' if lang == 'en' else bold_font, textColor=colors.white, alignment=TA_CENTER),
    }
    
    elements = []
    integrity_id = str(uuid.uuid4())[:12].upper()
    ref_no = transaction.get('ref_no', 'N/A')
    
    # ============ HEADER ============
    company_name = branding.get('company_name_ar' if lang == 'ar' else 'company_name_en', labels['company'])
    slogan = branding.get('slogan_ar' if lang == 'ar' else 'slogan_en', labels['slogan'])
    logo_data = branding.get('logo_data')
    
    logo_img = create_logo_image(logo_data)
    if logo_img:
        header_data = [[logo_img, make_para(company_name, styles['title'])]]
        header_table = Table(header_data, colWidths=[30*mm, CONTENT_WIDTH - 35*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ]))
        elements.append(header_table)
    else:
        elements.append(make_para(company_name, styles['title']))
    
    if slogan:
        elements.append(make_para(slogan, styles['small']))
    
    # Line separator
    line_table = Table([['']], colWidths=[CONTENT_WIDTH], rowHeights=[1.5])
    line_table.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, 0), 2, NAVY)]))
    elements.append(line_table)
    elements.append(Spacer(1, 3*mm))
    
    # ============ DOCUMENT TYPE ============
    tx_type = transaction.get('type', '')
    type_label = labels.get(tx_type, tx_type.replace('_', ' ').title())
    elements.append(make_para(type_label, styles['subtitle']))
    
    # ============ INFO BOX ============
    status_raw = transaction.get('status', '')
    status_label = labels.get(status_raw, status_raw.replace('_', ' ').title())
    
    info_data = [
        [make_para(labels['ref_no'], styles['cell_label']), make_ltr_para(ref_no, styles['cell']), 
         make_para(labels['status'], styles['cell_label']), make_para(status_label, styles['cell'])],
        [make_para(labels['date'], styles['cell_label']), make_ltr_para(format_saudi_time(transaction.get('created_at')), styles['cell']), 
         make_para(labels['integrity_id'], styles['cell_label']), make_ltr_para(integrity_id, styles['cell'])],
    ]
    
    info_table = Table(info_data, colWidths=[28*mm, 60*mm, 28*mm, 54*mm], rowHeights=[8*mm, 8*mm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    
    # ============ EMPLOYEE INFO ============
    if employee:
        elements.append(make_para(labels['employee_info'], styles['section']))
        
        emp_name = employee.get('full_name_ar' if lang == 'ar' else 'full_name', employee.get('full_name', '-'))
        emp_no = str(employee.get('employee_number', '-'))
        
        emp_data = [[
            make_para(labels['name'], styles['cell_label']), 
            make_para(emp_name, styles['cell']), 
            make_para(labels['emp_no'], styles['cell_label']), 
            make_ltr_para(emp_no, styles['cell'])
        ]]
        emp_table = Table(emp_data, colWidths=[25*mm, 80*mm, 25*mm, 40*mm], rowHeights=[8*mm])
        emp_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(emp_table)
    
    # ============ TRANSACTION DETAILS ============
    elements.append(make_para(labels['details'], styles['section']))
    
    tx_data = transaction.get('data', {})
    skip_fields = {'employee_name_ar', 'balance_before', 'balance_after', 'adjusted_end_date', 'sick_tier_info', 'leave_type_ar', 'medical_file_url'}
    
    # Fields that should use LTR (dates, numbers)
    ltr_fields = {'start_date', 'end_date', 'date', 'working_days', 'amount', 'estimatedvalue', 'estimated_value'}
    
    details_rows = []
    for key, value in tx_data.items():
        if key in skip_fields:
            continue
        if key == 'employee_name' and lang == 'ar' and 'employee_name_ar' in tx_data:
            value = tx_data['employee_name_ar']
        if isinstance(value, (dict, list)):
            continue
        
        field_label = labels.get(key, key.replace('_', ' ').title())
        
        if value is None:
            formatted_val = '-'
            use_ltr = True
        elif key == 'leave_type':
            if lang == 'ar' and 'leave_type_ar' in tx_data:
                formatted_val = tx_data['leave_type_ar']
            else:
                formatted_val = labels.get(str(value), str(value))
            use_ltr = False
        elif key in ('amount', 'estimatedvalue', 'estimated_value'):
            formatted_val = f"{value} SAR"
            use_ltr = True
        elif key in ('start_date', 'end_date', 'date'):
            formatted_val = format_date_only(str(value))
            use_ltr = True
        elif key == 'working_days':
            formatted_val = str(value)
            use_ltr = True
        else:
            formatted_val = str(value)
            use_ltr = not has_arabic(formatted_val)
        
        # Use appropriate paragraph type
        if use_ltr:
            val_para = make_ltr_para(formatted_val, styles['cell'])
        else:
            val_para = make_para(formatted_val, styles['cell'])
        
        details_rows.append([make_para(field_label, styles['cell_label']), val_para])
    
    if details_rows:
        if len(details_rows) > 3:
            mid = (len(details_rows) + 1) // 2
            col1 = details_rows[:mid]
            col2 = details_rows[mid:]
            while len(col2) < len(col1):
                col2.append([make_para('', styles['cell']), make_para('', styles['cell'])])
            
            combined = []
            for i in range(len(col1)):
                row = [col1[i][0], col1[i][1], col2[i][0] if i < len(col2) else '', col2[i][1] if i < len(col2) else '']
                combined.append(row)
            
            details_table = Table(combined, colWidths=[28*mm, 55*mm, 28*mm, 55*mm], rowHeights=[7*mm] * len(combined))
        else:
            details_table = Table(details_rows, colWidths=[40*mm, 130*mm], rowHeights=[7*mm] * len(details_rows))
        
        details_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBELOW', (0, 0), (-1, -2), 0.3, BORDER_GRAY),
        ]))
        elements.append(details_table)
    
    # ============ APPROVAL CHAIN ============
    approval_chain = transaction.get('approval_chain', [])
    if approval_chain:
        elements.append(make_para(labels['approvals'], styles['section']))
        
        headers = [
            make_para(labels['stage'], styles['header_cell']),
            make_para(labels['approver'], styles['header_cell']),
            make_para(labels['action'], styles['header_cell']),
            make_para(labels['time'], styles['header_cell']),
            make_para(labels['signature'], styles['header_cell']),
        ]
        approval_data = [headers]
        
        for approval in approval_chain:
            stage = approval.get('stage', '')
            
            if stage in ('stas', 'ceo'):
                stage_display = stage.upper()
                stage_para = make_ltr_para(stage_display, styles['cell_center'])
            else:
                stage_display = labels.get(stage, stage.title())
                stage_para = make_para(stage_display, styles['cell_center'])
            
            approver_name = approval.get('approver_name', approval.get('actor_name', '-'))
            action_raw = approval.get('status', approval.get('action', ''))
            action_label = labels.get(action_raw, action_raw.title())
            timestamp = format_saudi_time(approval.get('timestamp'))
            
            # Signature: BARCODE for STAS, QR for others
            approver_id = approval.get('approver_id', '')[:8]
            if stage == 'stas':
                sig_code = f"STAS-{ref_no[-8:]}"
                barcode_drawing = create_barcode_image(sig_code, width=35, height=8)
                if barcode_drawing:
                    ref_text = make_ltr_para(ref_no, styles['cell_center'])
                    sig_table = Table([[barcode_drawing], [ref_text]], colWidths=[40*mm], rowHeights=[10*mm, 4*mm])
                    sig_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ]))
                    sig_img = sig_table
                else:
                    sig_img = make_ltr_para(f"[STAS-{ref_no[-8:]}]", styles['cell_center'])
            else:
                sig_data = f"{stage}-{approver_id}"
                sig_img = create_qr_image(sig_data, size=12)
                if sig_img is None:
                    sig_img = make_ltr_para(f"[{approver_id[:6]}]", styles['cell_center'])
            
            approval_data.append([
                stage_para,
                make_para(approver_name, styles['cell_center']),
                make_para(action_label, styles['cell_center']),
                make_ltr_para(timestamp, styles['cell_center']),
                sig_img
            ])
        
        row_heights = [7*mm] + [14*mm] * (len(approval_data) - 1)
        
        approval_table = Table(
            approval_data,
            colWidths=[28*mm, 40*mm, 25*mm, 35*mm, 42*mm],
            rowHeights=row_heights
        )
        approval_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
            ('LINEBELOW', (0, 0), (-1, -1), 0.3, BORDER_GRAY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(approval_table)
    
    # ============ EMPLOYEE DEDUCTION CONSENT (Blue QR for sick leave > 30 days) ============
    tx_data = transaction.get('data', {})
    if transaction.get('type') == 'leave_request' and tx_data.get('leave_type') == 'sick':
        sick_tier_info = tx_data.get('sick_tier_info', {})
        tier_distribution = sick_tier_info.get('distribution', []) if isinstance(sick_tier_info, dict) else []
        
        has_deduction = False
        deduction_details = []
        for tier in tier_distribution:
            if isinstance(tier, dict) and tier.get('salary_percent', 100) < 100:
                has_deduction = True
                days = tier.get('days', 0)
                percent = tier.get('salary_percent', 0)
                deduction_percent = 100 - percent
                deduction_details.append(f"{days} {'يوم' if lang == 'ar' else 'days'} @ {deduction_percent}% {'خصم' if lang == 'ar' else 'deduction'}")
        
        if has_deduction:
            elements.append(Spacer(1, 5*mm))
            
            consent_title = "موافقة الموظف على الخصم - المادة 117" if lang == 'ar' else "Employee Deduction Consent - Article 117"
            consent_style = ParagraphStyle('consent_title', parent=base_ar_style, fontSize=9, fontName=bold_font, textColor=colors.HexColor('#2196F3'))
            elements.append(make_para(consent_title, consent_style))
            
            emp_first_name = ""
            if employee:
                full_name = employee.get('full_name_ar' if lang == 'ar' else 'full_name', '')
                emp_first_name = full_name.split()[0] if full_name else ""
            
            if lang == 'ar':
                consent_text = f"بتوقيعي أدناه، أوافق على تطبيق الخصم: {' | '.join(deduction_details)}"
            else:
                consent_text = f"By signing below, I agree to the deduction: {' | '.join(deduction_details)}"
            
            consent_text_style = ParagraphStyle('consent_text', parent=base_ar_style, fontSize=7)
            elements.append(make_para(consent_text, consent_text_style))
            
            # Blue QR code for employee signature
            emp_id = employee.get('id', 'unknown')[:8] if employee else 'unknown'
            consent_code = f"CONSENT-{emp_id}-{ref_no[-6:]}"
            consent_qr = create_qr_image(consent_code, size=15, fill_color="#2196F3")
            
            if consent_qr:
                sig_label = "توقيع الموظف" if lang == 'ar' else "Employee Signature"
                consent_table_data = [
                    [make_para(sig_label, styles['small_bold'])],
                    [consent_qr],
                    [make_para(consent_code, styles['small'])]
                ]
                consent_table = Table(consent_table_data, colWidths=[45*mm], rowHeights=[5*mm, 18*mm, 4*mm])
                consent_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#2196F3')),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E3F2FD')),
                ]))
                
                outer_consent = Table([[consent_table]], colWidths=[CONTENT_WIDTH])
                outer_consent.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
                elements.append(outer_consent)
    
    # ============ EXECUTION STAMP (STAS BARCODE) ============
    if transaction.get('status') == 'executed':
        elements.append(Spacer(1, 4*mm))
        
        executed_label = labels['executed_by']
        stamp_date = format_saudi_time(transaction.get('executed_at') or transaction.get('updated_at'))
        
        exec_code = f"EXEC-{ref_no.replace('TXN-', '')}"
        barcode_img = create_barcode_image(exec_code, width=55, height=14)
        
        stamp_elements = [
            [make_para(executed_label, styles['section'])],
        ]
        stamp_heights = [6*mm]
        
        if barcode_img:
            stamp_elements.append([barcode_img])
            stamp_heights.append(20*mm)
        
        # Use LTR for ref number
        ref_style = ParagraphStyle('ref_bold', fontName='Helvetica-Bold', fontSize=9, alignment=TA_CENTER, textColor=NAVY)
        stamp_elements.append([Paragraph(f"Ref No: {ref_no}", ref_style)])
        stamp_heights.append(6*mm)
        
        # Use LTR for date
        stamp_elements.append([make_ltr_para(stamp_date, styles['small'])])
        stamp_heights.append(4*mm)
        
        stamp_table = Table(stamp_elements, colWidths=[65*mm], rowHeights=stamp_heights)
        stamp_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1.5, NAVY),
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ]))
        
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
    elements.append(make_ltr_para(footer_text, styles['small']))
    
    # Build PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    return pdf_bytes, pdf_hash, integrity_id
