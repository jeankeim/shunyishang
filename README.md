# 顺衣尚 - 五行智能穿搭推荐系统

> 基于八字命理和五行理论的 AI 穿搭推荐平台 | 生产环境运行中

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue.svg" alt="Python 3.11">
  <img src="https://img.shields.io/badge/Next.js-14-black.svg" alt="Next.js 14">
  <img src="https://img.shields.io/badge/FastAPI-0.104-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/PostgreSQL-15-blue.svg" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/pgvector-0.5-orange.svg" alt="pgvector">
</p>

<p align="center">
  <b>结合传统命理学与现代 AI 技术的智能穿搭推荐平台</b>
</p>

---

## 📊 项目状态

**核心完成度**: 90%（Week 1-4 核心功能 + Week 5 海报生成 + Week 7 场景优化）  
**生产环境**: 🟢 运行中（Vercel + Zeabur + R2 + Upstash）  
**详细进度**: 查看 [PROGRESS.md](PROGRESS.md)

---

## ✨ 核心功能

- **八字命理分析**: 生辰八字计算五行强弱、喜用神
- **智能穿搭推荐**: 基于五行理论 + 语义搜索的个性化推荐
- **天气感知**: 实时天气数据 + 温度适配过滤
- **用户衣橱**: AI 自动打标 + 三种推荐模式
- **分享海报**: 3 种模板风格，一键生成高清海报

---

## 🏗️ 技术栈

### 后端
- **FastAPI**: 高性能 Python Web 框架
- **PostgreSQL + pgvector**: 关系型数据库 + 向量扩展
- **Redis (Upstash)**: 缓存与会话存储
- **LangGraph**: AI Agent 状态机框架
- **Cloudflare R2**: 图片对象存储

### 前端
- **Next.js 14**: React 全栈框架
- **TypeScript**: 类型安全
- **Tailwind CSS**: 原子化 CSS
- **Zustand**: 轻量级状态管理
- **Recharts**: 数据可视化（五行雷达图）

### AI/ML
- **千问 qwen-plus**: 大语言模型（阿里百炼）
- **BGE-M3**: 文本 Embedding 生成
- **向量搜索**: HNSW 索引 + 余弦相似度

---

## 📖 文档索引

| 文档 | 说明 |
|------|------|
| [PROGRESS.md](PROGRESS.md) | 📄 项目进度说明（功能清单/技术亮点/后续计划） |
| [project_spec.md](project_spec.md) | 技术规格说明（架构设计/目录规范/AI协作协议） |

---

## 🚀 快速开始

详见 [PROGRESS.md](PROGRESS.md#-快速开始)

---

<p align="center">
  Made with ❤️ and ☯️
</p>
