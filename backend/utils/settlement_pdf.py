"""
Settlement PDF Generator - وثيقة المخالصة
============================================================
- صفحة واحدة A4 فقط
- تعهد إبراء ذمة قانوني كامل
- العهد العينية مع تقدير التلفيات
- خصومات/سلف يدوية
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

# ألوان
NAVY = colors.HexColor('#1E3A5F')
LIGHT_BG = colors.HexColor('#F8FAFC')
BORDER = colors.HexColor('#E2E8F0')
GREEN = colors.HexColor('#16A34A')

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 8 * mm
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)

FONT_DIR = "/app/backend/fonts"
ARABIC_FONT = 'Helvetica'
ARABIC_FONT_BOLD = 'Helvetica-Bold'

def _register_fonts():
    global ARABIC_FONT, ARABIC_FONT_BOLD
    registered = pdfmetrics.getRegisteredFontNames()
    if 'Amiri' in registered:
        ARABIC_FONT = 'Amiri'
        ARABIC_FONT_BOLD = 'Amiri'
        return True
    amiri_path = os.path.join(FONT_DIR, 'Amiri-Regular.ttf')
    if os.path.exists(amiri_path):
        try:
            if os.path.getsize(amiri_path) > 50000:
                pdfmetrics.registerFont(TTFont('Amiri', amiri_path))
                ARABIC_FONT = 'Amiri'
                ARABIC_FONT_BOLD = 'Amiri'
                return True
        except:
            pass
    return False

_register_fonts()

def reshape_arabic(text):
    if not text:
        return ''
    try:
        return get_display(arabic_reshaper.reshape(str(text)))
    except:
        return str(text)

def create_qr_image(data, size=15):
    try:
        qr = qrcode.QRCode(version=1, box_size=2, border=1)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#1E3A5F", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return Image(buffer, width=size*mm, height=size*mm)
    except:
        return None

def load_logo_image(branding):
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
        return Image(io.BytesIO(logo_bytes), width=15*mm, height=10*mm)
    except:
        return None


def generate_settlement_pdf(settlement: dict, branding: dict = None) -> bytes:
    _register_fonts()
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=6*mm, bottomMargin=6*mm)
    
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
    manual_deductions = snapshot.get("manual_deductions", [])
    manual_loans = snapshot.get("manual_loans", [])
    inkind_damages = snapshot.get("inkind_damages", [])
    
    # Styles
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
    
    # === HEADER ===
    txn = settlement.get("transaction_number", "")
    issue_date = settlement.get("executed_at", "")[:10] if settlement.get("executed_at") else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    logo_img = load_logo_image(branding)
    
    if logo_img:
        header_data = [
            [en("Kingdom of Saudi Arabia"), logo_img, ar("المملكة العربية السعودية")],
            [en_b("Dar Al Code Engineering Consultancy"), '', ar_b("شركة دار الكود للاستشارات الهندسية")],
            [en("Riyadh | CR: 1010463476 | License: 5110004935"), '', ar("الرياض | سجل: 1010463476 | ترخيص: 5110004935")],
        ]
        col_widths = [col_w - 10*mm, 20*mm, col_w - 10*mm]
    else:
        header_data = [
            [en("Kingdom of Saudi Arabia"), ar("المملكة العربية السعودية")],
            [en_b("Dar Al Code Engineering Consultancy"), ar_b("شركة دار الكود للاستشارات الهندسية")],
            [en("Riyadh | CR: 1010463476 | License: 5110004935"), ar("الرياض | سجل: 1010463476 | ترخيص: 5110004935")],
        ]
        col_widths = [col_w, col_w]
    
    header_table = Table(header_data, colWidths=col_widths)
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'), ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LINEBELOW', (0, -1), (-1, -1), 1, NAVY),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 1.5*mm))
    
    # Reference
    ref_data = [[en(f"Settlement Ref: {txn} | Date: {issue_date}"), ar(f"مرجع المخالصة: {txn} | التاريخ: {issue_date}")]]
    ref_table = Table(ref_data, colWidths=[col_w, col_w])
    ref_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'), ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG), ('BOX', (0, 0), (-1, -1), 0.5, BORDER),
    ]))
    elements.append(ref_table)
    elements.append(Spacer(1, 1.5*mm))
    
    # === EMPLOYEE INFO ===
    emp_header = [[h_en("Employee Information"), h_ar("بيانات الموظف")]]
    emp_header_t = Table(emp_header, colWidths=[col_w, col_w])
    emp_header_t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), NAVY)]))
    elements.append(emp_header_t)
    
    emp_name = employee.get("name_ar", "")
    emp_name_en = employee.get("name_en", "") or "-"  # الاسم بالإنجليزي
    emp_code = employee.get("employee_number", "")
    national_id = employee.get("national_id", "") or employee.get("iqama_number", "")
    
    # المسمى الوظيفي - التحقق من أن القيمة إنجليزية (لا تحتوي على عربي)
    job_title_ar = contract.get("job_title_ar") or contract.get("job_title") or employee.get("job_title", "") or "-"
    job_title_en_raw = contract.get("job_title") or ""
    # إذا كان يحتوي على عربي، استخدم "-"
    job_title_en = job_title_en_raw if job_title_en_raw and not any('\u0600' <= c <= '\u06FF' for c in job_title_en_raw) else "-"
    
    # القسم - التحقق من أن القيمة إنجليزية
    department_ar = contract.get("department_ar") or contract.get("department") or employee.get("department", "") or "-"
    department_en_raw = contract.get("department") or ""
    department_en = department_en_raw if department_en_raw and not any('\u0600' <= c <= '\u06FF' for c in department_en_raw) else "-"
    
    bank_name = contract.get("bank_name", "")
    bank_iban = contract.get("bank_iban", "")
    hire_date = contract.get("start_date", "")
    last_day = contract.get("last_working_day", "")
    clearance_type = contract.get("termination_type_label", "")
    clearance_type_en = contract.get("termination_type", "").replace("_", " ").title()
    
    service_years = service.get("years", 0)
    service_months = service.get("months", 0)
    service_days_count = service.get("days", 0)
    service_duration = f"{service_years} سنة و {service_months} شهر و {service_days_count} يوم"
    
    # جدول بيانات الموظف - 4 أعمدة (العمود الأول والثاني إنجليزي، الثالث والرابع عربي)
    emp_data = [
        [en(emp_name_en), en("Name"), ar("الاسم"), ar(emp_name)],
        [en(emp_code), en("Employee ID"), ar("الرقم الوظيفي"), ar(emp_code)],
        [en(national_id), en("ID/Iqama"), ar("الهوية/الإقامة"), ar(national_id)],
        [en(job_title_en), en("Job Title"), ar("المسمى الوظيفي"), ar(job_title_ar)],
        [en(department_en), en("Department"), ar("القسم"), ar(department_ar)],
        [en(bank_name), en("Bank"), ar("البنك"), ar(bank_name)],
        [en(bank_iban), en("IBAN"), ar("الآيبان"), ar(bank_iban)],
        [en(hire_date), en("Hire Date"), ar("تاريخ التعيين"), ar(hire_date)],
        [en(last_day), en("Last Working Day"), ar("آخر يوم عمل"), ar(last_day)],
        [en(f"{service_years}y {service_months}m {service_days_count}d"), en("Service Period"), ar("مدة الخدمة"), ar(service_duration)],
        [en(clearance_type_en or "-"), en("Clearance Type"), ar("نوع المخالصة"), ar(clearance_type)],
    ]
    emp_table = Table(emp_data, colWidths=[col_w*0.35, col_w*0.65, col_w*0.65, col_w*0.35])
    emp_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (1, -1), 'LEFT'), ('ALIGN', (2, 0), (3, -1), 'RIGHT'),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER), ('INNERGRID', (0, 0), (-1, -1), 0.3, BORDER),
        ('BACKGROUND', (1, 0), (1, -1), LIGHT_BG), ('BACKGROUND', (2, 0), (2, -1), LIGHT_BG),
        ('TOPPADDING', (0, 0), (-1, -1), 0.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5),
    ]))
    elements.append(emp_table)
    elements.append(Spacer(1, 1.5*mm))
    
    # === SALARY ===
    sal_header = [[h_en("Salary Details"), h_ar("تفاصيل الراتب")]]
    sal_header_t = Table(sal_header, colWidths=[col_w, col_w])
    sal_header_t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), NAVY)]))
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
        ('ALIGN', (0, 0), (1, -1), 'LEFT'), ('ALIGN', (2, 0), (3, -1), 'RIGHT'),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER), ('INNERGRID', (0, 0), (-1, -1), 0.3, BORDER),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E8F5E9')),
        ('TOPPADDING', (0, 0), (-1, -1), 0.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5),
    ]))
    elements.append(sal_table)
    elements.append(Spacer(1, 1.5*mm))
    
    # === ENTITLEMENTS ===
    ent_header = [[h_en("Entitlements"), h_ar("الاستحقاقات")]]
    ent_header_t = Table(ent_header, colWidths=[col_w, col_w])
    ent_header_t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), NAVY)]))
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
        partial_month_str = partial_month.get("month", "")
        if partial_month_str:
            partial_from = f"01/{partial_month_str.split('-')[1]}/{partial_month_str.split('-')[0]}"
            partial_to = f"{partial_days:02d}/{partial_month_str.split('-')[1]}/{partial_month_str.split('-')[0]}"
        else:
            partial_from = f"01/{last_day[5:7]}/{last_day[:4]}"
            partial_to = f"{last_day[8:10]}/{last_day[5:7]}/{last_day[:4]}"
        ent_data.append([
            en(f"{partial_amount:,.0f}"), 
            en(f"Payroll Outside ({partial_from} to {partial_to})"), 
            ar(f"راتب خارج المسيرات (من {partial_from} إلى {partial_to})"), 
            ar(f"{partial_amount:,.0f}")
        ])
    
    # بدل الإجازات
    leave_detail = f"({leave_balance:.1f} يوم × {daily_wage:,.0f})"
    ent_data.append([en(f"{leave_comp:,.0f}"), en(f"Leave ({leave_balance:.1f} days)"), ar(f"بدل الإجازات {leave_detail}"), ar(f"{leave_comp:,.0f}")])
    
    # مكافأة نهاية الخدمة
    eos_detail = f"({service_years} سنة × {eos_pct}%)"
    ent_data.append([en(f"{eos_amount:,.0f}"), en(f"End of Service ({service_years}y × {eos_pct}%)"), ar(f"مكافأة نهاية الخدمة {eos_detail}"), ar(f"{eos_amount:,.0f}")])
    
    ent_data.append([en_b(f"{total_ent:,.0f}"), en_b("Total Entitlements"), ar_b("إجمالي الاستحقاقات"), ar_b(f"{total_ent:,.0f}")])
    
    ent_table = Table(ent_data, colWidths=[col_w*0.2, col_w*0.8, col_w*0.8, col_w*0.2])
    ent_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (1, -1), 'LEFT'), ('ALIGN', (2, 0), (3, -1), 'RIGHT'),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER), ('INNERGRID', (0, 0), (-1, -1), 0.3, BORDER),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E8F5E9')),
        ('TOPPADDING', (0, 0), (-1, -1), 0.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5),
    ]))
    elements.append(ent_table)
    elements.append(Spacer(1, 1.5*mm))
    
    # === DEDUCTIONS ===
    ded_header = [[h_en("Deductions"), h_ar("الاستقطاعات")]]
    ded_header_t = Table(ded_header, colWidths=[col_w, col_w])
    ded_header_t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), NAVY)]))
    elements.append(ded_header_t)
    
    deductions = totals.get("deductions", {})
    loans_total = deductions.get("loans", 0)
    other_ded = deductions.get("deductions", 0)
    custody_total = deductions.get("custody", 0) or custody.get("total", 0)
    total_ded = deductions.get("total", 0)
    
    # حساب مجموع الخصومات اليدوية والعهد العينية
    manual_ded_total = sum(d.get("amount", 0) for d in manual_deductions)
    manual_loans_total = sum(loan.get("amount", 0) for loan in manual_loans)
    inkind_total = sum(d.get("amount", 0) for d in inkind_damages)
    
    ded_data = []
    
    # السلف (تلقائي)
    if loans_total > 0:
        ded_data.append([en(f"{loans_total:,.0f}"), en("Loans / Advances"), ar("السلف"), ar(f"{loans_total:,.0f}")])
    
    # السلف اليدوية مع التفاصيل
    for loan in manual_loans:
        ded_data.append([en(f"{loan.get('amount', 0):,.0f}"), en(f"Loan: {loan.get('note_en', '')}"), ar(f"سلفة: {loan.get('note', '')}"), ar(f"{loan.get('amount', 0):,.0f}")])
    
    # العهد المالية
    if custody_total > 0:
        ded_data.append([en(f"{custody_total:,.0f}"), en("Financial Custody"), ar("العهد المالية"), ar(f"{custody_total:,.0f}")])
    
    # تلفيات العهد العينية مع التفاصيل
    for damage in inkind_damages:
        ded_data.append([en(f"{damage.get('amount', 0):,.0f}"), en(f"Damage: {damage.get('item_name', '')}"), ar(f"تلف: {damage.get('item_name_ar', '')}"), ar(f"{damage.get('amount', 0):,.0f}")])
    
    # الخصومات اليدوية مع التفاصيل
    for ded in manual_deductions:
        ded_data.append([en(f"{ded.get('amount', 0):,.0f}"), en(f"Deduction: {ded.get('note_en', '')}"), ar(f"خصم: {ded.get('note', '')}"), ar(f"{ded.get('amount', 0):,.0f}")])
    
    # خصومات أخرى (تلقائي)
    if other_ded > 0:
        ded_data.append([en(f"{other_ded:,.0f}"), en("Other Deductions"), ar("خصومات أخرى"), ar(f"{other_ded:,.0f}")])
    
    # إذا لا يوجد أي خصومات، نضيف صف فارغ
    if not ded_data:
        ded_data.append([en("0"), en("No Deductions"), ar("لا توجد استقطاعات"), ar("0")])
    
    # إجمالي الاستقطاعات (يشمل اليدوي)
    final_total_ded = total_ded + manual_ded_total + manual_loans_total + inkind_total
    ded_data.append([en_b(f"{final_total_ded:,.0f}"), en_b("Total Deductions"), ar_b("إجمالي الاستقطاعات"), ar_b(f"{final_total_ded:,.0f}")])
    
    ded_table = Table(ded_data, colWidths=[col_w*0.2, col_w*0.8, col_w*0.8, col_w*0.2])
    ded_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (1, -1), 'LEFT'), ('ALIGN', (2, 0), (3, -1), 'RIGHT'),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER), ('INNERGRID', (0, 0), (-1, -1), 0.3, BORDER),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FFEBEE')),
        ('TOPPADDING', (0, 0), (-1, -1), 0.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5),
    ]))
    elements.append(ded_table)
    elements.append(Spacer(1, 1.5*mm))
    
    # === NET AMOUNT ===
    net_amount = totals.get("net_amount", 0)
    # تعديل الصافي ليشمل الخصومات اليدوية
    net_amount = net_amount - manual_ded_total - manual_loans_total - inkind_total
    
    net_words = totals.get("net_amount_words", "")
    if not net_words:
        from utils.arabic_numbers import number_to_arabic
        net_words = number_to_arabic(net_amount)
    
    net_style = ParagraphStyle('net', fontName='Helvetica-Bold', fontSize=10, alignment=TA_CENTER, textColor=NAVY)
    net_style_ar = ParagraphStyle('net_ar', fontName=ARABIC_FONT_BOLD, fontSize=10, alignment=TA_CENTER, textColor=NAVY)
    
    net_data = [[Paragraph(f"SAR {net_amount:,.2f}", net_style), Paragraph(reshape_arabic(f"ريال {net_amount:,.2f}"), net_style_ar)]]
    net_table = Table(net_data, colWidths=[col_w, col_w])
    net_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('BOX', (0, 0), (-1, -1), 2, NAVY),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E3F2FD')),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(net_table)
    
    # المبلغ كتابةً
    words_style = ParagraphStyle('words', fontName=ARABIC_FONT, fontSize=6, alignment=TA_CENTER, textColor=NAVY)
    words_table = Table([[Paragraph(reshape_arabic(net_words), words_style)]], colWidths=[CONTENT_WIDTH])
    words_table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG), ('BOX', (0, 0), (-1, -1), 0.5, BORDER)]))
    elements.append(words_table)
    elements.append(Spacer(1, 2*mm))
    
    # === DECLARATION - إقرار إبراء الذمة ===
    decl_header = [[h_en("Declaration & Release"), h_ar("الإقرار وإبراء الذمة")]]
    decl_header_t = Table(decl_header, colWidths=[col_w, col_w])
    decl_header_t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), NAVY)]))
    elements.append(decl_header_t)
    
    # نص الإقرار القانوني المختصر
    decl_ar = f"""أقر بأنني استلمت كامل حقوقي المنصوص عليها في هذه المخالصة، وأنني أبرئ شركة دار الكود للاستشارات الهندسية من أي مطالبات مستقبلية، وأقر باستلام كامل مستحقاتي. وبالله التوفيق."""
    
    decl_en = f"""I acknowledge that I have received all my rights as stated in this settlement, and I release Dar Al Code Engineering Consultancy from any future claims. I confirm receipt of all my entitlements."""
    
    decl_style_ar = ParagraphStyle('decl_ar', fontName=ARABIC_FONT, fontSize=6, alignment=TA_RIGHT, leading=8)
    decl_style_en = ParagraphStyle('decl_en', fontName='Helvetica', fontSize=6, alignment=TA_LEFT, leading=8)
    
    decl_data = [[Paragraph(decl_en, decl_style_en), Paragraph(reshape_arabic(decl_ar), decl_style_ar)]]
    decl_table = Table(decl_data, colWidths=[col_w, col_w])
    decl_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'), ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER), ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(decl_table)
    elements.append(Spacer(1, 2*mm))
    
    # === SIGNATURES ===
    sig_header = [[h_en("Signatures"), h_ar("التوقيعات")]]
    sig_header_t = Table(sig_header, colWidths=[col_w, col_w])
    sig_header_t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), NAVY)]))
    elements.append(sig_header_t)
    
    qr_data = f"DAR-SETTLEMENT|{txn}|NET:{net_amount:.0f}|DATE:{issue_date}|RIYADH|VERIFIED"
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
    stas_content.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('BOX', (0, 0), (-1, -1), 0.5, GREEN), ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E8F5E9'))]))
    
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
    emp_short = emp_name[:20] if len(emp_name) > 20 else emp_name
    emp_content = Table([
        [Paragraph(reshape_arabic(emp_short), sig_name)],
        [Paragraph(reshape_arabic("الموظف"), sig_title)],
        [Spacer(1, 6*mm)],
        [Paragraph("___________", sig_line)],
    ], colWidths=[28*mm])
    emp_content.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('BOX', (0, 0), (-1, -1), 0.5, BORDER)]))
    
    sig_main = Table([[stas_content, sultan_content, mohammed_content, cashier_content, emp_content]], colWidths=[CONTENT_WIDTH/5] * 5)
    sig_main.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    elements.append(sig_main)
    
    # Footer
    elements.append(Spacer(1, 1*mm))
    footer_style = ParagraphStyle('footer', fontName='Helvetica', fontSize=5, alignment=TA_CENTER, textColor=colors.gray)
    elements.append(Paragraph(f"DAR AL CODE HR SYSTEM | {txn} | Riyadh | {issue_date}", footer_style))
    
    doc.build(elements)
    return buffer.getvalue()
