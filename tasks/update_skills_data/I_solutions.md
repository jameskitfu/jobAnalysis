# 方案设计：技能词库 (skills.yaml) 大规模扩充

## 1. 结构化设计
目前 `skills.yaml` 采用按类别划分的列表结构。我们将复用并细化这一结构，确保扩展性和 Jieba 搜索效率。

### 设计原则：
1. **多级分类**：将前端拆分为框架、渲染、工程、样式等二级分类。
2. **同义词归并**：在 `smart_skill_matcher.py` 逻辑中，虽然 YAML 主要是词表，但我们会尽量通过硬技能列表来覆盖常见的同义词。
3. **大小写规范**：词库中主要存储规范名称，代码层转换 `lower()` 进行匹配。

## 2. YAML 数据块模板
我们将构建以下大型数据块：

```yaml
  # 前端深度扩展
  前端核心框架:
    - React
    - Vue.js
    - ...
  前端渲染技术:
    - SSR (服务端渲染)
    - SSG (静态生成)
    - ...

  # AI/大模型深度扩展
  深度学习框架:
    - PyTorch
    - TensorFlow
    - ...
  大语言模型:
    - GPT-4
    - Claude
    - Llama
    - ...
```

## 3. 自动化处理逻辑（验证）
扩充后，需要确保：
1. `skills.yaml` 格式正确（无缩进错误）。
2. `smart_skill_matcher` 重载后不会因为词量激增（数千条）导致内存溢出或响应极慢（预计 Jieba 在万级词量下依然表现良好）。

## 4. 词汇生成方案
我将利用预置的、经过调研的词表进行合并，手动编写时确保覆盖：
- **前端**：Web Vitals, Micro-frontends, PWA, Shadow DOM, Hooks, Context, Redux, Zustand, Vite, Webpack, Babel, PostCSS, Less, Sass, Flexbox, Grid...
- **AI**：RAG, Embedding, Vector DB, Prompt Engineering, Fine-tuning, LoRA, RLHF, Transformer, Attention, LLMOps, ONNX, CUDA, PyTorch, LangChain, LlamaIndex...
