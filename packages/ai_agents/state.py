"""
LangGraph Agent 状态定义
定义 AgentState TypedDict，用于在节点间传递状态
"""

from typing import TypedDict, List, Dict, Optional, Any, Annotated
from operator import add


class AgentState(TypedDict):
    """
    LangGraph Agent 状态
    
    在节点间传递的所有数据都存储在这个状态中
    """
    # === 输入层 ===
    user_input: str                     # 用户原始描述
    scene: Optional[str]                # 提取的场景
    weather_element: Optional[str]      # 天气对应的五行
    weather_info: Optional[Dict]        # 天气详情 {"temperature": int, "weather_desc": str, ...}
    bazi_input: Optional[Dict]          # 原始八字输入 {"birth_year": ..., ...}
    user_gender: Optional[str]          # 用户性别（男/女）
    user_id: Optional[int]              # 用户ID（用于衣橱检索权限控制）
    top_k: int                          # 返回推荐数量，默认 5
    
    # === 检索模式控制 (Task 3) ===
    retrieval_mode: str                 # 检索模式: 'public' | 'wardrobe' | 'hybrid'
    
    # === 旅行/出差场景参数 ===
    travel_days: Optional[int]          # 旅行天数
    destination: Optional[str]          # 目的地城市
    luggage_size: Optional[str]         # 行李箱大小: 小/中/大
    travel_plan: Optional[Dict]         # 多天行程规划结果
    
    # === 换一批功能 ===
    batch_index: int                    # 批次索引（0-2，最多3批）
    
    # === 分析层 ===
    bazi_result: Optional[Dict]         # 八字计算结果（来自 Task 02）
    llm_token_usage: Optional[Dict]     # 本次请求 LLM token 用量累加（成本核算）
    annual_luck: Optional[Dict]         # 流年运势（当年）
    major_luck: Optional[Dict]          # 当前大运
    intent_result: Optional[Dict]       # 意图推断结果
    explicit_intent: Optional[Dict]     # 用户显式五行修正意图（缺X/补X/忌X，最高优先级）
    anchor_spec: Optional[Dict]         # 用户显式指定的锚点单品（颜色+品类，如白衬衫）
    anchor_specs: List[Dict]            # 用户显式指定的锚点单品列表（多锚点支持）
    target_elements: List[str]          # 最终推荐五行（合并后）
    xiyong_elements: List[str]          # 八字喜用神（纯八字，不含场景）
    added_elements: List[str]           # 场景/天气额外添加的五行
    boost_elements: List[str]           # 相生辅助五行（忌神但生喜用神，评分加分）
    
    # === 检索层 ===
    search_query: str                   # 优化后的向量搜索文本
    retrieved_items: List[Dict]         # 加权排序后的 Top K 物品
    item_sources: Dict[str, str]        # 物品来源标记: {'item_id': 'wardrobe'/'public'}
    
    # === 输出层 ===
    final_response: Dict                # 格式化的最终响应
    reasoning_text: str                 # 推荐理由文本（流式生成）
    
    # === 错误处理 ===
    error: Optional[str]                # 错误信息（有则终止流程）
    
    # === 流式输出支持 ===
    token_stream: Annotated[List[str], add]  # 累积的 token 流
    
    # === 可选：多轮对话 ===
    chat_history: List[Dict]            # 多轮对话历史


class ItemResult(TypedDict):
    """单个推荐物品结果"""
    item_code: str
    name: str
    category: str
    primary_element: str
    secondary_element: Optional[str]
    final_score: float
    semantic_score: float
    wuxing_score: float


class AnalysisOutput(TypedDict):
    """分析阶段输出"""
    target_elements: List[str]
    bazi_reasoning: Optional[str]
    intent_reasoning: Optional[str]
    scene: Optional[str]


class FinalOutput(TypedDict):
    """最终输出格式"""
    analysis: AnalysisOutput
    items: List[ItemResult]
    reason: str


def create_initial_state(
    user_input: str,
    scene: Optional[str] = None,
    weather_element: Optional[str] = None,
    weather_info: Optional[Dict] = None,
    bazi_input: Optional[Dict] = None,
    user_gender: Optional[str] = None,
    user_id: Optional[int] = None,
    retrieval_mode: str = 'public',
    top_k: int = 5,
    chat_history: Optional[List[Dict]] = None,
    travel_days: Optional[int] = None,
    destination: Optional[str] = None,
    luggage_size: Optional[str] = None,
    batch_index: int = 0,
) -> AgentState:
    """
    创建初始状态
    
    Args:
        user_input: 用户输入文本
        scene: 场景（可选）
        weather_element: 天气五行（可选）
        weather_info: 天气详情（可选）
        bazi_input: 八字输入（可选）
        user_gender: 用户性别（可选，男/女）
        user_id: 用户ID（可选，用于衣橱检索）
        retrieval_mode: 检索模式（默认public）
        top_k: 返回数量
        chat_history: 对话历史
        travel_days: 旅行天数（可选）
        destination: 目的地城市（可选）
        luggage_size: 行李箱大小（可选，小/中/大）
        batch_index: 换一批批次索引（0-2，默认0）
    
    Returns:
        AgentState: 初始状态
    """
    return AgentState(
        user_input=user_input,
        scene=scene,
        weather_element=weather_element,
        weather_info=weather_info,
        bazi_input=bazi_input,
        user_gender=user_gender,
        user_id=user_id,
        top_k=top_k,
        retrieval_mode=retrieval_mode,
        travel_days=travel_days,
        destination=destination,
        luggage_size=luggage_size,
        travel_plan=None,
        batch_index=batch_index,
        bazi_result=None,
        llm_token_usage=None,
        annual_luck=None,
        major_luck=None,
        intent_result=None,
        explicit_intent=None,
        anchor_spec=None,
        anchor_specs=[],
        target_elements=[],
        xiyong_elements=[],
        added_elements=[],
        boost_elements=[],
        search_query="",
        retrieved_items=[],
        item_sources={},
        final_response={},
        reasoning_text="",
        error=None,
        token_stream=[],
        chat_history=chat_history or [],
    )
