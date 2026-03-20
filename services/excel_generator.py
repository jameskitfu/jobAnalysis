"""
Excel 生成器
负责生成技能统计报表 Excel 文件
"""

import pandas as pd
from typing import Dict, List, Tuple
from pathlib import Path
from datetime import datetime


class ExcelGenerator:
    """Excel 报表生成器"""
    
    def __init__(self):
        """初始化 Excel 生成器"""
        pass
    
    def generate(
        self,
        total_counts: Dict[str, int],
        category_counts: Dict[str, Dict[str, int]],
        output_path: str,
        source_file: str = '',
        total_positions: int = 0
    ) -> str:
        """
        生成 Excel 统计报表
        
        Args:
            total_counts: 总统计表 {技能词：出现次数}
            category_counts: 分类统计表 {类别：{技能词：出现次数}}
            output_path: 输出文件路径
            source_file: 源文件名
            total_positions: 总职位数
            
        Returns:
            生成的文件路径
        """
        output_path = Path(output_path)
        
        # 创建 Excel Writer
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Sheet 1: 总统计表
            self._create_summary_sheet(
                writer, total_counts, source_file, total_positions
            )
            
            # Sheet 2: 分类统计
            self._create_category_sheets(writer, category_counts)
            
            # Sheet 3: Top 技能排行
            self._create_top_skills_sheet(writer, total_counts)
        
        return str(output_path)
    
    def generate_with_trend(
        self,
        total_counts: Dict[str, int],
        category_counts: Dict[str, Dict[str, int]],
        trend_data: Dict,
        summary_data: List[Dict],
        detail_data: List[Dict],
        output_path: str,
        source_file: str = '',
        total_positions: int = 0
    ) -> str:
        """
        生成带趋势分析的 Excel 报表
        
        Args:
            total_counts: 总统计表
            category_counts: 分类统计表
            trend_data: 趋势分析数据
            summary_data: 趋势汇总数据
            detail_data: 趋势详细数据
            output_path: 输出文件路径
            source_file: 源文件名
            total_positions: 总职位数
            
        Returns:
            生成的文件路径
        """
        output_path = Path(output_path)
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Sheet 1: 总统计表
            self._create_summary_sheet(writer, total_counts, source_file, total_positions)
            
            # Sheet 2: 分类统计
            self._create_category_sheets(writer, category_counts)
            
            # Sheet 3: Top 技能排行
            self._create_top_skills_sheet(writer, total_counts)
            
            # Sheet 4+: 趋势分析
            if trend_data and 'error' not in trend_data:
                self._create_trend_sheets(writer, trend_data, summary_data, detail_data)
        
        return str(output_path)
    
    def _create_trend_sheets(
        self,
        writer: pd.ExcelWriter,
        trend_data: Dict,
        summary_data: List[Dict],
        detail_data: List[Dict]
    ):
        """创建趋势分析工作表"""
        # 趋势汇总表
        if summary_data:
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='技能趋势汇总', index=False)
            
            worksheet = writer.sheets['技能趋势汇总']
            worksheet.column_dimensions['A'].width = 25
            worksheet.column_dimensions['B'].width = 12
        
        # 趋势详细表
        if detail_data:
            df_detail = pd.DataFrame(detail_data)
            df_detail.to_excel(writer, sheet_name='趋势详情', index=False)
            
            worksheet = writer.sheets['趋势详情']
            worksheet.column_dimensions['A'].width = 12
            worksheet.column_dimensions['B'].width = 25
            worksheet.column_dimensions['C'].width = 12
            worksheet.column_dimensions['D'].width = 10
        
        # 增长率排名
        if 'growth_rates' in trend_data and trend_data['growth_rates']:
            growth_data = [
                {'技能词': skill, '增长率 (%)': rate}
                for skill, rate in sorted(
                    trend_data['growth_rates'].items(),
                    key=lambda x: x[1] if x[1] != float('inf') else 0,
                    reverse=True
                )[:20]
            ]
            df_growth = pd.DataFrame(growth_data)
            df_growth.to_excel(writer, sheet_name='增长率排名', index=False)
            
            worksheet = writer.sheets['增长率排名']
            worksheet.column_dimensions['A'].width = 25
            worksheet.column_dimensions['B'].width = 15
    
    def _create_summary_sheet(
        self,
        writer: pd.ExcelWriter,
        total_counts: Dict[str, int],
        source_file: str,
        total_positions: int
    ):
        """
        创建总统计工作表
        
        Args:
            writer: Excel Writer
            total_counts: 总统计表
            source_file: 源文件名
            total_positions: 总职位数
        """
        # 计算总频次
        total_frequency = sum(total_counts.values())
        
        # 构建数据
        data = []
        for skill, count in sorted(total_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_positions * 100) if total_positions > 0 else 0
            data.append({
                '技能词': skill,
                '出现次数': count,
                '占比 (%)': round(percentage, 2),
                '累计占比': None  # 后面计算
            })
        
        # 计算累计占比
        cumulative = 0
        for row in data:
            cumulative += row['占比 (%)']
            row['累计占比'] = round(cumulative, 2)
        
        df = pd.DataFrame(data)
        
        # 写入 Excel
        df.to_excel(writer, sheet_name='总统计', index=False)
        
        # 添加表头信息
        worksheet = writer.sheets['总统计']
        worksheet.insert_rows(0, 3)
        
        # 写入表头信息
        worksheet.cell(row=1, column=1, value=f'技能词频统计报表')
        worksheet.cell(row=2, column=1, value=f'数据来源：{source_file}')
        worksheet.cell(row=3, column=1, value=f'生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        worksheet.cell(row=3, column=3, value=f'总职位数：{total_positions}')
        worksheet.cell(row=3, column=5, value=f'技能词总数：{len(total_counts)}')
        
        # 合并表头单元格
        from openpyxl.styles import Font, Alignment, PatternFill
        
        # 标题样式
        title_font = Font(bold=True, size=16)
        title_cell = worksheet.cell(row=1, column=1)
        title_cell.font = title_font
        
        # 调整列宽
        worksheet.column_dimensions['A'].width = 25
        worksheet.column_dimensions['B'].width = 12
        worksheet.column_dimensions['C'].width = 12
        worksheet.column_dimensions['D'].width = 12
    
    def _create_category_sheets(
        self,
        writer: pd.ExcelWriter,
        category_counts: Dict[str, Dict[str, int]]
    ):
        """
        创建分类统计工作表
        
        Args:
            writer: Excel Writer
            category_counts: 分类统计表
        """
        category_names = {
            'programming_languages': '编程语言',
            'backend_frameworks': '后端框架',
            'frontend_frameworks': '前端框架',
            'ml_frameworks': '机器学习',
            'databases': '数据库',
            'devops_tools': 'DevOps 工具',
            'version_control': '版本控制',
            'cloud_platforms': '云平台',
            'operating_systems': '操作系统',
            'message_queues': '消息队列',
            'architecture': '架构技术',
            'soft_skills': '软技能'
        }
        
        for category_en, skills in category_counts.items():
            # 获取中文名称
            category_cn = category_names.get(category_en, category_en)
            
            # 构建数据
            data = []
            total_in_category = sum(skills.values())
            for skill, count in sorted(skills.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_in_category * 100) if total_in_category > 0 else 0
                data.append({
                    '技能词': skill,
                    '出现次数': count,
                    '类别内占比 (%)': round(percentage, 2)
                })
            
            df = pd.DataFrame(data)
            
            # 限制 sheet 名称长度（Excel 限制 31 字符）
            sheet_name = category_cn[:31]
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # 调整列宽
            worksheet = writer.sheets[sheet_name]
            worksheet.column_dimensions['A'].width = 25
            worksheet.column_dimensions['B'].width = 12
            worksheet.column_dimensions['C'].width = 15
    
    def _create_top_skills_sheet(
        self,
        writer: pd.ExcelWriter,
        total_counts: Dict[str, int]
    ):
        """
        创建 Top 技能排行工作表
        
        Args:
            writer: Excel Writer
            total_counts: 总统计表
        """
        # 取 Top 50
        top_skills = sorted(total_counts.items(), key=lambda x: x[1], reverse=True)[:50]
        
        data = []
        for rank, (skill, count) in enumerate(top_skills, 1):
            data.append({
                '排名': rank,
                '技能词': skill,
                '出现次数': count
            })
        
        df = pd.DataFrame(data)
        df.to_excel(writer, sheet_name='Top50 排行', index=False)
        
        # 调整列宽
        worksheet = writer.sheets['Top50 排行']
        worksheet.column_dimensions['A'].width = 8
        worksheet.column_dimensions['B'].width = 25
        worksheet.column_dimensions['C'].width = 12
