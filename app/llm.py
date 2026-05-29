"""
SmartQuery LLM 调用模块
通过 OpenAI 兼容接口调用大模型，生成 SQL 查询语句和数据翻译。
内置自动重试和超时机制。
"""

import re
import time
from openai import OpenAI, APITimeoutError, APIError
from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from app.prompts import build_prompt, build_fix_prompt, build_translation_prompt

# 初始化 OpenAI 客户端（兼容 DeepSeek 等接口）
client = OpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
    timeout=30.0,  # 全局超时 30 秒
)

# 最多重试次数
MAX_RETRIES = 1


def _call_llm(prompt: str, max_tokens: int = 500, retries: int = MAX_RETRIES) -> str:
    """
    通用 LLM 调用封装。
    - 消息列表中只包含一条 user 消息，不使用 system 角色。
    - 超时 30s，失败自动重试 1 次（间隔 1.5s）。
    """
    last_error = None
    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],  # 仅 user 消息
                temperature=0,
                max_tokens=max_tokens,
                timeout=30,
            )
            return response.choices[0].message.content.strip()
        except APITimeoutError as e:
            last_error = RuntimeError(f"LLM 响应超时（30s），请检查网络或重试")
            if attempt < retries:
                time.sleep(1.5)
        except APIError as e:
            last_error = RuntimeError(f"LLM API 错误: {e}")
            if attempt < retries:
                time.sleep(1.5)
        except Exception as e:
            last_error = RuntimeError(f"LLM 调用失败: {str(e)}")
            if attempt < retries:
                time.sleep(1.5)
    raise last_error


def _strip_markdown_sql(text: str) -> str:
    """去除 LLM 可能包裹的 markdown 代码块标记"""
    text = re.sub(r"^```sql\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def generate_sql(question: str, schema: str) -> str:
    """
    调用 LLM 根据用户问题和数据库 Schema 生成 SQL 语句。
    返回去除 markdown 包裹后的纯 SQL 字符串。
    """
    prompt = build_prompt(question, schema)
    raw = _call_llm(prompt, max_tokens=500)
    return _strip_markdown_sql(raw)


def fix_sql(question: str, schema: str, failed_sql: str, error_msg: str) -> str:
    """
    当 SQL 执行失败时，将错误信息反馈给 LLM，让它修正 SQL。
    返回修正后的 SQL（或 UNANSWERABLE）。
    """
    prompt = build_fix_prompt(question, schema, failed_sql, error_msg)
    raw = _call_llm(prompt, max_tokens=500)
    return _strip_markdown_sql(raw)


def generate_translation(question: str, sql: str, data: list[dict]) -> dict[str, str]:
    """
    调用 LLM 将查询结果翻译为中英文自然语言解释。
    返回 {"zh": "中文解释", "en": "English explanation"}
    """
    prompt = build_translation_prompt(question, sql, data)
    raw = _call_llm(prompt, max_tokens=600)

    # 解析 LLM 返回的中英文内容
    zh_text = ""
    en_text = ""

    # 尝试按 "中文：" 和 "English:" 标记分割
    parts_zh = re.split(r"English:\s*", raw, maxsplit=1, flags=re.IGNORECASE)
    if len(parts_zh) >= 2:
        en_text = parts_zh[1].strip()

    # 从第一部分提取中文
    first_part = parts_zh[0]
    zh_match = re.search(r"中文[：:]\s*(.*?)$", first_part, re.DOTALL)
    if zh_match:
        zh_text = zh_match.group(1).strip()
    else:
        # 如果没有标记，把第一部分当作中文
        zh_text = first_part.replace("中文：", "").replace("中文:", "").strip()

    if not en_text:
        en_text = "No data available."

    return {"zh": zh_text, "en": en_text}
