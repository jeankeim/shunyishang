"""
LangGraph 状态机定义
构建推荐 Agent 的工作流图
"""

from typing import Literal

from langgraph.graph import StateGraph, END

from packages.ai_agents.state import AgentState, create_initial_state
from packages.ai_agents.nodes import (
    analyze_intent_node,
    retrieve_items_node,
    generate_advice_node,
    format_output_node,
)


def check_error(state: AgentState) -> Literal["continue", "error"]:
    """
    检查是否有错误
    
    Returns:
        "continue": 继续执行
        "error": 跳转到结束
    """
    if state.get("error"):
        return "error"
    return "continue"


def check_retrieved_items(state: AgentState) -> Literal["continue", "error"]:
    """
    检查是否有检索结果
    
    Returns:
        "continue": 继续执行
        "error": 跳转到结束
    """
    if not state.get("retrieved_items"):
        return "error"
    return "continue"


def build_graph() -> StateGraph:
    """
    构建 LangGraph 状态机
    
    流程：
    START → analyze_intent → retrieve_items → generate_advice → format_output → END
    
    条件边：
    - analyze_intent 后：如果 error → END
    - retrieve_items 后：如果无结果 → END
    """
    # 创建状态图
    graph = StateGraph(AgentState)
    
    # 添加节点
    graph.add_node("analyze_intent", analyze_intent_node)
    graph.add_node("retrieve_items", retrieve_items_node)
    graph.add_node("generate_advice", generate_advice_node)
    graph.add_node("format_output", format_output_node)
    
    # 设置入口
    graph.set_entry_point("analyze_intent")
    
    # 添加边
    # analyze_intent → retrieve_items（条件）
    graph.add_conditional_edges(
        "analyze_intent",
        check_error,
        {
            "continue": "retrieve_items",
            "error": END,
        }
    )
    
    # retrieve_items → generate_advice（条件）
    graph.add_conditional_edges(
        "retrieve_items",
        check_retrieved_items,
        {
            "continue": "generate_advice",
            "error": END,
        }
    )
    
    # generate_advice → format_output
    graph.add_edge("generate_advice", "format_output")
    
    # format_output → END
    graph.add_edge("format_output", END)
    
    return graph


# 编译图
_graph = build_graph()
app = _graph.compile()


def _extract_context_from_query(user_input: str) -> dict:
    """
    使用大模型从用户输入中提取场景、天气、气温信息
    
    优先级：用户提问中的信息 > 外部设置
    
    Args:
        user_input: 用户输入文本
    
    Returns:
        dict: 提取的上下文信息
        {
            "scene": str | None,  # 场景
            "weather_info": dict | None,  # 天气信息
            "weather_element": str | None,  # 天气五行
        }
    """
    from packages.ai_agents.nodes import get_llm_client
    import json
    
    result = {
        "scene": None,
        "weather_info": None,
        "weather_element": None,
    }
    
    try:
        # 使用大模型解析用户输入
        client = get_llm_client(timeout=30)
        
        prompt = f"""你是一位信息提取专家，请从用户的穿搭咨询中提取关键信息。

用户输入：{user_input}

请提取以下信息（如果存在）：
1. scene: 场景（商务/面试/约会/运动/居家/婚礼/派对/旅行/上班/其他）
2. temperature: 气温（数字，单位摄氏度）
3. weather_desc: 天气描述（闷热/炎热/寒冷/雨天/雪天/晴天/多云/大风）

**重要场景识别规则**：
- 如果提到"游泳"、"海边游泳"、"泳池"等，场景应该是"运动"（不是"旅行"）
- 如果提到"马拉松"、"跑步"、"健身"、"瑜伽"等，场景应该是"运动"
- 如果提到"三亚"、"海边"、"度假"但**没有**提到具体运动，场景才是"旅行"
- 运动场景优先级 > 旅行场景

返回严格的 JSON 格式，不要有任何其他内容。如果某个信息不存在，使用 null。

示例格式：
{{"scene": "商务", "temperature": 15, "weather_desc": "多云"}}
"""
        
        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "你是一个信息提取助手，只返回 JSON 格式的结果。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # 低温度确保稳定输出
            response_format={"type": "json_object"},
        )
        
        extracted = json.loads(response.choices[0].message.content)
        
        # 处理提取结果
        scene = extracted.get("scene")
        temperature = extracted.get("temperature")
        weather_desc = extracted.get("weather_desc")
        
        # 场景映射
        scene_mapping = {
            "商务": "商务",
            "面试": "面试",
            "约会": "约会",
            "运动": "运动",
            "居家": "居家",
            "婚礼": "婚礼",
            "派对": "派对",
            "旅行": "旅行",
            "上班": "商务",
            "办公": "商务",
            "会议": "商务",
        }
        
        if scene:
            result["scene"] = scene_mapping.get(scene, scene)
        
        # 组装天气信息
        if temperature is not None or weather_desc:
            result["weather_info"] = {
                "temperature": temperature,
                "weather_desc": weather_desc,
                "humidity": None,
                "wind_level": None,
            }
            
            # 从天气描述推断五行元素
            if weather_desc:
                weather_element_map = {
                    "闷热": "火",
                    "炎热": "火",
                    "寒冷": "水",
                    "雨天": "水",
                    "雪天": "水",
                    "晴天": "火",
                    "多云": "土",
                    "大风": "木",
                }
                result["weather_element"] = weather_element_map.get(weather_desc)
        
        print(f"[LLM提取] 场景: {result['scene']}, 天气: {weather_desc}, 温度: {temperature}")
        
    except Exception as e:
        print(f"[LLM提取] 失败，回退到规则提取: {e}")
        # 回退到原有的规则提取逻辑
        return _extract_context_by_rules(user_input)
    
    return result


def _extract_context_by_rules(user_input: str) -> dict:
    """
    基于规则的上下文提取（备用方案）
    
    Args:
        user_input: 用户输入文本
    
    Returns:
        dict: 提取的上下文信息
    """
    import re
    
    result = {
        "scene": None,
        "weather_info": None,
        "weather_element": None,
    }
    
    text = user_input.lower()
    
    # ==================== 1. 场景提取 ====================
    # 先检测高优先级场景（商务、面试）
    # 商务场景（优先级最高）
    if any(kw in text for kw in ['商务', '会议', '见客户', '办公']):
        result["scene"] = "商务"
    # 面试场景
    elif '面试' in text:
        result["scene"] = "面试"
    # 出差/旅行场景
    elif any(kw in text for kw in ['出差', '旅行', '旅游', '去成都', '去北京', '去上海', '去广州', '去深圳']):
        result["scene"] = "旅行"
    # 运动场景
    elif any(kw in text for kw in ['马拉松', '跑步', '健身', '运动', '打球', '游泳', '瑜伽']):
        result["scene"] = "运动"
    # 上班/工作场景
    elif any(kw in text for kw in ['上班', '工作']):
        result["scene"] = "商务"
    # 约会场景
    elif any(kw in text for kw in ['约会', '相亲', '见面']):
        result["scene"] = "约会"
    # 居家场景
    elif any(kw in text for kw in ['居家', '在家', '宅', '休息']):
        result["scene"] = "居家"
    # 婚礼场景
    elif any(kw in text for kw in ['婚礼', '结婚', '婚宴']):
        result["scene"] = "婚礼"
    # 派对场景
    elif any(kw in text for kw in ['派对', '聚会', 'party']):
        result["scene"] = "派对"
    
    # ==================== 2. 气温提取 ====================
    # 匹配温度：25度、25°C、25℃、气温25
    temp_match = re.search(r'(\d+)\s*[°度℃cC]', text)
    if not temp_match:
        temp_match = re.search(r'气温[^\d]*(\d+)', text)
    
    temperature = None
    if temp_match:
        temperature = int(temp_match.group(1))
    
    # ==================== 3. 天气描述提取 ====================
    weather_desc = None
    
    # 潮湿/闷热
    if any(kw in text for kw in ['潮湿', '闷热', '潮湿闷热']):
        weather_desc = "闷热"
    # 炎热/高温
    elif any(kw in text for kw in ['炎热', '高温', '很热', '太热']):
        weather_desc = "炎热"
    # 寒冷/低温
    elif any(kw in text for kw in ['寒冷', '低温', '很冷', '太冷', '极寒']):
        weather_desc = "寒冷"
    # 下雨
    elif any(kw in text for kw in ['下雨', '雨天', '阴雨']):
        weather_desc = "雨天"
    # 下雪
    elif any(kw in text for kw in ['下雪', '雪天']):
        weather_desc = "雪天"
    # 晴天
    elif any(kw in text for kw in ['晴天', '晴朗', '出太阳']):
        weather_desc = "晴天"
    # 多云
    elif '多云' in text:
        weather_desc = "多云"
    # 大风
    elif any(kw in text for kw in ['大风', '刮风']):
        weather_desc = "大风"
    
    # ==================== 4. 组装天气信息 ====================
    if temperature is not None or weather_desc is not None:
        result["weather_info"] = {
            "temperature": temperature,
            "weather_desc": weather_desc,
            "humidity": None,
            "wind_level": None,
        }
        
        # 从天气描述推断五行元素
        if weather_desc:
            weather_element_map = {
                "闷热": "火",
                "炎热": "火",
                "寒冷": "水",
                "雨天": "水",
                "雪天": "水",
                "晴天": "火",
                "多云": "土",
                "大风": "木",
            }
            result["weather_element"] = weather_element_map.get(weather_desc)
    
    return result


def run_agent(
    user_input: str,
    scene: str = None,
    weather_element: str = None,
    weather_info: dict = None,
    bazi_input: dict = None,
    top_k: int = 5,
) -> dict:
    """
    运行 Agent（同步方式）
    
    Args:
        user_input: 用户输入
        scene: 场景（可选）
        weather_element: 天气五行（可选）
        weather_info: 天气详情（可选）
        bazi_input: 八字输入（可选）
        top_k: 返回数量
    
    Returns:
        dict: 最终响应
    """
    # 从八字输入中提取性别
    user_gender = bazi_input.get("gender") if bazi_input else None
    
    initial_state = create_initial_state(
        user_input=user_input,
        scene=scene,
        weather_element=weather_element,
        weather_info=weather_info,
        bazi_input=bazi_input,
        user_gender=user_gender,
        top_k=top_k,
    )
    
    result = app.invoke(initial_state)
    return result.get("final_response", {})


def run_agent_stream(
    user_input: str,
    scene: str = None,
    weather_element: str = None,
    weather_info: dict = None,
    bazi_input: dict = None,
    user_gender: str = None,
    user_id: int = None,
    retrieval_mode: str = "public",
    top_k: int = 5,
):
    """
    运行 Agent（流式方式，供 SSE 使用）
    
    Args:
        user_input: 用户输入
        scene: 场景（可选）
        weather_element: 天气五行（可选）
        weather_info: 天气详情（可选）
        bazi_input: 八字输入（可选）
        user_id: 用户ID（衣橱模式必需）
        retrieval_mode: 检索模式（默认 public）
        top_k: 返回数量
    
    Yields:
        dict: 状态更新
    """
    from packages.ai_agents.nodes import generate_advice_stream
    
    # 新增：从用户输入中提取场景和天气信息（优先级：用户提问 > 外部设置）
    extracted = _extract_context_from_query(user_input)
    
    # 使用用户提问中提取的信息，如果未提取到则使用外部传入的参数
    final_scene = extracted.get("scene") or scene
    final_weather_info = extracted.get("weather_info") or weather_info
    final_weather_element = extracted.get("weather_element") or weather_element
    
    if extracted.get("scene"):
        print(f"[推荐] 从用户提问中提取到场景: {extracted['scene']}")
    if extracted.get("weather_info"):
        print(f"[推荐] 从用户提问中提取到天气: {extracted['weather_info']}")
    
    # 使用传入的 user_gender，如果没有则从八字输入中提取
    if user_gender is None and bazi_input:
        user_gender = bazi_input.get("gender")
    
    # 调试日志：打印 gender 信息
    print(f"[推荐] user_gender={user_gender}, bazi_input.gender={bazi_input.get('gender') if bazi_input else None}")
    
    initial_state = create_initial_state(
        user_input=user_input,
        scene=final_scene,  # 使用提取后的场景
        weather_element=final_weather_element,  # 使用提取后的天气五行
        weather_info=final_weather_info,  # 使用提取后的天气信息
        bazi_input=bazi_input,
        user_gender=user_gender,
        user_id=user_id,
        retrieval_mode=retrieval_mode,
        top_k=top_k,
    )
    
    # 执行前三个节点（同步）
    state = analyze_intent_node(initial_state)
    initial_state.update(state)
    
    if initial_state.get("error"):
        yield {"type": "error", "data": initial_state["error"]}
        return
    
    state = retrieve_items_node(initial_state)
    initial_state.update(state)
    
    # 检查是否有错误信息
    if initial_state.get("error"):
        yield {"type": "error", "data": initial_state["error"]}
        return
    
    if not initial_state.get("retrieved_items"):
        yield {"type": "error", "data": "没有找到合适的衣物"}
        return
    
    # 输出分析结果
    bazi_result = initial_state.get("bazi_result")
    yield {
        "type": "analysis",
        "data": {
            "target_elements": initial_state["target_elements"],
            "bazi_reasoning": bazi_result.get("reasoning") if bazi_result else None,
            "intent_reasoning": initial_state["intent_result"].get("reasoning") if initial_state.get("intent_result") else None,
            "scene": initial_state.get("scene"),
            # 八字五行分布（用于雷达图当前层）
            "element_scores": bazi_result.get("five_elements_count") if bazi_result else None,
            # 喜用神（用于雷达图建议层）
            "suggested_elements": bazi_result.get("suggested_elements") if bazi_result else initial_state["target_elements"],
        }
    }
    
    # 输出物品列表（包含 source 字段）
    items = []
    print(f"[调试] retrieved_items 总数: {len(initial_state['retrieved_items'])}")
    print(f"[调试] retrieved_items 类型: {type(initial_state['retrieved_items'])}")
    
    for idx, item in enumerate(initial_state["retrieved_items"]):
        # 调试：检查 item 的类型
        if not isinstance(item, dict):
            print(f"[错误] retrieved_items[{idx}] 不是字典，类型: {type(item)}, 值: {item}")
            continue
        
        # 额外调试：打印 item 的所有键
        if idx == 0:
            print(f"[调试] 第一个 item 的键: {list(item.keys())}")
        
        items.append({
            "item_code": item.get("item_code", ""),
            "name": item.get("name", ""),
            "category": item.get("category", ""),
            "primary_element": item.get("primary_element", ""),
            "secondary_element": item.get("secondary_element"),
            "final_score": round(item.get("final_score", 0), 3),
            "semantic_score": round(item.get("semantic_score", 0.5), 3),  # Task 05
            "wuxing_score": round(item.get("wuxing_score", 0), 3),  # Task 05
            "scene_score": round(item.get("scene_score", 0.5), 3),  # Task 05
            "source": item.get("source") or "public",
            "item_id": item.get("id"),
            "image_url": item.get("image_url"),
        })
    
    print(f"[调试] 成功构建 items 数量: {len(items)}")
    yield {"type": "items", "data": items}
    
    # 流式输出推荐理由
    reasoning_parts = []
    for token in generate_advice_stream(initial_state):
        reasoning_parts.append(token)
        yield {"type": "token", "data": token}
    
    # 完成
    yield {"type": "done", "data": None}
