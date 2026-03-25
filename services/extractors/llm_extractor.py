"""
大模型技能提取器
使用 LLM 进行智能技能识别，支持新技能发现
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any

from .base_extractor import SkillExtractor, SkillResult, NewSkillCandidate

# 添加父目录到路径以便导入 llm_service
sys.path.insert(0, str(Path(__file__).parent.parent))
from llm_service import LLMService  # noqa: E402


class LLMExtractor(SkillExtractor):
    """基于大模型的技能提取器"""
    
    def __init__(self, config_path: str, llm_config: Dict[str, Any] = None):
        """
        初始化 LLM 提取器
        
        Args:
            config_path: 技能词库 YAML 配置文件路径（用于验证标准技能）
            llm_config: LLM 服务配置
        """
        self.config_path = config_path
        self.llm_config = llm_config or {}
        
        # 加载技能词库用于标准化
        self.standard_skills_set = set()
        self.skill_categories = {}
        self._load_skill_index()
        
        # 初始化 LLM 服务
        provider = self.llm_config.get("provider", "aliyun")
        api_key = self.llm_config.get("api_key")
        self.llm_service = LLMService(
            provider=provider,
            api_key=api_key,
            model=self.llm_config.get("model"),
            timeout=self.llm_config.get("timeout", 30),
            batch_size=self.llm_config.get("batch_size", 10),
        )
    
    def _load_skill_index(self):
        """加载技能词索引"""
        import yaml
        from pathlib import Path
        
        config_file = Path(self.config_path)
        if not config_file.exists():
            return
        
        with open(config_file, 'r', encoding='utf-8') as f:
            skills_config = yaml.safe_load(f)
        
        # 提取硬技能
        hard_skills = skills_config.get('hard_skills', {})
        for category, skills in hard_skills.items():
            if isinstance(skills, list):
                for skill in skills:
                    skill = str(skill).strip()
                    self.standard_skills_set.add(skill.lower())
                    if category not in self.skill_categories:
                        self.skill_categories[category] = []
                    self.skill_categories[category].append(skill)
        
        # 提取软技能
        soft_skills = skills_config.get('soft_skills', [])
        if isinstance(soft_skills, list):
            for skill in soft_skills:
                skill = str(skill).strip()
                self.standard_skills_set.add(skill.lower())
            if 'soft_skills' not in self.skill_categories:
                self.skill_categories['soft_skills'] = []
            self.skill_categories['soft_skills'].extend([str(s).strip() for s in soft_skills])
    
    def extract(self, text: str) -> SkillResult:
        """从文本中提取技能（使用 LLM）
        
        Args:
            text: 输入的职位描述文本
            
        Returns:
            SkillResult: 包含标准技能和新发现技能的结果
        """
        try:
            # 调用 LLM 识别
            llm_result = self.llm_service.recognize(text, use_cache=True)
            
            # 解析结果
            standard_skills = self._process_standard_skills(
                llm_result.get("standard_skills", {})
            )
            new_skills = self._process_new_skills(
                llm_result.get("new_skills", []),
                text
            )
            
            # 计算置信度
            confidence = self._calculate_confidence(llm_result)
            
            return SkillResult(
                standard_skills=standard_skills,
                new_skills=new_skills,
                confidence=confidence,
                metadata={
                    'mode': 'llm',
                    'provider': self.llm_service.provider,
                    'model': self.llm_service.model,
                    'total_skills': sum(len(skills) for skills in standard_skills.values()),
                    'new_skills_count': len(new_skills),
                }
            )
        
        except Exception as e:
            # LLM 调用失败，记录错误并返回空结果
            print(f"[LLM] 提取失败：{e}")
            return SkillResult(
                standard_skills={},
                new_skills=[],
                confidence=0.0,
                metadata={
                    'mode': 'llm',
                    'error': str(e),
                }
            )
    
    def extract_batch(self, texts: List[str], progress_callback=None) -> List['SkillResult']:
        """批量提取技能，使用多线程并发，收集错误信息"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = [None] * len(texts)
        errors = []
        
        def process_text(index_and_text):
            idx, text = index_and_text
            try:
                # 随机微小休眠以避免请求瞬间过猛触发流控
                import time, random
                time.sleep(random.uniform(0.1, 0.5))
                res = self.extract(text)
                return idx, res
            except Exception as e:
                return idx, Exception(str(e))
                
        # 并发度设为 10，保证不会卡住
        completed_count = 0
        total_count = len(texts)
        with ThreadPoolExecutor(max_workers=10) as executor:
            # 提交所有任务
            future_to_idx = {executor.submit(process_text, (i, t)): i for i, t in enumerate(texts)}
            
            for future in as_completed(future_to_idx):
                idx, res = future.result()
                completed_count += 1
                
                # 回调进度
                if progress_callback:
                    try:
                        progress_callback(completed_count, total_count)
                    except Exception as e:
                        pass
                
                if isinstance(res, Exception):
                    errors.append(str(res))
                    # 本次调用失败，存个空的新结果或带着错误的
                    results[idx] = SkillResult({}, [], 0.0, {'mode': 'llm', 'error': str(res)})
                else:
                    results[idx] = res
                    err = res.metadata.get('error')
                    if err and err not in errors:
                        errors.append(err)
        
        # 如果全部都包含了 error，抛出一个供上层捕捉
        if len(errors) == total_count and total_count > 0:
            raise RuntimeError(f"{errors[0]}")
            
        return results
    
    def _process_standard_skills(self, raw_skills: dict) -> Dict[str, List[str]]:
        """
        处理标准技能
        
        Args:
            raw_skills: LLM 返回的原始技能字典
            
        Returns:
            Dict[str, List[str]]: 标准化后的技能字典
        """
        standardized = {}
        
        for category, skills in raw_skills.items():
            if not isinstance(skills, list):
                continue
            
            valid_skills = []
            for skill in skills:
                skill_lower = skill.lower()
                
                # 检查是否是标准技能
                if skill_lower in self.standard_skills_set:
                    # 找到对应的标准名称
                    standard_name = self._find_standard_name(skill)
                    if standard_name:
                        valid_skills.append(standard_name)
                else:
                    # 可能是新技能，先保留
                    valid_skills.append(skill)
            
            if valid_skills:
                standardized[category] = valid_skills
        
        return standardized
    
    def _find_standard_name(self, skill: str) -> str:
        """查找技能的标准名称"""
        skill_lower = skill.lower()
        
        # 同义词映射
        synonym_map = {
            'golang': 'Go',
            'react.js': 'React',
            'vue': 'Vue.js',
            'k8s': 'Kubernetes',
            'express.js': 'Express',
            'aws': 'AWS',
            'gcp': 'Google Cloud',
            '微服务': 'Microservices',
        }
        
        if skill_lower in synonym_map:
            return synonym_map[skill_lower]
        
        # 精确匹配
        for category, skills in self.skill_categories.items():
            for s in skills:
                if s.lower() == skill_lower:
                    return s
        
        return skill  # 未找到，返回原名
    
    def _process_new_skills(self, raw_new_skills: list, context_text: str) -> List[NewSkillCandidate]:
        """
        处理新技能候选
        
        Args:
            raw_new_skills: LLM 返回的新技能列表
            context_text: 原始文本（用于提取上下文）
            
        Returns:
            List[NewSkillCandidate]: 新技能候选列表
        """
        new_skill_candidates = []
        
        for item in raw_new_skills:
            if isinstance(item, dict):
                skill = item.get('skill', '')
                category = item.get('category', '其他')
                confidence = float(item.get('confidence', 0.5))
                context = item.get('context', '')
                
                # 跳过已存在的标准技能
                if skill.lower() in self.standard_skills_set:
                    continue
                
                # 提取更准确的上下文
                if not context:
                    context = self._extract_context(context_text, skill)
                
                candidate = NewSkillCandidate(
                    skill=skill,
                    category=category,
                    confidence=confidence,
                    context=context,
                    frequency=1
                )
                new_skill_candidates.append(candidate)
        
        return new_skill_candidates
    
    def _extract_context(self, text: str, skill: str) -> str:
        """从文本中提取技能相关的上下文"""
        import re
        
        # 查找技能词前后的内容
        pattern = r'(.{0,50})' + re.escape(skill) + r'(.{0,50})'
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        if matches:
            before, after = matches[0]
            return f"...{before.strip()}【{skill}】{after.strip()}..."
        
        return ""
    
    def _calculate_confidence(self, llm_result: dict) -> float:
        """
        计算整体置信度
        
        Args:
            llm_result: LLM 返回的完整结果
            
        Returns:
            float: 置信度分数 (0.0-1.0)
        """
        standard_skills = llm_result.get("standard_skills", {})
        new_skills = llm_result.get("new_skills", [])
        
        if not standard_skills and not new_skills:
            return 0.0
        
        # 基于识别到的技能数量
        total_standard = sum(len(skills) for skills in standard_skills.values())
        total_new = len(new_skills) if isinstance(new_skills, list) else 0
        
        # 标准技能权重更高
        confidence = min((total_standard * 0.1 + total_new * 0.05), 1.0)
        
        # 如果有 skill_levels，提升置信度
        if llm_result.get("skill_levels"):
            confidence = min(confidence + 0.1, 1.0)
        
        return confidence
    
    def get_mode_name(self) -> str:
        """返回模式名称
        
        Returns:
            str: 模式名称
        """
        return f"智能模式（LLM - {self.llm_service.provider}）"
