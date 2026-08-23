"""
存量衣橱重打标脚本

背景：历史上传链路未持久化 AI 打标的颜色/面料/风格属性
（attributes_detail 中相应键为 null，style 列为空），
导致场景风格判断与风格偏好加分对存量衣物失效。

用法：
    # 预览（不写库）
    python3 scripts/retag_wardrobe_items.py --env .env.production --dry-run

    # 执行（默认只处理 style/color/material 为空的物品）
    python3 scripts/retag_wardrobe_items.py --env .env.production

    # 指定用户 + 同步刷新 embedding
    python3 scripts/retag_wardrobe_items.py --env .env.production --user 2 --with-embedding

更新策略（保守）：
- 写入 style/color/material 列 + attributes_detail 的 颜色/面料/款式 键
- applicable_seasons/applicable_weather/thickness_level 仅在为空时补齐，不覆盖已有值
- 不改动 name/category/primary_element 等用户可能手工修正过的字段
- --with-embedding 时用补全后的属性重建 embedding（提升语义检索区分度）
"""

import argparse
import asyncio
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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


async def main() -> None:
    parser = argparse.ArgumentParser(description="存量衣橱重打标")
    parser.add_argument("--env", default=".env", help="env 文件路径（决定目标数据库与 API key）")
    parser.add_argument("--user", type=int, help="只处理指定用户ID")
    parser.add_argument("--ids", help="只处理指定物品ID，逗号分隔")
    parser.add_argument("--all", action="store_true", help="处理全部物品（默认只处理 style/color/material 为空的）")
    parser.add_argument("--with-embedding", action="store_true", help="同步重建 embedding")
    parser.add_argument("--no-vision", action="store_true",
                        help="强制走文字打标（视觉通道超时/不可用时，名称信息足够则推荐）")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划更新，不写库")
    args = parser.parse_args()

    db_url = load_env(args.env)

    # env 加载后再导入，确保 settings 读到正确的 API key
    import psycopg2
    from apps.api.services.ai_tagging_service import AITaggingService
    from apps.api.services.embedding_service import (
        build_wardrobe_embedding_text,
        embedding_service,
    )

    conditions = ["is_active = TRUE"]
    params: list = []
    if not args.all and not args.ids:
        conditions.append(
            "((style IS NULL OR style = '') OR (color IS NULL OR color = '') "
            "OR (material IS NULL OR material = ''))"
        )
    if args.user:
        conditions.append("user_id = %s")
        params.append(args.user)
    if args.ids:
        id_list = [int(x) for x in args.ids.split(",")]
        conditions.append("id = ANY(%s)")
        params.append(id_list)

    conn = psycopg2.connect(db_url)
    with conn.cursor() as cur:
        cur.execute(
            f"""SELECT id, user_id, name, category, image_url, attributes_detail,
                       applicable_seasons, applicable_weather, thickness_level
                FROM user_wardrobe WHERE {' AND '.join(conditions)} ORDER BY id""",
            params,
        )
        rows = cur.fetchall()

    print(f"待处理物品: {len(rows)} 件（库: {db_url.split('@')[-1].split('?')[0]}）")
    if not rows:
        conn.close()
        return

    service = AITaggingService()
    service.timeout = 60.0  # 视觉打标较慢，放宽超时
    ok, failed = 0, 0

    for item_id, user_id, name, category, image_url, detail, cur_seasons, cur_weather, cur_thickness in rows:
        desc = f"{name}（分类:{category}）" if category else name
        img = None if args.no_vision else image_url
        result = None
        for attempt in range(3):
            try:
                result = await service.analyze_item(description=desc, image_url=img)
                if not result.get("ai_error"):
                    break
                print(f"    [重试{attempt + 1}] #{item_id} {name}: {result['ai_error']}")
            except Exception as e:
                print(f"    [重试{attempt + 1}] #{item_id} {name}: {e}")
            await asyncio.sleep(2)

        if result is None or result.get("ai_error"):
            print(f"  [失败] #{item_id} {name}: AI 打标三次均失败，跳过")
            failed += 1
            continue

        style = result.get("style")
        color = result.get("color")
        material = result.get("material")
        if color in ("未知", ""):
            color = None
        if material in ("未知", ""):
            material = None

        # 缺失维度补齐（保守：仅空时填，不覆盖已有值）
        fill_seasons = cur_seasons or result.get("applicable_seasons") or []
        fill_weather = cur_weather or result.get("applicable_weather") or []
        fill_thickness = cur_thickness or result.get("thickness_level")

        detail = detail or {}
        detail["颜色"] = {
            "名称": color,
            "主五行": result.get("color_element"),
            "能量强度": result.get("energy_intensity"),
        }
        detail["面料"] = {"名称": material, "主五行": result.get("material_element")}
        detail["款式"] = {
            "形状": result.get("shape"),
            "细节": result.get("details", []),
            "风格": style,
        }
        if not detail.get("tags"):
            detail["tags"] = result.get("tags", [])

        print(f"  [{'预览' if args.dry_run else '更新'}] #{item_id} {name}: "
              f"风格={style} 颜色={color} 面料={material}"
              + ("" if cur_seasons else f" 补季节={fill_seasons}")
              + ("" if cur_weather else f" 补天气={fill_weather}")
              + ("" if cur_thickness else f" 补厚度={fill_thickness}"))

        if args.dry_run:
            ok += 1
            continue

        embedding = None
        if args.with_embedding:
            try:
                text = build_wardrobe_embedding_text(name, category, result)
                embedding = embedding_service.generate_embedding(text)
            except Exception as e:
                print(f"    [警告] #{item_id} embedding 重建失败，跳过该字段: {e}")

        with conn.cursor() as cur:
            if embedding is not None:
                cur.execute(
                    """UPDATE user_wardrobe
                       SET style=%s, color=%s, material=%s, attributes_detail=%s,
                           applicable_seasons=%s, applicable_weather=%s,
                           thickness_level=%s, embedding=%s, updated_at=NOW()
                       WHERE id=%s""",
                    [style, color, material, json.dumps(detail, ensure_ascii=False),
                     json.dumps(fill_seasons, ensure_ascii=False),
                     json.dumps(fill_weather, ensure_ascii=False),
                     fill_thickness, embedding, item_id],
                )
            else:
                cur.execute(
                    """UPDATE user_wardrobe
                       SET style=%s, color=%s, material=%s, attributes_detail=%s,
                           applicable_seasons=%s, applicable_weather=%s,
                           thickness_level=%s, updated_at=NOW()
                       WHERE id=%s""",
                    [style, color, material, json.dumps(detail, ensure_ascii=False),
                     json.dumps(fill_seasons, ensure_ascii=False),
                     json.dumps(fill_weather, ensure_ascii=False),
                     fill_thickness, item_id],
                )
        conn.commit()
        ok += 1

    conn.close()
    print(f"\n完成: 成功 {ok} 件, 失败/跳过 {failed} 件" + ("（dry-run 未写库）" if args.dry_run else ""))


if __name__ == "__main__":
    asyncio.run(main())
