"""
大模型 API 统一服务层
支持通义千问、文心一言、小米 Mimo、DeepSeek 等国内大模型 Provider
"""

import json
import time
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path
import yaml


class RateLimiter:
    """API 限流器"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """
        初始化限流器
        
        Args:
            max_requests: 时间窗口内最大请求数
            time_window: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: List[float] = []
    
    def acquire(self) -> bool:
        """获取请求许可
        
        Returns:
            bool: 是否成功获取许可
        """
        now = time.time()
        
        # 移除超过时间窗口的请求记录
        self.requests = [t for t in self.requests if now - t < self.time_window]
        
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        
        return False
    
    def wait_for_token(self) -> None:
        """等待直到获取请求许可（同步阻塞版）"""
        import time
        while not self.acquire():
            time.sleep(1)


class SkillCache:
    """技能识别结果缓存"""
    
    def __init__(self, ttl: int = 3600):
        """
        初始化缓存
        
        Args:
            ttl: 缓存过期时间（秒），默认 1 小时
        """
        self.cache: Dict[str, tuple] = {}  # {hash: (result, timestamp)}
        self.ttl = ttl
    
    def _get_key(self, text: str) -> str:
        """生成缓存键"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def get(self, text: str) -> Optional[dict]:
        """从缓存中获取结果"""
        key = self._get_key(text)
        if key in self.cache:
            result, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return result
            else:
                del self.cache[key]
        return None
    
    def set(self, text: str, result: dict) -> None:
        """设置缓存"""
        key = self._get_key(text)
        self.cache[key] = (result, time.time())
    
    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()


class RetryPolicy:
    """重试策略"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 8.0):
        """
        初始化重试策略
        
        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟时间（秒）
            max_delay: 最大延迟时间（秒）
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def get_delay(self, attempt: int) -> float:
        """计算重试延迟（指数退避）"""
        delay = self.base_delay * (2 ** attempt)
        return min(delay, self.max_delay)


class LLMService:
    """大模型 API 统一服务"""
    
    def __init__(self, provider: str = "aliyun", api_key: Optional[str] = None, **config):
        """
        初始化 LLM 服务
        
        Args:
            provider: Provider 名称（"aliyun" / "baidu" / "iflytek" / "xiaomi" / "deepseek"）
            api_key: API Key（前端传入，优先使用此参数）
            **config: 其他配置参数
        """
        self.provider = provider
        # API Key 必须从前端传入，不再从环境变量读取
        if not api_key:
            raise ValueError(f"API Key 不能为空，请在前端配置 {provider} 的 API Key")
        self.api_key = api_key
        self.model = config.get("model", self._get_default_model(provider))
        self.timeout = config.get("timeout", 30)
        self.batch_size = config.get("batch_size", 10)
        
        # 初始化组件
        self.rate_limiter = RateLimiter(
            max_requests=config.get("max_requests", 10),
            time_window=config.get("time_window", 60)
        )
        self.cache = SkillCache(ttl=config.get("cache_ttl", 3600))
        self.retry_policy = RetryPolicy(
            max_retries=config.get("max_retries", 3)
        )
        
        # 加载 Prompt 模板
        self.prompt_template = self._load_prompt_template()
        
        # Provider 客户端（延迟初始化）
        self._client = None
    
    def _get_default_model(self, provider: str) -> str:
        """获取 Provider 默认模型"""
        models = {
            "aliyun": "qwen-max",
            "baidu": "ernie-bot-4",
            "iflytek": "spark-v3.5",
            "xiaomi": "mimo-lite",  # 小米 Mimo
            "deepseek": "deepseek-chat",  # 深度求索
        }
        return models.get(provider, "qwen-max")
    
    def _load_prompt_template(self) -> dict:
        """加载 Prompt 模板"""
        prompt_path = Path(__file__).parent.parent / "config" / "prompt_templates.yaml"
        
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        
        # 返回默认模板
        return {
            "system_prompt": """你是一位专业的招聘职位技能分析专家...""",
            "few_shot_examples": []
        }
    
    def _get_client(self):
        """获取 Provider 客户端（延迟初始化）"""
        if self._client is None:
            if self.provider == "aliyun":
                try:
                    import dashscope
                    dashscope.api_key = self.api_key
                    self._client = dashscope.Generation
                except ImportError:
                    raise ImportError("请安装 dashscope: pip install dashscope")
            elif self.provider == "baidu":
                try:
                    from qianfan import ChatCompletion
                    self._client = ChatCompletion(
                        ak=self.api_key.split(":")[0] if ":" in self.api_key else self.api_key,
                        sk=self.api_key.split(":")[1] if ":" in self.api_key else ""
                    )
                except ImportError:
                    raise ImportError("请安装 qianfan: pip install qianfan")
            elif self.provider == "iflytek":
                try:
                    import sparkai
                    from sparkai.core.messages import ChatMessage
                    self._client = sparkai
                    self._message_class = ChatMessage
                except ImportError:
                    raise ImportError("请安装 spark-ai-python: pip install spark-ai-python")
            elif self.provider == "xiaomi":
                try:
                    import requests
                    self._client = requests
                    self.api_url = "https://api.mimo.xiaomi.com/v1/chat/completions"
                except ImportError:
                    raise ImportError("请安装 requests: pip install requests")
            elif self.provider == "deepseek":
                try:
                    import requests
                    self._client = requests
                    self.api_url = "https://api.deepseek.com/v1/chat/completions"
                except ImportError:
                    raise ImportError("请安装 requests: pip install requests")
            else:
                raise ValueError(f"不支持的 Provider: {self.provider}")
        
        return self._client
    
    def _build_prompt(self, job_description: str) -> str:
        """构建提示词"""
        system_prompt = self.prompt_template.get("system_prompt", "")
        
        # 添加 Few-Shot 示例
        examples = self.prompt_template.get("few_shot_examples", [])
        example_text = ""
        for i, ex in enumerate(examples[:2], 1):  # 最多 2 个示例
            if isinstance(ex, dict) and 'input' in ex and 'output' in ex:
                example_text += f"\n\n## 示例 {i}:\n输入：\"{ex['input']}\"\n\n输出：\n{json.dumps(ex['output'], ensure_ascii=False, indent=2)}"
        
        prompt = f"{system_prompt}\n\n{example_text}\n\n## 待分析文本:\n\"{job_description}\"\n\n请输出 JSON："
        
        return prompt
    
    def _parse_response(self, response: Any) -> dict:
        """解析 Provider 响应"""
        if self.provider == "aliyun":
            # 通义千问响应格式
            output = response.get('output', {})
            text = output.get('text', '')
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                # 尝试提取 JSON 部分
                import re
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    return json.loads(match.group())
                raise ValueError(f"无法解析响应：{text}")
        
        elif self.provider == "baidu":
            # 文心一言响应格式
            result = response.get('body', {})
            text = result.get('result', '')
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                import re
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    return json.loads(match.group())
                raise ValueError(f"无法解析响应：{text}")
        
        elif self.provider == "iflytek":
            # 讯飞星火响应格式
            result = response.choices[0].message.content if hasattr(response, 'choices') else ''
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                import re
                match = re.search(r'\{.*\}', result, re.DOTALL)
                if match:
                    return json.loads(match.group())
                raise ValueError(f"无法解析响应：{result}")
        
        elif self.provider in ["xiaomi", "deepseek"]:
            # 小米 Mimo 和 DeepSeek 使用标准 OpenAI 格式
            choices = response.get('choices', [])
            if not choices:
                raise ValueError(f"响应中没有 choices")
            text = choices[0].get('message', {}).get('content', '')
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                import re
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    return json.loads(match.group())
                raise ValueError(f"无法解析响应：{text}")
        
        else:
            raise ValueError(f"不支持的 Provider: {self.provider}")
    
    def recognize(self, text: str, use_cache: bool = True) -> dict:
        """
        识别单个职位描述中的技能
        
        Args:
            text: 职位描述文本
            use_cache: 是否使用缓存
            
        Returns:
            dict: 技能识别结果
        """
        # 检查缓存
        if use_cache:
            cached_result = self.cache.get(text)
            if cached_result:
                return cached_result
        
        # 构建 Prompt
        prompt = self._build_prompt(text)
        
        # 调用 API
        client = self._get_client()
        
        if self.provider == "aliyun":
            response = client.call(
                model=self.model,
                prompt=prompt,
                result_format='message',
                temperature=0.1,
                timeout=self.timeout
            )
        elif self.provider == "baidu":
            response = client.do(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
        elif self.provider == "iflytek":
            # 讯飞星火 API 调用
            from sparkai.core.messages import ChatMessage
            messages = [ChatMessage(role="user", content=prompt)]
            response = client.ChatCompletion(
                api_key=self.api_key,
                model=self.model,
                messages=messages,
                temperature=0.1
            )
        elif self.provider in ["xiaomi", "deepseek"]:
            # 小米 Mimo 和 DeepSeek 使用标准 OpenAI 格式
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1
            }
            resp = client.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            resp.raise_for_status()
            response = resp.json()
        else:
            raise ValueError(f"不支持的 Provider: {self.provider}")
        
        # 解析响应
        result = self._parse_response(response)
        
        # 存入缓存
        if use_cache:
            self.cache.set(text, result)
        
        return result
    
    def recognize_batch(self, texts: List[str], use_cache: bool = True) -> List[dict]:
        """
        批量识别技能（优化成本）
        
        Args:
            texts: 职位描述文本列表
            use_cache: 是否使用缓存
            
        Returns:
            List[dict]: 每个文本对应的识别结果
        """
        results = []
        
        # 分组处理
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            
            # 尝试从缓存获取
            batch_results = []
            need_api_call = []
            
            for j, text in enumerate(batch):
                if use_cache:
                    cached = self.cache.get(text)
                    if cached:
                        batch_results.append(cached)
                        continue
                
                need_api_call.append((j, text))
            
            # 批量调用 API
            if need_api_call:
                # 合并多个文本为一个 Prompt
                combined_texts = "\n\n".join([
                    f"【职位{j+1}】\n{text}" 
                    for j, text in need_api_call
                ])
                
                combined_prompt = f"""{self.prompt_template.get('system_prompt', '')}

请分析以下 {len(need_api_call)} 个职位描述，按顺序输出每个职位的技能识别结果：

{combined_texts}

输出格式：
{{
  "results": [
    {{ /* 职位 1 的结果 */ }},
    {{ /* 职位 2 的结果 */ }},
    ...
  ]
}}
"""
                # 调用 API
                client = self._get_client()
                
                if self.provider == "aliyun":
                    response = client.call(
                        model=self.model,
                        prompt=combined_prompt,
                        result_format='message',
                        temperature=0.1,
                        timeout=self.timeout * len(need_api_call)  # 适当延长超时
                    )
                elif self.provider == "baidu":
                    response = client.do(
                        messages=[{"role": "user", "content": combined_prompt}],
                        temperature=0.1
                    )
                else:
                    raise ValueError(f"不支持的 Provider: {self.provider}")
                
                # 解析批量响应
                combined_result = self._parse_response(response)
                individual_results = combined_result.get("results", [])
                
                # 填充结果
                for idx, (j, text) in enumerate(need_api_call):
                    if idx < len(individual_results):
                        result = individual_results[idx]
                        batch_results.insert(j, result)
                        
                        # 存入缓存
                        if use_cache:
                            self.cache.set(text, result)
                    else:
                        #  fallback：空结果
                        batch_results.insert(j, {"standard_skills": {}, "new_skills": []})
            
            results.extend(batch_results)
        
        return results
    
    def estimate_tokens(self, text: str) -> int:
        """
        估算 token 数量（简化版：按字符数估算）
        
        Args:
            text: 文本内容
            
        Returns:
            int: 估算的 token 数
        """
        # 中文约 1.5 字符/token，英文约 4 字符/token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        
        estimated_tokens = chinese_chars // 2 + other_chars // 4
        return max(estimated_tokens, 1)
    
    def get_usage_stats(self) -> dict:
        """获取使用统计"""
        return {
            "provider": self.provider,
            "model": self.model,
            "cache_size": len(self.cache.cache),
        }
