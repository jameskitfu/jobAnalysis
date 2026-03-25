"""
混合技能提取器
结合 Jieba 分词和 LLM 两种模式，提供对比结果
"""

from typing import Dict, List
from collections import defaultdict

from .base_extractor import SkillExtractor, SkillResult, NewSkillCandidate
from .jieba_extractor import JiebaExtractor
from .llm_extractor import LLMExtractor


class HybridExtractor(SkillExtractor):
    """混合技能提取器（Jieba + LLM 对比）"""
    
    def __init__(self, config_path: str, llm_config: dict = None):
        """
        初始化混合提取器
        
        Args:
            config_path: 技能词库 YAML 配置文件路径
            llm_config: LLM 服务配置
        """
        self.config_path = config_path
        self.llm_config = llm_config or {}
        
        # 初始化两个提取器
        self.jieba_extractor = JiebaExtractor(config_path)
        self.llm_extractor = LLMExtractor(config_path, llm_config)
    
    def extract(self, text: str) -> SkillResult:
        """从文本中提取技能（双模式对比）
        
        Args:
            text: 输入的职位描述文本
            
        Returns:
            SkillResult: 合并两种模式的结果
        """
        # 同时使用两种模式
        jieba_result = self.jieba_extractor.extract(text)
        llm_result = self.llm_extractor.extract(text)
        
        # 合并标准技能
        merged_skills = self._merge_standard_skills(
            jieba_result.standard_skills,
            llm_result.standard_skills
        )
        
        # 合并新技能（去重）
        merged_new_skills = self._merge_new_skills(
            jieba_result.new_skills,
            llm_result.new_skills
        )
        
        # 计算综合置信度
        confidence = self._calculate_combined_confidence(
            jieba_result.confidence,
            llm_result.confidence
        )
        
        return SkillResult(
            standard_skills=merged_skills,
            new_skills=merged_new_skills,
            confidence=confidence,
            metadata={
                'mode': 'both',
                'jieba_result': {
                    'total_skills': sum(len(skills) for skills in jieba_result.standard_skills.values()),
                    'confidence': jieba_result.confidence,
                },
                'llm_result': {
                    'total_skills': sum(len(skills) for skills in llm_result.standard_skills.values()),
                    'new_skills_count': len(llm_result.new_skills),
                    'confidence': llm_result.confidence,
                    'provider': llm_result.metadata.get('provider', 'unknown'),
                },
                'agreement_rate': self._calculate_agreement_rate(
                    jieba_result.standard_skills,
                    llm_result.standard_skills
                ),
            }
        )
    
    def _merge_standard_skills(
        self, 
        jieba_skills: Dict[str, List[str]], 
        llm_skills: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """
        合并两种模式的標準技能
        
        Args:
            jieba_skills: Jieba 模式识别的技能
            llm_skills: LLM 模式识别的技能
            
        Returns:
            Dict[str, List[str]]: 合并后的技能字典
        """
        merged = defaultdict(set)
        
        # 添加 Jieba 的结果
        for category, skills in jieba_skills.items():
            for skill in skills:
                merged[category].add(skill)
        
        # 添加 LLM 的结果（去重）
        for category, skills in llm_skills.items():
            for skill in skills:
                # 如果该类别已存在，合并；否则新建
                merged[category].add(skill)
        
        # 转换为列表
        return {k: list(v) for k, v in merged.items()}
    
    def _merge_new_skills(
        self,
        jieba_new_skills: List[NewSkillCandidate],
        llm_new_skills: List[NewSkillCandidate]
    ) -> List[NewSkillCandidate]:
        """
        合并新技能候选
        
        Args:
            jieba_new_skills: Jieba 模式的新技能（通常为空）
            llm_new_skills: LLM 模式的新技能
            
        Returns:
            List[NewSkillCandidate]: 合并后的新技能列表
        """
        # Jieba 模式通常不支持新技能发现
        if not jieba_new_skills:
            return llm_new_skills
        
        # 合并并去重
        skill_set = set()
        merged = []
        
        for candidate in jieba_new_skills + llm_new_skills:
            key = (candidate.skill.lower(), candidate.category.lower())
            if key not in skill_set:
                skill_set.add(key)
                merged.append(candidate)
        
        return merged
    
    def _calculate_combined_confidence(
        self,
        jieba_confidence: float,
        llm_confidence: float
    ) -> float:
        """
        计算综合置信度
        
        Args:
            jieba_confidence: Jieba 模式的置信度
            llm_confidence: LLM 模式的置信度
            
        Returns:
            float: 综合置信度
        """
        # 加权平均（LLM 权重更高）
        return 0.4 * jieba_confidence + 0.6 * llm_confidence
    
    def _calculate_agreement_rate(
        self,
        jieba_skills: Dict[str, List[str]],
        llm_skills: Dict[str, List[str]]
    ) -> float:
        """
        计算两种模式的一致性比率
        
        Args:
            jieba_skills: Jieba 模式识别的技能
            llm_skills: LLM 模式识别的技能
            
        Returns:
            float: 一致性比率 (0.0-1.0)
        """
        jieba_set = set()
        for skills in jieba_skills.values():
            for skill in skills:
                jieba_set.add(skill.lower())
        
        llm_set = set()
        for skills in llm_skills.values():
            for skill in skills:
                llm_set.add(skill.lower())
        
        if not jieba_set and not llm_set:
            return 0.0
        
        intersection = jieba_set & llm_set
        union = jieba_set | llm_set
        
        if not union:
            return 0.0
        
        # Jaccard 相似系数
        return len(intersection) / len(union)
    
    def get_mode_name(self) -> str:
        """返回模式名称
        
        Returns:
            str: 模式名称
        """
        return "对比模式（Jieba + LLM）"
    
    def extract_with_comparison(self, text: str) -> dict:
        """
        提取技能并返回详细对比报告
        
        Args:
            text: 输入的职位描述文本
            
        Returns:
            dict: 包含详细对比的报告
        """
        result = self.extract(text)
        
        # 构建对比报告
        report = {
            'merged_result': result.to_dict(),
            'comparison': {
                'jieba_only': [],
                'llm_only': [],
                'both_detected': [],
            }
        }
        
        # 这里可以进一步分析差异
        # 简化版本，实际使用时可扩展
        
        return report
