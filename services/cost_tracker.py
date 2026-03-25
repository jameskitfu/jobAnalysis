"""
成本追踪器
监控和统计大模型 API 调用成本
"""

import json
from typing import Dict, List
from pathlib import Path
from datetime import datetime, timedelta


class CostTracker:
    """API 成本追踪器"""
    
    def __init__(self, stats_path: str = None):
        """
        初始化成本追踪器
        
        Args:
            stats_path: 统计数据存储路径（JSON 文件）
        """
        self.stats_path = Path(stats_path) if stats_path else None
        
        # 如果没有指定路径，使用默认位置
        if self.stats_path is None:
            from pathlib import Path
            base_dir = Path(__file__).parent.parent
            self.stats_path = base_dir / "data" / "llm_usage_stats.json"
        
        # 确保目录存在
        self.stats_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载统计数据
        self.stats = {
            'total_requests': 0,
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'total_cost': 0.0,
            'monthly_stats': {},  # {YYYY-MM: {...}}
            'daily_stats': {},    # {YYYY-MM-DD: {...}}
            'last_updated': None,
        }
        self._load_stats()
        
        # Provider 价格表（元/千 tokens）
        self.price_table = {
            'aliyun': {
                'qwen-max': {'input': 0.04, 'output': 0.12},
                'qwen-plus': {'input': 0.02, 'output': 0.06},
                'default': {'input': 0.04, 'output': 0.12},
            },
            'baidu': {
                'ernie-bot-4': {'input': 0.03, 'output': 0.09},
                'ernie-bot-turbo': {'input': 0.01, 'output': 0.03},
                'default': {'input': 0.03, 'output': 0.09},
            },
            'iflytek': {
                'spark-v3.5': {'input': 0.02, 'output': 0.08},
                'default': {'input': 0.02, 'output': 0.08},
            },
        }
    
    def _load_stats(self):
        """加载统计数据"""
        if self.stats_path.exists():
            with open(self.stats_path, 'r', encoding='utf-8') as f:
                try:
                    loaded_stats = json.load(f)
                    self.stats.update(loaded_stats)
                except json.JSONDecodeError:
                    pass
    
    def _save_stats(self):
        """保存统计数据"""
        self.stats['last_updated'] = datetime.now().isoformat()
        
        with open(self.stats_path, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)
    
    def record_usage(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        success: bool = True
    ):
        """
        记录每次 API 调用
        
        Args:
            provider: Provider 名称
            model: 模型名称
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
            success: 是否成功
        """
        now = datetime.now()
        month_key = now.strftime('%Y-%m')
        day_key = now.strftime('%Y-%d')
        
        # 计算成本
        cost = self.calculate_cost(provider, model, input_tokens, output_tokens)
        
        # 更新总计
        self.stats['total_requests'] += 1
        self.stats['total_input_tokens'] += input_tokens
        self.stats['total_output_tokens'] += output_tokens
        self.stats['total_cost'] += cost
        
        # 更新月度统计
        if month_key not in self.stats['monthly_stats']:
            self.stats['monthly_stats'][month_key] = {
                'requests': 0,
                'input_tokens': 0,
                'output_tokens': 0,
                'cost': 0.0,
            }
        
        month_stat = self.stats['monthly_stats'][month_key]
        month_stat['requests'] += 1
        month_stat['input_tokens'] += input_tokens
        month_stat['output_tokens'] += output_tokens
        month_stat['cost'] += cost
        
        # 更新每日统计
        if day_key not in self.stats['daily_stats']:
            self.stats['daily_stats'][day_key] = {
                'requests': 0,
                'input_tokens': 0,
                'output_tokens': 0,
                'cost': 0.0,
            }
        
        day_stat = self.stats['daily_stats'][day_key]
        day_stat['requests'] += 1
        day_stat['input_tokens'] += input_tokens
        day_stat['output_tokens'] += output_tokens
        day_stat['cost'] += cost
        
        # 保存
        self._save_stats()
    
    def calculate_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        计算 API 调用成本
        
        Args:
            provider: Provider 名称
            model: 模型名称
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
            
        Returns:
            float: 成本（元）
        """
        # 获取价格
        prices = self.price_table.get(provider, {}).get(model)
        if not prices:
            prices = self.price_table.get(provider, {}).get('default', {'input': 0.04, 'output': 0.12})
        
        # 计算成本
        input_cost = (input_tokens / 1000) * prices['input']
        output_cost = (output_tokens / 1000) * prices['output']
        
        return round(input_cost + output_cost, 4)
    
    def get_total_cost(self) -> float:
        """获取总成本"""
        return round(self.stats['total_cost'], 2)
    
    def get_monthly_cost(self, year_month: str = None) -> float:
        """
        获取月度成本
        
        Args:
            year_month: 年月（YYYY-MM），默认为当前月
            
        Returns:
            float: 成本（元）
        """
        if year_month is None:
            year_month = datetime.now().strftime('%Y-%m')
        
        month_stat = self.stats['monthly_stats'].get(year_month, {})
        return round(month_stat.get('cost', 0.0), 2)
    
    def get_daily_cost(self, year_month_day: str = None) -> float:
        """
        获取日成本
        
        Args:
            year_month_day: 日期（YYYY-MM-DD），默认为今天
            
        Returns:
            float: 成本（元）
        """
        if year_month_day is None:
            year_month_day = datetime.now().strftime('%Y-%m-%d')
        
        day_stat = self.stats['daily_stats'].get(year_month_day, {})
        return round(day_stat.get('cost', 0.0), 2)
    
    def is_budget_exceeded(self, budget: float, year_month: str = None) -> bool:
        """
        检查是否超出预算
        
        Args:
            budget: 预算金额
            year_month: 年月（YYYY-MM），默认为当前月
            
        Returns:
            bool: 是否超出预算
        """
        monthly_cost = self.get_monthly_cost(year_month)
        return monthly_cost > budget
    
    def get_budget_usage(self, budget: float, year_month: str = None) -> dict:
        """
        获取预算使用情况
        
        Args:
            budget: 预算金额
            year_month: 年月（YYYY-MM），默认为当前月
            
        Returns:
            dict: 使用情况
        """
        monthly_cost = self.get_monthly_cost(year_month)
        usage_rate = monthly_cost / budget if budget > 0 else 0.0
        
        return {
            'budget': budget,
            'used': monthly_cost,
            'remaining': max(0, budget - monthly_cost),
            'usage_rate': round(usage_rate, 2),
            'is_exceeded': usage_rate > 1.0,
            'alert_threshold': 0.8,
            'needs_alert': usage_rate > 0.8,
        }
    
    def get_statistics(self) -> dict:
        """获取完整统计信息"""
        return {
            'total': {
                'requests': self.stats['total_requests'],
                'input_tokens': self.stats['total_input_tokens'],
                'output_tokens': self.stats['total_output_tokens'],
                'cost': self.get_total_cost(),
            },
            'current_month': {
                'requests': self.stats['monthly_stats'].get(
                    datetime.now().strftime('%Y-%m'), {}
                ).get('requests', 0),
                'cost': self.get_monthly_cost(),
            },
            'today': {
                'requests': self.stats['daily_stats'].get(
                    datetime.now().strftime('%Y-%m-%d'), {}
                ).get('requests', 0),
                'cost': self.get_daily_cost(),
            },
        }
    
    def get_trend(self, days: int = 7) -> List[dict]:
        """
        获取最近 N 天的成本趋势
        
        Args:
            days: 天数
            
        Returns:
            List[dict]: 每日成本列表
        """
        trend = []
        today = datetime.now()
        
        for i in range(days):
            date = today - timedelta(days=i)
            day_key = date.strftime('%Y-%m-%d')
            day_stat = self.stats['daily_stats'].get(day_key, {})
            
            trend.append({
                'date': day_key,
                'requests': day_stat.get('requests', 0),
                'cost': round(day_stat.get('cost', 0.0), 2),
            })
        
        return trend
    
    def reset_stats(self):
        """重置统计数据（谨慎使用）"""
        self.stats = {
            'total_requests': 0,
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'total_cost': 0.0,
            'monthly_stats': {},
            'daily_stats': {},
            'last_updated': None,
        }
        self._save_stats()
