"""
CSV 解析服务
负责读取和解析上传的 CSV 文件，支持多种编码格式
"""

import pandas as pd
import chardet
from typing import List, Optional
from pathlib import Path


class CSVParser:
    """CSV 文件解析器"""
    
    # 常见需要检测的列名（用于提取职位描述文本）
    DESCRIPTION_COLUMNS = [
        'description',
        'job_description',
        'jobdescription',
        '职位描述',
        '岗位描述',
        '职责描述',
        '工作内容',
        'requirements',
        '要求',
        '任职资格',
        '技能要求',
        'text',
        'content'
    ]
    
    def __init__(self, file_path: str):
        """
        初始化 CSV 解析器
        
        Args:
            file_path: CSV 文件路径
        """
        self.file_path = Path(file_path)
        self.df: Optional[pd.DataFrame] = None
        self.encoding: str = 'utf-8'
        
    def detect_encoding(self) -> str:
        """
        自动检测文件编码
        优先检测中文编码（GBK、GB18030）
        
        Returns:
            检测到的编码格式
        """
        with open(self.file_path, 'rb') as f:
            # 读取前 100KB 进行编码检测
            raw_data = f.read(100 * 1024)
            result = chardet.detect(raw_data)
            detected = result['encoding'] or 'utf-8'
            
            # 中文编码统一使用 GB18030（兼容 GB2312/GBK）
            if detected and ('gb2312' in detected.lower() or 'gbk' in detected.lower()):
                self.encoding = 'gb18030'
                return 'gb18030'
            
            # chardet 对中文编码检测可能不准确，尝试常见中文编码
            # 如果检测到 ASCII 或 UTF-8，但文件包含中文字符，尝试 GBK/GB18030
            if detected.lower() in ['ascii', 'utf-8', 'utf-8-sig']:
                # 尝试用 GB18030 解码部分数据，看是否成功
                try:
                    raw_data.decode('gb18030')
                    self.encoding = 'gb18030'
                    return 'gb18030'
                except UnicodeDecodeError:
                    pass
            
            self.encoding = detected
            return detected
    
    def load(self) -> bool:
        """
        加载并解析 CSV 文件
        
        Returns:
            是否加载成功
        """
        try:
            # 先检测编码
            if self.encoding == 'utf-8':
                self.detect_encoding()
            
            # 使用 Python 引擎，支持复杂的多行文本
            for sep in [',', '\t', ';']:
                try:
                    self.df = pd.read_csv(
                        self.file_path,
                        encoding=self.encoding,
                        sep=sep,
                        engine='python',
                        quotechar='"',
                        skipinitialspace=True
                    )
                    break
                except Exception:
                    continue
            
            if self.df is None or len(self.df) == 0:
                print("CSV 文件为空或解析失败")
                return False
            
            return True
        except Exception as e:
            print(f"加载 CSV 失败：{e}")
            return False
    
    def get_description_column(self) -> Optional[str]:
        """
        获取职位描述列的名称
        
        Returns:
            列名，如果未找到则返回 None
        """
        if self.df is None:
            return None
        
        # 标准化列名（转小写、去空格）
        column_mapping = {
            col.lower().strip(): col 
            for col in self.df.columns
        }
        
        # 查找匹配的列
        for desc_col in self.DESCRIPTION_COLUMNS:
            if desc_col.lower() in column_mapping:
                return column_mapping[desc_col.lower()]
        
        # 如果没找到，返回第一列文本类型的列
        for col in self.df.columns:
            if self.df[col].dtype == 'object':
                # 检查该列是否有较长的文本内容
                sample = str(self.df[col].iloc[0]) if len(self.df) > 0 else ''
                if len(sample) > 50:  # 假设职位描述至少 50 字符
                    return col
        
        return None
    
    def get_job_descriptions(self) -> List[str]:
        """
        获取所有职位描述文本
        
        Returns:
            职位描述文本列表
        """
        if self.df is None:
            return []
        
        desc_col = self.get_description_column()
        if desc_col is None:
            # 如果没有找到描述列，合并所有文本列
            texts = []
            for col in self.df.columns:
                if self.df[col].dtype == 'object':
                    texts.extend(self.df[col].dropna().astype(str).tolist())
            return [t for t in texts if len(t) > 10]  # 过滤太短的文本
        
        # 返回指定列的所有非空值
        descriptions = self.df[desc_col].dropna().astype(str).tolist()
        return [d for d in descriptions if len(d) > 10 and d != 'nan']
    
    def count_rows(self) -> int:
        """
        获取 CSV 行数（不包括表头）
        
        Returns:
            行数
        """
        if self.df is None:
            return 0
        return len(self.df)
    
    def get_columns_info(self) -> dict:
        """
        获取列信息
        
        Returns:
            包含列名和类型的字典
        """
        if self.df is None:
            return {}
        
        return {
            'columns': list(self.df.columns),
            'row_count': len(self.df),
            'description_column': self.get_description_column()
        }
    
    def get_date_column(self) -> Optional[str]:
        """
        获取日期/时间列的名称
        
        Returns:
            列名，如果未找到则返回 None
        """
        if self.df is None:
            return None
        
        # 常见日期列名
        date_columns = [
            'date', 'pub_date', 'publish_date', 'post_date',
            '发布日期', '发布时间', '日期', '更新时间',
            'created_at', 'updated_at', 'timestamp'
        ]
        
        column_mapping = {
            col.lower().strip(): col 
            for col in self.df.columns
        }
        
        for date_col in date_columns:
            if date_col.lower() in column_mapping:
                return column_mapping[date_col.lower()]
        
        return None
    
    def get_dates(self) -> List[Optional[str]]:
        """
        获取所有日期数据
        
        Returns:
            日期列表
        """
        if self.df is None:
            return []
        
        date_col = self.get_date_column()
        if date_col is None:
            return [None] * len(self.df)
        
        return self.df[date_col].fillna('').astype(str).tolist()
