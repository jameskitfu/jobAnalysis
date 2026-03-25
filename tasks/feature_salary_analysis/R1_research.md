# 调研：薪资与技能强关联分析

## 1. 现有基础
- `csv_parser.py`: 负责加载 DataFrame，并提取了 `descriptions` (文本) 和 `dates` (日期)。目前没有提取薪资 (`salary`) 的相关逻辑。
- `app.py`: 在 `/upload` 中处理匹配，并统计词频 (`total_counts` 和 `category_counts`)。
- `excel_generator.py`: 根据词频和趋势数据生成多 Sheet 的 Excel 文件。

## 2. 需要增加的能力
- **薪资列探测**: 需要在 `csv_parser.py` 或由专门的解析器，自动寻找包含 "薪酬"、"薪水"、"待遇"、"salary"、"月薪"、"年薪" 等关键字的列。
- **薪资正则解析 (Regex)**:
  招聘数据中的薪资格式通常非常乱：
  - `15-25K` -> 取平均 20K -> 20,000 * 12 = 240,000/年
  - `20-30k·14薪` -> 25K * 14 = 350,000/年
  - `300-400元/天` -> 350 * 22(天) * 12 = 92,400/年
  - `1.5万-2万` -> 1.75 * 10,000 * 12 = 210,000/年
  需要在后端增加一个专门的转换函数 `extract_normalized_annual_salary(text: str) -> Optional[float]`。
- **关联计算**: 
  在 `count_skills_from_texts` 遍历 `descriptions` 的同时，我们需要知道这行 description 对应的 `salary`。
  由于目前只传了 `List[str]`, 取不到薪水。
  **重构点**：`csv_parser.py` 需要返回对应的薪资列表，且该列表能与 `descriptions` 对应上的 `indices` 绑定，或者直接在 `app.py` 内部使用对应的并列 list。

## 3. 下一步
- 规划如何无缝且无破坏性地将 `salary_list` 传给特征统计系统。
