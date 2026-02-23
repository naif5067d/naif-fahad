"""
PDF Generator for In-Kind Custody (العهدة العينية)
مع QR Code وتوقيعات الاستلام والإرجاع
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
import io
import os
import hashlib
import uuid
from datetime import datetime, timezone

# ==================== PAGE SETUP ====================
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 15 * mm
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)

# ==================== COLORS ====================
NAVY = colors.Color(0.08, 0.16, 0.28)
GOLD = colors.Color(0.75, 0.62, 0.35)
WHITE = colors.white
LIGHT_BG = colors.Color(0.98, 0.98, 0.99)
BORDER = colors.Color(0.88, 0.88, 0.90)
TEXT_DARK = colors.Color(0.12, 0.12, 0.14)
SUCCESS = colors.Color(0.10, 0.55, 0.35)

# ==================== FONTS ====================
FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')
ARABIC_FONT = 'NotoNaskhArabic'
ARABIC_FONT_BOLD = 'NotoNaskhArabicBold'


def register_fonts():
    """Register Arabic fonts"""
    global ARABIC_FONT, ARABIC_FONT_BOLD
    font_pairs = [
        ('NotoNaskhArabic', 'NotoNaskhArabic-Regular.ttf', 'NotoNaskhArabic-Bold.ttf'),
        ('NotoSansArabic', 'NotoSansArabic-Regular.ttf', 'NotoSansArabic-Bold.ttf'),
    ]
    for font_name, regular_file, bold_file in font_pairs:
        try:
            regular_path = os.path.join(FONTS_DIR, regular_file)
            bold_path = os.path.join(FONTS_DIR, bold_file)
            if os.path.exists(regular_path):
                pdfmetrics.registerFont(TTFont(font_name, regular_path))
                ARABIC_FONT = font_name
                if os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont(f'{font_name}Bold', bold_path))
                    ARABIC_FONT_BOLD = f'{font_name}Bold'
                return True
        except Exception as e:
            print(f"Font error: {e}")
    return False


def reshape_arabic(text):
    """Reshape Arabic text for PDF display"""
    if not text:
        return ""
    try:
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except:
        return str(text)


def generate_qr_image(data, size=80):
    """Generate QR code image"""
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=4, border=1)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img = img.resize((size, size))
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return RLImage(buffer, width=size, height=size)


def generate_inkind_custody_pdf(custody_data: dict, employee_data: dict, lang: str = 'ar', branding: dict = None):
    """
    Generate In-Kind Custody PDF with QR Code
    
    Returns: (pdf_bytes, pdf_hash, integrity_id)
    """
    register_fonts()
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=MARGIN,
        leftMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN
    )
    
    # Styles
    styles = {
        'title': ParagraphStyle('title', fontName=ARABIC_FONT_BOLD, fontSize=18, textColor=NAVY, alignment=TA_CENTER, spaceAfter=10),
        'subtitle': ParagraphStyle('subtitle', fontName=ARABIC_FONT, fontSize=12, textColor=TEXT_DARK, alignment=TA_CENTER, spaceAfter=20),
        'label': ParagraphStyle('label', fontName=ARABIC_FONT, fontSize=10, textColor=TEXT_DARK, alignment=TA_RIGHT),
        'value': ParagraphStyle('value', fontName=ARABIC_FONT_BOLD, fontSize=11, textColor=NAVY, alignment=TA_RIGHT),
        'footer': ParagraphStyle('footer', fontName=ARABIC_FONT, fontSize=8, textColor=TEXT_DARK, alignment=TA_CENTER),
    }
    
    elements = []
    
    # Generate integrity ID
    ref_no = custody_data.get('ref_no', 'CUS-0000')
    content_hash = hashlib.sha256(f"{ref_no}{custody_data.get('id', '')}".encode()).hexdigest()[:8]
    integrity_id = f"CUS-{ref_no[-6:]}-{content_hash}".upper()
    
    # Title
    title = reshape_arabic('سند استلام عهدة عينية') if lang == 'ar' else 'In-Kind Custody Receipt'
    elements.append(Paragraph(title, styles['title']))
    elements.append(Paragraph(f"Ref: {ref_no}", styles['subtitle']))
    elements.append(Spacer(1, 10))
    
    # QR Code
    qr_data = f"DAR-CUSTODY:{integrity_id}:{ref_no}"
    qr_img = generate_qr_image(qr_data, 70)
    qr_table = Table([[qr_img]], colWidths=[80])
    qr_table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    elements.append(qr_table)
    elements.append(Spacer(1, 15))
    
    # Custody Details
    labels = {
        'ar': {
            'item_name': 'اسم العنصر',
            'serial_number': 'الرقم التسلسلي',
            'estimated_value': 'القيمة التقديرية',
            'description': 'الوصف',
            'employee_name': 'اسم الموظف',
            'assigned_date': 'تاريخ التسليم',
            'status': 'الحالة',
        },
        'en': {
            'item_name': 'Item Name',
            'serial_number': 'Serial Number',
            'estimated_value': 'Estimated Value',
            'description': 'Description',
            'employee_name': 'Employee Name',
            'assigned_date': 'Assigned Date',
            'status': 'Status',
        }
    }
    l = labels[lang]
    
    data = custody_data.get('data', custody_data)
    emp_name = data.get('employee_name_ar', employee_data.get('full_name_ar', '')) if lang == 'ar' else data.get('employee_name', employee_data.get('full_name', ''))
    
    details = [
        [reshape_arabic(l['item_name']), reshape_arabic(data.get('item_name_ar', data.get('item_name', '')))],
        [reshape_arabic(l['serial_number']), data.get('serial_number', '-')],
        [reshape_arabic(l['estimated_value']), f"{data.get('estimated_value', 0):,.2f} SAR"],
        [reshape_arabic(l['employee_name']), reshape_arabic(emp_name)],
        [reshape_arabic(l['assigned_date']), custody_data.get('assigned_at', custody_data.get('created_at', ''))[:10]],
    ]
    
    details_table = Table(details, colWidths=[CONTENT_WIDTH * 0.35, CONTENT_WIDTH * 0.65])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_BG),
        ('TEXTCOLOR', (0, 0), (-1, -1), TEXT_DARK),
        ('FONTNAME', (0, 0), (-1, -1), ARABIC_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 30))
    
    # Signatures Section
    sig_title = reshape_arabic('التوقيعات') if lang == 'ar' else 'Signatures'
    elements.append(Paragraph(sig_title, styles['title']))
    elements.append(Spacer(1, 10))
    
    # Employee Signature (Receipt)
    emp_sig_label = reshape_arabic('توقيع الموظف (استلام العهدة)') if lang == 'ar' else 'Employee Signature (Custody Receipt)'
    stas_sig_label = reshape_arabic('توقيع STAS (تنفيذ الإرجاع)') if lang == 'ar' else 'STAS Signature (Return Execution)'
    
    sig_data = [
        [reshape_arabic('التوقيع'), reshape_arabic('التاريخ'), reshape_arabic('الاسم'), reshape_arabic('الدور')],
        [
            '____________________',
            custody_data.get('employee_signed_at', '____/____/____')[:10] if custody_data.get('employee_signed_at') else '____/____/____',
            reshape_arabic(emp_name),
            reshape_arabic('المستلم') if lang == 'ar' else 'Recipient'
        ],
        [
            '____________________',
            custody_data.get('stas_signed_at', '____/____/____')[:10] if custody_data.get('stas_signed_at') else '____/____/____',
            reshape_arabic('STAS'),
            reshape_arabic('المنفذ') if lang == 'ar' else 'Executor'
        ],
    ]
    
    sig_table = Table(sig_data, colWidths=[CONTENT_WIDTH * 0.3, CONTENT_WIDTH * 0.25, CONTENT_WIDTH * 0.25, CONTENT_WIDTH * 0.2])
    sig_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, -1), ARABIC_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('ROWHEIGHTS', (0, 1), (-1, -1), 40),
    ]))
    elements.append(sig_table)
    elements.append(Spacer(1, 30))
    
    # Footer
    footer_text = f"DAR AL CODE | In-Kind Custody System | {integrity_id}"
    elements.append(Paragraph(footer_text, styles['footer']))
    
    # Build PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    return pdf_bytes, pdf_hash, integrity_id


def generate_custody_return_pdf(custody_data: dict, return_data: dict, lang: str = 'ar'):
    """
    Generate Custody Return PDF with STAS signature
    
    Returns: (pdf_bytes, pdf_hash, integrity_id)
    """
    register_fonts()
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=MARGIN, leftMargin=MARGIN, topMargin=MARGIN, bottomMargin=MARGIN)
    
    styles = {
        'title': ParagraphStyle('title', fontName=ARABIC_FONT_BOLD, fontSize=18, textColor=SUCCESS, alignment=TA_CENTER, spaceAfter=10),
        'subtitle': ParagraphStyle('subtitle', fontName=ARABIC_FONT, fontSize=12, textColor=TEXT_DARK, alignment=TA_CENTER, spaceAfter=20),
        'label': ParagraphStyle('label', fontName=ARABIC_FONT, fontSize=10, textColor=TEXT_DARK, alignment=TA_RIGHT),
        'value': ParagraphStyle('value', fontName=ARABIC_FONT_BOLD, fontSize=11, textColor=NAVY, alignment=TA_RIGHT),
        'footer': ParagraphStyle('footer', fontName=ARABIC_FONT, fontSize=8, textColor=TEXT_DARK, alignment=TA_CENTER),
    }
    
    elements = []
    
    ref_no = return_data.get('ref_no', 'RET-0000')
    content_hash = hashlib.sha256(f"{ref_no}{return_data.get('id', '')}".encode()).hexdigest()[:8]
    integrity_id = f"RET-{ref_no[-6:]}-{content_hash}".upper()
    
    # Title
    title = reshape_arabic('سند إرجاع عهدة عينية') if lang == 'ar' else 'In-Kind Custody Return Receipt'
    elements.append(Paragraph(title, styles['title']))
    elements.append(Paragraph(f"Ref: {ref_no}", styles['subtitle']))
    elements.append(Spacer(1, 10))
    
    # QR Code
    qr_data = f"DAR-RETURN:{integrity_id}:{ref_no}"
    qr_img = generate_qr_image(qr_data, 70)
    qr_table = Table([[qr_img]], colWidths=[80])
    qr_table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    elements.append(qr_table)
    elements.append(Spacer(1, 15))
    
    # Return Details
    data = return_data.get('data', return_data)
    emp_name = data.get('employee_name_ar', '') if lang == 'ar' else data.get('employee_name', '')
    
    labels_ar = ['اسم العنصر', 'الرقم التسلسلي', 'اسم الموظف', 'تاريخ الإرجاع', 'منفذ بواسطة']
    labels_en = ['Item Name', 'Serial Number', 'Employee Name', 'Return Date', 'Executed By']
    labels = labels_ar if lang == 'ar' else labels_en
    
    details = [
        [reshape_arabic(labels[0]), reshape_arabic(data.get('item_name_ar', data.get('item_name', '')))],
        [reshape_arabic(labels[1]), data.get('serial_number', '-')],
        [reshape_arabic(labels[2]), reshape_arabic(emp_name)],
        [reshape_arabic(labels[3]), return_data.get('executed_at', return_data.get('updated_at', ''))[:10]],
        [reshape_arabic(labels[4]), 'STAS'],
    ]
    
    details_table = Table(details, colWidths=[CONTENT_WIDTH * 0.35, CONTENT_WIDTH * 0.65])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_BG),
        ('TEXTCOLOR', (0, 0), (-1, -1), TEXT_DARK),
        ('FONTNAME', (0, 0), (-1, -1), ARABIC_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 30))
    
    # STAS Signature
    sig_title = reshape_arabic('توقيع التنفيذ - STAS') if lang == 'ar' else 'Execution Signature - STAS'
    elements.append(Paragraph(sig_title, styles['title']))
    elements.append(Spacer(1, 10))
    
    sig_box = reshape_arabic('تم استلام العهدة وإتمام الإرجاع بنجاح') if lang == 'ar' else 'Custody received and return completed successfully'
    elements.append(Paragraph(sig_box, styles['subtitle']))
    elements.append(Spacer(1, 20))
    
    sig_data = [
        [reshape_arabic('توقيع STAS'), '____________________'],
        [reshape_arabic('التاريخ'), return_data.get('executed_at', '')[:10] if return_data.get('executed_at') else '____/____/____'],
    ]
    
    sig_table = Table(sig_data, colWidths=[CONTENT_WIDTH * 0.3, CONTENT_WIDTH * 0.4])
    sig_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), ARABIC_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('ROWHEIGHTS', (0, 0), (-1, -1), 35),
    ]))
    elements.append(sig_table)
    elements.append(Spacer(1, 30))
    
    # Footer
    footer_text = f"DAR AL CODE | Custody Return | {integrity_id}"
    elements.append(Paragraph(footer_text, styles['footer']))
    
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    return pdf_bytes, pdf_hash, integrity_id
