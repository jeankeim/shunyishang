#!/usr/bin/env python3
"""
测试 DashScope API 连接

快速验证 API Key 是否有效
"""

import os
from pathlib import Path

# 尝试导入 dashscope
try:
    import dashscope
    from dashscope import ImageSynthesis
except ImportError:
    print("[ERROR] 未安装 dashscope")
    print("[INFO] 请运行：pip install dashscope>=1.14.0")
    exit(1)


def load_env():
    """加载环境变量"""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())


def test_api_key():
    """测试 API Key"""
    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    
    if not api_key:
        print("[ERROR] 未找到 DASHSCOPE_API_KEY")
        print("[INFO] 请在 .env 文件中配置或设置环境变量")
        return False
    
    print(f"[OK] API Key 已配置 ({len(api_key)} 字符)")
    dashscope.api_key = api_key
    return True


def test_image_generation():
    """测试图片生成（简化版）"""
    print("\n[TEST] 测试图片生成...")
    
    try:
        # 简单测试 prompt
        rsp = ImageSynthesis.call(
            model="wanx2.1",
            prompt="<photorealistic>, 一件简单的白色 T 恤，纯色背景",
            size="1024*1024",
            n=1
        )
        
        if rsp.status_code == 200:
            print("[SUCCESS] API 调用成功!")
            if rsp.output.results:
                print(f"[INFO] 生成图片 URL: {rsp.output.results[0].url}")
                return True
            else:
                print("[WARNING] 无生成结果")
                return False
        else:
            print(f"[ERROR] API 返回错误：code={rsp.code}, message={rsp.message}")
            return False
            
    except Exception as e:
        print(f"[ERROR] 测试失败：{e}")
        return False


def main():
    """主函数"""
    print("="*50)
    print("DashScope API 连接测试")
    print("="*50)
    
    # 加载环境变量
    load_env()
    
    # 测试 API Key
    if not test_api_key():
        print("\n[INFO] 获取 API Key: https://dashscope.console.aliyun.com/")
        return
    
    # 测试图片生成
    success = test_image_generation()
    
    # 输出结果
    print("\n" + "="*50)
    if success:
        print("[RESULT] ✅ 测试通过，可以开始生成图片")
        print("\n[下一步] 运行：python generate_images.py")
    else:
        print("[RESULT] ❌ 测试失败，请检查配置")
        print("\n[排查步骤]")
        print("1. 检查 API Key 是否正确")
        print("2. 确认账户余额充足")
        print("3. 检查网络连接")
        print("4. 查看官方文档：https://help.aliyun.com/zh/dashscope/")
    
    print("="*50)


if __name__ == "__main__":
    main()
