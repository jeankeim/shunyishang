"""R2 -> OSS 图片全量迁移脚本

将 Cloudflare R2 桶内全部对象流式拷贝到阿里云 OSS，保持 key 路径不变，
以便后续数据库 URL 只需替换域名前缀即可切换。

特性:
- 可重入: 目标已存在且大小一致的对象自动跳过
- 8 线程并发 + 单对象最多 3 次重试
- 结束后对比两端对象数量与总大小

用法:
    python scripts/migrate_r2_to_oss.py            # 执行迁移
    python scripts/migrate_r2_to_oss.py --verify   # 仅校验两端一致性
"""

import os
import sys
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

import boto3
import oss2
from dotenv import load_dotenv

load_dotenv(".env")
load_dotenv(".env.production", override=False)

R2_ACCOUNT_ID = os.environ["R2_ACCOUNT_ID"]
R2_ACCESS_KEY_ID = os.environ["R2_ACCESS_KEY_ID"]
R2_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
R2_BUCKET_NAME = os.environ["R2_BUCKET_NAME"]

OSS_ACCESS_KEY_ID = os.environ["OSS_ACCESS_KEY_ID"]
OSS_ACCESS_KEY_SECRET = os.environ["OSS_ACCESS_KEY_SECRET"]
OSS_BUCKET_NAME = os.environ["OSS_BUCKET_NAME"]
OSS_ENDPOINT = os.environ.get("OSS_ENDPOINT", "https://oss-cn-hangzhou.aliyuncs.com")

CONCURRENCY = 8
MAX_RETRY = 3


def r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    )


def oss_bucket():
    auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
    return oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)


def list_r2_objects(s3):
    """返回 {key: size}"""
    objects = {}
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=R2_BUCKET_NAME):
        for obj in page.get("Contents", []):
            objects[obj["Key"]] = obj["Size"]
    return objects


def list_oss_objects(bucket):
    """返回 {key: size}"""
    objects = {}
    for obj in oss2.ObjectIterator(bucket):
        objects[obj.key] = obj.size
    return objects


def copy_one(s3, bucket, key, size, stats, lock):
    for attempt in range(1, MAX_RETRY + 1):
        try:
            resp = s3.get_object(Bucket=R2_BUCKET_NAME, Key=key)
            body = resp["Body"].read()
            content_type = resp.get("ContentType") or "application/octet-stream"
            bucket.put_object(key, body, headers={"Content-Type": content_type})
            with lock:
                stats["done"] += 1
                stats["bytes"] += size
                if stats["done"] % 50 == 0:
                    print(f"  进度: {stats['done']}/{stats['total']} "
                          f"({stats['bytes'] / 1024 / 1024:.1f} MB)")
            return True
        except Exception as e:
            if attempt == MAX_RETRY:
                with lock:
                    stats["failed"].append((key, str(e)))
                return False
            time.sleep(1.5 * attempt)


def verify():
    s3 = r2_client()
    bucket = oss_bucket()
    r2_objs = list_r2_objects(s3)
    oss_objs = list_oss_objects(bucket)
    r2_total = sum(r2_objs.values())
    oss_total = sum(oss_objs.values())
    print(f"R2 : {len(r2_objs)} 个对象, {r2_total / 1024 / 1024:.1f} MB")
    print(f"OSS: {len(oss_objs)} 个对象, {oss_total / 1024 / 1024:.1f} MB")
    missing = [k for k in r2_objs if k not in oss_objs]
    mismatch = [k for k, v in r2_objs.items() if k in oss_objs and oss_objs[k] != v]
    if not missing and not mismatch:
        print("✅ 校验通过: OSS 已完整包含 R2 全部对象且大小一致")
        return True
    if missing:
        print(f"❌ OSS 缺失 {len(missing)} 个: {missing[:5]}...")
    if mismatch:
        print(f"❌ 大小不一致 {len(mismatch)} 个: {mismatch[:5]}...")
    return False


def migrate():
    s3 = r2_client()
    bucket = oss_bucket()
    print("列举 R2 对象...")
    r2_objs = list_r2_objects(s3)
    print(f"R2 共 {len(r2_objs)} 个对象, {sum(r2_objs.values()) / 1024 / 1024:.1f} MB")
    print("列举 OSS 已有对象(增量跳过)...")
    oss_objs = list_oss_objects(bucket)
    todo = {k: v for k, v in r2_objs.items() if oss_objs.get(k) != v}
    print(f"待迁移: {len(todo)} 个 (跳过已存在 {len(r2_objs) - len(todo)} 个)")
    if not todo:
        print("无需迁移")
        return verify()

    stats = {"done": 0, "bytes": 0, "total": len(todo), "failed": []}
    lock = Lock()
    start = time.time()
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = [
            pool.submit(copy_one, s3, bucket, key, size, stats, lock)
            for key, size in todo.items()
        ]
        for f in as_completed(futures):
            f.result()
    elapsed = time.time() - start
    print(f"完成: {stats['done']}/{stats['total']}, "
          f"{stats['bytes'] / 1024 / 1024:.1f} MB, 耗时 {elapsed:.0f}s")
    if stats["failed"]:
        print(f"❌ 失败 {len(stats['failed'])} 个:")
        for key, err in stats["failed"][:10]:
            print(f"  {key}: {err}")
        return False
    return verify()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true", help="仅校验不迁移")
    args = parser.parse_args()
    ok = verify() if args.verify else migrate()
    sys.exit(0 if ok else 1)
