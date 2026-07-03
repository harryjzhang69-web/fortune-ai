# 命由我造 · Fortune AI · 运营状态存档

> 最后更新：2026-07-03

## 当前状态

- **仅完成**：核心命理引擎（八字/易经/合盘，纯计算不依赖大模型）+ AI 对话层 + FastAPI 后端 + CLI demo
- **未部署**：没有公网访问链接，目前只能本地跑 `python cli.py` 或 `uvicorn server.app:app`
- **GitHub**：https://github.com/harryjzhang69-web/fortune-ai （已同步初始版本，源码 16 个文件，0.11MB，无大文件问题）
- **未接前端**：小程序前端（Taro）在路线图 M3，还没开始做

## 下次要做的事（按路线图）

- [ ] M3: 微信小程序前端
- [ ] M4: 每日一签 / 流年大运
- [ ] M5: 紫微斗数
- [ ] M6: 用户系统 + 订阅付费

## 换电脑须知

`.env`（LLM API Key）不在 GitHub 里，新电脑需照 `.env.example` 重新配置才能跑 CLI/API demo。目前没有云端部署，所以也没有"线上服务不受影响"这一层——这个产品目前完全依赖本地环境跑。
