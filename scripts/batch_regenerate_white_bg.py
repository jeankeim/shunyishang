#!/usr/bin/env python3
"""
批量重新生成指定物品的纯白背景无人物图片
"""

import sys
from pathlib import Path
from datetime import datetime
import requests
import json

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.generate_images import QwenImageGenerator
from apps.api.core.database import DatabasePool
from dotenv import load_dotenv

load_dotenv()

# 需要重新生成的物品 ID 列表
ITEMS_TO_REGENERATE = [
    "ITEM_004", "ITEM_005", "ITEM_011", "ITEM_014", "ITEM_018", "ITEM_019",
    "ITEM_023", "ITEM_025", "ITEM_028", "ITEM_032", "ITEM_039", "ITEM_041",
    "ITEM_045", "ITEM_048", "ITEM_050", "ITEM_057", "ITEM_061", "ITEM_062",
    "ITEM_070", "ITEM_076", "ITEM_078", "ITEM_083", "ITEM_085", "ITEM_086",
    "ITEM_089", "ITEM_096"
]

def get_item_name(item_code):
    """从数据库获取物品名称"""
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT name FROM items WHERE item_code = %s",
                    (item_code,)
                )
                row = cur.fetchone()
                return row[0] if row else None
    except Exception as e:
        print(f"⚠️  查询 {item_code} 失败: {e}")
        return None

def regenerate_item(generator, item_code, item_name, output_dir):
    """重新生成单个物品的图片"""
    print(f"\n{'='*60}")
    print(f"处理: {item_code} - {item_name}")
    print(f"{'='*60}")
    
    # 构建专用的无人物纯白背景 prompt
    prompt = f"{item_name}，纯白色背景，无模特，无任何人出现，平铺拍摄，电商产品图，清晰展示服装细节，专业摄影，商业级质量"
    
    print(f"🎨 Prompt: {prompt}")
    
    try:
        # 生成图片
        result = generator.generate_image(
            prompt=prompt,
            style="<photorealistic>",
            size="1024*1024",
            n=1
        )
        
        print(f"✅ 生成成功: {result['url']}")
        
        # 下载图片
        safe_name = item_name.replace('/', '_').replace('\\', '_')
        filename = f"image_{item_code}_{safe_name}_white_bg.png"
        file_path = output_dir / filename
        
        print(f"💾 下载中: {filename}")
        response = requests.get(result['url'])
        response.raise_for_status()
        
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        file_size = file_path.stat().st_size / 1024
        print(f"✅ 保存成功: {file_path} ({file_size:.1f} KB)")
        
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
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 元数据已保存")
        
        return {
            'success': True,
            'item_code': item_code,
            'item_name': item_name,
            'file_path': file_path,
            'file_size': file_size
        }
        
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'item_code': item_code,
            'item_name': item_name,
            'error': str(e)
        }

def replace_image(item_code, new_image_path, public_dir):
    """替换公共库中的图片"""
    original_path = public_dir / f"{item_code}.png"
    backup_path = public_dir / f"{item_code}_original.png"
    
    if not original_path.exists():
        print(f"⚠️  原图片不存在: {original_path}")
        return False
    
    # 备份原图片
    if not backup_path.exists():
        import shutil
        shutil.copy2(original_path, backup_path)
        print(f"📦 已备份原图片: {backup_path}")
    
    # 替换图片
    import shutil
    shutil.copy2(new_image_path, original_path)
    print(f"✅ 已替换: {original_path}")
    
    return True

def main():
    print("="*60)
    print("批量重新生成纯白背景无人物图片")
    print("="*60)
    print(f"总共 {len(ITEMS_TO_REGENERATE)} 个物品需要处理")
    print()
    
    # 初始化
    generator = QwenImageGenerator()
    DatabasePool.init_pool()
    
    output_dir = Path("/Users/mingyang/Desktop/shunyishang/data/generated_images/seed_data_100/20260404")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    public_dir = Path("/Users/mingyang/Desktop/shunyishang/apps/web/public/images/seed")
    
    results = []
    success_count = 0
    fail_count = 0
    
    for i, item_code in enumerate(ITEMS_TO_REGENERATE, 1):
        print(f"\n[{i}/{len(ITEMS_TO_REGENERATE)}] 开始处理...")
        
        # 获取物品名称
        item_name = get_item_name(item_code)
        if not item_name:
            print(f"⚠️  跳过 {item_code}: 未找到物品")
            fail_count += 1
            continue
        
        # 生成图片
        result = regenerate_item(generator, item_code, item_name, output_dir)
        
        if result['success']:
            # 替换公共库图片
            replaced = replace_image(item_code, result['file_path'], public_dir)
            if replaced:
                success_count += 1
            else:
                fail_count += 1
        else:
            fail_count += 1
        
        results.append(result)
        
        # 保存进度
        progress_file = output_dir / "regeneration_progress.json"
        with open(progress_file, 'w', encoding='utf-8') as f:
            # 将 Path 对象转换为字符串
            results_for_save = []
            for r in results:
                r_copy = r.copy()
                if 'file_path' in r_copy and hasattr(r_copy['file_path'], '__str__'):
                    r_copy['file_path'] = str(r_copy['file_path'])
                results_for_save.append(r_copy)
            
            json.dump({
                'total': len(ITEMS_TO_REGENERATE),
                'completed': i,
                'success': success_count,
                'failed': fail_count,
                'results': results_for_save
            }, f, ensure_ascii=False, indent=2)
    
    # 打印最终统计
    print("\n" + "="*60)
    print("🎉 批量生成完成！")
    print("="*60)
    print(f"总计: {len(ITEMS_TO_REGENERATE)} 个物品")
    print(f"✅ 成功: {success_count} 个")
    print(f"❌ 失败: {fail_count} 个")
    print(f"📁 生成目录: {output_dir}")
    print()
    
    # 显示失败列表
    if fail_count > 0:
        print("失败物品列表:")
        for r in results:
            if not r['success']:
                print(f"  - {r['item_code']} ({r['item_name']}): {r.get('error', '未知错误')}")
        print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断，进度已保存")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
