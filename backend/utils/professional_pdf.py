"""
Professional PDF Generator - مولد PDF الاحترافي
صفحة واحدة A4 - تصميم احترافي موحد
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image as RLImage
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, String
import arabic_reshaper
from bidi.algorithm import get_display
import qrcode
import hashlib
import io
import os
from datetime import datetime, timezone, timedelta

# ==================== PAGE SETUP ====================
PAGE_WIDTH, PAGE_HEIGHT = A4  # 210mm x 297mm
MARGIN = 10 * mm
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)

# ==================== COMPANY COLORS ====================
NAVY = colors.Color(0.118, 0.227, 0.373)       # #1E3A5F
GOLD = colors.Color(0.753, 0.620, 0.349)       # #C09E59
WHITE = colors.white
LIGHT_BG = colors.Color(0.96, 0.96, 0.97)      # #F5F5F7
BORDER = colors.Color(0.85, 0.85, 0.87)
TEXT_DARK = colors.Color(0.15, 0.15, 0.18)
TEXT_GRAY = colors.Color(0.45, 0.45, 0.50)
GREEN = colors.Color(0.13, 0.55, 0.33)

# ==================== FONTS ====================
FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')
AR_FONT = 'NotoNaskhArabic'
AR_BOLD = 'NotoNaskhArabicBold'
EN_FONT = 'Helvetica'
EN_BOLD = 'Helvetica-Bold'


def _register_fonts():
    global AR_FONT, AR_BOLD
    for name, reg, bold in [('NotoNaskhArabic', 'NotoNaskhArabic-Regular.ttf', 'NotoNaskhArabic-Bold.ttf')]:
        try:
            reg_path = os.path.join(FONTS_DIR, reg)
            bold_path = os.path.join(FONTS_DIR, bold)
            if os.path.exists(reg_path):
                pdfmetrics.registerFont(TTFont(name, reg_path))
                AR_FONT = name
                if os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont(f'{name}Bold', bold_path))
                    AR_BOLD = f'{name}Bold'
                return
        except:
            pass

_register_fonts()


def _ar(text):
    """تحويل النص العربي"""
    if not text:
        return ''
    try:
        return get_display(arabic_reshaper.reshape(str(text)))
    except:
        return str(text)


def _date(ts):
    """تنسيق التاريخ: 2026.02.23 | 14:00"""
    if not ts:
        return '-'
    try:
        if isinstance(ts, str):
            ts = ts.replace('Z', '+00:00')
            dt = datetime.fromisoformat(ts) if 'T' in ts else datetime.strptime(ts[:19], '%Y-%m-%d %H:%M:%S')
        else:
            dt = ts
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt + timedelta(hours=3)  # Saudi time
        return dt.strftime('%Y.%m.%d | %H:%M')
    except:
        return str(ts)[:16]


def _qr(data, size=18):
    """إنشاء QR Code"""
    try:
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=3, border=1)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return RLImage(buf, width=size*mm, height=size*mm)
    except:
        return None


def _logo():
    """شعار الشركة"""
    d = Drawing(20*mm, 20*mm)
    d.add(Rect(0, 0, 20*mm, 20*mm, fillColor=NAVY, strokeColor=None, rx=2, ry=2))
    d.add(String(3*mm, 7*mm, "DAC", fontName=EN_BOLD, fontSize=11, fillColor=WHITE))
    return d


def generate_professional_transaction_pdf(transaction: dict, employee: dict = None, branding: dict = None) -> tuple:
    """
    توليد PDF احترافي - صفحة واحدة A4
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=MARGIN, bottomMargin=MARGIN, leftMargin=MARGIN, rightMargin=MARGIN)
    
    elements = []
    
    # Extract data
    ref = transaction.get('ref_no', 'TXN-0000')
    tx_type = transaction.get('type', 'unknown')
    status = transaction.get('status', 'pending')
    created = transaction.get('created_at', '')
    data = transaction.get('data', {})
    chain = transaction.get('approval_chain', [])
    
    # Integrity ID
    h = hashlib.sha256(f"{ref}{transaction.get('id', '')}".encode()).hexdigest()[:8]
    integrity = f"DAR-{ref.replace('TXN-', '').replace('-', '')}-{h}".upper()
    
    # Company
    co_ar = branding.get('company_name_ar', 'شركة دار الكود للاستشارات الهندسية') if branding else 'شركة دار الكود للاستشارات الهندسية'
    co_en = branding.get('company_name_en', 'DAR AL CODE Engineering Consultancy') if branding else 'DAR AL CODE Engineering Consultancy'
    
    # Employee
    emp_ar = data.get('employee_name_ar', employee.get('full_name_ar', '') if employee else '')
    emp_en = data.get('employee_name', employee.get('full_name', '') if employee else '')
    emp_no = employee.get('employee_number', '') if employee else ''
    
    # Type labels
    types = {
        'leave_request': ('طلب إجازة', 'Leave Request'),
        'tangible_custody': ('عهدة عينية', 'In-Kind Custody'),
        'finance_60': ('عهدة مالية', 'Financial Custody'),
        'settlement': ('مخالصة نهائية', 'Final Settlement'),
        'salary_advance': ('سلفة راتب', 'Salary Advance'),
    }
    type_ar, type_en = types.get(tx_type, (tx_type, tx_type))
    
    # Status labels
    statuses = {
        'executed': ('منفذة', 'Executed', GREEN),
        'pending': ('معلقة', 'Pending', TEXT_GRAY),
        'stas': ('بانتظار STAS', 'Pending STAS', GOLD),
        'ceo': ('بانتظار CEO', 'Pending CEO', GOLD),
        'rejected': ('مرفوضة', 'Rejected', colors.red),
    }
    st_ar, st_en, st_color = statuses.get(status, (status, status, TEXT_GRAY))
    
    # ══════════════════════════════════════════════════════════════
    # STYLES
    # ══════════════════════════════════════════════════════════════
    s_co_ar = ParagraphStyle('co_ar', fontName=AR_BOLD, fontSize=12, alignment=TA_CENTER, textColor=NAVY, leading=15)
    s_co_en = ParagraphStyle('co_en', fontName=EN_BOLD, fontSize=10, alignment=TA_CENTER, textColor=NAVY)
    s_co_sm = ParagraphStyle('co_sm', fontName=EN_FONT, fontSize=7, alignment=TA_CENTER, textColor=TEXT_GRAY)
    s_title_ar = ParagraphStyle('t_ar', fontName=AR_BOLD, fontSize=13, alignment=TA_CENTER, textColor=NAVY)
    s_title_en = ParagraphStyle('t_en', fontName=EN_BOLD, fontSize=10, alignment=TA_CENTER, textColor=TEXT_GRAY)
    s_ref = ParagraphStyle('ref', fontName=EN_BOLD, fontSize=9, alignment=TA_CENTER, textColor=GOLD)
    s_label = ParagraphStyle('lbl', fontName=AR_FONT, fontSize=8, alignment=TA_RIGHT, textColor=TEXT_GRAY)
    s_value = ParagraphStyle('val', fontName=AR_BOLD, fontSize=9, alignment=TA_RIGHT, textColor=TEXT_DARK)
    s_label_en = ParagraphStyle('lbl_en', fontName=EN_FONT, fontSize=7, alignment=TA_LEFT, textColor=TEXT_GRAY)
    s_value_en = ParagraphStyle('val_en', fontName=EN_BOLD, fontSize=8, alignment=TA_LEFT, textColor=TEXT_DARK)
    s_status = ParagraphStyle('st', fontName=AR_BOLD, fontSize=10, alignment=TA_CENTER, textColor=st_color)
    s_status_en = ParagraphStyle('st_en', fontName=EN_BOLD, fontSize=8, alignment=TA_CENTER, textColor=st_color)
    s_sig_role = ParagraphStyle('sr', fontName=AR_BOLD, fontSize=8, alignment=TA_CENTER, textColor=WHITE)
    s_sig_role_en = ParagraphStyle('sr_en', fontName=EN_FONT, fontSize=6, alignment=TA_CENTER, textColor=colors.Color(0.9,0.9,0.95))
    s_sig_name = ParagraphStyle('sn', fontName=AR_BOLD, fontSize=7, alignment=TA_CENTER, textColor=TEXT_DARK)
    s_sig_name_en = ParagraphStyle('sn_en', fontName=EN_FONT, fontSize=6, alignment=TA_CENTER, textColor=TEXT_GRAY)
    s_sig_date = ParagraphStyle('sd', fontName=EN_FONT, fontSize=6, alignment=TA_CENTER, textColor=TEXT_GRAY)
    s_sig_ok = ParagraphStyle('sok', fontName=AR_BOLD, fontSize=6, alignment=TA_CENTER, textColor=GREEN)
    s_tear = ParagraphStyle('tear', fontName=EN_FONT, fontSize=8, alignment=TA_CENTER, textColor=TEXT_GRAY)
    s_coupon_ar = ParagraphStyle('cp_ar', fontName=AR_BOLD, fontSize=9, alignment=TA_CENTER, textColor=NAVY)
    s_coupon_en = ParagraphStyle('cp_en', fontName=EN_BOLD, fontSize=7, alignment=TA_CENTER, textColor=NAVY)
    s_coupon_sm = ParagraphStyle('cp_sm', fontName=EN_FONT, fontSize=6, alignment=TA_CENTER, textColor=TEXT_DARK)
    s_valid = ParagraphStyle('valid', fontName=AR_BOLD, fontSize=8, alignment=TA_CENTER, textColor=GREEN)
    
    # ══════════════════════════════════════════════════════════════
    # 1. HEADER - الترويسة
    # ══════════════════════════════════════════════════════════════
    header_content = [
        [_logo(), 
         Table([
             [Paragraph(_ar(co_ar), s_co_ar)],
             [Paragraph(co_en, s_co_en)],
             [Paragraph("Kingdom of Saudi Arabia | License: 5110004935 | CR: 1010463476", s_co_sm)],
         ], colWidths=[CONTENT_WIDTH - 25*mm])]
    ]
    header = Table(header_content, colWidths=[22*mm, CONTENT_WIDTH - 22*mm])
    header.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, 0), (-1, -1), 2, NAVY),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
    ]))
    elements.append(header)
    elements.append(Spacer(1, 3*mm))
    
    # ══════════════════════════════════════════════════════════════
    # 2. TITLE - العنوان
    # ══════════════════════════════════════════════════════════════
    title_tbl = Table([
        [Paragraph(_ar(type_ar), s_title_ar)],
        [Paragraph(type_en, s_title_en)],
        [Paragraph(ref, s_ref)],
    ], colWidths=[CONTENT_WIDTH])
    title_tbl.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    elements.append(title_tbl)
    elements.append(Spacer(1, 3*mm))
    
    # ══════════════════════════════════════════════════════════════
    # 3. INFO SECTION - ثلثين + ثلث
    # ══════════════════════════════════════════════════════════════
    two_thirds = CONTENT_WIDTH * 0.65
    one_third = CONTENT_WIDTH * 0.35
    
    # Left side - معلومات المعاملة (ثلثين)
    info_rows = []
    
    # Employee info
    info_rows.append([
        Paragraph(_ar("الموظف:"), s_label),
        Paragraph(_ar(emp_ar), s_value),
    ])
    info_rows.append([
        Paragraph("Employee:", s_label_en),
        Paragraph(emp_en, s_value_en),
    ])
    
    if emp_no:
        info_rows.append([
            Paragraph(_ar("الرقم الوظيفي:"), s_label),
            Paragraph(emp_no, s_value),
        ])
    
    # Type-specific details
    if tx_type == 'leave_request':
        lt = data.get('leave_type', '')
        lt_map = {'annual': ('سنوية', 'Annual'), 'sick': ('مرضية', 'Sick'), 'emergency': ('طارئة', 'Emergency')}
        lt_ar, lt_en = lt_map.get(lt, (lt, lt))
        
        info_rows.append([Paragraph(_ar("نوع الإجازة:"), s_label), Paragraph(_ar(lt_ar), s_value)])
        info_rows.append([Paragraph("Leave Type:", s_label_en), Paragraph(lt_en, s_value_en)])
        info_rows.append([Paragraph(_ar("من:"), s_label), Paragraph(data.get('start_date', '-').replace('-', '.'), s_value)])
        info_rows.append([Paragraph(_ar("إلى:"), s_label), Paragraph(data.get('end_date', '-').replace('-', '.'), s_value)])
        info_rows.append([Paragraph(_ar("أيام العمل:"), s_label), Paragraph(str(data.get('working_days', '-')), s_value)])
    
    elif tx_type in ('tangible_custody',):
        info_rows.append([Paragraph(_ar("العنصر:"), s_label), Paragraph(_ar(data.get('item_name_ar', data.get('item_name', '-'))), s_value)])
        info_rows.append([Paragraph("Item:", s_label_en), Paragraph(data.get('item_name', '-'), s_value_en)])
        info_rows.append([Paragraph(_ar("الرقم التسلسلي:"), s_label), Paragraph(data.get('serial_number', '-'), s_value)])
        info_rows.append([Paragraph(_ar("القيمة:"), s_label), Paragraph(f"{data.get('estimated_value', 0):,.2f} SAR", s_value)])
    
    elif tx_type == 'salary_advance':
        info_rows.append([Paragraph(_ar("المبلغ:"), s_label), Paragraph(f"{data.get('amount', 0):,.2f} SAR", s_value)])
        info_rows.append([Paragraph(_ar("السبب:"), s_label), Paragraph(_ar(data.get('reason', '-')), s_value)])
    
    left_tbl = Table(info_rows, colWidths=[two_thirds * 0.35, two_thirds * 0.65])
    left_tbl.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    
    # Right side - QR + الحالة (ثلث)
    verify_qr = _qr(f"VERIFY-{ref}", size=22)
    
    right_content = [
        [verify_qr if verify_qr else Paragraph("QR", s_coupon_sm)],
        [Spacer(1, 2*mm)],
        [Paragraph(_ar(st_ar), s_status)],
        [Paragraph(st_en, s_status_en)],
        [Spacer(1, 2*mm)],
        [Paragraph(_date(created), s_sig_date)],
        [Spacer(1, 2*mm)],
        [Paragraph(_ar("معرف السلامة:"), s_label)],
        [Paragraph(integrity, s_sig_date)],
    ]
    right_tbl = Table(right_content, colWidths=[one_third - 5*mm])
    right_tbl.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1, BORDER),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    # Combine left + right
    info_section = Table([[left_tbl, right_tbl]], colWidths=[two_thirds, one_third])
    info_section.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'RIGHT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(info_section)
    elements.append(Spacer(1, 4*mm))
    
    # ══════════════════════════════════════════════════════════════
    # 4. SIGNATURES TABLE - جدول التوقيعات الأفقي
    # ══════════════════════════════════════════════════════════════
    # Title
    sig_title = Table([[Paragraph(_ar("التوقيعات | Signatures"), s_title_ar)]], colWidths=[CONTENT_WIDTH])
    sig_title.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    elements.append(sig_title)
    elements.append(Spacer(1, 2*mm))
    
    # Build signatures
    sigs = []
    added = set()
    
    # Employee
    sigs.append(('الموظف', 'Employee', emp_ar, emp_en, True, created))
    added.add('Employee')
    
    # From approval chain
    for a in chain:
        stage = a.get('stage', '')
        ts = a.get('timestamp', '')
        if stage == 'ceo' and 'CEO' not in added:
            sigs.append(('الرئيس التنفيذي', 'CEO', 'محمد', 'Mohammed', True, ts))
            added.add('CEO')
        elif stage in ('hr', 'sultan') and 'HR' not in added:
            sigs.append(('الموارد البشرية', 'HR', 'سلطان', 'Sultan', True, ts))
            added.add('HR')
        elif stage == 'stas' and 'STAS' not in added:
            sigs.append(('STAS', 'STAS', 'STAS', 'STAS', True, ts))
            added.add('STAS')
    
    # Add STAS if executed
    if status == 'executed' and 'STAS' not in added:
        sigs.append(('STAS', 'STAS', 'STAS', 'STAS', True, transaction.get('executed_at', '')))
        added.add('STAS')
    
    # Build table
    sig_col_w = CONTENT_WIDTH / len(sigs) if sigs else CONTENT_WIDTH / 4
    
    # Header row
    header_row = []
    for role_ar, role_en, _, _, _, _ in sigs:
        cell = Table([
            [Paragraph(_ar(role_ar), s_sig_role)],
            [Paragraph(role_en, s_sig_role_en)],
        ], colWidths=[sig_col_w - 2*mm])
        cell.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BACKGROUND', (0, 0), (-1, -1), NAVY),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        header_row.append(cell)
    
    # QR row
    qr_row = []
    for role_ar, role_en, _, _, signed, _ in sigs:
        qr_img = _qr(f"SIG-{role_en.upper()}-{ref}", size=15) if signed else Paragraph("—", s_sig_date)
        qr_row.append(qr_img)
    
    # Name row
    name_row = []
    for _, _, name_ar, name_en, _, _ in sigs:
        cell = Table([
            [Paragraph(_ar(name_ar), s_sig_name)],
            [Paragraph(name_en, s_sig_name_en)],
        ], colWidths=[sig_col_w - 2*mm])
        cell.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
        name_row.append(cell)
    
    # Date row
    date_row = []
    for _, _, _, _, signed, ts in sigs:
        date_row.append(Paragraph(_date(ts) if signed else "____.__.__  |  __:__", s_sig_date))
    
    # Status row
    status_row = []
    for _, _, _, _, signed, _ in sigs:
        status_row.append(Paragraph(_ar("✓ موقع | Signed") if signed else "", s_sig_ok))
    
    # Combine
    sig_data = [header_row, qr_row, name_row, date_row, status_row]
    sig_tbl = Table(sig_data, colWidths=[sig_col_w] * len(sigs))
    sig_tbl.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1.5, NAVY),
        ('LINEBELOW', (0, 0), (-1, 0), 1, NAVY),
        ('INNERGRID', (0, 1), (-1, -1), 0.5, BORDER),
        ('BACKGROUND', (0, 1), (-1, -1), WHITE),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(sig_tbl)
    elements.append(Spacer(1, 5*mm))
    
    # ══════════════════════════════════════════════════════════════
    # 5. TEAR-OFF LINE - خط القص
    # ══════════════════════════════════════════════════════════════
    tear_line = "─ " * 25 + " ✂  قص هنا | Cut Here  ✂ " + " ─" * 25
    elements.append(Paragraph(tear_line, s_tear))
    elements.append(Spacer(1, 3*mm))
    
    # ══════════════════════════════════════════════════════════════
    # 6. COUPON - قسيمة STAS للملفات اليدوية
    # ══════════════════════════════════════════════════════════════
    stas_qr = _qr(f"STAS-FILE-{ref}", size=20) if status == 'executed' else Paragraph(_ar("بانتظار"), s_coupon_sm)
    
    coupon_left = Table([
        [stas_qr],
        [Paragraph("STAS QR", s_coupon_sm)],
        [Paragraph(_ar("للملفات اليدوية"), s_coupon_sm)],
    ], colWidths=[30*mm])
    coupon_left.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    
    coupon_center = Table([
        [Paragraph(_ar(co_ar), s_coupon_ar)],
        [Paragraph(co_en, s_coupon_en)],
        [Paragraph(f"{_ar(type_ar)} | {type_en}", s_coupon_sm)],
        [Paragraph(ref, s_coupon_sm)],
        [Paragraph(f"{_ar(emp_ar)} | {emp_en}", s_coupon_sm)],
        [Paragraph(_ar("✓ معاملة صحيحة | Valid Document") if status == 'executed' else _ar("بانتظار التنفيذ"), s_valid if status == 'executed' else s_coupon_sm)],
    ], colWidths=[CONTENT_WIDTH - 70*mm])
    coupon_center.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    
    coupon_right = Table([
        [_qr(f"VERIFY-{ref}", size=20)],
        [Paragraph("Verify QR", s_coupon_sm)],
        [Paragraph(_ar("للتحقق"), s_coupon_sm)],
    ], colWidths=[30*mm])
    coupon_right.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    
    coupon = Table([[coupon_left, coupon_center, coupon_right]], colWidths=[35*mm, CONTENT_WIDTH - 70*mm, 35*mm])
    coupon.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1.5, GOLD),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(coupon)
    
    # ══════════════════════════════════════════════════════════════
    # BUILD PDF
    # ══════════════════════════════════════════════════════════════
    doc.build(elements)
    pdf_bytes = buf.getvalue()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    return pdf_bytes, pdf_hash, integrity


# Compatibility exports
def create_unified_header(branding=None): pass
def create_tear_off_line(): pass
def create_signatures_table(signatures, ref_no): pass
def create_tear_off_coupon(*args, **kwargs): pass
def create_document_title(*args, **kwargs): pass
def create_bilingual_row(*args, **kwargs): pass
def create_footer(*args, **kwargs): pass
def format_saudi_time(ts): return _date(ts)
