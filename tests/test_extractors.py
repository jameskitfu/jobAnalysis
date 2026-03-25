"""
技能提取器单元测试
"""

import unittest
from pathlib import Path

from services.extractors.base_extractor import SkillResult, NewSkillCandidate
from services.extractors.jieba_extractor import JiebaExtractor


class TestJiebaExtractor(unittest.TestCase):
    """测试 Jieba 提取器"""
    
    @classmethod
    def setUpClass(cls):
        """测试前初始化"""
        config_path = Path(__file__).parent.parent / 'config' / 'skills.yaml'
        cls.extractor = JiebaExtractor(str(config_path))
    
    def test_extract_simple(self):
        """测试简单技能识别"""
        text = "要求 3 年以上 Java 开发经验，精通 Spring Boot、MyBatis，熟悉 MySQL、Redis"
        
        result = self.extractor.extract(text)
        
        # 验证结果结构
        self.assertIsInstance(result, SkillResult)
        self.assertGreater(result.confidence, 0.0)
        
        # 验证识别到的技能（至少应该有后端框架和数据库）
        self.assertTrue(len(result.standard_skills) > 0)
        self.assertIn('backend_frameworks', result.standard_skills)
        self.assertIn('Spring Boot', result.standard_skills['backend_frameworks'])
        
        print(f"✓ 成功识别技能：{result.standard_skills}")
        print(f"✓ 置信度：{result.confidence:.2f}")
    
    def test_extract_frontend(self):
        """测试前端技能识别"""
        text = "负责前端开发，精通 React、Vue.js，熟悉 TypeScript、Webpack"
        
        result = self.extractor.extract(text)
        
        # 验证前端框架
        self.assertIn('frontend_frameworks', result.standard_skills)
        
        print(f"✓ 前端技能识别：{result.standard_skills}")
    
    def test_batch_extract(self):
        """测试批量提取"""
        texts = [
            "要求 Java 开发经验，熟悉 Spring Boot",
            "招聘 Python 工程师，有 TensorFlow 经验者优先",
            "前端开发，需要 React 和 Vue.js 经验"
        ]
        
        results = self.extractor.extract_batch(texts)
        
        self.assertEqual(len(results), 3)
        
        for i, result in enumerate(results):
            self.assertIsInstance(result, SkillResult)
            print(f"✓ 职位{i+1}识别到 {len(result.standard_skills)} 个类别的技能")
    
    def test_mode_name(self):
        """测试模式名称"""
        mode_name = self.extractor.get_mode_name()
        
        self.assertIn('Jieba', mode_name)
        print(f"✓ 模式名称：{mode_name}")


class TestSkillResult(unittest.TestCase):
    """测试 SkillResult 数据类"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        candidate = NewSkillCandidate(
            skill='LangChain',
            category='AI 框架',
            confidence=0.9,
            context='需要使用 LangChain 开发 AI 应用',
            frequency=1
        )
        
        result = SkillResult(
            standard_skills={'编程语言': ['Python', 'Java']},
            new_skills=[candidate],
            confidence=0.85,
            metadata={'mode': 'test'}
        )
        
        result_dict = result.to_dict()
        
        self.assertIsInstance(result_dict, dict)
        self.assertEqual(len(result_dict['standard_skills']['编程语言']), 2)
        self.assertEqual(len(result_dict['new_skills']), 1)
        self.assertEqual(result_dict['new_skills'][0]['skill'], 'LangChain')
        
        print(f"✓ SkillResult 序列化正常")


if __name__ == '__main__':
    print("=" * 60)
    print("技能提取器单元测试")
    print("=" * 60)
    
    # 运行测试
    unittest.main(verbosity=2)
