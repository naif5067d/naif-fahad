"""
Settlement PDF Generator - وثيقة المخالصة
============================================================
- صفحة واحدة A4 فقط
- Hybrid bilingual: يمين عربي، يسار إنجليزي
- QR للتحقق من STAS فقط
- توقيع يدوي: سلطان + محمد + الموظف + محاسب الصندوق
============================================================
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display
import io
import qrcode
from datetime import datetime, timezone
import os
import base64

# ألوان الشركة
NAVY = colors.HexColor('#1E3A5F')
GOLD = colors.HexColor('#BF9E59')
LIGHT_BG = colors.HexColor('#F8FAFC')
BORDER = colors.HexColor('#E2E8F0')
GREEN = colors.HexColor('#16A34A')

# أبعاد
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 8 * mm
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)

# تسجيل الخطوط
FONT_DIR = "/app/backend/fonts"
ARABIC_FONT = 'Helvetica'
ARABIC_FONT_BOLD = 'Helvetica-Bold'

def _register_fonts():
    """تسجيل الخطوط العربية"""
    global ARABIC_FONT, ARABIC_FONT_BOLD
    
    registered = pdfmetrics.getRegisteredFontNames()
    if 'Amiri' in registered:
        ARABIC_FONT = 'Amiri'
        ARABIC_FONT_BOLD = 'Amiri'
        return True
    
    amiri_path = os.path.join(FONT_DIR, 'Amiri-Regular.ttf')
    if os.path.exists(amiri_path):
        try:
            file_size = os.path.getsize(amiri_path)
            if file_size > 50000:
                pdfmetrics.registerFont(TTFont('Amiri', amiri_path))
                ARABIC_FONT = 'Amiri'
                ARABIC_FONT_BOLD = 'Amiri'
                return True
        except Exception as e:
            print(f"[PDF] Amiri error: {e}")
    
    return False

_register_fonts()


def reshape_arabic(text):
    """تحويل النص العربي للعرض الصحيح"""
    if not text:
        return ''
    try:
        text_str = str(text)
        reshaped = arabic_reshaper.reshape(text_str)
        return get_display(reshaped)
    except Exception:
        return str(text)


def create_qr_image(data, size=18):
    """إنشاء QR Code"""
    try:
        qr = qrcode.QRCode(version=1, box_size=2, border=1)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#1E3A5F", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return Image(buffer, width=size*mm, height=size*mm)
    except Exception:
        return None


def load_logo_image(branding):
    """تحميل شعار الشركة"""
    if not branding:
        return None
    
    logo_data = None
    if isinstance(branding, dict):
        logo_data = branding.get('logo_data') or branding.get('logo_url')
        if not logo_data and 'branding' in branding:
            nested = branding.get('branding', {})
            if isinstance(nested, dict):
                logo_data = nested.get('logo_data') or nested.get('logo_url')
    
    if not logo_data:
        return None
    
    try:
        if isinstance(logo_data, str) and ',' in logo_data:
            logo_data = logo_data.split(',')[1]
        logo_bytes = base64.b64decode(logo_data)
        logo_buffer = io.BytesIO(logo_bytes)
        return Image(logo_buffer, width=15*mm, height=10*mm)
    except Exception:
        return None


def generate_settlement_pdf(settlement: dict, branding: dict = None) -> bytes:
    """توليد PDF المخالصة - صفحة واحدة A4"""
    
    _register_fonts()
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=6*mm,
        bottomMargin=6*mm
    )
    
    elements = []
    snapshot = settlement.get("snapshot", {})
    employee = snapshot.get("employee", {})
    contract = snapshot.get("contract", {})
    service = snapshot.get("service", {})
    wages = snapshot.get("wages", {})
    eos = snapshot.get("eos", {})
    leave = snapshot.get("leave", {})
    totals = snapshot.get("totals", {})
    partial_month = snapshot.get("partial_month_salary", {})
    custody = snapshot.get("custody_balance", {})
    
    # === STYLES (خطوط صغيرة جداً لضمان صفحة واحدة) ===
    style_ar = ParagraphStyle('ar', fontName=ARABIC_FONT, fontSize=6, alignment=TA_RIGHT, leading=7)
    style_ar_bold = ParagraphStyle('ar_bold', fontName=ARABIC_FONT_BOLD, fontSize=6, alignment=TA_RIGHT, leading=7)
    style_en = ParagraphStyle('en', fontName='Helvetica', fontSize=6, alignment=TA_LEFT, leading=7)
    style_en_bold = ParagraphStyle('en_bold', fontName='Helvetica-Bold', fontSize=6, alignment=TA_LEFT, leading=7)
    style_header_ar = ParagraphStyle('header_ar', fontName=ARABIC_FONT_BOLD, fontSize=7, alignment=TA_RIGHT, textColor=colors.white)
    style_header_en = ParagraphStyle('header_en', fontName='Helvetica-Bold', fontSize=7, alignment=TA_LEFT, textColor=colors.white)
    
    def ar(text): return Paragraph(reshape_arabic(str(text)), style_ar)
    def ar_b(text): return Paragraph(reshape_arabic(str(text)), style_ar_bold)
    def en(text): return Paragraph(str(text), style_en)
    def en_b(text): return Paragraph(str(text), style_en_bold)
    def h_ar(text): return Paragraph(reshape_arabic(str(text)), style_header_ar)
    def h_en(text): return Paragraph(str(text), style_header_en)
    
    col_w = CONTENT_WIDTH / 2
    
    # === 1. HEADER / الترويسة ===
    txn = settlement.get("transaction_number", "")
    issue_date = settlement.get("executed_at", "")[:10] if settlement.get("executed_at") else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    logo_img = load_logo_image(branding)
    
    if logo_img:
        header_data = [
            [en("Kingdom of Saudi Arabia"), logo_img, ar("المملكة العربية السعودية")],
            [en_b("Dar Al Code Engineering Consultancy"), '', ar_b("شركة دار الكود للاستشارات الهندسية")],
            [en("CR: 1010463476 | License: 5110004935"), '', ar("سجل: 1010463476 | ترخيص: 5110004935")],
        ]
        col_widths = [col_w - 10*mm, 20*mm, col_w - 10*mm]
    else:
        header_data = [
            [en("Kingdom of Saudi Arabia"), ar("المملكة العربية السعودية")],
            [en_b("Dar Al Code Engineering Consultancy"), ar_b("شركة دار الكود للاستشارات الهندسية")],
            [en("CR: 1010463476 | License: 5110004935"), ar("سجل: 1010463476 | ترخيص: 5110004935")],
        ]
        col_widths = [col_w, col_w]
    
    header_table = Table(header_data, colWidths=col_widths)
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, -1), (-1, -1), 1, NAVY),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 1.5*mm))
    
    # رقم المعاملة
    ref_data = [[en(f"Ref: {txn} | Date: {issue_date}"), ar(f"مرجع: {txn} | التاريخ: {issue_date}")]]
    ref_table = Table(ref_data, colWidths=[col_w, col_w])
    ref_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER),
    ]))
    elements.append(ref_table)
    elements.append(Spacer(1, 1.5*mm))
    
    # === 2. EMPLOYEE INFO / بيانات الموظف ===
    emp_header = [[h_en("Employee Information"), h_ar("بيانات الموظف")]]
    emp_header_t = Table(emp_header, colWidths=[col_w, col_w])
    emp_header_t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), NAVY), ('ALIGN', (0, 0), (0, 0), 'LEFT'), ('ALIGN', (1, 0), (1, 0), 'RIGHT')]))
    elements.append(emp_header_t)
    
    emp_name = employee.get("name_ar", "")
    emp_name_en = employee.get("name_en", "") or "Employee"  # اسم إنجليزي
    emp_code = employee.get("employee_number", "")
    national_id = employee.get("national_id", "") or employee.get("iqama_number", "")
    # المسمى والقسم من العقد أولاً ثم من الموظف
    job_title = contract.get("job_title", "") or employee.get("job_title", "")
    department = contract.get("department", "") or employee.get("department", "")
    bank_name = contract.get("bank_name", "")
    bank_iban = contract.get("bank_iban", "")
    hire_date = contract.get("start_date", "")
    last_day = contract.get("last_working_day", "")
    clearance_type = contract.get("termination_type_label", "")
    # نوع المخالصة بالإنجليزي
    clearance_type_en = contract.get("termination_type", "").replace("_", " ").title()
    
    service_years = service.get("years", 0)
    service_months = service.get("months", 0)
    service_days_count = service.get("days", 0)
    service_duration = f"{service_years} سنة و {service_months} شهر و {service_days_count} يوم"
    
    # جدول بيانات الموظف - 4 أعمدة (العمود الأول إنجليزي فقط)
    emp_data = [
        [en(emp_code), en("Name"), ar("الاسم"), ar(emp_name)],
        [en(emp_code), en("Employee ID"), ar("الرقم الوظيفي"), ar(emp_code)],
        [en(national_id), en("ID/Iqama"), ar("الهوية/الإقامة"), ar(national_id)],
        [en(job_title), en("Job Title"), ar("المسمى الوظيفي"), ar(job_title)],
        [en(department), en("Department"), ar("القسم"), ar(department)],
        [en(bank_name), en("Bank"), ar("البنك"), ar(bank_name)],
        [en(bank_iban), en("IBAN"), ar("الآيبان"), ar(bank_iban)],
        [en(hire_date), en("Hire Date"), ar("تاريخ التعيين"), ar(hire_date)],
        [en(last_day), en("Last Working Day"), ar("آخر يوم عمل"), ar(last_day)],
        [en(f"{service_years}y {service_months}m {service_days_count}d"), en("Service Period"), ar("مدة الخدمة"), ar(service_duration)],
        [en(clearance_type_en), en("Clearance Type"), ar("نوع المخالصة"), ar(clearance_type)],
    ]
    emp_table = Table(emp_data, colWidths=[col_w*0.35, col_w*0.65, col_w*0.65, col_w*0.35])
    emp_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (3, -1), 'RIGHT'),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, BORDER),
        ('BACKGROUND', (1, 0), (1, -1), LIGHT_BG),
        ('BACKGROUND', (2, 0), (2, -1), LIGHT_BG),
        ('TOPPADDING', (0, 0), (-1, -1), 0.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5),
    ]))
    elements.append(emp_table)
    elements.append(Spacer(1, 1.5*mm))
    
    # === 3. SALARY / الراتب ===
    sal_header = [[h_en("Salary Details"), h_ar("تفاصيل الراتب")]]
    sal_header_t = Table(sal_header, colWidths=[col_w, col_w])
    sal_header_t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), NAVY), ('ALIGN', (0, 0), (0, 0), 'LEFT'), ('ALIGN', (1, 0), (1, 0), 'RIGHT')]))
    elements.append(sal_header_t)
    
    basic = wages.get("basic", 0)
    housing = wages.get("housing", 0)
    transport = wages.get("transport", 0)
    nature = wages.get("nature_of_work", 0)
    last_wage = wages.get("last_wage", 0)
    
    sal_data = [
        [en(f"{basic:,.0f}"), en("Basic Salary"), ar("الراتب الأساسي"), ar(f"{basic:,.0f}")],
        [en(f"{housing:,.0f}"), en("Housing"), ar("بدل السكن"), ar(f"{housing:,.0f}")],
        [en(f"{transport:,.0f}"), en("Transport"), ar("بدل النقل"), ar(f"{transport:,.0f}")],
        [en(f"{nature:,.0f}"), en("Nature of Work"), ar("بدل طبيعة العمل"), ar(f"{nature:,.0f}")],
        [en_b(f"{last_wage:,.0f}"), en_b("Total Salary"), ar_b("إجمالي الراتب"), ar_b(f"{last_wage:,.0f}")],
    ]
    sal_table = Table(sal_data, colWidths=[col_w*0.3, col_w*0.7, col_w*0.7, col_w*0.3])
    sal_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (3, -1), 'RIGHT'),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, BORDER),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E8F5E9')),
        ('TOPPADDING', (0, 0), (-1, -1), 0.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5),
    ]))
    elements.append(sal_table)
    elements.append(Spacer(1, 1.5*mm))
    
    # === 4. ENTITLEMENTS / الاستحقاقات ===
    ent_header = [[h_en("Entitlements"), h_ar("الاستحقاقات")]]
    ent_header_t = Table(ent_header, colWidths=[col_w, col_w])
    ent_header_t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), NAVY), ('ALIGN', (0, 0), (0, 0), 'LEFT'), ('ALIGN', (1, 0), (1, 0), 'RIGHT')]))
    elements.append(ent_header_t)
    
    eos_amount = eos.get("final_amount", 0)
    leave_balance = leave.get("balance", 0)
    leave_comp = leave.get("compensation", 0)
    daily_wage = wages.get("daily_wage", 0)
    total_ent = totals.get("entitlements", {}).get("total", 0)
    partial_amount = partial_month.get("amount", 0)
    partial_days = partial_month.get("days", 0)
    
    eos_pct = eos.get('percentage', 100)
    
    ent_data = []
    
    # راتب خارج المسيرات
    if partial_amount > 0:
        ent_data.append([
            en(f"{partial_amount:,.0f}"), 
            en(f"Partial Month ({partial_days} days)"), 
            ar(f"راتب خارج المسيرات ({partial_days} يوم)"), 
            ar(f"{partial_amount:,.0f}")
        ])
    
    # بدل الإجازات
    leave_detail = f"({leave_balance:.1f} يوم × {daily_wage:,.0f})"
    leave_detail_en = f"({leave_balance:.1f} days × {daily_wage:,.0f})"
    ent_data.append([en(f"{leave_comp:,.0f}"), en(f"Leave {leave_detail_en}"), ar(f"بدل الإجازات {leave_detail}"), ar(f"{leave_comp:,.0f}")])
    
    # مكافأة نهاية الخدمة
    eos_detail = f"({service_years} سنة × {eos_pct}%)"
    eos_detail_en = f"({service_years}y × {eos_pct}%)"
    ent_data.append([en(f"{eos_amount:,.0f}"), en(f"End of Service {eos_detail_en}"), ar(f"مكافأة نهاية الخدمة {eos_detail}"), ar(f"{eos_amount:,.0f}")])
    
    # الإجمالي
    ent_data.append([en_b(f"{total_ent:,.0f}"), en_b("Total Entitlements"), ar_b("إجمالي الاستحقاقات"), ar_b(f"{total_ent:,.0f}")])
    
    ent_table = Table(ent_data, colWidths=[col_w*0.2, col_w*0.8, col_w*0.8, col_w*0.2])
    ent_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (3, -1), 'RIGHT'),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, BORDER),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E8F5E9')),
        ('TOPPADDING', (0, 0), (-1, -1), 0.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5),
    ]))
    elements.append(ent_table)
    elements.append(Spacer(1, 1.5*mm))
    
    # === 5. DEDUCTIONS / الاستقطاعات ===
    ded_header = [[h_en("Deductions"), h_ar("الاستقطاعات")]]
    ded_header_t = Table(ded_header, colWidths=[col_w, col_w])
    ded_header_t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), NAVY), ('ALIGN', (0, 0), (0, 0), 'LEFT'), ('ALIGN', (1, 0), (1, 0), 'RIGHT')]))
    elements.append(ded_header_t)
    
    deductions = totals.get("deductions", {})
    loans = deductions.get("loans", 0)
    other_ded = deductions.get("deductions", 0)
    custody_total = deductions.get("custody", 0) or custody.get("total", 0)
    total_ded = deductions.get("total", 0)
    
    ded_data = [
        [en(f"{loans:,.0f}"), en("Loans / Advances"), ar("السلف"), ar(f"{loans:,.0f}")],
        [en(f"{custody_total:,.0f}"), en("Petty Cash / Trust"), ar("رصيد العهد"), ar(f"{custody_total:,.0f}")],
        [en(f"{other_ded:,.0f}"), en("Other Deductions"), ar("خصومات أخرى"), ar(f"{other_ded:,.0f}")],
        [en_b(f"{total_ded:,.0f}"), en_b("Total Deductions"), ar_b("إجمالي الاستقطاعات"), ar_b(f"{total_ded:,.0f}")],
    ]
    ded_table = Table(ded_data, colWidths=[col_w*0.3, col_w*0.7, col_w*0.7, col_w*0.3])
    ded_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (3, -1), 'RIGHT'),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, BORDER),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FFEBEE')),
        ('TOPPADDING', (0, 0), (-1, -1), 0.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5),
    ]))
    elements.append(ded_table)
    elements.append(Spacer(1, 1.5*mm))
    
    # === 6. NET AMOUNT / الصافي ===
    net_amount = totals.get("net_amount", 0)
    net_words = totals.get("net_amount_words", "")
    
    # إذا لم يكن المبلغ كتابة موجوداً، نحسبه
    if not net_words:
        from utils.arabic_numbers import number_to_arabic
        net_words = number_to_arabic(net_amount)
    
    net_style = ParagraphStyle('net', fontName='Helvetica-Bold', fontSize=10, alignment=TA_CENTER, textColor=NAVY)
    net_style_ar = ParagraphStyle('net_ar', fontName=ARABIC_FONT_BOLD, fontSize=10, alignment=TA_CENTER, textColor=NAVY)
    
    net_data = [[
        Paragraph(f"SAR {net_amount:,.2f}", net_style),
        Paragraph(reshape_arabic(f"ريال {net_amount:,.2f}"), net_style_ar)
    ]]
    net_table = Table(net_data, colWidths=[col_w, col_w])
    net_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOX', (0, 0), (-1, -1), 2, NAVY),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E3F2FD')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(net_table)
    
    # المبلغ كتابةً
    words_style = ParagraphStyle('words', fontName=ARABIC_FONT, fontSize=6, alignment=TA_CENTER, textColor=NAVY)
    words_table = Table([[Paragraph(reshape_arabic(net_words), words_style)]], colWidths=[CONTENT_WIDTH])
    words_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER),
    ]))
    elements.append(words_table)
    elements.append(Spacer(1, 2*mm))
    
    # === 7. DECLARATION / الإقرار ===
    decl_header = [[h_en("Declaration"), h_ar("الإقرار")]]
    decl_header_t = Table(decl_header, colWidths=[col_w, col_w])
    decl_header_t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), NAVY), ('ALIGN', (0, 0), (0, 0), 'LEFT'), ('ALIGN', (1, 0), (1, 0), 'RIGHT')]))
    elements.append(decl_header_t)
    
    decl_ar = f"أقر باستلام من شركة دار الكود للاستشارات الهندسية جميع مستحقاتي وفقاً للبيانات أعلاه. أنا {emp_name} أُقر بأن هذا المبلغ يمثل كافة مستحقاتي حتى تاريخ {last_day}، وأُبرئ ذمة الشركة من أي مطالبات مستقبلية."
    decl_en = f"I acknowledge receipt of all my entitlements from Dar Al Code Engineering Consultancy. This amount represents all my dues until {last_day}, and I release the company from any future claims."
    
    decl_style_ar = ParagraphStyle('decl_ar', fontName=ARABIC_FONT, fontSize=5, alignment=TA_RIGHT, leading=6)
    decl_style_en = ParagraphStyle('decl_en', fontName='Helvetica', fontSize=5, alignment=TA_LEFT, leading=6)
    
    decl_data = [[Paragraph(decl_en, decl_style_en), Paragraph(reshape_arabic(decl_ar), decl_style_ar)]]
    decl_table = Table(decl_data, colWidths=[col_w, col_w])
    decl_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(decl_table)
    elements.append(Spacer(1, 2*mm))
    
    # === 8. SIGNATURES / التوقيعات (5 أعمدة) ===
    sig_header = [[h_en("Signatures"), h_ar("التوقيعات")]]
    sig_header_t = Table(sig_header, colWidths=[col_w, col_w])
    sig_header_t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), NAVY), ('ALIGN', (0, 0), (0, 0), 'LEFT'), ('ALIGN', (1, 0), (1, 0), 'RIGHT')]))
    elements.append(sig_header_t)
    
    qr_data = f"DAR-SETTLEMENT|{txn}|NET:{net_amount:.0f}|DATE:{issue_date}|VERIFIED"
    qr_img = create_qr_image(qr_data, size=15)
    
    sig_name = ParagraphStyle('sig_name', fontName=ARABIC_FONT_BOLD, fontSize=6, alignment=TA_CENTER, textColor=NAVY)
    sig_title = ParagraphStyle('sig_title', fontName=ARABIC_FONT, fontSize=5, alignment=TA_CENTER, textColor=colors.gray)
    sig_line = ParagraphStyle('sig_line', fontName='Helvetica', fontSize=7, alignment=TA_CENTER)
    
    # STAS - QR
    stas_content = Table([
        [Paragraph(reshape_arabic("تمت المخالصة"), ParagraphStyle('s', fontName=ARABIC_FONT_BOLD, fontSize=5, alignment=TA_CENTER, textColor=GREEN))],
        [qr_img if qr_img else Paragraph("QR", sig_line)],
        [Paragraph("STAS", ParagraphStyle('sl', fontName='Helvetica-Bold', fontSize=6, alignment=TA_CENTER, textColor=NAVY))],
    ], colWidths=[28*mm])
    stas_content.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOX', (0, 0), (-1, -1), 0.5, GREEN),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E8F5E9')),
    ]))
    
    # سلطان
    sultan_content = Table([
        [Paragraph(reshape_arabic("أ.سلطان الزامل"), sig_name)],
        [Paragraph(reshape_arabic("المدير الإداري"), sig_title)],
        [Spacer(1, 6*mm)],
        [Paragraph("___________", sig_line)],
    ], colWidths=[28*mm])
    sultan_content.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('BOX', (0, 0), (-1, -1), 0.5, BORDER)]))
    
    # محمد
    mohammed_content = Table([
        [Paragraph(reshape_arabic("م.محمد الثنيان"), sig_name)],
        [Paragraph(reshape_arabic("المدير التنفيذي"), sig_title)],
        [Spacer(1, 6*mm)],
        [Paragraph("___________", sig_line)],
    ], colWidths=[28*mm])
    mohammed_content.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('BOX', (0, 0), (-1, -1), 0.5, BORDER)]))
    
    # محاسب الصندوق
    cashier_content = Table([
        [Paragraph(reshape_arabic("محاسب الصندوق"), sig_name)],
        [Paragraph(reshape_arabic("الشؤون المالية"), sig_title)],
        [Spacer(1, 6*mm)],
        [Paragraph("___________", sig_line)],
    ], colWidths=[28*mm])
    cashier_content.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('BOX', (0, 0), (-1, -1), 0.5, BORDER)]))
    
    # الموظف
    emp_content = Table([
        [Paragraph(reshape_arabic(emp_name[:20] if len(emp_name) > 20 else emp_name), sig_name)],
        [Paragraph(reshape_arabic("الموظف"), sig_title)],
        [Spacer(1, 6*mm)],
        [Paragraph("___________", sig_line)],
    ], colWidths=[28*mm])
    emp_content.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('BOX', (0, 0), (-1, -1), 0.5, BORDER)]))
    
    # جدول التوقيعات (5 أعمدة)
    sig_main = Table(
        [[stas_content, sultan_content, mohammed_content, cashier_content, emp_content]],
        colWidths=[CONTENT_WIDTH/5] * 5
    )
    sig_main.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(sig_main)
    
    # === FOOTER ===
    elements.append(Spacer(1, 1*mm))
    footer_style = ParagraphStyle('footer', fontName='Helvetica', fontSize=5, alignment=TA_CENTER, textColor=colors.gray)
    elements.append(Paragraph(f"DAR AL CODE HR SYSTEM | {txn} | Generated: {issue_date}", footer_style))
    
    doc.build(elements)
    return buffer.getvalue()
