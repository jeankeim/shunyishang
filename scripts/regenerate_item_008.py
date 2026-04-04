#!/usr/bin/env python3
"""
重新生成指定物品的纯白背景无人物图片
目标：墨绿色丝绒阔腿裤 (ITEM_008)
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.generate_images import QwenImageGenerator
from dotenv import load_dotenv

load_dotenv()

def main():
    print("="*60)
    print("重新生成：墨绿色丝绒阔腿裤 (ITEM_008)")
    print("="*60)
    
    # 初始化生成器
    generator = QwenImageGenerator()
    
    # 物品信息
    target_item_id = "ITEM_008"
    item_name = "墨绿色丝绒阔腿裤"
    
    print(f"\n📦 物品信息:")
    print(f"  ID: {target_item_id}")
    print(f"  名称: {item_name}")
    
    # 构建专用的无人物纯白背景 prompt
    prompt = f"{item_name}，纯白色背景，无模特，无任何人出现，平铺拍摄，电商产品图，清晰展示服装细节，专业摄影，商业级质量"
    
    print(f"\n🎨 生成 Prompt:")
    print(f"  {prompt}")
    
    # 输出目录
    output_dir = Path("/Users/mingyang/Desktop/shunyishang/data/generated_images/seed_data_100/20260403")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 安全文件名
    safe_name = item_name.replace('/', '_').replace('\\', '_')
    
    print(f"\n 输出目录: {output_dir}")
    print("\n开始生成...")
    
    try:
        # 生成图片
        result = generator.generate_image(
            prompt=prompt,
            style="<photorealistic>",
            size="1024*1024",
            n=1
        )
        
        print("✅ 图片生成成功！")
        print(f"📥 下载链接: {result['url']}")
        
        # 下载图片
        import requests
        filename = f"image_{target_item_id}_{safe_name}_white_bg.png"
        file_path = output_dir / filename
        
        print(f"\n💾 正在下载: {filename}")
        response = requests.get(result['url'])
        response.raise_for_status()
        
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ 图片已保存: {file_path}")
        print(f"📊 文件大小: {file_path.stat().st_size / 1024:.1f} KB")
        
        # 保存元数据
        metadata = {
            "url": result['url'],
            "local_path": str(file_path),
            "filename": filename,
            "prompt": prompt,
            "original_name": item_name,
            "generated_at": datetime.now().isoformat(),
            "style": "纯白背景无人物"
        }
        
        metadata_path = output_dir / f"{filename.replace('.png', '.json')}"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            import json
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 元数据已保存: {metadata_path}")
        print("\n" + "="*60)
        print("🎉 生成完成！")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
