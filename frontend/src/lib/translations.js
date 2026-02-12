export const translations = {
  en: {
    app: { name: "DAR AL CODE HR OS", company: "Dar Al Code Engineering Consultancy" },
    nav: {
      dashboard: "Dashboard", transactions: "Transactions", leave: "Leave",
      attendance: "Attendance", finance: "Finance", contracts: "Contracts",
      employees: "Employees", settings: "Settings", stasMirror: "STAS Mirror",
      logout: "Logout", profile: "Profile"
    },
    login: {
      title: "Sign In", subtitle: "DAR AL CODE HR OS",
      username: "Username", password: "Password",
      submit: "Sign In", error: "Invalid credentials",
      noSignup: "Contact STAS administrator for account access"
    },
    dashboard: {
      welcome: "Welcome", pendingApprovals: "Pending Approvals",
      leaveBalance: "Leave Balance", teamSize: "Team Size",
      totalEmployees: "Total Employees", pendingExecution: "Pending Execution",
      totalTransactions: "Total Transactions", recentTransactions: "Recent Transactions",
      pendingFinance: "Pending Finance", days: "days"
    },
    transactions: {
      title: "Transactions", inbox: "Inbox", all: "All Transactions",
      refNo: "Ref No", type: "Type", status: "Status", employee: "Employee",
      stage: "Current Stage", date: "Date", actions: "Actions",
      approve: "Approve", reject: "Reject", viewDetail: "View Detail",
      downloadPdf: "Download PDF", timeline: "Timeline", approvalChain: "Approval Chain",
      noTransactions: "No transactions found"
    },
    leave: {
      title: "Leave Management", requestLeave: "Request Leave",
      balance: "Leave Balance", history: "Leave History",
      type: "Leave Type", startDate: "Start Date", endDate: "End Date",
      reason: "Reason", submit: "Submit Request",
      annual: "Annual", sick: "Sick", emergency: "Emergency",
      workingDays: "Working Days", remaining: "Remaining",
      holidays: "Public Holidays"
    },
    attendance: {
      title: "Attendance", checkIn: "Check In", checkOut: "Check Out",
      todayStatus: "Today's Status", history: "History",
      gpsRequired: "GPS location is required for attendance",
      noGps: "GPS not available on this device",
      checkedIn: "Checked In", checkedOut: "Checked Out",
      notCheckedIn: "Not Checked In"
    },
    finance: {
      title: "60 Code Finance", codes: "Finance Codes", statement: "Statement",
      createTransaction: "Create Finance Transaction", code: "Code",
      amount: "Amount", description: "Description"
    },
    contracts: {
      title: "Contracts", create: "Create Contract", settlement: "Settlement",
      salary: "Salary", type: "Type", version: "Version",
      startDate: "Start Date", endDate: "End Date"
    },
    employees: {
      title: "Employees", manage: "Manage Employees",
      name: "Name", department: "Department", position: "Position",
      status: "Status", active: "Active", inactive: "Inactive"
    },
    stas: {
      mirror: "STAS Mirror", preChecks: "Pre-Checks", traceLinks: "Trace Links (Veins)",
      beforeAfter: "Before / After Projection", execute: "Execute",
      allPass: "All checks passed", hasFails: "Some checks failed",
      executing: "Executing...", executed: "Executed",
      pass: "PASS", fail: "FAIL"
    },
    common: {
      save: "Save", cancel: "Cancel", confirm: "Confirm", delete: "Delete",
      edit: "Edit", view: "View", close: "Close", loading: "Loading...",
      search: "Search", filter: "Filter", noData: "No data",
      back: "Back", next: "Next", submit: "Submit"
    },
    roles: {
      employee: "Employee", supervisor: "Supervisor",
      sultan: "Ops Admin", naif: "Ops Strategic",
      salah: "Finance", mohammed: "CEO", stas: "STAS"
    },
    status: {
      created: "Created", pending_supervisor: "Pending Supervisor",
      pending_ops: "Pending Ops", pending_finance: "Pending Finance",
      pending_ceo: "Pending CEO", pending_stas: "Pending STAS",
      executed: "Executed", rejected: "Rejected"
    },
    theme: { light: "Light", dark: "Dark", toggle: "Toggle Theme" },
    lang: { toggle: "العربية", current: "English" }
  },
  ar: {
    app: { name: "دار الكود - نظام الموارد البشرية", company: "شركة دار الكود للاستشارات الهندسية" },
    nav: {
      dashboard: "لوحة القيادة", transactions: "المعاملات", leave: "الإجازات",
      attendance: "الحضور", finance: "المالية", contracts: "العقود",
      employees: "الموظفين", settings: "الإعدادات", stasMirror: "مرآة ستاس",
      logout: "تسجيل الخروج", profile: "الملف الشخصي"
    },
    login: {
      title: "تسجيل الدخول", subtitle: "نظام دار الكود للموارد البشرية",
      username: "اسم المستخدم", password: "كلمة المرور",
      submit: "دخول", error: "بيانات الدخول غير صحيحة",
      noSignup: "تواصل مع مسؤول ستاس للحصول على حساب"
    },
    dashboard: {
      welcome: "مرحباً", pendingApprovals: "الموافقات المعلقة",
      leaveBalance: "رصيد الإجازات", teamSize: "حجم الفريق",
      totalEmployees: "إجمالي الموظفين", pendingExecution: "معلق التنفيذ",
      totalTransactions: "إجمالي المعاملات", recentTransactions: "المعاملات الأخيرة",
      pendingFinance: "المالية المعلقة", days: "أيام"
    },
    transactions: {
      title: "المعاملات", inbox: "الوارد", all: "جميع المعاملات",
      refNo: "رقم المرجع", type: "النوع", status: "الحالة", employee: "الموظف",
      stage: "المرحلة الحالية", date: "التاريخ", actions: "الإجراءات",
      approve: "موافقة", reject: "رفض", viewDetail: "عرض التفاصيل",
      downloadPdf: "تحميل PDF", timeline: "الجدول الزمني", approvalChain: "سلسلة الموافقات",
      noTransactions: "لا توجد معاملات"
    },
    leave: {
      title: "إدارة الإجازات", requestLeave: "طلب إجازة",
      balance: "رصيد الإجازات", history: "سجل الإجازات",
      type: "نوع الإجازة", startDate: "تاريخ البداية", endDate: "تاريخ النهاية",
      reason: "السبب", submit: "إرسال الطلب",
      annual: "سنوية", sick: "مرضية", emergency: "طارئة",
      workingDays: "أيام العمل", remaining: "المتبقي",
      holidays: "العطل الرسمية"
    },
    attendance: {
      title: "الحضور", checkIn: "تسجيل الدخول", checkOut: "تسجيل الخروج",
      todayStatus: "حالة اليوم", history: "السجل",
      gpsRequired: "موقع GPS مطلوب للحضور",
      noGps: "GPS غير متوفر على هذا الجهاز",
      checkedIn: "تم تسجيل الدخول", checkedOut: "تم تسجيل الخروج",
      notCheckedIn: "لم يتم تسجيل الدخول"
    },
    finance: {
      title: "المالية - 60 رمز", codes: "رموز المالية", statement: "كشف الحساب",
      createTransaction: "إنشاء معاملة مالية", code: "الرمز",
      amount: "المبلغ", description: "الوصف"
    },
    contracts: {
      title: "العقود", create: "إنشاء عقد", settlement: "التسوية",
      salary: "الراتب", type: "النوع", version: "الإصدار",
      startDate: "تاريخ البداية", endDate: "تاريخ النهاية"
    },
    employees: {
      title: "الموظفين", manage: "إدارة الموظفين",
      name: "الاسم", department: "القسم", position: "المنصب",
      status: "الحالة", active: "نشط", inactive: "غير نشط"
    },
    stas: {
      mirror: "مرآة ستاس", preChecks: "الفحوصات المسبقة", traceLinks: "روابط التتبع (العروق)",
      beforeAfter: "الإسقاط قبل / بعد", execute: "تنفيذ",
      allPass: "جميع الفحوصات ناجحة", hasFails: "بعض الفحوصات فاشلة",
      executing: "جارٍ التنفيذ...", executed: "تم التنفيذ",
      pass: "ناجح", fail: "فاشل"
    },
    common: {
      save: "حفظ", cancel: "إلغاء", confirm: "تأكيد", delete: "حذف",
      edit: "تعديل", view: "عرض", close: "إغلاق", loading: "جارٍ التحميل...",
      search: "بحث", filter: "تصفية", noData: "لا توجد بيانات",
      back: "رجوع", next: "التالي", submit: "إرسال"
    },
    roles: {
      employee: "موظف", supervisor: "مشرف",
      sultan: "مدير العمليات", naif: "العمليات الاستراتيجية",
      salah: "المالية", mohammed: "الرئيس التنفيذي", stas: "ستاس"
    },
    status: {
      created: "تم الإنشاء", pending_supervisor: "بانتظار المشرف",
      pending_ops: "بانتظار العمليات", pending_finance: "بانتظار المالية",
      pending_ceo: "بانتظار الرئيس", pending_stas: "بانتظار ستاس",
      executed: "تم التنفيذ", rejected: "مرفوض"
    },
    theme: { light: "فاتح", dark: "داكن", toggle: "تبديل المظهر" },
    lang: { toggle: "English", current: "العربية" }
  }
};
