# 📅 Week 2: 后端智能大脑
**状态**: ✅ 已完成 (Completed)  
**目标**: 搭建 FastAPI 后端，实现正式版八字+场景推荐逻辑，构建 LangGraph 状态机 Agent，暴露 SSE 流式 API。  
**关键产出**: `apps/api/main.py`, `packages/utils/bazi_calculator.py`, `packages/ai_agents/graph.py`, `POST /api/v1/recommend/stream`  
**完成日期**: 2026-03-27

---

## 📂 任务概览

| 任务 | 名称 | 状态 | 关键产出 |
|:---|:---|:---:|:---|
| 01_FASTAPI_SCAFFOLD | FastAPI 骨架 + 连接池 | ✅ 已完成 | `apps/api/main.py`, `core/config.py` |
| 02_UTILS_BAZI | 八字计算 + 五行映射 | ✅ 已完成 | `packages/utils/bazi_calculator.py` |
| 03_LANGGRAPH_AGENT | 4 节点状态机 Agent | ✅ 已完成 | `packages/ai_agents/graph.py`, `nodes.py` |
| 04_API_EXPOSE | SSE 流式接口 | ✅ 已完成 | `apps/api/routers/recommend.py` |

---

## 🎯 本周里程碑

- [x] FastAPI 骨架搭建完成，psycopg2 连接池配置正常
- [x] 正式版八字计算实现（cnlunar 库 + 自写五行统计）
- [x] LangGraph 4 节点状态机跑通（意图→检索→生成→格式化）
- [x] SSE 流式接口首字延迟 < 1.5s
- [x] 推荐结果引用真实 `item_code`，无幻觉

---

## 🔧 技术决策（已确认）

- **LLM**: 阿里百炼千问（`DASHSCOPE_API_KEY`，兼容 OpenAI SDK）
- **数据库层**: 保持 psycopg2 连接池，不引入 SQLAlchemy
- **八字**: 方案B —— `cnlunar` 库做四柱转换，自写五行统计 + 喜用神推断
- **意图推断**: 规则优先（关键词→五行映射表）+ LLM 兜底
- **搜索增强**: `final_score = 语义相似度 × 0.6 + 五行匹配度 × 0.4`
- **SSE 格式**: 3 段式结构化流 `analysis → items → token流`

---

## 📊 性能指标

| 指标 | 目标 | 实际 |
|:---|:---|:---|
| SSE 首字延迟 | < 1.5s | ~1.2s |
| 推荐响应时间 | < 3s | ~2.5s |
| 缓存命中率 | > 80% | ~85% |

---

> **🏆 第二周通关标志**: `scripts/test_agent_flow.py` 跑通全流程，SSE 接口稳定输出结构化推荐结果。
