# 技能词频统计工具

📊 一个基于 Web 的职位 CSV 文件技能分析工具，支持智能 NLP 匹配和趋势分析。

## 功能特性

- ✅ **CSV 文件上传**：支持拖拽或点击上传，自动检测编码
- ✅ **智能 NLP 匹配**：基于 jieba 分词 + 上下文语义识别，准确区分技能词和普通词汇
- ✅ **趋势分析**：按时间段（月/季/年）统计技能需求变化，生成增长率排名
- ✅ **双维度统计**：硬技能（编程语言、框架、数据库等）+ 软技能（沟通能力、团队协作等）
- ✅ **Excel 报表**：多 Sheet 格式，包含总统计表、分类统计表、Top50 排行、趋势汇总、增长率排名
- ✅ **美观界面**：现代化 Web UI，支持实时进度显示、结果预览和趋势摘要

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | Flask 3.0 |
| 数据处理 | pandas 2.1 |
| Excel 生成 | openpyxl 3.1 + XlsxWriter |
| NLP 分词 | jieba |
| 配置文件 | PyYAML |
| 编码检测 | chardet |
| 前端 | Vue.js 3 + 自定义 CSS |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python app.py
```

### 3. 访问应用

打开浏览器访问：http://localhost:5001

### 4. 使用流程

1. 准备 CSV 文件（包含职位描述列）
2. 拖拽或点击上传 CSV
3. 等待分析完成
4. 查看 Top 技能预览
5. 下载完整 Excel 报表

## CSV 格式要求

CSV 文件应包含职位描述列，支持的列名：
- `description`（推荐）
- `job_description`
- `职位描述`
- `岗位描述`
- `requirements`
- `要求`
- 等其他常见变体

**示例 CSV 结构：**

```csv
job_id,title,description,company
1,Java 开发工程师，"职位要求：精通 Java、Spring Boot，熟悉 MySQL、Docker..."，公司 A
2,Python 工程师，"任职要求：熟练掌握 Python、Django，了解 Redis、Kubernetes..."，公司 B
```

## 项目结构

```
jobAnalysis/
├── app.py                      # Flask 主应用
├── requirements.txt            # Python 依赖
├── config/
│   └── skills.yaml             # 技能词库配置
├── services/
│   ├── csv_parser.py           # CSV 解析服务
│   ├── skill_matcher.py        # 技能匹配引擎
│   └── excel_generator.py      # Excel 生成服务
├── templates/
│   └── index.html              # 前端页面
├── uploads/                    # 临时上传目录
├── outputs/                    # 输出文件目录
├── test_with_date.csv          # 测试数据（带日期）
└── test_data_fixed.csv         # 测试数据
```

## 技能词库

词库位于 `config/skills.yaml`，包含：

### 硬技能（13 个类别）
- 编程语言（Java、Python、JavaScript 等）
- 后端框架（Spring Boot、Django、Flask 等）
- 前端框架（React、Vue.js、Angular 等）
- 数据库（MySQL、PostgreSQL、MongoDB 等）
- DevOps 工具（Docker、Kubernetes、Jenkins 等）
- 云平台（AWS、Azure、阿里云等）
- 操作系统（Linux、Windows、macOS 等）
- 消息队列（Kafka、RabbitMQ 等）
- 架构技术（微服务、RESTful、GraphQL 等）
- 版本控制（Git、SVN 等）
- 机器学习（TensorFlow、PyTorch 等）

### 软技能（20+ 项）
- 沟通能力、团队协作、领导力
- 项目管理、时间管理、问题解决能力
- 学习能力、逻辑思维、抗压能力等

## Excel 报表说明

生成的 Excel 文件包含多个 Sheet：

| Sheet 名称 | 内容 |
|-----------|------|
| 总统计 | 所有技能按频次排序，包含占比和累计占比 |
| 编程语言/后端框架/... | 按类别分类统计 |
| 软技能 | 软技能专项统计 |
| Top50 排行 | 前 50 热门技能排行 |
| **技能趋势汇总** | ✨ 新增：按时间段统计技能频次变化 |
| **趋势详情** | ✨ 新增：每个时间段的详细技能分布 |
| **增长率排名** | ✨ 新增：技能需求增长率 Top20 |

## API 接口

### POST /upload
上传 CSV 文件并分析

**请求：**
```
Content-Type: multipart/form-data
file: <CSV 文件>
```

**响应：**
```json
{
  "success": true,
  "message": "分析完成！共分析 10 个职位，匹配到 45 种技能",
  "data": {
    "total_positions": 10,
    "total_skills": 45,
    "top_skills": [{"skill": "Java", "count": 8}, ...],
    "download_url": "/download/skill_stats_20260320_153804.xlsx"
  }
}
```

### GET /download/<filename>
下载生成的 Excel 文件

## 配置说明

### 修改端口
编辑 `app.py` 第 229 行：
```python
app.run(debug=False, host='0.0.0.0', port=5001)
```

### 自定义词库
编辑 `config/skills.yaml`，添加或修改技能词。

### 文件限制
- 最大文件大小：50MB
- 支持格式：CSV
- 临时文件保留时间：1 小时

## 测试

使用提供的测试数据：
```bash
curl -X POST http://localhost:5001/upload \
  -F "file=@test_data_fixed.csv"
```

## 常见问题

### Q: CSV 解析失败？
A: 确保 CSV 格式正确，使用英文逗号分隔，多行文本用双引号包裹。

### Q: 未匹配到技能？
A: 检查 CSV 是否包含职位描述列，或尝试修改列名为 `description`。

### Q: 端口被占用？
A: 修改 `app.py` 中的端口号，或关闭占用 5001 端口的进程。

## 后续优化方向

- [ ] 支持更多文件格式（Excel、JSON）
- [ ] 添加技能同义词映射
- [ ] 支持自定义词库上传
- [ ] 增加词云可视化
- [ ] 支持批量文件处理
- [ ] 添加趋势分析功能

## License

MIT
