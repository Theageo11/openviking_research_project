# OpenViking Research

## OpenViking本身的特点（他github原文）
### 借助 OpenViking，开发者可以像管理本地文件一样构建智能体（Agent）的“大脑”：
client.initialize()
    ###     Virtual File System
                     │
 ┌──────────────┬──────────────┬──────────────┐
 memory         resources      agent
### 文件系统管理范式 → 解决碎片化问题：基于文件系统范式，对记忆、资源和技能进行统一的上下文管理。
无论是 memory / agent / resource
都用同一套接口。
  client.add_resource()
  client.query()
  client.read()
  client.ls()
### 分层上下文加载 → 降低 Token 消耗：采用 L0/L1/L2 三级架构，按需加载，显著节省成本。
### 目录递归检索 → 提升检索效果：支持原生的文件系统检索方式，将目录定位与语义搜索相结合，实现递归且精准的上下文获取。
    ### add_resource()
     │
     ├── parse resource
     ├── chunk （viking默认定义size 1000-1500 token）在高级接口中可以自定义。
     ├── generate L0 abstract ：限制检索范围（找到最相关的资源目录）作为 semantic map，指导向量检索
     ├── generate L1 overview
     ├── embedding （存入vectorDB）
     └── store
    ### L0 和 L1 在add_resource时通过LLM生成。每个文件都会配备L1 和 L0
     L0：抽象层，用于存储高阶语义信息。
     L1：概述层，用于存储低阶语义信息。
### 可视化检索轨迹 → 上下文可观测：支持目录检索轨迹的可视化，让用户清晰地观察问题根源，并指导检索逻辑的优化。
### 自动会话管理 → 上下文自我迭代：自动压缩对话中的内容、资源引用、工具调用等，提取长期记忆，使智能体越用越聪明。
agent：client.add_skill(
    uri="viking://agent/tools/python_executor",
    function=run_python
)

resources：client.add_resource(
    uri="viking://resources/rag_docs",
    file_path="./docs"
)

session：短期对话记忆
client.write(
    "viking://session/current_task",
    "Build RAG pipeline"
)

temp：储存临时推理数据。多步骤复杂任务时会自动生成plan.md

user: default是系统默认创建的一个用户
1. entities:用户相关实体 user/company/project
2. events：用户历史事件 user asked about rag
3. preferences：用户行为偏好 喜欢详细解释/喜欢代码片段。。

session.commit()
对话总结
↓
提取用户信息
↓
写入 user memory


### 总体流程：
query
 ↓
session context
 ↓
user memory
 ↓
resources retrieval
 ↓
agent skills
 ↓
generate answer

### 检索每一步做了啥。
触发query：
result = client.find(
    "viking://resources/my_project",
    query="Explain RAG architecture",
    top_k=5
)
1. 用户输入被转换成向量，用于和 vector store 的 chunk embedding 做相似度计算
2. Viking 会先在资源目录中匹配 L0 / L1 / L2，目的是 限制检索范围，找到最可能相关的文档或目录。
3. 定位目录后，find 会在该目录对应的 vector index 中搜索 chunk.
4. 返回score最高的top k结果。
5. 如果需要用到agent：User Query
    │
    ▼
client.find(query)
    │
    ├─> L0/L1/L2 semantic navigation → 定位资源
    │        │
    │        ▼
    │   vector retrieve → chunk_text
    │        │
    │        ▼
    │   rerank → top_k
    │        │
    │        ▼
    │   assemble context
    │
    └─> intent check → is agent call?
             │
             ├─> Yes → agent function auto invoked → result returned
             │
             └─> No → just return context text