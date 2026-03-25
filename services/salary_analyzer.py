import re
from typing import Optional

class SalaryAnalyzer:
    """薪资解析与分析服务"""

    def __init__(self):
        self.patterns = [
            # 1. xx[k]-xxK·yy薪 或 xx[k]-xxk*yy
            (re.compile(r'(\d+(?:\.\d+)?)[kK]?\s*-\s*(\d+(?:\.\d+)?)[kK][·*](\d+)薪?', re.IGNORECASE), 'k_months'),
            # 2. xx[k]-xxK/月 或 xx[k]-xxk
            (re.compile(r'(\d+(?:\.\d+)?)[kK]?\s*-\s*(\d+(?:\.\d+)?)[kK]', re.IGNORECASE), 'k_month'),
            # 3. xx[万]-xx万/年（必须含 /年 后缀）
            (re.compile(r'(\d+(?:\.\d+)?)[万Ww]?\s*-\s*(\d+(?:\.\d+)?)[万Ww]/年', re.IGNORECASE), 'w_year'),
            # 4. xx[万]-xx万/月 或 xx[万]-xx万（裸万默认按月薪）
            (re.compile(r'(\d+(?:\.\d+)?)[万Ww]?\s*-\s*(\d+(?:\.\d+)?)[万Ww](?:/月)?', re.IGNORECASE), 'w_month'),
            # 5. xx-xx元/天
            (re.compile(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)元?/天', re.IGNORECASE), 'yuan_day'),
            # 6. 单一数字类型: xxK
            (re.compile(r'^(\d+(?:\.\d+)?)[kK]$', re.IGNORECASE), 'k_single')
        ]

    def parse_annual_salary(self, text: str) -> Optional[float]:
        """
        将各种格式的薪资文本解析并统一为【万/年】(单位：万)
        
        Args:
            text: 薪水字符串，如 '15-25K·14薪'
        Returns:
            年薪（万元），解析失败返回 None
        """
        if not text or not isinstance(text, str):
            return None
            
        text = text.strip().replace(' ', '')
        if text in ['面议', '不限', '保密', 'nan']:
            return None

        for pattern, p_type in self.patterns:
            match = pattern.search(text)
            if match:
                try:
                    if p_type == 'k_months':
                        # ('15', '25', '14') -> 20k * 14 = 280k = 28.0万
                        low, high, months = map(float, match.groups())
                        if low > high: low, high = high, low
                        return ((low + high) / 2) * months / 10.0
                        
                    elif p_type == 'k_month':
                        # ('15', '25') -> 20k * 12 = 240k = 24.0万
                        low, high = map(float, match.groups())
                        if low > high: low, high = high, low
                        return ((low + high) / 2) * 12 / 10.0
                        
                    elif p_type == 'w_year':
                        # ('20', '30') -> 25.0万
                        low, high = float(match.group(1)), float(match.group(2))
                        if low > high: low, high = high, low
                        return (low + high) / 2
                        
                    elif p_type == 'w_month':
                        # ('1.5', '2.5') -> 2.0w * 12 = 24.0万
                        low, high = float(match.group(1)), float(match.group(2))
                        if low > high: low, high = high, low
                        return ((low + high) / 2) * 12
                        
                    elif p_type == 'yuan_day':
                        # ('300', '400') -> 350元 * 22天 * 12月 = 92400元 = 9.24万
                        low, high = map(float, match.groups())
                        if low > high: low, high = high, low
                        return ((low + high) / 2) * 22 * 12 / 10000.0
                        
                    elif p_type == 'k_single':
                        # ('15') -> 15k * 12 = 180k = 18.0万
                        val = float(match.group(1))
                        return val * 12 / 10.0
                        
                except ValueError:
                    continue
                    
        return None
