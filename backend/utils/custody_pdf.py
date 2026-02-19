"""
PDF Generator for Financial Custody (العهدة المالية)
Professional bilingual PDF with company branding
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
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
from datetime import datetime, timezone, timedelta

# Constants
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 12 * mm
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)

# Company Colors (DAR AL CODE)
PRIMARY_NAVY = colors.Color(0.12, 0.23, 0.37)  # #1E3A5F
ACCENT_PURPLE = colors.Color(0.65, 0.55, 0.98)  # #A78BFA
LIGHT_BG = colors.Color(0.97, 0.97, 0.98)
BORDER_COLOR = colors.Color(0.85, 0.85, 0.87)
TEXT_DARK = colors.Color(0.04, 0.04, 0.04)
TEXT_MUTED = colors.Color(0.42, 0.45, 0.50)
SUCCESS_GREEN = colors.Color(0.05, 0.65, 0.45)
DANGER_RED = colors.Color(0.85, 0.20, 0.20)

# Font Registration
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
        except:
            continue
    return False


register_fonts()


def reshape_arabic(text):
    """Reshape Arabic text for proper RTL display"""
    if not text:
        return ''
    try:
        text_str = str(text)
        reshaped = arabic_reshaper.reshape(text_str)
        return get_display(reshaped)
    except:
        return str(text)


def format_date(date_str):
    """Format date to YYYY-MM-DD"""
    if not date_str:
        return '-'
    try:
        if isinstance(date_str, str):
            return date_str.split('T')[0] if 'T' in date_str else date_str[:10]
        return str(date_str)[:10]
    except:
        return str(date_str)


def create_qr_image(data: str, size: int = 18):
    """Create QR code image"""
    try:
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=2, border=1)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return RLImage(buffer, width=size*mm, height=size*mm)
    except:
        return None


def create_barcode_image(code: str, width: int = 40, height: int = 8):
    """Create Code128 barcode"""
    try:
        barcode = code128.Code128(code, barWidth=0.35*mm, barHeight=height*mm)
        d = Drawing(width*mm, (height+2)*mm)
        d.add(barcode)
        return d
    except:
        return None


def create_logo_image(logo_data: str, max_width: int = 20, max_height: int = 12):
    """Create image from base64 logo"""
    if not logo_data:
        return None
    try:
        if ',' in logo_data:
            logo_data = logo_data.split(',')[1]
        img_bytes = base64.b64decode(logo_data)
        buffer = io.BytesIO(img_bytes)
        return RLImage(buffer, width=max_width*mm, height=max_height*mm)
    except:
        return None


def make_arabic_para(text, style):
    """Create paragraph with proper Arabic reshaping"""
    return Paragraph(reshape_arabic(text), style)


def make_ltr_para(text, style):
    """Create LTR paragraph (for numbers, dates, English)"""
    return Paragraph(str(text), style)


def generate_custody_pdf(custody: dict, expenses: list, branding: dict = None, lang: str = 'ar') -> bytes:
    """
    Generate professional PDF for financial custody
    
    Args:
        custody: Custody document with all details
        expenses: List of expense items
        branding: Company branding (logo_data, company_name, etc.)
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
    
    # Styles
    style_ar_title = ParagraphStyle(
        'ArTitle', fontName=ARABIC_FONT_BOLD, fontSize=16, alignment=TA_CENTER,
        textColor=PRIMARY_NAVY, wordWrap='RTL', leading=22
    )
    style_ar_subtitle = ParagraphStyle(
        'ArSubtitle', fontName=ARABIC_FONT, fontSize=10, alignment=TA_CENTER,
        textColor=TEXT_MUTED, wordWrap='RTL', leading=14
    )
    style_ar_normal = ParagraphStyle(
        'ArNormal', fontName=ARABIC_FONT, fontSize=9, alignment=TA_RIGHT,
        textColor=TEXT_DARK, wordWrap='RTL', leading=13
    )
    style_ar_bold = ParagraphStyle(
        'ArBold', fontName=ARABIC_FONT_BOLD, fontSize=9, alignment=TA_RIGHT,
        textColor=TEXT_DARK, wordWrap='RTL', leading=13
    )
    style_en_title = ParagraphStyle(
        'EnTitle', fontName='Helvetica-Bold', fontSize=16, alignment=TA_CENTER,
        textColor=PRIMARY_NAVY, leading=22
    )
    style_en_subtitle = ParagraphStyle(
        'EnSubtitle', fontName='Helvetica', fontSize=10, alignment=TA_CENTER,
        textColor=TEXT_MUTED, leading=14
    )
    style_en_normal = ParagraphStyle(
        'EnNormal', fontName='Helvetica', fontSize=9, alignment=TA_LEFT,
        textColor=TEXT_DARK, leading=13
    )
    style_ltr = ParagraphStyle(
        'LTR', fontName='Helvetica', fontSize=9, alignment=TA_CENTER,
        textColor=TEXT_DARK, leading=13
    )
    style_ltr_right = ParagraphStyle(
        'LTRRight', fontName='Helvetica-Bold', fontSize=9, alignment=TA_RIGHT,
        textColor=TEXT_DARK, leading=13
    )
    style_amount = ParagraphStyle(
        'Amount', fontName='Helvetica-Bold', fontSize=9, alignment=TA_RIGHT,
        textColor=DANGER_RED, leading=13
    )
    style_balance = ParagraphStyle(
        'Balance', fontName='Helvetica', fontSize=9, alignment=TA_RIGHT,
        textColor=TEXT_MUTED, leading=13
    )
    
    # ==================== HEADER ====================
    header_data = []
    
    # Logo
    logo_img = None
    if branding and branding.get('logo_data'):
        logo_img = create_logo_image(branding['logo_data'])
    
    # Company name
    company_name = branding.get('company_name', 'DAR AL CODE') if branding else 'DAR AL CODE'
    company_name_ar = branding.get('company_name_ar', 'دار الكود للاستشارات الهندسية') if branding else 'دار الكود للاستشارات الهندسية'
    
    if is_ar:
        title_text = make_arabic_para(company_name_ar, style_ar_title)
        subtitle_text = make_arabic_para('كشف العهدة المالية', style_ar_subtitle)
    else:
        title_text = Paragraph(company_name, style_en_title)
        subtitle_text = Paragraph('Financial Custody Statement', style_en_subtitle)
    
    if logo_img:
        header_data = [[logo_img, [title_text, Spacer(1, 2*mm), subtitle_text]]]
        header_table = Table(header_data, colWidths=[25*mm, CONTENT_WIDTH - 30*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ]))
    else:
        header_data = [[title_text], [subtitle_text]]
        header_table = Table(header_data, colWidths=[CONTENT_WIDTH])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
    
    elements.append(header_table)
    elements.append(Spacer(1, 8*mm))
    
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
    
    if is_ar:
        info_data = [
            [
                make_ltr_para(f'{budget:,.2f}', style_ltr_right),
                make_arabic_para('الميزانية:', style_ar_bold),
                make_ltr_para(custody_number, style_ltr_right),
                make_arabic_para('رقم العهدة:', style_ar_bold),
            ],
            [
                make_ltr_para(f'{spent:,.2f}', style_amount),
                make_arabic_para('المصروف:', style_ar_bold),
                make_ltr_para(created_at, style_ltr_right),
                make_arabic_para('التاريخ:', style_ar_bold),
            ],
            [
                make_ltr_para(f'{remaining:,.2f}', style_balance),
                make_arabic_para('المتبقي:', style_ar_bold),
                make_arabic_para(status_text, style_ar_normal),
                make_arabic_para('الحالة:', style_ar_bold),
            ],
        ]
    else:
        info_data = [
            [
                Paragraph('Custody No:', style_en_normal),
                make_ltr_para(custody_number, style_ltr_right),
                Paragraph('Budget:', style_en_normal),
                make_ltr_para(f'{budget:,.2f} SAR', style_ltr_right),
            ],
            [
                Paragraph('Date:', style_en_normal),
                make_ltr_para(created_at, style_ltr_right),
                Paragraph('Spent:', style_en_normal),
                make_ltr_para(f'{spent:,.2f} SAR', style_amount),
            ],
            [
                Paragraph('Status:', style_en_normal),
                Paragraph(status_text, style_en_normal),
                Paragraph('Remaining:', style_en_normal),
                make_ltr_para(f'{remaining:,.2f} SAR', style_balance),
            ],
        ]
    
    info_table = Table(info_data, colWidths=[CONTENT_WIDTH*0.25]*4)
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, BORDER_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4*mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 3*mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3*mm),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 6*mm))
    
    # ==================== EXPENSES TABLE ====================
    if is_ar:
        table_title = make_arabic_para('تفاصيل المصروفات', style_ar_bold)
    else:
        table_title = Paragraph('Expense Details', ParagraphStyle('', fontName='Helvetica-Bold', fontSize=11, textColor=PRIMARY_NAVY))
    
    elements.append(table_title)
    elements.append(Spacer(1, 3*mm))
    
    # Table header
    if is_ar:
        header_row = [
            make_arabic_para('الرصيد', style_ar_bold),
            make_arabic_para('المبلغ', style_ar_bold),
            make_arabic_para('الوصف', style_ar_bold),
            make_arabic_para('الحساب', style_ar_bold),
            make_arabic_para('الكود', style_ar_bold),
            make_arabic_para('#', style_ar_bold),
        ]
        col_widths = [22*mm, 22*mm, 50*mm, 40*mm, 18*mm, 12*mm]
    else:
        header_row = [
            Paragraph('#', style_en_normal),
            Paragraph('Code', style_en_normal),
            Paragraph('Account', style_en_normal),
            Paragraph('Description', style_en_normal),
            Paragraph('Amount', style_en_normal),
            Paragraph('Balance', style_en_normal),
        ]
        col_widths = [12*mm, 18*mm, 40*mm, 50*mm, 22*mm, 22*mm]
    
    table_data = [header_row]
    
    # Table rows
    running_balance = budget
    for i, exp in enumerate(expenses, 1):
        running_balance -= exp.get('amount', 0)
        
        if is_ar:
            row = [
                make_ltr_para(f'{running_balance:,.2f}', style_balance),
                make_ltr_para(f'-{exp.get("amount", 0):,.2f}', style_amount),
                make_arabic_para(exp.get('description', '-'), style_ar_normal),
                make_arabic_para(exp.get('code_name_ar', '-'), style_ar_normal),
                make_ltr_para(str(exp.get('code', '-')), style_ltr),
                make_ltr_para(str(i), style_ltr),
            ]
        else:
            row = [
                make_ltr_para(str(i), style_ltr),
                make_ltr_para(str(exp.get('code', '-')), style_ltr),
                Paragraph(exp.get('code_name_en', '-'), style_en_normal),
                Paragraph(exp.get('description', '-'), style_en_normal),
                make_ltr_para(f'-{exp.get("amount", 0):,.2f}', style_amount),
                make_ltr_para(f'{running_balance:,.2f}', style_balance),
            ]
        
        table_data.append(row)
    
    # Total row
    if is_ar:
        total_row = [
            make_ltr_para(f'{remaining:,.2f}', ParagraphStyle('', fontName='Helvetica-Bold', fontSize=10, alignment=TA_RIGHT, textColor=SUCCESS_GREEN)),
            make_ltr_para(f'-{spent:,.2f}', ParagraphStyle('', fontName='Helvetica-Bold', fontSize=10, alignment=TA_RIGHT, textColor=DANGER_RED)),
            make_arabic_para('الإجمالي', style_ar_bold),
            '', '', ''
        ]
    else:
        total_row = [
            '', '', '',
            Paragraph('TOTAL', ParagraphStyle('', fontName='Helvetica-Bold', fontSize=10, textColor=PRIMARY_NAVY)),
            make_ltr_para(f'-{spent:,.2f}', ParagraphStyle('', fontName='Helvetica-Bold', fontSize=10, alignment=TA_RIGHT, textColor=DANGER_RED)),
            make_ltr_para(f'{remaining:,.2f}', ParagraphStyle('', fontName='Helvetica-Bold', fontSize=10, alignment=TA_RIGHT, textColor=SUCCESS_GREEN)),
        ]
    
    table_data.append(total_row)
    
    expenses_table = Table(table_data, colWidths=col_widths)
    expenses_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        # Total row
        ('BACKGROUND', (0, -1), (-1, -1), LIGHT_BG),
        ('LINEABOVE', (0, -1), (-1, -1), 1, PRIMARY_NAVY),
        # Grid
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -2), 0.25, BORDER_COLOR),
        # Padding
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5*mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 2*mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2*mm),
    ]))
    
    elements.append(expenses_table)
    elements.append(Spacer(1, 8*mm))
    
    # ==================== SIGNATURES ====================
    sig_title = make_arabic_para('التوقيعات والاعتمادات', style_ar_bold) if is_ar else Paragraph('Signatures & Approvals', ParagraphStyle('', fontName='Helvetica-Bold', fontSize=11, textColor=PRIMARY_NAVY))
    elements.append(sig_title)
    elements.append(Spacer(1, 3*mm))
    
    # QR codes for signatures
    stas_qr = create_qr_image(f"STAS-CUSTODY-{custody_number}-{custody.get('id', '')[:8]}", size=16)
    audit_qr = create_qr_image(f"AUDIT-{custody.get('audited_by', 'pending')}", size=16)
    barcode = create_barcode_image(f"CST-{custody_number}", width=35, height=8)
    
    if is_ar:
        sig_data = [
            [
                make_arabic_para('STAS', style_ar_bold),
                make_arabic_para('المدقق', style_ar_bold),
                make_arabic_para('رقم العهدة', style_ar_bold),
            ],
            [
                stas_qr or '',
                audit_qr or '',
                barcode or '',
            ],
            [
                make_arabic_para(custody.get('executed_by_name', 'بانتظار التنفيذ'), style_ar_normal),
                make_arabic_para(custody.get('audited_by_name', 'بانتظار التدقيق'), style_ar_normal),
                make_ltr_para(custody_number, style_ltr),
            ],
        ]
    else:
        sig_data = [
            [
                Paragraph('Custody No.', style_en_normal),
                Paragraph('Auditor', style_en_normal),
                Paragraph('STAS', style_en_normal),
            ],
            [
                barcode or '',
                audit_qr or '',
                stas_qr or '',
            ],
            [
                make_ltr_para(custody_number, style_ltr),
                Paragraph(custody.get('audited_by_name', 'Pending'), style_en_normal),
                Paragraph(custody.get('executed_by_name', 'Pending'), style_en_normal),
            ],
        ]
    
    sig_table = Table(sig_data, colWidths=[CONTENT_WIDTH/3]*3)
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 3*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
    ]))
    
    elements.append(sig_table)
    elements.append(Spacer(1, 5*mm))
    
    # ==================== FOOTER ====================
    footer_text = f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC | DAR AL CODE HR OS"
    footer = Paragraph(footer_text, ParagraphStyle('', fontName='Helvetica', fontSize=7, alignment=TA_CENTER, textColor=TEXT_MUTED))
    elements.append(footer)
    
    # Build PDF
    doc.build(elements)
    
    return buffer.getvalue()
