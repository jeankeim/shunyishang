# 多模态图片生成脚本使用说明

## 📋 功能简介

使用阿里云通义千问 (Qwen) 多模态大模型生成衣物图片，支持：
- ✅ 文本描述生成图片
- ✅ 批量生成
- ✅ 自动保存到本地
- ✅ 元数据管理
- ✅ 自定义查询

---

## 🔧 环境准备

### 1. 安装依赖

```bash
# 在项目根目录执行
pip install dashscope>=1.14.0

# 或更新 requirements.txt 后统一安装
pip install -r requirements.txt
```

### 2. 获取 API Key

访问 [阿里云 DashScope 控制台](https://dashscope.console.aliyun.com/) 注册账号并获取 API Key。

### 3. 配置环境变量

在 `.env` 文件中添加：

```bash
# 通义千问 API Key
DASHSCOPE_API_KEY=your_api_key_here
```

---

## 🚀 快速开始

### 方式一：运行测试示例

```bash
cd scripts

# 运行默认测试（生成 5 张基础衣物图片）
python generate_images.py
```

**输出**：
- 图片保存在 `data/generated_images/YYYYMMDD/`
- 每张图附带 `.json` 元数据文件
- 汇总报告 `generation_report_YYYYMMDD_HHMMSS.json`

### 方式二：自定义查询

编辑 `generate_images_custom.py` 中的 `CUSTOM_QUERIES` 列表：

```python
CUSTOM_QUERIES = [
    {
        "query": "你的衣物描述",
        "category": "上装/下装/外套/裙装/鞋履/配饰",
        "element": "木/火/土/金/水",  # 可选
        "season": "春/夏/秋/冬"        # 可选
    },
    # ... 更多查询
]
```

然后运行：

```bash
python generate_images_custom.py
```

---

## 📝 参数说明

### 核心参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `prompt` | str | 必填 | 图片描述文本 |
| `style` | str | `<photorealistic>` | 风格选择 |
| `size` | str | `1024*1024` | 图片尺寸 |
| `n` | int | `1` | 每次生成数量 (1-4) |

### 可用风格

```python
"<photorealistic>"  # 照片级真实（默认）
"<anime>"           # 动漫风格
"<oil painting>"    # 油画风格
"<watercolor>"      # 水彩风格
"<sketch>"          # 素描风格
```

### 可用尺寸

```python
"1024*1024"  # 正方形（推荐）
"720*1280"   # 竖版（适合手机）
"1280*720"   # 横版（适合电脑）
```

---

## 💡 使用示例

### 示例 1: 单张图片生成

```python
from generate_images import QwenImageGenerator

generator = QwenImageGenerator()

result = generator.generate_image(
    prompt="一件蓝色牛仔夹克，复古水洗，宽松版型",
    style="<photorealistic>",
    size="1024*1024",
    n=1
)

if result:
    print(f"生成成功：{result['url']}")
```

### 示例 2: 批量生成

```python
queries = [
    {"query": "白色 T 恤，纯棉，简约风格", "category": "上装"},
    {"query": "黑色西装裤，修身剪裁，商务风", "category": "下装"},
    {"query": "卡其色风衣，双排扣，英伦风", "category": "外套"},
]

results = generator.generate_batch(
    queries=queries,
    output_dir=Path("./data/my_images"),
    delay=2.0  # 每张图片间隔 2 秒
)

print(f"成功生成 {len(results)}/{len(queries)} 张")
```

### 示例 3: 按五行属性生成

```python
wuxing_queries = {
    "木": "绿色棉麻衬衫，自然风格，春天穿着",
    "火": "红色连衣裙，热情奔放，夏季穿搭",
    "土": "黄色针织衫，温暖厚实，秋季日常",
    "金": "白色高领毛衣，简洁干练，冬季保暖",
    "水": "黑色皮衣，酷炫时尚，春秋百搭",
}

for element, prompt in wuxing_queries.items():
    result = generator.generate_image(
        prompt=prompt,
        style="<photorealistic>"
    )
    if result:
        result["element"] = element
        # 保存结果...
```

---

## 📂 输出结构

```
data/generated_images/
├── 20260329/                    # 按日期分类
│   ├── image_001_1711700000.png        # 图片文件
│   ├── image_001_1711700000.json       # 元数据
│   ├── image_002_1711700002.png
│   ├── image_002_1711700002.json
│   └── ...
├── custom/                       # 自定义生成
│   └── 20260329/
│       └── ...
└── generation_report_20260329_120000.json  # 汇总报告
```

### 元数据格式 (JSON)

```json
{
  "url": "https://...",
  "local_path": "/absolute/path/to/image.png",
  "filename": "image_001_1711700000.png",
  "prompt": "原始描述",
  "full_prompt": "完整提示词（含风格修饰）",
  "style": "<photorealistic>",
  "size": "1024*1024",
  "category": "上装",
  "element": "木",
  "created_at": "2026-03-29T12:00:00"
}
```

---

## ⚠️ 注意事项

### 1. API 限流

- 免费额度：每月 200 张（具体以官网为准）
- 建议设置 `delay=2.0` 以上避免触发限流
- 批量生成时注意控制并发

### 2. 图片版权

- 生成的图片仅供学习研究使用
- 商业用途请遵守阿里云相关协议

### 3. 网络要求

- 需要稳定的互联网连接
- 如遇超时错误，可增加 `timeout` 参数

### 4. 错误处理

常见错误及解决方案：

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `API key not found` | 未配置 API Key | 检查 `.env` 文件 |
| `Insufficient balance` | 余额不足 | 充值账户 |
| `Rate limit exceeded` | 请求过于频繁 | 增加 `delay` 时间 |
| `Invalid prompt` | 提示词违规 | 修改描述内容 |

---

## 🔗 相关资源

- [通义千问官方文档](https://help.aliyun.com/zh/dashscope/)
- [通义万相 API 参考](https://help.aliyun.com/zh/dashscope/developer-reference/api-details)
- [DashScope Python SDK](https://github.com/aliyun/alibabacloud-dashscope-python-sdk)

---

## 🎯 下一步

生成图片后，可以：

1. **用于衣橱管理**：将图片上传到用户衣橱
2. **训练推荐模型**：作为种子数据的视觉补充
3. **虚拟试衣**：结合 W5-02 任务实现试衣功能
4. **分享海报**：结合 W5-03 任务制作宣传物料

---

*最后更新：2026-03-29*
