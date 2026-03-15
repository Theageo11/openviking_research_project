# OpenViking Research Project

基于 [OpenViking](https://openviking.dev) 构建的代码片段检索与 AI Agent 长时记忆服务，提供 Web UI 和 REST API，让你像查文件一样查询自己代码库里的任何内容。

---

## 功能

- **资源注册**：把本地目录上传到 OpenViking，建立可检索的向量索引
- **语义查询**：用自然语言（中英文均可）检索代码片段，自动定位相关函数/逻辑块
- **会话记忆**：查询历史自动提炼为长时记忆，下次查询时提供上下文
- **Agent 上传**：支持上传自定义 Agent（JSON/文本），扩展检索能力
- **Web UI**：内置前端，开箱即用，无需额外部署

---

## 项目结构

```
viking/
├── app/
│   ├── main.py           # FastAPI 入口，路由定义
│   ├── viking_service.py # 核心服务逻辑（资源、会话、查询）
│   ├── snippet.py        # 从检索结果中提取最相关代码片段
│   └── models.py         # Pydantic 请求/响应模型
├── frontend/
│   └── index.html        # 单文件 Web UI
├── requirements.txt
└── ov.conf.example       # 配置文件模板（不含密钥）
```

---

## 快速开始

### 1. 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置

复制配置模板并填写你的 LLM / Embedding 服务信息：

```bash
cp ov.conf.example ov.conf
# 编辑 ov.conf，填入 api_key、model、api_base 等
```

`ov.conf` 支持的 provider：`volcengine`、`openai`、`azure` 等，详见 [OpenViking 文档](https://openviking.dev/docs/guides/configuration)。

### 3. 启动服务

```bash
OPENVIKING_CONFIG_FILE=./ov.conf uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

打开浏览器访问 [http://localhost:8080](http://localhost:8080)。

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/health` | 健康检查 |
| POST | `/api/resources/register` | 注册本地目录 |
| GET  | `/api/resources` | 列出已注册目录 |
| POST | `/api/sessions` | 创建会话 |
| POST | `/api/sessions/{id}/commit` | 提交会话记忆 |
| POST | `/api/agents/upload` | 上传 Agent 文件 |
| POST | `/api/query` | 语义查询，返回代码片段 |

### 查询示例

```bash
curl -X POST http://localhost:8080/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "怎么创建会话", "top_k": 5}'
```

---

## 配置模板

`ov.conf` 格式（JSON）：

```json
{
  "storage": {
    "workspace": "/path/to/your/workspace"
  },
  "vlm": {
    "provider": "openai",
    "api_key": "YOUR_API_KEY",
    "model": "gpt-4o",
    "api_base": "https://api.openai.com/v1"
  },
  "embedding": {
    "dense": {
      "provider": "openai",
      "api_key": "YOUR_API_KEY",
      "model": "text-embedding-3-large",
      "api_base": "https://api.openai.com/v1",
      "dimension": 1024
    }
  }
}
```

---

## 依赖

- Python 3.10+
- [openviking](https://pypi.org/project/openviking/)
- FastAPI + uvicorn
- python-multipart
