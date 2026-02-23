"""
PDF احترافي مدمج - صفحة واحدة A4
تصميم أفقي متوازن ومتناسق
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image as RLImage
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect
import arabic_reshaper
from bidi.algorithm import get_display
import qrcode
import hashlib
import io
import os
from datetime import datetime, timezone, timedelta

# A4
W, H = A4
M = 10*mm
CW = W - 2*M

# ألوان الشركة الرسمية
NAVY = colors.Color(0.118, 0.227, 0.373)  # #1E3A5F
GOLD = colors.Color(0.753, 0.620, 0.349)  # #C09E59
WHITE = colors.white
LIGHT = colors.Color(0.96, 0.96, 0.97)
GRAY = colors.Color(0.6, 0.6, 0.65)
DARK = colors.Color(0.2, 0.2, 0.22)
GREEN = colors.Color(0.2, 0.6, 0.4)

# Fonts
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

def qr(data, s=8):
    try:
        q = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=2, border=0)
        q.add_data(data)
        q.make(fit=True)
        img = q.make_image(fill_color="#1E3A5F", back_color="white")
        b = io.BytesIO()
        img.save(b, format='PNG')
        b.seek(0)
        return RLImage(b, width=s*mm, height=s*mm)
    except: return None

def logo(logo_data=None, size=12):
    """لوجو الشركة - من البيانات أو شكل افتراضي"""
    if logo_data:
        try:
            import base64
            if ',' in logo_data:
                logo_data = logo_data.split(',')[1]
            img_bytes = base64.b64decode(logo_data)
            buf = io.BytesIO(img_bytes)
            return RLImage(buf, width=size*mm, height=size*mm)
        except:
            pass
    # شكل افتراضي بألوان الشركة
    d = Drawing(size*mm, size*mm)
    d.add(Rect(0, 0, size*mm, size*mm, fillColor=NAVY, strokeColor=GOLD, strokeWidth=1))
    d.add(Rect(1*mm, 1*mm, (size-2)*mm, (size-2)*mm, fillColor=None, strokeColor=GOLD, strokeWidth=0.5))
    return d


def generate_professional_transaction_pdf(tx: dict, emp: dict = None, brand: dict = None) -> tuple:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=M, bottomMargin=M, leftMargin=M, rightMargin=M)
    els = []
    
    # Data
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
    
    emp_ar = data.get('employee_name_ar', emp.get('full_name_ar','') if emp else '')
    emp_en = data.get('employee_name', emp.get('full_name','') if emp else '')
    
    types = {'leave_request':('طلب إجازة','Leave Request'), 'tangible_custody':('عهدة عينية','In-Kind Custody'), 'salary_advance':('سلفة راتب','Salary Advance'), 'settlement':('مخالصة','Settlement')}
    typ_ar, typ_en = types.get(typ, (typ, typ))
    
    stats = {'executed':('منفذة','Executed',GREEN), 'pending':('معلقة','Pending',GRAY), 'stas':('STAS','Pending STAS',GOLD), 'ceo':('CEO','Pending CEO',GOLD)}
    st_ar, st_en, st_c = stats.get(status, (status, status, GRAY))
    
    # Styles
    s = {
        'h_ar': ParagraphStyle('har', fontName=ARB, fontSize=9, alignment=TA_RIGHT, textColor=NAVY),
        'h_en': ParagraphStyle('hen', fontName='Helvetica-Bold', fontSize=7, alignment=TA_LEFT, textColor=NAVY),
        'h_sm': ParagraphStyle('hsm', fontName='Helvetica', fontSize=6, alignment=TA_CENTER, textColor=GRAY),
        't': ParagraphStyle('t', fontName=ARB, fontSize=10, alignment=TA_CENTER, textColor=NAVY),
        'ref': ParagraphStyle('ref', fontName='Helvetica-Bold', fontSize=8, alignment=TA_CENTER, textColor=GOLD),
        'la': ParagraphStyle('la', fontName=AR, fontSize=7, alignment=TA_RIGHT, textColor=GRAY),
        'va': ParagraphStyle('va', fontName=ARB, fontSize=7, alignment=TA_RIGHT, textColor=DARK),
        'le': ParagraphStyle('le', fontName='Helvetica', fontSize=6, alignment=TA_LEFT, textColor=GRAY),
        've': ParagraphStyle('ve', fontName='Helvetica-Bold', fontSize=6, alignment=TA_LEFT, textColor=DARK),
        'sec': ParagraphStyle('sec', fontName=ARB, fontSize=8, alignment=TA_CENTER, textColor=NAVY),
        'sh': ParagraphStyle('sh', fontName=ARB, fontSize=6, alignment=TA_CENTER, textColor=WHITE),
        'sn': ParagraphStyle('sn', fontName=AR, fontSize=5, alignment=TA_CENTER, textColor=DARK),
        'sd': ParagraphStyle('sd', fontName='Helvetica', fontSize=5, alignment=TA_CENTER, textColor=GRAY),
        'ok': ParagraphStyle('ok', fontName=ARB, fontSize=5, alignment=TA_CENTER, textColor=GREEN),
        'cp': ParagraphStyle('cp', fontName='Helvetica', fontSize=5, alignment=TA_CENTER, textColor=DARK),
        'cpa': ParagraphStyle('cpa', fontName=ARB, fontSize=6, alignment=TA_CENTER, textColor=NAVY),
    }
    
    # ═══════════════════════════════════════════════════════════════
    # HEADER: لوجو (يمين) | اسم الشركة (وسط) | فارغ (يسار)
    # ═══════════════════════════════════════════════════════════════
    third = CW / 3
    
    hdr_r = Table([[Paragraph(ar(co_ar), s['h_ar'])], [Paragraph(co_en, s['h_en'])]], colWidths=[third])
    hdr_r.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'RIGHT'), ('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    
    hdr_c = Table([[logo()]], colWidths=[third])
    hdr_c.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'), ('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    
    hdr_l = Table([[Paragraph("KSA | 5110004935", s['h_sm'])]], colWidths=[third])
    hdr_l.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'LEFT'), ('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    
    header = Table([[hdr_l, hdr_c, hdr_r]], colWidths=[third, third, third])
    header.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 1, NAVY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    els.append(header)
    els.append(Spacer(1, 2*mm))
    
    # ═══════════════════════════════════════════════════════════════
    # TITLE
    # ═══════════════════════════════════════════════════════════════
    els.append(Paragraph(ar(typ_ar) + " | " + typ_en, s['t']))
    els.append(Paragraph(ref + " | " + integrity, s['ref']))
    els.append(Spacer(1, 2*mm))
    
    # ═══════════════════════════════════════════════════════════════
    # INFO: ثلثين (معلومات) | ثلث (حالة + QR)
    # ═══════════════════════════════════════════════════════════════
    two_third = CW * 0.65
    one_third = CW * 0.35
    
    # معلومات - جدول أفقي: English Left | Arabic Right
    info = []
    info.append([Paragraph(emp_en, s['ve']), Paragraph("Employee", s['le']), Paragraph(ar("الموظف"), s['la']), Paragraph(ar(emp_ar), s['va'])])
    
    if typ == 'leave_request':
        lt = data.get('leave_type', '')
        lt_m = {'annual':('سنوية','Annual'), 'sick':('مرضية','Sick'), 'emergency':('طارئة','Emergency')}
        lt_ar, lt_en = lt_m.get(lt, (lt, lt))
        info.append([Paragraph(lt_en, s['ve']), Paragraph("Type", s['le']), Paragraph(ar("النوع"), s['la']), Paragraph(ar(lt_ar), s['va'])])
        info.append([Paragraph(data.get('start_date','-').replace('-','.'), s['ve']), Paragraph("From", s['le']), Paragraph(ar("من"), s['la']), Paragraph(data.get('start_date','-').replace('-','.'), s['va'])])
        info.append([Paragraph(data.get('end_date','-').replace('-','.'), s['ve']), Paragraph("To", s['le']), Paragraph(ar("إلى"), s['la']), Paragraph(data.get('end_date','-').replace('-','.'), s['va'])])
        info.append([Paragraph(str(data.get('working_days','-')), s['ve']), Paragraph("Days", s['le']), Paragraph(ar("الأيام"), s['la']), Paragraph(str(data.get('working_days','-')), s['va'])])
    
    elif typ == 'tangible_custody':
        info.append([Paragraph(data.get('item_name','-'), s['ve']), Paragraph("Item", s['le']), Paragraph(ar("العنصر"), s['la']), Paragraph(ar(data.get('item_name_ar',data.get('item_name','-'))), s['va'])])
        info.append([Paragraph(f"{data.get('estimated_value',0):,.0f}", s['ve']), Paragraph("Value", s['le']), Paragraph(ar("القيمة"), s['la']), Paragraph(f"{data.get('estimated_value',0):,.0f}", s['va'])])
    
    elif typ == 'salary_advance':
        info.append([Paragraph(f"{data.get('amount',0):,.0f}", s['ve']), Paragraph("Amount", s['le']), Paragraph(ar("المبلغ"), s['la']), Paragraph(f"{data.get('amount',0):,.0f}", s['va'])])
    
    info.append([Paragraph(dt(created), s['ve']), Paragraph("Date", s['le']), Paragraph(ar("التاريخ"), s['la']), Paragraph(dt(created), s['va'])])
    
    iw = two_third / 4
    info_tbl = Table(info, colWidths=[iw, iw, iw, iw])
    info_tbl.setStyle(TableStyle([
        ('ALIGN', (0,0), (1,-1), 'LEFT'),
        ('ALIGN', (2,0), (3,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, LIGHT),
        ('BACKGROUND', (1,0), (2,-1), LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
    ]))
    
    # حالة + QR
    vqr = qr(f"V-{ref}", 15)
    status_tbl = Table([
        [Paragraph(ar(st_ar), ParagraphStyle('st', fontName=ARB, fontSize=9, alignment=TA_CENTER, textColor=st_c))],
        [Paragraph(st_en, ParagraphStyle('ste', fontName='Helvetica-Bold', fontSize=7, alignment=TA_CENTER, textColor=st_c))],
        [Spacer(1, 1*mm)],
        [vqr if vqr else Paragraph("QR", s['cp'])],
        [Paragraph("Verify", s['cp'])],
    ], colWidths=[one_third - 5*mm])
    status_tbl.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOX', (0,0), (-1,-1), 1, NAVY),
        ('BACKGROUND', (0,0), (-1,-1), LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    
    main = Table([[info_tbl, status_tbl]], colWidths=[two_third, one_third])
    main.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    els.append(main)
    els.append(Spacer(1, 3*mm))
    
    # ═══════════════════════════════════════════════════════════════
    # SIGNATURES: جدول أفقي منظم
    # ═══════════════════════════════════════════════════════════════
    els.append(Paragraph(ar("التوقيعات") + " | Signatures", s['sec']))
    els.append(Spacer(1, 1*mm))
    
    signed = {a.get('stage'): a.get('timestamp','') for a in chain}
    
    # التسلسل: موظف → HR → CEO → STAS
    sigs = [
        ('creator', ar('المنشئ'), 'Creator', emp_ar, emp_en, True, created),
        ('hr', 'HR', 'HR', 'سلطان', 'Sultan', 'hr' in signed or 'sultan' in signed, signed.get('hr', signed.get('sultan', ''))),
        ('ceo', 'CEO', 'CEO', 'محمد', 'Mohammed', 'ceo' in signed, signed.get('ceo', '')),
        ('stas', 'STAS', 'STAS', 'STAS', 'STAS', status == 'executed', signed.get('stas', tx.get('executed_at', ''))),
    ]
    
    n = len(sigs)
    sw = CW / n
    
    # Header
    hr = [Paragraph(f"{x[1]}\n{x[2]}", s['sh']) for x in sigs]
    # QR (only if signed)
    qr_r = [qr(f"S-{x[2]}-{ref}", 7) if x[5] else Paragraph("—", s['sd']) for x in sigs]
    # Name
    nr = [Paragraph(ar(x[3]) + "\n" + x[4], s['sn']) if x[5] else Paragraph("—", s['sd']) for x in sigs]
    # Date
    dr = [Paragraph(dt(x[6]), s['sd']) if x[5] and x[6] else Paragraph("—", s['sd']) for x in sigs]
    # Status
    sr = [Paragraph("✓", s['ok']) if x[5] else Paragraph("", s['sd']) for x in sigs]
    
    sig_tbl = Table([hr, qr_r, nr, dr, sr], colWidths=[sw]*n)
    sig_tbl.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('BOX', (0,0), (-1,-1), 1, NAVY),
        ('INNERGRID', (0,1), (-1,-1), 0.5, LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    els.append(sig_tbl)
    els.append(Spacer(1, 3*mm))
    
    # ═══════════════════════════════════════════════════════════════
    # TEAR-OFF
    # ═══════════════════════════════════════════════════════════════
    els.append(Paragraph("─ ─ ─ ─ ─ ─ ✂ " + ar("قص هنا") + " | Cut Here ✂ ─ ─ ─ ─ ─ ─", ParagraphStyle('tear', fontName='Helvetica', fontSize=6, alignment=TA_CENTER, textColor=GRAY)))
    els.append(Spacer(1, 2*mm))
    
    # ═══════════════════════════════════════════════════════════════
    # COUPON
    # ═══════════════════════════════════════════════════════════════
    stas_qr = qr(f"STAS-{ref}", 10) if status == 'executed' else Paragraph("—", s['cp'])
    
    cp_l = Table([[stas_qr], [Paragraph("STAS", s['cp'])]], colWidths=[15*mm])
    cp_l.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    
    cp_m = Table([
        [Paragraph(ar(co_ar), s['cpa'])],
        [Paragraph(f"{typ_en} | {ref}", s['cp'])],
        [Paragraph(ar(emp_ar) + " | " + emp_en, s['cp'])],
        [Paragraph(ar("✓ صحيحة") if status == 'executed' else ar("بانتظار"), ParagraphStyle('v', fontName=ARB, fontSize=6, alignment=TA_CENTER, textColor=GREEN if status == 'executed' else GRAY))],
    ], colWidths=[CW - 40*mm])
    cp_m.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    
    verify = qr(f"V-{ref}", 10)
    cp_r = Table([[verify], [Paragraph("Verify", s['cp'])]], colWidths=[15*mm])
    cp_r.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    
    coupon = Table([[cp_l, cp_m, cp_r]], colWidths=[20*mm, CW - 40*mm, 20*mm])
    coupon.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOX', (0,0), (-1,-1), 1, GOLD),
        ('BACKGROUND', (0,0), (-1,-1), LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    els.append(coupon)
    
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
