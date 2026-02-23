"""
PDF Generator for In-Kind Custody (العهدة العينية)
التصميم الاحترافي الموحد
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image as RLImage, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display
import qrcode
import io
import os
import hashlib
from datetime import datetime, timezone, timedelta

# ==================== SETUP ====================
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 15 * mm
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)

NAVY = colors.Color(0.118, 0.227, 0.373)
GOLD = colors.Color(0.75, 0.62, 0.35)
LIGHT_BLUE = colors.Color(0.93, 0.96, 0.99)
LIGHT_GRAY = colors.Color(0.95, 0.95, 0.96)
BORDER_COLOR = colors.Color(0.8, 0.82, 0.85)
TEXT_DARK = colors.Color(0.2, 0.2, 0.25)
TEXT_GRAY = colors.Color(0.5, 0.5, 0.55)
SUCCESS_GREEN = colors.Color(0.13, 0.55, 0.33)
WHITE = colors.white

FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')
ARABIC_FONT = 'NotoNaskhArabic'
ARABIC_FONT_BOLD = 'NotoNaskhArabicBold'
ENGLISH_FONT = 'Helvetica'
ENGLISH_FONT_BOLD = 'Helvetica-Bold'


def register_fonts():
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


def reshape_arabic(text):
    if not text:
        return ''
    try:
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except Exception:
        return str(text)


def format_date(ts):
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


def generate_inkind_custody_pdf(custody_data: dict, employee_data: dict, lang: str = 'ar', branding: dict = None):
    """Generate In-Kind Custody PDF"""
    register_fonts()
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=MARGIN, bottomMargin=MARGIN, leftMargin=MARGIN, rightMargin=MARGIN)
    
    elements = []
    
    ref_no = custody_data.get('ref_no', 'CUS-0000')
    content_hash = hashlib.sha256(f"{ref_no}{custody_data.get('id', '')}".encode()).hexdigest()[:8]
    integrity_id = f"DAR-CUS-{ref_no[-6:]}-{content_hash}".upper()
    
    data = custody_data.get('data', custody_data)
    emp_name_ar = data.get('employee_name_ar', employee_data.get('full_name_ar', ''))
    emp_name_en = data.get('employee_name', employee_data.get('full_name', ''))
    
    company_ar = branding.get('company_name_ar', 'شركة دار الكود للاستشارات الهندسية') if branding else 'شركة دار الكود للاستشارات الهندسية'
    company_en = branding.get('company_name_en', 'DAR AL CODE Engineering Consultancy') if branding else 'DAR AL CODE Engineering Consultancy'
    
    # Styles
    header_ar = ParagraphStyle('h_ar', fontName=ARABIC_FONT_BOLD, fontSize=14, alignment=TA_CENTER, textColor=NAVY, leading=18)
    header_en = ParagraphStyle('h_en', fontName=ENGLISH_FONT_BOLD, fontSize=11, alignment=TA_CENTER, textColor=NAVY)
    header_small = ParagraphStyle('h_s', fontName=ENGLISH_FONT, fontSize=8, alignment=TA_CENTER, textColor=TEXT_GRAY)
    title_ar = ParagraphStyle('t_ar', fontName=ARABIC_FONT_BOLD, fontSize=16, alignment=TA_CENTER, textColor=NAVY)
    title_en = ParagraphStyle('t_en', fontName=ENGLISH_FONT_BOLD, fontSize=12, alignment=TA_CENTER, textColor=TEXT_GRAY)
    ref_style = ParagraphStyle('ref', fontName=ENGLISH_FONT_BOLD, fontSize=10, alignment=TA_CENTER, textColor=GOLD)
    label = ParagraphStyle('label', fontName=ENGLISH_FONT, fontSize=9, alignment=TA_CENTER, textColor=TEXT_GRAY)
    label_ar = ParagraphStyle('label_ar', fontName=ARABIC_FONT, fontSize=9, alignment=TA_CENTER, textColor=TEXT_GRAY)
    value = ParagraphStyle('value', fontName=ENGLISH_FONT_BOLD, fontSize=10, alignment=TA_CENTER, textColor=TEXT_DARK)
    value_ar = ParagraphStyle('value_ar', fontName=ARABIC_FONT_BOLD, fontSize=10, alignment=TA_CENTER, textColor=TEXT_DARK)
    
    # Header
    elements.append(Paragraph(reshape_arabic(company_ar), header_ar))
    elements.append(Paragraph(company_en, header_en))
    elements.append(Paragraph("Kingdom of Saudi Arabia | License: 5110004935 | CR: 1010463476", header_small))
    elements.append(Spacer(1, 3*mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=NAVY, spaceBefore=2, spaceAfter=5))
    
    # Title
    elements.append(Paragraph(reshape_arabic('سند استلام عهدة عينية'), title_ar))
    elements.append(Paragraph('In-Kind Custody Receipt', title_en))
    elements.append(Paragraph(f"Ref: {ref_no}", ref_style))
    elements.append(Spacer(1, 5*mm))
    
    # Info table
    col_w = CONTENT_WIDTH / 4
    status = custody_data.get('status', 'pending')
    
    info_data = [
        [Paragraph("Value", label), Paragraph("Field", label), Paragraph(reshape_arabic("الحقل"), label_ar), Paragraph(reshape_arabic("القيمة"), label_ar)],
        [Paragraph(ref_no, value), Paragraph("Reference", label), Paragraph(reshape_arabic("رقم المرجع"), label_ar), Paragraph(reshape_arabic(ref_no), value_ar)],
        [Paragraph(emp_name_en, value), Paragraph("Employee", label), Paragraph(reshape_arabic("الموظف"), label_ar), Paragraph(reshape_arabic(emp_name_ar), value_ar)],
        [Paragraph(data.get('item_name', '-'), value), Paragraph("Item", label), Paragraph(reshape_arabic("العنصر"), label_ar), Paragraph(reshape_arabic(data.get('item_name_ar', data.get('item_name', '-'))), value_ar)],
        [Paragraph(data.get('serial_number', '-'), value), Paragraph("Serial No", label), Paragraph(reshape_arabic("الرقم التسلسلي"), label_ar), Paragraph(reshape_arabic(data.get('serial_number', '-')), value_ar)],
        [Paragraph(f"{data.get('estimated_value', 0):,.2f} SAR", value), Paragraph("Value", label), Paragraph(reshape_arabic("القيمة"), label_ar), Paragraph(reshape_arabic(f"{data.get('estimated_value', 0):,.2f} ريال"), value_ar)],
    ]
    
    info_table = Table(info_data, colWidths=[col_w]*4)
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('BOX', (0, 0), (-1, -1), 1, NAVY),
        ('LINEBELOW', (0, 0), (-1, 0), 1, NAVY),
        ('INNERGRID', (0, 1), (-1, -1), 0.5, BORDER_COLOR),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 8*mm))
    
    # Signatures
    section = ParagraphStyle('section', fontName=ARABIC_FONT_BOLD, fontSize=11, alignment=TA_CENTER, textColor=NAVY)
    elements.append(Paragraph(reshape_arabic("التوقيعات | Signatures"), section))
    elements.append(Spacer(1, 3*mm))
    
    sig_role = ParagraphStyle('sig_role', fontName=ARABIC_FONT_BOLD, fontSize=10, alignment=TA_CENTER, textColor=NAVY)
    sig_role_en = ParagraphStyle('sig_role_en', fontName=ENGLISH_FONT, fontSize=8, alignment=TA_CENTER, textColor=TEXT_GRAY)
    sig_name = ParagraphStyle('sig_name', fontName=ARABIC_FONT_BOLD, fontSize=9, alignment=TA_CENTER, textColor=TEXT_DARK)
    sig_name_en = ParagraphStyle('sig_name_en', fontName=ENGLISH_FONT, fontSize=8, alignment=TA_CENTER, textColor=TEXT_GRAY)
    sig_date = ParagraphStyle('sig_date', fontName=ENGLISH_FONT, fontSize=8, alignment=TA_CENTER, textColor=TEXT_GRAY)
    sig_status = ParagraphStyle('sig_status', fontName=ARABIC_FONT_BOLD, fontSize=8, alignment=TA_CENTER, textColor=SUCCESS_GREEN)
    
    emp_signed = custody_data.get('employee_signed', False)
    stas_signed = custody_data.get('stas_signed', False) or status == 'executed'
    
    signatures = [
        ('الموظف', 'Employee', emp_name_ar, emp_name_en, emp_signed, custody_data.get('employee_signed_at', '')),
        ('الموارد البشرية', 'HR', 'سلطان', 'Sultan', True, custody_data.get('created_at', '')),
        ('STAS', 'STAS', 'STAS', 'STAS', stas_signed, custody_data.get('stas_signed_at', custody_data.get('executed_at', ''))),
    ]
    
    sig_boxes = []
    for role_ar, role_en, name_ar, name_en, signed, timestamp in signatures:
        qr = create_qr_image(f"SIG-{role_en.upper()}-{ref_no}", size=20) if signed else Paragraph("—", sig_date)
        box = [
            [Paragraph(reshape_arabic(role_ar), sig_role)],
            [Paragraph(role_en, sig_role_en)],
            [Spacer(1, 2*mm)],
            [qr],
            [Spacer(1, 2*mm)],
            [Paragraph(reshape_arabic(name_ar), sig_name)],
            [Paragraph(name_en, sig_name_en)],
            [Paragraph(format_date(timestamp) if signed else "____/____/____", sig_date)],
            [Paragraph(reshape_arabic("✓ تم التوقيع") if signed else "", sig_status)],
        ]
        box_table = Table(box, colWidths=[50*mm])
        box_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BLUE),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        sig_boxes.append(box_table)
    
    sig_row = Table([sig_boxes], colWidths=[CONTENT_WIDTH/3]*3)
    sig_row.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    elements.append(sig_row)
    elements.append(Spacer(1, 10*mm))
    
    # Tear-off line
    tear = ParagraphStyle('tear', fontName=ENGLISH_FONT, fontSize=9, alignment=TA_CENTER, textColor=TEXT_GRAY)
    elements.append(HRFlowable(width="100%", thickness=1, color=BORDER_COLOR, spaceBefore=2, spaceAfter=0, dash=(3, 3)))
    elements.append(Paragraph("✂  Cut Here  |  قص هنا  ✂", tear))
    elements.append(HRFlowable(width="100%", thickness=1, color=BORDER_COLOR, spaceBefore=0, spaceAfter=5, dash=(3, 3)))
    
    # Coupon
    coupon_ar = ParagraphStyle('c_ar', fontName=ARABIC_FONT_BOLD, fontSize=11, alignment=TA_CENTER, textColor=NAVY)
    coupon_en = ParagraphStyle('c_en', fontName=ENGLISH_FONT_BOLD, fontSize=9, alignment=TA_CENTER, textColor=NAVY)
    coupon_text = ParagraphStyle('c_t', fontName=ENGLISH_FONT, fontSize=8, alignment=TA_CENTER, textColor=TEXT_DARK)
    coupon_text_ar = ParagraphStyle('c_t_ar', fontName=ARABIC_FONT, fontSize=9, alignment=TA_CENTER, textColor=TEXT_DARK)
    coupon_status = ParagraphStyle('c_s', fontName=ARABIC_FONT_BOLD, fontSize=9, alignment=TA_CENTER, textColor=SUCCESS_GREEN if stas_signed else TEXT_GRAY)
    
    stas_qr = create_qr_image(f"STAS-{ref_no}", size=25) if stas_signed else Paragraph("Pending", coupon_text)
    verify_qr = create_qr_image(f"VERIFY-{ref_no}", size=25)
    
    left = Table([[stas_qr], [Paragraph("STAS QR", coupon_text)]], colWidths=[35*mm])
    left.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    
    center = Table([
        [Paragraph(reshape_arabic(company_ar), coupon_ar)],
        [Paragraph(company_en, coupon_en)],
        [Spacer(1, 2*mm)],
        [Paragraph(reshape_arabic('عهدة عينية'), coupon_text_ar)],
        [Paragraph('In-Kind Custody', coupon_text)],
        [Paragraph(f"Ref: {ref_no}", coupon_text)],
        [Spacer(1, 2*mm)],
        [Paragraph(reshape_arabic(emp_name_ar), coupon_text_ar)],
        [Paragraph(emp_name_en, coupon_text)],
        [Paragraph(reshape_arabic("✓ معاملة صحيحة" if stas_signed else "بانتظار التنفيذ"), coupon_status)],
    ], colWidths=[90*mm])
    center.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    
    right = Table([[verify_qr], [Paragraph("Verify QR", coupon_text)]], colWidths=[35*mm])
    right.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    
    coupon = Table([[left, center, right]], colWidths=[40*mm, CONTENT_WIDTH-80*mm, 40*mm])
    coupon.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1.5, NAVY),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BLUE),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(coupon)
    elements.append(Spacer(1, 3*mm))
    
    # Footer
    footer = ParagraphStyle('footer', fontName=ENGLISH_FONT, fontSize=7, alignment=TA_CENTER, textColor=TEXT_GRAY)
    now = datetime.now(timezone.utc) + timedelta(hours=3)
    elements.append(Paragraph(f"DAR AL CODE HR OS | {integrity_id} | Generated: {now.strftime('%Y-%m-%d %H:%M')} KSA", footer))
    
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    return pdf_bytes, pdf_hash, integrity_id


def generate_custody_return_pdf(custody_data: dict, return_data: dict, lang: str = 'ar', branding: dict = None):
    """Generate Custody Return PDF - same structure as custody"""
    return generate_inkind_custody_pdf(return_data, {}, lang, branding)
