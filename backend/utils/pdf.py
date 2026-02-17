"""
Professional PDF Generator for DAR AL CODE HR OS
Single A4 Page - Arabic/English Support - QR/Barcode Signatures
Properly handles bilingual text without breaking either language
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
import hashlib
import uuid
import io
import os
import base64
from datetime import datetime, timezone, timedelta

# Constants
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 15 * mm
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)

# Colors
NAVY = colors.Color(0.12, 0.23, 0.37)
LIGHT_GRAY = colors.Color(0.96, 0.96, 0.97)
BORDER_GRAY = colors.Color(0.85, 0.85, 0.87)
TEXT_GRAY = colors.Color(0.4, 0.4, 0.45)

# Font Registration - تسجيل الخطوط العربية
FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')

# استخدام NotoNaskh كخط افتراضي للعربية - الأكثر اكتمالاً
ARABIC_FONT = 'NotoNaskhArabic'
ARABIC_FONT_BOLD = 'NotoNaskhArabicBold'
ENGLISH_FONT = 'Helvetica'
ENGLISH_FONT_BOLD = 'Helvetica-Bold'

# تسجيل الخطوط العربية - مهم للغاية
def register_arabic_fonts():
    """تسجيل جميع الخطوط العربية المتاحة"""
    global ARABIC_FONT, ARABIC_FONT_BOLD
    
    # محاولة تسجيل NotoNaskh أولاً (الأفضل والأكثر اكتمالاً للعربية)
    font_pairs = [
        ('NotoNaskhArabic', 'NotoNaskhArabic-Regular.ttf', 'NotoNaskhArabic-Bold.ttf'),
        ('NotoSansArabic', 'NotoSansArabic-Regular.ttf', 'NotoSansArabic-Bold.ttf'),
    ]
    
    registered_any = False
    for font_name, regular_file, bold_file in font_pairs:
        try:
            regular_path = os.path.join(FONTS_DIR, regular_file)
            bold_path = os.path.join(FONTS_DIR, bold_file)
            
            if os.path.exists(regular_path) and os.path.getsize(regular_path) > 1000:
                pdfmetrics.registerFont(TTFont(font_name, regular_path))
                print(f"✓ Registered font: {font_name}")
                
                if os.path.exists(bold_path) and os.path.getsize(bold_path) > 1000:
                    pdfmetrics.registerFont(TTFont(f'{font_name}Bold', bold_path))
                    print(f"✓ Registered font: {font_name}Bold")
                else:
                    # Fallback: use regular as bold
                    pdfmetrics.registerFont(TTFont(f'{font_name}Bold', regular_path))
                
                # تسجيل Font Family للدعم الكامل
                pdfmetrics.registerFontFamily(
                    font_name,
                    normal=font_name,
                    bold=f'{font_name}Bold',
                )
                
                # تعيين الخط الأول الناجح كافتراضي
                if not registered_any:
                    ARABIC_FONT = font_name
                    ARABIC_FONT_BOLD = f'{font_name}Bold'
                    registered_any = True
                    print(f"★ Default Arabic font set to: {font_name}")
                    
        except Exception as e:
            print(f"✗ Failed to register {font_name}: {e}")
            continue
    
    return registered_any

# تنفيذ التسجيل عند تحميل الموديول
_fonts_registered = register_arabic_fonts()
if not _fonts_registered:
    print("⚠️ WARNING: Arabic fonts not registered. PDF Arabic text may not display correctly.")
else:
    print(f"✓ Arabic fonts ready: {ARABIC_FONT}, {ARABIC_FONT_BOLD}")


def has_arabic(text):
    """Check if text contains Arabic characters"""
    if not text:
        return False
    return any('\u0600' <= c <= '\u06FF' for c in str(text))


def reshape_arabic_text(text):
    """Reshape Arabic text for proper RTL display"""
    if not text:
        return ''
    try:
        text_str = str(text)
        reshaped = arabic_reshaper.reshape(text_str)
        return get_display(reshaped)
    except Exception:
        return str(text)


def format_text_for_pdf(text, target_lang='ar'):
    """
    تنسيق النص للـ PDF مع دعم كامل للعربية
    - يعالج النص العربي بشكل صحيح
    - يحافظ على الأرقام
    """
    if not text:
        return '-'
    
    text = str(text)
    
    # إذا كان النص يحتوي على عربي
    if has_arabic(text):
        return reshape_arabic_text(text)
    
    return text


def format_text_bilingual(text, target_lang='ar'):
    """Alias for format_text_for_pdf for compatibility"""
    return format_text_for_pdf(text, target_lang)


def format_saudi_time(ts):
    """Format timestamp to Saudi Arabia time (UTC+3) with proper date format"""
    if not ts:
        return '-'
    try:
        if isinstance(ts, str):
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        else:
            dt = ts
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        saudi_time = dt + timedelta(hours=3)
        # تنسيق التاريخ مع فواصل: YYYY-MM-DD HH:MM
        return saudi_time.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return str(ts)[:16] if ts else '-'


def format_date_only(date_str):
    """Format date string with proper separators: YYYY-MM-DD"""
    if not date_str:
        return '-'
    try:
        # If already in YYYY-MM-DD format, return as is
        if '-' in str(date_str):
            return str(date_str)
        # If in YYYYMMDD format, add separators
        date_str = str(date_str)
        if len(date_str) == 8 and date_str.isdigit():
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return date_str
    except Exception:
        return str(date_str)


def create_qr_image(data: str, size: int = 18):
    """Create QR code image for PDF"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=2,
            border=1,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return RLImage(buffer, width=size*mm, height=size*mm)
    except:
        return None


def create_barcode_image(code: str, width: int = 40, height: int = 10):
    """Create Code128 barcode for STAS signature"""
    try:
        barcode = code128.Code128(code, barWidth=0.35*mm, barHeight=height*mm)
        d = Drawing(width*mm, (height+3)*mm)
        d.add(barcode)
        return d
    except:
        return None


def get_labels(lang: str):
    """Get all labels based on language"""
    if lang == 'ar':
        return {
            'company': 'شركة دار الكود للاستشارات الهندسية',
            'slogan': 'التميز الهندسي',
            'ref_no': 'رقم المرجع',
            'status': 'الحالة',
            'date': 'التاريخ',
            'integrity_id': 'معرف السلامة',
            'employee_info': 'معلومات الموظف',
            'name': 'الاسم',
            'emp_no': 'الرقم الوظيفي',
            'details': 'تفاصيل المعاملة',
            'approvals': 'سلسلة الموافقات',
            'stage': 'المرحلة',
            'approver': 'المعتمد',
            'action': 'الإجراء',
            'time': 'الوقت',
            'signature': 'التوقيع',
            'comments': 'التعليقات',
            'executed_by': 'تم التنفيذ بواسطة STAS',
            'transaction_id': 'رقم المعاملة',
            # Transaction types
            'leave_request': 'طلب إجازة',
            'finance_60': 'عهدة مالية',
            'tangible_custody': 'عهدة ملموسة',
            'settlement': 'تسوية',
            'contract': 'عقد',
            'salary_advance': 'سلفة راتب',
            # Statuses - تجنب شخصنة STAS
            'executed': 'منفذة',
            'rejected': 'مرفوضة',
            'cancelled': 'ملغاة',
            'stas': 'بانتظار التنفيذ',
            'pending_supervisor': 'بانتظار المشرف',
            'pending_ops': 'بانتظار العمليات',
            'pending_finance': 'بانتظار المالية',
            'pending_ceo': 'لدى سلطان',  # بدلاً من pending_ceo للموظف
            'pending_employee_accept': 'بانتظار الموظف',
            'returned': 'معادة',
            # Stages
            'supervisor': 'المشرف',
            'ops': 'العمليات',
            'finance': 'المالية',
            'ceo': 'CEO',
            'employee_accept': 'الموظف',
            # Actions
            'approve': 'موافقة',
            'approved': 'موافقة',
            'reject': 'رفض',
            'reject_action': 'مرفوض',
            'escalate': 'تصعيد',
            'escalated': 'تم التصعيد',
            # Data fields
            'leave_type': 'نوع الإجازة',
            'start_date': 'من تاريخ',
            'end_date': 'إلى تاريخ',
            'working_days': 'أيام العمل',
            'reason': 'السبب',
            'amount': 'المبلغ',
            'description': 'الوصف',
            'itemname': 'اسم العنصر',
            'estimatedvalue': 'القيمة التقديرية',
            # Leave types
            'annual': 'سنوية',
            'sick': 'مرضية',
            'emergency': 'طارئة',
        }
    else:
        return {
            'company': 'DAR AL CODE ENGINEERING CONSULTANCY',
            'slogan': 'Engineering Excellence',
            'ref_no': 'Reference No',
            'status': 'Status',
            'date': 'Date',
            'integrity_id': 'Integrity ID',
            'employee_info': 'Employee Information',
            'name': 'Name',
            'emp_no': 'Employee No',
            'details': 'Transaction Details',
            'approvals': 'Approval Chain',
            'stage': 'Stage',
            'approver': 'Approver',
            'action': 'Action',
            'time': 'Time',
            'signature': 'Signature',
            'comments': 'Comments',
            'executed_by': 'Executed by STAS',
            'transaction_id': 'Transaction ID',
            # Transaction types
            'leave_request': 'Leave Request',
            'finance_60': 'Financial Custody',
            'tangible_custody': 'Tangible Custody',
            'settlement': 'Settlement',
            'contract': 'Contract',
            'salary_advance': 'Salary Advance',
            # Statuses
            'executed': 'Executed',
            'rejected': 'Rejected',
            'cancelled': 'Cancelled',
            'stas': 'STAS',
            'pending_supervisor': 'Pending Supervisor',
            'pending_ops': 'Pending Operations',
            'pending_finance': 'Pending Finance',
            'pending_ceo': 'Pending CEO',
            'pending_employee_accept': 'Pending Employee',
            # Stages
            'supervisor': 'Supervisor',
            'ops': 'Operations',
            'finance': 'Finance',
            'ceo': 'CEO',
            'employee_accept': 'Employee',
            # Actions
            'approve': 'Approved',
            'approved': 'Approved',
            'reject': 'Rejected',
            'reject_action': 'Rejected',
            'escalate': 'Escalated',
            'escalated': 'Escalated',
            # Data fields
            'leave_type': 'Leave Type',
            'start_date': 'Start Date',
            'end_date': 'End Date',
            'working_days': 'Working Days',
            'reason': 'Reason',
            'amount': 'Amount',
            'description': 'Description',
            'itemname': 'Item Name',
            'estimatedvalue': 'Estimated Value',
            # Leave types
            'annual': 'Annual',
            'sick': 'Sick',
            'emergency': 'Emergency',
        }


def create_logo_image(logo_data: str, max_width: int = 25, max_height: int = 15):
    """Create image from base64 logo data"""
    if not logo_data:
        return None
    try:
        # Remove data:image/xxx;base64, prefix if present
        if ',' in logo_data:
            logo_data = logo_data.split(',')[1]
        
        img_bytes = base64.b64decode(logo_data)
        buffer = io.BytesIO(img_bytes)
        return RLImage(buffer, width=max_width*mm, height=max_height*mm)
    except:
        return None


def generate_transaction_pdf(transaction: dict, employee: dict = None, lang: str = 'ar', branding: dict = None) -> tuple:
    """Generate professional single-page PDF for transaction with proper bilingual support"""
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=12*mm,
        bottomMargin=10*mm,
        leftMargin=MARGIN,
        rightMargin=MARGIN
    )
    
    labels = get_labels(lang)
    
    # Get branding if not provided - use default if not passed
    if branding is None:
        branding = {
            "company_name_en": "DAR AL CODE ENGINEERING CONSULTANCY",
            "company_name_ar": "شركة دار الكود للاستشارات الهندسية",
            "slogan_en": "Engineering Excellence",
            "slogan_ar": "التميز الهندسي",
            "logo_data": None
        }
    
    # Choose fonts based on language
    # استخدام الخط العربي دائماً للنصوص العربية
    if ARABIC_FONT:
        main_font = ARABIC_FONT
        bold_font = ARABIC_FONT_BOLD or ARABIC_FONT
    else:
        main_font = ENGLISH_FONT
        bold_font = ENGLISH_FONT_BOLD
    
    # الخط الإنجليزي للعناوين والأرقام
    english_font = ENGLISH_FONT
    english_bold = ENGLISH_FONT_BOLD
    
    # Styles - استخدام الخط العربي لجميع الأنماط
    styles = {
        'title': ParagraphStyle('title', fontSize=14, fontName=bold_font, textColor=NAVY, alignment=TA_CENTER, spaceAfter=2*mm),
        'subtitle': ParagraphStyle('subtitle', fontSize=11, fontName=bold_font, textColor=NAVY, alignment=TA_CENTER, spaceAfter=4*mm),
        'section': ParagraphStyle('section', fontSize=9, fontName=bold_font, textColor=NAVY, spaceBefore=4*mm, spaceAfter=2*mm),
        'small': ParagraphStyle('small', fontSize=6, fontName=main_font, textColor=TEXT_GRAY, alignment=TA_CENTER),
        'small_bold': ParagraphStyle('small_bold', fontSize=7, fontName=bold_font, textColor=TEXT_GRAY, alignment=TA_CENTER),
        'arabic_text': ParagraphStyle('arabic_text', fontSize=8, fontName=main_font, textColor=colors.black, alignment=TA_RIGHT if lang == 'ar' else TA_LEFT),
    }
    
    elements = []
    integrity_id = str(uuid.uuid4())[:12].upper()
    ref_no = transaction.get('ref_no', 'N/A')
    
    # ============ HEADER WITH LOGO ============
    # Get company name based on language
    company_name = branding.get('company_name_ar' if lang == 'ar' else 'company_name_en', labels['company'])
    slogan = branding.get('slogan_ar' if lang == 'ar' else 'slogan_en', labels['slogan'])
    logo_data = branding.get('logo_data')
    
    # Format company name for display
    company_display = format_text_bilingual(company_name, lang)
    
    # Create header with logo if available
    logo_img = create_logo_image(logo_data)
    if logo_img:
        # Header with logo on left, company name on right
        header_data = [[logo_img, Paragraph(company_display, styles['title'])]]
        header_table = Table(header_data, colWidths=[30*mm, CONTENT_WIDTH - 35*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ]))
        elements.append(header_table)
    else:
        elements.append(Paragraph(company_display, styles['title']))
    
    # Slogan
    if slogan:
        slogan_display = format_text_bilingual(slogan, lang)
        elements.append(Paragraph(slogan_display, styles['small']))
    
    # Line separator
    line_table = Table([['']], colWidths=[CONTENT_WIDTH], rowHeights=[1.5])
    line_table.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, 0), 2, NAVY)]))
    elements.append(line_table)
    elements.append(Spacer(1, 3*mm))
    
    # ============ DOCUMENT TYPE ============
    tx_type = transaction.get('type', '')
    type_label = labels.get(tx_type, tx_type.replace('_', ' ').title())
    doc_type = format_text_bilingual(type_label, lang)
    elements.append(Paragraph(doc_type, styles['subtitle']))
    
    # ============ INFO BOX ============
    status_raw = transaction.get('status', '')
    status_label = labels.get(status_raw, status_raw.replace('_', ' ').title())
    status_display = format_text_bilingual(status_label, lang)
    
    ref_label = format_text_bilingual(labels['ref_no'], lang)
    status_label_text = format_text_bilingual(labels['status'], lang)
    date_label = format_text_bilingual(labels['date'], lang)
    integrity_label = format_text_bilingual(labels['integrity_id'], lang)
    
    info_data = [
        [ref_label, ref_no, status_label_text, status_display],
        [date_label, format_saudi_time(transaction.get('created_at')), integrity_label, integrity_id],
    ]
    
    info_table = Table(info_data, colWidths=[28*mm, 60*mm, 28*mm, 54*mm], rowHeights=[7*mm, 7*mm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('FONTNAME', (0, 0), (-1, -1), main_font),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('TEXTCOLOR', (0, 0), (0, -1), TEXT_GRAY),
        ('TEXTCOLOR', (2, 0), (2, -1), TEXT_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    
    # ============ EMPLOYEE INFO ============
    if employee:
        section_title = format_text_bilingual(labels['employee_info'], lang)
        elements.append(Paragraph(section_title, styles['section']))
        
        # Get name based on language preference
        emp_name = employee.get('full_name_ar' if lang == 'ar' else 'full_name', employee.get('full_name', '-'))
        emp_name_display = format_text_bilingual(emp_name, lang)
        emp_no = str(employee.get('employee_number', '-'))
        
        name_label = format_text_bilingual(labels['name'], lang)
        empno_label = format_text_bilingual(labels['emp_no'], lang)
        
        emp_data = [[name_label, emp_name_display, empno_label, emp_no]]
        emp_table = Table(emp_data, colWidths=[25*mm, 80*mm, 25*mm, 40*mm], rowHeights=[6*mm])
        
        # استخدام الخط العربي لجدول الموظف
        font_to_use = ARABIC_FONT if lang == 'ar' and ARABIC_FONT else main_font
        emp_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font_to_use),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('TEXTCOLOR', (0, 0), (0, 0), TEXT_GRAY),
            ('TEXTCOLOR', (2, 0), (2, 0), TEXT_GRAY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(emp_table)
    
    # ============ TRANSACTION DETAILS ============
    details_title = format_text_bilingual(labels['details'], lang)
    elements.append(Paragraph(details_title, styles['section']))
    
    tx_data = transaction.get('data', {})
    skip_fields = {'employee_name_ar', 'balance_before', 'balance_after', 'adjusted_end_date', 'sick_tier_info', 'leave_type_ar', 'medical_file_url'}
    
    details_rows = []
    for key, value in tx_data.items():
        if key in skip_fields:
            continue
        # Use Arabic name if available and lang is Arabic
        if key == 'employee_name' and lang == 'ar' and 'employee_name_ar' in tx_data:
            value = tx_data['employee_name_ar']
        # Skip complex types
        if isinstance(value, (dict, list)):
            continue
        
        # Get field label
        field_label = labels.get(key, key.replace('_', ' ').title())
        field_label_display = format_text_bilingual(field_label, lang)
        
        # Format value - تأكد من تنسيق جميع القيم العربية
        if value is None:
            formatted_val = '-'
        elif key == 'leave_type':
            # استخدام الترجمة العربية إذا متوفرة
            if lang == 'ar' and 'leave_type_ar' in tx_data:
                formatted_val = format_text_bilingual(tx_data['leave_type_ar'], lang)
            else:
                leave_label = labels.get(str(value), str(value))
                formatted_val = format_text_bilingual(leave_label, lang)
        elif key in ('amount', 'estimatedvalue', 'estimated_value'):
            formatted_val = f"{value} SAR"
        elif key in ('start_date', 'end_date', 'date'):
            # تنسيق التواريخ مع فواصل
            formatted_val = format_date_only(str(value))
        elif key == 'reason':
            # السبب - تأكد من تنسيق العربي
            formatted_val = format_text_bilingual(str(value), lang)
        else:
            formatted_val = format_text_bilingual(str(value), lang)
        
        details_rows.append([field_label_display, formatted_val])
    
    if details_rows:
        # Two-column layout for many fields
        if len(details_rows) > 3:
            mid = (len(details_rows) + 1) // 2
            col1 = details_rows[:mid]
            col2 = details_rows[mid:]
            while len(col2) < len(col1):
                col2.append(['', ''])
            
            combined = []
            for i in range(len(col1)):
                row = [
                    col1[i][0], col1[i][1],
                    col2[i][0] if i < len(col2) else '',
                    col2[i][1] if i < len(col2) else ''
                ]
                combined.append(row)
            
            details_table = Table(combined, colWidths=[28*mm, 55*mm, 28*mm, 55*mm], rowHeights=[6*mm] * len(combined))
        else:
            details_table = Table(details_rows, colWidths=[40*mm, 130*mm], rowHeights=[6*mm] * len(details_rows))
        
        # استخدام الخط العربي لجميع الخلايا
        font_to_use = ARABIC_FONT if lang == 'ar' and ARABIC_FONT else main_font
        details_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font_to_use),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('TEXTCOLOR', (0, 0), (0, -1), TEXT_GRAY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBELOW', (0, 0), (-1, -2), 0.3, BORDER_GRAY),
        ]))
        elements.append(details_table)
    
    # ============ APPROVAL CHAIN WITH QR/BARCODE ============
    approval_chain = transaction.get('approval_chain', [])
    if approval_chain:
        approvals_title = format_text_bilingual(labels['approvals'], lang)
        elements.append(Paragraph(approvals_title, styles['section']))
        
        # Headers
        stage_header = format_text_bilingual(labels['stage'], lang)
        approver_header = format_text_bilingual(labels['approver'], lang)
        action_header = format_text_bilingual(labels['action'], lang)
        time_header = format_text_bilingual(labels['time'], lang)
        sig_header = format_text_bilingual(labels['signature'], lang)
        
        headers = [stage_header, approver_header, action_header, time_header, sig_header]
        approval_data = [headers]
        
        for approval in approval_chain:
            stage = approval.get('stage', '')
            
            # Stage label - STAS and CEO always in English
            if stage in ('stas', 'ceo'):
                stage_display = stage.upper()
            else:
                stage_label = labels.get(stage, stage.title())
                stage_display = format_text_bilingual(stage_label, lang)
            
            # Approver name - CRITICAL: get from approval_chain entry
            approver_name = approval.get('approver_name', approval.get('actor_name', '-'))
            approver_display = format_text_bilingual(approver_name, lang)
            
            # Action
            action_raw = approval.get('status', approval.get('action', ''))
            action_label = labels.get(action_raw, action_raw.title())
            action_display = format_text_bilingual(action_label, lang)
            
            # Timestamp
            timestamp = format_saudi_time(approval.get('timestamp'))
            
            # Signature: BARCODE for STAS with Ref No underneath, QR for others
            approver_id = approval.get('approver_id', '')[:8]
            if stage == 'stas':
                # BARCODE for STAS with Ref No underneath
                sig_code = f"STAS-{ref_no[-8:]}"
                barcode_drawing = create_barcode_image(sig_code, width=35, height=8)
                if barcode_drawing:
                    # Create a table with barcode + ref_no text underneath
                    ref_text = Paragraph(f"<font size='5'>{ref_no}</font>", ParagraphStyle('ref', alignment=TA_CENTER, fontSize=5))
                    sig_table = Table([[barcode_drawing], [ref_text]], colWidths=[40*mm], rowHeights=[10*mm, 4*mm])
                    sig_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ]))
                    sig_img = sig_table
                else:
                    sig_img = f"[STAS-{ref_no[-8:]}]"
            else:
                # QR code for others
                sig_data = f"{stage}-{approver_id}"
                sig_img = create_qr_image(sig_data, size=12)
                if sig_img is None:
                    sig_img = f"[{approver_id[:6]}]"
            
            approval_data.append([stage_display, approver_display, action_display, timestamp, sig_img])
        
        # Calculate row heights
        row_heights = [7*mm] + [14*mm] * (len(approval_data) - 1)
        
        approval_table = Table(
            approval_data,
            colWidths=[28*mm, 40*mm, 25*mm, 35*mm, 42*mm],
            rowHeights=row_heights
        )
        approval_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), bold_font),
            ('FONTNAME', (0, 1), (-1, -1), main_font),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
            ('LINEBELOW', (0, 0), (-1, -1), 0.3, BORDER_GRAY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(approval_table)
    
    # ============ EXECUTION STAMP (STAS BARCODE with Ref No) ============
    if transaction.get('status') == 'executed':
        elements.append(Spacer(1, 4*mm))
        
        executed_label = format_text_bilingual(labels['executed_by'], lang)
        stamp_date = format_saudi_time(transaction.get('executed_at') or transaction.get('updated_at'))
        
        # Create execution barcode with unique transaction identifier
        exec_code = f"EXEC-{ref_no.replace('TXN-', '')}"
        barcode_img = create_barcode_image(exec_code, width=55, height=14)
        
        # Build stamp content (في الصفحة الرئيسية)
        stamp_elements = [
            [Paragraph(executed_label, styles['section'])],
        ]
        stamp_heights = [6*mm]
        
        if barcode_img:
            stamp_elements.append([barcode_img])
            stamp_heights.append(20*mm)
        
        # Ref No clearly displayed under barcode (REQUIRED)
        ref_no_style = ParagraphStyle('ref_bold', fontName=bold_font, fontSize=9, alignment=TA_CENTER, textColor=NAVY)
        stamp_elements.append([Paragraph(f"Ref No: {ref_no}", ref_no_style)])
        stamp_heights.append(6*mm)
        
        stamp_elements.append([Paragraph(stamp_date, styles['small'])])
        stamp_heights.append(4*mm)
        
        stamp_table = Table(stamp_elements, colWidths=[65*mm], rowHeights=stamp_heights)
        stamp_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1.5, NAVY),
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ]))
        
        # Center the stamp
        outer = Table([[stamp_table]], colWidths=[CONTENT_WIDTH])
        outer.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
        elements.append(outer)
    
    # ============ FOOTER ============
    elements.append(Spacer(1, 4*mm))
    footer_line = Table([['']], colWidths=[CONTENT_WIDTH], rowHeights=[0.5])
    footer_line.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, 0), 0.5, BORDER_GRAY)]))
    elements.append(footer_line)
    
    footer_text = f"DAR AL CODE HR OS | {integrity_id} | {format_saudi_time(datetime.now(timezone.utc).isoformat())}"
    elements.append(Spacer(1, 1*mm))
    elements.append(Paragraph(footer_text, styles['small']))
    
    # ============ CUT-OUT BARCODE SECTION (قابل للقص) ============
    if transaction.get('status') == 'executed':
        elements.append(Spacer(1, 8*mm))
        
        # خط منقط للقص
        cut_line_style = ParagraphStyle('cutline', fontSize=8, alignment=TA_CENTER, textColor=TEXT_GRAY)
        cut_text = "- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ✂ قص من هنا ✂ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -"
        elements.append(Paragraph(format_text_bilingual(cut_text, lang), cut_line_style))
        elements.append(Spacer(1, 3*mm))
        
        # مربع الباركود القابل للقص
        exec_code_cut = f"EXEC-{ref_no.replace('TXN-', '')}"
        barcode_cut = create_barcode_image(exec_code_cut, width=60, height=16)
        
        # Get transaction type label
        tx_type = transaction.get('type', '')
        type_label = labels.get(tx_type, tx_type.replace('_', ' ').title())
        type_display = format_text_bilingual(type_label, lang)
        
        # Get employee name
        emp_name = ''
        if employee:
            emp_name = employee.get('full_name_ar' if lang == 'ar' else 'full_name', employee.get('full_name', ''))
            emp_name = format_text_bilingual(emp_name, lang)
        
        # Build cut-out content
        cut_elements = []
        cut_heights = []
        
        # Company name header
        company_header = format_text_bilingual(branding.get('company_name_ar' if lang == 'ar' else 'company_name_en', labels['company']), lang)
        cut_elements.append([Paragraph(f"<font size='7'>{company_header}</font>", ParagraphStyle('cut_header', alignment=TA_CENTER, fontSize=7, textColor=NAVY))])
        cut_heights.append(5*mm)
        
        # Transaction type
        cut_elements.append([Paragraph(f"<font size='8'><b>{type_display}</b></font>", ParagraphStyle('cut_type', alignment=TA_CENTER, fontSize=8))])
        cut_heights.append(5*mm)
        
        # Employee name
        if emp_name:
            cut_elements.append([Paragraph(f"<font size='7'>{emp_name}</font>", ParagraphStyle('cut_emp', alignment=TA_CENTER, fontSize=7))])
            cut_heights.append(4*mm)
        
        # Barcode
        if barcode_cut:
            cut_elements.append([barcode_cut])
            cut_heights.append(22*mm)
        
        # Ref No (bold and clear)
        cut_elements.append([Paragraph(f"<font size='10'><b>{ref_no}</b></font>", ParagraphStyle('cut_ref', alignment=TA_CENTER, fontSize=10, textColor=NAVY))])
        cut_heights.append(6*mm)
        
        # Date
        cut_elements.append([Paragraph(f"<font size='6'>{stamp_date}</font>", ParagraphStyle('cut_date', alignment=TA_CENTER, fontSize=6, textColor=TEXT_GRAY))])
        cut_heights.append(4*mm)
        
        cut_table = Table(cut_elements, colWidths=[80*mm], rowHeights=cut_heights)
        cut_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, NAVY),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ]))
        
        # Center the cut-out
        cut_outer = Table([[cut_table]], colWidths=[CONTENT_WIDTH])
        cut_outer.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
        elements.append(cut_outer)
    
    # Build PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    return pdf_bytes, pdf_hash, integrity_id
