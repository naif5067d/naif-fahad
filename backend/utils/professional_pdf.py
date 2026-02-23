"""
Professional PDF Generator - مولد PDF الاحترافي
============================================================
التصميم الجديد الموحد لجميع مستندات الشركة:
- ترويسة موحدة (عربي + إنجليزي)
- خط القطع (عربي + إنجليزي)  
- جدول توقيعات منظم مع QR لكل موقع
- 2 QR لـ STAS: واحد في الجدول + واحد أسفل خط القطع
============================================================
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image as RLImage
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, String, Line
import arabic_reshaper
from bidi.algorithm import get_display
import qrcode
import hashlib
import uuid
import io
import os
import base64
from datetime import datetime, timezone, timedelta

# ==================== PAGE SETUP ====================
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 12 * mm
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)

# ==================== COLORS ====================
NAVY = colors.Color(0.118, 0.227, 0.373)      # #1E3A5F - الأزرق الداكن
GOLD = colors.Color(0.75, 0.62, 0.35)          # الذهبي
LIGHT_GRAY = colors.Color(0.96, 0.96, 0.97)    # رمادي فاتح
BORDER_GRAY = colors.Color(0.85, 0.85, 0.87)   # رمادي للحدود
TEXT_GRAY = colors.Color(0.4, 0.4, 0.45)       # رمادي للنص
SUCCESS_GREEN = colors.Color(0.1, 0.55, 0.3)   # أخضر للنجاح
WHITE = colors.white

# ==================== FONTS ====================
FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')
ARABIC_FONT = 'NotoNaskhArabic'
ARABIC_FONT_BOLD = 'NotoNaskhArabicBold'
ENGLISH_FONT = 'Helvetica'
ENGLISH_FONT_BOLD = 'Helvetica-Bold'


def register_fonts():
    """تسجيل الخطوط العربية"""
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


# تسجيل الخطوط عند التحميل
_fonts_registered = register_fonts()


def reshape_arabic(text):
    """تحويل النص العربي للعرض الصحيح RTL"""
    if not text:
        return ''
    try:
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except Exception:
        return str(text)


def has_arabic(text):
    """التحقق من وجود نص عربي"""
    if not text:
        return False
    return any('\u0600' <= c <= '\u06FF' for c in str(text))


def format_saudi_time(ts):
    """تحويل الوقت لتوقيت السعودية UTC+3"""
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


def create_qr_image(data: str, size: int = 20, fill_color="black"):
    """إنشاء صورة QR Code"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=3,
            border=1,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color=fill_color, back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return RLImage(buffer, width=size*mm, height=size*mm)
    except:
        return None


def create_logo_image(logo_data: str, width: int = 20, height: int = 20):
    """إنشاء صورة الشعار من base64"""
    if not logo_data:
        return None
    try:
        if ',' in logo_data:
            logo_data = logo_data.split(',')[1]
        img_bytes = base64.b64decode(logo_data)
        buffer = io.BytesIO(img_bytes)
        return RLImage(buffer, width=width*mm, height=height*mm)
    except:
        return None


def create_text_logo(width=20, height=20):
    """إنشاء شعار نصي بديل DAC"""
    d = Drawing(width*mm, height*mm)
    d.add(Rect(0, 0, width*mm, height*mm, fillColor=NAVY, strokeColor=None, rx=3, ry=3))
    d.add(String(2*mm, 7*mm, "D", fontName=ENGLISH_FONT_BOLD, fontSize=12, fillColor=WHITE))
    d.add(String(7*mm, 7*mm, "A", fontName=ENGLISH_FONT_BOLD, fontSize=12, fillColor=GOLD))
    d.add(String(12*mm, 7*mm, "C", fontName=ENGLISH_FONT_BOLD, fontSize=12, fillColor=WHITE))
    return d


# ==================== UNIFIED HEADER / الترويسة الموحدة ====================
def create_unified_header(branding: dict = None):
    """
    إنشاء الترويسة الموحدة للمستندات
    تتضمن: اللوجو في المنتصف + اسم الشركة عربي/إنجليزي + البيانات الرسمية
    """
    company_name_ar = "شركة دار الكود للاستشارات الهندسية"
    company_name_en = "DAR AL CODE Engineering Consultancy"
    slogan_ar = "التميز الهندسي"
    slogan_en = "Engineering Excellence"
    license_no = "5110004935"
    cr_no = "1010463476"
    
    if branding:
        company_name_ar = branding.get('company_name_ar', company_name_ar)
        company_name_en = branding.get('company_name_en', company_name_en)
        slogan_ar = branding.get('slogan_ar', slogan_ar)
        slogan_en = branding.get('slogan_en', slogan_en)
    
    # Styles
    style_ar = ParagraphStyle('header_ar', fontName=ARABIC_FONT_BOLD, fontSize=9, alignment=TA_RIGHT, wordWrap='RTL', leading=11)
    style_en = ParagraphStyle('header_en', fontName=ENGLISH_FONT_BOLD, fontSize=9, alignment=TA_LEFT, leading=11)
    style_small_ar = ParagraphStyle('small_ar', fontName=ARABIC_FONT, fontSize=7, alignment=TA_RIGHT, wordWrap='RTL', textColor=TEXT_GRAY)
    style_small_en = ParagraphStyle('small_en', fontName=ENGLISH_FONT, fontSize=7, alignment=TA_LEFT, textColor=TEXT_GRAY)
    
    # Logo
    logo = None
    if branding and branding.get('logo_data'):
        logo = create_logo_image(branding['logo_data'], 18, 18)
    if not logo:
        logo = create_text_logo(18, 18)
    
    # Left column (English)
    left_content = [
        [Paragraph("Kingdom of Saudi Arabia - Riyadh", style_small_en)],
        [Paragraph(company_name_en, style_en)],
        [Paragraph(f"License: {license_no} | CR: {cr_no}", style_small_en)],
    ]
    left_table = Table(left_content, colWidths=[CONTENT_WIDTH * 0.4])
    left_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    # Right column (Arabic)
    right_content = [
        [Paragraph(reshape_arabic("المملكة العربية السعودية - الرياض"), style_small_ar)],
        [Paragraph(reshape_arabic(company_name_ar), style_ar)],
        [Paragraph(reshape_arabic(f"ترخيص: {license_no} | سجل: {cr_no}"), style_small_ar)],
    ]
    right_table = Table(right_content, colWidths=[CONTENT_WIDTH * 0.4])
    right_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    # Main header table: Left | Logo | Right
    header_table = Table(
        [[left_table, logo, right_table]],
        colWidths=[CONTENT_WIDTH * 0.4, CONTENT_WIDTH * 0.2, CONTENT_WIDTH * 0.4]
    )
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, 0), (-1, 0), 2, NAVY),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    
    return header_table


# ==================== TEAR-OFF LINE / خط القطع ====================
def create_tear_off_line():
    """
    إنشاء خط القطع بالعربي والإنجليزي
    """
    style_center = ParagraphStyle('tear', fontName=ENGLISH_FONT, fontSize=8, alignment=TA_CENTER, textColor=TEXT_GRAY)
    
    # Scissors symbol + dashed line + text
    tear_text = "- - - - - - - -  ✂ Cut Here | قص هنا ✂  - - - - - - - -"
    
    tear_table = Table(
        [[Paragraph(tear_text, style_center)]],
        colWidths=[CONTENT_WIDTH]
    )
    tear_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, BORDER_GRAY),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, BORDER_GRAY),
    ]))
    
    return tear_table


# ==================== SIGNATURES TABLE / جدول التوقيعات ====================
def create_signatures_table(signatures: list, ref_no: str):
    """
    إنشاء جدول التوقيعات المنظم
    كل توقيع في خانة منفصلة مع QR Code واسم الموقع (عربي + إنجليزي)
    
    signatures: قائمة التوقيعات
    [
        {"role": "employee", "name_ar": "أحمد", "name_en": "Ahmed", "signed": True, "timestamp": "..."},
        {"role": "hr", "name_ar": "سلطان", "name_en": "Sultan", "signed": True, "timestamp": "..."},
        {"role": "ceo", "name_ar": "محمد", "name_en": "Mohammed", "signed": True, "timestamp": "..."},
        {"role": "stas", "name_ar": "STAS", "name_en": "STAS", "signed": True, "timestamp": "..."},
    ]
    """
    style_header = ParagraphStyle('sig_header', fontName=ARABIC_FONT_BOLD, fontSize=8, alignment=TA_CENTER, textColor=WHITE, wordWrap='RTL')
    style_name = ParagraphStyle('sig_name', fontName=ARABIC_FONT, fontSize=7, alignment=TA_CENTER, wordWrap='RTL')
    style_name_en = ParagraphStyle('sig_name_en', fontName=ENGLISH_FONT, fontSize=7, alignment=TA_CENTER)
    style_date = ParagraphStyle('sig_date', fontName=ENGLISH_FONT, fontSize=6, alignment=TA_CENTER, textColor=TEXT_GRAY)
    style_status = ParagraphStyle('sig_status', fontName=ARABIC_FONT, fontSize=6, alignment=TA_CENTER, textColor=SUCCESS_GREEN, wordWrap='RTL')
    
    # Build signature cells
    sig_cells = []
    
    for sig in signatures:
        role = sig.get('role', 'unknown')
        name_ar = sig.get('name_ar', '')
        name_en = sig.get('name_en', '')
        signed = sig.get('signed', False)
        timestamp = sig.get('timestamp', '')
        
        # QR code for this signature
        qr_data = f"SIG-{role.upper()}-{ref_no}"
        qr_img = create_qr_image(qr_data, size=15) if signed else None
        
        # Role labels
        role_labels = {
            'employee': ('الموظف', 'Employee'),
            'hr': ('الموارد البشرية', 'HR'),
            'ceo': ('الرئيس التنفيذي', 'CEO'),
            'stas': ('STAS', 'STAS'),
            'ops': ('العمليات', 'Operations'),
            'finance': ('المالية', 'Finance'),
            'supervisor': ('المشرف', 'Supervisor'),
        }
        
        role_ar, role_en = role_labels.get(role, (role, role))
        
        # Build cell content
        cell_content = []
        
        # Header with role
        cell_content.append([Paragraph(reshape_arabic(role_ar), style_header)])
        cell_content.append([Paragraph(role_en, style_name_en)])
        
        # QR or signature line
        if signed and qr_img:
            cell_content.append([qr_img])
        else:
            cell_content.append([Paragraph("________________", style_name_en)])
        
        # Name
        cell_content.append([Paragraph(reshape_arabic(name_ar), style_name)])
        cell_content.append([Paragraph(name_en, style_name_en)])
        
        # Date/Status
        if signed and timestamp:
            cell_content.append([Paragraph(format_saudi_time(timestamp), style_date)])
            cell_content.append([Paragraph(reshape_arabic("✓ تم التوقيع"), style_status)])
        else:
            cell_content.append([Paragraph("____/____/____", style_date)])
        
        # Create cell table
        cell_table = Table(cell_content, colWidths=[40*mm])
        cell_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (0, 0), NAVY),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        
        sig_cells.append(cell_table)
    
    # Calculate columns based on number of signatures
    num_sigs = len(sig_cells)
    if num_sigs == 0:
        return None
    
    col_width = CONTENT_WIDTH / num_sigs
    
    # Create main signatures table
    main_table = Table([sig_cells], colWidths=[col_width] * num_sigs)
    main_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_GRAY),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    
    return main_table


# ==================== TEAR-OFF COUPON / الكوبون ====================
def create_tear_off_coupon(doc_type: str, ref_no: str, employee_name_ar: str, employee_name_en: str, 
                           stas_signed: bool = False, stas_timestamp: str = None, branding: dict = None):
    """
    إنشاء قسيمة القطع (الكوبون) للملفات اليدوية
    يحتوي على QR لـ STAS + ملخص المستند
    """
    company_name_ar = branding.get('company_name_ar', 'شركة دار الكود') if branding else 'شركة دار الكود'
    company_name_en = branding.get('company_name_en', 'DAR AL CODE') if branding else 'DAR AL CODE'
    
    style_title = ParagraphStyle('coupon_title', fontName=ARABIC_FONT_BOLD, fontSize=9, alignment=TA_CENTER, textColor=NAVY, wordWrap='RTL')
    style_title_en = ParagraphStyle('coupon_title_en', fontName=ENGLISH_FONT_BOLD, fontSize=9, alignment=TA_CENTER, textColor=NAVY)
    style_label = ParagraphStyle('coupon_label', fontName=ARABIC_FONT, fontSize=7, alignment=TA_RIGHT, wordWrap='RTL', textColor=TEXT_GRAY)
    style_value = ParagraphStyle('coupon_value', fontName=ARABIC_FONT_BOLD, fontSize=8, alignment=TA_RIGHT, wordWrap='RTL')
    style_value_en = ParagraphStyle('coupon_value_en', fontName=ENGLISH_FONT_BOLD, fontSize=8, alignment=TA_LEFT)
    style_small = ParagraphStyle('coupon_small', fontName=ENGLISH_FONT, fontSize=6, alignment=TA_CENTER, textColor=TEXT_GRAY)
    style_verified = ParagraphStyle('coupon_verified', fontName=ARABIC_FONT_BOLD, fontSize=8, alignment=TA_CENTER, textColor=SUCCESS_GREEN, wordWrap='RTL')
    
    # Document type labels
    doc_types = {
        'leave_request': ('طلب إجازة', 'Leave Request'),
        'tangible_custody': ('عهدة عينية', 'In-Kind Custody'),
        'finance_60': ('عهدة مالية', 'Financial Custody'),
        'settlement': ('مخالصة نهائية', 'Final Settlement'),
        'contract': ('عقد عمل', 'Employment Contract'),
        'salary_advance': ('سلفة راتب', 'Salary Advance'),
        'tangible_custody_return': ('إرجاع عهدة', 'Custody Return'),
    }
    
    doc_type_ar, doc_type_en = doc_types.get(doc_type, (doc_type, doc_type))
    
    # STAS QR for manual files
    stas_qr_data = f"STAS-VERIFY-{ref_no}"
    stas_qr = create_qr_image(stas_qr_data, size=22) if stas_signed else None
    
    # Left side: QR + verification
    left_content = []
    if stas_qr:
        left_content.append([stas_qr])
        left_content.append([Paragraph("STAS QR", style_small)])
        left_content.append([Paragraph(reshape_arabic("للملفات اليدوية"), style_small)])
        if stas_timestamp:
            left_content.append([Paragraph(format_saudi_time(stas_timestamp), style_small)])
    else:
        left_content.append([Paragraph("Pending", style_small)])
    
    left_table = Table(left_content, colWidths=[30*mm])
    left_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    # Center: Document info
    center_content = [
        [Paragraph(reshape_arabic(company_name_ar), style_title)],
        [Paragraph(company_name_en, style_title_en)],
        [Spacer(1, 2*mm)],
        [Paragraph(reshape_arabic(doc_type_ar), style_value)],
        [Paragraph(doc_type_en, style_value_en)],
        [Spacer(1, 2*mm)],
        [Paragraph(f"Ref: {ref_no}", style_value_en)],
        [Spacer(1, 2*mm)],
        [Paragraph(reshape_arabic(employee_name_ar), style_value)],
        [Paragraph(employee_name_en, style_value_en)],
    ]
    
    if stas_signed:
        center_content.append([Spacer(1, 2*mm)])
        center_content.append([Paragraph(reshape_arabic("✓ معاملة صحيحة - Valid Document"), style_verified)])
    
    center_table = Table(center_content, colWidths=[80*mm])
    center_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    # Right side: Another QR for verification
    verify_qr_data = f"VERIFY-{ref_no}"
    verify_qr = create_qr_image(verify_qr_data, size=22)
    
    right_content = []
    if verify_qr:
        right_content.append([verify_qr])
        right_content.append([Paragraph("Verify QR", style_small)])
        right_content.append([Paragraph(reshape_arabic("للتحقق"), style_small)])
    
    right_table = Table(right_content, colWidths=[30*mm])
    right_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    # Main coupon table
    coupon_table = Table(
        [[left_table, center_table, right_table]],
        colWidths=[35*mm, CONTENT_WIDTH - 80*mm, 35*mm]
    )
    coupon_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1.5, NAVY),
        ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.98, 0.98, 1)),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    
    return coupon_table


# ==================== DOCUMENT TITLE / عنوان المستند ====================
def create_document_title(title_ar: str, title_en: str, ref_no: str):
    """إنشاء عنوان المستند مع رقم المرجع"""
    style_title_ar = ParagraphStyle('doc_title_ar', fontName=ARABIC_FONT_BOLD, fontSize=14, alignment=TA_CENTER, textColor=NAVY, wordWrap='RTL')
    style_title_en = ParagraphStyle('doc_title_en', fontName=ENGLISH_FONT_BOLD, fontSize=12, alignment=TA_CENTER, textColor=NAVY)
    style_ref = ParagraphStyle('doc_ref', fontName=ENGLISH_FONT_BOLD, fontSize=10, alignment=TA_CENTER, textColor=TEXT_GRAY)
    
    title_content = [
        [Paragraph(reshape_arabic(title_ar), style_title_ar)],
        [Paragraph(title_en, style_title_en)],
        [Paragraph(f"Reference: {ref_no}", style_ref)],
    ]
    
    title_table = Table(title_content, colWidths=[CONTENT_WIDTH])
    title_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    return title_table


# ==================== BILINGUAL ROW / صف ثنائي اللغة ====================
def create_bilingual_row(label_ar: str, label_en: str, value_ar: str, value_en: str, is_header: bool = False):
    """إنشاء صف ثنائي اللغة"""
    if is_header:
        style_label_ar = ParagraphStyle('row_label_ar', fontName=ARABIC_FONT_BOLD, fontSize=8, alignment=TA_RIGHT, wordWrap='RTL', textColor=WHITE)
        style_label_en = ParagraphStyle('row_label_en', fontName=ENGLISH_FONT_BOLD, fontSize=8, alignment=TA_LEFT, textColor=WHITE)
        bg_color = NAVY
    else:
        style_label_ar = ParagraphStyle('row_label_ar', fontName=ARABIC_FONT, fontSize=7, alignment=TA_RIGHT, wordWrap='RTL', textColor=TEXT_GRAY)
        style_label_en = ParagraphStyle('row_label_en', fontName=ENGLISH_FONT, fontSize=7, alignment=TA_LEFT, textColor=TEXT_GRAY)
        bg_color = LIGHT_GRAY
    
    style_value_ar = ParagraphStyle('row_value_ar', fontName=ARABIC_FONT_BOLD, fontSize=8, alignment=TA_RIGHT, wordWrap='RTL')
    style_value_en = ParagraphStyle('row_value_en', fontName=ENGLISH_FONT_BOLD, fontSize=8, alignment=TA_LEFT)
    
    row_data = [[
        Paragraph(str(value_en), style_value_en),
        Paragraph(label_en, style_label_en),
        Paragraph(reshape_arabic(label_ar), style_label_ar),
        Paragraph(reshape_arabic(str(value_ar)), style_value_ar),
    ]]
    
    col_width = CONTENT_WIDTH / 4
    row_table = Table(row_data, colWidths=[col_width] * 4)
    
    style_list = [
        ('ALIGN', (0, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (3, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]
    
    if is_header:
        style_list.append(('BACKGROUND', (0, 0), (-1, -1), bg_color))
        style_list.append(('TEXTCOLOR', (0, 0), (-1, -1), WHITE))
    else:
        style_list.append(('BACKGROUND', (1, 0), (2, -1), bg_color))
    
    row_table.setStyle(TableStyle(style_list))
    
    return row_table


# ==================== FOOTER / التذييل ====================
def create_footer(integrity_id: str):
    """إنشاء تذييل المستند"""
    style_footer = ParagraphStyle('footer', fontName=ENGLISH_FONT, fontSize=6, alignment=TA_CENTER, textColor=TEXT_GRAY)
    
    now = datetime.now(timezone.utc) + timedelta(hours=3)
    footer_text = f"DAR AL CODE HR OS | {integrity_id} | Generated: {now.strftime('%Y-%m-%d %H:%M')} KSA"
    
    return Paragraph(footer_text, style_footer)


# ==================== MAIN PDF GENERATOR ====================
def generate_professional_transaction_pdf(
    transaction: dict,
    employee: dict = None,
    branding: dict = None,
) -> tuple:
    """
    توليد PDF احترافي للمعاملات
    
    Returns: (pdf_bytes, pdf_hash, integrity_id)
    """
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        leftMargin=MARGIN,
        rightMargin=MARGIN
    )
    
    elements = []
    
    # Generate integrity ID
    ref_no = transaction.get('ref_no', 'TXN-0000')
    tx_id = transaction.get('id', str(uuid.uuid4()))
    content_hash = hashlib.sha256(f"{ref_no}{tx_id}".encode()).hexdigest()[:8]
    integrity_id = f"DAR-{ref_no.replace('TXN-', '')}-{content_hash}".upper()
    
    # Get transaction type
    tx_type = transaction.get('type', 'unknown')
    tx_data = transaction.get('data', {})
    
    # Document titles
    doc_titles = {
        'leave_request': ('طلب إجازة', 'Leave Request'),
        'tangible_custody': ('سند استلام عهدة عينية', 'In-Kind Custody Receipt'),
        'finance_60': ('سند عهدة مالية', 'Financial Custody Receipt'),
        'settlement': ('وثيقة المخالصة النهائية', 'Final Settlement Document'),
        'contract': ('عقد العمل', 'Employment Contract'),
        'salary_advance': ('طلب سلفة راتب', 'Salary Advance Request'),
        'tangible_custody_return': ('سند إرجاع عهدة عينية', 'Custody Return Receipt'),
    }
    
    title_ar, title_en = doc_titles.get(tx_type, (tx_type, tx_type))
    
    # Employee info
    emp_name_ar = ''
    emp_name_en = ''
    emp_no = ''
    if employee:
        emp_name_ar = employee.get('full_name_ar', employee.get('full_name', ''))
        emp_name_en = employee.get('full_name', '')
        emp_no = employee.get('employee_number', '')
    elif tx_data:
        emp_name_ar = tx_data.get('employee_name_ar', tx_data.get('employee_name', ''))
        emp_name_en = tx_data.get('employee_name', '')
    
    # ============ 1. HEADER ============
    elements.append(create_unified_header(branding))
    elements.append(Spacer(1, 4*mm))
    
    # ============ 2. DOCUMENT TITLE ============
    elements.append(create_document_title(title_ar, title_en, ref_no))
    elements.append(Spacer(1, 4*mm))
    
    # ============ 3. MAIN CONTENT ============
    # Status and date info
    status = transaction.get('status', 'pending')
    created_at = transaction.get('created_at', '')
    
    status_labels = {
        'executed': ('منفذة', 'Executed'),
        'rejected': ('مرفوضة', 'Rejected'),
        'cancelled': ('ملغاة', 'Cancelled'),
        'pending_stas': ('بانتظار STAS', 'Pending STAS'),
        'pending_ceo': ('بانتظار CEO', 'Pending CEO'),
        'pending_hr': ('بانتظار HR', 'Pending HR'),
    }
    status_ar, status_en = status_labels.get(status, (status, status))
    
    # Info section header
    info_header = create_bilingual_row('معلومات المعاملة', 'Transaction Info', '', '', is_header=True)
    elements.append(info_header)
    
    # Info rows
    info_rows = [
        ('رقم المرجع', 'Reference No', ref_no, ref_no),
        ('الحالة', 'Status', status_ar, status_en),
        ('التاريخ', 'Date', format_saudi_time(created_at), format_saudi_time(created_at)),
        ('معرف السلامة', 'Integrity ID', integrity_id, integrity_id),
    ]
    
    if emp_name_ar or emp_name_en:
        info_rows.append(('اسم الموظف', 'Employee Name', emp_name_ar, emp_name_en))
    if emp_no:
        info_rows.append(('الرقم الوظيفي', 'Employee No', emp_no, emp_no))
    
    for row in info_rows:
        elements.append(create_bilingual_row(row[0], row[1], row[2], row[3]))
    
    elements.append(Spacer(1, 3*mm))
    
    # Transaction-specific details
    details_header = create_bilingual_row('تفاصيل المعاملة', 'Transaction Details', '', '', is_header=True)
    elements.append(details_header)
    
    # Extract relevant fields based on transaction type
    detail_fields = []
    
    if tx_type == 'leave_request':
        leave_type = tx_data.get('leave_type', '')
        leave_types = {'annual': ('سنوية', 'Annual'), 'sick': ('مرضية', 'Sick'), 'emergency': ('طارئة', 'Emergency')}
        lt_ar, lt_en = leave_types.get(leave_type, (leave_type, leave_type))
        detail_fields = [
            ('نوع الإجازة', 'Leave Type', lt_ar, lt_en),
            ('من تاريخ', 'Start Date', tx_data.get('start_date', ''), tx_data.get('start_date', '')),
            ('إلى تاريخ', 'End Date', tx_data.get('end_date', ''), tx_data.get('end_date', '')),
            ('عدد الأيام', 'Working Days', tx_data.get('working_days', ''), tx_data.get('working_days', '')),
        ]
    elif tx_type in ('tangible_custody', 'tangible_custody_return'):
        detail_fields = [
            ('اسم العنصر', 'Item Name', tx_data.get('item_name_ar', tx_data.get('item_name', '')), tx_data.get('item_name', '')),
            ('الرقم التسلسلي', 'Serial Number', tx_data.get('serial_number', '-'), tx_data.get('serial_number', '-')),
            ('القيمة التقديرية', 'Estimated Value', f"{tx_data.get('estimated_value', 0):,.2f} ريال", f"{tx_data.get('estimated_value', 0):,.2f} SAR"),
        ]
    elif tx_type == 'finance_60':
        detail_fields = [
            ('المبلغ', 'Amount', f"{tx_data.get('amount', 0):,.2f} ريال", f"{tx_data.get('amount', 0):,.2f} SAR"),
            ('الوصف', 'Description', tx_data.get('description', '-'), tx_data.get('description', '-')),
        ]
    elif tx_type == 'salary_advance':
        detail_fields = [
            ('المبلغ', 'Amount', f"{tx_data.get('amount', 0):,.2f} ريال", f"{tx_data.get('amount', 0):,.2f} SAR"),
            ('السبب', 'Reason', tx_data.get('reason', '-'), tx_data.get('reason', '-')),
        ]
    
    for field in detail_fields:
        elements.append(create_bilingual_row(field[0], field[1], field[2], field[3]))
    
    elements.append(Spacer(1, 5*mm))
    
    # ============ 4. SIGNATURES TABLE ============
    # Build signatures list from approval chain
    approval_chain = transaction.get('approval_chain', [])
    signatures = []
    
    # Add employee signature if applicable
    if tx_type in ('leave_request', 'salary_advance', 'finance_60'):
        signatures.append({
            'role': 'employee',
            'name_ar': emp_name_ar,
            'name_en': emp_name_en,
            'signed': True,
            'timestamp': created_at,
        })
    
    # Add approval chain signatures
    for approval in approval_chain:
        stage = approval.get('stage', '')
        if stage == 'stas':
            signatures.append({
                'role': 'stas',
                'name_ar': 'STAS',
                'name_en': 'STAS',
                'signed': True,
                'timestamp': approval.get('timestamp', ''),
            })
        elif stage == 'ceo':
            signatures.append({
                'role': 'ceo',
                'name_ar': 'محمد',
                'name_en': 'Mohammed',
                'signed': True,
                'timestamp': approval.get('timestamp', ''),
            })
        elif stage == 'hr' or stage == 'sultan':
            signatures.append({
                'role': 'hr',
                'name_ar': 'سلطان',
                'name_en': 'Sultan',
                'signed': True,
                'timestamp': approval.get('timestamp', ''),
            })
    
    # Always add STAS if executed
    if status == 'executed':
        has_stas = any(s['role'] == 'stas' for s in signatures)
        if not has_stas:
            signatures.append({
                'role': 'stas',
                'name_ar': 'STAS',
                'name_en': 'STAS',
                'signed': True,
                'timestamp': transaction.get('executed_at', transaction.get('updated_at', '')),
            })
    
    if signatures:
        sig_title_style = ParagraphStyle('sig_title', fontName=ARABIC_FONT_BOLD, fontSize=10, alignment=TA_CENTER, textColor=NAVY, wordWrap='RTL')
        elements.append(Paragraph(reshape_arabic("التوقيعات | Signatures"), sig_title_style))
        elements.append(Spacer(1, 3*mm))
        
        sig_table = create_signatures_table(signatures, ref_no)
        if sig_table:
            elements.append(sig_table)
    
    elements.append(Spacer(1, 8*mm))
    
    # ============ 5. TEAR-OFF LINE ============
    elements.append(create_tear_off_line())
    elements.append(Spacer(1, 4*mm))
    
    # ============ 6. TEAR-OFF COUPON ============
    stas_signed = status == 'executed'
    stas_timestamp = transaction.get('executed_at', '')
    
    coupon = create_tear_off_coupon(
        doc_type=tx_type,
        ref_no=ref_no,
        employee_name_ar=emp_name_ar,
        employee_name_en=emp_name_en,
        stas_signed=stas_signed,
        stas_timestamp=stas_timestamp,
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
