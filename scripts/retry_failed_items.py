#!/usr/bin/env python3
"""
智能重试脚本 - 自动重试失败的物品，直到全部完成
特性：
- 自动检测已完成的物品，只重试失败的
- 遇到限流自动等待 60 秒
- 遇到欠费自动等待 5 分钟后重试
- 记录详细进度到日志文件
- 可以安全中断，下次继续
"""

import sys
from pathlib import Path
from datetime import datetime
import requests
import json
import time

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.generate_images import QwenImageGenerator
from apps.api.core.database import DatabasePool
from dotenv import load_dotenv

load_dotenv()

# 需要重试的物品 ID 列表（根据上次失败记录）
ITEMS_TO_RETRY = [
    "ITEM_032", "ITEM_039", "ITEM_041", "ITEM_045", "ITEM_048", "ITEM_050",
    "ITEM_057", "ITEM_061", "ITEM_062", "ITEM_076", "ITEM_078", "ITEM_083",
    "ITEM_085", "ITEM_086", "ITEM_089", "ITEM_096"
]

# 配置
MAX_RETRIES = 5  # 每个物品最大重试次数
RETRY_DELAY = 5  # 重试间隔（秒）
RATE_LIMIT_WAIT = 60  # 限流等待时间（秒）
ACCOUNT_ISSUE_WAIT = 300  # 账户问题等待时间（秒）

# 日志文件
LOG_DIR = Path("/Users/mingyang/Desktop/shunyishang/data/generated_images/seed_data_100/20260404")
LOG_FILE = LOG_DIR / "retry_progress.log"

def log(message):
    """记录日志到文件和终端"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    print(log_message)
    
    # 追加到日志文件
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_message + "\n")

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
        log(f"⚠️  查询 {item_code} 失败: {e}")
        return None

def is_already_completed(item_code, output_dir):
    """检查物品是否已经成功生成并替换"""
    public_dir = Path("/Users/mingyang/Desktop/shunyishang/apps/web/public/images/seed")
    original_backup = public_dir / f"{item_code}_original.png"
    
    # 如果原图已备份，说明已经处理过
    return original_backup.exists()

def regenerate_item(generator, item_code, item_name, output_dir, attempt=1):
    """重新生成单个物品的图片（带重试）"""
    
    # 检查是否已完成
    if is_already_completed(item_code, output_dir):
        log(f"✅ {item_code} 已完成，跳过")
        return {'success': True, 'skipped': True}
    
    log(f"\n{'='*60}")
    log(f"处理: {item_code} - {item_name} (尝试 {attempt}/{MAX_RETRIES})")
    log(f"{'='*60}")
    
    # 构建专用的无人物纯白背景 prompt
    prompt = f"{item_name}，纯白色背景，无模特，无任何人出现，平铺拍摄，电商产品图，清晰展示服装细节，专业摄影，商业级质量"
    
    log(f"🎨 Prompt: {prompt}")
    
    try:
        # 生成图片
        result = generator.generate_image(
            prompt=prompt,
            style="<photorealistic>",
            size="1024*1024",
            n=1
        )
        
        # 检查 result 是否有效
        if result is None:
            raise ValueError("API 返回结果为空")
        
        if 'url' not in result:
            raise ValueError(f"API 返回格式错误: {result}")
        
        log(f"✅ 生成成功: {result['url']}")
        
        # 下载图片
        safe_name = item_name.replace('/', '_').replace('\\', '_')
        filename = f"image_{item_code}_{safe_name}_white_bg.png"
        file_path = output_dir / filename
        
        log(f"💾 下载中: {filename}")
        response = requests.get(result['url'])
        response.raise_for_status()
        
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        file_size = file_path.stat().st_size / 1024
        log(f"✅ 保存成功: {file_path} ({file_size:.1f} KB)")
        
        # 保存元数据
        metadata = {
            "url": result['url'],
            "local_path": str(file_path),
            "filename": filename,
            "prompt": prompt,
            "original_name": item_name,
            "generated_at": datetime.now().isoformat(),
            "style": "纯白背景无人物",
            "retry_attempt": attempt
        }
        
        metadata_path = output_dir / f"{filename.replace('.png', '.json')}"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        log(f"✅ 元数据已保存")
        
        # 替换公共库图片
        public_dir = Path("/Users/mingyang/Desktop/shunyishang/apps/web/public/images/seed")
        original_path = public_dir / f"{item_code}.png"
        backup_path = public_dir / f"{item_code}_original.png"
        
        if not backup_path.exists():
            import shutil
            shutil.copy2(original_path, backup_path)
            log(f"📦 已备份原图片: {backup_path}")
        
        import shutil
        shutil.copy2(file_path, original_path)
        log(f"✅ 已替换: {original_path}")
        
        return {
            'success': True,
            'item_code': item_code,
            'item_name': item_name,
            'file_path': str(file_path),
            'file_size': file_size,
            'attempts': attempt
        }
        
    except Exception as e:
        error_msg = str(e)
        log(f"❌ 生成失败 (尝试 {attempt}/{MAX_RETRIES}): {error_msg}")
        
        # 检查错误类型
        if 'Arrearage' in error_msg or 'overdue-payment' in error_msg:
            log(f"⚠️  检测到账户欠费，等待 {ACCOUNT_ISSUE_WAIT//60} 分钟后重试...")
            return {'success': False, 'error_type': 'account', 'error': error_msg}
        elif 'Throttling' in error_msg or 'rate limit' in error_msg.lower():
            log(f"⚠️  检测到请求限流，等待 {RATE_LIMIT_WAIT} 秒后重试...")
            return {'success': False, 'error_type': 'rate_limit', 'error': error_msg}
        else:
            return {'success': False, 'error_type': 'other', 'error': error_msg}

def save_progress(results, output_dir):
    """保存进度"""
    progress_file = output_dir / "retry_final_progress.json"
    
    # 转换为可序列化的格式
    results_for_save = []
    for r in results:
        r_copy = r.copy()
        if 'file_path' in r_copy and isinstance(r_copy['file_path'], Path):
            r_copy['file_path'] = str(r_copy['file_path'])
        results_for_save.append(r_copy)
    
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total': len(ITEMS_TO_RETRY),
            'completed': len([r for r in results if r.get('success')]),
            'failed': len([r for r in results if not r.get('success')]),
            'results': results_for_save,
            'finished_at': datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2)

def main():
    log("="*60)
    log("🔄 智能重试脚本启动")
    log("="*60)
    log(f"需要重试的物品: {len(ITEMS_TO_RETRY)} 个")
    log(f"最大重试次数: {MAX_RETRIES} 次")
    log(f"限流等待时间: {RATE_LIMIT_WAIT} 秒")
    log(f"账户问题等待: {ACCOUNT_ISSUE_WAIT//60} 分钟")
    log("")
    
    # 初始化
    generator = QwenImageGenerator()
    DatabasePool.init_pool()
    
    output_dir = Path("/Users/mingyang/Desktop/shunyishang/data/generated_images/seed_data_100/20260404")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    success_count = 0
    fail_count = 0
    
    for i, item_code in enumerate(ITEMS_TO_RETRY, 1):
        log(f"\n{'#'*60}")
        log(f"进度: [{i}/{len(ITEMS_TO_RETRY)}]")
        log(f"{'#'*60}")
        
        # 获取物品名称
        item_name = get_item_name(item_code)
        if not item_name:
            log(f"⚠️  跳过 {item_code}: 未找到物品")
            fail_count += 1
            results.append({
                'success': False,
                'item_code': item_code,
                'error': 'Item not found in database'
            })
            continue
        
        # 尝试生成（带重试）
        item_success = False
        for attempt in range(1, MAX_RETRIES + 1):
            result = regenerate_item(generator, item_code, item_name, output_dir, attempt)
            
            if result['success']:
                if result.get('skipped'):
                    log(f"✅ {item_code} 已处理过，跳过")
                else:
                    success_count += 1
                    log(f"✅ {item_code} 成功！")
                results.append(result)
                item_success = True
                break
            
            # 检查错误类型，决定等待时间
            error_type = result.get('error_type', 'other')
            
            if error_type == 'rate_limit':
                log(f"⏳ 等待 {RATE_LIMIT_WAIT} 秒后重试...")
                time.sleep(RETRY_DELAY)  # 先短暂等待
            elif error_type == 'account':
                log(f"⏳ 等待 {ACCOUNT_ISSUE_WAIT} 秒后重试...")
                time.sleep(ACCOUNT_ISSUE_WAIT)  # 长时间等待
            else:
                # 其他错误，短暂等待后重试
                if attempt < MAX_RETRIES:
                    log(f"⏳ 等待 {RETRY_DELAY * attempt} 秒后重试...")
                    time.sleep(RETRY_DELAY * attempt)
        
        if not item_success:
            fail_count += 1
            results.append(result)
            log(f"❌ {item_code} 最终失败")
        
        # 保存当前进度
        save_progress(results, output_dir)
        
        # 物品间间隔，避免触发限流
        if i < len(ITEMS_TO_RETRY):
            log(f"\n⏳ 等待 10 秒后处理下一个物品...")
            time.sleep(10)
    
    # 最终统计
    log("\n" + "="*60)
    log("🎉 重试任务完成！")
    log("="*60)
    log(f"总计: {len(ITEMS_TO_RETRY)} 个物品")
    log(f"✅ 成功: {success_count} 个")
    log(f"❌ 失败: {fail_count} 个")
    log(f"📁 生成目录: {output_dir}")
    log(f"📝 详细日志: {LOG_FILE}")
    log("")
    
    # 显示失败列表
    if fail_count > 0:
        log("失败物品列表:")
        for r in results:
            if not r.get('success'):
                log(f"  - {r['item_code']} ({r.get('item_name', 'Unknown')}): {r.get('error', '未知错误')}")
        log("")
    
    # 保存最终进度
    save_progress(results, output_dir)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n\n⚠️  用户中断，进度已保存")
        log("下次运行脚本会继续处理未完成的物品")
    except Exception as e:
        log(f"\n❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
