"""
技能匹配引擎
负责从文本中匹配和统计技能关键词
"""

import yaml
import re
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path
from collections import defaultdict


class SkillMatcher:
    """技能关键词匹配器"""
    
    def __init__(self, config_path: str):
        """
        初始化技能匹配器
        
        Args:
            config_path: 技能词库 YAML 配置文件路径
        """
        self.config_path = Path(config_path)
        self.skills_config: dict = {}
        self.all_skills: List[str] = []
        self.skill_categories: Dict[str, List[str]] = {}
        self.synonym_map: Dict[str, str] = {}  # 同义词映射
        
        self._load_config()
        self._build_skill_index()
        self._build_synonym_map()
    
    def _load_config(self):
        """加载技能词库配置文件"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.skills_config = yaml.safe_load(f)
    
    def _build_skill_index(self):
        """构建技能词索引，按长度降序排序（优先匹配长词）"""
        all_skills_set: Set[str] = set()
        
        # 提取所有硬技能
        hard_skills = self.skills_config.get('hard_skills', {})
        for category, skills in hard_skills.items():
            if isinstance(skills, list):
                for skill in skills:
                    skill = str(skill).strip()
                    all_skills_set.add(skill)
                    if category not in self.skill_categories:
                        self.skill_categories[category] = []
                    self.skill_categories[category].append(skill)
        
        # 提取所有软技能
        soft_skills = self.skills_config.get('soft_skills', [])
        if isinstance(soft_skills, list):
            for skill in soft_skills:
                skill = str(skill).strip()
                all_skills_set.add(skill)
            if 'soft_skills' not in self.skill_categories:
                self.skill_categories['soft_skills'] = []
            self.skill_categories['soft_skills'].extend([str(s).strip() for s in soft_skills])
        
        # 按长度降序排序（优先匹配长的技能词，避免部分匹配）
        self.all_skills = sorted(
            list(all_skills_set),
            key=lambda x: len(x),
            reverse=True
        )
    
    def _build_synonym_map(self):
        """构建同义词映射表（从配置文件加载）"""
        self.synonym_map = {}
        synonyms = self.skills_config.get('synonyms', {})
        if isinstance(synonyms, dict):
            # 统一转为小写作为键，方便后续匹配
            for key, value in synonyms.items():
                self.synonym_map[key.lower()] = value
    
    def _normalize_text(self, text: str) -> str:
        """
        文本标准化处理
        """
        if not text:
            return ""
        # 统一转为小写
        return text.lower()
    
    def _find_skill_in_text(self, text: str, skill: str) -> bool:
        """
        在文本中查找技能词（不区分大小写）
        
        Args:
            text: 文本内容
            skill: 技能词
            
        Returns:
            是否找到
        """
        # 使用正则表达式进行单词边界匹配
        # 对于中英文混合的技能词，使用简单的包含匹配
        if any('\u4e00' <= c <= '\u9fff' for c in skill):
            # 包含中文，直接包含匹配
            return skill in text
        else:
            # 纯英文，使用单词边界匹配
            pattern = r'\b' + re.escape(skill) + r'\b'
            return bool(re.search(pattern, text, re.IGNORECASE))
    
    def find_skills(self, text: str) -> Dict[str, List[str]]:
        """
        从文本中查找所有匹配的技能
        
        Args:
            text: 职位描述文本
            
        Returns:
            匹配到的技能字典 {类别：[技能列表]}
        """
        matched_skills: Dict[str, Set[str]] = defaultdict(set)
        normalized_text = text.lower()
        
        for skill in self.all_skills:
            if self._find_skill_in_text(text, skill):
                # 查找该技能属于哪个类别
                category = self._get_skill_category(skill)
                if category:
                    # 使用标准名称（首字母大写或保持原样）
                    standard_name = self._get_standard_name(skill)
                    matched_skills[category].add(standard_name)
        
        # 转换为普通字典
        return {k: list(v) for k, v in matched_skills.items()}
    
    def _get_skill_category(self, skill: str) -> Optional[str]:
        """
        获取技能所属类别
        
        Args:
            skill: 技能词
            
        Returns:
            类别名称
        """
        skill_lower = skill.lower()
        
        # 检查硬技能类别
        hard_skills = self.skills_config.get('hard_skills', {})
        for category, skills in hard_skills.items():
            if isinstance(skills, list):
                for s in skills:
                    if str(s).strip().lower() == skill_lower:
                        return category
        
        # 检查是否是软技能
        soft_skills = self.skills_config.get('soft_skills', [])
        for s in soft_skills:
            if str(s).strip().lower() == skill_lower:
                return 'soft_skills'
        
        return None
    
    def _get_standard_name(self, skill: str) -> str:
        """
        获取技能的标准名称（用于统一展示）
        
        Args:
            skill: 技能词
            
        Returns:
            标准名称
        """
        skill_lower = skill.lower()
        
        # 检查同义词映射
        if skill_lower in self.synonym_map:
            return self.synonym_map[skill_lower]
        
        # 默认返回原词（保持原有大小写）
        return skill
    
    def count_skills_from_texts(self, texts: List[str]) -> Tuple[Dict[str, int], Dict[str, Dict[str, int]]]:
        """
        从多个文本中统计技能出现频率
        
        Args:
            texts: 职位描述文本列表
            
        Returns:
            (总统计表，分类统计表)
            - 总统计表：{技能词：出现次数}
            - 分类统计表：{类别：{技能词：出现次数}}
        """
        total_counts: Dict[str, int] = defaultdict(int)
        category_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        for text in texts:
            # 每个文本中找到的技能去重（同一职位中提到多次只计一次）
            found_skills = self.find_skills(text)
            
            for category, skills in found_skills.items():
                for skill in skills:
                    total_counts[skill] += 1
                    category_counts[category][skill] += 1
        
        return dict(total_counts), {k: dict(v) for k, v in category_counts.items()}
    
    def get_all_categories(self) -> List[str]:
        """
        获取所有技能类别
        
        Returns:
            类别列表
        """
        return list(self.skill_categories.keys())
    
    def get_category_display_name(self, category: str) -> str:
        """
        获取类别的中文显示名称
        
        Args:
            category: 类别英文名
            
        Returns:
            中文显示名称
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
        return category_names.get(category, category)
