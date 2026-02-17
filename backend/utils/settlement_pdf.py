"""
Settlement PDF Generator - وثيقة المخالصة
============================================================
- صفحة واحدة A4 عمودية فقط
- Hybrid bilingual: يمين عربي، يسار إنجليزي (نفس السطر)
- QR للتوقيعات + Barcode لـ STAS
- فراغ توقيع الموظف اليدوي
- شعار الشركة في الترويسة
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics import renderPDF
import arabic_reshaper
from bidi.algorithm import get_display
import io
import qrcode
import barcode
from barcode.writer import ImageWriter
from datetime import datetime, timezone
import os

# تسجيل الخطوط
FONT_DIR = "/app/backend/fonts"
try:
    pdfmetrics.registerFont(TTFont('NotoArabic', os.path.join(FONT_DIR, 'NotoNaskhArabic-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('NotoArabicBold', os.path.join(FONT_DIR, 'NotoNaskhArabic-Bold.ttf')))
    ARABIC_FONT = 'NotoArabic'
    ARABIC_FONT_BOLD = 'NotoArabicBold'
except:
    ARABIC_FONT = 'Helvetica'
    ARABIC_FONT_BOLD = 'Helvetica-Bold'

ENGLISH_FONT = 'Helvetica'
ENGLISH_FONT_BOLD = 'Helvetica-Bold'

# ألوان
NAVY = colors.Color(0.118, 0.227, 0.373)  # #1E3A5F
LIGHT_GRAY = colors.Color(0.95, 0.95, 0.95)
BORDER_GRAY = colors.Color(0.8, 0.8, 0.8)
GOLD = colors.Color(0.8, 0.6, 0.2)  # لون ذهبي للشعار

# أبعاد الصفحة
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 12 * mm
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)

# مسار اللوجو
LOGO_PATH = "/app/backend/assets/logo.png"


def create_company_logo(branding=None, width=25, height=25):
    """
    إنشاء شعار الشركة
    يحاول تحميل اللوجو من branding (base64) أو من ملف، وإذا لم يكن موجوداً ينشئ شعار نصي
    """
    # 1. محاولة تحميل من branding (base64)
    if branding and branding.get('logo_data'):
        try:
            import base64
            logo_data = branding['logo_data']
            # إزالة prefix مثل "data:image/jpeg;base64,"
            if ',' in logo_data:
                logo_data = logo_data.split(',')[1]
            logo_bytes = base64.b64decode(logo_data)
            logo_buffer = io.BytesIO(logo_bytes)
            return Image(logo_buffer, width=width*mm, height=height*mm)
        except Exception as e:
            print(f"Error loading logo from branding: {e}")
    
    # 2. محاولة تحميل من ملف
    if os.path.exists(LOGO_PATH):
        try:
            return Image(LOGO_PATH, width=width*mm, height=height*mm)
        except:
            pass
    
    # 3. إنشاء شعار نصي بديل - DAC
    d = Drawing(width*mm, height*mm)
    
    # مربع خلفية
    d.add(Rect(0, 0, width*mm, height*mm, fillColor=NAVY, strokeColor=None, rx=3, ry=3))
    
    # حرف D
    d.add(String(3*mm, 8*mm, "D", fontName=ENGLISH_FONT_BOLD, fontSize=14, fillColor=colors.white))
    # حرف A
    d.add(String(9*mm, 8*mm, "A", fontName=ENGLISH_FONT_BOLD, fontSize=14, fillColor=GOLD))
    # حرف C
    d.add(String(15*mm, 8*mm, "C", fontName=ENGLISH_FONT_BOLD, fontSize=14, fillColor=colors.white))
    
    return d


def reshape_arabic(text):
    """تحويل النص العربي للعرض الصحيح"""
    if not text:
        return ''
    try:
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except:
        return str(text)


def create_qr_image(data, size=18):
    """إنشاء صورة QR Code"""
    try:
        qr = qrcode.QRCode(version=1, box_size=2, border=1)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return Image(buffer, width=size*mm, height=size*mm)
    except:
        return None


def create_barcode_image(data, width=40, height=10):
    """إنشاء صورة Barcode"""
    try:
        code128 = barcode.get_barcode_class('code128')
        bc = code128(data, writer=ImageWriter())
        buffer = io.BytesIO()
        bc.write(buffer, options={'write_text': False, 'module_height': 5, 'quiet_zone': 1})
        buffer.seek(0)
        return Image(buffer, width=width*mm, height=height*mm)
    except:
        return None


def generate_settlement_pdf(settlement: dict, branding: dict = None) -> bytes:
    """
    توليد PDF المخالصة - صفحة واحدة A4 عمودية
    Hybrid bilingual: يمين عربي، يسار إنجليزي
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN
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
    
    # ============ STYLES ============
    style_ar = ParagraphStyle('ar', fontName=ARABIC_FONT, fontSize=8, alignment=TA_RIGHT, wordWrap='RTL', leading=10)
    style_ar_bold = ParagraphStyle('ar_bold', fontName=ARABIC_FONT_BOLD, fontSize=8, alignment=TA_RIGHT, wordWrap='RTL', leading=10)
    style_en = ParagraphStyle('en', fontName=ENGLISH_FONT, fontSize=8, alignment=TA_LEFT, leading=10)
    style_en_bold = ParagraphStyle('en_bold', fontName=ENGLISH_FONT_BOLD, fontSize=8, alignment=TA_LEFT, leading=10)
    style_title_ar = ParagraphStyle('title_ar', fontName=ARABIC_FONT_BOLD, fontSize=10, alignment=TA_RIGHT, wordWrap='RTL', textColor=NAVY)
    style_title_en = ParagraphStyle('title_en', fontName=ENGLISH_FONT_BOLD, fontSize=10, alignment=TA_LEFT, textColor=NAVY)
    style_small = ParagraphStyle('small', fontName=ENGLISH_FONT, fontSize=6, alignment=TA_CENTER, textColor=colors.gray)
    
    def ar(text): return Paragraph(reshape_arabic(str(text)), style_ar)
    def ar_bold(text): return Paragraph(reshape_arabic(str(text)), style_ar_bold)
    def en(text): return Paragraph(str(text), style_en)
    def en_bold(text): return Paragraph(str(text), style_en_bold)
    def title_ar(text): return Paragraph(reshape_arabic(str(text)), style_title_ar)
    def title_en(text): return Paragraph(str(text), style_title_en)
    
    col_ar = CONTENT_WIDTH * 0.5
    col_en = CONTENT_WIDTH * 0.5
    
    # ============ 1. HEADER WITH LOGO / الترويسة مع الشعار ============
    # إنشاء اللوجو
    logo = create_company_logo(width=20, height=20)
    
    # Header with logo in center
    header_left = [
        [en("Kingdom of Saudi Arabia – Riyadh")],
        [en_bold("Dar Al Code Engineering Consultancy")],
        [en("License No: 5110004935 – CR: 1010463476")],
    ]
    header_right = [
        [ar("المملكة العربية السعودية – الرياض")],
        [ar_bold("شركة دار الكود للاستشارات الهندسية")],
        [ar("ترخيص رقم: 5110004935 – سجل تجاري: 1010463476")],
    ]
    
    header_left_table = Table(header_left, colWidths=[col_en - 12*mm])
    header_left_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    header_right_table = Table(header_right, colWidths=[col_ar - 12*mm])
    header_right_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    # Main header with logo in center
    header_data = [[header_left_table, logo, header_right_table]]
    header_table = Table(header_data, colWidths=[col_en - 12*mm, 24*mm, col_ar - 12*mm])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, NAVY),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 3*mm))
    
    # Transaction Number
    txn = settlement.get("transaction_number", "")
    txn_table = Table([[en(f"Ref: {txn}"), ar(f"مرجع: {txn}")]], colWidths=[col_en, col_ar])
    txn_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
    ]))
    elements.append(txn_table)
    elements.append(Spacer(1, 3*mm))
    
    # ============ 2. EMPLOYEE INFO / بيانات الموظف ============
    section_header = Table([[title_en("Employee Information"), title_ar("بيانات الموظف")]], colWidths=[col_en, col_ar])
    section_header.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BACKGROUND', (0, 0), (-1, -1), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(section_header)
    
    emp_name_ar = employee.get("name_ar", "")
    emp_name_en = employee.get("name_en", employee.get("name_ar", ""))
    emp_code = employee.get("employee_number", "")
    national_id = employee.get("national_id", "")
    department = contract.get("department_ar", "")
    department_en = contract.get("department", department)
    job_title_ar = contract.get("job_title_ar", "")
    job_title_en = contract.get("job_title", job_title_ar)
    hire_date = contract.get("start_date", "")
    last_day = contract.get("last_working_day", "")
    clearance_type_ar = contract.get("termination_type_label", "")
    clearance_type_en = settlement.get("termination_type", "").replace("_", " ").title()
    issue_date = settlement.get("executed_at", "")[:10] if settlement.get("executed_at") else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    emp_data = [
        [en(emp_name_en), en("Employee Name"), ar("اسم الموظف"), ar(emp_name_ar)],
        [en(emp_code), en("Employee ID"), ar("الرقم الوظيفي"), ar(emp_code)],
        [en(national_id), en("Iqama / National ID"), ar("رقم الإقامة أو الهوية"), ar(national_id)],
        [en(department_en), en("Department"), ar("الإدارة"), ar(department)],
        [en(job_title_en), en("Job Title"), ar("المسمى الوظيفي"), ar(job_title_ar)],
        [en(hire_date), en("Hire Date"), ar("تاريخ التعيين"), ar(hire_date)],
        [en(last_day), en("Last Working Day"), ar("تاريخ آخر يوم عمل"), ar(last_day)],
        [en(clearance_type_en), en("Clearance Type"), ar("نوع المخالصة"), ar(clearance_type_ar)],
        [en(issue_date), en("Clearance Issue Date"), ar("تاريخ إصدار شهادة المخالصة"), ar(issue_date)],
    ]
    
    emp_table = Table(emp_data, colWidths=[col_en*0.5, col_en*0.5, col_ar*0.5, col_ar*0.5])
    emp_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (3, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, BORDER_GRAY),
        ('BACKGROUND', (1, 0), (1, -1), LIGHT_GRAY),
        ('BACKGROUND', (2, 0), (2, -1), LIGHT_GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    elements.append(emp_table)
    elements.append(Spacer(1, 2*mm))
    
    # ============ 3. SALARY DETAILS / تفاصيل الراتب ============
    salary_header = Table([[title_en("Salary & Allowances Details"), title_ar("تفاصيل الراتب والبدلات")]], colWidths=[col_en, col_ar])
    salary_header.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BACKGROUND', (0, 0), (-1, -1), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(salary_header)
    
    basic = wages.get("basic", 0)
    housing = wages.get("housing", 0)
    transport = wages.get("transport", 0)
    nature = wages.get("nature_of_work", 0)
    last_wage = wages.get("last_wage", 0)
    
    salary_data = [
        [en(f"{basic:,.2f}"), en("Basic Salary"), ar("الراتب الأساسي"), ar(f"{basic:,.2f}")],
        [en(f"{housing:,.2f}"), en("Housing Allowance"), ar("بدل السكن"), ar(f"{housing:,.2f}")],
        [en(f"{nature:,.2f}"), en("Nature of Work Allowance"), ar("بدل طبيعة العمل"), ar(f"{nature:,.2f}")],
        [en(f"{transport:,.2f}"), en("Transportation Allowance"), ar("بدل نقل"), ar(f"{transport:,.2f}")],
        [en_bold(f"{last_wage:,.2f}"), en_bold("Total Salary"), ar_bold("إجمالي الراتب"), ar_bold(f"{last_wage:,.2f}")],
    ]
    
    salary_table = Table(salary_data, colWidths=[col_en*0.4, col_en*0.6, col_ar*0.6, col_ar*0.4])
    salary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, BORDER_GRAY),
        ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.9, 0.95, 0.9)),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    elements.append(salary_table)
    elements.append(Spacer(1, 2*mm))
    
    # ============ 4. LEAVE DETAILS / تفاصيل الإجازات ============
    leave_header = Table([[title_en("Leave Details"), title_ar("تفاصيل الإجازات")]], colWidths=[col_en, col_ar])
    leave_header.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BACKGROUND', (0, 0), (-1, -1), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(leave_header)
    
    policy_days = leave.get("policy_days", 21)
    balance = leave.get("balance", 0)
    
    leave_data = [
        [en(f"{policy_days}"), en("Total Leave Days"), ar("عدد أيام الإجازة"), ar(f"{policy_days}")],
        [en(f"{balance:.2f}"), en("Leave Balance"), ar("رصيد الإجازات بالأيام"), ar(f"{balance:.2f}")],
    ]
    
    leave_table = Table(leave_data, colWidths=[col_en*0.4, col_en*0.6, col_ar*0.6, col_ar*0.4])
    leave_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, BORDER_GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    elements.append(leave_table)
    elements.append(Spacer(1, 2*mm))
    
    # ============ 5. ENTITLEMENTS / الاستحقاقات ============
    ent_header = Table([[title_en("Entitlements"), title_ar("الاستحقاقات")]], colWidths=[col_en, col_ar])
    ent_header.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BACKGROUND', (0, 0), (-1, -1), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(ent_header)
    
    eos_amount = eos.get("final_amount", 0)
    leave_comp = leave.get("compensation", 0)
    total_ent = totals.get("entitlements", {}).get("total", 0)
    
    ent_data = [
        [en(f"{eos_amount:,.2f}"), en("End of Service Benefit"), ar("مكافأة ترك الخدمة"), ar(f"{eos_amount:,.2f}")],
        [en(f"{leave_comp:,.2f}"), en("Leave Compensation"), ar("بدل إجازة"), ar(f"{leave_comp:,.2f}")],
        [en_bold(f"{total_ent:,.2f}"), en_bold("Total Entitlements"), ar_bold("إجمالي الاستحقاقات"), ar_bold(f"{total_ent:,.2f}")],
    ]
    
    ent_table = Table(ent_data, colWidths=[col_en*0.4, col_en*0.6, col_ar*0.6, col_ar*0.4])
    ent_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, BORDER_GRAY),
        ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.9, 0.95, 0.9)),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    elements.append(ent_table)
    elements.append(Spacer(1, 2*mm))
    
    # ============ 6. DEDUCTIONS / الاستقطاعات ============
    ded_header = Table([[title_en("Deductions"), title_ar("الاستقطاعات")]], colWidths=[col_en, col_ar])
    ded_header.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BACKGROUND', (0, 0), (-1, -1), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(ded_header)
    
    deductions = totals.get("deductions", {})
    loans = deductions.get("loans", 0)
    other_ded = deductions.get("deductions", 0)
    total_ded = deductions.get("total", 0)
    
    ded_data = [
        [en(f"{loans:,.2f}"), en("Loans Balance"), ar("رصيد السلف"), ar(f"{loans:,.2f}")],
        [en(f"{other_ded:,.2f}"), en("Other Deductions"), ar("حسميات أخرى"), ar(f"{other_ded:,.2f}")],
        [en_bold(f"{total_ded:,.2f}"), en_bold("Total Deductions"), ar_bold("إجمالي الاستقطاعات"), ar_bold(f"{total_ded:,.2f}")],
    ]
    
    ded_table = Table(ded_data, colWidths=[col_en*0.4, col_en*0.6, col_ar*0.6, col_ar*0.4])
    ded_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, BORDER_GRAY),
        ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.95, 0.9, 0.9)),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    elements.append(ded_table)
    elements.append(Spacer(1, 2*mm))
    
    # ============ 7. NET AMOUNT / الصافي ============
    net_amount = totals.get("net_amount", 0)
    
    net_header = Table([[title_en("Net Amount Payable to Employee"), title_ar("الصافي النهائي المستحق للموظف")]], colWidths=[col_en, col_ar])
    net_header.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BACKGROUND', (0, 0), (-1, -1), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(net_header)
    
    net_style_ar = ParagraphStyle('net_ar', fontName=ARABIC_FONT_BOLD, fontSize=12, alignment=TA_CENTER, wordWrap='RTL', textColor=NAVY)
    net_style_en = ParagraphStyle('net_en', fontName=ENGLISH_FONT_BOLD, fontSize=12, alignment=TA_CENTER, textColor=NAVY)
    
    net_data = [[
        Paragraph(f"SAR {net_amount:,.2f}", net_style_en),
        Paragraph(reshape_arabic(f"ريال {net_amount:,.2f}"), net_style_ar)
    ]]
    
    net_table = Table(net_data, colWidths=[col_en, col_ar])
    net_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1, NAVY),
        ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.95, 0.98, 1)),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(net_table)
    elements.append(Spacer(1, 2*mm))
    
    # ============ 8. DECLARATION / نص الإقرار ============
    decl_ar = "أقر أنا الموقع أدناه بأنني استلمت كافة مستحقاتي من شركة دار الكود للاستشارات الهندسية حسب البيانات المذكورة أعلاه، وهذا المبلغ شامل كافة مستحقاتي المالية حتى تاريخه، وتُعتبر هذه بمثابة براءة ذمة للشركة ولا يحق لي المطالبة بأية مستحقات لاحقة."
    decl_en = "I, the undersigned, confirm that I have received all my entitlements from Dar Al Code Engineering Consultancy according to the above details. This amount includes all my financial dues up to this date and represents a full release of liability for the company."
    
    decl_style_ar = ParagraphStyle('decl_ar', fontName=ARABIC_FONT, fontSize=7, alignment=TA_RIGHT, wordWrap='RTL', leading=9)
    decl_style_en = ParagraphStyle('decl_en', fontName=ENGLISH_FONT, fontSize=7, alignment=TA_LEFT, leading=9)
    
    decl_data = [[
        Paragraph(decl_en, decl_style_en),
        Paragraph(reshape_arabic(decl_ar), decl_style_ar)
    ]]
    
    decl_table = Table(decl_data, colWidths=[col_en, col_ar])
    decl_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(decl_table)
    elements.append(Spacer(1, 3*mm))
    
    # ============ 9. SIGNATURES / التوقيعات ============
    sig_header = Table([[title_en("Signatures"), title_ar("التوقيعات")]], colWidths=[col_en, col_ar])
    sig_header.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BACKGROUND', (0, 0), (-1, -1), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(sig_header)
    
    # QR codes للتوقيعات
    qr_sultan = create_qr_image(f"SULTAN-{txn}-APPROVED", size=15)
    qr_mohammed = create_qr_image(f"CEO-{txn}-APPROVED", size=15)
    qr_stas = create_qr_image(f"STAS-{txn}-EXECUTED", size=15)
    barcode_stas = create_barcode_image(f"EXEC-{txn}", width=35, height=8)
    
    # صف التوقيعات: الموظف | سلطان | محمد | STAS
    sig_label_style = ParagraphStyle('sig_label', fontName=ENGLISH_FONT, fontSize=7, alignment=TA_CENTER)
    sig_label_style_ar = ParagraphStyle('sig_label_ar', fontName=ARABIC_FONT, fontSize=7, alignment=TA_CENTER, wordWrap='RTL')
    
    sig_row1 = [
        Paragraph("STAS Execution", sig_label_style),
        Paragraph("CEO (Mohammed)", sig_label_style),
        Paragraph("HR (Sultan)", sig_label_style),
        Paragraph("Employee", sig_label_style),
    ]
    sig_row2 = [
        Paragraph(reshape_arabic("تنفيذ STAS"), sig_label_style_ar),
        Paragraph(reshape_arabic("المدير العام (محمد)"), sig_label_style_ar),
        Paragraph(reshape_arabic("الموارد البشرية (سلطان)"), sig_label_style_ar),
        Paragraph(reshape_arabic("الموظف"), sig_label_style_ar),
    ]
    
    # QR/Barcode row
    stas_cell = []
    if qr_stas:
        stas_cell.append(qr_stas)
    if barcode_stas:
        stas_cell.append(barcode_stas)
    
    sig_row3 = [
        Table([[qr_stas], [barcode_stas]], colWidths=[35*mm]) if qr_stas and barcode_stas else '',
        qr_mohammed or '',
        qr_sultan or '',
        Paragraph("________________", sig_label_style),  # فراغ توقيع الموظف اليدوي
    ]
    
    sig_row4 = [
        Paragraph(f"Ref: {txn}", sig_label_style),
        '',
        '',
        Paragraph(reshape_arabic(emp_name_ar), sig_label_style_ar),
    ]
    
    col_width = CONTENT_WIDTH / 4
    sig_data = [sig_row1, sig_row2, sig_row3, sig_row4]
    
    sig_table = Table(sig_data, colWidths=[col_width, col_width, col_width, col_width])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, BORDER_GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(sig_table)
    
    # ============ FOOTER ============
    elements.append(Spacer(1, 2*mm))
    footer_text = f"DAR AL CODE HR OS | {txn} | {issue_date}"
    elements.append(Paragraph(footer_text, style_small))
    
    # Build PDF
    doc.build(elements)
    return buffer.getvalue()
