"""
تحويل الأرقام إلى كلمات عربية
Arabic Number to Words Converter
"""

ONES = ['', 'واحد', 'اثنان', 'ثلاثة', 'أربعة', 'خمسة', 'ستة', 'سبعة', 'ثمانية', 'تسعة']
TENS = ['', 'عشرة', 'عشرون', 'ثلاثون', 'أربعون', 'خمسون', 'ستون', 'سبعون', 'ثمانون', 'تسعون']
TEENS = ['عشرة', 'أحد عشر', 'اثنا عشر', 'ثلاثة عشر', 'أربعة عشر', 'خمسة عشر', 
         'ستة عشر', 'سبعة عشر', 'ثمانية عشر', 'تسعة عشر']
HUNDREDS = ['', 'مائة', 'مائتان', 'ثلاثمائة', 'أربعمائة', 'خمسمائة', 
            'ستمائة', 'سبعمائة', 'ثمانمائة', 'تسعمائة']


def number_to_arabic(num: float) -> str:
    """
    تحويل الرقم إلى كلمات عربية
    مثال: 247242.00 -> "مائتان وسبعة وأربعون ألفاً ومائتان واثنان وأربعون ريالاً"
    """
    if num == 0:
        return "صفر ريال"
    
    # تقريب للعدد الصحيح
    num = int(round(num))
    
    if num < 0:
        return "سالب " + number_to_arabic(abs(num))
    
    parts = []
    
    # الملايين
    if num >= 1000000:
        millions = num // 1000000
        num %= 1000000
        if millions == 1:
            parts.append("مليون")
        elif millions == 2:
            parts.append("مليونان")
        elif 3 <= millions <= 10:
            parts.append(_convert_ones(millions) + " ملايين")
        else:
            parts.append(_convert_hundreds(millions) + " مليون")
    
    # الآلاف
    if num >= 1000:
        thousands = num // 1000
        num %= 1000
        if thousands == 1:
            parts.append("ألف")
        elif thousands == 2:
            parts.append("ألفان")
        elif 3 <= thousands <= 10:
            parts.append(_convert_ones(thousands) + " آلاف")
        else:
            parts.append(_convert_hundreds(thousands) + " ألفاً")
    
    # المئات والعشرات والآحاد
    if num > 0:
        parts.append(_convert_hundreds(num))
    
    result = " و".join(parts)
    result += " ريالاً فقط لا غير"
    
    return result


def _convert_ones(n: int) -> str:
    """تحويل الآحاد"""
    if 0 <= n <= 9:
        return ONES[n]
    return str(n)


def _convert_tens(n: int) -> str:
    """تحويل العشرات"""
    if n < 10:
        return _convert_ones(n)
    elif 10 <= n <= 19:
        return TEENS[n - 10]
    else:
        ones = n % 10
        tens = n // 10
        if ones == 0:
            return TENS[tens]
        else:
            return ONES[ones] + " و" + TENS[tens]


def _convert_hundreds(n: int) -> str:
    """تحويل المئات"""
    if n < 100:
        return _convert_tens(n)
    else:
        hundreds = n // 100
        remainder = n % 100
        if remainder == 0:
            return HUNDREDS[hundreds]
        else:
            return HUNDREDS[hundreds] + " و" + _convert_tens(remainder)


# اختبار سريع
if __name__ == "__main__":
    test_numbers = [0, 1, 15, 100, 247, 1000, 2500, 8450, 18000, 99000, 148242, 247242]
    for n in test_numbers:
        print(f"{n:,} = {number_to_arabic(n)}")
