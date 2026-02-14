"""
Contract Template Engine
Generates PDF contracts with dynamic placeholders.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime, timezone
import io
import hashlib
import os

# Register Arabic font
FONT_PATH = os.path.join(os.path.dirname(__file__), "..", "fonts", "NotoSansArabic-Regular.ttf")
if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont('Arabic', FONT_PATH))
    ARABIC_FONT = 'Arabic'
else:
    ARABIC_FONT = 'Helvetica'


def format_gregorian_hijri(date_str: str) -> str:
    """Format date as Gregorian with Hijri approximation"""
    if not date_str:
        return "-"
    try:
        # Simple Hijri approximation (for display only)
        from datetime import datetime
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        gregorian = dt.strftime("%Y/%m/%d")
        
        # Approximate Hijri calculation (simplified)
        hijri_year = int((dt.year - 622) * 33 / 32) + 1
        hijri_month = ((dt.month + 9) % 12) + 1
        hijri_day = dt.day
        
        return f"{gregorian} ({hijri_year}/{hijri_month:02d}/{hijri_day:02d} هـ)"
    except Exception:
        return date_str[:10] if date_str else "-"


def format_currency(amount: float) -> str:
    """Format amount as Saudi Riyal"""
    if amount is None:
        return "0.00 ريال"
    return f"{amount:,.2f} ريال"


CONTRACT_TEMPLATE_AR = """
عقد عمل

الطرف الأول (صاحب العمل):
{{company_name_ar}}

الطرف الثاني (الموظف):
الاسم: {{employee_name_ar}}
الرقم الوظيفي: {{employee_code}}
المسمى الوظيفي: {{job_title_ar}}
القسم: {{department_ar}}

تفاصيل العقد:
رقم العقد: {{contract_serial}}
نوع العقد: {{contract_type_ar}}
تاريخ البداية: {{start_date}}
تاريخ النهاية: {{end_date}}
فترة التجربة: {{probation_months}} شهر
فترة الإنذار: {{notice_period_days}} يوم

تفاصيل الراتب:
الراتب الأساسي: {{basic_salary}}
بدل السكن: {{housing_allowance}}
بدل النقل: {{transport_allowance}}
بدلات أخرى: {{other_allowances}}
────────────────────────
إجمالي الراتب الشهري: {{total_salary}}

الشروط والأحكام:
[سيتم إضافة النص القانوني الرسمي المعتمد لاحقاً]

التوقيعات:
_________________________          _________________________
توقيع صاحب العمل                    توقيع الموظف
التاريخ: {{execution_date}}

رقم التحقق: {{integrity_id}}
"""

CONTRACT_TEMPLATE_EN = """
EMPLOYMENT CONTRACT

FIRST PARTY (Employer):
{{company_name_en}}

SECOND PARTY (Employee):
Name: {{employee_name}}
Employee Code: {{employee_code}}
Job Title: {{job_title}}
Department: {{department}}

Contract Details:
Contract Number: {{contract_serial}}
Contract Type: {{contract_type}}
Start Date: {{start_date}}
End Date: {{end_date}}
Probation Period: {{probation_months}} months
Notice Period: {{notice_period_days}} days

Salary Details:
Basic Salary: {{basic_salary}}
Housing Allowance: {{housing_allowance}}
Transport Allowance: {{transport_allowance}}
Other Allowances: {{other_allowances}}
────────────────────────
Total Monthly Salary: {{total_salary}}

Terms and Conditions:
[Official legal text to be added later]

Signatures:
_________________________          _________________________
Employer Signature                    Employee Signature
Date: {{execution_date}}

Verification ID: {{integrity_id}}
"""


def generate_contract_pdf(
    contract: dict,
    employee: dict = None,
    branding: dict = None,
    lang: str = "ar"
) -> tuple:
    """
    Generate PDF contract document.
    Returns (pdf_bytes, pdf_hash, integrity_id)
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    if lang == "ar":
        title_style = ParagraphStyle(
            'ArabicTitle',
            parent=styles['Heading1'],
            fontName=ARABIC_FONT,
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=20
        )
        normal_style = ParagraphStyle(
            'ArabicNormal',
            parent=styles['Normal'],
            fontName=ARABIC_FONT,
            fontSize=12,
            alignment=TA_RIGHT,
            leading=18
        )
    else:
        title_style = styles['Heading1']
        normal_style = styles['Normal']
    
    # Build content
    story = []
    
    # Company header
    company_name = branding.get("company_name_ar" if lang == "ar" else "company_name_en", "شركة دار الكود") if branding else "شركة دار الكود للاستشارات الهندسية"
    
    # Title
    title = "عقد عمل" if lang == "ar" else "EMPLOYMENT CONTRACT"
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 30))
    
    # Contract Serial
    serial = contract.get("contract_serial", "-")
    story.append(Paragraph(f"رقم العقد: {serial}" if lang == "ar" else f"Contract No: {serial}", normal_style))
    story.append(Spacer(1, 20))
    
    # Employer Section
    story.append(Paragraph("الطرف الأول (صاحب العمل):" if lang == "ar" else "FIRST PARTY (Employer):", normal_style))
    story.append(Paragraph(company_name, normal_style))
    story.append(Spacer(1, 20))
    
    # Employee Section
    emp_name = contract.get("employee_name_ar" if lang == "ar" else "employee_name", "-")
    emp_code = contract.get("employee_code", "-")
    job_title = contract.get("job_title_ar" if lang == "ar" else "job_title", "-")
    department = contract.get("department_ar" if lang == "ar" else "department", "-")
    
    story.append(Paragraph("الطرف الثاني (الموظف):" if lang == "ar" else "SECOND PARTY (Employee):", normal_style))
    
    emp_data = [
        [("الاسم" if lang == "ar" else "Name") + ":", emp_name],
        [("الرقم الوظيفي" if lang == "ar" else "Employee Code") + ":", emp_code],
        [("المسمى الوظيفي" if lang == "ar" else "Job Title") + ":", job_title],
        [("القسم" if lang == "ar" else "Department") + ":", department],
    ]
    
    emp_table = Table(emp_data, colWidths=[4*cm, 10*cm])
    emp_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), ARABIC_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT' if lang == "ar" else 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT' if lang == "ar" else 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(emp_table)
    story.append(Spacer(1, 20))
    
    # Contract Details
    contract_type_map = {
        "unlimited": ("غير محدد المدة", "Unlimited"),
        "fixed_term": ("محدد المدة", "Fixed Term"),
        "trial_paid": ("فترة تجربة مدفوعة", "Paid Trial"),
    }
    
    category_map = {
        "employment": ("توظيف", "Employment"),
        "internship_unpaid": ("تدريب غير مدفوع", "Unpaid Internship"),
    }
    
    emp_type = contract.get("employment_type", "unlimited")
    category = contract.get("contract_category", "employment")
    
    contract_type_ar, contract_type_en = contract_type_map.get(emp_type, ("غير محدد", "Unknown"))
    category_ar, category_en = category_map.get(category, ("غير محدد", "Unknown"))
    
    story.append(Paragraph("تفاصيل العقد:" if lang == "ar" else "Contract Details:", normal_style))
    
    contract_data = [
        [("نوع العقد" if lang == "ar" else "Contract Type") + ":", contract_type_ar if lang == "ar" else contract_type_en],
        [("فئة العقد" if lang == "ar" else "Category") + ":", category_ar if lang == "ar" else category_en],
        [("تاريخ البداية" if lang == "ar" else "Start Date") + ":", format_gregorian_hijri(contract.get("start_date"))],
        [("تاريخ النهاية" if lang == "ar" else "End Date") + ":", format_gregorian_hijri(contract.get("end_date")) if contract.get("end_date") else ("غير محدد" if lang == "ar" else "Unlimited")],
        [("فترة التجربة" if lang == "ar" else "Probation") + ":", f"{contract.get('probation_months', 3)} " + ("شهر" if lang == "ar" else "months")],
        [("فترة الإنذار" if lang == "ar" else "Notice Period") + ":", f"{contract.get('notice_period_days', 30)} " + ("يوم" if lang == "ar" else "days")],
    ]
    
    contract_table = Table(contract_data, colWidths=[4*cm, 10*cm])
    contract_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), ARABIC_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT' if lang == "ar" else 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT' if lang == "ar" else 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(contract_table)
    story.append(Spacer(1, 20))
    
    # Salary Details (only for employment contracts)
    if category != "internship_unpaid":
        basic = contract.get("basic_salary", 0)
        housing = contract.get("housing_allowance", 0)
        transport = contract.get("transport_allowance", 0)
        other = contract.get("other_allowances", 0)
        total = basic + housing + transport + other
        
        story.append(Paragraph("تفاصيل الراتب:" if lang == "ar" else "Salary Details:", normal_style))
        
        salary_data = [
            [("الراتب الأساسي" if lang == "ar" else "Basic Salary") + ":", format_currency(basic)],
            [("بدل السكن" if lang == "ar" else "Housing Allowance") + ":", format_currency(housing)],
            [("بدل النقل" if lang == "ar" else "Transport Allowance") + ":", format_currency(transport)],
            [("بدلات أخرى" if lang == "ar" else "Other Allowances") + ":", format_currency(other)],
            ["─" * 20, "─" * 20],
            [("إجمالي الراتب الشهري" if lang == "ar" else "Total Monthly Salary") + ":", format_currency(total)],
        ]
        
        salary_table = Table(salary_data, colWidths=[5*cm, 9*cm])
        salary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), ARABIC_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT' if lang == "ar" else 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT' if lang == "ar" else 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('FONTNAME', (0, -1), (-1, -1), ARABIC_FONT),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.darkblue),
        ]))
        story.append(salary_table)
    else:
        story.append(Paragraph("هذا العقد للتدريب غير المدفوع - لا يوجد راتب" if lang == "ar" else "This is an unpaid internship contract - No salary", normal_style))
    
    story.append(Spacer(1, 30))
    
    # Terms placeholder
    story.append(Paragraph("الشروط والأحكام:" if lang == "ar" else "Terms and Conditions:", normal_style))
    story.append(Paragraph("[سيتم إضافة النص القانوني الرسمي المعتمد لاحقاً]" if lang == "ar" else "[Official legal text to be added later]", normal_style))
    story.append(Spacer(1, 40))
    
    # Signatures
    story.append(Paragraph("التوقيعات:" if lang == "ar" else "Signatures:", normal_style))
    story.append(Spacer(1, 20))
    
    sig_data = [
        [("توقيع صاحب العمل" if lang == "ar" else "Employer Signature"), ("توقيع الموظف" if lang == "ar" else "Employee Signature")],
        ["_" * 30, "_" * 30],
    ]
    
    sig_table = Table(sig_data, colWidths=[7*cm, 7*cm])
    sig_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), ARABIC_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
    ]))
    story.append(sig_table)
    story.append(Spacer(1, 20))
    
    # Execution date and integrity
    now = datetime.now(timezone.utc).isoformat()
    integrity_id = f"CTR-{hashlib.sha256((contract.get('contract_serial', '') + now).encode()).hexdigest()[:12].upper()}"
    
    story.append(Paragraph(f"تاريخ التنفيذ: {format_gregorian_hijri(now[:10])}" if lang == "ar" else f"Execution Date: {format_gregorian_hijri(now[:10])}", normal_style))
    story.append(Paragraph(f"رقم التحقق: {integrity_id}" if lang == "ar" else f"Verification ID: {integrity_id}", normal_style))
    
    # Build PDF
    doc.build(story)
    
    pdf_bytes = buffer.getvalue()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    return pdf_bytes, pdf_hash, integrity_id
