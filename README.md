# 技能词频统计工具 v1.2.0

📊 一个基于 Web 的职位 CSV 文件技能分析工具，支持智能 NLP 匹配、薪资关联分析和大模型混合动力引擎。

## v1.2.0 重大更新 🚀

- ✨ **薪资关联分析**：自动从 CSV 列（或职位描述）中提取薪资信息，计算各技能的**平均年薪**。
- ✨ **LLM 混合动力引擎**：除了传统的 Jieba 分词，新增 **大模型 (LLM) 模式**，可发现词库外的新兴技术词汇。
- ✨ **核心性能优化**：修复了在大批量数据下 Excel 生成卡死的问题；合并了 1000+ 碎片化分类，报表更清晰。
- ✨ **智能薪资兜底**：若 CSV 无独立薪资列，系统会自动从职位标题或描述中正则提取薪资。

## 功能特性

- ✅ **CSV 文件上传**：支持拖拽或点击上传，自动检测编码。
- ✅ **智能 NLP 匹配**：基于 Jieba 分词 + 上下文语义识别，准确区分技能词。
- ✅ **大模型 (LLM) 发现**：支持通义千问、DeepSeek、小米 Mimo 等多种模型，发现新兴 AI 技能。
- ✅ **薪资关联挖掘**：🔥 新增功能：统计技能与薪资的强关联，生成「高薪技能排行榜」。
- ✅ **趋势分析**：按时间段（月/季/年）统计技能需求变化，生成增长率排名。
- ✅ **Excel 报表**：多 Sheet 格式，包含：
  - 🔥 **高薪技能分析** (New)
  - 总统计表 (含平均年薪)
  - 分类统计表 (30+ 核心大类)
  - Top50 排行 (含平均年薪)
  - 趋势汇总/增长率排名 (需日期列)

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | Flask 3.0 |
| 数据处理 | pandas 2.1 |
| Excel 生成 | openpyxl 3.1 + XlsxWriter |
| NLP 分词 | jieba + LLM (Dashscope/DeepSeek/OpenAI API) |
| 词库管理 | PyYAML + 自研分类合并算法 |
| 前端 | Vue.js 3 + 现代化玻璃钢化 UI |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python app.py
```

### 3. 使用流程

1. 准备 CSV 文件（包含职位描述列，可选包含薪资列）。
2. 打开：http://localhost:5001。
3. 如果使用 **智能模式**，请填入大模型 API Key。
4. 分析完成后查看 Web 预览，并点击 **「下载完整 Excel 报表」**。

## 项目结构

```
jobAnalysis/
├── app.py                      # Flask 主应用
├── requirements.txt            # Python 依赖
├── config/
│   └── skills.yaml             # 技能词库（已合并优化）
├── services/
│   ├── csv_parser.py           # CSV 解析与薪资提取 (v1.2.0 增强)
│   ├── salary_analyzer.py      # 🔥 薪资标准化折算服务 (New)
│   ├── extractors.py           # LLM/Jieba 混合提取策略 (New)
│   ├── smart_skill_matcher.py  # 智能匹配引擎 (v1.2.0 增强)
│   └── excel_generator.py      # Excel 报表生成 (性能优化版)
├── templates/
│   └── index.html              # 前端界面 (UI 升级)
└── tasks/                      # 任务研发记录 (SSOT 规范)
```

## 技能词库

词库位于 `config/skills.yaml`，v1.2.0 已将 1000+ 碎片分类合并为 **31 个核心大类**：
- **AI 领域**：AI Agent、大语言模型、RAG与知识工程、Prompt工程等。
- **计算机视觉**：CV、多模态、生成式模型。
- **硬技能**：编程语言、后端框架、前端框架、数据库等。
- **AI 硬件**：AI芯片、高性能计算、编译器技术。

## 路线图 (Roadmap)

- [x] v1.1.0: 增加趋势分析与 Excel 导出
- [x] v1.2.0: 薪资关联分析与 LLM 混合引擎
- [x] v1.2.0: 修复 Excel 生成卡死及词库分类膨胀问题
- [ ] v2.0.0: 增加 Web 实时可视化图表 (ECharts)
- [ ] v2.0.0: 支持多个文件批量对比分析

## License

MIT
