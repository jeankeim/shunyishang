"""
物品性别标注修复脚本

背景：公共库中存在性别标注与实际款式不符的物品（bad case：ITEM_437
黑色简约乐福鞋款式图为男款，却标注为"中性"，导致女性用户被推荐），
同时名称含"男士/女款"等明确关键词的物品若 gender 标注与之矛盾，
属于数据质量问题，需要修复。

修复策略（保守）：
1. 手动修复清单（MANUAL_FIXES）：人工确认过的错标物品，按 item_code 精确修复
2. 名称关键词一致性检查：名称含"男士/男款/男装/男生"但 gender != '男'、
   或含"女士/女款/女装/女生"但 gender != '女' 的物品，自动修正
3. UPDATE 语句必须带 AND gender = '原错误值' 防护（防止并发/重复执行时
   覆盖已被人工修正过的数据）
4. 默认 dry-run 只打印计划，--apply 才真正写库

用法：
    # 预览（默认 dry-run，不写库）
    python3 scripts/fix_gender_mislabeled_items.py --env .env

    # 执行修复
    python3 scripts/fix_gender_mislabeled_items.py --env .env --apply

    # 生产环境先预览
    python3 scripts/fix_gender_mislabeled_items.py --env .env.production
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2

# ============================================================
# 手动修复清单：人工确认过的性别错标物品
# key=item_code, value=(目标性别, 修复原因)
# ============================================================
MANUAL_FIXES = {
    "ITEM_437": ("男", "款式图为男款乐福鞋，误标为中性，曾导致女性用户被推荐"),
}

# 名称关键词 → 预期性别（与 packages/recommendation/filters.py 保持同一口径）
MALE_NAME_KEYWORDS = ("男士", "男款", "男装", "男生")
FEMALE_NAME_KEYWORDS = ("女士", "女款", "女装", "女生")


def load_env(env_file: str) -> str:
    """加载 env 文件到环境变量，返回 DATABASE_URL"""
    text = open(env_file).read()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ[key.strip()] = value.strip()
    m = re.search(r"DATABASE_URL=(\S+)", text)
    if not m:
        raise SystemExit(f"{env_file} 中未找到 DATABASE_URL")
    return m.group(1)


def plan_manual_fixes(cur) -> list:
    """扫描手动修复清单，返回需要执行的修复项 [(item_code, name, 当前性别, 目标性别, 原因)]"""
    plan = []
    for item_code, (target_gender, reason) in MANUAL_FIXES.items():
        cur.execute(
            "SELECT item_code, name, gender FROM items WHERE item_code = %s",
            (item_code,),
        )
        row = cur.fetchone()
        if not row:
            print(f"[跳过] {item_code} 不存在")
            continue
        _, name, current_gender = row
        if current_gender == target_gender:
            print(f"[跳过] {item_code} {name} 已是 {target_gender}")
            continue
        plan.append((item_code, name, current_gender, target_gender, reason))
    return plan


def plan_name_keyword_fixes(cur) -> list:
    """扫描名称关键词与 gender 标注矛盾的物品"""
    plan = []
    cur.execute("SELECT item_code, name, gender FROM items WHERE gender IS NOT NULL")
    for item_code, name, current_gender in cur.fetchall():
        expected = None
        if any(kw in (name or "") for kw in MALE_NAME_KEYWORDS):
            expected = "男"
        elif any(kw in (name or "") for kw in FEMALE_NAME_KEYWORDS):
            expected = "女"
        if expected and current_gender != expected:
            plan.append((item_code, name, current_gender, expected, "名称关键词与性别标注矛盾"))
    return plan


def apply_fix(cur, item_code: str, current_gender, target_gender: str) -> bool:
    """执行单条修复，带 AND gender='原错误值' 防护；gender 为 NULL 时单独分支"""
    if current_gender is None:
        cur.execute(
            "UPDATE items SET gender = %s, updated_at = NOW() WHERE item_code = %s AND gender IS NULL",
            (target_gender, item_code),
        )
    else:
        cur.execute(
            "UPDATE items SET gender = %s, updated_at = NOW() WHERE item_code = %s AND gender = %s",
            (target_gender, item_code, current_gender),
        )
    return cur.rowcount > 0


def main() -> None:
    parser = argparse.ArgumentParser(description="物品性别标注修复")
    parser.add_argument("--env", default=".env", help="env 文件路径（决定目标数据库）")
    parser.add_argument("--apply", action="store_true", help="真正写库（默认 dry-run 只打印计划）")
    args = parser.parse_args()

    db_url = load_env(args.env)
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    try:
        manual_plan = plan_manual_fixes(cur)
        keyword_plan = plan_name_keyword_fixes(cur)
        all_plan = manual_plan + keyword_plan

        print(f"\n{'=' * 60}")
        print(f"修复计划：手动清单 {len(manual_plan)} 条 + 名称关键词 {len(keyword_plan)} 条")
        print(f"{'=' * 60}")
        for item_code, name, current, target, reason in all_plan:
            print(f"  {item_code} | {name} | {current} → {target} | {reason}")

        if not args.apply:
            print("\n[dry-run] 未写库。确认无误后加 --apply 执行。")
            return

        if not all_plan:
            print("无需修复。")
            return

        success = 0
        for item_code, name, current, target, reason in all_plan:
            if apply_fix(cur, item_code, current, target):
                success += 1
                print(f"[修复] {item_code} {name}: {current} → {target}")
            else:
                print(f"[跳过] {item_code} {name}: 当前值已变更（防护条件未命中），需人工复核")
        conn.commit()
        print(f"\n完成：成功修复 {success}/{len(all_plan)} 条")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
