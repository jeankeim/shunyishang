#!/usr/bin/env python3
"""
物品库扩充至 500 件生成器（上线前目标）

目标约束:
1. items 总量 500 件
2. 每品类 × 每五行 ≥ 10 件
3. gender='男' ≥ 150，gender='女' ≥ 150

流程:
1. 读取 DB 现有 (品类, 五行, 性别) 分布 → 计算缺口
2. 程序化组合生成（颜色×材质×款式模板，颜色主五行决定 primary_element，
   与现有 seed 数据口径一致）
3. 写入 data/seeds/seed_data_expansion_500.json（不动存量 seed 文件）

后续入库:
  .venv/bin/python scripts/import_seed_dashscope.py --file data/seeds/seed_data_expansion_500.json

用法:
  python scripts/expand_seed_to_500.py            # 生成 JSON
  python scripts/expand_seed_to_500.py --dry-run  # 只打印分配统计
"""

import json
import random
import argparse
from pathlib import Path
from collections import Counter

import psycopg2

ROOT = Path(__file__).parent.parent
OUT_PATH = ROOT / "data" / "seeds" / "seed_data_expansion_500.json"

DB_CONFIG = {
    "host": "localhost", "port": 5432,
    "database": "wuxing_db", "user": "wuxing_user", "password": "wuxing_password",
}

TOTAL_TARGET = 500
CELL_MIN = 10          # 每品类×每五行最少件数
GENDER_TARGET = 150    # 男/女装各自最少件数
ID_START = 176         # 现有 ITEM_001~ITEM_175

ELEMS = ["木", "火", "土", "金", "水"]
CATS = ["上装", "下装", "外套", "鞋履", "配饰", "饰品", "文玩", "裙装"]

# ============================================================
# 颜色库（颜色主五行 = 物品 primary_element，与存量数据口径一致）
# ============================================================
COLORS = {
    "木": [("翠绿", "#00A550"), ("墨绿", "#014421"), ("橄榄绿", "#708238"), ("薄荷绿", "#98FF98"),
           ("竹青", "#789262"), ("草木绿", "#7BA23F"), ("青碧", "#48C0A3"), ("军绿", "#556B2F")],
    "火": [("正红", "#E60012"), ("酒红", "#722F37"), ("珊瑚粉", "#FF7F50"), ("玫红", "#D5236C"),
           ("紫红", "#8E354A"), ("砖红", "#B22222"), ("橘红", "#FF4500"), ("浅粉", "#FFB6C1")],
    "土": [("卡其", "#C3B091"), ("驼色", "#A16B47"), ("棕色", "#8B4513"), ("米黄", "#F5E8C7"),
           ("姜黄", "#E2A93B"), ("焦糖", "#C68142"), ("大地棕", "#9B7653"), ("燕麦", "#D2B48C")],
    "金": [("纯白", "#FFFFFF"), ("象牙白", "#FFFFF0"), ("银灰", "#C0C0C0"), ("香槟金", "#F7E7CE"),
           ("珍珠白", "#F8F6F0"), ("浅灰", "#D3D3D3"), ("铂金灰", "#E5E4E2"), ("亮银", "#E8E8E8")],
    "水": [("藏蓝", "#003153"), ("黑色", "#1A1A1A"), ("深蓝", "#00008B"), ("雾霾蓝", "#7A8B99"),
           ("炭灰", "#36454F"), ("靛蓝", "#2E4E7E"), ("墨黑", "#0D0D0D"), ("海军蓝", "#000080")],
}
COLOR_NOTES = {
    "木": "草木生发，清新自然", "火": "热情明快，活力振奋", "土": "沉稳厚重，安定踏实",
    "金": "清透利落，简洁高级", "水": "深邃宁静，智慧沉着",
}

# ============================================================
# 面料库: (名称, 主五行, 次五行, 触感, 克重, 混纺比例)
# ============================================================
FABRICS = {
    "精梳棉": ("木", "金", "柔软舒适", "轻", {"棉": 1.0}),
    "棉麻混纺": ("木", "土", "干爽透气", "轻", {"棉": 0.6, "亚麻": 0.4}),
    "莫代尔": ("木", "水", "丝滑亲肤", "极轻", {"莫代尔": 0.95, "氨纶": 0.05}),
    "牛仔布": ("木", "水", "厚实耐磨", "中", {"棉": 0.98, "氨纶": 0.02}),
    "灯芯绒": ("木", "土", "绒感温暖", "中", {"棉": 0.9, "氨纶": 0.1}),
    "帆布": ("木", "土", "厚实透气", "中", {"棉": 0.8, "橡胶": 0.2}),
    "飞织面料": ("木", "土", "柔软弹性", "轻", {"飞织面料": 0.6, "EVA": 0.25, "橡胶": 0.15}),
    "真丝": ("火", "水", "丝滑柔亮", "极轻", {"桑蚕丝": 1.0}),
    "聚酯纤维": ("火", "金", "干爽顺滑", "极轻", {"聚酯纤维": 0.92, "氨纶": 0.08}),
    "摇粒绒": ("火", "土", "蓬松温暖", "轻", {"聚酯纤维": 1.0}),
    "缎面": ("火", "金", "丝滑光亮", "轻", {"缎面": 0.6, "真皮": 0.4}),
    "精纺羊毛": ("金", "土", "细腻挺括", "中", {"羊毛": 0.95, "氨纶": 0.05}),
    "头层牛皮": ("金", "土", "光滑硬挺", "中", {"牛皮": 1.0}),
    "尼龙面料": ("金", "水", "光滑挺括", "轻", {"尼龙": 0.9, "氨纶": 0.1}),
    "不锈钢合金": ("金", "水", "冰凉坚硬", "中", {"不锈钢": 0.8, "玻璃": 0.2}),
    "羊绒": ("水", "火", "极致柔软", "轻", {"羊绒": 1.0}),
    "冰丝": ("水", "金", "冰凉丝滑", "极轻", {"粘纤": 0.7, "聚酯纤维": 0.3}),
    "鹅绒填充面料": ("水", "金", "蓬松保暖", "厚", {"鹅绒": 0.9, "防风面料": 0.1}),
}

# ============================================================
# 服装类款式模板
# t: 类型名; g: 可用性别; fab: 可用面料; shape: 形状; det: 细节池;
# tags: 场景标签; season/weather/temp/thick/func: 穿着条件
# ============================================================
TYPES = {
    "上装": [
        {"t": "T恤", "g": ["男", "女", "中性"], "fab": ["精梳棉", "莫代尔", "聚酯纤维"], "shape": "圆领T恤",
         "det": ["领口加固", "预缩处理", "落肩袖", "印花装饰"], "tags": ["日常", "休闲", "百搭", "旅行"],
         "season": ["春", "夏"], "weather": ["晴天", "炎热"], "temp": (20, 38), "thick": "轻薄",
         "func": {"透气": True}},
        {"t": "衬衫", "g": ["男", "女"], "fab": ["精梳棉", "棉麻混纺", "真丝"], "shape": "长袖衬衫",
         "det": ["免烫工艺", "修身剪裁", "法式袖口", "下摆开衩"], "tags": ["通勤", "商务", "面试", "正式"],
         "season": ["春", "秋"], "weather": ["晴天", "温和"], "temp": (15, 28), "thick": "轻薄",
         "func": {"透气": True, "抗皱": True}},
        {"t": "毛衣", "g": ["男", "女", "中性"], "fab": ["精纺羊毛", "羊绒"], "shape": "圆领套头衫",
         "det": ["罗纹收口", "肌理编织", "微阔版型", "半高领"], "tags": ["日常", "通勤", "保暖", "秋冬"],
         "season": ["秋", "冬"], "weather": ["寒冷", "多云"], "temp": (-5, 15), "thick": "中厚",
         "func": {"保暖": True, "透气": True}},
        {"t": "卫衣", "g": ["男", "女", "中性"], "fab": ["精梳棉", "摇粒绒"], "shape": "连帽卫衣",
         "det": ["袋鼠兜", "抽绳帽", "加绒内里", "宽松落肩"], "tags": ["日常", "休闲", "居家", "运动"],
         "season": ["春", "秋"], "weather": ["温和", "多云"], "temp": (10, 22), "thick": "适中",
         "func": {"透气": True}},
        {"t": "Polo衫", "g": ["男"], "fab": ["精梳棉", "冰丝"], "shape": "翻领Polo衫",
         "det": ["两粒扣", "修身版型", "罗纹领口", "侧开衩"], "tags": ["商务", "通勤", "日常", "约会"],
         "season": ["春", "夏", "秋"], "weather": ["晴天", "温和"], "temp": (18, 32), "thick": "轻薄",
         "func": {"透气": True}},
        {"t": "针织开衫", "g": ["女"], "fab": ["精纺羊毛", "羊绒", "莫代尔"], "shape": "开衫",
         "det": ["珍珠扣", "落肩设计", "口袋贴袋", "收腰系带"], "tags": ["约会", "通勤", "优雅", "日常"],
         "season": ["春", "秋"], "weather": ["温和", "多云"], "temp": (14, 25), "thick": "轻薄",
         "func": {"透气": True}},
        {"t": "雪纺上衣", "g": ["女"], "fab": ["真丝", "聚酯纤维"], "shape": "泡泡袖上衣",
         "det": ["方领", "碎花印花", "荷叶边", "灯笼袖"], "tags": ["约会", "优雅", "日常", "甜美"],
         "season": ["春", "夏"], "weather": ["晴天", "温和"], "temp": (18, 32), "thick": "极薄",
         "func": {"透气": True}},
        {"t": "运动速干衣", "g": ["男", "女", "中性"], "fab": ["聚酯纤维", "冰丝"], "shape": "短袖T形",
         "det": ["反光条", "网眼透气区", "无缝拼接", "弹力收口"], "tags": ["运动", "速干", "透气", "跑步"],
         "season": ["春", "夏", "秋"], "weather": ["晴天", "炎热"], "temp": (15, 38), "thick": "极薄",
         "func": {"透气": True, "速干": True, "弹性": True}},
    ],
    "下装": [
        {"t": "直筒长裤", "g": ["男", "女", "中性"], "fab": ["精梳棉", "灯芯绒", "精纺羊毛"], "shape": "直筒长裤",
         "det": ["中腰设计", "免烫裤线", "后贴袋", "微弹面料"], "tags": ["通勤", "日常", "百搭", "商务"],
         "season": ["春", "秋"], "weather": ["温和", "晴天"], "temp": (10, 26), "thick": "适中",
         "func": {"透气": True, "抗皱": True}},
        {"t": "西裤", "g": ["男"], "fab": ["精纺羊毛", "聚酯纤维"], "shape": "修身西裤",
         "det": ["隐藏式弹力腰", "免烫裤线", "侧口袋", "修身剪裁"], "tags": ["商务", "面试", "正式", "通勤"],
         "season": ["春", "秋", "冬"], "weather": ["温和", "多云"], "temp": (5, 25), "thick": "适中",
         "func": {"抗皱": True, "透气": True}},
        {"t": "阔腿裤", "g": ["女"], "fab": ["冰丝", "棉麻混纺", "莫代尔"], "shape": "阔腿长裤",
         "det": ["高腰垂坠", "松紧腰", "侧口袋", "开衩裤脚"], "tags": ["通勤", "日常", "优雅", "夏季"],
         "season": ["春", "夏"], "weather": ["晴天", "炎热"], "temp": (18, 36), "thick": "轻薄",
         "func": {"透气": True, "速干": True}},
        {"t": "牛仔裤", "g": ["男", "女", "中性"], "fab": ["牛仔布"], "shape": "直筒牛仔裤",
         "det": ["水洗做旧", "微弹面料", "经典五袋", "卷边裤脚"], "tags": ["日常", "休闲", "百搭", "约会"],
         "season": ["春", "秋", "冬"], "weather": ["晴天", "多云"], "temp": (5, 26), "thick": "适中",
         "func": {"透气": True}},
        {"t": "运动束脚裤", "g": ["男", "女", "中性"], "fab": ["聚酯纤维", "精梳棉"], "shape": "束脚长裤",
         "det": ["松紧+抽绳腰", "拉链口袋", "弹力束脚", "反光logo"], "tags": ["运动", "日常", "休闲", "跑步"],
         "season": ["春", "秋"], "weather": ["晴天", "多云"], "temp": (8, 26), "thick": "轻薄",
         "func": {"透气": True, "速干": True, "弹性": True}},
        {"t": "休闲短裤", "g": ["男"], "fab": ["精梳棉", "棉麻混纺", "聚酯纤维"], "shape": "及膝短裤",
         "det": ["松紧腰带", "侧口袋", "抽绳设计", "轻量面料"], "tags": ["日常", "休闲", "夏季", "居家"],
         "season": ["夏"], "weather": ["炎热", "晴天"], "temp": (24, 40), "thick": "极薄",
         "func": {"透气": True, "速干": True}},
        {"t": "半身裤裙", "g": ["女"], "fab": ["精梳棉", "聚酯纤维"], "shape": "A字裤裙",
         "det": ["内衬防走光", "隐形拉链", "高腰显瘦", "百褶设计"], "tags": ["日常", "约会", "通勤", "甜美"],
         "season": ["春", "夏"], "weather": ["晴天", "温和"], "temp": (18, 33), "thick": "轻薄",
         "func": {"透气": True}},
    ],
    "外套": [
        {"t": "风衣", "g": ["男", "女", "中性"], "fab": ["尼龙面料", "精梳棉"], "shape": "中长款风衣",
         "det": ["双排扣", "腰带系结", "防风袖袢", "肩章设计"], "tags": ["通勤", "商务", "日常", "春秋"],
         "season": ["春", "秋"], "weather": ["多云", "温和"], "temp": (8, 20), "thick": "适中",
         "func": {"透气": True, "抗皱": True}},
        {"t": "西装外套", "g": ["男", "女"], "fab": ["精纺羊毛", "聚酯纤维"], "shape": "单排扣西装",
         "det": ["半衬设计", "平驳领", "手工锁眼", "开衩下摆"], "tags": ["商务", "面试", "正式", "通勤"],
         "season": ["春", "秋"], "weather": ["温和", "晴天"], "temp": (10, 25), "thick": "适中",
         "func": {"抗皱": True, "透气": True}},
        {"t": "夹克", "g": ["男"], "fab": ["尼龙面料", "头层牛皮", "帆布"], "shape": "翻领夹克",
         "det": ["多口袋设计", "按扣翻领", "罗纹收口", "可调节袖口"], "tags": ["日常", "休闲", "百搭", "户外"],
         "season": ["春", "秋"], "weather": ["多云", "温和"], "temp": (8, 22), "thick": "适中",
         "func": {"透气": True}},
        {"t": "大衣", "g": ["女"], "fab": ["精纺羊毛", "羊绒"], "shape": "长款大衣",
         "det": ["翻驳领", "腰带收腰", "暗扣门襟", "开衩后摆"], "tags": ["通勤", "优雅", "冬季", "商务"],
         "season": ["秋", "冬"], "weather": ["寒冷", "多云"], "temp": (-5, 15), "thick": "厚重",
         "func": {"保暖": True}},
        {"t": "羽绒服", "g": ["男", "女", "中性"], "fab": ["鹅绒填充面料"], "shape": "连帽羽绒服",
         "det": ["可拆卸帽", "防风袖口", "YKK拉链", "锁温内衬"], "tags": ["冬季", "保暖", "户外", "极寒"],
         "season": ["冬"], "weather": ["寒冷"], "temp": (-30, 5), "thick": "厚重",
         "func": {"保暖": True, "防水": True}},
        {"t": "防晒衣", "g": ["男", "女", "中性"], "fab": ["尼龙面料", "冰丝"], "shape": "连帽薄外套",
         "det": ["UPF50+防晒", "可收纳成小包", "弹力袖口", "透气孔"], "tags": ["旅行", "户外", "防晒", "夏季"],
         "season": ["夏"], "weather": ["炎热", "晴天"], "temp": (24, 42), "thick": "极薄",
         "func": {"透气": True, "防晒": True, "速干": True}},
        {"t": "冲锋衣", "g": ["男", "女", "中性"], "fab": ["尼龙面料"], "shape": "连帽冲锋衣",
         "det": ["全压胶防水", "腋下透气拉链", "防风帽檐", "魔术贴袖口"], "tags": ["户外", "登山", "防水", "旅行"],
         "season": ["春", "秋", "冬"], "weather": ["雨天", "多云", "寒冷"], "temp": (-10, 20), "thick": "中厚",
         "func": {"防水": True, "透气": True}},
    ],
    "鞋履": [
        {"t": "运动鞋", "g": ["男", "女", "中性"], "fab": ["飞织面料", "尼龙面料"], "shape": "低帮运动鞋",
         "det": ["气垫减震", "透气网面", "防滑橡胶底", "轻量中底"], "tags": ["运动", "日常", "跑步", "旅行"],
         "season": ["春", "夏", "秋"], "weather": ["晴天", "多云"], "temp": (5, 35), "thick": "轻薄",
         "func": {"透气": True, "弹性": True}},
        {"t": "皮鞋", "g": ["男"], "fab": ["头层牛皮"], "shape": "牛津鞋",
         "det": ["三接头设计", "橡胶防滑底", "真皮鞋垫", "手工缝线"], "tags": ["商务", "面试", "正式", "婚礼"],
         "season": ["春", "秋", "冬"], "weather": ["晴天", "多云"], "temp": (0, 28), "thick": "适中",
         "func": {"透气": True}},
        {"t": "高跟鞋", "g": ["女"], "fab": ["头层牛皮", "缎面"], "shape": "尖头细高跟",
         "det": ["6cm细跟", "真皮鞋垫", "防滑底", "蝴蝶结装饰"], "tags": ["正式", "约会", "派对", "婚礼"],
         "season": ["春", "夏", "秋"], "weather": ["晴天", "温和"], "temp": (10, 32), "thick": "轻薄",
         "func": {}},
        {"t": "乐福鞋", "g": ["男", "女", "中性"], "fab": ["头层牛皮"], "shape": "一脚蹬乐福鞋",
         "det": ["马衔扣", "软底舒适", "手工缝线", "防滑鞋底"], "tags": ["通勤", "日常", "商务", "百搭"],
         "season": ["春", "夏", "秋"], "weather": ["晴天", "温和"], "temp": (10, 32), "thick": "轻薄",
         "func": {"透气": True}},
        {"t": "短靴", "g": ["女"], "fab": ["头层牛皮"], "shape": "尖头短靴",
         "det": ["侧拉链", "粗跟设计", "防滑底纹", "加绒内里"], "tags": ["通勤", "日常", "冬季", "优雅"],
         "season": ["秋", "冬"], "weather": ["寒冷", "多云"], "temp": (-5, 18), "thick": "适中",
         "func": {"保暖": True}},
        {"t": "帆布鞋", "g": ["男", "女", "中性"], "fab": ["帆布"], "shape": "低帮帆布鞋",
         "det": ["硫化橡胶底", "经典系带", "加固鞋头", "可机洗"], "tags": ["日常", "休闲", "百搭", "学生"],
         "season": ["春", "夏", "秋"], "weather": ["晴天", "多云"], "temp": (10, 34), "thick": "轻薄",
         "func": {"透气": True}},
        {"t": "凉鞋", "g": ["女"], "fab": ["头层牛皮"], "shape": "露趾凉鞋",
         "det": ["魔术贴", "软木鞋垫", "防滑橡胶底", "编织鞋面"], "tags": ["夏季", "度假", "日常", "透气"],
         "season": ["夏"], "weather": ["炎热", "晴天"], "temp": (24, 40), "thick": "极薄",
         "func": {"透气": True}},
    ],
    "配饰": [
        {"t": "围巾", "g": ["男", "女", "中性"], "fab": ["羊绒", "精纺羊毛"], "shape": "长条围巾",
         "det": ["流苏边", "双面可用", "200cm加长", "肌理编织"], "tags": ["冬季", "保暖", "商务", "优雅"],
         "season": ["秋", "冬"], "weather": ["寒冷"], "temp": (-15, 12), "thick": "中厚",
         "func": {"保暖": True}},
        {"t": "腰带", "g": ["男"], "fab": ["头层牛皮"], "shape": "针扣腰带",
         "det": ["合金扣头", "双面用皮", "宽度3.5cm", "手工封边"], "tags": ["商务", "正式", "通勤", "百搭"],
         "season": ["春", "夏", "秋", "冬"], "weather": ["晴天", "温和"], "temp": (-10, 40), "thick": "轻薄",
         "func": {}},
        {"t": "丝巾", "g": ["女"], "fab": ["真丝"], "shape": "方巾",
         "det": ["手工卷边", "90cm大方巾", "原创印花", "多种系法"], "tags": ["优雅", "通勤", "约会", "百搭"],
         "season": ["春", "夏", "秋"], "weather": ["晴天", "温和"], "temp": (10, 35), "thick": "极薄",
         "func": {}},
        {"t": "棒球帽", "g": ["男", "女", "中性"], "fab": ["精梳棉", "尼龙面料"], "shape": "弧形帽檐棒球帽",
         "det": ["可调节帽围", "透气孔", "刺绣logo", "预弯帽檐"], "tags": ["日常", "运动", "防晒", "休闲"],
         "season": ["春", "夏", "秋"], "weather": ["晴天", "炎热"], "temp": (12, 38), "thick": "轻薄",
         "func": {"防晒": True, "透气": True}},
        {"t": "手表", "g": ["男"], "fab": ["不锈钢合金", "头层牛皮"], "shape": "圆形表盘",
         "det": ["日期窗口", "防水50米", "蓝宝石镜面", "精钢表带"], "tags": ["商务", "面试", "正式", "百搭"],
         "season": ["春", "夏", "秋", "冬"], "weather": ["晴天", "温和"], "temp": (-5, 40), "thick": "适中",
         "func": {"防水": True}},
        {"t": "发饰", "g": ["女"], "fab": ["缎面", "真丝"], "shape": "蝴蝶结发夹",
         "det": ["法式盘发夹", "缎面光泽", "防滑内齿", "轻量合金"], "tags": ["约会", "优雅", "日常", "甜美"],
         "season": ["春", "夏", "秋", "冬"], "weather": ["晴天", "温和"], "temp": (-5, 40), "thick": "轻薄",
         "func": {}},
        {"t": "托特包", "g": ["女"], "fab": ["头层牛皮", "帆布"], "shape": "大容量托特包",
         "det": ["磁扣开合", "内隔层", "可肩背手提", "加固底部"], "tags": ["通勤", "日常", "百搭", "旅行"],
         "season": ["春", "夏", "秋", "冬"], "weather": ["晴天", "多云"], "temp": (-10, 40), "thick": "适中",
         "func": {}},
        {"t": "领带", "g": ["男"], "fab": ["真丝"], "shape": "标准领带形",
         "det": ["手工卷边", "斜纹织纹", "可调节扣环", "7cm标准宽"], "tags": ["商务", "面试", "婚礼", "正式"],
         "season": ["春", "秋", "冬"], "weather": ["温和", "晴天"], "temp": (0, 28), "thick": "轻薄",
         "func": {}},
    ],
}

# ============================================================
# 文玩/饰品: 按五行的天然材质库 (材质, 颜色名, 色值, 寓意备注)
# ============================================================
STONES = {
    "木": [("小叶紫檀", "檀紫褐", "#4C2B20", "安神定气"), ("绿檀", "翠绿", "#3C7A52", "舒缓静心"),
           ("菩提子", "米褐", "#C8A165", "开悟增慧"), ("翡翠", "翠绿", "#00A86B", "通灵养性"),
           ("绿幽灵水晶", "幽绿", "#3E8E63", "正财事业"), ("沉香", "深褐", "#5B4636", "安神定气"),
           ("崖柏", "赭褐", "#8A5A3B", "宁神养心"), ("绿松石", "松石绿", "#30D5C8", "平和心境")],
    "火": [("南红玛瑙", "锦红", "#B93A26", "沉稳安心"), ("红玛瑙", "朱红", "#C3272B", "热情活力"),
           ("石榴石", "酒红", "#722F37", "养颜暖身"), ("粉水晶", "樱粉", "#F4C2C2", "旺人缘"),
           ("红纹石", "蔷薇粉", "#E75480", "悦心怡情"), ("朱砂", "丹红", "#FF4E20", "定心安神")],
    "土": [("蜜蜡", "鸡油黄", "#EAA221", "温养身心"), ("和田玉", "糖白", "#EFE3C8", "温润养人"),
           ("黄龙玉", "明黄", "#E3A857", "纳福寓意"), ("黄水晶", "柠檬黄", "#F7D774", "聚气纳福"),
           ("琥珀", "琥珀金", "#C9821E", "静心温养"), ("虎眼石", "褐金", "#B8860B", "增强决断")],
    "金": [("银饰", "亮银", "#DFE2E4", "解毒安神"), ("砗磲", "月白", "#F4F7F7", "净心宁神"),
           ("白水晶", "晶白", "#F0F4F8", "澄澈明晰"), ("珍珠", "珠光白", "#F5F0E6", "优雅温润"),
           ("白玉", "脂白", "#EDE8DC", "温润内敛"), ("铂金饰", "铂银", "#E5E4E2", "简约高级")],
    "水": [("黑曜石", "曜黑", "#0D0D0D", "静心宁神"), ("青金石", "青金蓝", "#1F4788", "开阔思维"),
           ("蓝砂石", "星空蓝", "#20315E", "静心明志"), ("黑玛瑙", "墨黑", "#161616", "沉稳内敛"),
           ("海蓝宝", "浅海蓝", "#79B9D1", "从容平和"), ("蓝虎眼", "靛蓝", "#33526E", "冷静专注")],
}

STONE_TYPES = {
    "文玩": [
        {"t": "手串", "g": ["男", "中性"], "shape": "圆形", "det": ["12mm珠径", "弹力绳串制", "手工打磨"],
         "tags": ["禅修", "静心", "日常", "文玩"]},
        {"t": "108颗佛珠", "g": ["中性"], "shape": "圆形", "det": ["108颗制式", "隔珠点缀", "可绕四圈"],
         "tags": ["禅修", "静心", "文玩", "礼佛"]},
        {"t": "吊坠", "g": ["女", "中性"], "shape": "圆形", "det": ["随形雕刻", "编织挂绳", "可调节长度"],
         "tags": ["日常", "静心", "装饰", "文玩"]},
        {"t": "手持把件", "g": ["男"], "shape": "不规则", "det": ["随形把玩", "包浆温润", "掌心大小"],
         "tags": ["文玩", "静心", "把玩", "收藏"]},
        {"t": "平安扣", "g": ["中性"], "shape": "圆形", "det": ["古法圆雕", "红绳编织", "双面抛光"],
         "tags": ["日常", "纳福", "装饰", "文玩"]},
    ],
    "饰品": [
        {"t": "项链", "g": ["女"], "shape": "圆形", "det": ["锁骨链长度", "925银链", "精工镶嵌"],
         "tags": ["约会", "优雅", "日常", "装饰"]},
        {"t": "手链", "g": ["女"], "shape": "圆形", "det": ["可调节链长", "小珠点缀", "叠戴设计"],
         "tags": ["日常", "优雅", "约会", "装饰"]},
        {"t": "耳钉", "g": ["女"], "shape": "圆形", "det": ["925银针", "轻巧贴耳", "抛光工艺"],
         "tags": ["约会", "优雅", "日常", "通勤"]},
        {"t": "戒指", "g": ["男", "女", "中性"], "shape": "圆形", "det": ["内圈打磨", "可选戒围", "简约镶嵌"],
         "tags": ["日常", "装饰", "约会", "百搭"]},
        {"t": "胸针", "g": ["女"], "shape": "不规则", "det": ["安全别针扣", "手工镶嵌", "微镶点缀"],
         "tags": ["正式", "优雅", "婚礼", "装饰"]},
        {"t": "袖扣", "g": ["男"], "shape": "圆形", "det": ["镜面抛光", "旋转扣杆", "礼盒装"],
         "tags": ["商务", "正式", "婚礼", "绅士"]},
        {"t": "手镯", "g": ["女"], "shape": "圆形", "det": ["内径56mm", "古法素圈", "细腻抛光"],
         "tags": ["优雅", "日常", "装饰", "温润"]},
    ],
}

# 裙装模板（全部女性）
SKIRT_TYPES = [
    {"t": "连衣裙", "fab": ["真丝", "精梳棉", "聚酯纤维"], "shape": "A字中长裙",
     "det": ["收腰系带", "隐形拉链", "泡泡袖", "碎花印花"], "tags": ["约会", "日常", "优雅", "甜美"],
     "season": ["春", "夏"], "weather": ["晴天", "温和"], "temp": (18, 33), "thick": "轻薄",
     "func": {"透气": True}},
    {"t": "半身长裙", "fab": ["棉麻混纺", "莫代尔", "冰丝"], "shape": "A字长裙",
     "det": ["松紧腰", "侧口袋", "自然褶皱", "开衩下摆"], "tags": ["日常", "文艺", "度假", "休闲"],
     "season": ["春", "夏"], "weather": ["温和", "晴天"], "temp": (18, 34), "thick": "轻薄",
     "func": {"透气": True}},
    {"t": "衬衫裙", "fab": ["精梳棉", "棉麻混纺"], "shape": "中长衬衫裙",
     "det": ["翻领门襟", "腰带收腰", "袖口可挽", "侧开衩"], "tags": ["通勤", "日常", "优雅", "百搭"],
     "season": ["春", "秋"], "weather": ["晴天", "温和"], "temp": (15, 28), "thick": "轻薄",
     "func": {"透气": True, "抗皱": True}},
    {"t": "针织裙", "fab": ["精纺羊毛", "羊绒"], "shape": "修身针织长裙",
     "det": ["罗纹收边", "微弹修身", "半高领", "侧开衩"], "tags": ["通勤", "优雅", "秋冬", "约会"],
     "season": ["秋", "冬"], "weather": ["寒冷", "多云"], "temp": (0, 18), "thick": "适中",
     "func": {"保暖": True}},
    {"t": "吊带裙", "fab": ["真丝", "缎面"], "shape": "垂坠吊带长裙",
     "det": ["细吊带", "斜裁垂坠", "可调节肩带", "开衩下摆"], "tags": ["派对", "约会", "度假", "优雅"],
     "season": ["夏"], "weather": ["炎热", "晴天"], "temp": (24, 38), "thick": "极薄",
     "func": {"透气": True}},
    {"t": "百褶裙", "fab": ["聚酯纤维", "缎面"], "shape": "中长百褶裙",
     "det": ["定型百褶", "松紧腰头", "垂坠光泽", "内衬防透"], "tags": ["通勤", "日常", "优雅", "百搭"],
     "season": ["春", "秋"], "weather": ["晴天", "温和"], "temp": (12, 28), "thick": "轻薄",
     "func": {"抗皱": True}},
]

ADJS = ["经典", "简约", "都市", "文艺", "轻奢", "复古", "雅致", "率性", "摩登", "静谧"]
BASE_FUNC = {"防水": False, "透气": False, "保暖": False, "速干": False, "防晒": False}


def fetch_current(conn):
    """读取现有 (品类, 五行, 性别) 分布与已用名称"""
    cur = conn.cursor()
    cur.execute("SELECT category, primary_element, gender, count(*) FROM items GROUP BY 1,2,3")
    cell = Counter()
    gender = Counter()
    for cat, elem, g, n in cur.fetchall():
        cell[(cat, elem)] += n
        gender[g] += n
    cur.execute("SELECT name FROM items")
    used_names = {r[0] for r in cur.fetchall()}
    cur.execute("SELECT count(*) FROM items")
    total = cur.fetchone()[0]
    cur.close()
    return cell, gender, used_names, total


def build_queue(cell, total, rng):
    """缺口队列 + 补足到 500 的额外配额"""
    queue = []
    for cat in CATS:
        for elem in ELEMS:
            deficit = max(0, CELL_MIN - cell.get((cat, elem), 0))
            queue.extend([(cat, elem)] * deficit)

    extra = (TOTAL_TARGET - total) - len(queue)
    if extra < 0:
        raise SystemExit(f"缺口 {len(queue)} 件已超过可新增数量 {TOTAL_TARGET - total}，请调高总量目标")
    # 额外配额轮转分给主力品类，保持矩阵均衡
    extra_cats = ["上装", "下装", "外套", "鞋履", "配饰", "裙装"]
    i = 0
    while extra > 0:
        cat = extra_cats[i % len(extra_cats)]
        elem = ELEMS[(i // len(extra_cats)) % len(ELEMS)]
        queue.append((cat, elem))
        i += 1
        extra -= 1
    rng.shuffle(queue)
    return queue


def pick_gender(cat, spec_pool, need_m, need_f):
    """按剩余缺口挑性别，并返回支持该性别的款式池"""
    if cat == "裙装":
        return "女", spec_pool
    male_specs = [s for s in spec_pool if "男" in s["g"]]
    female_specs = [s for s in spec_pool if "女" in s["g"]]
    neutral_specs = [s for s in spec_pool if "中性" in s["g"]]
    if need_m >= need_f and need_m > 0 and male_specs:
        return "男", male_specs
    if need_f > 0 and female_specs:
        return "女", female_specs
    if need_m > 0 and male_specs:
        return "男", male_specs
    if neutral_specs:
        return "中性", neutral_specs
    return "中性", spec_pool


def make_name(used, gender, color, adj, tname, rng):
    """生成唯一名称"""
    gprefix = {"男": "男士", "女": "女士", "中性": ""}[gender]
    cname = color if color.endswith("色") else f"{color}色"
    candidates = [
        f"{cname}{adj}{gprefix}{tname}",
        f"{cname}{gprefix}{adj}{tname}",
    ]
    for c in candidates:
        if c not in used:
            return c
    for extra_adj in rng.sample(ADJS, len(ADJS)):
        c = f"{cname}{extra_adj}{gprefix}{tname}"
        if c not in used:
            return c
    # 兜底加序号
    n = 2
    while f"{cname}{adj}{gprefix}{tname}{n}" in used:
        n += 1
    return f"{cname}{adj}{gprefix}{tname}{n}"


def build_clothing_item(item_id, cat, elem, gender, spec, used_names, rng):
    color, chex = rng.choice(COLORS[elem])
    adj = rng.choice(ADJS)
    name = make_name(used_names, gender, color, adj, spec["t"], rng)
    fab_name = rng.choice(spec["fab"])
    fab_elem, fab_sec, touch, weight, blend = FABRICS[fab_name]
    energy = round(rng.uniform(0.6, 0.92), 2)
    secondary = fab_elem if fab_elem != elem else None
    scores = {elem: 0.7}
    if secondary:
        scores[secondary] = 0.3
    else:
        scores[elem] = 1.0
    details = rng.sample(spec["det"], min(3, len(spec["det"])))
    tmin, tmax = spec["temp"]
    tmin += rng.choice([-2, 0, 2])
    tmax += rng.choice([-2, 0, 2])
    func = dict(BASE_FUNC)
    func.update(spec["func"])
    return {
        "物品 ID": f"ITEM_{item_id:03d}",
        "物品名称": name,
        "分类": cat,
        "属性详情": {
            "颜色": {"名称": color, "色值": chex, "主五行": elem, "次五行": None,
                     "能量强度": energy, "标注备注": COLOR_NOTES[elem]},
            "面料": {"名称": fab_name, "主五行": fab_elem, "次五行": fab_sec,
                     "触感": touch, "克重": weight, "混纺比例": blend},
            "款式": {"形状": spec["shape"], "细节": details, "综合五行得分": scores},
        },
        "适用标签": spec["tags"],
        "元数据": {"置信度": 0.95, "版本": "v3.0-expansion"},
        "适用性别": gender,
        "适用天气": spec["weather"],
        "适用季节": spec["season"],
        "适用温度范围": {"最低": tmin, "最高": tmax},
        "功能性": func,
        "厚度等级": spec["thick"],
    }


def build_stone_item(item_id, cat, elem, gender, spec, used_names, rng):
    stone, color, chex, note = rng.choice(STONES[elem])
    name = f"{stone}{spec['t']}"
    if name in used_names:
        for adj in rng.sample(ADJS, len(ADJS)):
            if f"{adj}{stone}{spec['t']}" not in used_names:
                name = f"{adj}{stone}{spec['t']}"
                break
    energy = round(rng.uniform(0.7, 0.95), 2)
    return {
        "物品 ID": f"ITEM_{item_id:03d}",
        "物品名称": name,
        "分类": cat,
        "属性详情": {
            "颜色": {"名称": color, "色值": chex, "主五行": elem, "次五行": None,
                     "能量强度": energy, "标注备注": f"{stone}{note}，{COLOR_NOTES[elem]}"},
            "面料": {"名称": f"天然{stone}", "主五行": elem, "次五行": None,
                     "触感": "温润细腻", "克重": "轻", "混纺比例": {f"天然{stone}": 1.0}},
            "款式": {"形状": spec["shape"], "细节": spec["det"], "综合五行得分": {elem: 1.0}},
        },
        "适用标签": spec["tags"],
        "元数据": {"置信度": 0.95, "版本": "v3.0-expansion"},
        "适用性别": gender,
        "适用天气": ["晴天", "多云", "温和"],
        "适用季节": ["春", "夏", "秋", "冬"],
        "适用温度范围": {"最低": -10, "最高": 45},
        "功能性": {"防水": False, "透气": False, "保暖": False, "速干": False, "防晒": False},
        "厚度等级": "轻薄",
    }


def generate(cell, gender_cnt, used_names, total, rng):
    queue = build_queue(cell, total, rng)
    need_m = max(0, GENDER_TARGET - gender_cnt.get("男", 0))
    need_f = max(0, GENDER_TARGET - gender_cnt.get("女", 0))
    items = []
    item_id = ID_START
    for cat, elem in queue:
        if cat == "裙装":
            spec = rng.choice(SKIRT_TYPES)
            g = "女"
            item = build_clothing_item(item_id, cat, elem, g, spec, used_names, rng)
        elif cat in ("文玩", "饰品"):
            g, pool = pick_gender(cat, STONE_TYPES[cat], need_m, need_f)
            spec = rng.choice(pool)
            item = build_stone_item(item_id, cat, elem, g, spec, used_names, rng)
        else:
            g, pool = pick_gender(cat, TYPES[cat], need_m, need_f)
            spec = rng.choice(pool)
            item = build_clothing_item(item_id, cat, elem, g, spec, used_names, rng)
        if g == "男":
            need_m = max(0, need_m - 1)
        elif g == "女":
            need_f = max(0, need_f - 1)
        used_names.add(item["物品名称"])
        items.append(item)
        item_id += 1
    return items, need_m, need_f


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只打印分配统计，不写文件")
    args = parser.parse_args()

    rng = random.Random(42)
    conn = psycopg2.connect(**DB_CONFIG)
    cell, gender_cnt, used_names, total = fetch_current(conn)
    conn.close()

    print(f"现有物品: {total} 件 | 性别分布: {dict(gender_cnt)}")
    items, remain_m, remain_f = generate(cell, gender_cnt, used_names, total, rng)

    # 统计
    new_cell = Counter((i["分类"], i["属性详情"]["颜色"]["主五行"]) for i in items)
    new_gender = Counter(i["适用性别"] for i in items)
    print(f"新增: {len(items)} 件 | 新增性别: {dict(new_gender)}")
    print(f"男缺口剩余: {remain_m} | 女缺口剩余: {remain_f}")

    print("\n=== 合并后 品类×五行 矩阵 ===")
    header = "品类      " + "".join(f"{e:>6}" for e in ELEMS)
    print(header)
    problems = []
    for cat in CATS:
        row = f"{cat:<8}"
        for elem in ELEMS:
            n = cell.get((cat, elem), 0) + new_cell.get((cat, elem), 0)
            row += f"{n:>6}"
            if n < CELL_MIN:
                problems.append((cat, elem, n))
        print(row)
    if problems:
        print(f"⚠️  仍不足 {CELL_MIN} 件的格子: {problems}")
    else:
        print(f"✅ 所有格子 ≥ {CELL_MIN} 件")

    merged_gender = Counter(gender_cnt)
    merged_gender.update(new_gender)
    print(f"合并后性别: {dict(merged_gender)} | 合并后总量: {total + len(items)}")

    if args.dry_run:
        return

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"\n已写入: {OUT_PATH}")
    print("下一步入库: .venv/bin/python scripts/import_seed_dashscope.py --file data/seeds/seed_data_expansion_500.json")


if __name__ == "__main__":
    main()
