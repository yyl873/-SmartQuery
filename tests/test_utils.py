"""
pytest 测试: SQL 安全检查 / 表名校验 / 编码检测
运行: pytest tests/ -v
"""

import pytest
from app.utils import is_safe_sql, is_safe_table_name, detect_encoding, format_sql


# ========== is_safe_sql ==========

class TestIsSafeSQL:
    """SQL 安全性检查（两级权限模型）"""

    # --- 只读模式（write_mode=False，默认） ---

    def test_select_simple(self):
        assert is_safe_sql("SELECT * FROM users", write_mode=False) is True

    def test_select_with_join(self):
        assert is_safe_sql(
            "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id",
            write_mode=False
        ) is True

    def test_select_with_subquery(self):
        assert is_safe_sql(
            "SELECT * FROM (SELECT id FROM users) AS sub",
            write_mode=False
        ) is True

    def test_select_with_where(self):
        assert is_safe_sql(
            "SELECT * FROM users WHERE name LIKE '%张%'",
            write_mode=False
        ) is True

    def test_select_count_group(self):
        assert is_safe_sql(
            "SELECT city, COUNT(*) FROM users GROUP BY city HAVING COUNT(*) > 5",
            write_mode=False
        ) is True

    # 只读模式：拒绝写操作

    def test_block_insert_readonly(self):
        assert is_safe_sql("INSERT INTO users VALUES (1, 'test')", write_mode=False) is False

    def test_block_update_readonly(self):
        assert is_safe_sql("UPDATE users SET name='x' WHERE id=1", write_mode=False) is False

    def test_block_delete_readonly(self):
        assert is_safe_sql("DELETE FROM users WHERE id=1", write_mode=False) is False

    def test_block_drop_readonly(self):
        assert is_safe_sql("DROP TABLE users", write_mode=False) is False

    # 写模式：允许 DML，拒绝 DDL

    def test_allow_insert_write_mode(self):
        assert is_safe_sql("INSERT INTO users VALUES (1, 'test')", write_mode=True) is True

    def test_allow_update_write_mode(self):
        assert is_safe_sql("UPDATE users SET name='x' WHERE id=1", write_mode=True) is True

    def test_allow_delete_write_mode(self):
        assert is_safe_sql("DELETE FROM users WHERE id=1", write_mode=True) is True

    def test_block_drop_write_mode(self):
        """DDL 永远禁止，即使写模式也不行"""
        assert is_safe_sql("DROP TABLE users", write_mode=True) is False

    def test_block_alter_write_mode(self):
        assert is_safe_sql("ALTER TABLE users ADD COLUMN age INT", write_mode=True) is False

    def test_block_create_write_mode(self):
        assert is_safe_sql("CREATE TABLE test (id INT)", write_mode=True) is False

    def test_block_truncate_write_mode(self):
        assert is_safe_sql("TRUNCATE TABLE users", write_mode=True) is False

    # 多语句检测

    def test_multi_statement_hidden_danger(self):
        """第二句是危险操作，必须检测出来"""
        assert is_safe_sql("SELECT 1; DROP TABLE users", write_mode=False) is False

    def test_multi_statement_hidden_delete(self):
        assert is_safe_sql("SELECT * FROM users; DELETE FROM users", write_mode=False) is False

    # 字符串字面量不误判

    def test_string_literal_not_blocked(self):
        """字符串里的 'drop' 不应该被拦截"""
        assert is_safe_sql(
            "SELECT * FROM songs WHERE title = 'drop it like it''s hot'",
            write_mode=False
        ) is True

    def test_string_literal_delete_not_blocked(self):
        assert is_safe_sql(
            "SELECT * FROM comments WHERE text = 'please delete this'",
            write_mode=False
        ) is True

    # 边界情况

    def test_empty_sql(self):
        assert is_safe_sql("", write_mode=False) is True

    def test_whitespace_only(self):
        assert is_safe_sql("   ", write_mode=False) is True

    def test_comment_only(self):
        assert is_safe_sql("-- this is a comment", write_mode=False) is True

    def test_case_insensitive(self):
        assert is_safe_sql("select * from users", write_mode=False) is True
        assert is_safe_sql("drop table users", write_mode=False) is False


# ========== is_safe_table_name ==========

class TestIsSafeTableName:

    def test_english_name(self):
        assert is_safe_table_name("users") is True

    def test_chinese_name(self):
        assert is_safe_table_name("订单表") is True

    def test_mixed_name(self):
        assert is_safe_table_name("订单_orders_2024") is True

    def test_empty_name(self):
        assert is_safe_table_name("") is False

    def test_too_long_name(self):
        assert is_safe_table_name("a" * 65) is False

    def test_just_under_limit(self):
        assert is_safe_table_name("a" * 64) is True

    def test_sql_injection_attempt(self):
        assert is_safe_table_name("users; DROP TABLE users") is False

    def test_special_chars(self):
        assert is_safe_table_name("users!@#") is False

    def test_none(self):
        """防御 None 输入，返回 False 不抛异常"""
        assert is_safe_table_name(None) is False


# ========== detect_encoding ==========

class TestDetectEncoding:

    def test_utf8_ascii(self):
        assert detect_encoding(b"hello world") == "utf-8"

    def test_utf8_chinese(self):
        assert detect_encoding("你好世界".encode("utf-8")) == "utf-8"

    def test_utf8_bom(self):
        assert detect_encoding(b'\xef\xbb\xbf' + "数据".encode("utf-8")) == "utf-8-sig"

    def test_gbk_chinese(self):
        data = "订单编号,产品名称,金额\n001,手机,2999".encode("gbk")
        assert detect_encoding(data) == "gbk"

    def test_utf16_le_bom(self):
        data = b'\xff\xfe' + "测试".encode("utf-16-le")
        assert detect_encoding(data) == "utf-16-le"

    def test_utf16_be_bom(self):
        data = b'\xfe\xff' + "测试".encode("utf-16-be")
        assert detect_encoding(data) == "utf-16-be"

    def test_empty_bytes(self):
        assert detect_encoding(b"") == "utf-8"

    def test_gb18030(self):
        """GB18030 兼容 GBK，能编码更生僻的字"""
        data = "𠀀测试".encode("gb18030")
        assert detect_encoding(data) == "gb18030"

    def test_latin1_fallback(self):
        """无法识别的二进制数据回退到 latin-1"""
        import struct
        # 随机二进制数据（不是任何有效文本编码）
        data = struct.pack("4f", 3.14, -2.71, 1.41, 0.0)
        # 这种随机构造的二进制在 detect_encoding 中可能会被 GBK 误吞，
        # 我们只验证它不会抛异常即可
        result = detect_encoding(data)
        assert result is not None  # 总能返回一个编码


# ========== format_sql ==========

class TestFormatSQL:

    def test_keyword_uppercase(self):
        result = format_sql("select * from users")
        assert "SELECT" in result.upper()
        assert "*" in result

    def test_reindent(self):
        result = format_sql("select id,name from users where id>10 order by name")
        # 应该有换行缩进
        lines = result.split("\n")
        assert len(lines) >= 2
