#!/usr/bin/env python3
"""
快速测试阿里云 DashScope 文生图 API
"""

import os
from pathlib import Path
from openai import OpenAI

# 从.env 加载 API Key
env_path = Path(__file__).parent.parent / ".env"
api_key = ""

if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('DASHSCOPE_API_KEY='):
                api_key = line.split('=', 1)[1].strip()
                break

print(f"API Key: {api_key[:10]}...{api_key[-5:]}")

# 初始化客户端
client = OpenAI(
    api_key=api_key,
    base_url="https://dashscope.aliyuncs.com/api/v1"
)

# 测试生成
prompt = "<photorealistic>, 一件白色衬衫，纯色背景，高质量"

print(f"\n正在生成：{prompt}")

try:
    # 方法 1: 使用 images.generate
    print("\n[方法 1] 使用 images.generate...")
    response = client.images.generate(
        model="wanx-v1",
        prompt=prompt,
        size="1024*1024",
        n=1
    )
    print(f"成功！URL: {response.data[0].url if response.data else 'N/A'}")
except Exception as e:
    print(f"失败：{e}")
    
    # 方法 2: 直接 POST
    print("\n[方法 2] 使用 requests.post...")
    import requests
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "wanx-v1",
        "input": {
            "prompt": prompt
        },
        "parameters": {
            "size": "1024*1024",
            "n": 1
        }
    }
    
    resp = requests.post(
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-to-image/image-synthesis",
        headers=headers,
        json=data
    )
    
    print(f"状态码：{resp.status_code}")
    print(f"响应：{resp.text[:500]}")
