export const translations = {
  en: {
    app: { name: "DAR AL CODE HR OS", company: "Dar Al Code Engineering Consultancy" },
    nav: {
      dashboard: "My Board", transactions: "Transactions", leave: "Leave",
      attendance: "Attendance", finance: "Finance", contracts: "Contracts",
      employees: "Employees", settings: "Settings", stasMirror: "STAS Mirror",
      logout: "Logout", profile: "Profile", workLocations: "Work Locations",
      custody: "Tangible Custody", financialCustody: "Financial Custody",
      companySettings: "Company Settings"
    },
    login: {
      title: "Sign In", subtitle: "DAR AL CODE HR OS",
      username: "Username", password: "Password",
      submit: "Sign In", error: "Invalid credentials",
      noSignup: "Contact STAS administrator for account access"
    },
    dashboard: {
      welcome: "My Board", pendingApprovals: "Pending Approvals",
      leaveBalance: "Leave Balance", teamSize: "Team Size",
      totalEmployees: "Total Employees", pendingExecution: "Pending Execution",
      totalTransactions: "Total Transactions", recentTransactions: "Recent Transactions",
      pendingFinance: "Pending Finance", days: "days", nextHoliday: "Next Holiday"
    },
    transactions: {
      title: "Transactions", inbox: "Inbox", all: "All Transactions",
      refNo: "Ref No", type: "Type", status: "Status", employee: "Employee",
      stage: "Current Stage", date: "Date", actions: "Actions",
      approve: "Approve", reject: "Reject", viewDetail: "View Detail",
      view: "View", search: "Search transactions...",
      downloadPdf: "Download PDF", previewPdf: "Preview PDF", timeline: "Timeline", 
      approvalChain: "Approval Chain", noTransactions: "No transactions found",
      actionNote: "Note (optional)", transactionAction: "Transaction Action",
      details: "Transaction Details", notePlaceholder: "Add a note...",
      confirmApprove: "Confirm Approval", confirmReject: "Confirm Rejection",
      confirmEscalate: "Confirm Escalation", allStatuses: "All Statuses",
      allTypes: "All Types",
      escalate: "Escalate to CEO", escalated: "Escalated",
      acceptCustody: "Accept", rejectCustody: "Reject"
    },
    leave: {
      title: "Leave Management", requestLeave: "Request Leave",
      balance: "Leave Balance", history: "Leave History",
      type: "Leave Type", startDate: "Start Date", endDate: "End Date",
      reason: "Reason", submit: "Submit Request",
      annual: "Annual", sick: "Sick", emergency: "Emergency",
      workingDays: "Working Days", remaining: "Remaining",
      holidays: "Public Holidays", holidayName: "Holiday Name",
      fillAllFields: "Please fill all fields"
    },
    attendance: {
      title: "Attendance", checkIn: "Check In", checkOut: "Check Out",
      todayStatus: "Today's Status", history: "History",
      gpsRequired: "GPS location is required for attendance",
      noGps: "GPS not available on this device",
      checkedIn: "Checked In", checkedOut: "Checked Out",
      notCheckedIn: "Not Checked In",
      workLocation: "Work Location", hq: "HQ", project: "Project",
      selectLocation: "Select work location", insideLocation: "Inside Location",
      outsideLocation: "Outside Location", distance: "Distance",
      gpsStatus: "GPS Status", valid: "Valid", invalid: "Invalid",
      date: "Date", time: "Time", adminView: "Team Attendance",
      daily: "Daily", weekly: "Weekly", monthly: "Monthly", yearly: "Yearly"
    },
    finance: {
      title: "60 Code Finance", codes: "Finance Codes", statement: "Statement",
      createTransaction: "Create Finance Transaction", code: "Code",
      amount: "Amount", description: "Description", category: "Category",
      earnings: "Earnings", deductions: "Deductions", loans: "Loans",
      other: "Other", selectCode: "Select finance code"
    },
    contracts: {
      title: "Contracts", create: "Create Contract", settlement: "Settlement",
      salary: "Salary", type: "Type", version: "Version",
      startDate: "Start Date", endDate: "End Date", content: "Content",
      noContracts: "No contracts found"
    },
    employees: {
      title: "Employees", manage: "Manage Employees",
      name: "Name", department: "Department", position: "Position",
      status: "Status", active: "Active", inactive: "Inactive",
      supervisor: "Supervisor", joinDate: "Join Date", noEmployees: "No employees found",
      assignSupervisor: "Assign Supervisor", noSupervisor: "No Supervisor"
    },
    stas: {
      mirror: "STAS Mirror", preChecks: "Pre-Checks", traceLinks: "Trace Links (Veins)",
      beforeAfter: "Before / After Projection", execute: "Execute",
      allPass: "All checks passed", hasFails: "Some checks failed",
      executing: "Executing...", executed: "Executed",
      pass: "PASS", fail: "FAIL", pendingExecution: "Pending Execution",
      selectTransaction: "Select a transaction to view its mirror",
      maintenance: "System Maintenance", purgeTransactions: "Purge Transactions",
      purgeUsers: "Purge Non-Admin Users", confirmPurge: "Type CONFIRM to proceed",
      purgeWarning: "This action cannot be undone!",
      holidayManagement: "Holiday Management", addHoliday: "Add Holiday",
      holidayDate: "Holiday Date", holidayNameEn: "Name (English)",
      holidayNameAr: "Name (Arabic)", deleteHoliday: "Delete",
      archivedUsers: "Archived Users", archiveUser: "Archive", restoreUser: "Restore",
      noArchivedUsers: "No archived users"
    },
    common: {
      save: "Save", cancel: "Cancel", confirm: "Confirm", delete: "Delete",
      edit: "Edit", view: "View", close: "Close", loading: "Loading...",
      search: "Search", filter: "Filter", noData: "No data",
      back: "Back", next: "Next", submit: "Submit", add: "Add",
      all: "All", success: "Success", error: "Error", warning: "Warning",
      preview: "Preview", download: "Download", actions: "Actions"
    },
    roles: {
      employee: "Employee", supervisor: "Supervisor",
      sultan: "Ops Admin", naif: "Ops Strategic",
      salah: "Finance", mohammed: "CEO", stas: "STAS"
    },
    txTypes: {
      leave_request: "Leave Request",
      finance_60: "Financial Custody (60 Code)",
      settlement: "Settlement",
      contract: "Contract",
      warning: "Warning",
      asset: "Asset",
      attendance_correction: "Attendance Correction",
      add_finance_code: "Add Finance Code",
      tangible_custody: "Tangible Custody",
      tangible_custody_return: "Custody Return"
    },
    stages: {
      supervisor: "Supervisor",
      ops: "Operations",
      finance: "Finance",
      ceo: "CEO",
      stas: "STAS",
      executed: "Executed",
      rejected: "Rejected",
      employee_accept: "Employee Acceptance",
      cancelled: "Cancelled",
      completed: "Completed"
    },
    status: {
      created: "Created", pending_supervisor: "Pending Supervisor",
      pending_ops: "Pending Ops", pending_finance: "Pending Finance",
      pending_ceo: "Pending CEO", stas: "STAS",
      pending_employee_accept: "Pending Employee",
      executed: "Executed", rejected: "Rejected", completed: "Completed",
      cancelled: "Cancelled", approved: "Approved", pending: "Pending"
    },
    theme: { light: "Light", dark: "Dark", toggle: "Toggle Theme" },
    lang: { toggle: "العربية", current: "English" },
    settings: {
      title: "Settings", appearance: "Appearance", language: "Language",
      profile: "Profile", username: "Username", role: "Role", 
      employeeId: "Employee ID"
    }
  },
  ar: {
    app: { name: "دار الكود - نظام الموارد البشرية", company: "شركة دار الكود للاستشارات الهندسية" },
    nav: {
      dashboard: "لوحتي", transactions: "المعاملات", leave: "الإجازات",
      attendance: "الحضور", finance: "المالية", contracts: "العقود",
      employees: "الموظفين", settings: "الإعدادات", stasMirror: "مرآة ستاس",
      logout: "تسجيل الخروج", profile: "الملف الشخصي", workLocations: "مواقع العمل",
      custody: "العهد الملموسة", financialCustody: "العهدة المالية"
    },
    login: {
      title: "تسجيل الدخول", subtitle: "نظام دار الكود للموارد البشرية",
      username: "اسم المستخدم", password: "كلمة المرور",
      submit: "دخول", error: "بيانات الدخول غير صحيحة",
      noSignup: "تواصل مع مسؤول ستاس للحصول على حساب"
    },
    dashboard: {
      welcome: "لوحتي", pendingApprovals: "الموافقات المعلقة",
      leaveBalance: "رصيد الإجازات", teamSize: "حجم الفريق",
      totalEmployees: "إجمالي الموظفين", pendingExecution: "معلق التنفيذ",
      totalTransactions: "إجمالي المعاملات", recentTransactions: "المعاملات الأخيرة",
      pendingFinance: "المالية المعلقة", days: "أيام", nextHoliday: "الإجازة القادمة"
    },
    transactions: {
      title: "المعاملات", inbox: "الوارد", all: "جميع المعاملات",
      refNo: "رقم المرجع", type: "النوع", status: "الحالة", employee: "الموظف",
      stage: "المرحلة الحالية", date: "التاريخ", actions: "الإجراءات",
      approve: "موافقة", reject: "رفض", viewDetail: "عرض التفاصيل",
      view: "عرض", search: "البحث في المعاملات...",
      downloadPdf: "تحميل PDF", previewPdf: "معاينة PDF", timeline: "الجدول الزمني", 
      approvalChain: "سلسلة الموافقات", noTransactions: "لا توجد معاملات",
      actionNote: "ملاحظة (اختياري)", transactionAction: "إجراء المعاملة",
      details: "تفاصيل المعاملة", notePlaceholder: "أضف ملاحظة...",
      confirmApprove: "تأكيد الموافقة", confirmReject: "تأكيد الرفض",
      confirmEscalate: "تأكيد التصعيد", allStatuses: "جميع الحالات",
      allTypes: "جميع الأنواع",
      escalate: "تصعيد للرئيس التنفيذي", escalated: "تم التصعيد",
      acceptCustody: "قبول", rejectCustody: "رفض"
    },
    leave: {
      title: "إدارة الإجازات", requestLeave: "طلب إجازة",
      balance: "رصيد الإجازات", history: "سجل الإجازات",
      type: "نوع الإجازة", startDate: "تاريخ البداية", endDate: "تاريخ النهاية",
      reason: "السبب", submit: "إرسال الطلب",
      annual: "سنوية", sick: "مرضية", emergency: "طارئة",
      workingDays: "أيام العمل", remaining: "المتبقي",
      holidays: "العطل الرسمية", holidayName: "اسم العطلة",
      fillAllFields: "يرجى ملء جميع الحقول"
    },
    attendance: {
      title: "الحضور", checkIn: "تسجيل الدخول", checkOut: "تسجيل الخروج",
      todayStatus: "حالة اليوم", history: "السجل",
      gpsRequired: "موقع GPS مطلوب للحضور",
      noGps: "GPS غير متوفر على هذا الجهاز",
      checkedIn: "تم تسجيل الدخول", checkedOut: "تم تسجيل الخروج",
      notCheckedIn: "لم يتم تسجيل الدخول",
      workLocation: "موقع العمل", hq: "المقر الرئيسي", project: "المشروع",
      selectLocation: "اختر موقع العمل", insideLocation: "داخل الموقع",
      outsideLocation: "خارج الموقع", distance: "المسافة",
      gpsStatus: "حالة GPS", valid: "صالح", invalid: "غير صالح",
      date: "التاريخ", time: "الوقت", adminView: "حضور الفريق",
      daily: "يومي", weekly: "أسبوعي", monthly: "شهري", yearly: "سنوي"
    },
    finance: {
      title: "المالية - 60 رمز", codes: "رموز المالية", statement: "كشف الحساب",
      createTransaction: "إنشاء معاملة مالية", code: "الرمز",
      amount: "المبلغ", description: "الوصف", category: "الفئة",
      earnings: "مستحقات", deductions: "خصومات", loans: "سلف",
      other: "أخرى", selectCode: "اختر رمز المالية"
    },
    contracts: {
      title: "العقود", create: "إنشاء عقد", settlement: "التسوية",
      salary: "الراتب", type: "النوع", version: "الإصدار",
      startDate: "تاريخ البداية", endDate: "تاريخ النهاية", content: "المحتوى",
      noContracts: "لا توجد عقود"
    },
    employees: {
      title: "الموظفين", manage: "إدارة الموظفين",
      name: "الاسم", department: "القسم", position: "المنصب",
      status: "الحالة", active: "نشط", inactive: "غير نشط",
      supervisor: "المشرف", joinDate: "تاريخ الانضمام", noEmployees: "لا يوجد موظفين",
      assignSupervisor: "تعيين المشرف", noSupervisor: "بدون مشرف"
    },
    stas: {
      mirror: "مرآة ستاس", preChecks: "الفحوصات المسبقة", traceLinks: "روابط التتبع (العروق)",
      beforeAfter: "الإسقاط قبل / بعد", execute: "تنفيذ",
      allPass: "جميع الفحوصات ناجحة", hasFails: "بعض الفحوصات فاشلة",
      executing: "جارٍ التنفيذ...", executed: "تم التنفيذ",
      pass: "ناجح", fail: "فاشل", pendingExecution: "معاملات معلقة للتنفيذ",
      selectTransaction: "اختر معاملة لعرض مرآتها",
      maintenance: "صيانة النظام", purgeTransactions: "حذف المعاملات",
      purgeUsers: "حذف المستخدمين غير الإداريين", confirmPurge: "اكتب CONFIRM للمتابعة",
      purgeWarning: "هذا الإجراء لا يمكن التراجع عنه!",
      holidayManagement: "إدارة العطل", addHoliday: "إضافة عطلة",
      holidayDate: "تاريخ العطلة", holidayNameEn: "الاسم (إنجليزي)",
      holidayNameAr: "الاسم (عربي)", deleteHoliday: "حذف",
      archivedUsers: "المستخدمين المؤرشفين", archiveUser: "أرشفة", restoreUser: "استعادة",
      noArchivedUsers: "لا يوجد مستخدمين مؤرشفين"
    },
    common: {
      save: "حفظ", cancel: "إلغاء", confirm: "تأكيد", delete: "حذف",
      edit: "تعديل", view: "عرض", close: "إغلاق", loading: "جارٍ التحميل...",
      search: "بحث", filter: "تصفية", noData: "لا توجد بيانات",
      back: "رجوع", next: "التالي", submit: "إرسال", add: "إضافة",
      all: "الكل", success: "نجاح", error: "خطأ", warning: "تحذير",
      preview: "معاينة", download: "تحميل", actions: "إجراءات"
    },
    roles: {
      employee: "موظف", supervisor: "مشرف",
      sultan: "مدير العمليات", naif: "العمليات الاستراتيجية",
      salah: "المالية", mohammed: "الرئيس التنفيذي", stas: "ستاس"
    },
    txTypes: {
      leave_request: "طلب إجازة",
      finance_60: "عهدة مالية (60 رمز)",
      settlement: "تسوية",
      contract: "عقد",
      warning: "إنذار",
      asset: "أصول",
      attendance_correction: "تصحيح حضور",
      add_finance_code: "إضافة رمز مالي",
      tangible_custody: "عهدة ملموسة",
      tangible_custody_return: "إرجاع عهدة"
    },
    stages: {
      supervisor: "المشرف",
      ops: "العمليات",
      finance: "المالية",
      ceo: "CEO",
      stas: "STAS",
      executed: "منفذة",
      rejected: "مرفوضة",
      employee_accept: "قبول الموظف",
      cancelled: "ملغاة",
      completed: "مكتملة"
    },
    status: {
      created: "تم الإنشاء", pending_supervisor: "بانتظار المشرف",
      pending_ops: "بانتظار العمليات", pending_finance: "بانتظار المالية",
      pending_ceo: "بانتظار CEO", stas: "STAS",
      pending_employee_accept: "بانتظار الموظف",
      executed: "منفذة", rejected: "مرفوضة", completed: "مكتملة",
      cancelled: "ملغاة", approved: "تمت الموافقة", pending: "معلق"
    },
    theme: { light: "فاتح", dark: "داكن", toggle: "تبديل المظهر" },
    theme: { light: "فاتح", dark: "داكن", toggle: "تبديل المظهر" },
    lang: { toggle: "English", current: "العربية" },
    settings: {
      title: "الإعدادات", appearance: "المظهر", language: "اللغة",
      profile: "الملف الشخصي", username: "اسم المستخدم", role: "الدور",
      employeeId: "رقم الموظف"
    }
  }
};
