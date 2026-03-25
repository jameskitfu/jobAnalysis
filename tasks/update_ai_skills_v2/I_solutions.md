# 方案设计：AI 词库 (V2) 深度扩充

## 1. 技术路线
我们将采用“垂直切片”的方式，针对 AI 的子领域进行地毯式扫描和注入。

### 新增子分类设计：
- `AI 智能体与工作流 (Agents)`
- `AI 推理加速与优化 (Optimization)`
- `AI 安全与伦理 (Security & Ethics)`
- `AI 基础设施与运维 (LLM Ops)`
- `具身智能与机器人 (Embodied AI)`

## 2. YAML 数据块模板 (部分)

```yaml
  AI 智能体架构:
    - LangGraph
    - CrewAI
    - Agentic Workflow
    - 智能体工作流
    - 多智能体系统
    - Multi-Agent System (MAS)
    - 思维链 (CoT)
    - 反思 (Reflection)
```

## 3. 自动化与校验
- 继续使用 `gen_skills.py` 进行逻辑生成。
- 增加对“模型名称+版本号”的多重覆盖。
