"""
SmartQuery 数据库模块
负责数据库连接、Schema 提取、SQL 执行、CSV 导入和动态切换数据库
"""

import csv
import io
from sqlalchemy import create_engine, inspect, text, Table, Column, MetaData
from sqlalchemy import Integer, Float, Text
from app.config import DATABASE_URL
from app.utils import is_safe_table_name

# 当前激活的数据库引擎（支持运行时切换）
engine = create_engine(DATABASE_URL, echo=False)
_current_connection_info: dict = {
    "type": "sqlite",
    "url": DATABASE_URL,
    "host": "",
    "port": "",
    "database": "",
    "user": "",
}


def get_connection_info() -> dict:
    """返回当前数据库连接信息"""
    return dict(_current_connection_info)


def test_connection(db_type: str, host: str, port: str,
                    database: str, user: str, password: str) -> bool:
    """
    测试数据库连接是否成功。
    不改变当前激活的引擎，仅做连接测试。
    """
    url = _build_url(db_type, host, port, database, user, password)
    try:
        test_engine = create_engine(url, echo=False)
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        test_engine.dispose()
        return True
    except Exception:
        return False


def reconnect(db_type: str, host: str = "", port: str = "",
              database: str = "", user: str = "", password: str = ""):
    """
    切换到新的数据库连接。
    - db_type: "sqlite" / "mysql" / "postgresql"
    - 如果是 SQLite，database 是文件路径
    - MySQL/PostgreSQL 需要 host, port, database, user, password
    """
    global engine, _current_connection_info

    # 关闭旧引擎
    engine.dispose()

    url = _build_url(db_type, host, port, database, user, password)
    engine = create_engine(url, echo=False)

    _current_connection_info = {
        "type": db_type,
        "url": url,
        "host": host,
        "port": port,
        "database": database,
        "user": user,
    }


def _build_url(db_type: str, host: str, port: str,
               database: str, user: str, password: str) -> str:
    """根据连接参数构建数据库 URL"""
    db_type = db_type.lower().strip()
    if db_type == "sqlite":
        path = database or "smartquery.db"
        return f"sqlite:///./{path}"
    elif db_type == "mysql":
        p = port or "3306"
        return f"mysql+pymysql://{user}:{password}@{host}:{p}/{database}"
    elif db_type == "postgresql":
        p = port or "5432"
        return f"postgresql://{user}:{password}@{host}:{p}/{database}"
    else:
        raise ValueError(f"不支持的数据库类型: {db_type}")


def get_schema() -> str:
    """
    提取数据库中所有表的结构信息，返回格式化的字符串。
    """
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    schema_parts = []

    for table in table_names:
        columns = inspector.get_columns(table)
        col_strs = [f"{col['name']}({col['type']})" for col in columns]
        schema_parts.append(
            f"表名: {table}\n列: {', '.join(col_strs)}"
        )

    return "\n\n".join(schema_parts)


def execute_sql(sql: str) -> list[dict]:
    """
    执行 SQL 查询，将结果转为 list[dict] 返回。
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = [dict(row._mapping) for row in result]
            return rows
    except Exception as e:
        raise RuntimeError(f"SQL 执行失败: {e}")


def _guess_type(values: list[str]) -> type:
    """根据一列的值猜测 SQLAlchemy 类型"""
    int_count = 0
    float_count = 0
    for v in values:
        if v is None or v.strip() == "":
            continue
        v = v.strip()
        try:
            int(v)
            int_count += 1
        except ValueError:
            try:
                float(v)
                float_count += 1
            except ValueError:
                return Text
    if float_count > 0:
        return Float
    if int_count > 0:
        return Integer
    return Text


def _detect_delimiter(csv_content: str) -> str:
    """自动检测 CSV 内容的分隔符（逗号、Tab、分号等）"""
    sample = csv_content[:16384]
    # 优先尝试 csv.Sniffer
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        return dialect.delimiter
    except csv.Error:
        pass
    # Sniffer 失败时，按常见分隔符逐一尝试，选列数最多的
    best_delim = ","
    best_cols = 0
    for delim in [",", "\t", ";", "|"]:
        reader = csv.reader(io.StringIO(sample), delimiter=delim)
        first = next(reader, [])
        if len(first) > best_cols:
            best_cols = len(first)
            best_delim = delim
    return best_delim


def import_csv(table_name: str, csv_content: str) -> dict:
    """
    将 CSV 字符串导入为新表。
    自动检测分隔符（支持逗号、Tab、分号、竖线等）。
    """
    delimiter = _detect_delimiter(csv_content)
    reader = csv.reader(io.StringIO(csv_content), delimiter=delimiter)
    rows_list = list(reader)

    if len(rows_list) < 2:
        raise RuntimeError("CSV 至少需要表头行和一行数据")

    headers = [h.strip() for h in rows_list[0]]
    data_rows = rows_list[1:]

    clean_headers = []
    for h in headers:
        clean = h.strip().replace(" ", "_").replace("-", "_")
        if not clean:
            clean = "col"
        clean_headers.append(clean)

    cols_values = list(zip(*data_rows)) if data_rows else [[] for _ in headers]

    columns = []
    for i, col_name in enumerate(clean_headers):
        col_type = _guess_type(cols_values[i]) if i < len(cols_values) else Text
        columns.append(Column(col_name, col_type))

    metadata = MetaData()
    new_table = Table(
        table_name.strip().replace(" ", "_"),
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        *columns,
    )
    metadata.create_all(engine, checkfirst=True)

    insert_rows = []
    for row in data_rows:
        if len(row) == 0:
            continue
        record = {}
        for j, col_name in enumerate(clean_headers):
            val = row[j] if j < len(row) else None
            if val is not None and val.strip() != "":
                if isinstance(columns[j].type, Integer):
                    try:
                        val = int(val.strip())
                    except ValueError:
                        val = None
                elif isinstance(columns[j].type, Float):
                    try:
                        val = float(val.strip())
                    except ValueError:
                        val = None
                else:
                    val = val.strip()
            else:
                val = None
            record[col_name] = val
        insert_rows.append(record)

    if insert_rows:
        with engine.connect() as conn:
            conn.execute(new_table.insert(), insert_rows)
            conn.commit()

    return {
        "table": table_name.strip().replace(" ", "_"),
        "rows": len(insert_rows),
        "columns": clean_headers,
    }


def drop_table(table_name: str) -> dict:
    """
    删除指定表，返回被删表信息。
    仅允许删除已存在的表，防止 SQL 注入。
    """
    inspector = inspect(engine)
    existing = inspector.get_table_names()

    if table_name not in existing:
        raise RuntimeError(f"表 '{table_name}' 不存在")

    # 获取列数（删除前记录）
    cols = inspector.get_columns(table_name)
    col_count = len(cols)

    with engine.connect() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS `{table_name}`"))
        conn.commit()

    return {"table": table_name, "columns": col_count}
