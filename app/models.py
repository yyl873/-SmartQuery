"""
SmartQuery 数据模型模块
定义 API 请求和响应的 Pydantic 模型
"""

from typing import Optional
from pydantic import BaseModel


class QueryRequest(BaseModel):
    """用户自然语言查询请求"""
    question: str = ""          # 用户用自然语言提出的问题
    sql: str = ""               # 可选：如果提供，跳过 LLM 生成，直接执行此 SQL
    write_mode: bool = False    # 是否启用写操作模式（允许 UPDATE/DELETE/INSERT）


class GenerateRequest(BaseModel):
    """仅生成 SQL 的请求"""
    question: str               # 用户自然语言问题


class GenerateResponse(BaseModel):
    """仅生成 SQL 的响应"""
    sql: str = ""               # LLM 生成的 SQL 语句
    error: Optional[str] = None # 错误信息


class Translation(BaseModel):
    """中英文翻译结果"""
    zh: str = ""  # 中文翻译
    en: str = ""  # 英文翻译


class QueryResponse(BaseModel):
    """查询响应，包含生成的 SQL、查询结果、翻译和错误信息"""
    sql: str = ""                              # 最终执行的 SQL 语句
    data: list[dict] = []                      # SQL 执行返回的数据
    translation: Optional[Translation] = None  # 中英文自然语言翻译
    error: Optional[str] = None                # 错误信息，成功时为 None


class ConnectRequest(BaseModel):
    """数据库连接请求"""
    db_type: str = "sqlite"     # sqlite / mysql / postgresql
    host: str = ""              # 主机地址
    port: str = ""              # 端口（mysql:3306, pg:5432）
    database: str = ""          # 数据库名（sqlite 为文件路径）
    user: str = ""              # 用户名
    password: str = ""          # 密码


class TableInfo(BaseModel):
    """表结构信息"""
    table_name: str                          # 表名
    columns: list[dict] = []                 # 列信息 [{"name":..., "type":..., "nullable":..., "default":...}]
