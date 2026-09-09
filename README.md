# AI 电商运营助手

> 求职作品集项目：展示「多模态视觉理解 + LLM 工作流编排 + 电商运营内容生成」的完整链路。

## 1. 项目能做什么

上传一张商品图片，系统自动生成一份可导出的《AI 电商商品运营报告》：

- 商品智能分析（类别、外观、风格、场景）
- 用户画像卡
- 三平台标题：淘宝 / 京东 / 小红书
- 五点卖点
- 商品详情页文案（痛点 → 方案 → 功能 → 场景 → 购买理由）
- 抖音/小红书短视频脚本
- AI 营销图片 Prompt 方案（按「主体 / 场景道具 / 光线影调 / 构图机位 / 风格质感」五要素拆解，可直接复制到 即梦 / Midjourney / SD 出图）
- 商品主体透明抠图（rembg，可一键复制透明 PNG）

**核心设计原则**：
- **演示优先**：内置 3 个示例商品 + Mock 引擎，无 API Key 也能完整跑通。
- **诚实边界**：材质、品牌、价格、竞争优势等不可见属性必须来自用户输入，视觉模型只做可见属性推断，并在报告里标注来源。
- **分析用原图，抠图只做展示**：视觉分析与主体抠图是两条独立链路，抠图失败自动降级为原图。

## 2. 技术栈

| 端 | 技术 |
|---|---|
| 前端 | React 18 + TypeScript + Vite |
| 后端 | Python 3.11 + FastAPI |
| AI 模型 | OpenAI 兼容接口（支持 GPT-4o、DeepSeek、智谱、通义、Moonshot 等）+ Mock 兜底 |
| 视觉分析 | 多模态 LLM（image_url 方式） |
| 主体抠图 | rembg（可降级，可替换为 SAM/U²-Net） |
| 缓存 | SQLite + 图片 hash |
| 部署 | Docker Compose / Uvicorn |

## 3. 目录结构

```
AI-commerce-assistant/
├── backend/              FastAPI 后端
│   ├── app/
│   │   ├── api.py        API 路由（上传/分析/进度/导出/静态资源）
│   │   ├── config.py     配置与目录
│   │   ├── db.py         SQLite 缓存/任务/上传记录
│   │   ├── task_state.py 运行时任务进度状态
│   │   ├── llm/          文本生成器（画像/标题/卖点/详情/脚本/营销图）
│   │   ├── providers/    统一模型接口：Mock / OpenAI 兼容
│   │   ├── prompts/      Prompt 模板（.txt，占位符渲染）
│   │   ├── schemas.py    结构化输出 Schema
│   │   ├── segmentation/ 主体抠图服务（rembg + 降级）
│   │   ├── services/     业务编排流水线 + 示例目录 + Markdown 导出
│   │   └── vision/       视觉理解模块
│   ├── requirements.txt            核心依赖
│   └── requirements-segmentation.txt  可选抠图依赖
├── frontend/             React + TS 前端
│   └── src/
│       ├── pages/        Home / Processing / ReportPage
│       ├── api.ts        API 客户端
│       └── types.ts      类型定义
├── examples/             内置示例
│   ├── images/           示例商品图（程序绘制示意图）
│   └── reports/          预写 Mock 报告
├── scripts/              辅助脚本（生成示例图、冒烟测试）
├── .env                  运行时配置（已默认 Mock 模式）
├── .env.example          配置模板
├── docker-compose.yml
└── Dockerfile
```

## 4. 快速开始

### 方式 0：Windows 一键启动（最快）

在项目根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_windows.ps1
```

脚本会自动：创建 Python 虚拟环境并安装依赖（首次）→ 启动后端 → 自动打开
http://localhost:8000。再次启动会复用已有环境并自动检测端口。

> 提示：若页面提示「无法连接后端服务」，就是后端没启动——运行上面这一句即可。
> 若改了前端代码，先执行 `cd frontend; npm run build` 再启动。

### 方式 A：本地开发

```powershell
# 1. 后端
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# 可选：透明抠图（rembg，首次使用自动下载 u2net 权重约 170MB 到 models/）
.\.venv\Scripts\python.exe -m pip install -r requirements-segmentation.txt
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000

# 2. 前端（另开终端）
cd frontend
npm install
npm run dev
```

然后打开 http://localhost:5173，点击下方任意「内置示例」即可完整跑通。

### 方式 B：单后端运行（前端已构建）

```powershell
cd frontend
npm install
npm run build

cd ../backend
.\.venv\Scripts\uvicorn.exe app.main:app --port 8000
```

打开 http://localhost:8000。

### 方式 C：Docker Compose（一条命令）

```powershell
docker compose up --build -d
```

打开 http://localhost:8000。

> 首次构建会包含 rembg，体积较大；也可在 `docker-compose.yml` 中注释掉 `requirements-segmentation.txt` 以跳过抠图。

## 5. 环境变量说明

复制 `.env.example` 为 `.env` 后按需修改：

```env
# auto|mock|openai_compatible，默认 mock（无 Key 可演示）
AI_PROVIDER=mock

# 使用真实模型时填写
OPENAI_API_KEY=your_key
OPENAI_BASE_URL=https://api.openai.com/v1

VISION_MODEL=gpt-4o-mini
TEXT_MODEL=gpt-4o-mini
MAX_IMAGE_MB=8

# 抠图（可选）：不配置则默认将 rembg 模型缓存在项目根 models/
# U2NET_HOME=models
# SEGMENT_MODEL=u2net
```

**OpenAI 兼容端点**：任何支持 `/chat/completions` 的厂商都可以接入，例如：
- OpenAI
- DeepSeek
- 智谱 GLM
- 通义千问
- Moonshot

## 6. Mock 模式 vs 真实模型

| 模式 | 是否需要 Key | 上传自有图片 | 说明 |
|---|---|---|---|
| Mock | 否 | 支持「演示报告」 | 点击内置示例秒出结果；上传图片时按填写的商品名称/描述匹配最接近的内置模板（保温杯 / 咖啡杯 / 耳机）生成演示报告，页面与字段结构与真实一致 |
| 真实模型 | 是 | 完整视觉分析 | 配置 Key 后由多模态模型真正识别图片内容，输出结构化报告 |

在 Mock 模式下**不会分析图片像素**，报告基于你填写的商品信息 + 内置模板生成（报告顶栏标注“演示模式”），不会谎称读懂了图片。配置 `OPENAI_API_KEY` 后即可上传任意商品图获得真实分析。

## 7. 关于示例商品图

`examples/images/` 下的三张商品图是本项目为了「无网络环境也能离线演示」而用 PIL 程序绘制的**示意图**，不是真实产品照片。它们对应 `examples/reports/` 中的专家预写 Mock 报告，足以支撑完整 UI 流程展示。真实场景中请上传自己的商品照片。

## 8. 报告导出

报告页支持：
- **导出 Markdown**：点击「导出 Markdown」下载 `.md` 文件。
- **打印 / 保存 PDF**：点击「打印 / 存 PDF」使用浏览器打印到 PDF。

## 9. 测试

```powershell
cd backend
.\.venv\Scripts\python.exe ..\scripts\smoke_api.py
```

该脚本会验证：示例分析、报告字段完整性、Markdown 导出、缓存命中、Mock 边界拒绝。

## 10. 后续优化方向

- 报告 → 正式 PDF 排版导出
- 接入真实 AIGC 出图（SD / 即梦 / 可灵）
- 平台规则版本化知识库
- 批量多图分析
- 抠图升级 SAM2

---

作者：AI 电商运营助手项目
