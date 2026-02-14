"""
Professional PDF Generator for DAR AL CODE HR OS
With QR Signatures, Language Support (Arabic/English), and Barcode for STAS
"""
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image as RLImage
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display
import hashlib
import uuid
import io
import os
import qrcode
from datetime import datetime, timezone

# Register Arabic fonts
FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')
try:
    pdfmetrics.registerFont(TTFont('NotoArabic', os.path.join(FONTS_DIR, 'NotoSansArabic-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('NotoArabicBold', os.path.join(FONTS_DIR, 'NotoSansArabic-Bold.ttf')))
    ARABIC_FONT_AVAILABLE = True
except Exception:
    ARABIC_FONT_AVAILABLE = False

# Brand Colors
NAVY_DARK = colors.Color(0.12, 0.23, 0.37)
LAVENDER = colors.Color(0.65, 0.55, 0.98)
GRAY_LIGHT = colors.Color(0.96, 0.96, 0.97)
GRAY_BORDER = colors.Color(0.88, 0.88, 0.90)
TEXT_DARK = colors.Color(0.04, 0.04, 0.04)


def process_arabic_text(text):
    """Process Arabic text for proper RTL display in PDF"""
    if not text:
        return ''
    text_str = str(text)
    has_arabic = any('\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F' for char in text_str)
    if has_arabic and ARABIC_FONT_AVAILABLE:
        try:
            reshaped = arabic_reshaper.reshape(text_str)
            return get_display(reshaped)
        except Exception:
            return text_str
    return text_str


def safe_text(text, lang='ar'):
    """Safely process text based on language"""
    if not text:
        return '-'
    if lang == 'ar':
        return process_arabic_text(str(text))
    return str(text)


def format_saudi_time(iso_timestamp):
    """Convert ISO timestamp to Saudi Arabia time (UTC+3)"""
    if not iso_timestamp:
        return '-'
    try:
        if isinstance(iso_timestamp, str):
            if 'T' in iso_timestamp:
                dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
            else:
                return iso_timestamp[:19]
        else:
            dt = iso_timestamp
        from datetime import timedelta
        saudi_time = dt + timedelta(hours=3)
        return saudi_time.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return str(iso_timestamp)[:16] if iso_timestamp else '-'


def generate_qr_code(data, size=25):
    """Generate QR code as ReportLab Image"""
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=3, border=1)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return RLImage(buffer, width=size*mm, height=size*mm)


def generate_barcode_text(code):
    """Generate a simple text barcode representation"""
    return f"|||{code}|||"


# Translations
TRANSLATIONS = {
    'ar': {
        'company_name': 'شركة دار الكود للاستشارات الهندسية',
        'document_title': 'مستند رسمي',
        'ref_no': 'رقم المرجع',
        'status': 'الحالة',
        'date': 'التاريخ',
        'integrity_id': 'معرف السلامة',
        'employee_info': 'معلومات الموظف',
        'name': 'الاسم',
        'employee_no': 'رقم الموظف',
        'department': 'القسم',
        'transaction_details': 'تفاصيل المعاملة',
        'timeline': 'الجدول الزمني',
        'approval_chain': 'سلسلة الموافقات',
        'stage': 'المرحلة',
        'approver': 'المعتمد',
        'note': 'ملاحظة',
        'signature': 'التوقيع',
        'system_signature': 'توقيع النظام',
        'footer': 'نظام دار الكود للموارد البشرية',
        'generated': 'تم الإنشاء',
        'saudi_time': 'توقيت السعودية',
        # Transaction types
        'leave_request': 'طلب إجازة',
        'finance_60': 'عهدة مالية',
        'settlement': 'تسوية',
        'contract': 'عقد',
        'tangible_custody': 'عهدة ملموسة',
        'tangible_custody_return': 'إرجاع عهدة',
        'salary_advance': 'سلفة راتب',
        'letter_request': 'طلب خطاب',
        # Statuses
        'executed': 'منفذة',
        'rejected': 'مرفوضة',
        'cancelled': 'ملغاة',
        'pending_supervisor': 'بانتظار المشرف',
        'pending_ops': 'بانتظار العمليات',
        'pending_finance': 'بانتظار المالية',
        'pending_ceo': 'بانتظار CEO',
        'stas': 'STAS',
        'pending_employee_accept': 'بانتظار الموظف',
        # Stages
        'supervisor': 'المشرف',
        'ops': 'العمليات',
        'finance': 'المالية',
        'ceo': 'CEO',
        'employee_accept': 'قبول الموظف',
        # Events
        'created': 'تم الإنشاء',
        'approved': 'تمت الموافقة',
        'reject': 'تم الرفض',
        'escalated': 'تم التصعيد',
        'returned': 'تم الإرجاع',
        # Data labels
        'leave_type': 'نوع الإجازة',
        'start_date': 'تاريخ البداية',
        'end_date': 'تاريخ النهاية',
        'working_days': 'أيام العمل',
        'reason': 'السبب',
        'amount': 'المبلغ',
        'description': 'الوصف',
        'itemname': 'اسم العنصر',
        'serial_number': 'الرقم التسلسلي',
        'estimatedvalue': 'القيمة التقديرية',
        'employee_name': 'اسم الموظف',
        # Leave types
        'annual': 'سنوية',
        'sick': 'مرضية',
        'emergency': 'طارئة',
    },
    'en': {
        'company_name': 'DAR AL CODE ENGINEERING CONSULTANCY',
        'document_title': 'Official Document',
        'ref_no': 'Reference No',
        'status': 'Status',
        'date': 'Date',
        'integrity_id': 'Integrity ID',
        'employee_info': 'Employee Information',
        'name': 'Name',
        'employee_no': 'Employee No',
        'department': 'Department',
        'transaction_details': 'Transaction Details',
        'timeline': 'Timeline',
        'approval_chain': 'Approval Chain',
        'stage': 'Stage',
        'approver': 'Approver',
        'note': 'Note',
        'signature': 'Signature',
        'system_signature': 'System Signature',
        'footer': 'DAR AL CODE HR OS',
        'generated': 'Generated',
        'saudi_time': 'Saudi Time',
        # Transaction types
        'leave_request': 'Leave Request',
        'finance_60': 'Financial Custody',
        'settlement': 'Settlement',
        'contract': 'Contract',
        'tangible_custody': 'Tangible Custody',
        'tangible_custody_return': 'Custody Return',
        'salary_advance': 'Salary Advance',
        'letter_request': 'Letter Request',
        # Statuses
        'executed': 'Executed',
        'rejected': 'Rejected',
        'cancelled': 'Cancelled',
        'pending_supervisor': 'Pending Supervisor',
        'pending_ops': 'Pending Ops',
        'pending_finance': 'Pending Finance',
        'pending_ceo': 'Pending CEO',
        'stas': 'STAS',
        'pending_employee_accept': 'Pending Employee',
        # Stages
        'supervisor': 'Supervisor',
        'ops': 'Operations',
        'finance': 'Finance',
        'ceo': 'CEO',
        'employee_accept': 'Employee Accept',
        # Events
        'created': 'Created',
        'approved': 'Approved',
        'reject': 'Rejected',
        'escalated': 'Escalated',
        'returned': 'Returned',
        # Data labels
        'leave_type': 'Leave Type',
        'start_date': 'Start Date',
        'end_date': 'End Date',
        'working_days': 'Working Days',
        'reason': 'Reason',
        'amount': 'Amount',
        'description': 'Description',
        'itemname': 'Item Name',
        'serial_number': 'Serial Number',
        'estimatedvalue': 'Estimated Value',
        'employee_name': 'Employee Name',
        # Leave types
        'annual': 'Annual',
        'sick': 'Sick',
        'emergency': 'Emergency',
    }
}


def t(key, lang='ar'):
    """Get translation for key"""
    return TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)


def generate_transaction_pdf(transaction: dict, employee: dict = None, lang: str = 'ar') -> tuple:
    """Generate professional PDF with QR signatures and language support"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        topMargin=15*mm, 
        bottomMargin=15*mm, 
        leftMargin=15*mm, 
        rightMargin=15*mm
    )
    
    # Fonts based on language
    if lang == 'ar' and ARABIC_FONT_AVAILABLE:
        base_font = 'NotoArabic'
        bold_font = 'NotoArabicBold'
        alignment = TA_RIGHT
    else:
        base_font = 'Helvetica'
        bold_font = 'Helvetica-Bold'
        alignment = TA_LEFT
    
    # Styles
    title_style = ParagraphStyle(
        'Title', 
        fontSize=16, 
        fontName=bold_font,
        textColor=NAVY_DARK,
        alignment=TA_CENTER,
        spaceAfter=3*mm
    )
    
    section_style = ParagraphStyle(
        'Section', 
        fontSize=12, 
        fontName=bold_font,
        textColor=NAVY_DARK,
        spaceBefore=8*mm,
        spaceAfter=4*mm,
        alignment=alignment
    )
    
    label_style = ParagraphStyle(
        'Label', 
        fontSize=9, 
        fontName=base_font,
        textColor=colors.Color(0.4, 0.4, 0.4),
        alignment=alignment
    )
    
    value_style = ParagraphStyle(
        'Value', 
        fontSize=10, 
        fontName=bold_font,
        textColor=TEXT_DARK,
        alignment=alignment
    )
    
    footer_style = ParagraphStyle(
        'Footer', 
        fontSize=7, 
        fontName=base_font,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    
    elements = []
    integrity_id = str(uuid.uuid4())[:12].upper()
    
    # ═══════════════════════════════════════════════════════════════
    # HEADER
    # ═══════════════════════════════════════════════════════════════
    
    company_name = safe_text(t('company_name', lang), lang)
    elements.append(Paragraph(company_name, title_style))
    
    # Divider
    divider = Table([['']], colWidths=[180*mm])
    divider.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 2, NAVY_DARK),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(divider)
    elements.append(Spacer(1, 5*mm))
    
    # Document Type Title
    tx_type = transaction.get('type', 'transaction')
    doc_title = safe_text(t(tx_type, lang), lang)
    doc_title_style = ParagraphStyle('DocTitle', fontSize=14, fontName=bold_font, textColor=TEXT_DARK, alignment=TA_CENTER, spaceAfter=5*mm)
    elements.append(Paragraph(doc_title, doc_title_style))
    
    # ═══════════════════════════════════════════════════════════════
    # REFERENCE INFO BOX
    # ═══════════════════════════════════════════════════════════════
    
    tx_status = transaction.get('status', 'pending')
    status_label = safe_text(t(tx_status, lang), lang)
    
    ref_data = [
        [
            Paragraph(f"<b>{safe_text(t('ref_no', lang), lang)}</b>", label_style),
            Paragraph(transaction.get('ref_no', 'N/A'), value_style),
            Paragraph(f"<b>{safe_text(t('status', lang), lang)}</b>", label_style),
            Paragraph(status_label, value_style),
        ],
        [
            Paragraph(f"<b>{safe_text(t('date', lang), lang)}</b>", label_style),
            Paragraph(format_saudi_time(transaction.get('created_at', '')), value_style),
            Paragraph(f"<b>{safe_text(t('integrity_id', lang), lang)}</b>", label_style),
            Paragraph(integrity_id, value_style),
        ],
    ]
    
    ref_table = Table(ref_data, colWidths=[40*mm, 50*mm, 40*mm, 50*mm])
    ref_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), GRAY_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(ref_table)
    
    # ═══════════════════════════════════════════════════════════════
    # EMPLOYEE INFO
    # ═══════════════════════════════════════════════════════════════
    
    if employee:
        elements.append(Paragraph(safe_text(t('employee_info', lang), lang), section_style))
        
        emp_name = employee.get('full_name_ar' if lang == 'ar' else 'full_name', employee.get('full_name', 'N/A'))
        emp_number = employee.get('employee_number', 'N/A')
        
        emp_data = [
            [
                Paragraph(f"<b>{safe_text(t('name', lang), lang)}</b>", label_style),
                Paragraph(safe_text(emp_name, lang), value_style),
            ],
            [
                Paragraph(f"<b>{safe_text(t('employee_no', lang), lang)}</b>", label_style),
                Paragraph(str(emp_number), value_style),
            ],
        ]
        
        emp_table = Table(emp_data, colWidths=[50*mm, 130*mm])
        emp_table.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(emp_table)
    
    # ═══════════════════════════════════════════════════════════════
    # TRANSACTION DETAILS
    # ═══════════════════════════════════════════════════════════════
    
    elements.append(Paragraph(safe_text(t('transaction_details', lang), lang), section_style))
    
    tx_data = transaction.get('data', {})
    details_rows = []
    
    for key, value in tx_data.items():
        if key in ('employee_name_ar', 'employee_name') and lang == 'ar' and 'employee_name_ar' in tx_data:
            if key == 'employee_name':
                continue
        
        label = safe_text(t(key, lang), lang)
        
        # Format value
        val_str = str(value) if value is not None else '-'
        if key == 'leave_type' and val_str in ('annual', 'sick', 'emergency'):
            val_str = safe_text(t(val_str, lang), lang)
        elif key in ('amount', 'estimatedvalue'):
            val_str = f"{val_str} SAR"
        elif lang == 'ar' and any('\u0600' <= c <= '\u06FF' for c in val_str):
            val_str = safe_text(val_str, lang)
        
        details_rows.append([
            Paragraph(f"<b>{label}</b>", label_style),
            Paragraph(val_str, value_style),
        ])
    
    if details_rows:
        details_table = Table(details_rows, colWidths=[60*mm, 120*mm])
        details_table.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, GRAY_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(details_table)
    
    # ═══════════════════════════════════════════════════════════════
    # APPROVAL CHAIN WITH QR SIGNATURES
    # ═══════════════════════════════════════════════════════════════
    
    if transaction.get('approval_chain'):
        elements.append(Paragraph(safe_text(t('approval_chain', lang), lang), section_style))
        
        # Header
        approval_header = [
            Paragraph(f"<b>{safe_text(t('stage', lang), lang)}</b>", label_style),
            Paragraph(f"<b>{safe_text(t('approver', lang), lang)}</b>", label_style),
            Paragraph(f"<b>{safe_text(t('status', lang), lang)}</b>", label_style),
            Paragraph(f"<b>{safe_text(t('date', lang), lang)}</b>", label_style),
            Paragraph(f"<b>{safe_text(t('signature', lang), lang)}</b>", label_style),
        ]
        
        approval_rows = [approval_header]
        
        for a in transaction['approval_chain']:
            stage = a.get('stage', '')
            stage_label = safe_text(t(stage, lang), lang) if stage not in ('stas', 'ceo') else stage.upper()
            
            status = a.get('status', '')
            status_label = safe_text(t(status, lang), lang)
            
            approver = a.get('approver_name', '')
            if lang == 'ar' and any('\u0600' <= c <= '\u06FF' for c in approver):
                approver = safe_text(approver, lang)
            
            # Generate QR signature for this approval
            sig_data = f"{transaction.get('ref_no')}|{stage}|{a.get('approver_id', '')}|{a.get('timestamp', '')}"
            
            # STAS gets barcode, others get QR
            if stage == 'stas':
                sig_text = f"[{safe_text(t('system_signature', lang), lang)}]\n|||STAS-{integrity_id}|||"
                sig_cell = Paragraph(sig_text, ParagraphStyle('Sig', fontSize=7, fontName=base_font, alignment=TA_CENTER))
            else:
                sig_cell = generate_qr_code(sig_data, size=15)
            
            approval_rows.append([
                Paragraph(stage_label, value_style),
                Paragraph(approver, value_style),
                Paragraph(status_label, value_style),
                Paragraph(format_saudi_time(a.get('timestamp', '')), value_style),
                sig_cell,
            ])
        
        approval_table = Table(approval_rows, colWidths=[35*mm, 40*mm, 35*mm, 35*mm, 35*mm])
        approval_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY_DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('BOX', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, GRAY_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(approval_table)
    
    # ═══════════════════════════════════════════════════════════════
    # TIMELINE
    # ═══════════════════════════════════════════════════════════════
    
    if transaction.get('timeline'):
        elements.append(Paragraph(safe_text(t('timeline', lang), lang), section_style))
        
        timeline_header = [
            Paragraph(f"<b>{safe_text(t('date', lang), lang)}</b>", label_style),
            Paragraph(f"<b>{safe_text(t('status', lang), lang)}</b>", label_style),
            Paragraph(f"<b>{safe_text(t('approver', lang), lang)}</b>", label_style),
            Paragraph(f"<b>{safe_text(t('note', lang), lang)}</b>", label_style),
        ]
        
        timeline_rows = [timeline_header]
        
        for event in transaction['timeline']:
            event_name = event.get('event', '')
            event_label = safe_text(t(event_name, lang), lang)
            
            actor_name = event.get('actor_name', '')
            if lang == 'ar' and any('\u0600' <= c <= '\u06FF' for c in actor_name):
                actor_name = safe_text(actor_name, lang)
            
            note = event.get('note', '')
            if lang == 'ar' and any('\u0600' <= c <= '\u06FF' for c in note):
                note = safe_text(note, lang)
            note = note[:40] + '...' if len(note) > 40 else note
            
            timeline_rows.append([
                Paragraph(format_saudi_time(event.get('timestamp', '')), value_style),
                Paragraph(event_label, value_style),
                Paragraph(actor_name, value_style),
                Paragraph(note, value_style),
            ])
        
        timeline_table = Table(timeline_rows, colWidths=[40*mm, 40*mm, 45*mm, 55*mm])
        timeline_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY_DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('BOX', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, GRAY_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(timeline_table)
    
    # ═══════════════════════════════════════════════════════════════
    # FOOTER WITH DOCUMENT QR
    # ═══════════════════════════════════════════════════════════════
    
    elements.append(Spacer(1, 10*mm))
    
    # Document verification QR
    doc_qr_data = f"DAR-AL-CODE|{transaction.get('ref_no')}|{integrity_id}|{transaction.get('status')}"
    doc_qr = generate_qr_code(doc_qr_data, size=20)
    
    footer_table = Table([
        [doc_qr, Paragraph(f"{safe_text(t('footer', lang), lang)}<br/>{safe_text(t('integrity_id', lang), lang)}: {integrity_id}<br/>{safe_text(t('generated', lang), lang)}: {format_saudi_time(datetime.now(timezone.utc).isoformat())} ({safe_text(t('saudi_time', lang), lang)})", footer_style)]
    ], colWidths=[25*mm, 155*mm])
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, GRAY_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(footer_table)
    
    # Build PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    return pdf_bytes, pdf_hash, integrity_id
