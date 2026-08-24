"""为 OSS Bucket 绑定自定义域名 images.shunyishang.cn（含域名归属验证）

用法:
  .venv/bin/python scripts/bind_oss_custom_domain.py           # 首次: 获取token并尝试自动加TXT记录
  .venv/bin/python scripts/bind_oss_custom_domain.py --bind    # 已手动添加TXT记录后: 直接绑定
流程: OSS 要求先通过 TXT token 验证域名归属:
  1. CreateCnameToken 获取验证 token
  2. 向 DNS 添加 TXT 记录 verification.images = token（子账号无DNS权限时需控制台手动添加）
  3. 等待 DNS 生效后重试绑定（最多 15 次，每次间隔 10 秒）
说明: 一次性运维脚本，绑定成功后图片可通过 https://images.shunyishang.cn/... 访问
"""
import sys
import time
from pathlib import Path

import oss2
from oss2.models import PutBucketCnameRequest

# 从 .env.ecs 读取凭证（OSS + 云解析 DNS 共用同一子账号）
ENV_FILE = Path(__file__).resolve().parent.parent / ".env.ecs"
config = {}
for line in ENV_FILE.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        config[k.strip()] = v.strip()

AK = config["OSS_ACCESS_KEY_ID"]
SK = config["OSS_ACCESS_KEY_SECRET"]
# 本地执行必须用公网 endpoint（internal 仅 ECS 内网可达）
ENDPOINT = "https://oss-cn-hangzhou.aliyuncs.com"
BUCKET_NAME = config["OSS_BUCKET_NAME"]
DOMAIN = "images.shunyishang.cn"
DOMAIN_NAME = "shunyishang.cn"

auth = oss2.Auth(AK, SK)
bucket = oss2.Bucket(auth, ENDPOINT, BUCKET_NAME)


def already_bound() -> bool:
    try:
        result = bucket.list_bucket_cname()
        existing = [c.domain for c in result.cname]
        print(f"当前已绑定域名: {existing or '(无)'}")
        return DOMAIN in existing
    except oss2.exceptions.NoSuchCnameConfiguration:
        print("当前已绑定域名: (无)")
        return False


if already_bound():
    print(f"✅ {DOMAIN} 已绑定，无需重复操作")
    sys.exit(0)

BIND_ONLY = "--bind" in sys.argv

# ---- Step 1: 获取域名归属验证 token（--bind 模式跳过）----
if not BIND_ONLY:
    try:
        token_result = bucket.create_bucket_cname_token(DOMAIN)
        token = token_result.token
        expire = getattr(token_result, "expire_time", "未知")
        print(f"[1/3] 获取验证 token: {token} (有效期至 {expire})")
    except oss2.exceptions.OssError as e:
        print(f"❌ 获取 token 失败: {e.code} - {e.message}")
        sys.exit(1)

    # ---- Step 2: 尝试通过阿里云 DNS API 自动添加 TXT 验证记录 ----
    print("[2/3] 尝试自动添加 DNS TXT 验证记录 verification.images → token ...")
    try:
        from alibabacloud_alidns20150109.client import Client as DnsClient  # noqa: E402
        from alibabacloud_alidns20150109 import models as dns_models  # noqa: E402
        from alibabacloud_tea_openapi import models as open_api_models  # noqa: E402

        dns_config = open_api_models.Config(access_key_id=AK, access_key_secret=SK)
        dns_config.endpoint = "alidns.cn-hangzhou.aliyuncs.com"
        dns = DnsClient(dns_config)

        list_req = dns_models.DescribeDomainRecordsRequest(
            domain_name=DOMAIN_NAME, rrkey_word="verification.images", type="TXT"
        )
        records = dns.describe_domain_records(list_req).body.domain_records.record
        if records:
            print(f"  ⏭  TXT 记录已存在({records[0].value[:16]}...)，跳过添加")
        else:
            add_req = dns_models.AddDomainRecordRequest(
                domain_name=DOMAIN_NAME,
                rr="verification.images",
                type="TXT",
                value=token,
                ttl=600,
            )
            dns.add_domain_record(add_req)
            print("  ✅ TXT 记录已添加（TTL 600s）")
    except Exception as e:
        print(f"  ⚠️  自动添加失败（子账号无DNS权限）: {getattr(e, 'code', str(e)[:80])}")
        print("  👉 请在阿里云DNS控制台手动添加:")
        print(f"     记录类型: TXT | 主机记录: _dnsauth.images | 记录值: {token}")
        print("     添加后执行: .venv/bin/python scripts/bind_oss_custom_domain.py --bind")
        sys.exit(0)
else:
    print("[模式] 跳过token获取，直接尝试绑定（假设TXT验证记录已添加）")

# ---- Step 3: 等待 DNS 生效后重试绑定 ----
print("[3/3] 等待 DNS 生效并绑定自定义域名...")
for attempt in range(1, 16):
    try:
        bucket.put_bucket_cname(PutBucketCnameRequest(DOMAIN))
        print(f"✅ 绑定成功: {DOMAIN} → oss://{BUCKET_NAME}")
        print(f"   图片访问地址示例: https://{DOMAIN}/<object-key>")
        print("   (验证用 TXT 记录可保留，也可在 DNS 控制台删除)")
        sys.exit(0)
    except oss2.exceptions.OssError as e:
        if e.code == "NeedVerifyDomainOwnership" and attempt < 15:
            print(f"  第 {attempt} 次尝试: token 尚未生效，10 秒后重试...")
            time.sleep(10)
        else:
            print(f"❌ 绑定失败: {e.code} - {e.message}")
            sys.exit(1)
