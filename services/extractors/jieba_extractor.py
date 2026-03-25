"""
Jieba 分词技能提取器
封装现有的 SmartSkillMatcher 逻辑，实现统一的 SkillExtractor 接口
"""

from .base_extractor import SkillExtractor, SkillResult, NewSkillCandidate
from ..smart_skill_matcher import SmartSkillMatcher


class JiebaExtractor(SkillExtractor):
    """基于 Jieba 分词的技能提取器"""
    
    def __init__(self, config_path: str):
        """
        初始化 Jieba 提取器
        
        Args:
            config_path: 技能词库 YAML 配置文件路径
        """
        self.matcher = SmartSkillMatcher(config_path)
        self.config_path = config_path
    
    def extract(self, text: str) -> SkillResult:
        """从文本中提取技能（使用 Jieba 分词）
        
        Args:
            text: 输入的职位描述文本
            
        Returns:
            SkillResult: 包含标准技能的结果（Jieba 模式不支持新技能发现）
        """
        # 使用现有的智能匹配逻辑
        matched_skills = self.matcher.find_skills_smart(text)
        
        # 计算置信度（基于匹配的技能和上下文验证）
        confidence = self._calculate_confidence(text, matched_skills)
        
        return SkillResult(
            standard_skills=matched_skills,
            new_skills=[],  # Jieba 模式不支持新技能发现
            confidence=confidence,
            metadata={
                'mode': 'jieba',
                'total_skills': sum(len(skills) for skills in matched_skills.values()),
            }
        )
    
    def _calculate_confidence(self, text: str, matched_skills: dict) -> float:
        """
        计算置信度分数
        
        Args:
            text: 原始文本
            matched_skills: 匹配到的技能字典
            
        Returns:
            置信度分数 (0.0-1.0)
        """
        if not matched_skills:
            return 0.0
        
        total_skills = sum(len(skills) for skills in matched_skills.values())
        
        # 基础置信度：匹配到的技能数量
        base_confidence = min(total_skills / 10.0, 1.0)  # 最多 10 个技能得满分
        
        # 上下文加分：检查是否有技能指示词
        skill_indicators = [
            '精通', '熟悉', '掌握', '了解', '熟练', '擅长',
            '有...经验', '有...能力', '具备', '要求', '需要'
        ]
        
        has_context = any(indicator in text for indicator in skill_indicators)
        context_bonus = 0.2 if has_context else 0.0
        
        # 最终置信度
        confidence = min(base_confidence + context_bonus, 1.0)
        
        return confidence
    
    def get_mode_name(self) -> str:
        """返回模式名称
        
        Returns:
            str: 模式名称
        """
        return "快速模式（Jieba 分词）"
    
    def extract_batch(self, texts: list[str]) -> list[SkillResult]:
        """批量提取技能（优化版本）
        
        Args:
            texts: 文本列表
            
        Returns:
            List[SkillResult]: 每个文本对应的识别结果
        """
        # 使用 matcher 的批量统计方法进行优化
        results = []
        for text in texts:
            result = self.extract(text)
            results.append(result)
        return results
