"""
PDF Generator for Financial Custody (العهدة المالية)
تصميم رسمي فخم مع ترويسة الشركة واللوقو
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image as RLImage
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import code128
from reportlab.graphics.shapes import Drawing
import arabic_reshaper
from bidi.algorithm import get_display
import qrcode
import io
import os
import base64
from datetime import datetime, timezone

# ==================== PAGE SETUP ====================
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 15 * mm
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)

# ==================== PREMIUM COLORS ====================
# الألوان الرسمية للشركة
NAVY = colors.Color(0.08, 0.16, 0.28)          # #142840 - كحلي داكن فخم
GOLD = colors.Color(0.75, 0.62, 0.35)          # #BF9E59 - ذهبي
LIGHT_GOLD = colors.Color(0.92, 0.88, 0.78)    # #EBE0C7 - ذهبي فاتح
WHITE = colors.white
LIGHT_BG = colors.Color(0.98, 0.98, 0.99)      # #FAFAFE
BORDER = colors.Color(0.88, 0.88, 0.90)
TEXT_DARK = colors.Color(0.12, 0.12, 0.14)
TEXT_MUTED = colors.Color(0.45, 0.45, 0.50)
SUCCESS = colors.Color(0.10, 0.55, 0.35)       # أخضر
DANGER = colors.Color(0.75, 0.15, 0.15)        # أحمر

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


register_fonts()


# ==================== HELPERS ====================

def reshape_arabic(text):
    """Reshape Arabic text for proper RTL display"""
    if not text:
        return ''
    try:
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except Exception:
        return str(text)


def format_date(date_str):
    """Format date to YYYY-MM-DD"""
    if not date_str:
        return '-'
    try:
        if isinstance(date_str, str):
            return date_str.split('T')[0] if 'T' in date_str else date_str[:10]
        return str(date_str)[:10]
    except Exception:
        return str(date_str)


def create_qr_image(data: str, size: int = 20):
    """Create QR code with navy color"""
    try:
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=2, border=1)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#142840", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return RLImage(buffer, width=size*mm, height=size*mm)
    except Exception:
        return None


def create_barcode_image(code: str, width: int = 45, height: int = 10):
    """Create Code128 barcode"""
    try:
        barcode = code128.Code128(code, barWidth=0.4*mm, barHeight=height*mm)
        d = Drawing(width*mm, (height+2)*mm)
        d.add(barcode)
        return d
    except Exception:
        return None


def create_logo_image(logo_data: str, max_width: int = 28, max_height: int = 18):
    """Create image from base64 logo"""
    if not logo_data:
        return None
    try:
        if ',' in logo_data:
            logo_data = logo_data.split(',')[1]
        img_bytes = base64.b64decode(logo_data)
        buffer = io.BytesIO(img_bytes)
        return RLImage(buffer, width=max_width*mm, height=max_height*mm)
    except Exception:
        return None


def ar_para(text, style):
    """Create Arabic paragraph"""
    return Paragraph(reshape_arabic(text), style)


def ltr_para(text, style):
    """Create LTR paragraph"""
    return Paragraph(str(text), style)


# ==================== MAIN GENERATOR ====================

def generate_custody_pdf(custody: dict, expenses: list, branding: dict = None, lang: str = 'ar') -> bytes:
    """
    Generate premium PDF for financial custody
    
    Args:
        custody: Custody document with all details
        expenses: List of expense items
        branding: Company branding from settings (logo_data, company_name, etc.)
        lang: Language ('ar' or 'en')
    
    Returns:
        PDF bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=MARGIN,
        leftMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )
    
    elements = []
    is_ar = lang == 'ar'
    
    # ==================== STYLES ====================
    style_ar_title = ParagraphStyle(
        'ArTitle', fontName=ARABIC_FONT_BOLD, fontSize=18, alignment=TA_CENTER,
        textColor=NAVY, wordWrap='RTL', leading=24
    )
    style_ar_subtitle = ParagraphStyle(
        'ArSubtitle', fontName=ARABIC_FONT, fontSize=11, alignment=TA_CENTER,
        textColor=GOLD, wordWrap='RTL', leading=15
    )
    style_ar_heading = ParagraphStyle(
        'ArHeading', fontName=ARABIC_FONT_BOLD, fontSize=12, alignment=TA_RIGHT,
        textColor=NAVY, wordWrap='RTL', leading=16
    )
    style_ar_normal = ParagraphStyle(
        'ArNormal', fontName=ARABIC_FONT, fontSize=9, alignment=TA_RIGHT,
        textColor=TEXT_DARK, wordWrap='RTL', leading=13
    )
    style_ar_bold = ParagraphStyle(
        'ArBold', fontName=ARABIC_FONT_BOLD, fontSize=9, alignment=TA_RIGHT,
        textColor=TEXT_DARK, wordWrap='RTL', leading=13
    )
    style_ar_small = ParagraphStyle(
        'ArSmall', fontName=ARABIC_FONT, fontSize=8, alignment=TA_RIGHT,
        textColor=TEXT_MUTED, wordWrap='RTL', leading=11
    )
    style_en_title = ParagraphStyle(
        'EnTitle', fontName='Helvetica-Bold', fontSize=18, alignment=TA_CENTER,
        textColor=NAVY, leading=24
    )
    style_en_subtitle = ParagraphStyle(
        'EnSubtitle', fontName='Helvetica', fontSize=11, alignment=TA_CENTER,
        textColor=GOLD, leading=15
    )
    style_ltr = ParagraphStyle(
        'LTR', fontName='Helvetica', fontSize=9, alignment=TA_CENTER,
        textColor=TEXT_DARK, leading=13
    )
    style_ltr_right = ParagraphStyle(
        'LTRRight', fontName='Helvetica-Bold', fontSize=10, alignment=TA_RIGHT,
        textColor=TEXT_DARK, leading=14
    )
    style_amount_red = ParagraphStyle(
        'AmountRed', fontName='Helvetica-Bold', fontSize=9, alignment=TA_RIGHT,
        textColor=DANGER, leading=13
    )
    style_amount_green = ParagraphStyle(
        'AmountGreen', fontName='Helvetica-Bold', fontSize=9, alignment=TA_RIGHT,
        textColor=SUCCESS, leading=13
    )
    style_footer = ParagraphStyle(
        'Footer', fontName='Helvetica', fontSize=7, alignment=TA_CENTER,
        textColor=TEXT_MUTED, leading=10
    )
    
    # ==================== HEADER WITH LOGO ====================
    # Get company info
    company_name_ar = 'دار الكود للاستشارات الهندسية'
    company_name_en = 'DAR AL CODE Engineering Consultants'
    company_slogan_ar = 'التميز الهندسي'
    company_slogan_en = 'Engineering Excellence'
    
    if branding:
        company_name_ar = branding.get('company_name_ar', company_name_ar)
        company_name_en = branding.get('company_name_en', branding.get('company_name', company_name_en))
        company_slogan_ar = branding.get('slogan_ar', company_slogan_ar)
        company_slogan_en = branding.get('slogan_en', branding.get('slogan', company_slogan_en))
    
    # Logo
    logo_img = None
    if branding and branding.get('logo_data'):
        logo_img = create_logo_image(branding['logo_data'], max_width=30, max_height=20)
    
    # Build header
    if is_ar:
        title_text = ar_para(company_name_ar, style_ar_title)
        subtitle_text = ar_para(company_slogan_ar, style_ar_subtitle)
        doc_title = ar_para('كشف العهدة المالية', style_ar_heading)
    else:
        title_text = Paragraph(company_name_en, style_en_title)
        subtitle_text = Paragraph(company_slogan_en, style_en_subtitle)
        doc_title = Paragraph('FINANCIAL CUSTODY STATEMENT', ParagraphStyle('', fontName='Helvetica-Bold', fontSize=12, alignment=TA_CENTER, textColor=NAVY))
    
    # Header table with logo
    if logo_img:
        if is_ar:
            # Logo on right for Arabic
            header_data = [[[title_text, Spacer(1, 1*mm), subtitle_text], logo_img]]
            header_table = Table(header_data, colWidths=[CONTENT_WIDTH - 35*mm, 35*mm])
        else:
            # Logo on left for English
            header_data = [[logo_img, [title_text, Spacer(1, 1*mm), subtitle_text]]]
            header_table = Table(header_data, colWidths=[35*mm, CONTENT_WIDTH - 35*mm])
    else:
        header_data = [[title_text], [subtitle_text]]
        header_table = Table(header_data, colWidths=[CONTENT_WIDTH])
    
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    
    elements.append(header_table)
    elements.append(Spacer(1, 4*mm))
    
    # Decorative line
    line_data = [['', '', '']]
    line_table = Table(line_data, colWidths=[CONTENT_WIDTH*0.35, CONTENT_WIDTH*0.3, CONTENT_WIDTH*0.35])
    line_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (0, 0), 1.5, GOLD),
        ('LINEABOVE', (1, 0), (1, 0), 3, NAVY),
        ('LINEABOVE', (2, 0), (2, 0), 1.5, GOLD),
    ]))
    elements.append(line_table)
    elements.append(Spacer(1, 4*mm))
    
    # Document title
    elements.append(doc_title)
    elements.append(Spacer(1, 6*mm))
    
    # ==================== CUSTODY INFO BOX ====================
    custody_number = custody.get('custody_number', '-')
    budget = custody.get('budget', custody.get('total_amount', 0))
    spent = custody.get('spent', 0)
    remaining = custody.get('remaining', 0)
    status = custody.get('status', 'open')
    created_at = format_date(custody.get('created_at', ''))
    created_by = custody.get('created_by_name', '-')
    
    status_map_ar = {
        'open': 'مفتوحة', 'pending_audit': 'بانتظار التدقيق',
        'approved': 'معتمدة', 'executed': 'منفذة', 'closed': 'مغلقة'
    }
    status_map_en = {
        'open': 'Open', 'pending_audit': 'Pending Audit',
        'approved': 'Approved', 'executed': 'Executed', 'closed': 'Closed'
    }
    status_text = status_map_ar.get(status, status) if is_ar else status_map_en.get(status, status)
    
    # Info box with premium styling
    if is_ar:
        info_data = [
            [
                ltr_para(f'{budget:,.2f}', style_ltr_right),
                ar_para('الميزانية', style_ar_bold),
                ltr_para(custody_number, style_ltr_right),
                ar_para('رقم العهدة', style_ar_bold),
            ],
            [
                ltr_para(f'{spent:,.2f}', style_amount_red),
                ar_para('المصروف', style_ar_bold),
                ltr_para(created_at, style_ltr_right),
                ar_para('تاريخ الإنشاء', style_ar_bold),
            ],
            [
                ltr_para(f'{remaining:,.2f}', style_amount_green),
                ar_para('المتبقي', style_ar_bold),
                ar_para(status_text, style_ar_normal),
                ar_para('الحالة', style_ar_bold),
            ],
            [
                '', '',
                ar_para(created_by, style_ar_small),
                ar_para('أنشأها', style_ar_bold),
            ],
        ]
    else:
        info_data = [
            [
                Paragraph('Custody No:', style_ar_bold),
                ltr_para(custody_number, style_ltr_right),
                Paragraph('Budget:', style_ar_bold),
                ltr_para(f'{budget:,.2f} SAR', style_ltr_right),
            ],
            [
                Paragraph('Date:', style_ar_bold),
                ltr_para(created_at, style_ltr_right),
                Paragraph('Spent:', style_ar_bold),
                ltr_para(f'{spent:,.2f} SAR', style_amount_red),
            ],
            [
                Paragraph('Status:', style_ar_bold),
                Paragraph(status_text, style_ar_normal),
                Paragraph('Remaining:', style_ar_bold),
                ltr_para(f'{remaining:,.2f} SAR', style_amount_green),
            ],
        ]
    
    info_table = Table(info_data, colWidths=[CONTENT_WIDTH*0.25]*4)
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 1, NAVY),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, BORDER),
        ('LINEBELOW', (0, 1), (-1, 1), 0.5, BORDER),
        ('LINEBELOW', (0, 2), (-1, 2), 0.5, BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4*mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 3*mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3*mm),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 8*mm))
    
    # ==================== EXPENSES TABLE ====================
    if is_ar:
        section_title = ar_para('تفاصيل المصروفات', style_ar_heading)
    else:
        section_title = Paragraph('EXPENSE DETAILS', ParagraphStyle('', fontName='Helvetica-Bold', fontSize=11, textColor=NAVY))
    
    elements.append(section_title)
    elements.append(Spacer(1, 3*mm))
    
    # Table header
    if is_ar:
        header_row = [
            ar_para('الرصيد', style_ar_bold),
            ar_para('المبلغ', style_ar_bold),
            ar_para('الوصف', style_ar_bold),
            ar_para('الحساب', style_ar_bold),
            ar_para('الكود', style_ar_bold),
            ar_para('م', style_ar_bold),
        ]
        col_widths = [24*mm, 24*mm, 48*mm, 42*mm, 16*mm, 10*mm]
    else:
        header_row = [
            Paragraph('#', style_ar_bold),
            Paragraph('Code', style_ar_bold),
            Paragraph('Account', style_ar_bold),
            Paragraph('Description', style_ar_bold),
            Paragraph('Amount', style_ar_bold),
            Paragraph('Balance', style_ar_bold),
        ]
        col_widths = [10*mm, 16*mm, 42*mm, 48*mm, 24*mm, 24*mm]
    
    table_data = [header_row]
    
    # Table rows
    running_balance = budget
    for i, exp in enumerate(expenses, 1):
        running_balance -= exp.get('amount', 0)
        
        if is_ar:
            row = [
                ltr_para(f'{running_balance:,.2f}', style_amount_green if running_balance > 0 else style_amount_red),
                ltr_para(f'-{exp.get("amount", 0):,.2f}', style_amount_red),
                ar_para(exp.get('description', '-'), style_ar_normal),
                ar_para(exp.get('code_name_ar', '-'), style_ar_small),
                ltr_para(str(exp.get('code', '-')), style_ltr),
                ltr_para(str(i), style_ltr),
            ]
        else:
            row = [
                ltr_para(str(i), style_ltr),
                ltr_para(str(exp.get('code', '-')), style_ltr),
                Paragraph(exp.get('code_name_en', '-'), style_ar_small),
                Paragraph(exp.get('description', '-'), style_ar_normal),
                ltr_para(f'-{exp.get("amount", 0):,.2f}', style_amount_red),
                ltr_para(f'{running_balance:,.2f}', style_amount_green if running_balance > 0 else style_amount_red),
            ]
        
        table_data.append(row)
    
    # Total row
    if is_ar:
        total_row = [
            ltr_para(f'{remaining:,.2f}', ParagraphStyle('', fontName='Helvetica-Bold', fontSize=10, alignment=TA_RIGHT, textColor=SUCCESS)),
            ltr_para(f'-{spent:,.2f}', ParagraphStyle('', fontName='Helvetica-Bold', fontSize=10, alignment=TA_RIGHT, textColor=DANGER)),
            ar_para('الإجمالي', ParagraphStyle('', fontName=ARABIC_FONT_BOLD, fontSize=10, alignment=TA_RIGHT, textColor=NAVY, wordWrap='RTL')),
            '', '', ''
        ]
    else:
        total_row = [
            '', '', '',
            Paragraph('TOTAL', ParagraphStyle('', fontName='Helvetica-Bold', fontSize=10, textColor=NAVY)),
            ltr_para(f'-{spent:,.2f}', ParagraphStyle('', fontName='Helvetica-Bold', fontSize=10, alignment=TA_RIGHT, textColor=DANGER)),
            ltr_para(f'{remaining:,.2f}', ParagraphStyle('', fontName='Helvetica-Bold', fontSize=10, alignment=TA_RIGHT, textColor=SUCCESS)),
        ]
    
    table_data.append(total_row)
    
    expenses_table = Table(table_data, colWidths=col_widths)
    expenses_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        # Total row
        ('BACKGROUND', (0, -1), (-1, -1), LIGHT_GOLD),
        ('LINEABOVE', (0, -1), (-1, -1), 2, GOLD),
        # Alternating rows
        *[('BACKGROUND', (0, i), (-1, i), LIGHT_BG) for i in range(2, len(table_data)-1, 2)],
        # Grid
        ('BOX', (0, 0), (-1, -1), 1, NAVY),
        ('INNERGRID', (0, 0), (-1, -2), 0.25, BORDER),
        # Padding
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 2*mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2*mm),
    ]))
    
    elements.append(expenses_table)
    elements.append(Spacer(1, 10*mm))
    
    # ==================== SIGNATURES ====================
    if is_ar:
        sig_title = ar_para('التوقيعات والاعتمادات', style_ar_heading)
    else:
        sig_title = Paragraph('SIGNATURES & APPROVALS', ParagraphStyle('', fontName='Helvetica-Bold', fontSize=11, textColor=NAVY))
    
    elements.append(sig_title)
    elements.append(Spacer(1, 4*mm))
    
    # QR codes
    stas_qr = create_qr_image(f"STAS-{custody_number}-{custody.get('id', '')[:8]}", size=18)
    audit_qr = create_qr_image(f"AUDIT-{custody.get('audited_by', 'pending')}", size=18)
    barcode = create_barcode_image(f"CST-{custody_number}", width=40, height=10)
    
    # أسماء المدقق والمنفذ - نستخدم النص مباشرة بدون تحويل
    audited_by_raw = custody.get('audited_by_name') or ('بانتظار التدقيق' if is_ar else 'Pending')
    executed_by_raw = custody.get('executed_by_name') or ('بانتظار التنفيذ' if is_ar else 'Pending')
    
    # Style للأسماء (بدون reshape لأن الأسماء قد تكون إنجليزية)
    style_name = ParagraphStyle('Name', fontName='Helvetica', fontSize=9, alignment=TA_CENTER, textColor=TEXT_DARK, leading=12)
    
    if is_ar:
        sig_data = [
            [
                Paragraph('STAS', ParagraphStyle('', fontName='Helvetica-Bold', fontSize=10, alignment=TA_CENTER, textColor=NAVY)),
                ar_para('المدقق', style_ar_bold),
                ar_para('رقم العهدة', style_ar_bold),
            ],
            [
                stas_qr or '',
                audit_qr or '',
                barcode or '',
            ],
            [
                Paragraph(executed_by_raw, style_name),
                Paragraph(audited_by_raw, style_name),
                ltr_para(custody_number, style_ltr),
            ],
        ]
    else:
        sig_data = [
            [
                Paragraph('Custody No.', style_ar_bold),
                Paragraph('Auditor', style_ar_bold),
                Paragraph('STAS', style_ar_bold),
            ],
            [
                barcode or '',
                audit_qr or '',
                stas_qr or '',
            ],
            [
                ltr_para(custody_number, style_ltr),
                Paragraph(audited_by, style_ar_small),
                Paragraph(executed_by, style_ar_small),
            ],
        ]
    
    sig_table = Table(sig_data, colWidths=[CONTENT_WIDTH/3]*3)
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_GOLD),
        ('BOX', (0, 0), (-1, -1), 1, NAVY),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 3*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
    ]))
    
    elements.append(sig_table)
    elements.append(Spacer(1, 8*mm))
    
    # ==================== FOOTER ====================
    # Decorative line
    elements.append(line_table)
    elements.append(Spacer(1, 3*mm))
    
    footer_text = f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC"
    if is_ar:
        footer_text += " | نظام دار الكود للموارد البشرية"
    else:
        footer_text += " | DAR AL CODE HR System"
    
    elements.append(Paragraph(footer_text, style_footer))
    
    # Build PDF
    doc.build(elements)
    
    return buffer.getvalue()
