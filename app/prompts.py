"""
SmartQuery 提示词模块
构建发送给 LLM 的 prompt（仅使用 user 角色消息）
"""


def build_prompt(question: str, schema: str) -> str:
    """
    构建 NL2SQL 的完整提示词。
    将指令、数据库 Schema 和用户问题拼接在一起，作为 user 消息内容发送给 LLM。
    注意：不使用 system 角色。
    """
    prompt = f"""你是一个专业的 SQL 生成助手。根据用户问题、数据库 schema，生成正确的 SQL 查询。

规则（严格遵守）：
- 只返回 SQL 语句，不要有任何解释。
- 列名和表名必须与 Schema 中完全一致，不允许编造或猜测。
- 如果用户提到的字段在 Schema 中不存在，只返回一个词：UNANSWERABLE
- 如果问题无法用 SQL 回答，只返回一个词：UNANSWERABLE

数据库 Schema:
{schema}

用户问题:
{question}

请生成 SQL:"""
    return prompt


def build_fix_prompt(question: str, schema: str, failed_sql: str, error_msg: str) -> str:
    """
    当 SQL 执行失败时，将错误信息和 Schema 反馈给 LLM，让它修正 SQL。
    """
    prompt = f"""你之前生成的 SQL 执行失败，请根据数据库 schema 修正它。

数据库 Schema:
{schema}

用户原始问题:
{question}

失败的 SQL:
{failed_sql}

数据库报错:
{error_msg}

规则：
- 只返回修正后的 SQL 语句，不要有任何解释。
- 列名和表名必须与 Schema 中完全一致。
- 如果确实无法修正，只返回一个词：UNANSWERABLE

请返回修正后的 SQL:"""
    return prompt


def build_translation_prompt(question: str, sql: str, data: list[dict]) -> str:
    """
    构建数据翻译的提示词。
    将用户问题、执行的 SQL 和查询结果发给 LLM，
    让它用中英文双语解释数据的含义，方便非技术人员理解。
    """
    # 将数据格式化为可读的表格文本
    if not data:
        data_text = "（无数据）"
    else:
        data_text = str(data)

    prompt = f"""你是一个数据翻译助手。请根据以下信息，用自然语言解释查询结果的含义。

要求：
- 用中文解释（标为"中文："）
- 用英文解释（标为"English:"）
- 解释要通俗易懂，让非技术人员也能理解
- 如果数据为空，说明"查询无匹配结果"
- 不要添加额外信息，只做翻译解释

用户原始问题:
{question}

执行的 SQL:
{sql}

查询结果:
{data_text}

请给出中英文翻译:"""
    return prompt
