# API 地址配置说明

## 问题原因
手机端无法访问 `localhost`，因为 `localhost` 指向设备自身，手机访问 `localhost:8000` 会尝试连接手机本地的8000端口，而不是电脑的后端服务。

## 解决方案

### 方案1: 使用局域网IP (已配置 ✅)

当前配置：
```bash
# apps/web/.env.local
NEXT_PUBLIC_API_URL=http://192.168.3.78:8000
```

**适用场景**：
- ✅ 手机端测试
- ✅ 同一WiFi下的其他设备访问
- ✅ 局域网演示

**注意事项**：
- 手机和电脑必须在**同一WiFi网络**
- 如果IP变化，需要更新配置并重启前端服务
- 查看当前IP：`ipconfig getifaddr en0`

---

### 方案2: 本地开发 (电脑端测试)

如果要恢复电脑本地测试，修改配置：
```bash
# apps/web/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**适用场景**：
- ✅ 电脑浏览器测试
- ✅ 快速开发调试
- ❌ 不支持手机访问

---

## 快速切换脚本

创建切换脚本方便在不同场景间切换：

```bash
# 切换到局域网模式 (支持手机访问)
npm run dev:lan

# 切换到本地模式 (仅电脑访问)  
npm run dev:local
```

---

## 验证配置是否生效

### 1. 检查前端配置
```bash
cat apps/web/.env.local
# 应该显示: NEXT_PUBLIC_API_URL=http://192.168.3.78:8000
```

### 2. 检查后端服务
```bash
lsof -i:8000
# 应该看到: TCP *:irdmi (LISTEN)
# * 表示监听所有接口
```

### 3. 测试后端API
```bash
# 在电脑上测试
curl http://192.168.3.78:8000/health
# 应该返回: {"status":"healthy","db":"connected"}
```

### 4. 在手机浏览器测试
打开Safari/Chrome，访问：
```
http://192.168.3.78:3000
```

然后尝试：
- 登录功能
- 计算八字
- 查看衣橱

---

## 常见问题

### Q1: 手机仍然无法访问后端？

**检查清单**：
1. ✅ 确认手机和电脑在同一WiFi
2. ✅ 确认IP地址正确：`ipconfig getifaddr en0`
3. ✅ 关闭Mac防火墙
4. ✅ 重启前端服务：`lsof -ti:3000 | xargs kill -9 && npm run dev`
5. ✅ 检查后端是否运行：`lsof -i:8000`

### Q2: 电脑IP变了怎么办？

重新获取IP并更新配置：
```bash
# 1. 获取新IP
ipconfig getifaddr en0

# 2. 更新 .env.local
# 将 NEXT_PUBLIC_API_URL 改为新IP

# 3. 重启前端服务
lsof -ti:3000 | xargs kill -9
npm run dev
```

### Q3: 如何同时支持电脑localhost和手机访问？

修改 `api.ts` 动态判断：
```typescript
const getAPIBase = () => {
  if (typeof window !== 'undefined') {
    // 浏览器环境
    const hostname = window.location.hostname
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://localhost:8000'
    }
    // 其他情况（包括手机访问）使用当前host
    return `http://${hostname}:8000`
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
}

const API_BASE = getAPIBase()
```

---

## 生产环境配置

生产环境部署时，需要在对应平台配置环境变量：

### Vercel (前端)
```
NEXT_PUBLIC_API_URL=https://your-backend.zeabur.app
```

### Zeabur (后端)
```
# 后端不需要额外配置
# 确保CORS配置允许前端域名
```

---

## 当前状态

✅ **已配置**：局域网模式
- 前端地址: http://192.168.3.78:3000
- 后端地址: http://192.168.3.78:8000
- 支持手机访问: ✅
- 支持电脑访问: ✅

最后更新: 2026-04-11
