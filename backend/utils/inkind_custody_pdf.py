"""
PDF Generator for In-Kind Custody (العهدة العينية)
مع QR Code وتوقيعات الاستلام والإرجاع
التصميم الاحترافي الموحد مع خط القطع
"""
from utils.professional_pdf import (
    generate_professional_transaction_pdf,
    create_unified_header,
    create_tear_off_line,
    create_signatures_table,
    create_tear_off_coupon,
    create_document_title,
    create_bilingual_row,
    create_footer,
    create_qr_image,
    reshape_arabic,
    format_saudi_time,
    register_fonts,
    CONTENT_WIDTH, MARGIN, PAGE_WIDTH, PAGE_HEIGHT,
    NAVY, GOLD, WHITE, LIGHT_GRAY, BORDER_GRAY, TEXT_GRAY, SUCCESS_GREEN
)
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image as RLImage
import io
import hashlib
import uuid
from datetime import datetime, timezone, timedelta


# Import font settings
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')
ARABIC_FONT = 'NotoNaskhArabic'
ARABIC_FONT_BOLD = 'NotoNaskhArabicBold'


def generate_inkind_custody_pdf(custody_data: dict, employee_data: dict, lang: str = 'ar', branding: dict = None):
    """
    Generate In-Kind Custody PDF with Professional Design
    التصميم الاحترافي مع خط القطع وجدول التوقيعات
    
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
    
    elements = []
    
    # Generate integrity ID
    ref_no = custody_data.get('ref_no', 'CUS-0000')
    content_hash = hashlib.sha256(f"{ref_no}{custody_data.get('id', '')}".encode()).hexdigest()[:8]
    integrity_id = f"DAR-CUS-{ref_no[-6:]}-{content_hash}".upper()
    
    # ============ 1. UNIFIED HEADER ============
    elements.append(create_unified_header(branding))
    elements.append(Spacer(1, 4*mm))
    
    # ============ 2. DOCUMENT TITLE ============
    title_ar = 'سند استلام عهدة عينية'
    title_en = 'In-Kind Custody Receipt'
    elements.append(create_document_title(title_ar, title_en, ref_no))
    elements.append(Spacer(1, 4*mm))
    
    # ============ 3. MAIN INFO ============
    data = custody_data.get('data', custody_data)
    emp_name_ar = data.get('employee_name_ar', employee_data.get('full_name_ar', ''))
    emp_name_en = data.get('employee_name', employee_data.get('full_name', ''))
    
    # Info header
    info_header = create_bilingual_row('معلومات العهدة', 'Custody Information', '', '', is_header=True)
    elements.append(info_header)
    
    # Info rows
    info_rows = [
        ('رقم المرجع', 'Reference No', ref_no, ref_no),
        ('اسم الموظف', 'Employee Name', emp_name_ar, emp_name_en),
        ('اسم العنصر', 'Item Name', data.get('item_name_ar', data.get('item_name', '')), data.get('item_name', '')),
        ('الرقم التسلسلي', 'Serial Number', data.get('serial_number', '-'), data.get('serial_number', '-')),
        ('القيمة التقديرية', 'Estimated Value', f"{data.get('estimated_value', 0):,.2f} ريال", f"{data.get('estimated_value', 0):,.2f} SAR"),
        ('تاريخ التسليم', 'Assigned Date', custody_data.get('assigned_at', custody_data.get('created_at', ''))[:10], custody_data.get('assigned_at', custody_data.get('created_at', ''))[:10]),
    ]
    
    if data.get('description'):
        info_rows.append(('الوصف', 'Description', data.get('description', ''), data.get('description', '')))
    
    for row in info_rows:
        elements.append(create_bilingual_row(row[0], row[1], row[2], row[3]))
    
    elements.append(Spacer(1, 5*mm))
    
    # ============ 4. SIGNATURES TABLE ============
    signatures = []
    
    # Employee signature (receipt)
    emp_signed = custody_data.get('employee_signed', False)
    signatures.append({
        'role': 'employee',
        'name_ar': emp_name_ar,
        'name_en': emp_name_en,
        'signed': emp_signed,
        'timestamp': custody_data.get('employee_signed_at', ''),
    })
    
    # HR/Sultan signature (issuer)
    signatures.append({
        'role': 'hr',
        'name_ar': 'سلطان',
        'name_en': 'Sultan',
        'signed': True,
        'timestamp': custody_data.get('created_at', ''),
    })
    
    # STAS signature
    stas_signed = custody_data.get('stas_signed', False) or custody_data.get('status') == 'executed'
    signatures.append({
        'role': 'stas',
        'name_ar': 'STAS',
        'name_en': 'STAS',
        'signed': stas_signed,
        'timestamp': custody_data.get('stas_signed_at', custody_data.get('executed_at', '')),
    })
    
    # Section title
    style_title = ParagraphStyle('sig_title', fontName=ARABIC_FONT_BOLD if ARABIC_FONT_BOLD else 'Helvetica-Bold', 
                                  fontSize=10, alignment=TA_CENTER, textColor=NAVY)
    elements.append(Paragraph(reshape_arabic("التوقيعات | Signatures"), style_title))
    elements.append(Spacer(1, 3*mm))
    
    sig_table = create_signatures_table(signatures, ref_no)
    if sig_table:
        elements.append(sig_table)
    
    elements.append(Spacer(1, 8*mm))
    
    # ============ 5. TEAR-OFF LINE ============
    elements.append(create_tear_off_line())
    elements.append(Spacer(1, 4*mm))
    
    # ============ 6. TEAR-OFF COUPON ============
    coupon = create_tear_off_coupon(
        doc_type='tangible_custody',
        ref_no=ref_no,
        employee_name_ar=emp_name_ar,
        employee_name_en=emp_name_en,
        stas_signed=stas_signed,
        stas_timestamp=custody_data.get('stas_signed_at', custody_data.get('executed_at', '')),
        branding=branding
    )
    elements.append(coupon)
    
    elements.append(Spacer(1, 4*mm))
    
    # ============ 7. FOOTER ============
    elements.append(create_footer(integrity_id))
    
    # Build PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    return pdf_bytes, pdf_hash, integrity_id


def generate_custody_return_pdf(custody_data: dict, return_data: dict, lang: str = 'ar', branding: dict = None):
    """
    Generate Custody Return PDF with Professional Design
    التصميم الاحترافي لإرجاع العهدة مع خط القطع
    
    Returns: (pdf_bytes, pdf_hash, integrity_id)
    """
    register_fonts()
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=MARGIN, leftMargin=MARGIN, topMargin=MARGIN, bottomMargin=MARGIN)
    
    elements = []
    
    ref_no = return_data.get('ref_no', 'RET-0000')
    content_hash = hashlib.sha256(f"{ref_no}{return_data.get('id', '')}".encode()).hexdigest()[:8]
    integrity_id = f"DAR-RET-{ref_no[-6:]}-{content_hash}".upper()
    
    # ============ 1. UNIFIED HEADER ============
    elements.append(create_unified_header(branding))
    elements.append(Spacer(1, 4*mm))
    
    # ============ 2. DOCUMENT TITLE ============
    title_ar = 'سند إرجاع عهدة عينية'
    title_en = 'In-Kind Custody Return Receipt'
    elements.append(create_document_title(title_ar, title_en, ref_no))
    elements.append(Spacer(1, 4*mm))
    
    # ============ 3. RETURN DETAILS ============
    data = return_data.get('data', return_data)
    emp_name_ar = data.get('employee_name_ar', '')
    emp_name_en = data.get('employee_name', '')
    
    # Info header
    info_header = create_bilingual_row('تفاصيل الإرجاع', 'Return Details', '', '', is_header=True)
    elements.append(info_header)
    
    # Info rows
    info_rows = [
        ('رقم المرجع', 'Reference No', ref_no, ref_no),
        ('اسم الموظف', 'Employee Name', emp_name_ar, emp_name_en),
        ('اسم العنصر', 'Item Name', data.get('item_name_ar', data.get('item_name', '')), data.get('item_name', '')),
        ('الرقم التسلسلي', 'Serial Number', data.get('serial_number', '-'), data.get('serial_number', '-')),
        ('تاريخ الإرجاع', 'Return Date', return_data.get('executed_at', return_data.get('updated_at', ''))[:10], return_data.get('executed_at', return_data.get('updated_at', ''))[:10]),
    ]
    
    for row in info_rows:
        elements.append(create_bilingual_row(row[0], row[1], row[2], row[3]))
    
    elements.append(Spacer(1, 5*mm))
    
    # ============ 4. SIGNATURES TABLE ============
    signatures = []
    
    # Employee signature (returnee)
    signatures.append({
        'role': 'employee',
        'name_ar': emp_name_ar,
        'name_en': emp_name_en,
        'signed': True,
        'timestamp': return_data.get('created_at', ''),
    })
    
    # HR/Sultan signature (receiver)
    signatures.append({
        'role': 'hr',
        'name_ar': 'سلطان',
        'name_en': 'Sultan',
        'signed': True,
        'timestamp': return_data.get('created_at', ''),
    })
    
    # STAS signature (executor)
    stas_signed = return_data.get('status') == 'executed'
    signatures.append({
        'role': 'stas',
        'name_ar': 'STAS',
        'name_en': 'STAS',
        'signed': stas_signed,
        'timestamp': return_data.get('executed_at', ''),
    })
    
    # Section title
    style_title = ParagraphStyle('sig_title', fontName=ARABIC_FONT_BOLD if ARABIC_FONT_BOLD else 'Helvetica-Bold', 
                                  fontSize=10, alignment=TA_CENTER, textColor=NAVY)
    elements.append(Paragraph(reshape_arabic("التوقيعات | Signatures"), style_title))
    elements.append(Spacer(1, 3*mm))
    
    sig_table = create_signatures_table(signatures, ref_no)
    if sig_table:
        elements.append(sig_table)
    
    elements.append(Spacer(1, 8*mm))
    
    # ============ 5. TEAR-OFF LINE ============
    elements.append(create_tear_off_line())
    elements.append(Spacer(1, 4*mm))
    
    # ============ 6. TEAR-OFF COUPON ============
    coupon = create_tear_off_coupon(
        doc_type='tangible_custody_return',
        ref_no=ref_no,
        employee_name_ar=emp_name_ar,
        employee_name_en=emp_name_en,
        stas_signed=stas_signed,
        stas_timestamp=return_data.get('executed_at', ''),
        branding=branding
    )
    elements.append(coupon)
    
    elements.append(Spacer(1, 4*mm))
    
    # ============ 7. FOOTER ============
    elements.append(create_footer(integrity_id))
    
    # Build PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    return pdf_bytes, pdf_hash, integrity_id
