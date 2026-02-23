"""
Professional PDF Generator - مولد PDF الاحترافي
============================================================
تصميم احترافي موحد لجميع مستندات الشركة
مع محاذاة صحيحة وتناسق كامل
============================================================
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image as RLImage, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, String, Line
import arabic_reshaper
from bidi.algorithm import get_display
import qrcode
import hashlib
import uuid
import io
import os
import base64
from datetime import datetime, timezone, timedelta

# ==================== PAGE SETUP ====================
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 15 * mm
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)

# ==================== COLORS ====================
NAVY = colors.Color(0.118, 0.227, 0.373)       # #1E3A5F
GOLD = colors.Color(0.75, 0.62, 0.35)          # ذهبي
LIGHT_BLUE = colors.Color(0.93, 0.96, 0.99)    # أزرق فاتح للخلفية
LIGHT_GRAY = colors.Color(0.95, 0.95, 0.96)    # رمادي فاتح
BORDER_COLOR = colors.Color(0.8, 0.82, 0.85)   # لون الحدود
TEXT_DARK = colors.Color(0.2, 0.2, 0.25)       # نص داكن
TEXT_GRAY = colors.Color(0.5, 0.5, 0.55)       # نص رمادي
SUCCESS_GREEN = colors.Color(0.13, 0.55, 0.33) # أخضر
WHITE = colors.white

# ==================== FONTS ====================
FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')
ARABIC_FONT = 'NotoNaskhArabic'
ARABIC_FONT_BOLD = 'NotoNaskhArabicBold'
ENGLISH_FONT = 'Helvetica'
ENGLISH_FONT_BOLD = 'Helvetica-Bold'


def register_fonts():
    """تسجيل الخطوط العربية"""
    global ARABIC_FONT, ARABIC_FONT_BOLD
    font_pairs = [
        ('NotoNaskhArabic', 'NotoNaskhArabic-Regular.ttf', 'NotoNaskhArabic-Bold.ttf'),
        ('NotoSansArabic', 'NotoSansArabic-Regular.ttf', 'NotoSansArabic-Bold.ttf'),
    ]
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
                ARABIC_FONT = font_name
                ARABIC_FONT_BOLD = f'{font_name}Bold'
                return True
        except Exception:
            continue
    return False


_fonts_registered = register_fonts()


def reshape_arabic(text):
    """تحويل النص العربي للعرض الصحيح RTL"""
    if not text:
        return ''
    try:
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except Exception:
        return str(text)


def format_date(ts):
    """تنسيق التاريخ"""
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
        return str(ts)[:16] if ts else '-'


def create_qr_image(data: str, size: int = 25):
    """إنشاء صورة QR Code"""
    try:
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=4, border=1)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return RLImage(buffer, width=size*mm, height=size*mm)
    except Exception:
        return None


def create_logo_placeholder():
    """إنشاء شعار نصي بديل"""
    d = Drawing(25*mm, 25*mm)
    d.add(Rect(0, 0, 25*mm, 25*mm, fillColor=NAVY, strokeColor=None, rx=3, ry=3))
    d.add(String(3*mm, 10*mm, "DAC", fontName=ENGLISH_FONT_BOLD, fontSize=14, fillColor=WHITE))
    return d


# ==================== MAIN PDF GENERATOR ====================
def generate_professional_transaction_pdf(transaction: dict, employee: dict = None, branding: dict = None) -> tuple:
    """
    توليد PDF احترافي للمعاملات
    Returns: (pdf_bytes, pdf_hash, integrity_id)
    """
    register_fonts()
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=MARGIN, bottomMargin=MARGIN, leftMargin=MARGIN, rightMargin=MARGIN)
    
    elements = []
    
    # Extract data
    ref_no = transaction.get('ref_no', 'TXN-0000')
    tx_type = transaction.get('type', 'unknown')
    status = transaction.get('status', 'pending')
    created_at = transaction.get('created_at', '')
    tx_data = transaction.get('data', {})
    
    # Generate integrity ID
    content_hash = hashlib.sha256(f"{ref_no}{transaction.get('id', '')}".encode()).hexdigest()[:8]
    integrity_id = f"DAR-{ref_no.replace('TXN-', '').replace('-', '')}-{content_hash}".upper()
    
    # Company info
    company_ar = branding.get('company_name_ar', 'شركة دار الكود للاستشارات الهندسية') if branding else 'شركة دار الكود للاستشارات الهندسية'
    company_en = branding.get('company_name_en', 'DAR AL CODE Engineering Consultancy') if branding else 'DAR AL CODE Engineering Consultancy'
    
    # Employee info
    emp_name_ar = ''
    emp_name_en = ''
    emp_no = ''
    if employee:
        emp_name_ar = employee.get('full_name_ar', employee.get('full_name', ''))
        emp_name_en = employee.get('full_name', '')
        emp_no = employee.get('employee_number', '')
    if tx_data:
        if not emp_name_ar:
            emp_name_ar = tx_data.get('employee_name_ar', tx_data.get('employee_name', ''))
        if not emp_name_en:
            emp_name_en = tx_data.get('employee_name', '')
    
    # ==================== 1. HEADER ====================
    # Simple centered header
    header_style_ar = ParagraphStyle('header_ar', fontName=ARABIC_FONT_BOLD, fontSize=14, alignment=TA_CENTER, textColor=NAVY, leading=18)
    header_style_en = ParagraphStyle('header_en', fontName=ENGLISH_FONT_BOLD, fontSize=11, alignment=TA_CENTER, textColor=NAVY, leading=14)
    header_style_small = ParagraphStyle('header_small', fontName=ENGLISH_FONT, fontSize=8, alignment=TA_CENTER, textColor=TEXT_GRAY)
    
    elements.append(Paragraph(reshape_arabic(company_ar), header_style_ar))
    elements.append(Paragraph(company_en, header_style_en))
    elements.append(Paragraph("Kingdom of Saudi Arabia | License: 5110004935 | CR: 1010463476", header_style_small))
    elements.append(Spacer(1, 3*mm))
    
    # Divider line
    elements.append(HRFlowable(width="100%", thickness=2, color=NAVY, spaceBefore=2, spaceAfter=5))
    
    # ==================== 2. DOCUMENT TITLE ====================
    doc_titles = {
        'leave_request': ('طلب إجازة', 'Leave Request'),
        'tangible_custody': ('سند عهدة عينية', 'In-Kind Custody'),
        'finance_60': ('عهدة مالية', 'Financial Custody'),
        'settlement': ('مخالصة نهائية', 'Final Settlement'),
        'salary_advance': ('سلفة راتب', 'Salary Advance'),
    }
    title_ar, title_en = doc_titles.get(tx_type, (tx_type, tx_type))
    
    title_style_ar = ParagraphStyle('title_ar', fontName=ARABIC_FONT_BOLD, fontSize=16, alignment=TA_CENTER, textColor=NAVY, spaceAfter=2)
    title_style_en = ParagraphStyle('title_en', fontName=ENGLISH_FONT_BOLD, fontSize=12, alignment=TA_CENTER, textColor=TEXT_GRAY, spaceAfter=2)
    ref_style = ParagraphStyle('ref', fontName=ENGLISH_FONT_BOLD, fontSize=10, alignment=TA_CENTER, textColor=GOLD)
    
    elements.append(Paragraph(reshape_arabic(title_ar), title_style_ar))
    elements.append(Paragraph(title_en, title_style_en))
    elements.append(Paragraph(f"Ref: {ref_no}", ref_style))
    elements.append(Spacer(1, 5*mm))
    
    # ==================== 3. INFO TABLE ====================
    # Create a clean 4-column table: Value EN | Label EN | Label AR | Value AR
    
    label_style = ParagraphStyle('label', fontName=ENGLISH_FONT, fontSize=9, alignment=TA_CENTER, textColor=TEXT_GRAY)
    label_style_ar = ParagraphStyle('label_ar', fontName=ARABIC_FONT, fontSize=9, alignment=TA_CENTER, textColor=TEXT_GRAY)
    value_style = ParagraphStyle('value', fontName=ENGLISH_FONT_BOLD, fontSize=10, alignment=TA_CENTER, textColor=TEXT_DARK)
    value_style_ar = ParagraphStyle('value_ar', fontName=ARABIC_FONT_BOLD, fontSize=10, alignment=TA_CENTER, textColor=TEXT_DARK)
    
    # Status translation
    status_map = {
        'executed': ('منفذة', 'Executed'),
        'pending': ('معلقة', 'Pending'),
        'pending_ops': ('بانتظار العمليات', 'Pending Ops'),
        'pending_stas': ('بانتظار STAS', 'Pending STAS'),
        'pending_ceo': ('بانتظار CEO', 'Pending CEO'),
        'stas': ('بانتظار STAS', 'Pending STAS'),
        'ceo': ('بانتظار CEO', 'Pending CEO'),
        'ops': ('بانتظار العمليات', 'Pending Ops'),
        'rejected': ('مرفوضة', 'Rejected'),
        'cancelled': ('ملغاة', 'Cancelled'),
    }
    status_ar, status_en = status_map.get(status, (status, status))
    
    # Build info rows
    info_data = [
        # Header row
        [
            Paragraph("Value", label_style),
            Paragraph("Field", label_style),
            Paragraph(reshape_arabic("الحقل"), label_style_ar),
            Paragraph(reshape_arabic("القيمة"), label_style_ar),
        ],
        # Reference
        [
            Paragraph(ref_no, value_style),
            Paragraph("Reference", label_style),
            Paragraph(reshape_arabic("رقم المرجع"), label_style_ar),
            Paragraph(reshape_arabic(ref_no), value_style_ar),
        ],
        # Status
        [
            Paragraph(status_en, value_style),
            Paragraph("Status", label_style),
            Paragraph(reshape_arabic("الحالة"), label_style_ar),
            Paragraph(reshape_arabic(status_ar), value_style_ar),
        ],
        # Date
        [
            Paragraph(format_date(created_at), value_style),
            Paragraph("Date", label_style),
            Paragraph(reshape_arabic("التاريخ"), label_style_ar),
            Paragraph(reshape_arabic(format_date(created_at)), value_style_ar),
        ],
        # Integrity ID
        [
            Paragraph(integrity_id, value_style),
            Paragraph("Integrity ID", label_style),
            Paragraph(reshape_arabic("معرف السلامة"), label_style_ar),
            Paragraph(reshape_arabic(integrity_id), value_style_ar),
        ],
    ]
    
    # Add employee info
    if emp_name_en or emp_name_ar:
        info_data.append([
            Paragraph(emp_name_en, value_style),
            Paragraph("Employee", label_style),
            Paragraph(reshape_arabic("الموظف"), label_style_ar),
            Paragraph(reshape_arabic(emp_name_ar), value_style_ar),
        ])
    
    if emp_no:
        info_data.append([
            Paragraph(emp_no, value_style),
            Paragraph("Employee No", label_style),
            Paragraph(reshape_arabic("الرقم الوظيفي"), label_style_ar),
            Paragraph(reshape_arabic(emp_no), value_style_ar),
        ])
    
    col_w = CONTENT_WIDTH / 4
    info_table = Table(info_data, colWidths=[col_w, col_w, col_w, col_w])
    info_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        # Grid
        ('BOX', (0, 0), (-1, -1), 1, NAVY),
        ('LINEBELOW', (0, 0), (-1, 0), 1, NAVY),
        ('INNERGRID', (0, 1), (-1, -1), 0.5, BORDER_COLOR),
        # Alignment
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        # Alternating colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 5*mm))
    
    # ==================== 4. DETAILS TABLE ====================
    # Transaction specific details
    detail_rows = []
    
    if tx_type == 'leave_request':
        leave_type = tx_data.get('leave_type', '')
        leave_map = {'annual': ('سنوية', 'Annual'), 'sick': ('مرضية', 'Sick'), 'emergency': ('طارئة', 'Emergency')}
        lt_ar, lt_en = leave_map.get(leave_type, (leave_type, leave_type))
        
        detail_rows = [
            (lt_en, 'Leave Type', 'نوع الإجازة', lt_ar),
            (tx_data.get('start_date', '-'), 'Start Date', 'من تاريخ', tx_data.get('start_date', '-')),
            (tx_data.get('end_date', '-'), 'End Date', 'إلى تاريخ', tx_data.get('end_date', '-')),
            (str(tx_data.get('working_days', '-')), 'Working Days', 'أيام العمل', str(tx_data.get('working_days', '-'))),
        ]
    elif tx_type in ('tangible_custody', 'tangible_custody_return'):
        detail_rows = [
            (tx_data.get('item_name', '-'), 'Item Name', 'اسم العنصر', tx_data.get('item_name_ar', tx_data.get('item_name', '-'))),
            (tx_data.get('serial_number', '-'), 'Serial No', 'الرقم التسلسلي', tx_data.get('serial_number', '-')),
            (f"{tx_data.get('estimated_value', 0):,.2f} SAR", 'Value', 'القيمة', f"{tx_data.get('estimated_value', 0):,.2f} ريال"),
        ]
    elif tx_type == 'salary_advance':
        detail_rows = [
            (f"{tx_data.get('amount', 0):,.2f} SAR", 'Amount', 'المبلغ', f"{tx_data.get('amount', 0):,.2f} ريال"),
            (tx_data.get('reason', '-'), 'Reason', 'السبب', tx_data.get('reason', '-')),
        ]
    
    if detail_rows:
        # Section title
        section_title = ParagraphStyle('section', fontName=ARABIC_FONT_BOLD, fontSize=11, alignment=TA_CENTER, textColor=NAVY, spaceBefore=5, spaceAfter=3)
        elements.append(Paragraph(reshape_arabic("تفاصيل المعاملة | Transaction Details"), section_title))
        
        detail_data = [[
            Paragraph("Value", label_style),
            Paragraph("Field", label_style),
            Paragraph(reshape_arabic("الحقل"), label_style_ar),
            Paragraph(reshape_arabic("القيمة"), label_style_ar),
        ]]
        
        for row in detail_rows:
            detail_data.append([
                Paragraph(str(row[0]), value_style),
                Paragraph(row[1], label_style),
                Paragraph(reshape_arabic(row[2]), label_style_ar),
                Paragraph(reshape_arabic(str(row[3])), value_style_ar),
            ])
        
        detail_table = Table(detail_data, colWidths=[col_w, col_w, col_w, col_w])
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), GOLD),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('BOX', (0, 0), (-1, -1), 1, GOLD),
            ('LINEBELOW', (0, 0), (-1, 0), 1, GOLD),
            ('INNERGRID', (0, 1), (-1, -1), 0.5, BORDER_COLOR),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ]))
        elements.append(detail_table)
    
    elements.append(Spacer(1, 8*mm))
    
    # ==================== 5. SIGNATURES TABLE ====================
    section_title = ParagraphStyle('section', fontName=ARABIC_FONT_BOLD, fontSize=11, alignment=TA_CENTER, textColor=NAVY, spaceBefore=5, spaceAfter=3)
    elements.append(Paragraph(reshape_arabic("التوقيعات | Signatures"), section_title))
    
    # Build signatures
    signatures = []
    
    # Employee signature
    signatures.append({
        'role_ar': 'الموظف',
        'role_en': 'Employee',
        'name_ar': emp_name_ar,
        'name_en': emp_name_en,
        'signed': True,
        'timestamp': created_at,
    })
    
    # Add from approval chain
    approval_chain = transaction.get('approval_chain', [])
    added_roles = set(['Employee'])  # Employee already added
    
    for approval in approval_chain:
        stage = approval.get('stage', '')
        if stage == 'ceo' and 'CEO' not in added_roles:
            signatures.append({
                'role_ar': 'الرئيس التنفيذي',
                'role_en': 'CEO',
                'name_ar': 'محمد',
                'name_en': 'Mohammed',
                'signed': True,
                'timestamp': approval.get('timestamp', ''),
            })
            added_roles.add('CEO')
        elif stage in ('hr', 'sultan') and 'HR' not in added_roles:
            signatures.append({
                'role_ar': 'الموارد البشرية',
                'role_en': 'HR',
                'name_ar': 'سلطان',
                'name_en': 'Sultan',
                'signed': True,
                'timestamp': approval.get('timestamp', ''),
            })
            added_roles.add('HR')
        elif stage == 'stas' and 'STAS' not in added_roles:
            signatures.append({
                'role_ar': 'STAS',
                'role_en': 'STAS',
                'name_ar': 'STAS',
                'name_en': 'STAS',
                'signed': True,
                'timestamp': approval.get('timestamp', ''),
            })
            added_roles.add('STAS')
    
    # Add STAS if executed but not in chain
    if status == 'executed' and 'STAS' not in added_roles:
            signatures.append({
                'role_ar': 'STAS',
                'role_en': 'STAS',
                'name_ar': 'STAS',
                'name_en': 'STAS',
                'signed': True,
                'timestamp': transaction.get('executed_at', transaction.get('updated_at', '')),
            })
    
    # Create signature table
    sig_role_style = ParagraphStyle('sig_role', fontName=ARABIC_FONT_BOLD, fontSize=10, alignment=TA_CENTER, textColor=NAVY)
    sig_role_en_style = ParagraphStyle('sig_role_en', fontName=ENGLISH_FONT, fontSize=8, alignment=TA_CENTER, textColor=TEXT_GRAY)
    sig_name_style = ParagraphStyle('sig_name', fontName=ARABIC_FONT_BOLD, fontSize=9, alignment=TA_CENTER, textColor=TEXT_DARK)
    sig_name_en_style = ParagraphStyle('sig_name_en', fontName=ENGLISH_FONT, fontSize=8, alignment=TA_CENTER, textColor=TEXT_GRAY)
    sig_date_style = ParagraphStyle('sig_date', fontName=ENGLISH_FONT, fontSize=8, alignment=TA_CENTER, textColor=TEXT_GRAY)
    sig_status_style = ParagraphStyle('sig_status', fontName=ARABIC_FONT_BOLD, fontSize=8, alignment=TA_CENTER, textColor=SUCCESS_GREEN)
    
    # Build horizontal signature boxes
    sig_boxes = []
    for sig in signatures:
        # QR
        qr_data = f"SIG-{sig['role_en'].upper()}-{ref_no}"
        qr_img = create_qr_image(qr_data, size=20) if sig['signed'] else Paragraph("—", sig_date_style)
        
        # Content
        box_content = [
            [Paragraph(reshape_arabic(sig['role_ar']), sig_role_style)],
            [Paragraph(sig['role_en'], sig_role_en_style)],
            [Spacer(1, 2*mm)],
            [qr_img],
            [Spacer(1, 2*mm)],
            [Paragraph(reshape_arabic(sig['name_ar']), sig_name_style)],
            [Paragraph(sig['name_en'], sig_name_en_style)],
            [Spacer(1, 1*mm)],
            [Paragraph(format_date(sig['timestamp']) if sig['signed'] else "____/____/____", sig_date_style)],
            [Paragraph(reshape_arabic("✓ تم التوقيع") if sig['signed'] else "", sig_status_style)],
        ]
        
        box_table = Table(box_content, colWidths=[45*mm])
        box_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BLUE),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        sig_boxes.append(box_table)
    
    # Arrange horizontally
    if sig_boxes:
        num_sigs = len(sig_boxes)
        sig_col_w = CONTENT_WIDTH / num_sigs
        sig_row = Table([sig_boxes], colWidths=[sig_col_w] * num_sigs)
        sig_row.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(sig_row)
    
    elements.append(Spacer(1, 10*mm))
    
    # ==================== 6. TEAR-OFF LINE ====================
    tear_style = ParagraphStyle('tear', fontName=ENGLISH_FONT, fontSize=9, alignment=TA_CENTER, textColor=TEXT_GRAY)
    elements.append(HRFlowable(width="100%", thickness=1, color=BORDER_COLOR, spaceBefore=2, spaceAfter=0, dash=(3, 3)))
    elements.append(Paragraph("✂  Cut Here  |  قص هنا  ✂", tear_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=BORDER_COLOR, spaceBefore=0, spaceAfter=5, dash=(3, 3)))
    
    # ==================== 7. COUPON ====================
    coupon_title_ar = ParagraphStyle('coupon_ar', fontName=ARABIC_FONT_BOLD, fontSize=11, alignment=TA_CENTER, textColor=NAVY)
    coupon_title_en = ParagraphStyle('coupon_en', fontName=ENGLISH_FONT_BOLD, fontSize=9, alignment=TA_CENTER, textColor=NAVY)
    coupon_text = ParagraphStyle('coupon_text', fontName=ENGLISH_FONT, fontSize=8, alignment=TA_CENTER, textColor=TEXT_DARK)
    coupon_text_ar = ParagraphStyle('coupon_text_ar', fontName=ARABIC_FONT, fontSize=9, alignment=TA_CENTER, textColor=TEXT_DARK)
    coupon_status = ParagraphStyle('coupon_status', fontName=ARABIC_FONT_BOLD, fontSize=9, alignment=TA_CENTER, textColor=SUCCESS_GREEN if status == 'executed' else TEXT_GRAY)
    
    # Left QR (STAS)
    stas_qr = create_qr_image(f"STAS-{ref_no}", size=25) if status == 'executed' else Paragraph("Pending", coupon_text)
    left_content = [[stas_qr], [Paragraph("STAS QR", coupon_text)]]
    left_table = Table(left_content, colWidths=[35*mm])
    left_table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    
    # Center info
    center_content = [
        [Paragraph(reshape_arabic(company_ar), coupon_title_ar)],
        [Paragraph(company_en, coupon_title_en)],
        [Spacer(1, 3*mm)],
        [Paragraph(reshape_arabic(title_ar), coupon_text_ar)],
        [Paragraph(title_en, coupon_text)],
        [Paragraph(f"Ref: {ref_no}", coupon_text)],
        [Spacer(1, 2*mm)],
        [Paragraph(reshape_arabic(emp_name_ar), coupon_text_ar)],
        [Paragraph(emp_name_en, coupon_text)],
        [Spacer(1, 2*mm)],
        [Paragraph(reshape_arabic("✓ معاملة صحيحة" if status == 'executed' else "بانتظار التنفيذ"), coupon_status)],
    ]
    center_table = Table(center_content, colWidths=[90*mm])
    center_table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    
    # Right QR (Verify)
    verify_qr = create_qr_image(f"VERIFY-{ref_no}", size=25)
    right_content = [[verify_qr], [Paragraph("Verify QR", coupon_text)]]
    right_table = Table(right_content, colWidths=[35*mm])
    right_table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    
    # Coupon table
    coupon_table = Table([[left_table, center_table, right_table]], colWidths=[40*mm, CONTENT_WIDTH - 80*mm, 40*mm])
    coupon_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1.5, NAVY),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BLUE),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(coupon_table)
    
    elements.append(Spacer(1, 3*mm))
    
    # ==================== 8. FOOTER ====================
    footer_style = ParagraphStyle('footer', fontName=ENGLISH_FONT, fontSize=7, alignment=TA_CENTER, textColor=TEXT_GRAY)
    now = datetime.now(timezone.utc) + timedelta(hours=3)
    elements.append(Paragraph(f"DAR AL CODE HR OS | {integrity_id} | Generated: {now.strftime('%Y-%m-%d %H:%M')} KSA", footer_style))
    
    # Build PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    return pdf_bytes, pdf_hash, integrity_id


# Export functions for use by other modules
def create_unified_header(branding=None):
    """للتوافق مع الملفات الأخرى"""
    pass

def create_tear_off_line():
    """للتوافق مع الملفات الأخرى"""
    pass

def create_signatures_table(signatures, ref_no):
    """للتوافق مع الملفات الأخرى"""
    pass

def create_tear_off_coupon(*args, **kwargs):
    """للتوافق مع الملفات الأخرى"""
    pass

def create_document_title(*args, **kwargs):
    """للتوافق مع الملفات الأخرى"""
    pass

def create_bilingual_row(*args, **kwargs):
    """للتوافق مع الملفات الأخرى"""
    pass

def create_footer(*args, **kwargs):
    """للتوافق مع الملفات الأخرى"""
    pass

def format_saudi_time(ts):
    """للتوافق - نفس format_date"""
    return format_date(ts)

def create_qr_image_export(data, size=25):
    """للتوافق"""
    return create_qr_image(data, size)
