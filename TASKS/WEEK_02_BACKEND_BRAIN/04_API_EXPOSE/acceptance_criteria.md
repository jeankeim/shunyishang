# 验收标准: SSE 流式 API 接口 (04_API_EXPOSE)

**任务**: SSE 流式推荐 API  
**验收人**: _______  
**验收日期**: _______

---

## ✅ 验收清单

### 1. 接口存在性验证

- [ ] `POST /api/v1/recommend/stream` 路由已实现（非 501 占位）

**验证命令**：
```bash
# 启动服务（另开终端）
PYTHONPATH=. uvicorn apps.api.main:app --port 8000

# 验证路由注册
curl -s http://localhost:8000/openapi.json | python3 -c "
import json, sys
spec = json.load(sys.stdin)
paths = list(spec['paths'].keys())
print('注册路由:', paths)
assert '/api/v1/recommend/stream' in paths, '路由未注册'
print('路由验证 OK')
"
```

---

### 2. SSE 基础格式验证

- [ ] 响应 Content-Type 为 `text/event-stream`
- [ ] 每条消息格式为 `data: {JSON}\n\n`

**验证命令**：
```bash
curl -s -i -X POST http://localhost:8000/api/v1/recommend/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"query": "明天面试穿什么"}' | head -30
```

**预期响应头包含**：
```
content-type: text/event-stream
cache-control: no-cache
```

**预期响应体格式**：
```
data: {"type": "analysis", "data": {...}}

data: {"type": "items", "data": [...]}

data: {"type": "token", "data": "根"}

data: {"type": "token", "data": "据"}

...

data: {"type": "done", "data": null}
```

---

### 3. 3段式结构完整性验证

- [ ] 收到 `analysis` 消息
- [ ] 收到 `items` 消息
- [ ] 收到至少 10 条 `token` 消息（即推荐理由有内容）
- [ ] 最后一条为 `done` 消息

**验证命令**：
```bash
PYTHONPATH=. python3 -c "
import requests, json

url = 'http://localhost:8000/api/v1/recommend/stream'
payload = {'query': '明天要去约会，想穿得浪漫一点'}

types_received = []
items_count = 0
token_count = 0

with requests.post(url, json=payload, stream=True, 
                   headers={'Accept': 'text/event-stream'}) as r:
    for line in r.iter_lines():
        if line and line.startswith(b'data: '):
            msg = json.loads(line[6:])
            types_received.append(msg['type'])
            if msg['type'] == 'items':
                items_count = len(msg['data'])
            if msg['type'] == 'token':
                token_count += 1
            if msg['type'] == 'done':
                break

print('收到消息类型:', set(types_received))
print('推荐物品数:', items_count)
print('token数量:', token_count)

assert 'analysis' in types_received, '缺少 analysis 消息'
assert 'items' in types_received, '缺少 items 消息'
assert token_count >= 10, f'token 数量太少: {token_count}'
assert types_received[-1] == 'done', '最后消息应为 done'
print('3段式结构验证 OK')
"
```

---

### 4. 中文编码验证

- [ ] SSE 消息中的中文正常显示，无 `\uXXXX` 转义

**验证命令**：
```bash
curl -s -X POST http://localhost:8000/api/v1/recommend/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "面试"}' | head -5 | grep -v "\\\\u"

# 如果 grep 有输出说明存在转义，不应有输出
echo "如果无输出则编码正确"
```

**另一种验证**：
```bash
PYTHONPATH=. python3 -c "
import requests, json
with requests.post('http://localhost:8000/api/v1/recommend/stream', 
                   json={'query': '约会穿搭'}, stream=True,
                   headers={'Accept': 'text/event-stream'}) as r:
    for line in r.iter_lines():
        if line and b'analysis' in line:
            raw = line.decode('utf-8')
            assert '\\\\u' not in raw, '存在 Unicode 转义，编码错误'
            print('编码检查:', raw[:80])
            break
print('中文编码验证 OK')
"
```

---

### 5. 含八字的 SSE 请求验证

- [ ] 传入八字信息时，`analysis` 消息包含八字推理

**验证命令**：
```bash
PYTHONPATH=. python3 -c "
import requests, json

payload = {
    'query': '参加朋友婚礼穿什么',
    'scene': '派对',
    'bazi': {
        'birth_year': 1995,
        'birth_month': 3,
        'birth_day': 20,
        'birth_hour': 8,
        'gender': '女'
    }
}

with requests.post('http://localhost:8000/api/v1/recommend/stream',
                   json=payload, stream=True,
                   headers={'Accept': 'text/event-stream'}) as r:
    for line in r.iter_lines():
        if line and b'analysis' in line:
            msg = json.loads(line[6:])
            analysis = msg['data']
            print('分析结果:', json.dumps(analysis, ensure_ascii=False, indent=2))
            assert analysis.get('bazi_reasoning'), '八字推理不应为空'
            print('含八字验证 OK')
            break
"
```

---

### 6. 首字延迟验证

- [ ] 从发送请求到收到第 1 条 `analysis` 消息，耗时 < 1.5 秒

**验证命令**：
```bash
PYTHONPATH=. python3 -c "
import requests, time, json

start = time.time()
with requests.post('http://localhost:8000/api/v1/recommend/stream',
                   json={'query': '今天穿什么好'},
                   stream=True,
                   headers={'Accept': 'text/event-stream'}) as r:
    for line in r.iter_lines():
        if line and b'analysis' in line:
            first_latency = time.time() - start
            print(f'首字延迟: {first_latency:.3f}s')
            assert first_latency < 1.5, f'首字延迟过高: {first_latency:.3f}s'
            print('延迟验证 OK')
            break
"
```

---

### 7. 错误处理验证

- [ ] 无效请求体返回 422
- [ ] 数据库断开时 SSE 返回 error 消息而非崩溃

**验证命令**：
```bash
# 无效请求体
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/api/v1/recommend/stream \
  -H "Content-Type: application/json" \
  -d '{"invalid": "body"}'
# 预期：422
```

---

### 8. 日志中间件验证

- [ ] 服务器终端输出请求日志

**验证方式**：发送请求后，查看 uvicorn 运行终端是否输出类似：
```
POST /api/v1/recommend/stream → 200 (3.421s)
```

---

## 📊 验收结果

| 检查项 | 状态 | 备注 |
|:---|:---:|:---|
| 路由注册成功 | ⬜ | |
| Content-Type 正确 | ⬜ | |
| 3段式结构完整 | ⬜ | |
| 中文编码正常 | ⬜ | |
| 含八字请求正常 | ⬜ | |
| 首字延迟 < 1.5s | ⬜ | |
| 错误处理不崩溃 | ⬜ | |
| 请求日志输出 | ⬜ | |

---

## ✍️ 验收签字

**验收结论**: ⬜ 通过 / ⬜ 不通过

**问题记录**:
```
(如有问题请在此记录)
```

**签字**: ________________ **日期**: ________________
