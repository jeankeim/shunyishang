#!/usr/bin/env python3
"""
扩充种子数据库：新增 50 条物品（ITEM_101 ~ ITEM_150）
覆盖当前种子库在场景、五行、季节、功能等方面的缺口
"""

import json
from pathlib import Path

SEED_PATH = Path(__file__).parent.parent / "data" / "seeds" / "seed_data_100_enhanced.json"

def build_item(
    item_id: int,
    name: str,
    category: str,
    color_name: str,
    color_hex: str,
    color_element: str,
    color_secondary,
    energy: float,
    color_note: str,
    fabric_name: str,
    fabric_element: str,
    fabric_secondary,
    touch: str,
    weight: str,
    blend: dict,
    shape: str,
    details: list,
    wuxing_scores: dict,
    tags: list,
    gender: str,
    weather: list,
    seasons: list,
    temp_min: int,
    temp_max: int,
    func: dict,
    thickness: str,
    confidence: float = 1.0,
):
    return {
        "物品 ID": f"ITEM_{item_id:03d}",
        "物品名称": name,
        "分类": category,
        "属性详情": {
            "颜色": {
                "名称": color_name,
                "色值": color_hex,
                "主五行": color_element,
                "次五行": color_secondary,
                "能量强度": energy,
                "标注备注": color_note,
            },
            "面料": {
                "名称": fabric_name,
                "主五行": fabric_element,
                "次五行": fabric_secondary,
                "触感": touch,
                "克重": weight,
                "混纺比例": blend,
            },
            "款式": {
                "形状": shape,
                "细节": details,
                "综合五行得分": wuxing_scores,
            },
        },
        "适用标签": tags,
        "元数据": {"置信度": confidence, "版本": "v2.0"},
        "适用性别": gender,
        "适用天气": weather,
        "适用季节": seasons,
        "适用温度范围": {"最低": temp_min, "最高": temp_max},
        "功能性": func,
        "厚度等级": thickness,
    }


def generate_new_items() -> list:
    items = []
    
    # ================================================================
    # 运动场景（当前仅4件，严重不足）- 8件
    # ================================================================
    
    # ITEM_101: 运动速干T恤 - 火
    items.append(build_item(101,
        name="荧光绿运动速干T恤", category="上装",
        color_name="荧光绿", color_hex="#39FF14", color_element="木", color_secondary="火",
        energy=0.8, color_note="木火相生，运动活力色",
        fabric_name="聚酯纤维", fabric_element="火", fabric_secondary="金",
        touch="干爽顺滑", weight="极轻", blend={"聚酯纤维": 0.92, "氨纶": 0.08},
        shape="短袖T形", details=["圆领", "反光条", "网眼透气区"],
        wuxing_scores={"木": 0.6, "火": 0.4},
        tags=["运动", "速干", "透气", "户外", "跑步"],
        gender="中性", weather=["炎热", "晴天"], seasons=["夏", "春"],
        temp_min=20, temp_max=40,
        func={"防水": False, "透气": True, "保暖": False, "速干": True, "防晒": True, "弹性": True},
        thickness="极薄",
    ))
    
    # ITEM_102: 运动短裤 - 火
    items.append(build_item(102,
        name="黑色运动短裤", category="下装",
        color_name="黑色", color_hex="#1A1A1A", color_element="水", color_secondary=None,
        energy=0.9, color_note="纯水能量，百搭运动色",
        fabric_name="聚酯纤维", fabric_element="火", fabric_secondary="金",
        touch="干爽顺滑", weight="极轻", blend={"聚酯纤维": 0.90, "氨纶": 0.10},
        shape="短裤", details=["松紧腰带", "侧口袋", "内衬防走光"],
        wuxing_scores={"水": 0.7, "火": 0.3},
        tags=["运动", "速干", "透气", "日常", "夏季"],
        gender="中性", weather=["炎热", "晴天"], seasons=["夏"],
        temp_min=25, temp_max=40,
        func={"防水": False, "透气": True, "保暖": False, "速干": True, "防晒": False, "弹性": True},
        thickness="极薄",
    ))
    
    # ITEM_103: 跑鞋 - 金
    items.append(build_item(103,
        name="白蓝配色专业跑鞋", category="鞋履",
        color_name="白蓝", color_hex="#E8F0FE", color_element="金", color_secondary="水",
        energy=0.85, color_note="金水相生，清爽运动感",
        fabric_name="网布+橡胶", fabric_element="金", fabric_secondary="土",
        touch="轻盈弹软", weight="轻", blend={"网布": 0.5, "橡胶": 0.3, "EVA": 0.2},
        shape="低帮运动鞋", details=["气垫减震", "透气网面", "防滑橡胶底"],
        wuxing_scores={"金": 0.6, "水": 0.4},
        tags=["运动", "跑步", "透气", "户外"],
        gender="中性", weather=["晴天", "多云"], seasons=["春", "夏", "秋"],
        temp_min=10, temp_max=35,
        func={"防水": False, "透气": True, "保暖": False, "速干": False, "防晒": False, "弹性": True},
        thickness="轻薄",
    ))
    
    # ITEM_104: 瑜伽裤 - 木
    items.append(build_item(104,
        name="深紫色高弹瑜伽裤", category="下装",
        color_name="深紫", color_hex="#4B0082", color_element="火", color_secondary="水",
        energy=0.75, color_note="火水既济，沉稳优雅",
        fabric_name="锦纶氨纶", fabric_element="水", fabric_secondary="木",
        touch="丝滑紧贴", weight="轻", blend={"锦纶": 0.80, "氨纶": 0.20},
        shape="紧身长裤", details=["高腰收腹", "四向弹力", "隐藏腰袋"],
        wuxing_scores={"火": 0.5, "水": 0.3, "木": 0.2},
        tags=["运动", "瑜伽", "弹性", "修身", "日常"],
        gender="女", weather=["晴天", "温和"], seasons=["春", "秋", "夏"],
        temp_min=15, temp_max=32,
        func={"防水": False, "透气": True, "保暖": False, "速干": True, "防晒": False, "弹性": True},
        thickness="轻薄",
    ))
    
    # ITEM_105: 运动背心 - 金
    items.append(build_item(105,
        name="银灰色运动背心", category="上装",
        color_name="银灰", color_hex="#C0C0C0", color_element="金", color_secondary=None,
        energy=0.8, color_note="纯金能量，科技感",
        fabric_name="冰丝面料", fabric_element="水", fabric_secondary="金",
        touch="冰凉丝滑", weight="极轻", blend={"锦纶": 0.85, "氨纶": 0.15},
        shape="背心", details=["工字背", "冰感科技", "防紫外线"],
        wuxing_scores={"金": 0.7, "水": 0.3},
        tags=["运动", "透气", "夏季", "防晒"],
        gender="中性", weather=["炎热", "晴天"], seasons=["夏"],
        temp_min=25, temp_max=42,
        func={"防水": False, "透气": True, "保暖": False, "速干": True, "防晒": True, "弹性": True},
        thickness="极薄",
    ))
    
    # ITEM_106: 运动外套 - 水
    items.append(build_item(106,
        name="藏蓝色防风运动外套", category="外套",
        color_name="藏蓝", color_hex="#003153", color_element="水", color_secondary="木",
        energy=0.85, color_note="深水带木，沉稳有活力",
        fabric_name="尼龙防风面料", fabric_element="金", fabric_secondary="水",
        touch="光滑挺括", weight="轻", blend={"尼龙": 0.90, "氨纶": 0.10},
        shape="拉链立领", details=["防风立领", "反光元素", "可收纳口袋"],
        wuxing_scores={"水": 0.6, "金": 0.3, "木": 0.1},
        tags=["运动", "户外", "防风", "春秋"],
        gender="中性", weather=["多云", "雨天"], seasons=["春", "秋"],
        temp_min=10, temp_max=25,
        func={"防水": True, "透气": True, "保暖": False, "速干": False, "防晒": False, "弹性": True},
        thickness="轻薄",
    ))
    
    # ITEM_107: 运动头带 - 火
    items.append(build_item(107,
        name="红色运动吸汗头带", category="配饰",
        color_name="红色", color_hex="#FF0000", color_element="火", color_secondary=None,
        energy=0.9, color_note="纯火能量，运动激情",
        fabric_name="棉质弹力布", fabric_element="木", fabric_secondary="火",
        touch="柔软吸汗", weight="极轻", blend={"棉": 0.85, "氨纶": 0.15},
        shape="环形带状", details=["加宽吸汗区", "防滑硅胶条"],
        wuxing_scores={"火": 0.8, "木": 0.2},
        tags=["运动", "吸汗", "跑步", "健身"],
        gender="中性", weather=["炎热", "晴天"], seasons=["春", "夏", "秋"],
        temp_min=15, temp_max=38,
        func={"防水": False, "透气": True, "保暖": False, "速干": True, "防晒": False, "弹性": True},
        thickness="极薄",
    ))
    
    # ITEM_108: 运动水壶腰包 - 土
    items.append(build_item(108,
        name="卡其色运动腰包", category="配饰",
        color_name="卡其", color_hex="#C3B091", color_element="土", color_secondary=None,
        energy=0.7, color_note="纯土能量，自然户外",
        fabric_name="防水尼龙", fabric_element="水", fabric_secondary="土",
        touch="光滑耐磨", weight="轻", blend={"尼龙": 0.95, "PU涂层": 0.05},
        shape="弧形腰包", details=["防水拉链", "弹力腰带", "多隔层"],
        wuxing_scores={"土": 0.7, "水": 0.3},
        tags=["运动", "户外", "跑步", "百搭"],
        gender="中性", weather=["晴天", "多云", "雨天"], seasons=["春", "夏", "秋"],
        temp_min=10, temp_max=35,
        func={"防水": True, "透气": False, "保暖": False, "速干": False, "防晒": False, "弹性": True},
        thickness="轻薄",
    ))
    
    # ================================================================
    # 商务/面试/出差场景（当前几乎为零）- 8件
    # ================================================================
    
    # ITEM_109: 商务衬衫 - 金
    items.append(build_item(109,
        name="浅蓝色免烫商务衬衫", category="上装",
        color_name="浅蓝", color_hex="#ADD8E6", color_element="水", color_secondary="金",
        energy=0.75, color_note="水金相生，沉稳专业",
        fabric_name="纯棉免烫面料", fabric_element="木", fabric_secondary="水",
        touch="挺括光滑", weight="轻", blend={"棉": 1.0},
        shape="长袖衬衫", details=["法式袖口", "免烫工艺", "修身剪裁"],
        wuxing_scores={"水": 0.5, "金": 0.3, "木": 0.2},
        tags=["商务", "面试", "正式", "通勤", "抗皱"],
        gender="男", weather=["温和", "晴天"], seasons=["春", "秋"],
        temp_min=15, temp_max=28,
        func={"防水": False, "透气": True, "保暖": False, "速干": False, "防晒": False, "抗皱": True},
        thickness="轻薄",
    ))
    
    # ITEM_110: 商务西装裤 - 土
    items.append(build_item(110,
        name="深灰色修身商务西裤", category="下装",
        color_name="深灰", color_hex="#4A4A4A", color_element="土", color_secondary="金",
        energy=0.8, color_note="土金相生，稳重专业",
        fabric_name="精纺羊毛", fabric_element="金", fabric_secondary="土",
        touch="细腻挺括", weight="中", blend={"羊毛": 0.95, "氨纶": 0.05},
        shape="直筒长裤", details=["中腰修身", "免烫裤线", "隐藏式弹力腰"],
        wuxing_scores={"土": 0.5, "金": 0.4, "水": 0.1},
        tags=["商务", "面试", "正式", "通勤", "抗皱"],
        gender="男", weather=["温和", "晴天", "多云"], seasons=["春", "秋", "冬"],
        temp_min=8, temp_max=25,
        func={"防水": False, "透气": True, "保暖": False, "速干": False, "防晒": False, "抗皱": True},
        thickness="适中",
    ))
    
    # ITEM_111: 商务皮鞋 - 土
    items.append(build_item(111,
        name="黑色商务牛津皮鞋", category="鞋履",
        color_name="黑色", color_hex="#0D0D0D", color_element="水", color_secondary=None,
        energy=0.9, color_note="纯水能量，最正式鞋色",
        fabric_name="头层牛皮", fabric_element="金", fabric_secondary="土",
        touch="光滑硬挺", weight="中", blend={"牛皮": 1.0},
        shape="牛津鞋", details=["三接头设计", "橡胶防滑底", "真皮鞋垫"],
        wuxing_scores={"水": 0.5, "金": 0.3, "土": 0.2},
        tags=["商务", "面试", "正式", "婚礼"],
        gender="男", weather=["晴天", "多云"], seasons=["春", "秋", "冬"],
        temp_min=5, temp_max=28,
        func={"防水": False, "透气": True, "保暖": False, "速干": False, "防晒": False},
        thickness="适中",
    ))
    
    # ITEM_112: 商务公文包 - 土
    items.append(build_item(112,
        name="棕色真皮商务公文包", category="配饰",
        color_name="棕色", color_hex="#8B4513", color_element="土", color_secondary="木",
        energy=0.85, color_note="土带木，自然稳重",
        fabric_name="头层牛皮", fabric_element="金", fabric_secondary="土",
        touch="厚实温润", weight="中", blend={"牛皮": 1.0},
        shape="方形手提包", details=["双提手", "可调节肩带", "多隔层", "笔记本夹层"],
        wuxing_scores={"土": 0.6, "金": 0.3, "木": 0.1},
        tags=["商务", "出差", "面试", "正式"],
        gender="男", weather=["晴天", "多云"], seasons=["春", "秋", "冬"],
        temp_min=0, temp_max=30,
        func={"防水": False, "透气": False, "保暖": False, "速干": False, "防晒": False},
        thickness="适中",
    ))
    
    # ITEM_113: 商务领带 - 火
    items.append(build_item(113,
        name="酒红色真丝商务领带", category="配饰",
        color_name="酒红", color_hex="#722F37", color_element="火", color_secondary="水",
        energy=0.8, color_note="火水相济，热情稳重",
        fabric_name="真丝", fabric_element="火", fabric_secondary="水",
        touch="丝滑柔亮", weight="极轻", blend={"桑蚕丝": 1.0},
        shape="标准领带形", details=["手工卷边", "可调节扣环"],
        wuxing_scores={"火": 0.6, "水": 0.4},
        tags=["商务", "面试", "婚礼", "正式"],
        gender="男", weather=["温和", "晴天"], seasons=["春", "秋", "冬"],
        temp_min=5, temp_max=25,
        func={"防水": False, "透气": True, "保暖": False, "速干": False, "防晒": False},
        thickness="轻薄",
    ))
    
    # ITEM_114: 出差轻便西装 - 金
    items.append(build_item(114,
        name="浅灰色轻便旅行西装", category="外套",
        color_name="浅灰", color_hex="#D3D3D3", color_element="金", color_secondary="水",
        energy=0.75, color_note="金水相生，轻商务",
        fabric_name="抗皱混纺", fabric_element="金", fabric_secondary="火",
        touch="挺括柔弹", weight="轻", blend={"聚酯纤维": 0.65, "粘纤": 0.30, "氨纶": 0.05},
        shape="单排扣西装", details=["半衬设计", "弹力面料", "防皱收纳"],
        wuxing_scores={"金": 0.6, "水": 0.3, "火": 0.1},
        tags=["商务", "出差", "旅行", "面试", "抗皱"],
        gender="中性", weather=["温和", "晴天", "多云"], seasons=["春", "秋"],
        temp_min=12, temp_max=28,
        func={"防水": False, "透气": True, "保暖": False, "速干": False, "防晒": False, "抗皱": True},
        thickness="轻薄",
    ))
    
    # ITEM_115: 商务女士衬衫 - 金
    items.append(build_item(115,
        name="米白色女士商务衬衫", category="上装",
        color_name="米白", color_hex="#F5F5DC", color_element="土", color_secondary="金",
        energy=0.7, color_note="土金相生，温和专业",
        fabric_name="真丝混纺", fabric_element="火", fabric_secondary="土",
        touch="丝滑挺括", weight="轻", blend={"真丝": 0.6, "聚酯纤维": 0.4},
        shape="翻领衬衫", details=["珍珠扣", "收腰剪裁", "袖口可调节"],
        wuxing_scores={"土": 0.5, "金": 0.3, "火": 0.2},
        tags=["商务", "面试", "正式", "优雅", "通勤"],
        gender="女", weather=["温和", "晴天"], seasons=["春", "秋"],
        temp_min=15, temp_max=28,
        func={"防水": False, "透气": True, "保暖": False, "速干": False, "防晒": False, "抗皱": True},
        thickness="轻薄",
    ))
    
    # ITEM_116: 商务手表 - 金
    items.append(build_item(116,
        name="银色金属商务手表", category="配饰",
        color_name="银色", color_hex="#E8E8E8", color_element="金", color_secondary=None,
        energy=0.9, color_note="纯金能量，精准专业",
        fabric_name="不锈钢+蓝宝石玻璃", fabric_element="金", fabric_secondary="水",
        touch="冰凉坚硬", weight="中", blend={"不锈钢": 0.8, "蓝宝石玻璃": 0.2},
        shape="圆形表盘", details=["日期窗口", "防水50米", "精钢表带"],
        wuxing_scores={"金": 0.8, "水": 0.2},
        tags=["商务", "面试", "正式", "百搭"],
        gender="中性", weather=["晴天", "温和"], seasons=["春", "夏", "秋", "冬"],
        temp_min=-5, temp_max=40,
        func={"防水": True, "透气": False, "保暖": False, "速干": False, "防晒": False},
        thickness="适中",
    ))
    
    # ================================================================
    # 婚礼/派对场景（当前为零）- 6件
    # ================================================================
    
    # ITEM_117: 婚礼旗袍 - 火
    items.append(build_item(117,
        name="正红色刺绣旗袍礼服", category="裙装",
        color_name="正红", color_hex="#FF0000", color_element="火", color_secondary=None,
        energy=1.0, color_note="纯火能量，喜庆热烈",
        fabric_name="织锦缎", fabric_element="火", fabric_secondary="金",
        touch="光滑华丽", weight="中", blend={"真丝": 0.7, "金属丝": 0.3},
        shape="修身旗袍", details=["立领盘扣", "开叉设计", "手工刺绣凤凰"],
        wuxing_scores={"火": 0.7, "金": 0.3},
        tags=["婚礼", "派对", "正式", "优雅", "晚宴"],
        gender="女", weather=["温和", "晴天"], seasons=["春", "秋", "冬"],
        temp_min=10, temp_max=28,
        func={"防水": False, "透气": False, "保暖": False, "速干": False, "防晒": False},
        thickness="适中",
    ))
    
    # ITEM_118: 婚礼高跟鞋 - 火
    items.append(build_item(118,
        name="红色缎面婚礼高跟鞋", category="鞋履",
        color_name="红色", color_hex="#DC143C", color_element="火", color_secondary=None,
        energy=0.9, color_note="纯火能量，喜庆优雅",
        fabric_name="缎面+真皮", fabric_element="火", fabric_secondary="土",
        touch="丝滑光亮", weight="轻", blend={"缎面": 0.6, "真皮": 0.4},
        shape="尖头细高跟", details=["8cm细跟", "蝴蝶结装饰", "真皮鞋垫"],
        wuxing_scores={"火": 0.7, "土": 0.3},
        tags=["婚礼", "派对", "晚宴", "优雅", "约会"],
        gender="女", weather=["晴天", "温和"], seasons=["春", "秋"],
        temp_min=12, temp_max=30,
        func={"防水": False, "透气": False, "保暖": False, "速干": False, "防晒": False},
        thickness="轻薄",
    ))
    
    # ITEM_119: 派对手拿包 - 金
    items.append(build_item(119,
        name="金色亮片派对手拿包", category="配饰",
        color_name="金色", color_hex="#FFD700", color_element="金", color_secondary="火",
        energy=0.9, color_note="金火相生，奢华耀眼",
        fabric_name="亮片布+金属", fabric_element="金", fabric_secondary="火",
        touch="坚硬闪亮", weight="轻", blend={"金属": 0.5, "亮片": 0.3, "绒布": 0.2},
        shape="矩形手拿包", details=["磁扣开合", "可拆卸链条", "内衬绒布"],
        wuxing_scores={"金": 0.7, "火": 0.3},
        tags=["派对", "晚宴", "婚礼", "时尚", "个性"],
        gender="女", weather=["温和", "晴天"], seasons=["春", "夏", "秋", "冬"],
        temp_min=0, temp_max=35,
        func={"防水": False, "透气": False, "保暖": False, "速干": False, "防晒": False},
        thickness="轻薄",
    ))
    
    # ITEM_120: 派对亮片连衣裙 - 金
    items.append(build_item(120,
        name="银色亮片派对连衣裙", category="裙装",
        color_name="银色", color_hex="#C0C0C0", color_element="金", color_secondary="火",
        energy=0.85, color_note="金火相映，派对焦点",
        fabric_name="亮片网纱", fabric_element="金", fabric_secondary="火",
        touch="闪亮微刺", weight="轻", blend={"亮片": 0.6, "网纱": 0.4},
        shape="A字短裙", details=["圆领无袖", "隐形拉链", "内衬防扎"],
        wuxing_scores={"金": 0.6, "火": 0.4},
        tags=["派对", "晚宴", "时尚", "个性", "亮眼"],
        gender="女", weather=["温和", "晴天"], seasons=["春", "秋", "冬"],
        temp_min=10, temp_max=28,
        func={"防水": False, "透气": False, "保暖": False, "速干": False, "防晒": False},
        thickness="轻薄",
    ))
    
    # ITEM_121: 婚礼胸花 - 木
    items.append(build_item(121,
        name="白色鲜花主题胸针", category="配饰",
        color_name="白色", color_hex="#FFFFFF", color_element="金", color_secondary="木",
        energy=0.7, color_note="金带木，纯洁生机",
        fabric_name="珍珠+合金", fabric_element="金", fabric_secondary="土",
        touch="温润光滑", weight="极轻", blend={"珍珠": 0.4, "合金": 0.4, "丝绸": 0.2},
        shape="花朵形胸针", details=["安全别针扣", "手工串珠", "微镶水钻"],
        wuxing_scores={"金": 0.5, "木": 0.3, "土": 0.2},
        tags=["婚礼", "正式", "优雅", "百搭"],
        gender="中性", weather=["晴天", "温和"], seasons=["春", "夏", "秋"],
        temp_min=10, temp_max=35,
        func={"防水": False, "透气": False, "保暖": False, "速干": False, "防晒": False},
        thickness="轻薄",
    ))
    
    # ITEM_122: 派对男士礼服 - 水
    items.append(build_item(122,
        name="黑色丝绒男士礼服套装", category="外套",
        color_name="黑色", color_hex="#0A0A0A", color_element="水", color_secondary=None,
        energy=0.95, color_note="纯水能量，极致正式",
        fabric_name="丝绒", fabric_element="水", fabric_secondary="火",
        touch="柔滑厚重", weight="中", blend={"真丝绒": 0.7, "聚酯纤维": 0.3},
        shape="戗驳领礼服", details=["缎面翻领", "单粒扣", "侧开叉"],
        wuxing_scores={"水": 0.7, "火": 0.3},
        tags=["派对", "婚礼", "晚宴", "正式", "优雅"],
        gender="男", weather=["温和", "寒冷"], seasons=["秋", "冬"],
        temp_min=5, temp_max=22,
        func={"防水": False, "透气": False, "保暖": False, "速干": False, "防晒": False},
        thickness="适中",
    ))
    
    # ================================================================
    # 约会场景（当前仅2件）- 5件
    # ================================================================
    
    # ITEM_123: 约会连衣裙 - 木
    items.append(build_item(123,
        name="浅粉色雪纺碎花连衣裙", category="裙装",
        color_name="浅粉", color_hex="#FFB6C1", color_element="火", color_secondary="木",
        energy=0.7, color_note="火木相生，甜美温柔",
        fabric_name="雪纺", fabric_element="火", fabric_secondary="水",
        touch="轻柔飘逸", weight="极轻", blend={"聚酯纤维": 1.0},
        shape="A字中长裙", details=["方领泡泡袖", "碎花印花", "收腰系带"],
        wuxing_scores={"火": 0.5, "木": 0.4, "水": 0.1},
        tags=["约会", "日常", "优雅", "春季", "甜美"],
        gender="女", weather=["晴天", "温和"], seasons=["春", "夏"],
        temp_min=18, temp_max=32,
        func={"防水": False, "透气": True, "保暖": False, "速干": False, "防晒": False},
        thickness="极薄",
    ))
    
    # ITEM_124: 约会针织衫 - 火
    items.append(build_item(124,
        name="奶白色慵懒风针织开衫", category="上装",
        color_name="奶白", color_hex="#FFFDD0", color_element="土", color_secondary="金",
        energy=0.65, color_note="土金相生，温柔知性",
        fabric_name="马海毛混纺", fabric_element="木", fabric_secondary="火",
        touch="蓬松柔软", weight="轻", blend={"马海毛": 0.5, "腈纶": 0.5},
        shape="开衫", details=["落肩设计", "珍珠扣", "口袋贴袋"],
        wuxing_scores={"土": 0.5, "木": 0.3, "金": 0.2},
        tags=["约会", "日常", "休闲", "温柔", "春秋"],
        gender="女", weather=["温和", "多云"], seasons=["春", "秋"],
        temp_min=15, temp_max=25,
        func={"防水": False, "透气": True, "保暖": False, "速干": False, "防晒": False},
        thickness="轻薄",
    ))
    
    # ITEM_125: 约会男士Polo - 土
    items.append(build_item(125,
        name="深蓝色丝光棉Polo衫", category="上装",
        color_name="深蓝", color_hex="#00008B", color_element="水", color_secondary=None,
        energy=0.8, color_note="纯水能量，沉稳可靠",
        fabric_name="丝光棉", fabric_element="火", fabric_secondary="水",
        touch="丝滑挺括", weight="轻", blend={"棉": 1.0},
        shape="Polo衫", details=["翻领", "两粒扣", "修身版型"],
        wuxing_scores={"水": 0.6, "火": 0.4},
        tags=["约会", "日常", "商务", "通勤", "休闲"],
        gender="男", weather=["温和", "晴天"], seasons=["春", "夏", "秋"],
        temp_min=18, temp_max=32,
        func={"防水": False, "透气": True, "保暖": False, "速干": False, "防晒": False},
        thickness="轻薄",
    ))
    
    # ITEM_126: 约会香水 - 水
    items.append(build_item(126,
        name="清新木质调淡香水", category="配饰",
        color_name="透明", color_hex="#E0E8F0", color_element="水", color_secondary="木",
        energy=0.7, color_note="水木相生，清雅脱俗",
        fabric_name="玻璃瓶+酒精", fabric_element="水", fabric_secondary="火",
        touch="冰凉液态", weight="轻", blend={"酒精": 0.8, "香精": 0.15, "水": 0.05},
        shape="圆柱瓶身", details=["喷雾头", "50ml容量", "木质调前中后调"],
        wuxing_scores={"水": 0.6, "木": 0.4},
        tags=["约会", "日常", "优雅", "百搭"],
        gender="中性", weather=["晴天", "温和"], seasons=["春", "夏", "秋", "冬"],
        temp_min=-5, temp_max=40,
        func={"防水": False, "透气": False, "保暖": False, "速干": False, "防晒": False},
        thickness="轻薄",
    ))
    
    # ITEM_127: 约会女士单鞋 - 土
    items.append(build_item(127,
        name="裸粉色尖头平底单鞋", category="鞋履",
        color_name="裸粉", color_hex="#E8C4B8", color_element="土", color_secondary="火",
        energy=0.7, color_note="土火相生，温柔自然",
        fabric_name="羊皮", fabric_element="金", fabric_secondary="土",
        touch="柔软细腻", weight="轻", blend={"羊皮": 1.0},
        shape="尖头平底", details=["蝴蝶结装饰", "真皮鞋垫", "橡胶防滑底"],
        wuxing_scores={"土": 0.6, "火": 0.3, "金": 0.1},
        tags=["约会", "日常", "优雅", "通勤"],
        gender="女", weather=["晴天", "温和"], seasons=["春", "夏", "秋"],
        temp_min=12, temp_max=32,
        func={"防水": False, "透气": True, "保暖": False, "速干": False, "防晒": False},
        thickness="轻薄",
    ))
    
    # ================================================================
    # 居家场景（当前仅3件）- 4件
    # ================================================================
    
    # ITEM_128: 居家睡衣套装 - 水
    items.append(build_item(128,
        name="浅蓝色纯棉睡衣套装", category="上装",
        color_name="浅蓝", color_hex="#B0C4DE", color_element="水", color_secondary="木",
        energy=0.5, color_note="水木相生，安宁助眠",
        fabric_name="纯棉纱布", fabric_element="木", fabric_secondary="水",
        touch="柔软亲肤", weight="轻", blend={"棉": 1.0},
        shape="长袖套装", details=["圆领", "松紧腰", "侧口袋"],
        wuxing_scores={"水": 0.5, "木": 0.3, "土": 0.2},
        tags=["居家", "睡衣", "舒适", "休闲"],
        gender="中性", weather=["温和", "晴天"], seasons=["春", "秋"],
        temp_min=18, temp_max=28,
        func={"防水": False, "透气": True, "保暖": False, "速干": False, "防晒": False},
        thickness="轻薄",
    ))
    
    # ITEM_129: 居家棉拖鞋 - 土
    items.append(build_item(129,
        name="灰色棉麻居家拖鞋", category="鞋履",
        color_name="灰色", color_hex="#808080", color_element="土", color_secondary=None,
        energy=0.5, color_note="纯土能量，安稳居家",
        fabric_name="棉麻+亚麻底", fabric_element="木", fabric_secondary="土",
        touch="柔软透气", weight="轻", blend={"棉麻": 0.7, "亚麻": 0.3},
        shape="半包拖鞋", details=["加厚鞋垫", "防滑底纹", "可机洗"],
        wuxing_scores={"土": 0.7, "木": 0.3},
        tags=["居家", "舒适", "休闲", "百搭"],
        gender="中性", weather=["温和", "寒冷"], seasons=["春", "秋", "冬"],
        temp_min=10, temp_max=30,
        func={"防水": False, "透气": True, "保暖": False, "速干": False, "防晒": False},
        thickness="适中",
    ))
    
    # ITEM_130: 居家浴袍 - 水
    items.append(build_item(130,
        name="白色华夫格浴袍", category="上装",
        color_name="白色", color_hex="#FFFFFF", color_element="金", color_secondary="水",
        energy=0.5, color_note="金水相生，洁净放松",
        fabric_name="华夫格棉", fabric_element="木", fabric_secondary="金",
        touch="蓬松吸水", weight="中", blend={"棉": 1.0},
        shape="长款浴袍", details=["腰带系结", "双口袋", "及膝长度"],
        wuxing_scores={"金": 0.5, "水": 0.3, "木": 0.2},
        tags=["居家", "舒适", "休闲", "百搭"],
        gender="中性", weather=["温和", "寒冷"], seasons=["春", "秋", "冬"],
        temp_min=15, temp_max=30,
        func={"防水": False, "透气": True, "保暖": False, "速干": True, "防晒": False},
        thickness="适中",
    ))
    
    # ITEM_131: 居家卫衣 - 木
    items.append(build_item(131,
        name="燕麦色宽松连帽卫衣", category="上装",
        color_name="燕麦", color_hex="#D2B48C", color_element="土", color_secondary="木",
        energy=0.55, color_note="土木相生，自然放松",
        fabric_name="纯棉毛圈", fabric_element="木", fabric_secondary="土",
        touch="柔软厚实", weight="中", blend={"棉": 1.0},
        shape="连帽卫衣", details=["袋鼠兜", "罗纹袖口", "抽绳帽"],
        wuxing_scores={"土": 0.5, "木": 0.4, "水": 0.1},
        tags=["居家", "休闲", "舒适", "日常", "百搭"],
        gender="中性", weather=["温和", "多云"], seasons=["春", "秋"],
        temp_min=15, temp_max=25,
        func={"防水": False, "透气": True, "保暖": False, "速干": False, "防晒": False},
        thickness="适中",
    ))
    
    # ================================================================
    # 旅行场景（当前为零）- 5件
    # ================================================================
    
    # ITEM_132: 旅行防晒衣 - 金
    items.append(build_item(132,
        name="薄荷绿轻薄防晒衣", category="外套",
        color_name="薄荷绿", color_hex="#98FF98", color_element="木", color_secondary="火",
        energy=0.7, color_note="木火相生，清新活力",
        fabric_name="锦纶防晒面料", fabric_element="水", fabric_secondary="木",
        touch="冰丝凉爽", weight="极轻", blend={"锦纶": 0.92, "氨纶": 0.08},
        shape="连帽薄外套", details=["UPF50+防晒", "可收纳成小包", "弹力袖口"],
        wuxing_scores={"木": 0.5, "水": 0.3, "火": 0.2},
        tags=["旅行", "户外", "防晒", "夏季", "百搭"],
        gender="中性", weather=["炎热", "晴天"], seasons=["夏"],
        temp_min=25, temp_max=42,
        func={"防水": False, "透气": True, "保暖": False, "速干": True, "防晒": True, "弹性": True},
        thickness="极薄",
    ))
    
    # ITEM_133: 旅行百搭T恤 - 土
    items.append(build_item(133,
        name="白色纯棉百搭T恤", category="上装",
        color_name="白色", color_hex="#FAFAFA", color_element="金", color_secondary=None,
        energy=0.7, color_note="纯金能量，干净百搭",
        fabric_name="精梳棉", fabric_element="木", fabric_secondary="金",
        touch="柔软舒适", weight="轻", blend={"棉": 1.0},
        shape="圆领T恤", details=["领口加固", "预缩处理", "不变形"],
        wuxing_scores={"金": 0.6, "木": 0.4},
        tags=["旅行", "日常", "百搭", "夏季", "休闲"],
        gender="中性", weather=["炎热", "晴天"], seasons=["春", "夏"],
        temp_min=20, temp_max=38,
        func={"防水": False, "透气": True, "保暖": False, "速干": False, "防晒": False},
        thickness="轻薄",
    ))
    
    # ITEM_134: 旅行舒适运动鞋 - 木
    items.append(build_item(134,
        name="米色轻便休闲运动鞋", category="鞋履",
        color_name="米色", color_hex="#F5F5DC", color_element="土", color_secondary="木",
        energy=0.7, color_note="土木相生，自然舒适",
        fabric_name="飞织面料", fabric_element="木", fabric_secondary="土",
        touch="柔软弹弹", weight="轻", blend={"飞织面料": 0.6, "EVA": 0.25, "橡胶": 0.15},
        shape="低帮休闲鞋", details=["一脚蹬设计", "记忆棉鞋垫", "轻量底"],
        wuxing_scores={"土": 0.5, "木": 0.4, "水": 0.1},
        tags=["旅行", "日常", "舒适", "百搭", "步行"],
        gender="中性", weather=["晴天", "多云", "温和"], seasons=["春", "夏", "秋"],
        temp_min=12, temp_max=35,
        func={"防水": False, "透气": True, "保暖": False, "速干": False, "防晒": False, "弹性": True},
        thickness="轻薄",
    ))
    
    # ITEM_135: 旅行折叠帽 - 木
    items.append(build_item(135,
        name="原色棉麻渔夫帽", category="配饰",
        color_name="原色", color_hex="#F0E6D3", color_element="土", color_secondary="木",
        energy=0.6, color_note="土木相生，自然文艺",
        fabric_name="棉麻", fabric_element="木", fabric_secondary="土",
        touch="干爽透气", weight="极轻", blend={"棉": 0.6, "亚麻": 0.4},
        shape="渔夫帽", details=["可折叠", "防风绳", "宽帽檐"],
        wuxing_scores={"土": 0.5, "木": 0.5},
        tags=["旅行", "户外", "防晒", "百搭", "休闲"],
        gender="中性", weather=["炎热", "晴天"], seasons=["春", "夏"],
        temp_min=20, temp_max=40,
        func={"防水": False, "透气": True, "保暖": False, "速干": False, "防晒": True},
        thickness="轻薄",
    ))
    
    # ITEM_136: 旅行速干裤 - 水
    items.append(build_item(136,
        name="深灰色速干旅行裤", category="下装",
        color_name="深灰", color_hex="#505050", color_element="土", color_secondary="金",
        energy=0.7, color_note="土金相生，实用稳重",
        fabric_name="尼龙速干面料", fabric_element="水", fabric_secondary="金",
        touch="光滑凉爽", weight="轻", blend={"尼龙": 0.90, "氨纶": 0.10},
        shape="直筒长裤", details=["松紧+抽绳腰", "拉链口袋", "可卷裤脚"],
        wuxing_scores={"土": 0.5, "水": 0.3, "金": 0.2},
        tags=["旅行", "户外", "速干", "百搭", "舒适"],
        gender="中性", weather=["温和", "晴天", "雨天"], seasons=["春", "夏", "秋"],
        temp_min=15, temp_max=35,
        func={"防水": True, "透气": True, "保暖": False, "速干": True, "防晒": False, "弹性": True},
        thickness="轻薄",
    ))
    
    # ================================================================
    # 户外探险（补充）- 4件
    # ================================================================
    
    # ITEM_137: 冲锋衣 - 水
    items.append(build_item(137,
        name="橙色防水冲锋衣", category="外套",
        color_name="橙色", color_hex="#FF8C00", color_element="土", color_secondary="火",
        energy=0.85, color_note="土火相生，户外醒目安全色",
        fabric_name="GORE-TEX面料", fabric_element="水", fabric_secondary="金",
        touch="硬挺光滑", weight="中", blend={"GORE-TEX": 0.8, "尼龙": 0.2},
        shape="连帽冲锋衣", details=["全压胶防水", "可拆卸帽", "腋下透气拉链"],
        wuxing_scores={"土": 0.4, "水": 0.4, "火": 0.2},
        tags=["户外", "登山", "防水", "防风", "探险"],
        gender="中性", weather=["雨天", "寒冷", "多云"], seasons=["春", "秋", "冬"],
        temp_min=-10, temp_max=20,
        func={"防水": True, "透气": True, "保暖": False, "速干": False, "防晒": False},
        thickness="中厚",
    ))
    
    # ITEM_138: 登山鞋 - 土
    items.append(build_item(138,
        name="棕色高帮防水登山鞋", category="鞋履",
        color_name="棕色", color_hex="#6B4226", color_element="土", color_secondary="木",
        energy=0.85, color_note="土木相生，大地色系",
        fabric_name="翻毛皮+尼龙", fabric_element="土", fabric_secondary="金",
        touch="厚实耐磨", weight="厚", blend={"翻毛皮": 0.6, "尼龙": 0.3, "橡胶": 0.1},
        shape="高帮登山鞋", details=["Vibram大底", "防水内衬", "护趾设计"],
        wuxing_scores={"土": 0.6, "金": 0.3, "木": 0.1},
        tags=["户外", "登山", "防水", "耐磨", "探险"],
        gender="中性", weather=["雨天", "寒冷", "多云"], seasons=["春", "秋", "冬"],
        temp_min=-15, temp_max=25,
        func={"防水": True, "透气": True, "保暖": True, "速干": False, "防晒": False},
        thickness="厚重",
    ))
    
    # ITEM_139: 户外抓绒衣 - 火
    items.append(build_item(139,
        name="黑色摇粒绒保暖上衣", category="上装",
        color_name="黑色", color_hex="#111111", color_element="水", color_secondary=None,
        energy=0.8, color_note="纯水能量，户外百搭",
        fabric_name="摇粒绒", fabric_element="火", fabric_secondary="土",
        touch="蓬松温暖", weight="轻", blend={"聚酯纤维": 1.0},
        shape="拉链立领", details=["立领防风", "双口袋", "可外穿可内胆"],
        wuxing_scores={"水": 0.5, "火": 0.5},
        tags=["户外", "保暖", "登山", "冬季", "百搭"],
        gender="中性", weather=["寒冷", "多云"], seasons=["秋", "冬"],
        temp_min=-15, temp_max=10,
        func={"防水": False, "透气": True, "保暖": True, "速干": True, "防晒": False},
        thickness="中厚",
    ))
    
    # ITEM_140: 户外手套 - 金
    items.append(build_item(140,
        name="黑色触屏户外手套", category="配饰",
        color_name="黑色", color_hex="#1A1A1A", color_element="水", color_secondary=None,
        energy=0.75, color_note="纯水能量，实用百搭",
        fabric_name="防风面料+抓绒", fabric_element="火", fabric_secondary="金",
        touch="温暖灵活", weight="轻", blend={"尼龙": 0.5, "抓绒": 0.3, "导电纤维": 0.2},
        shape="五指手套", details=["触屏指尖", "防滑掌心", "弹力腕口"],
        wuxing_scores={"水": 0.6, "火": 0.4},
        tags=["户外", "保暖", "登山", "冬季", "骑行"],
        gender="中性", weather=["寒冷"], seasons=["秋", "冬"],
        temp_min=-20, temp_max=10,
        func={"防水": True, "透气": False, "保暖": True, "速干": False, "防晒": False},
        thickness="中厚",
    ))
    
    # ================================================================
    # 五行平衡补充（木行仅16件，需额外补充）- 5件
    # ================================================================
    
    # ITEM_141: 木属性裙装 - 木
    items.append(build_item(141,
        name="翠绿色棉麻A字裙", category="裙装",
        color_name="翠绿", color_hex="#00A550", color_element="木", color_secondary=None,
        energy=0.85, color_note="纯木能量，强补木单品",
        fabric_name="棉麻", fabric_element="木", fabric_secondary="水",
        touch="干爽自然", weight="轻", blend={"棉": 0.6, "亚麻": 0.4},
        shape="A字中裙", details=["松紧腰", "侧口袋", "自然褶皱"],
        wuxing_scores={"木": 0.8, "水": 0.2},
        tags=["日常", "休闲", "补木", "夏季", "文艺"],
        gender="女", weather=["温和", "晴天"], seasons=["春", "夏"],
        temp_min=18, temp_max=33,
        func={"防水": False, "透气": True, "保暖": False, "速干": False, "防晒": False},
        thickness="轻薄",
    ))
    
    # ITEM_142: 木属性外套 - 木
    items.append(build_item(142,
        name="军绿色工装夹克", category="外套",
        color_name="军绿", color_hex="#556B2F", color_element="木", color_secondary="土",
        energy=0.8, color_note="木带土，自然实用",
        fabric_name="纯棉帆布", fabric_element="木", fabric_secondary="土",
        touch="厚实粗犷", weight="厚", blend={"棉": 1.0},
        shape="工装夹克", details=["多口袋设计", "按扣翻领", "可调节袖口"],
        wuxing_scores={"木": 0.7, "土": 0.3},
        tags=["户外", "日常", "休闲", "百搭", "春秋"],
        gender="中性", weather=["温和", "多云"], seasons=["春", "秋"],
        temp_min=10, temp_max=25,
        func={"防水": False, "透气": True, "保暖": False, "速干": False, "防晒": False},
        thickness="适中",
    ))
    
    # ITEM_143: 木属性下装 - 木
    items.append(build_item(143,
        name="青绿色直筒休闲裤", category="下装",
        color_name="青绿", color_hex="#4CBB17", color_element="木", color_secondary="水",
        energy=0.8, color_note="木水相生，清新自然",
        fabric_name="纯棉斜纹布", fabric_element="木", fabric_secondary="土",
        touch="柔软厚实", weight="中", blend={"棉": 0.98, "氨纶": 0.02},
        shape="直筒长裤", details=["中腰设计", "金属拉链", "后贴袋"],
        wuxing_scores={"木": 0.7, "水": 0.2, "土": 0.1},
        tags=["日常", "休闲", "补木", "通勤", "百搭"],
        gender="中性", weather=["温和", "晴天"], seasons=["春", "秋"],
        temp_min=12, temp_max=28,
        func={"防水": False, "透气": True, "保暖": False, "速干": False, "防晒": False},
        thickness="适中",
    ))
    
    # ITEM_144: 冬季围巾 - 水
    items.append(build_item(144,
        name="深蓝色羊绒围巾", category="配饰",
        color_name="深蓝", color_hex="#000080", color_element="水", color_secondary="木",
        energy=0.85, color_note="深水带木，温暖知性",
        fabric_name="羊绒", fabric_element="水", fabric_secondary="火",
        touch="极致柔软", weight="轻", blend={"羊绒": 1.0},
        shape="长条围巾", details=["流苏边", "双面可用", "200cm×30cm"],
        wuxing_scores={"水": 0.7, "木": 0.3},
        tags=["冬季", "保暖", "商务", "百搭", "优雅"],
        gender="中性", weather=["寒冷"], seasons=["冬"],
        temp_min=-15, temp_max=10,
        func={"防水": False, "透气": True, "保暖": True, "速干": False, "防晒": False},
        thickness="中厚",
    ))
    
    # ITEM_145: 夏季凉鞋 - 火
    items.append(build_item(145,
        name="棕色真皮编织凉鞋", category="鞋履",
        color_name="棕色", color_hex="#A0522D", color_element="土", color_secondary="火",
        energy=0.7, color_note="土火相生，自然休闲",
        fabric_name="真皮编织", fabric_element="土", fabric_secondary="火",
        touch="柔软透气", weight="轻", blend={"牛皮": 1.0},
        shape="露趾凉鞋", details=["魔术贴", "软木鞋垫", "防滑橡胶底"],
        wuxing_scores={"土": 0.5, "火": 0.3, "木": 0.2},
        tags=["夏季", "休闲", "度假", "日常", "透气"],
        gender="中性", weather=["炎热", "晴天"], seasons=["夏"],
        temp_min=25, temp_max=40,
        func={"防水": False, "透气": True, "保暖": False, "速干": False, "防晒": False},
        thickness="极薄",
    ))
    
    # ================================================================
    # 极端温度补充（极寒/极热覆盖不足）- 5件
    # ================================================================
    
    # ITEM_146: 极寒羽绒服 - 水
    items.append(build_item(146,
        name="黑色极寒鹅绒羽绒服", category="外套",
        color_name="黑色", color_hex="#0D0D0D", color_element="水", color_secondary=None,
        energy=0.9, color_note="纯水能量，极寒守护",
        fabric_name="鹅绒填充+防风面料", fabric_element="水", fabric_secondary="金",
        touch="蓬松温暖", weight="厚", blend={"鹅绒": 0.9, "防风面料": 0.1},
        shape="长款羽绒服", details=["毛领可拆卸", "防风袖口", "YKK拉链", "内袋"],
        wuxing_scores={"水": 0.7, "金": 0.3},
        tags=["冬季", "极寒", "保暖", "户外", "百搭"],
        gender="中性", weather=["寒冷"], seasons=["冬"],
        temp_min=-30, temp_max=0,
        func={"防水": True, "透气": False, "保暖": True, "速干": False, "防晒": False},
        thickness="厚重",
    ))
    
    # ITEM_147: 极热亚麻套装 - 木
    items.append(build_item(147,
        name="本白色亚麻短袖套装", category="上装",
        color_name="本白", color_hex="#FAF0E6", color_element="土", color_secondary="金",
        energy=0.6, color_note="土金相生，清凉素雅",
        fabric_name="纯亚麻", fabric_element="木", fabric_secondary="水",
        touch="干爽粗犷", weight="极轻", blend={"亚麻": 1.0},
        shape="短袖衬衫+短裤套装", details=["衬衫翻领", "短裤松紧腰", "天然褶皱"],
        wuxing_scores={"土": 0.4, "木": 0.4, "金": 0.2},
        tags=["夏季", "居家", "休闲", "度假", "透气"],
        gender="中性", weather=["炎热"], seasons=["夏"],
        temp_min=28, temp_max=42,
        func={"防水": False, "透气": True, "保暖": False, "速干": True, "防晒": False},
        thickness="极薄",
    ))
    
    # ITEM_148: 冬季保暖内衣 - 火
    items.append(build_item(148,
        name="黑色发热纤维保暖内衣套装", category="上装",
        color_name="黑色", color_hex="#1A1A1A", color_element="水", color_secondary=None,
        energy=0.7, color_note="纯水能量，贴身保暖",
        fabric_name="发热纤维", fabric_element="火", fabric_secondary="土",
        touch="柔软发热", weight="轻", blend={"腈纶": 0.5, "粘纤": 0.3, "氨纶": 0.2},
        shape="圆领套装", details=["发热科技", "四向弹力", "无缝拼接"],
        wuxing_scores={"水": 0.5, "火": 0.5},
        tags=["冬季", "保暖", "居家", "打底", "百搭"],
        gender="中性", weather=["寒冷"], seasons=["冬"],
        temp_min=-20, temp_max=10,
        func={"防水": False, "透气": True, "保暖": True, "速干": False, "防晒": False},
        thickness="中厚",
    ))
    
    # ITEM_149: 夏季冰丝裤 - 水
    items.append(build_item(149,
        name="浅灰色冰丝阔腿裤", category="下装",
        color_name="浅灰", color_hex="#D3D3D3", color_element="金", color_secondary="水",
        energy=0.65, color_note="金水相生，冰凉垂坠",
        fabric_name="冰丝面料", fabric_element="水", fabric_secondary="金",
        touch="冰凉丝滑", weight="极轻", blend={"粘纤": 0.7, "聚酯纤维": 0.3},
        shape="阔腿长裤", details=["松紧腰", "垂坠感", "侧口袋"],
        wuxing_scores={"金": 0.5, "水": 0.5},
        tags=["夏季", "日常", "休闲", "通勤", "透气"],
        gender="女", weather=["炎热"], seasons=["夏"],
        temp_min=28, temp_max=40,
        func={"防水": False, "透气": True, "保暖": False, "速干": True, "防晒": False},
        thickness="极薄",
    ))
    
    # ITEM_150: 雨天防水鞋 - 水
    items.append(build_item(150,
        name="黑色防水切尔西雨靴", category="鞋履",
        color_name="黑色", color_hex="#0D0D0D", color_element="水", color_secondary=None,
        energy=0.85, color_note="纯水能量，雨天守护",
        fabric_name="天然橡胶", fabric_element="水", fabric_secondary="土",
        touch="光滑防水", weight="中", blend={"天然橡胶": 0.8, "EVA": 0.2},
        shape="中筒雨靴", details=["切尔西松紧边", "防滑底纹", "可调节筒高"],
        wuxing_scores={"水": 0.7, "土": 0.3},
        tags=["雨天", "户外", "防水", "日常", "百搭"],
        gender="中性", weather=["雨天"], seasons=["春", "秋", "冬"],
        temp_min=0, temp_max=25,
        func={"防水": True, "透气": False, "保暖": False, "速干": False, "防晒": False},
        thickness="适中",
    ))
    
    return items


def main():
    # 读取现有数据
    with open(SEED_PATH, "r", encoding="utf-8") as f:
        existing = json.load(f)
    
    print(f"现有数据: {len(existing)} 条")
    
    # 生成新数据
    new_items = generate_new_items()
    print(f"新增数据: {len(new_items)} 条")
    
    # 合并
    all_data = existing + new_items
    
    # 写入（覆盖原文件）
    with open(SEED_PATH, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print(f"合并后总计: {len(all_data)} 条")
    print(f"已写入: {SEED_PATH}")
    
    # 输出覆盖统计
    from collections import Counter
    cats = Counter(d.get('分类','') for d in all_data)
    elements = Counter(d.get('属性详情',{}).get('颜色',{}).get('主五行','') for d in all_data)
    thickness = Counter(d.get('厚度等级','') for d in all_data)
    
    print("\n=== 扩充后覆盖统计 ===")
    print(f"分类: {dict(cats)}")
    print(f"五行: {dict(elements)}")
    print(f"厚度: {dict(thickness)}")


if __name__ == "__main__":
    main()
