import os
import pickle
import random
import re
from datetime import datetime, timedelta
from random import randint
from time import sleep
from typing import List, Optional, Tuple

import vk_api
from dotenv import load_dotenv  # type: ignore

from modules import module_logger

# загрузка переменных окружения из .env
load_dotenv()

skip = 0
# поддерживаем оба варианта имени, но приоритет у верхнего регистра
token = os.environ.get("TOKEN") or os.environ.get("token")
if not token:
    raise RuntimeError("VK API token is missing. Define TOKEN in .env or environment.")

# дефолтная пауза между постами, если не указана в groups.txt
wait_time = int(os.environ.get("DEFAULT_WAIT_TIME", str(60 * 60 * 12)))

vk_session = vk_api.VkApi(token=token)
vk = vk_session.get_api()
bot_id = vk.users.get()[0]["id"]

time_dict = {}
tgtg = 0


# функция для постинга
def post(_target_group: int, _text: str, _image: int):
    vk.wall.post(
        owner_id=-_target_group, message=_text, attachments=f"photo{bot_id}_{_image}"
    )


# --- NEW: Duration parser like "1d2h3m4s" (parts optional) ---
def parse_duration(spec: str) -> int:
    """
    Преобразует строку длительности (например, '3d2h1m5s' или '2h' или '45m') в секунды.
    """
    if not spec:
        return wait_time
    pattern = r"(?:(?P<d>\d+)d)?(?:(?P<h>\d+)h)?(?:(?P<m>\d+)m)?(?:(?P<s>\d+)s)?"
    m = re.fullmatch(pattern, spec.strip())
    if not m:
        # если формат неизвестен — лог и возврат дефолта
        module_logger.eLog(f"Bad delay format '{spec}', using default wait_time")
        return wait_time
    days = int(m.group("d") or 0)
    hours = int(m.group("h") or 0)
    mins = int(m.group("m") or 0)
    secs = int(m.group("s") or 0)
    return days * 86400 + hours * 3600 + mins * 60 + secs


# --- NEW: TextBuilder helpers ---
def load_variants_file(path: str) -> List[Tuple[str, str]]:
    """
    Загружает файл вариаций блоков/тегов/ссылок в формате:
    ##1
    text...
    ##2
    text...
    Возвращает список пар (ид_варианта, текст).
    Если встречаются заголовки вида '###name' — имя будет идентификатором.
    """
    variants: List[Tuple[str, str]] = []
    if not os.path.exists(path):
        return variants
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    # Разбиваем по линиям заголовков, допускаем ##<num> или ###<name>
    parts = re.split(r"^#{2,3}([^\r\n]+)\s*$", content, flags=re.MULTILINE)
    # parts будет: [pre, id1, block1, id2, block2, ...]
    # Игнорируем pre (до первого заголовка)
    for i in range(1, len(parts), 2):
        vid_raw = parts[i].strip()
        vid = vid_raw.lstrip("#").strip()
        body = parts[i + 1].strip()
        variants.append((vid, body))
    return variants


def pick_variant(variants: List[Tuple[str, str]], desired: Optional[str]) -> str:
    """
    Возвращает текст варианта.
    desired:
      - None или '-' => случайный
      - иначе ищем по id (совпадение идентификатора).
    Если не найден желаемый — случайный, если список пуст — пустая строка.
    """
    if not variants:
        return ""
    if desired is None or desired == "-":
        return random.choice(variants)[1]
    # ищем по идентификатору (строгое совпадение)
    for vid, body in variants:
        if vid == desired:
            return body
    # не нашли — случайный
    return random.choice(variants)[1]


def build_text(
    tags_var: Optional[str],
    b1_var: Optional[str],
    b2_var: Optional[str],
    b3_var: Optional[str],
    b4_var: Optional[str],
    b5_var: Optional[str],
    links_var: Optional[str],
) -> str:
    """
    Собирает итоговый текст из файлов:
      files/tags.txt
      files/block1.txt .. files/block5.txt
      files/links.txt
    Каждый файл содержит варианты в формате ##id / ###name.
    """
    tags = load_variants_file("files/tags.txt")
    b1 = load_variants_file("files/block1.txt")
    b2 = load_variants_file("files/block2.txt")
    b3 = load_variants_file("files/block3.txt")
    b4 = load_variants_file("files/block4.txt")
    b5 = load_variants_file("files/block5.txt")
    links = load_variants_file("files/links.txt")

    parts = []
    tv = pick_variant(tags, tags_var)
    if tv:
        parts.append(tv)
    for v, vv in [
        (b1, b1_var),
        (b2, b2_var),
        (b3, b3_var),
        (b4, b4_var),
        (b5, b5_var),
    ]:
        pv = pick_variant(v, vv)
        if pv:
            parts.append(pv)
    lv = pick_variant(links, links_var)
    if lv:
        parts.append(lv)
    # Соединяем блоки пустой строкой между ними
    return "\n\n".join(p.strip() for p in parts if p.strip())


# --- NEW: Новый парсер строки groups.txt c обратной совместимостью ---
def parse(_string: str) -> Tuple[int, str, int, Optional[int]]:
    """
    Поддержка старого формата:
      groupid:path|imageid[?seconds]
      где path == '-' означает рандом files/text{1..5}.txt
    И нового формата:
      groupid:[tags:b1:b2:b3:b4:b5:links:image]|delay
    где любой блок может быть '-' для рандома. delay в формате 1d2h3m4s.
    Пример рандомизации только b3:
      groupid:[-:-:-:b3var:-:-:linksvar:imageid]|3d2h
    """
    s = _string.strip()
    if not s:
        raise ValueError("Empty line")

    # Определяем новый формат по наличию '[' и ']'
    if "[" in s and "]" in s:
        # Новый формат
        try:
            group_part, right = s.split(":", 1)
            group_id = int(group_part)
            blocks_part = right[right.find("[") + 1 : right.find("]")]
            after = right[right.find("]") + 1 :].strip()
            delay_spec = None
            if after.startswith("|"):
                delay_spec = after[1:].strip()
            # Разбить варианты
            segs = blocks_part.split(":")
            if len(segs) != 8:
                raise ValueError("New format requires 8 segments in [ ... ]")
            tags_var, b1v, b2v, b3v, b4v, b5v, links_var, image_id_str = segs
            image_id = int(image_id_str)
            delay_seconds = parse_duration(delay_spec) if delay_spec else wait_time
            # Строим текст
            text_built = build_text(
                tags_var or None,
                b1v or None,
                b2v or None,
                b3v or None,
                b4v or None,
                b5v or None,
                links_var or None,
            )
            return group_id, text_built, image_id, delay_seconds
        except Exception as e:
            module_logger.eLog(f"Failed to parse new format line: '{s}'. Error: {e}")
            raise
    else:
        # Старый формат
        _timer = None
        _group, _text, _image = (
            s[: s.find(":")],
            s[s.find(":") + 1 : s.find("|")],
            s[s.find("|") + 1 :],
        )
        if "?" in s:
            _image = s[s.find("|") + 1 : s.find("?")]
            _timer = s[s.find("?") + 1 :]
            _timer = int(_timer)
        _group = int(_group)
        _image = int(_image.replace("\n", ""))
        return _group, _text, _image, _timer


def prepare(_text_or_built: str) -> Tuple[str, Optional[dict]]:
    """
    Старый путь: если пришел путь или '-' — загрузить контент из файла.
    Новый путь: если пришел уже собранный текст — вернуть как есть.
    Улучшено: безопасная загрузка dumping.pkl и логирование ошибок чтения файлов.
    """
    _time_dict = {}

    # Решаем, читать ли файл текста (старый формат)
    if _text_or_built != "-" and (
        ("\n" in _text_or_built) or (".txt" not in _text_or_built)
    ):
        _text = _text_or_built
    else:
        _text = _text_or_built
        if _text == "-":
            _text = "files/text" + str(random.randint(1, 5)) + ".txt"
        try:
            with open(_text, "r", encoding="utf-8") as f:
                _text = f.read()
        except Exception as e:
            module_logger.eLog(f"Failed to read text file '{_text}': {e}")
            _text = ""

    # безопасная загрузка словаря времени
    try:
        if (
            os.path.exists("files/dumping.pkl")
            and os.path.getsize("files/dumping.pkl") > 0
        ):
            with open("files/dumping.pkl", "rb") as _p:
                _time_dict = pickle.load(_p)
        else:
            # убедимся, что файл существует
            os.makedirs("files", exist_ok=True)
            open("files/dumping.pkl", "ab").close()
    except Exception as e:
        module_logger.eLog(f"Failed to load dumping.pkl: {e}")
        _time_dict = {}

    return _text, _time_dict


def get_last_post(_tg: int):
    """
    Возвращает последний пост, связанный с ботом, на стене группы _tg
    или None, если не найден. Возвращает -1 при ошибке.
    Улучшено логирование: логируем ключевые этапы и ошибки с контекстом.
    """
    last_post = None
    try:
        count = 2
        while count:
            group_info = vk.groups.getById(group_id=_tg, fields="wall")
            wt = group_info[0]["wall"]
            posts = vk.wall.get(
                owner_id=-_tg, offset=0 if count == 2 else 100, count=100
            )["items"]
            if len(posts) < 1:
                module_logger.Log(
                    f"No posts found in group {_tg} (offset {0 if count == 2 else 100})"
                )
                return None
            if wt == 1:
                for x in posts:
                    if x.get("from_id") == bot_id:
                        last_post = x
                        break
            elif wt in (2, 3):
                for x in posts:
                    if x.get("signer_id") == bot_id:
                        last_post = x
                        break
            if last_post is None:
                count -= 1
            else:
                module_logger.Log(f"Last bot-related post found in group {_tg}")
                return last_post
        return last_post
    except Exception as e:
        module_logger.eLog(f"get_last_post({_tg}) failed: {e}")
        return -1


def check_suggests(_tg: int, time_s: int):
    """
    Решение о постинге для стен 2/3 с учётом предложки.
    Улучшено логирование и обработка ошибок.
    """
    try:
        suggested_posts = vk.wall.get(owner_id=-_tg, filter="suggests")
    except Exception as e:
        module_logger.eLog(f"check_suggests({_tg}) get suggests failed: {e}")
        return -1

    last_pst = get_last_post(_tg)
    if len(suggested_posts.get("items", [])) < 1:
        if _tg in time_dict:
            if datetime.now() - time_dict[_tg] >= timedelta(seconds=time_s):
                module_logger.Log(
                    f"Suggest empty and time exceeded in group {_tg} — ready to post"
                )
                return 1
            else:
                return 0
        elif last_pst is not None:
            if last_pst != -1:
                if datetime.now() - datetime.fromtimestamp(
                    last_pst["date"]
                ) >= timedelta(seconds=time_s):
                    module_logger.Log(
                        f"Last post older than threshold in group {_tg} — ready to post"
                    )
                    return 1
                else:
                    return 0
            else:
                return -1
        else:
            if _tg in time_dict:
                if datetime.now() - time_dict[_tg] >= timedelta(seconds=time_s):
                    return 1
                else:
                    return 0
            else:
                return 1
    suggest_time = suggested_posts["items"][0]["date"]
    if datetime.now() - datetime.fromtimestamp(suggest_time) >= timedelta(
        seconds=time_s
    ):
        module_logger.Log(
            f"Suggest older than threshold in group {_tg} — ready to post"
        )
        return 1
    return 0


def choose_time(_timer):
    if _timer is None:
        return wait_time
    else:
        return _timer


while True:
    try:
        with open("files/groups.txt", "r", encoding="utf-8") as file:
            module_logger.eLog("STARTING FULL CYCLE")
            timef = open("files/time.txt", "w+", encoding="utf-8")
            timef.write(str(datetime.now()))
            timef.flush()
            timef.close()
            while True:
                string = file.readline()
                if not string:
                    break
                # Пропускаем строки, начинающиеся с "# " (комментарии)
                if string.lstrip().startswith("# "):
                    continue
                if skip == 1:
                    skip = 0
                    continue
                target_group, text_or_path_built, image, timer = parse(string)
                tgtg = target_group
                text, time_dict = prepare(text_or_path_built)
                module_logger.Log(f"Now working with group {target_group}")

                group = vk.groups.getById(group_id=target_group, fields="wall")
                wall_type = group[0]["wall"]
                module_logger.Log("Got the wall type")

                if wall_type == 2 or wall_type == 3:
                    should_post = check_suggests(target_group, choose_time(timer))
                    module_logger.Log(
                        f"Should I post in group {target_group}? result={should_post}"
                    )
                    if should_post == 1:
                        module_logger.Log("Decision: post now (suggest mode)")
                        vk.account.setOnline()
                        post(target_group, text, image)
                        time_dict[target_group] = datetime.now()
                        module_logger.Log("Posted and saved time")
                        try:
                            with open("files/dumping.pkl", "wb") as p:
                                pickle.dump(time_dict, p)
                        except Exception as e:
                            module_logger.eLog(f"Failed to save dumping.pkl: {e}")
                    if should_post == -1:
                        module_logger.Log("Decision: do not post due to error state")
                        vk.account.setOffline()
                        sleep(randint(30, 468))
                        continue
                elif wall_type == 1:
                    temp_time = choose_time(timer)
                    module_logger.Log(f"Choosed time to post: {temp_time}s")
                    last_bot_post = get_last_post(target_group)
                    if last_bot_post is None:
                        module_logger.Log("Can't find my post! Posting right now...")
                        vk.account.setOnline()
                        post(target_group, text, image)
                    elif last_bot_post != -1:
                        module_logger.Log("Found a post, evaluating time threshold")
                        post_time = last_bot_post["date"]
                        if datetime.fromtimestamp(
                            post_time
                        ) <= datetime.now() - timedelta(seconds=temp_time):
                            module_logger.Log("Threshold passed — posting")
                            vk.account.setOnline()
                            post(target_group, text, image)
                    elif last_bot_post == -1:
                        module_logger.Log(
                            "My job here is done (error in get_last_post)"
                        )
                        vk.account.setOffline()
                        sleep(randint(30, 468))
                        continue
                vk.account.setOffline()
                module_logger.Log("Sleep for next iteration")
            sleep(3)
            # time.txt ранее записали текущий момент; resultTime был неиспользуем
            module_logger.eLog("FULL ITERATION PAST")
    except Exception as e:
        module_logger.eLog(str(tgtg) + " " + str(e))
        sleep(60)
        skip = 1
