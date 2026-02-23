"""
PDF احترافي - صفحة واحدة A4
ألوان: أزرق داكن + أسود + رصاصي فقط (لا ذهبي)
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
M = 10*mm  # هوامش أصغر
CW = W - 2*M

# ألوان فقط: أزرق داكن + أسود + رصاصي (لا ذهبي أبداً)
NAVY = colors.Color(0.118, 0.227, 0.373)  # #1E3A5F
BLACK = colors.Color(0.15, 0.15, 0.15)
DARK_GRAY = colors.Color(0.35, 0.35, 0.35)
GRAY = colors.Color(0.55, 0.55, 0.55)
LIGHT_GRAY = colors.Color(0.94, 0.94, 0.95)
WHITE = colors.white

FD = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')
AR, ARB = 'Helvetica', 'Helvetica-Bold'
try:
    # استخدام NotoSansArabic لدعم أفضل للحروف اللاتينية والعربية
    pdfmetrics.registerFont(TTFont('Ar', os.path.join(FD, 'NotoSansArabic-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('ArB', os.path.join(FD, 'NotoSansArabic-Bold.ttf')))
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

def make_qr(data, sz=6):
    """QR code بحجم صغير ومتناسب"""
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

def make_logo(logo_data, sz=10):
    """شعار بحجم متناسب"""
    if logo_data:
        try:
            if ',' in logo_data:
                logo_data = logo_data.split(',')[1]
            img_bytes = base64.b64decode(logo_data)
            buf = io.BytesIO(img_bytes)
            return RLImage(buf, width=sz*mm, height=sz*mm)
        except: pass
    return None


def generate_professional_transaction_pdf(tx: dict, emp: dict = None, brand: dict = None, supervisor: dict = None) -> tuple:
    """توليد PDF احترافي متوازن ومتناسب"""
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
    
    # بيانات المشرف
    sup_ar = supervisor.get('full_name_ar', 'المشرف') if supervisor else 'المشرف'
    sup_en = supervisor.get('full_name', 'Supervisor') if supervisor else 'Supervisor'
    
    types = {'leave_request':('طلب إجازة','Leave Request'), 'tangible_custody':('عهدة عينية','In-Kind Custody'), 'salary_advance':('سلفة راتب','Salary Advance'), 'settlement':('مخالصة','Settlement')}
    typ_ar, typ_en = types.get(typ, (typ, typ))
    
    stats = {'executed':('منفذة','Executed'), 'pending':('معلقة','Pending'), 'stas':('STAS','Pending'), 'ceo':('CEO','Pending')}
    st_ar, st_en = stats.get(status, (status, status))
    
    # ═══════════════════════════════════════════════════════════════════
    # Styles - أحجام صغيرة ومتناسبة (لا تضخيم)
    # ═══════════════════════════════════════════════════════════════════
    s_co_ar = ParagraphStyle('co_ar', fontName=ARB, fontSize=8, alignment=TA_CENTER, textColor=NAVY, leading=10)
    s_co_en = ParagraphStyle('co_en', fontName='Helvetica-Bold', fontSize=6, alignment=TA_CENTER, textColor=DARK_GRAY, leading=8)
    s_info = ParagraphStyle('info', fontName=AR, fontSize=5, alignment=TA_CENTER, textColor=GRAY, leading=6)
    
    s_title = ParagraphStyle('title', fontName=ARB, fontSize=8, alignment=TA_CENTER, textColor=NAVY, leading=10)
    s_ref = ParagraphStyle('ref', fontName='Helvetica-Bold', fontSize=6, alignment=TA_CENTER, textColor=DARK_GRAY)
    
    s_hdr = ParagraphStyle('hdr', fontName=AR, fontSize=5, alignment=TA_CENTER, textColor=WHITE, leading=7)
    s_val = ParagraphStyle('val', fontName=AR, fontSize=5, alignment=TA_CENTER, textColor=BLACK, leading=7)
    s_val_en = ParagraphStyle('val_en', fontName='Helvetica', fontSize=5, alignment=TA_CENTER, textColor=DARK_GRAY, leading=6)
    
    s_sec = ParagraphStyle('sec', fontName=ARB, fontSize=6, alignment=TA_CENTER, textColor=NAVY, leading=8)
    s_role = ParagraphStyle('role', fontName=AR, fontSize=4.5, alignment=TA_CENTER, textColor=WHITE, leading=6)
    s_name = ParagraphStyle('name', fontName=AR, fontSize=4.5, alignment=TA_CENTER, textColor=BLACK, leading=6)
    s_date = ParagraphStyle('date', fontName=AR, fontSize=4, alignment=TA_CENTER, textColor=GRAY, leading=5)
    s_empty = ParagraphStyle('empty', fontName=AR, fontSize=4, alignment=TA_CENTER, textColor=LIGHT_GRAY, leading=5)
    
    s_tear = ParagraphStyle('tear', fontName=AR, fontSize=5, alignment=TA_CENTER, textColor=GRAY)
    s_coupon = ParagraphStyle('coupon', fontName=AR, fontSize=5, alignment=TA_CENTER, textColor=NAVY, leading=7)
    
    # ═══════════════════════════════════════════════════════════════════
    # 1. الترويسة - متوازنة ومركزة
    # ═══════════════════════════════════════════════════════════════════
    logo_img = make_logo(logo_data, 10)
    
    header_rows = []
    if logo_img:
        header_rows.append([logo_img])
    header_rows.append([Paragraph(ar(co_ar), s_co_ar)])
    header_rows.append([Paragraph(co_en, s_co_en)])
    header_rows.append([Paragraph("Kingdom of Saudi Arabia | CR: 1010463476", s_info)])
    
    header = Table(header_rows, colWidths=[CW])
    header.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,-1), (-1,-1), 0.5, NAVY),
        ('BOTTOMPADDING', (0,-1), (-1,-1), 2*mm),
    ]))
    els.append(header)
    els.append(Spacer(1, 2*mm))
    
    # ═══════════════════════════════════════════════════════════════════
    # 2. عنوان المعاملة - في المنتصف تماماً
    # ═══════════════════════════════════════════════════════════════════
    title_tbl = Table([
        [Paragraph(ar(typ_ar), s_title)],
        [Paragraph(typ_en, s_ref)],
        [Paragraph(ref + " | " + integrity, s_info)],
    ], colWidths=[CW])
    title_tbl.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ]))
    els.append(title_tbl)
    els.append(Spacer(1, 2*mm))
    
    # ═══════════════════════════════════════════════════════════════════
    # 3. معلومات المعاملة - جدول أفقي متوازن (عربي فوق إنجليزي)
    # ═══════════════════════════════════════════════════════════════════
    col4 = CW / 4
    
    # صف العناوين
    headers1 = [
        Paragraph(ar("الحالة"), s_hdr),
        Paragraph(ar("التاريخ"), s_hdr),
        Paragraph(ar("الموظف"), s_hdr),
        Paragraph(ar("المعرف"), s_hdr),
    ]
    
    # صف القيم العربية
    vals_ar = [
        Paragraph(ar(st_ar), s_val),
        Paragraph(dt(created).split(' | ')[0], s_val),
        Paragraph(ar(emp_ar), s_val),
        Paragraph(integrity[:12], s_val),
    ]
    
    # صف القيم الإنجليزية
    vals_en = [
        Paragraph(st_en, s_val_en),
        Paragraph(dt(created).split(' | ')[1] if ' | ' in dt(created) else '', s_val_en),
        Paragraph(emp_en, s_val_en),
        Paragraph(integrity[12:] if len(integrity) > 12 else '', s_val_en),
    ]
    
    info_tbl = Table([headers1, vals_ar, vals_en], colWidths=[col4]*4)
    info_tbl.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('BOX', (0,0), (-1,-1), 0.5, NAVY),
        ('INNERGRID', (0,0), (-1,-1), 0.25, LIGHT_GRAY),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    els.append(info_tbl)
    els.append(Spacer(1, 1.5*mm))
    
    # ═══════════════════════════════════════════════════════════════════
    # تفاصيل حسب نوع المعاملة
    # ═══════════════════════════════════════════════════════════════════
    if typ == 'leave_request':
        lt = data.get('leave_type', '')
        lt_m = {'annual':('سنوية','Annual'), 'sick':('مرضية','Sick'), 'emergency':('طارئة','Emergency')}
        lt_ar, lt_en = lt_m.get(lt, (lt, lt))
        
        h2 = [Paragraph(ar("النوع"), s_hdr), Paragraph(ar("من"), s_hdr), Paragraph(ar("إلى"), s_hdr), Paragraph(ar("الأيام"), s_hdr)]
        v2_ar = [Paragraph(ar(lt_ar), s_val), Paragraph(data.get('start_date','-'), s_val), Paragraph(data.get('end_date','-'), s_val), Paragraph(str(data.get('working_days','-')), s_val)]
        v2_en = [Paragraph(lt_en, s_val_en), Paragraph("From", s_val_en), Paragraph("To", s_val_en), Paragraph("Days", s_val_en)]
        
        detail_tbl = Table([h2, v2_ar, v2_en], colWidths=[col4]*4)
        detail_tbl.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,0), (-1,0), DARK_GRAY),
            ('BOX', (0,0), (-1,-1), 0.5, DARK_GRAY),
            ('INNERGRID', (0,0), (-1,-1), 0.25, LIGHT_GRAY),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        els.append(detail_tbl)
    
    elif typ == 'tangible_custody':
        h2 = [Paragraph(ar("العنصر"), s_hdr), Paragraph(ar("الرقم التسلسلي"), s_hdr), Paragraph(ar("القيمة"), s_hdr), Paragraph("", s_hdr)]
        v2_ar = [Paragraph(ar(data.get('item_name_ar', data.get('item_name','-'))), s_val), Paragraph(data.get('serial_number','-'), s_val), Paragraph(f"{data.get('estimated_value',0):,.0f}", s_val), Paragraph("SAR", s_val)]
        v2_en = [Paragraph(data.get('item_name','-'), s_val_en), Paragraph("Serial", s_val_en), Paragraph("Value", s_val_en), Paragraph("", s_val_en)]
        
        detail_tbl = Table([h2, v2_ar, v2_en], colWidths=[col4]*4)
        detail_tbl.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,0), (-1,0), DARK_GRAY),
            ('BOX', (0,0), (-1,-1), 0.5, DARK_GRAY),
            ('INNERGRID', (0,0), (-1,-1), 0.25, LIGHT_GRAY),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        els.append(detail_tbl)
    
    elif typ == 'salary_advance':
        h2 = [Paragraph(ar("المبلغ"), s_hdr), Paragraph(ar("السبب"), s_hdr), Paragraph("", s_hdr), Paragraph("", s_hdr)]
        v2_ar = [Paragraph(f"{data.get('amount',0):,.0f} SAR", s_val), Paragraph(ar(data.get('reason','-')[:30]), s_val), Paragraph("", s_val), Paragraph("", s_val)]
        
        detail_tbl = Table([h2, v2_ar], colWidths=[col4]*4)
        detail_tbl.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,0), (-1,0), DARK_GRAY),
            ('BOX', (0,0), (-1,-1), 0.5, DARK_GRAY),
            ('INNERGRID', (0,0), (-1,-1), 0.25, LIGHT_GRAY),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        els.append(detail_tbl)
    
    els.append(Spacer(1, 2*mm))
    
    # ═══════════════════════════════════════════════════════════════════
    # 4. جدول التوقيعات - تسلسلي حسب مراحل المعاملة
    # يظهر فقط الأدوار التي وصلت لها المعاملة
    # ═══════════════════════════════════════════════════════════════════
    els.append(Paragraph(ar("التوقيعات") + " | Signatures", s_sec))
    els.append(Spacer(1, 1*mm))
    
    # بناء قائمة الموقعين الفعليين من approval_chain
    signed_stages = {}
    for approval in chain:
        stage = approval.get('stage', '')
        ts = approval.get('timestamp', '')
        # جرب أكثر من حقل للاسم
        signer = approval.get('approver_name', '') or approval.get('signer_name', '') or approval.get('approver_name_en', '')
        if stage and ts:
            signed_stages[stage] = {'timestamp': ts, 'signer': signer}
    
    # التعامل مع المراحل البديلة (ops = supervisor)
    if 'ops' in signed_stages and 'supervisor' not in signed_stages:
        signed_stages['supervisor'] = signed_stages['ops']
    # التعامل مع أسماء المراحل البديلة
    if 'sultan' in signed_stages and 'hr' not in signed_stages:
        signed_stages['hr'] = signed_stages['sultan']
    if 'mohammed' in signed_stages and 'ceo' not in signed_stages:
        signed_stages['ceo'] = signed_stages['mohammed']
    
    # تحديد المراحل التي وصلت لها المعاملة بناءً على الحالة
    # الترتيب: pending -> supervisor -> hr -> ceo -> stas -> executed
    current_status = status.lower()
    
    # تحديد عدد الأعمدة بناءً على الحالة الحالية
    stage_order = ['employee', 'supervisor', 'hr', 'ceo', 'stas']
    status_to_max_stage = {
        'pending': 1,      # فقط الموظف
        'supervisor': 2,   # موظف + مشرف
        'hr': 3,           # موظف + مشرف + المدير الإداري
        'sultan': 3,       # نفس hr
        'ceo': 4,          # موظف + مشرف + المدير الإداري + المدير التنفيذي
        'mohammed': 4,     # نفس ceo
        'stas': 5,         # الكل
        'executed': 5      # الكل
    }
    max_stages = status_to_max_stage.get(current_status, 5)
    
    # إذا المعاملة منفذة، نعرض كل المراحل
    if current_status == 'executed':
        max_stages = 5
    
    # الأدوار مع المسميات الرسمية
    # (stage_key, ar_role_title, en_role_title, ar_name, en_name)
    all_roles = [
        ('employee', 'الموظف', 'Employee', emp_ar, emp_en),
        ('supervisor', 'المشرف', 'Supervisor', sup_ar, sup_en),
        ('hr', 'المدير الإداري', 'Admin. Manager', 'أ.سلطان', 'Sultan'),
        ('ceo', 'المدير التنفيذي', 'Exec. Manager', 'م.محمد الثنيان', 'M. Al-Thunayan'),
        ('stas', 'STAS', 'STAS', 'STAS', 'STAS'),
    ]
    
    # فقط الأدوار التي وصلت لها المعاملة
    roles = all_roles[:max_stages]
    num_cols = len(roles)
    col_width = CW / num_cols
    
    # صف العناوين (الأدوار)
    role_row = []
    for r in roles:
        role_row.append(Paragraph(ar(r[1]) + "\n" + r[2], s_role))
    
    # صف QR - يظهر فقط للموقعين الفعليين
    qr_row = []
    for r in roles:
        stage_key = r[0]
        if stage_key == 'employee':
            # الموظف دائماً وقع (منشئ المعاملة)
            qr_row.append(make_qr(f"SIG-{r[2]}-{ref}", 6))
        elif stage_key in signed_stages:
            qr_row.append(make_qr(f"SIG-{r[2]}-{ref}", 6))
        else:
            qr_row.append(Paragraph("—", s_empty))
    
    # صف الأسماء - يظهر فقط للموقعين الفعليين
    name_row = []
    for r in roles:
        stage_key = r[0]
        if stage_key == 'employee':
            name_row.append(Paragraph(ar(r[3]) if r[3] else "—", s_name))
        elif stage_key in signed_stages:
            # استخدام اسم الموقع الفعلي إذا متوفر، وإلا استخدم الاسم الافتراضي
            signer_info = signed_stages[stage_key]
            actual_name = r[3]  # الاسم الافتراضي
            if isinstance(signer_info, dict) and signer_info.get('signer'):
                actual_name = signer_info.get('signer')
            # تحديد الخط بناءً على نوع النص (عربي أم إنجليزي)
            if actual_name and any('\u0600' <= c <= '\u06FF' for c in actual_name):
                # نص عربي
                name_row.append(Paragraph(ar(actual_name), s_name))
            else:
                # نص إنجليزي - استخدم خط مختلف
                s_name_en = ParagraphStyle('name_en', fontName='Helvetica', fontSize=4.5, alignment=TA_CENTER, textColor=BLACK, leading=6)
                name_row.append(Paragraph(actual_name if actual_name else "—", s_name_en))
        else:
            name_row.append(Paragraph("—", s_empty))
    
    # صف التواريخ - يظهر فقط للموقعين الفعليين
    date_row = []
    for r in roles:
        stage_key = r[0]
        if stage_key == 'employee':
            date_row.append(Paragraph(dt(created).split(' | ')[0], s_date))
        elif stage_key in signed_stages:
            signer_info = signed_stages[stage_key]
            ts = signer_info.get('timestamp', '') if isinstance(signer_info, dict) else signer_info
            date_row.append(Paragraph(dt(ts).split(' | ')[0], s_date))
        else:
            date_row.append(Paragraph("—", s_empty))
    
    sig_tbl = Table([role_row, qr_row, name_row, date_row], colWidths=[col_width]*num_cols, rowHeights=[6*mm, 8*mm, 5*mm, 4*mm])
    sig_tbl.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('BOX', (0,0), (-1,-1), 0.5, NAVY),
        ('INNERGRID', (0,0), (-1,-1), 0.25, LIGHT_GRAY),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ]))
    els.append(sig_tbl)
    els.append(Spacer(1, 2*mm))
    
    # ═══════════════════════════════════════════════════════════════════
    # 5. QR للمعاملة (فوق خط القص) - حجم صغير
    # ═══════════════════════════════════════════════════════════════════
    tx_qr = make_qr(f"TX-{ref}-{integrity}", 10)
    
    qr_info = Table([
        [Paragraph(ar("رمز التحقق") + " | Verification", s_info)],
        [Paragraph(integrity, s_val_en)],
    ], colWidths=[CW - 15*mm])
    
    qr_above = Table([
        [tx_qr if tx_qr else '', qr_info],
    ], colWidths=[15*mm, CW - 15*mm])
    qr_above.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,-1), 'CENTER'),
        ('ALIGN', (1,0), (1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    els.append(qr_above)
    els.append(Spacer(1, 2*mm))
    
    # ═══════════════════════════════════════════════════════════════════
    # 6. خط القص
    # ═══════════════════════════════════════════════════════════════════
    els.append(Paragraph("─ ─ ─ ─ ─ ─ ─ ─ ✂ " + ar("قص هنا") + " ✂ ─ ─ ─ ─ ─ ─ ─ ─", s_tear))
    els.append(Spacer(1, 2*mm))
    
    # ═══════════════════════════════════════════════════════════════════
    # 7. كوبون (تحت خط القص) - مختصر
    # ═══════════════════════════════════════════════════════════════════
    file_qr = make_qr(f"FILE-{ref}-{integrity}", 10)
    
    coupon_info = Table([
        [Paragraph(ar(co_ar), s_coupon)],
        [Paragraph(f"{typ_en} | {ref}", s_info)],
        [Paragraph(f"{ar(emp_ar)} | {emp_en}", s_info)],
        [Paragraph(ar("صالحة") + " | Valid" if status == 'executed' else ar("قيد المعالجة") + " | Processing", s_date)],
    ], colWidths=[CW - 15*mm])
    
    coupon_tbl = Table([
        [file_qr if file_qr else '', coupon_info],
    ], colWidths=[15*mm, CW - 15*mm])
    coupon_tbl.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,-1), 'CENTER'),
        ('ALIGN', (1,0), (1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOX', (0,0), (-1,-1), 0.5, NAVY),
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_GRAY),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    els.append(coupon_tbl)
    
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
