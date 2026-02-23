"""
PDF بسيط ومنظم - مثل Excel
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
import base64
import io
import os
from datetime import datetime, timezone, timedelta

W, H = A4
M = 10*mm
CW = W - 2*M

NAVY = colors.Color(0.118, 0.227, 0.373)
GOLD = colors.Color(0.753, 0.620, 0.349)
WHITE = colors.white
LIGHT = colors.Color(0.96, 0.96, 0.97)
GRAY = colors.Color(0.5, 0.5, 0.55)
DARK = colors.Color(0.2, 0.2, 0.22)
GREEN = colors.Color(0.2, 0.55, 0.35)

FD = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')
AR, ARB = 'Helvetica', 'Helvetica-Bold'
try:
    pdfmetrics.registerFont(TTFont('Ar', os.path.join(FD, 'NotoNaskhArabic-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('ArB', os.path.join(FD, 'NotoNaskhArabic-Bold.ttf')))
    AR, ARB = 'Ar', 'ArB'
except: pass

def ar(t):
    if not t: return ''
    try: return get_display(arabic_reshaper.reshape(str(t)))
    except: return str(t)

def dt(ts):
    if not ts: return '-'
    try:
        if isinstance(ts, str):
            ts = ts.replace('Z', '+00:00')
            d = datetime.fromisoformat(ts) if 'T' in ts else datetime.strptime(ts[:19], '%Y-%m-%d %H:%M:%S')
        else: d = ts
        if d.tzinfo is None: d = d.replace(tzinfo=timezone.utc)
        d = d + timedelta(hours=3)
        return d.strftime('%Y.%m.%d | %H:%M')
    except: return str(ts)[:16]

def make_qr(data, sz=10):
    try:
        q = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=2, border=0)
        q.add_data(data)
        q.make(fit=True)
        img = q.make_image(fill_color="#1E3A5F", back_color="white")
        b = io.BytesIO()
        img.save(b, format='PNG')
        b.seek(0)
        return RLImage(b, width=sz*mm, height=sz*mm)
    except: return None

def make_logo(logo_data, sz=15):
    if logo_data:
        try:
            if ',' in logo_data:
                logo_data = logo_data.split(',')[1]
            img_bytes = base64.b64decode(logo_data)
            buf = io.BytesIO(img_bytes)
            return RLImage(buf, width=sz*mm, height=sz*mm)
        except: pass
    return None


def generate_professional_transaction_pdf(tx: dict, emp: dict = None, brand: dict = None) -> tuple:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=M, bottomMargin=M, leftMargin=M, rightMargin=M)
    els = []
    
    ref = tx.get('ref_no', 'TXN-0000')
    typ = tx.get('type', '')
    status = tx.get('status', '')
    created = tx.get('created_at', '')
    data = tx.get('data', {})
    chain = tx.get('approval_chain', [])
    
    h = hashlib.sha256(f"{ref}{tx.get('id','')}".encode()).hexdigest()[:8]
    integrity = f"DAR-{ref.replace('TXN-','').replace('-','')}-{h}".upper()
    
    co_ar = brand.get('company_name_ar', 'شركة دار الكود للاستشارات الهندسية') if brand else 'شركة دار الكود للاستشارات الهندسية'
    co_en = brand.get('company_name_en', 'DAR AL CODE Engineering Consultancy') if brand else 'DAR AL CODE Engineering Consultancy'
    logo_data = brand.get('logo_data') if brand else None
    
    emp_ar = data.get('employee_name_ar', emp.get('full_name_ar','') if emp else '')
    emp_en = data.get('employee_name', emp.get('full_name','') if emp else '')
    
    types = {'leave_request':('طلب إجازة','Leave Request'), 'tangible_custody':('عهدة عينية','In-Kind Custody'), 'salary_advance':('سلفة راتب','Salary Advance'), 'settlement':('مخالصة','Settlement')}
    typ_ar, typ_en = types.get(typ, (typ, typ))
    
    stats = {'executed':('منفذة','Executed'), 'pending':('معلقة','Pending'), 'stas':('STAS','Pending'), 'ceo':('CEO','Pending')}
    st_ar, st_en = stats.get(status, (status, status))
    
    # Styles
    s_title = ParagraphStyle('title', fontName=ARB, fontSize=11, alignment=TA_CENTER, textColor=NAVY)
    s_sub = ParagraphStyle('sub', fontName='Helvetica-Bold', fontSize=8, alignment=TA_CENTER, textColor=NAVY)
    s_small = ParagraphStyle('small', fontName='Helvetica', fontSize=6, alignment=TA_CENTER, textColor=GRAY)
    s_lbl = ParagraphStyle('lbl', fontName=AR, fontSize=7, alignment=TA_CENTER, textColor=GRAY)
    s_val = ParagraphStyle('val', fontName=ARB, fontSize=8, alignment=TA_CENTER, textColor=DARK)
    s_sec = ParagraphStyle('sec', fontName=ARB, fontSize=9, alignment=TA_CENTER, textColor=NAVY)
    s_sig = ParagraphStyle('sig', fontName=ARB, fontSize=7, alignment=TA_CENTER, textColor=DARK)
    s_role = ParagraphStyle('role', fontName=AR, fontSize=6, alignment=TA_CENTER, textColor=GRAY)
    s_ok = ParagraphStyle('ok', fontName=ARB, fontSize=6, alignment=TA_CENTER, textColor=GREEN)
    s_tear = ParagraphStyle('tear', fontName='Helvetica', fontSize=7, alignment=TA_CENTER, textColor=GRAY)
    
    # ═══════════════════════════════════════════════════════════════════
    # 1. الترويسة الكاملة
    # ═══════════════════════════════════════════════════════════════════
    logo_img = make_logo(logo_data, 18)
    
    if logo_img:
        header = Table([
            [logo_img],
            [Paragraph(ar(co_ar), s_title)],
            [Paragraph(co_en, s_sub)],
            [Paragraph("Kingdom of Saudi Arabia | License: 5110004935 | CR: 1010463476", s_small)],
        ], colWidths=[CW])
    else:
        header = Table([
            [Paragraph(ar(co_ar), s_title)],
            [Paragraph(co_en, s_sub)],
            [Paragraph("Kingdom of Saudi Arabia | License: 5110004935 | CR: 1010463476", s_small)],
        ], colWidths=[CW])
    
    header.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('LINEBELOW', (0,-1), (-1,-1), 1.5, NAVY),
        ('BOTTOMPADDING', (0,-1), (-1,-1), 3),
    ]))
    els.append(header)
    els.append(Spacer(1, 4*mm))
    
    # ═══════════════════════════════════════════════════════════════════
    # 2. نوع المعاملة ورقمها
    # ═══════════════════════════════════════════════════════════════════
    els.append(Paragraph(ar(typ_ar) + " | " + typ_en, s_title))
    els.append(Paragraph(ref, ParagraphStyle('ref', fontName='Helvetica-Bold', fontSize=9, alignment=TA_CENTER, textColor=GOLD)))
    els.append(Spacer(1, 3*mm))
    
    # ═══════════════════════════════════════════════════════════════════
    # 3. معلومات المعاملة والموظف - جدول أفقي
    # ═══════════════════════════════════════════════════════════════════
    # صف العناوين
    labels_ar = [ar("الحالة"), ar("التاريخ"), ar("الموظف"), ar("المعرف")]
    labels_en = ["Status", "Date", "Employee", "ID"]
    values = [ar(st_ar) + " | " + st_en, dt(created), ar(emp_ar), integrity]
    
    col_w = CW / 4
    
    info_header = Table([[Paragraph(l, s_lbl) for l in labels_ar]], colWidths=[col_w]*4)
    info_header.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BACKGROUND', (0,0), (-1,-1), NAVY),
        ('TEXTCOLOR', (0,0), (-1,-1), WHITE),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    
    info_values = Table([[Paragraph(v, s_val) for v in values]], colWidths=[col_w]*4)
    info_values.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOX', (0,0), (-1,-1), 0.5, NAVY),
        ('INNERGRID', (0,0), (-1,-1), 0.5, LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    
    els.append(info_header)
    els.append(info_values)
    els.append(Spacer(1, 2*mm))
    
    # تفاصيل حسب نوع المعاملة
    if typ == 'leave_request':
        lt = data.get('leave_type', '')
        lt_m = {'annual':('سنوية','Annual'), 'sick':('مرضية','Sick'), 'emergency':('طارئة','Emergency')}
        lt_ar, lt_en = lt_m.get(lt, (lt, lt))
        
        det_labels = [ar("النوع"), ar("من"), ar("إلى"), ar("الأيام")]
        det_values = [ar(lt_ar), data.get('start_date','-').replace('-','.'), data.get('end_date','-').replace('-','.'), str(data.get('working_days','-'))]
        
        det_header = Table([[Paragraph(l, s_lbl) for l in det_labels]], colWidths=[col_w]*4)
        det_header.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('BACKGROUND', (0,0), (-1,-1), GOLD),
            ('TEXTCOLOR', (0,0), (-1,-1), WHITE),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        
        det_values_tbl = Table([[Paragraph(v, s_val) for v in det_values]], colWidths=[col_w]*4)
        det_values_tbl.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('BOX', (0,0), (-1,-1), 0.5, GOLD),
            ('INNERGRID', (0,0), (-1,-1), 0.5, LIGHT),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        
        els.append(det_header)
        els.append(det_values_tbl)
    
    elif typ == 'tangible_custody':
        det_labels = [ar("العنصر"), ar("الرقم التسلسلي"), ar("القيمة"), ""]
        det_values = [ar(data.get('item_name_ar', data.get('item_name','-'))), data.get('serial_number','-'), f"{data.get('estimated_value',0):,.0f} SAR", ""]
        
        det_header = Table([[Paragraph(l, s_lbl) for l in det_labels]], colWidths=[col_w]*4)
        det_header.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('BACKGROUND', (0,0), (-1,-1), GOLD), ('TEXTCOLOR', (0,0), (-1,-1), WHITE), ('TOPPADDING', (0,0), (-1,-1), 2), ('BOTTOMPADDING', (0,0), (-1,-1), 2)]))
        
        det_values_tbl = Table([[Paragraph(v, s_val) for v in det_values]], colWidths=[col_w]*4)
        det_values_tbl.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('BOX', (0,0), (-1,-1), 0.5, GOLD), ('INNERGRID', (0,0), (-1,-1), 0.5, LIGHT), ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3)]))
        
        els.append(det_header)
        els.append(det_values_tbl)
    
    elif typ == 'salary_advance':
        det_labels = [ar("المبلغ"), ar("السبب"), "", ""]
        det_values = [f"{data.get('amount',0):,.0f} SAR", ar(data.get('reason','-')), "", ""]
        
        det_header = Table([[Paragraph(l, s_lbl) for l in det_labels]], colWidths=[col_w]*4)
        det_header.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('BACKGROUND', (0,0), (-1,-1), GOLD), ('TEXTCOLOR', (0,0), (-1,-1), WHITE), ('TOPPADDING', (0,0), (-1,-1), 2), ('BOTTOMPADDING', (0,0), (-1,-1), 2)]))
        
        det_values_tbl = Table([[Paragraph(v, s_val) for v in det_values]], colWidths=[col_w]*4)
        det_values_tbl.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('BOX', (0,0), (-1,-1), 0.5, GOLD), ('INNERGRID', (0,0), (-1,-1), 0.5, LIGHT), ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3)]))
        
        els.append(det_header)
        els.append(det_values_tbl)
    
    els.append(Spacer(1, 5*mm))
    
    # ═══════════════════════════════════════════════════════════════════
    # 4. جدول التوقيعات - 3 مستطيلات أفقية
    # ═══════════════════════════════════════════════════════════════════
    els.append(Paragraph(ar("التوقيعات") + " | Signatures", s_sec))
    els.append(Spacer(1, 2*mm))
    
    signed = {a.get('stage'): a.get('timestamp','') for a in chain}
    
    # 3 أشخاص: سلطان (HR) | محمد (CEO) | STAS
    sig_w = CW / 3
    
    # سلطان
    sultan_signed = 'hr' in signed or 'sultan' in signed
    sultan_ts = signed.get('hr', signed.get('sultan', ''))
    
    # محمد
    ceo_signed = 'ceo' in signed
    ceo_ts = signed.get('ceo', '')
    
    # STAS
    stas_signed = status == 'executed' or 'stas' in signed
    stas_ts = signed.get('stas', tx.get('executed_at', ''))
    
    def make_sig_box(name_ar, name_en, role_ar, role_en, is_signed, timestamp):
        qr_img = make_qr(f"SIG-{name_en}-{ref}", 12) if is_signed else Paragraph("—", s_role)
        return Table([
            [Paragraph(ar("توقيع"), s_lbl)],
            [qr_img],
            [Paragraph(ar(name_ar), s_sig)],
            [Paragraph(name_en, s_role)],
            [Paragraph(ar(role_ar), s_role)],
            [Paragraph(role_en, s_role)],
            [Paragraph(dt(timestamp) if is_signed else "—", s_role)],
            [Paragraph("✓" if is_signed else "", s_ok)],
        ], colWidths=[sig_w - 4*mm])
    
    sultan_box = make_sig_box("سلطان", "Sultan", "الموارد البشرية", "HR", sultan_signed, sultan_ts)
    mohammed_box = make_sig_box("محمد", "Mohammed", "الرئيس التنفيذي", "CEO", ceo_signed, ceo_ts)
    stas_box = make_sig_box("STAS", "STAS", "التنفيذ", "Execution", stas_signed, stas_ts)
    
    sig_table = Table([[sultan_box, mohammed_box, stas_box]], colWidths=[sig_w, sig_w, sig_w])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOX', (0,0), (-1,-1), 1, NAVY),
        ('INNERGRID', (0,0), (-1,-1), 0.5, NAVY),
        ('BACKGROUND', (0,0), (-1,-1), LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    els.append(sig_table)
    els.append(Spacer(1, 4*mm))
    
    # ═══════════════════════════════════════════════════════════════════
    # 5. QR للمعاملة (فوق خط القص)
    # ═══════════════════════════════════════════════════════════════════
    tx_qr = make_qr(f"TX-{ref}-{integrity}", 15)
    
    qr_above = Table([
        [tx_qr if tx_qr else Paragraph("QR", s_role)],
        [Paragraph(ar("رمز التحقق من المعاملة"), s_role)],
        [Paragraph(integrity, s_small)],
    ], colWidths=[CW])
    qr_above.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    els.append(qr_above)
    els.append(Spacer(1, 3*mm))
    
    # ═══════════════════════════════════════════════════════════════════
    # 6. خط القص
    # ═══════════════════════════════════════════════════════════════════
    els.append(Paragraph("─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ✂ " + ar("قص هنا") + " | Cut Here ✂ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─", s_tear))
    els.append(Spacer(1, 3*mm))
    
    # ═══════════════════════════════════════════════════════════════════
    # 7. QR للملفات (تحت خط القص)
    # ═══════════════════════════════════════════════════════════════════
    file_qr = make_qr(f"FILE-{ref}-{integrity}", 15)
    
    qr_below = Table([
        [file_qr if file_qr else Paragraph("QR", s_role)],
        [Paragraph(ar("للملفات اليدوية"), s_role)],
        [Paragraph(ar(co_ar), ParagraphStyle('co', fontName=ARB, fontSize=7, alignment=TA_CENTER, textColor=NAVY))],
        [Paragraph(f"{typ_en} | {ref}", s_small)],
        [Paragraph(ar(emp_ar) + " | " + emp_en, s_small)],
        [Paragraph(ar("✓ معاملة صحيحة") if status == 'executed' else ar("بانتظار"), s_ok if status == 'executed' else s_role)],
    ], colWidths=[CW])
    qr_below.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOX', (0,0), (-1,-1), 1, GOLD),
        ('BACKGROUND', (0,0), (-1,-1), LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    els.append(qr_below)
    
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
def format_saudi_time(t): return dt(t)
