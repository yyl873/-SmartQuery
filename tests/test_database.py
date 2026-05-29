"""
pytest 测试: CSV 分隔符检测、列类型推断、URL 构建
运行: pytest tests/ -v
"""

import pytest
from sqlalchemy import Integer, Float, Text
from app.database import _detect_delimiter, _guess_type, _build_url


# ========== _detect_delimiter ==========

class TestDetectDelimiter:

    def test_comma_csv(self):
        content = "id,name,age\n1,张三,25\n2,李四,30"
        assert _detect_delimiter(content) == ","

    def test_tab_tsv(self):
        content = "id\tname\tage\n1\t张三\t25\n2\t李四\t30"
        assert _detect_delimiter(content) == "\t"

    def test_semicolon(self):
        content = "id;name;age\n1;张三;25\n2;李四;30"
        assert _detect_delimiter(content) == ";"

    def test_pipe(self):
        content = "id|name|age\n1|张三|25\n2|李四|30"
        assert _detect_delimiter(content) == "|"

    def test_comma_with_quotes(self):
        """带引号的 CSV，sniffer 能识别"""
        content = 'id,name,note\n1,张三,"hello, world"\n2,李四,test'
        assert _detect_delimiter(content) == ","

    def test_single_column_fallback(self):
        """只有一列时，sniffer 返回什么就用什么"""
        content = "id\n1\n2\n3"
        assert _detect_delimiter(content) in [",", "\t", ";", "|"]

    def test_multiline_content(self):
        """多行数据"""
        content = "city,count\n北京,100\n上海,200\n广州,150"
        assert _detect_delimiter(content) == ","


# ========== _guess_type ==========

class TestGuessType:

    def test_integer_column(self):
        assert _guess_type(["1", "2", "3", "100"]) is Integer

    def test_float_column(self):
        assert _guess_type(["1.5", "2.0", "3.14"]) is Float

    def test_mixed_int_float(self):
        assert _guess_type(["1", "2.5", "3"]) is Float

    def test_text_column(self):
        assert _guess_type(["hello", "world", "test"]) is Text

    def test_mixed_text_numbers(self):
        """混合文本和数字 → Text"""
        assert _guess_type(["1", "2", "hello"]) is Text

    def test_empty_list(self):
        assert _guess_type([]) is Text

    def test_single_value(self):
        assert _guess_type(["42"]) is Integer

    def test_negative_numbers(self):
        assert _guess_type(["-1", "-2", "3"]) is Integer

    def test_boolean_like(self):
        """True/False 字符串应该识别为 Text（避免误判）"""
        assert _guess_type(["True", "False", "True"]) is Text


# ========== _build_url ==========

class TestBuildURL:

    def test_sqlite_default(self):
        url = _build_url("sqlite", "", "", "", "", "")
        assert url.startswith("sqlite:///")
        assert "smartquery.db" in url

    def test_sqlite_custom_path(self):
        url = _build_url("sqlite", "", "", "mydata.db", "", "")
        assert "mydata.db" in url

    def test_mysql(self):
        url = _build_url("mysql", "localhost", "3306", "testdb", "root", "pass")
        assert url == "mysql+pymysql://root:pass@localhost:3306/testdb"

    def test_postgresql(self):
        url = _build_url("postgresql", "192.168.1.1", "5432", "mydb", "admin", "secret")
        assert url == "postgresql://admin:secret@192.168.1.1:5432/mydb"

    def test_postgresql_default_port(self):
        url = _build_url("postgresql", "localhost", "", "mydb", "user", "pw")
        assert ":5432" in url

    def test_mysql_default_port(self):
        url = _build_url("mysql", "localhost", "", "mydb", "user", "pw")
        assert ":3306" in url

    def test_unknown_db_type(self):
        with pytest.raises(ValueError) as exc:
            _build_url("oracle", "", "", "", "", "")
        assert "不支持" in str(exc.value)
