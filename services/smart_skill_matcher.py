"""
智能 NLP 技能匹配服务
基于中文分词和上下文语义识别的技能匹配引擎
"""

import jieba
import yaml
import re
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path
from collections import defaultdict

# 新增
from services.salary_analyzer import SalaryAnalyzer


class SmartSkillMatcher:
    """智能技能匹配器（NLP 增强版）"""
    
    def __init__(self, config_path: str):
        """
        初始化智能技能匹配器
        
        Args:
            config_path: 技能词库 YAML 配置文件路径
        """
        self.config_path = Path(config_path)
        self.skills_config: dict = {}
        self.all_skills: List[str] = []
        self.skill_categories: Dict[str, List[str]] = {}
        self.synonym_map: Dict[str, str] = {}
        
        # NLP 相关
        self.skill_keywords: Set[str] = set()  # 用于分词的关键词集合
        self.context_patterns: Dict[str, List[str]] = {}  # 上下文模式
        
        self._load_config()
        self._build_skill_index()
        self._build_synonym_map()
        self._load_jieba_dict()
        self._build_context_patterns()
        
        # 优化：构建反向查找索引
        self.skill_to_category: Dict[str, str] = {}
        self.skill_to_standard: Dict[str, str] = {}
        self._build_fast_lookup_index()
        
        # 薪水解析器
        self.salary_analyzer = SalaryAnalyzer()


    def _build_fast_lookup_index(self):
        """构建用于 O(1) 查找的快速索引"""
        for category, skills in self.skill_categories.items():
            for skill in skills:
                skill_lower = skill.lower()
                # 词库中同一技能可能被配置到多个类别（例如 React）。
                # 优先保留第一次出现的类别，避免被后续“泛 AI 分类”覆盖。
                if skill_lower not in self.skill_to_category:
                    self.skill_to_category[skill_lower] = category
                    self.skill_to_standard[skill_lower] = self._get_standard_name(skill)
        
        self.skill_lookup_set = set(self.skill_to_category.keys())
    
    def _load_config(self):
        """加载技能词库配置文件"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.skills_config = yaml.safe_load(f)
    
    def _build_skill_index(self):
        """构建技能词索引"""
        all_skills_set: Set[str] = set()
        
        # 提取硬技能
        hard_skills = self.skills_config.get('hard_skills', {})
        for category, skills in hard_skills.items():
            if isinstance(skills, list):
                for skill in skills:
                    skill = str(skill).strip()
                    all_skills_set.add(skill)
                    if category not in self.skill_categories:
                        self.skill_categories[category] = []
                    self.skill_categories[category].append(skill)
        
        # 提取软技能
        soft_skills = self.skills_config.get('soft_skills', [])
        if isinstance(soft_skills, list):
            for skill in soft_skills:
                skill = str(skill).strip()
                all_skills_set.add(skill)
            if 'soft_skills' not in self.skill_categories:
                self.skill_categories['soft_skills'] = []
            self.skill_categories['soft_skills'].extend([str(s).strip() for s in soft_skills])
        
        # 按长度降序排序
        self.all_skills = sorted(list(all_skills_set), key=lambda x: len(x), reverse=True)
    
    def _build_synonym_map(self):
        """构建同义词映射表（从配置文件加载）"""
        self.synonym_map = {}
        synonyms = self.skills_config.get('synonyms', {})
        if isinstance(synonyms, dict):
            # 统一转为小写作为键
            for key, value in synonyms.items():
                self.synonym_map[key.lower()] = value
    
    def _load_jieba_dict(self):
        """加载自定义分词词典"""
        # 将所有技能词添加到 jieba 词典
        for skill in self.all_skills:
            # 英文技能词
            if all('\u4e00' <= c <= '\u9fff' or c.isalnum() or c in '.#' for c in skill):
                jieba.add_word(skill)
            
            # 中文技能词
            if any('\u4e00' <= c <= '\u9fff' for c in skill):
                jieba.add_word(skill)
        
        # 添加常见技术术语
        tech_terms = [
            '编程语言', '框架', '数据库', '云平台', 'DevOps',
            '机器学习', '深度学习', '前端', '后端', '全栈',
            '分布式', '微服务', '容器化', '自动化'
        ]
        for term in tech_terms:
            jieba.add_word(term)
    
    def _build_context_patterns(self):
        """构建上下文识别模式"""
        # 技能相关的上下文关键词
        self.context_patterns = {
            'skill_indicator': [
                '精通', '熟悉', '掌握', '了解', '熟练', '擅长',
                '有...经验', '有...能力', '具备', '要求', '需要',
                '职责', '负责', '参与', '从事'
            ],
            'level_indicator': [
                '精通', '熟练', '熟悉', '了解', '初级', '中级', '高级',
                '专家', '资深', '5 年以上', '3 年以上', '1 年以上'
            ]
        }
    
    def _preprocess_text(self, text: str) -> str:
        """
        文本预处理
        
        Args:
            text: 原始文本
            
        Returns:
            预处理后的文本
        """
        # 统一大小写
        text = text.lower()
        
        # 去除多余空白
        text = re.sub(r'\s+', ' ', text)
        
        # 标准化常见缩写
        text = text.replace('c++', 'cpp')
        text = text.replace('c#', 'csharp')
        text = text.replace('.net', 'dotnet')
        
        return text
    
    def _extract_skill_context(self, text: str, skill: str) -> Dict[str, Optional[str]]:
        """
        提取技能出现的上下文信息
        
        Args:
            text: 文本内容
            skill: 技能词
            
        Returns:
            上下文信息字典
        """
        # 查找技能词前后的内容
        pattern = r'(.{0,30})' + re.escape(skill) + r'(.{0,30})'
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        contexts = []
        for before, after in matches:
            contexts.append({
                'before': before.strip(),
                'after': after.strip(),
                'full': (before + skill + after).strip()
            })
        
        return contexts
    
    def _is_valid_skill_match(self, text: str, skill: str) -> bool:
        """
        验证技能匹配是否有效（通过上下文判断）
        
        Args:
            text: 文本内容
            skill: 技能词
            
        Returns:
            是否是有效的技能提及
        """
        contexts = self._extract_skill_context(text, skill)

        # 超短英文技能词容易发生子串误匹配（例如 ".NET" 里的 "NE"）。
        # 对长度 <= 2 的纯字母技能，要求命中时两侧不是字母数字。
        if len(skill) <= 2 and skill.isalpha():
            boundary_pattern = rf'(?<![A-Za-z0-9]){re.escape(skill)}(?![A-Za-z0-9])'
            if not re.search(boundary_pattern, text, re.IGNORECASE):
                return False
        
        for ctx in contexts:
            full_ctx = (ctx['before'] + ' ' + ctx['after']).lower()
            
            # 检查是否有技能相关的上下文
            has_skill_context = any(
                indicator in full_ctx 
                for indicator in self.context_patterns['skill_indicator']
            )
            
            # 对于短技能词（如"Git"），需要更强的上下文证据
            if len(skill) <= 4 and not any(c.isalpha() for c in skill):
                if not has_skill_context:
                    continue
            
            # 单字符技能词特殊处理（C、R 等）
            if len(skill) == 1 and skill.isalpha():
                if not self._is_valid_single_char_skill(skill, ctx, text):
                    continue
            
            # Java 特殊处理：需要更严格的上下文验证
            if skill.lower() == 'java':
                if not self._is_valid_java_skill(ctx, text):
                    continue
            
            # 排除非技能场景
            if self._is_non_skill_context(skill, ctx):
                continue
            
            return True
        
        return False
    
    def _is_non_skill_context(self, skill: str, context: dict) -> bool:
        """
        判断是否是非技能场景（如地名、人名等）
        
        Args:
            skill: 技能词
            context: 上下文信息
            
        Returns:
            是否是非技能场景
        """
        before = context['before'].lower()
        after = context['after'].lower()
        full_ctx = (before + ' ' + after).lower()
        
        # Java 岛
        if skill.lower() == 'java' and ('岛' in before or '岛' in after):
            return True
        
        # Java 咖啡（Java 本意是咖啡）
        if skill.lower() == 'java' and any(word in full_ctx for word in ['咖啡', 'coffee', '饮品']):
            return True
        
        # Python 蛇
        if skill.lower() == 'python' and ('蛇' in before or '蟒蛇' in before):
            return True
        
        # Redis 作为人名
        if skill.lower() == 'redis' and any(name in before for name in ['叫', '名为']):
            return True
        
        return False
    
    def _is_valid_java_skill(self, context: dict, full_text: str) -> bool:
        """
        验证 Java 是否是真正的编程语言提及（而非后端协作场景）
        
        Args:
            context: 上下文信息
            full_text: 完整文本
            
        Returns:
            是否是有效的编程语言提及
        """
        before = context['before'].lower()
        after = context['after'].lower()
        full_ctx = (before + ' ' + after).lower()
        
        # 排除非编程场景
        non_programming_patterns = [
            '咖啡', 'coffee', '饮品', '岛', '印尼', '爪哇',  # Java 本意
        ]
        
        for pattern in non_programming_patterns:
            if pattern in full_ctx:
                return False
        
        # 要求有编程语言相关的上下文
        programming_context_indicators = [
            # 通用编程关键词
            '语言', '开发', '编程', '工程师', '技术', '代码', '软件', '程序员',
            # Java 特定
            'java 语言', 'java 开发', 'java 工程师', 'java 程序员', 'java 技术',
            # Java 生态
            'jvm', 'jdk', 'jre', 'javase', 'javaee', 'spring', 'hibernate', 'mybatis',
            # 前端职位中 Java 通常是协作场景，需要更严格验证
            '后端', '接口', 'api', '服务器', '微服务',
        ]
        
        has_programming_context = any(
            indicator in full_ctx 
            for indicator in programming_context_indicators
        )
        
        if not has_programming_context:
            return False
        
        # 额外检查：如果前后有字母相连，可能是缩写的一部分
        if len(before) > 0 and before[-1].isalpha():
            return False
        if len(after) > 0 and after[0].isalpha():
            return False
        
        return True
    
    def _is_valid_single_char_skill(self, skill: str, context: dict, full_text: str) -> bool:
        """
        验证单字符技能词（C、R 等）是否是真正的编程语言提及
        
        Args:
            skill: 单字符技能词（如 "C", "R"）
            context: 上下文信息
            full_text: 完整文本
            
        Returns:
            是否是有效的编程语言提及
        """
        skill_lower = skill.lower()
        before = context['before'].lower()
        after = context['after'].lower()
        full_ctx = (before + ' ' + after).lower()
        
        # 常见非编程场景模式（需要排除的）
        non_programming_patterns = [
            # C 相关误识别
            ('c', ['pc 端', 'pc ', ' pc', 'c 端', 'c 轮', 'c 端用户', 'c 轮融资']),
            # R 相关误识别
            ('r', ['hr', 'pr', 'ar', 'vr', 'cr', 'br', 'gr', 'sr', 'tr', 'or', 'mr', 'dr']),
            # 融资轮次（A/B/C/D 轮）
            (skill_lower, ['a 轮', 'b 轮', 'c 轮', 'd 轮', 'e 轮', '天使轮', 'pre-a']),
        ]
        
        # 检查是否在非编程上下文中
        for pattern_skill, patterns in non_programming_patterns:
            if pattern_skill == skill_lower:
                for pattern in patterns:
                    if pattern in full_ctx:
                        return False
        
        # 特殊检查：PC/ABC 测试等
        if skill_lower == 'c':
            if 'pc' in full_ctx or 'abc' in full_ctx:
                return False
        
        # 要求有编程语言相关的上下文（强验证）
        programming_context_indicators = [
            # 通用编程关键词
            '语言', '开发', '编程', '工程师', '技术', '代码', '软件',
            # C 语言特定
            'c 语言', 'c 程序', 'c 代码', 'c 开发', 'c 程序员',
            # R 语言特定
            'r 语言', 'r 程序', 'r 代码', 'r 开发', 'r 统计', 'r 编程',
            # 与其他编程语言共现
            'java', 'python', 'javascript', 'html', 'css', 'sql',
            'git', 'linux', '算法', '数据结构', '面向对象',
        ]
        
        has_programming_context = any(
            indicator in full_ctx 
            for indicator in programming_context_indicators
        )
        
        if not has_programming_context:
            return False
        
        # 额外检查：如果前后有字母相连，可能是缩写的一部分
        # 例如："HR"中的 R，"PR"中的 R
        if len(before) > 0 and before[-1].isalpha():
            return False
        if len(after) > 0 and after[0].isalpha():
            return False
        
        return True
    
    def find_skills_smart(self, text: str) -> Dict[str, List[str]]:
        """
        智能识别文本中的技能 (优化版)
        使用反向查找算法，复杂度从 O(Skills) 降至 O(Tokens)
        
        Args:
            text: 职位描述文本
            
        Returns:
            匹配到的技能字典 {类别：[技能列表]}
        """
        matched_skills: Dict[str, Set[str]] = defaultdict(set)
        
        # 1. 预处理文本
        preprocessed_text = self._preprocess_text(text)
        
        # 2. 使用 jieba 分词
        # 搜索模式的分词结果更细，适合识别嵌入的词
        seg_text = jieba.lcut_for_search(text)
        tokens = set(t.strip().lower() for t in seg_text if t.strip())
        
        # 3. 反向查找 (O(Tokens))
        for token in tokens:
            if token in self.skill_lookup_set:
                # 针对识别出的词执行上下文验证
                if self._is_valid_skill_match(text, token):
                    category = self.skill_to_category[token]
                    standard_name = self.skill_to_standard[token]
                    matched_skills[category].add(standard_name)
        
        # 4. 针对极长技能词的额外扫描（由于 jieba 可能将长英文短语切散，针对长度 > 10 的核心词做兜底）
        for skill in self.all_skills:
            if len(skill) > 10:
                skill_lower = skill.lower()
                if skill_lower in preprocessed_text and self._is_valid_skill_match(text, skill):
                    category = self._get_skill_category(skill)
                    if category:
                        matched_skills[category].add(self._get_standard_name(skill))

        # 5. 单字符编程语言兜底（如“C语言”“R语言”）
        # jieba 在中文场景中可能只切出 “C语言” 而不是 “C”，导致单字符技能漏识别。
        single_char_patterns = {
            'c': r'(?i)(?<![a-z0-9])c\s*语言',
            'r': r'(?i)(?<![a-z0-9])r\s*语言',
        }
        for single_skill, pattern in single_char_patterns.items():
            if single_skill not in self.skill_lookup_set:
                continue
            if re.search(pattern, text):
                category = self.skill_to_category[single_skill]
                standard_name = self.skill_to_standard[single_skill]
                matched_skills[category].add(standard_name)
                        
        return {k: list(v) for k, v in matched_skills.items()}
    
    def _get_skill_category(self, skill: str) -> Optional[str]:
        """获取技能所属类别"""
        skill_lower = skill.lower()
        
        # 检查硬技能
        hard_skills = self.skills_config.get('hard_skills', {})
        for category, skills in hard_skills.items():
            if isinstance(skills, list):
                for s in skills:
                    if str(s).strip().lower() == skill_lower:
                        return category
        
        # 检查软技能
        soft_skills = self.skills_config.get('soft_skills', [])
        for s in soft_skills:
            if str(s).strip().lower() == skill_lower:
                return 'soft_skills'
        
        return None
    
    def _get_standard_name(self, skill: str) -> str:
        """获取技能标准名称"""
        skill_lower = skill.lower()
        if skill_lower in self.synonym_map:
            return self.synonym_map[skill_lower]
        return skill
    
    def count_skills_from_texts(
        self, 
        texts: List[str],
        use_smart: bool = True,
        progress_callback: Optional[callable] = None,
        salaries: Optional[List[Optional[str]]] = None
    ) -> Tuple[Dict[str, int], Dict[str, Dict[str, int]], Dict[str, List[float]]]:
        """
        统计技能频率并关联薪资
        
        Args:
            texts: 职位描述文本列表
            use_smart: 是否使用智能匹配
            progress_callback: 进度回调函数，接收 (current, total)
            salaries: 与 texts 一一对应的薪资文本列表
            
        Returns:
            (总统计表，分类统计表，技能薪资表) {skill: [salary1, salary2...]}
        """
        total_counts: Dict[str, int] = defaultdict(int)
        category_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        skill_salaries: Dict[str, List[float]] = defaultdict(list)
        
        matcher = self.find_skills_smart if use_smart else self.find_skills_simple
        total_texts = len(texts)
        
        for i, text in enumerate(texts):
            found_skills = matcher(text)
            
            # 解析当条薪水
            salary_val = None
            if salaries and i < len(salaries) and salaries[i]:
                salary_val = self.salary_analyzer.parse_annual_salary(salaries[i])
            
            for category, skills in found_skills.items():
                for skill in skills:
                    total_counts[skill] += 1
                    category_counts[category][skill] += 1
                    if salary_val is not None:
                        skill_salaries[skill].append(salary_val)
            
            # 执行进度回调 (每 1% 或每 10 条汇报一次)
            if progress_callback and (i % max(1, total_texts // 100) == 0 or i == total_texts - 1):
                progress_callback(i + 1, total_texts)
        
        return dict(total_counts), {k: dict(v) for k, v in category_counts.items()}, dict(skill_salaries)
    
    def find_skills_simple(self, text: str) -> Dict[str, List[str]]:
        """简单字符串匹配（向后兼容）"""
        return self.find_skills_smart(text)
    
    def get_all_categories(self) -> List[str]:
        """获取所有类别"""
        return list(self.skill_categories.keys())
    
    def get_category_display_name(self, category: str) -> str:
        """获取类别显示名称"""
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
