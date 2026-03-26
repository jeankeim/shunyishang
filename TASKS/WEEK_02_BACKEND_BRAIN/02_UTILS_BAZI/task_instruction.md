# 任务 2: 八字与五行计算工具库 (02_UTILS_BAZI)

**优先级**: 🟡 中高  
**预估时间**: 3-4 小时  
**依赖**: Task 1 完成（cnlunar 已安装）

---

## 📋 任务目标

实现正式版八字排盘与五行分析工具库。用户传入出生日期时间，系统输出四柱八字、五行强弱分布、喜用神推荐及推理说明。同时支持纯场景（无八字）的五行推断，供 LangGraph Agent 调用。

---

## 🔧 执行步骤

### 步骤 1: 创建工具库目录结构

```
packages/utils/
├── __init__.py
├── bazi_calculator.py    # 主入口：八字计算
├── wuxing_rules.py       # 五行规则映射表
└── scene_mapper.py       # 场景→五行映射
```

---

### 步骤 2: `packages/utils/wuxing_rules.py`

定义所有静态规则映射表，供其他模块引用。

**必须包含的规则表**：

#### 2.1 天干五行映射
```
甲→木, 乙→木, 丙→火, 丁→火, 戊→土
己→土, 庚→金, 辛→金, 壬→水, 癸→水
```

#### 2.2 地支五行映射
```
子→水, 丑→土, 寅→木, 卯→木, 辰→土
巳→火, 午→火, 未→土, 申→金, 酉→金
戌→土, 亥→水
```

#### 2.3 季节/月份五行强弱修正
```
春季（寅卯辰月，2-4月）：木旺、火相、水休、金囚、土死
夏季（巳午未月，5-7月）：火旺、土相、木休、水囚、金死
秋季（申酉戌月，8-10月）：金旺、水相、土休、火囚、木死
冬季（亥子丑月，11-1月）：水旺、木相、金休、土囚、火死
```

#### 2.4 喜用神推断规则（日元 × 季节 组合，覆盖 40 种常见组合）

格式：`(日元五行, 当令五行) → (喜用神列表, 忌神列表, 推理说明)`

示例：
```
(木, 火)：木生火，木被火泄，火旺木弱 → 喜：水(生木)、木(比扶) 忌：火(泄)、金(克)
(木, 水)：冬木，水生木，但水过旺 → 喜：火(暖局)、土(止水) 忌：水(太旺)
(火, 金)：秋天火弱，金克火 → 喜：木(生火)、火(比扶) 忌：水(克)、金(克)
... （至少覆盖 5×8=40 种组合）
```

#### 2.5 关键词→五行映射表（用于意图推断）

```python
KEYWORD_ELEMENT_MAP = {
    # 木属性关键词
    "木": ["清新", "自然", "生机", "活力", "成长", "春天", "户外", "运动", "随性", "文艺"],
    # 火属性关键词  
    "火": ["热情", "浪漫", "活泼", "张扬", "喜庆", "派对", "约会", "桃花", "亮丽", "旺桃花"],
    # 土属性关键词
    "土": ["稳重", "踏实", "温暖", "亲和", "家居", "休闲", "舒适", "包容", "温柔"],
    # 金属性关键词
    "金": ["干练", "专业", "正式", "精致", "简约", "利落", "面试", "商务", "高冷", "天真", "清纯"],
    # 水属性关键词
    "水": ["神秘", "深沉", "冷静", "沉稳", "内敛", "智慧", "高贵", "优雅", "浮躁（互补）"],
}
```

#### 2.6 场景→五行映射表

```python
SCENE_ELEMENT_MAP = {
    "面试": {"primary": ["金"], "secondary": ["水"], "desc": "职业干练"},
    "约会": {"primary": ["火", "木"], "secondary": ["水"], "desc": "浪漫活力"},
    "日常": {"primary": ["土", "木"], "secondary": [], "desc": "舒适自然"},
    "商务": {"primary": ["金", "水"], "secondary": [], "desc": "专业沉稳"},
    "运动": {"primary": ["木", "火"], "secondary": [], "desc": "活力清爽"},
    "派对": {"primary": ["火"], "secondary": ["金"], "desc": "热情闪耀"},
    "居家": {"primary": ["土"], "secondary": ["木"], "desc": "温暖舒适"},
    "旅行": {"primary": ["木", "水"], "secondary": [], "desc": "自由灵动"},
}
```

---

### 步骤 3: `packages/utils/bazi_calculator.py`

**核心函数接口规范**：

#### 3.1 `calculate_bazi(birth_year, birth_month, birth_day, birth_hour, gender) -> BaziResult`

使用 `cnlunar` 库获取农历信息，计算四柱：

```
输入：1995, 6, 15, 10, "男"
处理：
  1. cnlunar.Lunar(1995, 6, 15, 10) 获取天干地支
  2. 提取年柱、月柱、日柱、时柱
  3. 统计八个字的五行分布
  4. 确定日元（日柱天干的五行）
  5. 确定月令（月柱地支对应的当旺五行）
  6. 查询喜用神规则表

输出 BaziResult：
{
  "pillars": {
    "year": "乙亥", "month": "壬午",
    "day": "甲申", "hour": "壬午"
  },
  "eight_chars": ["乙", "亥", "壬", "午", "甲", "申", "壬", "午"],
  "five_elements_count": {"木": 2, "水": 3, "火": 2, "金": 1, "土": 0},
  "dominant_element": "水",
  "lacking_element": "土",
  "day_master": "木",        # 日柱天干的五行
  "month_element": "火",     # 月令当旺五行
  "suggested_elements": ["水", "木"],  # 喜用神
  "avoid_elements": ["金", "火"],      # 忌神
  "reasoning": "日元甲木，生于午月（火旺），木被火泄能量，建议用水来滋养木气，用木来比扶。"
}
```

#### 3.2 `infer_elements_from_text(text: str) -> IntentResult`

规则优先的五行意图推断（用于 LangGraph Agent）：

```
输入："我明天要去面试，想显得专业干练"
处理：
  1. 分词，在 KEYWORD_ELEMENT_MAP 中查找匹配关键词
  2. 统计各五行的命中关键词数量
  3. 如果命中数 >= 1，返回 method="rule"
  4. 如果命中数 = 0，返回 method="llm_needed"（由 Agent 触发 LLM 兜底）

输出 IntentResult：
{
  "elements": ["金", "水"],
  "confidence": 0.85,
  "method": "rule",  # or "llm_needed"
  "matched_keywords": ["面试→金", "干练→金"],
  "reasoning": "关键词'面试'匹配金属性，'干练'匹配金属性"
}
```

#### 3.3 `get_scene_elements(scene: str) -> dict`

场景五行查询（直接查 SCENE_ELEMENT_MAP）：

```
输入："面试"
输出：{"primary": ["金"], "secondary": ["水"], "desc": "职业干练"}
```

#### 3.4 `merge_recommendations(bazi_result, intent_result, scene_result) -> list[str]`

综合合并推荐五行（优先级：八字喜用神 > 场景 > 意图）：

```
逻辑：
1. 如果有八字，取 bazi_result.suggested_elements 为主
2. 叠加 scene_result.primary 中与喜用神不冲突的五行
3. intent_result 作为补充参考
4. 返回最终推荐五行列表（去重，最多 3 个）
```

---

### 步骤 4: `packages/utils/scene_mapper.py`

封装场景相关的工具函数，独立于八字逻辑：

```python
def extract_scene_from_text(text: str) -> str | None:
    """从用户输入中提取场景关键词，如"面试"、"约会"等"""
    
def get_season_element(month: int) -> str:
    """根据月份返回当令五行"""
    
def get_color_by_element(element: str) -> list[str]:
    """根据五行返回对应颜色关键词，供向量搜索增强使用"""
    # 金→白、银、灰
    # 木→绿、青
    # 水→黑、蓝、深蓝
    # 火→红、粉、橙、紫
    # 土→棕、黄、卡其
```

---

## 📁 输出文件清单

| 文件路径 | 说明 |
|:---|:---|
| `packages/utils/__init__.py` | 新建 |
| `packages/utils/bazi_calculator.py` | 核心计算逻辑 |
| `packages/utils/wuxing_rules.py` | 静态规则映射表 |
| `packages/utils/scene_mapper.py` | 场景工具函数 |
| `tests/test_bazi.py` | 单元测试（见验收标准） |

---

## ⚠️ 注意事项

1. **cnlunar 用法**：`import cnlunar; c = cnlunar.Lunar(year, month, day, hour, isLunarDate=False)`，获取 `c.day8Char`（四柱八字）
2. **精度说明**：本实现为简化版喜用神推断（日元+月令），不涉及格局、神煞、大运等复杂算法，但接口预留扩展字段
3. **无八字时降级**：`bazi` 参数为 `None` 时，`merge_recommendations` 仅使用场景+意图推断结果
4. **Type Hints 必须完整**：所有返回值使用 TypedDict 或 dataclass 定义
