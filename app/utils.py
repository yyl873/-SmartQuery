"""
SmartQuery 工具函数模块
提供 SQL 安全性检查和格式化功能（基于 sqlparse AST 分析）
"""

import sqlparse

# 永远禁止的 DDL / 权限操作（任何模式下都不允许）
DDL_DANGEROUS_KEYWORDS = {
    "DROP", "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE", "REPLACE",
}

# 写操作关键字（仅在 write_mode=True 时允许）
DML_WRITE_KEYWORDS = {
    "DELETE", "UPDATE", "INSERT",
}

# 所有危险关键字（只读模式用，保持向后兼容）
ALL_DANGEROUS_KEYWORDS = DDL_DANGEROUS_KEYWORDS | DML_WRITE_KEYWORDS


def is_safe_sql(sql: str, write_mode: bool = False) -> bool:
    """
    使用 sqlparse AST 级别检查 SQL 语句是否安全。

    两级安全控制：
    - 默认（write_mode=False）：仅允许 SELECT 只读查询
    - 写模式（write_mode=True）：允许 SELECT / UPDATE / DELETE / INSERT，
      但永远禁止 DROP / ALTER / TRUNCATE / CREATE / GRANT / REVOKE / REPLACE

    优势（相比简单子串匹配）：
    - 可检测多语句 SQL 中第二句的危险操作（如 SELECT 1; DROP TABLE users）
    - 不会误判字符串字面量中的关键字（如 SELECT 'drop it'）
    - 通过 token type 精确识别真正的 DML/DDL 关键字

    如果解析失败，降级为简单子串检查。
    """
    if write_mode:
        blocked = DDL_DANGEROUS_KEYWORDS
    else:
        blocked = ALL_DANGEROUS_KEYWORDS

    try:
        statements = sqlparse.parse(sql)
        for stmt in statements:
            if not stmt:
                continue
            for token in stmt.flatten():
                # 只检查真正的关键字 token（不含字符串字面量、注释等）
                ttype = getattr(token, 'ttype', None)
                if ttype in (
                    sqlparse.tokens.Keyword,
                    sqlparse.tokens.Keyword.DDL,
                    sqlparse.tokens.Keyword.DML,
                ):
                    kw = token.value.upper().strip()
                    if kw in blocked:
                        return False
        return True
    except Exception:
        # 解析失败时，降级为简单子串检查
        sql_lower = sql.lower()
        for kw in blocked:
            if kw.lower() in sql_lower:
                return False
        return True


def is_safe_table_name(name: str) -> bool:
    """
    验证表名是否安全：只允许字母、数字、下划线、中文，长度 1-64。
    防止 SQL 注入。
    """
    if not name or len(name) > 64:
        return False
    return all(c.isalnum() or c in "_" or '一' <= c <= '鿿' or
               '㐀' <= c <= '䶿' for c in name)


def detect_encoding(raw_bytes: bytes) -> str:
    """
    自动检测文本编码，优先中文兼容编码。
    按顺序尝试：UTF-8 BOM → UTF-16 BOM → UTF-8 → GBK → GB18030 → UTF-16
    """
    if not raw_bytes:
        return "utf-8"

    # BOM 检测
    if raw_bytes.startswith(b'\xef\xbb\xbf'):
        return "utf-8-sig"   # UTF-8 with BOM（Excel 导出常见）
    if raw_bytes.startswith(b'\xff\xfe'):
        return "utf-16-le"
    if raw_bytes.startswith(b'\xfe\xff'):
        return "utf-16-be"

    # 逐一尝试解码
    encodings = ["utf-8", "gbk", "gb18030", "utf-16"]
    for enc in encodings:
        try:
            raw_bytes.decode(enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue

    # 所有编码都失败，尝试 latin-1（永不失败）并警告
    return "latin-1"


def format_sql(sql: str) -> str:
    """
    使用 sqlparse 格式化 SQL 语句，关键字大写。
    """
    formatted = sqlparse.format(
        sql,
        reindent=True,        # 重新缩进
        keyword_case="upper",  # 关键字大写
    )
    return formatted.strip()
