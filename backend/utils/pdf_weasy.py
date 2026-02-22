"""
Professional PDF Generator using WeasyPrint
Supports Arabic text properly with RTL layout
"""

import hashlib
import uuid
import base64
import io
import os
from datetime import datetime, timezone, timedelta
from weasyprint import HTML, CSS
import qrcode
from PIL import Image

# Fonts directory
FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')


def format_saudi_time(ts):
    """Format timestamp to Saudi Arabia time (UTC+3)"""
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
        ts_str = str(ts)
        if len(ts_str) >= 8 and ts_str[:8].isdigit():
            return f"{ts_str[:4]}-{ts_str[4:6]}-{ts_str[6:8]}"
        return str(ts)[:16] if ts else '-'


def format_date_only(date_str):
    """Format date with separators"""
    if not date_str:
        return '-'
    try:
        date_str = str(date_str).strip()
        if '-' in date_str and len(date_str.split('-')[0]) == 4:
            return date_str.split('T')[0] if 'T' in date_str else date_str
        if len(date_str) >= 8 and date_str[:8].isdigit():
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return date_str
    except Exception:
        return str(date_str)


def generate_qr_base64(data: str, size: int = 100) -> str:
    """Generate QR code as base64 image"""
    qr = qrcode.QRCode(version=1, box_size=4, border=1)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Resize
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode()


def get_labels(lang: str) -> dict:
    """Get field labels based on language"""
    if lang == 'ar':
        return {
            'leave_type': 'نوع الإجازة',
            'start_date': 'تاريخ البداية',
            'end_date': 'تاريخ النهاية',
            'working_days': 'أيام العمل',
            'reason': 'السبب',
            'employee_name': 'اسم الموظف',
            'amount': 'المبلغ',
            'annual': 'سنوية',
            'sick': 'مرضية',
            'emergency': 'طارئة',
            'marriage': 'زواج',
            'bereavement': 'وفاة',
            'exam': 'اختبار',
            'unpaid': 'بدون راتب',
            'stage': 'المرحلة',
            'status': 'الحالة',
            'approver': 'المعتمد',
            'time': 'الوقت',
            'signature': 'التوقيع',
            'approved': 'موافق',
            'rejected': 'مرفوض',
            'executed': 'منفذ',
            'pending': 'معلق',
            'supervisor': 'المشرف',
            'operations': 'العمليات',
            'stas': 'ستاس',
            'ceo': 'الرئيس التنفيذي',
        }
    else:
        return {
            'leave_type': 'Leave Type',
            'start_date': 'Start Date',
            'end_date': 'End Date',
            'working_days': 'Working Days',
            'reason': 'Reason',
            'employee_name': 'Employee Name',
            'amount': 'Amount',
            'annual': 'Annual',
            'sick': 'Sick',
            'emergency': 'Emergency',
            'marriage': 'Marriage',
            'bereavement': 'Bereavement',
            'exam': 'Exam',
            'unpaid': 'Unpaid',
            'stage': 'Stage',
            'status': 'Status',
            'approver': 'Approver',
            'time': 'Time',
            'signature': 'Signature',
            'approved': 'Approved',
            'rejected': 'Rejected',
            'executed': 'Executed',
            'pending': 'Pending',
            'supervisor': 'Supervisor',
            'operations': 'Operations',
            'stas': 'STAS',
            'ceo': 'CEO',
        }


def generate_transaction_pdf(transaction: dict, employee: dict = None, lang: str = 'ar', branding: dict = None) -> tuple:
    """
    Generate professional PDF using WeasyPrint with proper Arabic support
    
    Returns: (pdf_bytes, pdf_hash, integrity_id)
    """
    
    labels = get_labels(lang)
    
    # Extract data
    ref_no = transaction.get('ref_no', 'N/A')
    tx_type = transaction.get('type', 'transaction')
    status = transaction.get('status', 'pending')
    created_at = format_saudi_time(transaction.get('created_at'))
    executed_at = format_saudi_time(transaction.get('executed_at'))
    tx_data = transaction.get('data', {})
    approval_chain = transaction.get('approval_chain', [])
    
    # Branding
    company_name = branding.get('company_name_ar' if lang == 'ar' else 'company_name_en', 'DAR AL CODE') if branding else 'DAR AL CODE'
    slogan = branding.get('slogan_ar' if lang == 'ar' else 'slogan_en', '') if branding else ''
    
    # Employee info
    emp_name = ''
    emp_no = ''
    if employee:
        emp_name = employee.get('full_name_ar' if lang == 'ar' else 'full_name', '')
        emp_no = employee.get('employee_number', '')
    elif tx_data:
        emp_name = tx_data.get('employee_name_ar' if lang == 'ar' else 'employee_name', '')
    
    # Generate hashes for integrity
    content_hash = hashlib.sha256(f"{ref_no}{created_at}{emp_name}".encode()).hexdigest()[:8].upper()
    integrity_id = f"{ref_no[-6:]}-{content_hash}"
    
    # Generate QR codes
    main_qr = generate_qr_base64(f"VERIFY:{integrity_id}", 80)
    stas_qr = generate_qr_base64(f"STAS-EXEC:{ref_no}", 60)
    
    # Type labels
    type_labels = {
        'leave_request': 'طلب إجازة' if lang == 'ar' else 'Leave Request',
        'attendance_request': 'طلب حضور' if lang == 'ar' else 'Attendance Request',
        'settlement': 'تسوية' if lang == 'ar' else 'Settlement',
        'contract': 'عقد' if lang == 'ar' else 'Contract',
    }
    type_label = type_labels.get(tx_type, tx_type)
    
    # Build data rows
    data_rows_html = ""
    skip_fields = {'employee_name_ar', 'balance_before', 'balance_after', 'adjusted_end_date', 'sick_tier_info', 'leave_type_ar', 'medical_file_url'}
    
    for key, value in tx_data.items():
        if key in skip_fields or isinstance(value, (dict, list)) or value is None:
            continue
        
        field_label = labels.get(key, key.replace('_', ' ').title())
        
        # Format value
        if key == 'leave_type':
            formatted_val = tx_data.get('leave_type_ar', '') if lang == 'ar' else labels.get(str(value), str(value))
            if not formatted_val:
                formatted_val = labels.get(str(value), str(value))
        elif key == 'employee_name' and lang == 'ar' and tx_data.get('employee_name_ar'):
            formatted_val = tx_data['employee_name_ar']
        elif key in ('start_date', 'end_date', 'date'):
            formatted_val = format_date_only(str(value))
        elif key in ('amount', 'estimatedvalue', 'estimated_value'):
            formatted_val = f"{value} SAR"
        else:
            formatted_val = str(value)
        
        data_rows_html += f"""
        <tr>
            <td class="label">{field_label}</td>
            <td class="value">{formatted_val}</td>
        </tr>
        """
    
    # Build approval chain
    approval_html = ""
    for entry in approval_chain:
        stage = entry.get('stage', '')
        stage_label = labels.get(stage, stage)
        entry_status = entry.get('status', 'pending')
        status_label = labels.get(entry_status, entry_status)
        approver = entry.get('approver_name', '-')
        timestamp = format_saudi_time(entry.get('timestamp'))
        
        # Status color
        status_class = 'status-approved' if entry_status == 'approved' else 'status-executed' if entry_status == 'executed' else 'status-pending'
        
        # QR for each approval
        approval_qr = generate_qr_base64(f"{stage.upper()}-{ref_no[-4:]}", 40)
        
        approval_html += f"""
        <tr>
            <td>{stage_label}</td>
            <td class="{status_class}">{status_label}</td>
            <td>{approver}</td>
            <td>{timestamp}</td>
            <td><img src="data:image/png;base64,{approval_qr}" class="qr-small" alt="QR"></td>
        </tr>
        """
    
    # Employee deduction consent section (for sick leave > 30 days)
    consent_html = ""
    if tx_type == 'leave_request' and tx_data.get('leave_type') == 'sick':
        sick_tier_info = tx_data.get('sick_tier_info', {})
        if isinstance(sick_tier_info, dict):
            tier_distribution = sick_tier_info.get('distribution', [])
            has_deduction = any(t.get('salary_percent', 100) < 100 for t in tier_distribution if isinstance(t, dict))
            
            if has_deduction:
                emp_first_name = emp_name.split()[0] if emp_name else 'الموظف' if lang == 'ar' else 'Employee'
                consent_qr = generate_qr_base64(f"CONSENT-{emp_no or 'EMP'}-{ref_no[-6:]}", 80)
                
                deduction_details = ""
                for tier in tier_distribution:
                    if isinstance(tier, dict) and tier.get('salary_percent', 100) < 100:
                        days = tier.get('days', 0)
                        percent = tier.get('salary_percent', 0)
                        if lang == 'ar':
                            deduction_details += f"<li>{days} يوم بنسبة خصم {100-percent}%</li>"
                        else:
                            deduction_details += f"<li>{days} days at {100-percent}% deduction</li>"
                
                if lang == 'ar':
                    consent_html = f"""
                    <div class="consent-section">
                        <h3>موافقة الموظف على الخصم - المادة 117</h3>
                        <p>عزيزي {emp_first_name}،</p>
                        <p>بناءً على المادة 117 من نظام العمل السعودي، سيتم تطبيق الخصم التالي:</p>
                        <ul>{deduction_details}</ul>
                        <p class="consent-text">بتوقيعي أدناه، أوافق على تطبيق الخصم المذكور أعلاه.</p>
                        <div class="consent-signature">
                            <p>توقيع الموظف</p>
                            <img src="data:image/png;base64,{consent_qr}" class="qr-consent" alt="Employee Consent">
                        </div>
                    </div>
                    """
                else:
                    consent_html = f"""
                    <div class="consent-section">
                        <h3>Employee Deduction Consent - Article 117</h3>
                        <p>Dear {emp_first_name},</p>
                        <p>According to Article 117 of Saudi Labor Law, the following deduction will apply:</p>
                        <ul>{deduction_details}</ul>
                        <p class="consent-text">By signing below, I agree to the above deduction.</p>
                        <div class="consent-signature">
                            <p>Employee Signature</p>
                            <img src="data:image/png;base64,{consent_qr}" class="qr-consent" alt="Employee Consent">
                        </div>
                    </div>
                    """
    
    # Direction
    direction = 'rtl' if lang == 'ar' else 'ltr'
    text_align = 'right' if lang == 'ar' else 'left'
    
    # Build HTML
    html_content = f"""
    <!DOCTYPE html>
    <html dir="{direction}" lang="{lang}">
    <head>
        <meta charset="UTF-8">
        <style>
            @font-face {{
                font-family: 'NotoNaskh';
                src: url('file://{FONTS_DIR}/NotoNaskhArabic-Regular.ttf');
            }}
            @font-face {{
                font-family: 'NotoNaskh';
                src: url('file://{FONTS_DIR}/NotoNaskhArabic-Bold.ttf');
                font-weight: bold;
            }}
            
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'NotoNaskh', 'Arial', sans-serif;
                font-size: 10pt;
                line-height: 1.4;
                color: #333;
                direction: {direction};
                text-align: {text_align};
            }}
            
            .page {{
                width: 210mm;
                min-height: 297mm;
                padding: 15mm;
                background: white;
            }}
            
            /* Header */
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 2px solid #1a365d;
                padding-bottom: 10px;
                margin-bottom: 15px;
            }}
            
            .company-info {{
                text-align: {text_align};
            }}
            
            .company-name {{
                font-size: 16pt;
                font-weight: bold;
                color: #1a365d;
            }}
            
            .slogan {{
                font-size: 9pt;
                color: #666;
            }}
            
            .qr-header {{
                width: 60px;
                height: 60px;
            }}
            
            /* Title */
            .title {{
                text-align: center;
                margin: 15px 0;
            }}
            
            .title h1 {{
                font-size: 14pt;
                color: #1a365d;
                margin-bottom: 5px;
            }}
            
            .ref-no {{
                font-size: 11pt;
                color: #666;
            }}
            
            /* Employee Info */
            .employee-section {{
                background: #f7fafc;
                border: 1px solid #e2e8f0;
                border-radius: 5px;
                padding: 10px;
                margin-bottom: 15px;
            }}
            
            .employee-section table {{
                width: 100%;
            }}
            
            .employee-section td {{
                padding: 5px;
            }}
            
            .employee-section .label {{
                color: #666;
                width: 100px;
            }}
            
            /* Data Table */
            .data-section {{
                margin-bottom: 15px;
            }}
            
            .data-section h3 {{
                font-size: 11pt;
                color: #1a365d;
                margin-bottom: 8px;
                border-bottom: 1px solid #e2e8f0;
                padding-bottom: 5px;
            }}
            
            .data-section table {{
                width: 100%;
                border-collapse: collapse;
            }}
            
            .data-section td {{
                padding: 6px 8px;
                border-bottom: 1px solid #eee;
            }}
            
            .data-section .label {{
                color: #666;
                width: 150px;
            }}
            
            .data-section .value {{
                font-weight: 500;
            }}
            
            /* Approval Chain */
            .approval-section {{
                margin-bottom: 15px;
            }}
            
            .approval-section h3 {{
                font-size: 11pt;
                color: #1a365d;
                margin-bottom: 8px;
            }}
            
            .approval-table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 9pt;
            }}
            
            .approval-table th {{
                background: #1a365d;
                color: white;
                padding: 8px;
                text-align: {text_align};
            }}
            
            .approval-table td {{
                padding: 8px;
                border-bottom: 1px solid #e2e8f0;
                vertical-align: middle;
            }}
            
            .qr-small {{
                width: 35px;
                height: 35px;
            }}
            
            .status-approved {{
                color: #38a169;
                font-weight: bold;
            }}
            
            .status-executed {{
                color: #2b6cb0;
                font-weight: bold;
            }}
            
            .status-pending {{
                color: #d69e2e;
            }}
            
            /* Consent Section */
            .consent-section {{
                background: #ebf8ff;
                border: 2px solid #2b6cb0;
                border-radius: 8px;
                padding: 15px;
                margin: 20px 0;
            }}
            
            .consent-section h3 {{
                color: #2b6cb0;
                margin-bottom: 10px;
            }}
            
            .consent-section ul {{
                margin: 10px 20px;
            }}
            
            .consent-text {{
                font-weight: bold;
                margin-top: 15px;
            }}
            
            .consent-signature {{
                text-align: center;
                margin-top: 15px;
                padding: 10px;
                background: white;
                border-radius: 5px;
            }}
            
            .qr-consent {{
                width: 70px;
                height: 70px;
            }}
            
            /* STAS Seal */
            .stas-seal {{
                text-align: center;
                margin: 20px 0;
                padding: 15px;
                border: 2px dashed #1a365d;
                border-radius: 10px;
            }}
            
            .stas-seal h4 {{
                color: #1a365d;
                margin-bottom: 10px;
            }}
            
            .qr-stas {{
                width: 80px;
                height: 80px;
            }}
            
            /* Footer */
            .footer {{
                margin-top: 20px;
                padding-top: 10px;
                border-top: 1px solid #e2e8f0;
                font-size: 8pt;
                color: #666;
                text-align: center;
            }}
            
            .footer .integrity {{
                font-family: monospace;
                background: #f7fafc;
                padding: 3px 8px;
                border-radius: 3px;
            }}
            
            /* Tear-off Section - قسم القص */
            .tear-off {{
                margin-top: 30px;
                padding-top: 20px;
            }}
            
            .tear-line {{
                border-top: 2px dashed #999;
                text-align: center;
                margin-bottom: 15px;
                position: relative;
            }}
            
            .tear-line span {{
                background: white;
                padding: 0 15px;
                color: #666;
                font-size: 10pt;
                position: relative;
                top: -12px;
            }}
            
            .tear-content {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px;
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }}
            
            .tear-qr-left, .tear-qr-right {{
                text-align: center;
            }}
            
            .qr-tear {{
                width: 70px;
                height: 70px;
            }}
            
            .tear-label {{
                font-size: 8pt;
                color: #666;
                margin-top: 5px;
            }}
            
            .tear-info {{
                text-align: center;
                flex: 1;
                padding: 0 20px;
            }}
            
            .tear-ref {{
                font-size: 16pt;
                font-weight: bold;
                color: #1a365d;
                font-family: monospace;
            }}
            
            .tear-emp {{
                font-size: 11pt;
                margin: 5px 0;
            }}
            
            .tear-type {{
                font-size: 9pt;
                color: #666;
            }}
            
            .tear-status {{
                font-size: 11pt;
                font-weight: bold;
                margin-top: 5px;
            }}
        </style>
    </head>
    <body>
        <div class="page">
            <!-- Header -->
            <div class="header">
                <div class="company-info">
                    <div class="company-name">{company_name}</div>
                    <div class="slogan">{slogan}</div>
                </div>
                <img src="data:image/png;base64,{main_qr}" class="qr-header" alt="Verify QR">
            </div>
            
            <!-- Title -->
            <div class="title">
                <h1>{type_label}</h1>
                <div class="ref-no">{ref_no}</div>
            </div>
            
            <!-- Employee Info -->
            <div class="employee-section">
                <table>
                    <tr>
                        <td class="label">{'اسم الموظف' if lang == 'ar' else 'Employee Name'}</td>
                        <td><strong>{emp_name}</strong></td>
                        <td class="label">{'رقم الموظف' if lang == 'ar' else 'Employee No.'}</td>
                        <td><strong>{emp_no}</strong></td>
                    </tr>
                </table>
            </div>
            
            <!-- Request Data -->
            <div class="data-section">
                <h3>{'تفاصيل الطلب' if lang == 'ar' else 'Request Details'}</h3>
                <table>
                    {data_rows_html}
                </table>
            </div>
            
            <!-- Approval Chain -->
            <div class="approval-section">
                <h3>{'سلسلة الموافقات' if lang == 'ar' else 'Approval Chain'}</h3>
                <table class="approval-table">
                    <thead>
                        <tr>
                            <th>{labels['stage']}</th>
                            <th>{labels['status']}</th>
                            <th>{labels['approver']}</th>
                            <th>{labels['time']}</th>
                            <th>{labels['signature']}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {approval_html}
                    </tbody>
                </table>
            </div>
            
            {consent_html}
            
            <!-- STAS Execution Seal -->
            <div class="stas-seal">
                <h4>{'ختم التنفيذ - STAS' if lang == 'ar' else 'Execution Seal - STAS'}</h4>
                <img src="data:image/png;base64,{stas_qr}" class="qr-stas" alt="STAS Seal">
                <p>{executed_at if status == 'executed' else '-'}</p>
            </div>
            
            <!-- Footer with Tear-off Section -->
            <div class="footer">
                <p>{'تم الإنشاء' if lang == 'ar' else 'Generated'}: {created_at}</p>
                <p class="integrity">{integrity_id}</p>
                <p>DAR AL CODE HR OS | {content_hash}</p>
            </div>
            
            <!-- Tear-off Section - قسم القص -->
            <div class="tear-off">
                <div class="tear-line">
                    <span>{'✂️ قص هنا' if lang == 'ar' else '✂️ Cut Here'}</span>
                </div>
                <div class="tear-content">
                    <div class="tear-qr-left">
                        <img src="data:image/png;base64,{main_qr}" class="qr-tear" alt="QR1">
                        <p class="tear-label">{'QR التحقق' if lang == 'ar' else 'Verify QR'}</p>
                    </div>
                    <div class="tear-info">
                        <p class="tear-ref">{ref_no}</p>
                        <p class="tear-emp">{emp_name}</p>
                        <p class="tear-type">{type_label}</p>
                        <p class="tear-status" style="color: {'#22c55e' if status == 'executed' else '#f59e0b'}">
                            {'منفذ' if status == 'executed' and lang == 'ar' else 'Executed' if status == 'executed' else 'معلق' if lang == 'ar' else 'Pending'}
                        </p>
                    </div>
                    <div class="tear-qr-right">
                        <img src="data:image/png;base64,{stas_qr}" class="qr-tear" alt="QR2">
                        <p class="tear-label">{'QR المعاملة' if lang == 'ar' else 'Transaction QR'}</p>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Generate PDF
    html = HTML(string=html_content)
    pdf_bytes = html.write_pdf()
    
    # Calculate hash
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    return pdf_bytes, pdf_hash, integrity_id


# Test function
if __name__ == "__main__":
    test_tx = {
        "id": "test-123",
        "ref_no": "TXN-2026-0002",
        "type": "leave_request",
        "status": "executed",
        "created_at": "2026-02-17T10:00:00Z",
        "executed_at": "2026-02-17T12:00:00Z",
        "data": {
            "leave_type": "sick",
            "leave_type_ar": "مرضية",
            "start_date": "2026-02-18",
            "end_date": "2026-04-05",
            "working_days": 39,
            "reason": "تبعاً للسياسة الداخلية للشركة",
            "employee_name": "Naif Al-Quraishi",
            "employee_name_ar": "نايف فهد القريشي",
            "sick_tier_info": {
                "distribution": [
                    {"days": 30, "salary_percent": 100},
                    {"days": 9, "salary_percent": 50}
                ]
            }
        },
        "approval_chain": [
            {"stage": "supervisor", "status": "approved", "approver_name": "أحمد محمد", "timestamp": "2026-02-17T11:00:00Z"},
            {"stage": "operations", "status": "approved", "approver_name": "العمليات", "timestamp": "2026-02-17T11:30:00Z"},
            {"stage": "stas", "status": "executed", "approver_name": "STAS", "timestamp": "2026-02-17T12:00:00Z"}
        ]
    }
    
    test_emp = {
        "id": "emp-001",
        "full_name": "Naif Al-Quraishi",
        "full_name_ar": "نايف فهد القريشي",
        "employee_number": "22919"
    }
    
    pdf_bytes, pdf_hash, integrity_id = generate_transaction_pdf(test_tx, test_emp, lang='ar')
    
    with open('/tmp/test_weasy_ar.pdf', 'wb') as f:
        f.write(pdf_bytes)
    print(f"✓ Arabic PDF: /tmp/test_weasy_ar.pdf ({len(pdf_bytes)} bytes)")
    
    pdf_bytes_en, _, _ = generate_transaction_pdf(test_tx, test_emp, lang='en')
    with open('/tmp/test_weasy_en.pdf', 'wb') as f:
        f.write(pdf_bytes_en)
    print(f"✓ English PDF: /tmp/test_weasy_en.pdf ({len(pdf_bytes_en)} bytes)")
