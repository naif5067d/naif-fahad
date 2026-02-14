"""
Professional PDF Generator for DAR AL CODE HR OS
Redesigned with professional layout, proper alignment, and clean formatting.
"""
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display
import hashlib
import uuid
import io
import os
from datetime import datetime, timezone
from database import db

# Register Arabic fonts
FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')
try:
    pdfmetrics.registerFont(TTFont('NotoArabic', os.path.join(FONTS_DIR, 'NotoSansArabic-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('NotoArabicBold', os.path.join(FONTS_DIR, 'NotoSansArabic-Bold.ttf')))
    ARABIC_FONT_AVAILABLE = True
except Exception:
    ARABIC_FONT_AVAILABLE = False

# Brand Colors
NAVY_DARK = colors.Color(0.12, 0.23, 0.37)  # #1E3A5F
LAVENDER = colors.Color(0.65, 0.55, 0.98)   # #A78BFA
GRAY_LIGHT = colors.Color(0.96, 0.96, 0.97)  # #F5F5F7
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


def safe_arabic(text):
    """Safely process any text that might contain Arabic"""
    if not text:
        return '-'
    return process_arabic_text(str(text))


def format_saudi_time(iso_timestamp):
    """Convert ISO timestamp to Saudi Arabia time (UTC+3)"""
    if not iso_timestamp:
        return '-'
    try:
        if isinstance(iso_timestamp, str):
            # Parse ISO format
            if 'T' in iso_timestamp:
                dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
            else:
                return iso_timestamp[:19]
        else:
            dt = iso_timestamp
        
        # Add 3 hours for Saudi timezone
        from datetime import timedelta
        saudi_time = dt + timedelta(hours=3)
        return saudi_time.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return str(iso_timestamp)[:16] if iso_timestamp else '-'


async def get_company_settings():
    """Get company branding settings from database"""
    settings = await db.settings.find_one({"type": "company_branding"}, {"_id": 0})
    if settings:
        return settings
    # Default settings
    return {
        "company_name_en": "DAR AL CODE ENGINEERING CONSULTANCY",
        "company_name_ar": "شركة دار الكود للاستشارات الهندسية",
        "slogan_en": "Engineering Excellence",
        "slogan_ar": "التميز الهندسي",
        "logo_url": None
    }


def generate_transaction_pdf(transaction: dict, employee: dict = None, company_settings: dict = None) -> tuple:
    """Generate professional PDF with clean layout and proper Arabic support"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        topMargin=15*mm, 
        bottomMargin=15*mm, 
        leftMargin=15*mm, 
        rightMargin=15*mm
    )
    
    # Fonts
    base_font = 'NotoArabic' if ARABIC_FONT_AVAILABLE else 'Helvetica'
    bold_font = 'NotoArabicBold' if ARABIC_FONT_AVAILABLE else 'Helvetica-Bold'
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_en_style = ParagraphStyle(
        'TitleEN', 
        fontSize=14, 
        fontName='Helvetica-Bold',
        textColor=NAVY_DARK,
        alignment=TA_CENTER,
        spaceAfter=2*mm
    )
    
    title_ar_style = ParagraphStyle(
        'TitleAR', 
        fontSize=12, 
        fontName=bold_font,
        textColor=NAVY_DARK,
        alignment=TA_CENTER,
        spaceAfter=4*mm
    )
    
    section_title_style = ParagraphStyle(
        'SectionTitle', 
        fontSize=11, 
        fontName=bold_font,
        textColor=NAVY_DARK,
        spaceBefore=8*mm,
        spaceAfter=4*mm
    )
    
    label_style = ParagraphStyle(
        'Label', 
        fontSize=9, 
        fontName=base_font,
        textColor=colors.Color(0.4, 0.4, 0.4)
    )
    
    value_style = ParagraphStyle(
        'Value', 
        fontSize=10, 
        fontName=bold_font,
        textColor=TEXT_DARK
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
    
    # Default company settings if not provided
    if not company_settings:
        company_settings = {
            "company_name_en": "DAR AL CODE ENGINEERING CONSULTANCY",
            "company_name_ar": "شركة دار الكود للاستشارات الهندسية",
        }
    
    # ═══════════════════════════════════════════════════════════════
    # HEADER SECTION
    # ═══════════════════════════════════════════════════════════════
    
    # Company name (English)
    elements.append(Paragraph(company_settings.get("company_name_en", "DAR AL CODE ENGINEERING CONSULTANCY"), title_en_style))
    
    # Company name (Arabic)
    elements.append(Paragraph(safe_arabic(company_settings.get("company_name_ar", "شركة دار الكود للاستشارات الهندسية")), title_ar_style))
    
    # Divider line
    divider_table = Table([['']], colWidths=[180*mm])
    divider_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 2, NAVY_DARK),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(divider_table)
    elements.append(Spacer(1, 6*mm))
    
    # Document title
    type_translations = {
        'leave_request': ('Leave Request', 'طلب إجازة'),
        'finance_60': ('Financial Custody', 'عهدة مالية'),
        'settlement': ('Settlement', 'تسوية'),
        'contract': ('Contract', 'عقد'),
        'tangible_custody': ('Tangible Custody', 'عهدة ملموسة'),
        'tangible_custody_return': ('Custody Return', 'إرجاع عهدة'),
    }
    tx_type = transaction.get('type', 'transaction')
    type_en, type_ar = type_translations.get(tx_type, (tx_type.replace('_', ' ').title(), tx_type))
    
    doc_title_style = ParagraphStyle(
        'DocTitle', 
        fontSize=13, 
        fontName=bold_font,
        textColor=TEXT_DARK,
        alignment=TA_CENTER,
        spaceAfter=6*mm
    )
    elements.append(Paragraph(f"{type_en} / {safe_arabic(type_ar)}", doc_title_style))
    
    # ═══════════════════════════════════════════════════════════════
    # REFERENCE INFO BOX
    # ═══════════════════════════════════════════════════════════════
    
    status_translations = {
        'pending_supervisor': ('Pending Supervisor', 'بانتظار المشرف'),
        'pending_ops': ('Pending Ops', 'بانتظار العمليات'),
        'pending_finance': ('Pending Finance', 'بانتظار المالية'),
        'pending_ceo': ('Pending CEO', 'بانتظار الرئيس'),
        'pending_stas': ('Pending STAS', 'بانتظار ستاس'),
        'executed': ('Executed', 'منفذة'),
        'rejected': ('Rejected', 'مرفوضة'),
    }
    
    tx_status = transaction.get('status', 'pending')
    status_en, status_ar = status_translations.get(tx_status, (tx_status.replace('_', ' ').title(), tx_status))
    
    # Reference info table with clean layout
    ref_data = [
        [
            Paragraph(f"<b>Ref No / {safe_arabic('رقم المرجع')}</b>", label_style),
            Paragraph(transaction.get('ref_no', 'N/A'), value_style),
            Paragraph(f"<b>Status / {safe_arabic('الحالة')}</b>", label_style),
            Paragraph(f"{status_en} / {safe_arabic(status_ar)}", value_style),
        ],
        [
            Paragraph(f"<b>Date / {safe_arabic('التاريخ')}</b>", label_style),
            Paragraph(format_saudi_time(transaction.get('created_at', '')), value_style),
            Paragraph(f"<b>ID / {safe_arabic('المعرف')}</b>", label_style),
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
    # EMPLOYEE INFO SECTION
    # ═══════════════════════════════════════════════════════════════
    
    if employee:
        elements.append(Paragraph(f"Employee Information / {safe_arabic('معلومات الموظف')}", section_title_style))
        
        emp_name = employee.get('full_name', 'N/A')
        emp_name_ar = employee.get('full_name_ar', '')
        emp_number = employee.get('employee_number', 'N/A')
        emp_dept = employee.get('department', 'N/A')
        
        emp_data = [
            [
                Paragraph(f"<b>Name / {safe_arabic('الاسم')}</b>", label_style),
                Paragraph(f"{emp_name}" + (f" / {safe_arabic(emp_name_ar)}" if emp_name_ar else ""), value_style),
            ],
            [
                Paragraph(f"<b>Employee No / {safe_arabic('رقم الموظف')}</b>", label_style),
                Paragraph(str(emp_number), value_style),
            ],
        ]
        
        emp_table = Table(emp_data, colWidths=[50*mm, 130*mm])
        emp_table.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(emp_table)
    
    # ═══════════════════════════════════════════════════════════════
    # TRANSACTION DETAILS SECTION
    # ═══════════════════════════════════════════════════════════════
    
    elements.append(Paragraph(f"Transaction Details / {safe_arabic('تفاصيل المعاملة')}", section_title_style))
    
    label_translations = {
        'leave_type': ('Leave Type', 'نوع الإجازة'),
        'start_date': ('Start Date', 'تاريخ البداية'),
        'end_date': ('End Date', 'تاريخ النهاية'),
        'adjusted_end_date': ('Adjusted End Date', 'تاريخ النهاية المعدل'),
        'working_days': ('Working Days', 'أيام العمل'),
        'reason': ('Reason', 'السبب'),
        'employee_name': ('Employee', 'الموظف'),
        'employee_name_ar': ('Employee (AR)', 'الموظف'),
        'balance_before': ('Balance Before', 'الرصيد قبل'),
        'balance_after': ('Balance After', 'الرصيد بعد'),
        'amount': ('Amount', 'المبلغ'),
        'description': ('Description', 'الوصف'),
        'asset_name': ('Asset', 'الأصل'),
        'asset_serial': ('Serial No', 'الرقم التسلسلي'),
    }
    
    leave_type_translations = {
        'annual': ('Annual', 'سنوية'),
        'sick': ('Sick', 'مرضية'),
        'emergency': ('Emergency', 'طارئة'),
    }
    
    tx_data = transaction.get('data', {})
    details_rows = []
    
    for key, value in tx_data.items():
        if key in ('employee_name_ar',) and 'employee_name' in tx_data:
            continue  # Skip if already showing combined name
            
        label_en, label_ar = label_translations.get(key, (key.replace('_', ' ').title(), key))
        
        # Format value
        val_str = str(value) if value is not None else '-'
        if key == 'leave_type' and val_str in leave_type_translations:
            val_en, val_ar = leave_type_translations[val_str]
            val_str = f"{val_en} / {safe_arabic(val_ar)}"
        elif any('\u0600' <= char <= '\u06FF' for char in val_str):
            val_str = safe_arabic(val_str)
        elif key == 'amount':
            val_str = f"{val_str} SAR"
        
        details_rows.append([
            Paragraph(f"<b>{label_en} / {safe_arabic(label_ar)}</b>", label_style),
            Paragraph(val_str, value_style),
        ])
    
    if details_rows:
        details_table = Table(details_rows, colWidths=[60*mm, 120*mm])
        details_table.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, GRAY_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(details_table)
    
    # ═══════════════════════════════════════════════════════════════
    # TIMELINE SECTION
    # ═══════════════════════════════════════════════════════════════
    
    if transaction.get('timeline'):
        elements.append(Paragraph(f"Transaction Timeline / {safe_arabic('الجدول الزمني')}", section_title_style))
        
        event_translations = {
            'created': ('Created', 'تم الإنشاء'),
            'approved': ('Approved', 'تمت الموافقة'),
            'rejected': ('Rejected', 'تم الرفض'),
            'executed': ('Executed', 'تم التنفيذ'),
            'escalated': ('Escalated', 'تم التصعيد'),
        }
        
        # Timeline header
        timeline_header = [
            Paragraph(f"<b>Date / {safe_arabic('التاريخ')}</b>", label_style),
            Paragraph(f"<b>Event / {safe_arabic('الحدث')}</b>", label_style),
            Paragraph(f"<b>By / {safe_arabic('بواسطة')}</b>", label_style),
            Paragraph(f"<b>Note / {safe_arabic('ملاحظة')}</b>", label_style),
        ]
        
        timeline_rows = [timeline_header]
        
        for event in transaction['timeline']:
            event_name = event.get('event', '')
            event_en, event_ar = event_translations.get(event_name, (event_name.title(), event_name))
            actor_name = event.get('actor_name', '')
            
            # Format actor name
            if any('\u0600' <= c <= '\u06FF' for c in actor_name):
                actor_display = safe_arabic(actor_name)
            else:
                actor_display = actor_name
            
            note = event.get('note', '')
            if any('\u0600' <= c <= '\u06FF' for c in note):
                note = safe_arabic(note)
            
            timeline_rows.append([
                Paragraph(format_saudi_time(event.get('timestamp', '')), value_style),
                Paragraph(f"{event_en} / {safe_arabic(event_ar)}", value_style),
                Paragraph(actor_display, value_style),
                Paragraph(note[:50] + '...' if len(note) > 50 else note, value_style),
            ])
        
        timeline_table = Table(timeline_rows, colWidths=[40*mm, 45*mm, 45*mm, 50*mm])
        timeline_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY_DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, GRAY_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(timeline_table)
    
    # ═══════════════════════════════════════════════════════════════
    # APPROVAL CHAIN SECTION
    # ═══════════════════════════════════════════════════════════════
    
    if transaction.get('approval_chain'):
        elements.append(Paragraph(f"Approval Chain / {safe_arabic('سلسلة الموافقات')}", section_title_style))
        
        stage_translations = {
            'supervisor': ('Supervisor', 'المشرف'),
            'ops': ('Operations', 'العمليات'),
            'finance': ('Finance', 'المالية'),
            'ceo': ('CEO', 'الرئيس'),
            'stas': ('STAS', 'ستاس'),
        }
        
        approval_status_translations = {
            'approve': ('Approved', 'موافق'),
            'approved': ('Approved', 'موافق'),
            'reject': ('Rejected', 'مرفوض'),
            'rejected': ('Rejected', 'مرفوض'),
            'pending': ('Pending', 'معلق'),
        }
        
        approval_header = [
            Paragraph(f"<b>Stage / {safe_arabic('المرحلة')}</b>", label_style),
            Paragraph(f"<b>Approver / {safe_arabic('المعتمد')}</b>", label_style),
            Paragraph(f"<b>Status / {safe_arabic('الحالة')}</b>", label_style),
            Paragraph(f"<b>Date / {safe_arabic('التاريخ')}</b>", label_style),
        ]
        
        approval_rows = [approval_header]
        
        for a in transaction['approval_chain']:
            stage = a.get('stage', '')
            stage_en, stage_ar = stage_translations.get(stage, (stage.title(), stage))
            status = a.get('status', '')
            status_en, status_ar = approval_status_translations.get(status, (status.title(), status))
            approver = a.get('approver_name', '')
            
            if any('\u0600' <= c <= '\u06FF' for c in approver):
                approver = safe_arabic(approver)
            
            approval_rows.append([
                Paragraph(f"{stage_en} / {safe_arabic(stage_ar)}", value_style),
                Paragraph(approver, value_style),
                Paragraph(f"{status_en} / {safe_arabic(status_ar)}", value_style),
                Paragraph(format_saudi_time(a.get('timestamp', '')), value_style),
            ])
        
        approval_table = Table(approval_rows, colWidths=[45*mm, 50*mm, 45*mm, 40*mm])
        approval_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY_DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 0.5, GRAY_BORDER),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, GRAY_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(approval_table)
    
    # ═══════════════════════════════════════════════════════════════
    # FOOTER
    # ═══════════════════════════════════════════════════════════════
    
    elements.append(Spacer(1, 15*mm))
    
    # Footer divider
    footer_divider = Table([['']], colWidths=[180*mm])
    footer_divider.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, GRAY_BORDER),
    ]))
    elements.append(footer_divider)
    elements.append(Spacer(1, 3*mm))
    
    # Footer text
    footer_text = f"DAR AL CODE HR OS | Document ID: {integrity_id} | Generated: {format_saudi_time(datetime.now(timezone.utc).isoformat())} (Saudi Time)"
    elements.append(Paragraph(footer_text, footer_style))
    
    # Build PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    return pdf_bytes, pdf_hash, integrity_id
