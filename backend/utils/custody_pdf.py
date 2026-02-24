"""
PDF Generator for Financial Custody
تصميم احترافي مثل Excel مع ترويسة الشركة وترقيم الصفحات
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, 
    Spacer, PageBreak, Image as RLImage
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
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

# ==================== COMPANY COLORS ====================
NAVY = colors.HexColor('#1E3A5F')
GOLD = colors.HexColor('#BF9E59')
WHITE = colors.white
LIGHT_BG = colors.HexColor('#F8FAFC')
LIGHT_GOLD = colors.HexColor('#FEF3C7')
BORDER_COLOR = colors.HexColor('#E2E8F0')
TEXT_DARK = colors.HexColor('#1E293B')
TEXT_MUTED = colors.HexColor('#64748B')
RED = colors.HexColor('#DC2626')
GREEN = colors.HexColor('#16A34A')

# ==================== FONTS ====================
FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')
ARABIC_FONT = 'Amiri'


def register_fonts():
    """Register Arabic fonts"""
    global ARABIC_FONT
    
    amiri_path = os.path.join(FONTS_DIR, 'Amiri-Regular.ttf')
    if os.path.exists(amiri_path) and os.path.getsize(amiri_path) > 1000:
        try:
            pdfmetrics.registerFont(TTFont('Amiri', amiri_path))
            ARABIC_FONT = 'Amiri'
            return True
        except Exception as e:
            print(f"Font error: {e}")
    
    font_pairs = [
        ('NotoNaskhArabic', 'NotoNaskhArabic-Regular.ttf'),
        ('NotoSansArabic', 'NotoSansArabic-Regular.ttf'),
    ]
    
    for font_name, font_file in font_pairs:
        try:
            font_path = os.path.join(FONTS_DIR, font_file)
            if os.path.exists(font_path) and os.path.getsize(font_path) > 1000:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                ARABIC_FONT = font_name
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
    """Create QR code"""
    try:
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=2, border=1)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#1E3A5F", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return RLImage(buffer, width=size*mm, height=size*mm)
    except Exception:
        return None


def create_logo_image(logo_data: str, max_width: int = 25, max_height: int = 15):
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


# ==================== PAGE TEMPLATE WITH HEADER/FOOTER ====================

class NumberedCanvas(canvas.Canvas):
    """Canvas with page numbers and borders"""
    
    def __init__(self, *args, **kwargs):
        self.company_name = kwargs.pop('company_name', 'دار الكود للاستشارات الهندسية')
        self.report_title = kwargs.pop('report_title', 'تقرير العهدة المالية')
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []
    
    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()
    
    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_border()
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)
    
    def draw_border(self):
        """Draw professional border on every page"""
        # الإطار الخارجي - أزرق داكن
        self.setStrokeColor(NAVY)
        self.setLineWidth(2)
        self.rect(10*mm, 10*mm, PAGE_WIDTH - 20*mm, PAGE_HEIGHT - 20*mm)
        
        # خط ذهبي داخلي
        self.setStrokeColor(GOLD)
        self.setLineWidth(0.5)
        self.rect(12*mm, 12*mm, PAGE_WIDTH - 24*mm, PAGE_HEIGHT - 24*mm)
    
    def draw_page_number(self, page_count):
        """Draw page number at bottom center"""
        # استخدام أرقام عربية بسيطة
        page_text = str(self._pageNumber) + " / " + str(page_count)
        
        self.setFont('Helvetica', 9)
        self.setFillColor(TEXT_MUTED)
        self.drawCentredString(PAGE_WIDTH / 2, 13*mm, page_text)


# ==================== SINGLE CUSTODY PDF ====================

def generate_custody_pdf(custody: dict, expenses: list, branding: dict = None, lang: str = 'ar') -> bytes:
    """Generate PDF for single custody"""
    buffer = io.BytesIO()
    
    company_name = 'دار الكود للاستشارات الهندسية'
    if branding:
        company_name = branding.get('company_name_ar', company_name)
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=MARGIN,
        leftMargin=MARGIN,
        topMargin=25*mm,
        bottomMargin=25*mm,
    )
    
    elements = []
    
    # Styles
    style_title = ParagraphStyle(
        'Title', fontName=ARABIC_FONT, fontSize=16, alignment=TA_CENTER,
        textColor=NAVY, spaceAfter=5
    )
    style_subtitle = ParagraphStyle(
        'Subtitle', fontName=ARABIC_FONT, fontSize=10, alignment=TA_CENTER,
        textColor=GOLD, spaceAfter=10
    )
    style_header = ParagraphStyle(
        'Header', fontName=ARABIC_FONT, fontSize=9, alignment=TA_CENTER,
        textColor=WHITE
    )
    style_cell = ParagraphStyle(
        'Cell', fontName=ARABIC_FONT, fontSize=9, alignment=TA_RIGHT,
        textColor=TEXT_DARK
    )
    style_cell_center = ParagraphStyle(
        'CellCenter', fontName='Helvetica', fontSize=9, alignment=TA_CENTER,
        textColor=TEXT_DARK
    )
    
    # === HEADER ===
    logo_img = None
    if branding and branding.get('logo_data'):
        logo_img = create_logo_image(branding['logo_data'])
    
    # Company header
    if logo_img:
        header_data = [[logo_img, ar_para(company_name, style_title)]]
        header_table = Table(header_data, colWidths=[30*mm, CONTENT_WIDTH - 30*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        elements.append(header_table)
    else:
        elements.append(ar_para(company_name, style_title))
    
    elements.append(ar_para('للاستشارات الهندسية', style_subtitle))
    
    # Decorative line
    line_table = Table([['', '', '']], colWidths=[CONTENT_WIDTH*0.35, CONTENT_WIDTH*0.3, CONTENT_WIDTH*0.35])
    line_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (0, 0), 1.5, GOLD),
        ('LINEABOVE', (1, 0), (1, 0), 3, NAVY),
        ('LINEABOVE', (2, 0), (2, 0), 1.5, GOLD),
    ]))
    elements.append(line_table)
    elements.append(Spacer(1, 5*mm))
    
    # Document title
    elements.append(ar_para('كشف العهدة المالية', ParagraphStyle(
        'DocTitle', fontName=ARABIC_FONT, fontSize=14, alignment=TA_CENTER, textColor=NAVY
    )))
    elements.append(Spacer(1, 8*mm))
    
    # === CUSTODY INFO ===
    custody_number = custody.get('custody_number', '-')
    budget = custody.get('budget', custody.get('total_amount', 0))
    spent = custody.get('spent', 0)
    remaining = custody.get('remaining', 0)
    created_at = format_date(custody.get('created_at', ''))
    
    info_data = [
        [ar_para('القيمة', style_header), ar_para('البيان', style_header)],
        [custody_number, ar_para('رقم العهدة', style_cell)],
        [created_at, ar_para('التاريخ', style_cell)],
        [f'{budget:,.2f}', ar_para('الميزانية', style_cell)],
        [f'{spent:,.2f}', ar_para('المصروف', style_cell)],
        [f'{remaining:,.2f}', ar_para('المتبقي', style_cell)],
    ]
    
    info_table = Table(info_data, colWidths=[50*mm, 50*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), ARABIC_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 1), (-1, -1), LIGHT_BG),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10*mm))
    
    # === EXPENSES TABLE ===
    if expenses:
        elements.append(ar_para('جدول المصروفات', ParagraphStyle(
            'SectionTitle', fontName=ARABIC_FONT, fontSize=12, alignment=TA_RIGHT, textColor=NAVY
        )))
        elements.append(Spacer(1, 3*mm))
        
        # Table header
        exp_header = [
            ar_para('الرصيد', style_header),
            ar_para('المبلغ', style_header),
            ar_para('الوصف', style_header),
            ar_para('البيان', style_header),
            ar_para('الكود', style_header),
            ar_para('م', style_header),
        ]
        exp_data = [exp_header]
        
        running_balance = budget
        for i, exp in enumerate(expenses, 1):
            amount = exp.get('amount', 0)
            running_balance -= amount
            
            exp_data.append([
                Paragraph(f'{running_balance:,.2f}', style_cell_center),
                Paragraph(f'-{amount:,.2f}', ParagraphStyle('Red', fontName='Helvetica', fontSize=9, alignment=TA_CENTER, textColor=RED)),
                ar_para(exp.get('description', '-'), style_cell),
                ar_para(exp.get('code_name_ar', '-'), style_cell),
                Paragraph(str(exp.get('code', '-')), style_cell_center),
                Paragraph(str(i), style_cell_center),
            ])
        
        # Total row
        exp_data.append([
            Paragraph(f'{remaining:,.2f}', ParagraphStyle('Green', fontName='Helvetica-Bold', fontSize=10, alignment=TA_CENTER, textColor=GREEN)),
            Paragraph(f'-{spent:,.2f}', ParagraphStyle('Red', fontName='Helvetica-Bold', fontSize=10, alignment=TA_CENTER, textColor=RED)),
            ar_para('الإجمالي', ParagraphStyle('Total', fontName=ARABIC_FONT, fontSize=10, alignment=TA_CENTER, textColor=NAVY)),
            '', '', ''
        ])
        
        exp_table = Table(exp_data, colWidths=[24*mm, 22*mm, 50*mm, 40*mm, 15*mm, 10*mm])
        exp_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), ARABIC_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('BACKGROUND', (0, -1), (-1, -1), LIGHT_GOLD),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (3, -2), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LINEABOVE', (0, -1), (-1, -1), 1.5, GOLD),
        ]))
        elements.append(exp_table)
    
    elements.append(Spacer(1, 15*mm))
    
    # === QR CODE ===
    qr_data = f"DAR-CUSTODY|{custody_number}|{budget}|{spent}"
    qr_img = create_qr_image(qr_data, size=20)
    if qr_img:
        qr_table = Table([[qr_img, ar_para(f'رقم العهدة: {custody_number}', style_cell)]], colWidths=[25*mm, CONTENT_WIDTH - 25*mm])
        qr_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        elements.append(qr_table)
    
    # Build with numbered canvas
    doc.build(
        elements,
        canvasmaker=lambda *args, **kwargs: NumberedCanvas(
            *args, 
            company_name=company_name,
            report_title='كشف العهدة المالية',
            **kwargs
        )
    )
    
    return buffer.getvalue()


# ==================== MONTHLY REPORT ====================

def generate_monthly_custody_report(custodies: list, month: str, lang: str = 'ar', branding: dict = None, signatures: dict = None):
    """Generate professional monthly custody report"""
    buffer = io.BytesIO()
    
    # Company info
    company_name = 'دار الكود للاستشارات الهندسية'
    company_slogan = 'للاستشارات الهندسية'
    if branding:
        company_name = branding.get('company_name_ar', company_name)
        company_slogan = branding.get('slogan_ar', company_slogan)
    
    # Signature names
    admin_name = 'أ.سلطان الزامل'
    admin_title = 'المدير الإداري'
    accountant_name = 'أ.صلاح صحبي'
    accountant_title = 'المحاسب المالي'
    ceo_name = 'م.محمد الثنيان'
    ceo_title = 'المدير التنفيذي'
    
    if signatures:
        admin_name = signatures.get('admin_name', admin_name)
        admin_title = signatures.get('admin_title', admin_title)
        accountant_name = signatures.get('accountant_name', accountant_name)
        accountant_title = signatures.get('accountant_title', accountant_title)
        ceo_name = signatures.get('ceo_name', ceo_name)
        ceo_title = signatures.get('ceo_title', ceo_title)
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=MARGIN,
        leftMargin=MARGIN,
        topMargin=25*mm,
        bottomMargin=25*mm,
    )
    
    elements = []
    
    # === STYLES ===
    style_company = ParagraphStyle(
        'Company', fontName=ARABIC_FONT, fontSize=18, alignment=TA_CENTER, textColor=NAVY
    )
    style_slogan = ParagraphStyle(
        'Slogan', fontName=ARABIC_FONT, fontSize=10, alignment=TA_CENTER, textColor=GOLD
    )
    style_title = ParagraphStyle(
        'Title', fontName=ARABIC_FONT, fontSize=14, alignment=TA_CENTER, textColor=NAVY, spaceBefore=10
    )
    style_subtitle = ParagraphStyle(
        'Subtitle', fontName=ARABIC_FONT, fontSize=11, alignment=TA_CENTER, textColor=TEXT_MUTED
    )
    style_section = ParagraphStyle(
        'Section', fontName=ARABIC_FONT, fontSize=12, alignment=TA_RIGHT, textColor=NAVY, spaceBefore=15, spaceAfter=5
    )
    style_header = ParagraphStyle(
        'Header', fontName=ARABIC_FONT, fontSize=9, alignment=TA_CENTER, textColor=WHITE
    )
    style_cell = ParagraphStyle(
        'Cell', fontName=ARABIC_FONT, fontSize=9, alignment=TA_RIGHT, textColor=TEXT_DARK
    )
    style_cell_center = ParagraphStyle(
        'CellCenter', fontName='Helvetica', fontSize=9, alignment=TA_CENTER, textColor=TEXT_DARK
    )
    style_sig_name = ParagraphStyle(
        'SigName', fontName=ARABIC_FONT, fontSize=10, alignment=TA_CENTER, textColor=NAVY
    )
    style_sig_title = ParagraphStyle(
        'SigTitle', fontName=ARABIC_FONT, fontSize=9, alignment=TA_CENTER, textColor=TEXT_MUTED
    )
    
    # === HEADER WITH LOGO ===
    logo_img = None
    if branding and branding.get('logo_data'):
        logo_img = create_logo_image(branding['logo_data'])
    
    if logo_img:
        header_data = [[logo_img, ar_para(company_name, style_company)]]
        header_table = Table(header_data, colWidths=[30*mm, CONTENT_WIDTH - 30*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        elements.append(header_table)
    else:
        elements.append(ar_para(company_name, style_company))
    
    elements.append(ar_para(company_slogan, style_slogan))
    
    # Decorative line
    line_table = Table([['', '', '']], colWidths=[CONTENT_WIDTH*0.35, CONTENT_WIDTH*0.3, CONTENT_WIDTH*0.35])
    line_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (0, 0), 1.5, GOLD),
        ('LINEABOVE', (1, 0), (1, 0), 3, NAVY),
        ('LINEABOVE', (2, 0), (2, 0), 1.5, GOLD),
    ]))
    elements.append(line_table)
    elements.append(Spacer(1, 5*mm))
    
    # Report title
    elements.append(ar_para('التقرير الشهري للعهد المالية', style_title))
    elements.append(ar_para('شهر: ' + month, style_subtitle))
    elements.append(Spacer(1, 10*mm))
    
    # === SUMMARY TABLE ===
    total_budget = sum(c.get('budget', 0) or c.get('amount', 0) or 0 for c in custodies)
    total_spent = sum(c.get('spent', 0) or 0 for c in custodies)
    total_remaining = sum(c.get('remaining', 0) or 0 for c in custodies)
    
    summary_data = [
        [ar_para('القيمة (ريال)', style_header), ar_para('البيان', style_header)],
        [f'{total_budget:,.2f}', ar_para('إجمالي الميزانية', style_cell)],
        [f'{total_spent:,.2f}', ar_para('إجمالي المصروفات', style_cell)],
        [f'{total_remaining:,.2f}', ar_para('إجمالي المتبقي', style_cell)],
        [str(len(custodies)), ar_para('عدد العهد', style_cell)],
    ]
    
    summary_table = Table(summary_data, colWidths=[50*mm, 70*mm])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), ARABIC_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 1), (-1, -1), LIGHT_BG),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 15*mm))
    
    # === CUSTODY DETAILS ===
    elements.append(ar_para('تفاصيل العهد والمصروفات', style_section))
    
    for idx, custody in enumerate(custodies):
        custody_num = custody.get('custody_number', str(idx + 1))
        custody_budget = custody.get('budget', 0) or custody.get('amount', 0) or 0
        custody_spent = custody.get('spent', 0) or 0
        custody_remaining = custody.get('remaining', 0) or 0
        expenses = custody.get('expenses', [])
        
        # Custody header
        custody_title = f'عهدة رقم {custody_num} | الميزانية: {custody_budget:,.2f} ريال'
        elements.append(ar_para(custody_title, ParagraphStyle(
            'CustodyTitle', fontName=ARABIC_FONT, fontSize=11, alignment=TA_RIGHT, 
            textColor=NAVY, spaceBefore=10, spaceAfter=5,
            backColor=LIGHT_GOLD, borderPadding=5
        )))
        
        if expenses:
            # Expenses table
            exp_header = [
                ar_para('الرصيد', style_header),
                ar_para('المبلغ', style_header),
                ar_para('الوصف', style_header),
                ar_para('البيان', style_header),
                ar_para('الكود', style_header),
                ar_para('م', style_header),
            ]
            exp_data = [exp_header]
            
            running_balance = custody_budget
            for i, exp in enumerate(expenses, 1):
                amount = exp.get('amount', 0) or 0
                running_balance -= amount
                
                code_name = exp.get('code_name_ar', '') or ''
                description = exp.get('description', '') or ''
                
                balance_color = GREEN if running_balance >= 0 else RED
                
                exp_data.append([
                    Paragraph(f'{running_balance:,.2f}', ParagraphStyle('Balance', fontName='Helvetica', fontSize=9, alignment=TA_CENTER, textColor=balance_color)),
                    Paragraph(f'-{amount:,.2f}', ParagraphStyle('Amount', fontName='Helvetica', fontSize=9, alignment=TA_CENTER, textColor=RED)),
                    ar_para(description, style_cell),
                    ar_para(code_name, style_cell),
                    Paragraph(str(exp.get('code', '')), style_cell_center),
                    Paragraph(str(i), style_cell_center),
                ])
            
            # Total row
            exp_data.append([
                Paragraph(f'{custody_remaining:,.2f}', ParagraphStyle('TotalGreen', fontName='Helvetica-Bold', fontSize=10, alignment=TA_CENTER, textColor=GREEN if custody_remaining >= 0 else RED)),
                Paragraph(f'-{custody_spent:,.2f}', ParagraphStyle('TotalRed', fontName='Helvetica-Bold', fontSize=10, alignment=TA_CENTER, textColor=RED)),
                ar_para('الإجمالي', ParagraphStyle('TotalLabel', fontName=ARABIC_FONT, fontSize=10, alignment=TA_CENTER, textColor=NAVY)),
                '', '', ''
            ])
            
            exp_table = Table(exp_data, colWidths=[24*mm, 22*mm, 50*mm, 40*mm, 15*mm, 10*mm])
            exp_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), ARABIC_FONT),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, 0), (-1, 0), NAVY),
                ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
                ('BACKGROUND', (0, -1), (-1, -1), LIGHT_GOLD),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (2, 1), (3, -2), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LINEABOVE', (0, -1), (-1, -1), 1.5, GOLD),
            ]))
            elements.append(exp_table)
        else:
            elements.append(ar_para('لا توجد مصروفات', style_cell))
        
        elements.append(Spacer(1, 8*mm))
    
    # === SIGNATURES ===
    elements.append(Spacer(1, 15*mm))
    elements.append(line_table)
    elements.append(Spacer(1, 10*mm))
    
    elements.append(ar_para('التوقيعات والاعتمادات', style_section))
    elements.append(Spacer(1, 8*mm))
    
    # Signature table with names
    sig_data = [
        [ar_para(ceo_name, style_sig_name), ar_para(accountant_name, style_sig_name), ar_para(admin_name, style_sig_name)],
        [ar_para(ceo_title, style_sig_title), ar_para(accountant_title, style_sig_title), ar_para(admin_title, style_sig_title)],
        ['_________________', '_________________', '_________________'],
        [ar_para('التاريخ: ___/___/___', style_sig_title), ar_para('التاريخ: ___/___/___', style_sig_title), ar_para('التاريخ: ___/___/___', style_sig_title)],
    ]
    
    sig_table = Table(sig_data, colWidths=[CONTENT_WIDTH/3]*3)
    sig_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), ARABIC_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_GOLD),
        ('BOX', (0, 0), (-1, -1), 1, NAVY),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
    ]))
    elements.append(sig_table)
    elements.append(Spacer(1, 15*mm))
    
    # === QR AND FOOTER ===
    qr_data = f"DAR-MONTHLY|{month}|BUDGET:{total_budget:.0f}|SPENT:{total_spent:.0f}|COUNT:{len(custodies)}"
    qr_img = create_qr_image(qr_data, size=22)
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    if qr_img:
        footer_data = [[
            qr_img,
            [
                ar_para('تاريخ الطباعة: ' + now, style_sig_title),
                Spacer(1, 2*mm),
                ar_para('نظام دار الكود للموارد البشرية', style_sig_title),
            ]
        ]]
        footer_table = Table(footer_data, colWidths=[28*mm, CONTENT_WIDTH - 28*mm])
        footer_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        elements.append(footer_table)
    
    # Build with numbered canvas
    doc.build(
        elements,
        canvasmaker=lambda *args, **kwargs: NumberedCanvas(
            *args,
            company_name=company_name,
            report_title='التقرير الشهري للعهد المالية',
            **kwargs
        )
    )
    
    buffer.seek(0)
    return buffer
