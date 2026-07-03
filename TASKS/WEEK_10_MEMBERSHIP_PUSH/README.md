# Week 10: VIP会员体系与推送通知

**周期**: Week 10  
**主题**: 商业化基础设施与用户触达能力  
**状态**: ✅ 已完成（2026-07-01）  
**预估工时**: 40小时

---

## 🎯 本周目标

1. **VIP会员体系**: 建立三级会员体系，实现付费转化能力
2. **支付集成**: 集成微信支付和支付宝支付
3. **推送通知**: 实现每日运势推送能力
4. **权限控制**: 完善功能权限中间件

---

## 📋 任务清单

| 序号 | 任务 | 优先级 | 预估工时 | 依赖 | 状态 |
|:---:|------|:---:|:---:|:---:|:---|
| 01 | [会员数据库设计](./01_MEMBERSHIP_DB/) | 🔴 高 | 2h | - | ✅ 已完成 |
| 02 | [会员订阅API](./02_SUBSCRIPTION_API/) | 🔴 高 | 4h | 01 | ✅ 已完成 |
| 03 | [微信支付集成](./03_WECHAT_PAY/) | 🔴 高 | 5h | 02 | ✅ 已完成（Mock 实现） |
| 04 | [支付宝集成](./04_ALIPAY/) | 🟡 中 | 3h | 03 | ✅ 已完成（Mock 实现） |
| 05 | [权限控制中间件](./05_PERMISSION/) | 🔴 高 | 4h | 02 | ✅ 已完成 |
| 06 | [会员中心页面](./06_MEMBERSHIP_FRONTEND/) | 🔴 高 | 5h | 02 | ✅ 已完成 |
| 07 | [推送通知系统](./07_PUSH_SYSTEM/) | 🟡 中 | 6h | - | ✅ 已完成 |
| 08 | [每日运势推送任务](./08_FORTUNE_PUSH/) | 🟡 中 | 4h | 07 | ✅ 已完成 |
| 09 | [支付回调处理](./09_PAYMENT_CALLBACK/) | 🔴 高 | 4h | 03 | ✅ 已完成（Mock 实现） |
| 10 | [会员状态同步](./10_STATUS_SYNC/) | 🟡 中 | 3h | 02 | ✅ 已完成 |

> **注**: Task 03/04/09 的微信支付、支付宝支付及回调处理为 Mock 实现，模拟完整支付流程但未对接真实支付网关。真实对接需具备微信商户号和支付宝商户资质后替换 Mock 逻辑。

---

## 🗄️ 数据模型设计

### 会员订阅表 (subscriptions)

```sql
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    plan_type VARCHAR(20) NOT NULL,    -- free/monthly/yearly
    status VARCHAR(20) NOT NULL,       -- active/expired/cancelled/pending
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    auto_renew BOOLEAN DEFAULT TRUE,
    original_plan VARCHAR(20),          -- 原始套餐（升级前）
    upgrade_from_id INTEGER REFERENCES subscriptions(id),
    
    -- 支付信息
    payment_method VARCHAR(20),         -- wechat/alipay
    last_payment_id INTEGER,
    
    -- 统计信息
    total_payments INTEGER DEFAULT 0,
    total_amount DECIMAL(10,2) DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT valid_date_range CHECK (end_date IS NULL OR end_date > start_date)
);

CREATE INDEX idx_subscription_user ON subscriptions(user_id);
CREATE INDEX idx_subscription_status ON subscriptions(status, end_date);
CREATE INDEX idx_subscription_end ON subscriptions(end_date) WHERE status = 'active';
```

### 支付记录表 (payment_records)

```sql
CREATE TABLE payment_records (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    subscription_id INTEGER REFERENCES subscriptions(id),
    
    -- 支付类型
    payment_type VARCHAR(20) NOT NULL,  -- new/renew/upgrade/refund
    
    -- 金额信息
    amount DECIMAL(10,2) NOT NULL,
    original_amount DECIMAL(10,2),      -- 原价
    discount_amount DECIMAL(10,2),      -- 优惠金额
    plan_type VARCHAR(20) NOT NULL,
    plan_duration INTEGER,              -- 购买月数
    
    -- 支付方式
    payment_method VARCHAR(20) NOT NULL,-- wechat/alipay
    
    -- 第三方信息
    transaction_id VARCHAR(100),        -- 我方订单号
    out_trade_no VARCHAR(100),          -- 第三方订单号
    
    -- 状态
    status VARCHAR(20) NOT NULL,        -- pending/success/failed/refunded
    
    -- 时间
    paid_at TIMESTAMP,
    refunded_at TIMESTAMP,
    expired_at TIMESTAMP,               -- 订单过期时间
    
    -- 回调信息
    callback_raw JSONB,                 -- 原始回调数据
    
    -- 元数据
    ip_address VARCHAR(50),
    user_agent TEXT,
    device_info JSONB,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_payment_user ON payment_records(user_id);
CREATE INDEX idx_payment_transaction ON payment_records(transaction_id);
CREATE INDEX idx_payment_out_trade ON payment_records(out_trade_no);
CREATE INDEX idx_payment_status ON payment_records(status, created_at);
```

### 推送记录表 (push_notifications)

```sql
CREATE TABLE push_notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    
    -- 推送类型
    push_type VARCHAR(50) NOT NULL,     -- daily_fortune/weather/alert
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    
    -- 推送渠道
    channel VARCHAR(20) NOT NULL,       -- webpush/sms/email
    
    -- 目标信息
    target_url TEXT,                    -- 点击跳转URL
    target_data JSONB,                  -- 额外数据
    
    -- 状态
    status VARCHAR(20) NOT NULL,        -- pending/sent/failed
    sent_at TIMESTAMP,
    read_at TIMESTAMP,
    
    -- 错误信息
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_push_user ON push_notifications(user_id);
CREATE INDEX idx_push_status ON push_notifications(status, created_at);
CREATE INDEX idx_push_type ON push_notifications(push_type, created_at);
```

### 用户推送设置表 (user_push_settings)

```sql
CREATE TABLE user_push_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    
    -- 推送开关
    daily_fortune_enabled BOOLEAN DEFAULT TRUE,
    weather_alert_enabled BOOLEAN DEFAULT TRUE,
    important_day_enabled BOOLEAN DEFAULT TRUE,
    wardrobe_reminder_enabled BOOLEAN DEFAULT TRUE,
    marketing_enabled BOOLEAN DEFAULT FALSE,
    
    -- 推送时间
    daily_fortune_time TIME DEFAULT '08:00:00',  -- 运势推送时间
    
    -- 推送渠道
    webpush_enabled BOOLEAN DEFAULT TRUE,
    sms_enabled BOOLEAN DEFAULT FALSE,
    email_enabled BOOLEAN DEFAULT FALSE,
    
    -- 设备token
    webpush_subscription JSONB,         -- Web Push订阅信息
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(user_id)
);
```

---

## 💰 会员体系设计

### 会员等级与权益

| 权益 | 免费用户 | 月度会员 ¥19.9 | 年度会员 ¥168 |
|------|:-------:|:-------------:|:------------:|
| **基础推荐** | 5次/日 | 无限 | 无限 |
| **衣橱容量** | 20件 | 200件 | 无限 |
| **AI穿搭点评** | 基础版 | 详细版 | 专家版 |
| **每日运势** | 基础运势 | 详细运势 | 详细运势+指导 |
| **穿搭日记** | ✅ | ✅ | ✅ |
| **海报生成** | 3次/月 | 无限 | 无限+专属模板 |
| **大运流年分析** | ❌ | ❌ | ✅ |
| **五行能量报告** | ❌ | ✅ | ✅ |
| **专属客服** | ❌ | ✅ | VIP专属 |
| **线下活动** | ❌ | ❌ | ✅优先报名 |
| **品牌折扣** | ❌ | 5% | 10% |

### 定价策略

```javascript
const PRICING_PLANS = {
  free: {
    name: '免费用户',
    price: 0,
    features: ['basic_recommend', 'limited_wardrobe', 'basic_fortune']
  },
  monthly: {
    name: '月度会员',
    price: 19.9,
    originalPrice: 29.9,
    discount: '6.7折',
    features: ['unlimited_recommend', 'wardrobe_200', 'detailed_fortune', 'priority_support']
  },
  yearly: {
    name: '年度会员',
    price: 168,
    originalPrice: 238.8,
    discount: '¥14/月',
    savings: 70.8,
    features: ['all_monthly', 'unlimited_wardrobe', 'dayun_analysis', 'vip_support', 'offline_events']
  }
};
```

---

## 🔌 API 设计

### 会员订阅 API

```
# 会员信息
GET    /api/v2/membership/status        # 获取会员状态
GET    /api/v2/membership/plans         # 获取套餐列表
GET    /api/v2/membership/benefits      # 获取权益详情

# 订阅操作
POST   /api/v2/membership/subscribe     # 创建订阅（发起支付）
POST   /api/v2/membership/cancel        # 取消订阅
POST   /api/v2/membership/upgrade       # 升级套餐
POST   /api/v2/membership/renew         # 续费

# 支付相关
POST   /api/v2/payment/create           # 创建支付订单
POST   /api/v2/payment/wechat/callback  # 微信支付回调
POST   /api/v2/payment/alipay/callback  # 支付宝回调
GET    /api/v2/payment/status/:orderId  # 查询支付状态
POST   /api/v2/payment/refund           # 申请退款
```

### 推送通知 API

```
# 推送设置
GET    /api/v2/push/settings            # 获取推送设置
PUT    /api/v2/push/settings            # 更新推送设置

# Web Push
POST   /api/v2/push/webpush/subscribe   # 订阅Web Push
POST   /api/v2/push/webpush/unsubscribe # 取消订阅

# 管理接口（内部）
POST   /api/internal/push/send          # 发送推送
POST   /api/internal/push/batch         # 批量推送
```

### 请求/响应示例

**创建订阅请求**:
```json
{
  "plan_type": "yearly",
  "payment_method": "wechat",
  "auto_renew": true
}
```

**创建订阅响应**:
```json
{
  "code": 0,
  "data": {
    "order_id": "ORD20260417001",
    "transaction_id": "TXN20260417001",
    "amount": 168.00,
    "original_amount": 238.80,
    "discount_amount": 70.80,
    "plan_type": "yearly",
    "plan_duration": 12,
    "payment_method": "wechat",
    "payment_params": {
      "appId": "wx1234567890",
      "timeStamp": "1713340800",
      "nonceStr": "abc123",
      "package": "prepay_id=wx123",
      "signType": "RSA",
      "paySign": "签名字符串"
    },
    "expire_at": "2026-04-17T10:00:00Z"
  }
}
```

---

## 🎨 前端页面设计

### 1. 会员中心页 (/membership)

```
┌─────────────────────────────────────────┐
│ ← 会员中心                              │
├─────────────────────────────────────────┤
│                                         │
│ ┌─────────────────────────────────────┐│
│ │ 👤 当前会员：免费用户                ││
│ │                                     ││
│ │ 已使用权益：                         ││
│ │ • 今日推荐：3/5次                    ││
│ │ • 衣橱容量：8/20件                   ││
│ │ • 本月海报：1/3次                    ││
│ │                                     ││
│ │ 📅 会员到期：-                       ││
│ └─────────────────────────────────────┘│
│                                         │
│ ✨ 升级会员享受更多权益                 │
│                                         │
│ ┌─────────────────────────────────────┐│
│ │ 💎 月度会员           ¥19.9/月      ││
│ │                                     ││
│ │ ✓ 无限穿搭推荐                       ││
│ │ ✓ 200件衣橱容量                      ││
│ │ ✓ 详细每日运势                       ││
│ │ ✓ 无限海报生成                       ││
│ │                                     ││
│ │        [立即开通]                    ││
│ └─────────────────────────────────────┘│
│                                         │
│ ┌─────────────────────────────────────┐│
│ │ 👑 年度会员           ¥168/年       ││
│ │          🔥 ¥14/月 省¥70            ││
│ │                                     ││
│ │ ✓ 包含月度会员所有权益               ││
│ │ ✓ 无限衣橱容量                       ││
│ │ ✓ 大运流年分析                       ││
│ │ ✓ VIP专属客服                        ││
│ │ ✓ 线下活动优先报名                   ││
│ │                                     ││
│ │        [立即开通] 推荐               ││
│ └─────────────────────────────────────┘│
│                                         │
├─────────────────────────────────────────┤
│  [查看完整权益对比]                      │
└─────────────────────────────────────────┘
```

### 2. 支付页面 (/payment)

```
┌─────────────────────────────────────────┐
│ ← 确认订单                              │
├─────────────────────────────────────────┤
│                                         │
│ 📦 订单详情                             │
│ ┌─────────────────────────────────────┐│
│ │ 年度会员                             ││
│ │ 有效期：12个月                       ││
│ │                                     ││
│ │ 原价              ¥238.80           ││
│ │ 优惠              -¥70.80           ││
│ │ ──────────────────────────          ││
│ │ 实付              ¥168.00           ││
│ └─────────────────────────────────────┘│
│                                         │
│ 💳 支付方式                             │
│ ┌─────────────────────────────────────┐│
│ │ ◉ 微信支付                          ││
│ │ ○ 支付宝                            ││
│ └─────────────────────────────────────┘│
│                                         │
│ □ 开通自动续费（可随时关闭）            │
│                                         │
│ 📋 服务协议                             │
│ 购买即表示同意《会员服务协议》          │
│                                         │
├─────────────────────────────────────────┤
│         [确认支付 ¥168.00]              │
└─────────────────────────────────────────┘
```

### 3. 推送设置页 (/settings/push)

```
┌─────────────────────────────────────────┐
│ ← 推送设置                              │
├─────────────────────────────────────────┤
│                                         │
│ 🔔 推送开关                             │
│                                         │
│ ┌─────────────────────────────────────┐│
│ │ 每日运势推送              [开关]    ││
│ │ 每天早上8点推送今日运势              ││
│ └─────────────────────────────────────┘│
│                                         │
│ ┌─────────────────────────────────────┐│
│ │ 天气预警推送              [开关]    ││
│ │ 突发天气变化时推送穿搭建议           ││
│ └─────────────────────────────────────┘│
│                                         │
│ ┌─────────────────────────────────────┐│
│ │ 重要日子提醒              [开关]    ││
│ │ 面试、约会等重要日子提前提醒         ││
│ └─────────────────────────────────────┘│
│                                         │
│ ┌─────────────────────────────────────┐│
│ │ 衣橱管理提醒              [开关]    ││
│ │ 换季收纳、闲置衣物提醒               ││
│ └─────────────────────────────────────┘│
│                                         │
│ ⏰ 推送时间                             │
│ ┌─────────────────────────────────────┐│
│ │ 运势推送时间              [08:00 ▾] ││
│ └─────────────────────────────────────┘│
│                                         │
│ 📱 推送渠道                             │
│ ┌─────────────────────────────────────┐│
│ │ 浏览器推送                [开关]    ││
│ │ 短信推送                  [开关]    ││
│ │ 邮件推送                  [开关]    ││
│ └─────────────────────────────────────┘│
│                                         │
└─────────────────────────────────────────┘
```

---

## 🔐 权限控制设计

### 权限中间件

```python
# 权限装饰器
def require_plan(required_plans: List[str]):
    """
    检查用户是否有指定套餐权限
    
    用法:
    @require_plan(['monthly', 'yearly'])
    async def some_premium_feature():
        ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, user_id: int, **kwargs):
            subscription = await get_user_subscription(user_id)
            
            if subscription.plan_type not in required_plans:
                raise InsufficientPermissionError(
                    required_plans=required_plans,
                    current_plan=subscription.plan_type
                )
            
            return await func(*args, user_id=user_id, **kwargs)
        return wrapper
    return decorator


# 功能配额检查
def check_quota(quota_type: str, amount: int = 1):
    """
    检查用户功能配额
    
    用法:
    @check_quota('daily_recommend')
    async def create_recommend():
        ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, user_id: int, **kwargs):
            usage = await get_user_usage(user_id, quota_type)
            limit = get_plan_quota(user_plan, quota_type)
            
            if usage + amount > limit:
                raise QuotaExceededError(
                    quota_type=quota_type,
                    usage=usage,
                    limit=limit
                )
            
            result = await func(*args, user_id=user_id, **kwargs)
            await increment_usage(user_id, quota_type, amount)
            return result
        return wrapper
    return decorator
```

### 权限配置表

```python
PLAN_QUOTAS = {
    'free': {
        'daily_recommend': 5,
        'wardrobe_items': 20,
        'monthly_poster': 3,
        'ai_comment_detail': False,
        'fortune_detail': False,
        'dayun_analysis': False,
    },
    'monthly': {
        'daily_recommend': -1,  # 无限
        'wardrobe_items': 200,
        'monthly_poster': -1,
        'ai_comment_detail': True,
        'fortune_detail': True,
        'dayun_analysis': False,
    },
    'yearly': {
        'daily_recommend': -1,
        'wardrobe_items': -1,
        'monthly_poster': -1,
        'ai_comment_detail': True,
        'fortune_detail': True,
        'dayun_analysis': True,
    }
}
```

---

## 🧪 测试用例

### 支付流程测试

| 测试场景 | 输入 | 预期输出 |
|---------|------|---------|
| 微信支付成功 | 有效支付参数 | 订单状态更新为success，会员生效 |
| 支付宝支付成功 | 有效支付参数 | 订单状态更新为success，会员生效 |
| 支付超时 | 订单创建30分钟后未支付 | 订单自动关闭 |
| 重复支付 | 同一订单重复支付 | 第二次支付被拒绝 |
| 退款 | 已支付订单申请退款 | 退款成功，会员失效 |

### 权限控制测试

| 测试场景 | 用户状态 | 预期输出 |
|---------|---------|---------|
| 免费用户访问高级功能 | 免费用户 | 返回权限不足错误 |
| 月度会员访问年度功能 | 月度会员 | 返回权限不足错误 |
| 配额用尽 | 免费用户第6次推荐 | 返回配额超限错误 |
| 会员过期 | 过期会员访问会员功能 | 返回会员已过期错误 |

### 推送功能测试

| 测试场景 | 条件 | 预期输出 |
|---------|------|---------|
| 每日运势推送 | 早8点 | 推送到所有开启的用户 |
| 天气预警推送 | 突发降温 | 推送到相关地区用户 |
| 重复推送 | 同一用户同一天 | 不重复推送 |
| 推送失败 | 设备token失效 | 记录错误，重试3次 |

---

## ✅ 验收标准

### 支付功能验收

- [x] 微信支付完整流程可用（Mock 实现）
- [x] 支付宝支付完整流程可用（Mock 实现）
- [x] 支付回调正确处理（Mock 模拟）
- [x] 订单状态实时更新
- [x] 退款流程可用（Mock 模拟）

### 会员功能验收

- [x] 会员权益正确生效
- [x] 权限控制无漏洞
- [x] 配额统计准确
- [x] 升级/降级流程正确
- [x] 会员到期提醒正常

### 推送功能验收

- [x] Web Push 订阅/取消正常
- [x] 每日运势准时推送
- [x] 推送到达率>90%
- [x] 推送设置保存正确

---

## 📅 每日进度

| 日期 | 完成任务 | 备注 |
|------|---------|------|
| Day 1 | 会员数据库 + 订阅API | 4张新表创建完成 |
| Day 2 | Mock支付集成 | 微信/支付宝 Mock 实现 |
| Day 3 | 权限中间件 + 支付回调 | require_plan/check_quota |
| Day 4 | 会员中心页面 + 支付页面 | MembershipCard/PaymentForm |
| Day 5 | 推送系统 + 运势推送任务 | PushSettings/NotificationBell |

---

## 📝 实现详情

### 后端实现

#### 数据库（4张新表）
- `subscriptions`：会员订阅表，支持免费/月度/年度三级
- `payment_records`：支付记录表，含交易号、回调信息、退款
- `push_notifications`：推送记录表，支持多渠道（webpush/sms/email）
- `user_push_settings`：用户推送设置表，含推送开关和时间配置

#### 会员 API
- **订阅操作**：订阅/取消/升级/续费，支持自动续费
- **Mock 支付服务**：`payment_service.py` - 模拟完整支付流程（创建订单→模拟支付→回调确认→开通会员）
- **权限中间件**：`require_plan()` 检查套餐权限，`check_quota()` 检查功能配额

#### 推送服务
- **推送服务**：`push_service.py` - 支持多渠道推送
- **定时调度**：`push_scheduler.py` - 每日运势定时推送
- **Web Push**：浏览器推送订阅管理

### 前端实现

#### 页面与组件
- 会员中心页面（`/membership`）：当前权益展示+套餐升级
- `MembershipCard`：会员卡片组件
- `PaymentForm`：支付表单组件
- `PushSettings`：推送设置组件
- `NotificationBell`：通知铃铛组件

### 三级会员体系

| 权益 | 免费用户 | 月度会员 ¥19.9 | 年度会员 ¥168 |
|------|:-------:|:-------------:|:------------:|
| 基础推荐 | 5次/日 | 无限 | 无限 |
| 衣橱容量 | 20件 | 200件 | 无限 |
| AI穿搭点评 | 基础版 | 详细版 | 专家版 |
| 大运流年分析 | ❌ | ❌ | ✅ |
| 海报生成 | 3次/月 | 无限 | 无限+专属模板 |

### Mock 支付说明

微信支付和支付宝支付目前为 Mock 实现：
- 模拟完整支付流程：创建订单 → 模拟支付 → 回调确认 → 开通会员
- 支付参数为模拟数据，不涉及真实交易
- 真实对接需具备以下资质后替换 Mock 逻辑：
  - 微信支付商户号（MCH_ID）+ API密钥
  - 支付宝商户应用（APP_ID）+ RSA密钥
  - ICP备案完成（国内支付前置条件）

---

*创建时间: 2026-04-17*  
*状态: ✅ 已完成（2026-07-01）*
