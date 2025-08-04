"""Одноразовый отладочный скрипт для диагностики VK и бота.

Запускать из корня проекта:
  python -m tools.debug_probe

Функции:
- Проверка токена и базовых вызовов VK API.
- Проверка wall_type для заданной группы.
- Пробная публикация "PING" поста с (и без) вложения.
- Быстрые проверки build_text и парсера groups.txt.
"""

from __future__ import annotations

import os
import sys
import traceback
from typing import Any, Mapping, Optional

# Локальный импорт основного бота; важно запускать из корня проекта
try:
   import botautomatic as ba  # noqa: E402
except Exception:
    print("[FATAL] Не удалось импортировать botautomatic.py. Текущая директория:", os.getcwd())
    print("sys.path[0..5]:", sys.path[:6])
    print("Трассировка:\n", "".join(traceback.format_exc()))
    sys.exit(1)


def p(title: str, value: Any) -> None:
    print(f"\n=== {title} ===\n{value}")


def check_env() -> None:
    p("Python version", sys.version)
    p("Working dir", os.getcwd())
    token = os.environ.get("TOKEN") or os.environ.get("token")
    p("TOKEN present", bool(token))
    p("DEFAULT_WAIT_TIME", os.environ.get("DEFAULT_WAIT_TIME"))


def check_vk_basics() -> None:
    try:
        me = ba.vk.users.get()
        p("vk.users.get()", me)
        p("bot_id", ba.bot_id)
        info = ba.vk.account.getInfo()
        p("vk.account.getInfo()", info)
    except Exception as e:
        p("VK BASIC ERROR", f"{e}\n{traceback.format_exc()}")


def check_group_wall(group_id: int) -> Optional[int]:
    try:
        grp = ba.vk.groups.getById(group_id=group_id, fields="wall,can_post,can_suggest")
        p("vk.groups.getById(..., fields='wall,can_post,can_suggest')", grp)
        wt = grp[0].get("wall")
        p("wall_type", wt)
        return int(wt) if wt is not None else None
    except Exception as e:
        p("GROUP INFO ERROR", f"{e}\n{traceback.format_exc()}")
        return None


def try_build_text() -> None:
    try:
        sample = ba.build_text("-", "-", "-", "-", "-", "-", "-")
        p("build_text('-',...)", sample[:500] if sample else "(empty)")
    except Exception as e:
        p("BUILD_TEXT ERROR", f"{e}\n{traceback.format_exc()}")


def try_parse_line(line: str) -> None:
    try:
        res = ba.parse(line)
        p("parse(line) -> (group, text/path, image, delay)", res)
    except Exception as e:
        p("PARSE ERROR", f"{e}\n{traceback.format_exc()}")


def try_post_ping(group_id: int, image_id: Optional[int]) -> None:
    """Попробовать опубликовать тестовый пост 'PING'."""
    try:
        if image_id is None:
            p("wall.post attempt (no attachments)", "message='PING'")
            resp = ba.vk.wall.post(owner_id=-group_id, message="PING")
            p("wall.post response", resp)
        else:
            att = f"photo{ba.bot_id}_{image_id}"
            p("wall.post attempt (with attachment)", f"attachments={att}")
            resp = ba.vk.wall.post(owner_id=-group_id, message="PING", attachments=att)
            p("wall.post response", resp)
    except Exception as e:
        p("POST ERROR", f"{e}\n{traceback.format_exc()}")


def try_check_suggests(group_id: int) -> None:
    try:
        res = ba.check_suggests(group_id, time_s=60)  # порог 60 сек, для проверки
        p("check_suggests(group, 60s)", res)
    except Exception as e:
        p("CHECK_SUGGESTS ERROR", f"{e}\n{traceback.format_exc()}")


def try_get_last_post(group_id: int) -> None:
    try:
        post = ba.get_last_post(group_id)
        p("get_last_post(group)", post)
        if isinstance(post, Mapping):
            p("last_post['date']", post.get("date"))
    except Exception as e:
        p("GET_LAST_POST ERROR", f"{e}\n{traceback.format_exc()}")


def main() -> None:
    print("== TBPostBot Debug Probe ==")
    check_env()
    check_vk_basics()

    # Базовая рабочая строка из вашего groups.txt
    line = "213294396:[-:-:-:-:-:-:-:457239111]|5m"
    try_parse_line(line)
    group_id = 213294396
    image_id = 457239111

    wt = check_group_wall(group_id)  # 1 | 2 | 3 | None
    try_build_text()
    try_get_last_post(group_id)
    try_check_suggests(group_id)

    # Пробный пост. ВНИМАНИЕ: ДЕЙСТВИТЕЛЬНАЯ ПУБЛИКАЦИЯ!
    # Сначала попробуем без вложений, затем с вложением.
    print("\n! ВНИМАНИЕ: Следующие два вызова реально публикуют тестовый пост 'PING' !")
    try_post_ping(group_id, image_id=None)
    try_post_ping(group_id, image_id=image_id)

    print("\n== Debug probe finished ==")


if __name__ == "__main__":
    main()