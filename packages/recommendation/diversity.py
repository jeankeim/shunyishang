"""
推荐多样性保障

包含：分类多样性约束、五行多样性约束、搭配完整性保障、温度安全检查。
确保推荐结果不会全是同一类别或同一五行属性，并能形成完整穿搭。
"""

import random
import logging
from typing import Dict, List

from packages.recommendation.config import (
    CATEGORY_LIMITS, DEFAULT_CATEGORY_LIMIT,
    ACCENT_CATEGORIES, TEMP_SAFETY_THRESHOLD, TEMP_ESSENTIAL_THRESHOLD,
)

logger = logging.getLogger(__name__)

# 搭配完整性：核心品类定义
TOP_BODY_CATEGORIES = {"上装", "裙装"}       # 覆盖上半身的品类
BOTTOM_BODY_CATEGORIES = {"下装", "裙装"}    # 覆盖下半身的品类
SHOE_CATEGORIES = {"鞋履"}                  # 足部覆盖
OUTFIT_CORE_CATEGORIES = {"上装", "下装", "裙装", "外套", "鞋履"}  # 核心服装品类


def ensure_category_diversity(items: List[Dict], limit: int) -> List[Dict]:
    """
    确保推荐结果包含不同分类的物品

    策略：
    - 核心服装（上装/下装/裙装/外套）每类最多2件
    - 配饰/鞋履每类最多1件
    - 饰品/文玩作为点缀（最多2/1件）
    - 确保至少1件点缀类物品（如果存在）
    - 确保至少1件饰品/文玩（产品核心差异化）

    Args:
        items: 已排序的物品列表
        limit: 返回数量

    Returns:
        多样化后的物品列表
    """
    # 防御性检查
    valid_items = [item for item in items if isinstance(item, dict)]
    if not valid_items:
        return []

    # 点缀类物品随机化（避免同一件饰品反复出现）
    accessory_items = [item for item in valid_items if item.get("category") in ACCENT_CATEGORIES]
    if len(accessory_items) > 1:
        top_n = min(3, len(accessory_items))
        candidates = accessory_items[:top_n]
        random.shuffle(candidates)
        accessory_items[:top_n] = candidates
        # 调整 valid_items 中点缀类的顺序
        acc_idx = 0
        new_valid = []
        for item in valid_items:
            if item.get("category") in ACCENT_CATEGORIES:
                new_valid.append(accessory_items[acc_idx])
                acc_idx += 1
            else:
                new_valid.append(item)
        valid_items = new_valid

    # 按分类限制选取
    result = []
    category_count: Dict[str, int] = {}

    for item in valid_items:
        category = item.get("category", "其他")
        max_count = CATEGORY_LIMITS.get(category, DEFAULT_CATEGORY_LIMIT)
        current_count = category_count.get(category, 0)

        if current_count < max_count:
            result.append(item)
            category_count[category] = current_count + 1
            if len(result) >= limit:
                break

    # 确保至少有1件点缀类物品
    _ensure_accent_item(result, accessory_items, limit)

    # 确保至少有1件饰品/文玩（产品核心差异化）
    _ensure_ornament_item(result, valid_items, limit)

    return result


def _ensure_accent_item(result: List[Dict], accessory_items: List[Dict], limit: int) -> None:
    """确保结果中至少有1件点缀类物品"""
    has_accessory = any(item.get("category") in ACCENT_CATEGORIES for item in result)
    if not has_accessory and accessory_items and len(result) >= limit:
        for i in range(len(result) - 1, -1, -1):
            if result[i].get("category") in ["上装", "下装", "裙装", "外套", "鞋履"]:
                # 不替换温度必需物品
                if (result[i].get("temp_score") or 0) >= TEMP_ESSENTIAL_THRESHOLD:
                    continue
                cat = result[i].get("category")
                same_cat_count = sum(1 for item in result if item.get("category") == cat)
                if same_cat_count > 1:
                    result[i] = accessory_items[0]
                    break


def _ensure_ornament_item(result: List[Dict], valid_items: List[Dict], limit: int) -> None:
    """确保结果中至少有1件饰品/文玩"""
    ornament_categories = {"饰品", "文玩"}
    has_ornament = any(item.get("category") in ornament_categories for item in result)
    ornament_items = [item for item in valid_items if item.get("category") in ornament_categories]

    if not has_ornament and ornament_items and len(result) >= limit:
        # 优先替换同属点缀类的非饰品物品
        replaced = False
        for i in range(len(result) - 1, -1, -1):
            if result[i].get("category") in ACCENT_CATEGORIES and result[i].get("category") not in ornament_categories:
                result[i] = ornament_items[0]
                replaced = True
                break

        if not replaced:
            for i in range(len(result) - 1, -1, -1):
                if result[i].get("category") in ["上装", "下装", "裙装", "外套"]:
                    if (result[i].get("temp_score") or 0) >= TEMP_ESSENTIAL_THRESHOLD:
                        continue
                    cat = result[i].get("category")
                    same_cat_count = sum(1 for item in result if item.get("category") == cat)
                    if same_cat_count > 1:
                        result[i] = ornament_items[0]
                        break


def ensure_outfit_completeness(
    items: List[Dict],
    all_scored: List[Dict],
    limit: int,
    style_preference: str = None,
    body_type: str = None,
    target_elements: List[str] = None,
) -> List[Dict]:
    """
    搭配完整性保障 + 个性化保障

    策略：
    1. 检查是否有上半身衣物（上装/裙装），缺失则从候选中补充
    2. 检查是否有下半身衣物（下装/裙装），缺失则从候选中补充
    3. 检查是否有鞋履，缺失则补充
    4. 个性化保障：确保 top-5 中至少2件风格匹配 + 1件体型匹配
    5. 五行保障：确保 top-1 的 primary_element 匹配喜用神

    Args:
        items: 当前 top-k 物品列表
        all_scored: 所有已评分物品（已排序）
        limit: top-k 数量
        style_preference: 用户风格偏好（用于个性化保障）
        body_type: 用户体型（用于体型匹配保障）
        target_elements: 喜用神五行列表（用于五行保障）

    Returns:
        搭配完整性优化后的物品列表
    """
    if len(items) < 3:
        return items

    # 检查当前品类覆盖
    categories_present = {item.get("category", "") for item in items}
    has_top = bool(categories_present & TOP_BODY_CATEGORIES)
    has_bottom = bool(categories_present & BOTTOM_BODY_CATEGORIES)

    used_ids = {str(item.get("id", item.get("item_code", ""))) for item in items}

    # 缺少上半身：从候选中找最佳上装/裙装
    if not has_top:
        replacement = _find_best_category_candidate(
            all_scored, TOP_BODY_CATEGORIES, used_ids,
            style_preference=style_preference, target_elements=target_elements,
        )
        if replacement:
            # 优先替换重复品类的最低分物品
            swap_idx = _find_swap_target(items, exclude_categories=TOP_BODY_CATEGORIES)
            if swap_idx is not None:
                old_item = items[swap_idx]
                items[swap_idx] = replacement
                used_ids.discard(str(old_item.get("id", old_item.get("item_code", ""))))
                used_ids.add(str(replacement.get("id", replacement.get("item_code", ""))))
                logger.debug(
                    f"[搭配完整性] 补充上半身: {old_item.get('name')}({old_item.get('category')}) "
                    f"→ {replacement.get('name')}({replacement.get('category')})"
                )

    # 重新检查（裙装同时覆盖上下半身）
    categories_present = {item.get("category", "") for item in items}
    has_bottom = bool(categories_present & BOTTOM_BODY_CATEGORIES)

    # 缺少下半身：从候选中找最佳下装/裙装
    if not has_bottom:
        replacement = _find_best_category_candidate(
            all_scored, BOTTOM_BODY_CATEGORIES, used_ids,
            style_preference=style_preference, target_elements=target_elements,
        )
        if replacement:
            swap_idx = _find_swap_target(items, exclude_categories=BOTTOM_BODY_CATEGORIES)
            if swap_idx is not None:
                old_item = items[swap_idx]
                items[swap_idx] = replacement
                used_ids.discard(str(old_item.get("id", old_item.get("item_code", ""))))
                used_ids.add(str(replacement.get("id", replacement.get("item_code", ""))))
                logger.debug(
                    f"[搭配完整性] 补充下半身: {old_item.get('name')}({old_item.get('category')}) "
                    f"→ {replacement.get('name')}({replacement.get('category')})"
                )

    # 检查鞋履覆盖：如果缺少鞋子且有可替换位置，补充一双鞋
    categories_present = {item.get("category", "") for item in items}
    has_shoes = bool(categories_present & SHOE_CATEGORIES)
    if not has_shoes and len(items) >= 4:
        replacement = _find_best_category_candidate(
            all_scored, SHOE_CATEGORIES, used_ids,
            style_preference=style_preference, target_elements=target_elements,
        )
        if replacement:
            # 鞋履替换优先级较低：仅替换点缀类或重复品类
            swap_idx = _find_swap_target_for_shoes(items)
            if swap_idx is not None:
                old_item = items[swap_idx]
                items[swap_idx] = replacement
                used_ids.discard(str(old_item.get("id", old_item.get("item_code", ""))))
                used_ids.add(str(replacement.get("id", replacement.get("item_code", ""))))
                logger.debug(
                    f"[搭配完整性] 补充鞋履: {old_item.get('name')}({old_item.get('category')}) "
                    f"→ {replacement.get('name')}({replacement.get('category')})"
                )

    # 检查外套覆盖：如果缺少外套且有可替换位置，补充一件外套
    categories_present = {item.get("category", "") for item in items}
    has_outer = "外套" in categories_present
    if not has_outer and len(items) >= 4:
        replacement = _find_best_category_candidate(
            all_scored, {"外套"}, used_ids,
            style_preference=style_preference, target_elements=target_elements,
        )
        if replacement:
            swap_idx = _find_swap_target_for_outer(items)
            if swap_idx is not None:
                old_item = items[swap_idx]
                items[swap_idx] = replacement
                used_ids.discard(str(old_item.get("id", old_item.get("item_code", ""))))
                used_ids.add(str(replacement.get("id", replacement.get("item_code", ""))))
                logger.debug(
                    f"[搭配完整性] 补充外套: {old_item.get('name')}({old_item.get('category')}) "
                    f"→ {replacement.get('name')}({replacement.get('category')})"
                )

    # 个性化保障：确保 top-5 中至少2件风格匹配
    if style_preference and len(items) >= 3:
        _ensure_style_guarantee(items, all_scored, style_preference, used_ids)

    # 体型保障：确保 top-5 中至少1件体型匹配
    if body_type and len(items) >= 3:
        _ensure_body_type_guarantee(items, all_scored, body_type, used_ids)

    # 最终点缀保护：确保至少有1件点缀物品（配饰/饰品/文玩）
    _ensure_final_accent(items, all_scored, used_ids)

    # 五行保障：确保 top-1 匹配喜用神（放在最后，确保不被其他保障覆盖）
    if target_elements and len(items) >= 1:
        _ensure_wuxing_top1(items, all_scored, target_elements, used_ids)

    return items


def _is_coverage_critical(item: Dict, items: List[Dict]) -> bool:
    """
    判断物品是否是唯一提供某种覆盖的（不可替换）

    覆盖类型：
    - 唯一上半身（上装/裙装）
    - 唯一下半身（下装/裙装）
    - 唯一鞋履
    - 唯一外套
    """
    cat = item.get("category", "")

    # 检查上半身覆盖
    if cat in TOP_BODY_CATEGORIES:
        top_count = sum(1 for i in items if i.get("category", "") in TOP_BODY_CATEGORIES)
        if top_count <= 1:
            return True

    # 检查下半身覆盖
    if cat in BOTTOM_BODY_CATEGORIES:
        bottom_count = sum(1 for i in items if i.get("category", "") in BOTTOM_BODY_CATEGORIES)
        if bottom_count <= 1:
            return True

    # 检查鞋履覆盖
    if cat in SHOE_CATEGORIES:
        shoe_count = sum(1 for i in items if i.get("category", "") in SHOE_CATEGORIES)
        if shoe_count <= 1:
            return True

    # 检查外套覆盖
    if cat == "外套":
        outer_count = sum(1 for i in items if i.get("category", "") == "外套")
        if outer_count <= 1:
            return True

    return False


def _ensure_final_accent(items: List[Dict], all_scored: List[Dict], used_ids: set) -> None:
    """
    最终点缀保护：确保至少有1件点缀物品（配饰/饰品/文玩）

    在所有其他保障之后执行，替换最低优先级的非覆盖物品。
    仅替换非覆盖关键且非温度必需的物品。
    """
    has_accent = any(item.get("category", "") in ACCENT_CATEGORIES for item in items)
    if has_accent:
        return

    # 找一件点缀候选（点缀类不受温度/场景约束，因为配饰饰品不分季节）
    accent_candidate = None
    for candidate in all_scored:
        cand_id = str(candidate.get("id", candidate.get("item_code", "")))
        if cand_id in used_ids:
            continue
        if candidate.get("category", "") not in ACCENT_CATEGORIES:
            continue
        accent_candidate = candidate
        break

    if not accent_candidate:
        return

    # 找可替换的物品：非覆盖关键 + 非温度必需 + 位置靠后
    for i in range(len(items) - 1, -1, -1):
        if _is_coverage_critical(items[i], items):
            continue
        if (items[i].get("temp_score") or 0) >= TEMP_ESSENTIAL_THRESHOLD:
            continue
        old_item = items[i]
        items[i] = accent_candidate
        used_ids.discard(str(old_item.get("id", old_item.get("item_code", ""))))
        used_ids.add(str(accent_candidate.get("id", accent_candidate.get("item_code", ""))))
        logger.debug(
            f"[点缀保护] 补充点缀: {old_item.get('name')}({old_item.get('category')}) "
            f"→ {accent_candidate.get('name')}({accent_candidate.get('category')})"
        )
        return


def _is_style_match(item: Dict, style_preference: str, keywords: List[str]) -> bool:
    """判断物品是否匹配用户风格偏好"""
    if item.get("style") == style_preference:
        return True
    item_name = item.get("name", "")
    if any(kw in item_name for kw in keywords):
        return True
    detail = item.get("attributes_detail") or {}
    if isinstance(detail, dict):
        style_info = detail.get("款式", {})
        if isinstance(style_info, dict):
            style_text = style_info.get("风格", "")
            if any(kw in style_text for kw in keywords):
                return True
    return False


def _ensure_style_guarantee(
    items: List[Dict],
    all_scored: List[Dict],
    style_preference: str,
    used_ids: set,
) -> None:
    """
    确保 top-5 中至少有2件精确风格匹配物品（item.style == user_preference）

    策略：
    1. 统计当前 top-5 中精确风格匹配数量
    2. 如果不足2件，从候选中补充精确匹配物品
    3. 替换优先级：重复品类 > 点缀类 > 最低分非核心物品
    """
    from packages.recommendation.config import STYLE_KEYWORDS

    keywords = STYLE_KEYWORDS.get(style_preference, [])

    # 统计当前精确风格匹配数（评估器只认 style 字段精确匹配）
    exact_match_count = sum(1 for item in items if item.get("style") == style_preference)
    if exact_match_count >= 2:
        return

    # 需要补充的数量
    need_count = 2 - exact_match_count

    # 从候选中找精确风格匹配物品
    style_candidates = []
    for candidate in all_scored:
        cand_id = str(candidate.get("id", candidate.get("item_code", "")))
        if cand_id in used_ids:
            continue
        if (candidate.get("temp_score") or 0) < TEMP_SAFETY_THRESHOLD:
            continue
        if candidate.get("style") == style_preference:
            style_candidates.append(candidate)
            if len(style_candidates) >= need_count:
                break

    if not style_candidates:
        return

    # 逐个补充
    for candidate in style_candidates:
        swap_idx = _find_swap_target_for_personalization(items, style_preference, keywords)
        if swap_idx is not None:
            old_item = items[swap_idx]
            items[swap_idx] = candidate
            used_ids.discard(str(old_item.get("id", old_item.get("item_code", ""))))
            used_ids.add(str(candidate.get("id", candidate.get("item_code", ""))))
            logger.debug(
                f"[个性化保障] 补充风格匹配: {old_item.get('name')}({old_item.get('style')}) "
                f"→ {candidate.get('name')}({candidate.get('style')})"
            )


def _ensure_body_type_guarantee(
    items: List[Dict],
    all_scored: List[Dict],
    body_type: str,
    used_ids: set,
) -> None:
    """
    确保 top-5 中至少有1件体型匹配物品（最佳版型）

    如果 top-5 中没有匹配用户最佳版型的物品，从候选中找一件替换。
    """
    from packages.recommendation.config import BODY_TYPE_FIT

    fit_map = BODY_TYPE_FIT.get(body_type)
    if not fit_map:
        return

    best_fit = max(fit_map.keys(), key=lambda k: fit_map[k])

    # 检查是否已有体型匹配
    for item in items:
        detail = item.get("attributes_detail") or {}
        if isinstance(detail, dict):
            fit = detail.get("款式", {}).get("版型", "")
            if fit == best_fit:
                return

    # 从候选中找一件体型匹配的物品
    body_candidate = None
    for candidate in all_scored:
        cand_id = str(candidate.get("id", candidate.get("item_code", "")))
        if cand_id in used_ids:
            continue
        if (candidate.get("temp_score") or 0) < TEMP_SAFETY_THRESHOLD:
            continue
        detail = candidate.get("attributes_detail") or {}
        if isinstance(detail, dict):
            fit = detail.get("款式", {}).get("版型", "")
            if fit == best_fit:
                body_candidate = candidate
                break

    if not body_candidate:
        return

    # 替换最低分的非核心物品（位置4或3，即最后几件）
    for i in range(len(items) - 1, 1, -1):
        cat = items[i].get("category", "")
        if cat in TOP_BODY_CATEGORIES or cat in BOTTOM_BODY_CATEGORIES:
            continue
        if _is_coverage_critical(items[i], items):
            continue
        if (items[i].get("temp_score") or 0) >= TEMP_ESSENTIAL_THRESHOLD:
            continue
        old_item = items[i]
        items[i] = body_candidate
        used_ids.discard(str(old_item.get("id", old_item.get("item_code", ""))))
        used_ids.add(str(body_candidate.get("id", body_candidate.get("item_code", ""))))
        logger.debug(
            f"[体型保障] 补充体型匹配: {old_item.get('name')} "
            f"→ {body_candidate.get('name')}(版型:{best_fit})"
        )
        return


def _ensure_wuxing_top1(
    items: List[Dict],
    all_scored: List[Dict],
    target_elements: List[str],
    used_ids: set,
) -> None:
    """
    确保 top-1 的 primary_element 匹配喜用神

    策略：
    1. 优先在 top-5 内部交换（不破坏场景适配性）
    2. 如果 top-5 无匹配，从候选中找一件高场景分的五行匹配物品替换 top-1
    """
    if not target_elements:
        return

    # top-1 主五行已匹配（满分情况）
    if items[0].get("primary_element") in target_elements:
        return

    # 在 top-5 中找主五行匹配的，提升到 top-1
    for i in range(1, len(items)):
        if items[i].get("primary_element") in target_elements:
            items[0], items[i] = items[i], items[0]
            logger.debug(
                f"[五行保障] 提升五行匹配到top-1: {items[0].get('name')}({items[0].get('primary_element')})"
            )
            return

    # 无主五行匹配，尝试次五行（评估器给3分）
    if items[0].get("secondary_element") in target_elements:
        return  # top-1 次五行已匹配，不交换

    # top-5 都不匹配，从候选中找一件五行匹配且场景安全的物品
    for candidate in all_scored[:20]:  # 只看前20名（保证质量）
        cand_id = str(candidate.get("id", candidate.get("item_code", "")))
        if cand_id in used_ids:
            continue
        if candidate.get("primary_element") not in target_elements:
            continue
        if (candidate.get("temp_score") or 0) < TEMP_SAFETY_THRESHOLD:
            continue
        if (candidate.get("scene_score") or 0.5) < 0.3:
            continue
        # 替换 top-1
        old_item = items[0]
        items[0] = candidate
        used_ids.discard(str(old_item.get("id", old_item.get("item_code", ""))))
        used_ids.add(str(candidate.get("id", candidate.get("item_code", ""))))
        logger.debug(
            f"[五行保障] 替换top-1为五行匹配: {old_item.get('name')} "
            f"→ {candidate.get('name')}({candidate.get('primary_element')})"
        )
        return


def _find_swap_target_for_personalization(
    items: List[Dict],
    style_preference: str,
    keywords: List[str],
) -> int | None:
    """
    为个性化保障找到可替换的物品索引

    不替换：精确风格已匹配的物品、覆盖关键物品、上装/下装/裙装
    """
    cat_counts = {}
    for item in items:
        cat = item.get("category", "")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    def _is_exact_style_match(item):
        return item.get("style") == style_preference

    def _can_swap(i):
        if _is_exact_style_match(items[i]):
            return False
        if _is_coverage_critical(items[i], items):
            return False
        cat = items[i].get("category", "")
        if cat in TOP_BODY_CATEGORIES or cat in BOTTOM_BODY_CATEGORIES:
            return False
        if (items[i].get("temp_score") or 0) >= TEMP_ESSENTIAL_THRESHOLD:
            return False
        return True

    # 策略1：重复品类的物品（保留点缀多样性）
    for i in range(len(items) - 1, -1, -1):
        if _can_swap(i):
            cat = items[i].get("category", "")
            if cat_counts.get(cat, 0) > 1:
                return i

    # 策略2：任何可替换物品（非点缀，从后往前）
    for i in range(len(items) - 1, -1, -1):
        if _can_swap(i) and items[i].get("category", "") not in ACCENT_CATEGORIES:
            return i

    # 策略3：最后手段 - 点缀类物品
    for i in range(len(items) - 1, -1, -1):
        if _can_swap(i):
            return i

    return None


def _find_swap_target_for_shoes(items: List[Dict]) -> int | None:
    """
    找到可替换为鞋履的物品索引

    优先级：
    1. 点缀类物品（配饰/饰品/文玩）中最低分的
    2. 同品类有2件以上的重复物品
    3. 外套类物品（鞋履比外套更重要，因为外套不是所有场景必需）
    """
    # 统计品类分布
    cat_counts = {}
    for item in items:
        cat = item.get("category", "")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    # 策略1：找同品类有2件以上的物品（保留点缀）
    for i in range(len(items) - 1, -1, -1):
        cat = items[i].get("category", "")
        if cat in SHOE_CATEGORIES:
            continue
        if cat_counts.get(cat, 0) > 1:
            if (items[i].get("temp_score") or 0) >= TEMP_ESSENTIAL_THRESHOLD:
                continue
            return i

    # 策略2：找外套类物品（仅当有2件以上外套时）
    for i in range(len(items) - 1, -1, -1):
        cat = items[i].get("category", "")
        if cat == "外套":
            if cat_counts.get("外套", 0) <= 1:
                continue  # 保护唯一外套
            if (items[i].get("temp_score") or 0) >= TEMP_ESSENTIAL_THRESHOLD:
                continue
            return i

    # 策略3：找任何非上装/下装/裙装/点缀的最低分物品
    for i in range(len(items) - 1, -1, -1):
        cat = items[i].get("category", "")
        if cat in TOP_BODY_CATEGORIES or cat in BOTTOM_BODY_CATEGORIES or cat in SHOE_CATEGORIES:
            continue
        if cat in ACCENT_CATEGORIES:
            continue
        if (items[i].get("temp_score") or 0) < TEMP_ESSENTIAL_THRESHOLD:
            return i

    # 策略4：最后手段 - 点缀类物品
    for i in range(len(items) - 1, -1, -1):
        cat = items[i].get("category", "")
        if cat in ACCENT_CATEGORIES:
            return i

    return None


def _find_swap_target_for_outer(items: List[Dict]) -> int | None:
    """
    找到可替换为外套的物品索引

    优先级：
    1. 同品类有2件以上的重复物品
    2. 任何非覆盖关键的非核心物品（非点缀）
    3. 最后手段：点缀类物品
    不替换：唯一上装/下装/裙装/鞋履
    """
    cat_counts = {}
    for item in items:
        cat = item.get("category", "")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    # 策略1：同品类有2件以上的物品（保留点缀）
    for i in range(len(items) - 1, -1, -1):
        cat = items[i].get("category", "")
        if cat == "外套":
            continue
        if cat_counts.get(cat, 0) > 1:
            if (items[i].get("temp_score") or 0) >= TEMP_ESSENTIAL_THRESHOLD:
                continue
            if _is_coverage_critical(items[i], items):
                continue
            return i

    # 策略2：任何非覆盖关键的非核心物品（非点缀）
    for i in range(len(items) - 1, -1, -1):
        cat = items[i].get("category", "")
        if cat in TOP_BODY_CATEGORIES or cat in BOTTOM_BODY_CATEGORIES:
            continue
        if cat == "外套":
            continue
        if cat in ACCENT_CATEGORIES:
            continue
        if _is_coverage_critical(items[i], items):
            continue
        if (items[i].get("temp_score") or 0) < TEMP_ESSENTIAL_THRESHOLD:
            return i

    # 策略3：最后手段 - 点缀类物品
    for i in range(len(items) - 1, -1, -1):
        cat = items[i].get("category", "")
        if cat in ACCENT_CATEGORIES:
            return i

    return None


def _find_best_category_candidate(
    all_scored: List[Dict],
    target_categories: set,
    used_ids: set,
    style_preference: str = None,
    target_elements: List[str] = None,
) -> Dict | None:
    """
    从已排序候选中找到指定品类的最佳物品（温度安全 + 场景分不为0）

    优先级：风格+五行双匹配 > 风格匹配 > 五行匹配 > 最佳分数
    """
    # 优先找风格+五行双匹配的候选
    if style_preference and target_elements:
        for candidate in all_scored:
            cand_cat = candidate.get("category", "")
            cand_id = str(candidate.get("id", candidate.get("item_code", "")))
            if cand_cat in target_categories and cand_id not in used_ids:
                if (candidate.get("temp_score") or 0) >= TEMP_SAFETY_THRESHOLD:
                    if (candidate.get("scene_score") or 0.5) > 0:
                        if (candidate.get("style") == style_preference and
                                candidate.get("primary_element") in target_elements):
                            return candidate

    # 优先找风格匹配的候选
    if style_preference:
        for candidate in all_scored:
            cand_cat = candidate.get("category", "")
            cand_id = str(candidate.get("id", candidate.get("item_code", "")))
            if cand_cat in target_categories and cand_id not in used_ids:
                if (candidate.get("temp_score") or 0) >= TEMP_SAFETY_THRESHOLD:
                    if (candidate.get("scene_score") or 0.5) > 0:
                        if candidate.get("style") == style_preference:
                            return candidate

    # 找五行匹配的候选
    if target_elements:
        for candidate in all_scored:
            cand_cat = candidate.get("category", "")
            cand_id = str(candidate.get("id", candidate.get("item_code", "")))
            if cand_cat in target_categories and cand_id not in used_ids:
                if (candidate.get("temp_score") or 0) >= TEMP_SAFETY_THRESHOLD:
                    if (candidate.get("scene_score") or 0.5) > 0:
                        if candidate.get("primary_element") in target_elements:
                            return candidate

    # 回退到最佳分数候选
    for candidate in all_scored:
        cand_cat = candidate.get("category", "")
        cand_id = str(candidate.get("id", candidate.get("item_code", "")))
        if cand_cat in target_categories and cand_id not in used_ids:
            if (candidate.get("temp_score") or 0) >= TEMP_SAFETY_THRESHOLD:
                if (candidate.get("scene_score") or 0.5) > 0:
                    return candidate
    return None


def _find_swap_target(
    items: List[Dict],
    exclude_categories: set,
) -> int | None:
    """
    找到可替换的物品索引

    优先级：
    1. 同品类有2件以上的物品（从最低分开始）
    2. 非核心服装品类（配饰/饰品/文玩）
    3. 不替换温度必需物品
    """
    # 统计品类分布
    cat_counts = {}
    for item in items:
        cat = item.get("category", "")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    # 策略1：找同品类有2件以上的（从后往前，即最低分）
    for i in range(len(items) - 1, -1, -1):
        cat = items[i].get("category", "")
        if cat in exclude_categories:
            continue
        if cat_counts.get(cat, 0) > 1:
            # 不替换温度必需物品
            if (items[i].get("temp_score") or 0) >= TEMP_ESSENTIAL_THRESHOLD:
                continue
            return i

    # 策略2：找点缀类物品（配饰/饰品/文玩）
    for i in range(len(items) - 1, -1, -1):
        cat = items[i].get("category", "")
        if cat in exclude_categories:
            continue
        if cat in ACCENT_CATEGORIES:
            return i

    # 策略3：找非核心品类的最低分物品
    for i in range(len(items) - 1, -1, -1):
        cat = items[i].get("category", "")
        if cat in exclude_categories:
            continue
        if cat not in OUTFIT_CORE_CATEGORIES:
            if (items[i].get("temp_score") or 0) >= TEMP_ESSENTIAL_THRESHOLD:
                continue
            return i

    # 最后手段：找任何非温度必需的物品
    for i in range(len(items) - 1, -1, -1):
        cat = items[i].get("category", "")
        if cat in exclude_categories:
            continue
        if (items[i].get("temp_score") or 0) < TEMP_ESSENTIAL_THRESHOLD:
            return i

    return None


def ensure_wuxing_diversity(
    items: List[Dict],
    all_scored: List[Dict],
    limit: int,
) -> List[Dict]:
    """
    五行多样性约束：确保推荐结果至少覆盖 2 种不同五行属性

    策略：
    - 如果 top-k 中所有物品都是同一五行，用次高分的不同五行物品替换最低分的重复物品
    - 最多替换 1 件，避免过度干预排序
    - 不引入 temp_score < TEMP_SAFETY_THRESHOLD 的候选

    Args:
        items: 当前 top-k 物品列表
        all_scored: 所有已评分物品（已排序）
        limit: top-k 数量

    Returns:
        五行多样性优化后的物品列表
    """
    if len(items) < 2:
        return items

    # 统计当前五行分布
    elements = set()
    for item in items:
        elem = item.get("primary_element", "")
        if elem:
            elements.add(elem)

    if len(elements) >= 2:
        return items

    # 找出主导五行
    dominant_element = elements.pop() if elements else None

    # 从备选中找分数最高的不同五行物品（温度安全）
    used_ids = {str(item.get("id", item.get("item_code", ""))) for item in items}
    best_replacement = None
    for candidate in all_scored:
        cand_elem = candidate.get("primary_element", "")
        cand_id = str(candidate.get("id", candidate.get("item_code", "")))
        if cand_elem and cand_elem != dominant_element and cand_id not in used_ids:
            if (candidate.get("temp_score") or 0) < TEMP_SAFETY_THRESHOLD:
                continue
            best_replacement = candidate
            break

    if best_replacement:
        for i in range(len(items) - 1, -1, -1):
            if items[i].get("primary_element", "") == dominant_element:
                logger.debug(
                    f"[五行多样性] 替换: {items[i].get('name')}({dominant_element}) "
                    f"→ {best_replacement.get('name')}({best_replacement.get('primary_element')})"
                )
                items[i] = best_replacement
                break

    return items
