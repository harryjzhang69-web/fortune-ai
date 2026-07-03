# 命由我造 · Fortune AI

一个**不只是算命，更是懂你的 AI 树洞**——基于易经、八字的传统文化体验型对话产品。

> ⚠️ 本项目内容为**传统文化娱乐性质**，不是科学预测，不构成任何决策建议。

---

## 核心差异化

市面上的命理小程序 90% 都长一个样：填一堆信息 → 输出一张静态报告。

我们做的不一样：

1. **你问什么，AI 结合你的盘 + 当下情景，像朋友一样跟你聊。**
2. **多套体系互证**——同一件事，八字 + 易经分别给出结论，让你看到"两条路指向同一个方向"的信任感。
3. **不卖恐惧、不制造焦虑**——温和、真诚、把劲儿引回到你自己身上，而不是"花 198 元消灾"。
4. **回答永远"先共情、再分析、最后给方向"**——这是产品最重要的人格设计。

---

## 项目结构

```
fortune_ai/
├── core/                  # 命理引擎（不依赖大模型，纯计算）
│   ├── bazi.py           # 八字排盘
│   ├── yijing.py         # 易经起卦
│   ├── compat.py         # 合盘分析
│   └── data/
│       └── gua64.json    # 64 卦数据
├── ai/                    # AI 对话层
│   ├── prompts.py        # System Prompt（命理师人设）
│   └── chat.py           # 大模型调用封装
├── server/
│   └── app.py            # FastAPI 后端（小程序对接）
├── cli.py                 # 命令行 demo（一键体验）
├── requirements.txt
└── .env.example
```

---

## 快速开始

### 1. 安装依赖

```bash
cd fortune_ai
pip install -r requirements.txt
```

### 2. 配置大模型 API

复制 `.env.example` 为 `.env`，填入你的 API Key：

```env
# 推荐 DeepSeek（国内+性价比高）
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-xxxxxxxx
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

也支持 OpenAI / 通义千问 / 任意 OpenAI 兼容 API。

### 3. 跑 CLI demo

```bash
python cli.py
```

体验流程：
1. 输入你的出生信息
2. （可选）输入对方的出生信息（合盘）
3. 自由提问，AI 结合你的盘回答

### 4. 跑后端 API（小程序对接用）

```bash
uvicorn server.app:app --reload --port 8000
```

接口：
- `POST /api/bazi` —— 八字排盘
- `POST /api/yijing/divine` —— 易经起卦
- `POST /api/compat` —— 合盘
- `POST /api/chat` —— AI 对话（带流式）

---

## 路线图

- [x] M1: 八字排盘 + 易经起卦 + 合盘 + AI 对话（CLI 跑通）
- [x] M2: FastAPI 后端
- [ ] M3: 微信小程序前端（Taro）
- [ ] M4: 每日一签 / 流年大运
- [ ] M5: 紫微斗数
- [ ] M6: 用户系统 + 订阅付费

---

## 合规 Tips（必读）

1. 输出永远带"传统文化娱乐性质"声明
2. 不用"算命/占卜/预测"作主打词，用"传统文化体验/易学参考"
3. 涉及生死、健康、法律 → 必须引导专业人士
4. 不接受未成年人

---

## License

MIT
