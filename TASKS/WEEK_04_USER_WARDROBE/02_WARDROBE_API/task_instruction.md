# 任务 2: 衣橱 CRUD 与 AI 自动打标 (02_WARDROBE_API)

**优先级**: 🔴 高  
**预估时间**: 3-4 小时  
**依赖**: Task 1 数据库迁移完成

---

## 📋 任务目标

实现衣橱管理接口，**核心亮点是 AI 自动打标**：
- 用户只需描述衣物（如"红色羊毛大衣"），AI 自动识别五行属性
- 自动生成 Embedding 用于语义搜索
- 完整 CRUD 接口支持

---

## 🔧 执行步骤

### 步骤 1: AI 打标服务

创建 `apps/api/services/ai_tagging_service.py`：

```python
import os
import json
from openai import AsyncOpenAI
from typing import Dict, Optional

class AITaggingService:
    """
    AI 自动打标服务
    分析衣物描述，返回五行属性
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.model = os.getenv("QWEN_MODEL", "qwen-plus")
    
    async def analyze_item(
        self, 
        description: str, 
        image_url: Optional[str] = None
    ) -> Dict:
        """
        分析衣物，返回五行属性
        
        Args:
            description: 衣物描述，如 "红色羊毛大衣"
            image_url: 图片URL（可选）
        
        Returns:
            {
                "primary_element": "火",
                "secondary_element": "土", 
                "color": "红色",
                "material": "羊毛",
                "style": "正式",
                "season": ["秋", "冬"],
                "tags": ["商务", "保暖"],
                "suggested_name": "红色羊毛大衣"
            }
        """
        
        prompt = f"""你是一个专业的五行穿搭顾问。请分析这件衣物的五行属性。

衣物描述: {description}
{f"图片参考: {image_url}" if image_url else ""}

请根据以下规则分析：
1. 颜色五行对照：
   - 红、橙、紫 → 火
   - 黄、棕、土色 → 土  
   - 白、金、银 → 金
   - 黑、蓝、灰 → 水
   - 绿、青 → 木

2. 材质五行对照：
   - 丝绸、棉麻 → 木
   - 皮革、毛呢 → 土
   - 羽绒、羊毛 → 水/火（视颜色而定）
   - 金属装饰 → 金

3. 款式五行对照：
   - 正装、西装 → 金
   - 运动休闲 → 木
   - 华丽礼服 → 火
   - 简约基础 → 水
   - 自然田园 → 土

请以 JSON 格式输出分析结果，不要输出其他内容：
{{
    "primary_element": "主五行（金/木/水/火/土之一）",
    "secondary_element": "次五行（可选，多个用逗号分隔）",
    "color": "主色调",
    "material": "材质",
    "style": "风格",
    "season": ["适合季节"],
    "tags": ["标签1", "标签2"],
    "suggested_name": "建议名称"
}}"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是专业的五行穿搭顾问，擅长分析衣物的五行属性。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # 降低随机性，提高一致性
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result


# 单例
ai_tagging_service = AITaggingService()
```

---

### 步骤 2: Embedding 生成服务

创建 `apps/api/services/embedding_service.py`：

```python
import os
from openai import AsyncOpenAI
from typing import List

class EmbeddingService:
    """
    文本向量化服务
    与 Week 1 公共库使用相同的模型
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        # 与 Week 1 保持一致的模型
        self.model = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        生成文本向量
        
        Args:
            text: 衣物描述文本
        
        Returns:
            1024维向量
        """
        response = await self.client.embeddings.create(
            model=self.model,
            input=text,
            dimensions=1024
        )
        return response.data[0].embedding


# 单例
embedding_service = EmbeddingService()
```

---

### 步骤 3: Pydantic Schema

创建 `apps/api/schemas/wardrobe.py`：

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

# ============================================
# 请求模型
# ============================================

class WardrobeItemCreate(BaseModel):
    """添加衣物请求"""
    description: str = Field(..., description="衣物描述", min_length=2, max_length=500)
    image_url: Optional[str] = Field(None, description="图片URL（可选）")
    primary_element: Optional[str] = Field(None, description="手动指定主五行")
    category: Optional[str] = Field(None, description="分类：上装/下装/外套/配饰")


class WardrobeItemUpdate(BaseModel):
    """更新衣物请求"""
    name: Optional[str] = None
    category: Optional[str] = None
    primary_element: Optional[str] = None
    secondary_element: Optional[str] = None
    attributes_detail: Optional[dict] = None
    image_url: Optional[str] = None


class AITaggingPreview(BaseModel):
    """AI打标预览请求"""
    description: str = Field(..., min_length=2, max_length=500)
    image_url: Optional[str] = None


# ============================================
# 响应模型
# ============================================

class AITaggingResult(BaseModel):
    """AI打标结果"""
    primary_element: str
    secondary_element: Optional[str] = None
    color: Optional[str] = None
    material: Optional[str] = None
    style: Optional[str] = None
    season: List[str] = []
    tags: List[str] = []
    suggested_name: str


class WardrobeItemResponse(BaseModel):
    """衣物响应"""
    item_id: UUID
    name: str
    category: Optional[str]
    image_url: Optional[str]
    primary_element: Optional[str]
    secondary_element: Optional[str]
    attributes_detail: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WardrobeListResponse(BaseModel):
    """衣物列表响应"""
    total: int
    items: List[WardrobeItemResponse]
```

---

### 步骤 4: 衣橱路由

创建 `apps/api/routers/wardrobe.py`：

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from typing import Optional

from apps.api.core.database import get_connection
from apps.api.core.security import get_current_user_id
from apps.api.schemas.wardrobe import (
    WardrobeItemCreate, WardrobeItemUpdate, AITaggingPreview,
    AITaggingResult, WardrobeItemResponse, WardrobeListResponse,
)
from apps.api.services.ai_tagging_service import ai_tagging_service
from apps.api.services.embedding_service import embedding_service

router = APIRouter(prefix="/wardrobe", tags=["wardrobe"])


@router.post("/items/preview-tagging", response_model=AITaggingResult)
async def preview_tagging(
    request: AITaggingPreview,
    user_id: UUID = Depends(get_current_user_id)
):
    """预览 AI 打标结果"""
    result = await ai_tagging_service.analyze_item(
        description=request.description,
        image_url=request.image_url
    )
    return AITaggingResult(**result)


@router.post("/items", response_model=WardrobeItemResponse)
async def add_wardrobe_item(
    request: WardrobeItemCreate,
    user_id: UUID = Depends(get_current_user_id)
):
    """添加衣物到个人衣橱"""
    # 1. AI 打标
    ai_result = await ai_tagging_service.analyze_item(
        description=request.description,
        image_url=request.image_url
    )
    
    # 2. 用户手动覆盖优先
    primary_element = request.primary_element or ai_result.get("primary_element")
    
    # 3. 生成向量
    embedding_text = f"{request.description} {ai_result.get('color', '')}"
    embedding = await embedding_service.generate_embedding(embedding_text)
    
    # 4. 存入数据库（实现略）
    ...


@router.get("/items", response_model=WardrobeListResponse)
async def list_wardrobe_items(
    category: Optional[str] = Query(None),
    element: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user_id: UUID = Depends(get_current_user_id)
):
    """获取用户衣橱列表"""
    ...


@router.patch("/items/{item_id}", response_model=WardrobeItemResponse)
async def update_wardrobe_item(
    item_id: UUID,
    request: WardrobeItemUpdate,
    user_id: UUID = Depends(get_current_user_id)
):
    """更新衣物信息（修正 AI 识别错误）"""
    ...


@router.delete("/items/{item_id}")
async def delete_wardrobe_item(
    item_id: UUID,
    user_id: UUID = Depends(get_current_user_id)
):
    """删除衣物（软删除）"""
    ...


@router.get("/stats")
async def get_wardrobe_stats(
    user_id: UUID = Depends(get_current_user_id)
):
    """获取衣橱统计信息"""
    ...
```

---

## 📁 输出文件清单

| 文件路径 | 操作 |
|:---|:---|
| `apps/api/services/ai_tagging_service.py` | 新建 |
| `apps/api/services/embedding_service.py` | 新建 |
| `apps/api/schemas/wardrobe.py` | 新建 |
| `apps/api/routers/wardrobe.py` | 新建 |
| `apps/api/main.py` | 更新（注册路由） |

---

## ⚠️ 注意事项

1. **AI 识别准确性**: 用户可通过 PATCH 接口修正 AI 错误结果
2. **超时处理**: MVP 阶段同步执行，需设置合理超时（建议 30s）
3. **向量一致性**: 使用与公共库相同的 Embedding 模型
4. **权限验证**: 所有操作必须验证 `user_id`
