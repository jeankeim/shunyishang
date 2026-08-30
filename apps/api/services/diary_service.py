"""
穿搭日记服务层
处理日记 CRUD、日历视图、统计等操作
"""

import json
import logging
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any

from psycopg2.extras import RealDictCursor

from apps.api.core.database import DatabasePool
from apps.api.schemas.diary import (
    CreateDiaryRequest,
    UpdateDiaryRequest,
    DiaryItemRequest,
    DiaryResponse,
    DiaryListResponse,
    DiaryCalendarEntry,
    DiaryCalendarResponse,
    DiaryStatsResponse,
    DiaryOutfitItemResponse,
)

logger = logging.getLogger(__name__)


class DiaryService:
    """穿搭日记服务"""

    @staticmethod
    def create_diary(user_id: int, data: CreateDiaryRequest) -> DiaryResponse:
        """创建日记+关联衣物"""
        query = """
            INSERT INTO outfit_diaries (
                user_id, diary_date, mood, occasion, notes, rating, image_urls
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, user_id, diary_date, mood, weather_snapshot, occasion,
                      notes, rating, ai_review, image_urls, created_at, updated_at
        """
        params = [
            user_id,
            data.diary_date,
            data.mood,
            data.occasion,
            data.notes,
            data.rating,
            json.dumps(data.image_urls),
        ]

        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                row = cur.fetchone()

                # 关联衣物
                if data.items:
                    DiaryService._insert_diary_items(cur, row['id'], data.items)
                    DiaryService._adjust_wardrobe_wear(
                        cur, user_id,
                        DiaryService._wardrobe_ids_from_items(data.items),
                        delta=1,
                    )

                conn.commit()

        return DiaryService._build_diary_response(row, user_id)

    @staticmethod
    def _wardrobe_ids_from_items(items: List[DiaryItemRequest]) -> List[int]:
        """提取关联衣物中的衣橱物品 ID 列表"""
        return [
            it.wardrobe_item_id for it in items
            if it.item_source == 'wardrobe' and it.wardrobe_item_id
        ]

    @staticmethod
    def _adjust_wardrobe_wear(cur, user_id: int, wardrobe_item_ids: List[int], delta: int) -> None:
        """
        日记关联衣物时对称更新衣橱穿着统计

        - wear_count 增量维护（+1/-1，下限 0），历史数据不回溯
        - last_worn_date 从剩余日记关联重算（无关联则置 NULL）
        需在同一事务、关联行已插入/删除后调用
        """
        for wid in wardrobe_item_ids:
            if delta > 0:
                cur.execute(
                    """
                    UPDATE user_wardrobe
                    SET wear_count = COALESCE(wear_count, 0) + %s
                    WHERE id = %s AND user_id = %s
                    """,
                    [delta, wid, user_id],
                )
            else:
                cur.execute(
                    """
                    UPDATE user_wardrobe
                    SET wear_count = GREATEST(COALESCE(wear_count, 0) - %s, 0)
                    WHERE id = %s AND user_id = %s
                    """,
                    [-delta, wid, user_id],
                )
            cur.execute(
                """
                UPDATE user_wardrobe uw
                SET last_worn_date = (
                    SELECT MAX(d.diary_date)
                    FROM diary_outfit_items doi
                    JOIN outfit_diaries d ON d.id = doi.diary_id
                    WHERE doi.wardrobe_item_id = uw.id AND d.user_id = %s
                )
                WHERE uw.id = %s AND uw.user_id = %s
                """,
                [user_id, wid, user_id],
            )

    @staticmethod
    def _insert_diary_items(cur, diary_id: int, items: List[DiaryItemRequest]):
        """批量插入日记关联衣物"""
        query = """
            INSERT INTO diary_outfit_items (
                diary_id, item_source, wardrobe_item_id, seed_item_code, category, notes
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        for item in items:
            cur.execute(query, [
                diary_id,
                item.item_source,
                item.wardrobe_item_id,
                item.seed_item_code,
                item.category,
                item.notes,
            ])

    @staticmethod
    def get_diaries(
        user_id: int,
        page: int = 1,
        size: int = 20,
        mood_filter: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> DiaryListResponse:
        """分页查询日记+过滤"""
        base_query = "SELECT * FROM outfit_diaries WHERE user_id = %s"
        params: list = [user_id]

        if mood_filter:
            base_query += " AND mood = %s"
            params.append(mood_filter)
        if date_from:
            base_query += " AND diary_date >= %s"
            params.append(date_from)
        if date_to:
            base_query += " AND diary_date <= %s"
            params.append(date_to)

        # 总数
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) sub"

        # 分页
        offset = (page - 1) * size
        list_query = base_query + " ORDER BY diary_date DESC LIMIT %s OFFSET %s"
        params.extend([size, offset])

        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(count_query, params[:-2])
                total = cur.fetchone()['total']

                cur.execute(list_query, params)
                rows = cur.fetchall()

        diaries = [DiaryService._build_diary_response(row, user_id) for row in rows]
        return DiaryListResponse(diaries=diaries, total=total, page=page, size=size)

    @staticmethod
    def get_diary_by_id(diary_id: int, user_id: int) -> Optional[DiaryResponse]:
        """获取单条日记+关联衣物"""
        query = "SELECT * FROM outfit_diaries WHERE id = %s AND user_id = %s"
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, [diary_id, user_id])
                row = cur.fetchone()

        if not row:
            return None
        return DiaryService._build_diary_response(row, user_id)

    @staticmethod
    def update_diary(diary_id: int, user_id: int, data: UpdateDiaryRequest) -> Optional[DiaryResponse]:
        """更新日记"""
        updates = []
        params: list = []

        if data.mood is not None:
            updates.append("mood = %s")
            params.append(data.mood)
        if data.occasion is not None:
            updates.append("occasion = %s")
            params.append(data.occasion)
        if data.notes is not None:
            updates.append("notes = %s")
            params.append(data.notes)
        if data.rating is not None:
            updates.append("rating = %s")
            params.append(data.rating)
        if data.image_urls is not None:
            updates.append("image_urls = %s")
            params.append(json.dumps(data.image_urls))

        if not updates:
            return DiaryService.get_diary_by_id(diary_id, user_id)

        updates.append("updated_at = NOW()")
        params.extend([diary_id, user_id])

        query = f"""
            UPDATE outfit_diaries
            SET {', '.join(updates)}
            WHERE id = %s AND user_id = %s
            RETURNING *
        """

        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                conn.commit()

        if not row:
            return None
        return DiaryService._build_diary_response(row, user_id)

    @staticmethod
    def delete_diary(diary_id: int, user_id: int) -> bool:
        """删除日记（同步回退关联衣物的穿着计数）"""
        items_query = """
            SELECT wardrobe_item_id FROM diary_outfit_items
            WHERE diary_id = %s AND item_source = 'wardrobe' AND wardrobe_item_id IS NOT NULL
        """
        query = "DELETE FROM outfit_diaries WHERE id = %s AND user_id = %s"
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 先取关联的衣橱衣物（删除后级联清空，无法再查）
                cur.execute(items_query, [diary_id])
                wardrobe_ids = [row['wardrobe_item_id'] for row in cur.fetchall()]

                cur.execute(query, [diary_id, user_id])
                affected = cur.rowcount

                if affected and wardrobe_ids:
                    DiaryService._adjust_wardrobe_wear(cur, user_id, wardrobe_ids, delta=-1)

                conn.commit()
        return affected > 0

    @staticmethod
    def get_calendar(user_id: int, year: int, month: int) -> DiaryCalendarResponse:
        """日历视图"""
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        query = """
            SELECT d.diary_date, d.mood, d.rating,
                   EXISTS(SELECT 1 FROM diary_outfit_items doi WHERE doi.diary_id = d.id) as has_items
            FROM outfit_diaries d
            WHERE d.user_id = %s AND d.diary_date >= %s AND d.diary_date < %s
            ORDER BY d.diary_date
        """
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, [user_id, start_date, end_date])
                rows = cur.fetchall()

        entries = [
            DiaryCalendarEntry(
                date=row['diary_date'],
                mood=row['mood'],
                rating=row['rating'],
                has_items=row['has_items'],
            )
            for row in rows
        ]
        return DiaryCalendarResponse(year=year, month=month, entries=entries)

    @staticmethod
    def get_stats(user_id: int) -> DiaryStatsResponse:
        """统计数据"""
        stats_query = """
            SELECT
                COUNT(*) as total_diaries,
                AVG(rating) as avg_rating
            FROM outfit_diaries
            WHERE user_id = %s
        """
        mood_query = """
            SELECT mood, COUNT(*) as count
            FROM outfit_diaries
            WHERE user_id = %s AND mood IS NOT NULL
            GROUP BY mood
        """
        items_query = """
            SELECT COUNT(*) as total
            FROM diary_outfit_items doi
            JOIN outfit_diaries d ON d.id = doi.diary_id
            WHERE d.user_id = %s
        """
        dates_query = """
            SELECT diary_date FROM outfit_diaries
            WHERE user_id = %s
            ORDER BY diary_date DESC
        """

        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(stats_query, [user_id])
                stats = cur.fetchone()

                cur.execute(mood_query, [user_id])
                mood_rows = cur.fetchall()

                cur.execute(items_query, [user_id])
                items_row = cur.fetchone()

                cur.execute(dates_query, [user_id])
                date_rows = cur.fetchall()

        mood_distribution = {row['mood']: row['count'] for row in mood_rows}

        # 计算连续打卡天数
        streak = 0
        if date_rows:
            dates = [row['diary_date'] for row in date_rows]
            today = date.today()
            check_date = today
            for d in dates:
                if d == check_date:
                    streak += 1
                    check_date -= timedelta(days=1)
                elif d < check_date:
                    # 如果今天没有，从最新日期开始
                    if streak == 0 and d == today - timedelta(days=1):
                        check_date = d
                        streak = 1
                        check_date -= timedelta(days=1)
                    else:
                        break

        return DiaryStatsResponse(
            total_diaries=stats['total_diaries'],
            avg_rating=round(float(stats['avg_rating']), 1) if stats['avg_rating'] else None,
            mood_distribution=mood_distribution,
            streak_days=streak,
            total_items=items_row['total'] if items_row else 0,
        )

    @staticmethod
    def add_item_to_diary(diary_id: int, user_id: int, item_data: DiaryItemRequest) -> Optional[DiaryOutfitItemResponse]:
        """添加衣物到日记"""
        # 验证日记归属
        check_query = "SELECT id FROM outfit_diaries WHERE id = %s AND user_id = %s"
        insert_query = """
            INSERT INTO diary_outfit_items (
                diary_id, item_source, wardrobe_item_id, seed_item_code, category, notes
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, diary_id, item_source, wardrobe_item_id, seed_item_code, category, notes, created_at
        """
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(check_query, [diary_id, user_id])
                if not cur.fetchone():
                    return None

                cur.execute(insert_query, [
                    diary_id,
                    item_data.item_source,
                    item_data.wardrobe_item_id,
                    item_data.seed_item_code,
                    item_data.category,
                    item_data.notes,
                ])
                row = cur.fetchone()

                # 衣橱衣物追加进日记 = 一次穿着记录
                if item_data.item_source == 'wardrobe' and item_data.wardrobe_item_id:
                    DiaryService._adjust_wardrobe_wear(
                        cur, user_id, [item_data.wardrobe_item_id], delta=1
                    )

                conn.commit()

        return DiaryOutfitItemResponse(**dict(row))

    @staticmethod
    def remove_item_from_diary(diary_id: int, user_id: int, item_id: int) -> bool:
        """从日记移除衣物（同步回退穿着计数）"""
        check_query = "SELECT id FROM outfit_diaries WHERE id = %s AND user_id = %s"
        lookup_query = """
            SELECT item_source, wardrobe_item_id
            FROM diary_outfit_items WHERE id = %s AND diary_id = %s
        """
        delete_query = "DELETE FROM diary_outfit_items WHERE id = %s AND diary_id = %s"

        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(check_query, [diary_id, user_id])
                if not cur.fetchone():
                    return False

                cur.execute(lookup_query, [item_id, diary_id])
                removed_row = cur.fetchone()

                cur.execute(delete_query, [item_id, diary_id])
                affected = cur.rowcount

                if (
                    affected
                    and removed_row
                    and removed_row['item_source'] == 'wardrobe'
                    and removed_row['wardrobe_item_id']
                ):
                    DiaryService._adjust_wardrobe_wear(
                        cur, user_id, [removed_row['wardrobe_item_id']], delta=-1
                    )

                conn.commit()
        return affected > 0

    @staticmethod
    def update_ai_review(diary_id: int, user_id: int, review: Dict[str, Any]) -> Optional[DiaryResponse]:
        """更新AI点评"""
        query = """
            UPDATE outfit_diaries
            SET ai_review = %s, updated_at = NOW()
            WHERE id = %s AND user_id = %s
            RETURNING *
        """
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, [json.dumps(review), diary_id, user_id])
                row = cur.fetchone()
                conn.commit()

        if not row:
            return None
        return DiaryService._build_diary_response(row, user_id)

    @staticmethod
    def _get_diary_items(diary_id: int) -> List[DiaryOutfitItemResponse]:
        """获取日记关联衣物（含名称、图片等扩展信息）"""
        query = """
            SELECT doi.id, doi.diary_id, doi.item_source,
                   doi.wardrobe_item_id, doi.seed_item_code,
                   doi.category, doi.notes, doi.created_at,
                   COALESCE(uw.name, si.name) as name,
                   COALESCE(uw.image_url, si.image_url) as image_url,
                   COALESCE(uw.primary_element, si.primary_element) as primary_element,
                   uw.notes as wardrobe_notes
            FROM diary_outfit_items doi
            LEFT JOIN user_wardrobe uw ON doi.wardrobe_item_id = uw.id
            LEFT JOIN items si ON doi.seed_item_code = si.item_code
            WHERE doi.diary_id = %s
            ORDER BY doi.created_at
        """
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, [diary_id])
                rows = cur.fetchall()

        return [DiaryOutfitItemResponse(**dict(row)) for row in rows]

    @staticmethod
    def _build_diary_response(row: Dict, user_id: int) -> DiaryResponse:
        """构建完整日记响应（含关联衣物）"""
        diary_data = dict(row)

        # 解析 JSONB 字段
        image_urls = diary_data.get('image_urls', [])
        if isinstance(image_urls, str):
            try:
                image_urls = json.loads(image_urls)
            except (json.JSONDecodeError, TypeError):
                image_urls = []

        ai_review = diary_data.get('ai_review', {})
        if isinstance(ai_review, str):
            try:
                ai_review = json.loads(ai_review)
            except (json.JSONDecodeError, TypeError):
                ai_review = {}

        weather_snapshot = diary_data.get('weather_snapshot', {})
        if isinstance(weather_snapshot, str):
            try:
                weather_snapshot = json.loads(weather_snapshot)
            except (json.JSONDecodeError, TypeError):
                weather_snapshot = {}

        # 获取关联衣物
        items = DiaryService._get_diary_items(diary_data['id'])

        return DiaryResponse(
            id=diary_data['id'],
            user_id=diary_data['user_id'],
            diary_date=diary_data['diary_date'],
            mood=diary_data.get('mood'),
            weather_snapshot=weather_snapshot,
            occasion=diary_data.get('occasion'),
            notes=diary_data.get('notes'),
            rating=diary_data.get('rating'),
            ai_review=ai_review,
            image_urls=image_urls,
            items=items,
            created_at=diary_data['created_at'],
            updated_at=diary_data['updated_at'],
        )


diary_service = DiaryService()
