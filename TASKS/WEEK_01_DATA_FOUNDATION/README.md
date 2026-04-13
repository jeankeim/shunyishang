# 📅 Week 1: 数据基石与向量库构建
**状态**: ✅ 已完成 (Completed)  
**目标**: 搭建支持 `pgvector` 的数据库环境，完成 100 条种子数据的清洗、向量化导入，并验证语义搜索的有效性。  
**关键产出**: `docker-compose.yml`, `init_db.sql`, `import_seed.py`, `test_semantic_search.py`
**完成日期**: 2026-03-20

---

## 📂 任务概览

| 任务 | 名称 | 状态 | 关键产出 |
|:---|:---|:---:|:---|
| 01_DB_SETUP | 数据库环境搭建 | ⏳ 待开始 | `docker-compose.yml`, `init_db.sql` |
| 02_ETL_PIPELINE | ETL 流水线 | ⏳ 待开始 | `import_seed.py` |
| 03_VECTOR_TEST | 语义搜索验证 | ⏳ 待开始 | `test_semantic_search.py` |

---

## 🎯 本周里程碑

- [ ] Docker 容器正常运行，pgvector 扩展已激活
- [ ] 数据库表结构创建完成，HNSW 索引就绪
- [ ] 100 条种子数据成功导入，向量非空
- [ ] 三个语义搜索场景验证通过

---

## 🚀 如何开始？

**给 AI 助手的启动 Prompt**:
```
我已准备好开始 Week 1 的开发。请首先读取 TASKS/WEEK_01_DATA_FOUNDATION/01_DB_SETUP/task_instruction.md，生成所需的 docker-compose.yml 和 scripts/init_db.sql 文件。生成完成后，请告诉我如何验证（参考 acceptance_criteria.md）。
```

一旦第一步验证通过，继续发送：
```
第一步验证通过。现在请执行 Week 1 Task 2，读取 02_ETL_PIPELINE/task_instruction.md 生成 ETL 脚本。
```

---

## 📊 进度追踪

| 日期 | 完成任务 | 备注 |
|:---|:---|:---|
| - | - | - |

---

> **🏆 第一周通关标志**: 三个语义搜索场景的搜索结果均符合人类直觉，证明向量库已准备好支持后续的 Agent 推荐。
