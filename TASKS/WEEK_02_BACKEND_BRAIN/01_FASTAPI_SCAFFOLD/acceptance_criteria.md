# 验收标准: FastAPI 骨架搭建 (01_FASTAPI_SCAFFOLD)

**任务**: FastAPI 骨架搭建  
**验收人**: _______  
**验收日期**: _______

---

## ✅ 验收清单

### 1. 目录结构验证

- [ ] `apps/api/` 目录结构完整（main.py / core / schemas / routers）
- [ ] 所有子目录含 `__init__.py`

**验证命令**：
```bash
find apps/api -type f -name "*.py" | sort
```

**预期输出包含**：
```
apps/api/__init__.py
apps/api/main.py
apps/api/core/__init__.py
apps/api/core/config.py
apps/api/core/database.py
apps/api/schemas/__init__.py
apps/api/schemas/request.py
apps/api/schemas/response.py
apps/api/routers/__init__.py
apps/api/routers/recommend.py
```

---

### 2. 依赖安装验证

- [ ] fastapi、uvicorn、pydantic-settings 已安装
- [ ] openai、cnlunar、langgraph 已安装

**验证命令**：
```bash
source .venv/bin/activate
python -c "import fastapi, uvicorn, pydantic_settings, openai, cnlunar, langgraph; print('ALL OK')"
```

**预期输出**：`ALL OK`

---

### 3. 服务启动验证

- [ ] uvicorn 启动无报错

**验证命令**：
```bash
source .venv/bin/activate
cd /Users/mingyang/Desktop/shunyishang
PYTHONPATH=. uvicorn apps.api.main:app --port 8000
```

**预期现象**：终端输出 `Application startup complete.`，无 ImportError 或 AttributeError

---

### 4. 健康检查接口验证

- [ ] `GET /health` 返回正确结构
- [ ] 数据库连接状态正确反映

**验证命令**：
```bash
# 确保 wuxing-db 容器运行
docker compose ps

# 测试健康检查
curl -s http://localhost:8000/health | python3 -m json.tool
```

**预期输出**：
```json
{
  "status": "ok",
  "db": "connected",
  "env": "development"
}
```

- [ ] 停止数据库后返回 503：
```bash
docker compose stop db
curl -o /dev/null -w "%{http_code}" http://localhost:8000/health
# 预期：503
docker compose start db
```

---

### 5. Swagger 文档验证

- [ ] `/docs` 可正常访问，显示 API 文档
- [ ] `/api/v1/recommend/stream` 路由出现在文档中（即使返回 501）

**验证命令**：
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs
# 预期：200
```

---

### 6. CORS 配置验证

- [ ] 跨域请求不报错

**验证命令**：
```bash
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS \
     -s -I http://localhost:8000/api/v1/recommend/stream | grep -i access-control
```

**预期输出包含**：`access-control-allow-origin: *`

---

### 7. Pydantic Schema 验证

- [ ] `RecommendRequest` 包含 `query`、`scene`、`bazi`、`top_k` 字段
- [ ] `BaziInput` 包含 `birth_year`、`birth_month`、`birth_day`、`birth_hour`、`gender` 字段
- [ ] `bazi` 字段为可选（`None` 时不报错）

**验证命令**：
```bash
python3 -c "
from apps.api.schemas.request import RecommendRequest
# 不带八字
r1 = RecommendRequest(query='明天约会穿什么')
print('无八字:', r1.model_dump())
# 带八字
from apps.api.schemas.request import BaziInput
r2 = RecommendRequest(
    query='面试穿什么',
    bazi=BaziInput(birth_year=1995, birth_month=6, birth_day=15, birth_hour=10, gender='男')
)
print('有八字:', r2.model_dump())
print('Schema OK')
"
```

---

## 📊 验收结果

| 检查项 | 状态 | 备注 |
|:---|:---:|:---|
| 目录结构完整 | ⬜ | |
| 依赖全部安装 | ⬜ | |
| 服务正常启动 | ⬜ | |
| /health 返回正确 | ⬜ | |
| DB 断开返回 503 | ⬜ | |
| /docs 可访问 | ⬜ | |
| CORS 配置生效 | ⬜ | |
| Schema 验证通过 | ⬜ | |

---

## ✍️ 验收签字

**验收结论**: ⬜ 通过 / ⬜ 不通过

**问题记录**:
```
(如有问题请在此记录)
```

**签字**: ________________ **日期**: ________________
