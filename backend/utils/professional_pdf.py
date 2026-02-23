"""
Professional PDF - تصميم مدمج متوازن
صفحة واحدة A4
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image as RLImage
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display
import qrcode
import hashlib
import io
import os
from datetime import datetime, timezone, timedelta

# Page
PAGE_W, PAGE_H = A4
MARGIN = 12 * mm
WIDTH = PAGE_W - (2 * MARGIN)

# Colors
NAVY = colors.Color(0.118, 0.227, 0.373)
GOLD = colors.Color(0.753, 0.620, 0.349)
WHITE = colors.white
LIGHT = colors.Color(0.97, 0.97, 0.98)
BORDER = colors.Color(0.88, 0.88, 0.90)
DARK = colors.Color(0.2, 0.2, 0.22)
GRAY = colors.Color(0.5, 0.5, 0.55)
GREEN = colors.Color(0.15, 0.55, 0.35)

# Fonts
FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')
AR = 'NotoNaskhArabic'
AR_B = 'NotoNaskhArabicBold'

def _init_fonts():
    global AR, AR_B
    try:
        p = os.path.join(FONTS_DIR, 'NotoNaskhArabic-Regular.ttf')
        pb = os.path.join(FONTS_DIR, 'NotoNaskhArabic-Bold.ttf')
        if os.path.exists(p):
            pdfmetrics.registerFont(TTFont('NotoNaskhArabic', p))
            AR = 'NotoNaskhArabic'
        if os.path.exists(pb):
            pdfmetrics.registerFont(TTFont('NotoNaskhArabicBold', pb))
            AR_B = 'NotoNaskhArabicBold'
    except:
        pass

_init_fonts()

def _ar(t):
    if not t: return ''
    try: return get_display(arabic_reshaper.reshape(str(t)))
    except: return str(t)

def _dt(ts):
    if not ts: return '-'
    try:
        if isinstance(ts, str):
            ts = ts.replace('Z', '+00:00')
            dt = datetime.fromisoformat(ts) if 'T' in ts else datetime.strptime(ts[:19], '%Y-%m-%d %H:%M:%S')
        else:
            dt = ts
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt + timedelta(hours=3)
        return dt.strftime('%Y.%m.%d | %H:%M')
    except:
        return str(ts)[:16]

def _qr(data, sz=12):
    try:
        q = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=2, border=1)
        q.add_data(data)
        q.make(fit=True)
        img = q.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return RLImage(buf, width=sz*mm, height=sz*mm)
    except:
        return None


def generate_professional_transaction_pdf(tx: dict, emp: dict = None, brand: dict = None) -> tuple:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=MARGIN, bottomMargin=MARGIN, leftMargin=MARGIN, rightMargin=MARGIN)
    
    els = []
    
    # Data
    ref = tx.get('ref_no', 'TXN-0000')
    typ = tx.get('type', 'unknown')
    status = tx.get('status', 'pending')
    created = tx.get('created_at', '')
    data = tx.get('data', {})
    chain = tx.get('approval_chain', [])
    
    # Integrity
    h = hashlib.sha256(f"{ref}{tx.get('id', '')}".encode()).hexdigest()[:8]
    integrity = f"DAR-{ref.replace('TXN-', '').replace('-', '')}-{h}".upper()
    
    # Company
    co_ar = brand.get('company_name_ar', 'شركة دار الكود للاستشارات الهندسية') if brand else 'شركة دار الكود للاستشارات الهندسية'
    co_en = brand.get('company_name_en', 'DAR AL CODE Engineering Consultancy') if brand else 'DAR AL CODE Engineering Consultancy'
    
    # Employee
    emp_ar = data.get('employee_name_ar', emp.get('full_name_ar', '') if emp else '')
    emp_en = data.get('employee_name', emp.get('full_name', '') if emp else '')
    emp_no = emp.get('employee_number', '') if emp else ''
    
    # Type
    types = {
        'leave_request': ('طلب إجازة', 'Leave Request'),
        'tangible_custody': ('عهدة عينية', 'In-Kind Custody'),
        'finance_60': ('عهدة مالية', 'Financial Custody'),
        'settlement': ('مخالصة نهائية', 'Final Settlement'),
        'salary_advance': ('سلفة راتب', 'Salary Advance'),
    }
    typ_ar, typ_en = types.get(typ, (typ, typ))
    
    # Status
    stats = {
        'executed': ('منفذة', 'Executed', GREEN),
        'pending': ('معلقة', 'Pending', GRAY),
        'stas': ('بانتظار STAS', 'Pending STAS', GOLD),
        'ceo': ('بانتظار CEO', 'Pending CEO', GOLD),
        'rejected': ('مرفوضة', 'Rejected', colors.red),
    }
    st_ar, st_en, st_c = stats.get(status, (status, status, GRAY))
    
    # Styles
    s_h_ar = ParagraphStyle('har', fontName=AR_B, fontSize=10, alignment=TA_CENTER, textColor=NAVY)
    s_h_en = ParagraphStyle('hen', fontName='Helvetica-Bold', fontSize=8, alignment=TA_CENTER, textColor=NAVY)
    s_h_sm = ParagraphStyle('hsm', fontName='Helvetica', fontSize=6, alignment=TA_CENTER, textColor=GRAY)
    s_t_ar = ParagraphStyle('tar', fontName=AR_B, fontSize=11, alignment=TA_CENTER, textColor=NAVY)
    s_t_en = ParagraphStyle('ten', fontName='Helvetica-Bold', fontSize=8, alignment=TA_CENTER, textColor=GRAY)
    s_ref = ParagraphStyle('ref', fontName='Helvetica-Bold', fontSize=8, alignment=TA_CENTER, textColor=GOLD)
    
    s_lbl_ar = ParagraphStyle('lar', fontName=AR, fontSize=8, alignment=TA_RIGHT, textColor=GRAY)
    s_val_ar = ParagraphStyle('var', fontName=AR_B, fontSize=8, alignment=TA_RIGHT, textColor=DARK)
    s_lbl_en = ParagraphStyle('len', fontName='Helvetica', fontSize=7, alignment=TA_LEFT, textColor=GRAY)
    s_val_en = ParagraphStyle('ven', fontName='Helvetica-Bold', fontSize=7, alignment=TA_LEFT, textColor=DARK)
    
    s_sec = ParagraphStyle('sec', fontName=AR_B, fontSize=9, alignment=TA_CENTER, textColor=NAVY)
    s_sig_h = ParagraphStyle('sigh', fontName=AR_B, fontSize=7, alignment=TA_CENTER, textColor=WHITE)
    s_sig_n = ParagraphStyle('sign', fontName=AR, fontSize=6, alignment=TA_CENTER, textColor=DARK)
    s_sig_d = ParagraphStyle('sigd', fontName='Helvetica', fontSize=5, alignment=TA_CENTER, textColor=GRAY)
    s_sig_ok = ParagraphStyle('sigok', fontName=AR_B, fontSize=5, alignment=TA_CENTER, textColor=GREEN)
    
    s_tear = ParagraphStyle('tear', fontName='Helvetica', fontSize=7, alignment=TA_CENTER, textColor=GRAY)
    s_cp = ParagraphStyle('cp', fontName='Helvetica', fontSize=6, alignment=TA_CENTER, textColor=DARK)
    s_cp_ar = ParagraphStyle('cpar', fontName=AR_B, fontSize=7, alignment=TA_CENTER, textColor=NAVY)
    s_valid = ParagraphStyle('valid', fontName=AR_B, fontSize=7, alignment=TA_CENTER, textColor=GREEN)
    
    # ═══════════════════════════════════════════════════════════
    # 1. HEADER (مدمج)
    # ═══════════════════════════════════════════════════════════
    header = Table([
        [Paragraph(_ar(co_ar) + " | " + co_en, s_h_ar)],
        [Paragraph("License: 5110004935 | CR: 1010463476 | KSA", s_h_sm)],
    ], colWidths=[WIDTH])
    header.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('LINEBELOW', (0,-1), (-1,-1), 1.5, NAVY),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    els.append(header)
    els.append(Spacer(1, 2*mm))
    
    # ═══════════════════════════════════════════════════════════
    # 2. TITLE
    # ═══════════════════════════════════════════════════════════
    title = Table([
        [Paragraph(_ar(typ_ar) + " | " + typ_en, s_t_ar)],
        [Paragraph(ref, s_ref)],
    ], colWidths=[WIDTH])
    title.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    els.append(title)
    els.append(Spacer(1, 3*mm))
    
    # ═══════════════════════════════════════════════════════════
    # 3. INFO TABLE (الأولوية - عربي يمين | إنجليزي يسار)
    # ═══════════════════════════════════════════════════════════
    half = WIDTH / 2
    
    # Build rows: Arabic right | English left
    rows = []
    
    # Employee
    rows.append([
        Paragraph(emp_en, s_val_en), Paragraph("Employee", s_lbl_en),
        Paragraph(_ar("الموظف"), s_lbl_ar), Paragraph(_ar(emp_ar), s_val_ar)
    ])
    
    if emp_no:
        rows.append([
            Paragraph(emp_no, s_val_en), Paragraph("Emp No", s_lbl_en),
            Paragraph(_ar("الرقم"), s_lbl_ar), Paragraph(emp_no, s_val_ar)
        ])
    
    # Type specific
    if typ == 'leave_request':
        lt = data.get('leave_type', '')
        lt_m = {'annual': ('سنوية', 'Annual'), 'sick': ('مرضية', 'Sick'), 'emergency': ('طارئة', 'Emergency')}
        lt_ar, lt_en = lt_m.get(lt, (lt, lt))
        
        rows.append([
            Paragraph(lt_en, s_val_en), Paragraph("Type", s_lbl_en),
            Paragraph(_ar("النوع"), s_lbl_ar), Paragraph(_ar(lt_ar), s_val_ar)
        ])
        rows.append([
            Paragraph(data.get('start_date', '-').replace('-', '.'), s_val_en), Paragraph("From", s_lbl_en),
            Paragraph(_ar("من"), s_lbl_ar), Paragraph(data.get('start_date', '-').replace('-', '.'), s_val_ar)
        ])
        rows.append([
            Paragraph(data.get('end_date', '-').replace('-', '.'), s_val_en), Paragraph("To", s_lbl_en),
            Paragraph(_ar("إلى"), s_lbl_ar), Paragraph(data.get('end_date', '-').replace('-', '.'), s_val_ar)
        ])
        rows.append([
            Paragraph(str(data.get('working_days', '-')), s_val_en), Paragraph("Days", s_lbl_en),
            Paragraph(_ar("الأيام"), s_lbl_ar), Paragraph(str(data.get('working_days', '-')), s_val_ar)
        ])
    
    elif typ == 'tangible_custody':
        rows.append([
            Paragraph(data.get('item_name', '-'), s_val_en), Paragraph("Item", s_lbl_en),
            Paragraph(_ar("العنصر"), s_lbl_ar), Paragraph(_ar(data.get('item_name_ar', data.get('item_name', '-'))), s_val_ar)
        ])
        rows.append([
            Paragraph(data.get('serial_number', '-'), s_val_en), Paragraph("Serial", s_lbl_en),
            Paragraph(_ar("الرقم"), s_lbl_ar), Paragraph(data.get('serial_number', '-'), s_val_ar)
        ])
        rows.append([
            Paragraph(f"{data.get('estimated_value', 0):,.0f} SAR", s_val_en), Paragraph("Value", s_lbl_en),
            Paragraph(_ar("القيمة"), s_lbl_ar), Paragraph(f"{data.get('estimated_value', 0):,.0f} ريال", s_val_ar)
        ])
    
    elif typ == 'salary_advance':
        rows.append([
            Paragraph(f"{data.get('amount', 0):,.0f} SAR", s_val_en), Paragraph("Amount", s_lbl_en),
            Paragraph(_ar("المبلغ"), s_lbl_ar), Paragraph(f"{data.get('amount', 0):,.0f} ريال", s_val_ar)
        ])
    
    # Status & Date
    rows.append([
        Paragraph(st_en, s_val_en), Paragraph("Status", s_lbl_en),
        Paragraph(_ar("الحالة"), s_lbl_ar), Paragraph(_ar(st_ar), s_val_ar)
    ])
    rows.append([
        Paragraph(_dt(created), s_val_en), Paragraph("Date", s_lbl_en),
        Paragraph(_ar("التاريخ"), s_lbl_ar), Paragraph(_dt(created), s_val_ar)
    ])
    rows.append([
        Paragraph(integrity, s_val_en), Paragraph("ID", s_lbl_en),
        Paragraph(_ar("المعرف"), s_lbl_ar), Paragraph(integrity, s_val_ar)
    ])
    
    # Create table
    cw = [half*0.35, half*0.15, half*0.15, half*0.35]
    info_tbl = Table(rows, colWidths=cw)
    info_tbl.setStyle(TableStyle([
        ('ALIGN', (0,0), (1,-1), 'LEFT'),
        ('ALIGN', (2,0), (3,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOX', (0,0), (-1,-1), 1, NAVY),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER),
        ('BACKGROUND', (1,0), (2,-1), LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    els.append(info_tbl)
    els.append(Spacer(1, 4*mm))
    
    # ═══════════════════════════════════════════════════════════
    # 4. SIGNATURES (التسلسل: موظف → مشرف → HR → CEO → STAS)
    # ═══════════════════════════════════════════════════════════
    els.append(Paragraph(_ar("التوقيعات | Signatures"), s_sec))
    els.append(Spacer(1, 2*mm))
    
    # Determine who signed
    signed_stages = {a.get('stage'): a.get('timestamp', '') for a in chain}
    
    # Signature order
    sig_order = [
        ('creator', 'الموظف', 'Creator', emp_ar, emp_en, True, created),  # Creator always signed
        ('supervisor', 'المشرف', 'Supervisor', '-', '-', 'supervisor' in signed_stages, signed_stages.get('supervisor', '')),
        ('hr', 'HR', 'HR', 'سلطان', 'Sultan', 'hr' in signed_stages or 'sultan' in signed_stages, signed_stages.get('hr', signed_stages.get('sultan', ''))),
        ('ceo', 'CEO', 'CEO', 'محمد', 'Mohammed', 'ceo' in signed_stages, signed_stages.get('ceo', '')),
        ('stas', 'STAS', 'STAS', 'STAS', 'STAS', status == 'executed' or 'stas' in signed_stages, signed_stages.get('stas', tx.get('executed_at', ''))),
    ]
    
    # Filter - remove supervisor if not used
    if 'supervisor' not in signed_stages:
        sig_order = [s for s in sig_order if s[0] != 'supervisor']
    
    num_sigs = len(sig_order)
    sig_w = WIDTH / num_sigs
    
    # Header row
    h_row = []
    for _, ar, en, _, _, _, _ in sig_order:
        h_row.append(Paragraph(_ar(ar) + "\n" + en, s_sig_h))
    
    # QR row (only if signed)
    qr_row = []
    for key, _, en, _, _, signed, _ in sig_order:
        if signed:
            qr_row.append(_qr(f"SIG-{en}-{ref}", sz=10))
        else:
            qr_row.append(Paragraph("—", s_sig_d))
    
    # Name row
    n_row = []
    for _, _, _, n_ar, n_en, signed, _ in sig_order:
        if signed:
            n_row.append(Paragraph(_ar(n_ar) + "\n" + n_en, s_sig_n))
        else:
            n_row.append(Paragraph("—", s_sig_d))
    
    # Date row
    d_row = []
    for _, _, _, _, _, signed, ts in sig_order:
        if signed and ts:
            d_row.append(Paragraph(_dt(ts), s_sig_d))
        else:
            d_row.append(Paragraph("—", s_sig_d))
    
    # Status row
    st_row = []
    for _, _, _, _, _, signed, _ in sig_order:
        if signed:
            st_row.append(Paragraph(_ar("✓"), s_sig_ok))
        else:
            st_row.append(Paragraph("", s_sig_d))
    
    sig_tbl = Table([h_row, qr_row, n_row, d_row, st_row], colWidths=[sig_w]*num_sigs)
    sig_tbl.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('BOX', (0,0), (-1,-1), 1, NAVY),
        ('INNERGRID', (0,1), (-1,-1), 0.5, BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    els.append(sig_tbl)
    els.append(Spacer(1, 4*mm))
    
    # ═══════════════════════════════════════════════════════════
    # 5. TEAR-OFF LINE
    # ═══════════════════════════════════════════════════════════
    els.append(Paragraph("─ ─ ─ ─ ─ ─ ─ ─ ✂ قص هنا | Cut Here ✂ ─ ─ ─ ─ ─ ─ ─ ─", s_tear))
    els.append(Spacer(1, 2*mm))
    
    # ═══════════════════════════════════════════════════════════
    # 6. COUPON (مدمج)
    # ═══════════════════════════════════════════════════════════
    stas_qr = _qr(f"STAS-{ref}", sz=12) if status == 'executed' else Paragraph("—", s_cp)
    verify_qr = _qr(f"VERIFY-{ref}", sz=12)
    
    cp_left = Table([[stas_qr], [Paragraph("STAS", s_cp)]], colWidths=[20*mm])
    cp_left.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    
    cp_mid = Table([
        [Paragraph(_ar(co_ar), s_cp_ar)],
        [Paragraph(f"{typ_en} | {ref}", s_cp)],
        [Paragraph(_ar(emp_ar), s_cp)],
        [Paragraph(_ar("✓ صحيحة") if status == 'executed' else _ar("بانتظار"), s_valid if status == 'executed' else s_cp)],
    ], colWidths=[WIDTH - 50*mm])
    cp_mid.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    
    cp_right = Table([[verify_qr], [Paragraph("Verify", s_cp)]], colWidths=[20*mm])
    cp_right.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    
    coupon = Table([[cp_left, cp_mid, cp_right]], colWidths=[25*mm, WIDTH - 50*mm, 25*mm])
    coupon.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOX', (0,0), (-1,-1), 1, GOLD),
        ('BACKGROUND', (0,0), (-1,-1), LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    els.append(coupon)
    
    # Build
    doc.build(els)
    pdf = buf.getvalue()
    return pdf, hashlib.sha256(pdf).hexdigest(), integrity


# Compat
def create_unified_header(b=None): pass
def create_tear_off_line(): pass
def create_signatures_table(s, r): pass
def create_tear_off_coupon(*a, **k): pass
def create_document_title(*a, **k): pass
def create_bilingual_row(*a, **k): pass
def create_footer(*a, **k): pass
def format_saudi_time(t): return _dt(t)
