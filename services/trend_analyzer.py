"""
趋势分析服务
按时间段统计技能频率变化，生成趋势数据
"""

import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from collections import defaultdict
import re


class TrendAnalyzer:
    """技能趋势分析器"""
    
    def __init__(self):
        """初始化趋势分析器"""
        self.time_periods: List[str] = []
        self.period_skill_counts: Dict[str, Dict[str, int]] = {}
    
    def parse_date(self, date_str: str) -> Optional[datetime]:
        """
        解析日期字符串
        
        Args:
            date_str: 日期字符串
            
        Returns:
            解析后的 datetime 对象
        """
        if not date_str or date_str == 'nan' or pd.isna(date_str):
            return None
        
        # 尝试多种日期格式
        date_formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%Y-%m',
            '%Y/%m',
            '%Y年%m月%d日',
            '%Y年%m月',
            '%m/%d/%Y',
            '%d-%m-%Y',
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(str(date_str), fmt)
            except ValueError:
                continue
        
        # 尝试提取年月（兼容模糊日期）
        match = re.search(r'(\d{4})[-/年](\d{1,2})', str(date_str))
        if match:
            year, month = int(match.group(1)), int(match.group(2))
            if 1 <= month <= 12:
                return datetime(year, month, 1)
        
        return None
    
    def group_by_period(
        self,
        dates: List[Optional[str]],
        period_type: str = 'month'
    ) -> Dict[str, List[int]]:
        """
        将日期按时间段分组
        
        Args:
            dates: 日期列表
            period_type: 分组类型 ('month', 'quarter', 'year')
            
        Returns:
            {时间段：[索引列表]}
        """
        period_indices: Dict[str, List[int]] = defaultdict(list)
        
        for idx, date_str in enumerate(dates):
            parsed_date = self.parse_date(date_str)
            
            if parsed_date is None:
                # 无法解析的日期归为"未知"
                period_indices['unknown'].append(idx)
                continue
            
            # 按时间段格式化
            if period_type == 'year':
                period = parsed_date.strftime('%Y')
            elif period_type == 'quarter':
                quarter = (parsed_date.month - 1) // 3 + 1
                period = f'{parsed_date.year}Q{quarter}'
            else:  # month (default)
                period = parsed_date.strftime('%Y-%m')
            
            period_indices[period].append(idx)
        
        return dict(period_indices)
    
    def analyze_trend(
        self,
        skill_counts_by_period: Dict[str, Dict[str, int]],
        top_n: int = 20
    ) -> Dict:
        """
        分析技能趋势
        
        Args:
            skill_counts_by_period: {时间段：{技能词：次数}}
            top_n: 返回 Top N 技能
            
        Returns:
            趋势分析结果
        """
        if not skill_counts_by_period:
            return {'error': '无数据'}
        
        # 排序时间段
        sorted_periods = sorted(skill_counts_by_period.keys())
        
        # 收集所有技能
        all_skills: Set[str] = set()
        for period_data in skill_counts_by_period.values():
            all_skills.update(period_data.keys())
        
        # 计算每个技能的总频次
        skill_totals = defaultdict(int)
        for period_data in skill_counts_by_period.values():
            for skill, count in period_data.items():
                skill_totals[skill] += count
        
        # 取 Top N 技能
        top_skills = sorted(skill_totals.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
        # 构建趋势数据
        trend_data = {
            'periods': sorted_periods,
            'skills': [],
            'trend_series': []
        }
        
        for skill, total_count in top_skills:
            series_data = []
            for period in sorted_periods:
                count = skill_counts_by_period.get(period, {}).get(skill, 0)
                series_data.append(count)
            
            trend_data['skills'].append({
                'name': skill,
                'total': total_count
            })
            trend_data['trend_series'].append({
                'name': skill,
                'data': series_data
            })
        
        # 计算增长率
        growth_rates = self._calculate_growth_rates(skill_counts_by_period, top_skills)
        trend_data['growth_rates'] = growth_rates
        
        return trend_data
    
    def _calculate_growth_rates(
        self,
        skill_counts_by_period: Dict[str, Dict[str, int]],
        top_skills: List[Tuple[str, int]]
    ) -> Dict[str, float]:
        """
        计算技能增长率
        
        Args:
            skill_counts_by_period: {时间段：{技能词：次数}}
            top_skills: Top 技能列表
            
        Returns:
            {技能词：增长率}
        """
        sorted_periods = sorted(skill_counts_by_period.keys())
        
        if len(sorted_periods) < 2:
            return {}
        
        first_period = sorted_periods[0]
        last_period = sorted_periods[-1]
        
        growth_rates = {}
        for skill, _ in top_skills:
            first_count = skill_counts_by_period.get(first_period, {}).get(skill, 0)
            last_count = skill_counts_by_period.get(last_period, {}).get(skill, 0)
            
            if first_count > 0:
                rate = ((last_count - first_count) / first_count) * 100
                growth_rates[skill] = round(rate, 2)
            else:
                growth_rates[skill] = float('inf') if last_count > 0 else 0
        
        return growth_rates
    
    def prepare_excel_trend_data(
        self,
        skill_counts_by_period: Dict[str, Dict[str, int]]
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        准备 Excel 趋势数据
        
        Args:
            skill_counts_by_period: {时间段：{技能词：次数}}
            
        Returns:
            (汇总表数据，详细数据)
        """
        sorted_periods = sorted(skill_counts_by_period.keys())
        
        # 收集所有技能
        all_skills: Set[str] = set()
        for period_data in skill_counts_by_period.values():
            all_skills.update(period_data.keys())
        
        # 计算总计
        skill_totals = defaultdict(int)
        for period_data in skill_counts_by_period.values():
            for skill, count in period_data.items():
                skill_totals[skill] += count
        
        # 汇总表（Top 20）
        summary_data = []
        for skill, total in sorted(skill_totals.items(), key=lambda x: x[1], reverse=True)[:20]:
            row = {'技能词': skill, '总计': total}
            for period in sorted_periods:
                count = skill_counts_by_period.get(period, {}).get(skill, 0)
                row[period] = count
            summary_data.append(row)
        
        # 详细数据（按时间段）
        detail_data = []
        for period in sorted_periods:
            period_skills = skill_counts_by_period.get(period, {})
            for skill, count in sorted(period_skills.items(), key=lambda x: x[1], reverse=True):
                detail_data.append({
                    '时间段': period,
                    '技能词': skill,
                    '出现次数': count,
                    '占比': round(count / sum(period_skills.values()) * 100, 2) if period_skills else 0
                })
        
        return summary_data, detail_data
