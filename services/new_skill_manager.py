"""
新技能管理器
负责收集、审核和管理 LLM 发现的新技能候选
"""

import yaml
import json
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

from .extractors.base_extractor import NewSkillCandidate


class NewSkillManager:
    """新技能管理器"""
    
    def __init__(self, skills_yaml_path: str, pending_db_path: str = None):
        """
        初始化新技能管理器
        
        Args:
            skills_yaml_path: skills.yaml 文件路径
            pending_db_path: 待审核数据库路径（JSON 文件，可选）
        """
        self.skills_yaml_path = Path(skills_yaml_path)
        self.pending_db_path = Path(pending_db_path) if pending_db_path else None
        
        # 如果没有指定 pending_db_path，使用默认位置
        if self.pending_db_path is None:
            self.pending_db_path = self.skills_yaml_path.parent / "pending_skills.json"
        
        # 加载待审核列表
        self.pending_skills: List[Dict] = []
        self._load_pending_db()
        
        # 技能类别映射
        self.category_names = {
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
            'soft_skills': '软技能',
        }
    
    def _load_pending_db(self):
        """加载待审核数据库"""
        if self.pending_db_path.exists():
            with open(self.pending_db_path, 'r', encoding='utf-8') as f:
                try:
                    self.pending_skills = json.load(f)
                except json.JSONDecodeError:
                    self.pending_skills = []
        else:
            self.pending_skills = []
    
    def _save_pending_db(self):
        """保存待审核数据库"""
        with open(self.pending_db_path, 'w', encoding='utf-8') as f:
            json.dump(self.pending_skills, f, ensure_ascii=False, indent=2)
    
    def add_candidate(self, candidate: NewSkillCandidate) -> int:
        """
        添加新技能候选
        
        Args:
            candidate: 新技能候选对象
            
        Returns:
            int: 候选 ID
        """
        # 检查是否已存在
        for i, skill in enumerate(self.pending_skills):
            if (skill['skill'].lower() == candidate.skill.lower() and 
                skill['status'] == 'pending'):
                # 已存在，增加频次
                skill['frequency'] += 1
                skill['last_seen'] = datetime.now().isoformat()
                self._save_pending_db()
                return i
        
        # 新增候选
        new_entry = {
            'id': len(self.pending_skills),
            'skill': candidate.skill,
            'category': candidate.category,
            'confidence': candidate.confidence,
            'context': candidate.context,
            'frequency': candidate.frequency,
            'status': 'pending',  # pending / approved / rejected
            'created_at': datetime.now().isoformat(),
            'reviewed_at': None,
            'reviewer_note': '',
        }
        
        self.pending_skills.append(new_entry)
        self._save_pending_db()
        
        return new_entry['id']
    
    def add_candidates_batch(self, candidates: List[NewSkillCandidate]) -> List[int]:
        """
        批量添加新技能候选
        
        Args:
            candidates: 新技能候选列表
            
        Returns:
            List[int]: 候选 ID 列表
        """
        ids = []
        for candidate in candidates:
            skill_id = self.add_candidate(candidate)
            ids.append(skill_id)
        return ids
    
    def get_pending_list(self, status: str = 'pending') -> List[Dict]:
        """
        获取待审核列表
        
        Args:
            status: 状态过滤（pending / approved / rejected / all）
            
        Returns:
            List[Dict]: 待审核技能列表
        """
        if status == 'all':
            return self.pending_skills
        
        return [s for s in self.pending_skills if s['status'] == status]
    
    def approve_skill(self, skill_id: int, category: str, reviewer_note: str = '') -> bool:
        """
        批准新技能并写入 skills.yaml
        
        Args:
            skill_id: 候选 ID
            category: 目标类别
            reviewer_note: 审核备注
            
        Returns:
            bool: 是否成功
        """
        # 查找候选
        skill_entry = None
        for skill in self.pending_skills:
            if skill['id'] == skill_id:
                skill_entry = skill
                break
        
        if not skill_entry:
            return False
        
        # 更新状态
        skill_entry['status'] = 'approved'
        skill_entry['category'] = category
        skill_entry['reviewed_at'] = datetime.now().isoformat()
        skill_entry['reviewer_note'] = reviewer_note
        
        # 写入 skills.yaml
        success = self._add_to_skills_yaml(skill_entry['skill'], category)
        
        if success:
            self._save_pending_db()
        
        return success
    
    def reject_skill(self, skill_id: int, reason: str = '') -> bool:
        """
        拒绝新技能
        
        Args:
            skill_id: 候选 ID
            reason: 拒绝原因
            
        Returns:
            bool: 是否成功
        """
        # 查找候选
        skill_entry = None
        for skill in self.pending_skills:
            if skill['id'] == skill_id:
                skill_entry = skill
                break
        
        if not skill_entry:
            return False
        
        # 更新状态
        skill_entry['status'] = 'rejected'
        skill_entry['reviewed_at'] = datetime.now().isoformat()
        skill_entry['reviewer_note'] = reason
        
        self._save_pending_db()
        return True
    
    def _add_to_skills_yaml(self, skill: str, category: str) -> bool:
        """
        添加技能到 YAML 配置文件
        
        Args:
            skill: 技能名称
            category: 类别
        
        Returns:
            bool: 是否成功
        """
        try:
            # 读取现有配置
            with open(self.skills_yaml_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 确保硬技能部分存在
            if 'hard_skills' not in config:
                config['hard_skills'] = {}
            
            # 确保类别存在
            if category not in config['hard_skills']:
                config['hard_skills'][category] = []
            
            # 添加技能（如果不存在）
            if isinstance(config['hard_skills'][category], list):
                if skill not in config['hard_skills'][category]:
                    config['hard_skills'][category].append(skill)
            else:
                config['hard_skills'][category] = [skill]
            
            # 写回文件
            with open(self.skills_yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            
            return True
        
        except Exception as e:
            print(f"添加技能到 YAML 失败：{e}")
            return False
    
    def get_statistics(self) -> dict:
        """
        获取统计信息
        
        Returns:
            dict: 统计数据
        """
        total = len(self.pending_skills)
        pending = len([s for s in self.pending_skills if s['status'] == 'pending'])
        approved = len([s for s in self.pending_skills if s['status'] == 'approved'])
        rejected = len([s for s in self.pending_skills if s['status'] == 'rejected'])
        
        return {
            'total': total,
            'pending': pending,
            'approved': approved,
            'rejected': rejected,
            'approval_rate': approved / total if total > 0 else 0.0,
        }
    
    def clear_reviewed(self, keep_days: int = 30) -> int:
        """
        清理已审核记录
        
        Args:
            keep_days: 保留天数
            
        Returns:
            int: 清理的记录数
        """
        cutoff_date = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
        
        original_count = len(self.pending_skills)
        
        # 保留未审核和近期审核的记录
        self.pending_skills = [
            s for s in self.pending_skills
            if s['status'] == 'pending' or 
               (s['reviewed_at'] and 
                datetime.fromisoformat(s['reviewed_at']).timestamp() > cutoff_date)
        ]
        
        self._save_pending_db()
        
        return original_count - len(self.pending_skills)
    
    def export_pending(self, output_path: str) -> bool:
        """
        导出待审核列表为 JSON
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            bool: 是否成功
        """
        try:
            pending_list = self.get_pending_list('pending')
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(pending_list, f, ensure_ascii=False, indent=2)
            
            return True
        
        except Exception as e:
            print(f"导出失败：{e}")
            return False
