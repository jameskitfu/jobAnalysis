# 执行计划：薪资与技能强关联分析

## 第一阶段：数据底座
- [x] 在 `csv_parser.py` 中新增 `get_salary_column` 和 `get_salaries`。
- [x] 创建 `services/salary_analyzer.py`，实现正则提取逻辑 `parse_annual_salary`，并编写简单的边界测试用例。

## 第二阶段：引擎与聚合
- [x] 修改 `app.py` 的 `/upload` 路由，获取 salaries 并提取为数值。
- [x] 在统计词频的同时，将有效薪水记录进 `skill_salaries` 字典。
- [x] 计算出各个技能的 `平均年薪`。

## 第三阶段：报表与呈现
- [x] 改造 `excel_generator.py`，在总表中加入【平均年薪】列。
- [x] 在 Excel 中新增【🔥高薪技能挖掘】Sheet。
- [x] 改造 `app.py` `/upload` 返回值，以及 `index.html` 中的 Top 技能展示（展示薪酬）。

## 第四阶段：验证测试
- [x] 使用一份含有各种乱七八糟薪资格式的测试数据运行分析，验证准确度。
