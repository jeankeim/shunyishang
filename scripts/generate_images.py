#!/usr/bin/env python3
"""
五行 AI 衣橱 - 多模态图片生成脚本

使用阿里云通义千问 (Qwen) 多模态大模型生成衣物图片
支持批量生成并保存到 data/generated_images 目录

Usage:
    python generate_images.py
    
环境变量:
    DASHSCOPE_API_KEY: 阿里云 DashScope API Key
"""

import os
import json
import time
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

# 使用阿里云 DashScope SDK
import dashscope
from dashscope import ImageSynthesis

# ============================================================================
# 配置
# ============================================================================

# 获取 API Key (从环境变量或.env 文件)
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")

# 输出目录
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "generated_images"

# 模型配置
MODEL_NAME = "wanx-v1"  # 通义万相文生图模型

# 默认生成参数
DEFAULT_CONFIG = {
    "style": "<photorealistic>",  # 照片级真实风格
    "size": "1024*1024",  # 图片尺寸
    "n": 1,  # 每次生成数量
}


# ============================================================================
# 测试查询列表
# ============================================================================

TEST_QUERIES = [
    {
        "query": "一件简约风格的白色棉质 T 恤，圆领设计，修身版型",
        "category": "上装",
        "element": "金"
    },
    {
        "query": "深蓝色牛仔裤，直筒剪裁，经典五袋设计",
        "category": "下装",
        "element": "水"
    },
    {
        "query": "米色风衣，双排扣，腰带设计，英伦风格",
        "category": "外套",
        "element": "土"
    },
    {
        "query": "红色丝绸连衣裙，V 领，收腰设计，优雅气质",
        "category": "裙装",
        "element": "火"
    },
    {
        "query": "黑色真皮短靴，粗跟，侧拉链，街头风格",
        "category": "鞋履",
        "element": "水"
    },
]


# ============================================================================
# 工具函数
# ============================================================================

def load_env_from_file():
    """从.env 文件加载环境变量"""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())


def create_output_directory():
    """创建输出目录"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] 输出目录：{OUTPUT_DIR}")


# ============================================================================
# 图片生成服务
# ============================================================================

class QwenImageGenerator:
    """通义千问图片生成器"""
    
    def __init__(self, api_key: str = None):
        """
        初始化生成器
        
        Args:
            api_key: DashScope API Key
        """
        # 优先使用传入的 api_key，否则从环境变量获取
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
        
        if not self.api_key:
            raise ValueError(
                "请设置 DASHSCOPE_API_KEY 环境变量\n"
                "获取方式：访问 https://dashscope.console.aliyun.com/"
            )
        
        # 使用阿里云 DashScope SDK
        dashscope.api_key = self.api_key
        print(f"[INFO] 已初始化 DashScope SDK (通义万相)")
    
    def generate_image(
        self,
        prompt: str,
        style: str = DEFAULT_CONFIG["style"],
        size: str = DEFAULT_CONFIG["size"],
        n: int = DEFAULT_CONFIG["n"]
    ) -> Optional[Dict]:
        """
        生成单张图片
        
        Args:
            prompt: 提示词
            style: 风格 (<photorealistic>|<anime>|<oil painting>|<watercolor>|<sketch>)
            size: 尺寸 (1024*1024|720*1280|1280*720)
            n: 生成数量 (1-4)
            
        Returns:
            生成结果 {"url": "...", "prompt": "..."} 或 None
        """
        try:
            print(f"[INFO] 正在生成：{prompt[:50]}...")
            
            # 构建完整 prompt
            full_prompt = f"{style}, {prompt}, 高质量，精细，专业摄影"
            
            # 调用阿里云 DashScope 通义万相 API
            rsp = ImageSynthesis.call(
                model="wanx-v1",
                prompt=full_prompt,
                size=size,
                n=n
            )
            
            # 检查响应
            if rsp.status_code == 200:
                results = rsp.output.results
                if results and len(results) > 0:
                    image_url = results[0].url
                    print(f"[SUCCESS] 生成成功：{image_url}")
                    
                    return {
                        "url": image_url,
                        "prompt": prompt,
                        "full_prompt": full_prompt,
                        "style": style,
                        "size": size,
                        "created_at": datetime.now().isoformat()
                    }
            else:
                print(f"[ERROR] 无生成结果")
                return None
                
        except Exception as e:
            print(f"[ERROR] 生成异常：{e}")
            return None
    
    def generate_batch(
        self,
        queries: List[Dict],
        output_dir: Path = OUTPUT_DIR,
        delay: float = 1.0
    ) -> List[Dict]:
        """
        批量生成图片
        
        Args:
            queries: 查询列表 [{"query": "...", "category": "...", "element": "..."}]
            output_dir: 输出目录
            delay: 请求间隔时间 (秒)
            
        Returns:
            生成结果列表
        """
        results = []
        
        for idx, item in enumerate(queries, 1):
            print(f"\n{'='*60}")
            print(f"[{idx}/{len(queries)}] 处理：{item.get('query', '')[:50]}...")
            print(f"{'='*60}")
            
            result = self.generate_image(
                prompt=item["query"],
                style=DEFAULT_CONFIG["style"],
                size=DEFAULT_CONFIG["size"],
                n=DEFAULT_CONFIG["n"]
            )
            
            if result:
                # 添加元数据
                result["category"] = item.get("category", "")
                result["element"] = item.get("element", "")
                results.append(result)
                
                # 下载图片到本地
                self._download_image(result["url"], output_dir, idx, result["prompt"])
            
            # 延迟避免限流
            if idx < len(queries):
                time.sleep(delay)
        
        return results
    
    def _download_image(self, url: str, output_dir: Path, index: int, prompt: str = "") -> str:
        """
        下载图片到本地
        
        Args:
            url: 图片 URL
            output_dir: 输出目录
            index: 索引编号
            prompt: 图片描述（用于生成文件名）
            
        Returns:
            保存的文件路径
        """
        import requests
        
        try:
            # 创建子目录（按日期）
            date_str = datetime.now().strftime("%Y%m%d")
            sub_dir = output_dir / date_str
            sub_dir.mkdir(parents=True, exist_ok=True)
            
            # 下载图片
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # 从 prompt 生成文件名（提取关键词）
            if prompt:
                # 移除特殊字符和空格，保留中文
                safe_prompt = prompt.replace("/", "_").replace("\\", "_")
                # 截取前 30 个字符作为文件名
                filename_base = safe_prompt[:30].strip()
                # 生成文件名：序号_描述.png
                filename = f"image_{index:03d}_{filename_base}.png"
            else:
                filename = f"image_{index:03d}_{int(time.time())}.png"
            
            filepath = sub_dir / filename
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            print(f"[SUCCESS] 已保存到：{filepath}")
            
            # 同时保存元数据
            metadata = {
                "url": url,
                "local_path": str(filepath),
                "filename": filename,
                "prompt": prompt
            }
            meta_path = sub_dir / f"{filename.replace('.png', '.json')}"
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            return str(filepath)
            
        except Exception as e:
            print(f"[ERROR] 下载失败：{e}")
            return ""


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    print("="*60)
    print("五行 AI 衣橱 - 多模态图片生成")
    print("="*60)
    
    # 加载环境变量
    load_env_from_file()
    
    # 创建输出目录
    create_output_directory()
    
    # 初始化生成器
    try:
        generator = QwenImageGenerator()
    except ValueError as e:
        print(f"\n[ERROR] {e}")
        return
    
    # 批量生成
    print(f"\n[INFO] 开始批量生成 {len(TEST_QUERIES)} 张图片...")
    results = generator.generate_batch(
        queries=TEST_QUERIES,
        output_dir=OUTPUT_DIR,
        delay=2.0  # 2 秒间隔
    )
    
    # 输出统计
    print(f"\n{'='*60}")
    print(f"[SUMMARY] 生成完成")
    print(f"{'='*60}")
    print(f"总查询数：{len(TEST_QUERIES)}")
    print(f"成功数：{len(results)}")
    print(f"失败数：{len(TEST_QUERIES) - len(results)}")
    print(f"成功率：{len(results)/len(TEST_QUERIES)*100:.1f}%")
    print(f"\n输出目录：{OUTPUT_DIR}")
    
    # 保存汇总报告
    report_path = OUTPUT_DIR / f"generation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            "total": len(TEST_QUERIES),
            "success": len(results),
            "failed": len(TEST_QUERIES) - len(results),
            "results": results,
            "output_dir": str(OUTPUT_DIR)
        }, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n[INFO] 汇总报告已保存：{report_path}")


if __name__ == "__main__":
    main()
