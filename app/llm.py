"""
SmartQuery LLM 调用模块
通过 OpenAI 兼容接口调用大模型，生成 SQL 查询语句和数据翻译。
内置自动重试、超时机制、流式输出和少量示例检索。
"""

import re
import time
from typing import Generator
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

# ========== Few-Shot 示例库 ==========
# 根据用户问题关键词匹配合适的 example，提高生成质量
FEWSHOT_EXAMPLES = [
    {
        "keywords": ["统计", "每个", "数量", "分组", "count", "group"],
        "question": "每个城市的用户数量是多少？",
        "sql": "SELECT city, COUNT(*) AS user_count FROM users GROUP BY city ORDER BY user_count DESC",
    },
    {
        "keywords": ["排名", "前", "最高", "top", "order", "排序"],
        "question": "销售额最高的前 5 个产品是什么？",
        "sql": "SELECT name, SUM(amount) AS total FROM orders GROUP BY name ORDER BY total DESC LIMIT 5",
    },
    {
        "keywords": ["平均", "avg", "均值"],
        "question": "产品的平均价格是多少？",
        "sql": "SELECT category, AVG(price) AS avg_price FROM products GROUP BY category",
    },
    {
        "keywords": ["大于", "小于", "过滤", "条件", "where", "筛选"],
        "question": "价格大于 100 的产品有哪些？",
        "sql": "SELECT * FROM products WHERE price > 100",
    },
    {
        "keywords": ["连接", "关联", "join", "联合"],
        "question": "每个用户有多少订单？",
        "sql": "SELECT u.name, COUNT(o.id) AS order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.name",
    },
    {
        "keywords": ["插入", "新增", "添加", "insert"],
        "question": "添加一个新用户张三到北京",
        "sql": "INSERT INTO users (name, city, register_date) VALUES ('张三', '北京', '2024-01-01')",
    },
    {
        "keywords": ["更新", "修改", "改", "update"],
        "question": "把张三的城市改成上海",
        "sql": "UPDATE users SET city = '上海' WHERE name = '张三'",
    },
    {
        "keywords": ["删除", "移除", "delete"],
        "question": "删除所有已过期的订单",
        "sql": "DELETE FROM orders WHERE status = 'expired'",
    },
]


def _match_fewshot(question: str, max_examples: int = 2) -> list[dict]:
    """
    基于关键词匹配，从示例库中选取最相关的 few-shot 示例。
    简单高效，无需向量数据库。
    """
    q_lower = question.lower()
    scored = []
    for ex in FEWSHOT_EXAMPLES:
        score = sum(1 for kw in ex["keywords"] if kw.lower() in q_lower)
        if score > 0:
            scored.append((score, ex))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [ex for _, ex in scored[:max_examples]]


def _build_prompt_with_fewshot(question: str, schema: str) -> str:
    """
    构建增强版 prompt：加入匹配到的 few-shot 示例，
    提升 LLM 生成 SQL 的准确率。
    """
    examples = _match_fewshot(question)
    if not examples:
        return build_prompt(question, schema)

    # 在原始 prompt 中注入示例
    example_str = ""
    for i, ex in enumerate(examples, 1):
        example_str += f"示例 {i}:\n问题: {ex['question']}\nSQL: {ex['sql']}\n\n"

    prompt = f"""你是一个专业的 SQL 生成助手。根据用户问题、数据库 schema 和参考示例，生成正确的 SQL 查询。

规则：
- 只返回 SQL 语句，不要有任何解释。
- 列名和表名必须与 Schema 中完全一致。
- 如果用户提到的字段在 Schema 中不存在，只返回一个词：UNANSWERABLE

参考示例:
{example_str}
数据库 Schema:
{schema}

用户问题:
{question}

请生成 SQL:"""
    return prompt


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
                messages=[{"role": "user", "content": prompt}],
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


def _call_llm_stream(prompt: str, max_tokens: int = 500) -> Generator[str, None, None]:
    """
    流式 LLM 调用，逐 token yield 返回内容。
    用于 SSE（Server-Sent Events）实时展示生成过程。
    """
    try:
        stream = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=max_tokens,
            timeout=30,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except APITimeoutError:
        yield "\n[ERROR] LLM 响应超时"
    except APIError as e:
        yield f"\n[ERROR] API 错误: {e}"
    except Exception as e:
        yield f"\n[ERROR] 调用失败: {str(e)}"


def _strip_markdown_sql(text: str) -> str:
    """去除 LLM 可能包裹的 markdown 代码块标记"""
    text = re.sub(r"^```sql\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def generate_sql(question: str, schema: str) -> str:
    """
    调用 LLM 根据用户问题和数据库 Schema 生成 SQL 语句。
    自动匹配 few-shot 示例提高准确率。
    返回去除 markdown 包裹后的纯 SQL 字符串。
    """
    prompt = _build_prompt_with_fewshot(question, schema)
    raw = _call_llm(prompt, max_tokens=500)
    return _strip_markdown_sql(raw)


def generate_sql_stream(question: str, schema: str) -> Generator[str, None, None]:
    """
    流式生成 SQL（逐 token 返回），用于 SSE 端点。
    """
    prompt = _build_prompt_with_fewshot(question, schema)
    return _call_llm_stream(prompt, max_tokens=500)


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
