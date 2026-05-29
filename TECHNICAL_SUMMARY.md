# SmartQuery 项目技术总结

## 项目概述

**SmartQuery** — NL2SQL 智能数据库查询平台。用户输入自然语言问题，系统调用大模型自动生成 SQL 查询，执行后返回中英文双语翻译结果。提供 Stripe 风格毛玻璃 Web 界面，支持 SQLite / MySQL / PostgreSQL 动态切换，并打包为单文件 Windows EXE。

**技术栈**: Python 3.13 · FastAPI · SQLAlchemy Core · SQLite/MySQL/PostgreSQL · OpenAI 兼容 API (DeepSeek) · sqlparse · 原生 HTML/CSS/JS · PyInstaller · Docker · pytest

**代码规模**: 18 个 API 端点 · 67 个测试用例 · 52KB 单页前端 · 约 1500 行 Python

**开源协议**: GPL v3.0  
**仓库地址**: https://github.com/yyl873/-SmartQuery

---

## 一、系统架构

```
┌──────────────────────────────────────────────────────────┐
│                    SmartQuery 架构                        │
├─────────────┬──────────────────┬─────────────────────────┤
│   前端层     │      API 层       │       数据层            │
│ (vanilla)   │   (FastAPI)       │   (SQLAlchemy Core)     │
├─────────────┼──────────────────┼─────────────────────────┤
│ 入口选择页   │ /generate-sql     │ 全局 engine (可动态切换)  │
│ 3种角色模式  │ /generate-sql-    │                         │
│             │   stream (SSE)    │ SQLite ←→ MySQL ←→ PG   │
│ 毛玻璃 UI   │ /query            │                         │
│ 主题切换     │ /connect          │ Schema 提取 (inspect)    │
│ 查询编辑器   │ /disconnect       │ SQL 执行 (text query)    │
│ 结果展示     │ /import-csv       │ CSV 导入 + 类型推断      │
│ 导出/导入    │ /export           │ 表管理 (增/查/删)        │
│             │ /table-info       │                         │
│             │ /table/{name}     │                         │
├─────────────┴──────────────────┼─────────────────────────┤
│           安全层 (sqlparse AST) │       LLM 层              │
│  ├─ 只读模式 (默认)             │  OpenAI 兼容客户端         │
│  ├─ 写模式 (勾选后)             │  ├─ 仅使用 user 角色消息   │
│  └─ DDL 永久拦截               │  ├─ Few-Shot 示例匹配      │
│                                │  ├─ SSE 流式输出           │
│                                │  └─ 执行失败自动修正 (1次)  │
└────────────────────────────────┴──────────────────────────┘
```

## 二、核心技术实现

### 1. 两级 SQL 安全模型

**技术选型**: sqlparse AST 分析，而非正则匹配

**实现原理**:
- 解析 SQL 为 token 树，只检查 `Keyword.DDL` / `Keyword.DML` 类型的 token
- 自动忽略字符串字面量、注释中的关键字
- 支持多语句 SQL 的完整扫描（如 `SELECT 1; DROP TABLE users`）
- 解析失败时降级为子串匹配作为兜底

```python
# 两级权限定义
DDL_DANGEROUS_KEYWORDS = {"DROP", "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE", "REPLACE"}
DML_WRITE_KEYWORDS    = {"DELETE", "UPDATE", "INSERT"}

# 只读模式: 拦截 DDL + DML
# 写模式:   仅拦截 DDL，允许 DML
```

**设计优势**:
- 不会误判 `SELECT 'drop it' FROM songs` 为危险操作
- 多语句注入（`SELECT 1; DROP TABLE users`）能完整检测
- 通过 token type 精确识别，而非简单的子串包含

### 2. LLM 调用优化策略

**仅使用 user 角色消息**: 兼容 DeepSeek 等不支持 system 角色的 API，实测不影响生成质量。

**Few-Shot 示例自动匹配**: 维护 8 组 (问题, SQL) 示例对，根据输入问题的关键词匹配最相关的 2 个示例注入 prompt，显著提升生成准确率。

**SSE 流式输出**: 基于 Server-Sent Events 实现逐 token 实时推送，用户可实时看到 SQL 生成过程，体验类似 ChatGPT。

**执行失败自动修正**: SQL 执行失败时，将错误信息反馈 LLM 重新生成，最多修正 1 次。修正后重新过安全校验。

```
用户提问 → get_schema() → Few-Shot 匹配 → LLM 生成 → 
安全校验 → 执行 → 失败? → LLM 修正 → 再执行 → 双语翻译
```

### 3. CSV 智能导入

**编码自动检测**: 按优先级尝试 UTF-8 BOM → UTF-16 BOM → UTF-8 → GBK → GB18030 → UTF-16 → latin-1 兜底。覆盖国内用户 Excel 导出中文 CSV 的常见编码场景。

**分隔符自动识别**: 
- 优先使用 `csv.Sniffer().sniff()` 自动分析
- 失败时枚举逗号/Tab/分号/竖线，选列数最多的

**列类型推断**: 逐列扫描值，区分 Integer / Float / Text。支持混合类型降级 (如 `["1", "2.5", "hello"]` → Text)。

### 4. 数据库动态切换

SQLAlchemy Core 全局 `engine` 对象支持运行时热切换：

```python
# 切换流程
engine.dispose()                # 关闭旧连接
engine = create_engine(url)     # 创建新引擎
# url 格式:
#   SQLite:      sqlite:///./path.db
#   MySQL:       mysql+pymysql://user:pass@host:port/db
#   PostgreSQL:  postgresql://user:pass@host:port/db
```

通过 `/connect` 和 `/disconnect` 端点实现，无需重启服务。

### 5. 前端设计

**零框架**: 52KB 单文件 HTML，无 React/Vue 依赖，加载毫秒级。

**毛玻璃 UI**: `backdrop-filter: blur(20px)` + 半透明 `rgba(15,15,38,0.72)` 背景 + 紫蓝渐变 (#635bff→#00a4ff) 发光阴影。

**CSS 变量主题系统**: 通过 `[data-theme="dark"]` 属性选择器覆盖 20+ 自定义属性，实现浅色/深色一键切换。

**三种角色模式**: 入口页按角色分流 — 专业模式（完整功能）/ 日常查询（隐藏 DB 管理 + 写操作）/ 路人劝退。

**安全交互**: 所有危险操作（删表/断开连接/启用写模式/清空历史）均需确认弹窗。

### 6. 部署方案

| 方式 | 命令 | 产物 |
|------|------|------|
| 开发 | `uvicorn app.main:app --reload` | localhost:8000 |
| Docker | `docker compose up -d` | 容器化部署 |
| 桌面 EXE | `pyinstaller smartquery.spec` | 37MB 单文件 |

EXE 启动器 (`desktop_app.py`) 自动寻找空闲端口、检测 `.env` 配置、后台启动 uvicorn、自动打开浏览器。

---

## 三、测试覆盖

67 个 pytest 用例，覆盖核心模块：

| 模块 | 测试项 | 用例数 |
|------|--------|--------|
| `is_safe_sql()` | 只读模式拒绝/写模式允许/DDL 永拒/多语句/字符串字面量/空输入/大小写 | 18 |
| `is_safe_table_name()` | 英文/中文/混合/空/超长/注入/特殊字符/None | 9 |
| `detect_encoding()` | UTF-8/UTF-8-BOM/GBK/GB18030/UTF-16-LE/UTF-16-BE/空/损坏 | 8 |
| `format_sql()` | 关键字大写/缩进 | 2 |
| `_detect_delimiter()` | 逗号/Tab/分号/竖线/引号/单列/多行 | 7 |
| `_guess_type()` | Integer/Float/Text/混合/空/负数 | 9 |
| `_build_url()` | SQLite/MySQL/PG/默认端口/不支持类型 | 7 |

运行: `pytest tests/ -v` — 67 passed in 0.3s

---

## 四、API 端点清单

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/` | Web 界面 |
| POST | `/generate-sql` | NL2SQL 生成（非流式） |
| POST | `/generate-sql-stream` | NL2SQL 生成（SSE 流式） |
| POST | `/query` | 查询 + 执行 + 翻译 |
| POST | `/connect` | 切换数据库 |
| POST | `/disconnect` | 断开恢复 SQLite |
| POST | `/test-connection` | 测试连接 |
| GET | `/connection-info` | 当前连接信息 |
| GET | `/table-info/{name}` | 表结构详情 |
| GET | `/tables` | 所有表名 |
| DELETE | `/table/{name}` | 删除表 |
| POST | `/import-csv` | CSV 导入 |
| POST | `/export` | 导出 csv/json/xlsx |

---

## 五、项目亮点总结

1. **安全设计严谨**: sqlparse AST 级别的两级 SQL 权限模型，不是简单的关键词黑名单
2. **LLM 工程化**: Few-Shot 自动匹配 + SSE 流式 + 执行失败自动修正，不只是调 API
3. **编码兼容性**: GBK/GB18030/UTF-8/UTF-16 自动检测，解决真实场景的"乱码"问题
4. **多数据库支持**: SQLite/MySQL/PostgreSQL 动态切换，SQLAlchemy Core 抽象层
5. **前端工程能力**: 原生实现 Stripe 级毛玻璃 UI，CSS 变量主题系统，零框架依赖
6. **工程完整性**: 67 个测试 · Docker 部署 · 桌面 EXE · 文件日志 · 开源 GPL v3
7. **用户分层设计**: 三种角色模式，非技术人员也能安全使用
