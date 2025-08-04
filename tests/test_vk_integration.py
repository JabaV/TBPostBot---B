import types
from datetime import datetime, timedelta

import pytest

import botautomatic as ba


class DummyVK:
    """Простой двойник VK API для мока вызовов vk_api."""

    def __init__(self, wall_items=None, wall_suggests=None, group_wall_type=1):
        # wall.get вернёт items как есть
        self._wall_items = wall_items or []
        self._wall_suggests = wall_suggests or []
        self._group_wall_type = group_wall_type

    # Эмулируем подпакет groups
    class GroupsAPI:
        def __init__(self, wall_type):
            self._wall_type = wall_type

        def getById(self, group_id, fields):
            # Возвращаем список как делает VK API
            return [{"id": group_id, "wall": self._wall_type}]

    # Эмулируем подпакет wall
    class WallAPI:
        def __init__(self, items, suggests):
            self._items = items
            self._suggests = suggests

        def get(self, owner_id, offset=0, count=100, filter=None):
            if filter == "suggests":
                return {"items": self._suggests}
            # имитируем пагинацию по 100, но для тестов достаточно вернуть  items как есть
            return {"items": self._items}

    def build_api(self):
        api = types.SimpleNamespace()
        api.groups = DummyVK.GroupsAPI(self._group_wall_type)
        api.wall = DummyVK.WallAPI(self._wall_items, self._wall_suggests)
        return api


def test_get_last_post_wall_type_1(monkeypatch):
    """Должен находить последний пост бота по from_id при wall_type == 1."""
    now = int(datetime.now().timestamp())
    items = [
        {"from_id": 123, "date": now - 10},
        {"from_id": ba.bot_id, "date": now - 5},
    ]
    dummy = DummyVK(wall_items=items, group_wall_type=1)
    api = dummy.build_api()

    # Подменим vk и groups.getById/wall.get целиком
    monkeypatch.setattr(ba, "vk", api)

    post = ba.get_last_post(999)
    assert isinstance(post, dict)
    assert post["from_id"] == ba.bot_id


def test_get_last_post_wall_type_2_with_signer(monkeypatch):
    """Должен находить последний пост бота по signer_id при wall_type == 2."""
    now = int(datetime.now().timestamp())
    items = [
        {"signer_id": 111, "date": now - 10},
        {"signer_id": ba.bot_id, "date": now - 5},
    ]
    dummy = DummyVK(wall_items=items, group_wall_type=2)
    api = dummy.build_api()
    monkeypatch.setattr(ba, "vk", api)

    post = ba.get_last_post(999)
    assert isinstance(post, dict)
    assert post["signer_id"] == ba.bot_id


def test_check_suggests_empty_and_time_exceeded(monkeypatch):
    """Пустая предложка и превышение порога времени => вернуть 1 (постить)."""
    # Нет постов, пустая предложка
    dummy = DummyVK(wall_items=[], wall_suggests=[], group_wall_type=2)
    api = dummy.build_api()
    monkeypatch.setattr(ba, "vk", api)

    # Заполним time_dict так, чтобы время было в прошлом дальше порога
    gid = 555
    past = datetime.now() - timedelta(hours=13)
    ba.time_dict[gid] = past

    assert ba.check_suggests(gid, time_s=12 * 3600) == 1


def test_check_suggests_nonempty_but_too_old(monkeypatch):
    """Есть предложка, но её время старше порога => вернуть 1 (постить)."""
    old_suggest_time = int((datetime.now() - timedelta(days=4)).timestamp())
    suggests = [{"date": old_suggest_time}]

    dummy = DummyVK(wall_items=[], wall_suggests=suggests, group_wall_type=2)
    api = dummy.build_api()
    monkeypatch.setattr(ba, "vk", api)

    assert ba.check_suggests(777, time_s=3 * 24 * 3600) == 1


def test_check_suggests_recent(monkeypatch):
    """Недавняя предложка => 0 (не постить)."""
    recent_suggest_time = int((datetime.now() - timedelta(hours=1)).timestamp())
    suggests = [{"date": recent_suggest_time}]
    dummy = DummyVK(wall_items=[], wall_suggests=suggests, group_wall_type=2)
    api = dummy.build_api()
    monkeypatch.setattr(ba, "vk", api)

    assert ba.check_suggests(888, time_s=3 * 3600) == 0