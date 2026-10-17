"""
隐性行为反馈链路测试（2026-10-17 新增行为埋点扩充的回归防线）

覆盖三段：
1. /api/v1/wardrobe/behavior 的 action / item_source 白名单校验
2. 行为身份归属：以 Bearer token 的 sub 为准（修复前端传 undefined 导致
   行为全部落 user_id=NULL、聚合永远读不到的问题）
3. config.BEHAVIOR_WEIGHTS 的新增强信号（adopt/share/download/check_in）
   与 diary_service 的实穿打卡埋点
"""

import pytest
from unittest.mock import MagicMock, patch

from datetime import date, datetime

from packages.recommendation.config import (
    ALLOWED_BEHAVIOR_ACTIONS,
    ALLOWED_ITEM_SOURCES,
    BEHAVIOR_MAX_SCORE,
    BEHAVIOR_WEIGHTS,
)
from packages.recommendation.behavior import get_user_behavior_preferences
from apps.api.core.security import create_access_token


BEHAVIOR_URL = "/api/v1/wardrobe/behavior"

# 聚合查询的列顺序（与 behavior.py 的 SELECT 一致）
_AGG_COLUMNS = [
    "action", "dwell_duration", "item_id", "item_source",
    "category", "element", "color", "style", "days_old",
]


def _mock_pool_with_rows(rows):
    """构造 DatabasePool mock，让聚合查询返回指定行为行"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.description = [(c,) for c in _AGG_COLUMNS]
    mock_cursor.fetchall.return_value = rows
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    pool = MagicMock()
    pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
    pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
    return pool, mock_cursor


class TestBehaviorWhitelist:
    """行为上报的入参校验与身份归属"""

    @pytest.mark.parametrize("action", sorted(ALLOWED_BEHAVIOR_ACTIONS))
    async def test_allowed_actions_accepted(self, async_client, mock_db_pool, action):
        resp = await async_client.post(
            BEHAVIOR_URL,
            json={"item_id": "ITEM-001", "action": action, "item_source": "public"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"status": "ok"}

    async def test_unknown_action_rejected(self, async_client, mock_db_pool):
        resp = await async_client.post(
            BEHAVIOR_URL,
            json={"item_id": "ITEM-001", "action": "buy_this"},
        )
        assert resp.status_code == 400
        assert "不支持的行为类型" in resp.json()["detail"]
        # 脏 action 不得入库
        executed_sql = [str(c.args[0]) for c in mock_db_pool["cursor"].execute.call_args_list]
        assert not any("INSERT INTO user_behaviors" in sql for sql in executed_sql)

    async def test_unknown_item_source_rejected(self, async_client, mock_db_pool):
        assert "external" not in ALLOWED_ITEM_SOURCES
        resp = await async_client.post(
            BEHAVIOR_URL,
            json={"item_id": "1", "action": "view", "item_source": "external"},
        )
        assert resp.status_code == 400
        assert "不支持的物品来源" in resp.json()["detail"]

    async def test_token_identity_overrides_body_user_id(self, async_client, mock_db_pool):
        """已登录时以 token 为准，客户端不能替他人写行为"""
        token = create_access_token(data={"sub": "42"})
        resp = await async_client.post(
            BEHAVIOR_URL,
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": 999, "item_id": "ITEM-002", "action": "check_in"},
        )
        assert resp.status_code == 200
        insert_call = next(
            c for c in mock_db_pool["cursor"].execute.call_args_list
            if "INSERT INTO user_behaviors" in str(c.args[0])
        )
        params = insert_call.args[1]
        assert params[0] == 42, f"应使用 token 里的 user_id，实际 {params[0]}"
        assert params[3] == "check_in"

    async def test_anonymous_falls_back_to_body_user_id(self, async_client, mock_db_pool):
        resp = await async_client.post(
            BEHAVIOR_URL,
            json={"user_id": 7, "item_id": "ITEM-003", "action": "view"},
        )
        assert resp.status_code == 200
        insert_call = next(
            c for c in mock_db_pool["cursor"].execute.call_args_list
            if "INSERT INTO user_behaviors" in str(c.args[0])
        )
        assert insert_call.args[1][0] == 7

    async def test_invalid_token_does_not_break_reporting(self, async_client, mock_db_pool):
        resp = await async_client.post(
            BEHAVIOR_URL,
            headers={"Authorization": "Bearer not-a-jwt"},
            json={"item_id": "ITEM-004", "action": "share"},
        )
        assert resp.status_code == 200


class TestBehaviorWeightConfig:
    """权重配置与聚合代码不得漂移"""

    def test_new_signals_configured_and_ordered(self):
        assert BEHAVIOR_WEIGHTS["check_in"] > BEHAVIOR_WEIGHTS["download"] > BEHAVIOR_WEIGHTS["share"] > BEHAVIOR_WEIGHTS["adopt"]
        # 强正信号必须高于既有最强 implicit 信号（长停留）
        assert BEHAVIOR_WEIGHTS["adopt"] > BEHAVIOR_WEIGHTS["dwell_long"]

    def test_every_allowed_action_resolves_to_a_weight(self):
        """白名单里的 action 都要能在 BEHAVIOR_WEIGHTS 落到具体权重（dwell 走长/短分支）"""
        for action in ALLOWED_BEHAVIOR_ACTIONS:
            if action == "dwell":
                assert {"dwell_long", "dwell_short"} <= set(BEHAVIOR_WEIGHTS)
                continue
            assert action in BEHAVIOR_WEIGHTS, f"{action} 在白名单但无权重，会被当成 view 计入"

    def test_unknown_action_aggregates_as_view(self):
        """脏数据兼容：历史遗留的未知 action 仍按 view 权重，不抛异常"""
        rows = [("legacy_ping", 0, "C1", "public", "上装", "木", "绿色", "简约", 0)]
        pool, _ = _mock_pool_with_rows(rows)
        with patch("apps.api.core.database.DatabasePool", pool):
            prefs = get_user_behavior_preferences(1)
        known = [("view", 0, "C1", "public", "上装", "木", "绿色", "简约", 0)]
        pool2, _ = _mock_pool_with_rows(known)
        with patch("apps.api.core.database.DatabasePool", pool2):
            prefs_view = get_user_behavior_preferences(1)
        assert prefs == prefs_view

    def test_dwell_splits_by_duration(self):
        long_rows = [("dwell", 30, "C1", "public", "上装", None, None, None, 0),
                     ("view", 0, "C2", "public", "下装", None, None, None, 0)]
        short_rows = [("dwell", 3, "C1", "public", "上装", None, None, None, 0),
                      ("view", 0, "C2", "public", "下装", None, None, None, 0)]
        pool_l, _ = _mock_pool_with_rows(long_rows)
        pool_s, _ = _mock_pool_with_rows(short_rows)
        with patch("apps.api.core.database.DatabasePool", pool_l):
            prefs_long = get_user_behavior_preferences(1)
        with patch("apps.api.core.database.DatabasePool", pool_s):
            prefs_short = get_user_behavior_preferences(1)
        # 长停留相对浏览的领先幅度，必须大于短停留相对浏览的幅度
        ratio_long = prefs_long["category"]["上装"] / prefs_long["category"]["下装"]
        ratio_short = prefs_short["category"]["上装"] / prefs_short["category"]["下装"]
        assert ratio_long > ratio_short
        # 聚合内部归一化时按 4 位小数舍入，预期值用同一口径计算
        expected_long = round(
            BEHAVIOR_WEIGHTS["view"] / BEHAVIOR_WEIGHTS["dwell_long"] * BEHAVIOR_MAX_SCORE, 4
        )
        expected_short = round(
            BEHAVIOR_WEIGHTS["view"] / BEHAVIOR_WEIGHTS["dwell_short"] * BEHAVIOR_MAX_SCORE, 4
        )
        assert prefs_long["category"]["下装"] == pytest.approx(expected_long)
        assert prefs_short["category"]["下装"] == pytest.approx(expected_short)

    def test_check_in_dominates_view(self):
        """实穿打卡对同一维度的拉动应显著强于普通浏览"""
        rows = [
            ("check_in", 0, "C1", "public", "上装", None, None, None, 0),
            ("view", 0, "C2", "public", "下装", None, None, None, 0),
        ]
        pool, _ = _mock_pool_with_rows(rows)
        with patch("apps.api.core.database.DatabasePool", pool):
            prefs = get_user_behavior_preferences(1)
        assert prefs["category"]["上装"] == pytest.approx(BEHAVIOR_MAX_SCORE)
        assert prefs["category"]["下装"] == pytest.approx(
            round(BEHAVIOR_WEIGHTS["view"] / BEHAVIOR_WEIGHTS["check_in"] * BEHAVIOR_MAX_SCORE, 4)
        )

    def test_empty_user_id_short_circuits(self):
        assert get_user_behavior_preferences(0) == {}


class TestCheckInBehaviorRecording:
    """diary_service 把实穿打卡写成隐性行为"""

    @staticmethod
    def _item(**kwargs):
        from apps.api.schemas.diary import DiaryItemRequest
        base = dict(item_source="wardrobe", wardrobe_item_id=None, seed_item_code=None,
                    category=None, notes=None)
        base.update(kwargs)
        return DiaryItemRequest(**base)

    def test_maps_wardrobe_and_seed_to_item_source(self):
        from apps.api.services.diary_service import DiaryService

        cur = MagicMock()
        items = [
            self._item(item_source="wardrobe", wardrobe_item_id=15),
            self._item(item_source="seed", seed_item_code="ITEM-A"),
        ]
        DiaryService._record_check_in_behaviors(cur, 3, items)

        savepoints = [c for c in cur.execute.call_args_list if "SAVEPOINT check_in_behavior" in str(c.args[0])]
        assert len(savepoints) == 2, "应含 SAVEPOINT 与 RELEASE 各一次"
        exec_call = next(c for c in cur.executemany.call_args_list if "user_behaviors" in str(c.args[0]))
        assert exec_call.args[1] == [(3, "15", "wardrobe"), (3, "ITEM-A", "public")]
        assert "'check_in'" in str(exec_call.args[0])

    def test_skips_items_without_identity(self):
        from apps.api.services.diary_service import DiaryService

        cur = MagicMock()
        DiaryService._record_check_in_behaviors(cur, 3, [self._item(item_source="wardrobe")])
        cur.executemany.assert_not_called()

    def test_failure_does_not_raise_or_abort_transaction(self):
        """埋点写失败必须回滚到保存点并继续，不能拖垮打卡主链路"""
        from apps.api.services.diary_service import DiaryService

        cur = MagicMock()
        cur.executemany.side_effect = RuntimeError("table missing")
        DiaryService._record_check_in_behaviors(cur, 3, [self._item(wardrobe_item_id=8)])

        sqls = [str(c.args[0]) for c in cur.execute.call_args_list]
        assert any("ROLLBACK TO SAVEPOINT check_in_behavior" in s for s in sqls)

    def test_add_item_to_diary_is_wired_to_the_hook(self):
        """接上钩子：单件追加到日记时也要产生 check_in 行为（防未来重构把埋点弄丢）"""
        from apps.api.services.diary_service import DiaryService

        mock_conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.return_value = {
            "id": 1, "diary_id": 1, "item_source": "wardrobe",
            "wardrobe_item_id": 9, "seed_item_code": None, "category": None, "notes": None,
            "created_at": datetime(2026, 10, 17, 12, 0, 0),
        }
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        pool = MagicMock()
        pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        item = self._item(item_source="wardrobe", wardrobe_item_id=9)
        # diary_service 在模块层 import 了 DatabasePool，必须 patch 它自己的引用
        with patch("apps.api.services.diary_service.DatabasePool", pool), \
                patch.object(DiaryService, "_record_check_in_behaviors") as mock_hook:
            DiaryService.add_item_to_diary(1, 3, item)

        assert mock_hook.called, "add_item_to_diary 未上报实穿行为"
        hook_user_id = mock_hook.call_args.args[1]
        assert hook_user_id == 3
        assert mock_hook.call_args.args[2] == [item]

    def test_create_diary_is_wired_to_the_hook(self):
        """整单打卡（带 items）也要批量产生 check_in 行为"""
        from apps.api.schemas.diary import CreateDiaryRequest
        from apps.api.services.diary_service import DiaryService

        mock_conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.return_value = {"id": 7, "user_id": 3, "diary_date": date(2026, 10, 17)}
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        pool = MagicMock()
        pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        items = [self._item(item_source="seed", seed_item_code="ITEM-B")]
        data = CreateDiaryRequest(diary_date=date(2026, 10, 17), items=items)

        with patch("apps.api.services.diary_service.DatabasePool", pool), \
                patch.object(DiaryService, "_insert_diary_items"), \
                patch.object(DiaryService, "_adjust_wardrobe_wear"), \
                patch.object(DiaryService, "_wardrobe_ids_from_items", return_value=[]), \
                patch.object(DiaryService, "_build_diary_response", return_value=MagicMock()), \
                patch.object(DiaryService, "_record_check_in_behaviors") as mock_hook:
            DiaryService.create_diary(3, data)

        assert mock_hook.called, "create_diary 未上报实穿行为"
        assert mock_hook.call_args.args[1] == 3
        assert mock_hook.call_args.args[2] == items
