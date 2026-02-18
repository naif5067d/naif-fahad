"""
Deduction Proposals Model - مقترحات الخصم
ممنوع الخصم المباشر - النظام يقترح → سلطان يراجع → STAS ينفذ
"""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel


class DeductionType(str, Enum):
    """أنواع الخصومات"""
    ABSENCE = "absence"                    # غياب
    LATE = "late"                          # تأخير
    EARLY_LEAVE = "early_leave"            # خروج مبكر
    HOURS_DEFICIT = "hours_deficit"        # نقص ساعات شهري
    VIOLATION = "violation"                # مخالفة
    OTHER = "other"                        # أخرى


class ProposalStatus(str, Enum):
    """حالات المقترح"""
    PENDING = "pending"           # بانتظار المراجعة
    APPROVED = "approved"         # موافق عليه من سلطان
    REJECTED = "rejected"         # مرفوض
    EXECUTED = "executed"         # تم التنفيذ من STAS
    CANCELLED = "cancelled"       # ملغي


class DeductionProposal(BaseModel):
    id: str
    employee_id: str
    
    # نوع الخصم
    deduction_type: DeductionType
    deduction_type_ar: str
    
    # المبلغ
    amount: float
    currency: str = "SAR"
    
    # الفترة
    period_start: str  # YYYY-MM-DD
    period_end: str    # YYYY-MM-DD
    month: str         # YYYY-MM
    
    # سبب الخصم (مهم جداً)
    reason: str
    reason_ar: str
    
    # التفسير الكامل (مرآة STAS)
    explanation: dict  # يحتوي على كل التفاصيل
    
    # المرجعيات
    source_records: List[str]      # IDs of daily_status records
    monthly_hours_id: Optional[str] = None
    
    # المعادلة المالية
    calculation_formula: str
    calculation_details: dict
    
    # حالة المقترح
    status: ProposalStatus = ProposalStatus.PENDING
    
    # المراجعة (سلطان/نايف)
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    review_note: Optional[str] = None
    
    # التنفيذ (STAS فقط)
    executed_by: Optional[str] = None
    executed_at: Optional[str] = None
    execution_note: Optional[str] = None
    finance_ledger_id: Optional[str] = None  # الربط بالسجل المالي
    
    # التدقيق
    created_at: str
    created_by: str = "system"
    
    # سجل التغييرات
    status_history: List[dict] = []


# أنواع الخصومات بالعربي
DEDUCTION_TYPE_AR = {
    DeductionType.ABSENCE: "غياب",
    DeductionType.LATE: "تأخير",
    DeductionType.EARLY_LEAVE: "خروج مبكر",
    DeductionType.HOURS_DEFICIT: "نقص ساعات شهري",
    DeductionType.VIOLATION: "مخالفة",
    DeductionType.OTHER: "أخرى",
}
