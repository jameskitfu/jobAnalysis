# 执行计划 - 修复项目核心 Bug

## 1. 任务拆解## 📋 WBS (工作分解结构)

### 1. 核心 Bug 修复 (P0)
- [x] **任务 #1.1**: 合并 `app.py` 中的 `/upload` 路由
    - [x] 整合 `jieba` 与 `llm` 模式逻辑
    - [x] 引入 `mode` 参数控制
- [x] **任务 #2.1**: 修复 `llm_service.py` 中的 `asyncio` 语法错误
    - [x] 将 `RateLimiter.wait_for_token` 改为同步阻塞

### 2. 性能与配置优化 (P1)
- [x] **任务 #3.1**: 同义词配置外部化
    - [x] 迁移硬编码同义词至 `config/skills.yaml`
    - [x] 更新 `SkillMatcher` 加载逻辑
- [x] **任务 #3.2**: `SmartSkillMatcher` 性能优化
    - [x] 引入分词预筛选机制，减少无效正则扫描
## 2. 验收标准 (DoD)
- [x] 服务正常启动，无 SyntaxError。
- [x] `/upload` 接口可接收 `mode` 参数。
- [x] `mode="llm"` 时能正确调用 LLM 提取器。
- [x] 生成的 Excel 报告内容完整。
