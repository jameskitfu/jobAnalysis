"""
技能提取器基类
定义统一的技能提取接口（策略模式）
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class NewSkillCandidate:
    """新技能候选"""
    skill: str
    category: str
    confidence: float
    context: str
    frequency: int = 1
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'skill': self.skill,
            'category': self.category,
            'confidence': self.confidence,
            'context': self.context,
            'frequency': self.frequency,
        }


@dataclass
class SkillResult:
    """技能识别结果"""
    standard_skills: Dict[str, List[str]] = field(default_factory=dict)
    new_skills: List[NewSkillCandidate] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'standard_skills': self.standard_skills,
            'new_skills': [skill.to_dict() for skill in self.new_skills],
            'confidence': self.confidence,
            'metadata': self.metadata,
        }


class SkillExtractor(ABC):
    """技能提取器基类（策略模式）"""
    
    @abstractmethod
    def extract(self, text: str) -> SkillResult:
        """从文本中提取技能
        
        Args:
            text: 输入的职位描述文本
            
        Returns:
            SkillResult: 包含标准技能和新发现技能的结果
        """
        pass
    
    @abstractmethod
    def get_mode_name(self) -> str:
        """返回模式名称（用于前端展示）
        
        Returns:
            str: 模式名称
        """
        pass
    
    def extract_batch(self, texts: List[str]) -> List[SkillResult]:
        """批量提取技能
        
        Args:
            texts: 文本列表
            
        Returns:
            List[SkillResult]: 每个文本对应的识别结果
        """
        return [self.extract(text) for text in texts]
