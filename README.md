# 🧠 SmartQuery — 说人话就能查数据库

**NL2SQL 智能查询助手**：用大白话提问，AI 自动生成 SQL 并出结果。提供 Stripe 风格毛玻璃 Web 界面，支持 SQLite / MySQL / PostgreSQL，自带桌面 EXE。

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue" alt="Python">
  <img src="https://img.shields.io/badge/framework-FastAPI-009688" alt="FastAPI">
  <img src="https://img.shields.io/badge/database-SQLite%20%7C%20MySQL%20%7C%20PG-orange" alt="Database">
  <img src="https://img.shields.io/badge/LLM-OpenAI%20%7C%20DeepSeek-purple" alt="LLM">
  <img src="https://img.shields.io/badge/frontend-vanilla-green" alt="Frontend">
</p>

---

## 🎯 三种模式，谁都能用

打开后先选角色，不吓唬人：

| 模式 | 适合谁 | 能干啥 |
|------|--------|--------|
| 🛠️ **专业模式** | 开发者、数据分析师 | 完整功能：连接数据库、导入 CSV、写 SQL、删表 |
| 📊 **日常查询** | 业务同学、非技术人员 | 用大白话提问就行，**只能查不能改**，不怕改错数据 |
| 👶 **我就是来看看** | 逛进来的路人 | 会被礼貌劝退 😅 "别闹～这不是您该来的地方" |

---

## ✨ 功能一览

### 核心
- 🔍 **自然语言 → SQL**：输入中文问题，AI 自动生成并格式化 SQL，可手动编辑后执行
- 🌐 **中英文翻译**：查询结果附带双语解释，非技术人员也能看懂
- 🛡️ **两级安全**：
  - 默认只允许 SELECT（AST 级别拦截）
  - 勾选"启用写操作"后允许 UPDATE / DELETE / INSERT
  - DDL（DROP / ALTER / TRUNCATE / CREATE）永久拦截

### 数据库管理（专业模式）
- 🔗 **DBeaver 风格连接**：Web 界面切换 SQLite / MySQL / PostgreSQL
- 🧪 **连接测试**：一键测试，无需重启
- 🔌 **断开恢复**：切回默认 SQLite
- 📋 **表结构预览**：点击表名查看列名、类型、主键
- 📤 **CSV 导入**：拖拽上传，自动识别分隔符和编码（GBK / UTF-8 / UTF-16 都行）
- 🗑 **删表确认**：弹窗确认后才删除，防手滑
- 📥 **多格式导出**：CSV / JSON / Excel

### 体验
- 🎨 **Stripe 风格界面**：毛玻璃卡片、紫蓝渐变、大圆角 + 发光阴影
- 🌓 **浅色 / 深色主题**：一键切换，偏好自动记忆
- 🕐 **查询历史**：最近 20 条，点击恢复
- ⌨️ **快捷键**：Enter 生成 SQL，Ctrl+Enter 执行
- ⚠️ **免责声明**：首次使用弹窗确认

### 桌面版
- 📦 **单文件 EXE**：37MB，双击即用，自动打开浏览器
- 🔄 **自动找端口**：8000 被占了就换一个
- 📝 **.env 放旁边**：API Key 在 EXE 同目录配置

---

## 🚀 快速开始

### 方式一：双击 start.bat（推荐）

自动完成：安装依赖 → 初始化数据库 → 启动服务 → 打开浏览器。

### 方式二：手动

```bash
pip install -r requirements.txt
python init_db.py
uvicorn app.main:app --reload
```

打开 **http://localhost:8000**

### 方式三：桌面 EXE

下载 `dist/SmartQuery.exe`，双击运行。将 `.env` 放在同目录配置 API Key。

### 自己打包

```bash
pip install pyinstaller
pyinstaller smartquery.spec --clean --noconfirm
# 输出 → dist/SmartQuery.exe
```

---

## ⚙️ 配置

编辑 `.env`（或复制 `.env.example`）：

```env
# 数据库（默认 SQLite，不改也能用）
DATABASE_URL=sqlite:///./smartquery.db

# LLM API（必须填，否则不能生成 SQL）
LLM_API_KEY=sk-your-key-here
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

---

## 📁 项目结构

```
smartquery/
├── app/
│   ├── main.py          # FastAPI 入口，17 个 API 端点
│   ├── database.py      # 数据库引擎、Schema、SQL 执行、CSV 导入、动态切换
│   ├── llm.py           # LLM 调用封装（重试 + 超时，仅 user 角色消息）
│   ├── prompts.py       # NL2SQL / 修复 / 翻译的提示词模板
│   ├── models.py        # Pydantic 请求/响应模型
│   ├── utils.py         # SQL AST 安全校验 + 编码检测 + 表名校验
│   ├── config.py        # 环境变量加载
│   └── static/
│       └── index.html   # 完整前端（Stripe 毛玻璃 UI，52KB 单页应用）
├── desktop_app.py       # 桌面 EXE 启动器
├── smartquery.spec      # PyInstaller 打包配置
├── build_exe.bat        # 一键打包脚本
├── start.bat            # 一键启动脚本
├── init_db.py           # 初始化示例数据库
├── requirements.txt     # Python 依赖
├── .env.example         # 配置模板
└── README.md
```

---

## 🔌 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | Web 界面 |
| POST | `/generate-sql` | 仅生成 SQL（不执行） |
| POST | `/query` | 自然语言查询 + 执行 |
| POST | `/connect` | 切换数据库连接 |
| POST | `/disconnect` | 断开当前连接（恢复 SQLite） |
| POST | `/test-connection` | 测试数据库连接 |
| GET | `/connection-info` | 当前连接 + 表列表 |
| GET | `/table-info/{name}` | 表结构详情 |
| GET | `/tables` | 所有表名 |
| DELETE | `/table/{table_name}` | 删除数据表 |
| POST | `/import-csv` | 导入 CSV 文件 |
| POST | `/export` | 导出结果（csv/json/xlsx） |
| GET | `/history` | 本地查询历史 |

---

## 🧪 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| 数据库 | SQLAlchemy Core（SQLite / MySQL / PostgreSQL） |
| LLM | OpenAI 兼容 API（DeepSeek / GPT / 任意兼容接口） |
| SQL 解析 | sqlparse（AST 级别关键词分析） |
| 前端 | 原生 HTML + CSS + JS，无框架，零依赖 |
| 打包 | PyInstaller → 单文件 Windows EXE |

---

## 📄 License

MIT
